#!/usr/bin/env node
/**
 * Run the portal's jsdom tests, and say plainly which ones did not run.
 *
 * Slice 034 / ALV-111. Five tests under alvoraa_portal/tests/ load the real
 * rendered page in jsdom and click it. None of them had ever run: jsdom was not
 * installed anywhere, so every one of them stopped at
 * "Cannot find module 'jsdom'" and nobody saw it. jsdom is now a pinned
 * devDependency in the repository's package.json and these run in CI.
 *
 * Slice 034 Wave 1 adds a fourth that runs, next_frame_test.js: the new frame,
 * loaded from the preview page's own source and clicked. Three of the original
 * five still do not run.
 *
 * Two of the five run. Three do not, and the reasons are recorded here rather
 * than in a comment nobody reads:
 *
 *   portal_tree_test.js      needs a get_performance_tree payload as argv[3].
 *   portal_redesign_test.js  the same payload. No such fixture is in the
 *                            repository, so the file cannot be produced by
 *                            reading the repo alone.
 *   portal_appraisal_test.js drives #panel-appraisals. The page has 19 panels
 *                            and that is not one of them, so the test is
 *                            written against a layout the page no longer has.
 *
 * All three are about the Growth screens, which Wave 3 rebuilds. Repairing them
 * belongs with that work, not with the frame.
 *
 * The skip list is checked, not trusted: if a sixth test appears, or one of
 * these is renamed, this script fails rather than quietly running less.
 */
const { execFileSync } = require("child_process");
const fs = require("fs");
const path = require("path");

const DIR = path.join(__dirname, "..", "alvoraa_portal", "tests");

const RUN = ["portal_dom_test.js", "portal_notes_test.js", "next_frame_test.js",
             "next_panels_test.js"];
const SKIP = {
  "portal_tree_test.js": "needs a get_performance_tree fixture that is not in the repository (ALV-111, Wave 3)",
  "portal_redesign_test.js": "needs a get_performance_tree fixture that is not in the repository (ALV-111, Wave 3)",
  "portal_appraisal_test.js": "drives #panel-appraisals, which the page does not have (ALV-111, Wave 3)",
};

const onDisk = fs.readdirSync(DIR).filter((f) => f.endsWith("_test.js")).sort();
const known = [...RUN, ...Object.keys(SKIP)].sort();
if (onDisk.join(",") !== known.join(",")) {
  console.error("The DOM test list here and the files on disk disagree.");
  console.error("  on disk: " + onDisk.join(", "));
  console.error("  listed:  " + known.join(", "));
  console.error("Add the new test to RUN, or to SKIP with the reason it cannot run.");
  process.exit(1);
}

let failed = 0;
for (const name of RUN) {
  console.log("=== " + name);
  try {
    execFileSync(process.execPath, [path.join(DIR, name)], { stdio: "inherit" });
  } catch (e) {
    failed++;
  }
}
for (const [name, why] of Object.entries(SKIP)) {
  console.log("=== " + name + "  NOT RUN: " + why);
}
console.log(`\nDOM tests: ${RUN.length} run, ${Object.keys(SKIP).length} not run, ${failed} failed`);
process.exit(failed ? 1 : 0);
