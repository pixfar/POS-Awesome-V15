# Copyright (c) 2026, POS Awesome and contributors
# For license information, please see license.txt

"""POS Awesome screens for bsp_engineering's Production Requirement: a
per-warehouse sheet recording, per item, the Shortage Qty and the Plan Qty
set against it.

The doctype (and the server-side Shortage Qty snapshot) live in bsp_engineering -- this
module only builds/reads those documents for the POS UI, plus serves the
"Production Requirement Report" data the create screen shows as its item
catalog.

Access:
- Warehouse and Production By default to the logged-in user (their POS
  warehouse / themselves); only System Manager / BSP Admin may change them.
- Everyone else is scoped to their permitted warehouse(s), same as the
  doctype's own permission hooks.
- BSP Viewer is read-only.
"""

import json

import frappe
from frappe import _
from frappe.utils import flt, getdate, today

from posawesome.posawesome.utils.warehouse_doc_permissions import (
	ensure_can_create,
	get_expanded_permitted_warehouses,
	is_privileged_invoice_viewer,
	is_read_only_viewer,
)

DOCTYPE = 'Production Requirement'
ITEM_DOCTYPE = 'Production Requirement Item'
STATUSES = ('Pending', 'In Progress', 'Completed', 'On Hold', 'Cancelled')


def _parse_json(value):
	if isinstance(value, str):
		return json.loads(value) if value else None
	return value


def _ensure_can_view():
	if not frappe.has_permission(DOCTYPE, 'read'):
		frappe.throw(_('You are not permitted to view Production Requirements.'), exc=frappe.PermissionError)


def _ensure_doc_access(doc):
	permitted = get_expanded_permitted_warehouses()
	if permitted is not None and doc.warehouse not in permitted:
		frappe.throw(
			_('You are not permitted to access Production Requirement {0}.').format(doc.name),
			exc=frappe.PermissionError,
		)


def _can_edit():
	return not is_read_only_viewer()


def _can_delete(doc_or_row):
	if is_read_only_viewer():
		return False
	if is_privileged_invoice_viewer():
		return True
	# Staff may discard their own sheets.
	return doc_or_row.get('owner') == frappe.session.user


def _user_label(user):
	return frappe.db.get_value('User', user, 'full_name') or user


def _default_warehouse(pos_profile=None):
	from bsp_engineering.utils.pos_warehouse import resolve_pos_warehouse

	profile = _parse_json(pos_profile) if pos_profile else None
	company = profile.get('company') if isinstance(profile, dict) else None
	return resolve_pos_warehouse(company=company, pos_profile=profile if isinstance(profile, dict) else None)


@frappe.whitelist()
def get_form_context(pos_profile=None):
	"""Defaults for the create screen: the user's own warehouse and name, and
	whether this user may change either."""
	_ensure_can_view()
	warehouse = _default_warehouse(pos_profile)
	can_change = is_privileged_invoice_viewer()
	return {
		'warehouse': warehouse,
		'warehouse_name': frappe.db.get_value('Warehouse', warehouse, 'warehouse_name') if warehouse else None,
		'production_by': frappe.session.user,
		'production_by_name': _user_label(frappe.session.user),
		'can_change_warehouse': can_change,
		'can_change_production_by': can_change,
		'can_create': not is_read_only_viewer(),
		'today': today(),
	}


@frappe.whitelist()
def get_filter_options():
	_ensure_can_view()
	return {
		'item_groups': frappe.get_all('Item Group', filters={'is_group': 0}, pluck='name', order_by='name asc'),
		'production_groups': frappe.get_all('Production Group', pluck='name', order_by='name asc'),
	}


@frappe.whitelist()
def search_users(search_text=None, limit=20):
	"""Enabled system users for the Production By picker (admins only)."""
	if not is_privileged_invoice_viewer():
		frappe.throw(_('Only a System Manager or BSP Admin can change Production By.'), exc=frappe.PermissionError)
	limit = max(1, min(int(limit or 20), 50))
	or_filters = None
	if search_text and search_text.strip():
		like = f'%{search_text.strip()}%'
		or_filters = [['name', 'like', like], ['full_name', 'like', like]]
	return frappe.get_all(
		'User',
		filters={'enabled': 1, 'user_type': 'System User'},
		or_filters=or_filters,
		fields=['name', 'full_name'],
		order_by='full_name asc',
		limit_page_length=limit,
	)


