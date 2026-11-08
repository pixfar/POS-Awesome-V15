import frappe
import erpnext
from frappe import _
from frappe.utils import nowdate, flt
from erpnext.accounts.party import get_party_account
from erpnext.accounts.utils import get_account_currency
from erpnext.setup.utils import get_exchange_rate
from erpnext.accounts.doctype.bank_account.bank_account import get_party_bank_account
from posawesome.posawesome.api.idempotency import doctype_supports_client_request_id
from posawesome.posawesome.api.payment_processing.utils import (
    get_bank_cash_account,
    get_pos_change_account,
    set_paid_amount_and_received_amount
)

def create_payment_entry(
    company,
    amount,
    currency,
    mode_of_payment,
    customer=None,
    party=None,
    party_type="Customer",
    payment_type="Receive",
    exchange_rate=None,
    reference_date=None,
    reference_no=None,
    posting_date=None,
    cost_center=None,
    submit=0,
    client_request_id=None,
    override_account=None,
):
    date = nowdate() if not posting_date else posting_date
    party = party or customer

    # Cache commonly used values
    company_doc = frappe.get_cached_doc("Company", company)
    company_currency = company_doc.default_currency
    letter_head = company_doc.default_letter_head

    # Get party account and currency
    party_account = get_party_account(party_type, party, company)
    if not party_account:
        frappe.throw(_(
            "No default {0} account set for {1}"
        ).format("receivable" if party_type == "Customer" else "payable", party))
    party_account_currency = get_account_currency(party_account)

    # Get bank details BEFORE validation
    bank = get_bank_cash_account(company, mode_of_payment)
    if not bank:
        frappe.throw(_("Bank/Cash account not found for mode of payment {0}").format(mode_of_payment))

    # Validate currency: frontend always sends bank currency (physical cash)
    expected_currency = bank.account_currency
    if currency != expected_currency:
        frappe.throw(_(
            "Currency is not correct. Expected {expected}, got {currency}"
        ).format(expected=expected_currency, currency=currency))

    # Get exchange rate
    if exchange_rate and flt(exchange_rate) > 0:
        conversion_rate = flt(exchange_rate)
    else:
        conversion_rate = get_exchange_rate(
            currency, company_currency, date,
            "for_buying" if payment_type == "Pay" else "for_selling"
        )

    # Create payment entry with metadata only
    pe = frappe.new_doc("Payment Entry")
    pe.payment_type = payment_type
    pe.company = company
    pe.cost_center = cost_center or erpnext.get_default_cost_center(company)
    pe.posting_date = date
    pe.mode_of_payment = mode_of_payment
    pe.party_type = party_type
    pe.party = party
    # Company-side account (paid_to for Receive/customer, paid_from for
    # Pay/supplier) is the submitting cashier's POS Profile
    # account_for_change_amount rather than the mode of payment's own
    # account, so accounting can be tracked per showroom. `override_account`
    # (System Manager / BSP Admin only -- re-verified by the caller, never
    # trusted from the client alone) takes priority when set, same "Accounts"
    # override convention as the Sales/Purchase Invoice and Expense Claim
    # screens, letting an admin route this payment through a different
    # showroom's cash account. Falls back to the mode of payment's account
    # if neither is available.
    company_account = override_account or get_pos_change_account() or bank.account
    pe.paid_from = party_account if payment_type == "Receive" else company_account
    pe.paid_to = party_account if payment_type == "Pay" else company_account
    pe.paid_from_account_currency = (
        party_account_currency if payment_type == "Receive" else bank.account_currency
    )
    pe.paid_to_account_currency = party_account_currency if payment_type == "Pay" else bank.account_currency
    pe.letter_head = letter_head
    pe.reference_date = reference_date
    pe.reference_no = reference_no

    if client_request_id and doctype_supports_client_request_id("Payment Entry"):
        pe.posa_client_request_id = client_request_id

    # Set bank account if available
    if pe.party_type in ["Customer", "Supplier"]:
        bank_account = get_party_bank_account(pe.party_type, pe.party)
        if bank_account:
            pe.bank_account = bank_account
            pe.set_bank_account_data()

    # Let ERPNext fill missing metadata (party name, contact, defaults)
    pe.setup_party_account_field()
    pe.set_missing_values()

    # NOW override with our multi-currency calculations
    bank_amount = flt(amount)
    precision = flt(frappe.db.get_default("currency_precision") or 2)

    if party_account_currency != bank.account_currency:
        bank_to_base = conversion_rate
        party_to_base = flt(get_exchange_rate(party_account_currency, company_currency, date))

        if payment_type == "Receive":
            pe.received_amount = bank_amount
            pe.source_exchange_rate = party_to_base
            pe.target_exchange_rate = bank_to_base
            pe.paid_amount = flt(bank_amount * bank_to_base / party_to_base, precision)
        else:  # Pay
            pe.paid_amount = bank_amount
            pe.source_exchange_rate = bank_to_base
            pe.target_exchange_rate = party_to_base
            pe.received_amount = flt(bank_amount * bank_to_base / party_to_base, precision)

        pe.base_paid_amount = flt(pe.paid_amount * pe.source_exchange_rate, precision)
        pe.base_received_amount = flt(pe.received_amount * pe.target_exchange_rate, precision)
    else:
        paid_amount, received_amount = set_paid_amount_and_received_amount(
            party_account_currency, bank, amount, payment_type, None, conversion_rate
        )
        pe.paid_amount = paid_amount
        pe.received_amount = received_amount
        # Defensive: ensure base amounts are set for same-currency case
        if not pe.base_paid_amount:
            pe.base_paid_amount = flt(paid_amount)
        if not pe.base_received_amount:
            pe.base_received_amount = flt(received_amount)

    if submit:
        pe.insert(ignore_permissions=True)
        pe.submit()

    return pe


