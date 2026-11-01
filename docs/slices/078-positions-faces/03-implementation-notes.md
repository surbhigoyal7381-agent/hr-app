---
slice: 078-positions-faces
artifact: 03-implementation-notes
author: hrms-fullstack-engineer
date: 2026-10-31
status: ALL SIX STEPS built, tested and committed LOCALLY. Surbhi settled the four open decisions on 31 Oct 2026 and the blocker in §2.1 is now a recorded deviation rather than a stop. Nothing pushed, no site setting changed, no deploy command run.
worktree: .claude/worktrees/078-positions-faces on slice/078-positions-faces, from origin/dev d3afcaa5
commits: a378af03 (step 1) · 38faec2f (2) · febf6ba3 (3) · 42a6671c (4) · a41912b8 (5) · dca34c19 (four bugs the tests found) · 851be6e8 (the Frappe fork patch) · 5bfe98bd (email opt-out, PRIV-3, AC-47) · c1059381 (step 6)
---

# 078 · Implementation notes

---

## 0 · The answer first

**All six steps are built, tested and committed locally.** Steps 1 to 5 went in
first; Surbhi then settled the four open decisions, and step 6 followed.

**Three things in this slice are not what the spec asked for, and each is a
decision rather than a miss.** They are §2.1 (the token's clear-text storage,
which makes AC-101 wrong as worded), §2.2 (an upstream bug, now patched in our
own image **and** worked around), and §5.4 (a used link is indistinguishable
from an unknown one, which makes AC-112 and AC-125 wrong as worded). Each says
plainly what the criterion would have to say instead.

**Three things found by RUNNING the code that reading it did not reveal.** All
three are in this report because each one would have shipped silently.

| # | What | Where it came from |
|---|---|---|
| **1** | **The 48 px copy was never made.** `File.get_content()` with no argument *decodes* what it read, and for a JPEG one of its encodings succeeds lossily, returning a `str` with bytes changed. `derive_thumbnail` then raised `UnidentifiedImageError`, was swallowed by its own "never fail an Employee save" guard, and left **no thumbnail for anybody** - with only an Error Log row. The chart would have fallen back to the full 512 px picture for every face: the ~720 KB first paint the derived copy exists to avoid. **Nothing would have gone red.** Fixed: `get_content(encodings=[])`, at three call sites | the first Python test run |
| **2** | **An employee adding their own photograph made their own record unsaveable.** Upstream: `frappe/core/doctype/file/file.py:795-796` fills `_content` with the decoding `get_content()`, and line 819 hands that `str` to `strip_exif_data`, which wants bytes. ERPNext's `Employee.update_user()` triggers it whenever `image` changed **or the linked User's `user_image` is empty**. The portal writes with `db.set_value`, so `user_image` stayed empty and **every later Desk save of that employee raised, for ever**. Mitigated in our own code (§2.2); the underlying fault is upstream and is an escalation | the second test run - it broke a whole test class's `setUpClass`, which is how the stickiness was noticed |
| **3** | **`Web Form Request.key` is a plain `Data` field, stored in clear.** Option (c) delegates the token to Frappe, and Frappe keeps the live bearer token in the clear in `tabWebFormRequest`, for ever - nothing purges it. So **078-SEC-9's bold "only its SHA-256 hash is stored" and AC-101 cannot both be true under option (c)**. **Settled by Surbhi on 31 Oct: option (c) plus a purge.** §2.1 | reading `web_form_request.json` in the running image before writing a line against it |
| **4** | **The not-hired retention clock was keyed on `modified`**, which moves on *any* later edit - so ticking legal hold and unticking it again would have restarted a 180-day clock. A dedicated `closed_on`, stamped once | a test that aged a row and watched it survive |
| **5** | **AC-47's "no second request" did not work.** It copied `held.src` onto a fresh `<img>`, which **is** a new request - and private files go out `Cache-Control: no-cache`, so the browser revalidates every time. It now puts the held element itself back | the test written to cover that debt, on its first run |
| **6** | **`frappe.get_all` ignores permissions by design.** A "Guest cannot list this" test using it passed while proving nothing. `frappe.get_list` is the one that checks | reading why it passed |

**What is in `dev`'s way: nothing.** Every default ships empty or off, and every
risky part reverses with data rather than a deploy. The one thing that is **not**
data is the Frappe patch in `deploy/Dockerfile` and `ci.yml`: it changes the next
image build, and it fails the build loudly if the line it edits has moved.

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

## 2 · ⚠ The three things that are not what the spec asked for

### 2.1 ⚠ DECIDED DEVIATION · the token's clear-text storage, and the purge

**Surbhi's decision, 31 October 2026: option (c) plus a purge.** This section is
here so the security reviewer reads a decision rather than discovering a gap.

**What Frappe does.** `Web Form Request.key` is `{"fieldtype": "Data",
"read_only": 1, "unique": 1}` - not a `Password` field, not hashed, not
encrypted - and the lookup is a direct comparison against the stored clear
value. **Nothing purges the row:** `Web Form Request` appears nowhere in
`frappe/hooks.py` and nowhere in Log Settings, and `first_used_on` only marks a
key used. The table ships `Website Manager`-only, which is the one mitigation
Frappe provides.

**So 078-SEC-9 cannot be met as written.** Its bold rule is *"only its SHA-256
hash is stored"*, and option (c) stores the key in clear. I take the gap: my
impact analysis §0.1 said Frappe "owns the key generation, expiry, single-use
burn" and did not check **how** it stores it.

**What is built instead.** The row holding the key is **deleted the moment the
key stops being usable** - on submit, on cancel, and by the daily job for an
expired one, all through one function (`joiner_invite._drop_request`) so the
three paths cannot drift. So a clear-text key exists only **while the link still
works**, never after. Four tests assert exactly that, in
`TestTheClearTextKeyIsShortLived`, and a fifth asserts our own row has no field
that could hold a token at all.

The half of SEC-9 that is kept in full is the half about where the token
travels: **URL fragment**, posted in a **request body**, under the parameter
name **`web_form_request_key`** - which is load-bearing, because Frappe's
error-snapshot redaction masks any form key whose name contains `key`, `token`,
`secret`, `password`, `passwd` or `pwd`. **Rename it and the redaction silently
stops**, so a test pins the name.

> **⚠ AC-101 IS WRONG AS WORDED.** It says *"No field equals the token in plain
> text."* What is built means: *"No field of OUR OWN holds the token in any
> form, and Frappe's own request row - which does hold it in clear - is deleted
> the moment the link stops working, so the clear-text value never outlives the
> live link."* **That is the criterion the test engineer should verify against.**
> I have not quietly re-pointed the old one.

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

**Surbhi's decision, 31 October 2026: patch it in our own image AND keep the
workaround.** Both, deliberately: the patch is the fix, and the workaround is
what protects any tenant running an image built before it.

`scripts/patch_frappe_binary_file_content.py` does the patch, and it runs in
`deploy/Dockerfile` and in `.github/workflows/ci.yml` - both, because CI testing
a Frappe that behaves differently from the one that ships is worse than not
patching at all. The patch file is in CI's bench cache key, so changing it
rebuilds the bench.

**It turned out to be three instances of one fault, not one.** I found the
first by running a test, and only found the other two when the patch did not fix
the symptom:

| in | the line | what breaks |
|---|---|---|
| `before_insert` | `save_file(content=self.get_content())` | **the one that bites** - this is ERPNext's path |
| `save_file` | `flags.original_content = self.get_content()` | a rollback would write a **corrupted** image over a good one |
| `optimize_file` | `original_content = self.get_content()` | `optimize_image()` is handed a `str` |

Reading the code found one of three. Running it found the rest.

**The test now asserts both ways**, detecting the fix by reading
`File.before_insert`'s source for `encodings=[]` rather than looking for our own
marker comment - so it is also true the day upstream fixes it their own way,
which is the point of reporting it. Proved on a throwaway container from the
shipping image, unpatched and patched: unpatched it asserts the `TypeError`,
patched it asserts the Desk save **works** and makes the 48 px copy, which is
**AC-25b in full**.

