# Copyright (c) 2026, POS Awesome contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _
from frappe.utils import cint, flt, nowdate, getdate
from erpnext.accounts.party import get_party_account


from .utils import get_active_pos_profile, get_default_warehouse
from .invoice_processing.creation import _resolve_territory_for_warehouse


def _resolve_pos_profile(pos_profile):
    if isinstance(pos_profile, dict):
        return pos_profile

    if isinstance(pos_profile, str):
        raw_value = pos_profile.strip()
        if raw_value:
            try:
                decoded = json.loads(raw_value)
            except Exception:
                decoded = raw_value

            if isinstance(decoded, dict):
                return decoded
            if isinstance(decoded, str) and decoded:
                return frappe.get_doc("POS Profile", decoded).as_dict()

    profile = get_active_pos_profile()
    if not profile:
        frappe.throw(_("POS Profile is required to create purchase documents."))
    return profile


def _ensure_allowed(profile, flag, label):
    if not cint(profile.get(flag)):
        frappe.throw(_("{0} is disabled for this POS Profile.").format(label))


def _purchase_invoice_allowed(profile):
    return cint(profile.get("posa_allow_purchase_invoice")) or cint(
        profile.get("posa_allow_purchase_order")
    )


def _ensure_purchase_invoice_allowed(profile):
    if not _purchase_invoice_allowed(profile):
        frappe.throw(_("Purchase Invoice is disabled for this POS Profile."))


def _purchase_invoice_has_custom_is_paid():
    return frappe.db.has_column("Purchase Invoice", "custom_is_paid")


def _resolve_supplier(supplier_value):
    if isinstance(supplier_value, dict):
        supplier_value = (
            supplier_value.get("name")
            or supplier_value.get("supplier_name")
            or supplier_value.get("supplier")
        )

    supplier = str(supplier_value or "").strip()
    if not supplier:
        return None

    if frappe.db.exists("Supplier", supplier):
        return supplier

    supplier_by_label = frappe.db.get_value("Supplier", {"supplier_name": supplier}, "name")
    if supplier_by_label:
        return supplier_by_label

    # Fallback: case-insensitive lookup by name/supplier_name
    ci_match = frappe.db.sql(
        """
        select name
        from `tabSupplier`
        where lower(name) = lower(%s)
           or lower(supplier_name) = lower(%s)
        limit 1
        """,
        (supplier, supplier),
    )
    if ci_match and ci_match[0]:
        return ci_match[0][0]

    return None


def _resolve_buying_price_list():
    buying_price_list = frappe.db.get_single_value("Buying Settings", "buying_price_list")
    if not buying_price_list:
        buying_price_list = frappe.db.get_value("Price List", {"buying": 1}, "name")

    if not buying_price_list:
        # Fallback to standard default if exists
        if frappe.db.exists("Price List", "Standard Buying"):
            buying_price_list = "Standard Buying"

    return buying_price_list


def _resolve_supplier_buying_price_list(supplier):
    """Resolve buying price list for a specific supplier.
    Checks Supplier-level default_price_list first, then falls back
    to the generic buying price list from Buying Settings.
    """
    if not supplier:
        return _resolve_buying_price_list()

    supplier_price_list = frappe.db.get_value("Supplier", supplier, "default_price_list")
    if supplier_price_list:
        is_buying = frappe.db.get_value("Price List", supplier_price_list, "buying")
        if is_buying:
            return supplier_price_list

    return _resolve_buying_price_list()


def _normalize_item_codes(item_codes):
    normalized = []

    def visit(value):
        if isinstance(value, (list, tuple, set)):
            for item in value:
                visit(item)
            return

        if isinstance(value, str):
            code = value.strip()
            if code:
                normalized.append(code)
            return

        if isinstance(value, int) and not isinstance(value, bool):
            normalized.append(value)

    visit(item_codes)
    return normalized


def _upsert_item_price(item_code, price_list, rate, uom=None, buying=False, selling=False):
    if not price_list or rate is None:
        return None

    rate = flt(rate)
    filters = {"item_code": item_code, "price_list": price_list}
    if uom:
        filters["uom"] = uom

    existing = frappe.db.get_value("Item Price", filters, "name")
    if existing:
        doc = frappe.get_doc("Item Price", existing)
        doc.price_list_rate = rate
        doc.flags.ignore_permissions = True
        doc.save()
        return doc.name

    doc = frappe.get_doc(
        {
            "doctype": "Item Price",
            "price_list": price_list,
            "item_code": item_code,
            "price_list_rate": rate,
            "buying": 1 if buying else 0,
            "selling": 1 if selling else 0,
            "uom": uom,
        }
    )
    doc.flags.ignore_permissions = True
    doc.insert()
    return doc.name


