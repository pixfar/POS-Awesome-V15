# Copyright (c) 2026, POS Awesome and contributors
# For license information, please see license.txt

"""Session helpers for the POS Awesome client."""

import frappe


@frappe.whitelist(methods=["GET"])
def get_csrf_token():
	"""The current session's CSRF token, for a tab whose copy went stale (a
	page served from the service-worker cache, or a re-login in another tab).
	`user` lets the client refuse to silently continue when the session now
	belongs to someone else. GET requests are exempt from the CSRF check;
	this returns the same token /app already embeds in its own page."""
	if frappe.session.user == "Guest":
		return {"user": "Guest", "csrf_token": None}
	return {"user": frappe.session.user, "csrf_token": frappe.sessions.get_csrf_token()}
