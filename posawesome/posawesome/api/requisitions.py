# Copyright (c) 2026, POS Awesome and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _
from frappe.utils import flt, today

from posawesome.posawesome.utils.warehouse_doc_permissions import (
	ensure_warehouse_doc_read_access,
	get_warehouse_doc_list_rows,
	get_warehouse_doc_status_counts,
	is_system_manager,
	ensure_can_create,
)
from posawesome.posawesome.utils.weight import get_total_weight_by_parent

ALLOWED_STATUS_TRANSITIONS = {'Sent': {'Received', 'Rejected'}}


def _parse_json(value):
	if isinstance(value, str):
		return json.loads(value)
	return value


@frappe.whitelist()
def create_requisition(data):
	"""Create and submit a requisition from POS."""
	ensure_can_create(_('create a Requisition'))
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


def _enrich_list_row(row):
	row['can_manage_status'] = bool(is_system_manager()) and row.get('transfer_status') == 'Sent'
	return row


@frappe.whitelist()
def get_requisitions_list(
	page_start=0,
	page_length=20,
	mine_only=0,
	status=None,
	from_date=None,
	to_date=None,
	item_code=None,
	item_group=None,
	warehouse=None,
	search=None,
):
	"""Paginated, filterable requisition list for POS tracking."""
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
		search=search,
		search_fields=['name', 'source_warehouse', 'target_warehouse', 'requested_by'],
		# A cancelled Requisition (docstatus=2) should still show up in the list
		# rather than disappearing, matching Material Transfer's list behavior.
		# Drafts (docstatus=0) stay visible too, so they remain deletable.
		include_cancelled=True,
		include_draft=True,
	)

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
			'docstatus',
			'modified',
		],
		page_start=page_start,
		page_length=page_length,
		extra_filters={'transfer_status': status} if status else None,
		**shared_filter_args,
	)

	status_counts = get_warehouse_doc_status_counts(
		'Requisition',
		'source_warehouse',
		'target_warehouse',
		'transfer_status',
		**shared_filter_args,
	)

	weight_by_parent = get_total_weight_by_parent(
		'Requisition Item', [row['name'] for row in rows], qty_field='required_qty',
	)
	for row in rows:
		row['total_weight'] = weight_by_parent.get(row['name'], 0.0)

	requisitions = [_enrich_list_row(row) for row in rows]

	return {
		'requisitions': requisitions,
		'total': total,
		'has_more': (page_start + page_length) < total,
		'status_counts': status_counts,
	}


@frappe.whitelist()
def get_requisition_detail(requisition):
	doc = frappe.get_doc('Requisition', requisition)
	ensure_warehouse_doc_read_access(doc, 'source_warehouse', 'target_warehouse')
	owner_name = frappe.db.get_value('User', doc.owner, 'full_name') or doc.owner

	# custom_default_weigt_of_measure (weight per unit) lives on the Item
	# master, not the Requisition Item child row -- one bulk lookup rather
	# than N+1 queries per item.
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
		weight = flt(weight_by_item.get(row.item_code)) * flt(row.required_qty)
		total_weight += weight
		items.append(
			{
				'name': row.name,
				'item_code': row.item_code,
				'item_name': row.item_name,
				'item_group': row.item_group,
				'required_qty': flt(row.required_qty),
				'uom': row.uom,
				'schedule_date': row.schedule_date,
				'weight': flt(weight),
			}
		)

	return {
		'name': doc.name,
		'transaction_date': doc.transaction_date,
		'requested_by': doc.requested_by,
		'source_warehouse': doc.source_warehouse,
		'target_warehouse': doc.target_warehouse,
		'transfer_status': doc.transfer_status,
		'notes': doc.notes,
		'created_by': owner_name,
		'creation': doc.creation,
		'amended_from': doc.get('amended_from'),
		'total_required_qty': flt(sum(flt(row.required_qty) for row in doc.items)),
		'total_weight': flt(total_weight),
		'item_count': len(doc.items),
		'items': items,
		'can_manage_status': bool(is_system_manager()) and doc.transfer_status == 'Sent',
	}


@frappe.whitelist()
def set_requisition_status(requisition, status):
	"""Transition a submitted Requisition from Sent to Received/Rejected."""
	if not is_system_manager():
		frappe.throw(
			_('Only a System Manager can update the Requisition status.'),
			title=_('Not Allowed'),
			exc=frappe.PermissionError,
		)

	if status not in ('Received', 'Rejected'):
		frappe.throw(_('Invalid status {0}.').format(status))

	doc = frappe.get_doc('Requisition', requisition)
	if doc.docstatus != 1:
		frappe.throw(_('Submit the Requisition before updating its status.'))

	allowed_next = ALLOWED_STATUS_TRANSITIONS.get(doc.transfer_status, set())
	if status not in allowed_next:
		frappe.throw(
			_('Requisition {0} cannot move from {1} to {2}.').format(
				doc.name, doc.transfer_status, status
			),
			title=_('Invalid Status Change'),
		)

	doc.db_set('transfer_status', status, update_modified=False)
	return {'name': doc.name, 'transfer_status': status}


@frappe.whitelist()
def cancel_requisition(requisition):
	"""Cancel a submitted Requisition. Restricted to System Manager, matching
	the Sales/Purchase Invoice cancel gate elsewhere in POS Awesome. Requisition
	never creates a Stock Entry (unlike Material Transfer), so there is nothing
	beyond docstatus for a plain cancel to reverse."""
	if "System Manager" not in frappe.get_roles(frappe.session.user):
		frappe.throw(
			_("Only a user with the System Manager role can cancel this document."),
			frappe.PermissionError,
		)

	doc = frappe.get_doc('Requisition', requisition)
	if doc.docstatus != 1:
		frappe.throw(_('Only a submitted document can be cancelled.'))

	doc.flags.ignore_permissions = True
	doc.cancel()
	return {'name': doc.name, 'docstatus': doc.docstatus}


@frappe.whitelist()
def delete_cancelled_requisition(requisition):
	"""Permanently delete a Draft or Cancelled Requisition."""
	if not is_system_manager():
		frappe.throw(
			_('Only a System Manager can delete Requisitions.'),
			exc=frappe.PermissionError,
		)

	if frappe.db.get_value('Requisition', requisition, 'docstatus') not in (0, 2):
		frappe.throw(_('Only a draft or cancelled document can be deleted.'))

	frappe.delete_doc('Requisition', requisition, ignore_permissions=True)
	return {'name': requisition}


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
			'custom_default_weigt_of_measure',
		],
		order_by='item_name asc',
		limit_page_length=limit,
	)
