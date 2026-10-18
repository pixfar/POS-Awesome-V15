import frappe


def execute():
	"""Requisition gained a real Draft status before Sent.

	New requisitions start as Draft (editable). Sent is now the step that
	locks editing, ahead of Seen. Existing unsent rows were stored as
	transfer_status Sent while still docstatus 0, and the POS list labeled
	those Draft -- move them to Draft so they stay editable until someone
	sends them. Reload the Select options first so Draft is a valid value.
	"""
	frappe.reload_doc('posawesome', 'doctype', 'requisition', force=True)

	frappe.db.sql(
		"""
		UPDATE `tabRequisition`
		SET transfer_status = 'Draft'
		WHERE docstatus = 0 AND transfer_status = 'Sent'
		"""
	)
