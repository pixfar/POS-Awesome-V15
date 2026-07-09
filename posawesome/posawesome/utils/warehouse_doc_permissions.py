# Copyright (c) 2026, POS Awesome and contributors
# For license information, please see license.txt

"""Warehouse OR-permissions for doctypes with source/target warehouse links.

Frappe User Permissions apply AND logic across link fields, which hides
requisitions/transfers when the user only has access to one warehouse.
Sales uses a single warehouse field; this module mirrors that behaviour
using custom permission hooks and ignore_user_permissions on warehouse fields.
"""

import frappe
from frappe import _

SYSTEM_MANAGER_ROLE = 'System Manager'


def is_system_manager(user=None):
	user = user or frappe.session.user
	return user == 'Administrator' or SYSTEM_MANAGER_ROLE in frappe.get_roles(user)


def user_has_warehouse_restrictions(user=None):
	user = user or frappe.session.user
	if user == 'Administrator' or is_system_manager(user):
		return False
	return bool(
		frappe.db.exists('User Permission', {'user': user, 'allow': 'Warehouse'})
	)


def get_expanded_permitted_warehouses(user=None):
	user = user or frappe.session.user
	if user == 'Administrator' or is_system_manager(user):
		return None

	try:
		from bsp_engineering.utils.pos_warehouse import get_permitted_warehouse_names

		names = get_permitted_warehouse_names() or []
	except Exception:
		names = frappe.get_all(
			'User Permission',
			filters={'user': user, 'allow': 'Warehouse'},
			pluck='for_value',
		)

	if not names:
		return []

	expanded = set()
	for name in names:
		if not name:
			continue
		expanded.add(name)
		if frappe.db.get_value('Warehouse', name, 'is_group'):
			expanded.update(frappe.db.get_descendants('Warehouse', name) or [])

	return list(expanded)


def _sql_in_list(values):
	if not values:
		return ''
	escaped = ', '.join(frappe.db.escape(v) for v in values)
	return f'({escaped})'


def build_warehouse_or_condition(doctype, source_field, target_field, user=None):
	"""Return SQL fragment restricting to permitted source OR target warehouses."""
	if not user_has_warehouse_restrictions(user):
		return ''

	warehouses = get_expanded_permitted_warehouses(user)
	if not warehouses:
		return '1=0'

	table = f'`tab{doctype}`'
	in_list = _sql_in_list(warehouses)
	return f'({table}.{source_field} in {in_list} or {table}.{target_field} in {in_list})'


def user_can_read_warehouse_doc(doc, source_field, target_field, user=None):
	user = user or frappe.session.user
	if not user_has_warehouse_restrictions(user):
		return True

	warehouses = get_expanded_permitted_warehouses(user)
	if not warehouses:
		return False

	source = doc.get(source_field)
	target = doc.get(target_field)
	return source in warehouses or target in warehouses


def ensure_warehouse_doc_read_access(doc, source_field, target_field):
	if not user_can_read_warehouse_doc(doc, source_field, target_field):
		frappe.throw(
			_('You do not have permission to view this document.'),
			exc=frappe.PermissionError,
		)


def _build_warehouse_doc_conditions(
	doctype,
	source_field,
	target_field,
	mine_only=False,
	mine_field='requested_by',
	extra_filters=None,
	date_field=None,
	from_date=None,
	to_date=None,
	item_code=None,
	item_group=None,
	warehouse=None,
	search=None,
	search_fields=None,
	include_cancelled=False,
):
	"""Build the shared WHERE conditions/values for warehouse-scoped doc list queries.

	The main table must be aliased as `main` by the caller so the item EXISTS
	subquery below can reference `main.name`.

	include_cancelled=True also matches docstatus=2 records — for doctypes (like
	Material Transfer's Rejected flow) where cancelling is a normal terminal status
	that should still show up in the list, not just submitted ones.
	"""
	conditions = ['main.docstatus IN (1, 2)'] if include_cancelled else ['main.docstatus = 1']
	values = {}

	if extra_filters:
		for key, val in extra_filters.items():
			conditions.append(f'main.{key} = %({key})s')
			values[key] = val

	if date_field and from_date:
		conditions.append(f'main.{date_field} >= %(from_date)s')
		values['from_date'] = from_date
	if date_field and to_date:
		conditions.append(f'main.{date_field} <= %(to_date)s')
		values['to_date'] = to_date

	if warehouse:
		conditions.append(
			f'(main.{source_field} = %(warehouse)s OR main.{target_field} = %(warehouse)s)'
		)
		values['warehouse'] = warehouse

	if item_code or item_group:
		item_conditions = ['item.parent = main.name', 'item.parenttype = %(main_doctype)s']
		values['main_doctype'] = doctype
		if item_code:
			item_conditions.append('item.item_code = %(item_code)s')
			values['item_code'] = item_code
		if item_group:
			item_conditions.append('item.item_group = %(item_group)s')
			values['item_group'] = item_group
		item_table = f'`tab{doctype} Item`'
		conditions.append(
			f"EXISTS (SELECT 1 FROM {item_table} item WHERE {' AND '.join(item_conditions)})"
		)

	if search and search_fields:
		like_conditions = [f'main.{field} LIKE %(search)s' for field in search_fields]
		conditions.append('(' + ' OR '.join(like_conditions) + ')')
		values['search'] = f'%{search}%'

	if int(mine_only or 0):
		conditions.append(f'main.{mine_field} = %(mine_user)s')
		values['mine_user'] = frappe.session.user
	else:
		warehouse_condition = build_warehouse_or_condition(
			doctype,
			source_field,
			target_field,
		)
		if warehouse_condition:
			conditions.append(warehouse_condition.replace(f'`tab{doctype}`.', 'main.'))

	return conditions, values


