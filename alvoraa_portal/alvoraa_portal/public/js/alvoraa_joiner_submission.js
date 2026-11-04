/* The buttons on the joiner submission form (slice 078 step 6, 079, 082).
 *
 * Desk, not a new portal screen: HR reviews a submission here, HR Manager
 * already has Desk, and a second screen for a handful of actions would be a
 * surface before an answer.
 *
 * WHAT IS DELIBERATELY NOT HERE, and slice 082 narrowed this rather than
 * dropping it: nothing fills in a date. "Make their employee record" opens a
 * new, UNSAVED Employee form with the six details and the name on it and NO
 * date of any kind, and HR types the real first working day before they press
 * Save. A back-dated joining date makes Frappe mark the person Absent for every
 * day since and deleting those rows does not help - a logged DTC fault, not a
 * theory. Nothing here saves an Employee; HR's own Save does.
 *
 * Neither button is a permission. Both endpoints check the caller's rights on
 * the row and on the Employee, server side, every time.
 */
frappe.ui.form.on("Alvoraa Joiner Submission", {
	refresh(frm) {
		/* The password is shown ONCE, by the call that makes it, and is
		   stored nowhere we can read back: Frappe's own password store is the
		   only copy. If HR loses it, they cancel and make another. */
		if (frm.is_new()) return;

		/* Said on the form rather than left to a refusal: the button is
		   absent until HR has typed what the person will sign in with. An
		   absent control is an answer; a control that refuses is a guess. */
		if (frm.doc.status === "Invited" && !frm.doc.user && !frm.doc.login_id) {
			frm.dashboard.add_comment(
				__("Type the mobile number or email you reached this person on, in "
				 + "“Signs in with”, and save. Then you can make their sign-in."),
				"orange", true);
		}

		if (frm.doc.status === "Invited" && !frm.doc.user && frm.doc.login_id) {
			frm.add_custom_button(__("Make the sign-in"), () => makeSignIn(frm));
		}

		/* Slice 082. Only a submitted invite that nobody has linked yet, and
		   only while there is still something on it to copy. */
		if (frm.doc.status === "Submitted" && !frm.doc.employee
				&& !frm.doc.erased_on) {
			frm.dashboard.add_comment(
				__("It will not fill in the joining date. Type the real first "
				 + "working day — a date in the past marks them absent for "
				 + "every day since."),
				"blue", true);

			if (frappe.model.can_create("Employee")) {
				frm.add_custom_button(__("Make their employee record"),
				                      () => makeEmployeeRecord(frm));
			}
			if (frm.perm[0] && frm.perm[0].write) {
				frm.add_custom_button(__("Link the employee record"),
				                      () => linkEmployeeRecord(frm));
			}
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

/* Slice 082, US-1. The six details and the name onto a new, UNSAVED Employee.
 *
 * `frappe.new_doc("Employee", values)` is Frappe's own mechanism, the one
 * `Employee Onboarding` uses to hand HR a filled-in form: the values go into
 * `frappe.route_options`, `frappe.model.get_new_doc` copies them onto the new
 * document (`create_new.js:60-67`), and because `Employee` has no quick entry
 * the full form opens instead of a dialog (`quick_entry.js:57-70`). Read in the
 * installed source, v16.33.1, not from memory.
 *
 * The server decides what crosses. This function names no field at all, so the
 * map cannot drift away from `COLUMN_FOR_TICK` - which is the whole reason the
 * prefill is an endpoint rather than a list in here.
 */
function makeEmployeeRecord(frm) {
	frappe.call({
		method: "alvoraa_portal.joiner_to_employee.details_for_a_new_employee",
		args: { submission: frm.doc.name },
		freeze: true,
	}).then((r) => {
		if (!r || !r.message) return;
		frappe.new_doc("Employee", r.message);
	});
}

/* Slice 082, US-3 and 082-SEC-6. Name the person before anything is written.
 *
 * Linking the WRONG employee is the worst thing that can happen here and it
 * cannot be undone - "Made an employee" is terminal. So HR picks the record,
 * is shown the name on it, and says yes to that name. The name comes from the
 * Employee row itself, not from this form, so a confirmation cannot agree with
 * the mistake.
 */
function linkEmployeeRecord(frm) {
	frappe.prompt(
		[{
			fieldname: "employee", fieldtype: "Link", options: "Employee",
			reqd: 1, label: __("Their employee record"),
			description: __("The record you have just saved for this person."),
		}],
		(v) => frappe.db.get_value("Employee", v.employee, "employee_name")
			.then((got) => {
				/* Escaped: `frappe.warn` and `frappe.msgprint` render HTML, and
				   this name came out of the database. `makeSignIn` below already
				   does the same for the message it builds. */
				const named = frappe.utils.escape_html(
					(got && got.message && got.message.employee_name)
					|| v.employee);
				frappe.warn(
					__("Link this invite to {0}?", [named]),
					__("Everything this person sent becomes part of {0} ({1}), "
					 + "their joiner sign-in is closed, and this cannot be "
					 + "undone. Check the name is the right one.",
					   [named, v.employee]),
					() => linkItNow(frm, v.employee),
					__("Link it"), true);
			}),
		__("Link the employee record"), __("Next"));
}

function linkItNow(frm, employee) {
	frappe.call({
		method: "alvoraa_portal.joiner_to_employee.link_the_employee",
		args: { submission: frm.doc.name, employee: employee },
		freeze: true,
	}).then((r) => {
		const d = (r && r.message) || {};
		/* Rendered as HTML by `msgprint`, and both came out of the database -
		   so escaped, the way `makeSignIn` above already does it. */
		const who = frappe.utils.escape_html(d.employee_name || "");
		const which = frappe.utils.escape_html(d.employee || "");
		/* Real counts, computed from what actually moved. And the documents are
		   told the truth: nothing moves them to the employee record yet, so
		   this must not claim a tick that does not exist. */
		const lines = [
			__("{0} details are now on {1} ({2}), and their joiner sign-in is closed.",
			   [d.details, who, which]),
		];
		if (d.documents_left_behind) {
			lines.push(__("The {0} document(s) they uploaded are still on this "
			            + "invite and have NOT moved to the employee record. "
			            + "Download anything you need to keep.",
			              [d.documents_left_behind]));
		} else {
			lines.push(__("They uploaded no documents."));
		}
		frappe.msgprint({
			title: __("{0} is now an employee", [who]),
			indicator: "green",
			message: lines.map((l) => `<p>${l}</p>`).join(""),
		});
		frm.reload_doc();
	});
}
