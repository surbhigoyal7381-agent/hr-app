---
slice: 079-pre-onboarding
artifact: 03-implementation-notes-dialog-overhaul
author: hrms-fullstack-engineer
date: 2026-11-04
tickets: [ALV-310, ALV-305, ALV-304]
status: built locally, not pushed, not deployed
branch: slice/083-dialog-overhaul (worktree .claude/worktrees/083-dialog-overhaul)
---

# What was built

Three approved tickets as one change, because all three alter the same screen.
Nothing is pushed and nothing is deployed.

## File by file

| File | What changed | Mechanism, and why |
|---|---|---|
| `alvoraa_portal/alvoraa_portal/public/js/ess/portal.js` | The whole `ocs` block: `ocsWord` (ALV-305), a new `ocsWords(kind)` holding each list's words once, `ocsRow`/`ocsRows` rebuilt as table rows, `ocsDialog` wrapping them in a table with sticky headings and a new footer, `ocsSummary`'s button and amber line, `ocsPreview` per list, the change handler that no longer redraws, and a new `ocsTold`/`ocsToldSave` dialog for ALV-304 | **New code** in the existing file and its existing name prefix. No cheaper rung reaches a bespoke page's layout |
| `alvoraa_portal/alvoraa_portal/public/css/ess/panels.css` | Added the `oc2-` rules (table, sticky heading, empty cell, lead, tie, chip, footer, the five fields, phone rules) and `.ocs-told`. **Deleted** `.ocs-ft-b [data-ocs="ok"]{order:-1}` | **New code.** Only existing design tokens; the gate counts 0 loose colours, 0 new shadows, 0 new radii, 7 font sizes (the limit) |
| `alvoraa_portal/alvoraa_portal/people_settings.py` | One new output field, `joiner_not_ready_keys`, and `what_the_employer_has_not_set()` now called **once** instead of twice | **Extend** an existing endpoint. No new endpoint, no new key, no new permission |
| `alvoraa_portal/tests/portal_joiner_079_test.js` | Three assertions rewritten to the approved behaviour, each keeping its sentence and its AC number; fixture gains `joiner_not_ready_keys` | The old shape pinned "the second tick exists only on a ticked row", which is exactly what ALV-310 reverses |
| `alvoraa_portal/tests/portal_faces_078_test.js` | Three assertions updated: the save button's wording (AC-89) and the footer's DOM order (D-6). Both intentions kept — the consequence is still on the button, and the footer is still Preview, Cancel, Save | The design rewrote the button's words and deleted the phone's `order:-1`; the D-6 assertion counted every child, so it saw the new spacer. It now reads the buttons by their `data-ocs` attribute |
| `alvoraa_portal/tests/portal_settings_dialog_310_test.js` | **New**, 66 assertions | Proves all three tickets, and proves the two things the old tests could not see |
| `alvoraa_portal/alvoraa_portal/tests/test_joiner_words_305.py` | **New**, 2 tests | Pins the six joiner-facing labels against `joining.html` |
| `scripts/run_dom_tests.js` | The new suite registered; `EXPECTED_BROWSER_TESTS` 22 → 23 in the same commit | The runner refuses a list that disagrees with the files on disk |

Rung of the ladder: **4 (new code)**, as proposed and approved in
`00-impact-analysis-dialog-overhaul.md` §1. No new DocType, endpoint, app,
dependency, flag, cache, job or index.

## The acceptance criteria, from the design's §11

