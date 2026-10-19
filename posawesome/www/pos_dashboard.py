"""Send a logged-in Desk user who opens the site root (/) to the POS dashboard.

Frappe renders "/" as whatever get_home_page() returns, and with no home page
configured that is "me" (the website "My Account" page). get_home_page() runs
the get_website_user_home_page hook for every logged-in user, so get_home_page
below points System Users at this page, whose get_context only redirects.

A direct request for /pos-dashboard never reaches this file: the
website_redirects rule in hooks.py matches the path first. Only the resolved
home page of "/" renders it.
"""

import frappe

from posawesome.www.login import DASHBOARD_PATH

no_cache = 1


def get_home_page(user):
	if user == "Guest":
		return None
	if frappe.get_cached_value("User", user, "user_type") != "System User":
		# Website Users cannot open Desk -- fall through to Frappe's defaults.
		return None
	return "pos-dashboard"


def get_context(context):
	frappe.local.flags.redirect_location = DASHBOARD_PATH
	# 302 so the browser does not cache "/" -> dashboard past a logout.
	raise frappe.Redirect(302)
