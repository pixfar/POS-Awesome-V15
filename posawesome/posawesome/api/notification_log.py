# Copyright (c) 2026, POS Awesome and contributors
# For license information, please see license.txt

"""Bridges Frappe's own per-user Notification Log (mentions, assignments,
shares, energy points, alerts -- the same feed the Desk bell icon shows) into
POS Awesome's notification bell, so a cashier working entirely inside the POS
screen still sees things like an assignment or a mention without switching
over to the Desk UI.

Reading/marking-as-read reuses Frappe's own whitelisted, already
permission-scoped methods
(`frappe.desk.doctype.notification_log.notification_log`) directly from the
frontend where possible; this module only adds the one thing Frappe doesn't
already expose -- a combined "recent notifications + unread count" fetch
shaped for the bell.
"""

import frappe


@frappe.whitelist()
def get_recent_notifications(limit=20):
	"""Notification Log entries for the logged-in user, newest first.

	frappe.get_list applies Notification Log's own permission query
	conditions (for_user = frappe.session.user, or everyone's for
	Administrator -- see notification_log.get_permission_query_conditions),
	so this is already scoped to "my notifications" without an explicit
	filter, matching what Desk's own bell shows.
	"""
	limit = max(1, min(int(limit or 20), 50))

	rows = frappe.get_list(
		'Notification Log',
		fields=[
			'name',
			'subject',
			'type',
			'document_type',
			'document_name',
			'link',
			'read',
			'creation',
		],
		order_by='creation desc',
		limit_page_length=limit,
	)

	unread_count = frappe.db.count(
		'Notification Log', filters={'for_user': frappe.session.user, 'read': 0}
	)

	return {'notifications': rows, 'unread_count': unread_count}