| AC | How it is satisfied |
|---|---|
| 1 · one row per item, decisions as columns, sticky heading, 2 columns on `joiner`/`my` and 1 on `docs`/`profile` | `ocsRow`/`ocsDialog`; `.oc2-tbl thead th{position:sticky}`. Tested on all four lists |
| 2 · a tick does not re-render the list; a test asserts the focused element after Space is still the same checkbox | The change handler writes one class, at most one other box, and the footer. Tested: `doc.activeElement === box` after a change event |
| 3 · the second cell is empty and not focusable on a row not asked for; unticking clears the saved value | `tr.oc2-off .oc2-cell.oc2-n{visibility:hidden}`, plus `OCS.need[f]=0` and the box unchecked in place. Three layers still prune it: the browser, `_set_access_setting`, every reader |
| 4 · each box's accessible name contains the item name **and** the column name | `aria-label="<name> — <column>"`, plus `<th scope="col">`. Tested on every box |
| 5 · the phone footer is Preview, Cancel, Save in both DOM and screen order; `order:-1` deleted | Deleted. Tested by DOM order and by the rule's absence from the page's CSS |
| 6 · the preview is per list; the joiner's preview shows the joiner's own labels and hints, not the Positions map and not raw columns | `ocsPreview` branches per list; `OCS_JOINER_READS` carries the joiner's words. Tested that no column name appears in the sheet |
| 7 · the exact strings in §4 and §7 | Built verbatim, including "Save — 6 asked for, 6 must be filled in", "Save — ask a joiner for nothing", the two lead sentences, both tie lines and the "send the form back empty" line |
| 8 · the word "compulsory" does not appear | Gone from the dialog, the button and the card chip (now "Must fill in"). Tested |

ALV-305's own criteria: the rows and the preview both show plain words, and the
new test asserts the **visible text**, which is what the old test could not.

ALV-304's own criteria: five inputs on the card saving through
`set_people_setting`; the existing validation path untouched; the card no longer
prints a retention number nobody chose.

### What I could not satisfy

Nothing in the three tickets. Two things are **deliberately out**, as the task
set them:

- **The compulsory-documents column (OCS8 / design DECISION 4).** Not built. It
  decides what a stranger is asked to hand over and has not had the security
  review. The table makes it cheap to add once `01c` has seen it.
- **ALV-311** and **slice 082**. Untouched.

## Design question 5, answered

The six joiner-facing labels live in `joining.html` (Jinja-translated at render)
and are needed in `portal.js` (translated in the browser). One shared source
would mean a new server constant exposed through two different translation
mechanisms — more code than the copy. **I kept the duplication and wrote the
test that makes it safe** (`test_joiner_words_305.py`), and proved the test
fails by changing one word. Declared below as an acceptable simplification.

## The seven dimensions, against the code actually written

| Dimension | Before → after | Verdict |
|---|---|---|
| **Performance** | A tick rewrote up to 18 rows of HTML; now it writes one class, at most one checkbox and two footer nodes. Server calls unchanged (1 for the card, 1 for the document list); ALV-304's dialog opens with **no** fetch and saves only changed fields, so 0–5 POSTs. One fewer duplicated call inside `get_people_settings` | **improves** |
| **Security** | No new endpoint, key, role or whitelisted function. **New `ignore_permissions`: zero.** Every write still goes System Manager only through `_set_access_setting`, with the logged refusal and the `Version` row. A field name is never put into a CSS selector — the need box is matched by attribute | **neutral** |
| **Reliability** | The browser refuses nothing; the server's own sentence is what the person reads, with the focus moved to the field it refused and the typed values kept. The card repaints from the server after every save. A partial save of five independent settings leaves the gate shut and the card still naming what is missing | **improves** |
| **Scalability** | Longest list is 18 and does not grow with headcount; the removed per-tick redraw is the case that scaled worst | **neutral / slightly improves** |
| **Maintainability** | Each list's words are in one place instead of four-way ternaries in five functions; one row builder for all four lists; six repeated strings deleted. Against that: one duplicated label map, pinned by a test | **improves** |
| **Data integrity** | No cache, no denormalised field, no new transaction boundary. "Compulsory ⊆ asked" keeps all three layers | **neutral** |
| **Compliance / privacy** | Nothing personal is shown, logged or widened: no field added to any list, export, notification, report or reply that carries a person's data. The new server field carries **setting key names only**. Two improvements: the card stops presenting our default retention period as the employer's decision, and 079-PRIV-1 and 079-PRIV-3 are now dischargeable from a screen | **improves** |

