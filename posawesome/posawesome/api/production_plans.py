# Copyright (c) 2026, POS Awesome and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _
from frappe.utils import flt, get_datetime, today

from posawesome.posawesome.utils.warehouse_doc_permissions import is_system_manager

ALLOWED_TRANSITIONS = {
	'Draft': {'Start Production': 'Work In Progress'},
	'Work In Progress': {'Mark Production Complete': 'Production Complete'},
	'Production Complete': {'Cancel': 'Cancelled'},
}


def _parse_json(value):
	if isinstance(value, str):
		return json.loads(value)
	return value


def _resolve_company(pos_profile):
	if isinstance(pos_profile, dict):
		return pos_profile.get('company')
	if pos_profile:
		return frappe.db.get_value('POS Profile', pos_profile, 'company')
	return frappe.defaults.get_default('company')


@frappe.whitelist()
def get_default_fg_warehouse():
	"""Manufacturing Settings' Default Finished Goods Warehouse, used to prefill the
	Production Plan's Source/Target Warehouse fields."""
	if not is_system_manager():
		frappe.throw(
			_('Only a System Manager can view Production Plans.'),
			exc=frappe.PermissionError,
		)

	warehouse = frappe.db.get_single_value('Manufacturing Settings', 'default_fg_warehouse')
	if not warehouse:
		return None

	return {
		'name': warehouse,
		'warehouse_name': frappe.db.get_value('Warehouse', warehouse, 'warehouse_name') or warehouse,
	}


@frappe.whitelist()
def search_manufacturable_items(search_text=None, limit=20):
	"""Item search restricted to items with an active default BOM, for the Production
	Plan item picker. Each result carries its default bom_no so the caller doesn't need
	a second lookup."""
	limit = max(1, min(int(limit or 20), 50))
	conditions = ['item.disabled = 0', 'bom.is_active = 1', 'bom.is_default = 1', 'bom.docstatus = 1']
	values = {}
	if search_text and len(search_text.strip()) >= 2:
		conditions.append('(item.name LIKE %(search)s OR item.item_name LIKE %(search)s)')
		values['search'] = f'%{search_text.strip()}%'

	where_clause = ' AND '.join(conditions)
	return frappe.db.sql(
		f"""
		SELECT
			item.name AS item_code,
			item.item_name AS item_name,
			item.item_group AS item_group,
			item.stock_uom AS stock_uom,
			bom.name AS bom_no
		FROM `tabItem` item
		INNER JOIN `tabBOM` bom ON bom.item = item.name
		WHERE {where_clause}
		ORDER BY item.item_name ASC
		LIMIT %(limit)s
		""",
		{**values, 'limit': limit},
		as_dict=True,
	)


@frappe.whitelist()
def get_bom_raw_materials(bom_no, qty=1):
	"""Raw materials (BOM Item rows) for a BOM, scaled to the given quantity, so the
	Production Plan item picker can preview what will be consumed before creating the
	plan."""
	if not is_system_manager():
		frappe.throw(
			_('Only a System Manager can view Production Plans.'),
			exc=frappe.PermissionError,
		)

	if not bom_no or not frappe.db.exists('BOM', bom_no):
		return []

	company = frappe.db.get_value('BOM', bom_no, 'company')

	from erpnext.manufacturing.doctype.bom.bom import get_bom_items

	items = get_bom_items(bom_no, company, qty=flt(qty) or 1, fetch_exploded=0)
	return [
		{
			'item_code': d.item_code,
			'item_name': d.item_name,
			'qty': flt(d.qty),
			'uom': d.stock_uom,
		}
		for d in items
	]


