# Copyright (c) 2026, POS Awesome and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _
from frappe.utils import flt, money_in_words, nowdate, today
from erpnext.accounts.utils import get_balance_on

from posawesome.posawesome.utils.warehouse_doc_permissions import (
	get_accounts_for_warehouses,
	get_expanded_permitted_warehouses,
	is_privileged_invoice_viewer,
	user_can_access_payment_entry,
)

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



def _sum_not_cancelled(doctype, field, filters, or_filters):
	"""Sum of `field` over every row matching the list filters, leaving out
	cancelled documents -- the list header's money total, which has to cover
	all pages, not just the one on screen."""
	filters = dict(filters)
	if filters.get('docstatus') == 2:
		return 0.0
	filters.setdefault('docstatus', ['!=', 2])
	return flt(
		frappe.get_all(
			doctype,
			filters=filters,
			or_filters=or_filters,
			fields=[f'sum({field}) as total'],
			ignore_permissions=True,
		)[0].total
	)

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
	"""Dict filters for Fund Transfer queries (dashboard / ``get_all``).

	Unrestricted users get every fund transfer. Warehouse-restricted users
	are limited to rows whose ``custom_warehouse`` matches, falling back to
	``paid_to`` showroom cash accounts when no warehouse field is set.
	"""
	filters = {
		'payment_type': 'Internal Transfer',
		'custom_fund_transfer': 1,
		'docstatus': ('!=', 2),
	}
	permitted = get_expanded_permitted_warehouses()
	if permitted is None:
		return filters
	if not permitted:
		filters['name'] = ''
		return filters

	# Dict filters cannot OR warehouse + account; prefer custom_warehouse,
	# else paid_to accounts for the permitted showrooms (dashboard legacy).
	filters['custom_warehouse'] = ['in', list(permitted)]
	return filters


def _list_scope():
	"""Base Fund Transfer filters + warehouse OR-scope for restricted users.

	Visibility is warehouse-based: ``custom_warehouse`` match, or ``paid_to`` /
	``paid_from`` belonging to a permitted showroom cash account. Unrestricted
	admins (no Warehouse User Permission) see every fund transfer.
	"""
	filters = [
		[DOCTYPE, 'payment_type', '=', 'Internal Transfer'],
		[DOCTYPE, 'custom_fund_transfer', '=', 1],
	]
	or_filters = None
	permitted = get_expanded_permitted_warehouses()
	if permitted is None:
		return filters, or_filters
	if not permitted:
		filters.append([DOCTYPE, 'name', '=', ''])
		return filters, or_filters

	accounts = get_accounts_for_warehouses(permitted)
	or_filters = [[DOCTYPE, 'custom_warehouse', 'in', list(permitted)]]
	if accounts:
		or_filters.append([DOCTYPE, 'paid_to', 'in', accounts])
		or_filters.append([DOCTYPE, 'paid_from', 'in', accounts])
	return filters, or_filters


