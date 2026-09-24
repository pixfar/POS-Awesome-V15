# Copyright (c) 2026, POS Awesome and contributors
# For license information, please see license.txt

"""POS Awesome screens for bsp_engineering's Molding (piece-rate) Salary System:
Molding Daily Production and Molding Weekly Wastage.

The doctypes, their wage/penalty maths and the Additional Salary side effects
all live in bsp_engineering -- this module only builds/reads those documents
for the POS UI. Access follows the same role split as the rest of POS Awesome:
System Manager / BSP Admin can create and cancel, BSP Viewer can only view.
"""

import json

import frappe
from frappe import _
from frappe.utils import flt, getdate, today

from posawesome.posawesome.utils.warehouse_doc_permissions import (
	ensure_can_create,
	is_privileged_invoice_viewer,
	is_read_only_viewer,
)

DAILY_PRODUCTION = 'Molding Daily Production'
WEEKLY_WASTAGE = 'Molding Weekly Wastage'


def _parse_json(value):
	if isinstance(value, str):
		return json.loads(value)
	return value


def _ensure_can_view():
	if not (is_privileged_invoice_viewer() or is_read_only_viewer()):
		frappe.throw(_('You are not permitted to view Molding records.'), exc=frappe.PermissionError)


def _ensure_can_manage(action_label):
	ensure_can_create(action_label)
	if not is_privileged_invoice_viewer():
		frappe.throw(
			_('Only a System Manager or BSP Admin can {0}.').format(action_label),
			exc=frappe.PermissionError,
		)


def _status(docstatus):
	return {0: 'Draft', 1: 'Submitted', 2: 'Cancelled'}.get(docstatus, 'Draft')


def _list(doctype, fields, date_field, from_date=None, to_date=None, search=None, page_start=0, page_length=100):
	page_start = max(0, int(page_start or 0))
	page_length = max(1, min(int(page_length or 100), 200))

	filters = [[doctype, 'docstatus', 'in', [0, 1, 2]]]
	if from_date:
		filters.append([doctype, date_field, '>=', getdate(from_date)])
	if to_date:
		filters.append([doctype, date_field, '<=', getdate(to_date)])
	or_filters = [[doctype, 'name', 'like', f'%{search.strip()}%']] if search and search.strip() else None

	rows = frappe.get_all(
		doctype,
		filters=filters,
		or_filters=or_filters,
		fields=fields,
		order_by=f'{date_field} desc, modified desc',
		limit_start=page_start,
		limit_page_length=page_length,
		ignore_permissions=True,
	)
	total = len(
		frappe.get_all(doctype, filters=filters, or_filters=or_filters, pluck='name', ignore_permissions=True)
	)
	for row in rows:
		row['status'] = _status(row.docstatus)
	return rows, total


def _cancel(doctype, name):
	_ensure_can_manage(_('cancel a {0}').format(_(doctype)))
	doc = frappe.get_doc(doctype, name)
	if doc.docstatus != 1:
		frappe.throw(_('Only a submitted document can be cancelled.'))
	doc.flags.ignore_permissions = True
	doc.cancel()
	return {'name': doc.name, 'status': _status(doc.docstatus)}


def _owner_name(doc):
	return frappe.db.get_value('User', doc.owner, 'full_name') or doc.owner


# ---------------------------------------------------------------------------
# Molding Daily Production
# ---------------------------------------------------------------------------


@frappe.whitelist()
def get_default_rate_per_kg():
	_ensure_can_view()
	meta = frappe.get_meta(DAILY_PRODUCTION)
	return flt(meta.get_field('rate_per_kg').default or 0)


@frappe.whitelist()
def fetch_attendance(date):
	"""Employees marked Present on `date`, with their Molding Point."""
	_ensure_can_manage(_('create a Molding Daily Production'))
	from bsp_engineering.bsp_engineering.doctype.molding_daily_production.molding_daily_production import (
		fetch_attendance as _fetch_attendance,
	)

	return _fetch_attendance(date)


