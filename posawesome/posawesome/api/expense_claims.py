# Copyright (c) 2026, POS Awesome and contributors
# For license information, please see license.txt

import json

import erpnext
import frappe
from frappe import _
from frappe.utils import flt, today

from posawesome.posawesome.utils.warehouse_doc_permissions import (
	is_system_manager,
	is_privileged_invoice_viewer,
	ensure_can_create,
)
from posawesome.posawesome.api.payment_processing.utils import get_pos_change_account

DEFAULT_MODE_OF_PAYMENT = 'Cash'
DEFAULT_PAYABLE_ACCOUNT = 'Creditors - BSP'
DEFAULT_EXPENSE_ACCOUNT = 'Operating Expenses - BSP'
MAX_EXPENSE_IMAGES = 3
_IMAGE_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.heic', '.heif')


def _parse_json(value):
	if isinstance(value, str):
		return json.loads(value)
	return value


_EMPLOYEE_FIELDS = ['name', 'employee_name', 'company', 'department', 'expense_approver']


def _get_employee_for_user(user=None):
	user = user or frappe.session.user
	employee = frappe.db.get_value(
		'Employee',
		{'user_id': user, 'status': 'Active'},
		_EMPLOYEE_FIELDS,
		as_dict=True,
	)
	if not employee:
		frappe.throw(
			_('No active Employee record is linked to your user account. Please contact your administrator.'),
			title=_('Employee Not Found'),
		)
	return employee


def _get_employee_by_id(employee_id):
	employee = frappe.db.get_value(
		'Employee',
		{'name': employee_id, 'status': 'Active'},
		_EMPLOYEE_FIELDS,
		as_dict=True,
	)
	if not employee:
		frappe.throw(
			_('Employee {0} not found or is not active.').format(employee_id),
			title=_('Employee Not Found'),
		)
	return employee


@frappe.whitelist()
def get_current_employee():
	"""Employee record linked to the logged-in POS user, used to prefill the Expense form."""
	return _get_employee_for_user()


@frappe.whitelist()
def search_employees(search_text=None, limit=20):
	"""Employee search for the Expense form's admin-only "From Employee"
	override (System Manager / BSP Admin) -- lets them create an Expense
	Claim on behalf of a different employee instead of only their own.
	Gated the same way as the "Accounts" override (get_cash_in_hand_accounts)
	since this is meant to be admin-only functionality."""
	if not is_privileged_invoice_viewer():
		frappe.throw(_('Not permitted'), exc=frappe.PermissionError)

	limit = max(1, min(int(limit or 20), 50))
	filters = {'status': 'Active'}
	or_filters = None
	if search_text and len(search_text.strip()) >= 2:
		like = f'%{search_text.strip()}%'
		or_filters = {'name': ['like', like], 'employee_name': ['like', like]}

	return frappe.get_all(
		'Employee',
		filters=filters,
		or_filters=or_filters,
		fields=_EMPLOYEE_FIELDS,
		order_by='employee_name asc',
		limit_page_length=limit,
		ignore_permissions=True,
	)


@frappe.whitelist()
def get_expense_claim_types():
	return frappe.get_all(
		'Expense Claim Type',
		fields=['name'],
		order_by='name asc',
		ignore_permissions=True,
	)


@frappe.whitelist()
def create_expense_claim_type(expense_type):
	"""Create an Expense Claim Type for System Manager / BSP Admin.

	The accounts row is always Operating Expenses - BSP for that account's
	company, matching the Expense Claim Type screen in Desk.
	"""
	if not is_privileged_invoice_viewer():
		frappe.throw(
			_('Only a System Manager or BSP Admin can create an Expense Claim Type.'),
			exc=frappe.PermissionError,
		)

	name = (expense_type or '').strip()
	if not name:
		frappe.throw(_('Expense Claim Type is required.'))

	if frappe.db.exists('Expense Claim Type', name):
		return {'name': name, 'exists': True}

	company = frappe.db.get_value('Account', DEFAULT_EXPENSE_ACCOUNT, 'company')
	if not company:
		frappe.throw(
			_('Default account {0} was not found.').format(DEFAULT_EXPENSE_ACCOUNT),
			title=_('Account Not Found'),
		)

	doc = frappe.new_doc('Expense Claim Type')
	doc.expense_type = name
	doc.append('accounts', {
		'company': company,
		'default_account': DEFAULT_EXPENSE_ACCOUNT,
	})
	doc.flags.ignore_permissions = True
	doc.insert(ignore_permissions=True)
	return {'name': doc.name, 'default_account': DEFAULT_EXPENSE_ACCOUNT}


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

	# "From Employee" override -- System Manager / BSP Admin only, same trust
	# model as the "Accounts" override below: re-verified server-side, never
	# trusted from the client alone.
	employee_override = data.get('employee')
	if employee_override and is_privileged_invoice_viewer():
		employee = _get_employee_by_id(employee_override)
	else:
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
	_attach_expense_images(doc, data.get('attachments'))

	# Server re-verifies System Manager / BSP Admin before honoring this --
	# never trust the client alone, same gate as Purchase Invoice's own
	# "Accounts" override (see purchase_orders.create_purchase_invoice).
	payment_account_override = data.get('payment_account')
	if payment_account_override and not is_privileged_invoice_viewer():
		payment_account_override = None

	payment_entry = _pay_expense_claim(doc, override_account=payment_account_override)
	doc.reload()  # payment_entry's on_submit hook updates status to Paid

	return {
		'name': doc.name,
		'status': doc.status,
		'grand_total': doc.grand_total,
		'payment_entry': payment_entry.name,
	}


