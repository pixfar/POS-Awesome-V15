"""POS Awesome login page -- replaces Frappe's standard /login.

posawesome is installed after frappe, and Frappe resolves a www page from the
last-installed app that has one, so this file (plus login.html) takes over
/login. It still logs in through Frappe's own /api/method/login, but sends
System Users to the POS Awesome dashboard instead of whatever Desk workspace
Frappe would otherwise pick.
"""

import frappe
from frappe import _
from frappe.utils import cint
from frappe.website.utils import get_home_page

DASHBOARD_PATH = "/app/posapp/overview"
MEETING_URL = "https://calendly.com/pixfar-quick-meeting/30min"
PIXFAR_URL = "https://www.pixfar.com"

ERP_URL = "https://www.pixfar.com/service/erp"

# (icon key, colour, title, description) -- icons are inline SVGs in login.html.
INDUSTRIES = [
	("factory", "#0891b2", "Manufacturing", "BOMs, shop floor & production control"),
	("truck", "#ea580c", "Trading & Distribution", "Supply chain, logistics & fulfilment"),
	("heart", "#e11d48", "Healthcare", "Clinics, hospitals & patient billing"),
	("cart", "#db2777", "Retail & E-Commerce", "POS, online store & inventory sync"),
	("cap", "#4f46e5", "Education", "Enrolment, fees & campus operations"),
	("cash", "#059669", "Financial Services", "Multi-entity finance & compliance"),
	("helmet", "#d97706", "Engineering (EPC)", "Project costing, contracts & assets"),
	("briefcase", "#7c3aed", "Professional Services", "Timesheets, billing & project P&L"),
	("hand", "#0d9488", "Non-Profits", "Grants, donors & fund accounting"),
]

MODULES = [
	("bank", "#2563eb", "Accounting", "GL, AP/AR, multi-currency & tax"),
	("bag", "#7c3aed", "Procurement", "Purchase orders, suppliers & RFQs"),
	("trend", "#059669", "Sales", "Quotes, orders, invoicing & targets"),
	("target", "#e11d48", "CRM", "Leads, pipeline, deals & forecasting"),
	("boxes", "#ea580c", "Stock", "Inventory, warehouses & valuation"),
	("factory", "#0891b2", "Manufacturing", "BOM, work orders & production planning"),
	("folder", "#4f46e5", "Projects", "Tasks, timesheets & milestone billing"),
	("building", "#d97706", "Assets", "Fixed assets, depreciation & disposal"),
	("store", "#db2777", "Point of Sale", "Retail & restaurant POS terminals"),
	("check", "#0d9488", "Quality", "QC, inspections & non-conformance"),
	("headset", "#dc2626", "Support", "Helpdesk, SLA & knowledge base"),
	("people", "#9333ea", "HR & Payroll", "People ops, attendance & payroll"),
]

no_cache = 1


def sanitize_redirect(path):
	"""Only same-site absolute paths; anything else (other hosts, protocol-
	relative //evil.com, javascript:) falls back to the default."""
	if not path or not isinstance(path, str):
		return None
	path = path.strip()
	if not path.startswith("/") or path.startswith("//") or path.startswith("/\\"):
		return None
	# Bare Desk roots just mean "wherever you land by default" -- send those to
	# the dashboard too rather than the generic Desk home.
	if path.rstrip("/") in ("/app", "/desk", "/login", "/apps"):
		return None
	return path


def get_context(context):
	redirect_to = sanitize_redirect(frappe.form_dict.get("redirect-to"))

	if frappe.session.user != "Guest":
		if frappe.session.data.user_type == "Website User":
			target = redirect_to or "/" + get_home_page()
		else:
			target = redirect_to or DASHBOARD_PATH
		frappe.local.flags.redirect_location = target
		# 302, not the default 301: a cached permanent redirect on /login would
		# keep bouncing the browser to the dashboard even after logout.
		raise frappe.Redirect(302)

	company = frappe.defaults.get_global_default("company") or ""
	settings = frappe.get_cached_doc("Website Settings")
	system_settings = frappe.get_cached_doc("System Settings")

	context.no_cache = 1
	context.title = _("Login")
	# The page itself carries Pixfar's branding; the site's company name only
	# tells the user which workspace they are signing in to.
	context.company_name = company or settings.app_name or ""
	context.pixfar_logo = "/assets/posawesome/images/pixfar-logo.png"
	context.favicon = settings.favicon or "/assets/posawesome/icons/logo-144.png"
	context.meeting_url = MEETING_URL
	context.pixfar_url = PIXFAR_URL
	context.erp_url = ERP_URL
	context.modules = MODULES
	context.industries = INDUSTRIES
	context.dashboard_path = DASHBOARD_PATH
	context.redirect_to = redirect_to or ""
	context.disable_password_login = cint(system_settings.disable_user_pass_login)
	context.login_label = _("Email or username") if cint(system_settings.allow_login_using_user_name) else _("Email address")
	context.lang = frappe.local.lang or "en"
	return context
