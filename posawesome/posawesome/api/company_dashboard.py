# Copyright (c) 2026, POS Awesome and contributors
# For license information, please see license.txt

"""Company-wide overview for the POS sidebar's Dashboard page.

BSP Admin / System Manager get every metric company-wide, with optional
Warehouse + date-range filtering. Everyone else gets the same metrics scoped
to their own data (own invoices/warehouses/employee/showroom account, per
doctype -- see each _collect_* helper), with date-range filtering only.
"""

import frappe
from frappe.utils import cint, flt, today

from posawesome.posawesome.api.fund_transfer import _list_filters as _fund_transfer_filters
from posawesome.posawesome.utils.warehouse_doc_permissions import (
    get_expanded_permitted_warehouses,
    get_permission_scoped_names,
    get_warehouse_doc_status_counts,
    is_privileged_invoice_viewer,
)


def _resolve_company(pos_profile):
    if pos_profile:
        company = frappe.db.get_value("POS Profile", pos_profile, "company")
        if company:
            return company
    return frappe.defaults.get_user_default("Company") or frappe.defaults.get_global_default(
        "Company"
    )


def _company_warehouses(company):
    if not company:
        return []
    return frappe.get_all(
        "Warehouse",
        filters={"company": company, "is_group": 0, "disabled": 0},
        pluck="name",
        limit_page_length=0,
    )


def _sum_invoice_doctype(doctype, company, start_date, end_date, warehouse, is_admin, is_return=0):
    filters = [
        [doctype, "docstatus", "=", 1],
        [doctype, "is_return", "=", is_return],
        [doctype, "posting_date", ">=", start_date],
        [doctype, "posting_date", "<=", end_date],
    ]
    if company:
        filters.append([doctype, "company", "=", company])
    if warehouse:
        filters.append([doctype, "set_warehouse", "=", warehouse])
    if not is_admin:
        scoped_names = get_permission_scoped_names(doctype, "set_warehouse")
        if scoped_names is not None:
            filters.append([doctype, "name", "in", scoped_names])

    rows = frappe.get_list(
        doctype,
        filters=filters,
        fields=[
            "sum(grand_total) as total",
            "sum(outstanding_amount) as due",
            "count(name) as count",
        ],
        ignore_permissions=True,
    )
    row = rows[0] if rows else {}
    total = flt(row.get("total"))
    due = flt(row.get("due"))
    # Collection = total - due, not sum(paid_amount). paid_amount is only ever
    # populated for immediate/POS-style payment (is_pos/is_paid = 1 at submit
    # time) -- an invoice settled later via a separate Payment Entry leaves
    # paid_amount at 0 forever even though outstanding_amount correctly drops
    # as that payment gets reconciled. outstanding_amount is the one field
    # Frappe's accounting engine keeps correct regardless of *how* an invoice
    # was paid, so deriving collection from it is what keeps
    # total == collection + due true in every case.
    return {
        "total": total,
        "collection": total - due,
        "due": due,
        "count": cint(row.get("count")),
    }


def _collect_sales(company, start_date, end_date, warehouse, is_admin):
    sales_invoice = _sum_invoice_doctype(
        "Sales Invoice", company, start_date, end_date, warehouse, is_admin
    )
    pos_invoice = _sum_invoice_doctype(
        "POS Invoice", company, start_date, end_date, warehouse, is_admin
    )
    return {
        "total": sales_invoice["total"] + pos_invoice["total"],
        "collection": sales_invoice["collection"] + pos_invoice["collection"],
        "due": sales_invoice["due"] + pos_invoice["due"],
        "count": sales_invoice["count"] + pos_invoice["count"],
    }


def _collect_purchase(company, start_date, end_date, warehouse, is_admin):
    return _sum_invoice_doctype(
        "Purchase Invoice", company, start_date, end_date, warehouse, is_admin
    )


def _collect_sales_return(company, start_date, end_date, warehouse, is_admin):
    sales_invoice = _sum_invoice_doctype(
        "Sales Invoice", company, start_date, end_date, warehouse, is_admin, is_return=1
    )
    pos_invoice = _sum_invoice_doctype(
        "POS Invoice", company, start_date, end_date, warehouse, is_admin, is_return=1
    )
    # Return invoices carry negative grand_total (they're credit notes) --
    # abs() so the card reads as "how much was returned", a positive amount,
    # matching how every other total on this dashboard is displayed.
    return {
        "total": abs(sales_invoice["total"] + pos_invoice["total"]),
        "count": sales_invoice["count"] + pos_invoice["count"],
    }


def _collect_purchase_return(company, start_date, end_date, warehouse, is_admin):
    purchase_invoice = _sum_invoice_doctype(
        "Purchase Invoice", company, start_date, end_date, warehouse, is_admin, is_return=1
    )
    return {"total": abs(purchase_invoice["total"]), "count": purchase_invoice["count"]}


