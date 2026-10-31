/* Three buttons on the joiner submission form (slice 078, step 6).
 *
 * Desk, not a new portal screen: HR reviews a submission here, HR Manager
 * already has Desk, and a second screen for three actions would be a surface
 * before an answer.
 *
 * WHAT IS DELIBERATELY NOT HERE: anything that creates an Employee. 078-SEC-12
 * - HR makes the personnel record by hand and sets the joining date itself,
 * because a back-dated joining date makes Frappe mark the person Absent for
 * every day since and deleting those rows does not help. That is a logged DTC
 * fault, not a theory. Linking the Employee on this form is what moves the
 * status on, in the controller's own validate.
 */
frappe.ui.form.on("Alvoraa Joiner Submission", {
	refresh(frm) {
		/* The link is shown ONCE, by the call that makes it, and is stored
		   nowhere we can read back - our submit path deletes the row holding
		   Frappe's key the moment it is used. If HR loses it, they cancel and
		   issue another. */
		if (frm.is_new()) return;

		if (frm.doc.status === "Invited" && !frm.doc.web_form_request) {
			frm.add_custom_button(__("Make the link"), () => invite(frm));
		}

		if (["Invited", "Submitted"].includes(frm.doc.status)) {
			frm.add_custom_button(__("Cancel this invite"), () => {
				frappe.prompt(
					[{
						fieldname: "reason", fieldtype: "Select", reqd: 1,
						label: __("Why"),
						options: ["By HR", "The joiner is not coming",
						          "Sent to the wrong person",
						          "A newer link was made"].join("\n"),
					}],
					(v) => frappe.call({
						method: "alvoraa_portal.joiner_invite.cancel_invite",
						args: { submission: frm.doc.name, reason: v.reason },
						freeze: true,
					}).then(() => frm.reload_doc()),
					__("Cancel this invite"), __("Cancel the invite"));
			});
		}

		/* Counsel, 29 October 2026. A candidate who never joined has no login,
		   so they cannot see or export anything themselves - HR has to be able
		   to answer "what do you hold about me" and "delete it" in one click,
		   without a developer. */
		frm.add_custom_button(__("Export everything held"), () => {
			open_url_post("/api/method/alvoraa_portal.joiner_invite.export_submission",
			              { submission: frm.doc.name });
		}, __("Their rights"));

		if (!frm.doc.erased_on) {
			frm.add_custom_button(__("Purge on their request"), () => {
				frappe.warn(
					__("Delete everything this person sent?"),
					__("Their details and every file they uploaded are deleted "
					 + "for good. This cannot be undone, and it ignores legal "
					 + "hold - use it when the person has asked."),
					() => frappe.call({
						method: "alvoraa_portal.joiner_invite.purge_submission",
						args: { submission: frm.doc.name },
						freeze: true,
					}).then(() => frm.reload_doc()),
					__("Delete it"), true);
			}, __("Their rights"));
		}

		if (frm.doc.erased_on) {
			frm.dashboard.add_comment(
				__("The details were erased on {0}: {1}",
				   [frappe.datetime.str_to_user(frm.doc.erased_on),
				    frm.doc.erased_why || ""]),
				"blue", true);
		}
	},
});

function invite(frm) {
	frappe.call({
		method: "alvoraa_portal.joiner_invite.invite_joiner",
		args: { full_name: frm.doc.full_name },
		freeze: true,
	}).then((r) => {
		const d = (r && r.message) || {};
		/* Shown once, and selectable so HR can copy it. Email is the only
		   channel this product has, and a copyable link covers the rest. */
		frappe.msgprint({
			title: __("Send this link to the joiner"),
			indicator: "green",
			message: `<p>${__("It works for {0} days and only once.", [d.link_days])}</p>
				<p><textarea readonly rows="3"
				   style="width:100%;font-family:monospace;font-size:12px"
				   onclick="this.select()">${frappe.utils.escape_html(d.link || "")}</textarea></p>
				<p class="text-muted">${__("This is the only time it is shown. "
				 + "If it is lost, cancel this invite and make another.")}</p>`,
		});
		frm.reload_doc();
	});
}
