"""Restock via Delivery Note / Purchase Receipt returns.

When an invoice was fulfilled with update_stock=0 (stock moved later via DN/PR),
ERPNext blocks Sales/Purchase Invoice returns from flipping update_stock on.
Stock must come back through a DN/PR return against the fulfillment voucher.

Only the *delivered/received* portion of a return may restock. Example:

	Sell 5 (no stock) → Return 1 (undelivered, no stock) → Deliver 3
	→ Return 1 (still 1 undelivered left → no stock) → Return 1 (from
	delivered → DN return +1). Net stock out = 2, matching net sale 5-3=2.
"""

from collections import defaultdict

import frappe
from frappe.utils import flt


def restock_sales_return(source, return_doc):
	"""Create Delivery Note returns for the delivered portion of a SI return."""
	if source.doctype != "Sales Invoice" or flt(source.update_stock):
		return []

	need_by_si_detail = _return_qty_by_source_item(
		return_doc, "sales_invoice_item"
	)
	if not need_by_si_detail:
		return []

	si_qty = {row.name: flt(row.qty) for row in source.items}
	prior_returned = _prior_invoice_returned_qty(
		"Sales Invoice",
		"sales_invoice_item",
		source.name,
		exclude_return=return_doc.name,
	)
	net_delivered = _net_fulfilled_by_source_item(
		fulfillment_doctype="Delivery Note",
		invoice_field="against_sales_invoice",
		source_item_field="si_detail",
		return_detail_field="dn_detail",
		invoice_name=source.name,
	)

	# Only restock the slice of this return that cannot be covered by
	# still-undelivered qty on the source invoice item.
	for si_detail, ret_qty in list(need_by_si_detail.items()):
		undelivered = max(
			0.0,
			flt(si_qty.get(si_detail))
			- flt(prior_returned.get(si_detail))
			- flt(net_delivered.get(si_detail)),
		)
		from_delivered = max(0.0, flt(ret_qty) - undelivered)
		if from_delivered <= 0.0001:
			need_by_si_detail.pop(si_detail, None)
		else:
			need_by_si_detail[si_detail] = from_delivered

	if not need_by_si_detail:
		return []

	return _allocate_and_submit_returns(
		fulfillment_doctype="Delivery Note",
		invoice_field="against_sales_invoice",
		source_item_field="si_detail",
		return_detail_field="dn_detail",
		invoice_name=source.name,
		need_by_source_item=need_by_si_detail,
	)


def restock_purchase_return(source, return_doc):
	"""Create Purchase Receipt returns for the received portion of a PI return."""
	if source.doctype != "Purchase Invoice" or flt(source.update_stock):
		return []

	need_by_pi_item = _return_qty_by_source_item(
		return_doc, "purchase_invoice_item"
	)
	if not need_by_pi_item:
		return []

	pi_qty = {row.name: flt(row.qty) for row in source.items}
	prior_returned = _prior_invoice_returned_qty(
		"Purchase Invoice",
		"purchase_invoice_item",
		source.name,
		exclude_return=return_doc.name,
	)
	net_received = _net_fulfilled_by_source_item(
		fulfillment_doctype="Purchase Receipt",
		invoice_field="purchase_invoice",
		source_item_field="purchase_invoice_item",
		return_detail_field="purchase_receipt_item",
		invoice_name=source.name,
	)

	for pi_item, ret_qty in list(need_by_pi_item.items()):
		unreceived = max(
			0.0,
			flt(pi_qty.get(pi_item))
			- flt(prior_returned.get(pi_item))
			- flt(net_received.get(pi_item)),
		)
		from_received = max(0.0, flt(ret_qty) - unreceived)
		if from_received <= 0.0001:
			need_by_pi_item.pop(pi_item, None)
		else:
			need_by_pi_item[pi_item] = from_received

	if not need_by_pi_item:
		return []

	return _allocate_and_submit_returns(
		fulfillment_doctype="Purchase Receipt",
		invoice_field="purchase_invoice",
		source_item_field="purchase_invoice_item",
		return_detail_field="purchase_receipt_item",
		invoice_name=source.name,
		need_by_source_item=need_by_pi_item,
	)


def _return_qty_by_source_item(return_doc, source_item_field):
	need = defaultdict(float)
	for row in return_doc.items or []:
		key = row.get(source_item_field)
		qty = abs(flt(row.qty))
		if key and qty:
			need[key] += qty
	return need


def _prior_invoice_returned_qty(doctype, source_item_field, invoice_name, exclude_return=None):
	"""Abs returned qty per source item row, excluding the current return doc."""
	filters = {
		"return_against": invoice_name,
		"docstatus": 1,
		"is_return": 1,
	}
	returns = frappe.get_all(doctype, filters=filters, pluck="name")
	if exclude_return and exclude_return in returns:
		returns = [name for name in returns if name != exclude_return]
	if not returns:
		return {}

	rows = frappe.db.sql(
		f"""
		SELECT `{source_item_field}` AS source_item, SUM(ABS(qty)) AS qty
		FROM `tab{doctype} Item`
		WHERE parent IN %(returns)s
		  AND IFNULL(`{source_item_field}`, '') != ''
		GROUP BY `{source_item_field}`
		""",
		{"returns": returns},
		as_dict=True,
	)
	return {row.source_item: flt(row.qty) for row in rows}


