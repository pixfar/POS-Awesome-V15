# Copyright (c) 2026, POS Awesome and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _
from frappe.utils import cint, flt

from posawesome.posawesome.utils.warehouse_doc_permissions import is_system_manager
from posawesome.posawesome.utils.weight import get_total_weight_by_parent


def _parse_json(value):
	if isinstance(value, str):
		return json.loads(value)
	return value


def _resolve_company(pos_profile, fallback=None):
	if isinstance(pos_profile, dict):
		company = pos_profile.get('company')
		if company:
			return company
	elif pos_profile:
		company = frappe.db.get_value('POS Profile', pos_profile, 'company')
		if company:
			return company
	return fallback or frappe.defaults.get_default('company')


@frappe.whitelist()
def get_default_pos_profile():
	"""Resolve a usable POS Profile for the current user so the item catalog (used by
	the raw material browser) can initialize even when no POS register/shift is open
	-- this page is for back-office BOM management, not cashier sales, so it shouldn't
	depend on a cashier session existing."""
	if not is_system_manager():
		frappe.throw(
			_('Only a System Manager can manage BOMs.'),
			exc=frappe.PermissionError,
		)

	assigned = frappe.db.sql(
		"""
		SELECT p.name
		FROM `tabPOS Profile` p
		INNER JOIN `tabPOS Profile User` u ON u.parent = p.name
		WHERE p.disabled = 0 AND u.user = %s
		ORDER BY p.name
		LIMIT 1
		""",
		frappe.session.user,
	)
	profile_name = assigned[0][0] if assigned else frappe.db.get_value('POS Profile', {'disabled': 0}, 'name')
	if not profile_name:
		return None

	return frappe.get_cached_doc('POS Profile', profile_name).as_dict()


@frappe.whitelist()
def get_default_wip_warehouse():
	"""Manufacturing Settings' Default Work In Progress Warehouse, used as the stock
	context for the BOM raw material browser."""
	if not is_system_manager():
		frappe.throw(
			_('Only a System Manager can manage BOMs.'),
			exc=frappe.PermissionError,
		)

	warehouse = frappe.db.get_single_value('Manufacturing Settings', 'default_wip_warehouse')
	if not warehouse:
		return None

	return {
		'name': warehouse,
		'warehouse_name': frappe.db.get_value('Warehouse', warehouse, 'warehouse_name') or warehouse,
	}


