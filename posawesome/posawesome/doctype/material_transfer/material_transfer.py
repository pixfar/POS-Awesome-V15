# Copyright (c) 2026, POS Awesome and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from posawesome.posawesome.utils.warehouse_doc_permissions import (
	ensure_warehouse_doc_read_access,
	get_expanded_permitted_warehouses,
	is_privileged_invoice_viewer,
	is_system_manager,
)

STATUS_IN_TRANSIT = 'In Transit'
STATUS_PARTIAL = 'Partially Received'
STATUS_FULL = 'Fully Received'
STATUS_REJECTED = 'Rejected'


def _ensure_transfer_read_access(doc):
	ensure_warehouse_doc_read_access(doc, 'from_warehouse', 'to_warehouse')


def _get_transit_warehouse(company):
	"""The warehouse stock actually sits in between dispatch and receipt --
	see the module-level note on why this exists at all: without a real
	transit leg, stock landed at the target warehouse's ledger the instant
	the Material Transfer was submitted, before anyone had actually
	confirmed the goods arrived."""
	transit_warehouse = frappe.db.get_value('Company', company, 'default_in_transit_warehouse')
	if not transit_warehouse:
		transit_warehouse = frappe.db.get_value(
			'Warehouse',
			{'company': company, 'warehouse_type': 'Transit', 'disabled': 0, 'is_group': 0},
			'name',
		)
	if not transit_warehouse:
		frappe.throw(
			_(
				'No in-transit warehouse is configured for company {0}. Set '
				'"Default In Transit Warehouse" on the Company, or create a '
				'Warehouse with type "Transit".'
			).format(company),
			title=_('Missing In-Transit Warehouse'),
		)
	return transit_warehouse


class MaterialTransfer(Document):
	def before_insert(self):
		self.requested_by = frappe.session.user

	def validate(self):
		if self.from_warehouse and self.to_warehouse:
			if self.from_warehouse == self.to_warehouse:
				frappe.throw(
					_('From Warehouse and To Warehouse cannot be the same.'),
					title=_('Invalid Warehouses'),
				)

	def on_submit(self):
		self._create_stock_entry()
		self._dispatch_stock_entry()

	def before_cancel(self):
		# Dispatch, receipt, and return Stock Entries all link via
		# custom_material_transfer -- any still-active one blocks cancel.
		active = frappe.get_all(
			'Stock Entry',
			filters={'custom_material_transfer': self.name, 'docstatus': ['<', 2]},
			pluck='name',
		)
		if active:
			frappe.throw(
				_('Cancel the linked Stock Entry {0} before cancelling this Material Transfer.').format(
					frappe.bold(', '.join(active))
				),
				title=_('Active Stock Entry Exists'),
			)

	def _create_stock_entry(self):
		"""Dispatch leg only -- moves stock from From Warehouse into the
		company's in-transit warehouse (add_to_transit=1), *not* into To
		Warehouse directly. Stock only actually reaches To Warehouse once
		confirm_receipt() below creates and submits the receipt leg -- see
		_get_transit_warehouse's note for why."""
		if not self.from_warehouse:
			frappe.throw(_('From Warehouse is required.'))
		if not self.to_warehouse:
			frappe.throw(_('To Warehouse is required.'))

		company = frappe.db.get_value('Warehouse', self.from_warehouse, 'company')
		if not company:
			frappe.throw(_('Could not determine Company from From Warehouse.'))

		transit_warehouse = _get_transit_warehouse(company)

		se = frappe.new_doc('Stock Entry')
		se.stock_entry_type = 'Material Transfer'
		se.purpose = 'Material Transfer'
		se.company = company
		# Post the dispatch on the Material Transfer's own date so a backdated
		# transfer isn't booked on today's date.
		if self.transaction_date:
			se.set_posting_time = 1
			se.posting_date = self.transaction_date
		se.add_to_transit = 1
		se.from_warehouse = self.from_warehouse
		se.to_warehouse = transit_warehouse
		se.custom_material_transfer = self.name

		for row in self.items:
			item_details = frappe.db.get_value(
				'Item',
				row.item_code,
				['item_name', 'stock_uom', 'description'],
				as_dict=True,
			)
			if not item_details:
				frappe.throw(_('Item {0} not found.').format(row.item_code))

			se.append('items', {
				'item_code': row.item_code,
				'item_name': row.item_name or item_details.item_name,
				'description': item_details.description,
				'qty': flt(row.qty),
				'transfer_qty': flt(row.qty),
				'uom': row.uom or item_details.stock_uom,
				'stock_uom': item_details.stock_uom,
				'conversion_factor': 1,
				's_warehouse': self.from_warehouse,
				't_warehouse': transit_warehouse,
				'custom_material_transfer_item': row.name,
			})

		se.set_stock_entry_type()
		se.insert(ignore_permissions=True)
		self.db_set('stock_entry', se.name, update_modified=False)

	def _dispatch_stock_entry(self):
		if not self.stock_entry:
			return

		se = frappe.get_doc('Stock Entry', self.stock_entry)
		if se.docstatus != 0:
			return

		se.flags.ignore_permissions = True
		se.flags.ignore_workflow = True
		se.submit()
		frappe.db.set_value(
			'Stock Entry',
			se.name,
			'workflow_state',
			STATUS_IN_TRANSIT,
			update_modified=False,
		)
		self.db_set('transfer_status', STATUS_IN_TRANSIT, update_modified=False)