#### 2.2.1 The upstream report, for somebody to file

I have not filed it - that was not mine to do. Everything needed is here.

> **Title:** `File.get_content()` decodes binary files, breaking EXIF strip,
> rollback and image optimisation
>
> **Where:** `frappe/core/doctype/file/file.py`, three callers of
> `self.get_content()` with no `encodings` argument.
>
> **What happens:** `get_content()` loops over `FILE_ENCODING_OPTIONS` and
> returns a `str` as soon as one does not raise. For a JPEG, a PNG or a PDF one
> of them succeeds **lossily** - a stored JPEG came back with its first four
> bytes altered, so Pillow could not identify it. Then:
> (1) `before_insert` passes that `str` to `save_file(content=...)`, which puts
> it in `_content`, and `strip_exif_data` raises `TypeError: a bytes-like object
> is required, not 'str'` whenever `strip_exif_metadata_from_uploaded_images` is
> on (the default);
> (2) `save_file` puts it in `flags.original_content`, and `on_rollback` writes
> it back to disk choosing `"w+"` for a `str` - corrupting the file it was
> restoring;
> (3) `optimize_file` passes it to `optimize_image(content=...)`.
>
> **How to reproduce (1):** on a site with the strip setting on, insert a `File`
> with a jpeg; then insert a second `File` carrying only `file_url` pointing at
> it. ERPNext reaches this from `Employee.update_user()` whenever an employee's
> `image` changes or the linked User's `user_image` is empty - so **adding an
> employee photograph in Desk raises**, and because each failure leaves
> `user_image` empty it then raises on every later save of that employee.
>
> **Fix:** `get_content(encodings=[])` at all three. The decode loop's body then
> never runs. `on_rollback` already handles `bytes` (`"wb+"`), so nothing
> downstream needs changing.
>
> **Version:** found on v16.33.1, lines unchanged through the v16.35.0 we ship.

### 2.3 OPS-41 - what is left of it

DevOps asked me to re-read `web_form.py` and `web_form_request.py` on
**v16.35.0** before writing against them. I could not:
`hrlocal-bench`'s frappe checkout knows **only `v16.33.1`** (`git tag --list`),
and fetching v16.35.0 into the shared container would change another session's
bench. **Everything in §2.1 is read on v16.33.1 and is marked as such.**

**One signature, not two.** The build does **not** call Frappe's `accept()` at
all - see §3A.2 - so `accept(web_form, data, web_form_request_key=None)` does
not need confirming. The only call into Frappe's token machinery is
**`WebForm.get_web_form_request(key, *, docname=None, for_update=False,
allow_used=False)`**, used with `for_update` and `allow_used`. That one
signature on v16.35.0 is all that is left of OPS-41.

---

## 3 · Every acceptance criterion, and the ones I could not satisfy

### 3.1 Satisfied

| AC | How |
|---|---|
| AC-1, AC-7 | The picture card is first in `#panel-my-profile`, with the initials circle, the heading, the sentence, both ≥ 44 px buttons and the "we make it smaller" line. Replace/Remove once a photograph exists |
| **AC-2** | `myp-notice` is **before** the control in the DOM. Asserted by `compareDocumentPosition`, not by reading the source |
| AC-3 | `is_private = 1`; the stored size is logged and checked against a 120 **KB** ceiling (see AC-3a below) |
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
| **AC-25b** (Desk upload makes the copy) | **SATISFIED, once the Frappe patch is in the image** | §2.2. The handler was always on `Employee.on_update`; ERPNext raised before it ran. The patch fixes that, and the test asserts the working behaviour on a patched bench and the `TypeError` on an unpatched one, so it is honest on both |
| AC-34, OPS-38 (count faces on dev) | **Not done** | It is a read of dev. Not mine to do, and release-stage |
| AC-39 (wall-chart photo tick) | **Not built** | ⚠ DECISION C's second half. `ocFacesAllNow()` and the `.pos-print-faces` rule are in and tested, so the tick is ~10 lines on slice 069's dialog - but it is slice 069's dialog, and faces are off on Ctrl+P either way |
| AC-47's in-memory hold | **Built and asserted - and it was BROKEN** | The test written to cover this debt caught it making two requests instead of one, because it copied the `src` onto a fresh `<img>`. It now reuses the held element. §0 #5 |
| AC-72 (`max_file_size = 5`) | **Not done, deliberately** | A per-site setting, Surbhi's word at release. **Not mine** |
| **AC-3a** - the spec's `p95 ≤ 50 KB` (**referenced as AC-72a until 31 Oct 2026; that id was never issued. The spec now carries this as AC-3a**) | **Changed to a record, per OPS-42** | DevOps measured a worst case at **82 KB** through these exact parameters. 50 KB is a good target and a bad assertion: it fails a build on one employee's busy photograph. The build ceiling is **120 KB** and the real size is logged on every upload |
| AC-100 to AC-135 (pre-onboarding) | **Built.** 42 tests | §3A |
| **AC-101** | **Built differently.** The criterion is wrong as worded | §2.1 |
| **AC-112, AC-125** | **Built differently.** Both are wrong as worded, and the build is stronger than they ask | §3A.4 |
| AC-103, AC-104 | **Built as DevOps re-worded them**: both switches asserted still OFF, because our own endpoint does the uploads | §3A.2 |
| **AC-141's Hindi half** | **Cannot be done in this repository** | Every new string goes through `drT()` - that half is done and checkable. But **there is no Hindi file anywhere in this repo**: `translations/` holds only `en.csv`, which exists for the Alvoraa → Alvora rename. Hindi is a site-level `Translation` import, so "has a Hindi entry" is not something a commit here can satisfy. Flagged rather than quietly skipped |
| AC-142, AC-143 | **Not checked** | Needs a rendered page in Hindi |

---

## 3A · Step 6, pre-onboarding - and four mechanism choices worth checking

### 3A.1 What is built

| Piece | File |
|---|---|
| The one new DocType, 26 fields, **no Guest permission row** | `.../doctype/alvoraa_joiner_submission/` |
| HR's side: invite, cancel, Export, Purge | `joiner_invite.py` |
| The joiner's side: three token-bound endpoints | `joiner_public.py` |
| The daily job: expire, three erase clocks, the day-75 warning, the invariant | `joiner_housekeeping.py` |
| The public page, everything inline | `www/joiner.py`, `www/joiner.html` |
| HR's three buttons, in Desk | `public/js/alvoraa_joiner_submission.js` |
| Five settings keys | `alvoraa_org_structure/settings.py` |
| 42 tests | `tests/test_joiner_078.py` |

### 3A.2 Four mechanism choices, each cheaper than the plan

**1. Frappe's `accept()` is not called, and its form is never published.**
Option (c) needs Frappe's `Web Form Request` as the token store and validator -
and that is a method on a `Web Form` doc, so one `Web Form` record has to exist.
Ours is **`published = 0`**, and nothing of Frappe's own form is ever served.

That single choice removes three things the impact analysis worried about: the
**query string** (no Frappe route renders, so there is no `?web_form_request_key=`
anywhere), `accept`'s **shared 10-per-60-seconds rate bucket** across every web
form on the site, and `accept`'s generic `doc.insert(ignore_permissions=True)`
on a guest-writable path. We write our own row with our own closed field list, so
PRIV-9's allow-list is a constant in our code rather than a Web Form's field
table.

One consequence to check: the anchor record is **found by `doc_type`, never by a
guessed name**. Frappe autonames a Web Form from its title, so looking it up by
title collided with its own row on every call after the first - which is how 28
tests failed at once.

**2. The guest-upload switch stays off.** Our own token-checked endpoint does
the uploads, so `allow_guests_to_upload_files` never has to go on and the
allow-list stays empty. **AC-103 and AC-104 are therefore assertions that both
are still off** (DevOps OPS-40), which is cheaper and stronger than a procedure
for opening a site-wide hole carefully. Frappe's own
`test_guest_upload_for_empty_whitelist` is why that matters: the switch on with
an empty list lets a guest attach a file to **any** doctype.