def _build_items_map(items):
    items_by_code = {}
    for row in items or []:
        item_code = row.get("item_code")
        if not item_code:
            continue
        items_by_code.setdefault(item_code, []).append(row)
    return items_by_code


def _resolve_input_row(items_by_code, item_code):
    rows = items_by_code.get(item_code)
    if not rows:
        return {}
    return rows.pop(0)


def _create_purchase_receipt(po_doc, payload, default_warehouse, transaction_date):
    receipt_date = payload.get("receipt_date") or payload.get("posting_date") or transaction_date
    receipt = frappe.get_doc(
        {
            "doctype": "Purchase Receipt",
            "supplier": po_doc.supplier,
            "company": po_doc.company,
            "posting_date": receipt_date,
            "currency": po_doc.currency,
        }
    )
    if default_warehouse:
        receipt.set_warehouse = default_warehouse

    items_by_code = _build_items_map(payload.get("items"))

    for po_item in po_doc.items:
        payload_row = _resolve_input_row(items_by_code, po_item.item_code)
        if (
            payload.get("receive")
            and not payload_row.get("received_qty")
            and not payload_row.get("receive_qty")
        ):
            payload_row["receive_qty"] = po_item.qty
            payload_row["received_qty"] = po_item.qty
        received_qty = flt(
            payload_row.get("received_qty")
            or payload_row.get("receive_qty")
            or payload_row.get("qty")
            or po_item.qty
        )
        if received_qty <= 0:
            continue

        receipt.append(
            "items",
            {
                "item_code": po_item.item_code,
                "item_name": po_item.item_name,
                "qty": received_qty,
                "uom": po_item.uom,
                "stock_uom": po_item.stock_uom,
                "conversion_factor": po_item.conversion_factor or 1,
                "rate": po_item.rate,
                "warehouse": po_item.warehouse or default_warehouse,
                "purchase_order": po_doc.name,
                "purchase_order_item": po_item.name,
                "schedule_date": po_item.schedule_date,
            },
        )

    if not receipt.items:
        frappe.throw(_("No items to receive. Please enter received quantities."))

    receipt.flags.ignore_permissions = True
    frappe.flags.ignore_account_permission = True
    receipt.insert()
    receipt.submit()
    return receipt.name


def create_supplier(data):
    payload = json.loads(data) if isinstance(data, str) else data
    profile = _resolve_pos_profile(payload.get("pos_profile"))
    _ensure_allowed(profile, "posa_allow_create_purchase_suppliers", _("Create suppliers"))

    supplier_name = payload.get("supplier_name") or payload.get("supplier")
    if not supplier_name:
        frappe.throw(_("Supplier name is required."))

    existing = frappe.db.get_value("Supplier", {"supplier_name": supplier_name}, "name")
    if existing:
        return frappe.get_doc("Supplier", existing).as_dict()

    supplier_group = payload.get("supplier_group") or frappe.db.get_value(
        "Supplier Group", {"is_group": 0}, "name"
    )
    supplier_group = supplier_group or "All Supplier Groups"

    supplier = frappe.get_doc(
        {
            "doctype": "Supplier",
            "supplier_name": supplier_name,
            "supplier_group": supplier_group,
            "supplier_type": payload.get("supplier_type") or "Company",
            "tax_id": payload.get("tax_id"),
            "mobile_no": payload.get("mobile_no"),
            "email_id": payload.get("email_id"),
        }
    )
    supplier.flags.ignore_permissions = True
    supplier.insert()
    return supplier.as_dict()


def search_suppliers(search_text=None, limit=20):
    filters = {"disabled": 0}
    or_filters = None
    if search_text:
        like_value = f"%{search_text}%"
        or_filters = {
            "name": ["like", like_value],
            "supplier_name": ["like", like_value],
        }

    suppliers = frappe.get_all(
        "Supplier",
        filters=filters,
        or_filters=or_filters,
        fields=["name", "supplier_name", "supplier_group", "supplier_type", "default_currency"],
        order_by="supplier_name asc",
        limit_page_length=limit,
    )
    return suppliers


