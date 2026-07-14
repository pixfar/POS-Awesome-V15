# Copyright (c) 2020, Youssef Restom and contributors
# For license information, please see license.txt

"""Public invoice API facade backed by `invoice_processing` modules."""

import frappe
import time
from frappe.utils import flt
from erpnext.selling.doctype.sales_order.sales_order import make_sales_invoice
from posawesome.posawesome.api.invoice_processing.utils import (
    _get_return_validity_settings,
    _build_invoice_remarks,
    _set_return_valid_upto,
    _validate_return_window,
    get_latest_rate,
    get_price_list_currency,
    get_available_currencies,
)
from posawesome.posawesome.api.invoice_processing.stock import (
    _strip_client_freebies_from_payload,
    _validate_stock_on_invoice,
    _apply_item_name_overrides,
    _deduplicate_free_items,
    _merge_duplicate_taxes,
    _auto_set_return_batches,
    _collect_stock_errors,
    _should_block,
)
from posawesome.posawesome.api.invoice_processing.creation import (
    update_invoice,
    submit_invoice,
    submit_in_background_job,
    repair_invoice_submission,
    validate_cart_items,
)
from posawesome.posawesome.api.invoice_processing.returns import (
    search_invoices_for_return,
    validate_return_items,
    get_invoice_for_return,
)
from posawesome.posawesome.api.invoice_processing.payment import _create_change_payment_entries
from posawesome.posawesome.api.invoice_processing.data import get_last_invoice_rates
from posawesome.posawesome.api.utils import log_perf_event
from posawesome.posawesome.utils.warehouse_doc_permissions import get_permission_scoped_names


@frappe.whitelist()
def get_draft_invoices(
    pos_opening_shift=None,
    doctype="Sales Invoice",
    limit_page_length=0,
    company=None,
    pos_profile=None,
    cashier=None,
    is_supervisor=0,
):
    started_at = time.perf_counter()
    try:
        limit_page_length = int(limit_page_length or 0)
    except (TypeError, ValueError):
        limit_page_length = 0
    if limit_page_length < 0:
        limit_page_length = 0

    supervisor_scope = int(is_supervisor or 0)
    filters = {
        "docstatus": 0,
    }
    if supervisor_scope and company:
        filters["company"] = company
        if pos_profile:
            filters["pos_profile"] = pos_profile
        if cashier:
            filters["owner"] = cashier
    else:
        filters["posa_pos_opening_shift"] = pos_opening_shift
    if frappe.db.has_column(doctype, "posa_is_printed"):
        filters["posa_is_printed"] = 0

    invoices_list = frappe.get_list(
        doctype,
        filters=filters,
        fields=[
            "name",
            "customer",
            "customer_name",
            "posting_date",
            "posting_time",
            "grand_total",
            "currency",
            "pos_profile",
            "owner",
            "modified_by",
        ],
        limit_page_length=limit_page_length,
        order_by="modified desc",
    )
    for invoice in invoices_list:
        invoice["doctype"] = doctype
    log_perf_event(
        "get_draft_invoices",
        started_at,
        doctype=doctype,
        rows=len(invoices_list),
    )
    return invoices_list


