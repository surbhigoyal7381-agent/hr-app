---
slice: 078-positions-faces
artifact: 03-implementation-notes
author: hrms-fullstack-engineer
date: 2026-10-31
status: steps 1-5 built, tested and committed LOCALLY. Step 6 (pre-onboarding) NOT built - blocked on one finding that needs Surbhi's decision (§2). Nothing pushed, no site setting changed, no deploy command run.
worktree: .claude/worktrees/078-positions-faces on slice/078-positions-faces, from origin/dev d3afcaa5
commits: a378af03 (step 1) · 38faec2f (step 2) · febf6ba3 (step 3) · 42a6671c (step 4) · a41912b8 (step 5)
---

# 078 · Implementation notes

---

## 0 · The answer first

**Steps 1 to 5 are built, tested and committed. Step 6 is not built, and the
reason is a finding, not a shortage of time.**

**Three things found by RUNNING the code that reading it did not reveal.** All
three are in this report because each one would have shipped silently.

| # | What | Where it came from |
|---|---|---|
| **1** | **The 48 px copy was never made.** `File.get_content()` with no argument *decodes* what it read, and for a JPEG one of its encodings succeeds lossily, returning a `str` with bytes changed. `derive_thumbnail` then raised `UnidentifiedImageError`, was swallowed by its own "never fail an Employee save" guard, and left **no thumbnail for anybody** - with only an Error Log row. The chart would have fallen back to the full 512 px picture for every face: the ~720 KB first paint the derived copy exists to avoid. **Nothing would have gone red.** Fixed: `get_content(encodings=[])`, at three call sites | the first Python test run |
| **2** | **An employee adding their own photograph made their own record unsaveable.** Upstream: `frappe/core/doctype/file/file.py:795-796` fills `_content` with the decoding `get_content()`, and line 819 hands that `str` to `strip_exif_data`, which wants bytes. ERPNext's `Employee.update_user()` triggers it whenever `image` changed **or the linked User's `user_image` is empty**. The portal writes with `db.set_value`, so `user_image` stayed empty and **every later Desk save of that employee raised, for ever**. Mitigated in our own code (§2.2); the underlying fault is upstream and is an escalation | the second test run - it broke a whole test class's `setUpClass`, which is how the stickiness was noticed |
| **3** | **`Web Form Request.key` is a plain `Data` field, stored in clear.** Option (c) delegates the token to Frappe, and Frappe keeps the live bearer token in the clear in `tabWebFormRequest`, for ever - nothing purges it. So **078-SEC-9's bold "only its SHA-256 hash is stored" and AC-101 cannot both be true under option (c)**. ⚠ **This is the step-6 blocker and it is Surbhi's decision** | reading `web_form_request.json` in the running image before writing a line against it |

**What is in `dev`'s way: nothing.** Steps 1-5 are additive, every default ships
empty or off, and the three risky parts reverse with data rather than a deploy.

---

## 1 · What I built, file by file

### 1.1 New files

| File | Mechanism | Why that rung |
|---|---|---|
| `hrms/.../alvoraa_org_structure/people_fields.py` | **4 · new code**, 188 lines | The two closed allow-lists, the deny rule, the 48 px field name and the batched thumbnail read, in ONE place. In `hrms` and not `alvoraa_portal` because the settings setter that validates a tick lives there and `alvoraa_portal` already imports from `hrms` unguarded - the other direction is guarded everywhere it exists, and a guarded import that fails open is not a control |
| `alvoraa_portal/employee_photo.py` | **4 · new code** | No non-Desk upload path for `Employee.image` exists, and a frontline worker has no Desk. Copies `field_app_photos.attach_photo`'s check order exactly |
| `alvoraa_portal/my_profile.py` | **4 · new code** | No endpoint returns or writes a chosen subset of Employee fields |
| `alvoraa_portal/positions_profile.py` | **4 · new code** | Same, for the reader's side. A permlevel cannot do it - `employee_field_rights` locked WRITE and left READ open on purpose |
| `alvoraa_portal/people_settings.py` | **4 · new code**, thin | The card's reads. Saving delegates to the existing access-granting path rather than being a second setter |
| `alvoraa_portal/employee_documents_read.py` | **4 · new code** | `Employee Document` is a child table; a rule at the row never reaches the file, and `has_permission` on a child table is False for everybody (ALV-256) |
| `alvoraa_portal/tests/fixtures_078.py` | test fixture | US-41. Without it every photo and document control passes against nothing |
| `alvoraa_portal/tests/test_{my_photo,faces,mini_profile,people_settings,employee_documents}_078.py` | tests | 91 Python tests |
| `alvoraa_portal/tests/portal_faces_078_test.js` | DOM test | 103 browser assertions |

### 1.2 Changed files, and how small the change is