def get_buying_price_list():
    return _resolve_buying_price_list()


def get_supplier_info(supplier):
    """Get supplier details including the effective buying price list."""
    supplier = _resolve_supplier(supplier)
    if not supplier:
        frappe.throw(_("Supplier not found."))

    supplier_doc = frappe.get_doc("Supplier", supplier)
    buying_price_list = _resolve_supplier_buying_price_list(supplier)

    price_list_currency = None
    if buying_price_list:
        price_list_currency = frappe.db.get_value("Price List", buying_price_list, "currency")

    outstanding_amount = (
        frappe.db.sql(
            """
            SELECT COALESCE(SUM(outstanding_amount), 0)
            FROM `tabPurchase Invoice`
            WHERE supplier = %s
              AND docstatus = 1
              AND outstanding_amount > 0
            """,
            supplier,
        )[0][0]
        or 0
    )

    return {
        "supplier": supplier,
        "supplier_name": supplier_doc.supplier_name,
        "supplier_group": supplier_doc.supplier_group,
        "default_currency": supplier_doc.default_currency,
        "buying_price_list": buying_price_list,
        "price_list_currency": price_list_currency,
        "outstanding_amount": flt(outstanding_amount),
    }


def get_last_buying_rate(supplier, item_codes, company=None):
    """Get the last buying rate for items from supplier price lists or recent Purchase Invoices."""
    if isinstance(item_codes, str):
        try:
            item_codes = json.loads(item_codes)
        except Exception:
            item_codes = [item_codes]

    item_codes = _normalize_item_codes(item_codes)

    if not item_codes:
        return {}

    result = {}
    resolved_supplier = _resolve_supplier(supplier) if supplier else None

    if resolved_supplier:
        buying_price_list = _resolve_supplier_buying_price_list(resolved_supplier)
        price_list_rates = frappe.get_list(
            "Item Price",
            filters={
                "price_list": buying_price_list,
                "item_code": ["in", item_codes],
                "buying": 1,
            },
            fields=["item_code", "price_list_rate", "uom", "currency"],
        )

        for row in price_list_rates:
            code = row.get("item_code")
            if code and code not in result:
                price_list_currency = row.get("currency")
                if not price_list_currency and buying_price_list:
                    price_list_currency = frappe.db.get_value("Price List", buying_price_list, "currency")
                result[code] = {
                    "rate": row.get("price_list_rate", 0),
                    "currency": price_list_currency,
                    "uom": row.get("uom"),
                    "source": "price_list",
                    "supplier": resolved_supplier,
                }

    supplier_clause = ""
    params = [tuple(item_codes)]
    if resolved_supplier:
        supplier_clause = "AND pi.supplier = %s"
        params.append(resolved_supplier)
    if company:
        supplier_clause += " AND pi.company = %s"
        params.append(company)

    last_pi_items = frappe.db.sql(
        f"""
        SELECT
            ranked.item_code,
            ranked.rate,
            ranked.uom,
            ranked.currency,
            ranked.invoice,
            ranked.posting_date,
            ranked.supplier
        FROM (
            SELECT
                pii.item_code,
                pii.rate,
                pii.uom,
                pi.currency,
                pi.name AS invoice,
                pi.posting_date,
                pi.supplier,
                ROW_NUMBER() OVER (
                    PARTITION BY pii.item_code
                    ORDER BY pi.posting_date DESC, pi.creation DESC
                ) AS rn
            FROM `tabPurchase Invoice Item` pii
            JOIN `tabPurchase Invoice` pi ON pi.name = pii.parent
            WHERE pi.docstatus = 1
              AND pii.item_code IN %s
              {supplier_clause}
        ) ranked
        WHERE ranked.rn = 1
        """,
        tuple(params),
        as_dict=True,
    )

    for row in last_pi_items:
        code = row.get("item_code")
        if code and code not in result:
            result[code] = {
                "rate": row.get("rate", 0),
                "currency": row.get("currency"),
                "uom": row.get("uom"),
                "source": "last_invoice",
                "invoice": row.get("invoice"),
                "posting_date": row.get("posting_date"),
                "supplier": row.get("supplier"),
            }

    return result


