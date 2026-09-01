# Copyright (c) 2026, POS Awesome and contributors
# For license information, please see license.txt

import json

import erpnext
import frappe
from frappe import _
from frappe.utils import flt, today

from posawesome.posawesome.utils.warehouse_doc_permissions import is_system_manager, ensure_can_create
from posawesome.posawesome.api.payment_processing.utils import get_pos_change_account

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
	ensure_can_create(_('create an Expense'))
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
	# Warehouse the expense is attributed to, for warehouse-wise cash summary
	# reporting -- same trust model as Material Transfer/Requisition/Daily
	# Deposit: the frontend already locks this to the user's permitted
	# warehouse for non-System-Manager users.
	if data.get('warehouse'):
		doc.custom_warehouse = data.get('warehouse')

	doc.posting_date = expense_date
	doc.approval_status = 'Approved'
	# is_paid=0: the claim only books the liability (Dr Expense / Cr Payable)
	# on submit. A separate Payment Entry below actually pays it out, so the
	# cash leg posts against the showroom's account_for_change_amount instead
	# of a generic mode-of-payment account.
	doc.is_paid = 0
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

	payment_entry = _pay_expense_claim(doc)
	doc.reload()  # payment_entry's on_submit hook updates status to Paid

	return {
		'name': doc.name,
		'status': doc.status,
		'grand_total': doc.grand_total,
		'payment_entry': payment_entry.name,
	}


def _pay_expense_claim(doc):
	"""Pay out a just-submitted Expense Claim immediately, via the exact same
	whitelisted call HRMS's own 'Make Payment Entry' button uses
	(hrms.overrides.employee_payment_entry.get_payment_entry_for_employee) --
	that builds a correctly populated Payment Entry (party_type Employee,
	payment_type Pay, paid_to = the claim's payable account, references/
	amounts computed by HRMS itself) so we don't have to re-derive those
	amounts by hand.

	The only thing overridden here is paid_from: the showroom's POS Profile
	account_for_change_amount for the logged-in user instead of a generic
	mode-of-payment account, so accounting can be tracked per showroom --
	same convention as the Sales/Purchase Invoice and standalone Customer/
	Supplier payment flows. Falls back to HRMS's own default bank/cash
	account if the POS Profile has none configured.
	"""
	from hrms.overrides.employee_payment_entry import get_payment_entry_for_employee

	pe = get_payment_entry_for_employee('Expense Claim', doc.name)

	change_account = get_pos_change_account()
	if change_account:
		pe.paid_from = change_account

	pe.flags.ignore_permissions = True
	pe.insert(ignore_permissions=True)
	pe.submit()
	return pe


@frappe.whitelist()
def get_expense_claims_list(page_start=0, page_length=20, from_date=None, to_date=None, search=None):
	"""Paginated list of Expense Claims -- all of them for System Manager,
	otherwise only the logged-in user's own."""
	page_start = max(0, int(page_start or 0))
	page_length = max(1, min(int(page_length or 20), 100))

	filters = {}
	if not is_system_manager():
		employee = _get_employee_for_user()
		filters['employee'] = employee.name

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
		'employee_name',
		'posting_date',
		'remark',
		'approval_status',
		'status',
		'total_claimed_amount',
		'total_sanctioned_amount',
		'grand_total',
		'is_paid',
		'docstatus',
		'custom_warehouse as warehouse',
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
	doc = frappe.get_doc('Expense Claim', expense_claim)
	if not is_system_manager():
		employee = _get_employee_for_user()
		if doc.employee != employee.name:
			frappe.throw(_('You are not permitted to view this Expense Claim.'), exc=frappe.PermissionError)

	return {
		'name': doc.name,
		'posting_date': doc.posting_date,
		'employee': doc.employee,
		'employee_name': doc.employee_name,
		'warehouse': doc.custom_warehouse,
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


@frappe.whitelist()
def cancel_expense_claim(expense_claim):
	"""Cancel a submitted Expense Claim. Restricted to System Manager, matching
	the Sales/Purchase Invoice cancel gate elsewhere in POS Awesome. ERPNext's
	own Expense Claim controller reverses its GL Entries on cancel."""
	if "System Manager" not in frappe.get_roles(frappe.session.user):
		frappe.throw(
			_("Only a user with the System Manager role can cancel this document."),
			frappe.PermissionError,
		)

	doc = frappe.get_doc("Expense Claim", expense_claim)
	if doc.docstatus != 1:
		frappe.throw(_("Only a submitted document can be cancelled."))

	# _pay_expense_claim() always pays a claim out in full on creation, via a
	# submitted Payment Entry referencing this claim -- ERPNext blocks
	# doc.cancel() below with "linked with Payment Entry" until that's gone.
	# The same cascade-cancel bsp_engineering applies to Sales/Purchase Invoice
	# is wired as a before_cancel hook on Expense Claim too (see
	# bsp_engineering/hooks.py), so it runs automatically inside doc.cancel()
	# below rather than being called manually here -- calling it beforehand
	# left this `doc` stale (hrms re-saves the Expense Claim as a side effect
	# of cancelling its Payment Entry) and doc.cancel() would then fail with
	# "Document has been modified after you have opened it".
	doc.flags.ignore_permissions = True
	doc.cancel()
	return {"name": doc.name, "status": doc.status}


@frappe.whitelist()
def delete_cancelled_expense_claim(expense_claim):
	"""Permanently delete a Draft or Cancelled Expense Claim."""
	if not is_system_manager():
		frappe.throw(
			_("Only a System Manager can delete expense claims."),
			exc=frappe.PermissionError,
		)

	if frappe.db.get_value("Expense Claim", expense_claim, "docstatus") not in (0, 2):
		frappe.throw(_("Only a draft or cancelled document can be deleted."))

	frappe.delete_doc("Expense Claim", expense_claim)
	return {"name": expense_claim}