def _item_outstanding(row):
	"""Qty still sitting in transit for this line (sent - received - returned)."""
	return max(flt(row.qty) - flt(row.received_qty) - flt(getattr(row, 'returned_qty', 0)), 0)


def _has_outstanding(doc):
	return any(_item_outstanding(row) > 0 for row in doc.items)


def _calculate_receipt_status(doc):
	"""Status from how much has left transit.

	Outstanding stays in Goods In Transit until Received (to destination) or
	Returned (back to source) by an admin. Fully Received means nothing is
	left outstanding -- including when the remainder was returned.
	"""
	if not doc.items:
		return STATUS_FULL

	any_progress = False
	any_outstanding = False
	for row in doc.items:
		if flt(row.received_qty) > 0 or flt(getattr(row, 'returned_qty', 0)) > 0:
			any_progress = True
		if _item_outstanding(row) > 0:
			any_outstanding = True

	if not any_progress:
		return STATUS_IN_TRANSIT
	return STATUS_PARTIAL if any_outstanding else STATUS_FULL


def _check_target_warehouse_permission(doc):
	if is_system_manager():
		return

	if frappe.session.user == doc.requested_by:
		frappe.throw(
			_('You cannot receive your own Material Transfer request.'),
			title=_('Not Allowed'),
		)

	# None means unrestricted (BSP Admin / BSP Viewer, same as System
	# Manager above) -- `or []` would collapse that into "no warehouse
	# allowed", the opposite of what it means.
	warehouses = get_expanded_permitted_warehouses()
	if warehouses is None or (doc.to_warehouse and doc.to_warehouse in warehouses):
		return

	frappe.throw(
		_('You need a User Permission on the Target Warehouse ({0}) to perform this action.').format(
			doc.to_warehouse or _('not set')
		),
		title=_('No Warehouse Permission'),
		exc=frappe.PermissionError,
	)


def _user_may_act_on_target(doc):
	if is_system_manager():
		return True
	if doc.requested_by == frappe.session.user:
		return False
	warehouses = get_expanded_permitted_warehouses()
	return warehouses is None or doc.to_warehouse in warehouses


def can_confirm_receipt(doc):
	"""Receive remaining outstanding qty while In Transit or Partially Received."""
	if doc.docstatus != 1:
		return False
	if doc.transfer_status not in (STATUS_IN_TRANSIT, STATUS_PARTIAL):
		return False
	if not _has_outstanding(doc):
		return False
	return _user_may_act_on_target(doc)


def can_reject_transfer(doc):
	"""Full reject only while still purely in transit (nothing received/returned)."""
	if doc.docstatus != 1 or doc.transfer_status != STATUS_IN_TRANSIT:
		return False
	return _user_may_act_on_target(doc)


