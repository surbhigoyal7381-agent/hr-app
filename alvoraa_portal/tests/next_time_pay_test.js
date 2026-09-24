/* Slice 043, Wave 3: the Time and Pay panels, driven in a real DOM.
 *
 * Same method as `next_panels_test.js`: load the preview page's own source -
 * markup, stylesheets and scripts, expanded the way the server serves them -
 * put it in jsdom, answer the calls with a fixture, then look at what a PERSON
 * would see.
 *
 * What this file is for, and what it cannot do. It answers questions the
 * server's payload cannot: whether a weekly off is drawn differently from a
 * public holiday, whether a future day is a button, whether the Why? sheet
 * shows the server's sentences unchanged. It does NOT prove anything that
 * depends on a failed call being NOTICED - jsdom is kinder than a browser, and
 * its stub calls an error path `website.js` never calls. Those go through
 * `scripts/browser_check_frame.js`.
 *
 * The hostile string is a Salary Component name and a holiday description.
 * Both are free text an HR user can really set, so this is a stored-XSS shape
 * rather than a theoretical one.
 *
 * Run through scripts/run_dom_tests.js, which is what CI runs.
 */

const { JSDOM, VirtualConsole } = require("jsdom");
const { readPreviewSource } = require("../../scripts/lib/portal_source");

let pass = 0, fail = 0;
const ok = (m) => { pass++; console.log("  PASS  " + m); };
const bad = (m) => { fail++; console.log("  FAIL  " + m); };
const is = (got, want, m) =>
  (String(got) === String(want) ? ok(m) : bad(m + "  (got " + JSON.stringify(got) + ", wanted " + JSON.stringify(want) + ")"));

const NASTY = '<img src=x onerror=alert(1)>';