def create_purchase_item(data):
    payload = json.loads(data) if isinstance(data, str) else data
    profile = _resolve_pos_profile(payload.get("pos_profile"))
    _ensure_allowed(profile, "posa_allow_create_purchase_items", _("Create items"))

    item_code = payload.get("item_code") or payload.get("item_name")
    item_name = payload.get("item_name") or item_code
    stock_uom = payload.get("stock_uom")

    if not item_code:
        frappe.throw(_("Item code is required."))
    if not stock_uom:
        frappe.throw(_("Stock UOM is required."))

    existing = frappe.db.exists("Item", item_code)
    if existing:
        return frappe.get_doc("Item", item_code).as_dict()

    item_group = payload.get("item_group") or frappe.db.get_value("Item Group", {"is_group": 0}, "name")
    item_group = item_group or "All Item Groups"

    barcode = payload.get("barcode")
    if barcode and frappe.db.exists("Item Barcode", {"barcode": barcode}):
        frappe.throw(_("Barcode {0} already exists.").format(barcode))

    item_doc = frappe.get_doc(
        {
            "doctype": "Item",
            "item_code": item_code,
            "item_name": item_name,
            "item_group": item_group,
            "stock_uom": stock_uom,
            "is_stock_item": 1,
            "disabled": 0,
            "default_warehouse": profile.get("warehouse"),
            "standard_rate": flt(payload.get("buying_price") or 0),
        }
    )

    if barcode:
        item_doc.append("barcodes", {"barcode": barcode})

    item_doc.flags.ignore_permissions = True
    item_doc.flags.ignore_mandatory = True
    item_doc.insert()

    selling_price_list = payload.get("selling_price_list") or profile.get("selling_price_list")
    buying_price_list = payload.get("buying_price_list") or _resolve_buying_price_list()

    selling_price = payload.get("selling_price")
    buying_price = payload.get("buying_price")

    _upsert_item_price(
        item_code,
        selling_price_list,
        selling_price,
        uom=stock_uom,
        selling=True,
    )
    _upsert_item_price(
        item_code,
        buying_price_list,
        buying_price,
        uom=stock_uom,
        buying=True,
    )

    if buying_price is not None:
        item_doc.db_set("standard_rate", flt(buying_price), update_modified=False)

    return {
        "item": item_doc.as_dict(),
        "selling_price_list": selling_price_list,
        "buying_price_list": buying_price_list,
    }


def _get_mode_of_payment_account(mode, company):
    account = frappe.db.get_value(
        "Mode of Payment Account", {"parent": mode, "company": company}, "default_account"
    )
    if not account:
        frappe.throw(
            _("Please set default account for Mode of Payment {0} in company {1}").format(mode, company)
        )
    return account


def _create_payment_entry(reference_doc, payments, company, transaction_date):
    if not payments:
        return []

    created_payments = []
    reference_doc.reload()

    ref_doctype = reference_doc.doctype
    ref_name = reference_doc.name

    if ref_doctype == "Purchase Invoice":
        outstanding_amount = flt(reference_doc.outstanding_amount)
    else:
        outstanding_amount = flt(reference_doc.grand_total)

    if outstanding_amount <= 0:
        return created_payments

    for pay in payments:
        amount = flt(pay.get("amount"))
        mode = pay.get("mode_of_payment")

        if amount <= 0:
            continue

        paid_from_account = _get_mode_of_payment_account(mode, company)

        pe = frappe.new_doc("Payment Entry")
        pe.payment_type = "Pay"
        pe.company = company
        pe.posting_date = transaction_date
        pe.mode_of_payment = mode
        pe.party_type = "Supplier"
        pe.party = reference_doc.supplier

        pe.paid_from = paid_from_account

        # Fetch party account
        pe.paid_to = get_party_account("Supplier", reference_doc.supplier, company)
        if not pe.paid_to:
            frappe.throw(_("Please set Default Payable Account in Company {0}").format(company))

        pe.paid_amount = amount
        pe.received_amount = amount
        # Note: If currencies differ, conversion handling is needed.
        # Assuming base currency for simplified POS flow or that user enters converted amount.

        # References
        # Allocate only up to outstanding amount
        allocated_amount = 0
        if outstanding_amount > 0:
            allocated_amount = min(amount, outstanding_amount)
            outstanding_amount -= allocated_amount

        if allocated_amount > 0:
            pe.append(
                "references",
                {
                    "reference_doctype": ref_doctype,
                    "reference_name": ref_name,
                    "allocated_amount": allocated_amount,
                },
            )

        pe.flags.ignore_permissions = True
        pe.insert()
        pe.submit()
        created_payments.append(pe.name)

    return created_payments