@frappe.whitelist()
def search_employees(search_text=None, limit=20):
	"""Active employees with their Molding Point, to add a worker manually."""
	_ensure_can_manage(_('create a Molding Daily Production'))
	limit = max(1, min(int(limit or 20), 50))
	or_filters = None
	if search_text and len(search_text.strip()) >= 2:
		like = f'%{search_text.strip()}%'
		or_filters = {'name': ['like', like], 'employee_name': ['like', like]}

	rows = frappe.get_all(
		'Employee',
		filters={'status': 'Active'},
		or_filters=or_filters,
		fields=['name as employee', 'employee_name', 'custom_molding_point as point'],
		order_by='employee_name asc',
		limit_page_length=limit,
		ignore_permissions=True,
	)
	for row in rows:
		row['point'] = flt(row.point)
	return rows


@frappe.whitelist()
def create_daily_production(data):
	_ensure_can_manage(_('create a Molding Daily Production'))
	data = _parse_json(data) or {}

	if flt(data.get('total_work_kg')) <= 0:
		frappe.throw(_('Total Work (KG) must be greater than zero.'))

	doc = frappe.new_doc(DAILY_PRODUCTION)
	doc.date = data.get('date') or today()
	if data.get('rate_per_kg') not in (None, ''):
		doc.rate_per_kg = flt(data.get('rate_per_kg'))
	doc.total_work_kg = flt(data.get('total_work_kg'))

	seen = set()
	for row in data.get('present_employees') or []:
		employee = row.get('employee')
		if not employee or employee in seen:
			continue
		seen.add(employee)
		doc.append('present_employees', {'employee': employee, 'point': flt(row.get('point'))})

	if not doc.present_employees:
		frappe.throw(_('Add at least one present employee.'), title=_('Employees Required'))

	doc.insert(ignore_permissions=True)
	doc.flags.ignore_permissions = True
	doc.submit()

	return {'name': doc.name, 'status': _status(doc.docstatus)}


@frappe.whitelist()
def get_daily_production_list(from_date=None, to_date=None, search=None, page_start=0, page_length=100):
	_ensure_can_view()
	rows, total = _list(
		DAILY_PRODUCTION,
		['name', 'date', 'rate_per_kg', 'total_work_kg', 'total_wage', 'docstatus', 'modified'],
		'date',
		from_date=from_date,
		to_date=to_date,
		search=search,
		page_start=page_start,
		page_length=page_length,
	)

	counts = {}
	if rows:
		for parent, count in frappe.get_all(
			'Molding Daily Production Detail',
			filters={'parent': ['in', [row.name for row in rows]], 'parenttype': DAILY_PRODUCTION},
			fields=['parent', 'count(name) as count'],
			group_by='parent',
			as_list=True,
			ignore_permissions=True,
		):
			counts[parent] = count
	for row in rows:
		row['employee_count'] = counts.get(row.name, 0)

	return {'records': rows, 'total': total}


@frappe.whitelist()
def get_daily_production_detail(name):
	_ensure_can_view()
	doc = frappe.get_doc(DAILY_PRODUCTION, name)
	total_points = sum(flt(row.point) for row in doc.present_employees)
	return {
		'name': doc.name,
		'date': doc.date,
		'rate_per_kg': flt(doc.rate_per_kg),
		'total_work_kg': flt(doc.total_work_kg),
		'total_wage': flt(doc.total_wage),
		'total_points': flt(total_points),
		'per_point_rate': flt(doc.total_wage) / total_points if total_points else 0,
		'docstatus': doc.docstatus,
		'status': _status(doc.docstatus),
		'created_by': _owner_name(doc),
		'creation': doc.creation,
		'amended_from': doc.get('amended_from'),
		'present_employees': [
			{
				'employee': row.employee,
				'employee_name': row.employee_name,
				'point': flt(row.point),
				'daily_salary': flt(row.daily_salary),
			}
			for row in doc.present_employees
		],
	}


@frappe.whitelist()
def cancel_daily_production(name):
	return _cancel(DAILY_PRODUCTION, name)


# ---------------------------------------------------------------------------
# Molding Weekly Wastage
# ---------------------------------------------------------------------------


