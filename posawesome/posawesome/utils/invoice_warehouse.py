# Copyright (c) 2026, POS Awesome and contributors
# For license information, please see license.txt

"""Single source of truth for which warehouse each line of a POS sale uses.

Rules (Sales Invoice / POS Invoice created from POS Awesome, i.e. with a
pos_profile):

* Every stock item line uses the invoice's own ``set_warehouse`` -- the
  warehouse the cashier actually selected for this sale.
* A non-stock item line (service / labour charges) carries **no** warehouse
  at all. It never touches stock, so showing the POS Profile's default
  warehouse on it only misleads.
* Product Bundle parents are treated like stock lines so their packed items
  inherit the selected warehouse.

Whether a line is a stock item is always read from the Item master. It used to
be read from an ``is_stock_item`` attribute on the line itself, but that is not
a Sales Invoice Item field -- it only exists on rows the browser built, and is
lost whenever the invoice is saved and reloaded from the server. Every line
coming back from the database looked like a non-stock item, so the warehouse
switch silently skipped it and ERPNext's own POS defaults
(``set_pos_fields``) left it on the POS Profile's warehouse.

ERPNext also blanks ``set_warehouse`` at the end of validate whenever the item
lines don't all share one warehouse (``reset_default_field_value``) -- which a
blank non-stock line always triggers. ``capture_sale_warehouse`` therefore
remembers the selected warehouse in ``before_validate`` and
``enforce_sale_warehouse`` puts it back afterwards.

The sale's cash/bank account follows the same warehouse: each warehouse lists
its own accounts (Warehouse.custom_cash_accounts, "Cash / Bank Accounts").
``apply_sale_cash_account`` keeps the payment account if it is one of the sale
warehouse's accounts and otherwise switches it to that warehouse's first one,
so a sale's money is never booked to a different warehouse than its stock.
"""

import frappe
from frappe.utils import cint

POS_SALE_DOCTYPES = ("Sales Invoice", "POS Invoice")
WAREHOUSE_CASH_ACCOUNT_DOCTYPE = "Warehouse Cash Account"
SALE_WAREHOUSE_FLAG = "posa_sale_warehouse"


def _get(row, fieldname):
    if isinstance(row, dict):
        return row.get(fieldname)
    return row.get(fieldname) if hasattr(row, "get") else getattr(row, fieldname, None)


def _set(row, fieldname, value):
    if isinstance(row, dict):
        row[fieldname] = value
    else:
        setattr(row, fieldname, value)


def get_stock_item_flags(item_codes):
    """Return ``{item_code: True/False}`` -- True when the line needs a warehouse.

    Unknown item codes are simply absent from the result.
    """
    codes = sorted({code for code in (item_codes or []) if code})
    if not codes:
        return {}

    flags = {
        row.name: bool(cint(row.is_stock_item))
        for row in frappe.get_all(
            "Item",
            filters={"name": ["in", codes]},
            fields=["name", "is_stock_item"],
        )
    }
    for bundle in frappe.get_all(
        "Product Bundle",
        filters={"new_item_code": ["in", codes], "disabled": 0},
        pluck="new_item_code",
    ):
        flags[bundle] = True
    return flags


def apply_sale_warehouse(doc, warehouse=None):
    """Make every line follow the sale warehouse; works on a Document or a dict.

    ``warehouse`` defaults to the doc's own ``set_warehouse``. When there is no
    sale warehouse at all (e.g. a return keeping its original lines), stock
    lines are left as they are and only non-stock lines are cleared.

    Also stamps ``is_stock_item`` on each line, so a payload returned to the
    browser carries the correct flag.
    """
    target = (warehouse or _get(doc, "set_warehouse") or "").strip() or None
    items = _get(doc, "items") or []
    flags = get_stock_item_flags([_get(row, "item_code") for row in items])

    for row in items:
        is_stock = flags.get(_get(row, "item_code"))
        if is_stock is None:
            continue
        _set(row, "is_stock_item", 1 if is_stock else 0)
        if not is_stock:
            if _get(row, "warehouse"):
                _set(row, "warehouse", None)
        elif target and _get(row, "warehouse") != target:
            _set(row, "warehouse", target)

    if target:
        for row in _get(doc, "packed_items") or []:
            if _get(row, "warehouse") != target:
                _set(row, "warehouse", target)
        _set(doc, "set_warehouse", target)

    return target


def get_warehouse_cash_accounts(warehouse):
    """Accounts on a warehouse's "Cash / Bank Accounts" table, in row order.

    Empty when the warehouse has none configured (or the site doesn't have
    that table at all) -- callers then leave the account untouched.
    """
    if not warehouse or not frappe.db.exists("DocType", WAREHOUSE_CASH_ACCOUNT_DOCTYPE):
        return []
    return frappe.get_all(
        WAREHOUSE_CASH_ACCOUNT_DOCTYPE,
        filters={"parent": warehouse, "parenttype": "Warehouse"},
        pluck="account",
        order_by="idx asc",
    )


def resolve_sale_cash_account(warehouse, current=None):
    """The account a sale from ``warehouse`` must use: ``current`` when it is
    one of the warehouse's accounts, else the warehouse's first account, else
    ``current`` unchanged (nothing configured)."""
    accounts = get_warehouse_cash_accounts(warehouse)
    if not accounts or current in accounts:
        return current
    return accounts[0]


def apply_sale_cash_account(doc, warehouse=None):
    """Point the sale's payment account -- and every payment / payment-split
    row -- at an account belonging to the sale warehouse."""
    target = (warehouse or _get(doc, "set_warehouse") or "").strip() or None
    if not target:
        return None
    rows = (_get(doc, "payments") or []) + (_get(doc, "custom_payment_method_split") or [])
    current = _get(doc, "payment_account") or next(
        (_get(row, "account") for row in rows if _get(row, "account")), None
    )
    account = resolve_sale_cash_account(target, current)
    if not account:
        return None

    _set(doc, "payment_account", account)
    for row in rows:
        if _get(row, "account") != account:
            _set(row, "account", account)
    return account


@frappe.whitelist()
def get_sale_cash_account(warehouse, current=None):
    """For the POS warehouse switch: the account a sale from ``warehouse``
    should use (keeps ``current`` if it belongs to that warehouse)."""
    return resolve_sale_cash_account(warehouse, current or None)


def is_pos_sale(doc):
    return doc.doctype in POS_SALE_DOCTYPES and bool(doc.get("pos_profile"))


def capture_sale_warehouse(doc, method=None):
    """before_validate: remember the selected warehouse before ERPNext's own
    validate can blank it, then normalise the lines."""
    if not is_pos_sale(doc):
        return
    target = doc.get("set_warehouse") or doc.flags.get(SALE_WAREHOUSE_FLAG)
    if target:
        doc.flags[SALE_WAREHOUSE_FLAG] = target
    apply_sale_warehouse(doc, target)
    apply_sale_cash_account(doc, target)


def enforce_sale_warehouse(doc, method=None):
    """validate / before_save / before_submit: re-apply the selected warehouse
    after ERPNext (set_pos_fields, reset_default_field_value) has run."""
    if not is_pos_sale(doc):
        return
    target = doc.flags.get(SALE_WAREHOUSE_FLAG) or doc.get("set_warehouse")
    apply_sale_warehouse(doc, target)
    apply_sale_cash_account(doc, target)
