/* Slice 063: the Leave page where the company's pay rule set is on, walked
   against prototype v3's words (the parity table, spec 6.4).

   The server's payloads here are shaped exactly as get_leave_summary,
   preview_leave_request, apply_leave, cancel_leave and action_leave return
   them; the names and numbers are the prototype's invented ones. Each check
   names its parity row, so a merge that drops a sentence fails here. */
const { JSDOM } = require("jsdom");
const { readPortalSource } = require("../../scripts/lib/portal_source");

const html = readPortalSource(process.argv[2]);
let pass = 0, fail = 0;
const ok  = m => { pass++; console.log("  PASS  " + m); };
const bad = m => { fail++; console.log("  FAIL  " + m); };
const has = (text, want, row) => (String(text).indexOf(want) >= 0
  ? ok(row + ": " + want) : bad(row + ": missing <" + want + "> in <" + String(text).slice(0, 300) + ">"));
const hasNot = (text, want, row) => (String(text).indexOf(want) < 0
  ? ok(row + ": no " + want) : bad(row + ": should not show <" + want + ">"));

const iso = d => d.toISOString().slice(0, 10);
const shift = n => { const d = new Date(); d.setDate(d.getDate() + n); return iso(d); };
const TODAY = iso(new Date()), FUT = shift(6), PAST = shift(-2), PAST2 = shift(-9);
const day = s => new Date(s + "T00:00:00").toLocaleDateString("en-GB", {weekday: "short", day: "numeric", month: "short"});
const short = s => new Date(s + "T00:00:00").toLocaleDateString("en-GB", {day: "numeric", month: "short"});

const PRIYA_CARD = {month: "October", "class": "A", earns: true, credited: 4, used: 1.5,
  used_dates: [{date: PAST, to: PAST, half: true}, {date: PAST2, to: PAST2, half: false}],
  waiting: 1, waiting_from: FUT, approver: "Sunil Mehra", to_be_paid_out: 1.5,
  lwp_in_play: 3, lwp_limit: 5, gate: 15};
const APPS = [
  {name: "LA-1", leave_type: "Paid Leaves", from_date: FUT, to_date: FUT, status: "Open", docstatus: 0,
   total_leave_days: 1, half_day: 0, approver_label: "Sunil Mehra", can_cancel: true},
  {name: "LA-2", leave_type: "Leave Without Pay", from_date: FUT, to_date: FUT, status: "Approved", docstatus: 1,
   total_leave_days: 1, half_day: 0, approver_label: "HR", can_cancel: true, told_count: 2,
   told_top_name: "Kavita Arora", has_manager: true, first_manager: "Sunil Mehra"},
  {name: "LA-3", leave_type: "Paid Leaves", from_date: PAST, to_date: PAST, half_day_date: PAST, status: "Approved",
   docstatus: 1, total_leave_days: 0.5, half_day: 1, approver_label: "Sunil Mehra", can_cancel: false,
   told_count: 2, told_top_name: "Kavita Arora", has_manager: true, missing_punch: "check-out"},
  {name: "LA-4", leave_type: "Leave Without Pay", from_date: PAST2, to_date: PAST2, status: "Rejected",
   docstatus: 1, total_leave_days: 1, half_day: 0, approver_label: "HR", can_cancel: false},
];
const TYPES = [{leave_type: "Paid Leaves", paid_leaves: 1, left: 2.5},
               {leave_type: "Leave Without Pay", lwp: 1, lwp_in_play: 3, lwp_limit: 5}];

let SUMMARY = {balances: [], applications: APPS, employee: {name: "E1"}, ever_allocated: false,
               types_offered: TYPES, paid_leaves: PRIYA_CARD};
let PREVIEW = {};
let FAIL_NEXT = null;
const calls = [];
function reply(url, body) {
  const m = /hr_api\.(\w+)/.exec(url) || [];
  const fn = m[1] || "";
  calls.push({fn, body});
  if (fn === "get_leave_summary") return SUMMARY;
  if (fn === "preview_leave_request") return PREVIEW;
  if (fn === "apply_leave") return {name: "LA-9"};
  if (fn === "cancel_leave") return {status: "Cancelled", was: "Open", told_n: 2};
  if (fn === "get_portal_context") return {employee_id: "E1", employee_name: "Priya Sharma", dashboard: {}, cycle: null};
  if (fn === "get_checkin_status") return {no_employee: 1};
  return [];
}