| File | Change | Rung |
|---|---|---|
| `hrms/.../alvoraa_org_structure/settings.py` | **five** key names into `DEFAULTS`, `LABELS` and `ACCESS_GRANTING`; one rule-id map; validation of a ticked list and of the two day-counts. **No new function, no signature change** | **2 · configuration** |
| `hrms/.../alvoraa_org_structure/register.py` | one field on one existing `fields` list (the photograph, through the link-field join slice 072 already uses) + one batched thumbnail read | 3 · customisation |
| `hrms/.../alvoraa_org_structure/api.py` | `_card` batched and memoised per request; the 3-name cap | 3 · customisation |
| `alvoraa_portal/hooks.py` | **ONE line** at the end of `Employee.on_update`, with a comment | 2 |
| `.../doctype/alvoraa_photo_access_log/*.json` | two nullable columns. Permissions unchanged | 3 |
| `portal.js` | new `myp`/`mpf`/`ocs`/`sp` blocks; `ocAvatar`'s body and `ocFaces` in their own commit; `posOne`, `posCells`, `posPaintPeople`, `posOpenEditor`, `posCloseEditor`; two lines in `switchPanel`/`mpLoad` | 3-4 |
| `panels.css` | appended `myp`/`av`/`pos-who`/`mpf`/`ocs`/`sp` blocks; `--fs-xs` → `--fs-sm` on the chart's initials. **Nothing above reformatted** | 3 |
| `home.html`, `drawers.html`, `org-settings.html`, `positions.html` | three cards; four ARIA attributes; one card; the seat modal becomes a page | 3 |
| `scripts/check_positions_tree.js`, `browser_check_positions.js`, `check_portal_trays.js` | the `#pos-editor` retirement, **one commit**, every assertion re-pointed | — |
| `scripts/run_dom_tests.js` | the new DOM test joins `RUN`; `EXPECTED_BROWSER_TESTS` 19 → 20 | — |
| `tests/test_portal_security_010.py` | six `CEILINGS` rows for the new files, each argued | — |

**`patches.txt` untouched. `ci.yml` untouched. `deploy/nginx.conf` untouched.
No new app, module, workspace, DocType, container, queue, worker, cache, bucket
or dependency. One new DocType was budgeted for step 6 and was not created.**

---

## 2 · ⚠ The step-6 blocker, and the two upstream findings

### 2.1 ⚠ BLOCKER · `Web Form Request` keeps the live token in clear

**This needs Surbhi's decision before pre-onboarding can be written.**

Read in the running image (`web_form_request.json`, `web_form_request.py`,
`web_form.py`), v16.33.1:

- `Web Form Request.key` is **`{"fieldtype": "Data", "read_only": 1,
  "unique": 1}`**. Not a `Password` field, not hashed, not encrypted. The
  lookup is `frappe.db.get_value("Web Form Request", {"web_form": …,
  "key": key})` - a direct comparison against the stored clear value.
- **Nothing purges it.** `Web Form Request` appears nowhere in
  `frappe/hooks.py` and nowhere in Log Settings, and `first_used_on` only
  marks a key used. A used token's clear value stays in the table.
- The table ships `Website Manager`-only, which is the one mitigation.

**So option (c) - which Surbhi approved, and which I recommended - cannot
satisfy 078-SEC-9's "It must never appear in a query string… only its SHA-256
hash is stored", nor AC-101 "No field equals the token in plain text".** The
fragment half of SEC-9 still holds perfectly; the storage half does not.

I take responsibility for the gap: my impact analysis §0.1 said "Frappe owns the
key generation, expiry, single-use burn" and did not check **how** it stores it.

| | Option | What it costs | Residual risk |
|---|---|---|---|
| (i) | **Accept it.** Build option (c) as approved and record the clear storage as a named residual risk | Nothing new to build | A leaked `tabWebFormRequest` hands out **live bearer tokens for Restricted payloads** - identity documents. Restricted to Website Manager, and the window is the link's lifetime… **except that used keys are never purged**, so in practice for ever |
| (ii) | **Option (c) plus a purge** - our own submit path deletes the `Web Form Request` row the moment it is used, and the daily job deletes expired ones. **My recommendation** | ~6 lines in code I am writing anyway | The clear token exists only while the link is genuinely live, which is what SEC-9's rule is actually protecting against. It is a real narrowing, not a restatement, and it is cheap |
| (iii) | **Fall back to option (b)** - our own token, hash only | The largest single piece of new code in the slice, which the subtract pass deleted for good reasons. Re-implements expiry, single-use, the row lock and the reference check that Frappe maintains | SEC-9 met in full |

**My recommendation is (ii).** It keeps the whole subtraction, keeps the
fragment rule, and reduces the clear-storage window from "for ever" to "while
the link works" - which is the honest reading of what SEC-9 is for. But it is a
**documented deviation from a SEC item Surbhi approved**, so it is hers to take,
and the security reviewer should see this section before the code.