**3. HR's screen is the Desk form, not a new portal page.** Three buttons via
`doctype_js`: make the link, cancel it, and counsel's Export and Purge. HR
reviews a submission there anyway and HR Manager already has Desk, so a second
screen would be a surface before an answer. **This is a deviation from the
spec's "HR's own screen"** - said plainly, because it is a UI decision somebody
may want differently.

**Nothing creates an Employee.** There is no button and no endpoint: HR makes
the personnel record by hand, then links it on this form, and the controller's
own `validate` moves the status on. Declarative, so there is nothing to press by
accident and no endpoint that could be called with somebody else's id. A test
asserts no `Employee` row appears and the naming series does not move; another
asserts **no field with "joining" in its name exists on the row at all** - the
absence-backfill trap is a logged DTC fault, not a theory.

**4. The erase leaves a shell, and that is a judgement.** `erase()` clears every
field the joiner typed and **deletes the uploaded files, bytes included** - a
parent that keeps its `File` rows is the obvious way to get this wrong, and
those files are identity documents. What survives is the status, who issued the
link, the dates and the Employee link: **no personal data at all.**

Counsel said there is no reason to hold the data, and this holds none of it;
§15 of the spec promises that "who issued a joiner's invite" is answerable a
year later, and this is what answers it. **A reviewer may reasonably want the
row deleted outright** - it is one line either way, and the choice is recorded
here rather than buried.

### 3A.3 Counsel's clocks, as built

| Case | Erased when | Setting | Default |
|---|---|---|---|
| They joined | next run - the details are already their Employee record | — | — |
| They did not join | the window after the invite **closed** | `alvoraa_joiner_not_hired_days` | **180**, range 180-365 |
| Nobody actioned it | the backstop after it **arrived**, whatever state it is in | `alvoraa_joiner_backstop_days` | **90** |
| Before that happens | HR is told, once | `alvoraa_joiner_warn_days` | **75** |
| The link itself | expires, and the key's row is destroyed | `alvoraa_joiner_link_days` | **7** |

**The not-hired clock runs from `closed_on`, not from `modified`.** A test
caught that: `modified` moves on *any* later edit, so ticking legal hold and
unticking it again would have restarted a 180-day clock. `closed_on` is stamped
once, by the controller, when the status first becomes terminal.

**No setting has a value that means "keep for ever".** A blank and a `0` are
both refused at every one of the three - the opposite of `field_app_photos`'
`0 = never delete`, and the one thing counsel's 18 September policy rules out in
so many words. The setter also refuses a warning that is not **before** the
deletion it warns about, checked against what is stored, so changing either one
in either order cannot leave them crossed.

**The old `alvoraa_joiner_retention_days` key is deleted.** It existed to be a
number nobody had chosen, which is why PRIV-7 gated switching the form on until
somebody set it deliberately. Counsel replaced it with two periods that mean
different things, so one key could not carry both - and a key nothing reads is
dead configuration.

**078-PRIV-7's switch-on precondition is gone**, per that decision. The form is
still **off by default**, for the ordinary reason: a tenant turns a feature on
deliberately.

### 3A.4 ⚠ Two more acceptance criteria that are wrong as worded

**AC-112 and AC-125** want a narrower *"already used"* answer, and
*"This link will not open again"* on a second visit. **The build cannot give
them**, because the purge in §2.1 deletes the row holding the key the moment it
is used - so afterwards a used key is simply an unknown key and there is nothing
left to recognise.

The purge wins. 078-SEC-13 is satisfied **more strongly** than it asks: missing,
unknown, expired, cancelled **and used** are one byte-identical answer, asserted
across six inputs. The joiner is not left in the dark either - the answer says
*"nothing you sent is lost"*, which is true, and J6 told them at the time that
the link would not open again.

**What those criteria should say:** *"A used link gives the same answer as an
unknown one, because the row holding its key has been destroyed."*

### 3A.5 What is NOT built in step 6

| Thing | Why |
|---|---|
| **A Hindi version of the joiner's page** | The page's strings are plain English in the HTML, **not** wrapped in `drT()`, because it is a standalone public page that does not load `portal.js`. **That is a real gap and the worst one in step 6**, because this page is for a frontline joiner. Wrapping them needs Frappe's own `_()` in the Jinja and a site-level Hindi import, which is the same missing piece as AC-141 everywhere else |
| An email to HR when a joiner submits | ⚠ DECISION H, recommended and not overruled: HR issued the invite and is watching for it, and an email naming a joiner is one more place a non-employee's data travels. The day-75 warning uses `Notification Log`, which the portal's bell already reads, for the same reason |
| A browser check of the joiner's page | No playwright here. **The page has never been rendered in a browser** |

## 4 · The seven non-functional dimensions, re-assessed against the code I wrote

Not against the proposal. Where the code turned out different from §3 of
`00-impact-analysis.md`, the row says so.