@frappe.whitelist()
def get_fund_transfers_list(
	page_start=0,
	page_length=20,
	from_date=None,
	to_date=None,
	search=None,
	paid_to=None,
	mode_of_payment=None,
	docstatus=None,
):
	"""Paginated Fund Transfers visible when the warehouse (or showroom
	cash account) matches the user's permitted warehouses."""
	from posawesome.posawesome.utils.list_query import count_distinct

	page_start = max(0, int(page_start or 0))
	page_length = max(1, min(int(page_length or 20), 100))

	filters, warehouse_or = _list_scope()
	if paid_to:
		filters.append([DOCTYPE, 'paid_to', '=', paid_to])
	if mode_of_payment:
		filters.append([DOCTYPE, 'mode_of_payment', '=', mode_of_payment])
	if docstatus not in (None, ''):
		filters.append([DOCTYPE, 'docstatus', '=', int(docstatus)])

	if from_date:
		filters.append([DOCTYPE, 'posting_date', '>=', from_date])
	if to_date:
		filters.append([DOCTYPE, 'posting_date', '<=', to_date])

	or_filters = None
	if search and len(search.strip()) >= 2:
		like = f'%{search.strip()}%'
		search_or = [
			[DOCTYPE, 'name', 'like', like],
			[DOCTYPE, 'paid_to', 'like', like],
		]
		if warehouse_or:
			# Can't nest OR groups — AND on custom_warehouse, OR for search.
			filters.append(warehouse_or[0])
			or_filters = search_or
		else:
			or_filters = search_or
	else:
		or_filters = warehouse_or

	fields = [
		'name',
		'posting_date',
		'paid_from',
		'paid_to',
		'mode_of_payment',
		'paid_amount as amount',
		'docstatus',
		'owner',
		'creation',
	]

	rows = frappe.get_list(
		DOCTYPE,
		filters=filters,
		or_filters=or_filters,
		fields=fields,
		order_by='creation desc',
		limit_start=page_start,
		limit_page_length=page_length,
		ignore_permissions=True,
	)

	total = count_distinct(DOCTYPE, filters=filters, or_filters=or_filters)

	# Sum helper expects dict filters — compute with get_list.
	sum_filters = [f for f in filters if not (f[0] == DOCTYPE and f[1] == 'docstatus')]
	sum_filters.append([DOCTYPE, 'docstatus', '!=', 2])
	sum_rows = frappe.get_list(
		DOCTYPE,
		filters=sum_filters,
		or_filters=or_filters,
		fields=['sum(paid_amount) as total'],
		ignore_permissions=True,
		limit_page_length=1,
	)

	return {
		'transfers': rows,
		'total': total,
		'has_more': (page_start + page_length) < total,
		'total_transferred': flt(sum_rows[0].total if sum_rows else 0),
	}


@frappe.whitelist()
def get_fund_transfer_detail(name):
	doc = frappe.get_doc(DOCTYPE, name)
	if not doc.custom_fund_transfer or doc.payment_type != 'Internal Transfer':
		frappe.throw(_('Fund Transfer not found.'), exc=frappe.DoesNotExistError)

	if not user_can_access_payment_entry(name):
		frappe.throw(
			_('You are not permitted to view this Fund Transfer.'),
			exc=frappe.PermissionError,
		)

	currency = doc.paid_to_account_currency or frappe.get_cached_value('Company', doc.company, 'default_currency')
	amount = flt(doc.paid_amount)

	return {
		'name': doc.name,
		'posting_date': doc.posting_date,
		'creation': doc.creation,
		'company': doc.company,
		'paid_from': doc.paid_from,
		'paid_to': doc.paid_to,
		'mode_of_payment': doc.mode_of_payment,
		'amount': amount,
		'docstatus': doc.docstatus,
		'owner': doc.owner,
		'remarks': doc.reference_no,
		# Same figures as the "BSP Fundtransfer" print (Fund Receive Voucher).
		'currency': currency,
		'received_from': frappe.db.get_value('User', doc.owner, 'full_name') or doc.owner,
		'reference_no': doc.reference_no,
		'description': doc.remarks,
		'amount_in_words': money_in_words(amount, currency),
		**_voucher_balances(doc, amount),
	}


def _voucher_balances(doc, amount):
	"""Previous / current balance of the receiving account, computed like the
	print format: balance as on the posting date, minus this transfer for
	"previous". Only meaningful for a submitted transfer."""
	if doc.docstatus != 1:
		return {'previous_balance': None, 'current_balance': None}
	current = flt(get_balance_on(account=doc.paid_to, date=doc.posting_date, company=doc.company))
	return {'previous_balance': current - amount, 'current_balance': current}


@frappe.whitelist()
def get_account_closing_balance(account, company=None):
	"""Current closing balance of a "Account Paid To" option, shown on the
	New Fund Transfer screen when the account is picked."""
	_require_fund_transfer_manager()
	company = company or _default_company()
	allowed = {row.name for row in get_paid_to_account_options(company)}
	if account not in allowed:
		frappe.throw(_('{0} is not a valid Cash In Hand account for this company.').format(account))
	return {
		'account': account,
		'balance': flt(get_balance_on(account=account, date=nowdate(), company=company)),
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

	# Payment Entry's own doctype permissions only grant `cancel` to Accounts
	# User/Accounts Manager -- neither BSP Admin nor System Manager, which is
	# what _require_fund_transfer_manager() above actually authorises against.
	# Same gap already fixed for BSP Daily Deposit / Expense Claim cancel.
	doc.flags.ignore_permissions = True
	doc.cancel()
	return {'name': doc.name, 'docstatus': doc.docstatus}
