// The "Field attendance app" tab on HR Settings (slice 013 step 2, US-3).
//
// What this file does: shows the live counts, the photo retention line and the
// change history beside the fields; and, before HR turns the app off or removes
// a designation, says what that will stop and asks for a reason.
//
// What it does NOT do: enforce anything. The server refuses a save that turns
// the app off, or drops a designation, without a reason - on the desk, over
// REST and through set_value alike (field_app_settings.validate_hr_settings).
// This script only makes sure nobody is surprised by that refusal, and that
// the person sees how many phones they are about to stop before they do it.
//
// Every function and CSS hook is prefixed `alvfa` so this file cannot collide
// with hrms' own hr_settings.js, which runs on the same form.

(function () {
	const F = {
		designations: "alvoraa_field_worker_designations",
		enabled: "alvoraa_field_app_enabled",
		lifetime: "alvoraa_app_code_lifetime",
		reason: "alvoraa_field_app_change_reason",
		info: "alvoraa_field_app_info",
	};
	const METHOD = "alvoraa_portal.field_app_settings.settings_info";

	const esc = frappe.utils.escape_html;

	function alvfaRows(frm) {
		return (frm.doc[F.designations] || []).map((r) => r.designation).filter(Boolean);
	}

	function alvfaHasTab(frm) {
		return !!(frm.fields_dict && frm.fields_dict[F.enabled] && frm.fields_dict[F.info]);
	}

	function alvfaIsHr() {
		return frappe.user.has_role(["HR Manager", "HR User", "System Manager"]);
	}

	// The saved state, remembered whenever the form is clean, so a change on
	// screen can be compared against what the database holds.
	function alvfaRemember(frm) {
		if (!frm.is_dirty()) {
			frm._alvfa_saved = {
				enabled: !!frm.doc[F.enabled],
				designations: alvfaRows(frm),
			};
		}
	}

	function alvfaFetch(frm, designations) {
		return frappe.call({
			method: METHOD,
			args: { designations: JSON.stringify(designations) },
			// A refusal (not in the plan, not HR) is shown in the box, not as a
			// dialog over a settings page the person can otherwise use.
			error: () => {},
		});
	}

	// ── the box beside the fields ───────────────────────────────────────

	function alvfaRender(frm) {
		if (!alvfaHasTab(frm)) return;
		const $box = frm.fields_dict[F.info].$wrapper;
		if (!alvfaIsHr()) {
			$box.html("");
			return;
		}
		alvfaFetch(frm, alvfaRows(frm))
			.then((r) => alvfaDraw(frm, $box, r && r.message))
			.catch((e) => {
				const msg = (e && e.message) || __("This section could not be loaded.");
				$box.html(`<p class="text-muted alvfa-note">${esc(String(msg))}</p>`);
			});
	}

	function alvfaDraw(frm, $box, info) {
		if (!info) {
			$box.html("");
			return;
		}
		const count = __("{0} active employees have these designations.", [
			info.employees_with_designations,
		]);
		let history = `<p class="text-muted">${esc(__("No changes yet."))}</p>`;
		if (info.history && info.history.length) {
			history =
				`<ul class="alvfa-history" aria-label="${esc(__("Change history"))}">` +
				info.history
					.map((h) => {
						const lines = h.lines.map((l) => `<div>${esc(l)}</div>`).join("");
						const reason = h.reason
							? `<div class="text-muted">${esc(__("Why: {0}", [h.reason]))}</div>`
							: "";
						return (
							`<li><div><strong>${esc(frappe.datetime.str_to_user(h.when))}</strong>` +
							` · ${esc(h.who)}</div>${lines}${reason}</li>`
						);
					})
					.join("") +
				`</ul>`;
		}
		$box.html(`
			<div class="alvfa-info">
				<p class="alvfa-count" aria-live="polite">${esc(count)}</p>
				<h6>${esc(__("Photos"))}</h6>
				<p>${esc(info.retention_line)}</p>
				<h6>${esc(__("Change history"))}</h6>
				<p class="text-muted">${esc(info.history_note)}</p>
				${history}
			</div>
			<style>
				.alvfa-history { padding-left: 1.2em; margin: 0; }
				.alvfa-history li { margin-bottom: .6em; }
				.alvfa-info h6 { margin-top: 1em; }
			</style>
		`);
	}

	// ── the confirm dialogs ─────────────────────────────────────────────

	function alvfaReasonField() {
		// The same fixed list the field on the form has, read off the form so
		// the two can never differ.
		const df = frappe.meta.get_docfield("HR Settings", F.reason);
		return {
			fieldtype: "Select",
			fieldname: "reason",
			label: __("Why? (kept in the change history)"),
			options: (df && df.options) || "",
			reqd: 1,
			description: __("Choose a reason. It is kept in the change history."),
		};
	}

	function alvfaConfirm(frm, opts) {
		// opts: title, lines[], primary, onKeep, onGo
		const d = new frappe.ui.Dialog({
			title: opts.title,
			fields: [
				{
					fieldtype: "HTML",
					fieldname: "what",
					options: `<ul class="alvfa-what">${opts.lines
						.map((l) => `<li>${esc(l)}</li>`)
						.join("")}</ul>`,
				},
				alvfaReasonField(),
			],
			primary_action_label: opts.primary,
			primary_action(values) {
				if (!values.reason) {
					frappe.msgprint(__("Choose a reason. It is kept in the change history."));
					return;
				}
				d.hide();
				opts.onGo(values.reason);
			},
			secondary_action_label: __("Keep it"),
			secondary_action() {
				d.hide();
				opts.onKeep();
			},
		});
		d.get_primary_btn().addClass("btn-danger");
		d.show();
		return d;
	}

	function alvfaAskBeforeTurningOff(frm) {
		alvfaFetch(frm, alvfaRows(frm)).then((r) => {
			const info = (r && r.message) || {};
			alvfaConfirm(frm, {
				title: __("Turn off the app for field workers?"),
				lines: [
					__("You will not be able to make new codes."),
					__("{0} codes waiting to be used will stop working.", [info.waiting_codes || 0]),
					__('{0} phones that joined will stop marking attendance. They will say: "{1}"', [
						info.active_app_phones || 0,
						info.app_off_words || "",
					]),
					__("Field workers can still use the web check-in page."),
				],
				primary: __("Turn off"),
				onKeep() {
					frm.set_value(F.enabled, 1);
				},
				onGo(reason) {
					frm.set_value(F.reason, reason);
				},
			});
		});
	}

	function alvfaAskBeforeRemoving(frm, designation) {
		alvfaFetch(frm, [designation]).then((r) => {
			const info = (r && r.message) || {};
			const per = (info.per_designation && info.per_designation[designation]) || {};
			alvfaConfirm(frm, {
				title: __("Remove {0} from the field worker designations?", [designation]),
				lines: [
					__("{0} active employees have this designation.", [per.employees || 0]),
					__('{0} of them have an app phone. Those phones will stop marking attendance. They will say: "{1}"', [
						per.phones || 0,
						info.not_field_words || "",
					]),
					__("They can still use the web check-in page."),
				],
				primary: __("Remove"),
				onKeep() {
					// Put the row back exactly as it was.
					frm.add_child(F.designations, { designation: designation });
					frm.refresh_field(F.designations);
					alvfaRender(frm);
				},
				onGo(reason) {
					frm.set_value(F.reason, reason);
				},
			});
		});
	}

	// ── form events ─────────────────────────────────────────────────────

	const events = {
		refresh(frm) {
			alvfaRemember(frm);
			alvfaRender(frm);
		},

		after_save(frm) {
			alvfaRemember(frm);
			alvfaRender(frm);
		},

		validate(frm) {
			// The server refuses this too. Saying it here first means the person
			// is told what to do, not shown a red error after a round trip.
			if (!alvfaHasTab(frm) || !frm._alvfa_saved) return;
			const saved = frm._alvfa_saved;
			const now = alvfaRows(frm);
			const turningOff = saved.enabled && !frm.doc[F.enabled];
			const removed = saved.designations.filter((d) => !now.includes(d));
			if ((turningOff || removed.length) && !frm.doc[F.reason]) {
				frappe.msgprint({
					title: __("Choose a reason"),
					message: __("Choose a reason. It is kept in the change history."),
					indicator: "orange",
				});
				frappe.validated = false;
			}
		},
	};

	events[F.enabled] = function (frm) {
		if (!frm._alvfa_saved) return;
		if (frm._alvfa_saved.enabled && !frm.doc[F.enabled]) {
			alvfaAskBeforeTurningOff(frm);
		}
	};

	events[F.designations] = function (frm) {
		alvfaRender(frm);
	};

	// Table MultiSelect fires these two on the PARENT form when a pill is
	// removed: the first while the row still exists, the second after it has
	// gone. The designation is read in the first and the question asked in the
	// second, so the row is really gone by the time the counts are shown.
	events[`before_${F.designations}_remove`] = function (frm, cdt, cdn) {
		const row = frappe.get_doc(cdt, cdn);
		frm._alvfa_removing = row && row.designation;
	};

	events[`${F.designations}_remove`] = function (frm) {
		const designation = frm._alvfa_removing;
		frm._alvfa_removing = null;
		alvfaRender(frm);
		if (!designation || !frm._alvfa_saved) return;
		if (frm._alvfa_saved.designations.includes(designation)) {
			alvfaAskBeforeRemoving(frm, designation);
		}
	};

	events[`${F.designations}_add`] = function (frm) {
		alvfaRender(frm);
	};

	frappe.ui.form.on("HR Settings", events);
})();
