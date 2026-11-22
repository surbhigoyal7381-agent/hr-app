// Slice 087 AC-2: the client's kind rule (acKind in portal.js) against the same six rows the
// server test uses (test_punch_fix_087.Kind). Run: node scripts/087_kind_table_check.js
const fs = require("fs");
const src = fs.readFileSync(__dirname + "/../alvoraa_portal/alvoraa_portal/public/js/ess/portal.js", "utf8");
const body = src.slice(src.indexOf("window.acKind = function"), src.indexOf("\n};\n", src.indexOf("window.acKind = function")) + 4);
const window = {}; eval(body);
const m = (h) => h.split(":").reduce((a, b) => a * 60 + +b);
const rows = [
  [["10:30", "14:00", "19:30"], "14:40", "IN", "Back in after a break"],
  [["11:15", "19:30"], "10:30", "IN", "Arrival"],
  [["19:30"], "10:30", "IN", "Arrival"],            // 11:15 set aside leaves only 19:30
  [["10:30"], "19:30", "OUT", "Leaving"],
  [["10:30", "14:00", "19:30"], "12:00", "OUT", "Out for a break"],
  [["19:30"], "10:00", "IN", "Arrival"],
];
let bad = 0;
for (const [p, t, log, label] of rows) {
  const k = window.acKind(p.map(m), m(t));
  if (k.log !== log || k.label !== label) { bad++; console.log("FAIL", p, t, k); }
}
console.log(bad ? bad + " failed" : "kind table: " + rows.length + " of " + rows.length + " ok");
process.exit(bad ? 1 : 0);