def _append_purchase_invoice_items(invoice, items, warehouse, item_map):
    for row in items:
        item_code = row.get("item_code")
        if not item_code:
            continue

        qty = flt(row.get("qty"))
        if qty <= 0:
            continue

        meta = item_map.get(item_code)
        stock_uom = row.get("stock_uom") or (meta.stock_uom if meta else None)
        item_name = row.get("item_name") or (meta.item_name if meta else item_code)
        uom = row.get("uom") or stock_uom
        conversion_factor = flt(row.get("conversion_factor") or 1) or 1

        invoice.append(
            "items",
            {
                "item_code": item_code,
                "item_name": item_name,
                "qty": qty,
                "uom": uom,
                "stock_uom": stock_uom,
                "conversion_factor": conversion_factor,
                "rate": flt(row.get("rate")),
                "warehouse": row.get("warehouse") or warehouse,
            },
        )


def _resolve_purchase_invoice_custom_is_paid(payload, payments, grand_total):
    total_paid = sum(flt(pay.get("amount")) for pay in (payments or []))
    if payments:
        return 1 if total_paid >= flt(grand_total) - 0.001 else 0
    return cint(payload.get("custom_is_paid"))


def _create_purchase_invoice_from_pos(payload):
    profile = _resolve_pos_profile(payload.get("pos_profile"))
    _ensure_purchase_invoice_allowed(profile)

    receive_now = cint(payload.get("receive"))
    if receive_now:
        _ensure_allowed(profile, "posa_allow_purchase_receipt", _("Receive stock"))

    supplier_input = payload.get("supplier")
    if not supplier_input:
        frappe.throw(_("Supplier is required."))

    supplier = _resolve_supplier(supplier_input)
    if not supplier:
        frappe.throw(_("Supplier {0} was not found.").format(supplier_input))

    company = payload.get("company") or profile.get("company") or frappe.defaults.get_default("company")
    if not company:
        frappe.throw(_("Company is required."))

    warehouse = payload.get("warehouse") or profile.get("warehouse") or get_default_warehouse(company)
    transaction_date = (
        payload.get("posting_date")
        or payload.get("transaction_date")
        or nowdate()
    )
    posting_time = payload.get("posting_time")
    schedule_date = payload.get("schedule_date") or transaction_date

    items = payload.get("items") or []
    if not items:
        frappe.throw(_("Purchase Invoice requires at least one item."))

    supplier_doc = frappe.get_doc("Supplier", supplier)
    supplier_currency = supplier_doc.default_currency
    if not supplier_currency:
        supplier_currency = frappe.get_value("Company", company, "default_currency")

    buying_price_list = payload.get("buying_price_list") or _resolve_supplier_buying_price_list(supplier)
    price_list_currency = frappe.get_value("Price List", buying_price_list, "currency")
    if price_list_currency and price_list_currency != supplier_currency:
        alternative_price_list = frappe.db.get_value(
            "Price List", {"currency": supplier_currency, "buying": 1, "enabled": 1}, "name"
        )
        if alternative_price_list:
            buying_price_list = alternative_price_list

    update_stock = cint(payload.get("update_stock"))
    if receive_now:
        update_stock = 1

    invoice = frappe.get_doc(
        {
            "doctype": "Purchase Invoice",
            "supplier": supplier,
            "company": company,
            "posting_date": transaction_date,
            "due_date": schedule_date,
            "currency": supplier_currency,
            "buying_price_list": buying_price_list,
            "update_stock": update_stock,
        }
    )

    if posting_time:
        invoice.posting_time = posting_time
        invoice.set_posting_time = 1

    if warehouse:
        invoice.set_warehouse = warehouse

    item_codes = [row.get("item_code") for row in items if row.get("item_code")]
    item_map = {}
    if item_codes:
        item_meta = frappe.get_all(
            "Item",
            filters={"name": ["in", item_codes]},
            fields=["name", "item_name", "stock_uom"],
        )
        item_map = {row.name: row for row in item_meta}

    _append_purchase_invoice_items(invoice, items, warehouse, item_map)

    if not invoice.items:
        frappe.throw(_("Purchase Invoice requires at least one item with quantity."))

    # Set territory from warehouse (so invoices are attributed to their warehouse)
    territory = _resolve_territory_for_warehouse(warehouse)
    if territory:
        invoice.territory = territory

    payments = payload.get("payments") or []
    meaningful_payments = [
        pay for pay in payments if flt(pay.get("amount")) > 0
    ]
    pos_handles_payment = bool(meaningful_payments)

    if _purchase_invoice_has_custom_is_paid():
        # Override custom field default (1) — POS uses custom_is_paid, not is_paid.
        invoice.is_paid = 0
        invoice.custom_is_paid = 0

    invoice.flags.ignore_permissions = True
    frappe.flags.ignore_account_permission = True
    invoice.save()
    # Suppress "Expense Head Changed" toast — expected when update_stock=1 and the
    # item's default expense account differs from the warehouse valuation account.
    frappe.local.message_log[:] = [
        m for m in frappe.local.message_log
        if "Expense Head" not in (m.get("title", "") if isinstance(m, dict) else str(m))
    ]

    # Purchase Invoices always support partial payment from POS.
    total_paid = sum(flt(pay.get("amount")) for pay in meaningful_payments)

    if _purchase_invoice_has_custom_is_paid():
        resolved_is_paid = _resolve_purchase_invoice_custom_is_paid(
            payload, meaningful_payments, invoice.grand_total
        )
        initial_is_paid = 0 if pos_handles_payment else resolved_is_paid
        # Keep in-memory doc aligned with DB before submit. db_set alone left
        # custom_is_paid=1 (field default) on the object while the DB had 0,
        # which caused post-submit is_paid / custom_is_paid validation errors.
        invoice.is_paid = 0
        invoice.custom_is_paid = initial_is_paid
        invoice.save()

    frappe.db.commit()

    try:
        if cint(payload.get("submit", 1)):
            if pos_handles_payment:
                frappe.flags.skip_purchase_invoice_auto_payment = True
            try:
                invoice.submit()
            finally:
                frappe.flags.skip_purchase_invoice_auto_payment = False
            # Suppress "Expense Head Changed" again — validate() re-runs during submit.
            frappe.local.message_log[:] = [
                m for m in frappe.local.message_log
                if "Expense Head" not in (m.get("title", "") if isinstance(m, dict) else str(m))
            ]

        payment_names = []
        if pos_handles_payment:
            invoice.reload()
            payment_names = _create_payment_entry(
                invoice, meaningful_payments, company, transaction_date
            )

        if _purchase_invoice_has_custom_is_paid():
            invoice.reload()
            paid_flag = 1 if flt(invoice.outstanding_amount) <= 0.001 else 0
            frappe.db.set_value(
                "Purchase Invoice",
                invoice.name,
                "custom_is_paid",
                paid_flag,
                update_modified=False,
            )

        return {
            "purchase_invoice": invoice.name,
            "purchase_order": invoice.name,
            "payment_entries": payment_names,
        }
    except Exception as err:
        frappe.db.rollback()
        frappe.log_error(frappe.get_traceback(), "POS Awesome Purchase Invoice Submit Failed")
        frappe.throw(
            _("Purchase Invoice {0} has been saved as Draft. Error: {1}").format(
                invoice.name, str(err)
            )
        )


