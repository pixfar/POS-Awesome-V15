import frappe


WAREHOUSE_DOC_FIELDS = {
	'Requisition': ['source_warehouse', 'target_warehouse'],
	'Material Transfer': ['from_warehouse', 'to_warehouse'],
}


def execute():
	"""Stop Frappe AND-filtering on multiple warehouse link fields."""
	for doctype, fieldnames in WAREHOUSE_DOC_FIELDS.items():
		for fieldname in fieldnames:
			_set_ignore_user_permissions(doctype, fieldname)


def _set_ignore_user_permissions(doctype, fieldname):
	existing = frappe.db.get_value(
		'Property Setter',
		{
			'doc_type': doctype,
			'field_name': fieldname,
			'property': 'ignore_user_permissions',
		},
		'name',
	)
	if existing:
		frappe.db.set_value(
			'Property Setter',
			existing,
			'value',
			'1',
			update_modified=False,
		)
		return

	frappe.make_property_setter(
		{
			'doctype': doctype,
			'fieldname': fieldname,
			'property': 'ignore_user_permissions',
			'value': '1',
			'property_type': 'Check',
		},
		ignore_validate=True,
	)
