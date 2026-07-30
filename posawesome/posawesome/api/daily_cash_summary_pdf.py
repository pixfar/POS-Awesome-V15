# Copyright (c) 2026, POS Awesome and contributors
# For license information, please see license.txt

"""Single warehouse, single day view/export of the Daily Cash Summary Report
(bsp_engineering) -- the branch's own cash-box handover slip: Sales
Collection Summary, Fund Transfer, Cash Out Outflow and BSP Deposit,
with the day's Opening/Closing Balance. Reuses the same warehouse-scoped
access rules as the rest of POS Awesome and the same report-data functions as
the underlying Script Report so the numbers always match, whether viewed
in-app (get_report_data) or downloaded as a PDF (download_pdf)."""

import frappe
from frappe import _
from frappe.utils import flt, fmt_money, formatdate, getdate, now_datetime
from frappe.utils.pdf import get_pdf

from posawesome.posawesome.utils.warehouse_doc_permissions import (
	get_expanded_permitted_warehouses,
	is_system_manager,
)

TEMPLATE_PATH = "posawesome/posawesome/templates/daily_cash_summary_pdf.html"


def _ensure_warehouse_access(warehouse):
	if is_system_manager():
		return
	permitted = get_expanded_permitted_warehouses() or []
	if warehouse not in permitted:
		frappe.throw(
			_("You do not have permission to view this warehouse."), exc=frappe.PermissionError
		)


def _get_report_functions():
	from bsp_engineering.bsp_engineering.report.daily_cash_summary_report.daily_cash_summary_report import (
		get_deposits,
		get_expense_claims,
		get_fund_transfers,
		get_opening_balances,
		get_sales_invoices,
	)

	return (
		get_sales_invoices,
		get_expense_claims,
		get_deposits,
		get_fund_transfers,
		get_opening_balances,
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


def _build_context(warehouse, date):
	if not warehouse:
		frappe.throw(_("Warehouse is required."))

	_ensure_warehouse_access(warehouse)

	report_date = getdate(date) if date else getdate()
	company = frappe.db.get_value("Warehouse", warehouse, "company")
	if not company:
		frappe.throw(_("Warehouse not found."))

	(
		get_sales_invoices,
		get_expense_claims,
		get_deposits,
		get_fund_transfers,
		get_opening_balances,
	) = _get_report_functions()

	invoices = get_sales_invoices(company, warehouse, report_date, report_date)
	expenses = get_expense_claims(company, warehouse, report_date, report_date)
	deposits = get_deposits(company, warehouse, report_date, report_date)
	fund_transfers = get_fund_transfers(company, warehouse, report_date, report_date)
	opening_balance = flt(get_opening_balances(company, warehouse, report_date).get(warehouse))

	currency = frappe.get_cached_value("Company", company, "default_currency")

	def money(value):
		return fmt_money(flt(value), currency=currency)

	sales_rows = []
	sales_total = {"selling": 0.0, "discount": 0.0, "due": 0.0, "received": 0.0}
	for idx, inv in enumerate(invoices, start=1):
		selling = flt(inv.grand_total) + flt(inv.discount_amount)
		discount = flt(inv.discount_amount)
		due = flt(inv.outstanding_amount)
		received = flt(inv.grand_total) - flt(inv.outstanding_amount)
		sales_total["selling"] += selling
		sales_total["discount"] += discount
		sales_total["due"] += due
		sales_total["received"] += received
		sales_rows.append(
			{
				"sl": idx,
				"invoice_no": inv.name,
				"selling": money(selling),
				"discount": money(discount),
				"due": money(due),
				"received": money(received),
			}
		)

	fund_transfer_rows = []
	fund_transfer_total = 0.0
	for idx, row in enumerate(fund_transfers, start=1):
		amount = flt(row.amount)
		fund_transfer_total += amount
		fund_transfer_rows.append(
			{
				"sl": idx,
				"particulars": _("Fund Transfer"),
				"description": row.paid_to or "",
				"reference_no": row.name,
				"amount": money(amount),
			}
		)

	# Cash Out Outflow is broken down per expense LINE (Expense Claim Type +
	# its own Description), not one generic "Expense" row per claim -- the
	# claim's own grand_total still drives the income/closing-balance math
	# below, so expense_total is summed separately from the claim rows.
	expense_total = 0.0
	for row in expenses:
		expense_total += flt(row.grand_total)

	expense_claim_names = [row.name for row in expenses]
	expense_lines = (
		frappe.get_all(
			"Expense Claim Detail",
			filters={"parent": ["in", expense_claim_names]},
			fields=["parent", "expense_type", "description", "amount", "sanctioned_amount"],
			order_by="parent, idx",
		)
		if expense_claim_names
		else []
	)

	expense_rows = []
	for idx, row in enumerate(expense_lines, start=1):
		amount = flt(row.sanctioned_amount) or flt(row.amount)
		expense_rows.append(
			{
				"sl": idx,
				"cash_out_type": row.expense_type or _("Expense"),
				"description": row.description or "",
				"reference_no": row.parent,
				"amount": money(amount),
			}
		)

	deposit_rows = []
	deposit_total = 0.0
	for idx, row in enumerate(deposits, start=1):
		amount = flt(row.amount)
		deposit_total += amount
		deposit_rows.append(
			{
				"sl": idx,
				"deposit_type": row.deposit_type or _("Deposit"),
				"bank_name": row.bank_name or "",
				"reference_no": row.name,
				"amount": money(amount),
			}
		)

	income = sales_total["received"] + fund_transfer_total - expense_total
	closing_balance = opening_balance + income - deposit_total

	return {
		"branding": _warehouse_branding(warehouse),
		"report_date": formatdate(report_date, "dd MMMM, yyyy"),
		"report_time": now_datetime().strftime("%I:%M %p"),
		"opening_balance": money(opening_balance),
		"closing_balance": money(closing_balance),
		"expected_deposit": money(income),
		"sales_rows": sales_rows,
		"sales_total": {key: money(value) for key, value in sales_total.items()},
		"fund_transfer_rows": fund_transfer_rows,
		"fund_transfer_total": money(fund_transfer_total),
		"expense_rows": expense_rows,
		"expense_total": money(expense_total),
		"deposit_rows": deposit_rows,
		"deposit_total": money(deposit_total),
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
