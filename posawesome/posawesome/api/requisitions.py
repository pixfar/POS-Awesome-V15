# Copyright (c) 2026, POS Awesome and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _
from frappe.utils import flt, today

from posawesome.posawesome.doctype.requisition.transfer_status import (
	get_transferred_by_item,
	update_requisition_transfer_status,
)
from posawesome.posawesome.utils.warehouse_doc_permissions import (
	ensure_warehouse_doc_read_access,
	get_expanded_permitted_warehouses,
	get_warehouse_doc_list_rows,
	is_system_manager,
)


def _parse_json(value):
	if isinstance(value, str):
		return json.loads(value)
	return value


def _get_in_transit_se_name(requisition):
	return frappe.db.get_value('Stock Entry', {
		'custom_requisition': requisition,
		'workflow_state': 'In Transit',
		'docstatus': ['!=', 2],
	}, 'name')


@frappe.whitelist()
def create_requisition(data):
	"""Create and submit a requisition from POS."""
	data = _parse_json(data)
	if not data:
		frappe.throw(_('Requisition data is required.'))

	items = data.get('items') or []
	if not items:
		frappe.throw(_('Add at least one item.'), title=_('Items Required'))

	target_warehouse = data.get('target_warehouse')
	if not target_warehouse:
		frappe.throw(_('Target Warehouse is required.'), title=_('Warehouse Required'))

	source_warehouse = data.get('source_warehouse')
	if not source_warehouse:
		frappe.throw(_('Source Warehouse is required.'), title=_('Warehouse Required'))
	if source_warehouse == target_warehouse:
		frappe.throw(
			_('Source Warehouse and Target Warehouse cannot be the same.'),
			title=_('Invalid Warehouses'),
		)

	doc = frappe.new_doc('Requisition')
	doc.transaction_date = data.get('transaction_date') or today()
	doc.source_warehouse = source_warehouse
	doc.target_warehouse = target_warehouse
	doc.notes = data.get('notes')

	for row in items:
		if flt(row.get('required_qty') or row.get('qty')) <= 0:
			continue
		doc.append('items', {
			'item_group': row.get('item_group'),
			'item_code': row.get('item_code'),
			'item_name': row.get('item_name'),
			'required_qty': flt(row.get('required_qty') or row.get('qty')),
			'schedule_date': row.get('schedule_date') or doc.transaction_date,
			'uom': row.get('uom'),
		})

	if not doc.items:
		frappe.throw(_('Add at least one item with quantity.'), title=_('Items Required'))

	doc.insert()
	if doc.docstatus == 0:
		doc.submit()

	return {
		'name': doc.name,
		'transfer_status': doc.transfer_status,
	}


def _can_confirm_receipt(doc):
	return (
		doc.transfer_status == 'In Transit'
		and frappe.session.user == doc.requested_by
	)


def _can_create_stock_entry(doc):
	if doc.requested_by == frappe.session.user:
		return False
	if is_system_manager():
		return True
	warehouses = get_expanded_permitted_warehouses() or []
	return doc.source_warehouse in warehouses


def _enrich_list_row(row):
	doc = frappe.get_doc('Requisition', row.name)
	row['can_transfer'] = _can_create_stock_entry(doc)
	row['can_confirm'] = _can_confirm_receipt(doc)
	return row


@frappe.whitelist()
def get_requisitions_list(page_start=0, page_length=20, mine_only=0):
	"""Paginated requisition list for POS tracking."""
	page_start = max(0, int(page_start or 0))
	page_length = max(1, min(int(page_length or 20), 100))

	rows, total = get_warehouse_doc_list_rows(
		'Requisition',
		'source_warehouse',
		'target_warehouse',
		fields=[
			'name',
			'transaction_date',
			'requested_by',
			'source_warehouse',
			'target_warehouse',
			'transfer_status',
			'modified',
		],
		page_start=page_start,
		page_length=page_length,
		mine_only=mine_only,
	)

	requisitions = [_enrich_list_row(row) for row in rows]

	return {
		'requisitions': requisitions,
		'total': total,
		'has_more': (page_start + page_length) < total,
	}


