/**
 * The portal's left sidebar starts pinned open (Surbhi, 22 Nov 2026).
 *
 * A folded sidebar showed only icons, so people could not find the nav words
 * or their own name, which opens My profile. Only a person who unpinned it
 * ("sb-pinned" = "0" in their browser) starts folded.
 *
 * Runs the two real functions from portal.js against a jsdom page, once per
 * stored value, so a change back to "folded unless pinned" fails here by name.
 */
const fs = require("fs");
const path = require("path");
const { JSDOM } = require("jsdom");

const src = fs.readFileSync(path.join(__dirname,
  "../alvoraa_portal/public/js/ess/portal.js"), "utf8");
const start = src.indexOf("function initSbCollapse()");
const end = src.indexOf("/* ── Boot", start);
if (start < 0 || end < 0) {
  console.log("  FAIL  initSbCollapse / toggleSbPin not found in portal.js");
  process.exit(1);
}
const code = src.slice(start, end) + "\nwindow.initSbCollapse = initSbCollapse;";

let pass = 0, fail = 0;
const ok  = m => { pass++; console.log("  PASS  " + m); };
const bad = m => { fail++; console.log("  FAIL  " + m); };

function page(stored) {
  const dom = new JSDOM('<body><button id="sb-pin-btn"></button></body>',
    { runScripts: "outside-only", url: "https://ppj.dev.alvoraa.co/" });
  const w = dom.window;
  if (stored !== null) w.localStorage.setItem("sb-pinned", stored);
  w.eval(code);
  w.initSbCollapse();
  return w;
}
const folded = w => w.document.body.classList.contains("sb-collapsed");
const title = w => w.document.getElementById("sb-pin-btn").title;

let w = page(null);
!folded(w) && title(w) === "Unpin sidebar"
  ? ok("nothing stored (first visit, or after sign-out): the sidebar starts open")
  : bad("nothing stored: the sidebar started folded");

w = page("1");
!folded(w) ? ok("pinned (\"1\"): starts open") : bad("pinned (\"1\"): started folded");

w = page("0");
folded(w) && title(w) === "Pin sidebar open"
  ? ok("unpinned (\"0\"): starts folded, and the button offers to pin it")
  : bad("unpinned (\"0\"): did not start folded");

w = page(null);
w.toggleSbPin();
folded(w) && w.localStorage.getItem("sb-pinned") === "0"
  ? ok("unpinning from the default folds it and remembers \"0\"")
  : bad("unpinning from the default did not fold it or did not store \"0\"");
w.toggleSbPin();
!folded(w) && w.localStorage.getItem("sb-pinned") === "1"
  ? ok("pinning again opens it and remembers \"1\"")
  : bad("pinning again did not open it or did not store \"1\"");

console.log(`\n### sidebar pinned by default: ${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
