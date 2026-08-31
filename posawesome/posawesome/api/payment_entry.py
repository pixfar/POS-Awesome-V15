# Copyright (c) 2021, Youssef Restom and contributors
# For license information, please see license.txt

"""Compatibility facade for payment-entry APIs.

This module intentionally re-exports functions from `payment_processing/*`
to preserve stable dotted paths used by existing clients and hooks.
"""

import json
import frappe
from frappe import _
from frappe.utils import flt, cint, nowdate, getdate
from erpnext.accounts.party import get_party_account
from erpnext.accounts.utils import get_account_currency
from erpnext.setup.utils import get_exchange_rate
from posawesome.posawesome.api.payment_processing.creation import create_payment_entry
from posawesome.posawesome.utils.warehouse_doc_permissions import (
    is_system_manager,
    is_privileged_invoice_viewer,
    ensure_can_create,
)
from posawesome.posawesome.api.payment_processing.utils import (
    get_bank_cash_account,
    set_paid_amount_and_received_amount,
)
from posawesome.posawesome.api.payment_processing.data import (
    get_outstanding_invoices,
    get_unallocated_payments,
    get_available_pos_profiles,
    get_unreconciled_entries,
    _get_unreconciled_journal_dues,
    _get_unreconciled_journal_dues_for_company,
)
from posawesome.posawesome.api.payment_processing.reconciliation import auto_reconcile_customer_invoices
from posawesome.posawesome.api.payment_processing.processor import process_pos_payment
from posawesome.posawesome.api.payment_processing.journal_entry import create_direct_journal_entry


def _default_company():
    return (
        frappe.defaults.get_user_default("Company")
        or frappe.defaults.get_global_default("Company")
        or ""
    )


def _invoice_sort_key(inv):
    due = inv.get("due_date") or inv.get("posting_date")
    return (
        getdate(due) if due else getdate(nowdate()),
        inv.get("voucher_no") or inv.get("name") or "",
    )


def _resolve_invoices_for_allocation(
    party,
    party_type,
    company,
    selected_invoices,
    auto_allocate,
):
    if selected_invoices:
        return sorted(selected_invoices, key=_invoice_sort_key)

    if not auto_allocate:
        return []

    rows = get_outstanding_invoices(
        party=party,
        party_type=party_type,
        company=company,
        include_all_currencies=True,
    )
    return sorted(rows or [], key=_invoice_sort_key)


def _party_amount_available(pe, party_type):
    payment_type = pe.payment_type
    if payment_type == "Receive":
        return flt(pe.paid_amount), pe.paid_to_account_currency
    return flt(pe.received_amount), pe.paid_from_account_currency


