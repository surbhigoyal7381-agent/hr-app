// The "Field attendance app" section on the Employee form (slice 013 step 5).
//
// What this file does: asks the server (E12) where this person stands with
// the app and draws the answer - one status line, the actions that state
// allows, the phones, the code history. The invite dialog draws HR's code as a
// QR picture from E7's answer, in the browser, and forgets it when the dialog
// closes (AC-47, AC-50). The block dialog asks for a reason (AC-110).
//
// What it does NOT do: decide anything. The server works out the state, refuses
// an HR user who may not read this employee, refuses a block with no reason,
// and never lets a blocked phone come back. This script can only offer less
// than the server allows, never more.
//
// Every refusal is written into the section, never popped up: `silent: true`
// on every call (step 2 found a plain 403 pops a dialog on every refresh).
//
// Every function and CSS hook is prefixed `alvfe` so this file cannot collide
// with ERPNext's employee.js, which runs on the same form.

(function () {
	const HTML_FIELD = "alvoraa_field_app_html";
	const M = {
		section: "alvoraa_portal.field_app_desk.employee_app_section",
		make: "alvoraa_portal.field_app_join.make_code",
		cancel: "alvoraa_portal.field_app_join.cancel_code",
		block: "alvoraa_portal.field_app_device.block_phone",
	};
	const esc = frappe.utils.escape_html;

	// ── words for a moment in time ──────────────────────────────────────

	function alvfeMoment(dt) {
		// Server datetimes are in the system time zone; shown in the user's.
		return frappe.datetime.convert_to_user_tz(dt, false);
	}

	function alvfeTime(dt) {
		return alvfeMoment(dt).format(frappe.datetime.get_user_time_fmt());
	}

	function alvfeFull(dt) {
		// "Thu 24 Sep 2026, 10:05 am" in the user's own time format.
		return alvfeMoment(dt).format("ddd D MMM YYYY, " + frappe.datetime.get_user_time_fmt());
	}

	function alvfeDay(dt) {
		return alvfeMoment(dt).format("D MMM YYYY");
	}

	// today and yesterday as "YYYY-MM-DD" in the user's time zone
	function alvfeDays() {
		const today = frappe.datetime.now_date();
		return { today: today, yesterday: moment(today, "YYYY-MM-DD").subtract(1, "days").format("YYYY-MM-DD") };
	}

	// "today at 10:05 am" / "yesterday at 4:12 pm" / "17 Sep 2026, 9:01 am"
	function alvfeWhen(dt) {
		if (!dt) return "";
		const m = alvfeMoment(dt);
		const day = m.format("YYYY-MM-DD");
		const d = alvfeDays();
		if (day === d.today) return __("today at {0}", [alvfeTime(dt)]);
		if (day === d.yesterday) return __("yesterday at {0}", [alvfeTime(dt)]);
		return m.format("D MMM YYYY, " + frappe.datetime.get_user_time_fmt());
	}

	// "today" / "yesterday" / "on 16 Sep 2026" - for "the code you made yesterday"
	function alvfeWhichDay(dt) {
		if (!dt) return "";
		const day = alvfeMoment(dt).format("YYYY-MM-DD");
		const d = alvfeDays();
		if (day === d.today) return __("today");
		if (day === d.yesterday) return __("yesterday");
		return __("on {0}", [alvfeDay(dt)]);
	}

	function alvfeFromNow(dt) {
		return alvfeMoment(dt).fromNow();    // "in 7 days", "2 hours ago"
	}

	function alvfeLifetime(hours) {
		if (hours % 24 === 0) {
			const d = hours / 24;
			return d === 1 ? __("1 day") : __("{0} days", [d]);
		}
		return hours === 1 ? __("1 hour") : __("{0} hours", [hours]);
	}

	// "you" for the person looking, the name for everybody else (D13, AC-104)
	function alvfeWho(info, user, name) {
		if (user && user === info.me) return __("you");
		return name || user || __("HR");
	}

	// ── talking to the server ───────────────────────────────────────────

	function alvfeCall(method, args) {
		return frappe.call({ method: method, args: args, silent: true, error: () => {} });
	}

	function alvfeRefusal(xhr) {
		// The body's own code first (desk_request puts it there), then the sentence.
		const body = (xhr && xhr.responseJSON) || {};
		let sentence = "";
		try {
			const messages = JSON.parse(body._server_messages);
			sentence = JSON.parse(messages[0]).message;
		} catch (e) {
			sentence = "";
		}
		return { code: body.code || "", sentence: sentence || __("This section could not be loaded.") };
	}

	// ── drawing ─────────────────────────────────────────────────────────

	function alvfeBox(frm) {
		const f = frm.fields_dict && frm.fields_dict[HTML_FIELD];
		return f ? f.$wrapper : null;
	}

	function alvfeIsHr() {
		return frappe.user.has_role(["HR Manager", "HR User", "System Manager"]);
	}

	function alvfeRender(frm) {
		const $box = alvfeBox(frm);
		if (!$box) return;
		if (frm.is_new() || !alvfeIsHr()) {
			$box.html("");
			return;
		}
		$box.html(`<p class="text-muted alvfe-note">${esc(__("Loading…"))}</p>`);
		alvfeCall(M.section, { employee: frm.doc.name })
			.then((r) => alvfeDraw(frm, $box, r && r.message))
			.catch((xhr) => {
				const why = alvfeRefusal(xhr);
				const words = why.code === "FEATURE_OFF"
					? __("Field check-in is not part of your plan.")
					: why.sentence;
				$box.html(alvfeStyle() + `<div class="alvfe"><p class="text-muted alvfe-note">${esc(words)}</p></div>`);
			});
	}

	function alvfeStyle() {
		return `<style>
			.alvfe .alvfe-sub { color: var(--text-muted); margin: 0 0 .8em; }
			.alvfe .alvfe-line { display: flex; flex-wrap: wrap; gap: .5em 1em; align-items: baseline; margin: 0 0 .5em; }
			.alvfe .alvfe-actions { display: flex; flex-wrap: wrap; gap: .5em; margin: .6em 0 1em; }
			.alvfe h6 { margin: 1.2em 0 .4em; }
			.alvfe table { width: 100%; }
			.alvfe td, .alvfe th { vertical-align: top; padding: .4em .5em; border-bottom: 1px solid var(--border-color); text-align: left; }
			.alvfe small { display: block; color: var(--text-muted); }
			.alvfe .alvfe-hist { list-style: none; padding: 0; margin: 0; }
			.alvfe .alvfe-hist li { display: flex; flex-wrap: wrap; gap: .5em 1em; padding: .4em 0; border-bottom: 1px solid var(--border-color); }
			.alvfe .alvfe-when { min-width: 11em; color: var(--text-muted); }
			.alvfe .alvfe-warn { background: var(--yellow-50, #fff8e1); border-left: 3px solid var(--yellow-500, #e5a100); padding: .5em .8em; margin: .6em 0; }
			.alvfe .alvfe-info { background: var(--bg-light-gray, #f5f5f5); padding: .5em .8em; margin: .6em 0; }
			.alvfe .alvfe-dot { display: inline-block; width: .6em; height: .6em; border-radius: 50%; margin-right: .35em; vertical-align: middle; }
			.alvfe-qr { display: flex; flex-wrap: wrap; gap: 1.2em; align-items: flex-start; }
			.alvfe-qr svg { width: 220px; height: 220px; border: 1px solid var(--border-color); }
			.alvfe-qr .alvfe-facts { flex: 1 1 200px; }
		</style>`;
	}

	// Colour AND a word, never colour alone.
	function alvfePill(colour, word) {
		return `<span class="indicator-pill ${esc(colour)}"><span class="alvfe-dot"></span>${esc(word)}</span>`;
	}

	const STATUS_COLOUR = {
		Active: "green", "Waiting for HR": "orange", Blocked: "red", Replaced: "gray",
		Removed: "gray", Stopped: "gray", "Not agreed yet": "orange", "Signed out": "gray",
	};

	function alvfeStatusLine(info) {
		const e = info.employee;
		const first = e.first_name;
		const p = info.phone;
		const w = info.waiting_code;
		const line = (pill, words, hint) =>
			`<div class="alvfe-line">${pill || ""}<span>${words}</span></div>` +
			(hint ? `<p class="text-muted alvfe-note">${hint}</p>` : "");

		switch (info.state) {
			case "not_active":
				return line("", `<b>${esc(__("{0} is not an active employee.", [e.employee_name]))}</b> ${esc(__("Codes and phones are stopped when somebody leaves."))}`);
			case "app_off":
				return line(alvfePill("orange", __("App switched off")),
					esc(__("Field workers cannot use the app at the moment. You cannot make codes.")),
					esc(__("{0} can still use the web check-in page at {1}.", [first, info.checkin_url])));
			case "not_field":
				return line("", `<b>${esc(__("The app is not available for {0}.", [e.employee_name]))}</b> ` +
					(e.designation
						? esc(__("Designation {0} is not a field worker designation.", [e.designation]))
						: esc(__("This employee has no designation, and only listed designations can use the app."))),
					esc(__("{0} marks attendance at the reception machine, or with Check In in the portal.", [first])));
			case "code_waiting":
				return line(alvfePill("purple", __("Code waiting")),
					esc(__("Made by {0} {1}.", [alvfeWho(info, w.made_by, w.made_by_name), alvfeWhen(w.made_at)])) +
					" " + __("Works until <b>{0}</b> ({1}).", [esc(alvfeFull(w.expires_at)), esc(alvfeFromNow(w.expires_at))]),
					esc(__("This code cannot be shown again. If {0} lost it, make a new one. That cancels this one.", [first])));
			case "joined": {
				const how = p.join_method === "App QR code"
					? __("by the QR code {0} made {1}", [alvfeWho(info, p.invite_made_by, p.invite_made_by_name), alvfeWhichDay(p.invite_made_at)])
					: p.join_method === "App password sign-in"
						? __("by signing in with their email and password")
						: __("on the web check-in page, approved by {0}", [alvfeWho(info, p.activated_by, p.activated_by_name)]);
				const last = p.last_seen
					? esc(__("Last check-in {0}{1}.", [alvfeWhen(p.last_seen), p.last_place ? " " + __("at {0}", [p.last_place]) : ""]))
					: esc(__("No check-in from this phone yet."));
				return line(alvfePill("green", __("Joined")),
					`<b>${esc(__("Joined {0} · {1} · {2}", [alvfeWhen(p.registered_on), p.device_label || __("phone"), how]))}</b>`, last);
			}
			case "not_agreed":
				return line(alvfePill("orange", __("Not agreed yet")),
					esc(__("{0} set up {1} {2} but has not agreed to the notice yet. The app asks again each time it opens; the phone cannot check in until then.",
						[first, p.device_label || __("a phone"), alvfeWhen(p.registered_on)])));
			case "web_pending":
				return line(alvfePill("orange", __("Waiting for HR")),
					esc(__("{0} registered {1} on the web check-in page {2}. Open the phone record to switch it on, or invite {0} to the app instead.",
						[first, p.device_label || __("a phone"), alvfeWhen(p.registered_on)])));
			case "blocked":
				return line(alvfePill("red", __("No working phone")),
					esc(__("{0} was blocked {1} by {2} · {3}.", [p.device_label || __("The phone"), alvfeWhen(p.status_changed_on),
						alvfeWho(info, p.status_changed_by, p.status_changed_by_name), __(p.block_reason || "")])));
			default:
				if (p && p.status === "Signed out") {
					return line("", `<b>${esc(__("No working phone."))}</b> ${esc(__("The password for {0}'s login was changed {1}, so {2} was signed out. {0} can sign in again with the new password. No code is needed.", [first, alvfeWhen(p.status_changed_on), p.device_label || __("the phone")]))}`);
				}
				if (p && p.status === "Removed") {
					return line("", `<b>${esc(__("No working phone."))}</b> ${esc(__("{0} removed {1} {2}.", [first, p.device_label || __("the last phone"), alvfeWhen(p.status_changed_on)]))}`);
				}
				return line("", `<b>${esc(__("Not joined yet."))}</b> ${__("{0} can use the app: <b>{1}</b> is a field worker designation.", [esc(first), esc(e.designation)])}`);
		}
	}

	function alvfeActions(info) {
		const out = [];
		if (info.can_invite) {
			const label = info.state === "code_waiting" ? __("Make a new code")
				: info.state === "joined" ? __("Invite to the app again")
				: __("Invite to the app");
			const primary = info.state === "code_waiting" || info.state === "joined" ? "btn-default" : "btn-primary";
			out.push(`<button type="button" class="btn btn-sm ${primary}" data-alvfe="invite">${esc(label)}</button>`);
		}
		if (info.state === "code_waiting") {
			out.push(`<button type="button" class="btn btn-sm btn-default" data-alvfe="cancel" data-name="${esc(info.waiting_code.name)}">${esc(__("Cancel this code"))}</button>`);
		}
		if (info.state === "not_field") {
			out.push(`<a class="btn btn-sm btn-default" href="/app/hr-settings">${esc(__("Change field worker designations"))}</a>`);
		}
		if (info.state === "app_off") {
			out.push(`<a class="btn btn-sm btn-default" href="/app/hr-settings">${esc(__("Open Field App Settings"))}</a>`);
		}
		return out.length ? `<div class="alvfe-actions">${out.join("")}</div>` : "";
	}

	function alvfePhones(info) {
		if (!info.phones.length) {
			return `<h6>${esc(__("Phones"))}</h6><p class="text-muted">${esc(__("No phones yet."))}</p>`;
		}
		const rows = info.phones.map((p) => {
			const how = p.join_method === "App QR code"
				? esc(__("QR code made by {0}", [alvfeWho(info, p.invite_made_by, p.invite_made_by_name)])) + `<small>${esc(alvfeWhen(p.invite_made_at))}</small>`
				: p.join_method === "App password sign-in"
				? esc(__("Email and password")) + `<small>${esc(alvfeWhen(p.registered_on))}</small>`
				: esc(__("Web check-in page")) + (p.activated_by
					? `<small>${esc(__("approved by {0}, {1}", [alvfeWho(info, p.activated_by, p.activated_by_name), alvfeWhen(p.status_changed_on || p.registered_on)]))}</small>`
					: "");
			let status = alvfePill(STATUS_COLOUR[p.status_word] || "gray", __(p.status_word));
			if (p.status === "Blocked") status += `<small>${esc(alvfeWhen(p.status_changed_on))}${p.block_reason ? " · " + esc(__(p.block_reason)) : ""}</small>`;
			else if (p.status === "Replaced" || p.status === "Removed" || p.status === "Signed out") status += `<small>${esc(alvfeWhen(p.status_changed_on))}</small>`;
			else if (p.stopped) status += `<small>${esc(info.app.enabled ? __("Not a field worker designation now") : __("App switched off"))}</small>`;
			if (p.not_field_worker) {
				status += `<small>${alvfePill("orange", __("Not a field worker"))}</small><small>${esc(__("Joined before this rule. Keeps working."))}</small>`;
			}
			const last = p.last_seen
				? esc(alvfeWhen(p.last_seen)) + (p.last_place ? `<small>${esc(p.last_place)}</small>` : "")
				: `<span class="text-muted">${esc(__("None yet"))}</span>`;
			const action = p.can_block
				? `<button type="button" class="btn btn-xs btn-default" data-alvfe="block" data-name="${esc(p.name)}" data-label="${esc(p.device_label || __("this phone"))}">${esc(__("Block this phone"))}</button>`
				: "";
			return `<tr>
				<td><b>${esc(p.device_label || __("Phone"))}</b><small>${esc([p.platform, p.app_version ? __("app {0}", [p.app_version]) : ""].filter(Boolean).join(" · "))}</small></td>
				<td>${how}</td>
				<td>${esc(alvfeWhen(p.registered_on))}</td>
				<td>${last}</td>
				<td>${status}</td>
				<td>${action}</td>
			</tr>`;
		}).join("");
		return `<h6>${esc(__("Phones"))}</h6>
			<div class="table-responsive" role="region" aria-label="${esc(__("Phones"))}" tabindex="0"><table class="table table-sm">
			<thead><tr><th>${esc(__("Phone"))}</th><th>${esc(__("How it joined"))}</th><th>${esc(__("Joined"))}</th><th>${esc(__("Last check-in"))}</th><th>${esc(__("Status"))}</th><th><span class="sr-only">${esc(__("Action"))}</span></th></tr></thead>
			<tbody>${rows}</tbody></table></div>`;
	}

	function alvfeCodes(info) {
		if (!info.codes.length) {
			return `<h6>${esc(__("App codes"))}</h6><p class="text-muted">${esc(__("No codes made yet."))}</p>`;
		}
		const items = info.codes.map((c) => {
			let outcome;
			switch (c.outcome) {
				case "waiting": outcome = alvfePill("purple", __("Waiting to be used · until {0}", [alvfeFull(c.expires_at)])); break;
				case "used": outcome = alvfePill("green", __("Used {0} on {1}", [alvfeWhen(c.used_at), c.used_device_label || __("a phone")])); break;
				case "cancelled_by_hr": outcome = alvfePill("gray", __("Cancelled by {0}, {1}", [alvfeWho(info, c.cancelled_by, c.cancelled_by_name), alvfeWhen(c.cancelled_at)])); break;
				case "not_me": outcome = alvfePill("orange", __('Cancelled on a phone: "This is not me", {0}', [alvfeWhen(c.cancelled_at)])); break;
				case "newer_code": outcome = alvfePill("gray", __("Replaced by a newer code, {0}", [alvfeWhen(c.cancelled_at)])); break;
				case "employee_left": outcome = alvfePill("gray", __("Cancelled: left the company, {0}", [alvfeWhen(c.cancelled_at)])); break;
				default: outcome = alvfePill("gray", __("Ran out {0}", [alvfeWhen(c.expires_at)]));
			}
			return `<li><span class="alvfe-when">${esc(alvfeWhen(c.made_at))}</span>
				<span>${esc(__("Made by {0} · works {1}", [alvfeWho(info, c.made_by, c.made_by_name), alvfeLifetime(c.lifetime_hours)]))}</span>${outcome}</li>`;
		}).join("");
		return `<h6>${esc(__("App codes"))}</h6><ul class="alvfe-hist" aria-label="${esc(__("App codes"))}">${items}</ul>`;
	}

	function alvfeDraw(frm, $box, info) {
		if (!info) {
			$box.html("");
			return;
		}
		frm._alvfe = info;
		$box.html(alvfeStyle() + `<div class="alvfe">
			<p class="alvfe-sub">${esc(__("The Alvoraa phone app for field workers: photo check-in with place and time."))}</p>
			${alvfeStatusLine(info)}
			${alvfeActions(info)}
			${alvfePhones(info)}
			${alvfeCodes(info)}
		</div>`);
		$box.find("[data-alvfe=invite]").on("click", () => alvfeInvite(frm, info));
		$box.find("[data-alvfe=cancel]").on("click", (ev) => alvfeCancel(frm, info, ev.currentTarget.dataset.name));
		$box.find("[data-alvfe=block]").on("click", (ev) =>
			alvfeBlock(frm, info, ev.currentTarget.dataset.name, ev.currentTarget.dataset.label));
	}

	// ── invite: step 1, choose the time ─────────────────────────────────

	function alvfeInvite(frm, info) {
		const first = info.employee.first_name;
		const full = info.employee.employee_name;
		const options = info.app.lifetimes.map((l) =>
			({ value: String(l.hours), label: l.hours === info.app.lifetime_hours
				? __("{0} (your organisation's setting)", [__(l.label)]) : __(l.label) }));
		const hasCode = info.state === "code_waiting";
		const active = info.phones.find((p) => p.status === "Active");
		let notes = "";
		if (hasCode) notes += `<div class="alvfe-warn">${esc(__("{0} already has a code waiting to be used. Making a new code cancels it.", [first]))}</div>`;
		if (active) notes += `<div class="alvfe-info">${esc(__("Use this when {0} changes phone. When the new phone joins, {1} stops working.", [first, active.device_label || __("the current phone")]))}</div>`;

		const d = new frappe.ui.Dialog({
			title: __("Invite {0} to the app", [full]),
			fields: [
				{
					fieldtype: "HTML", fieldname: "intro",
					options: alvfeStyle() + `<div class="alvfe"><p>${esc(__("This makes a QR code that only {0} can use, once. When {0} scans it with the Alvoraa app and confirms the name, the phone is set up straight away.", [first]))} <b>${esc(__("You do not need to approve it."))}</b></p></div>`,
				},
				{
					fieldtype: "Select", fieldname: "hours", label: __("The code works for"),
					options: options, default: String(info.app.lifetime_hours), reqd: 0,
					description: __("You can choose a shorter time than your organisation's setting, not a longer one. Shorter is safer."),
				},
				{ fieldtype: "HTML", fieldname: "notes", options: alvfeStyle() + `<div class="alvfe">${notes}</div>` },
			],
			primary_action_label: __("Make the code"),
			primary_action(values) {
				d.get_primary_btn().prop("disabled", true);
				alvfeCall(M.make, { employee: info.employee.name, lifetime_hours: values.hours })
					.then((r) => {
						d.hide();
						alvfeShowCode(frm, info, r.message);
					})
					.catch((xhr) => {
						d.get_primary_btn().prop("disabled", false);
						const why = alvfeRefusal(xhr);
						// ALV-128: HR turned the code way in off on HR Settings.
						const words = why.code === "JOIN_CODE_OFF"
							? __("Joining codes are switched off in HR Settings.")
							: why.sentence;
						d.fields_dict.notes.$wrapper.html(alvfeStyle() + `<div class="alvfe"><div class="alvfe-warn" role="alert">${esc(words)}</div></div>`);
					});
			},
			secondary_action_label: __("Cancel"),
			secondary_action() { d.hide(); },
		});
		d.show();
	}

	// ── invite: step 2, the code, shown once ────────────────────────────

	function alvfeShowCode(frm, info, made) {
		const first = info.employee.first_name;
		const full = info.employee.employee_name;
		const link = made.link;
		const svg = window.AlvoraaQR.svg(link, 4, 4);
		const steps = `<ol>
			<li>${__("Install <b>Alvoraa</b> from the Play Store.")}</li>
			<li>${__("Open it and press <b>Scan the QR code from HR</b>.")}</li>
			<li>${__("Check the name and press <b>Yes, this is me</b>.")}</li></ol>`;
		const d = new frappe.ui.Dialog({
			title: __("App code for {0}", [full]),
			size: "large",
			fields: [{
				fieldtype: "HTML", fieldname: "code",
				options: alvfeStyle() + `<div class="alvfe">
					<div class="alvfe-qr"><div class="alvfe-qr-pic" aria-label="${esc(__("QR code for {0}", [full]))}">${svg}</div>
					<div class="alvfe-facts">${alvfePill("purple", __("Waiting to be used"))}
						<p style="margin:.6em 0 .2em"><b>${esc(__("Works once."))}</b></p>
						<p style="margin:0 0 .2em">${__("Works until <b>{0}</b> ({1}).", [esc(alvfeFull(made.expires_at)), esc(alvfeFromNow(made.expires_at))])}</p>
						<p class="text-muted" style="margin:0">${esc(__("Made by you {0}.", [alvfeWhen(made.made_at)]))}</p>
					</div></div>
					<h6>${esc(__("Tell {0}", [first]))}</h6>${steps}
					<div class="alvfe-warn"><b>${esc(__("Anyone who has this code or link can join as {0} until it is used.", [first]))}</b> ${esc(__("Give it only to {0}. If it goes to the wrong person, cancel it.", [first]))}</div>
					<div class="alvfe-info">${esc(__("You can see this code only now. If it is lost, make a new one."))}</div>
					<div class="alvfe-actions">
						<button type="button" class="btn btn-sm btn-default" data-alvfe="print">${esc(__("Print"))}</button>
						<button type="button" class="btn btn-sm btn-default" data-alvfe="copy">${esc(__("Copy picture"))}</button>
					</div>
					<p role="status" aria-live="polite" class="alvfe-status" style="margin:0"></p>
				</div>`,
			}],
			primary_action_label: __("Done"),
			primary_action() { d.hide(); },
			onhide() {
				// The code lives only in this dialog. Gone with it (AC-50).
				d.fields_dict.code.$wrapper.html("");
				alvfeRender(frm);
			},
		});
		d.show();
		const $w = d.fields_dict.code.$wrapper;
		$w.find("[data-alvfe=print]").on("click", () => alvfePrint(info, made, svg));
		$w.find("[data-alvfe=copy]").on("click", () => alvfeCopyPicture(link, first, $w.find(".alvfe-status")));
	}

	function alvfeCopyPicture(link, first, $status) {
		const say = (words) => $status.text(words);
		if (!navigator.clipboard || typeof window.ClipboardItem === "undefined") {
			say(__("This browser cannot copy a picture. Use Print instead."));
			return;
		}
		try {
			const canvas = window.AlvoraaQR.draw(document.createElement("canvas"), link, 8, 4);
			canvas.toBlob((blob) => {
				navigator.clipboard.write([new window.ClipboardItem({ "image/png": blob })])
					.then(() => say(__("Picture copied. Paste it in WhatsApp to {0}.", [first])))
					.catch(() => say(__("Could not copy the picture. Use Print instead.")));
			}, "image/png");
		} catch (e) {
			say(__("Could not copy the picture. Use Print instead."));
		}
	}

	// Our own printed sheet (AC-49): company, name, designation, the QR, the
	// three steps, the warning. No employee ID. Not Frappe's print view - the
	// phone record has print switched off on purpose, and the code must not be
	// sent to the server to be laid out.
	function alvfePrint(info, made, svg) {
		const e = info.employee;
		const html = `<!doctype html><html lang="en"><head><meta charset="utf-8"><title>${esc(__("Your Alvoraa app code"))}</title>
			<style>
				body { font-family: sans-serif; margin: 20mm; color: #111; }
				h1 { font-size: 22pt; margin: .2em 0; } .co { color: #555; font-size: 11pt; }
				.row { display: flex; gap: 12mm; align-items: flex-start; margin: 8mm 0; }
				svg { width: 60mm; height: 60mm; } ol { font-size: 13pt; line-height: 1.6; }
				.foot { border-top: 1px solid #999; padding-top: 4mm; font-size: 12pt; }
				@page { size: A4; margin: 15mm; }
			</style></head><body>
			<div class="co">${esc(e.company)}</div>
			<h1>${esc(__("Your Alvoraa app code"))}</h1>
			<div>${__("For <b>{0}</b>", [esc(e.employee_name)])}${e.designation ? " · " + esc(e.designation) : ""}</div>
			<div class="row">${svg}<ol>
				<li>${__("Install <b>Alvoraa</b> from the Play Store.")}</li>
				<li>${__("Open it and press <b>Scan the QR code from HR</b>.")}</li>
				<li>${__("Check your name and press <b>Yes, this is me</b>.")}</li></ol></div>
			<div class="foot">${__("This code works <b>once</b>, until <b>{0}</b>. Do not share it. If this sheet is lost, tell HR.", [esc(alvfeFull(made.expires_at))])}</div>
			<script>window.onload = function () { window.print(); };</script>
			</body></html>`;
		const w = window.open("", "_blank");
		if (!w) {
			frappe.show_alert({ message: __("The browser blocked the print window. Allow pop-ups for this site and try again."), indicator: "orange" });
			return;
		}
		w.document.open();
		w.document.write(html);
		w.document.close();
	}

	// ── cancel a waiting code ───────────────────────────────────────────

	function alvfeCancel(frm, info, name) {
		const first = info.employee.first_name;
		const d = new frappe.ui.Dialog({
			title: __("Cancel this code?"),
			fields: [{ fieldtype: "HTML", fieldname: "what", options: `<p>${esc(__("{0} will not be able to use it. Nothing else changes. You can make a new code at any time.", [first]))}</p><p class="alvfe-err text-danger" role="alert"></p>` }],
			primary_action_label: __("Cancel the code"),
			primary_action() {
				alvfeCall(M.cancel, { invite: name })
					.then(() => { d.hide(); alvfeRender(frm); })
					.catch((xhr) => d.fields_dict.what.$wrapper.find(".alvfe-err").text(alvfeRefusal(xhr).sentence));
			},
			secondary_action_label: __("Keep it"),
			secondary_action() { d.hide(); },
		});
		d.get_primary_btn().addClass("btn-danger");
		d.show();
	}

	// ── block a phone ───────────────────────────────────────────────────

	function alvfeBlock(frm, info, name, label) {
		const first = info.employee.first_name;
		const d = new frappe.ui.Dialog({
			title: __("Block {0}?", [label]),
			fields: [
				{
					fieldtype: "HTML", fieldname: "what",
					options: `<ul>
						<li>${esc(__("{0} cannot mark attendance on this phone from now on.", [first]))}</li>
						<li>${esc(__("Attendance already marked stays."))}</li>
						<li>${esc(__('The phone will say: "This phone has been stopped. Please speak to HR."'))}</li>
						<li><b>${esc(__("This cannot be undone."))}</b> ${esc(__("If {0} gets the phone back, make a new code.", [first]))}</li></ul>`,
				},
				{
					fieldtype: "Select", fieldname: "reason", label: __("Why are you blocking it?"),
					options: ["", ...info.block_reasons.map((r) => ({ value: r, label: __(r) }))],
					// Not `reqd`: Frappe would then show its own "missing fields"
					// popup instead of the sentence under the field (AC-110).
					reqd: 0,
					description: __("Kept in the record. {0} does not see the reason.", [first]),
				},
				{ fieldtype: "HTML", fieldname: "err", options: `<p class="alvfe-err text-danger" role="alert"></p>` },
			],
			primary_action_label: __("Block this phone"),
			primary_action(values) {
				const $err = d.fields_dict.err.$wrapper.find(".alvfe-err");
				if (!values.reason) {
					$err.text(__("Choose a reason. It is kept in the record."));
					return;
				}
				alvfeCall(M.block, { device: name, reason: values.reason })
					.then(() => { d.hide(); alvfeRender(frm); })
					.catch((xhr) => $err.text(alvfeRefusal(xhr).sentence));
			},
			secondary_action_label: __("Keep it working"),
			secondary_action() { d.hide(); },
		});
		d.get_primary_btn().addClass("btn-danger");
		d.show();
	}

	// ── form events ─────────────────────────────────────────────────────

	frappe.ui.form.on("Employee", {
		refresh(frm) {
			alvfeRender(frm);
		},
		after_save(frm) {
			alvfeRender(frm);
		},
	});
})();