@frappe.whitelist()
def get_requirement_catalog(item_group=None, production_group=None, stock_status=None):
	"""Rows of bsp_engineering's "Production Requirement Report" (Low Qty /
	Stock per production-feeder warehouse, plus totals), for the create
	screen's item cards. Each row also carries stock_uom/image and a
	`shortage` = Total Low Qty - Total Stock (never below zero), used as the
	suggested Plan Qty."""
	_ensure_can_view()
	from bsp_engineering.bsp_engineering.report.production_requirement_report.production_requirement_report import (
		execute,
	)

	filters = {}
	if item_group:
		filters['item_group'] = [item_group] if isinstance(item_group, str) and not item_group.startswith('[') else _parse_json(item_group)
	if production_group:
		filters['production_group'] = (
			[production_group]
			if isinstance(production_group, str) and not production_group.startswith('[')
			else _parse_json(production_group)
		)
	if stock_status in ('Low Stock', 'Sufficient Stock'):
		filters['stock_status'] = stock_status

	columns, data = execute(filters)

	# Report columns are "<Warehouse> Low Qty" / "<Warehouse> Stock" pairs in
	# fieldname order wh_0_low_qty, wh_0_stock, wh_1_low_qty, ...
	warehouses = []
	for col in columns:
		fieldname = col.get('fieldname') or ''
		if fieldname.startswith('wh_') and fieldname.endswith('_stock'):
			idx = fieldname[3:-6]
			label = str(col.get('label') or '')
			warehouses.append({'key': idx, 'label': label.rsplit(' ', 1)[0] if label.endswith('Stock') else label})

	item_codes = [row['item_code'] for row in data]
	item_meta = {}
	if item_codes:
		for row in frappe.get_all(
			'Item',
			filters={'name': ['in', item_codes]},
			fields=['name', 'stock_uom', 'image', 'disabled', 'custom_production_group'],
		):
			item_meta[row.name] = row

	rows = []
	for row in data:
		meta = item_meta.get(row['item_code']) or {}
		if meta.get('disabled'):
			continue
		total_low = flt(row.get('total_low_qty'))
		total_stock = flt(row.get('total_stock'))
		rows.append(
			{
				'item_code': row['item_code'],
				'item_name': row.get('item_name'),
				'item_group': row.get('item_group'),
				'production_group': meta.get('custom_production_group'),
				'stock_uom': meta.get('stock_uom'),
				'image': meta.get('image'),
				'total_low_qty': total_low,
				'total_stock': total_stock,
				'shortage': max(total_low - total_stock, 0.0),
				'is_low': total_stock < total_low,
				'warehouses': [
					{
						'label': wh['label'],
						'low_qty': flt(row.get(f"wh_{wh['key']}_low_qty")),
						'stock': flt(row.get(f"wh_{wh['key']}_stock")),
					}
					for wh in warehouses
				],
			}
		)

	return {'warehouses': [wh['label'] for wh in warehouses], 'items': rows}


def _resolve_warehouse_for_save(requested, existing_doc, pos_profile):
	if is_privileged_invoice_viewer():
		warehouse = requested or (existing_doc.warehouse if existing_doc else None) or _default_warehouse(pos_profile)
	elif existing_doc:
		# Non-admins can't move an existing sheet to another warehouse.
		warehouse = existing_doc.warehouse
	else:
		warehouse = _default_warehouse(pos_profile)
	if not warehouse:
		frappe.throw(_('Warehouse is required.'), title=_('Warehouse Required'))
	return warehouse