def _sum_weight(doctype, item_doctype, company, start_date, end_date, warehouse, is_admin):
    """Sum(item.qty * Item.custom_default_weigt_of_measure) for submitted,
    non-return rows of `doctype` in range -- the per-unit weight lives on the
    Item master, not the invoice row, hence the join."""
    conditions = [
        "main.docstatus = 1",
        "main.is_return = 0",
        "main.posting_date >= %(start_date)s",
        "main.posting_date <= %(end_date)s",
    ]
    values = {"start_date": start_date, "end_date": end_date}
    if company:
        conditions.append("main.company = %(company)s")
        values["company"] = company
    if warehouse:
        conditions.append("main.set_warehouse = %(warehouse)s")
        values["warehouse"] = warehouse
    if not is_admin:
        scoped_names = get_permission_scoped_names(doctype, "set_warehouse")
        if scoped_names is not None:
            if not scoped_names:
                return 0.0
            conditions.append("main.name in %(scoped_names)s")
            values["scoped_names"] = tuple(scoped_names)

    where_clause = " AND ".join(conditions)
    rows = frappe.db.sql(
        f"""
        SELECT SUM(item.qty * IFNULL(weight_item.custom_default_weigt_of_measure, 0)) as total_weight
        FROM `tab{item_doctype}` item
        INNER JOIN `tab{doctype}` main ON main.name = item.parent
        LEFT JOIN `tabItem` weight_item ON weight_item.name = item.item_code
        WHERE {where_clause}
        """,
        values,
        as_dict=True,
    )
    return flt(rows[0].total_weight) if rows else 0.0


def _collect_sales_weight(company, start_date, end_date, warehouse, is_admin):
    return _sum_weight(
        "Sales Invoice", "Sales Invoice Item", company, start_date, end_date, warehouse, is_admin
    ) + _sum_weight(
        "POS Invoice", "POS Invoice Item", company, start_date, end_date, warehouse, is_admin
    )


def _collect_purchase_weight(company, start_date, end_date, warehouse, is_admin):
    return _sum_weight(
        "Purchase Invoice", "Purchase Invoice Item", company, start_date, end_date, warehouse, is_admin
    )


def _collect_stock_qty(company, warehouse, is_admin):
    warehouses = _company_warehouses(company)
    if warehouse:
        warehouses = [w for w in warehouses if w == warehouse]
    elif not is_admin:
        permitted = get_expanded_permitted_warehouses()
        if permitted is not None:
            warehouses = [w for w in warehouses if w in permitted]
    if not warehouses:
        return 0.0

    rows = frappe.get_all(
        "Bin",
        filters={"warehouse": ["in", warehouses]},
        fields=["sum(actual_qty) as total_qty"],
    )
    return flt(rows[0].total_qty) if rows else 0.0


def _collect_material_transfers(start_date, end_date, warehouse):
    status_counts = get_warehouse_doc_status_counts(
        "Material Transfer",
        "from_warehouse",
        "to_warehouse",
        "transfer_status",
        mine_only=0,
        date_field="transaction_date",
        from_date=start_date,
        to_date=end_date,
        warehouse=warehouse,
        include_cancelled=True,
        include_draft=True,
    )
    return {"status_counts": status_counts, "total": sum(status_counts.values())}


def _collect_requisitions(start_date, end_date, warehouse):
    status_counts = get_warehouse_doc_status_counts(
        "Requisition",
        "source_warehouse",
        "target_warehouse",
        "transfer_status",
        mine_only=0,
        date_field="transaction_date",
        from_date=start_date,
        to_date=end_date,
        warehouse=warehouse,
        include_cancelled=True,
        include_draft=True,
    )
    return {"status_counts": status_counts, "total": sum(status_counts.values())}


def _collect_production_plans(company, start_date, end_date, warehouse):
    """Admin-only -- mirrors production_plans.py's own status_counts block, but
    without its is_system_manager() throw (BSP Admin should see this too)."""
    doctype = "Production Plan"
    filters = [[doctype, "posting_date", ">=", start_date], [doctype, "posting_date", "<=", end_date]]
    if company:
        filters.append([doctype, "company", "=", company])
    if warehouse:
        filters.append([doctype, "for_warehouse", "=", warehouse])

    rows = frappe.get_list(
        doctype,
        filters=filters,
        fields=["workflow_state", "count(name) as count"],
        group_by="workflow_state",
        ignore_permissions=True,
        limit_page_length=0,
    )
    status_counts = {row.workflow_state: row.count for row in rows}
    return {"status_counts": status_counts, "total": sum(status_counts.values())}


