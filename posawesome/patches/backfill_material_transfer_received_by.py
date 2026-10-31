import frappe


def execute():
	"""Stamp Material Transfer.modified_by from the receipt Stock Entry owner.

	confirm_receipt historically wrote transfer_status / stock_entry_received
	with update_modified=False, so "Last Modified By" kept showing the
	creator instead of whoever actually received the goods. New receipts
	update modified_by correctly; this backfills existing received rows
	from the receipt Stock Entry's owner (and its creation time).
	"""
	if not frappe.db.has_column('Material Transfer', 'stock_entry_received'):
		return

	frappe.db.sql(
		"""
		UPDATE `tabMaterial Transfer` mt
		INNER JOIN `tabStock Entry` se ON se.name = mt.stock_entry_received
		SET mt.modified_by = se.owner,
			mt.modified = se.creation
		WHERE IFNULL(mt.stock_entry_received, '') != ''
			AND mt.modified_by != se.owner
		"""
	)