def _allocate_payment_references(pe, party, party_type, company, invoices, posting_date, remaining_inv=None):
    """Allocate payment entry against invoices using ERPNext party-currency amounts."""
    if not invoices:
        pe.total_allocated_amount = 0
        party_amount, _party_currency = _party_amount_available(pe, party_type)
        pe.unallocated_amount = flt(party_amount)
        return 0

    if remaining_inv is None:
        remaining_inv = {}

    party_account = get_party_account(party_type, party, company)
    party_account_currency = get_account_currency(party_account)
    company_currency = frappe.get_cached_value("Company", company, "default_currency")
    precision = flt(frappe.db.get_default("currency_precision") or 2)
    payment_type = pe.payment_type

    bank_amount = (
        flt(pe.received_amount) if payment_type == "Receive" else flt(pe.paid_amount)
    )
    bank_currency = (
        pe.paid_to_account_currency if payment_type == "Receive"
        else pe.paid_from_account_currency
    )

    if bank_currency == party_account_currency:
        remaining_party = flt(bank_amount, precision)
    elif bank_currency == company_currency:
        comp_to_party = flt(
            get_exchange_rate(company_currency, party_account_currency, posting_date)
        )
        remaining_party = flt(bank_amount * comp_to_party, precision)
    else:
        bank_to_party = flt(
            get_exchange_rate(bank_currency, party_account_currency, posting_date)
        )
        remaining_party = flt(bank_amount * bank_to_party, precision)

    total_allocated = 0
    for inv in invoices:
        if remaining_party <= 0:
            break

        voucher_type = inv.get("voucher_type") or (
            "Purchase Invoice" if party_type == "Supplier" else "Sales Invoice"
        )
        inv_no = inv.get("voucher_no") or inv.get("name")
        if not inv_no:
            continue

        # A Journal Entry due (see _get_unreconciled_journal_dues) isn't an
        # invoice -- it has no outstanding_amount/grand_total/conversion_rate
        # fields to read a doc for, so its row already carries everything
        # needed (as derived at query time) instead of being looked up here.
        is_journal_due = voucher_type == "Journal Entry"
        if is_journal_due:
            if inv_no not in remaining_inv:
                remaining_inv[inv_no] = flt(inv.get("outstanding_amount"))
            inv_currency = inv.get("currency") or party_account_currency
            inv_conv_rate = flt(inv.get("conversion_rate")) or 1
            inv_due_date = inv.get("due_date") or inv.get("posting_date")
        else:
            inv_doc = frappe.get_cached_doc(voucher_type, inv_no)
            if inv_no not in remaining_inv:
                remaining_inv[inv_no] = flt(inv_doc.outstanding_amount)
            inv_currency = inv_doc.currency
            inv_conv_rate = flt(inv_doc.conversion_rate) or 1
            inv_due_date = inv_doc.due_date

        if remaining_inv[inv_no] <= 0:
            continue

        if inv_currency == party_account_currency:
            inv_outstanding_party = flt(remaining_inv[inv_no])
            inv_total_party = (
                inv_outstanding_party
                if is_journal_due
                else flt(inv_doc.grand_total or inv_doc.rounded_total or inv_outstanding_party)
            )
        elif party_account_currency == company_currency:
            inv_outstanding_party = flt(
                remaining_inv[inv_no] * inv_conv_rate, precision
            )
            inv_total_party = (
                inv_outstanding_party
                if is_journal_due
                else flt(
                    inv_doc.base_rounded_total
                    or inv_doc.base_grand_total
                    or inv_outstanding_party
                )
            )
        else:
            inv_to_party = flt(
                get_exchange_rate(inv_currency, party_account_currency, posting_date)
            )
            inv_outstanding_party = flt(
                remaining_inv[inv_no] * inv_to_party, precision
            )
            inv_total_party = (
                inv_outstanding_party
                if is_journal_due
                else flt(
                    (inv_doc.base_rounded_total or inv_doc.base_grand_total)
                    * inv_to_party,
                    precision,
                )
            )

        if inv_outstanding_party <= 0:
            continue

        allocation = min(remaining_party, inv_outstanding_party)
        if allocation <= 0:
            continue

        pe.append(
            "references",
            {
                "reference_doctype": voucher_type,
                "reference_name": inv_no,
                "due_date": inv_due_date,
                "total_amount": inv_total_party,
                "outstanding_amount": inv_outstanding_party,
                "allocated_amount": allocation,
            },
        )
        remaining_party -= allocation
        total_allocated = flt(total_allocated + allocation, precision)

        if inv_currency == party_account_currency:
            remaining_inv[inv_no] -= allocation
        elif party_account_currency == company_currency:
            remaining_inv[inv_no] -= flt(allocation / inv_conv_rate, precision) if inv_conv_rate else allocation
        else:
            inv_to_party = flt(
                get_exchange_rate(inv_currency, party_account_currency, posting_date)
            ) or 1
            remaining_inv[inv_no] -= flt(allocation / inv_to_party, precision)

    party_amount, _party_currency = _party_amount_available(pe, party_type)
    pe.total_allocated_amount = total_allocated
    pe.unallocated_amount = flt(party_amount - total_allocated, precision)
    return total_allocated


