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
 * **Slice 045, Wave 4: the SKIP map is empty, and the three that had never run
 * now do.** 045 AC-62 to AC-64.
 *
 * The comment this file used to carry said the three skipped tests were "about
 * the Growth screens, which Wave 3 rebuilds". **That was wrong twice over:**
 * Growth is Wave 4's, not Wave 3's, and the reason they were skipped was not
 * the wave but a missing fixture. What happened to each:
 *
 *   portal_tree_test.js      and portal_redesign_test.js needed a
 *   portal_redesign_test.js  `get_performance_tree` payload as argv[3]. There
 *                            is one now - `alvoraa_portal/tests/fixtures/
 *                            performance_tree.json`, captured from a real call
 *                            with every name replaced, by
 *                            `alvoraa_portal.tests.make_performance_tree_fixture`.
 *                            Both run here, with the page and the fixture.
 *   portal_appraisal_test.js drove #panel-appraisals, a panel the page has not
 *                            had for a long time. It is REPLACED by
 *                            next_growth_team_test.js, which drives the Growth
 *                            panel that exists - AC-64's first option. The
 *                            commit that did it says why.
 *
 * **Two things the newly-running tests found, which is the argument against
 * skipping in the first place.** The filter popover on the Objectives screen
 * was never portaled out of the sticky control bar, so it painted underneath
 * the sidebar - the CSS comment beside it had said for months that it could
 * not live there. And two blocks of `portal_redesign_test.js` were written
 * against controls the page had replaced, so they crashed rather than failed.
 * A skipped test is not coverage; it is a question nobody is asking.
 *
 * The lists are checked, not trusted: if a test appears, disappears or is
 * renamed, this script fails rather than quietly running less. The expected
 * count is asserted too (AC-64), so a fourth cannot go missing unnoticed.
 */
const { execFileSync } = require("child_process");
const fs = require("fs");
const path = require("path");

const DIR = path.join(__dirname, "..", "alvoraa_portal", "tests");
const PAGE = path.join(__dirname, "..", "alvoraa_portal", "alvoraa_portal",
                       "www", "hrms-employee.html");
const TREE_FIXTURE = path.join(__dirname, "..", "alvoraa_portal", "alvoraa_portal",
                               "tests", "fixtures", "performance_tree.json");

/* Each entry is the file and the arguments it needs. Two of them take the page
   and a payload; the rest find the page themselves. */
const RUN = [
  { file: "portal_dom_test.js" },
  { file: "portal_notes_test.js" },
  { file: "next_frame_test.js" },
  { file: "next_panels_test.js" },
  /* Slice 043, Wave 3: the Time and Pay panels. */
  { file: "next_time_pay_test.js" },
  /* Slice 045, Wave 4: the Growth and Team panels. Replaces
     portal_appraisal_test.js, which drove a panel the page no longer has. */
  { file: "next_growth_team_test.js" },
  /* Slice 051: the salary drawer on the EXISTING portal - both pay figures,
     the year so far, and the Why? behind a deduction. */
  { file: "portal_salary_test.js", args: [PAGE] },
  /* Slice 045, Wave 4: the two that needed a get_performance_tree payload. */
  { file: "portal_tree_test.js", args: [PAGE, TREE_FIXTURE] },
  { file: "portal_redesign_test.js", args: [PAGE, TREE_FIXTURE] },
];

/* **Empty, and it stays empty.** AC-62: an entry here needs a ticket and a
   date, not a wave. */
const SKIP = {};

/* AC-64. A number, so a test that disappears is a failure rather than a
   shorter run nobody reads. Raise it deliberately when you add one. */
const EXPECTED_BROWSER_TESTS = 9;

const onDisk = fs.readdirSync(DIR).filter((f) => f.endsWith("_test.js")).sort();
const known = [...RUN.map((r) => r.file), ...Object.keys(SKIP)].sort();
if (onDisk.join(",") !== known.join(",")) {
  console.error("The DOM test list here and the files on disk disagree.");
  console.error("  on disk: " + onDisk.join(", "));
  console.error("  listed:  " + known.join(", "));
  console.error("Add the new test to RUN, or to SKIP with the reason it cannot run.");
  process.exit(1);
}
if (known.length !== EXPECTED_BROWSER_TESTS) {
  console.error(`There are ${known.length} DOM tests and this script expects ` +
                `${EXPECTED_BROWSER_TESTS}. If that is deliberate, change ` +
                "EXPECTED_BROWSER_TESTS in the same commit and say why.");
  process.exit(1);
}
for (const entry of RUN) {
  for (const arg of entry.args || []) {
    if (!fs.existsSync(arg)) {
      console.error(`${entry.file} needs ${arg}, which does not exist. ` +
                    "Capture it with " +
                    "`bench --site <site> execute " +
                    "alvoraa_portal.tests.make_performance_tree_fixture.main`.");
      process.exit(1);
    }
  }
}

let failed = 0;
for (const entry of RUN) {
  console.log("=== " + entry.file);
  try {
    execFileSync(process.execPath,
                 [path.join(DIR, entry.file), ...(entry.args || [])],
                 { stdio: "inherit" });
  } catch (e) {
    failed++;
  }
}
for (const [name, why] of Object.entries(SKIP)) {
  console.log("=== " + name + "  NOT RUN: " + why);
}
console.log(`\nDOM tests: ${RUN.length} run, ${Object.keys(SKIP).length} not run, ${failed} failed`);
process.exit(failed ? 1 : 0);