def create_purchase_invoice(data):
    payload = json.loads(data) if isinstance(data, str) else data
    return _create_purchase_invoice_from_pos(payload)


def create_purchase_order(data):
    payload = json.loads(data) if isinstance(data, str) else data
    return _create_purchase_invoice_from_pos(payload)


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
    search=None,
):
    """Paginated, filterable list of submitted purchase invoices for the Invoice List page.

    Purchase Invoice has no pos_profile field, so scope by company instead.
    """
    doctype = "Purchase Invoice"
    profile = _resolve_pos_profile(pos_profile)

    filters = [
        [doctype, "docstatus", "=", 1],
        [doctype, "company", "=", profile.get("company")],
    ]
    if int(mine_only or 0):
        filters.append([doctype, "owner", "=", frappe.session.user])
    if status:
        filters.append([doctype, "status", "=", status])
    if from_date:
        filters.append([doctype, "posting_date", ">=", from_date])
    if to_date:
        filters.append([doctype, "posting_date", "<=", to_date])
    if supplier:
        filters.append([doctype, "supplier", "=", supplier])

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
            [doctype, "supplier", "like", like],
        ]

    page_start = max(0, int(page_start or 0))
    page_length = max(1, min(int(page_length or 100), 200))

    fields = [
        "name",
        "supplier",
        "posting_date",
        "posting_time",
        "grand_total",
        "outstanding_amount",
        "status",
        "currency",
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


def search_items(search_text=None, limit=20):
    filters = {"disabled": 0}
    or_filters = None
    if search_text:
        like_value = f"%{search_text}%"
        or_filters = {
            "name": ["like", like_value],
            "item_name": ["like", like_value],
        }

    items = frappe.get_all(
        "Item",
        filters=filters,
        or_filters=or_filters,
        fields=["name", "item_name", "stock_uom", "standard_rate"],
        limit_page_length=limit,
        order_by="name asc",
    )
    item_codes = [it.get("name") for it in items if it.get("name")]
    uom_rows = []
    bin_rows = []
    if item_codes:
        uom_rows = frappe.get_all(
            "UOM Conversion Detail",
            filters={"parent": ["in", item_codes]},
            fields=["parent", "uom", "conversion_factor"],
        )
        bin_rows = frappe.get_all(
            "Bin",
            filters={"item_code": ["in", item_codes]},
            fields=["item_code", "actual_qty"],
        )

    uom_map = {}
    for row in uom_rows:
        uom_map.setdefault(row.parent, []).append(
            {"uom": row.uom, "conversion_factor": row.conversion_factor}
        )

    qty_map = {}
    for row in bin_rows:
        qty_map[row.item_code] = qty_map.get(row.item_code, 0) + (row.actual_qty or 0)

    results = []
    for it in items:
        item_code = it.get("name")
        stock_uom = it.get("stock_uom")
        uoms = uom_map.get(item_code, [])
        if stock_uom and not any(u.get("uom") == stock_uom for u in uoms):
            uoms.append({"uom": stock_uom, "conversion_factor": 1})
        results.append(
            {
                "item_code": item_code,
                "item_name": it.get("item_name"),
                "stock_uom": stock_uom,
                "item_uoms": uoms,
                "standard_rate": it.get("standard_rate"),
                "actual_qty": qty_map.get(item_code, 0),
            }
        )
    return results


def _create_purchase_invoice(po_doc, payload, default_warehouse, transaction_date, receipt_doc=None):
    invoice_date = payload.get("invoice_date") or payload.get("invoice_posting_date") or transaction_date
    invoice = frappe.get_doc(
        {
            "doctype": "Purchase Invoice",
            "supplier": po_doc.supplier,
            "company": po_doc.company,
            "posting_date": invoice_date,
            "purchase_order": po_doc.name,
            "currency": payload.get("currency") or po_doc.currency,
        }
    )
    if default_warehouse:
        invoice.set_warehouse = default_warehouse

    items_by_code = _build_items_map(payload.get("items"))
    receipt_items = (
        {item.purchase_order_item: item for item in (receipt_doc.items or [])} if receipt_doc else {}
    )
    for po_item in po_doc.items:
        payload_row = _resolve_input_row(items_by_code, po_item.item_code)
        qty = flt(payload_row.get("qty") or po_item.qty)
        if qty <= 0:
            continue
        invoice_item = {
            "item_code": po_item.item_code,
            "item_name": po_item.item_name,
            "qty": qty,
            "uom": po_item.uom,
            "stock_uom": po_item.stock_uom,
            "conversion_factor": po_item.conversion_factor or 1,
            "rate": po_item.rate,
            "warehouse": po_item.warehouse or default_warehouse,
            "purchase_order": po_doc.name,
            "po_detail": po_item.name,
            "schedule_date": po_item.schedule_date,
        }
        receipt_item = receipt_items.get(po_item.name)
        if receipt_item and receipt_doc:
            invoice_item["purchase_receipt"] = receipt_doc.name
            invoice_item["pr_detail"] = receipt_item.name
        invoice.append("items", invoice_item)

    if not invoice.items:
        frappe.throw(_("No items to invoice. Please ensure there are items on the Purchase Order."))

    invoice.flags.ignore_permissions = True
    frappe.flags.ignore_account_permission = True
    invoice.insert()
    invoice.submit()
    return invoice.name
