# Copyright (c) 2026, POS Awesome contributors
# For license information, please see license.txt

import frappe


def execute():
	"""Ensure Material Transfer.requisition exists for sites that already
	synced the DocType before the Link field was added to JSON."""
	if frappe.db.has_column("Material Transfer", "requisition"):
		return

	frappe.reload_doc("POSAwesome", "doctype", "material_transfer")
	frappe.db.commit()
