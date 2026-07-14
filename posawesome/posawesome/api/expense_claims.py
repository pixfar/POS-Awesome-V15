# Copyright (c) 2026, POS Awesome and contributors
# For license information, please see license.txt

import json

import erpnext
import frappe
from frappe import _
from frappe.utils import flt, today

DEFAULT_MODE_OF_PAYMENT = 'Cash'
DEFAULT_PAYABLE_ACCOUNT = 'Creditors - BSP'


def _parse_json(value):
	if isinstance(value, str):
		return json.loads(value)
	return value


def _get_employee_for_user(user=None):
	user = user or frappe.session.user
	employee = frappe.db.get_value(
		'Employee',
		{'user_id': user, 'status': 'Active'},
		['name', 'employee_name', 'company', 'department', 'expense_approver'],
		as_dict=True,
	)
	if not employee:
		frappe.throw(
			_('No active Employee record is linked to your user account. Please contact your administrator.'),
			title=_('Employee Not Found'),
		)
	return employee


@frappe.whitelist()
def get_current_employee():
	"""Employee record linked to the logged-in POS user, used to prefill the Expense form."""
	return _get_employee_for_user()


@frappe.whitelist()
def get_expense_claim_types():
	return frappe.get_all(
		'Expense Claim Type',
		fields=['name'],
		order_by='name asc',
		ignore_permissions=True,
	)


@frappe.whitelist()
def create_expense_claim(data):
	"""Create and submit an Expense Claim for the logged-in POS user's Employee record."""
	data = _parse_json(data)
	if not data:
		frappe.throw(_('Expense data is required.'))

	rows = data.get('expenses') or []
	if not rows:
		frappe.throw(_('Add at least one expense.'), title=_('Expenses Required'))

	employee = _get_employee_for_user()
	expense_date = data.get('expense_date') or today()

	doc = frappe.new_doc('Expense Claim')
	doc.employee = employee.name
	doc.company = employee.company
	if employee.department:
		doc.department = employee.department
	if employee.expense_approver:
		doc.expense_approver = employee.expense_approver

	doc.posting_date = expense_date
	doc.approval_status = 'Approved'
	doc.is_paid = 1
	doc.mode_of_payment = DEFAULT_MODE_OF_PAYMENT
	doc.payable_account = DEFAULT_PAYABLE_ACCOUNT
	doc.remark = data.get('remark')

	default_cost_center = erpnext.get_default_cost_center(employee.company)

	for row in rows:
		amount = flt(row.get('amount'))
		if amount <= 0:
			continue
		sanctioned_amount = row.get('sanctioned_amount')
		doc.append('expenses', {
			'expense_date': expense_date,
			'expense_type': row.get('expense_type'),
			'description': row.get('description'),
			'amount': amount,
			'sanctioned_amount': flt(sanctioned_amount) if sanctioned_amount not in (None, '') else amount,
			'cost_center': default_cost_center,
		})

	if not doc.expenses:
		frappe.throw(_('Add at least one expense with an amount.'), title=_('Expenses Required'))

	doc.insert(ignore_permissions=True)
	doc.submit()

	return {
		'name': doc.name,
		'status': doc.status,
		'grand_total': doc.grand_total,
	}


@frappe.whitelist()
def get_expense_claims_list(page_start=0, page_length=20, from_date=None, to_date=None, search=None):
	"""Paginated list of the logged-in user's own Expense Claims."""
	page_start = max(0, int(page_start or 0))
	page_length = max(1, min(int(page_length or 20), 100))

	employee = _get_employee_for_user()

	filters = {'employee': employee.name}
	if from_date and to_date:
		filters['posting_date'] = ['between', [from_date, to_date]]
	elif from_date:
		filters['posting_date'] = ['>=', from_date]
	elif to_date:
		filters['posting_date'] = ['<=', to_date]

	or_filters = None
	if search and len(search.strip()) >= 2:
		like = f'%{search.strip()}%'
		or_filters = {'name': ['like', like], 'remark': ['like', like]}

	fields = [
		'name',
		'posting_date',
		'remark',
		'approval_status',
		'status',
		'total_claimed_amount',
		'total_sanctioned_amount',
		'grand_total',
		'is_paid',
		'docstatus',
	]

	rows = frappe.get_all(
		'Expense Claim',
		filters=filters,
		or_filters=or_filters,
		fields=fields,
		order_by='posting_date desc, creation desc',
		start=page_start,
		page_length=page_length,
		ignore_permissions=True,
	)

	total = frappe.get_all(
		'Expense Claim',
		filters=filters,
		or_filters=or_filters,
		fields=['count(name) as total'],
		ignore_permissions=True,
	)[0].total

	return {
		'expense_claims': rows,
		'total': total,
		'has_more': (page_start + page_length) < total,
	}


@frappe.whitelist()
def get_expense_claim_detail(expense_claim):
	employee = _get_employee_for_user()
	doc = frappe.get_doc('Expense Claim', expense_claim)
	if doc.employee != employee.name:
		frappe.throw(_('You are not permitted to view this Expense Claim.'), exc=frappe.PermissionError)

	return {
		'name': doc.name,
		'posting_date': doc.posting_date,
		'employee': doc.employee,
		'employee_name': doc.employee_name,
		'approval_status': doc.approval_status,
		'status': doc.status,
		'is_paid': doc.is_paid,
		'mode_of_payment': doc.mode_of_payment,
		'payable_account': doc.payable_account,
		'remark': doc.remark,
		'total_claimed_amount': flt(doc.total_claimed_amount),
		'total_sanctioned_amount': flt(doc.total_sanctioned_amount),
		'grand_total': flt(doc.grand_total),
		'expenses': [
			{
				'expense_date': row.expense_date,
				'expense_type': row.expense_type,
				'description': row.description,
				'amount': flt(row.amount),
				'sanctioned_amount': flt(row.sanctioned_amount),
			}
			for row in doc.expenses
		],
	}