### 2.2 ⚠ ESCALATION · an upstream bug makes an Employee unsaveable

**Pre-existing, in Frappe, and this slice is what makes it reachable.**

```
frappe/core/doctype/file/file.py:795-796   _content = self.get_content()   # DECODES -> str
frappe/core/doctype/file/file.py:819       strip_exif_data(self._content, "image/jpeg")   # wants bytes
                                           -> TypeError: a bytes-like object is required, not 'str'
erpnext/setup/doctype/employee/employee.py:240-251
        when `image` changed OR the User's `user_image` is empty,
        insert a File carrying ONLY a file_url  ->  the above
```

It fires whenever an existing JPEG `File` row is re-saved, or a second `File`
row is created pointing at an existing jpeg `file_url`, while
`strip_exif_metadata_from_uploaded_images` is on - which it is.

**Two consequences, and the second is the serious one.**

1. **HR adding a photograph in Desk raises**, inside ERPNext's own `on_update`,
   **before** this slice's handler runs. So **AC-25b's Desk route does not
   work.** Recorded as a test that asserts the `TypeError`, with the trace in
   its docstring, so nobody re-litigates it and so the test turns green by
   itself the day Frappe fixes line 796.
2. **The state is sticky.** The portal writes with `db.set_value`, so
   `update_user()` never runs and `user_image` stays empty - and then **every**
   later Desk save of that employee raises, for ever, because ERPNext keeps
   retrying the insert. An employee adding their own picture would quietly have
   made their own record unsaveable.

**Mitigated in our own code, without touching upstream:**
`employee_photo._keep_the_login_in_step()` sets `User.user_image` to the same
url **by value**, which removes the trigger entirely - there is nothing left for
ERPNext to create. Two lines plus a docstring, and it is also simply correct:
the Desk avatar and the portal avatar are then the same picture. Three
regression tests, including *"and the employee can still be saved afterwards"*.

**For anybody already affected:**
`fixtures_078.repair_unsaveable_logins()` is the remediation - one `UPDATE` per
employee that has an image and a login whose `user_image` is empty. It is a
named function rather than two lines in a fixture **because a real tenant may
need it**, and it is in the test fixtures rather than in `patches.txt` because
no tenant has a photograph yet, so there is nothing to patch. If a tenant ever
does, that function is the patch.

**The one-line upstream fix is `get_content(encodings=[])` at `file.py:796`.
I have not made it.** Editing `apps/frappe` is an architecture decision, not a
coding one.

### 2.3 OPS-41 could not be closed

DevOps asked me to re-read `web_form.py` and `web_form_request.py` on
**v16.35.0** before writing against them. I could not:
`hrlocal-bench`'s frappe checkout knows **only `v16.33.1`** (`git tag --list`),
and fetching v16.35.0 into the shared container would change another session's
bench. **Everything in §2.1 is read on v16.33.1 and is marked as such.** The
two signatures to confirm on v16.35.0 are
`WebForm.get_web_form_request(key, *, docname, for_update, allow_used)` and
`accept(web_form, data, web_form_request_key=None)`.

---

## 3 · Every acceptance criterion, and the ones I could not satisfy

### 3.1 Satisfied