def get_warehouse_doc_list_rows(
	doctype,
	source_field,
	target_field,
	fields,
	page_start=0,
	page_length=20,
	mine_only=False,
	mine_field='requested_by',
	extra_filters=None,
	date_field=None,
	from_date=None,
	to_date=None,
	item_code=None,
	item_group=None,
	warehouse=None,
	search=None,
	search_fields=None,
	include_cancelled=False,
):
	page_start = max(0, int(page_start or 0))
	page_length = max(1, min(int(page_length or 20), 100))

	conditions, values = _build_warehouse_doc_conditions(
		doctype,
		source_field,
		target_field,
		mine_only=mine_only,
		mine_field=mine_field,
		extra_filters=extra_filters,
		date_field=date_field,
		from_date=from_date,
		to_date=to_date,
		item_code=item_code,
		item_group=item_group,
		warehouse=warehouse,
		search=search,
		search_fields=search_fields,
		include_cancelled=include_cancelled,
	)
	where_clause = ' AND '.join(conditions)
	table = f'`tab{doctype}`'
	field_sql = ', '.join(f'main.{field}' for field in fields)

	rows = frappe.db.sql(
		f"""
		SELECT {field_sql}
		FROM {table} AS main
		WHERE {where_clause}
		ORDER BY main.modified DESC
		LIMIT %(limit_start)s, %(limit_length)s
		""",
		{
			**values,
			'limit_start': page_start,
			'limit_length': page_length,
		},
		as_dict=True,
	)

	count_result = frappe.db.sql(
		f'SELECT COUNT(*) FROM {table} AS main WHERE {where_clause}',
		values,
	)
	total = count_result[0][0] if count_result else 0

	return rows, total


def get_warehouse_doc_status_counts(
	doctype,
	source_field,
	target_field,
	status_field,
	mine_only=False,
	mine_field='requested_by',
	date_field=None,
	from_date=None,
	to_date=None,
	item_code=None,
	item_group=None,
	warehouse=None,
	search=None,
	search_fields=None,
	include_cancelled=False,
):
	"""Grouped status counts using the same scoping as get_warehouse_doc_list_rows,
	but without a status filter, so every status tile stays accurate."""
	conditions, values = _build_warehouse_doc_conditions(
		doctype,
		source_field,
		target_field,
		mine_only=mine_only,
		mine_field=mine_field,
		date_field=date_field,
		from_date=from_date,
		to_date=to_date,
		item_code=item_code,
		item_group=item_group,
		warehouse=warehouse,
		search=search,
		search_fields=search_fields,
		include_cancelled=include_cancelled,
	)
	where_clause = ' AND '.join(conditions)
	table = f'`tab{doctype}`'

	rows = frappe.db.sql(
		f"""
		SELECT main.{status_field} AS status, COUNT(*) AS count
		FROM {table} AS main
		WHERE {where_clause}
		GROUP BY main.{status_field}
		""",
		values,
		as_dict=True,
	)
	return {row.status: row.count for row in rows}


def get_requisition_permission_query(user, doctype=None):
	return build_warehouse_or_condition(
		'Requisition',
		'source_warehouse',
		'target_warehouse',
		user=user,
	)


def get_material_transfer_permission_query(user, doctype=None):
	return build_warehouse_or_condition(
		'Material Transfer',
		'from_warehouse',
		'to_warehouse',
		user=user,
	)


def has_requisition_permission(doc, ptype='read', user=None, debug=False):
	if not user_has_warehouse_restrictions(user):
		return None
	return user_can_read_warehouse_doc(
		doc,
		'source_warehouse',
		'target_warehouse',
		user=user,
	)


def has_material_transfer_permission(doc, ptype='read', user=None, debug=False):
	if not user_has_warehouse_restrictions(user):
		return None
	return user_can_read_warehouse_doc(
		doc,
		'from_warehouse',
		'to_warehouse',
		user=user,
	)