| Dimension | Before | After | Verdict |
|---|---|---|---|
| **Performance** | the chart read one `get_value` per person per box per expansion; `position_table` was 2 statements | `_card` is **two statements for a whole subtree**, memoised per request, so a person drawn in two boxes costs nothing twice. `position_table` is **3**, not the 2 the spec asked: the third is the batched thumbnail read, 13.4 ms for 403 ids, flat in headcount. First paint is **~10 KB of faces**, not the 48 KB estimated - DevOps measured the 48 px copy at 0.4-0.7 KB. The table and a filtered chart are bounded by our own observer. The one real cost is **~240 ms of CPU in the uploader's own request**, which is the first time this product has spent a quarter of a second of CPU in a user request | **IMPROVES** on the chart, which is the opposite of what the analysis predicted. The proposal said "degrades, bounded on purpose"; the measurements and the batching turned it round. The upload's 240 ms is the honest cost |
| **Scalability** | one read per person, growing with headcount | flat in headcount on every new path; the query-count gate asserts 20 ids and 400 ids cost the same. **ONE scheduled job** - the daily joiner erase, which 078-PRIV-6 names - and no queue, no worker, no cache, no bucket, no CDN and no container. The 48 px copy is 4 ms inside the request, which is the number that says no job | **IMPROVES** |
| **Security** | — | **Six** new permission surfaces, as the analysis predicted, and the sixth is the one it called the honest degradation: the photo upload (own Active record, **no employee argument exists**), the My-Profile save (closed list ∩ ticked), the mini profile (`may_view` + `employee_in_scope`), the documents endpoint (five ordered checks, scope **before** ticked-type), the settings setters (`ACCESS_GRANTING`, System Manager only), and **the first public write path in this product's history**. Against that: no Frappe form is ever published, so there is no route that can put a token in a query string; the site-wide guest-upload switch **stays off**; a stranger gets one byte-identical answer to six different wrong inputs; and Frappe's own token row is destroyed the moment the link dies. 18 `ignore_permissions`, every one declared and argued in the ceiling test. No new scope helper. No `has_permission` hook | **DEGRADES, knowingly, as predicted.** The public write path is real and is the thing to review hardest. R1 stands exactly as accepted |
| **Reliability** | My profile threw a 500 for a login with no Employee row | **Fixed**, and three more: the thumbnail handler catches everything and can never fail an Employee save; `ocFaces` is guarded, because it is called after every paint and would otherwise have been the thing that took a paint down (found by running a check); and **`_keep_the_login_in_step` stops an employee's own upload making their record unsaveable** (§2.2). Step 6 adds four more: the public page shows a plain "this link has run out" rather than a failure; a failed upload never discards what was typed and always offers a way forward that is not "try again"; the erase catches per row so one bad file cannot stop the job; and the daily job is safe to run twice | **IMPROVES**, and by more than the analysis claimed |
| **Maintainability** | — | ~45 new server functions across 11 modules, 6 test modules, one new DocType, one DocType JSON change, ~1,100 new lines of `portal.js` and a 440-line standalone public page. Holding it: `ocAvatar` changed **once** for five states and three callers; **one** mini-profile field list, asserted; **one** `ocFaces`; the settings card reads its words from the drawer's array so a rename cannot leave the two disagreeing; no new abstraction and no base class; one `_drop_request` for the three places a token dies; one `erase` for the four reasons a submission is erased | **DEGRADES**, more than the analysis predicted - step 6 is a third of the slice's code and all of it is new |
| **Data integrity** | — | No schema change to `Employee`, no migration, no patch, no backfill. **One new table**, which `bench migrate` creates; two nullable columns on an existing one. `invalidate_portal_context_cache` is already first in the `on_update` chain, so a photo change busts the 1-hour cache that carries `image`. Replacing or clearing a photograph deletes the old rows **and their bytes** - the old rows are noted first and deleted **last**, so a failed store never takes away the picture somebody had. The access log's new `source` defaults to `Check-in photo`, correct for every row written before this slice | **NEUTRAL** |
| **Compliance / privacy** | — | PRIV-1's notice is **before** the control, names appraisals, and now states **what the tenant configured** about email rather than a fixed claim. PRIV-2's removal takes the bytes. PRIV-3 has a static assertion over the real tree. PRIV-4: the mini profile is its own call and no personal field joined `position_table`. PRIV-5's record holds no file, url, document number or value. PRIV-6: three erase clocks, all settings, **none with a value meaning "keep for ever"**, real deletion including the files, legal hold winning. PRIV-8: the notice before the first question, with the configured numbers and a contact the screen **refuses to render without**. PRIV-9: a seven-field closed allow-list, no bank, salary or statutory field. Every list and the form itself ship **empty or off**. Counsel's three additions are in: the email opt-out, the upload timestamp, and Export and Purge with the files | **DEGRADES, and it is still the dimension to argue about.** The trigger for 24 surfaces to show faces is created, and strangers are now invited to upload identity documents at a tenant that switches it on. Four things make it defensible and all four are built; the fifth - a Hindi joiner page - is not

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
| `python scripts/check_app_integrity.py` | **881 checks, OK** |
| `python scripts/check_scope_traps.py` | **OK** - no caller's id can replace a scope |
| `python scripts/check_api_paths.py --max 0` | **OK**, 0 unresolved of 281 paths |
| `python scripts/check_portal_assets_gate.py` | **OK** - no new asset file, so nothing to add to the deploy step |
| `python scripts/check_tag_balance.py` | **OK** - both pages balance after the seat-page restructure |
| `python scripts/check_design_system.py` | **OK** - it **failed first** on two raw `font-size` values I had written; fixed with tokens rather than by raising the limit |
| `python scripts/check_brand_spelling.py` | **OK** - it **failed first**, on two real hits in step 6, and was right about both |
| `python scripts/check_version_pins.py` | **OK** - no pin changed |
| `node scripts/check_undefined_js.js` | **OK** - no undefined identifier |
| `node scripts/check_portal_trays.js` (static half) | **OK, 27 of 27 in INVENTORY** - it **failed first** on the new picker's backdrop, which is the gate working |
| `node scripts/check_positions_tree.js` | **404 checks** |
| `node scripts/check_wall_chart.js` | **225 checks** - nothing private reaches paper |
| `node scripts/run_dom_tests.js` | **20 run, 0 not run, 0 failed.** The 078 test alone: **116 assertions, 0 failed** |

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
| `test_my_photo_078` | **34 tests, OK** - run on an unpatched AND a patched Frappe |
| `test_faces_078` | **8 tests, OK** |
| `test_mini_profile_078` | **12 tests, OK** |
| `test_people_settings_078` | **22 tests, OK** |
| `test_employee_documents_078` | **20 tests, OK** |
| `test_joiner_078` | **42 tests, OK** |
| `test_portal_security_010` | the `ignore_permissions` ceilings, with a row for each of the eleven new files |
| **total** | **138 tests across six modules, 0 failures, 0 errors** - one clean SERIAL pass. Two processes on one site clash on shared fixtures, which cost two confusing red runs before I stopped running them in parallel |

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
| **Not-hired retention: 180 days, range 180-365** | **Built**, keyed on `closed_on` rather than `modified` - see §3A.3 |
| **Unactioned backstop: 90 days, HR warned at day 75** | **Built.** The warning uses `Notification Log`, which the portal's bell already reads, rather than an email |
| **⚠ COMPLIANCE 2 closed by counsel** | **Closed 29 Oct 2026 (counsel), defaults approved 31 Oct 2026 (Surbhi).** PRIV-7's switch-on precondition is **not built**, per that decision; the form is still off by default for the ordinary reason |
| **Export and Purge on a submission, contact footer on the joiner's form** | **Built.** Both as Desk buttons under a "Their rights" group; the footer is on the joiner's page and carries **the employer's** contact details, never ours. Purge takes the files and **ignores legal hold**, because there the erasure is the obligation rather than the risk |
| **Photo upload timestamp for audit** | **BUILT.** The upload and removal log lines carry `now()` |
| **An admin setting to keep photographs out of company-wide emails** | **BUILT.** One access-granting settings key, one Jinja method that fails closed, and our own copies of hrms' two reminder templates with ONE condition changed - sha-pinned in the format `check_email_template_overrides.py --check-upstream-shape` parses, and verified with that script's own hashing against the vendored hrms, which is the file CI copies into its bench. **OFF by default**, which is a deliberate change to what the product does today: nothing visible changes on the day it ships because no employee has a photograph, and email is the one place the safe default is worth a changed behaviour. The override wins the template search because Frappe's Jinja loader searches installed apps in REVERSED install order - read from `_get_jloader`'s source, then **proved by asking the loader itself** in a test rather than trusting the reading. It had to be a template override and not a wrapper, because `send_work_anniversary_reminders` is a scheduler entry in `hrms/hooks.py`, which `override_whitelisted_methods` cannot reach. PRIV-1's notice now states what the tenant configured, and BOTH halves are asserted - because claiming mail when there is none is wrong too |

### 8.1 ⚠ For whoever writes the Processor agreement

**Flagged deliberately, and NOT fixed in code. Surbhi approved all five
defaults and they are not being changed.**

Counsel's framing is that **our customers are the Data Controllers and we are a
Data Processor**: our job is the tools, the notices and the settings, and the
Controller decides its own periods. The build follows that exactly - every
period in this slice is a configurable setting and not one of them is
hard-coded.

But **"the employer sets its own periods" and "we ship a default" are not the
same sentence**, and this slice ships five values no tenant has chosen:

| Setting | Ships at | Chosen by |
|---|---|---|
| `alvoraa_joiner_link_days` | 7 | us |
| `alvoraa_joiner_not_hired_days` | 180 | us, from counsel's 180-365 range |
| `alvoraa_joiner_backstop_days` | 90 | us |
| `alvoraa_joiner_warn_days` | 75 | us |
| `alvoraa_photo_in_emails` | off | us |

Until a Controller changes one, **the Processor's default is what is
operating.** That is the right engineering answer - the alternative is a feature
nobody can switch on until four boxes are filled in - and it is exactly the kind
of thing a Processor agreement should say out loud: either that the Controller
is taken to have adopted the defaults by switching the feature on, or that it
must set them before first use.

**Two of the five are more than conveniences.** The 90-day backstop **deletes
data**, and the email default **changes what the product did yesterday**. Both
are defensible, and both are recorded here with Surbhi's name and 31 October
2026 against them, which is the most the code can do. The contract is where it
has to be settled.

---

## 9 · Known gaps and shortcuts, each labelled

### Dangerous debt - escalate now

| # | Thing |
|---|---|
| **D1** | **The Frappe fork patch is now the only thing standing between HR and a broken Desk upload** (§2.2). It is applied in `deploy/Dockerfile` and in `ci.yml`, **and it has never been through a real image build** - only a throwaway container. If the build fails, the script says which line it could not find; if somebody removes the step, the bug comes back silently for any employee whose `user_image` is empty. The workaround in `employee_photo` stays for exactly that reason. **Nobody should be told HR can add a photograph in Desk until an image built from this commit has been seen to work.** |
| **D2** | **The joiner's page has never been rendered in a browser.** It is 440 lines of inline HTML, CSS and JavaScript on the one public page in this product, used by people who cannot ring our helpdesk. Every endpoint behind it is tested; **the page itself is not.** That is the single biggest untested surface in the slice. |

