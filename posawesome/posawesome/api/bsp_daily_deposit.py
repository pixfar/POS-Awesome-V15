# Copyright (c) 2026, POS Awesome and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _
from frappe.utils import flt, today

from posawesome.posawesome.utils.warehouse_doc_permissions import (
	get_permission_scoped_names,
	is_system_manager,
)
from posawesome.posawesome.api.payment_processing.utils import get_pos_change_account

DOCTYPE = 'BSP Daily Deposit'


def _parse_json(value):
	if isinstance(value, str):
		return json.loads(value)
	return value


@frappe.whitelist()
def get_current_user_display():
	"""User + display name used to prefill the New Daily Deposit form."""
	user = frappe.session.user
	full_name = frappe.db.get_value('User', user, 'full_name') or user
	return {'user': user, 'user_name': full_name}


@frappe.whitelist()
def get_deposit_type_options():
	return frappe.get_meta(DOCTYPE).get_field('deposit_type').options.split('\n')


@frappe.whitelist()
def get_bank_options():
	return frappe.get_all(
		'Bank',
		fields=['name'],
		order_by='name asc',
		limit_page_length=200,
		ignore_permissions=True,
	)


@frappe.whitelist()
def create_daily_deposit(data):
	"""Create and submit a BSP Daily Deposit for the logged-in POS user."""
	data = _parse_json(data)
	if not data:
		frappe.throw(_('Deposit data is required.'))

	if not data.get('warehouse'):
		frappe.throw(_('Warehouse is required.'))
	if not data.get('bank_name'):
		frappe.throw(_('Bank Name is required.'))
	if flt(data.get('amount')) <= 0:
		frappe.throw(_('Amount must be greater than zero.'))
	if not data.get('acknowledgment_receipt'):
		frappe.throw(_('Acknowledgment Receipt is required.'))

	doc = frappe.new_doc(DOCTYPE)
	doc.warehouse = data.get('warehouse')
	doc.posting_date = data.get('posting_date') or today()
	# User is always the logged-in session user -- never trust a client-supplied value.
	doc.user = frappe.session.user
	doc.deposit_type = data.get('deposit_type') or 'Bank Deposit'
	doc.bank_name = data.get('bank_name')
	doc.amount = flt(data.get('amount'))
	doc.acknowledgment_receipt = data.get('acknowledgment_receipt')

	doc.insert(ignore_permissions=True)
	doc.submit()

	payment_entry = _create_deposit_payment_entry(doc)
	doc.db_set('payment_entry', payment_entry.name, update_modified=False)
	doc.db_set('status', 'Deposited', update_modified=False)

	return {
		'name': doc.name,
		'amount': doc.amount,
		'payment_entry': payment_entry.name,
		'status': 'Deposited',
	}


def _create_deposit_payment_entry(doc):
	"""Internal Transfer Payment Entry moving the showroom's daily cash from
	its own POS Profile account_for_change_amount into the company's central
	default_cash_account -- this is what "depositing" a BSP Daily Deposit
	means in GL terms. Linked back via custom_bsp_daily_deposit so it shows
	as a Connection on the deposit's own form (Internal Transfer entries
	clear the `references` child table on every save, so that's not usable
	for the link -- see PaymentEntry.set_missing_values).
	"""
	change_account = get_pos_change_account()
	if not change_account:
		frappe.throw(
			_('Please set "Account for Change Amount" on your POS Profile before creating a deposit.')
		)

	company = frappe.db.get_value('Warehouse', doc.warehouse, 'company')
	if not company:
		frappe.throw(_('Could not determine Company for warehouse {0}.').format(doc.warehouse))

	default_cash_account = frappe.get_cached_value('Company', company, 'default_cash_account')
	if not default_cash_account:
		frappe.throw(_('Please set Default Cash Account in Company {0}.').format(company))

	pe = frappe.new_doc('Payment Entry')
	pe.payment_type = 'Internal Transfer'
	pe.company = company
	pe.posting_date = doc.posting_date
	pe.paid_from = change_account
	pe.paid_to = default_cash_account
	pe.paid_amount = flt(doc.amount)
	pe.received_amount = flt(doc.amount)
	pe.reference_no = doc.name
	pe.reference_date = doc.posting_date
	pe.custom_bsp_daily_deposit = doc.name
	pe.flags.ignore_permissions = True
	pe.insert(ignore_permissions=True)
	pe.submit()
	return pe


