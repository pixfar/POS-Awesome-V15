import frappe
from frappe import _
from erpnext.accounts.doctype.journal_entry.journal_entry import get_default_bank_cash_account


def get_party_account(party_type, party, company):
    try:
        # First try to get from Party Account
        account = frappe.get_cached_value(
            "Party Account",
            {"parenttype": party_type, "parent": party, "company": company},
            "account",
        )

        if not account:
            # Try to get default account from company
            account = frappe.get_cached_value(
                "Company",
                company,
                ("default_receivable_account" if party_type == "Customer" else "default_payable_account"),
            )

        if not account:
            frappe.log_error(
                f"No account found for {party_type} {party} in company {company}",
                "POS Account Error",
            )

        return account
    except Exception as e:
        frappe.log_error(f"Error getting party account: {str(e)}")
        return None


def get_pos_change_account(user=None):
    """account_for_change_amount from the logged-in user's active POS Profile.

    Used as the company-side account (paid_to for Receive, paid_from for
    Pay) on Payment Entries instead of each mode of payment's own account,
    so accounting can be tracked per showroom. Returns None if the user has
    no active POS Profile or it has no change account set -- callers fall
    back to the mode of payment's account in that case.
    """
    from posawesome.posawesome.api.utils import get_active_pos_profile

    profile = get_active_pos_profile(user) or {}
    return profile.get("account_for_change_amount")


def get_bank_cash_account(company, mode_of_payment, bank_account=None):
    bank = get_default_bank_cash_account(
        company, "Bank", mode_of_payment=mode_of_payment, account=bank_account
    )

    if not bank:
        bank = get_default_bank_cash_account(
            company, "Cash", mode_of_payment=mode_of_payment, account=bank_account
        )

    return bank


def set_paid_amount_and_received_amount(
    party_account_currency,
    bank,
    outstanding_amount,
    payment_type,
    bank_amount,
    conversion_rate,
):
    paid_amount = received_amount = 0
    if party_account_currency == bank.account_currency:
        paid_amount = received_amount = abs(outstanding_amount)
    elif payment_type == "Receive":
        paid_amount = abs(outstanding_amount)
        if bank_amount:
            received_amount = bank_amount
        else:
            received_amount = paid_amount * conversion_rate

    else:
        received_amount = abs(outstanding_amount)
        if bank_amount:
            paid_amount = bank_amount
        else:
            # if party account currency and bank currency is different then populate paid amount as well
            paid_amount = received_amount * conversion_rate

    return paid_amount, received_amount


@frappe.whitelist()
def get_mode_of_payment_accounts(company, mode_of_payments):
    import json

    if isinstance(mode_of_payments, str):
        mode_of_payments = json.loads(mode_of_payments)

    currency_map = {}
    for mode in mode_of_payments:
        account = get_bank_cash_account(company, mode)
        if account:
            currency_map[mode] = account.get("account_currency")
    return currency_map


@frappe.whitelist()
def get_cash_in_hand_accounts(company):
    """Every non-group Cash account under the company's "Cash In Hand"
    parent group -- one per showroom's till, same accounts each POS
    Profile's own account_for_change_amount is picked from. Backs the
    Purchase Invoice screen's admin-only "Accounts" override dropdown
    (System Manager / BSP Admin), so an admin can route a specific
    purchase's payment through a different showroom's cash account than
    their own active POS Profile's default.

    Gated server-side (not just hidden client-side) since this is meant to
    be admin-only functionality, even though the account list itself isn't
    sensitive -- and ignore_permissions on the actual fetch because regular
    POS users generally have no Account-doctype read permission at all,
    which would otherwise make this silently return nothing for them.
    """
    from posawesome.posawesome.utils.warehouse_doc_permissions import is_privileged_invoice_viewer

    if not is_privileged_invoice_viewer():
        frappe.throw(_("Not permitted"), exc=frappe.PermissionError)

    if not company:
        return []

    parent = frappe.db.get_value(
        "Account",
        {"company": company, "account_name": "Cash In Hand", "is_group": 1},
        "name",
    )
    if not parent:
        return []

    return frappe.get_all(
        "Account",
        filters={"company": company, "parent_account": parent, "is_group": 0, "disabled": 0},
        fields=["name", "account_name"],
        order_by="account_name asc",
        ignore_permissions=True,
    )
