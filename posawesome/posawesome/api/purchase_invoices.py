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
def get_supplier_info(supplier, company=None):
	return po.get_supplier_info(supplier, company=company)


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
	do_number=None,
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
		do_number=do_number,
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
def create_purchase_return(invoice, items=None):
	return po.create_purchase_return(invoice, items=items)


@frappe.whitelist()
def get_purchase_invoice_for_receipt(invoice_name):
	return po.get_purchase_invoice_for_receipt(invoice_name)


@frappe.whitelist()
def create_purchase_receipt(invoice, doctype=None, items=None):
	return po.create_purchase_receipt(invoice, doctype=doctype, items=items)


@frappe.whitelist()
def get_items_by_do_number(do_number, warehouse=None, company=None):
	return po.get_items_by_do_number(do_number, warehouse=warehouse, company=company)


# Generic item search used by ItemsSelector in purchase context.
@frappe.whitelist()
def search_items(search_text=None, limit=20):
	return po.search_items(search_text=search_text, limit=limit)



@frappe.whitelist()
def get_purchase_drafts(search=None, limit=50):
	"""Draft Purchase Invoices for the purchase screen's "Drafts" dialog,
	newest first, scoped like the Purchase Invoice list."""
	from frappe.utils import cint, flt

	limit = max(1, min(cint(limit) or 50, 100))
	filters = [["Purchase Invoice", "docstatus", "=", 0]]
	scoped = po.get_permission_scoped_names("Purchase Invoice", "set_warehouse")
	if scoped is not None:
		if not scoped:
			return []
		filters.append(["Purchase Invoice", "name", "in", scoped])
	or_filters = None
	if search and search.strip():
		like = f"%{search.strip()}%"
		or_filters = [
			["Purchase Invoice", "name", "like", like],
			["Purchase Invoice", "supplier", "like", like],
			["Purchase Invoice", "supplier_name", "like", like],
		]
	rows = frappe.get_all(
		"Purchase Invoice",
		filters=filters,
		or_filters=or_filters,
		fields=["name", "supplier", "supplier_name", "posting_date", "set_warehouse", "grand_total", "currency", "modified", "owner"],
		order_by="modified desc",
		limit_page_length=limit,
		ignore_permissions=True,
	)
	counts = dict(
		frappe.get_all(
			"Purchase Invoice Item",
			filters={"parent": ["in", [r.name for r in rows]], "parenttype": "Purchase Invoice"},
			fields=["parent", "count(name) as n"],
			group_by="parent",
			as_list=True,
			ignore_permissions=True,
		)
	) if rows else {}
	for row in rows:
		row["item_count"] = counts.get(row.name, 0)
		row["grand_total"] = flt(row.grand_total)
		row["owner_name"] = frappe.db.get_value("User", row.owner, "full_name") or row.owner
	return rows


@frappe.whitelist()
def get_purchase_draft(name):
	"""Everything the purchase screen needs to load a Draft back into its form."""
	from frappe.utils import flt

	invoice = po.get_editable_purchase_draft(name)
	item_codes = list({row.item_code for row in invoice.items if row.item_code})
	uoms_by_item = {}
	item_info = {}
	if item_codes:
		for row in frappe.get_all(
			"UOM Conversion Detail",
			filters={"parent": ["in", item_codes], "parenttype": "Item"},
			fields=["parent", "uom", "conversion_factor"],
			order_by="idx asc",
		):
			uoms_by_item.setdefault(row.parent, []).append({"uom": row.uom, "conversion_factor": flt(row.conversion_factor)})
		item_info = {
			row.name: row
			for row in frappe.get_all(
				"Item",
				filters={"name": ["in", item_codes]},
				fields=["name", "item_group", "standard_rate", "custom_default_weigt_of_measure"],
			)
		}

	items = []
	for row in invoice.items:
		info = item_info.get(row.item_code) or {}
		item_uoms = uoms_by_item.get(row.item_code) or []
		if not any(u["uom"] == row.stock_uom for u in item_uoms):
			item_uoms.insert(0, {"uom": row.stock_uom, "conversion_factor": 1})
		items.append(
			{
				"item_code": row.item_code,
				"item_name": row.item_name,
				"item_group": row.item_group or info.get("item_group"),
				"stock_uom": row.stock_uom,
				"uom": row.uom,
				"conversion_factor": flt(row.conversion_factor) or 1,
				"qty": flt(row.qty),
				"rate": flt(row.rate),
				"standard_rate": flt(info.get("standard_rate")),
				"item_uoms": item_uoms,
				"custom_default_weigt_of_measure": flt(info.get("custom_default_weigt_of_measure")),
			}
		)

	return {
		"name": invoice.name,
		"supplier": invoice.supplier,
		"supplier_name": invoice.supplier_name,
		"posting_date": str(invoice.posting_date) if invoice.posting_date else None,
		"posting_time": str(invoice.posting_time) if invoice.posting_time else None,
		"warehouse": invoice.set_warehouse,
		"update_stock": invoice.update_stock,
		"custom_do_number": invoice.get("custom_do_number"),
		"remarks": invoice.remarks,
		"discount_amount": flt(invoice.discount_amount),
		"items": items,
	}