const dom = new JSDOM(html, {
  runScripts: "dangerously", pretendToBeVisual: true,
  url: "http://grace.localhost/hrms-employee",
  beforeParse(w) {
    w.fetch = (url, opts) => Promise.resolve({ok: true, status: 200,
      json: () => Promise.resolve({message: reply(String(url), opts && opts.body)}),
      text: () => Promise.resolve("")});
    const call = (o) => {
      const out = reply(String(o.method || ""), JSON.stringify(o.args || {}));
      if (FAIL_NEXT && String(o.method).indexOf(FAIL_NEXT.fn) >= 0) {
        const f = FAIL_NEXT; FAIL_NEXT = null;
        setTimeout(() => { o.error && o.error(f.r); }, 0);
        return Promise.resolve({});
      }
      setTimeout(() => { o.callback && o.callback({message: out}); }, 0);
      return Promise.resolve({message: out});
    };
    w.frappe = {call, csrf_token: "x", boot: {}, ui: {}, _messages: {}, utils: {escape_html: s => s}};
  },
});
const {window} = dom, doc = window.document;
const settle = ms => new Promise(r => setTimeout(r, ms));
const txt = id => (doc.getElementById(id) || {}).textContent || "";

(async () => {
  await settle(400);
  if (typeof window.lpRenderCard !== "function") { bad("lpRenderCard is not on the page"); process.exit(1); }

  // ── the card ──────────────────────────────────────────────────────────
  window.loadLeaves();
  await settle(50);
  has(txt("lv-bal-title"), "Paid Leaves - October", "R-2");
  has(txt("att-sub"), "Your Paid Leaves this month and your leave requests", "R-1");
  const card = txt("leave-rings");
  has(card, "Class A · 4 days of Paid Leaves for October", "R-3");
  has(card, "Paid Leaves this month", "R-4");
  has(card, "given on 1 Oct", "R-4");
  has(card, short(PAST) + " (half), " + short(PAST2), "R-5");
  has(card, "Waiting for approval", "R-6");
  has(card, "set aside for now", "R-6");
  has(card, "To be paid out", "R-7");
  has(card, "with October salary", "R-7");
  has(card, "1 day is set aside for your " + short(FUT) + " request until Sunil Mehra approves or declines it. If it is declined or you cancel it, the day comes back.", "R-10");
  has(card, "Paid with your October salary. Nothing carries over.", "R-11");
  has(card, "How Paid Leaves work - class A", "R-12");
  has(card, "4 days of Paid Leaves on the 1st of every month. They count once you have attended 15 days that month; approved Paid Leaves days count toward the 15. Days you do not use are paid with that month's salary. Nothing carries over.", "R-12");
  doc.querySelector(".lp-fig.out") ? ok("R-8: only To be paid out is tinted") : bad("R-8: no tinted figure");
  doc.querySelector(".lp-fig.wait") ? ok("R-8: Waiting is dashed") : bad("R-8: no dashed figure");
  hasNot(card, "₹", "R-8 / D8");

  window.lpRenderCard(Object.assign({}, PRIYA_CARD, {attended_so_far: 10, attended_up_to: shift(-1)}));
  has(txt("leave-rings"), "These count once you have attended 15 days in October. You have attended 10 so far (up to " + short(shift(-1)) + ").", "R-9 (X-3 agreed)");
  has(txt("leave-rings"), "once you reach 15 days", "R-7 under 15");

  window.lpRenderCard({month: "October", earns: false, category: "Contract", lwp_in_play: 5, lwp_limit: 5});
  has(txt("leave-rings"), "Contract staff do not get monthly Paid Leaves.", "R-15");
  has(txt("leave-rings"), "You can still ask for Leave Without Pay, up to 5 days a month. HR approves it. You have 5 of 5 days waiting or approved in October.", "R-15");
  window.lpRenderCard({month: "October", earns: false, "class": "No Leave", lwp_in_play: 0, lwp_limit: 5});
  has(txt("leave-rings"), "Your leave class (No Leave) does not get monthly Paid Leaves.", "R-16");
  window.lpRenderCard(null);
  has(txt("leave-rings"), "Getting your Paid Leaves...", "R-13");
  window.lpRenderCard({error: 1});
  has(txt("leave-rings"), "Your Paid Leaves figures could not be shown just now. Your leave requests below are not affected, and you can still apply.", "R-14");
  has(txt("leave-rings"), "Try again", "R-14");

  // ── the list ──────────────────────────────────────────────────────────
  const list = txt("lv-apps-wrap");
  has(list, "Waiting for Sunil Mehra", "R-19");
  has(list, "Approved by HR", "R-20");
  has(list, "Declined", "R-21");
  has(list, "Paid Leaves (half day)", "R-17");
  has(list, "Your managers up to Kavita Arora have been told (2 people).", "R-22");
  has(list, "Cancel request", "R-24");
  has(list, "Cancel this leave", "R-25");
  has(list, "This day has started or passed. To change it, speak to HR.", "R-26");
  has(list, "Your check-out for the other half of " + day(PAST) + " is missing.", "R-27");
  has(list, "Until HR approves a correction, that half counts as absent. Ask for the correction on Attendance and HR will approve it.", "R-27");
  has(list, "Ask HR to correct " + short(PAST), "R-27");
  doc.querySelector(".lp-list") ? ok("R-17: the stacked list for a phone exists") : bad("R-17: no phone list");
  window.lpRenderApps([]);
  has(txt("lv-apps-wrap"), "No leave asked for yet. Use Apply Leave above.", "R-18");
  window.lpRenderApps(APPS);
  window.lpRenderApps([Object.assign({}, APPS[1], {has_manager: false, told_count: 0})]);
  has(txt("lv-apps-wrap"), "No manager is set above you, so only HR knows.", "R-23");
  window.lpRenderApps(APPS);

  // ── cancel ────────────────────────────────────────────────────────────
  window.lpAskCancel("LA-1");
  let dlg = doc.getElementById("lp-dlg");
  dlg && dlg.querySelector('[role="alertdialog"]') ? ok("R-53: an alertdialog") : bad("R-53: not an alertdialog");
  has(dlg.textContent, "Cancel this request?", "R-49");
  has(dlg.textContent, "Sunil Mehra will no longer see this request.", "R-49");
  has(dlg.textContent, "The 1 day set aside comes back to your Paid Leaves.", "R-49");
  const btns = [...dlg.querySelectorAll(".gp-modal-footer button")].map(b => b.textContent);
  btns[0] === "Keep the request" ? ok("R-53: Keep first") : bad("R-53: first button is " + btns[0]);
  window.lpDoCancel("LA-1");
  await settle(30);
  has(doc.getElementById("lp-dlg").textContent, "Request cancelled", "R-50");
  has(doc.getElementById("lp-dlg").textContent, "Sunil Mehra has been told.", "R-50");
  window.lpCloseDialog();
  window.lpAskCancel("LA-2");
  dlg = doc.getElementById("lp-dlg");
  has(dlg.textContent, "Cancel this approved leave?", "R-51");
  has(dlg.textContent, "You will be expected at work on this day.", "R-51");
  has(dlg.textContent, "You are paid for this day if you work it.", "R-51");
  window.lpCloseDialog();

  // ── the Apply pop-up ──────────────────────────────────────────────────
  window._leaveSummaryCache = SUMMARY;
  window.openLeaveModal();
  await settle(20);
  has(txt("la-title"), "Apply for leave", "R-28");
  has(txt("la-close-btn"), "Close", "R-33");
  doc.querySelector("#la-modal .gp-modal.lp-modal") ? ok("R-75: the DTC form takes the phone sizes") : bad("R-75: no lp-modal class");
  const opts = [...doc.querySelectorAll("#la-leave-type option")].map(o => o.textContent).join("|");
  has(opts, "Paid Leaves - 2.5 days left", "R-30");
  has(opts, "Leave Without Pay - 3 of 5 used", "R-30");
  has(txt("la-submit-btn"), "Choose a leave type", "R-33");
  has(txt("la-reason-help"), "Only the person who approves it and HR can read this. Managers are never sent it.", "R-32");
  (doc.getElementById("la-from-date").min || "").slice(8) === "01" ? ok("R-72: dates start at the 1st") : bad("R-72: min is " + doc.getElementById("la-from-date").min);

  window.submitLeaveApp();
  has(txt("la-error"), "Choose a leave type first.", "R-33");

  const pick = (t, f, to, half) => {
    doc.getElementById("la-leave-type").value = t;
    doc.getElementById("la-from-date").value = f;
    doc.getElementById("la-to-date").value = to;
    doc.getElementById("la-half-day").checked = !!half;
    window.laToggleHalfDay();
    window.laPreview();
  };
  const base = {dtc: 1, month: "October", prev_month: "September", month_end: "Sat 31 Oct", hr_name: "Ritika",
                chain_top: "Kavita Arora", chain_n: 2, lwp_limit: 5, past_day: false, unlimited: true};
  pick("Paid Leaves", FUT, PAST);
  await settle(20);
  has(txt("la-preview"), "The end date is before the start date. Change one of them.", "R-34");
  doc.getElementById("la-submit-btn").style.display === "none" ? ok("R-34: no send button") : bad("R-34: send shown");

  PREVIEW = Object.assign({}, base, {verdict: "ok", days: 1, approver_label: "Sunil Mehra", credited: 4, pl_left: 2.5, lwp_in_play: 3});
  pick("Paid Leaves", FUT, FUT);
  await settle(400);
  has(txt("la-preview"), "Asking for 1 day of Paid Leaves.", "R-35");
  has(txt("la-preview"), "Until Sunil Mehra decides, 1 day is set aside from your 4. The leave is paid.", "R-35");
  has(txt("la-preview"), "Sunil Mehra decides. Once it is approved, your managers up to Kavita Arora are told.", "R-40");
  has(txt("la-submit-btn"), "Send to Sunil Mehra", "R-33");

  PREVIEW = Object.assign({}, base, {verdict: "block", reason_code: "pl_short", days: 2, approver_label: "Sunil Mehra", credited: 4, pl_left: 0.5, lwp_in_play: 1});
  pick("Paid Leaves", FUT, FUT);
  await settle(400);
  has(txt("la-preview"), "2 days asked for, but you have 0.5 days of Paid Leaves left for October.", "R-36");
  has(txt("la-preview"), "Days already used or waiting for approval are taken off the 4. You can ask for Leave Without Pay instead (1 of 5 used this month).", "R-36");
  has(txt("la-preview"), "Ask for Leave Without Pay instead", "R-36");

  PREVIEW = Object.assign({}, base, {verdict: "ok", days: 1, approver_label: "HR", lwp_in_play: 3, lwp_left: 2});
  pick("Leave Without Pay", FUT, FUT);
  await settle(400);
  has(txt("la-preview"), "Asking for 1 day of Leave Without Pay.", "R-37");
  has(txt("la-preview"), "If approved, you are not paid for this day; your Paid Leaves for October are still paid out.", "R-37");
  has(txt("la-preview"), "This will be 4 of 5 days of Leave Without Pay in October.", "R-37");
  has(txt("la-preview"), "Ritika (HR) decides.", "R-40");
  has(txt("la-submit-btn"), "Send to HR", "R-33");

  PREVIEW = Object.assign({}, base, {verdict: "block", reason_code: "lwp_over", days: 2, approver_label: "HR", lwp_in_play: 4, lwp_left: 1,
    lwp_waiting: [{from: PAST, to: PAST, days: 1, label: day(PAST)}]});
  pick("Leave Without Pay", FUT, FUT);
  await settle(400);
  has(txt("la-preview"), "Only 1 day of Leave Without Pay left in October; these dates need 2 days.", "R-38");
  has(txt("la-preview"), "Up to 5 days a month, counting requests that are waiting or approved (4 of 5 so far). Shorten the dates to 1 day.", "R-38");
  has(txt("la-preview"), "A request that is still waiting counts too: " + day(PAST) + " (1 day). If it is not approved yet, you can cancel it from the list to free its days, or remind HR to approve it.", "R-38");
  doc.getElementById("la-submit-btn").style.display === "none" ? ok("R-38: no send button") : bad("R-38: send shown");

  PREVIEW = Object.assign({}, base, {verdict: "block", reason_code: "lwp_over", days: 1, approver_label: "HR", lwp_in_play: 5, lwp_left: 0, lwp_waiting: []});
  pick("Leave Without Pay", FUT, FUT);
  await settle(400);
  has(txt("la-preview"), "You have used all 5 days of Leave Without Pay for October.", "R-39");
  has(txt("la-preview"), "All of them are approved. If you need more time off, speak to Ritika (HR).", "R-39");

  PREVIEW = Object.assign({}, base, {verdict: "block", reason_code: "earlier_month", days: 1, approver_label: "HR"});
  pick("Leave Without Pay", FUT, FUT);
  await settle(400);
  has(txt("la-preview"), "Leave can only be asked for days in October.", "R-41");
  has(txt("la-preview"), "September is closed. If a September day needs changing, speak to Ritika (HR).", "R-41");

  PREVIEW = Object.assign({}, base, {verdict: "ok", days: 0.5, approver_label: "Sunil Mehra", credited: 4, pl_left: 2.5, past_day: true,
    special_day: {date: FUT, label: day(FUT), name: "Festive sale"}});
  pick("Paid Leaves", FUT, FUT, true);
  await settle(400);
  has(txt("la-preview"), "Half day: it uses half a day of Paid Leaves. You must check in and check out for the other half; it is measured against half the shift. Arriving late or leaving early does not count against you that day, and there is no green mark on a half-day leave day. If a punch is missed, ask HR to approve an attendance correction; until then the other half counts as absent and, on this special day, is charged double.", "R-43");
  has(txt("la-preview"), day(FUT) + " is a special day (Festive sale). If this leave is approved, the day is not charged double. A day taken without approved leave is unpaid and charged double.", "R-44");
  has(txt("la-preview"), "This includes a past day. Past days in October can be asked for until Sat 31 Oct.", "R-42");
  has(txt("la-lbl-from"), "Date", "R-28 half day");

  // send - the result in the pop-up
  doc.getElementById("la-half-day").checked = false;
  PREVIEW = Object.assign({}, base, {verdict: "ok", days: 1, approver_label: "HR", lwp_in_play: 3, lwp_left: 2});
  pick("Leave Without Pay", FUT, FUT);
  await settle(400);
  window.submitLeaveApp();
  await settle(40);
  const res = txt("la-result");
  has(txt("la-title"), "Sent", "R-46");
  has(res, "Sent to HR", "R-47");
  has(res, "Leave Without Pay · " + day(FUT) + " · 1 day", "R-47");
  has(res, "Ritika (HR) will approve or decline it. You will see the answer here, under Leave Applications.", "R-47");
  has(res, "Once it is approved, your managers up to Kavita Arora are told.", "R-47");
  has(res, "If approved, you are not paid for this day. 4 of 5 days of Leave Without Pay are now waiting or approved in October.", "R-47");
  has(res, "Changed your mind? It can be cancelled from the list.", "R-47");
  has(txt("la-submit-btn"), "Done", "R-47");

  // a failed send keeps the form
  window.openLeaveModal();
  await settle(20);
  pick("Leave Without Pay", FUT, FUT);
  await settle(400);
  FAIL_NEXT = {fn: "apply_leave", r: {}};
  window.submitLeaveApp();
  await settle(40);
  has(txt("la-error"), "Not sent: the connection dropped. Nothing was saved. Your choices are still here - try again.", "R-48");
  doc.getElementById("la-leave-type").value === "Leave Without Pay" ? ok("R-48: choices kept") : bad("R-48: form was cleared");

  // ── the approver's and HR's rows ──────────────────────────────────────
  const row = window.lpApprLines({employee_name: "Manoj Singh", from_date: FUT, chain_top: "Kavita Arora",
                                  lwp_in_play: 5, lwp_limit: 5, special_day: {label: day(FUT)}});
  has(row, "5 of 5 Leave Without Pay days in", "R-55");
  has(row, day(FUT) + " is a special day. Approved, it is not charged double.", "R-56");
  has(row, "Once it is approved, Manoj's managers up to Kavita Arora are told.", "R-57");
  has(window.lpDecisionWords({first: "Manoj", leave_type: "Leave Without Pay", dates: "Tue 27 Oct", told_n: 2, told_top: "Kavita Arora", employee_emailed: true}),
      "Approved · Leave Without Pay · Tue 27 Oct. Manoj's managers up to Kavita Arora have been told (2 people). Manoj has been told too.", "R-58");
  has(window.lpDecisionWords({first: "Manoj", leave_type: "Leave Without Pay", dates: "Tue 27 Oct", told_n: 2, told_top: "Kavita Arora", employee_emailed: false}),
      "Manoj has no email on record, so please tell them.", "R-58 (X-4)");
  has(window.lpDecisionWords({first: "Manoj", employee_emailed: true}),
      "Declined. Manoj has been told. Managers are not told about a declined request.", "R-59");

  console.log(`### leave 063 DOM test: ${pass} passed, ${fail} failed`);
  process.exit(fail ? 1 : 0);
})();