## NFR notes

- **Query counts.** `get_people_settings` is unchanged except that
  `what_the_employer_has_not_set()` now runs once rather than twice — about four
  fewer `get_default` reads per card load. No new query anywhere.
- **Indexes, background jobs, caches:** none added. None needed; no measured
  number says the simple version misses the budget.
- **Permission enforcement points:** `people_settings._require_system_manager`
  (read), `org_settings._set_access_setting` (write, System Manager only, with
  the range checks and the `Version` row), and the readers' own intersection of
  required ⊆ asked. All pre-existing; none changed.
- **Sensitive fields touched:** none. The picker's allow-list is untouched, so
  bank account, PAN, salary and date of birth are still not offered and would
  still be refused twice if they were.
- **Fallbacks:** if `joiner_not_ready_keys` is absent (an old reply), the card
  prints the numbers as it does today — the same behaviour as before this
  change, not a new failure mode.

## Departures from the prototype

| Departure | Why |
|---|---|
| ALV-304's dialog uses the existing `.ocs-back`/`.ocs-dlg` chrome, not the prototype's `oc2-sheet` | The prototype drew that dialog inside its own review sheet and labelled it "Recommendation, not a build", so there is no drawn product chrome to copy. Its five fields, their labels and their hints are built word for word. Reusing the picker's dialog also keeps Escape, Cancel and focus-return working with no new code, and adds no new `position:fixed` element for the tray check to learn |
| The "Set what a joiner is told" button also appears in the section's action row once nothing is missing | The prototype puts it only inside the amber block. That block disappears once the four values are set — which would leave the notice text unchangeable for ever, a new dead end in the ticket that is about a value that cannot be set. Exactly one button is on screen in either state |
| The docs and Positions lists get the heading "Detail" over their name column | The prototype's heading for all four lists. Stated because "Detail" over a list of document types reads slightly oddly; it is what was drawn, and changing it is a word Surbhi should pick, not me |

Nothing else differs. The leads, tie lines, column headings, button sentences,
the per-row "The joiner reads: …" line, the sticky heading, the empty cell and
the footer order are as drawn.

## What else moved while I worked

- My worktree's base is `f40e368b`, which was `origin/dev`'s head when I
  started. **Three commits came in from somebody else while I worked** -
  `683e16d1`, `f9daf944` and `3cd1b04d`, all ALV-293 (a User Permission row
  restricts, so a manager who is also HR got no rows; plus a country on the
  company fallback). They touch `manager_scope.py`, `test_manager_scope.py` and
  two documents under `docs/slices/alv-293/`. **No overlap with anything I
  changed**, so the rebase onto them was clean and nothing of theirs had to be
  rescued.
- Read before starting, and reported: `aefb68d0`, `174c6c2f`, `99e436b2`,
  `4de0c01b` (ALV-302, biometric sync punches — attendance and auth, no
  overlap), `ccfeab34` (ALV-303, a camera emoji removed from a button in
  `portal.js`, a different block), `aaa55c5b` and `55b4a698` (CI and 081 docs).
- **The main checkout holds other sessions' uncommitted edits**, including in
  `portal.js`, `hooks.py`, `auth.py` and `people_settings.py`. None of them was
  touched, staged or brought in. Nothing was run on the shared bench, so no
  other session's test run was disturbed.
- Nothing of anyone else's had to be proved to survive, because nothing merged.

## Commands run, and what they said