@frappe.whitelist()
def create_production_plan(data):
	"""Create a Production Plan (Draft) from POS. Restricted to System Manager."""
	if not is_system_manager():
		frappe.throw(
			_('Only a System Manager can create a Production Plan.'),
			exc=frappe.PermissionError,
		)

	data = _parse_json(data)
	if not data:
		frappe.throw(_('Production Plan data is required.'))

	items = data.get('items') or []
	if not items:
		frappe.throw(_('Add at least one item.'), title=_('Items Required'))
	if len(items) > 1:
		frappe.throw(_('Only one production item is allowed per plan.'), title=_('Too Many Items'))

	target_warehouse = data.get('target_warehouse')
	if not target_warehouse:
		frappe.throw(_('Target Warehouse is required.'), title=_('Warehouse Required'))

	company = _resolve_company(data.get('pos_profile'))
	if not company:
		frappe.throw(_('Could not determine Company.'))

	posting_date = data.get('posting_date') or today()

	doc = frappe.new_doc('Production Plan')
	doc.company = company
	doc.posting_date = posting_date
	if data.get('source_warehouse'):
		doc.for_warehouse = data.get('source_warehouse')

	for row in items:
		qty = flt(row.get('qty'))
		if qty <= 0:
			continue
		if not row.get('item_code') or not row.get('bom_no'):
			continue
		doc.append('po_items', {
			'item_code': row.get('item_code'),
			'bom_no': row.get('bom_no'),
			'planned_qty': qty,
			'stock_uom': row.get('uom'),
			'warehouse': target_warehouse,
			'planned_start_date': get_datetime(row.get('planned_start_date') or posting_date),
		})

	if not doc.po_items:
		frappe.throw(_('Add at least one item with quantity.'), title=_('Items Required'))

	doc.flags.ignore_permissions = True
	doc.insert()

	return {'name': doc.name, 'workflow_state': doc.workflow_state}


def _enrich_list_row(row):
	row['available_actions'] = list(ALLOWED_TRANSITIONS.get(row.get('workflow_state'), {}).keys())
	return row


@frappe.whitelist()
def get_production_plans_list(
	page_start=0,
	page_length=20,
	status=None,
	from_date=None,
	to_date=None,
	item_code=None,
	item_group=None,
	warehouse=None,
	search=None,
):
	"""Paginated, filterable Production Plan list. Restricted to System Manager."""
	if not is_system_manager():
		frappe.throw(
			_('Only a System Manager can view Production Plans.'),
			exc=frappe.PermissionError,
		)

	doctype = 'Production Plan'
	filters = []
	if status:
		filters.append([doctype, 'workflow_state', '=', status])
	if from_date:
		filters.append([doctype, 'posting_date', '>=', from_date])
	if to_date:
		filters.append([doctype, 'posting_date', '<=', to_date])
	if warehouse:
		filters.append([doctype, 'for_warehouse', '=', warehouse])

	item_doctype = 'Production Plan Item'
	if item_code:
		filters.append([item_doctype, 'item_code', '=', item_code])
	if item_group:
		filters.append([item_doctype, 'item_group', '=', item_group])

	or_filters = None
	if search:
		like = f'%{search}%'
		or_filters = [
			[doctype, 'name', 'like', like],
			[doctype, 'for_warehouse', 'like', like],
		]

	page_start = max(0, int(page_start or 0))
	page_length = max(1, min(int(page_length or 20), 100))

	fields = [
		'name',
		'posting_date',
		'company',
		'for_warehouse',
		'workflow_state',
		'total_planned_qty',
		'modified',
	]

	rows = frappe.get_list(
		doctype,
		filters=filters,
		or_filters=or_filters,
		fields=fields,
		order_by='posting_date desc, modified desc',
		limit_start=page_start,
		limit_page_length=page_length,
		distinct=True,
		ignore_permissions=True,
	)
	rows = [_enrich_list_row(row) for row in rows]

	total = len(
		frappe.get_list(
			doctype,
			filters=filters,
			or_filters=or_filters,
			fields=['name'],
			distinct=True,
			ignore_permissions=True,
			limit_page_length=0,
		)
	)

	status_filters = [f for f in filters if not (f[0] == doctype and f[1] == 'workflow_state')]
	status_counts = {
		row.workflow_state: row.count
		for row in frappe.get_list(
			doctype,
			filters=status_filters,
			or_filters=or_filters,
			fields=['workflow_state', 'count(name) as count'],
			group_by='workflow_state',
			ignore_permissions=True,
			limit_page_length=0,
		)
	}

	return {
		'plans': rows,
		'total': total,
		'has_more': (page_start + page_length) < total,
		'status_counts': status_counts,
	}


