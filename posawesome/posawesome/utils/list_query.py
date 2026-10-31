# Copyright (c) 2026, POS Awesome and contributors
# For license information, please see license.txt

"""Shared helpers for fast POS list endpoints."""

from __future__ import annotations

import frappe
from frappe.utils import cint


def count_distinct(
	doctype,
	filters=None,
	or_filters=None,
	distinct_field="name",
):
	"""COUNT(DISTINCT …) for a get_list-compatible filter set.

	Replaces ``len(frappe.get_list(..., limit_page_length=0))``, which pulls
	every matching name into Python and stalls list pages on large tables.
	"""
	table_field = (
		f"count(distinct `tab{doctype}`.{distinct_field}) as total"
		if "." not in distinct_field and not distinct_field.startswith("`")
		else f"count(distinct {distinct_field}) as total"
	)
	rows = frappe.get_list(
		doctype,
		filters=filters,
		or_filters=or_filters,
		fields=[table_field],
		ignore_permissions=True,
		limit_page_length=1,
	)
	return cint((rows[0].total if rows else 0) or 0)