@frappe.whitelist()
def get_sales_invoices_list(
    pos_profile,
    page_start=0,
    page_length=100,
    mine_only=0,
    status=None,
    from_date=None,
    to_date=None,
    item_code=None,
    item_group=None,
    customer=None,
    warehouse=None,
    search=None,
):
    """Paginated, filterable list of submitted sales invoices for the Invoice List page."""
    profile = (
        frappe.get_cached_doc("POS Profile", pos_profile)
        if isinstance(pos_profile, str)
        else pos_profile
    )
    doctype = (
        "POS Invoice"
        if profile.get("create_pos_invoice_instead_of_sales_invoice")
        else "Sales Invoice"
    )

    # No docstatus filter here on purpose — the list should show invoices of
    # any status (Draft, submitted, Cancelled), matching the Status dropdown's
    # own options (which already includes "Draft" and "Cancelled").
    filters = [
        [doctype, "company", "=", profile.get("company")],
    ]
    if int(mine_only or 0):
        filters.append([doctype, "owner", "=", frappe.session.user])
    else:
        # Warehouse-restricted users (not System Manager) only ever see their
        # own invoices or ones drawn from their permitted warehouse(s).
        scoped_names = get_permission_scoped_names(doctype, "set_warehouse")
        if scoped_names is not None:
            filters.append([doctype, "name", "in", scoped_names])
    if status:
        filters.append([doctype, "status", "=", status])
    if from_date:
        filters.append([doctype, "posting_date", ">=", from_date])
    if to_date:
        filters.append([doctype, "posting_date", "<=", to_date])
    if customer:
        filters.append([doctype, "customer", "=", customer])
    if warehouse:
        filters.append([doctype, "set_warehouse", "=", warehouse])

    item_doctype = f"{doctype} Item"
    if item_code:
        filters.append([item_doctype, "item_code", "=", item_code])
    if item_group:
        filters.append([item_doctype, "item_group", "=", item_group])

    or_filters = None
    if search:
        like = f"%{search}%"
        or_filters = [
            [doctype, "name", "like", like],
            [doctype, "customer_name", "like", like],
            [doctype, "customer", "like", like],
        ]

    page_start = max(0, int(page_start or 0))
    page_length = max(1, min(int(page_length or 100), 200))

    fields = [
        "name",
        "customer",
        "customer_name",
        "posting_date",
        "posting_time",
        "grand_total",
        "outstanding_amount",
        "status",
        "currency",
        "is_return",
        "owner",
    ]

    rows = frappe.get_list(
        doctype,
        filters=filters,
        or_filters=or_filters,
        fields=fields,
        order_by="posting_date desc, posting_time desc, modified desc",
        limit_start=page_start,
        limit_page_length=page_length,
        distinct=True,
        ignore_permissions=True,
    )
    for row in rows:
        row["doctype"] = doctype

    total = len(
        frappe.get_list(
            doctype,
            filters=filters,
            or_filters=or_filters,
            fields=["name"],
            distinct=True,
            ignore_permissions=True,
            limit_page_length=0,
        )
    )

    status_filters = [f for f in filters if not (f[0] == doctype and f[1] == "status")]
    status_counts = {
        row.status: row.count
        for row in frappe.get_list(
            doctype,
            filters=status_filters,
            or_filters=or_filters,
            fields=["status", "count(name) as count"],
            group_by="status",
            ignore_permissions=True,
            limit_page_length=0,
        )
    }

    return {
        "invoices": rows,
        "total": total,
        "has_more": (page_start + page_length) < total,
        "status_counts": status_counts,
    }


@frappe.whitelist()
def get_sales_invoice_detail(name, doctype="Sales Invoice"):
    """Full detail (header + items) for the Sales Invoice list's detail page."""
    if doctype not in ("Sales Invoice", "POS Invoice"):
        doctype = "Sales Invoice"

    doc = frappe.get_doc(doctype, name)
    owner_name = frappe.db.get_value("User", doc.owner, "full_name") or doc.owner
    return {
        "name": doc.name,
        "doctype": doctype,
        "customer": doc.customer,
        "customer_name": doc.customer_name,
        "posting_date": doc.posting_date,
        "posting_time": doc.posting_time,
        "status": doc.status,
        "currency": doc.currency,
        "company": doc.company,
        "pos_profile": doc.get("pos_profile"),
        "warehouse": doc.get("set_warehouse"),
        "territory": doc.get("territory"),
        "net_total": flt(doc.net_total),
        "total_qty": flt(doc.total_qty),
        "discount_amount": flt(doc.get("discount_amount")),
        "additional_discount_percentage": flt(doc.get("additional_discount_percentage")),
        "grand_total": flt(doc.grand_total),
        "paid_amount": flt(doc.paid_amount),
        "outstanding_amount": flt(doc.outstanding_amount),
        "change_amount": flt(doc.get("change_amount")),
        "is_return": doc.is_return,
        "return_against": doc.get("return_against"),
        "remarks": doc.get("remarks"),
        "owner": owner_name,
        "payments": [
            {
                "mode_of_payment": row.mode_of_payment,
                "amount": flt(row.amount),
            }
            for row in (doc.get("payments") or [])
        ],
        "taxes": [
            {
                "description": row.description,
                "rate": flt(row.rate),
                "tax_amount": flt(row.tax_amount),
            }
            for row in (doc.get("taxes") or [])
        ],
        "items": [
            {
                "item_code": row.item_code,
                "item_name": row.item_name,
                "qty": flt(row.qty),
                "uom": row.uom,
                "rate": flt(row.rate),
                "amount": flt(row.amount),
                "warehouse": row.get("warehouse"),
            }
            for row in doc.items
        ],
    }


