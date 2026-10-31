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
BSP_ADMIN_ROLE = 'BSP Admin'
BSP_VIEWER_ROLE = 'BSP Viewer'


def is_system_manager(user=None):
	user = user or frappe.session.user
	return user == 'Administrator' or SYSTEM_MANAGER_ROLE in frappe.get_roles(user)


def is_privileged_invoice_viewer(user=None):
	"""System Manager or BSP Admin may see every Sales/Purchase Invoice
	regardless of who created it or which warehouse it touches."""
	user = user or frappe.session.user
	if user == 'Administrator' or is_system_manager(user):
		return True
	return BSP_ADMIN_ROLE in frappe.get_roles(user)


def is_read_only_viewer(user=None):
	"""True when this user holds BSP Viewer -- view/report/export/print
	everything, create nothing (see the Custom DocPerm fixture granting that
	role read/report/export/print/email=1 and nothing else on every
	transaction doctype). System Manager/Administrator always pass through,
	matching every other override in this module, in case someone is ever
	given both roles."""
	user = user or frappe.session.user
	if user == 'Administrator' or is_system_manager(user):
		return False
	return BSP_VIEWER_ROLE in frappe.get_roles(user)


def ensure_can_create(action_label):
	"""Raise PermissionError if this user is a read-only BSP Viewer.

	POS Awesome's own creation endpoints generally set
	ignore_permissions=True on the documents they build (the cashier/staff
	creating a Sales Invoice etc. doesn't necessarily hold the underlying
	DocType's own "create" permission -- POS Profile/warehouse assignment is
	the real authorization boundary there), which means Frappe's own
	DocType-permission check -- BSP Viewer's create=0 -- never gets a chance
	to run. Call this explicitly at the top of every such entrypoint instead.

	`action_label` is a short verb phrase completing "cannot {label}", e.g.
	"create a Sales Invoice".
	"""
	if is_read_only_viewer():
		frappe.throw(
			_('BSP Viewer is a read-only role and cannot {0}.').format(action_label),
			frappe.PermissionError,
		)


def _has_warehouse_user_permission(user=None):
	user = user or frappe.session.user
	if user == 'Administrator':
		return False
	return bool(
		frappe.db.exists(
			'User Permission',
			{'user': user, 'allow': 'Warehouse'},
		)
	)


def user_has_warehouse_restrictions(user=None):
	"""Whether Material Transfer/Requisition access should be narrowed to this
	user's permitted warehouse(s) via build_warehouse_or_condition() below.

	True for:
	- anyone with an explicit Warehouse User Permission (including BSP Admin /
	  System Manager / BSP Viewer — those roles otherwise see every showroom)
	- anyone who isn't privileged / BSP Viewer (POS Profile–based scoping)

	False for Administrator and for privileged / BSP Viewer users with no
	Warehouse User Permission. get_expanded_permitted_warehouses() is the
	source of truth for *which* warehouse(s) that then permits."""
	user = user or frappe.session.user
	if user == 'Administrator':
		return False
	if _has_warehouse_user_permission(user):
		return True
	return not (is_privileged_invoice_viewer(user) or is_read_only_viewer(user))


def get_expanded_permitted_warehouses(user=None):
	"""None means unrestricted (every warehouse); an empty/populated list
	means scoped to exactly those.

	Warehouse User Permissions always win — even for System Manager / BSP
	Admin / BSP Viewer. Without those rows, privileged / BSP Viewer users
	remain unrestricted (management oversight across every showroom).
	Everyone else is scoped through bsp_engineering.utils.pos_warehouse
	(POS Profile / User Permission resolution).
	"""
	user = user or frappe.session.user

	if _has_warehouse_user_permission(user):
		try:
			from bsp_engineering.utils.pos_warehouse import (
				get_user_permission_warehouse_names,
			)

			# include_groups=True so OR-filters on linked docs also match
			# parent/group warehouses that appear on older records.
			names = get_user_permission_warehouse_names(
				user=user, include_groups=True
			)
			return list(names or [])
		except Exception:
			names = frappe.get_all(
				'User Permission',
				filters={'user': user, 'allow': 'Warehouse'},
				pluck='for_value',
			)
			expanded = set()
			for name in names or []:
				if not name:
					continue
				expanded.add(name)
				if frappe.db.get_value('Warehouse', name, 'is_group'):
					expanded.update(
						frappe.db.get_descendants('Warehouse', name) or []
					)
			return list(expanded)

	if is_privileged_invoice_viewer(user) or is_read_only_viewer(user):
		return None

	try:
		from bsp_engineering.utils.pos_warehouse import get_permitted_warehouse_names

		names = get_permitted_warehouse_names() or []
	except Exception:
		names = []

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


