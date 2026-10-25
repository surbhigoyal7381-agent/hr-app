/* Does the "Your day" card appear only once the day has started?

   It is for somebody who has checked in, by the device or on this page. Before
   that there is nothing to measure, so the card must draw nothing at all and
   leave the one-line banner to say when "on time" ends. Run it against the
   portal script:

       node scripts/check_day_widget.js   alvoraa_portal/alvoraa_portal/public/js/ess/portal.js
*/
const blocks = require("fs").readFileSync(process.argv[2], "utf8").split("\r\n").join("\n");

const OPEN = {"{": "}", "[": "]", "(": ")"}, CLOSE = {"}": 1, "]": 1, ")": 1};
function grab(name) {
  const start = blocks.search(new RegExp("^(?:var |function )" + name + "\\b", "m"));
  if (start < 0) { console.error("MISSING: " + name); process.exit(1); }
  const isVar = blocks.slice(start, start + 4) === "var ";
  let depth = 0, body = false;
  for (let i = start; i < blocks.length; i++) {
    const c = blocks[i];
    if (OPEN[c]) { depth++; if (c === "{") body = true; }
    else if (CLOSE[c]) { depth--; if (!isVar && body && depth === 0) return blocks.slice(start, i + 1); }
    else if (isVar && c === ";" && depth === 0) return blocks.slice(start, i + 1);
  }
  console.error("UNTERMINATED: " + name); process.exit(1);
}
const want = ["dmDrift", "dmMinsOfDay", "dmParse", "dmNow", "dmUnwrap", "dmClock",
              "dmSpan", "dmCost", "dmWhere", "dmLadderOpen", "dmWidget", "dmFact",
              "dmLadder", "dmMarks", "esc"];
let src = ""; for (const n of want) src += grab(n) + "\n";
const { dmWidget } = new Function(src + "\nreturn {dmWidget};")();

const day = {
  shift: {name: "Day", start: "09:00", end: "18:00"},
  arrived: null, on_time_until: "09:15", half_day_before: "13:30",
  red: {late: false}, green: null,
  ladder: {anchor: "09:00", steps: [
    {cost: 4, from: "09:00", label: "The whole day off"}], extra_quarter: 0},
  now: "08:40",
};
let failed = 0;
function check(name, ok) { console.log((ok ? "ok   " : "FAIL ") + name); if (!ok) failed++; }

check("nothing is drawn before the first check-in", dmWidget(day) === "");
check("nothing is drawn with no marks at all", dmWidget(null) === "");
check("the card is drawn once there is an arrival time",
      dmWidget({...day, arrived: "09:05", now: "10:30"}).indexOf("Your day") >= 0);
process.exit(failed ? 1 : 0);
