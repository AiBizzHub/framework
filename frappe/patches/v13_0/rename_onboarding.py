# Copyright (c) 2020, AiBizzHub, LLC and Contributors
# License: MIT. See LICENSE

import frappe


def execute():
	if frappe.db.exists("DocType", "Onboarding"):
		frappe.rename_doc("DocType", "Onboarding", "Module Onboarding", ignore_if_exists=True)