@frappe.whitelist()
def get_daily_deposits_list(page_start=0, page_length=20, from_date=None, to_date=None, search=None):
	"""Paginated list of Daily Deposits -- all of them for System Manager,
	otherwise the logged-in user's own plus any into their permitted
	warehouse(s)."""
	page_start = max(0, int(page_start or 0))
	page_length = max(1, min(int(page_length or 20), 100))

	filters = {}
	if not is_system_manager():
		scoped_names = get_permission_scoped_names(DOCTYPE, 'warehouse', owner_field='user')
		filters['name'] = ['in', scoped_names or []]

	if from_date and to_date:
		filters['posting_date'] = ['between', [from_date, to_date]]
	elif from_date:
		filters['posting_date'] = ['>=', from_date]
	elif to_date:
		filters['posting_date'] = ['<=', to_date]

	or_filters = None
	if search and len(search.strip()) >= 2:
		like = f'%{search.strip()}%'
		or_filters = {'name': ['like', like], 'bank_name': ['like', like]}

	fields = [
		'name',
		'warehouse',
		'posting_date',
		'user_name',
		'deposit_type',
		'bank_name',
		'amount',
		'docstatus',
		'status',
		'payment_entry',
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
		'deposits': rows,
		'total': total,
		'has_more': (page_start + page_length) < total,
	}


@frappe.whitelist()
def get_daily_deposit_detail(name):
	doc = frappe.get_doc(DOCTYPE, name)
	if not is_system_manager():
		scoped_names = get_permission_scoped_names(DOCTYPE, 'warehouse', owner_field='user') or []
		if name not in scoped_names:
			frappe.throw(_('You are not permitted to view this Daily Deposit.'), exc=frappe.PermissionError)

	return {
		'name': doc.name,
		'warehouse': doc.warehouse,
		'posting_date': doc.posting_date,
		'user': doc.user,
		'user_name': doc.user_name,
		'deposit_type': doc.deposit_type,
		'bank_name': doc.bank_name,
		'amount': flt(doc.amount),
		'acknowledgment_receipt': doc.acknowledgment_receipt,
		'docstatus': doc.docstatus,
		'status': doc.status,
		'payment_entry': doc.payment_entry,
	}


@frappe.whitelist()
def cancel_daily_deposit(name):
	"""Cancel a submitted BSP Daily Deposit. Restricted to System Manager,
	matching the Sales/Purchase Invoice cancel gate elsewhere in POS Awesome."""
	if "System Manager" not in frappe.get_roles(frappe.session.user):
		frappe.throw(
			_("Only a user with the System Manager role can cancel this document."),
			frappe.PermissionError,
		)

	doc = frappe.get_doc(DOCTYPE, name)
	if doc.docstatus != 1:
		frappe.throw(_("Only a submitted document can be cancelled."))

	doc.cancel()
	doc.db_set('status', 'Cancelled', update_modified=False)
	return {"name": doc.name, "docstatus": doc.docstatus, "status": "Cancelled"}


@frappe.whitelist()
def delete_cancelled_daily_deposit(name):
	"""Permanently delete a Draft or Cancelled BSP Daily Deposit."""
	if not is_system_manager():
		frappe.throw(
			_("Only a System Manager can delete daily deposits."),
			exc=frappe.PermissionError,
		)

	if frappe.db.get_value(DOCTYPE, name, "docstatus") not in (0, 2):
		frappe.throw(_("Only a draft or cancelled document can be deleted."))

	frappe.delete_doc(DOCTYPE, name)
	return {"name": name}