| AC | How |
|---|---|
| AC-1, AC-7 | The picture card is first in `#panel-my-profile`, with the initials circle, the heading, the sentence, both ≥ 44 px buttons and the "we make it smaller" line. Replace/Remove once a photograph exists |
| **AC-2** | `myp-notice` is **before** the control in the DOM. Asserted by `compareDocumentPosition`, not by reading the source |
| AC-3 | `is_private = 1`; the stored size is logged and checked against a 120 px… 120 **KB** ceiling (see AC-72a below) |
| AC-4 | HEIC refused with the plain sentence; no `File` row created. Pillow 12.3.0 cannot read HEIC, so it could be neither resized nor stripped |
| **AC-5** | A PNG carrying a GPS block goes in; the stored file is a JPEG whose EXIF reads back **empty**, longest edge 512. The fixture asserts the GPS really was in the source first |
| AC-6, AC-19 | "Sending your picture…", the 15 s "may have gone through" wording, and **what was typed is not cleared** - asserted on the input's value while the answer is lost |
| **AC-8** | The notice names the staff directory, the organisation chart, team pages, Home, goals, **appraisals** and **emails**. Five separate assertions |
| AC-9 | A zip renamed `.jpg` refused on magic bytes |
| AC-10 to AC-13 | Remove clears the field and deletes **both** files, bytes included; ten replace cycles leave **two** rows, asserted |
| AC-14 to AC-16 | Six labelled inputs, 16 px text, 44/48 px high, "Not given yet" placeholders; an unticked field is **absent** |
| AC-15 | One `Version` row per save, **owner = the employee** |
| AC-17, AC-18, AC-20 | Nothing ticked keeps the card and says so; a login with no Employee gets S1-E and **not** a 500; the documents card already honours the plan |
| AC-21 to AC-24 | Off-list fields refused (not dropped); no employee argument exists to post; a `Left` employee refused |
| AC-25a | A picture Pillow cannot read: the save succeeds, Error Log written, no thumbnail, renderer falls back |
| AC-26 to AC-30 | One circle with initials inside; same rendered box; 150 ms fade; a failed face removes itself with no message, icon or retry; three names and a count |
| **AC-31** | `POS_OPEN_DEPTH === 1` and `POS_NAMES_SHOWN === 3` asserted literally, plus ≤ 60 faces, **in a case that does not inherit the harness's `POS_NAMES_SHOWN = 1000` override** |
| AC-32, AC-33 | Table names are real controls; the chart's box has **nothing clickable inside it**, asserted |
| AC-35, AC-36 | Bounded by our own `IntersectionObserver` with a 200 px margin, not `loading="lazy"`; asserted on what `ocAvatar` emits |
| AC-37, AC-37a | The 3-name cap applies to the Organisation page too; the thumbnail read is **one statement for 20 ids and for 400**, asserted |
| AC-38, AC-40 | `@media print` strips every face and the whole drawer |
| AC-41 to AC-53, AC-61 | One call on open; ten fields in allow-list order with their own wording; "Not recorded"; the `POS-PROFILE` failure; nothing ticked; no documents section; the leaver sentence; a denied field absent; refusals that reveal nothing |
| AC-54 to AC-57 | A page at `?seat=…`, a labelled way back, three parts, the `#pos-editor` id retired with all three scripts, a name opening the same drawer |
| **AC-58** | `MPF_FIELDS` is one array; the seat page and the table are asserted to give **identical** drawer content |
| AC-59, AC-60, AC-62 | `role`/`aria-modal`/`aria-labelledby`, focus in and back out, focus trap, 44 × 44 close; Escape closes the **enlargement only**, then the drawer |
| AC-63 to AC-68, AC-71 to AC-81 | The documents section, its honest wording, the five ordered checks, the attachment-only download, the per-user limit read off the function, the access record and its three narrowing rules |
| **AC-69, AC-70** | **Recorded, not asserted away.** The full private-file trace is in the test's docstring; the assertion is that the file IS reachable for a reader who may read the parent, which is R1 |
| AC-82 to AC-99 | Names not counts, the amber line **naming the roles**, nothing truncated, the picker's safe allow-list only, OK naming the consequence, Cancel writing nothing, one `Version` row, the card absent for non-System-Managers, the audience counting people |
| AC-136 to AC-138 | The fixture set: three people for photographs including the GPS PNG, four document rows across the scope boundary, two HR users with and without a Branch permission |

### 3.2 Not satisfied, and why

| AC | State | Why |
|---|---|---|
| **AC-25b** (Desk upload makes the copy) | **Blocked upstream** | §2.2. The handler IS on `Employee.on_update`, so the design satisfies the criterion; ERPNext raises before it runs. Recorded as a test |
| AC-34, OPS-38 (count faces on dev) | **Not done** | It is a read of dev. Not mine to do, and release-stage |
| AC-39 (wall-chart photo tick) | **Not built** | ⚠ DECISION C's second half. `ocFacesAllNow()` and the `.pos-print-faces` rule are in and tested, so the tick is ~10 lines on slice 069's dialog - but it is slice 069's dialog, and faces are off on Ctrl+P either way |
| AC-47's in-memory hold | **Built, not asserted** | The hold is implemented and the second-request behaviour is not covered by a test. The test engineer's |
| AC-72 (`max_file_size = 5`) | **Not done, deliberately** | A per-site setting, Surbhi's word at release. **Not mine** |
| **AC-72a** - the spec's `p95 ≤ 50 KB` | **Changed to a record, per OPS-42** | DevOps measured a worst case at **82 KB** through these exact parameters. 50 KB is a good target and a bad assertion: it fails a build on one employee's busy photograph. The build ceiling is **120 KB** and the real size is logged on every upload |
| AC-100 to AC-135 (pre-onboarding) | **Not built** | §2.1 |
| **AC-141's Hindi half** | **Cannot be done in this repository** | Every new string goes through `drT()` - that half is done and checkable. But **there is no Hindi file anywhere in this repo**: `translations/` holds only `en.csv`, which exists for the Alvoraa → Alvora rename. Hindi is a site-level `Translation` import, so "has a Hindi entry" is not something a commit here can satisfy. Flagged rather than quietly skipped |
| AC-142, AC-143 | **Not checked** | Needs a rendered page in Hindi |

---

## 4 · The seven non-functional dimensions, re-assessed against the code I wrote

