# Copyright (c) 2021, Youssef Restom and contributors
# For license information, please see license.txt

"""Compatibility facade for payment-entry APIs.

This module intentionally re-exports functions from `payment_processing/*`
to preserve stable dotted paths used by existing clients and hooks.
"""

import json
import frappe
from frappe import _
from frappe.utils import flt, nowdate
from posawesome.posawesome.api.payment_processing.creation import create_payment_entry
from posawesome.posawesome.api.payment_processing.utils import (
    get_bank_cash_account,
    set_paid_amount_and_received_amount,
    get_party_account,
)
from posawesome.posawesome.api.payment_processing.data import (
    get_outstanding_invoices,
    get_unallocated_payments,
    get_available_pos_profiles,
    get_unreconciled_entries,
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


@frappe.whitelist()
def get_all_outstanding_invoices(company=None, party_type="Customer", page_length=200):
    """Return outstanding invoices for a company without filtering by party.

    Used to populate the invoice list before a customer/supplier is selected.
    """
    company = company or _default_company()
    if not company:
        return []

    party_type = party_type or "Customer"
    page_length = max(1, min(int(page_length or 200), 500))

    doctype = "Purchase Invoice" if party_type == "Supplier" else "Sales Invoice"
    party_field = "supplier" if party_type == "Supplier" else "customer"
    name_field = "supplier_name" if party_type == "Supplier" else "customer_name"

    invoices = frappe.get_list(
        doctype,
        filters={"company": company, "docstatus": 1, "outstanding_amount": (">", 0)},
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
        order_by="posting_date desc, name desc",
        limit_page_length=page_length,
    )

    return [
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
):
    """Create Payment Entry(ies) directly without requiring POS profile setup.

    Accepts multiple payment methods and allocates against selected invoices.
    Each mode of payment creates one Payment Entry; allocations are distributed
    across entries in order until all selected invoices are covered.
    """
    if isinstance(payment_methods, str):
        payment_methods = json.loads(payment_methods)
    if isinstance(selected_invoices, str):
        selected_invoices = json.loads(selected_invoices) if selected_invoices else []
    selected_invoices = selected_invoices or []

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

    # Track remaining outstanding per invoice so we don't over-allocate
    remaining_inv = {
        inv["voucher_no"]: flt(inv.get("outstanding_amount", 0))
        for inv in selected_invoices
    }

    created = []
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

        # Allocate selected invoices up to this payment's amount
        budget = amount
        for inv in selected_invoices:
            inv_no = inv.get("voucher_no")
            if budget <= 0:
                break
            inv_remaining = remaining_inv.get(inv_no, 0)
            if inv_remaining <= 0:
                continue
            allocated = min(inv_remaining, budget)
            inv_doctype = inv.get(
                "voucher_type",
                "Purchase Invoice" if party_type == "Supplier" else "Sales Invoice",
            )
            pe.append(
                "references",
                {
                    "reference_doctype": inv_doctype,
                    "reference_name": inv_no,
                    "due_date": inv.get("due_date"),
                    "total_amount": flt(inv.get("invoice_amount")),
                    "outstanding_amount": inv_remaining,
                    "allocated_amount": allocated,
                },
            )
            remaining_inv[inv_no] -= allocated
            budget -= allocated

        pe.insert(ignore_permissions=True)
        pe.submit()
        created.append(pe.name)

    if not created:
        frappe.throw(_("Payment could not be processed"))

    return {"name": created[0], "payments": created}
