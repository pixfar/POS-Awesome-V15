# Copyright (c) 2026, POS Awesome and contributors
# For license information, please see license.txt

"""Shared helper for the "Weight" column/total shown across POS Awesome's
Sales, Purchase, Material Transfer, Requisition, BOM and Production Plan
create/list/detail pages.

An item's weight-per-unit lives on the Item master
(`custom_default_weigt_of_measure`), not on any of these transaction
doctypes' own child rows -- every list page needs a per-document *total*
weight (qty * that item field, summed across all its lines), which this
computes in one JOIN query per list page rather than N+1 lookups.
"""

import frappe
from frappe.utils import flt


def get_total_weight_by_parent(child_doctype, parent_names, item_code_field="item_code", qty_field="qty"):
    """Bulk per-parent total weight for a batch of documents.

    Returns {parent_name: total_weight}. A parent with no rows, or whose
    items don't resolve to a real Item (or one with no weight set), simply
    isn't a key in the result -- callers should default missing entries to 0.
    """
    parent_names = [name for name in (parent_names or []) if name]
    if not parent_names:
        return {}

    rows = frappe.db.sql(
        f"""
        SELECT child.parent AS parent,
               SUM(IFNULL(child.{qty_field}, 0) * IFNULL(item.custom_default_weigt_of_measure, 0)) AS total_weight
        FROM `tab{child_doctype}` child
        INNER JOIN `tabItem` item ON item.name = child.{item_code_field}
        WHERE child.parent IN %(parent_names)s
        GROUP BY child.parent
        """,
        {"parent_names": tuple(parent_names)},
        as_dict=True,
    )
    return {row.parent: flt(row.total_weight) for row in rows}