@frappe.whitelist()
def fetch_weekly_data(start_date, end_date):
	"""Total work (KG) of submitted Daily Productions in the period, plus the
	per-employee points the penalty would be split by -- shown as a preview
	before submitting."""
	_ensure_can_manage(_('create a Molding Weekly Wastage'))
	from bsp_engineering.bsp_engineering.doctype.molding_weekly_wastage.molding_weekly_wastage import (
		fetch_weekly_data as _fetch_weekly_data,
		get_weekly_points,
	)

	result = _fetch_weekly_data(start_date, end_date)
	points = get_weekly_points(start_date, end_date)
	names = dict(
		frappe.get_all(
			'Employee',
			filters={'name': ['in', list(points)]},
			fields=['name', 'employee_name'],
			as_list=True,
		)
	) if points else {}
	result['employee_points'] = [
		{'employee': employee, 'employee_name': names.get(employee), 'points': flt(total)}
		for employee, total in sorted(points.items(), key=lambda kv: names.get(kv[0]) or kv[0])
	]
	return result


@frappe.whitelist()
def create_weekly_wastage(data):
	_ensure_can_manage(_('create a Molding Weekly Wastage'))
	data = _parse_json(data) or {}

	start_date = data.get('start_date')
	end_date = data.get('end_date')
	if not (start_date and end_date):
		frappe.throw(_('Both Start Date and End Date are required.'))
	if data.get('actual_wastage_kg') in (None, '') or flt(data.get('actual_wastage_kg')) < 0:
		frappe.throw(_('Actual Wastage (KG) is required.'))

	from bsp_engineering.bsp_engineering.doctype.molding_weekly_wastage.molding_weekly_wastage import (
		fetch_weekly_data as _fetch_weekly_data,
	)

	doc = frappe.new_doc(WEEKLY_WASTAGE)
	doc.start_date = start_date
	doc.end_date = end_date
	# Never trust the client's total -- recompute from submitted Daily Productions.
	doc.total_weekly_work_kg = _fetch_weekly_data(start_date, end_date)['total_weekly_work_kg']
	doc.actual_wastage_kg = flt(data.get('actual_wastage_kg'))
	doc.insert(ignore_permissions=True)
	doc.flags.ignore_permissions = True
	doc.submit()

	return {'name': doc.name, 'status': _status(doc.docstatus)}


@frappe.whitelist()
def get_weekly_wastage_list(from_date=None, to_date=None, search=None, page_start=0, page_length=100):
	_ensure_can_view()
	rows, total = _list(
		WEEKLY_WASTAGE,
		[
			'name',
			'start_date',
			'end_date',
			'total_weekly_work_kg',
			'allowed_wastage_kg',
			'actual_wastage_kg',
			'excess_wastage_kg',
			'penalty_amount',
			'docstatus',
			'modified',
		],
		'start_date',
		from_date=from_date,
		to_date=to_date,
		search=search,
		page_start=page_start,
		page_length=page_length,
	)
	return {'records': rows, 'total': total}


@frappe.whitelist()
def get_weekly_wastage_detail(name):
	_ensure_can_view()
	doc = frappe.get_doc(WEEKLY_WASTAGE, name)

	deductions = frappe.get_all(
		'Additional Salary',
		filters={'ref_doctype': WEEKLY_WASTAGE, 'ref_docname': doc.name, 'docstatus': ['!=', 2]},
		fields=['name', 'employee', 'employee_name', 'amount', 'payroll_date'],
		order_by='employee_name asc',
		ignore_permissions=True,
	)

	return {
		'name': doc.name,
		'start_date': doc.start_date,
		'end_date': doc.end_date,
		'total_weekly_work_kg': flt(doc.total_weekly_work_kg),
		'allowed_wastage_kg': flt(doc.allowed_wastage_kg),
		'actual_wastage_kg': flt(doc.actual_wastage_kg),
		'excess_wastage_kg': flt(doc.excess_wastage_kg),
		'penalty_amount': flt(doc.penalty_amount),
		'docstatus': doc.docstatus,
		'status': _status(doc.docstatus),
		'created_by': _owner_name(doc),
		'creation': doc.creation,
		'amended_from': doc.get('amended_from'),
		'deductions': [
			{
				'additional_salary': row.name,
				'employee': row.employee,
				'employee_name': row.employee_name,
				'amount': flt(row.amount),
				'payroll_date': row.payroll_date,
			}
			for row in deductions
		],
	}


@frappe.whitelist()
def cancel_weekly_wastage(name):
	return _cancel(WEEKLY_WASTAGE, name)