| Command | Result |
|---|---|
| `node --check` on `portal.js`, both test files, `run_dom_tests.js` | OK |
| `node alvoraa_portal/tests/portal_settings_dialog_310_test.js <page>` | **66 passed, 0 failed** |
| `node alvoraa_portal/tests/portal_joiner_079_test.js <page>` | **40 passed, 0 failed** |
| `node alvoraa_portal/tests/portal_faces_078_test.js <page>` | **186 passed, 0 failed** (3 failed before the assertions above were updated — found by running the whole suite, not one file) |
| `node scripts/run_dom_tests.js` (the whole suite, 23 files) | **23 run, 0 not run, 0 failed**, exit 0 — read in full, not tailed, because the runner prints one summary per file and a tail hides the rest |
| `test_joiner_words_305.py`, standalone, plus a mutation | 2 passed; **fails as intended** when one word is changed |
| `python scripts/check_app_integrity.py` | 915 checks, all consistent |
| `python scripts/check_design_system.py` | OK — 0 loose colours, 0 emoji, 7 font sizes (the limit), 3 radii, 0 shadows |
| `check_api_paths.py --max 0`, `check_brand_spelling.py`, `check_tag_balance.py`, `check_nginx_conf.py`, `check_scope_traps.py`, `check_no_demo_passwords.py`, `check_preview_flag.py`, `check_portal_assets_gate.py`, `check_min_app_version.py` | all OK |
| `node scripts/check_portal_handlers.js`, `check_portal_trays.js --static`, `check_undefined_js.js`, `check_rating_bands.js` | all OK |
| `ruff format` / `ruff check` on the new Python file | clean |
| `ruff check` on `people_settings.py` | one `I001` import-order finding, **pre-existing** — the same finding is reported on the file at `HEAD`, and I did not touch its imports. CI's ruff steps are non-blocking |

**Not run:** `bench run-tests` for `test_joiner_078`, `test_joiner_079`,
`test_people_settings_078`, `test_browser_call_args_045` and
`test_portal_security_010`. These need a bench, and the task's instruction is
local-only and not the shared `hrlocal-bench` container. Reasoning about what
they assert is in the report; **somebody must still run them before this
lands**, and they are the suites that would catch a server-side mistake in the
one line of Python I changed.

## Known gaps and shortcuts

- **Acceptable simplification.** The six joiner labels are duplicated in
  `portal.js` and `joining.html`, with a test that fails if they diverge. One
  shared source needs a server constant rendered through two translation
  mechanisms.
- **Acceptable simplification.** ALV-304 saves five settings as up to five
  sequential writes rather than atomically. They are five independent settings,
  each independently validated and refused, and the invite gate stays shut until
  all of them are set, so a partial save is visible and recoverable on the
  screen the person is still looking at. Making it atomic would need a new
  endpoint.
- **Intentional trade-off.** Two System Managers editing these settings at the
  same time: last write wins, with a `Version` row each. Unchanged from today,
  on a screen used a handful of times a year by one or two people.
- **Intentional trade-off.** The dialog's inputs carry `min`/`max` so the
  browser can help, but nothing in the browser refuses a value. The rule lives
  once, on the server.
- **Temporary debt.** The bench suites above have not been run. Removed by one
  `bench run-tests` pass on a throwaway site.
- **Not debt, but worth Surbhi's eye.** ALV-304 makes the joiner form
  switchable-on at a tenant for the first time. `alvoraa_joiner_form_on` is
  still a separate, deliberate setting and I did not touch it, and `ALV-215` is
  still open against switch-on.

No dangerous debt.

## The subtract pass

Read once more asking only what can be deleted. Removed on that pass:

1. **A per-row `Needed` chip** in the picker. The "Must fill in" column already
   says it; the chip would have been the same thing twice on one line. (The
   designer removed it in her own subtract pass; I did not put it back.)
2. **An `ocsPick` guard that closed any already-open dialog.** Written, then
   deleted: a modal covers the card, so no person can open a second dialog. It
   was defending against a state only a test can create, and the test now
   closes the first dialog as a person would.
3. **A browser-side range check** before saving the two clocks. Deleted: it
   would have been a second place for the rule to be wrong, and the server
   already refuses with a better sentence than I would have written.
4. **A `canNeed` variable** in `ocsRows`. Redundant once each list's words say
   whether it has a second column — `w.c2` is the one source.
5. **A separate stacked layout for 200 % text.** Not written: the designer
   measured the table at 195 CSS px and it does not need one.

Nothing else could go without losing an approved requirement.