@frappe.whitelist()
def get_all_outstanding_invoices(
    company=None,
    party_type="Customer",
    page_start=0,
    page_length=10,
):
    """Return outstanding invoices for a company without filtering by party.

    Includes both invoice-based dues and dues posted directly via Journal
    Entry (e.g. opening balances from data migration) -- see
    _get_unreconciled_journal_dues_for_company. Invoice and JE rows come from
    two separate queries with no shared ordering key, so they're merged and
    paginated here in Python rather than at the SQL level; MAX_ROWS caps the
    invoice fetch to keep that bounded on a company with a very large number
    of outstanding invoices.
    """
    company = company or _default_company()
    if not company:
        return {"invoices": [], "total": 0, "has_more": False}

    party_type = party_type or "Customer"
    page_start = max(0, int(page_start or 0))
    page_length = max(1, min(int(page_length or 10), 100))

    doctype = "Purchase Invoice" if party_type == "Supplier" else "Sales Invoice"
    party_field = "supplier" if party_type == "Supplier" else "customer"
    name_field = "supplier_name" if party_type == "Supplier" else "customer_name"

    MAX_ROWS = 2000
    filters = {"company": company, "docstatus": 1, "outstanding_amount": (">", 0)}

    invoices = frappe.get_list(
        doctype,
        filters=filters,
        fields=[
            "name",
            "posting_date",
            "due_date",
            "outstanding_amount",
            "grand_total",
            "currency",
            f"`tab{doctype}`.`{party_field}` as party",
            f"`tab{doctype}`.`{name_field}` as party_name",
        ],
        order_by="posting_date asc, name asc",
        limit_page_length=MAX_ROWS,
    )

    rows = [
        {
            "voucher_no": inv.name,
            "voucher_type": doctype,
            "outstanding_amount": flt(inv.outstanding_amount),
            "invoice_amount": flt(inv.grand_total),
            "due_date": str(inv.due_date) if inv.due_date else "",
            "posting_date": str(inv.posting_date) if inv.posting_date else "",
            "currency": inv.currency or "",
            "party": inv.party or "",
            "party_name": inv.party_name or inv.party or "",
        }
        for inv in invoices
    ]
    rows.extend(_get_unreconciled_journal_dues_for_company(company, party_type))
    rows.sort(key=lambda r: (r["posting_date"] or "", r["voucher_no"] or ""))

    total = len(rows)
    page = rows[page_start : page_start + page_length]

    return {
        "invoices": page,
        "total": total,
        "has_more": (page_start + page_length) < total,
    }


@frappe.whitelist()
def get_payment_history(
    party,
    party_type="Customer",
    company=None,
    page_start=0,
    page_length=10,
):
    """Paginated payment entry history for a party."""
    if not party:
        return {"payments": [], "total": 0, "has_more": False}

    company = company or _default_company()
    page_start = max(0, int(page_start or 0))
    page_length = max(1, min(int(page_length or 10), 100))

    filters = {
        "party_type": party_type,
        "party": party,
        "docstatus": 1,
    }
    if company:
        filters["company"] = company

    total = frappe.db.count("Payment Entry", filters)
    rows = frappe.get_list(
        "Payment Entry",
        filters=filters,
        fields=[
            "name",
            "posting_date",
            "mode_of_payment",
            "paid_amount",
            "unallocated_amount",
            "payment_type",
            "reference_no",
        ],
        order_by="posting_date desc, creation desc",
        limit_start=page_start,
        limit_page_length=page_length,
    )

    payment_names = [row.name for row in rows]
    refs_by_payment = {}
    if payment_names:
        ref_rows = frappe.get_all(
            "Payment Entry Reference",
            filters={
                "parent": ["in", payment_names],
                "allocated_amount": [">", 0],
            },
            fields=["parent", "reference_name"],
            order_by="idx asc",
        )
        for ref in ref_rows:
            if not ref.reference_name:
                continue
            refs_by_payment.setdefault(ref.parent, []).append(ref.reference_name)

    payments = []
    for row in rows:
        paid = flt(row.paid_amount)
        unallocated = flt(row.unallocated_amount)
        allocated = max(paid - unallocated, 0)
        invoice_refs = refs_by_payment.get(row.name, [])
        reference_no = (row.reference_no or "").strip() or ", ".join(invoice_refs)

        payments.append(
            {
                **row,
                "allocated_amount": allocated,
                "reference_no": reference_no,
            }
        )

    return {
        "payments": payments,
        "total": total,
        "has_more": (page_start + page_length) < total,
    }


