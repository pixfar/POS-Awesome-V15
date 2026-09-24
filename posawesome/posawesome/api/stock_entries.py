# Copyright (c) 2026, POS Awesome and contributors
# For license information, please see license.txt

"""POS Awesome screens for ERPNext Stock Entries of purpose Material Issue
(stock out of a warehouse) and Material Receipt (stock into a warehouse).

System Manager / BSP Admin can create and cancel; BSP Viewer can only view.
Item search and on-hand qty reuse material_transfers.search_items and
material_transfers.get_stock_qty.
"""

import json

import frappe
from frappe import _
from frappe.utils import flt, today

from posawesome.posawesome.utils.warehouse_doc_permissions import (
	ensure_can_create,
	is_privileged_invoice_viewer,
	is_read_only_viewer,
)

MATERIAL_ISSUE = 'Material Issue'
MATERIAL_RECEIPT = 'Material Receipt'
PURPOSES = (MATERIAL_ISSUE, MATERIAL_RECEIPT)


def _parse_json(value):
	if isinstance(value, str):
		return json.loads(value)
	return value


def _validate_purpose(purpose):
	if purpose not in PURPOSES:
		frappe.throw(_('Invalid purpose {0}.').format(purpose))


def _ensure_can_view():
	if not (is_privileged_invoice_viewer() or is_read_only_viewer()):
		frappe.throw(_('You are not permitted to view Stock Entries.'), exc=frappe.PermissionError)


def _ensure_can_manage(action_label):
	ensure_can_create(action_label)
	if not is_privileged_invoice_viewer():
		frappe.throw(
			_('Only a System Manager or BSP Admin can {0}.').format(action_label),
			exc=frappe.PermissionError,
		)


def _status(docstatus):
	return {0: 'Draft', 1: 'Submitted', 2: 'Cancelled'}.get(docstatus, 'Draft')


@frappe.whitelist()
def create_stock_entry(purpose, data):
	"""Create and submit a Material Issue (source warehouse) or Material
	Receipt (target warehouse) Stock Entry."""
	_validate_purpose(purpose)
	_ensure_can_manage(_('create a {0}').format(_(purpose)))
	data = _parse_json(data) or {}

	warehouse = data.get('warehouse')
	if not warehouse:
		frappe.throw(_('Warehouse is required.'), title=_('Warehouse Required'))

	company = frappe.db.get_value('Warehouse', warehouse, 'company')
	if not company:
		frappe.throw(_('Warehouse {0} has no Company set.').format(warehouse))

	is_issue = purpose == MATERIAL_ISSUE
	doc = frappe.new_doc('Stock Entry')
	doc.stock_entry_type = purpose
	doc.purpose = purpose
	doc.company = company
	doc.posting_date = data.get('posting_date') or today()
	doc.set_posting_time = 1
	doc.remarks = (data.get('remarks') or '').strip() or None
	if is_issue:
		doc.from_warehouse = warehouse
	else:
		doc.to_warehouse = warehouse

	for row in data.get('items') or []:
		if not row.get('item_code') or flt(row.get('qty')) <= 0:
			continue
		item = {
			'item_code': row.get('item_code'),
			'qty': flt(row.get('qty')),
			's_warehouse': warehouse if is_issue else None,
			't_warehouse': None if is_issue else warehouse,
		}
		# Stock Entry doesn't fill uom/conversion_factor server-side (Desk's
		# form does it client-side) -- without them transfer_qty and every
		# value total come out as 0.
		stock_uom = frappe.db.get_value('Item', row.get('item_code'), 'stock_uom')
		uom = row.get('uom') or stock_uom
		conversion_factor = 1
		if uom != stock_uom:
			conversion_factor = flt(
				frappe.db.get_value(
					'UOM Conversion Detail',
					{'parent': row.get('item_code'), 'uom': uom},
					'conversion_factor',
				)
			)
			if not conversion_factor:
				frappe.throw(_('No UOM conversion for {0} in item {1}.').format(uom, row.get('item_code')))
		item.update({'uom': uom, 'stock_uom': stock_uom, 'conversion_factor': conversion_factor})
		if not is_issue and flt(row.get('basic_rate')) > 0:
			# A non-zero basic_rate is kept by set_basic_rate(); don't use
			# set_basic_rate_manually, which also skips computing basic_amount.
			item['basic_rate'] = flt(row.get('basic_rate'))
		doc.append('items', item)

	if not doc.items:
		frappe.throw(_('Add at least one item with quantity.'), title=_('Items Required'))

	doc.flags.ignore_permissions = True
	doc.insert(ignore_permissions=True)
	doc.submit()
	return {'name': doc.name, 'status': _status(doc.docstatus)}