def can_return_transfer(doc):
	"""Partial return of outstanding transit qty -- BSP Admin / System Manager only."""
	if doc.docstatus != 1:
		return False
	if doc.transfer_status not in (STATUS_IN_TRANSIT, STATUS_PARTIAL):
		return False
	if not _has_outstanding(doc):
		return False
	return is_privileged_invoice_viewer()


def _ensure_can_return():
	if not is_privileged_invoice_viewer():
		frappe.throw(
			_('Only a BSP Admin or System Manager can return Material Transfer quantity.'),
			exc=frappe.PermissionError,
		)


def _get_dispatch_se(doc):
	if not doc.stock_entry:
		frappe.throw(_('No Stock Entry linked to this Material Transfer.'))
	se = frappe.get_doc('Stock Entry', doc.stock_entry)
	if se.docstatus == 2:
		frappe.throw(_('Stock Entry has been cancelled.'), title=_('Cannot Continue'))
	if se.docstatus == 0:
		frappe.throw(_('Goods have not been dispatched yet.'), title=_('Not In Transit'))
	return se


def _outstanding_item_rows(doc, se):
	"""Dialog rows: qty = outstanding still in transit (keyed by dispatch SE item name)."""
	mt_item_by_name = {row.name: row for row in doc.items}
	items = []
	for se_item in se.items:
		mt_item_name = getattr(se_item, 'custom_material_transfer_item', None)
		mt_item = mt_item_by_name.get(mt_item_name) if mt_item_name else None
		if not mt_item:
			continue
		outstanding = _item_outstanding(mt_item)
		if outstanding <= 0:
			continue
		items.append(
			{
				'name': se_item.name,
				'item_code': se_item.item_code,
				'item_name': se_item.item_name,
				'qty': outstanding,
				'sent_qty': flt(se_item.qty),
				'received_qty': flt(mt_item.received_qty),
				'returned_qty': flt(getattr(mt_item, 'returned_qty', 0)),
				'uom': se_item.uom,
				'stock_uom': se_item.stock_uom,
				'conversion_factor': flt(se_item.conversion_factor) or 1,
			}
		)
	return items


@frappe.whitelist()
def get_stock_entry_items(transfer):
	"""Outstanding items for the Receive dialog (remaining in transit)."""
	doc = frappe.get_doc('Material Transfer', transfer)
	_ensure_transfer_read_access(doc)
	se = _get_dispatch_se(doc)
	items = _outstanding_item_rows(doc, se)
	if not items:
		frappe.throw(_('Nothing left to receive for this Material Transfer.'), title=_('Nothing to Receive'))
	return {'se_name': se.name, 'items': items}


@frappe.whitelist()
def get_returnable_items(transfer):
	"""Outstanding items for the Return dialog (admin-only)."""
	_ensure_can_return()
	doc = frappe.get_doc('Material Transfer', transfer)
	_ensure_transfer_read_access(doc)
	se = _get_dispatch_se(doc)
	items = _outstanding_item_rows(doc, se)
	if not items:
		frappe.throw(_('Nothing left to return for this Material Transfer.'), title=_('Nothing to Return'))
	return {'se_name': se.name, 'items': items}