@frappe.whitelist()
def save_production_requirement(data, name=None):
	"""Create (no `name`) or update a Production Requirement from POS."""
	ensure_can_create(_('create or edit a Production Requirement'))
	data = _parse_json(data) or {}

	existing = None
	if name:
		existing = frappe.get_doc(DOCTYPE, name)
		_ensure_doc_access(existing)
		doc = existing
	else:
		doc = frappe.new_doc(DOCTYPE)

	doc.production_date = getdate(data.get('production_date') or today())
	doc.posting_date = getdate(data.get('posting_date') or today())
	doc.warehouse = _resolve_warehouse_for_save(data.get('warehouse'), existing, data.get('pos_profile'))
	if is_privileged_invoice_viewer() and data.get('production_by'):
		doc.production_by = data.get('production_by')
	elif not existing:
		doc.production_by = frappe.session.user
	doc.remarks = data.get('remarks')
	if data.get('status'):
		doc.status = _validated_status(data.get('status'))

	items = data.get('items') or []
	if not items:
		frappe.throw(_('Add at least one item.'), title=_('Items Required'))

	doc.set('items', [])
	for row in items:
		item_code = (row or {}).get('item_code')
		if not item_code:
			continue
		doc.append(
			'items',
			{
				'item_code': item_code,
				'item_name': row.get('item_name'),
				'uom': row.get('uom') or frappe.db.get_value('Item', item_code, 'stock_uom'),
				# shortage_qty is set by the doctype itself (never trusted from the client).
				'plan_qty': flt(row.get('plan_qty')),
			},
		)

	doc.flags.ignore_permissions = True
	doc.save()
	return {'name': doc.name, 'status': doc.status}


def _validated_status(status):
	if status not in STATUSES:
		frappe.throw(_('Invalid status {0}.').format(status))
	return status


@frappe.whitelist()
def set_production_requirement_status(name, status):
	"""Quick status change from the list/detail pages."""
	ensure_can_create(_('change the status of a Production Requirement'))
	doc = frappe.get_doc(DOCTYPE, name)
	_ensure_doc_access(doc)
	doc.db_set('status', _validated_status(status), notify=True)
	return {'name': doc.name, 'status': doc.status}


@frappe.whitelist()
def get_production_requirements_list(
	page_start=0,
	page_length=20,
	status=None,
	from_date=None,
	to_date=None,
	warehouse=None,
	item_code=None,
	item_group=None,
	production_group=None,
	production_by=None,
	search=None,
):
	_ensure_can_view()

	conditions = ['1=1']
	values = {}
	if status:
		conditions.append('pr.status = %(status)s')
		values['status'] = status
	if from_date:
		conditions.append('pr.production_date >= %(from_date)s')
		values['from_date'] = getdate(from_date)
	if to_date:
		conditions.append('pr.production_date <= %(to_date)s')
		values['to_date'] = getdate(to_date)
	if warehouse:
		conditions.append('pr.warehouse = %(warehouse)s')
		values['warehouse'] = warehouse
	if production_by:
		conditions.append('pr.production_by = %(production_by)s')
		values['production_by'] = production_by
	if search and search.strip():
		conditions.append('(pr.name LIKE %(search)s OR pr.warehouse LIKE %(search)s OR pr.remarks LIKE %(search)s)')
		values['search'] = f'%{search.strip()}%'

	item_conditions = []
	if item_code:
		item_conditions.append('pri.item_code = %(item_code)s')
		values['item_code'] = item_code
	if item_group:
		item_conditions.append('item.item_group = %(item_group)s')
		values['item_group'] = item_group
	if production_group:
		item_conditions.append('item.custom_production_group = %(production_group)s')
		values['production_group'] = production_group
	if item_conditions:
		conditions.append(
			f"""EXISTS (
				SELECT 1 FROM `tab{ITEM_DOCTYPE}` pri
				LEFT JOIN `tabItem` item ON item.name = pri.item_code
				WHERE pri.parent = pr.name AND pri.parenttype = %(doctype)s AND {' AND '.join(item_conditions)}
			)"""
		)
		values['doctype'] = DOCTYPE

	permitted = get_expanded_permitted_warehouses()
	if permitted is not None:
		if not permitted:
			return {'rows': [], 'total': 0, 'has_more': False, 'status_counts': {}, 'can_create': False}
		conditions.append('pr.warehouse IN %(permitted)s')
		values['permitted'] = tuple(permitted)

	page_start = max(0, int(page_start or 0))
	page_length = max(1, min(int(page_length or 20), 100))
	values.update({'page_start': page_start, 'page_length': page_length})

	base_where = ' AND '.join(conditions)
	# Status counts ignore the status filter itself so every tile stays
	# meaningful while one status is selected.
	counts_where = ' AND '.join(c for c in conditions if c != 'pr.status = %(status)s')

	rows = frappe.db.sql(
		f"""
		SELECT pr.name, pr.production_date, pr.posting_date, pr.warehouse, pr.production_by,
			pr.status, pr.total_shortage_qty, pr.total_plan_qty,
			pr.owner, pr.modified, wh.warehouse_name, usr.full_name AS production_by_name,
			(SELECT COUNT(*) FROM `tab{ITEM_DOCTYPE}` c WHERE c.parent = pr.name AND c.parenttype = '{DOCTYPE}') AS item_count
		FROM `tab{DOCTYPE}` pr
		LEFT JOIN `tabWarehouse` wh ON wh.name = pr.warehouse
		LEFT JOIN `tabUser` usr ON usr.name = pr.production_by
		WHERE {base_where}
		ORDER BY pr.production_date DESC, pr.modified DESC
		LIMIT %(page_start)s, %(page_length)s
		""",
		values,
		as_dict=True,
	)
	total = frappe.db.sql(f'SELECT COUNT(*) FROM `tab{DOCTYPE}` pr WHERE {base_where}', values)[0][0]
	status_counts = dict(
		frappe.db.sql(
			f'SELECT pr.status, COUNT(*) FROM `tab{DOCTYPE}` pr WHERE {counts_where} GROUP BY pr.status', values
		)
	)
	totals = frappe.db.sql(
		f"""SELECT COALESCE(SUM(pr.total_shortage_qty), 0), COALESCE(SUM(pr.total_plan_qty), 0)
		FROM `tab{DOCTYPE}` pr WHERE {base_where}""",
		values,
	)[0]

	for row in rows:
		row['can_edit'] = _can_edit()
		row['can_delete'] = _can_delete(row)

	return {
		'rows': rows,
		'total': total,
		'has_more': (page_start + page_length) < total,
		'status_counts': status_counts,
		'total_shortage_qty': flt(totals[0]),
		'total_plan_qty': flt(totals[1]),
		'can_create': not is_read_only_viewer(),
	}