@frappe.whitelist()
def get_stock_entries_list(
	purpose,
	page_start=0,
	page_length=100,
	from_date=None,
	to_date=None,
	warehouse=None,
	remarks=None,
	search=None,
):
	"""Many entries (e.g. ones made in Desk) leave the header from/to
	warehouse blank and only set it per row, so the warehouse filter and the
	displayed warehouse both come from the Stock Entry Detail rows."""
	_validate_purpose(purpose)
	_ensure_can_view()
	page_start = max(0, int(page_start or 0))
	page_length = max(1, min(int(page_length or 100), 200))
	is_issue = purpose == MATERIAL_ISSUE
	row_warehouse = 's_warehouse' if is_issue else 't_warehouse'

	conditions = ['se.purpose = %(purpose)s', 'se.docstatus IN (0, 1, 2)']
	values = {'purpose': purpose}
	if from_date:
		conditions.append('se.posting_date >= %(from_date)s')
		values['from_date'] = from_date
	if to_date:
		conditions.append('se.posting_date <= %(to_date)s')
		values['to_date'] = to_date
	if warehouse:
		conditions.append(
			f"""EXISTS (SELECT 1 FROM `tabStock Entry Detail` d
			WHERE d.parent = se.name AND d.{row_warehouse} = %(warehouse)s)"""
		)
		values['warehouse'] = warehouse
	if remarks and remarks.strip():
		conditions.append('se.remarks LIKE %(remarks)s')
		values['remarks'] = f'%{remarks.strip()}%'
	if search and search.strip():
		conditions.append(
			f"""(se.name LIKE %(search)s OR se.remarks LIKE %(search)s OR EXISTS (
				SELECT 1 FROM `tabStock Entry Detail` d WHERE d.parent = se.name
				AND (d.item_code LIKE %(search)s OR d.item_name LIKE %(search)s
				OR d.{row_warehouse} LIKE %(search)s)))"""
		)
		values['search'] = f'%{search.strip()}%'
	where_clause = ' AND '.join(conditions)

	rows = frappe.db.sql(
		f"""
		SELECT se.name, se.posting_date, se.total_outgoing_value, se.total_incoming_value,
			se.remarks, se.owner, se.docstatus, se.modified
		FROM `tabStock Entry` se
		WHERE {where_clause}
		ORDER BY se.posting_date DESC, se.modified DESC
		LIMIT %(limit_start)s, %(limit_length)s
		""",
		{**values, 'limit_start': page_start, 'limit_length': page_length},
		as_dict=True,
	)
	total = frappe.db.sql(f'SELECT COUNT(*) FROM `tabStock Entry` se WHERE {where_clause}', values)[0][0]

	summary_by_parent = {}
	if rows:
		for summary in frappe.db.sql(
			f"""
			SELECT parent, SUM(qty) AS qty, COUNT(name) AS count,
				GROUP_CONCAT(DISTINCT {row_warehouse} ORDER BY {row_warehouse} SEPARATOR ', ') AS warehouses
			FROM `tabStock Entry Detail`
			WHERE parenttype = 'Stock Entry' AND parent IN %(parents)s
			GROUP BY parent
			""",
			{'parents': [row.name for row in rows]},
			as_dict=True,
		):
			summary_by_parent[summary.parent] = summary

	owner_names = dict(
		frappe.get_all(
			'User',
			filters={'name': ['in', list({row.owner for row in rows})]},
			fields=['name', 'full_name'],
			as_list=True,
		)
	) if rows else {}

	for row in rows:
		summary = summary_by_parent.get(row.name) or {}
		row['warehouse'] = summary.get('warehouses')
		row['total_qty'] = flt(summary.get('qty'))
		row['item_count'] = summary.get('count') or 0
		row['total_value'] = flt(row.total_outgoing_value if is_issue else row.total_incoming_value)
		row['status'] = _status(row.docstatus)
		row['created_by'] = owner_names.get(row.owner) or row.owner

	return {'records': rows, 'total': total}


@frappe.whitelist()
def get_stock_entry_detail(name):
	_ensure_can_view()
	doc = frappe.get_doc('Stock Entry', name)
	_validate_purpose(doc.purpose)
	is_issue = doc.purpose == MATERIAL_ISSUE

	items = [
		{
			'item_code': row.item_code,
			'item_name': row.item_name,
			'warehouse': row.s_warehouse if is_issue else row.t_warehouse,
			'qty': flt(row.qty),
			'uom': row.uom,
			'basic_rate': flt(row.basic_rate),
			'amount': flt(row.amount),
		}
		for row in doc.items
	]

	return {
		'name': doc.name,
		'purpose': doc.purpose,
		'posting_date': doc.posting_date,
		'posting_time': str(doc.posting_time or ''),
		'company': doc.company,
		'warehouse': ', '.join(sorted({item['warehouse'] for item in items if item['warehouse']})),
		'remarks': doc.remarks,
		'docstatus': doc.docstatus,
		'status': _status(doc.docstatus),
		'created_by': frappe.db.get_value('User', doc.owner, 'full_name') or doc.owner,
		'creation': doc.creation,
		'total_qty': flt(sum(flt(row.qty) for row in doc.items)),
		'total_value': flt(doc.total_outgoing_value if is_issue else doc.total_incoming_value),
		'item_count': len(doc.items),
		'items': items,
	}


@frappe.whitelist()
def cancel_stock_entry(name):
	doc = frappe.get_doc('Stock Entry', name)
	_validate_purpose(doc.purpose)
	_ensure_can_manage(_('cancel a {0}').format(_(doc.purpose)))
	if doc.docstatus != 1:
		frappe.throw(_('Only a submitted document can be cancelled.'))
	doc.flags.ignore_permissions = True
	doc.cancel()
	return {'name': doc.name, 'status': _status(doc.docstatus)}
