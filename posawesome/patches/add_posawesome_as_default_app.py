import frappe


def execute():
	"""Land users on the POS Awesome dashboard (/app/posapp/overview) after
	login. Frappe redirects to System Settings.default_app's apps-screen route
	(see add_to_apps_screen in hooks.py) unless the user has their own Default
	Workspace or Default App set. Only fills it in when nothing is set yet."""
	if not frappe.db.get_single_value("System Settings", "default_app"):
		frappe.db.set_single_value("System Settings", "default_app", "posawesome")