@frappe.whitelist()
def get_payment_entries_list(
    pos_profile=None,
    company=None,
    page_start=0,
    page_length=20,
    mine_only=0,
    party_type=None,
    party=None,
    mode_of_payment=None,
    payment_type=None,
    from_date=None,
    to_date=None,
    search=None,
):
    """Paginated, filterable list of submitted Payment Entries for the Payment List page.

    Payment Entry has no pos_profile field, so scope by company instead (same
    convention as the Purchase Invoice list).
    """
    from posawesome.posawesome.api.purchase_orders import _resolve_pos_profile

    if not company and pos_profile:
        profile = _resolve_pos_profile(pos_profile)
        company = profile.get("company")
    company = company or _default_company()

    doctype = "Payment Entry"
    filters = []
    if company:
        filters.append([doctype, "company", "=", company])
    # Payment Entry has no warehouse field, so restricted users (not System
    # Manager) simply only ever see their own payments.
    if int(mine_only or 0) or not is_system_manager():
        filters.append([doctype, "owner", "=", frappe.session.user])
    if party_type:
        filters.append([doctype, "party_type", "=", party_type])
    if party:
        filters.append([doctype, "party", "=", party])
    if mode_of_payment:
        filters.append([doctype, "mode_of_payment", "=", mode_of_payment])
    if payment_type:
        filters.append([doctype, "payment_type", "=", payment_type])
    if from_date:
        filters.append([doctype, "posting_date", ">=", from_date])
    if to_date:
        filters.append([doctype, "posting_date", "<=", to_date])

    or_filters = None
    if search:
        like = f"%{search}%"
        or_filters = [
            [doctype, "name", "like", like],
            [doctype, "party", "like", like],
            [doctype, "party_name", "like", like],
            [doctype, "reference_no", "like", like],
        ]

    page_start = max(0, int(page_start or 0))
    page_length = max(1, min(int(page_length or 20), 200))

    fields = [
        "name",
        "posting_date",
        "party_type",
        "party",
        "party_name",
        "payment_type",
        "mode_of_payment",
        "paid_amount",
        "received_amount",
        "reference_no",
        "company",
        "owner",
        "docstatus",
    ]

    rows = frappe.get_list(
        doctype,
        filters=filters,
        or_filters=or_filters,
        fields=fields,
        order_by="posting_date desc, creation desc",
        limit_start=page_start,
        limit_page_length=page_length,
        distinct=True,
        ignore_permissions=True,
    )
    for row in rows:
        row["amount"] = flt(row.get("paid_amount"))

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

    type_filters = [f for f in filters if not (f[0] == doctype and f[1] == "payment_type")]
    type_counts = {
        row.payment_type: row.count
        for row in frappe.get_list(
            doctype,
            filters=type_filters,
            or_filters=or_filters,
            fields=["payment_type", "count(name) as count"],
            group_by="payment_type",
            ignore_permissions=True,
            limit_page_length=0,
        )
    }

    total_amount = frappe.get_list(
        doctype,
        filters=filters,
        or_filters=or_filters,
        fields=["sum(paid_amount) as total"],
        ignore_permissions=True,
    )
    total_amount = flt(total_amount[0].total) if total_amount else 0

    return {
        "payments": rows,
        "total": total,
        "has_more": (page_start + page_length) < total,
        "type_counts": type_counts,
        "total_amount": total_amount,
    }