### Temporary debt - what removes it

| # | Thing | What removes it |
|---|---|---|
| T1 | `browser_check_positions.js` is re-pointed but **never executed** - no playwright here | One run with a browser against a rendered chart. Same job as AC-34 and OPS-38 |
| T2 | The **rest** of the `alvoraa_portal` and `hrms` suites is unverified against this branch | The test engineer's full run. Only my six modules ran |
| T3 | **The joiner's page is not translated.** Its strings are plain English in the HTML, not wrapped, because it is a standalone page that does not load `portal.js` | Frappe's own `_()` in the Jinja, plus the same site-level Hindi import AC-141 needs everywhere else |
| T4 | `_hr_contact()` reads two `DefaultValue` keys (`alvoraa_hr_contact_phone`, `alvoraa_hr_contact_email`) that **no screen sets** | One row on the settings card. The welcome screen refuses to render without a contact, so a tenant switching the form on finds out immediately rather than a joiner finding out - but it is a sharp edge |
| T5 | OPS-41: `get_web_form_request`'s signature is confirmed on **v16.33.1**, not the **v16.35.0** we ship | Read that one method in a container built from the shipped image. §2.3 |

### Acceptable simplification

| # | Thing | Why |
|---|---|---|
| S1 | The seat page's address is **`?seat=…`**, not a route | `?grooming=` and `?who=` already do exactly this in `portal.js`, which has no hash router |
| S2 | The Organisation page caps a seat at three names **with no way to see the rest** | It has no tray to hold them, unlike Positions. A count is the honest answer |
| S3 | `get_cover_settings` now returns the new keys to **HR Manager** as well as System Manager | A read of a setting's value, on an endpoint `01a` F16 measured as called by **no screen at all**. Writing is still System-Manager-only. Worth a line in the security review |
| S4 | The documents list and the joiner's documents are each their own call | A document read that fails or is refused must not take the screen with it |
| S5 | **HR's joiner screen is the Desk form**, not a portal page | §3A.2. A deviation from the spec's wording, and the cheapest rung |
| S6 | The erase **leaves a shell** with no personal data rather than deleting the row | §3A.2 item 4. A judgement, and a reviewer may want it the other way |

### Intentional trade-off

| # | Thing |
|---|---|
| I1 | **`position_table` is 3 statements, not the 2 the spec required.** The extra one is flat in headcount at 13.4 ms, which is what the gate actually asserts. The alternative was a column on the HR master |
| I2 | **`people_fields.thumbnails_for` reads with `ignore_permissions=True`.** Frappe's own `File` query condition narrows a Website User to `owner = me`, so a scoped read would hide every colleague's thumbnail and the one chart a frontline employee can open would lose its faces. It returns a **url and nothing else**, and fetching the bytes behind it still asks the parent Employee's read permission |
| I3 | **The mini profile shares `#emp-drawer`** with the manager's detail drawer. One element means one set of ARIA attributes, one Escape handler and one focus trap rather than two that drift |
| I4 | **E14 / ⚠ DECISION K left as it is.** An import of 403 photographs is ~240 ms a row, about **1 min 40 s**, inside one import job. The release note should say that figure rather than "will be slow" |
| I5 | **The clear-text token window is "while the link works" rather than "never".** §2.1. Surbhi's decision, and the alternative was re-implementing Frappe's token machinery |
| I6 | **A used link is indistinguishable from an unknown one.** §3A.4. Stronger than SEC-13 asks and weaker than AC-112's wording; the purge wins |

### Three acceptance criteria that need rewording before the test engineer runs

Said here together, because a reviewer should not have to find them separately.

| AC | As worded | What is built |
|---|---|---|
| **AC-101** | *"No field equals the token in plain text."* | No field **of ours** holds it in any form; Frappe's own row does, in clear, and is **deleted the moment the link stops working** |
| **AC-112** | a used link *"may say already used"* | It cannot. A used link gives the **same** answer as an unknown one, because the row holding its key is gone |
| **AC-125** | *"This link will not open again"* on a second visit | Same reason. J6 says it at the time; a second visit gets the generic answer, which still says *"nothing you sent is lost"* |

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

**Removed in the second half - five more:**

6. **The hand-built token, finally and completely.** Step 6 generates no key,
   stores no hash and has no `Waiting/Used/Cancelled/Ran out` state machine of
   its own. Our doctype has **no field that could hold a token**, and a test
   asserts that by name.
7. **Frappe's `accept()`, and with it its form, its route, its query string and
   its shared rate bucket.** The anchor record is unpublished and nothing of
   Frappe's own form is ever served.
8. **The guest-upload switch, and the release step that would have turned it
   on.** Our own endpoint does the work, so the site-wide hole is never opened
   and AC-103/AC-104 became assertions that it is shut.
9. **The `alvoraa_joiner_retention_days` key**, which after counsel's answer had
   no reader. A key nothing reads is dead configuration.
10. **A second portal screen for HR.** Three buttons on the Desk form they
    already use.

**And one thing I deleted twice, because the first attempt was wrong:** a broad
`canvas` ban in PRIV-3's static test. It failed on the check-in camera, which
legitimately captures a selfie, so it became a ban on the DOM-to-image
libraries everywhere plus a ban on canvas export in the files that draw the
chart. A rule nobody can keep is worse than no rule.

**What I did not manage to delete:** the ~1,100 new lines in `portal.js`. Every
block has its own prefix and its own one line in `switchPanel`, which is the
rule, but the file is 1.12 MB and this slice made it bigger. That is OPS-11's
standing debt and I did not quietly start fixing it.

---

## 11 · The defect fixes, 31 October 2026 — after the test report

`04-test-report.md` returned **Fail**. Surbhi decided two things before this
work started: **a joiner's personal data is tenant-side**, and **all the
remaining defects are to be fixed, including the four prototype-parity gaps,
built as drawn.** This section is what I did about each one, on
`slice/078-positions-faces` in the worktree, five commits, nothing pushed.

### 11.1 What is fixed

| # | Fix | Where | Rung |
|---|---|---|---|
| **D-1** | `Alvoraa Joiner Submission` is named in `TENANT_DOCTYPES`, with the comment saying why: the tenant's own record about a person it is hiring, read and written inside the tenant by its HR. Its three Link fields — `User`, `Employee`, `Web Form Request` — were checked and none widens the derivation, so no further guard | `subscription.py` | **configuration** — one line on an existing list |
| **D-2** | The arguments gate now **reads the raw-fetch shape** instead of excusing it | `tests/test_browser_call_args_045.py` | **new code in a test** — see 11.2 for why not `NO_ARG_CALL` |
| **D-3** | An empty submission is refused **before** the key is burnt and before the row that holds it is purged, so the link still works and the joiner can send again. The browser checks the same thing first | `joiner_public.py`, `www/joiner.html` | **new code** — the cheapest rung that exists; no `reqd` was added, see 8.3 |
| **D-5(a)** | A name in the **seat tray** opens the mini profile | `portal.js` `posSeatSheet` | **customisation** — the same markup the other two surfaces already emit, picked up by the one delegated handler |
| **D-5(b)** | **J4, the photo screen**, built: optional, skippable, and it travels through the existing documents endpoint under one reserved type name | `www/joiner.html`, `joiner_public.py` | **new code** — but see 11.4: no fourth guest endpoint, no new DocType field |
| **D-5(c)** | `my-docs-card` **moved** out of `#panel-home` into `#panel-my-profile`, between the details and the password | `templates/includes/ess/parts/home.html` | **already there** — the card is unchanged; only its place moved |
| **D-5(d)** | The enlarged photograph closes when the pointer leaves both it and the photo; a **click pins** it | `portal.js` | **customisation** — one `mouseout` listener, one boolean and one 260 ms grace timer, for the reason in 11.4a |
| **D-6** | The picker's laptop footer renders **Preview · Cancel · OK** | `portal.js`, `panels.css` | **configuration** — DOM order plus one `order` rule |
| **D-7** | `context.joiner_on` deleted | `www/joiner.py` | **deletion** |
| **P4** | `test_the_stored_file_is_private` now asserts privacy on the **48 px** copy too | `tests/test_my_photo_078.py` | **new code in a test** |