def _collect_expenses(company, start_date, end_date, warehouse, is_admin):
    doctype = "Expense Claim"
    filters = {
        "docstatus": 1,
        "posting_date": ["between", [start_date, end_date]],
    }
    if company:
        filters["company"] = company
    if warehouse:
        filters["custom_warehouse"] = warehouse
    if not is_admin:
        employee = frappe.db.get_value(
            "Employee", {"user_id": frappe.session.user, "status": "Active"}, "name"
        )
        if not employee:
            return {"total": 0.0, "count": 0}
        filters["employee"] = employee

    rows = frappe.get_all(
        doctype,
        filters=filters,
        fields=["sum(grand_total) as total", "count(name) as count"],
    )
    row = rows[0] if rows else {}
    return {"total": flt(row.get("total")), "count": cint(row.get("count"))}


def _collect_deposits(company, start_date, end_date, warehouse, is_admin):
    doctype = "BSP Daily Deposit"
    filters = {
        "docstatus": 1,
        "posting_date": ["between", [start_date, end_date]],
    }
    if warehouse:
        filters["warehouse"] = warehouse
    elif company:
        filters["warehouse"] = ["in", _company_warehouses(company) or [""]]
    if not is_admin:
        scoped_names = get_permission_scoped_names(doctype, "warehouse", owner_field="user")
        if scoped_names is not None:
            filters["name"] = ["in", scoped_names]

    rows = frappe.get_all(
        doctype,
        filters=filters,
        fields=["sum(amount) as total", "count(name) as count"],
    )
    row = rows[0] if rows else {}
    return {"total": flt(row.get("total")), "count": cint(row.get("count"))}


def _fund_transfer_accounts_for_warehouse(warehouse):
    """Fund Transfers have no warehouse field of their own -- they're tracked
    against a POS Profile's change account (see _list_filters/paid_to below),
    so filtering "by warehouse" means: accounts belonging to POS Profiles
    whose default warehouse is the selected one."""
    accounts = frappe.get_all(
        "POS Profile",
        filters={"warehouse": warehouse, "disabled": 0},
        pluck="account_for_change_amount",
    )
    return [account for account in accounts if account]


def _collect_fund_transfers(company, start_date, end_date, warehouse):
    filters = _fund_transfer_filters()
    if company:
        filters["company"] = company
    filters["posting_date"] = ["between", [start_date, end_date]]
    if warehouse:
        # Only meaningful when the caller (admin) isn't already restricted to
        # their own showroom's account -- _fund_transfer_filters() only sets
        # paid_to for non-privileged users, and warehouse filtering is
        # admin-only on this dashboard, so this never overwrites that.
        filters["paid_to"] = ["in", _fund_transfer_accounts_for_warehouse(warehouse) or [""]]

    rows = frappe.get_all(
        "Payment Entry",
        filters=filters,
        fields=["sum(paid_amount) as total", "count(name) as count"],
    )
    row = rows[0] if rows else {}
    return {"total": flt(row.get("total")), "count": cint(row.get("count"))}


def _sum_top_items(doctype, item_doctype, company, start_date, end_date, warehouse, is_admin, limit):
    conditions = [
        "main.docstatus = 1",
        "main.is_return = 0",
        "main.posting_date >= %(start_date)s",
        "main.posting_date <= %(end_date)s",
    ]
    values = {"start_date": start_date, "end_date": end_date, "limit": limit}
    if company:
        conditions.append("main.company = %(company)s")
        values["company"] = company
    if warehouse:
        conditions.append("main.set_warehouse = %(warehouse)s")
        values["warehouse"] = warehouse
    if not is_admin:
        scoped_names = get_permission_scoped_names(doctype, "set_warehouse")
        if scoped_names is not None:
            if not scoped_names:
                return []
            conditions.append("main.name in %(scoped_names)s")
            values["scoped_names"] = tuple(scoped_names)

    where_clause = " AND ".join(conditions)
    return frappe.db.sql(
        f"""
        SELECT item.item_code as item_code, item.item_name as item_name,
               SUM(item.amount) as amount, SUM(item.qty) as qty
        FROM `tab{item_doctype}` item
        INNER JOIN `tab{doctype}` main ON main.name = item.parent
        WHERE {where_clause}
        GROUP BY item.item_code
        ORDER BY amount DESC
        LIMIT %(limit)s
        """,
        values,
        as_dict=True,
    )


def _collect_top_items(company, start_date, end_date, warehouse, is_admin, limit=5):
    merged = {}
    for doctype, item_doctype in (
        ("Sales Invoice", "Sales Invoice Item"),
        ("POS Invoice", "POS Invoice Item"),
    ):
        # Pull more than `limit` per doctype before merging, since an item
        # split across both doctypes could rank inside the top 5 only after
        # combining -- still capped, not exhaustive, which is fine for a
        # "Top 5" widget.
        rows = _sum_top_items(
            doctype, item_doctype, company, start_date, end_date, warehouse, is_admin, limit=200
        )
        for row in rows:
            entry = merged.setdefault(
                row.item_code,
                {"item_code": row.item_code, "item_name": row.item_name, "amount": 0.0, "qty": 0.0},
            )
            entry["amount"] += flt(row.amount)
            entry["qty"] += flt(row.qty)

    return sorted(merged.values(), key=lambda r: r["amount"], reverse=True)[:limit]


