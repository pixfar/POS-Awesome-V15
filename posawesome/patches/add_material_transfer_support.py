import frappe


def execute():
	_create_custom_field({
		'dt': 'Stock Entry',
		'fieldname': 'custom_material_transfer',
		'fieldtype': 'Link',
		'label': 'Material Transfer',
		'options': 'Material Transfer',
		'read_only': 1,
		'insert_after': 'custom_requisition',
		'in_standard_filter': 1,
	})
	_create_custom_field({
		'dt': 'Stock Entry Detail',
		'fieldname': 'custom_material_transfer_item',
		'fieldtype': 'Data',
		'label': 'Material Transfer Item',
		'hidden': 1,
		'read_only': 1,
		'insert_after': 'custom_requisition_item',
	})


def _create_custom_field(field):
	name = f"{field['dt']}-{field['fieldname']}"
	if frappe.db.exists('Custom Field', name):
		return
	frappe.get_doc({'doctype': 'Custom Field', **field}).insert(
		ignore_permissions=True
	)