@frappe.whitelist()
def confirm_receipt(transfer, received_quantities=None):
	doc = frappe.get_doc('Material Transfer', transfer)
	_ensure_transfer_read_access(doc)

	if doc.docstatus != 1:
		frappe.throw(_('Material Transfer must be submitted.'))
	if doc.transfer_status not in (STATUS_IN_TRANSIT, STATUS_PARTIAL):
		frappe.throw(
			_('Receipt can only be confirmed while goods are in transit or partially received — current status: {0}.').format(
				doc.transfer_status
			)
		)
	if not _has_outstanding(doc):
		frappe.throw(_('Nothing left to receive for this Material Transfer.'), title=_('Nothing to Receive'))

	_check_target_warehouse_permission(doc)
	se = _get_dispatch_se(doc)

	# Incremental receive: quantities in the payload are THIS batch only
	# (dialog already shows outstanding as max). Shortfall stays in transit
	# until a later Receive or an admin Return.
	if isinstance(received_quantities, str):
		received_quantities = json.loads(received_quantities)
	received_quantities = received_quantities or {}

	mt_item_by_name = {row.name: row for row in doc.items}
	any_positive = False
	receive_rows = []

	for se_item in se.items:
		mt_item_name = getattr(se_item, 'custom_material_transfer_item', None)
		mt_item = mt_item_by_name.get(mt_item_name) if mt_item_name else None
		if not mt_item:
			continue

		outstanding = _item_outstanding(mt_item)
		if outstanding <= 0:
			continue

		this_qty = flt(received_quantities.get(se_item.name, 0))
		if this_qty < 0:
			frappe.throw(_('Received quantity cannot be negative for item {0}.').format(se_item.item_code))
		if this_qty > outstanding:
			frappe.throw(
				_('Received qty ({0}) cannot exceed outstanding qty ({1}) for item {2}.').format(
					this_qty, outstanding, se_item.item_code
				)
			)
		if this_qty <= 0:
			continue

		any_positive = True
		new_received = flt(mt_item.received_qty) + this_qty
		receive_rows.append((se_item, mt_item_name, this_qty))
		frappe.db.set_value(
			'Material Transfer Item', mt_item_name, 'received_qty', new_received, update_modified=False
		)

	if not any_positive:
		frappe.throw(
			_('All received quantities are zero. Enter at least one positive quantity.'),
			title=_('Nothing to Receive'),
		)

	frappe.db.set_value(
		'Stock Entry',
		se.name,
		'workflow_state',
		'Requisition Received',
		update_modified=False,
	)

	transit_warehouse = se.to_warehouse
	se_in = frappe.new_doc('Stock Entry')
	se_in.stock_entry_type = 'Material Transfer'
	se_in.purpose = 'Material Transfer'
	se_in.company = se.company
	se_in.from_warehouse = transit_warehouse
	se_in.to_warehouse = doc.to_warehouse
	se_in.outgoing_stock_entry = se.name
	se_in.custom_material_transfer = doc.name

	for se_item, mt_item_name, received_qty in receive_rows:
		se_in.append('items', {
			'item_code': se_item.item_code,
			'item_name': se_item.item_name,
			'description': se_item.description,
			's_warehouse': transit_warehouse,
			't_warehouse': doc.to_warehouse,
			'qty': received_qty,
			'transfer_qty': received_qty,
			'uom': se_item.uom,
			'stock_uom': se_item.stock_uom,
			'conversion_factor': flt(se_item.conversion_factor) or 1,
			'against_stock_entry': se.name,
			'ste_detail': se_item.name,
			'custom_material_transfer_item': mt_item_name,
		})

	se_in.set_stock_entry_type()
	se_in.flags.ignore_permissions = True
	se_in.insert(ignore_permissions=True)
	se_in.submit()
	doc.db_set('stock_entry_received', se_in.name, update_modified=False)

	doc.reload()
	status = _calculate_receipt_status(doc)
	doc.db_set('transfer_status', status, update_modified=True)
	return status