def _net_fulfilled_by_source_item(
	fulfillment_doctype,
	invoice_field,
	source_item_field,
	return_detail_field,
	invoice_name,
):
	"""Net DN/PR qty still out per source invoice item (after DN/PR returns)."""
	items = frappe.db.sql(
		f"""
		SELECT dni.parent, dni.name AS detail, dni.`{source_item_field}` AS source_item,
		       dni.qty
		FROM `tab{fulfillment_doctype} Item` dni
		INNER JOIN `tab{fulfillment_doctype}` dn ON dn.name = dni.parent
		WHERE dni.`{invoice_field}` = %s
		  AND dn.docstatus = 1
		  AND IFNULL(dn.is_return, 0) = 0
		  AND IFNULL(dni.`{source_item_field}`, '') != ''
		""",
		invoice_name,
		as_dict=True,
	)
	if not items:
		return {}

	already = _already_returned_against_details(
		fulfillment_doctype, return_detail_field, [row.detail for row in items]
	)
	net = defaultdict(float)
	for row in items:
		open_qty = flt(row.qty) - flt(already.get(row.detail, 0))
		if open_qty > 0:
			net[row.source_item] += open_qty
	return dict(net)


def _allocate_and_submit_returns(
	fulfillment_doctype,
	invoice_field,
	source_item_field,
	return_detail_field,
	invoice_name,
	need_by_source_item,
):
	items = frappe.db.sql(
		f"""
		SELECT dni.parent, dni.name AS detail, dni.`{source_item_field}` AS source_item,
		       dni.qty
		FROM `tab{fulfillment_doctype} Item` dni
		INNER JOIN `tab{fulfillment_doctype}` dn ON dn.name = dni.parent
		WHERE dni.`{invoice_field}` = %s
		  AND dn.docstatus = 1
		  AND IFNULL(dn.is_return, 0) = 0
		  AND IFNULL(dni.`{source_item_field}`, '') != ''
		ORDER BY dn.posting_date, dn.creation, dni.idx
		""",
		invoice_name,
		as_dict=True,
	)
	if not items:
		return []

	already = _already_returned_against_details(
		fulfillment_doctype, return_detail_field, [row.detail for row in items]
	)
	need = defaultdict(float, need_by_source_item)
	alloc_by_parent = defaultdict(dict)

	for row in items:
		want = need.get(row.source_item, 0)
		if want <= 0.0001:
			continue
		open_qty = flt(row.qty) - flt(already.get(row.detail, 0))
		if open_qty <= 0.0001:
			continue
		take = min(want, open_qty)
		alloc_by_parent[row.parent][row.detail] = take
		need[row.source_item] = want - take

	return _submit_fulfillment_returns(
		fulfillment_doctype, return_detail_field, alloc_by_parent
	)


def _already_returned_against_details(doctype, detail_field, detail_names):
	"""Sum abs(qty) already returned against each source DN/PR item row."""
	if not detail_names:
		return {}

	rows = frappe.db.sql(
		f"""
		SELECT dni.`{detail_field}` AS detail, SUM(ABS(dni.qty)) AS qty
		FROM `tab{doctype} Item` dni
		INNER JOIN `tab{doctype}` dn ON dn.name = dni.parent
		WHERE dn.docstatus = 1
		  AND IFNULL(dn.is_return, 0) = 1
		  AND dni.`{detail_field}` IN %(details)s
		GROUP BY dni.`{detail_field}`
		""",
		{"details": detail_names},
		as_dict=True,
	)
	return {row.detail: flt(row.qty) for row in rows if row.detail}


def _submit_fulfillment_returns(doctype, detail_field, alloc_by_parent):
	from erpnext.controllers.sales_and_purchase_return import make_return_doc

	created = []
	for parent_name, detail_qty in alloc_by_parent.items():
		if not detail_qty:
			continue
		try:
			return_doc = make_return_doc(doctype, parent_name)
			kept = []
			for row in return_doc.items:
				source_detail = row.get(detail_field)
				qty = detail_qty.get(source_detail)
				if not qty:
					continue
				row.qty = -abs(flt(qty))
				if doctype == "Purchase Receipt":
					row.received_qty = row.qty
					if row.get("rejected_qty"):
						row.rejected_qty = 0
				row.stock_qty = flt(row.qty) * flt(row.conversion_factor or 1)
				kept.append(row)
			if not kept:
				continue
			return_doc.set("items", kept)
			return_doc.insert(ignore_permissions=True)
			return_doc.submit()
			created.append(return_doc.name)
		except Exception:
			frappe.log_error(
				title=f"{doctype} return restock failed for {parent_name}",
				message=frappe.get_traceback(),
			)
	return created
