# Copyright (c) 2026, POS Awesome and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _
from frappe.utils import flt, today

from posawesome.posawesome.utils.warehouse_doc_permissions import is_privileged_invoice_viewer
from posawesome.posawesome.api.payment_processing.utils import get_pos_change_account

DOCTYPE = 'Payment Entry'


def _parse_json(value):
	if isinstance(value, str):
		return json.loads(value)
	return value


def _default_company():
	return (
		frappe.defaults.get_user_default('Company')
		or frappe.defaults.get_global_default('Company')
		or ''
	)


def _require_fund_transfer_manager():
	if not is_privileged_invoice_viewer():
		frappe.throw(
			_('Only a user with the BSP Admin or System Manager role can do this.'),
			frappe.PermissionError,
		)


def _default_cash_account(company):
	account = frappe.get_cached_value('Company', company, 'default_cash_account')
	if not account:
		frappe.throw(_('Please set Default Cash Account in Company {0}.').format(company))
	return account


@frappe.whitelist()
def get_paid_from_account(company=None):
	"""Company's default cash account -- fixed, display-only Account Paid
	From for the Fund Transfer form."""
	_require_fund_transfer_manager()

	company = company or _default_company()
	if not company:
		frappe.throw(_('Company is required.'))

	return {'company': company, 'account': _default_cash_account(company)}


@frappe.whitelist()
def get_paid_to_account_options(company=None):
	"""Leaf accounts under the same Cash In Hand group as the company's
	default cash account, excluding that account itself -- the set of
	showroom cash accounts a Fund Transfer can be sent to."""
	_require_fund_transfer_manager()

	company = company or _default_company()
	if not company:
		frappe.throw(_('Company is required.'))

	default_account = _default_cash_account(company)
	parent_account = frappe.db.get_value('Account', default_account, 'parent_account')
	if not parent_account:
		return []

	return frappe.get_all(
		'Account',
		filters={
			'parent_account': parent_account,
			'is_group': 0,
			'company': company,
			'name': ['!=', default_account],
		},
		fields=['name', 'account_name'],
		order_by='account_name asc',
	)


@frappe.whitelist()
def get_mode_of_payment_options():
	_require_fund_transfer_manager()
	return frappe.get_all('Mode of Payment', fields=['name'], order_by='name asc')


@frappe.whitelist()
def create_fund_transfer(data):
	"""Internal Transfer Payment Entry moving cash from the company's
	central default_cash_account out to a showroom's own cash account
	(the reverse direction of a BSP Daily Deposit)."""
	_require_fund_transfer_manager()

	data = _parse_json(data)
	if not data:
		frappe.throw(_('Transfer data is required.'))

	company = data.get('company') or _default_company()
	if not company:
		frappe.throw(_('Company is required.'))

	paid_to = data.get('paid_to')
	if not paid_to:
		frappe.throw(_('Account Paid To is required.'))

	mode_of_payment = data.get('mode_of_payment')
	if not mode_of_payment:
		frappe.throw(_('Mode of Payment is required.'))

	amount = flt(data.get('amount'))
	if amount <= 0:
		frappe.throw(_('Amount must be greater than zero.'))

	default_account = _default_cash_account(company)

	# Re-validate against the server-computed option set rather than trusting
	# the client's paid_to value outright -- this is money leaving the
	# company's central account.
	allowed_accounts = {row.name for row in get_paid_to_account_options(company)}
	if paid_to not in allowed_accounts:
		frappe.throw(_('{0} is not a valid Cash In Hand account for this company.').format(paid_to))

	posting_date = data.get('posting_date') or today()

	pe = frappe.new_doc('Payment Entry')
	pe.payment_type = 'Internal Transfer'
	pe.company = company
	pe.posting_date = posting_date
	pe.mode_of_payment = mode_of_payment
	pe.paid_from = default_account
	pe.paid_to = paid_to
	pe.paid_amount = amount
	pe.received_amount = amount
	pe.reference_no = data.get('remarks') or _('Fund Transfer')
	pe.reference_date = posting_date
	pe.custom_fund_transfer = 1

	# Warehouse follows Account Paid To (showroom receiving the funds),
	# not the logged-in user's POS Profile.
	if frappe.get_meta('Payment Entry').has_field('custom_warehouse'):
		warehouse = (
			frappe.db.get_value('Account', paid_to, 'custom_warehouse')
			or frappe.db.get_value(
				'POS Profile',
				{'account_for_change_amount': paid_to, 'disabled': 0},
				'warehouse',
			)
			or (paid_to if frappe.db.exists('Warehouse', paid_to) else None)
		)
		if warehouse:
			pe.custom_warehouse = warehouse

	pe.flags.ignore_permissions = True
	pe.insert(ignore_permissions=True)
	pe.submit()

	return {
		'name': pe.name,
		'paid_from': pe.paid_from,
		'paid_to': pe.paid_to,
		'amount': pe.paid_amount,
	}