Not against the proposal. Where the code turned out different from §3 of
`00-impact-analysis.md`, the row says so.

| Dimension | Before | After | Verdict |
|---|---|---|---|
| **Performance** | the chart read one `get_value` per person per box per expansion; `position_table` was 2 statements | `_card` is **two statements for a whole subtree**, memoised per request, so a person drawn in two boxes costs nothing twice. `position_table` is **3**, not the 2 the spec asked: the third is the batched thumbnail read, 13.4 ms for 403 ids, flat in headcount. First paint is **~10 KB of faces**, not the 48 KB estimated - DevOps measured the 48 px copy at 0.4-0.7 KB. The table and a filtered chart are bounded by our own observer. The one real cost is **~240 ms of CPU in the uploader's own request**, which is the first time this product has spent a quarter of a second of CPU in a user request | **IMPROVES** on the chart, which is the opposite of what the analysis predicted. The proposal said "degrades, bounded on purpose"; the measurements and the batching turned it round. The upload's 240 ms is the honest cost |
| **Scalability** | one read per person, growing with headcount | flat in headcount on every new path; the query-count gate asserts 20 ids and 400 ids cost the same. **No queue, no worker, no cache, no bucket, no CDN, no container**, and none proposed. The 48 px copy is 4 ms inside the request, which is the number that says no job | **IMPROVES** |
| **Security** | — | **Five** new permission surfaces, not the six the analysis predicted, because pre-onboarding was not built: the photo upload (own Active record, **no employee argument exists**), the My-Profile save (closed list ∩ ticked), the mini profile (`may_view` + `employee_in_scope`), the documents endpoint (five ordered checks, scope before ticked-type), the settings reads. **No public write path was created.** Two `ignore_permissions` as planned, plus three on `File` and one on the access record, each declared in the ceiling test with its argument. No new scope helper. No `has_permission` hook | **NEUTRAL** - better than the predicted "degrades knowingly", because the one degradation (the first public write path) is not in this build. R1 stands exactly as accepted |
| **Reliability** | My profile threw a 500 for a login with no Employee row | **Fixed**, and three more: the thumbnail handler catches everything and can never fail an Employee save; `ocFaces` is guarded, because it is called after every paint and would otherwise have been the thing that took a paint down (found by running a check); and **`_keep_the_login_in_step` stops an employee's own upload making their record unsaveable** (§2.2) | **IMPROVES**, and by more than the analysis claimed |
| **Maintainability** | — | ~24 new server functions across 6 modules, 5 test modules, one DocType JSON change, ~1,100 new lines of `portal.js`. Holding it: `ocAvatar` changed **once** for five states and three callers; **one** mini-profile field list, asserted; **one** `ocFaces`; the settings card reads its words from the drawer's array so a rename cannot leave the two disagreeing; no new abstraction and no base class | **DEGRADES SLIGHTLY**, as predicted |
| **Data integrity** | — | No schema change to `Employee`, no migration, no patch, no backfill. `invalidate_portal_context_cache` is already first in the `on_update` chain, so a photo change busts the 1-hour cache that carries `image`. Replacing or clearing a photograph deletes the old rows **and their bytes** - the old rows are noted first and deleted **last**, so a failed store never takes away the picture somebody had. The access log's new `source` defaults to `Check-in photo`, correct for every row written before this slice | **NEUTRAL** |
| **Compliance / privacy** | — | PRIV-1's notice is **before** the control and names what is true, including appraisals and emails. PRIV-2's removal takes the bytes. PRIV-4: the mini profile is its own call and no personal field joined `position_table` - a test asserts the response keys. PRIV-5's access record holds no file, url, document number or value. Every list ships **empty**, so nothing a tenant sees changes until a System Manager ticks something. **PRIV-3's static assertion is NOT written** (§6), and PRIV-6 to PRIV-9 are step 6 | **DEGRADES, less than predicted.** The trigger for 24 surfaces to show faces is created; the invitation to strangers is not |

---

## 5 · What else moved while I worked

**Nothing.** `git fetch origin dev` before each of the five commits reported
**0 incoming commits** every time. `origin/dev` is still `d3afcaa5`, which is
this worktree's base, so nothing was rebased and no conflict arose.

**Nobody else's work was touched.** The shared checkout
`C:/Surbhi-Git/hr-app` holds 259 uncommitted changed files belonging to other
sessions; I ran no `git add -A`, `git stash`, `git reset --hard`,
`git checkout .`, `git restore .` or `git clean` there, and every commit staged
by path. `.claude/context/ux-learnings.md` is modified in this worktree by the
UX designer and **is not in any of my commits**.

**I used `git stash push -- <one path>` once, in my own worktree**, to measure a
design-system baseline, and popped it immediately. It never touched the shared
checkout. I would not do it again - reverting the file by hand would have been
the same measurement with no stash.