def get_permission_scoped_names(doctype, warehouse_field, owner_field='owner', user=None):
	"""Legacy helper that materializes every visible doc name.

	Do **not** use this for list/count queries — a warehouse-restricted user
	can own thousands of invoices, and ``name IN (…thousands…)`` makes the
	list page hang. Prefer ``apply_list_warehouse_scope`` (indexed warehouse
	filter) or ``user_can_access_warehouse_scoped_doc`` (single-doc check).

	Returns None when unrestricted, else the name list (possibly empty).
	"""
	user = user or frappe.session.user
	permitted = get_expanded_permitted_warehouses(user)
	if permitted is None:
		return None

	or_filters = [[doctype, owner_field, '=', user]]
	if permitted:
		or_filters.append([doctype, warehouse_field, 'in', permitted])

	return frappe.get_all(
		doctype,
		or_filters=or_filters,
		pluck='name',
		limit_page_length=0,
		ignore_permissions=True,
	)


def apply_list_warehouse_scope(
	filters,
	doctype,
	warehouse_field,
	owner_field='owner',
	user=None,
	mine_only=False,
):
	"""Append cheap list filters for warehouse-scoped users.

	Uses ``set_warehouse IN (permitted)`` (indexed) instead of materializing
	every visible document name. Unrestricted users (no Warehouse User
	Permission / privileged without UP) get no extra filter.
	"""
	user = user or frappe.session.user
	if mine_only:
		filters.append([doctype, owner_field, '=', user])
		return

	permitted = get_expanded_permitted_warehouses(user)
	if permitted is None:
		return
	if permitted:
		filters.append([doctype, warehouse_field, 'in', list(permitted)])
	else:
		# No usable warehouse — only their own docs.
		filters.append([doctype, owner_field, '=', user])


def apply_dict_warehouse_scope(
	filters,
	warehouse_field,
	owner_field='owner',
	user=None,
):
	"""Dict-filter variant of apply_list_warehouse_scope (get_all style)."""
	user = user or frappe.session.user
	permitted = get_expanded_permitted_warehouses(user)
	if permitted is None:
		return
	if permitted:
		filters[warehouse_field] = ['in', list(permitted)]
	else:
		filters[owner_field] = user


def get_accounts_for_warehouses(warehouses):
	"""Cash/bank accounts mapped to the given warehouses (for Payment Entry)."""
	accounts = set()
	if not warehouses:
		return []
	try:
		from bsp_engineering.utils.warehouse_accounts import get_accounts_for_warehouse
	except ImportError:
		return []
	for warehouse in warehouses:
		for account in get_accounts_for_warehouse(warehouse) or []:
			if account:
				accounts.add(account)
	return list(accounts)


def apply_payment_entry_warehouse_scope(
	filters,
	or_filters,
	doctype='Payment Entry',
	user=None,
	mine_only=False,
):
	"""Scope Payment Entry lists by warehouse match.

	A row is visible when ``custom_warehouse`` is permitted, or when
	``paid_from`` / ``paid_to`` is a cash account belonging to a permitted
	warehouse. ``mine_only`` still locks to the session user.
	"""
	user = user or frappe.session.user
	if mine_only:
		filters.append([doctype, 'owner', '=', user])
		return filters, or_filters

	permitted = get_expanded_permitted_warehouses(user)
	if permitted is None:
		return filters, or_filters
	if not permitted:
		filters.append([doctype, 'owner', '=', user])
		return filters, or_filters

	accounts = get_accounts_for_warehouses(permitted)
	warehouse_or = [[doctype, 'custom_warehouse', 'in', list(permitted)]]
	if accounts:
		warehouse_or.append([doctype, 'paid_from', 'in', accounts])
		warehouse_or.append([doctype, 'paid_to', 'in', accounts])

	if or_filters:
		# get_list can't nest two OR groups — fall back to warehouse field.
		filters.append([doctype, 'custom_warehouse', 'in', list(permitted)])
		return filters, or_filters
	return filters, warehouse_or