def _collect_top_warehouses(company, start_date, end_date, is_admin, limit=5):
    """Always ranks across every warehouse the caller can see, regardless of
    the dashboard's Warehouse filter -- a single-warehouse selection would
    make a "best selling warehouse" ranking meaningless."""
    merged = {}
    for doctype in ("Sales Invoice", "POS Invoice"):
        filters = [
            [doctype, "docstatus", "=", 1],
            [doctype, "is_return", "=", 0],
            [doctype, "posting_date", ">=", start_date],
            [doctype, "posting_date", "<=", end_date],
        ]
        if company:
            filters.append([doctype, "company", "=", company])
        if not is_admin:
            scoped_names = get_permission_scoped_names(doctype, "set_warehouse")
            if scoped_names is not None:
                if not scoped_names:
                    continue
                filters.append([doctype, "name", "in", scoped_names])

        rows = frappe.get_list(
            doctype,
            filters=filters,
            fields=["set_warehouse as warehouse", "sum(grand_total) as amount", "count(name) as count"],
            group_by="set_warehouse",
            ignore_permissions=True,
            limit_page_length=0,
        )
        for row in rows:
            if not row.warehouse:
                continue
            entry = merged.setdefault(
                row.warehouse, {"warehouse": row.warehouse, "amount": 0.0, "count": 0}
            )
            entry["amount"] += flt(row.amount)
            entry["count"] += cint(row.count)

    top = sorted(merged.values(), key=lambda r: r["amount"], reverse=True)[:limit]
    if top:
        names = frappe.get_all(
            "Warehouse",
            filters={"name": ["in", [row["warehouse"] for row in top]]},
            fields=["name", "warehouse_name"],
        )
        name_map = {row.name: row.warehouse_name for row in names}
        for row in top:
            row["warehouse_name"] = name_map.get(row["warehouse"]) or row["warehouse"]
    return top


@frappe.whitelist()
def get_dashboard_warehouses(pos_profile=None):
    company = _resolve_company(pos_profile)
    if not company:
        return []
    return frappe.get_list(
        "Warehouse",
        filters={"company": company, "is_group": 0, "disabled": 0},
        fields=["name", "warehouse_name"],
        order_by="warehouse_name asc",
        limit_page_length=200,
    )


@frappe.whitelist()
def get_company_dashboard(pos_profile=None, start_date=None, end_date=None, warehouse=None):
    company = _resolve_company(pos_profile)
    is_admin = is_privileged_invoice_viewer()

    start_date = start_date or today()
    end_date = end_date or today()
    if not is_admin:
        warehouse = None

    currency = (
        frappe.get_cached_value("Company", company, "default_currency")
        if company
        else None
    ) or frappe.defaults.get_global_default("currency")

    sales = _collect_sales(company, start_date, end_date, warehouse, is_admin)
    purchase = _collect_purchase(company, start_date, end_date, warehouse, is_admin)
    expenses = _collect_expenses(company, start_date, end_date, warehouse, is_admin)

    return {
        "scope": "all" if is_admin else "own",
        "start_date": start_date,
        "end_date": end_date,
        "warehouse": warehouse,
        "currency": currency,
        "sales": sales,
        "purchase": purchase,
        "sales_return": _collect_sales_return(company, start_date, end_date, warehouse, is_admin),
        "purchase_return": _collect_purchase_return(company, start_date, end_date, warehouse, is_admin),
        "sales_weight": _collect_sales_weight(company, start_date, end_date, warehouse, is_admin),
        "purchase_weight": _collect_purchase_weight(company, start_date, end_date, warehouse, is_admin),
        "stock_qty": _collect_stock_qty(company, warehouse, is_admin),
        "material_transfers": _collect_material_transfers(start_date, end_date, warehouse),
        "requisitions": _collect_requisitions(start_date, end_date, warehouse),
        "production_plans": (
            _collect_production_plans(company, start_date, end_date, warehouse)
            if is_admin
            else None
        ),
        "expenses": expenses,
        "deposits": _collect_deposits(company, start_date, end_date, warehouse, is_admin),
        "fund_transfers": _collect_fund_transfers(company, start_date, end_date, warehouse),
        "top_items": _collect_top_items(company, start_date, end_date, warehouse, is_admin),
        "top_warehouses": _collect_top_warehouses(company, start_date, end_date, is_admin),
    }
