# Copyright (c) 2015, AiBizzHub, LLC and contributors
# License: MIT. See LICENSE

from frappe.model.document import Document


class UserEmail(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		awaiting_password: DF.Check
		email_account: DF.Link
		email_id: DF.Data | None
		enable_outgoing: DF.Check
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		used_oauth: DF.Check
	# end: auto-generated types
	pass
