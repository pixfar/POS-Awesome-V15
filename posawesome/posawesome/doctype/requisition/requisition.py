# Copyright (c) 2026, POS Awesome and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class Requisition(Document):
	def before_insert(self):
		self.requested_by = frappe.session.user
		self.transfer_status = 'Draft'

	def on_submit(self):
		self.db_set('transfer_status', 'Sent', update_modified=False)

	def validate(self):
		if self.source_warehouse and self.target_warehouse:
			if self.source_warehouse == self.target_warehouse:
				frappe.throw(
					_('Source Warehouse and Target Warehouse cannot be the same.'),
					title=_('Invalid Warehouses'),
				)

		if self.is_new():
			return
		before = self.get_doc_before_save()
		if not before or before.docstatus != 0:
			return
		# Draft stays editable. Sending, and every later step, locks the
		# document. Submitting a Sent requisition (Seen / Rejected) is the
		# one change still allowed.
		if before.transfer_status in (None, '', 'Draft'):
			return
		if self.docstatus == 1 and before.docstatus == 0:
			return
		frappe.throw(
			_('Requisition {0} can no longer be edited.').format(self.name),
			title=_('Not Editable'),
		)