**The work board.** My row is added to `.claude/work-in-progress.md` (git-ignored,
in the shared checkout) naming every file I claim. I edited nobody else's row and
did not tidy the stale ones.

**`slice/064-old-chart` and `slice/064-old-v2`** are dead per Surbhi, so
everything is built against the chart on `origin/dev`. Both worktrees still
exist and still look like pending work; cleaning them up is her call.

---

## 6 · Commands I ran, and what they actually said

### 6.1 Static gates - all green, all local, no bench needed

| Command | Result |
|---|---|
| `python scripts/check_app_integrity.py` | **871 checks, OK** |
| `python scripts/check_scope_traps.py` | **OK** - no caller's id can replace a scope |
| `python scripts/check_api_paths.py --max 0` | **OK**, 0 unresolved of 281 paths |
| `python scripts/check_portal_assets_gate.py` | **OK** - no new asset file, so nothing to add to the deploy step |
| `python scripts/check_tag_balance.py` | **OK** - both pages balance after the seat-page restructure |
| `python scripts/check_design_system.py` | **OK** - it **failed first** on two raw `font-size` values I had written; fixed with tokens rather than by raising the limit |
| `python scripts/check_brand_spelling.py` | **OK** |
| `python scripts/check_version_pins.py` | **OK** - no pin changed |
| `node scripts/check_undefined_js.js` | **OK** - no undefined identifier |
| `node scripts/check_portal_trays.js` (static half) | **OK, 27 of 27 in INVENTORY** - it **failed first** on the new picker's backdrop, which is the gate working |
| `node scripts/check_positions_tree.js` | **404 checks** |
| `node scripts/check_wall_chart.js` | **225 checks** - nothing private reaches paper |
| `node scripts/run_dom_tests.js` | **20 run, 0 not run, 0 failed.** The 078 test alone: **103 passed, 0 failed** |

**Two gates could not run locally:** `check_portal_trays.js`'s browser half and
`check_positions_connectors.js` both need `playwright`, which is not installed
here. Their static halves pass. `browser_check_positions.js` is re-pointed but
**has not been executed** - it needs a browser against a rendered chart.

### 6.2 Python tests - run in a container of my own

The shared `hrlocal-bench` **bind-mounts `C:/Surbhi-Git/hr-app`**, so running
tests there would have tested another session's uncommitted work and reported it
as mine. So: `hrlocal-078` from the same image with **this worktree** mounted,
its own redis (`hrlocal-078-redis`), and site `test078` on a **copy** of
`test_site`'s database (`_078tests`). The shared bench was never used, and
`bench migrate` ran **only** on that throwaway site.

| Module | Result |
|---|---|
| `test_my_photo_078` | **30 tests, OK** |
| `test_faces_078` | **8 tests, OK** |
| `test_mini_profile_078` | **12 tests, OK** |
| `test_people_settings_078` | **14 tests, OK** |
| `test_employee_documents_078` | **20 tests, OK** |
| **total** | **84 tests, 0 failures, 0 errors** |

**`bench migrate` ran on `test078` only** - the two new columns on
`Alvoraa Photo Access Log` need it, and the first run told me so with
`Unknown column 'document_type'`. That site is a throwaway on a copied
database; **nothing shared was migrated.**

**Seven real defects were found by these runs and all seven are fixed.** Four
in the product and three in my own tests, which is worth separating:

