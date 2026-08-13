# Copyright (c) 2026, POS Awesome and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _
from frappe.utils import flt, today

from posawesome.posawesome.doctype.material_transfer.material_transfer import (
	can_confirm_receipt,
)
from posawesome.posawesome.utils.warehouse_doc_permissions import (
	ensure_warehouse_doc_read_access,
	get_warehouse_doc_list_rows,
	get_warehouse_doc_status_counts,
	is_system_manager,
)


def _parse_json(value):
	if isinstance(value, str):
		return json.loads(value)
	return value


def _enrich_list_row(row):
	doc = frappe.get_doc('Material Transfer', row.name)
	row['can_confirm'] = can_confirm_receipt(doc)
	return row


@frappe.whitelist()
def create_material_transfer(data):
	data = _parse_json(data)
	if not data:
		frappe.throw(_('Material Transfer data is required.'))

	items = data.get('items') or []
	if not items:
		frappe.throw(_('Add at least one item.'), title=_('Items Required'))

	from_warehouse = data.get('from_warehouse')
	to_warehouse = data.get('to_warehouse')
	if not from_warehouse:
		frappe.throw(_('From Warehouse is required.'), title=_('Warehouse Required'))
	if not to_warehouse:
		frappe.throw(_('To Warehouse is required.'), title=_('Warehouse Required'))
	if from_warehouse == to_warehouse:
		frappe.throw(
			_('From Warehouse and To Warehouse cannot be the same.'),
			title=_('Invalid Warehouses'),
		)

	doc = frappe.new_doc('Material Transfer')
	doc.transaction_date = data.get('transaction_date') or today()
	doc.from_warehouse = from_warehouse
	doc.to_warehouse = to_warehouse
	doc.custom_do_number = (data.get('custom_do_number') or '').strip() or None
	doc.notes = data.get('notes')

	for row in items:
		if flt(row.get('qty')) <= 0:
			continue
		doc.append('items', {
			'item_group': row.get('item_group'),
			'item_code': row.get('item_code'),
			'item_name': row.get('item_name'),
			'qty': flt(row.get('qty')),
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


@frappe.whitelist()
def get_material_transfers_list(
	page_start=0,
	page_length=20,
	mine_only=0,
	status=None,
	from_date=None,
	to_date=None,
	item_code=None,
	item_group=None,
	warehouse=None,
	do_number=None,
	search=None,
):
	page_start = max(0, int(page_start or 0))
	page_length = max(1, min(int(page_length or 20), 100))

	shared_filter_args = dict(
		mine_only=mine_only,
		date_field='transaction_date',
		from_date=from_date,
		to_date=to_date,
		item_code=item_code,
		item_group=item_group,
		warehouse=warehouse,
		do_number=do_number,
		search=search,
		search_fields=['name', 'from_warehouse', 'to_warehouse', 'requested_by'],
		# Rejecting a transfer cancels it (docstatus=2); it should still show up in
		# the list with a Rejected status rather than disappearing. Drafts
		# (docstatus=0) stay visible too, so they remain deletable.
		include_cancelled=True,
		include_draft=True,
	)

	rows, total = get_warehouse_doc_list_rows(
		'Material Transfer',
		'from_warehouse',
		'to_warehouse',
		fields=[
			'name',
			'transaction_date',
			'requested_by',
			'from_warehouse',
			'to_warehouse',
			'transfer_status',
			'custom_do_number',
			'docstatus',
			'modified',
		],
		page_start=page_start,
		page_length=page_length,
		extra_filters={'transfer_status': status} if status else None,
		**shared_filter_args,
	)

	status_counts = get_warehouse_doc_status_counts(
		'Material Transfer',
		'from_warehouse',
		'to_warehouse',
		'transfer_status',
		**shared_filter_args,
	)

	transfers = [_enrich_list_row(row) for row in rows]

	return {
		'transfers': transfers,
		'total': total,
		'has_more': (page_start + page_length) < total,
		'status_counts': status_counts,
	}


@frappe.whitelist()
def get_material_transfer_detail(transfer):
	doc = frappe.get_doc('Material Transfer', transfer)
	ensure_warehouse_doc_read_access(doc, 'from_warehouse', 'to_warehouse')
	owner_name = frappe.db.get_value('User', doc.owner, 'full_name') or doc.owner
	return {
		'name': doc.name,
		'transaction_date': doc.transaction_date,
		'requested_by': doc.requested_by,
		'from_warehouse': doc.from_warehouse,
		'to_warehouse': doc.to_warehouse,
		'transfer_status': doc.transfer_status,
		'custom_do_number': doc.get('custom_do_number'),
		'notes': doc.notes,
		'stock_entry': doc.get('stock_entry'),
		'created_by': owner_name,
		'creation': doc.creation,
		'amended_from': doc.get('amended_from'),
		'total_qty': flt(sum(flt(row.qty) for row in doc.items)),
		'total_received_qty': flt(sum(flt(row.received_qty) for row in doc.items)),
		'item_count': len(doc.items),
		'items': [
			{
				'name': row.name,
				'item_code': row.item_code,
				'item_name': row.item_name,
				'item_group': row.item_group,
				'qty': flt(row.qty),
				'received_qty': flt(row.received_qty),
				'uom': row.uom,
				'schedule_date': row.schedule_date,
			}
			for row in doc.items
		],
		'can_confirm': can_confirm_receipt(doc),
	}


@frappe.whitelist()
def search_items(search_text=None, limit=20):
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


@frappe.whitelist()
def get_stock_qty(item_codes, warehouse):
	"""Current on-hand qty (Bin.actual_qty) for a batch of items in a single
	warehouse -- used by the "Transfer Items" table's Stock Qty column so the
	cashier can see, right next to the qty being transferred, how much is
	actually available in the From Warehouse. Items with no Bin row for that
	warehouse (never stocked there) are simply left out, not zeroed --
	callers should treat a missing key the same as 0.
	"""
	if isinstance(item_codes, str):
		item_codes = frappe.parse_json(item_codes)
	item_codes = [code for code in (item_codes or []) if code]
	if not item_codes or not warehouse:
		return {}

	rows = frappe.get_all(
		'Bin',
		filters={'item_code': ['in', item_codes], 'warehouse': warehouse},
		fields=['item_code', 'actual_qty'],
	)
	return {row.item_code: flt(row.actual_qty) for row in rows}


@frappe.whitelist()
def delete_cancelled_material_transfer(transfer):
	"""Permanently delete a Draft or Cancelled Material Transfer. A submitted
	(In Transit / Received) transfer must be rejected first.

	reject_transfer always creates and then cancels a linked Stock Entry
	(custom_material_transfer points back at this doc), so every Cancelled
	transfer is guaranteed to still be link-checked against that now-cancelled
	Stock Entry. force=True skips that check the same way invoices.py's
	delete_invoice already does for draft invoices -- the Stock Entry itself
	is untouched and remains as the cancelled audit trail."""
	if not is_system_manager():
		frappe.throw(
			_('Only a System Manager can delete Material Transfers.'),
			exc=frappe.PermissionError,
		)

	if frappe.db.get_value('Material Transfer', transfer, 'docstatus') not in (0, 2):
		frappe.throw(_('Only a draft or cancelled document can be deleted.'))

	frappe.delete_doc('Material Transfer', transfer, ignore_permissions=True, force=True)
	return {'name': transfer}