@frappe.whitelist()
def get_requisition_detail(requisition):
	doc = frappe.get_doc('Requisition', requisition)
	ensure_warehouse_doc_read_access(doc, 'source_warehouse', 'target_warehouse')
	return {
		'name': doc.name,
		'transaction_date': doc.transaction_date,
		'requested_by': doc.requested_by,
		'source_warehouse': doc.source_warehouse,
		'target_warehouse': doc.target_warehouse,
		'transfer_status': doc.transfer_status,
		'notes': doc.notes,
		'items': [
			{
				'name': row.name,
				'item_code': row.item_code,
				'item_name': row.item_name,
				'item_group': row.item_group,
				'required_qty': flt(row.required_qty),
				'uom': row.uom,
				'schedule_date': row.schedule_date,
			}
			for row in doc.items
		],
		'can_transfer': _can_create_stock_entry(doc),
		'can_confirm': _can_confirm_receipt(doc),
	}


@frappe.whitelist()
def can_create_stock_entry(requisition):
	doc = frappe.get_doc('Requisition', requisition)
	ensure_warehouse_doc_read_access(doc, 'source_warehouse', 'target_warehouse')

	if not _can_create_stock_entry(doc):
		reason = 'requester' if doc.requested_by == frappe.session.user else 'no_permission'
		return {'can_create': False, 'reason': reason}

	return {'can_create': True}


@frappe.whitelist()
def make_stock_entry(requisition):
	doc = frappe.get_doc('Requisition', requisition)
	ensure_warehouse_doc_read_access(doc, 'source_warehouse', 'target_warehouse')

	if doc.requested_by == frappe.session.user:
		frappe.throw(
			_('You cannot create a Stock Entry for your own Requisition.'),
			title=_('Not Allowed'),
		)

	if not is_system_manager():
		warehouses = get_expanded_permitted_warehouses() or []
		if not doc.source_warehouse or doc.source_warehouse not in warehouses:
			frappe.throw(
				_('You need permission on the Source Warehouse ({0}) to transfer stock.').format(
					doc.source_warehouse or _('not set')
				),
				title=_('No Warehouse Permission'),
			)

	if doc.docstatus != 1:
		frappe.throw(
			_('Submit the Requisition before creating a Stock Entry.'),
			title=_('Not Submitted'),
		)
	if not doc.source_warehouse:
		frappe.throw(_('Source Warehouse is required to transfer stock.'))
	if not doc.target_warehouse:
		frappe.throw(_('Target Warehouse is required to transfer stock.'))
	if doc.source_warehouse == doc.target_warehouse:
		frappe.throw(
			_('Source and Target Warehouse cannot be the same for a transfer.')
		)

	company = frappe.db.get_value('Warehouse', doc.source_warehouse, 'company')
	if not company:
		frappe.throw(_('Could not determine Company from Source Warehouse.'))

	transferred_by_item = get_transferred_by_item(doc.name)
	stock_entry = frappe.new_doc('Stock Entry')
	stock_entry.stock_entry_type = 'Material Transfer'
	stock_entry.purpose = 'Material Transfer'
	stock_entry.company = company
	stock_entry.from_warehouse = doc.source_warehouse
	stock_entry.to_warehouse = doc.target_warehouse
	stock_entry.custom_requisition = doc.name

	for row in doc.items:
		remaining = flt(row.required_qty) - flt(
			transferred_by_item.get(row.name)
		)
		if remaining <= 0:
			continue

		item_details = frappe.db.get_value(
			'Item',
			row.item_code,
			['item_name', 'stock_uom', 'description'],
			as_dict=True,
		)
		conversion_factor = 1
		stock_entry.append(
			'items',
			{
				'item_code': row.item_code,
				'item_name': row.item_name or item_details.item_name,
				'description': item_details.description,
				'qty': remaining,
				'transfer_qty': remaining * conversion_factor,
				'uom': row.uom or item_details.stock_uom,
				'stock_uom': item_details.stock_uom,
				'conversion_factor': conversion_factor,
				's_warehouse': doc.source_warehouse,
				't_warehouse': doc.target_warehouse,
				'custom_requisition_item': row.name,
			},
		)

	if not stock_entry.items:
		frappe.throw(
			_('All items on this Requisition are already fully transferred.'),
			title=_('Nothing to Transfer'),
		)

	stock_entry.set_stock_entry_type()
	return stock_entry.as_dict()