def _payments_allocated_to_invoice(doctype, invoice_name):
    """Submitted Payment Entry rows allocated against one invoice."""
    rows = frappe.get_all(
        "Payment Entry Reference",
        filters={"reference_doctype": doctype, "reference_name": invoice_name},
        fields=["parent", "allocated_amount"],
    )
    out = []
    for row in rows:
        if frappe.db.get_value("Payment Entry", row.parent, "docstatus") != 1:
            continue
        amount = abs(flt(row.allocated_amount))
        if amount <= 0.0001:
            continue
        out.append(frappe._dict(parent=row.parent, allocated_amount=amount))
    return out


def _already_refunded_for_invoice(doctype, invoice_name):
    """Cash already paid out for submitted returns against this invoice."""
    returns = frappe.get_all(
        doctype,
        filters={"return_against": invoice_name, "is_return": 1, "docstatus": 1},
        pluck="name",
    )
    if not returns:
        return 0.0

    total = 0.0
    for row in frappe.get_all(
        "Payment Entry Reference",
        filters={"reference_doctype": doctype, "reference_name": ["in", returns]},
        fields=["parent", "allocated_amount"],
    ):
        if frappe.db.get_value("Payment Entry", row.parent, "docstatus") != 1:
            continue
        total += abs(flt(row.allocated_amount))
    return total


def _return_finishes_original_invoice(original_doc, return_doc, doctype):
    """True when this return (plus prior submitted ones) covers all goods."""
    original = abs(flt(original_doc.get("discount_amount")))
    source_base = abs(flt(original_doc.grand_total)) + original
    return_base = abs(sum(flt(row.amount) for row in return_doc.get("items") or []))
    prior = frappe.get_all(
        doctype,
        filters={
            "return_against": original_doc.name,
            "is_return": 1,
            "docstatus": 1,
            "name": ["!=", return_doc.name or ""],
        },
        pluck="name",
    )
    already_items = 0.0
    if prior:
        item_dt = doctype + " Item"
        already_items = abs(
            flt(
                frappe.db.sql(
                    f"""
                    SELECT COALESCE(SUM(amount), 0)
                    FROM `tab{item_dt}`
                    WHERE parent IN %s
                    """,
                    (prior,),
                )[0][0]
            )
        )
    return (already_items + return_base) >= (source_base - 0.0001)


