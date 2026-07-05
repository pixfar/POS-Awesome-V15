# Copyright (c) 2026, POS Awesome and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class Requisition(Document):
	def before_insert(self):
		self.requested_by = frappe.session.user

	def on_submit(self):
		self.db_set('transfer_status', 'Sent', update_modified=False)

	def validate(self):
		if self.source_warehouse and self.target_warehouse:
			if self.source_warehouse == self.target_warehouse:
				frappe.throw(
					_('Source Warehouse and Target Warehouse cannot be the same.'),
					title=_('Invalid Warehouses'),
				)