def user_can_access_payment_entry(name, user=None):
	"""Payment Entry detail access: unrestricted, owner, warehouse, or account."""
	user = user or frappe.session.user
	permitted = get_expanded_permitted_warehouses(user)
	if permitted is None:
		return True
	row = frappe.db.get_value(
		'Payment Entry',
		name,
		['owner', 'custom_warehouse', 'paid_from', 'paid_to'],
		as_dict=True,
	)
	if not row:
		return False
	if row.owner == user:
		return True
	allowed = set(permitted or [])
	if row.custom_warehouse and row.custom_warehouse in allowed:
		return True
	accounts = set(get_accounts_for_warehouses(permitted))
	return bool(
		(row.paid_from and row.paid_from in accounts)
		or (row.paid_to and row.paid_to in accounts)
	)


def user_can_access_warehouse_scoped_doc(
	doctype,
	name,
	warehouse_field,
	owner_field='owner',
	user=None,
):
	"""Single-document visibility check matching list warehouse scope."""
	user = user or frappe.session.user
	permitted = get_expanded_permitted_warehouses(user)
	if permitted is None:
		return True
	row = frappe.db.get_value(
		doctype, name, [owner_field, warehouse_field], as_dict=True
	)
	if not row:
		return False
	if row.get(owner_field) == user:
		return True
	return bool(row.get(warehouse_field) and row.get(warehouse_field) in set(permitted))


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
	do_number=None,
	remarks=None,
	search=None,
	search_fields=None,
	include_cancelled=False,
	include_draft=False,
):
	"""Build the shared WHERE conditions/values for warehouse-scoped doc list queries.

	The main table must be aliased as `main` by the caller so the item EXISTS
	subquery below can reference `main.name`.

	include_cancelled=True also matches docstatus=2 records — for doctypes (like
	Material Transfer's Rejected flow) where cancelling is a normal terminal status
	that should still show up in the list, not just submitted ones.

	include_draft=True also matches docstatus=0 records, so a Draft row stays
	visible (and deletable) instead of disappearing before it's ever submitted.
	"""
	docstatuses = [1]
	if include_draft:
		docstatuses.append(0)
	if include_cancelled:
		docstatuses.append(2)
	conditions = [f"main.docstatus IN ({', '.join(str(d) for d in docstatuses)})"]
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

	# Doctype-specific column, so only apply this when the doctype actually
	# carries a DO Number (Material Transfer today; Requisition doesn't).
	if do_number and frappe.db.has_column(doctype, 'custom_do_number'):
		conditions.append('main.custom_do_number LIKE %(do_number)s')
		values['do_number'] = f'%{do_number}%'

	if remarks:
		remarks_conds = []
		if frappe.db.has_column(doctype, 'remarks'):
			remarks_conds.append('main.remarks LIKE %(remarks)s')
		if frappe.db.has_column(doctype, 'notes'):
			remarks_conds.append('main.notes LIKE %(remarks)s')
		if remarks_conds:
			conditions.append('(' + ' OR '.join(remarks_conds) + ')')
			values['remarks'] = f'%{remarks}%'

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
	do_number=None,
	remarks=None,
	search=None,
	search_fields=None,
	include_cancelled=False,
	include_draft=False,
	order_by='main.creation DESC',
):
	"""``order_by`` is a fixed SQL fragment chosen by the calling endpoint
	(never user input), using the ``main`` table alias."""
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
		do_number=do_number,
		remarks=remarks,
		search=search,
		search_fields=search_fields,
		include_cancelled=include_cancelled,
		include_draft=include_draft,
	)
	where_clause = ' AND '.join(conditions)
	table = f'`tab{doctype}`'
	field_sql = ', '.join(f'main.{field}' for field in fields)

	rows = frappe.db.sql(
		f"""
		SELECT {field_sql}
		FROM {table} AS main
		WHERE {where_clause}
		ORDER BY {order_by}
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
	do_number=None,
	remarks=None,
	search=None,
	search_fields=None,
	include_cancelled=False,
	include_draft=False,
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
		do_number=do_number,
		remarks=remarks,
		search=search,
		search_fields=search_fields,
		include_cancelled=include_cancelled,
		include_draft=include_draft,
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


# ---------------------------------------------------------------------------
# Stock Entry
# ---------------------------------------------------------------------------
# A showroom transfer passes through "Goods In Transit - BSP" (or names the
# other showroom), so plain User Permissions -- which demand that *every*
# warehouse on the document be permitted -- locked showroom users out of
# their own stock entries. Stock Entry's warehouse fields carry
# ignore_user_permissions (bsp_engineering fixtures) and these hooks apply
# the source-OR-target rule instead.
#
# Only users restricted by a Warehouse User Permission are scoped here;
# everyone else (System Manager / BSP Admin / BSP Viewer, and users with no
# Warehouse User Permission such as Store Room or manufacturing staff) keeps
# exactly the access they had before.

STOCK_ENTRY_ACTION_PTYPES = frozenset({'create', 'write', 'submit', 'cancel', 'amend', 'delete'})


def get_stock_entry_warehouses(user=None):
	"""Warehouses a restricted user may act on for Stock Entry: their Warehouse
	User Permission(s) plus their POS Profile warehouse(s), including child
	warehouses of any group. None means not restricted (unchanged access).

	Warehouse User Permissions also restrict System Manager / BSP Admin /
	BSP Viewer; without those rows those roles stay unrestricted."""
	user = user or frappe.session.user
	if user == 'Administrator':
		return None

	permitted = frappe.db.sql_list(
		"""
		SELECT for_value FROM `tabUser Permission`
		WHERE user = %(user)s AND allow = 'Warehouse'
			AND (apply_to_all_doctypes = 1 OR applicable_for = 'Stock Entry')
		""",
		{'user': user},
	)
	if not permitted:
		# No Warehouse UP → privileged / everyone else keep prior access.
		return None

	profile_warehouses = frappe.db.sql_list(
		"""
		SELECT DISTINCT pp.warehouse FROM `tabPOS Profile User` pu
		INNER JOIN `tabPOS Profile` pp ON pp.name = pu.parent
		WHERE pu.user = %(user)s AND pp.disabled = 0 AND IFNULL(pp.warehouse, '') != ''
		""",
		{'user': user},
	)

	warehouses = set()
	for name in [*permitted, *profile_warehouses]:
		if not name:
			continue
		warehouses.add(name)
		if frappe.db.get_value('Warehouse', name, 'is_group'):
			warehouses.update(frappe.db.get_descendants('Warehouse', name) or [])
	return sorted(warehouses)


def _stock_entry_warehouse_sides(doc):
	sources = {doc.get('from_warehouse')}
	targets = {doc.get('to_warehouse')}
	for row in doc.get('items') or []:
		sources.add(row.get('s_warehouse'))
		targets.add(row.get('t_warehouse'))
	return sources - {None, ''}, targets - {None, ''}


def get_stock_entry_permission_query(user=None, doctype=None):
	warehouses = get_stock_entry_warehouses(user)
	if warehouses is None:
		return ''
	in_list = _sql_in_list(warehouses)
	return (
		f'(`tabStock Entry`.from_warehouse in {in_list}'
		f' or `tabStock Entry`.to_warehouse in {in_list}'
		' or exists (select 1 from `tabStock Entry Detail` sed'
		' where sed.parent = `tabStock Entry`.name and sed.parenttype = \'Stock Entry\''
		f' and (sed.s_warehouse in {in_list} or sed.t_warehouse in {in_list})))'
	)


def has_stock_entry_permission(doc, ptype='read', user=None, debug=False):
	"""View: any source or target warehouse is the user's. Create/edit/submit/
	cancel: every source warehouse is the user's (or, with no source, every
	target) -- stock can be sent out of the user's warehouse but never pulled
	in from someone else's."""
	warehouses = get_stock_entry_warehouses(user)
	if warehouses is None:
		return None
	allowed = set(warehouses)
	sources, targets = _stock_entry_warehouse_sides(doc)

	if ptype in STOCK_ENTRY_ACTION_PTYPES:
		if sources:
			return sources <= allowed
		if targets:
			return targets <= allowed
		# Nothing set yet (a blank new form) -- the real check runs on save.
		return True

	return bool((sources | targets) & allowed)