def refund_payments_for_return(original_doc, return_doc, doctype):
    """When a Sales/Purchase Invoice being returned has one or more submitted
    Payment Entries allocated against it (paid via a separate Payment Entry,
    not the invoice's own inline POS payment table), create reversing Payment
    Entries so the money is refunded through the same account and mode of
    payment it originally moved through.

    Shop rules:
    - If paid still covers this return in full, refund the return amount
      (e.g. bill 7200, paid 5000, return 3600 → refund 3600; due stays 2200).
    - If paid is less than the return, do not pay cash out — keep the payment
      on the account and let the credit reduce due
      (e.g. after-discount 7000, paid 1000, return 3000 → refund 0; due 3000).
    - When this return finishes the whole bill, pay back any paid amount that
      is still unrefunded so a completed return cannot leave stranded cash.

    For Purchase Invoice, bsp_engineering's on_submit hook often settles the
    return first when custom_is_paid is set; this then finds nothing left and
    is a no-op. Sales/POS Invoice use this as the real refund path.

    Returns the list of created refund Payment Entry names."""
    return_total = abs(flt(return_doc.grand_total))
    if return_total <= 0.0001:
        return []

    ref_rows = _payments_allocated_to_invoice(doctype, original_doc.name)
    if not ref_rows:
        return []

    total_paid = sum(row.allocated_amount for row in ref_rows)
    already = _already_refunded_for_invoice(doctype, original_doc.name)
    remaining_paid = max(total_paid - already, 0)
    if remaining_paid <= 0.0001:
        return []

    if remaining_paid + 0.0001 >= return_total:
        refund_needed = return_total
    elif _return_finishes_original_invoice(original_doc, return_doc, doctype):
        refund_needed = remaining_paid
    else:
        # Paid is smaller than this return and goods still remain — keep the
        # payment applied; due becomes grand - paid - return.
        return []

    if refund_needed <= 0.0001:
        return []

    from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

    created = []
    for ref in ref_rows:
        this_refund = flt(ref.allocated_amount) / total_paid * refund_needed
        if this_refund <= 0.0001:
            continue

        original_pe = frappe.get_doc("Payment Entry", ref.parent)
        # get_payment_entry builds a correctly-typed (Pay for a sales
        # return, Receive for a purchase return), correctly-referenced draft
        # against the *return* document, defaulting to its full outstanding
        # amount in one reference row -- amount/accounts are adjusted below.
        refund_pe = get_payment_entry(doctype, return_doc.name)
        base_amount = abs(flt(refund_pe.paid_amount or refund_pe.received_amount or 0))
        if not base_amount:
            continue
        pe_ratio = this_refund / base_amount

        refund_pe.mode_of_payment = original_pe.mode_of_payment
        # Reverse through the exact same two accounts the original payment
        # used, just swapped -- not whatever account this mode of payment or
        # POS profile would default to today, which may not be the same one.
        refund_pe.paid_from = original_pe.paid_to
        refund_pe.paid_to = original_pe.paid_from
        refund_pe.paid_from_account_currency = original_pe.paid_to_account_currency
        refund_pe.paid_to_account_currency = original_pe.paid_from_account_currency
        refund_pe.paid_amount = abs(flt(refund_pe.paid_amount) * pe_ratio)
        refund_pe.received_amount = abs(flt(refund_pe.received_amount) * pe_ratio)
        refund_pe.base_paid_amount = abs(flt(refund_pe.base_paid_amount) * pe_ratio)
        refund_pe.base_received_amount = abs(flt(refund_pe.base_received_amount) * pe_ratio)
        for row in refund_pe.references:
            row.allocated_amount = flt(row.allocated_amount) * pe_ratio
        refund_pe.reference_no = f"Refund of {original_pe.name} for return {return_doc.name}"
        refund_pe.reference_date = return_doc.posting_date

        refund_pe.insert(ignore_permissions=True)
        refund_pe.submit()
        created.append(refund_pe.name)

    return created