### 11.2 D-2 — why the report's own suggested fix was not taken

The report said: add the endpoint to `NO_ARG_CALL` with a reason. One line,
and the suite goes green.

**I did not do that, and this is the reason.** That gate exists because
`next-inbox.js` sent `{name, action, reason}` to `action_leave(leave_id,
action)` — Frappe drops what a function does not declare, so every Approve and
Decline failed for two months and nothing went red. An entry in `NO_ARG_CALL`
would have made CI green while leaving **a new endpoint on the documents path
permanently outside the check**, which is the exact hole the gate was written
to close.

So the reader was taught the shape instead:

```
fetch("/api/method/<literal alvoraa_portal path>", { ... body: JSON.stringify({ ...keys... }) })
```

The one thing to know about that shape: **the arguments are not the second
argument**, as they are for every helper. The second argument is `fetch`'s own
options, and the names the server sees are the keys of the object inside
`JSON.stringify` in its `body`. One new call site is found, and
`open_employee_document` is now checked: the browser sends `{ row }`, the
server declares `open_employee_document(row=None)`.

A fetch whose **path** is built at run time — `next-frame.js:281`,
`portal.js:13792` — names no endpoint to read, and every endpoint reached that
way already goes through a helper shape the reader does read. The docstring now
says six shapes, not five, and the "What this does NOT cover" list names the
dynamic-path case by file and line, so the file still describes itself honestly.

`MIN_CALL_SITES` **200 → 201**, up by the one site found. Never down. Measured
today: **226 sites read, 0 orphans.**

### 11.3 D-3 — the rule, and what I deliberately did not add

The defect was irreversible for the person it happened to, which is why it was
labelled dangerous debt. Tapping Start → Next → Next → Send with nothing typed
reached J6. `submit_invite` set `status = "Submitted"` and then called
`_drop_request`, which destroys the `Web Form Request` row holding the key — so
the page's *"This link will not open again"* was true, HR got a blank record,
and the joiner had no route back.

Both of those now happen **after** the check, so a refusal leaves `status` at
`Invited` and the key's row untouched. `get_web_form_request` does not set
`first_used_on` — I read Frappe's own source to confirm it, because the whole
fix rests on it — so nothing else burns the key either.

**The rule is the spec's new AC-110c and nothing more: one field with a value,
or one document.** Surbhi's standing decision holds — HR ticks the field list
and we impose no restriction on top of it. So:

- **No `reqd` was added to any joiner field**, and a test reads that off the
  DocType meta rather than off the prose, so a `reqd` added later fails;
- `full_name` is **not** treated as mandatory. The spec's §21 names it as the
  one row to change if Surbhi wants it always required;
- the browser's check is the same rule, and it stays on **J5** with every box
  still holding what was typed, which is what AC-110a asks for. I built it at
  J2's Next first and **removed that**, because documents alone are a valid
  submission and blocking Next would have been our restriction, not HR's;
- the refusal the joiner reads on a round trip is **the server's own sentence**,
  parsed out of `_server_messages`, never "check your connection". That path
  already existed and I left it alone.

### 11.4 D-5(b) — J4 without a fourth public surface

J4 needed somewhere to put a photograph. The ladder:

- **a new guest endpoint** — rejected. §7.3 of the test report confirms three
  `allow_guest` endpoints and no more, and AC-126 asks for them to stay
  enumerable. A fourth public write surface for one optional picture is the
  most expensive thing in the slice;
- **a new field on the DocType** — rejected. AC-108c only asks that the picture
  be held *on the submission row, never on an `Employee`*, and a `File`
  attached to that row already is;
- **the existing `upload_invite_file`**, with one reserved type name. Taken.

So `PHOTO_TYPE = "__photo__"` goes through the same endpoint: the same token
check first, the same per-file and per-token ceilings, the same magic-byte
check, the same private `File`, the same re-encode that strips the metadata.
The only two differences are the edge and the refusal:

- **512 px at quality 82, read off `employee_photo.STORED_EDGE` and
  `STORED_QUALITY`** rather than typed again, so the joiner's face and a member
  of staff's face are one treatment and cannot drift apart (AC-108c);
- a PDF, or anything Pillow cannot read, is refused with
  `employee_photo._refused_type_message()` — AC-4's own words. The documents
  refusal offers *"I will bring it on my first day"*, which is no answer to a
  photograph.

It cannot collide with a real document type: a type is named by its own title,
and `__photo__` is not a title. A test asserts that rather than assuming it.

### 11.4a D-5(d) — why there is a timer, which the design did not ask for

The plain rule — close on the first `mouseout` from both elements — **does not
work**, and I found it by reading the geometry rather than in a browser, which
is the honest provenance.

`.emp-drawer-head` is `padding:22px 22px 18px` (`panels.css:550`). The photo is
a 40 px circle inside that head; `.mpf-big` is `position:absolute;inset:0`
inside the scrolling body below it. **So 18 px of head padding sits between the
two, belonging to neither.** A pointer moving from the photo onto the picture
crosses it, and the plain rule would close the picture exactly when somebody
reaches for it.

So: a **260 ms** grace period, cleared the instant the pointer is back on
either element, and cleared by every other close path. Evidence first, then the
extra — and it is six lines, not a hover-intent library.

