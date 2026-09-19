/*
 * Pin the rating-band maths on the calibration and distribution tabs.
 *
 * On 2026-09-19 the 9-box grid was found to be wrong for 204 of 403 people in
 * the PP Jewellers Q1 FY27 cycle, all in the same direction: anything that was
 * not a whole number - a 4.5, a 3.5 - was matched against the rating scale by
 * exact value, missed, and dropped into the lowest band. The whole Moderate
 * column was empty for all 403 people, and the same assumption silently
 * removed those people from both bell curves and from every figure above them.
 * The grid HR uses for promotion, succession and pay banding was wrong for
 * half the company.
 *
 * The assertions below are the user's own arithmetic from that cycle. If any
 * of them fails, that bug is back.
 *
 * Usage:   node scripts/check_rating_bands.js [path/to/hrms-employee.html]
 *
 * To prove the pin works, run it against the version before the fix:
 *   git show <rev>:alvoraa_portal/alvoraa_portal/www/hrms-employee.html > /tmp/before.html
 *   node scripts/check_rating_bands.js /tmp/before.html     # must fail
 */
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const FILE = process.argv[2] || path.join(
  __dirname, "..", "alvoraa_portal", "alvoraa_portal", "www", "hrms-employee.html");

const SOURCE = fs.readFileSync(FILE, "utf8");

// The helpers are published as `window.pfX = function...` at page scope. Pull
// each one out by name rather than running the whole page, which would need a
// browser.
const WANTED = ["pfScaleValues", "pfRatingBand", "pfRatingToBandValue",
                "pfHasRating", "pfRatingStats", "pfRatingLabel"];

function extract(name) {
  const start = SOURCE.indexOf("window." + name + " = function");
  if (start < 0) return null;
  // Walk braces from the first "{" to find the end of the function body.
  let i = SOURCE.indexOf("{", start), depth = 0, end = -1;
  for (; i < SOURCE.length; i++) {
    const c = SOURCE[i];
    if (c === "{") depth++;
    else if (c === "}") { depth--; if (depth === 0) { end = i + 1; break; } }
  }
  if (end < 0) return null;
  return SOURCE.slice(start, end) + ";";
}

const sandbox = {window: {}};
vm.createContext(sandbox);
const missing = [];
for (const name of WANTED) {
  const src = extract(name);
  if (!src) { missing.push(name); continue; }
  vm.runInContext(src, sandbox);
}
if (missing.length) {
  console.error("FAIL: the page does not define " + missing.join(", ") + ".");
  console.error("      Every screen that places a rating must go through these,");
  console.error("      or half-point ratings fall to the lowest band again.");
  process.exit(1);
}
const W = sandbox.window;

// ── The failures, and the numbers ──────────────────────────────────────────
let failures = 0;
function check(label, got, want) {
  const ok = JSON.stringify(got) === JSON.stringify(want);
  if (!ok) { failures++; console.error(`FAIL  ${label}\n      expected ${JSON.stringify(want)}, got ${JSON.stringify(got)}`); }
  else console.log(`ok    ${label}`);
}

// The PPJ 5-Point scale.
const SCALE = {scale_name: "PPJ 5-Point", items: [
  {label: "Unsatisfactory",       value: 1},
  {label: "Needs Improvement",    value: 2},
  {label: "Meets Expectations",   value: 3},
  {label: "Exceeds Expectations", value: 4},
  {label: "Outstanding",          value: 5},
]};
const VALS = W.pfScaleValues(SCALE);
check("the scale reads as 1..5 ascending", VALS, [1, 2, 3, 4, 5]);

// ── 1. The 9-box places by where a rating sits on the scale ────────────────
// 0 = Low, 1 = Moderate, 2 = High.
const BAND = ["Low", "Moderate", "High"];
function band(v) { const b = W.pfRatingBand(v, VALS); return b === null ? "none" : BAND[b]; }

check("a 4.5 is High, not Low  (Dinesh Gill, Arjun Bhatia, Ajay Malhotra)", band(4.5), "High");
check("a 3.5 is Moderate, not Low  (Ankit Sethi)",                          band(3.5), "Moderate");
check("a 4 is still High",                                                  band(4),   "High");
check("a 5 is still High",                                                  band(5),   "High");
check("a 3 is still Moderate",                                              band(3),   "Moderate");
check("a 1.5 is still Low",                                                 band(1.5), "Low");
check("a 1 is still Low",                                                   band(1),   "Low");
check("nothing to place returns null, so nobody is boxed by a blank",
      W.pfRatingBand(null, VALS), null);

