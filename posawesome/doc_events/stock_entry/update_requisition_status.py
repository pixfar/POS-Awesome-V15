import frappe
from posawesome.posawesome.doctype.requisition.transfer_status import (
	update_requisition_transfer_status,
)


def sync_requisition_transfer_status(doc, method=None):
	requisition = doc.get('custom_requisition')

	if doc.docstatus == 2 and doc.get('workflow_state') != 'Cancelled':
		frappe.db.set_value(
			'Stock Entry', doc.name, 'workflow_state', 'Cancelled', update_modified=False
		)

	if not requisition:
		return
	update_requisition_transfer_status(requisition)
