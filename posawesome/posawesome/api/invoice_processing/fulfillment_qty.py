"""Remaining delivery/receipt qty helpers that subtract invoice returns.

ERPNext's delivered_qty / received_qty only track fulfillment notes. POS also
allows Sales/Purchase Invoice returns before or after fulfillment — those
returned quantities must no longer be deliverable/receivable.
"""

from collections import defaultdict

import frappe
from frappe.utils import flt


def get_returned_qty_by_invoice_item(doctype, invoice_names):
	"""Map source invoice item row -> abs(returned qty).

	Returns {invoice_name: {source_item_row_name: returned_qty}}.
	"""
	if not invoice_names:
		return {}

	ref_field = (
		"sales_invoice_item"
		if doctype == "Sales Invoice"
		else "purchase_invoice_item"
	)
	item_doctype = f"{doctype} Item"

	returns = frappe.get_all(
		doctype,
		filters={
			"return_against": ["in", list(invoice_names)],
			"docstatus": 1,
			"is_return": 1,
		},
		fields=["name", "return_against"],
	)
	if not returns:
		return {name: {} for name in invoice_names}

	return_against = {row.name: row.return_against for row in returns}
	rows = frappe.get_all(
		item_doctype,
		filters={"parent": ["in", list(return_against.keys())]},
		fields=["parent", ref_field, "qty", "item_code"],
	)

	result = {name: defaultdict(float) for name in invoice_names}
	# Fallback when return rows lack the source-item link: by item_code.
	by_code = {name: defaultdict(float) for name in invoice_names}

	for row in rows:
		invoice_name = return_against.get(row.parent)
		if not invoice_name:
			continue
		qty = abs(flt(row.qty))
		source_row = row.get(ref_field)
		if source_row:
			result[invoice_name][source_row] += qty
		else:
			by_code[invoice_name][row.item_code] += qty

	# Apply item_code fallback only for return docs that had no row links,
	# distributing onto the first matching source item (same as returns.py).
	unlinked_codes = {
		inv: codes
		for inv, codes in by_code.items()
		if codes
	}
	if unlinked_codes:
		source_items = frappe.get_all(
			item_doctype,
			filters={"parent": ["in", list(unlinked_codes.keys())]},
			fields=["name", "parent", "item_code"],
		)
		first_row_by_code = {}
		for item in source_items:
			key = (item.parent, item.item_code)
			first_row_by_code.setdefault(key, item.name)
		for invoice_name, codes in unlinked_codes.items():
			for item_code, qty in codes.items():
				row_name = first_row_by_code.get((invoice_name, item_code))
				if row_name:
					result[invoice_name][row_name] += qty

	return {name: dict(vals) for name, vals in result.items()}


def get_returned_qty_totals(doctype, invoice_names):
	"""Map invoice_name -> total abs(returned qty) across all return items."""
	by_item = get_returned_qty_by_invoice_item(doctype, invoice_names)
	return {
		name: sum(vals.values()) for name, vals in by_item.items()
	}


def remaining_fulfillment_qty(row_qty, fulfilled_qty, returned_qty):
	"""qty still open for Delivery Note / Purchase Receipt."""
	return max(0.0, flt(row_qty) - flt(fulfilled_qty) - flt(returned_qty))


def get_linked_returns(doctype, invoice_name):
	"""Submitted return invoices linked to a source Sales/Purchase Invoice.

	Used by the POS detail page so cashiers can jump to each return doc.
	"""
	if not invoice_name or doctype not in ("Sales Invoice", "Purchase Invoice"):
		return []

	rows = frappe.get_all(
		doctype,
		filters={
			"return_against": invoice_name,
			"docstatus": 1,
			"is_return": 1,
		},
		fields=[
			"name",
			"posting_date",
			"posting_time",
			"creation",
			"status",
			"currency",
			"grand_total",
			"outstanding_amount",
			"total_qty",
		],
		order_by="creation asc",
	)
	result = []
	for row in rows:
		grand_total = flt(row.grand_total)
		outstanding = flt(row.outstanding_amount)
		result.append(
			{
				"name": row.name,
				"posting_date": row.posting_date,
				"posting_time": row.posting_time,
				"creation": row.creation,
				"status": row.status,
				"currency": row.currency,
				"grand_total": grand_total,
				# Returns carry negative totals; show abs qty for the list.
				"total_qty": abs(flt(row.total_qty)),
				"outstanding_amount": outstanding,
				"paid_amount": abs(grand_total) - outstanding,
			}
		)
	return result