@frappe.whitelist()
def search_items(search_text=None, limit=20):
    """Generic item search used by the Sales Invoice list's item filter."""
    limit = max(1, min(int(limit or 20), 50))
    filters = {"disabled": 0, "has_variants": 0}
    or_filters = None
    if search_text and len(search_text.strip()) >= 2:
        like = f"%{search_text.strip()}%"
        or_filters = {
            "name": ["like", like],
            "item_name": ["like", like],
        }

    return frappe.get_all(
        "Item",
        filters=filters,
        or_filters=or_filters,
        fields=["name as item_code", "item_name", "item_group"],
        order_by="item_name asc",
        limit_page_length=limit,
    )


@frappe.whitelist()
def get_draft_invoice_doc(invoice_name, doctype="Sales Invoice"):
    started_at = time.perf_counter()
    doc = frappe.get_cached_doc(doctype, invoice_name)
    log_perf_event(
        "get_draft_invoice_doc",
        started_at,
        doctype=doctype,
        invoice=invoice_name,
        items=len(getattr(doc, "items", []) or []),
    )
    return doc


@frappe.whitelist()
def delete_invoice(invoice):
    from frappe import _
    from posawesome.posawesome.api.invoice import delete_invoice_submission_ledger_entries_for_invoice

    doctype = "Sales Invoice"
    if frappe.db.exists("POS Invoice", invoice):
        doctype = "POS Invoice"
    elif not frappe.db.exists("Sales Invoice", invoice):
        frappe.throw(_("Invoice {0} does not exist").format(invoice))

    if frappe.db.has_column(doctype, "posa_is_printed") and frappe.get_value(
        doctype, invoice, "posa_is_printed"
    ):
        frappe.throw(_("This invoice {0} cannot be deleted").format(invoice))

    frappe.delete_doc(doctype, invoice, force=1)
    delete_invoice_submission_ledger_entries_for_invoice(doctype, invoice)
    return _("Invoice {0} Deleted").format(invoice)


@frappe.whitelist()
def fetch_exchange_rate_pair(from_currency, to_currency):
    """Return exchange rate payload expected by POS multi-currency UI."""

    if not from_currency or not to_currency:
        frappe.throw("from_currency and to_currency are required")

    if from_currency == to_currency:
        from frappe.utils import nowdate

        return {
            "exchange_rate": 1,
            "date": nowdate(),
        }

    exchange_rate, rate_date = get_latest_rate(from_currency, to_currency)
    return {
        "exchange_rate": exchange_rate,
        "date": rate_date,
    }


@frappe.whitelist()
def create_sales_invoice_from_order(sales_order):
    """Backward-compatible facade for legacy frontend method path."""

    if not sales_order:
        frappe.throw("sales_order is required")

    if not frappe.db.exists("Sales Order", sales_order):
        frappe.throw(f"Sales Order {sales_order} does not exist")

    invoice_doc = make_sales_invoice(sales_order)
    invoice_doc.flags.ignore_permissions = True
    invoice_doc.run_method("set_missing_values")
    invoice_doc.run_method("calculate_taxes_and_totals")
    return invoice_doc


@frappe.whitelist()
def delete_sales_invoice(sales_invoice):
    """Backward-compatible facade for legacy frontend method path."""

    if not sales_invoice:
        frappe.throw("sales_invoice is required")

    if frappe.db.exists("Sales Invoice", sales_invoice):
        frappe.delete_doc("Sales Invoice", sales_invoice, force=1)
    return True


@frappe.whitelist()
def update_invoice_from_order(data):
    """Backward-compatible facade used by order-to-invoice flow."""

    return update_invoice(data)