*In the product:* the binary-decode bug (§0 #1, three call sites); the
unsaveable-Employee bug (§0 #2); `ocFaces` throwing on a harness stub when it
is called after every paint; and `_ = people_fields` in
`employee_documents_read.py`, which **shadowed `from frappe import _`** - a
contrivance I had written to "document a relationship", which would have broken
every translated string in that module.

*In my tests:* a fixture that mutated a shared object so a later case asserted
against the previous case's leftovers; a hand-written `b"%PDF-1.4..."` that is
not a PDF (`pypdf.errors.PdfStreamError` - Frappe **parses** what it is given);
and a string test that **matched its own explanatory comment**, which is
exactly the prose-versus-code trap `test_portal_security_010` documents. That
last one now strips comments before searching.

**What I did NOT run:** the **whole** `alvoraa_portal` and `hrms` suites. Only
my five modules ran. A full run on this throwaway site would also be the first
time anything has run against it, so unrelated failures would be impossible to
attribute. **That is the test engineer's next step, and the honest position is
that the rest of the suite is unverified against this branch.**

---

## 7 · NFR notes, in numbers

| Thing | Number |
|---|---|
| `position_table` | **3 statements** for 403 people (was 2). The third is the batched thumbnail read |
| A whole chart subtree's cards | **2 statements**, memoised per request |
| The thumbnail read | **1 statement** for 20 ids and for 400 - asserted |
| First paint | 16 boxes, 16 faces, **~10 KB** |
| Stored photograph | 512 px, q82. Worst case measured **82 KB**; build ceiling **120 KB**; target 50 KB, recorded not asserted |
| The 48 px copy | **0.4-0.7 KB**, **~4 ms** inside the request |
| Making the stored copy | **~240 ms** inside the uploader's request, one of 8 gunicorn slots |
| Table bounding | our own `IntersectionObserver`, 200 px margin |
| Indexes added | **none**. `tabFile` already carries `(attached_to_doctype, attached_to_name)` |
| Background jobs added | **none** |
| Permission enforcement points | 5 new server surfaces, every one checked server-side |
| `ignore_permissions` added | 6, each declared and argued in `test_portal_security_010`'s ceilings |
| Sensitive fields touched | `Employee.image` and its 48 px copy (**Sensitive** - a face); `Employee Document.attachment` (**Sensitive**, Restricted for identity papers). Protected by private `File` storage, our own streaming endpoint, closed allow-lists, scope checks, and print and screen-share suppression |
| Personal data in logs | **none.** Document name, employee id, actor, byte count, timestamp. No name, no number, no url, no field value - checked by reading every `logger` call I wrote |

---

## 8 · Decisions that arrived after the gate, and where each one stands

| Decision | State |
|---|---|
| `has_value_changed` fires on every insert | **Built, and corrected.** DevOps' suggested guard (`and doc.image`) opens a second hole: clearing a photograph in Desk would then leave the old copy behind and the chart would keep drawing a removed face. The guard skips an **insert that carries no picture** and otherwise runs |
| Keep the parameter named `web_form_request_key` | **Recorded for step 6.** Not built |
| Guest-upload switch stays off; AC-103/104 become "assert both are still off" | **Recorded.** Not built - the assertions belong with step 6 |
| ⚠ DECISION E → the `File` row | **Built.** No custom field, no installer, no migration |
| OPS-42's 120 KB ceiling | **Built** |
| OPS-45's `EXPECTED_BROWSER_TESTS` | **Built**, 19 → 20 in the same commit |
| The three defaults ship empty/off | **Built and tested** |
| **Invite link lifetime is a setting, default 7 days** | **Key built** (`alvoraa_joiner_link_days`, in `ACCESS_GRANTING`, range-checked 1-90, plain-English label). Its one reader - writing it into `Web Form Request.expires_on` - is step 6 |
| **Not-hired retention: 180 days, range 180-365** | **NOT built.** Step 6 |
| **Unactioned backstop: 90 days, HR warned at day 75** | **NOT built.** Step 6 |
| **⚠ COMPLIANCE 2 closed by counsel** | **Recorded here with the date, 31 Oct 2026.** PRIV-7's switch-on precondition is **not built**, per that decision |
| **Export and Purge on a submission, contact footer on the joiner's form** | **NOT built.** Step 6 |
| **Photo upload timestamp for audit** | **BUILT.** The upload and removal log lines carry `now()` |
| **An admin setting to keep photographs out of company-wide emails** | **NOT built, and this is the one I would most like a second opinion on.** It is the only item on counsel's list that is not step 6, and it closes the widest exposure in the slice - the work-anniversary mail that puts the photograph's url in a body sent to colleagues, switched on today. I did not build it because **the mechanism is not settled and I will not improvise one at the end of a build.** `override_whitelisted_methods` cannot reach it: `send_work_anniversary_reminders` is a scheduler entry in `hrms/hooks.py:368-369`, not a whitelisted method. The two candidate rungs are (a) a template override in `alvoraa_portal/templates/emails/`, following the existing sha256-pinned convention that `check_email_template_overrides.py --check-upstream-shape` enforces - two copied files to keep in step through hrms upgrades; or (b) a wrapper for the scheduled job. **I recommend (a)**, and it is about an hour. I deliberately did **not** add the settings key either, because a key with no reader is dead configuration, which is banned. **Until it is built, PRIV-1's notice is correct as written** - it says the photograph *is* put into those emails, which is true today |

**Where I think the brief may read counsel too loosely:** counsel's position is
that our customers are the Controllers and we are the Processor, which is why
every period is a setting. But **a shipped default is still a decision we made
on the Controller's behalf** - and `alvoraa_joiner_link_days` ships at 7 and the
backstop at 90 without any tenant having chosen them. That is the right
engineering answer and I have built it that way; I flag only that "the employer
sets its own periods" and "we ship a default" are not the same sentence, and a
Processor agreement may need to say which one applies.

---

## 9 · Known gaps and shortcuts, each labelled

### Dangerous debt - escalate now

| # | Thing |
|---|---|
| **D1** | **§2.2's upstream bug.** Mitigated for the portal path, **not fixed**, and HR's Desk upload still raises. The one-line fix is in `apps/frappe`. Until it is made, **nobody should be told that HR can add a photograph in Desk** |
| **D2** | **§2.1's clear-text token.** Blocks step 6 and needs Surbhi's decision. Building pre-onboarding without settling it would ship a Restricted bearer credential in clear, for ever, against a SEC item she approved |

### Temporary debt - what removes it

| # | Thing | What removes it |
|---|---|---|
| T1 | `browser_check_positions.js` is re-pointed but **never executed** - no playwright here | One run with a browser against a rendered chart. It is also AC-34 and OPS-38, so it is one job |
| T2 | The **rest** of the `alvoraa_portal` and `hrms` suites is unverified against this branch | The test engineer's full run |
| T3 | **PRIV-3's static assertion is not written** - that `Employee.image` and the thumbnail field appear in no module under an AI or model path, and that nothing reads `alvoraa_checkin_photo` into `Employee.image` or the reverse. Three greps in a test | One test, ~20 lines. It is the only PRIV item for steps 1-5 that is not covered |
| T4 | AC-47's in-memory hold is built but has no test | One DOM case |

### Acceptable simplification

| # | Thing | Why |
|---|---|---|
| S1 | The seat page's address is **`?seat=…`**, not a route | `?grooming=` and `?who=` already do exactly this in `portal.js`. A second routing mechanism for one screen is not worth owning, and `portal.js` has no hash router |
| S2 | The Organisation page caps a seat at three names **with no way to see the rest** | It has no tray to hold them, unlike Positions. A count is the honest answer and the person can search. Flagged because it is a real, if small, loss |
| S3 | `get_cover_settings` now returns the five new keys to **HR Manager** as well as System Manager, because it is gated on both | A read of a setting's value, on an endpoint `01a` F16 measured as called by **no screen at all**. Writing is still System-Manager-only. Worth a line in the security review |
| S4 | The documents list is its own call, after the profile | A document read that fails or is refused must not take the profile with it |

### Intentional trade-off

| # | Thing |
|---|---|
| I1 | **`position_table` is 3 statements, not the 2 the spec required.** The extra one is flat in headcount at 13.4 ms, which is what the gate actually asserts. The alternative was a column on the HR master |
| I2 | **`people_fields.thumbnails_for` reads with `ignore_permissions=True`.** Frappe's own `File` query condition narrows a Website User to `owner = me`, so a scoped read would hide every colleague's thumbnail and the one chart a frontline employee can open would lose its faces. It returns a **url and nothing else**, and fetching the bytes behind it still asks the parent Employee's read permission - so it grants nothing. Declared in the ceiling test with that argument |
| I3 | **The mini profile shares `#emp-drawer` with the manager's detail drawer.** One element means one set of ARIA attributes, one Escape handler and one focus trap rather than two that drift. They never open at once and each fully replaces the head and body |
| I4 | **E14 / ⚠ DECISION K left as it is.** An import of 403 photographs is ~240 ms a row, about **1 min 40 s**, inside one import job. The release note should say that figure rather than "will be slow" |

---

## 10 · Subtract pass

Read back once, asking only: **what can I delete and still meet the
requirement?** On top of the nine things `00-impact-analysis.md` §10 removed.

**Removed while building - five things:**

1. **A contrived `_ = people_fields` line** in `employee_documents_read.py`,
   written to "document a relationship". It was noise, and worse: `from frappe
   import _` was already in that module, so it **shadowed the translation
   function**. Deleted, with the unused import.
2. **A second drawer element.** The mini profile shares the existing one.
3. **A second `IntersectionObserver`.** `ocFaces` is called from the chart, the
   table and the seat page.
4. **A second settings setter.** `set_people_setting` checks the key is one of
   ours and hands over to the access-granting path, so nothing about who may
   change these settings is decided twice.
5. **A `.emp-drawer{position:fixed}` rule** I had written redundantly, which
   would also have added a 27th entry to the fixed-element inventory for
   nothing.

**Not removed, and the reason, since the user should be able to judge:**

- **`repair_unsaveable_logins()`** could be deleted - the fixture would work
  without it once every record is sound. It stays because it is the remediation
  a real tenant needs, and burying it inside a fixture would lose it.
- **The two "recorded, not asserted" tests** (AC-69/AC-70, and §2.2's
  `TypeError`) look like tests that assert nothing useful. They are the only
  thing that will tell us the day Frappe fixes either path.
- **`spAbout`'s six facts** could come from the mini profile instead of from the
  row the chart already has. They stay local because a page that needs its own
  fetch to say "Cashier, Noida, 3 of 3 filled" is a page that can fail at
  saying it.

**What I did not manage to delete:** the ~1,100 new lines in `portal.js`. Every
block has its own prefix and its own one line in `switchPanel`, which is the
rule, but the file is 1.12 MB and this slice made it bigger. That is OPS-11's
standing debt and I did not quietly start fixing it.
