import frappe


WORKFLOW_STATES = {
	'In Transit': 'Warning',
	'Requisition Received': 'Success',
}


def execute():
	_create_custom_field({
		'dt': 'Stock Entry',
		'fieldname': 'custom_requisition',
		'fieldtype': 'Link',
		'label': 'Requisition',
		'options': 'Requisition',
		'read_only': 1,
		'insert_after': 'stock_entry_type',
		'in_standard_filter': 1,
	})
	_create_custom_field({
		'dt': 'Stock Entry Detail',
		'fieldname': 'custom_requisition_item',
		'fieldtype': 'Data',
		'label': 'Requisition Item',
		'hidden': 1,
		'read_only': 1,
		'insert_after': 'item_code',
	})
	if not frappe.db.has_column('Stock Entry', 'workflow_state'):
		_create_custom_field({
			'dt': 'Stock Entry',
			'fieldname': 'workflow_state',
			'fieldtype': 'Link',
			'label': 'Workflow State',
			'options': 'Workflow State',
			'hidden': 1,
			'read_only': 1,
			'insert_after': 'custom_requisition',
		})

	for state_name, style in WORKFLOW_STATES.items():
		if frappe.db.exists('Workflow State', state_name):
			continue
		frappe.get_doc({
			'doctype': 'Workflow State',
			'workflow_state_name': state_name,
			'style': style,
		}).insert(ignore_permissions=True)

	_ensure_stock_entry_workflow()


def _create_custom_field(field):
	name = f"{field['dt']}-{field['fieldname']}"
	if frappe.db.exists('Custom Field', name):
		return
	frappe.get_doc({'doctype': 'Custom Field', **field}).insert(
		ignore_permissions=True
	)


def _ensure_stock_entry_workflow():
	workflow_name = 'BSP Material Transfer Receipt'
	if frappe.db.exists('Workflow', workflow_name):
		return

	doc = frappe.get_doc({
		'doctype': 'Workflow',
		'workflow_name': workflow_name,
		'document_type': 'Stock Entry',
		'is_active': 1,
		'workflow_state_field': 'workflow_state',
		'states': [
			{
				'state': 'In Transit',
				'doc_status': '1',
				'allow_edit': 'Stock User',
			},
			{
				'state': 'Requisition Received',
				'doc_status': '1',
				'allow_edit': 'Stock User',
			},
			{
				'state': 'Cancelled',
				'doc_status': '2',
				'allow_edit': 'Stock User',
			},
		],
		'transitions': [
			{
				'state': 'In Transit',
				'action': 'Confirm Receipt',
				'next_state': 'Requisition Received',
				'allowed': 'Stock User',
				'allow_self_approval': 1,
			},
		],
	})
	doc.insert(ignore_permissions=True)