@frappe.whitelist()
def get_payment_entry_detail(name):
    """Full detail (header + allocated references) for the Payment List's detail page."""
    doc = frappe.get_doc("Payment Entry", name)
    owner_name = frappe.db.get_value("User", doc.owner, "full_name") or doc.owner

    return {
        "name": doc.name,
        "posting_date": doc.posting_date,
        "company": doc.company,
        "party_type": doc.party_type,
        "party": doc.party,
        "party_name": doc.party_name,
        "payment_type": doc.payment_type,
        "mode_of_payment": doc.mode_of_payment,
        "paid_amount": flt(doc.paid_amount),
        "received_amount": flt(doc.received_amount),
        "total_allocated_amount": flt(doc.total_allocated_amount),
        "unallocated_amount": flt(doc.unallocated_amount),
        "reference_no": doc.reference_no,
        "reference_date": doc.reference_date,
        "paid_from": doc.paid_from,
        "paid_to": doc.paid_to,
        "remarks": doc.remarks,
        "created_by": owner_name,
        "creation": doc.creation,
        "amended_from": doc.get("amended_from"),
        "items": [
            {
                "reference_doctype": row.reference_doctype,
                "reference_name": row.reference_name,
                "total_amount": flt(row.total_amount),
                "outstanding_amount": flt(row.outstanding_amount),
                "allocated_amount": flt(row.allocated_amount),
            }
            for row in (doc.get("references") or [])
        ],
        "docstatus": doc.docstatus,
    }


@frappe.whitelist()
def cancel_payment_entry(name):
    """Cancel a submitted Payment Entry. Restricted to System Manager, matching
    the Sales/Purchase Invoice cancel gate elsewhere in POS Awesome. ERPNext's
    own Payment Entry controller reverses its GL Entries on cancel."""
    if "System Manager" not in frappe.get_roles(frappe.session.user):
        frappe.throw(
            _("Only a user with the System Manager role can cancel this document."),
            frappe.PermissionError,
        )

    doc = frappe.get_doc("Payment Entry", name)
    if doc.docstatus != 1:
        frappe.throw(_("Only a submitted document can be cancelled."))

    doc.cancel()
    return {"name": doc.name, "docstatus": doc.docstatus}


@frappe.whitelist()
def delete_cancelled_payment_entry(name):
    """Permanently delete a Draft or Cancelled Payment Entry."""
    if not is_system_manager():
        frappe.throw(
            _("Only a System Manager can delete Payment Entries."),
            exc=frappe.PermissionError,
        )

    if frappe.db.get_value("Payment Entry", name, "docstatus") not in (0, 2):
        frappe.throw(_("Only a draft or cancelled document can be deleted."))

    frappe.delete_doc("Payment Entry", name)
    return {"name": name}


@frappe.whitelist()
def get_party_outstanding(party, party_type="Customer", company=None):
    """Return total outstanding amount (and row count) for a customer or
    supplier.

    Includes both invoice-based dues (Sales/Purchase Invoice) and dues that
    were posted directly via Journal Entry -- e.g. opening balances brought
    over at data migration instead of through an invoice. See
    _get_unreconciled_journal_dues for how a JE row's outstanding amount is
    derived. `count` powers the "N Outstanding Invoices" label in the
    frontend -- cheap to add here (a single extra COUNT(*) alongside the
    SUM already being computed) rather than a second round trip, and it's
    the true total regardless of how many rows the paginated invoice list
    has loaded so far.
    """
    if not party:
        return {"outstanding": 0, "count": 0}

    company = company or _default_company()
    if party_type == "Supplier":
        doctype = "Purchase Invoice"
        party_field = "supplier"
    else:
        doctype = "Sales Invoice"
        party_field = "customer"

    outstanding, invoice_count = frappe.db.sql(
        f"""
        SELECT COALESCE(SUM(outstanding_amount), 0), COUNT(*)
        FROM `tab{doctype}`
        WHERE {party_field} = %(party)s
          AND docstatus = 1
          AND outstanding_amount > 0
          {("AND company = %(company)s" if company else "")}
        """,
        {"party": party, "company": company},
    )[0]

    journal_dues = _get_unreconciled_journal_dues(
        party=party,
        party_type=party_type,
        company=company,
        include_all_currencies=True,
    )
    outstanding = flt(outstanding) + sum(flt(row.get("outstanding_amount")) for row in journal_dues)
    count = cint(invoice_count) + len(journal_dues)

    return {"outstanding": flt(outstanding), "count": count}


