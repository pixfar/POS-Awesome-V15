import frappe


def create_column_pref_doctype():
	"""Ensure POS Awesome Column Preference exists (legacy bootstrap).

	Prefer the real DocType under posawesome/doctype; this remains as a
	safe fallback for sites that have not migrated yet.
	"""
	if frappe.db.exists("DocType", "POS Awesome Column Preference"):
		return

	doc = frappe.get_doc(
		{
			"doctype": "DocType",
			"module": "POSAwesome",
			"name": "POS Awesome Column Preference",
			"custom": 0,
			"istable": 0,
			"fields": [
				{
					"fieldname": "user",
					"fieldtype": "Link",
					"options": "User",
					"label": "User",
					"reqd": 1,
					"in_list_view": 1,
				},
				{
					"fieldname": "report_name",
					"fieldtype": "Data",
					"label": "Report Name",
					"reqd": 1,
					"in_list_view": 1,
				},
				{
					"fieldname": "selected_columns",
					"fieldtype": "JSON",
					"label": "Selected Columns",
				},
			],
			"permissions": [
				{
					"role": "System Manager",
					"read": 1,
					"write": 1,
					"create": 1,
					"delete": 1,
				},
				{
					"role": "BSP Admin",
					"read": 1,
					"write": 1,
					"create": 1,
					"delete": 1,
				},
				{
					"role": "All",
					"read": 1,
					"write": 1,
					"create": 1,
					"delete": 1,
				},
			],
			"naming_rule": "Expression",
			"autoname": "format:{user}-{report_name}",
		}
	)
	doc.insert(ignore_permissions=True)
	frappe.db.commit()
