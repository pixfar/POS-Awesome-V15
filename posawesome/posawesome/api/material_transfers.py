# Copyright (c) 2026, POS Awesome and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _
from frappe.utils import flt, getdate, today

from posawesome.posawesome.doctype.material_transfer.material_transfer import (
	can_confirm_receipt,
	can_reject_transfer,
	can_return_transfer,
)
from posawesome.posawesome.utils.warehouse_doc_permissions import (
	ensure_warehouse_doc_read_access,
	get_warehouse_doc_list_rows,
	get_warehouse_doc_status_counts,
	is_system_manager,
	is_privileged_invoice_viewer,
	ensure_can_create,
)
from posawesome.posawesome.utils.weight import get_total_weight_by_parent
from posawesome.posawesome.api.utils import (
	attach_actual_qty,
	attach_user_full_names,
	attach_warehouse_stock,
)


def _parse_json(value):
	if isinstance(value, str):
		return json.loads(value)
	return value


def _enrich_list_row(row):
	doc = frappe.get_doc('Material Transfer', row.name)
	row['can_confirm'] = can_confirm_receipt(doc)
	row['can_reject'] = can_reject_transfer(doc)
	row['can_return'] = can_return_transfer(doc)
	return row


@frappe.whitelist()
def create_material_transfer(data):
	ensure_can_create(_('create a Material Transfer'))
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
	# Back/forward-dating is BSP Admin / System Manager only -- same gate as
	# canEditPostingDate on the client, re-checked here since that's UX-only.
	transaction_date = data.get('transaction_date') or today()
	if getdate(transaction_date) != getdate(today()) and not is_privileged_invoice_viewer():
		transaction_date = today()
	doc.transaction_date = transaction_date
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

	# Pre-check every item's stock up front so the cashier sees ALL shortages at
	# once, instead of ERPNext's Stock Entry validation throwing on the first
	# short item one by one. The linked Stock Entry maps qty 1:1 to stock qty
	# (conversion_factor = 1, see MaterialTransfer.on_submit), so the required
	# stock qty per item is simply its qty in the From Warehouse. This only
	# changes the error message; the Stock Entry still runs its own check on
	# submit, so nothing can slip through.
	required_by_item = {}
	name_by_item = {}
	for mt_item in doc.items:
		required_by_item[mt_item.item_code] = required_by_item.get(mt_item.item_code, 0) + flt(mt_item.qty)
		name_by_item[mt_item.item_code] = mt_item.item_name or mt_item.item_code

	on_hand = get_stock_qty(list(required_by_item.keys()), doc.from_warehouse)
	shortages = [
		(code, name_by_item[code], need, flt(on_hand.get(code, 0)))
		for code, need in required_by_item.items()
		if flt(on_hand.get(code, 0)) < need
	]
	if shortages:
		rows_html = ''.join(
			_('<li><b>{0}</b> units of <b>{1}: {2}</b> needed, but only <b>{3}</b> available.</li>').format(
				'%g' % flt(need),
				frappe.utils.escape_html(code),
				frappe.utils.escape_html(name),
				'%g' % flt(have),
			)
			for code, name, need, have in shortages
		)
		frappe.throw(
			_('The following items do not have enough stock in {0} to complete this transfer:').format(
				frappe.bold(doc.from_warehouse)
			)
			+ f'<ul style="margin-top:8px">{rows_html}</ul>',
			title=_('Insufficient Stock'),
		)

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
	remarks=None,
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
		remarks=remarks,
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
			'owner',
			'modified',
			'modified_by',
			'notes',
			'creation',
		],
		page_start=page_start,
		page_length=page_length,
		extra_filters={'transfer_status': status} if status else None,
		# Newest posting date first; within a date, latest first by the time
		# shown in the list's Time column (time of day of creation -- Material
		# Transfer has no separate posting time). A back-dated transfer sorts
		# under its own date. creation/name keep paging stable on ties.
		order_by='main.transaction_date DESC, TIME(main.creation) DESC, main.creation DESC, main.name DESC',
		**shared_filter_args,
	)

	status_counts = get_warehouse_doc_status_counts(
		'Material Transfer',
		'from_warehouse',
		'to_warehouse',
		'transfer_status',
		**shared_filter_args,
	)

	weight_by_parent = get_total_weight_by_parent('Material Transfer Item', [row['name'] for row in rows])
	for row in rows:
		row['total_weight'] = weight_by_parent.get(row['name'], 0.0)

	transfers = [_enrich_list_row(row) for row in rows]
	attach_user_full_names(
		transfers,
		{'owner': 'owner_name', 'modified_by': 'modified_by_name'},
	)

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

	# custom_default_weigt_of_measure (weight per unit) lives on the Item
	# master, not the Material Transfer Item child row.
	item_codes = {row.item_code for row in doc.items if row.item_code}
	weight_by_item = (
		frappe._dict(
			frappe.get_all(
				'Item',
				filters={'name': ['in', list(item_codes)]},
				fields=['name', 'custom_default_weigt_of_measure'],
				as_list=True,
			)
		)
		if item_codes
		else {}
	)

	items = []
	total_weight = 0.0
	for row in doc.items:
		weight = flt(weight_by_item.get(row.item_code)) * flt(row.qty)
		total_weight += weight
		items.append(
			{
				'name': row.name,
				'item_code': row.item_code,
				'item_name': row.item_name,
				'item_group': row.item_group,
				'qty': flt(row.qty),
				'received_qty': flt(row.received_qty),
				'returned_qty': flt(getattr(row, 'returned_qty', 0)),
				'uom': row.uom,
				'schedule_date': row.schedule_date,
				'weight': flt(weight),
			}
		)

	stock_visibility = attach_warehouse_stock(items, doc.from_warehouse, doc.to_warehouse)

	return {
		**stock_visibility,
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
		'last_modified_by': frappe.db.get_value('User', doc.modified_by, 'full_name') or doc.modified_by,
		'modified': doc.modified,
		'creation': doc.creation,
		'amended_from': doc.get('amended_from'),
		'total_qty': flt(sum(flt(row.qty) for row in doc.items)),
		'total_received_qty': flt(sum(flt(row.received_qty) for row in doc.items)),
		'total_returned_qty': flt(sum(flt(getattr(row, 'returned_qty', 0)) for row in doc.items)),
		'total_weight': flt(total_weight),
		'item_count': len(doc.items),
		'items': items,
		'can_confirm': can_confirm_receipt(doc),
		'can_reject': can_reject_transfer(doc),
		'can_return': can_return_transfer(doc),
	}