def _pay_expense_claim(doc, override_account=None):
	"""Pay out a just-submitted Expense Claim immediately, via the exact same
	whitelisted call HRMS's own 'Make Payment Entry' button uses
	(hrms.overrides.employee_payment_entry.get_payment_entry_for_employee) --
	that builds a correctly populated Payment Entry (party_type Employee,
	payment_type Pay, paid_to = the claim's payable account, references/
	amounts computed by HRMS itself) so we don't have to re-derive those
	amounts by hand.

	paid_from is the showroom's POS Profile account_for_change_amount for
	the logged-in user instead of a generic mode-of-payment account, so
	accounting can be tracked per showroom -- same convention as the Sales/
	Purchase Invoice and standalone Customer/Supplier payment flows.
	`override_account` (System Manager / BSP Admin only -- re-verified by
	the caller, never trusted from the client alone) takes priority when
	set, so an admin can route this specific expense through a different
	showroom's cash account. Falls back to HRMS's own default bank/cash
	account if neither is available.

	posting_date is overridden to the claim's own expense date -- HRMS's
	get_payment_entry_for_employee defaults it to nowdate(), which would
	otherwise leave the payment dated today even when the expense itself
	was back- or post-dated (see ExpenseNew.vue's canEditPostingDate).
	"""
	from hrms.overrides.employee_payment_entry import get_payment_entry_for_employee

	pe = get_payment_entry_for_employee('Expense Claim', doc.name)
	pe.posting_date = doc.posting_date

	change_account = override_account or get_pos_change_account()
	if change_account:
		pe.paid_from = change_account

	pe.flags.ignore_permissions = True
	pe.insert(ignore_permissions=True)
	pe.submit()
	return pe


def _is_image_filename(name):
	return (name or '').lower().split('?')[0].endswith(_IMAGE_EXTENSIONS)


def _attach_expense_images(doc, file_urls):
	"""Link images uploaded before the claim existed, same as a deposit receipt.

	Only unattached files owned by the current user are accepted, and a claim
	can hold at most three images.
	"""
	urls = []
	for url in file_urls or []:
		url = (url or '').strip()
		if url and url not in urls:
			urls.append(url)
	if not urls:
		return
	if len(urls) > MAX_EXPENSE_IMAGES:
		frappe.throw(_('You can attach at most {0} images.').format(MAX_EXPENSE_IMAGES))

	for url in urls:
		if not _is_image_filename(url):
			frappe.throw(_('Only image files can be attached.'))
		file_name = frappe.db.get_value(
			'File',
			{'file_url': url, 'owner': frappe.session.user},
			'name',
		)
		if not file_name:
			frappe.throw(_('Attachment could not be found.'))
		file_doc = frappe.get_doc('File', file_name)
		if file_doc.attached_to_name and not (
			file_doc.attached_to_doctype == 'Expense Claim' and file_doc.attached_to_name == doc.name
		):
			frappe.throw(_('Attachment is already used on another document.'))
		if not _is_image_filename(file_doc.file_name or file_doc.file_url):
			frappe.throw(_('Only image files can be attached.'))
		file_doc.attached_to_doctype = 'Expense Claim'
		file_doc.attached_to_name = doc.name
		file_doc.flags.ignore_permissions = True
		file_doc.save(ignore_permissions=True)


def _expense_claim_images(name):
	files = frappe.get_all(
		'File',
		filters={'attached_to_doctype': 'Expense Claim', 'attached_to_name': name},
		fields=['file_url', 'file_name'],
		order_by='creation asc',
		ignore_permissions=True,
	)
	return [row for row in files if _is_image_filename(row.file_name or row.file_url)]


@frappe.whitelist()
def get_expense_claims_list(
	page_start=0,
	page_length=20,
	from_date=None,
	to_date=None,
	search=None,
	warehouse=None,
	expense_type=None,
):
	"""Paginated list of Expense Claims -- all of them for System Manager,
	otherwise only the logged-in user's own."""
	page_start = max(0, int(page_start or 0))
	page_length = max(1, min(int(page_length or 20), 100))

	filters = {}
	if not is_system_manager():
		employee = _get_employee_for_user()
		filters['employee'] = employee.name

	if warehouse:
		filters['custom_warehouse'] = warehouse

	if expense_type:
		parents = frappe.get_all(
			'Expense Claim Detail',
			filters={'expense_type': expense_type, 'parenttype': 'Expense Claim'},
			pluck='parent',
		)
		filters['name'] = ['in', parents or ['__none__']]

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
		'creation',
	]

	rows = frappe.get_all(
		'Expense Claim',
		filters=filters,
		or_filters=or_filters,
		fields=fields,
		order_by='creation desc',
		start=page_start,
		page_length=page_length,
		ignore_permissions=True,
	)
	_attach_expense_types(rows)

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


def _attach_expense_types(rows):
	"""Comma-separated Expense Claim Types on each list row."""
	if not rows:
		return
	details = frappe.get_all(
		'Expense Claim Detail',
		filters={'parent': ['in', [row.name for row in rows]], 'parenttype': 'Expense Claim'},
		fields=['parent', 'expense_type'],
		ignore_permissions=True,
	)
	by_parent = {}
	for detail in details:
		if not detail.expense_type:
			continue
		types = by_parent.setdefault(detail.parent, [])
		if detail.expense_type not in types:
			types.append(detail.expense_type)
	for row in rows:
		row['expense_types'] = ', '.join(by_parent.get(row.name) or [])


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
		'creation': doc.creation,
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
		'attachments': _expense_claim_images(doc.name),
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
