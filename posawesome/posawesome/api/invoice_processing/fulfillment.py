"""Delivery Note / Purchase Receipt fulfillment status and item lookups.

Sales Invoices (and Purchase Invoices) submitted with `update_stock` unchecked
defer their stock movement to a separate Delivery Note / Purchase Receipt.
ERPNext tracks the outstanding quantity per item via `qty` vs `delivered_qty`
(Sales Invoice Item) / `received_qty` (Purchase Invoice Item) — this module
reads that state in bulk for list views and per-invoice for the fulfillment
dialog. See `returns.py`'s `get_invoice_for_return` for the pattern this mirrors.
"""

import frappe
from frappe import _
from frappe.utils import cint, flt

from posawesome.posawesome.api.invoice_processing.fulfillment_qty import (
	get_returned_qty_by_invoice_item,
	get_returned_qty_totals,
	remaining_fulfillment_qty,
)

NOT_DELIVERED = "Not Delivered"
PARTLY_DELIVERED = "Partly Delivered"
DELIVERED = "Delivered"


def _status_from_qty(net_qty, total_delivered):
	if net_qty <= 0.0001:
		# Fully returned — treat as delivered so Create Delivery stays hidden.
		return DELIVERED
	if total_delivered <= 0.0001:
		return NOT_DELIVERED
	if total_delivered + 0.0001 < net_qty:
		return PARTLY_DELIVERED
	return DELIVERED


def get_delivery_statuses(names):
	"""Bulk delivery status for a set of Sales Invoice names.

	Returns {name: "Not Delivered"|"Partly Delivered"|"Delivered"}. Callers are
	expected to have already excluded Draft/Cancelled/return rows — this only
	looks at quantities. Returned qty is subtracted from the deliverable total.
	"""
	if not names:
		return {}

	totals = frappe.db.get_all(
		"Sales Invoice Item",
		filters={"parent": ["in", names]},
		fields=["parent", "sum(qty) as total_qty", "sum(delivered_qty) as total_delivered"],
		group_by="parent",
	)
	returned_totals = get_returned_qty_totals("Sales Invoice", names)

	statuses = {}
	for row in totals:
		net_qty = flt(row.total_qty) - flt(returned_totals.get(row.parent, 0))
		statuses[row.parent] = _status_from_qty(net_qty, flt(row.total_delivered))
	return statuses


def sales_invoice_names_for_delivery_status(company, delivery_status):
	"""Submitted, non-return Sales Invoice names whose delivery status matches.

	Mirrors get_delivery_statuses, including update_stock invoices, which are
	Delivered even though delivered_qty stays 0.
	"""
	if delivery_status not in (NOT_DELIVERED, PARTLY_DELIVERED, DELIVERED) or not company:
		return []

	rows = frappe.db.sql(
		"""
		SELECT si.name,
		       IFNULL(si.update_stock, 0) AS update_stock,
		       COALESCE(SUM(sii.qty), 0) AS total_qty,
		       COALESCE(SUM(sii.delivered_qty), 0) AS total_delivered
		FROM `tabSales Invoice` si
		INNER JOIN `tabSales Invoice Item` sii ON sii.parent = si.name
		WHERE si.docstatus = 1
		  AND IFNULL(si.is_return, 0) = 0
		  AND si.company = %(company)s
		GROUP BY si.name, si.update_stock
		""",
		{"company": company},
		as_dict=True,
	)
	returned_totals = get_returned_qty_totals(
		"Sales Invoice", [row.name for row in rows]
	)
	names = []
	for row in rows:
		if cint(row.update_stock):
			status = DELIVERED
		else:
			net_qty = flt(row.total_qty) - flt(returned_totals.get(row.name, 0))
			status = _status_from_qty(net_qty, flt(row.total_delivered))
		if status == delivery_status:
			names.append(row.name)
	return names


@frappe.whitelist()
def get_sales_invoice_for_delivery(invoice_name):
	"""Sales Invoice items with remaining (undelivered, non-returned) quantity."""
	doc = frappe.get_doc("Sales Invoice", invoice_name)
	if doc.docstatus != 1:
		frappe.throw(_("Only a submitted invoice can be delivered."))
	if doc.is_return:
		frappe.throw(_("This document is a return and cannot be delivered."))
	if cint(doc.update_stock):
		frappe.throw(
			_("This invoice already moved stock directly and has nothing left to deliver.")
		)

	returned = get_returned_qty_by_invoice_item(
		"Sales Invoice", [doc.name]
	).get(doc.name, {})

	rows = []
	for row in doc.items:
		remaining = remaining_fulfillment_qty(
			row.qty, row.delivered_qty, returned.get(row.name, 0)
		)
		if remaining <= 0.0001:
			continue
		rows.append(
			{
				"name": row.name,
				"item_code": row.item_code,
				"item_name": row.item_name,
				"uom": row.uom,
				"qty": remaining,
			}
		)
	return {"name": doc.name, "items": rows}