@frappe.whitelist()
def get_in_transit_se_items(requisition):
	doc = frappe.get_doc('Requisition', requisition)
	ensure_warehouse_doc_read_access(doc, 'source_warehouse', 'target_warehouse')

	se_name = _get_in_transit_se_name(requisition)
	if not se_name:
		frappe.throw(_('No In Transit Stock Entry found for this Requisition.'), title=_('Nothing to Confirm'))

	se = frappe.get_doc('Stock Entry', se_name)
	items = [
		{
			'name': item.name,
			'item_code': item.item_code,
			'item_name': item.item_name,
			'qty': item.qty,
			'uom': item.uom,
			'stock_uom': item.stock_uom,
			'conversion_factor': flt(item.conversion_factor) or 1,
		}
		for item in se.items
	]
	return {'se_name': se_name, 'items': items}


@frappe.whitelist()
def confirm_receipt_from_requisition(requisition, received_quantities=None):
	doc = frappe.get_doc('Requisition', requisition)
	ensure_warehouse_doc_read_access(doc, 'source_warehouse', 'target_warehouse')

	if frappe.session.user != doc.requested_by:
		frappe.throw(
			_('Only {0} (the person who submitted this Requisition) can confirm receipt.').format(
				frappe.bold(doc.requested_by)
			),
			title=_('Not Allowed'),
			exc=frappe.PermissionError,
		)

	se_name = _get_in_transit_se_name(requisition)
	if not se_name:
		frappe.throw(_('No In Transit Stock Entry found for this Requisition.'), title=_('Nothing to Confirm'))

	se = frappe.get_doc('Stock Entry', se_name)

	if received_quantities:
		received_quantities = _parse_json(received_quantities)

		for item in se.items:
			if item.name not in received_quantities:
				continue
			new_qty = flt(received_quantities[item.name])
			if new_qty < 0:
				frappe.throw(_('Received quantity cannot be negative for item {0}.').format(item.item_code))
			if new_qty > flt(item.qty):
				frappe.throw(
					_('Received quantity ({0}) cannot exceed sent quantity ({1}) for item {2}.').format(
						new_qty, item.qty, item.item_code
					)
				)
			item.qty = new_qty
			item.transfer_qty = new_qty * (flt(item.conversion_factor) or 1)

		se.items = [item for item in se.items if flt(item.qty) > 0]

		if not se.items:
			frappe.throw(
				_('All received quantities are zero. Enter at least one positive quantity.'),
				title=_('Nothing to Confirm'),
			)

		se.flags.ignore_permissions = True
		se.save()

	se.reload()
	se.flags.ignore_permissions = True
	se.flags.ignore_workflow = True
	se.submit()
	frappe.db.set_value(
		'Stock Entry', se.name, 'workflow_state', 'Requisition Received', update_modified=False
	)

	update_requisition_transfer_status(requisition)
	return frappe.db.get_value('Requisition', requisition, 'transfer_status')


@frappe.whitelist()
def search_items(search_text=None, limit=20):
	"""Item search for POS requisition autocomplete."""
	limit = max(1, min(int(limit or 20), 50))
	filters = {'disabled': 0, 'has_variants': 0}
	or_filters = None
	if search_text and len(search_text.strip()) >= 2:
		like = f'%{search_text.strip()}%'
		or_filters = {
			'name': ['like', like],
			'item_name': ['like', like],
		}

	return frappe.get_all(
		'Item',
		filters=filters,
		or_filters=or_filters,
		fields=[
			'name as item_code',
			'item_name',
			'item_group',
			'stock_uom',
			'standard_rate',
		],
		order_by='item_name asc',
		limit_page_length=limit,
	)
