# Copyright (c) 2026, POS Awesome and contributors
# For license information, please see license.txt

"""Shareable PDF links for the POS detail pages' "Share" button.

The link points at Frappe's own download_pdf endpoint with a Document Share
Key, which download_pdf (allow_guest) accepts in place of a login -- so
whoever receives the link on WhatsApp/email can open the PDF without an
account, but only for that one document and only until the key expires
(System Settings > Document Share Key Expiry).
"""

from urllib.parse import urlencode

import frappe
from frappe import _
from frappe.utils import add_days, today


@frappe.whitelist()
def get_document_share_link(doctype, name, print_format=None):
	doc = frappe.get_doc(doctype, name)
	if not (frappe.has_permission(doctype, 'read', doc) or frappe.has_permission(doctype, 'print', doc)):
		frappe.throw(_('You are not permitted to share {0} {1}.').format(_(doctype), name), frappe.PermissionError)

	if print_format and frappe.db.get_value('Print Format', print_format, 'doc_type') != doctype:
		print_format = None

	# Reuse a key that is still good for at least a week rather than minting
	# a new one on every click (Frappe's own get_document_share_key only
	# reuses keys that never expire).
	existing = frappe.get_all(
		'Document Share Key',
		filters={
			'reference_doctype': doctype,
			'reference_docname': name,
			'expires_on': ['>=', add_days(today(), 7)],
		},
		fields=['key', 'expires_on'],
		order_by='expires_on desc',
		limit=1,
	)
	if existing:
		key, expires_on = existing[0].key, existing[0].expires_on
	else:
		key = doc.get_document_share_key()
		expires_on = frappe.db.get_value(
			'Document Share Key',
			{'reference_doctype': doctype, 'reference_docname': name, 'key': key},
			'expires_on',
		)

	params = {'doctype': doctype, 'name': name, 'no_letterhead': 1, 'key': key}
	if print_format:
		params['format'] = print_format

	# A path, not a full URL: the browser prefixes its own origin, which is
	# the address people actually reach this site on (host_name can point at
	# an internal address).
	return {
		'path': f'/api/method/frappe.utils.print_format.download_pdf?{urlencode(params)}',
		'expires_on': expires_on,
	}
