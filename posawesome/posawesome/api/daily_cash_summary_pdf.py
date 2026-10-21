# Copyright (c) 2026, POS Awesome and contributors
# For license information, please see license.txt

"""Single warehouse, single day view/export of the Daily Cash Summary Report
(bsp_engineering) -- the branch's own cash-box handover slip: Sales
Collection Summary, Purchase Summary, Customer / Supplier Payments, Fund
Transfer, Journal Entries, Cash Out Outflow and BSP Deposit, with the day's
Opening/Closing Balance. Reuses the same warehouse-scoped
access rules as the rest of POS Awesome and the same report-data functions as
the underlying Script Report so the numbers always match, whether viewed
in-app (get_report_data) or downloaded as a PDF (download_pdf)."""

import frappe
from frappe import _
from frappe.utils import add_days, cint, flt, fmt_money, formatdate, getdate, now_datetime, today
from frappe.utils.pdf import get_pdf
from frappe.utils.verified_command import get_signed_params, verify_request

from posawesome.posawesome.utils.warehouse_doc_permissions import (
	get_expanded_permitted_warehouses,
)

TEMPLATE_PATH = "posawesome/posawesome/templates/daily_cash_summary_pdf.html"


def _ensure_warehouse_access(warehouse):
	# None means unrestricted (System Manager / BSP Admin / BSP Viewer --
	# get_expanded_permitted_warehouses already covers all three); `or []`
	# used to collapse that into "no warehouse allowed", which is why a BSP
	# Viewer picking any warehouse other than their own POS Profile default
	# got "You do not have permission to view this warehouse" here even
	# though the warehouse *switcher* itself had already correctly opened up
	# for them.
	permitted = get_expanded_permitted_warehouses()
	if permitted is None:
		return
	if warehouse not in permitted:
		frappe.throw(
			_("You do not have permission to view this warehouse."), exc=frappe.PermissionError
		)


def _warehouse_branding(warehouse):
	wh = (
		frappe.db.get_value(
			"Warehouse",
			warehouse,
			["warehouse_name", "address_line_1", "mobile_no"],
			as_dict=True,
		)
		or {}
	)

	tagline, address = "", ""
	raw = (wh.get("address_line_1") or "").strip()
	if raw:
		lines = [line.strip() for line in raw.splitlines() if line.strip()]
		if lines:
			tagline = lines[0]
			address = " ".join(lines[1:])

	mobile = wh.get("mobile_no") or ""
	if mobile and not mobile.startswith(("0", "+")):
		mobile = "0" + mobile

	return {
		"warehouse_name": wh.get("warehouse_name") or warehouse,
		"tagline": tagline,
		"address": address,
		"mobile": mobile,
	}


