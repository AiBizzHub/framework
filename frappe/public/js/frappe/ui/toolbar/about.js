frappe.provide("frappe.ui.misc");
frappe.ui.misc.about = function () {
	if (!frappe.ui.misc.about_dialog) {
		var d = new frappe.ui.Dialog({ title: __("AiBizzApp Framework") });

		$(d.body).html(
			repl(
				`<div>
					<p>${__("Streamline Your Business With AiBizzHub")}</p>
					<p><i class='fa fa-globe fa-fw'></i>
						${__("Website")}:
						<a href='https://frappeframework.com' target='_blank'>https://frappeframework.com</a></p>
					
					<p><i class='fa fa-graduation-cap fa-fw'></i>
						AiBizzHub School: <a href='https://aibizzhub.school' target='_blank'>https://aibizzhub.school</a></p>

					<p><i class='fa fa-linkedin fa-fw'></i>
						Linkedin: <a href='https://linkedin.com/company/aibizzhub' target='_blank'>https://linkedin.com/company/aibizzhub</a></p>

					<p><i class='fa fa-twitter fa-fw'></i>
						Twitter: <a href='https://twitter.com/aibizzhub' target='_blank'>https://twitter.com/aibizzhub</a></p>
					<p><i class='fa fa-youtube fa-fw'></i>
						YouTube: <a href='https://www.youtube.com/@aibizzhub' target='_blank'>https://www.youtube.com/@aibizzhub</a></p>
					<hr>
					<h4>${__("Installed Apps")}</h4>
					<div id='about-app-versions'>${__("Loading versions...")}</div>
					<hr>
					<p class='text-muted'>${__("&copy; AiBizzHub, LLC and contributors")} </p>
					</div>`,
				frappe.app
			)
		);

		frappe.ui.misc.about_dialog = d;

		frappe.ui.misc.about_dialog.on_page_show = function () {
			if (!frappe.versions) {
				frappe.call({
					method: "frappe.utils.change_log.get_versions",
					callback: function (r) {
						show_versions(r.message);
					},
				});
			} else {
				show_versions(frappe.versions);
			}
		};

		var show_versions = function (versions) {
			var $wrap = $("#about-app-versions").empty();
			$.each(Object.keys(versions).sort(), function (i, key) {
				var v = versions[key];
				let text;
				if (v.branch) {
					text = $.format("<p><b>{0}:</b> v{1} ({2})<br></p>", [
						v.title,
						v.branch_version || v.version,
						v.branch,
					]);
				} else {
					text = $.format("<p><b>{0}:</b> v{1}<br></p>", [v.title, v.version]);
				}
				$(text).appendTo($wrap);
			});

			frappe.versions = versions;
		};
	}

	frappe.ui.misc.about_dialog.show();
};