def _list_filters():
	filters = {
		'payment_type': 'Internal Transfer',
		'custom_fund_transfer': 1,
		'docstatus': ('!=', 2),
	}
	if not is_privileged_invoice_viewer():
		# Regular users only ever see transfers sent to their own showroom's
		# account -- if they have none configured, they see nothing rather
		# than every transfer.
		change_account = get_pos_change_account()
		filters['paid_to'] = change_account or ''
	return filters


@frappe.whitelist()
def get_fund_transfers_list(page_start=0, page_length=20, from_date=None, to_date=None, search=None):
	"""Paginated list of Fund Transfers -- all of them for BSP Admin/System
	Manager, otherwise only the ones sent to the logged-in user's own
	showroom account (POS Profile account_for_change_amount)."""
	page_start = max(0, int(page_start or 0))
	page_length = max(1, min(int(page_length or 20), 100))

	filters = _list_filters()

	if from_date and to_date:
		filters['posting_date'] = ['between', [from_date, to_date]]
	elif from_date:
		filters['posting_date'] = ['>=', from_date]
	elif to_date:
		filters['posting_date'] = ['<=', to_date]

	or_filters = None
	if search and len(search.strip()) >= 2:
		like = f'%{search.strip()}%'
		or_filters = {'name': ['like', like], 'paid_to': ['like', like]}

	fields = [
		'name',
		'posting_date',
		'paid_from',
		'paid_to',
		'mode_of_payment',
		'paid_amount as amount',
		'docstatus',
		'owner',
	]

	rows = frappe.get_all(
		DOCTYPE,
		filters=filters,
		or_filters=or_filters,
		fields=fields,
		order_by='posting_date desc, creation desc',
		start=page_start,
		page_length=page_length,
		ignore_permissions=True,
	)

	total = frappe.get_all(
		DOCTYPE,
		filters=filters,
		or_filters=or_filters,
		fields=['count(name) as total'],
		ignore_permissions=True,
	)[0].total

	return {
		'transfers': rows,
		'total': total,
		'has_more': (page_start + page_length) < total,
	}


@frappe.whitelist()
def get_fund_transfer_detail(name):
	doc = frappe.get_doc(DOCTYPE, name)
	if not doc.custom_fund_transfer or doc.payment_type != 'Internal Transfer':
		frappe.throw(_('Fund Transfer not found.'), exc=frappe.DoesNotExistError)

	if not is_privileged_invoice_viewer():
		change_account = get_pos_change_account()
		if not change_account or doc.paid_to != change_account:
			frappe.throw(_('You are not permitted to view this Fund Transfer.'), exc=frappe.PermissionError)

	return {
		'name': doc.name,
		'posting_date': doc.posting_date,
		'company': doc.company,
		'paid_from': doc.paid_from,
		'paid_to': doc.paid_to,
		'mode_of_payment': doc.mode_of_payment,
		'amount': flt(doc.paid_amount),
		'docstatus': doc.docstatus,
		'owner': doc.owner,
		'remarks': doc.reference_no,
	}


@frappe.whitelist()
def cancel_fund_transfer(name):
	"""Cancel a submitted Fund Transfer. Restricted to BSP Admin/System
	Manager, matching the cancel gate used elsewhere in POS Awesome."""
	_require_fund_transfer_manager()

	doc = frappe.get_doc(DOCTYPE, name)
	if not doc.custom_fund_transfer or doc.payment_type != 'Internal Transfer':
		frappe.throw(_('Fund Transfer not found.'), exc=frappe.DoesNotExistError)
	if doc.docstatus != 1:
		frappe.throw(_('Only a submitted document can be cancelled.'))

	doc.cancel()
	return {'name': doc.name, 'docstatus': doc.docstatus}