@frappe.whitelist()
def get_transfer_warehouses():
	"""Every active, non-group warehouse, in BSP's official warehouse order,
	for the Material Transfer "To Warehouse" picker and the list's Warehouse
	filter.

	frappe.client.get_list applies Warehouse User Permissions, so a user
	restricted to their own showroom got back only that one warehouse -- and
	with it already the From Warehouse, To Warehouse ended up empty. Sending
	stock *to* any warehouse is intended (Material Transfer's from/to
	warehouse fields carry ignore_user_permissions), so this lists them all."""
	from bsp_engineering.utils.warehouse_sort import sort_warehouses

	rows = frappe.get_all(
		'Warehouse',
		filters={'is_group': 0, 'disabled': 0},
		fields=['name', 'warehouse_name'],
		limit_page_length=0,
	)
	return sort_warehouses(rows, key='name')


@frappe.whitelist()
def search_items(search_text=None, limit=20, warehouse=None, page_start=0):
	limit = max(1, min(int(limit or 20), 500))
	page_start = max(0, int(page_start or 0))
	filters = {'disabled': 0, 'has_variants': 0}
	or_filters = None
	if search_text and len(search_text.strip()) >= 2:
		eng_text = search_text.strip()
		ben_text = eng_text
		for e, b in zip(['0', '1', '2', '3', '4', '5', '6', '7', '8', '9'], ['০', '১', '২', '৩', '৪', '৫', '৬', '৭', '৮', '৯']):
			ben_text = ben_text.replace(e, b)
			
		like_eng = f'%{eng_text}%'
		like_ben = f'%{ben_text}%'
		
		or_filters = [
			['Item', 'name', 'like', like_eng],
			['Item', 'item_name', 'like', like_eng],
		]
		if like_eng != like_ben:
			or_filters.extend([
				['Item', 'name', 'like', like_ben],
				['Item', 'item_name', 'like', like_ben],
			])

	items = frappe.get_all(
		'Item',
		filters=filters,
		or_filters=or_filters,
		fields=[
			'name as item_code',
			'item_name',
			'item_group',
			'stock_uom',
			'standard_rate',
			'custom_default_weigt_of_measure',
		],
		# Same order as the item selector's Browse cards (item code), so the
		# dropdown and the cards list items in the same sequence.
		order_by='name asc',
		limit_start=page_start,
		limit_page_length=limit,
	)
	attach_actual_qty(items, warehouse)
	return items


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