@frappe.whitelist()
def return_transfer(transfer, returned_quantities=None):
	"""Return some/all outstanding transit qty back to From Warehouse.

	BSP Admin / System Manager only. Partial quantities are allowed; anything
	not returned stays in transit for a later Receive or Return.
	"""
	_ensure_can_return()
	doc = frappe.get_doc('Material Transfer', transfer)
	_ensure_transfer_read_access(doc)

	if doc.docstatus != 1:
		frappe.throw(_('Material Transfer must be submitted.'))
	if doc.transfer_status not in (STATUS_IN_TRANSIT, STATUS_PARTIAL):
		frappe.throw(
			_('Quantity can only be returned while goods are in transit or partially received — current status: {0}.').format(
				doc.transfer_status
			)
		)
	if not _has_outstanding(doc):
		frappe.throw(_('Nothing left to return for this Material Transfer.'), title=_('Nothing to Return'))

	se = _get_dispatch_se(doc)
	if not se.add_to_transit:
		frappe.throw(
			_('This Material Transfer was not dispatched through an in-transit warehouse, so quantity cannot be returned.'),
			title=_('Cannot Return'),
		)

	if isinstance(returned_quantities, str):
		returned_quantities = json.loads(returned_quantities)
	returned_quantities = returned_quantities or {}

	mt_item_by_name = {row.name: row for row in doc.items}
	any_positive = False
	return_rows = []

	for se_item in se.items:
		mt_item_name = getattr(se_item, 'custom_material_transfer_item', None)
		mt_item = mt_item_by_name.get(mt_item_name) if mt_item_name else None
		if not mt_item:
			continue

		outstanding = _item_outstanding(mt_item)
		if outstanding <= 0:
			continue

		this_qty = flt(returned_quantities.get(se_item.name, 0))
		if this_qty < 0:
			frappe.throw(_('Returned quantity cannot be negative for item {0}.').format(se_item.item_code))
		if this_qty > outstanding:
			frappe.throw(
				_('Returned qty ({0}) cannot exceed outstanding qty ({1}) for item {2}.').format(
					this_qty, outstanding, se_item.item_code
				)
			)
		if this_qty <= 0:
			continue

		any_positive = True
		new_returned = flt(getattr(mt_item, 'returned_qty', 0)) + this_qty
		return_rows.append((se_item, mt_item_name, this_qty))
		frappe.db.set_value(
			'Material Transfer Item', mt_item_name, 'returned_qty', new_returned, update_modified=False
		)

	if not any_positive:
		frappe.throw(
			_('All returned quantities are zero. Enter at least one positive quantity.'),
			title=_('Nothing to Return'),
		)

	transit_warehouse = se.to_warehouse
	se_return = frappe.new_doc('Stock Entry')
	se_return.stock_entry_type = 'Material Transfer'
	se_return.purpose = 'Material Transfer'
	se_return.company = se.company
	se_return.from_warehouse = transit_warehouse
	se_return.to_warehouse = doc.from_warehouse
	se_return.custom_material_transfer = doc.name

	for se_item, mt_item_name, return_qty in return_rows:
		se_return.append('items', {
			'item_code': se_item.item_code,
			'item_name': se_item.item_name,
			'description': se_item.description,
			's_warehouse': transit_warehouse,
			't_warehouse': doc.from_warehouse,
			'qty': return_qty,
			'transfer_qty': return_qty,
			'uom': se_item.uom,
			'stock_uom': se_item.stock_uom,
			'conversion_factor': flt(se_item.conversion_factor) or 1,
			'custom_material_transfer_item': mt_item_name,
		})

	se_return.set_stock_entry_type()
	se_return.flags.ignore_permissions = True
	se_return.insert(ignore_permissions=True)
	se_return.submit()

	doc.reload()
	status = _calculate_receipt_status(doc)
	doc.db_set('transfer_status', status, update_modified=True)
	return status


@frappe.whitelist()
def reject_transfer(transfer):
	"""Reject an in-transit Material Transfer: cancel the linked Stock Entry to
	reverse the stock movement (goods never arrived), cancel the Material Transfer
	itself, and mark it Rejected. Only available to whoever could have confirmed
	receipt, and only while still purely in transit (nothing received yet)."""
	doc = frappe.get_doc('Material Transfer', transfer)
	_ensure_transfer_read_access(doc)

	if doc.docstatus != 1:
		frappe.throw(_('Material Transfer must be submitted.'))
	if doc.transfer_status != STATUS_IN_TRANSIT:
		frappe.throw(
			_('A transfer can only be rejected while goods are in transit — current status: {0}.').format(
				doc.transfer_status
			)
		)

	_check_target_warehouse_permission(doc)

	if doc.stock_entry:
		se = frappe.get_doc('Stock Entry', doc.stock_entry)
		if se.docstatus == 1:
			se.flags.ignore_permissions = True
			se.flags.ignore_workflow = True
			# The Material Transfer (still submitted at this point) links back to this
			# Stock Entry, which would otherwise trip Frappe's linked-document guard.
			se.flags.ignore_links = True
			se.cancel()

	doc.flags.ignore_permissions = True
	doc.cancel()
	# Keep modified_by as the user who rejected (cancel already stamped
	# them; update_modified=True preserves that on the status write).
	doc.db_set('transfer_status', STATUS_REJECTED, update_modified=True)

	return STATUS_REJECTED