@frappe.whitelist()
def search_bom_items(search_text=None, limit=20, stock_items_only=0, exclude_item_code=None):
	"""Item search for the BOM creation form: the item to manufacture (any item) or a
	raw material row (stock items only)."""
	if not is_system_manager():
		frappe.throw(
			_('Only a System Manager can manage BOMs.'),
			exc=frappe.PermissionError,
		)

	limit = max(1, min(int(limit or 20), 50))
	conditions = ['item.disabled = 0']
	values = {}

	if cint(stock_items_only):
		conditions.append('item.is_stock_item = 1')

	if exclude_item_code:
		conditions.append('item.name != %(exclude_item_code)s')
		values['exclude_item_code'] = exclude_item_code

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
			item.custom_default_weigt_of_measure AS custom_default_weigt_of_measure
		FROM `tabItem` item
		WHERE {where_clause}
		ORDER BY item.item_name ASC
		LIMIT %(limit)s
		""",
		{**values, 'limit': limit},
		as_dict=True,
	)


@frappe.whitelist()
def create_bom(data):
	"""Create and submit a BOM (item to manufacture + raw materials) from POS.
	Restricted to System Manager. Submitting makes it the item's active default BOM
	(BOM.manage_default_bom unmarks any previous default automatically)."""
	if not is_system_manager():
		frappe.throw(
			_('Only a System Manager can create a BOM.'),
			exc=frappe.PermissionError,
		)

	data = _parse_json(data)
	if not data:
		frappe.throw(_('BOM data is required.'))

	item_code = data.get('item_code')
	if not item_code:
		frappe.throw(_('Item to manufacture is required.'), title=_('Item Required'))

	raw_materials = data.get('items') or []
	if not raw_materials:
		frappe.throw(_('Add at least one raw material.'), title=_('Raw Materials Required'))

	company = _resolve_company(data.get('pos_profile'), data.get('company'))
	if not company:
		frappe.throw(_('Could not determine Company.'))

	doc = frappe.new_doc('BOM')
	doc.item = item_code
	doc.quantity = flt(data.get('quantity')) or 1
	doc.company = company
	# Mandatory and normally set by the desk form's client script on load; there's no
	# equivalent hook when creating a BOM headlessly through this API.
	doc.currency = frappe.get_cached_value('Company', company, 'default_currency')
	doc.is_active = 1
	doc.is_default = 1

	for row in raw_materials:
		qty = flt(row.get('qty'))
		if qty <= 0 or not row.get('item_code'):
			continue
		if row.get('item_code') == item_code:
			frappe.throw(_('Raw material cannot be the same as the item being manufactured.'))
		doc.append('items', {'item_code': row.get('item_code'), 'qty': qty})

	if not doc.items:
		frappe.throw(_('Add at least one raw material with a quantity.'), title=_('Raw Materials Required'))

	doc.flags.ignore_permissions = True
	doc.insert()
	doc.submit()

	return {'name': doc.name}


def _enrich_list_row(row):
	row['status'] = 'Cancelled' if row.get('docstatus') == 2 else ('Submitted' if row.get('docstatus') == 1 else 'Draft')
	return row


@frappe.whitelist()
def get_boms_list(
	page_start=0,
	page_length=20,
	item_code=None,
	is_active=None,
	is_default=None,
	search=None,
):
	"""Paginated, filterable BOM list for the POS BOM list page. Restricted to
	System Manager."""
	if not is_system_manager():
		frappe.throw(
			_('Only a System Manager can view BOMs.'),
			exc=frappe.PermissionError,
		)

	doctype = 'BOM'
	filters = []
	if item_code:
		filters.append([doctype, 'item', '=', item_code])
	if is_active not in (None, ''):
		filters.append([doctype, 'is_active', '=', cint(is_active)])
	if is_default not in (None, ''):
		filters.append([doctype, 'is_default', '=', cint(is_default)])

	or_filters = None
	if search:
		like = f'%{search}%'
		or_filters = [
			[doctype, 'name', 'like', like],
			[doctype, 'item', 'like', like],
			[doctype, 'item_name', 'like', like],
		]

	page_start = max(0, int(page_start or 0))
	page_length = max(1, min(int(page_length or 20), 100))

	fields = [
		'name',
		'item',
		'item_name',
		'uom',
		'quantity',
		'is_active',
		'is_default',
		'docstatus',
		'total_cost',
		'modified',
	]

	rows = frappe.get_list(
		doctype,
		filters=filters,
		or_filters=or_filters,
		fields=fields,
		order_by='modified desc',
		limit_start=page_start,
		limit_page_length=page_length,
		ignore_permissions=True,
	)
	rows = [_enrich_list_row(row) for row in rows]

	weight_by_parent = get_total_weight_by_parent('BOM Item', [row['name'] for row in rows])
	for row in rows:
		row['total_weight'] = weight_by_parent.get(row['name'], 0.0)

	total = len(
		frappe.get_list(
			doctype,
			filters=filters,
			or_filters=or_filters,
			fields=['name'],
			ignore_permissions=True,
			limit_page_length=0,
		)
	)

	return {
		'boms': rows,
		'total': total,
		'has_more': (page_start + page_length) < total,
	}


@frappe.whitelist()
def get_bom_detail(name):
	"""Full detail (header + raw materials) for the BOM list's detail page.
	Restricted to System Manager."""
	if not is_system_manager():
		frappe.throw(
			_('Only a System Manager can view BOMs.'),
			exc=frappe.PermissionError,
		)

	doc = frappe.get_doc('BOM', name)
	status = 'Cancelled' if doc.docstatus == 2 else ('Submitted' if doc.docstatus == 1 else 'Draft')

	# custom_default_weigt_of_measure (weight per unit) lives on the Item
	# master, not the BOM Item child row.
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
				'item_code': row.item_code,
				'item_name': row.item_name,
				'qty': flt(row.qty),
				'uom': row.uom,
				'rate': flt(row.rate),
				'amount': flt(row.amount),
				'weight': flt(weight),
			}
		)

	return {
		'name': doc.name,
		'item': doc.item,
		'item_name': doc.item_name,
		'quantity': flt(doc.quantity),
		'uom': doc.uom,
		'company': doc.company,
		'is_active': doc.is_active,
		'is_default': doc.is_default,
		'docstatus': doc.docstatus,
		'status': status,
		'total_cost': flt(doc.total_cost),
		'total_weight': flt(total_weight),
		'creation': doc.creation,
		'modified': doc.modified,
		'items': items,
	}


@frappe.whitelist()
def cancel_bom(name):
	"""Cancel a submitted BOM. Restricted to System Manager, matching the
	Sales/Purchase Invoice cancel gate elsewhere in POS Awesome."""
	if "System Manager" not in frappe.get_roles(frappe.session.user):
		frappe.throw(
			_("Only a user with the System Manager role can cancel this document."),
			frappe.PermissionError,
		)

	doc = frappe.get_doc("BOM", name)
	if doc.docstatus != 1:
		frappe.throw(_("Only a submitted document can be cancelled."))

	doc.cancel()
	return {"name": doc.name, "docstatus": doc.docstatus}


@frappe.whitelist()
def delete_cancelled_bom(name):
	"""Permanently delete a Draft or Cancelled BOM."""
	if not is_system_manager():
		frappe.throw(
			_("Only a System Manager can delete BOMs."),
			exc=frappe.PermissionError,
		)

	if frappe.db.get_value("BOM", name, "docstatus") not in (0, 2):
		frappe.throw(_("Only a draft or cancelled document can be deleted."))

	frappe.delete_doc("BOM", name)
	return {"name": name}
