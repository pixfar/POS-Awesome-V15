# Copyright (c) 2026, POS Awesome contributors
# For license information, please see license.txt

import json

import frappe

from . import purchase_orders as po


@frappe.whitelist()
def create_supplier(data):
	return po.create_supplier(data)


@frappe.whitelist()
def search_suppliers(search_text=None, limit=20):
	return po.search_suppliers(search_text=search_text, limit=limit)


@frappe.whitelist()
def get_buying_price_list():
	return po.get_buying_price_list()


@frappe.whitelist()
def get_supplier_info(supplier):
	return po.get_supplier_info(supplier)


@frappe.whitelist()
def get_last_buying_rate(supplier, item_codes, company=None):
	return po.get_last_buying_rate(supplier, item_codes, company=company)


@frappe.whitelist()
def create_purchase_item(data):
	return po.create_purchase_item(data)


@frappe.whitelist()
def create_purchase_invoice(data):
	payload = json.loads(data) if isinstance(data, str) else data
	return po._create_purchase_invoice_from_pos(payload)


@frappe.whitelist()
def get_purchase_invoices_list(
	pos_profile,
	page_start=0,
	page_length=100,
	mine_only=0,
	status=None,
	from_date=None,
	to_date=None,
	item_code=None,
	item_group=None,
	supplier=None,
	warehouse=None,
	search=None,
):
	return po.get_purchase_invoices_list(
		pos_profile,
		page_start=page_start,
		page_length=page_length,
		mine_only=mine_only,
		status=status,
		from_date=from_date,
		to_date=to_date,
		item_code=item_code,
		item_group=item_group,
		supplier=supplier,
		warehouse=warehouse,
		search=search,
	)


@frappe.whitelist()
def get_purchase_invoice_detail(name):
	return po.get_purchase_invoice_detail(name)


@frappe.whitelist()
def cancel_purchase_invoice(invoice):
	return po.cancel_purchase_invoice(invoice)


@frappe.whitelist()
def delete_cancelled_purchase_invoice(invoice):
	return po.delete_cancelled_purchase_invoice(invoice)


@frappe.whitelist()
def create_purchase_return(invoice):
	return po.create_purchase_return(invoice)


# Generic item search used by ItemsSelector in purchase context.
@frappe.whitelist()
def search_items(search_text=None, limit=20):
	return po.search_items(search_text=search_text, limit=limit)

