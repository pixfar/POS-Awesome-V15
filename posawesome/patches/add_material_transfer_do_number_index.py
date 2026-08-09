import frappe


def execute():
    # Material Transfer's own doctype json already marks custom_do_number as
    # search_index: 1, so a normal schema sync (bench migrate) adds this on
    # a fresh install. This patch exists purely to backfill the index on
    # sites (like this one) where the column existed before that flag was
    # set -- add_index is idempotent, so it's a no-op if the index is
    # already there.
    if not frappe.db.has_column("Material Transfer", "custom_do_number"):
        return
    try:
        frappe.db.add_index("Material Transfer", ["custom_do_number"])
    except Exception as e:
        frappe.log_error(str(e), "Add Material Transfer DO Number index")
