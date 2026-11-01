/* Three buttons on the joiner submission form (slice 078 step 6, 079).
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
		/* The password is shown ONCE, by the call that makes it, and is
		   stored nowhere we can read back: Frappe's own password store is the
		   only copy. If HR loses it, they cancel and make another. */
		if (frm.is_new()) return;

		if (frm.doc.status === "Invited" && !frm.doc.user) {
			frm.add_custom_button(__("Make the sign-in"), () => makeSignIn(frm));
		}

		if (["Invited", "Submitted"].includes(frm.doc.status)) {
			frm.add_custom_button(__("Cancel this invite"), () => {
				frappe.prompt(
					[{
						fieldname: "reason", fieldtype: "Select", reqd: 1,
						label: __("Why"),
						options: ["By HR", "The joiner is not coming",
						          "Sent to the wrong person",
						          "A newer sign-in was made"].join("\n"),
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

/* The six-line message HR sends, shown ONCE (01b §3, M1 and M2).
 *
 * It is designed rather than left to whoever writes the SMS template, because a
 * joiner's whole experience of us begins as six lines of text on a lock screen.
 * Each line earns its place: a short typeable address, the thing they already
 * carry as a username, a password they can read off paper or down a telephone,
 * a weekday and a date rather than "7 days", and a named person with a phone
 * number.
 *
 * The password is in no log line, no Version row and no field, and there is no
 * endpoint that reads it back. If HR loses it they cancel and make another,
 * which leaves a cleaner trail than a reissue.
 */
function makeSignIn(frm) {
	frappe.call({
		method: "alvoraa_portal.joiner_invite.make_sign_in",
		args: { submission: frm.doc.name },
		freeze: true,
	}).then((r) => {
		const d = (r && r.message) || {};
		const esc = frappe.utils.escape_html;
		const who = frappe.session.user_fullname || "";
		const contact = [(d.contact || {}).phone, (d.contact || {}).email]
			.filter(Boolean).join(" or ");
		const finishBy = d.expires_on
			? frappe.datetime.str_to_user(d.expires_on) : "";
		const message = [
			`${frappe.boot.sysdefaults.company || ""} — ${__("before your first day")}`,
			"",
			__("Please fill in a few details before you start. About 5 minutes on your phone."),
			"",
			`${__("Open")}:          ${d.address || ""}`,
			`${__("Sign in with")}:  ${d.username || ""}`,
			`${__("Password")}:      ${d.password || ""}`,
			"",
			`${__("Finish by")} ${finishBy}.`,
			__("Keep this message — you need it if you stop and come back."),
			"",
			`${__("Questions")}: ${who}${contact ? ", " + contact : ""}`,
		].join("\n");

		frappe.msgprint({
			title: __("{0} can now sign in", [frm.doc.full_name || ""]),
			indicator: "green",
			message: `
				<p><b>${__("You will not see this password again.")}</b> ${__(
					"Send these lines however you already reach this person — a text "
					+ "message, WhatsApp, or printed on a slip. If it is lost there is "
					+ "nothing to look up: cancel this invite and make another.")}</p>
				<p><textarea readonly rows="13"
				   style="width:100%;font-family:monospace;font-size:12px"
				   onclick="this.select()">${esc(message)}</textarea></p>
				<p>${__("Copy it with Ctrl+C after clicking in the box.")}</p>
				<p class="text-muted"><b>${__("She cannot see anything else.")}</b> ${__(
					"This sign-in opens their own form and nothing else here. They are "
					+ "not an employee, not in your headcount, not on the organisation "
					+ "chart, and not a paid seat until they start.")}</p>`,
		});
		frm.reload_doc();
	});
}
