# Copyright (c) 2026, POS Awesome and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, today

from posawesome.posawesome.doctype.requisition.transfer_status import (
	STATUS_NOT,
	calculate_transfer_status,
	get_transferred_by_item,
	update_requisition_transfer_status,
)


class Requisition(Document):
	def before_insert(self):
		self.requested_by = frappe.session.user

	def on_submit(self):
		self.db_set('transfer_status', STATUS_NOT, update_modified=False)

	def validate(self):
		if self.source_warehouse and self.target_warehouse:
			if self.source_warehouse == self.target_warehouse:
				frappe.throw(
					_('Source Warehouse and Target Warehouse cannot be the same.'),
					title=_('Invalid Warehouses'),
				)
		if self.docstatus == 1:
			self.transfer_status = calculate_transfer_status(self)

	def before_cancel(self):
		active_ses = frappe.get_all(
			'Stock Entry',
			filters={'custom_requisition': self.name, 'docstatus': ['!=', 2]},
			fields=['name', 'docstatus'],
		)
		if not active_ses:
			return
		names_html = ', '.join(frappe.bold(se.name) for se in active_ses)
		frappe.throw(
			_('The following Stock Entries must be cancelled or deleted before cancelling'
			  ' this Requisition: {0}').format(names_html),
			title=_('Active Stock Entries Exist'),
		)