function fillTemplate(src) {
  return src
    .replace(/\{%\s*extends[^%]*%\}/g, "")
    .replace(/\{%\s*block [a-z_]+\s*%\}/g, "")
    .replace(/\{%\s*endblock\s*%\}/g, "")
    .replace(/\{%\s*include[^%]*%\}/g, "")
    .replace(/\{#[\s\S]*?#\}/g, "")
    .replace(/\{\{\s*tenant_name\s*\|\s*tojson\s*\}\}/g, '"Test Tenant"')
    .replace(/\{\{\s*tenant_name\[0\]\s*\|\s*upper\s*\}\}/g, "T")
    .replace(/\{\{\s*tenant_name\s*\}\}/g, "Test Tenant")
    .replace(/\{\{\s*asset_version\s*\|\s*e\s*\}\}/g, "1")
    .replace(/\{\{\s*brand_mark_url\s*\|\s*e\s*\}\}/g, "")
    .replace(/\{%\s*if brand_mark_url\s*%\}[\s\S]*?\{%\s*endif\s*%\}/g, "")
    .replace(/\{\{\s*_\("([^"]*)"\)\s*\}\}/g, "$1");
}

const SRC = fillTemplate(readPreviewSource());

function makeFrame(over) {
  return Object.assign({
    user: "rahul@example.com",
    user_full_name: "Rahul Sharma",
    has_employee: true,
    me: { employee: "HR-EMP-1", employee_name: "Rahul Sharma", designation: "Sales Executive",
          department: "Sales", image: null, company: "Test Co" },
    is_hr: false, is_manager: false, is_system_manager: false, is_control_plane: false,
    has_reports: false, scope_is_store: false, may_save_settings: false,
    review_open_count: null,
    features: { plan_payroll: 1, goals: 1, expenses: 1 },
    switch_target: null, persona_rule: 4, show_team: false,
    allowed_pages: ["home", "inbox", "time", "growth", "pay"],
    bottom_bar: ["home", "time", "pay", "growth"],
  }, over || {});
}

function makeCounts(over) {
  return Object.assign({
    total: 0, approvals_total: 0, has_employee: true, parts: [],
    corrections_hr_scope: false,
  }, over || {});
}

/* One day, in the shape `attendance_correction._day` really returns - the same
   key set, so a test cannot pass against a shape the server does not send. */
function day(date, weekday, over) {
  return Object.assign({
    date: date, weekday: weekday, future: false, holiday: null,
    weekly_off: false, leave_type: null, status: null, shift: null,
    in_time: null, out_time: null, hours: null, expected_hours: null,
    short_by: 0.0, late_entry: 0, early_exit: 0, is_late: false,
    grace_mins: 0, grace_source: null, attendance: null, punches: [],
    shift_starts: null, shift_ends: null, late_by_mins: 0,
    missing_punch: false, request: null, state: "no_record",
    before_joining: false,
  }, over || {});
}

/* August 2026, the same month the Python tests use: weekly offs on THURSDAYS
   and a named holiday on a SATURDAY. A fixture with a Saturday weekend would
   let a hard-coded weekend pass. */
function makeMonth(over) {
  const days = [
    day("2026-08-03", "Monday", { state: "present", status: "Present",
      in_time: "09:25", shift_starts: "09:30", shift_ends: "18:30",
      grace_mins: 15, grace_source: "shift", shift: "Day Shift" }),
    day("2026-08-05", "Wednesday", { state: "present", status: "Present",
      in_time: "09:42", late_by_mins: 12, is_late: false, grace_mins: 15,
      grace_source: "shift", shift: "Day Shift" }),
    day("2026-08-06", "Thursday", { weekly_off: true, holiday: "Weekly Off" }),
    day("2026-08-07", "Friday", { state: "present", status: "Present",
      in_time: "10:45", late_by_mins: 75, is_late: true, grace_mins: 15,
      grace_source: "shift", shift: "Day Shift" }),
    day("2026-08-10", "Monday", { state: "absent", status: "Absent" }),
    day("2026-08-11", "Tuesday", { state: "absent", status: "Absent" }),
    day("2026-08-15", "Saturday", { holiday: "Independence Day" }),
    day("2026-08-17", "Monday", { state: "on_leave", status: "On Leave",
      leave_type: "Casual Leave" }),
    day("2026-08-31", "Monday", { future: true, state: "future" }),
  ];
  return Object.assign({
    year: 2026, month: 8, last_day: 31, days: days,
    totals: { present: 3, absent: 2, half_day: 0, leave: 1, holiday: 2,
              no_record: 0, short_days: 0, hours_short: 0, missing_punches: 0,
              late_days: 1, hours_worked: 27, weekly_offs: 1,
              named_holidays: 1, before_joining: 0 },
    late_grace_mins: 0, tolerance_mins: 30, can_request: true,
    can_review: false, joined_on: "2024-01-01",
  }, over || {});
}

function makeTime(over) {
  return Object.assign({
    me: { employee: "HR-EMP-1", employee_name: "Rahul Sharma",
          designation: "Sales Executive", department: "Sales", image: null,
          company: "Test Co" },
    is_self: true,
    month: makeMonth(),
    shift: { shift: "Day Shift", starts: "09:30", ends: "18:30",
             source: "assignment", note: null },
    days_off: { holidays: [{ date: "2026-10-02", description: "Gandhi Jayanti" }],
                note: null, weekly_off_weekdays: ["Thursday"] },
    leave: { balances: [{ leave_type: "Casual Leave", total: 8, taken: 1,
                          pending: 0, expired: 0, left: 7 }],
             past: [{ kind: "rule", name: "L1", leave_type: "Casual Leave",
                      from_date: "2026-08-17", to_date: "2026-08-17", days: 1,
                      status: null, label: "Taken by the late-coming rule" }],
             since: "2026-01-01" },
    rule: { covered: true, note: null, rule_name: "Late Rule",
            late_threshold_minutes: 60, counts_early_exit: false,
            early_exit_threshold_minutes: 0, free_violations_per_week: 1,
            deduction_per_violation_days: 0.25, round_up_from_days: 0.75,
            round_up_to_days: 1.0, week_start_day: "Monday",
            week_end_day: "Sunday", deduct_from_leave_first: false,
            leave_types: [],
            clauses: ["Arriving more than 60 minutes after your shift starts counts as one late day.",
                      "Weeks are counted from Monday to Sunday."],
            accountable: "your HR team - no individual is named on this rule yet",
            accountable_named: false },
    record_this_year: { from_date: "2026-01-01",
      months: [{ month: "2026-10", days: 0.5,
                 weeks: [{ deduction: "D2", week_start: "2026-09-29",
                           week_end: "2026-10-05", days: 0.5, lwp_days: 0.5,
                           counted_violations: 2 }] }],
      total_days: 0.5, weeks_listed: 1, capped: false, cap: 120 },
  }, over || {});
}

function makePay(over) {
  return Object.assign({
    me: { employee: "HR-EMP-1", employee_name: "Rahul Sharma",
          designation: "Sales Executive", department: "Sales", image: null,
          company: "Test Co" },
    payslips: [{ name: "SS-2", posting_date: "2026-08-31",
                 start_date: "2026-08-01", end_date: "2026-08-31",
                 gross_pay: 37000, total_deduction: 5000.39,
                 net_pay: 31999.61, rounded_total: 32000, currency: "INR" }],
    latest: { name: "SS-2", employee_name: "Rahul Sharma",
              designation: "Sales Executive", department: "Sales",
              company: "Test Co", start_date: "2026-08-01",
              end_date: "2026-08-31", posting_date: "2026-08-31",
              currency: "INR", total_working_days: 31, payment_days: 31,
              leave_without_pay: 0, absent_days: 0, gross_pay: 37000,
              total_deduction: 5000.39, net_pay: 31999.61,
              rounded_total: 32000,
              earnings: [{ component: "Basic", amount: 30000 }],
              deductions: [{ component: "Late Coming Deduction",
                             amount: 548.39, additional_salary: "AS-1" },
                           { component: "Provident Fund", amount: 1800 }] },
    year_to_date: { net: 100000, gross: 120000, from_slip: "SS-2",
                    up_to: "2026-08-31" },
    take_home: 32000, currency: "INR", note: null,
  }, over || {});
}

function makeWhy(over) {
  return Object.assign({
    deduction: "D1", rule_name: "Late Rule", decided_on: "2026-08-24",
    week_start: "2026-08-17", week_end: "2026-08-23",
    violations: [
      { attendance_date: "2026-08-18", violation_type: "Late Arrival",
        expected_time: "09:30", actual_time: "10:47", minutes: 77,
        counted: 0 },
      { attendance_date: "2026-08-19", violation_type: "Late Arrival",
        expected_time: "09:30", actual_time: "10:35", minutes: 65,
        counted: 1 },
    ],
    total_violations: 2, counted_violations: 1, free_per_week: 1,
    per_violation_days: 0.25, computed_days: 0.75, deduction_days: 1.0,
    rounded_up: true, round_up_from: 0.75, round_up_to: 1.0,
    taken_from_leave: [{ leave_type: "Casual Leave", days: 0.5 }],
    lwp_days: 0.5, currency: "INR",
    how_it_was_decided: "This was worked out automatically by the Late Rule rule on 24-08-2026. Nobody looked at your week by hand.",
    if_a_day_is_wrong: "If a day in this week is wrong, get it corrected. That puts your attendance record right and it counts for the weeks after it.",
    what_a_correction_does_not_do: "It does not undo this deduction. Once the rule has worked a week out, it does not work it out again.",
    getting_it_put_back: "Only your HR team can cancel a deduction, and only before that month's payslip is finalised.",
    who_to_go_to: "If you think this is wrong, contact your HR team.",
    accountable_named: false,
  }, over || {});
}

function reply(status, payload) {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status: status,
    statusText: String(status),
    text: () => Promise.resolve(JSON.stringify(payload)),
  });
}

function said(sentence) {
  return JSON.stringify([JSON.stringify({ message: sentence })]);
}

function load(hash, frame, counts, answers) {
  answers = answers || {};
  const vc = new VirtualConsole();
  vc.on("jsdomError", (e) => {
    if (!/Not implemented: navigation/.test(e.message)) { console.error(e.message); }
  });
  const dom = new JSDOM(
    "<!doctype html><html><head></head><body>" + SRC + "</body></html>",
    {
      runScripts: "dangerously",
      pretendToBeVisual: true,
      virtualConsole: vc,
      url: "http://test.localhost/hrms-employee-next" + (hash || ""),
      beforeParse(w) {
        w.calls = [];
        w.frappe = { _: (s) => s, csrf_token: "token-the-page-was-built-with" };
        w.document.cookie = "user_id=rahul@example.com";
        w.alert = () => { w.__alerted = true; };
        w.__alerted = false;

        w.fetch = (url, opts) => {
          url = String(url);
          if (url.indexOf("/api/method/") !== 0) {
            return Promise.resolve({
              ok: true, status: 200, statusText: "OK",
              text: () => Promise.resolve(
                '<script>frappe.csrf_token = "a-fresh-token"</script>'),
            });
          }
          const method = url.slice("/api/method/".length);
          w.calls.push(method);
          const args = opts && opts.body ? JSON.parse(opts.body) : {};
          const custom = answers[method];
          if (custom && custom.refuse) {
            return reply(403, { exc_type: "PermissionError",
                                _server_messages: said(custom.refuse) });
          }
          if (typeof custom === "function") { return reply(200, { message: custom(args) }); }
          let message = null;
          if (method.endsWith("get_frame")) { message = frame; }
          else if (method.endsWith("get_nav_counts")) { message = counts; }
          else { message = custom === undefined ? { rows: [] } : custom; }
          return reply(200, { message: message });
        };
      },
    });
  return new Promise((resolve) => {
    /* Five turns: get_frame, get_nav_counts, the panel's own call, and room
       for the retry behind a stale token. */
    setTimeout(() => setTimeout(() => setTimeout(() => setTimeout(
      () => setTimeout(() => resolve(dom), 0), 0), 0), 0), 0);
  });
}

const el = (dom, id) => dom.window.document.getElementById(id);
const screens = (dom) => el(dom, "nf-screens");
const kind = (dom) => el(dom, "nf-state").hidden ? null : el(dom, "nf-state").getAttribute("data-kind");
const text = (dom) => screens(dom).textContent;
const sheetText = (dom) => el(dom, "nf-sheet-body").textContent;
const sheetOpen = (dom) => !el(dom, "nf-sheet-wrap").hidden;
const settle = () => new Promise((r) => setTimeout(() => setTimeout(r, 0), 0));

const TIME = "alvoraa_portal.time_api.get_time";
const PAY = "alvoraa_portal.pay_api.get_pay";
const WHY = "alvoraa_portal.pay_api.get_deduction_explanation";

async function run() {

  /* ── the panels are wired in at all ───────────────────────────────────── */

  let dom = await load("#time", makeFrame(), makeCounts(), { [TIME]: makeTime() });
  is(dom.window.NextFrame.hasPanel("time"), true, "the Time panel registered itself");
  is(dom.window.NextFrame.hasPanel("pay"), true, "the Pay panel registered itself");

  /* AC-32: both skeletons are in the HTML the SERVER sends, not built by
     JavaScript. Checked in the source, with no timing involved. */
  const sk = ["nf-skeleton-time", "nf-skeleton-pay"];
  is(sk.filter((id) => !SRC.includes('id="' + id + '"')).length, 0,
     "both skeletons are server-rendered: " + sk.join(", "));

  /* §13: Time costs ONE call beyond the frame's two. */
  let boot = dom.window.calls.filter((m) => /get_frame|get_nav_counts|get_time/.test(m));
  is(boot.length, 3, "Time costs three calls: " + boot.join(" + "));

  /* ── AC-1: six states, and a weekly off is not a public holiday ────────── */

  const clsOf = (d, date) => {
    const btn = screens(d).querySelector('.nf-cal-btn[data-day="' + date + '"]');
    return btn ? btn.parentNode.className : "";
  };

  is(/nf-cal-weeklyoff/.test(clsOf(dom, "2026-08-06")), true,
     "a weekly off is drawn as a weekly off");
  is(/nf-cal-holiday/.test(clsOf(dom, "2026-08-15")), true,
     "a named public holiday is drawn as a holiday");
  is(clsOf(dom, "2026-08-06") === clsOf(dom, "2026-08-15"), false,
     "and the two are NOT drawn the same way");

  /* AC-2: the words are "Marked absent", not "No punch and no leave". */
  is(/Marked absent/.test(text(dom)), true,
     'an auto-marked absent day reads "Marked absent"');
  is(/No punch and no leave/.test(text(dom)), false,
     'and never "No punch and no leave" (design correction D5)');

  /* AC-4: the true minutes, and the grace deciding only whether it COUNTS. */
  is(/Late by 12 min \(within grace\)/.test(text(dom)), true,
     "09:42 on a 09:30 shift reads 12 minutes, within grace");
  is(/Late by 75 min/.test(text(dom)), true, "10:45 reads 75 minutes");
  is(/Late by 25 min/.test(text(dom)), false,
     "and a 09:25 arrival is NOT 25 minutes late (the slice 017 bug)");
  is(/On time/.test(text(dom)), true, "09:25 reads On time");

  /* AC-3: a future day is not a button, so it is not in the tab order and is
     never announced as something to press. */
  is(screens(dom).querySelector('.nf-cal-btn[data-day="2026-08-31"]'), null,
     "a future day is not tappable");
  is(screens(dom).querySelectorAll('.nf-cal-btn[data-day="2026-08-10"]').length, 1,
     "and a real absent day IS, so the check above can fail");

  /* Colour is never the only signal: every cell says its state in words in
     its accessible name. A month calendar is the most tempting place in an HR
     product to say everything with colour, so this is asserted on every cell
     rather than spot-checked. */
  is(screens(dom).querySelectorAll(".nf-cal-day .nf-sr").length,
     screens(dom).querySelectorAll(".nf-cal-day").length,
     "every day cell carries its state in words");

  /* ── the shift card and days off ──────────────────────────────────────── */

  is(/09:30 – 18:30/.test(text(dom)), true, "the shift card shows the times");
  is(/Off on Thursday/.test(text(dom)), true,
     "the weekly off weekday comes from the record: Thursday, not the weekend");
  is(/Saturday|Sunday/.test(text(dom)), false,
     "and no weekend is assumed anywhere on the Days tab");

  /* ── the day sheet ────────────────────────────────────────────────────── */

  screens(dom).querySelector('.nf-cal-btn[data-day="2026-08-05"]').click();
  await settle();
  is(sheetOpen(dom), true, "tapping a day opens the day sheet");
  is(/15 minutes of grace, set on the Day Shift shift/.test(sheetText(dom)), true,
     "AC-5: the grace row names the record it came from");
  is(/Late by 12 min \(within grace\)/.test(sheetText(dom)), true,
     "and the sheet shows the true minutes");

  /* AC-9: a day already covered by an open request offers no second Fix. */
  dom = await load("#time", makeFrame(), makeCounts(), {
    [TIME]: makeTime({ month: makeMonth({
      days: [day("2026-08-10", "Monday", { state: "absent", status: "Absent",
        request: { name: "AR-1", alvoraa_reviewed_by: "Kamal" } })],
    }) }),
  });
  screens(dom).querySelector('.nf-cal-btn[data-day="2026-08-10"]').click();
  await settle();
  is(/Request sent · waiting for Kamal/.test(sheetText(dom)), true,
     "AC-9: it says where the request got to");
  is(el(dom, "nf-day-fix"), null, "and Fix is not offered a second time");

  /* AC-7: an unclaimed run of absent days is offered as ONE range. */
  dom = await load("#time", makeFrame(), makeCounts(), { [TIME]: makeTime() });
  const span = dom.window.NextTime.run(
    day("2026-08-10", "Monday", { state: "absent" }),
    makeMonth().days);
  is(span.from, "2026-08-10", "the range starts at the first absent day");
  is(span.to, "2026-08-11", "and ends at the last one in the run");

  /* ── AC-33: an empty month is the calendar plus a sentence ─────────────── */

  dom = await load("#time", makeFrame(), makeCounts(), {
    [TIME]: makeTime({ month: makeMonth({
      days: [day("2026-08-01", "Saturday"), day("2026-08-02", "Sunday")],
      totals: { present: 0, absent: 0, weekly_offs: 0, named_holidays: 0,
                no_record: 2, late_days: 0, holiday: 0 },
    }) }),
  });
  is(screens(dom).querySelectorAll(".nf-cal-day").length, 2,
     "an empty month still draws the calendar, never a blank grid");
  is(/No attendance was recorded this month/.test(text(dom)), true,
     "and the day list says so in words");
  is(kind(dom), null, "and it is not an error state");

  /* ── AC-35: no rule covers this person ─────────────────────────────────── */

  dom = await load("#time", makeFrame(), makeCounts(), {
    [TIME]: makeTime({ rule: { covered: false,
      note: "No late-coming rule applies to you.", clauses: [],
      accountable: null, accountable_named: false } }),
  });
  dom.window.NextTime.setTab("rule");
  screens(dom).querySelector('[data-tab="rule"]').click();
  await settle();
  is(/No late-coming rule applies to you/.test(text(dom)), true,
     "AC-35: the tab is still there and says so");
  is(/\b0\b/.test(screens(dom).querySelector(".nf-counts") ? "0" : ""), false,
     "and it does not show zeros as if the rule were satisfied");

  /* ── the rule tab shows the SERVER's sentences ─────────────────────────── */

  dom = await load("#time", makeFrame(), makeCounts(), { [TIME]: makeTime() });
  screens(dom).querySelector('[data-tab="rule"]').click();
  await settle();
  is(/Arriving more than 60 minutes after your shift starts/.test(text(dom)), true,
     "the rule's clauses are drawn as the server wrote them");
  is(/Weeks are counted from Monday to Sunday/.test(text(dom)), true,
     "including the week's start day, which came from the record");

  /* ── AC-37: a refusal is a sentence, not an error page ─────────────────── */

  dom = await load("#time", makeFrame(), makeCounts(), {
    [TIME]: { refuse: "You can only open the attendance of people who report to you." },
  });
  is(/You can only open the attendance of people who report to you/.test(text(dom)), true,
     "AC-37: a month outside your line is a plain sentence");
  is(kind(dom), null, "and not the page-error state");

  /* ── Pay ──────────────────────────────────────────────────────────────── */

  dom = await load("#pay", makeFrame(), makeCounts(), { [PAY]: makePay() });
  boot = dom.window.calls.filter((m) => /get_pay$/.test(m));
  is(boot.length, 1, "Pay costs one call of its own");

  /* §20 D-2 and the rounding that is NOT being fixed: the hero is the rounded
     figure the bank paid, and the exact net is beside it, not instead of it. */
  is(/32,000/.test(text(dom)), true, "take-home is the rounded total");
  is(/31,999\.61/.test(text(dom)), true,
     "and the exact amount on the payslip is shown too");

  /* AC-25: the year figure is the stored one, not the sum of the slips. */
  is(/100,000/.test(text(dom)), true, "the year so far is the stored figure");
  is(/Read from payslip SS-2/.test(text(dom)), true,
     "and it names the slip it was read off");

  /* §20 D-4: no comparison with last month, anywhere. */
  is(/more than|compared/i.test(text(dom)), false,
     "no comparison line: a one-off incentive must not read as a raise");

  /* The Why? control is on the line that CARRIES the link and on no other. */
  is(screens(dom).querySelectorAll("[data-why]").length, 1,
     "one Why? control, on the deduction that has something behind it");
  is(screens(dom).querySelector('[data-why="AS-1"]') !== null, true,
     "and it carries that line's own link");

  /* ── AC-39: no payslips yet ────────────────────────────────────────────── */

  dom = await load("#pay", makeFrame(), makeCounts(), {
    [PAY]: makePay({ payslips: [], latest: null, year_to_date: null,
                     take_home: null,
                     note: "No payslips have been issued to you yet." }),
  });
  is(/No payslips have been issued to you yet/.test(text(dom)), true,
     "AC-39: the sentence");
  is(kind(dom), null, "and no error state");

  /* ── a tenant without payroll ──────────────────────────────────────────── */

  dom = await load("#pay", makeFrame(), makeCounts(), {
    [PAY]: { refuse: "That payslip is not available." },
  });
  is(/That payslip is not available/.test(text(dom)), true,
     "a tenant without payroll gets the one refusal sentence");

  /* ── the Why? sheet ───────────────────────────────────────────────────── */

  dom = await load("#pay", makeFrame(), makeCounts(),
                   { [PAY]: makePay(), [WHY]: makeWhy() });
  screens(dom).querySelector('[data-why="AS-1"]').click();
  await settle();
  is(sheetOpen(dom), true, "the Why? sheet opens");

  /* AC-57: it says the decision was automatic, when, and under which rule -
     in the server's own words, unchanged. */
  is(/worked out automatically by the Late Rule rule on 24-08-2026/.test(sheetText(dom)), true,
     "it says it was automatic, when, and which rule");
  is(/Nobody looked at your week by hand/.test(sheetText(dom)), true,
     "and that nobody looked at the week");

  /* AC-58: the remedy on the screen is the remedy that EXISTS. */
  is(/It does not undo this deduction/.test(sheetText(dom)), true,
     "AC-58: correcting a day does not undo the deduction, and it says so");
  is(/the rule follows the attendance record/.test(sheetText(dom)), false,
     "and the false sentence from revision 1 of the spec is nowhere");

  /* AC-60: a route to somebody, never a blank. */
  is(/If you think this is wrong, contact/.test(sheetText(dom)), true,
     "it says who to go to");

  /* The inputs, with the free one marked from the server's flag. */
  is(/10:47/.test(sheetText(dom)), true, "the violations carry their real times");
  is(/0\.75 days, rounded up to 1/.test(sheetText(dom)), true,
     "and the rounding is shown");

  /* AC-61: showing it creates no record. Closing the sheet calls NOTHING. */
  const before = dom.window.calls.length;
  dom.window.NextFrame.closeSheet();
  await settle();
  is(dom.window.calls.length, before,
     "AC-61: closing the Why? sheet sends nothing to the server");

  /* AC-29: a hand-entered deduction says so and shows NO week. */
  dom = await load("#pay", makeFrame(), makeCounts(),
                   { [PAY]: makePay(), [WHY]: { hand_entered: true } });
  screens(dom).querySelector('[data-why="AS-1"]').click();
  await settle();
  is(/This was entered by hand, so there are no days behind it/.test(sheetText(dom)), true,
     "AC-29: the sentence");
  is(/The week this covers/.test(sheetText(dom)), false,
     "and no empty week is drawn");

  /* ── escaping: a hostile string is TEXT, in two places ─────────────────── */

  dom = await load("#pay", makeFrame(), makeCounts(), {
    [PAY]: makePay({ latest: Object.assign(makePay().latest, {
      earnings: [{ component: NASTY, amount: 1 }] }) }),
  });
  is(screens(dom).querySelectorAll("img").length, 0,
     "a hostile Salary Component name creates no element on Pay");
  is(dom.window.__alerted, false, "and nothing on Pay executed");

  dom = await load("#time", makeFrame(), makeCounts(), {
    [TIME]: makeTime({ days_off: { holidays: [{ date: "2026-10-02",
      description: NASTY }], note: null, weekly_off_weekdays: ["Thursday"] } }),
  });
  is(screens(dom).querySelectorAll("img").length, 0,
     "a hostile holiday description creates no element on Time");
  is(dom.window.__alerted, false, "and nothing on Time executed");

  console.log("\n" + pass + " passed, " + fail + " failed");
  process.exit(fail ? 1 : 0);
}

run().catch((e) => { console.error(e); process.exit(1); });
