// Copyright (c) 2016, AiBizzHub, LLC and contributors
// For license information, please see license.txt

frappe.ui.form.on("Patch Log", {
	refresh: function (frm) {
		frm.disable_save();
	},
});