def _build_context(warehouse, date, check_access=True):
	"""One warehouse, one day. The figures come from the Script Report's own
	get_day_summary() so this page, its PDF and the Daily Cash Summary
	Script Report always match; this only formats them for display."""
	from bsp_engineering.bsp_engineering.report.daily_cash_summary_report.daily_cash_summary_report import (
		get_day_summary,
	)

	if not warehouse:
		frappe.throw(_("Warehouse is required."))

	if check_access:
		_ensure_warehouse_access(warehouse)

	report_date = getdate(date) if date else getdate()
	company = frappe.db.get_value("Warehouse", warehouse, "company")
	if not company:
		frappe.throw(_("Warehouse not found."))

	summary = get_day_summary(company, warehouse, report_date)
	currency = frappe.get_cached_value("Company", company, "default_currency")

	def money(value):
		return fmt_money(flt(value), currency=currency)

	def formatted(rows, *money_fields):
		return [{**row, **{field: money(row[field]) for field in money_fields}} for row in rows]

	def payment_rows(rows):
		# Payments show the amount unsigned; the till direction is kept in signed_amount.
		return [{**row, "amount": money(abs(row.amount)), "signed_amount": row.amount} for row in rows]

	return {
		"branding": _warehouse_branding(warehouse),
		"report_date": formatdate(report_date, "dd MMMM, yyyy"),
		"report_time": now_datetime().strftime("%I:%M %p"),
		"opening_balance": money(summary.opening_balance),
		"closing_balance": money(summary.closing_balance),
		"expected_deposit": money(summary.income),
		"total_collection": money(summary.total_collection),
		"total_purchase_paid": money(summary.total_purchase_paid),
		"other_activity": money(summary.other_activity) if summary.other_activity else "",
		"sales_rows": formatted(summary.sales_rows, "selling", "discount", "due", "received"),
		"sales_total": {key: money(value) for key, value in summary.sales_total.items()},
		"purchase_rows": formatted(summary.purchase_rows, "purchase", "discount", "due", "paid"),
		"purchase_total": {key: money(value) for key, value in summary.purchase_total.items()},
		"customer_payment_rows": payment_rows(summary.customer_payment_rows),
		"customer_payment_total": money(summary.customer_payment_total),
		"supplier_payment_rows": payment_rows(summary.supplier_payment_rows),
		"supplier_payment_total": money(summary.supplier_payment_out),
		"fund_transfer_rows": formatted(summary.fund_transfer_rows, "amount"),
		"fund_transfer_total": money(summary.fund_transfer_total),
		"journal_rows": formatted(summary.journal_rows, "amount"),
		"journal_total": money(summary.journal_total),
		"expense_rows": formatted(summary.expense_rows, "amount"),
		"expense_total": money(summary.expense_total),
		"deposit_rows": formatted(summary.deposit_rows, "amount"),
		"deposit_total": money(summary.deposit_total),
	}


@frappe.whitelist()
def get_report_data(warehouse, date=None):
	return _build_context(warehouse, date)


@frappe.whitelist()
def download_pdf(warehouse, date=None):
	context = _build_context(warehouse, date)
	report_date = getdate(date) if date else getdate()

	html = frappe.render_template(TEMPLATE_PATH, context, is_path=True)
	pdf_content = get_pdf(html)

	filename = f"Daily Cash Summary Report- {formatdate(report_date, 'dd-mm-yyyy')}.pdf"
	frappe.local.response.filename = filename
	frappe.local.response.filecontent = pdf_content
	frappe.local.response.type = "pdf"


def _render_pdf(warehouse, date, check_access=True):
	context = _build_context(warehouse, date, check_access=check_access)
	report_date = getdate(date) if date else getdate()
	html = frappe.render_template(TEMPLATE_PATH, context, is_path=True)
	frappe.local.response.filename = f"Daily Cash Summary Report- {formatdate(report_date, 'dd-mm-yyyy')}.pdf"
	frappe.local.response.filecontent = get_pdf(html)
	frappe.local.response.type = "pdf"


@frappe.whitelist()
def get_share_link(warehouse, date=None):
	"""Public link to this warehouse/day's PDF -- for any user who may view it
	(same access check as the page itself; no special role needed). The link
	is signed with the site secret, so warehouse/date can't be altered, and
	stops working after the Document Share Key expiry (System Settings,
	default 30 days) -- same lifetime as document "Share" links."""
	_ensure_warehouse_access(warehouse)
	report_date = getdate(date) if date else getdate()
	days = cint(frappe.db.get_single_value("System Settings", "document_share_key_expiry")) or 30
	expires_on = add_days(today(), days)
	params = get_signed_params(
		{"warehouse": warehouse, "date": str(report_date), "expires_on": str(expires_on)}
	)
	return {
		"path": f"/api/method/posawesome.posawesome.api.daily_cash_summary_pdf.download_shared_pdf?{params}",
		"expires_on": expires_on,
	}


@frappe.whitelist(allow_guest=True, methods=["GET"])
def download_shared_pdf(warehouse, date, expires_on, **kwargs):
	"""Opens a get_share_link() link without logging in."""
	if not verify_request():
		frappe.throw(_("This link is invalid."), frappe.PermissionError)
	if getdate(expires_on) < getdate(today()):
		frappe.throw(_("This link has expired."), frappe.PermissionError)
	# Access was checked for the user who created the link.
	_render_pdf(warehouse, date, check_access=False)