// ── 2. The Moderate column is not empty ────────────────────────────────────
// Her Q1 FY27 counts: overall 3.5 x 17, 4 x 162, 4.5 x 187, 5 x 37 = 403.
const OVERALL = [].concat(
  Array(17).fill(3.5), Array(162).fill(4), Array(187).fill(4.5), Array(37).fill(5));
check("403 overall ratings in the fixture", OVERALL.length, 403);

const cols = {Low: 0, Moderate: 0, High: 0};
OVERALL.forEach(v => cols[band(v)]++);
check("the Moderate column is not empty  (it held 0 of 403)", cols.Moderate > 0, true);
check("the columns are 0 low / 17 moderate / 386 high", cols, {Low: 0, Moderate: 17, High: 386});
check("every one of the 403 is placed somewhere",
      cols.Low + cols.Moderate + cols.High, 403);

// Potential: 1.5 x 59, 3 x 216, 4 x 87, 4.5 x 40, and one person never rated.
const POTENTIAL = [].concat(
  Array(59).fill(1.5), Array(216).fill(3), Array(87).fill(4), Array(40).fill(4.5));
check("402 potential ratings plus one unrated", POTENTIAL.length + 1, 403);
check("a 4.5 potential is High, not Low", band(4.5), "High");

// ── 3. An unrated person is not a person rated zero ────────────────────────
check("a stored 0 is not a rating",            W.pfHasRating(0, VALS),    false);
check("a real 4.5 is a rating",                W.pfHasRating(4.5, VALS),  true);
check("null is not a rating",                  W.pfHasRating(null, VALS), false);
check("an unrated person gets no band",        W.pfRatingBand(0, VALS) === null || !W.pfHasRating(0, VALS), true);
// If a scale ever carries a real 0, that 0 must count as an answer.
const ZERO_SCALE = {items: [{label: "None", value: 0}, {label: "Some", value: 1}]};
check("a scale that has a 0 keeps 0 as a real answer",
      W.pfHasRating(0, W.pfScaleValues(ZERO_SCALE)), true);

// ── 4. The statistics come from the raw ratings ────────────────────────────
// The bug made these read 4.2 and 3.3 - the mean of the whole numbers alone
// (833/199 = 4.186 and 996/303 = 3.287). The truth is 4.303 and 3.146.
const oStats = W.pfRatingStats(OVERALL, VALS);
check("all 403 overall ratings count towards the figures  (it used 199)", oStats.total, 403);
check("the average overall is 4.303, not 4.186",  Number(oStats.avg.toFixed(3)), 4.303);
check("the average overall is NOT the whole-number-only 4.186",
      Number(oStats.avg.toFixed(3)) !== 4.186, true);
check("the median overall is 4.5, not 4",         oStats.median, 4.5);

const pStats = W.pfRatingStats(POTENTIAL, VALS);
check("all 402 rated potentials count  (it used 303)", pStats.total, 402);
check("the average potential is 3.146, not 3.287", Number(pStats.avg.toFixed(3)), 3.146);

// ── 5. Which bar a rating is drawn on ──────────────────────────────────────
// A half-point rounds UP: where a rating is genuinely ambiguous the benefit
// goes to the employee rather than against them.
const toBar = v => W.pfRatingToBandValue(v, VALS);
check("4.5 is drawn on 5 - a half-point rounds up", toBar(4.5), 5);
check("3.5 is drawn on 4 - a half-point rounds up", toBar(3.5), 4);
check("4.2 is drawn on 4 - nearest band",           toBar(4.2), 4);
check("4 is drawn on 4",                            toBar(4),   4);
// Nobody may be dropped from a chart again.
const bars = {};
OVERALL.forEach(v => { const b = toBar(v); bars[b] = (bars[b] || 0) + 1; });
const plotted = Object.values(bars).reduce((a, b) => a + b, 0);
check("all 403 are drawn on a bar  (the curve plotted 199)", plotted, 403);

// ── 6. A rating always reads as something ──────────────────────────────────
check("a 4 reads as its band name",    W.pfRatingLabel(4, SCALE),   "Exceeds Expectations");
check("a 4.5 reads as 4.5, not blank", W.pfRatingLabel(4.5, SCALE), "4.5");

// ───────────────────────────────────────────────────────────────────────────
if (failures) {
  console.error(`\n${failures} check(s) failed in ${FILE}`);
  process.exit(1);
}
console.log(`\nrating bands: all checks passed (${FILE})`);
