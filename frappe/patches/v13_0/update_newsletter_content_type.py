# Copyright (c) 2020, AiBizzHub, LLC and Contributors
# License: MIT. See LICENSE

import frappe


def execute():
	frappe.reload_doc("email", "doctype", "Newsletter")
	frappe.db.sql(
		"""
		UPDATE tabNewsletter
		SET content_type = 'Rich Text'
	"""
	)