@frappe.whitelist()
def get_production_requirement_detail(name):
	_ensure_can_view()
	doc = frappe.get_doc(DOCTYPE, name)
	_ensure_doc_access(doc)

	item_codes = [row.item_code for row in doc.items]
	item_meta = {
		row.name: row
		for row in frappe.get_all(
			'Item',
			filters={'name': ['in', item_codes or ['']]},
			fields=['name', 'item_group', 'custom_production_group'],
		)
	}
	return {
		'name': doc.name,
		'production_date': doc.production_date,
		'posting_date': doc.posting_date,
		'warehouse': doc.warehouse,
		'warehouse_name': frappe.db.get_value('Warehouse', doc.warehouse, 'warehouse_name') or doc.warehouse,
		'production_by': doc.production_by,
		'production_by_name': _user_label(doc.production_by),
		'status': doc.status,
		'remarks': doc.remarks,
		'total_shortage_qty': flt(doc.total_shortage_qty),
		'total_plan_qty': flt(doc.total_plan_qty),
		'created_by': _user_label(doc.owner),
		'creation': doc.creation,
		'modified': doc.modified,
		'can_edit': _can_edit(),
		'can_delete': _can_delete(doc.as_dict()),
		'items': [
			{
				'item_code': row.item_code,
				'item_name': row.item_name,
				'item_group': (item_meta.get(row.item_code) or {}).get('item_group') or row.item_group,
				'production_group': (item_meta.get(row.item_code) or {}).get('custom_production_group'),
				'uom': row.uom,
				'shortage_qty': flt(row.shortage_qty),
				'plan_qty': flt(row.plan_qty),
			}
			for row in doc.items
		],
	}


@frappe.whitelist()
def delete_production_requirement(name):
	ensure_can_create(_('delete a Production Requirement'))
	doc = frappe.get_doc(DOCTYPE, name)
	_ensure_doc_access(doc)
	if not _can_delete(doc.as_dict()):
		frappe.throw(
			_('Only its creator, a System Manager or a BSP Admin can delete this Production Requirement.'),
			exc=frappe.PermissionError,
		)
	frappe.delete_doc(DOCTYPE, name, ignore_permissions=True)
	return {'name': name}
