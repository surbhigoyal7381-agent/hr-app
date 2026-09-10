/* Does the attendance strip draw the day it is given?

   Each row on "My Attendance" carries a strip: the shift as the track, the
   time actually worked laid over it. That is the part of the screen somebody
   reads before they decide a day is wrong, so it has to be right - and it is
   the easiest thing on the page to get subtly wrong, because clamping hides a
   bad scale perfectly. A night shift drew inside its bounds while its track
   had collapsed from eight hours to one.

   These functions are pure string building, so no browser and no server is
   needed. Run it against the portal page:

       node scripts/check_attendance_strip.js             alvoraa_portal/alvoraa_portal/www/hrms-employee.html
*/
const fs = require("fs");
const target = process.argv[2];

// Line endings are normalised first: the page is stored with CRLF, and the
// blank-line boundary the extractor below relies on is a bare newline.
const raw = fs.readFileSync(target, "utf8").split("\r\n").join("\n");

const blocks = [...raw.matchAll(/<script(?![^>]*src=)[^>]*>([\s\S]*?)<\/script>/g)]
  .map((m) => m[1]).join("\n;\n")
  .replace(/\{\{[\s\S]*?\}\}/g, "null")
  .replace(/\{%[\s\S]*?%\}/g, "");

// Only the attendance-record functions are pulled out. Loading the whole page
// would drag in every unrelated global it touches.
const want = ["AC_MONTHS", "acState", "acMinutes", "acMins", "acSay", "acPairs",
              "acStrip", "acReqCard", "acForm", "acRow", "acDetail"];
/* Extracted by counting braces, not by looking for the next blank line.
   Several of these functions have a blank line inside them, and the blank-line
   version cut them in half - which showed up as a syntax error rather than as
   a missing function, so it took a moment to see. */
const OPEN = {"{": "}", "[": "]", "(": ")"};
const CLOSE = {"}": 1, "]": 1, ")": 1};

function grab(name) {
  const start = blocks.search(new RegExp("^(?:var |function )" + name + "\\b", "m"));
  if (start < 0) { console.error("MISSING: " + name); process.exit(1); }
  const isVar = blocks.slice(start, start + 4) === "var ";

  // A `var` runs to its terminating semicolon; a function runs to the closing
  // brace of its body. Doing both by counting braces alone got AC_MONTHS wrong
  // - it is an array, so the counter never saw a brace at all.
  let depth = 0, body = false;
  for (let i = start; i < blocks.length; i++) {
    const c = blocks[i];
    if (OPEN[c]) { depth++; if (c === "{") body = true; }
    else if (CLOSE[c]) {
      depth--;
      if (!isVar && body && depth === 0) return blocks.slice(start, i + 1);
    } else if (isVar && c === ";" && depth === 0) {
      return blocks.slice(start, i + 1);
    }
  }
  console.error("UNTERMINATED: " + name);
  process.exit(1);
}

let src = "";
for (const name of want) src += grab(name) + "\n";

const gpEsc = (s) => String(s === null || s === undefined ? "" : s)
  .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

const F = new Function(
  "gpEsc",
  src + "\nreturn {acRow, acStrip, acPairs, acDetail, acMins, acState};")(gpEsc);

F.acState.data = {is_self: true, can_request: true, employee_name: "Asha Rao",
                  tolerance_mins: 30};
F.acState.reasons = [{value: "Forgot to Punch Out",
                      help: "You clocked in but did not clock out.",
                      becomes: "Present"}];

const base = {
  date: "2026-08-12", weekday: "Wednesday", future: false, holiday: null,
  leave_type: null, status: "Present", shift: "General", in_time: "09:32",
  out_time: "18:04", hours: 8.53, expected_hours: 9, short_by: 0,
  late_entry: 1, early_exit: 0, attendance: "HR-ATT-1", punches: [],
  shift_starts: "09:00", shift_ends: "18:00", late_by_mins: 32,
  missing_punch: false, request: null, state: "present",
};

