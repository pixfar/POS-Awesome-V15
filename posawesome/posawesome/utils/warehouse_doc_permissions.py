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
):
	page_start = max(0, int(page_start or 0))
	page_length = max(1, min(int(page_length or 20), 100))
	conditions = ['docstatus = 1']
	values = {}

	if extra_filters:
		for key, val in extra_filters.items():
			conditions.append(f'{key} = %({key})s')
			values[key] = val

	if int(mine_only or 0):
		conditions.append(f'{mine_field} = %(mine_user)s')
		values['mine_user'] = frappe.session.user
	else:
		warehouse_condition = build_warehouse_or_condition(
			doctype,
			source_field,
			target_field,
		)
		if warehouse_condition:
			conditions.append(warehouse_condition)

	where_clause = ' AND '.join(conditions)
	table = f'`tab{doctype}`'
	field_sql = ', '.join(fields)

	rows = frappe.db.sql(
		f"""
		SELECT {field_sql}
		FROM {table}
		WHERE {where_clause}
		ORDER BY modified DESC
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
		f'SELECT COUNT(*) FROM {table} WHERE {where_clause}',
		values,
	)
	total = count_result[0][0] if count_result else 0

	return rows, total


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