@frappe.whitelist()
def make_payment_direct(
    party,
    party_type,
    company,
    payment_methods,
    posting_date=None,
    selected_invoices=None,
    reference_no=None,
    reference_date=None,
    auto_allocate=False,
):
    """Create Payment Entry(ies) with ERPNext-style invoice allocation."""
    ensure_can_create(_("create a Payment"))

    # Same gate as Fund Transfer creation (see fund_transfer.py's
    # _require_fund_transfer_manager) -- Supplier Payment is a money-out
    # action restricted to BSP Admin/System Manager. The POS frontend already
    # hides the "Supplier Payment" entry points for everyone else; this is
    # the actual enforcement, since a hidden button alone doesn't stop a
    # direct API call.
    if party_type == "Supplier" and not is_privileged_invoice_viewer():
        frappe.throw(
            _("Only a user with the BSP Admin or System Manager role can make a Supplier Payment."),
            frappe.PermissionError,
        )

    if isinstance(payment_methods, str):
        payment_methods = json.loads(payment_methods)
    if isinstance(selected_invoices, str):
        selected_invoices = json.loads(selected_invoices) if selected_invoices else []
    selected_invoices = selected_invoices or []
    auto_allocate = frappe.parse_json(auto_allocate) if isinstance(
        auto_allocate, str
    ) else bool(auto_allocate)

    if not party:
        frappe.throw(_("Party is required"))

    company = company or _default_company()
    if not company:
        frappe.throw(_("Company is required. Please configure a default company."))

    payment_type = "Pay" if party_type == "Supplier" else "Receive"
    posting_date = posting_date or nowdate()

    active_methods = [m for m in (payment_methods or []) if flt(m.get("amount")) > 0]
    if not active_methods:
        frappe.throw(_("Please enter a payment amount"))

    invoices_to_allocate = _resolve_invoices_for_allocation(
        party, party_type, company, selected_invoices, auto_allocate
    )

    created = []
    remaining_inv = {}

    for method in active_methods:
        mode_of_payment = method.get("mode_of_payment")
        amount = flt(method.get("amount"))

        bank = get_bank_cash_account(company, mode_of_payment)
        if not bank:
            frappe.throw(
                _("No bank/cash account configured for mode of payment: {0}").format(
                    mode_of_payment
                )
            )

        pe = create_payment_entry(
            company=company,
            amount=amount,
            currency=bank.account_currency,
            mode_of_payment=mode_of_payment,
            party=party,
            party_type=party_type,
            payment_type=payment_type,
            reference_no=reference_no or None,
            reference_date=reference_date or None,
            posting_date=posting_date,
        )

        if invoices_to_allocate:
            _allocate_payment_references(
                pe,
                party,
                party_type,
                company,
                invoices_to_allocate,
                posting_date,
                remaining_inv,
            )
        else:
            pe.total_allocated_amount = 0
            party_amount, _party_currency = _party_amount_available(pe, party_type)
            pe.unallocated_amount = flt(party_amount)

        pe.insert(ignore_permissions=True)
        pe.submit()
        created.append(pe.name)

    if not created:
        frappe.throw(_("Payment could not be processed"))

    return {"name": created[0], "payments": created}
