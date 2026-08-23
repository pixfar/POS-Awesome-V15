import json

import frappe

WORKSPACE_NAME = "POS Awesome"

# Matches exactly what add_cash_movement_to_workspace / add_gift_card_to_workspace
# / add_submission_ledger_to_workspace (formerly run on every `bench migrate`
# via hooks.py's after_migrate -- see the comment there) used to add. Removed
# unconditionally here, once, regardless of whether the underlying DocType
# still exists -- the workspace should only ever show "POS Awesome App".
#
# Card Break rows carry the card's own label ("Submission Ledger"), but the
# Link row underneath doesn't always match it -- e.g. its label is "Invoice
# Submission Ledger", not "Submission Ledger" -- so Link rows are matched by
# `link_to` (the actual DocType, unambiguous) instead of by label.
CARD_LABELS = {"Cash Movement", "Gift Cards", "Submission Ledger"}
LINK_TARGETS = {"POS Cash Movement", "POS Gift Card", "POS Invoice Submission Ledger"}
CARD_BLOCK_IDS = {"posaCashMovementCard", "posaGiftCardsCard", "posaSubmissionLedgerCard"}


def _recompute_card_break_counts(links):
	card_break = None
	for link in links:
		if link.type == "Card Break":
			card_break = link
			card_break.link_count = 0
			continue
		if card_break and link.type == "Link":
			card_break.link_count = (card_break.link_count or 0) + 1


def _set_link_indexes(links):
	for idx, link in enumerate(links, start=1):
		link.idx = idx


def _remove_extra_links(workspace):
	links = workspace.links or []
	changed = False
	for idx in range(len(links) - 1, -1, -1):
		link = links[idx]
		if (link.type == "Card Break" and link.label in CARD_LABELS) or (
			link.type == "Link" and (link.label in CARD_LABELS or link.link_to in LINK_TARGETS)
		):
			links.pop(idx)
			changed = True

	if changed:
		_recompute_card_break_counts(links)
		_set_link_indexes(links)

	return changed


def _remove_extra_content(workspace):
	if not workspace.content:
		return False

	try:
		content = json.loads(workspace.content)
	except Exception:
		return False

	filtered_content = [
		block
		for block in content
		if not (
			block.get("id") in CARD_BLOCK_IDS
			or (block.get("type") == "card" and (block.get("data") or {}).get("card_name") in CARD_LABELS)
		)
	]

	if len(filtered_content) == len(content):
		return False

	workspace.content = json.dumps(filtered_content, separators=(",", ":"))
	return True


def execute():
	if not frappe.db.table_exists("Workspace"):
		return
	if not frappe.db.exists("Workspace", WORKSPACE_NAME):
		return

	workspace = frappe.get_doc("Workspace", WORKSPACE_NAME)
	removed_links = _remove_extra_links(workspace)
	removed_content = _remove_extra_content(workspace)
	if removed_links or removed_content:
		if not workspace.get("type"):
			workspace.type = "Workspace"
		workspace.flags.ignore_mandatory = True
		workspace.save(ignore_permissions=True)
