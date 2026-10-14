// ATT-07, the button: re-run the attendance rules before the slips are made.
//
// Attendance does not stand still. Punches arrive late, a device gets fixed, a
// manager confirms a held day, the special-day calendar lands mid-month. A
// payroll entry prepared on Monday is built on Monday's attendance.
//
// This offers the reprocess at the moment it matters - with the payroll entry
// open and the employees already chosen - and it NEVER writes on the first
// click. The first click only asks the server what would change, and shows it.
//
// The dialogue deliberately leads with the money. A confirmation that says
// "Reprocess?" with no numbers is a button, not a decision, and somebody will
// click it without looking.

frappe.ui.form.on("Payroll Entry", {
	refresh(frm) {
		if (frm.doc.docstatus === 2) return;

		frm.add_custom_button(__("Reprocess Attendance"), () => {
			reprocess_preview(frm);
		}, __("Tools"));
	},
});

function selected_employees(frm) {
	// The payroll entry's own list. Empty means every employee in the company
	// for those dates, which is what the server does with no list.
	return (frm.doc.employees || []).map((row) => row.employee).filter(Boolean);
}

function reprocess_preview(frm) {
	if (!frm.doc.company || !frm.doc.start_date || !frm.doc.end_date) {
		frappe.msgprint({
			title: __("Not enough to go on"),
			message: __("Set the company and the payroll period first."),
			indicator: "orange",
		});
		return;
	}

	frappe.dom.freeze(__("Working out what would change..."));
	frappe.call({
		method: "alvoraa_portal.payroll_reprocess.preview",
		args: {
			company: frm.doc.company,
			from_date: frm.doc.start_date,
			to_date: frm.doc.end_date,
			employees: JSON.stringify(selected_employees(frm)),
		},
		callback: (r) => {
			frappe.dom.unfreeze();
			if (!r.message) return;
			if (!r.message.ok) {
				frappe.msgprint({
					title: __("Nothing to re-run"),
					message: r.message.reason,
					indicator: "blue",
				});
				return;
			}
			show_preview(frm, r.message);
		},
		error: () => frappe.dom.unfreeze(),
	});
}

function show_preview(frm, data) {
	const t = data.totals;

	if (!t.changed) {
		frappe.msgprint({
			title: __("Nothing has changed"),
			message: __(
				"{0} day(s) were checked and every one already matches the rules. "
				+ "The attendance behind this payroll run has settled.",
				[t.days]
			),
			indicator: "green",
		});
		return;
	}

	// Positive money means the reprocess hands pay back; negative means it
	// deducts more. Saying which, in words, matters more than the sign.
	const gives_back = t.money >= 0;
	const money = frappe.format(Math.abs(t.money), { fieldtype: "Currency" });

	let html = `
		<div style="margin-bottom:14px;padding:12px 14px;border-radius:6px;
		            background:${gives_back ? "#e8f3f0" : "#fce9e6"}">
			<div style="font-size:1.35em;font-weight:600">
				${gives_back ? __("Pays back {0}", [money]) : __("Deducts a further {0}", [money])}
			</div>
			<div class="text-muted" style="margin-top:3px">
				${__("across {0} day(s) for {1} employee(s)", [t.changed, data.employees_affected])}
			</div>
		</div>
		<table class="table table-bordered" style="margin-bottom:12px">
			<thead><tr>
				<th></th><th class="text-right">${__("Before")}</th>
				<th class="text-right">${__("After")}</th>
			</tr></thead>
			<tbody>
				<tr><td>${__("Quarters deducted")}</td>
					<td class="text-right">${t.quarters_before}</td>
					<td class="text-right"><b>${t.quarters_after}</b></td></tr>
				<tr><td>${__("Red marks")}</td>
					<td class="text-right">${t.reds_before}</td>
					<td class="text-right"><b>${t.reds_after}</b></td></tr>
				<tr><td>${__("Days held for a missing check-out")}</td>
					<td class="text-right">${t.held_before}</td>
					<td class="text-right"><b>${t.held_after}</b></td></tr>
			</tbody>
		</table>`;

	if (data.skipped_paid && data.skipped_paid.length) {
		const names = data.skipped_paid
			.map((s) => `${frappe.utils.escape_html(s.employee_name || s.employee)}`)
			.join(", ");
		html += `
			<div style="margin-bottom:12px;padding:10px 12px;border-radius:6px;
			            background:#fff8e6">
				<b>${__("{0} employee(s) will be skipped", [data.skipped_paid.length])}</b>
				<div style="margin-top:4px">${names}</div>
				<div class="text-muted" style="margin-top:4px">
					${__("Their salary slip for this period is already submitted. A "
					+ "correction after payment is a decision for next month - an "
					+ "arrear or a deduction - not a recalculation.")}
				</div>
			</div>`;
	}

	const rows = (data.moved || []).slice(0, 50).map((m) => `
		<tr>
			<td>${frappe.utils.escape_html(m.employee_name || m.employee)}</td>
			<td>${m.date}</td>
			<td class="text-right">${m.quarters_before} &rarr; <b>${m.quarters_after}</b></td>
			<td class="text-right">${m.reds_before} &rarr; <b>${m.reds_after}</b></td>
			<td class="text-right">${frappe.format(m.money, { fieldtype: "Currency" })}</td>
		</tr>`).join("");

	html += `
		<div style="font-weight:600;margin-bottom:6px">${__("The days that move")}</div>
		<div style="max-height:260px;overflow:auto">
			<table class="table table-bordered table-sm">
				<thead><tr>
					<th>${__("Employee")}</th><th>${__("Date")}</th>
					<th class="text-right">${__("Quarters")}</th>
					<th class="text-right">${__("Reds")}</th>
					<th class="text-right">${__("Pay")}</th>
				</tr></thead>
				<tbody>${rows}</tbody>
			</table>
		</div>`;

	if (data.moved_truncated) {
		html += `<div class="text-muted" style="margin-top:6px">${
			__("and {0} more, all of which will be reprocessed", [data.moved_truncated])
		}</div>`;
	}

	const d = new frappe.ui.Dialog({
		title: __("What a reprocess would change"),
		size: "large",
		fields: [{ fieldtype: "HTML", fieldname: "body", options: html }],
		primary_action_label: __("Reprocess these days"),
		primary_action: () => {
			d.hide();
			reprocess_apply(frm, data);
		},
		secondary_action_label: __("Leave it"),
		secondary_action: () => d.hide(),
	});
	d.show();
}

function reprocess_apply(frm, previewed) {
	frappe.dom.freeze(__("Reprocessing..."));
	frappe.call({
		method: "alvoraa_portal.payroll_reprocess.apply",
		args: {
			company: frm.doc.company,
			from_date: frm.doc.start_date,
			to_date: frm.doc.end_date,
			employees: JSON.stringify(selected_employees(frm)),
			confirmed: 1,
		},
		callback: (r) => {
			frappe.dom.unfreeze();
			if (!r.message || !r.message.ok) return;
			frappe.msgprint({
				title: __("Reprocessed"),
				message: __(
					"{0} day(s) were re-judged. The record of this run is "
					+ "<a href='/app/alvoraa-payroll-reprocess-log/{1}'>{1}</a>.",
					[r.message.written, r.message.log]
				),
				indicator: "green",
			});
			frm.reload_doc();
		},
		error: () => frappe.dom.unfreeze(),
	});
}
