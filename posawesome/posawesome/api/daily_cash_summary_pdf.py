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
from frappe.utils import flt, fmt_money, formatdate, getdate, now_datetime
from frappe.utils.pdf import get_pdf

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


def _get_report_functions():
	from bsp_engineering.bsp_engineering.report.daily_cash_summary_report.daily_cash_summary_report import (
		get_deposits,
		get_expense_claims,
		get_fund_transfers,
		get_gl_balance,
		get_opening_balances,
		get_purchase_invoices,
		get_sales_invoices,
	)

	return (
		get_sales_invoices,
		get_purchase_invoices,
		get_expense_claims,
		get_deposits,
		get_fund_transfers,
		get_opening_balances,
		get_gl_balance,
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


def _get_party_payments(company, warehouse, accounts, report_date):
	"""Customer / Supplier Payment Entries posted on report_date that moved
	money through this warehouse's till -- its cash account(s) as paid_to /
	paid_from, or tagged with the warehouse (custom_warehouse). Covers the
	sale-time payments POS creates as well as payments made later from
	Payments > Customer / Supplier.

	`cash` is the signed effect on the till: + money in, - money out.
	`refs` maps reference_name -> allocated_amount (company currency)."""
	conditions = ["pe.custom_warehouse = %(warehouse)s"]
	if accounts:
		conditions += ["pe.paid_to IN %(accounts)s", "pe.paid_from IN %(accounts)s"]

	rows = frappe.db.sql(
		f"""
		SELECT pe.name, pe.payment_type, pe.party_type, pe.party, pe.party_name,
		       pe.mode_of_payment, pe.reference_no, pe.custom_cheque_bank,
		       pe.base_paid_amount, pe.base_received_amount
		FROM `tabPayment Entry` pe
		WHERE pe.docstatus = 1
		  AND pe.company = %(company)s
		  AND pe.posting_date = %(date)s
		  AND pe.party_type IN ('Customer', 'Supplier')
		  AND ({" OR ".join(conditions)})
		ORDER BY pe.creation, pe.name
		""",
		{"company": company, "date": report_date, "warehouse": warehouse, "accounts": tuple(accounts or [""])},
		as_dict=True,
	)
	if not rows:
		return []

	refs = frappe.db.sql(
		"""
		SELECT parent, reference_doctype, reference_name, allocated_amount
		FROM `tabPayment Entry Reference`
		WHERE parent IN %(names)s
		ORDER BY idx
		""",
		{"names": tuple(row.name for row in rows)},
		as_dict=True,
	)
	refs_by_pe = {}
	for ref in refs:
		refs_by_pe.setdefault(ref.parent, []).append(ref)

	for row in rows:
		row.cash = flt(row.base_received_amount) if row.payment_type == "Receive" else -flt(row.base_paid_amount)
		row.refs = refs_by_pe.get(row.name, [])
	return rows


def _get_journal_party_map(journal_names):
	"""{journal entry: "Customer: X, Supplier: Y"} -- the parties named on the
	other rows of each Journal Entry, so a JE payment to/from a customer or
	supplier shows who it was for."""
	if not journal_names:
		return {}
	rows = frappe.db.sql(
		"""
		SELECT DISTINCT parent, party_type, party
		FROM `tabJournal Entry Account`
		WHERE parent IN %(names)s AND IFNULL(party, '') != ''
		""",
		{"names": tuple(journal_names)},
		as_dict=True,
	)
	parties = {}
	for row in rows:
		parties.setdefault(row.parent, []).append(f"{row.party_type}: {row.party}")
	return {name: ", ".join(values) for name, values in parties.items()}


def _build_context(warehouse, date):
	"""One warehouse, one day. Money received / paid is counted on the
	Payment Entry's own posting date, so a customer paying an old invoice
	today shows up today (Customer Payments) and never changes an earlier
	day's figures."""
	if not warehouse:
		frappe.throw(_("Warehouse is required."))

	_ensure_warehouse_access(warehouse)

	report_date = getdate(date) if date else getdate()
	company = frappe.db.get_value("Warehouse", warehouse, "company")
	if not company:
		frappe.throw(_("Warehouse not found."))

	(
		get_sales_invoices,
		get_purchase_invoices,
		get_expense_claims,
		get_deposits,
		get_fund_transfers,
		get_opening_balances,
		get_gl_balance,
	) = _get_report_functions()
	from bsp_engineering.utils.warehouse_accounts import get_accounts_for_warehouse

	wh_accounts = get_accounts_for_warehouse(warehouse)

	invoices = get_sales_invoices(company, warehouse, report_date, report_date)
	purchases = get_purchase_invoices(company, warehouse, report_date, report_date)
	expenses = get_expense_claims(company, warehouse, report_date, report_date)
	deposits = get_deposits(company, warehouse, report_date, report_date)
	transfers = get_fund_transfers(company, warehouse, report_date, report_date)
	payments = _get_party_payments(company, warehouse, wh_accounts, report_date)
	opening_balance = flt(get_opening_balances(company, warehouse, report_date).get(warehouse))

	# get_fund_transfers() also returns manual Journal Entries against the
	# till's accounts -- shown in their own section here.
	fund_transfers = [row for row in transfers if row.get("source_label") != _("Journal Entry")]
	journals = [row for row in transfers if row.get("source_label") == _("Journal Entry")]

	currency = frappe.get_cached_value("Company", company, "default_currency")

	def money(value):
		return fmt_money(flt(value), currency=currency)

	# ── Money received / paid today against today's own invoices ─────────
	sales_names = {inv.name for inv in invoices}
	purchase_names = {inv.name for inv in purchases}
	received_today, paid_today = {}, {}
	for pe in payments:
		for ref in pe.refs:
			if pe.party_type == "Customer" and ref.reference_name in sales_names:
				received_today[ref.reference_name] = received_today.get(ref.reference_name, 0.0) + flt(
					ref.allocated_amount
				)
			elif pe.party_type == "Supplier" and ref.reference_name in purchase_names:
				paid_today[ref.reference_name] = paid_today.get(ref.reference_name, 0.0) + flt(
					ref.allocated_amount
				)

	# ── Sales Collection Summary ──────────────────────────────────────────
	sales_rows = []
	sales_total = {"selling": 0.0, "discount": 0.0, "due": 0.0, "received": 0.0}
	for idx, inv in enumerate(invoices, start=1):
		selling = flt(inv.grand_total) + flt(inv.discount_amount)
		discount = flt(inv.discount_amount)
		received = received_today.get(inv.name, 0.0)
		due = flt(inv.grand_total) - received
		sales_total["selling"] += selling
		sales_total["discount"] += discount
		sales_total["due"] += due
		sales_total["received"] += received
		sales_rows.append(
			{
				"sl": idx,
				"invoice_no": inv.name,
				"description": _("Return against {0}").format(inv.return_against) if inv.is_return else "",
				"selling": money(selling),
				"discount": money(discount),
				"due": money(due),
				"received": money(received),
			}
		)

	# ── Purchase Summary ──────────────────────────────────────────────────
	purchase_rows = []
	purchase_total = {"purchase": 0.0, "discount": 0.0, "due": 0.0, "paid": 0.0}
	for idx, inv in enumerate(purchases, start=1):
		amount = flt(inv.grand_total) + flt(inv.discount_amount)
		discount = flt(inv.discount_amount)
		paid = paid_today.get(inv.name, 0.0)
		due = flt(inv.grand_total) - paid
		purchase_total["purchase"] += amount
		purchase_total["discount"] += discount
		purchase_total["due"] += due
		purchase_total["paid"] += paid
		purchase_rows.append(
			{
				"sl": idx,
				"invoice_no": inv.name,
				"supplier": frappe.db.get_value("Purchase Invoice", inv.name, "supplier_name") or "",
				"description": _("Return against {0}").format(inv.return_against) if inv.is_return else "",
				"purchase": money(amount),
				"discount": money(discount),
				"due": money(due),
				"paid": money(paid),
			}
		)

	# ── Customer / Supplier Payments (not for today's own invoices) ───────
	def payment_rows_for(party_type, own_invoices):
		rows, total = [], 0.0
		for pe in payments:
			if pe.party_type != party_type:
				continue
			own = sum(flt(r.allocated_amount) for r in pe.refs if r.reference_name in own_invoices)
			# Signed from the till's point of view: + in, - out.
			own_cash = own if party_type == "Customer" else -own
			amount = flt(pe.cash) - own_cash
			if abs(amount) < 0.005:
				continue
			other_refs = [r.reference_name for r in pe.refs if r.reference_name not in own_invoices]
			total += amount
			rows.append(
				{
					"sl": len(rows) + 1,
					"party": pe.party_name or pe.party,
					"payment_type": _(pe.payment_type),
					"mode_of_payment": pe.mode_of_payment or "",
					"against": ", ".join(other_refs) if other_refs else _("Advance / On Account"),
					"reference_no": pe.name,
					"cheque": " ".join(filter(None, [pe.custom_cheque_bank, pe.reference_no]))
					if pe.custom_cheque_bank
					else "",
					"amount": money(abs(amount)),
					"signed_amount": amount,
				}
			)
		return rows, total

	customer_payment_rows, customer_payment_total = payment_rows_for("Customer", sales_names)
	supplier_payment_rows, supplier_payment_total = payment_rows_for("Supplier", purchase_names)
	# Supplier total as money *out* of the till (positive = paid out).
	supplier_payment_out = -supplier_payment_total

	# ── Fund Transfer ─────────────────────────────────────────────────────
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

	# ── Journal Entries against the till's cash account(s) ────────────────
	journal_parties = _get_journal_party_map([row.name for row in journals])
	journal_rows = []
	journal_total = 0.0
	for idx, row in enumerate(journals, start=1):
		amount = flt(row.amount)
		journal_total += amount
		journal_rows.append(
			{
				"sl": idx,
				"party": journal_parties.get(row.name, ""),
				"description": row.get("reference_no") or "",
				"reference_no": row.name,
				"direction": _("In") if amount >= 0 else _("Out"),
				"amount": money(amount),
			}
		)

	# ── Cash Out Outflow (expense claim lines) ────────────────────────────
	expense_total = sum(flt(row.grand_total) for row in expenses)
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

	# ── BSP Deposit ───────────────────────────────────────────────────────
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

	# ── Totals ────────────────────────────────────────────────────────────
	total_collection = sales_total["received"] + customer_payment_total
	total_purchase_paid = purchase_total["paid"] + supplier_payment_out
	income = total_collection + fund_transfer_total + journal_total - expense_total - total_purchase_paid
	formula_closing_balance = opening_balance + income - deposit_total

	# GL-mapped warehouse: the real ledger balance of its cash account(s) --
	# the same figure Trial Balance shows. Anything posted to those accounts
	# that none of the sections above list is shown as Other Ledger Activity
	# instead of being silently absorbed.
	closing_balance = (
		get_gl_balance(wh_accounts, company, report_date) if wh_accounts else formula_closing_balance
	)
	other_activity = closing_balance - formula_closing_balance if wh_accounts else 0.0
	if abs(other_activity) < 0.005:
		other_activity = 0.0

	return {
		"branding": _warehouse_branding(warehouse),
		"report_date": formatdate(report_date, "dd MMMM, yyyy"),
		"report_time": now_datetime().strftime("%I:%M %p"),
		"opening_balance": money(opening_balance),
		"closing_balance": money(closing_balance),
		"expected_deposit": money(income),
		"total_collection": money(total_collection),
		"total_purchase_paid": money(total_purchase_paid),
		"other_activity": money(other_activity) if other_activity else "",
		"sales_rows": sales_rows,
		"sales_total": {key: money(value) for key, value in sales_total.items()},
		"purchase_rows": purchase_rows,
		"purchase_total": {key: money(value) for key, value in purchase_total.items()},
		"customer_payment_rows": customer_payment_rows,
		"customer_payment_total": money(customer_payment_total),
		"supplier_payment_rows": supplier_payment_rows,
		"supplier_payment_total": money(supplier_payment_out),
		"fund_transfer_rows": fund_transfer_rows,
		"fund_transfer_total": money(fund_transfer_total),
		"journal_rows": journal_rows,
		"journal_total": money(journal_total),
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
