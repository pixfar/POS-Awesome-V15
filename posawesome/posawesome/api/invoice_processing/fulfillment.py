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

NOT_DELIVERED = "Not Delivered"
PARTLY_DELIVERED = "Partly Delivered"
DELIVERED = "Delivered"


def get_delivery_statuses(names):
    """Bulk delivery status for a set of Sales Invoice names.

    Returns {name: "Not Delivered"|"Partly Delivered"|"Delivered"}. Callers are
    expected to have already excluded Draft/Cancelled/return rows — this only
    looks at quantities.
    """
    if not names:
        return {}

    totals = frappe.db.get_all(
        "Sales Invoice Item",
        filters={"parent": ["in", names]},
        fields=["parent", "sum(qty) as total_qty", "sum(delivered_qty) as total_delivered"],
        group_by="parent",
    )

    statuses = {}
    for row in totals:
        total_qty = flt(row.total_qty)
        total_delivered = flt(row.total_delivered)
        if total_delivered <= 0.0001:
            statuses[row.parent] = NOT_DELIVERED
        elif total_delivered + 0.0001 < total_qty:
            statuses[row.parent] = PARTLY_DELIVERED
        else:
            statuses[row.parent] = DELIVERED
    return statuses


@frappe.whitelist()
def get_sales_invoice_for_delivery(invoice_name):
    """Sales Invoice items with remaining (undelivered) quantity."""
    doc = frappe.get_doc("Sales Invoice", invoice_name)
    if doc.docstatus != 1:
        frappe.throw(_("Only a submitted invoice can be delivered."))
    if doc.is_return:
        frappe.throw(_("This document is a return and cannot be delivered."))
    if cint(doc.update_stock):
        frappe.throw(_("This invoice already moved stock directly and has nothing left to deliver."))

    rows = []
    for row in doc.items:
        remaining = flt(row.qty) - flt(row.delivered_qty)
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
