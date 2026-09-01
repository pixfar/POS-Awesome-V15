import frappe


def execute():
	"""Requisition's transfer_status Select gained a new "Seen" step between
	Sent and the (renamed) "Completed" step -- reload the schema so the
	widened option list is in the DB before touching any rows, then rename
	every existing "Received" row to "Completed" so old data still validates
	against the new option list."""
	frappe.reload_doc('posawesome', 'doctype', 'requisition', force=True)

	frappe.db.set_value(
		'Requisition',
		{'transfer_status': 'Received'},
		'transfer_status',
		'Completed',
		update_modified=False,
	)