**Unmeasured, and said out loud:** 260 ms is a judgement, not a measurement. I
could not try it, because `playwright` does not resolve from this worktree
(`check_portal_trays.js`'s browser half has the same problem). **H-6's
keyboard-and-pointer pass should look at this specifically.**

### 11.5 The seven non-functional dimensions, against the code I actually wrote

| Dimension | Verdict | Why |
|---|---|---|
| **Performance** | **improves** | One settings read **deleted** from every anonymous hit of the public page (D-7). D-3's check adds **one** `File` count, and only on the submit path, and only when every field came in empty — the normal submission never runs it. The tray's button is markup, not a request. The moved documents card is the same one call it always was |
| **Security** | **improves** | D-3 closes a path that let an unauthenticated caller consume a token for nothing. J4 adds **no new public endpoint** — the guest surface is still exactly three, all POST. The photo goes through the same five-step check the documents do, and the stored `File` is `is_private = 1`, asserted |
| **Reliability** | **improves** | The refusal is now recoverable: `status` stays `Invited`, the key's row survives, and a test proves the link reopens and a second attempt works. Before, one stray tap was final |
| **Scalability** | **neutral** | No new index, job, queue, cache or denormalised field. Nothing here grows with headcount |
| **Maintainability** | **improves slightly** | The gate reads one more real shape instead of carrying an excuse. Three lazy imports of `employee_photo` in one function became one. Against that: `sendPhoto` repeats ~15 lines of `sendFile`'s FileReader dance — left duplicated on purpose, because two uses do not earn a helper and a merged one would need four parameters |
| **Data integrity** | **improves** | No blank submission can reach `Submitted` any more, so HR's list stops carrying empty rows that cannot be chased |
| **Compliance / privacy** | **improves** | **No visibility widened anywhere.** The tray exposes no field the table did not already — it opens the same `get_profile`, which intersects the same server-side allow-list with the same `may_view` and `employee_in_scope`. Moving the documents card changes who sees it not at all; it is the person's own card, on their own page. D-5(d) **narrows** exposure: a colleague's enlarged face no longer stays on screen after the pointer leaves, on the one screen that also carries *"Hide before I share my screen"*. D-1 puts a non-employee's personal data **inside** the tenant access derivation, which is the stricter side |

### 11.6 NFR notes

- **Query counts.** D-3: `+1` statement, submit path only, only on an
  all-empty submission. D-7: `-1` settings read per public page load. Everything
  else: `0`.
- **Permission enforcement points.** Unchanged. The tray's name goes to
  `positions_profile.get_profile`, which already runs `may_view()` **and**
  `employee_in_scope()`. J4's upload goes through `_open`, which is the token
  check and the only way into that module. No `ignore_permissions` added
  anywhere; `_has_a_document` uses it to count the row's own attachments, which
  is the same pattern `upload_invite_file` already used four lines later.
- **Sensitive fields touched.** The joiner's photograph is new stored personal
  data. It is EXIF-stripped, 512 px, `is_private = 1`, attached to the
  submission row, and it falls under the same `_drop_request`/erase machinery as
  the joiner's documents — `TestRetention`'s `test_the_erase_takes_the_files_with_it`
  covers files attached to that row, and the photo is one.
- **Fallbacks.** J4 is skippable, and a failed upload says so and offers the way
  on. The mini profile's enlargement degrades to the blurred 48 px copy, as
  before.
- **Logging.** The photo's log line carries the row, `__photo__` as the type,
  the byte count and the time. No name, no file address, no bytes.

### 11.7 What else moved while I worked

- **`docs/slices/078-positions-faces/02-functional-spec.md`** was being edited by
  `hrms-business-analyst` **at the same time**, in this worktree. I read their
  new rows before finishing D-3 and **changed my implementation to follow them**
  — AC-110a's exact sentence and its "stay on J5", AC-110c's "or one document",
  and AC-108a/b/c's wording for J4. My first version blocked J2's Next and
  demanded a typed field; the spec says documents alone are enough, so that
  version was wrong and was removed. Their file is still uncommitted and is
  **not** in any of my five commits.
- **`03-implementation-notes.md`** was corrected by somebody else while I worked:
  the `AC-72a` id the test report flagged as never issued is now `AC-3a`, in two
  places. **I kept their edit** and appended this section below it.
- **`.claude/context/ux-learnings.md`** has been modified since before I started.
  It is the UX designer's and I have not touched it.
- **A leftover chained test run.** `hrlocal-078` was running
  `/home/frappe/full078.sh` — `run-tests --app alvoraa_portal` then `--app hrms`
  — started at 11:56 and still going at 13:44. It was reading this worktree's
  apps by bind mount, so it was testing my **half-finished** edits and its
  portal numbers could not be trusted. I stopped the portal half. A live session
  then started its own `hrms` run on the same site, which I let finish: **I
  changed no `hrms` file in this work**, so that result stands on its own.

### 11.8 Commands I ran, and what they said

| Command | Result |
|---|---|
| `python scripts/check_app_integrity.py` | **OK — 881 checks** |
| `python scripts/check_scope_traps.py` | **OK** |
| `python scripts/check_design_system.py` | **OK** |
| `python scripts/check_brand_spelling.py` | **OK** |
| `python scripts/check_tag_balance.py` | **OK** |
| `python scripts/check_version_pins.py` | **OK** |
| `python scripts/check_api_paths.py --max 0` | **OK** |
| `python scripts/check_portal_assets_gate.py` | **OK** |
| `node scripts/check_undefined_js.js` | **OK — none** |
| `node scripts/check_positions_tree.js` | **OK — 404 checks** |
| `node scripts/check_wall_chart.js` | **OK — 225 checks** |
| `node scripts/check_portal_handlers.js` | **OK — all reachable and callable** |
| `node scripts/check_portal_trays.js` | **static half OK — 27 of 27.** The browser half still cannot run: `playwright` does not resolve from the worktree. Pre-existing (T1 / N-1), not mine |
| `node scripts/run_dom_tests.js` | **OK — 20 run, 0 not run, 0 failed.** The 078 suite alone **116 passed, 0 failed** |
| `node --check portal.js`, `python -m ast` on every changed `.py` | **parse clean** |
| The 045 gate, re-run standalone outside the bench | **226 sites, 0 orphans, floor 201** |
| `bench --site test078 run-tests --module …` x 7, run **serially** | **see 11.8a** |

### 11.8a The Python suites, module by module

Run on `test078` in `hrlocal-078`, **one at a time**, never two against the one
site. Every module that owns a surface this work touched:

| Module | Result |
|---|---|
| `test_invoicing` — **the D-1 gate** | the gate itself run alone: **1 test, OK.** `test_every_billing_doctype_is_named_as_control_plane_only` passes |
| `test_browser_call_args_045` — **the D-2 gate** | **6 tests, OK**, `test_no_endpoint_is_named_but_never_read` among them |
| `test_joiner_078` | **54 tests, OK** — 41 that were there plus my 13 |
| `test_my_photo_078` | **34 tests, OK** |
| `test_mini_profile_078` | **12 tests, OK** |
| `test_employee_documents_078` | **20 tests, OK** |
| `test_expense_birthdays_076` | **35 tests, 1 error — and it is not mine.** See below |
| `node scripts/run_dom_tests.js`, re-run after the last change | **20 run, 0 failed; the 078 suite 116 passed** |

**The whole `test_invoicing` module, run for its own sake, is 20 tests with 1
failure and 10 errors** — all of them about multi-site billing on
`sharma.alvoraa.co` and a `Party Account Debtors - TPC currency (USD)`
mismatch. None of them is the gate, and none of them touches anything this work
changed. The gate is the one I was asked about, and it is green on its own.

**`test_expense_birthdays_076`'s one error, and why it is the site's and not
mine.** The failing test is
`test_the_department_approver_is_used_when_the_employee_has_none`, and the error
is hrms's own `MismatchError: Department C076 Dept - TPC does not belong to
company: N076 Co Y`. I proved the cause rather than asserting it: **`test078`
carries two leftover `C076 Dept` rows** — `C076 Dept - N76Y` under `N076 Co Y`
and `C076 Dept - TPC` under `Test PCV Company` — **54 companies accumulated from
months of runs, and no default company set at all.** `N076 Co Y` belongs to
`test_announcements_076`, a different module.

Two more things place it outside my diff: the module imports `home_people`,
`hr_api`, `inbox_api` and five test helpers, **none of which I changed**; and it
contains **no reference to `home.html`, `my-docs-card` or
`#panel-my-profile`** — the only surfaces this work touched that it could
possibly see. It was green in the test engineer's full-app run earlier the same
day, on the same site, under a different order. **It is fixture accumulation on
a long-lived test database.** Worth a separate ticket; not this slice's.

### 11.9 What I could NOT close

| # | Thing | Why |
|---|---|---|
| **R-1** | **The full 1,118-test `alvoraa_portal` suite has not been re-run end to end.** I ran the **seven modules that own every surface I touched**, serially, and they are in 11.8a — but the whole app, in one pass, I did not. It takes about 75 minutes and `test078` was held by another live session for most of my build | One command, once the site is free. It should run before anybody calls this green |
| **R-1a** | **The `hrms` suite cannot run on `test078` at all.** It fails in **discovery**, before a single test: `TestRunnerError: Failed to discover tests for ['hrms']: Could not find Parent Item Group: All Item Groups`. That is why `04-test-report.md` §2.2 still carries an empty `<!--HRMS-RESULTS-->`. **I changed no `hrms` file in this work**, so nothing here depends on it — but it needs fixing before anybody can claim the hrms side is green | A site bootstrap gap, the same shape as the fiscal-year one. Its own ticket |
| **R-2** | **The joiner's page has not been re-driven in a browser since J4 was added.** The test engineer's 46-assertion harness lives in their scratchpad, not in the repository | A committed `joiner_078_test.js` in the DOM suite is the right home, with `EXPECTED_BROWSER_TESTS` raised to 21 in the same commit. That is the test engineer's call, not mine to add unasked |
| **R-3** | **D-4 is untouched.** Cross-company isolation for the two new read endpoints is still untested, and no CXO persona exists in this slice | The brief did not list it, and `fixtures_078.py` explains why a second company was not built. It stays an **untested control** and belongs in the release note |

### 11.10 Decisions Surbhi should see

1. **A photograph counts as "something sent".** AC-110c says "one field with a
   value, **or one document**". A joiner who sends only their J4 picture and
   types nothing is **accepted**, by both the browser and the server, because
   refusing somebody who has just sent us their face reads as a fault. Strictly,
   a photograph is not a document. **If that is wrong, it is one condition in
   `_has_a_document` and one in `nothingSent()`.**
2. **`full_name` is still not mandatory.** Per Decision 3 and AC-110c, we add no
   field of our own. The spec's §21 names the one row to change if she wants the
   name always required.
3. **A click now pins the enlarged photograph.** On touch nothing changes — a tap
   opens it pinned and a second tap closes it, exactly as before. On a mouse the
   behaviour is new: a click no longer closes a picture the pointer opened. That
   is what `01b` §6.3.1 draws, and it is a real change to a gesture people may
   have learned in testing.

### 11.11 Subtract pass

Read back with one question: **what can I delete and still meet the
requirement?**

**Removed:**

1. **The J2 error paragraph and the block on J2's Next.** My first version
   stopped the joiner at *Your details* with its own message. The spec says
   documents alone are a valid submission, so that block was our restriction on
   top of HR's ticked list — the exact thing Decision 3 forbids. Both the markup
   and the handler went, along with the `keep()` line that cleared it.
2. **`askForSomething()`**, the helper that bounced the joiner back to J2 and
   focused the first input. AC-110a says stay on J5, so there was nowhere to
   bounce to and nothing to focus.
3. **Two of three lazy imports of `employee_photo`** inside
   `upload_invite_file`. One import of the module, used three times, says the
   same thing.
4. **A 48 px thumbnail for the joiner's photograph.** Tempting, for symmetry
   with the employee's. Nothing reads it: there is no `Employee`, so no chart
   draws a joiner's face. It would have been a second file per joiner for a
   reader that does not exist.
5. **A second copy of the picker's footer markup** for the phone. One `order`
   rule on `[data-ocs="ok"]` does it.

**Not removed, and why:** `sendPhoto` in `joiner.html` repeats about fifteen
lines of `sendFile`'s FileReader handling. Merging them needs four parameters
(the status element, the type, what to do on success, what to say on failure)
and makes both harder to read for one caller each. Two uses do not earn a
helper; the third would.

---

## 12 · The query budget CI was red on, 1 November 2026

`test_unseated_071.test_statement_count_is_a_fixed_handful` failed on dev at
**43 statements against a ceiling of 40**. I measured it rather than reasoned
about it: every statement dumped and read.

**The answer: nothing this slice added appears in the 43, and the ceiling did
not need raising. 19 of them were a cold `get_meta` load the gate never meant
to measure.** Warmed properly, the same call is **24**.

### 12.1 What the 43 actually were

Measured on `test078f`, with `frappe.db.sql` wrapped so every statement was
written out in order.

| Group | Count | What |
|---|---|---|
| The plain assignment path | **13** | the seat's row, the caller's company twice, the person's company and branch, their name, their joining date, the seat's status, their other assignments (3 reads), the `INSERT`, then the seat and its holders read back |
| **Frappe's cold `get_meta("Alvoraa Position")`** | **12** | `tabDocType`, `tabDocField`, `tabDocPerm`, `tabDocType Action`, `tabDocType Link`, `tabDocType State`, `tabCustom Field`, `tabProperty Setter`, `tabCustom DocPerm`, and the three `custom=1` counterparts |
| Two `information_schema` reads | **2** | `tables.table_rows`, then `columns.column_name` |
| Frappe's standard save machinery | **5** | `tabNotification`, `tabWorkflow`, two `tabAssignment Rule`, `tabMilestone Tracker` |
| The `add_place` branch's own work | **5** | the `FOR UPDATE` lock, the seat's holders, the children check, the `UPDATE` of the position, the `old_parent` nested-set write |
| Re-reads after the save | **6** | the position again, its children, the person's name, the seat, their other assignments, the holders |

**The second, third and fourth groups — 19 statements — happen once per
process**, the first time any `Alvoraa Position` is *saved*. They are not per
click and not per person.

### 12.2 Why the gate was measuring them

The test warmed the **plain** path (`register.assign_person(roomy, warm)`) and
not the `add_place` path. Only `add_place` **saves** a position, so the cold
meta load landed inside the measured block — and the number then moved with
whatever order the suites happened to run in. That is why it was 43 here and
had been under 40 when slice 071 wrote the ceiling.

**The fix is in the test, and it is the test's own convention:** warm the
`add_place` path too, with one position save before the measured block. The
ceiling **stays at 40**, and the measurement is now **24** — 16 statements of
headroom, and it measures what it claims to.

I did not raise the ceiling. There was nothing to raise it for.

### 12.3 The `has_value_changed` question, settled

The suspicion was that `employee_photo.on_employee_update` was firing on every
Employee **insert**, because `has_value_changed` returns True whenever there is
no previous document.

**It is not, and this path never reaches it at all.** Two separate proofs:

1. **Measured.** The 43 statements contain **no `tabFile` read, no
   `alvoraa_photo_48`, and no `UPDATE tabEmployee`**. `assign_person` saves an
   `Alvoraa Position` and inserts an `Alvoraa Position Assignment`. It saves no
   Employee, so an `Employee.on_update` hook cannot run.
2. **The guard was already two-part**, and the docstring says DevOps found the
   trap during the build (OPS §4). It skips an insert that carries no picture,
   and otherwise runs — because the one-part fix DevOps suggested
   (`has_value_changed(...) and doc.image`) would close that hole and open the
   opposite one: clearing a photograph in Desk would leave the 48 px copy
   behind and the chart would keep drawing a face that had been removed.

**What was missing was the test, not the guard.** One existing test proved only
the first corner, which means the guard could have been over-tightened to
"return on any insert" and still passed. `test_the_guard_is_right_in_all_four_corners`
now asserts all four: a new Employee with no picture does nothing; a new
Employee arriving with one derives; a changed picture derives; and a **cleared**
picture derives, which is what deletes the copy.

**The same trap elsewhere in this slice: nowhere.** `has_value_changed` is
called in four other places in `alvoraa_portal` — `crm_steps.py` (×4),
`employee_field_rights.py`, `alvoraa_field_device.py` — and **none of them is
this slice's**. Worth one line for somebody else's attention:
`employee_field_rights.py:148` is `any(doc.has_value_changed(df.fieldname) for
df in doc.meta.get_high_permlevel_fields())`, which by the same rule is True for
every high-permlevel field on every insert. Not mine, not this slice, **not
touched** — written down rather than quietly changed.

### 12.4 What I broke and put back

**My own measurement polluted `test078f`, and I should say so plainly.** The
dump ran as a subclass of `PlaceAnyway071`, and `hr_user()` inserts an Employee
carrying `user_id` on every call, relying on its own teardown. When a test
errors the teardown does not finish, so four `Scope194` Employees were left
behind holding `scope194.count071@`, `.rollback071@`, `.words071@` and
`.noflag071@`. `hr_user()` then refused with
`DuplicateEntryError: User … is already assigned to Employee …`, and **five
tests in `test_unseated_071` failed for that reason and no other.**

I deleted the four leftover Employees and their Users — the rows the teardown
would have removed — and re-ran. **All 12 pass.** The lesson is the standing
one: a fixture that inserts a `user_id` link is not safe to leave behind, and a
measurement harness that subclasses a real test case inherits that risk.

### 12.5 The runs

| Suite | Result |
|---|---|
| `test_unseated_071` | **12 tests, OK** — `14 plain, 24 with add_place` |
| `test_my_photo_078` | **35 tests, OK** — including the new four-corner guard test |
| `test_faces_078` | **8 tests, OK** |
| `test_register_194` | **38 tests, OK** |
| `python scripts/check_app_integrity.py` | **OK — 890 checks** |

### 12.6 Noted in passing, not fixed

A `V17FrappeDeprecationWarning` surfaces during these tests: *"The
`limit_page_length` parameter is deprecated. Use `limit` instead."* It is a
warning, not a failure, and it is not this slice's code. It will matter at the
v17 upgrade and belongs in its own ticket.