const cases = {
  "an ordinary day, two punches": {
    ...base,
    punches: [{log_type: "IN", at: "09:32", where: "Gate 1"},
              {log_type: "OUT", at: "18:04", where: "Gate 1"}],
  },
  "a lunch break, four punches": {
    ...base, hours: 7.5,
    punches: [{log_type: "IN", at: "09:00"}, {log_type: "OUT", at: "13:04"},
              {log_type: "IN", at: "13:50"}, {log_type: "OUT", at: "17:20"}],
  },
  "the missing punch out": {
    ...base, hours: 4.1, out_time: null, missing_punch: true, short_by: 4.4,
    punches: [{log_type: "IN", at: "09:00"}],
  },
  "no punch rows at all": {...base, punches: []},
  "arrived before the shift started": {
    ...base, in_time: "08:31", late_by_mins: 0,
    punches: [{log_type: "IN", at: "08:31"}, {log_type: "OUT", at: "18:04"}],
  },
  "stayed well past the shift": {
    ...base, out_time: "21:40", hours: 12.1,
    punches: [{log_type: "IN", at: "09:32"}, {log_type: "OUT", at: "21:40"}],
  },
  "no record, a weekend": {
    ...base, status: null, in_time: null, out_time: null, hours: null,
    expected_hours: null, attendance: null, state: "no_record",
    shift_starts: null, shift_ends: null, late_by_mins: 0, weekday: "Saturday",
  },
  "still to come": {
    ...base, future: true, state: "future", attendance: null,
    in_time: null, out_time: null, hours: null,
  },
  "a holiday": {
    ...base, holiday: "Independence Day", state: "holiday", attendance: null,
    in_time: null, out_time: null, hours: null,
  },
  "a night shift crossing midnight": {
    ...base, shift_starts: "22:00", shift_ends: "06:00", in_time: "22:05",
    out_time: "06:02", hours: 7.9,
    punches: [{log_type: "IN", at: "22:05"}, {log_type: "OUT", at: "06:02"}],
  },
  "a request already raised": {
    ...base,
    request: {state: "waiting", says: "Waiting for HR", name: "R1",
              reason: "Forgot to Punch Out", from_date: "2026-08-12",
              to_date: "2026-08-12", note: null,
              explanation: "Left via the back gate."},
  },
  "a leave type with markup in it": {...base, leave_type: "<script>x</script>"},
};

/* What each case must actually look like, not just that it stays in bounds.
   The night shift passed the bounds check while being drawn as a one-hour
   track, because clamping hides a wrong scale perfectly. */
const expect = {
  "an ordinary day, two punches": {blocks: 1, startsNear: 5.9, endsNear: 100},
  "a lunch break, four punches": {blocks: 2},
  "the missing punch out": {blocks: 1, gap: true},
  "arrived before the shift started": {blocks: 1, startsNear: 0},
  "stayed well past the shift": {blocks: 1, endsNear: 100},
  // 22:05 to 06:02 across an eight-hour night shift: starts ~1% in, runs
  // almost the whole track. Drawn on a collapsed track it started at 0 and
  // filled everything, which is what the scale bug looked like.
  "a night shift crossing midnight": {blocks: 1, startsNear: 1, endsNear: 100},
};

let bad = 0;
for (const [label, day] of Object.entries(cases)) {
  const html = F.acRow(day) + (day.attendance ? F.acDetail(day) : "");
  const problems = [];

  const want = expect[label];
  if (want) {
    const found = [...html.matchAll(/left:([-\d.]+)%;width:([-\d.]+)%/g)]
      .map((m) => [parseFloat(m[1]), parseFloat(m[2])]);
    if (want.blocks !== undefined && found.length !== want.blocks) {
      problems.push(`expected ${want.blocks} block(s), drew ${found.length}`);
    }
    if (found.length) {
      const [l, w] = found[0];
      if (want.startsNear !== undefined && Math.abs(l - want.startsNear) > 3) {
        problems.push(`first block starts at ${l}%, expected about ${want.startsNear}%`);
      }
      if (want.endsNear !== undefined && Math.abs(l + w - want.endsNear) > 3) {
        problems.push(`first block ends at ${(l + w).toFixed(1)}%, expected about ${want.endsNear}%`);
      }
    }
    if (want.gap && !/<i class="gap"/.test(html)) {
      problems.push("an unfinished block should be marked, and is not");
    }
  }

  if (/undefined|NaN|\[object/.test(html)) problems.push("a placeholder leaked into the markup");
  if (/<script>/.test(html)) problems.push("unescaped markup reached the page");

  // Every block in the strip has to sit inside its own track.
  for (const m of html.matchAll(/left:([-\d.]+)%;width:([-\d.]+)%/g)) {
    const l = parseFloat(m[1]), w = parseFloat(m[2]);
    if (!(l >= 0 && l <= 100)) problems.push(`a block starts at ${l}%`);
    if (!(w >= 0 && l + w <= 101)) problems.push(`a block ends at ${(l + w).toFixed(1)}%`);
  }

  const open = (html.match(/<t[dr]\b/g) || []).length;
  const close = (html.match(/<\/t[dr]>/g) || []).length;
  if (open !== close) problems.push(`${open} cells opened, ${close} closed`);

  const strip = (html.match(/class="ac-strip[^"]*"/) || ['class="(none)"'])[0];
  const n = (html.match(/<i class=/g) || []).length;
  console.log(`${problems.length ? "FAIL" : "ok  "}  ${label.padEnd(34)} ${strip.padEnd(26)} ${n} block(s)`);
  problems.forEach((p) => { bad++; console.log("        " + p); });
}
console.log(bad ? `\n${bad} problem(s)` : "\nevery case draws cleanly");
process.exit(bad ? 1 : 0);