@frappe.whitelist()
def get_production_plan_detail(name):
	"""Full detail (header + items) for the Production Plan list's detail page.
	Restricted to System Manager."""
	if not is_system_manager():
		frappe.throw(
			_('Only a System Manager can view Production Plans.'),
			exc=frappe.PermissionError,
		)

	doc = frappe.get_doc('Production Plan', name)

	# Production Plan Item has no item_name field of its own; look it up in bulk.
	item_codes = list({row.item_code for row in doc.po_items if row.item_code})
	item_names = (
		{
			row.name: row.item_name
			for row in frappe.get_all('Item', filters={'name': ['in', item_codes]}, fields=['name', 'item_name'])
		}
		if item_codes
		else {}
	)

	owner_name = frappe.db.get_value('User', doc.owner, 'full_name') or doc.owner

	return {
		'name': doc.name,
		'company': doc.company,
		'posting_date': doc.posting_date,
		'for_warehouse': doc.for_warehouse,
		'customer': doc.get('customer'),
		'get_items_from': doc.get('get_items_from'),
		'workflow_state': doc.workflow_state,
		'status': doc.status,
		'total_planned_qty': flt(doc.total_planned_qty),
		'total_produced_qty': flt(doc.get('total_produced_qty')),
		'created_by': owner_name,
		'creation': doc.creation,
		'amended_from': doc.get('amended_from'),
		'item_count': len(doc.po_items),
		'items': [
			{
				'item_code': row.item_code,
				'item_name': item_names.get(row.item_code),
				'bom_no': row.bom_no,
				'planned_qty': flt(row.planned_qty),
				'pending_qty': flt(row.get('pending_qty')),
				'produced_qty': flt(row.get('produced_qty')),
				'stock_uom': row.stock_uom,
				'warehouse': row.warehouse,
				'planned_start_date': row.planned_start_date,
			}
			for row in doc.po_items
		],
		'available_actions': list(ALLOWED_TRANSITIONS.get(doc.workflow_state, {}).keys()),
	}


def _cancel_linked_production_documents(production_plan_name):
	"""Cancel every submitted document this Production Plan produced, in
	dependency order, so raw-material consumption and finished-goods
	production are both reversed in the stock ledger:

	Stock Entry (and Job Card) -> Work Order -> Production Plan.

	Work Order.validate_cancel blocks cancellation while a submitted Stock
	Entry against it still exists, so those must go first. Job Cards aren't
	stock documents and don't block Work Order cancel, but they're still
	"related documents" the user expects cleaned up rather than left
	orphaned against a cancelled Work Order.
	"""
	work_orders = frappe.get_all(
		'Work Order',
		filters={'production_plan': production_plan_name, 'docstatus': 1},
		pluck='name',
	)

	for wo_name in work_orders:
		stock_entries = frappe.get_all(
			'Stock Entry',
			filters={'work_order': wo_name, 'docstatus': 1},
			pluck='name',
		)
		for se_name in stock_entries:
			se_doc = frappe.get_doc('Stock Entry', se_name)
			se_doc.flags.ignore_permissions = True
			se_doc.cancel()

		job_cards = frappe.get_all(
			'Job Card',
			filters={'work_order': wo_name, 'docstatus': 1},
			pluck='name',
		)
		for jc_name in job_cards:
			jc_doc = frappe.get_doc('Job Card', jc_name)
			jc_doc.flags.ignore_permissions = True
			jc_doc.cancel()

		wo_doc = frappe.get_doc('Work Order', wo_name)
		wo_doc.flags.ignore_permissions = True
		wo_doc.cancel()


@frappe.whitelist()
def advance_production_plan_status(name, action):
	"""Transition a Production Plan through Draft -> Work In Progress ->
	Production Complete -> Cancelled. Restricted to System Manager.

	Bypasses the underlying Frappe Workflow's native role check (Manufacturing
	User/Manager) the same way confirm_receipt_from_requisition bypasses Stock
	Entry's workflow for Requisition receipts: submit/cancel with
	ignore_permissions, then set workflow_state via db_set (a raw update, so it
	never re-triggers the workflow's own transition-permission validation).
	"""
	if not is_system_manager():
		frappe.throw(
			_('Only a System Manager can update Production Plan status.'),
			exc=frappe.PermissionError,
		)

	doc = frappe.get_doc('Production Plan', name)
	next_state = (ALLOWED_TRANSITIONS.get(doc.workflow_state) or {}).get(action)
	if not next_state:
		frappe.throw(
			_('Production Plan {0} cannot perform {1} from {2}.').format(
				doc.name, action, doc.workflow_state
			),
			title=_('Invalid Status Change'),
		)

	doc.flags.ignore_permissions = True
	if action == 'Mark Production Complete':
		doc.submit()
	elif action == 'Cancel':
		_cancel_linked_production_documents(doc.name)
		# Cancelling the linked Work Order(s) updates fields (ordered_qty etc.)
		# on this same Production Plan, bumping its modified timestamp -- reload
		# so the in-memory doc's timestamp matches before cancel's own save.
		doc.reload()
		doc.flags.ignore_permissions = True
		doc.cancel()

	doc.db_set('workflow_state', next_state, update_modified=False)
	return {'name': doc.name, 'workflow_state': next_state}
