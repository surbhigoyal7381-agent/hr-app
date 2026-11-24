---
slice: 088-register-notice-and-forms
artifact: 06-security-review
author: hrms-security-privacy-engineer
date: 2026-11-24
status: recommendations only. Surbhi decides; I approve nothing.
scope: the production release candidate — branch `release/088-alv436`, HEAD `b4cf01a5`,
       18 commits on top of `main` (`f68f2333`). Diff reviewed: `origin/main..HEAD`.
covers: slice 088 (13 commits), ALV-436 (3), ALV-435 (1), one test-only date fix
---

# 088 · Security and privacy review of the release candidate

## 0 · Governance note, first

**I wrote `01c-security-privacy-requirements.md` for this slice, and I am now marking my
own requirements.** That is the failure mode CLAUDE.md names, and 01c §14 already asked
for a second pair of eyes on **SEC-4** (nobody records a confirmation they have an
interest in) and **SEC-8** (only HR in scope can open the photo). That request still
stands: the technofunctional reviewer should check those two independently.

**There is no `04-test-report.md` and there was no `06` before this one.** What that
costs me, concretely:

- I have no list of what was run, on which site, with what data. CI being green tells me
  the suite passed on a **clean** site; it tells me nothing about the data shapes 01c §9
  said must exist for each control to be *observable* (lesson 1 of the September list).
- I checked the data shape myself where it mattered, by reading the test fixtures and by
  running read-only queries on the dev test site. Where I could not, I say so.
- Nobody has written down that the "fails first" breaks in 01c were actually performed.
  Two test docstrings say they were (`test_hr_scoped_to_one_branch...` and
  `test_the_reason_reaches_the_page...`), and both read like real accounts of a break.
  For the rest I am trusting the code, not a record.

## 1 · Verdict

**No code blocker for this release.** One **P1 process item must be cleared before the
push to `main`**, and it is one command.

The release is safe mainly because **the feature ships dark**: `alvoraa_print_change_notices`
is a per-company Check with `"default": "0"`
(`alvoraa_register_notice`'s field set, `register_notice.py:76-86`), and
`notices_are_on()` answers **no** when the column is missing or the lookup throws
(`register_notice.py:89-112`). Every 088 surface — the HR list, printing, the employee's
own view — is gated on it (`:311`, `:563`, `:933`).

So there are two different decisions here, and they should not be taken together:

| Decision | My recommendation |
|---|---|
| **Push `b4cf01a5` to `main`** | Yes, after the P1 below. The feature is off on every company, and nothing in the diff changes behaviour that is live today except ALV-436's refusal (which is a refusal, not a widening). |
| **Switch `alvoraa_print_change_notices` on at DTC or Grace** | Not yet. The three **P2** findings below are about the signature photo and an audit trail, and they should be fixed or accepted in writing, by name and date, before any real worker's thumb print is stored. |

**On counsel's condition:** 088 discharges it **partly, and not at all on day one**. See §5.

## 2 · What I read and ran, and where

- **Worktree** `/Users/mac/hr-app/.claude/worktrees/release-088-alv436`, branch
  `release/088-alv436`, HEAD `b4cf01a5`. Diff read in full (`git diff origin/main..HEAD`,
  25 files, +3,971).
- **Installed Frappe**, read only, in container `alv436rel-bench`: Frappe `988e54f`,
  v16.33.1. Files read: `core/doctype/file/file.py` (`has_permission` 989-1026),
  `permissions.py` (`has_permission` 81-245, `has_child_permission` 808-903),
  `model/db_query.py` (`check_read_permission` 612-632, `build_match_conditions`
  1026-1095, `get_permission_query_conditions` 1159-1185),
  `utils/response.py` (`download_private_file` 294-306),
  `utils/__init__.py` (`get_traceback` 315-332, `_get_traceback_sanitizer` 335-372),
  `utils/error.py:68`, `hooks.py` (`default_log_clearing_doctypes` 522-538),
  `model/delete_doc.py` (`add_to_deleted_document` 237-246).
- **Ran** (dev site `test_site` on that container, read-only except where noted):
  1. `punch_fix.refuse_if_the_words_would_be_lost` against 17 strings — results in §4,
     ALV-436.
  2. `access.security_logger().info(...)` — wrote **one probe line** into
     `/home/frappe/frappe-bench/logs/security.log` and read it back. That is the only
     write I made anywhere.
  3. `frappe.client.get_list` on the notice and on **both child tables**, as an
     out-of-scope HR Manager and as in-scope HR Managers.
  4. `File.has_permission("read"/"write"/"delete")` on a real stored signature photo, as
     the employee, as an out-of-scope HR Manager, and as the uploading HR Manager.
  5. `register_notice.notice_query_conditions` / `photo_log_query_conditions` for several
     real users.
  6. Row counts on `Alvoraa Photo Access Log`, grouped by `source` and by whether
     `employee` is set.
  7. `gh run view 45318596896 --log | grep Scanning:` — what the secret scan covered.
  8. `python3 scripts/check_no_demo_passwords.py` on the tree — passed, 41 files.
- **Did not touch production.** The production figures in this review are the ones the
  caller measured read-only on 23 Nov (DTC: 1 Attendance Request, not a punch fix; Grace:
  137, none a punch fix), and I am relying on them as stated, not re-deriving them.
- **Did not run** the 088 or 087 suites myself (CI run `45318596896` is green: 80 tests in
  `test_register_notice_088.py`, 134 in `test_punch_fix_087.py`).

## 3 · Requirement-by-requirement

Every "proves it" reference is a file and line in this worktree unless it says *installed
Frappe*. Verdicts: **MET** / **PARTIAL** / **NOT MET** / **NOT CHECKED**.

| Req | Verdict | The mechanism, and the test | Label |
|---|---|---|---|
| **SEC-1** one scope rule on every reader and writer | **MET** | Role gate `_hr_or_refuse` (`register_notice.py:159-161`) on all five endpoints. Scope from `access.permitted_employee_filters` / `employee_in_scope` (`hrms/hrms/alvoraa_hr_core/access.py:297-347`): list `:310-311`, print `:537-541`, record `:735-739`, photo `:817-820`, row filter `_scope_sql` `:873-896`. Tests: branch HR refused (`test_register_notice_088.py:1119`), out-of-scope HR (`:1105`), employee and line manager (`:534`), HR with no company (`:544`). **I grepped for unscoped siblings: the only readers of `Alvoraa Register Notice` outside this module are an existence check (`punch_fix.py:1117`), two hook registrations and a label list** — none returns data. | Verified in code **and by running**: for an out-of-scope HR Manager the condition is `1=0` and the list returns 0 rows |
| **SEC-2** content leaves only through one logged call | **MET**, one named test missing | The list payload carries no reason, time or request id (`:352-370`; test `:517`). The notice row is inserted **before** any sheet is built and before the return (`:572` insert, `:574-596` sheets, `:598` return) — one request, one transaction, so a failed insert returns nothing. 100 people refused before a row is written (`:527-530`; test `:754`). Durable record is a DocType row, not a log line. | Verified in code. **The 01c test "force the insert to fail and assert no content is returned" does not exist** (no failure injection anywhere in the suite) → P3-1 |
| **SEC-3** a signature covers exactly what was printed | **MET** | `_content_hash` over `punch_fix.CONFIRMED_CONTENT` (`:483-492`), stored per change row; `_still_the_same` (`:628-641`); covered changes read from the record, never from the caller (`:755`); an older notice refused once a newer one exists (`:745-746`). Tests `:868`, `:883`, `:894`. | Verified in code |
| **SEC-4** nobody records a confirmation they have an interest in | **MET** | `access.refuse_own_decision` (`:737`) → `is_own_record` has **no status filter** (`access.py:101-106`), so a leaver who is HR is still refused. Filer check reads the request `owner` from the database for every covered change (`:757-763`). Both outcomes go through the same path (`:765-786`). Tests `:911` (endpoint), `:495` (both sides of the button). | Verified in code. **Second pair of eyes still wanted** (§0) |
| **SEC-5** the confirmation fields are written by the record call only | **MET** for HR; System Manager Desk write remains, as 01c allowed | `AlvoraaRegisterNotice.validate` refuses a hand-made insert, any edit to what was printed, and any edit after an answer (`alvoraa_register_notice.py:50-85`); `on_trash` refuses deletion by every role (`:96-107`). HR Manager and HR User hold **read only** (`alvoraa_register_notice.json` permissions). On the request side, `alvoraa_signed_notice` is in `SERVER_OWNED` (`punch_fix.py:55-58`), cleared on insert (`:506`) and put back from the stored value on every edit (`:513-514`). Tests `:246`-`:293`, `:351`, `:379`. | Verified in code |
| **SEC-6** the photo reuses slice 081's checks | **MET** | `_photo_bytes` (`:641-652`) calls `expense_evidence._decode` (length before decode, magic bytes JPEG/PNG only) and `_shrink_to_cap` (re-encode through Pillow → EXIF and GPS gone, long edge 1,600, stored ≤ 1 MB: `expense_evidence.py:105-131, 311-329`). PDF refused explicitly. Stored name generated, names nobody (`expense_evidence.py:332-349`). Tests `:937`, `:954`. | Verified in code. **Not checked:** what a real signed A4 page weighs after the re-encode (01c OPS-8) — that is DevOps' measurement and I have not seen it |
| **SEC-7** a reused photo is refused; the dialog shows who it is | **PARTIAL** | Reuse: `_refuse_a_reused_photo` (`:655-671`) on Frappe's own `content_hash`, scoped to notice attachments; test `:921`. The dialog names the person ("Record this only if {first} signed…", `portal.js:7217-7227`) and says the page holds only their details — but **it does not show the page reference next to the preview**, which is what 01c asked for and what tells two pages of the same month apart. The reference is on the paper (`:586-588`) and in the preview, not in the record dialog. | Verified in code (both halves). The missing half is P3-2 |
| **SEC-8** only HR in scope can open the photo, by structure | **PARTIAL** — the structure holds, one clause does not | The photo is attached to the **notice** and to nothing else (`:674-699`); the notice has no Employee role row and is not on any manager User Permission (`manager_scope.py:52` scopes four doctypes, never "all"); the private-file route asks the parent's read right, which runs our hook (installed Frappe `file.py:1009-1024` → `permissions.py:239`). No export and no report right for any role (test `:1181`). **But 01c's clause "the browser never gets a `/private/files` address" is false**: an in-scope HR user reads `photo` straight off the `Alvoraa Register Notice Page` child table, and sees it on the notice's Desk form. See P2-3. | **Proven by running**: as the employee → `File.has_permission("read")` **False**; as an out-of-scope HR Manager → **False**; as the in-scope uploading HR Manager → True. **Proven by running**: an in-scope HR Manager reads `photo = /private/files/register-…jpg` through `frappe.client.get_list` on the child table |
| **SEC-9** free text is shown as text, never as markup | **MET** | Every value on the card, the A4 sheet, the preview and the dialog goes through `gpEsc` → `esc` (`portal.js:265-270`), which escapes `& < > "`. And since ALV-436, a reason whose content `sanitize_html` would alter cannot be filed at all. | **Proven by running**: `<img src=x onerror=…>`, `<script>…`, `<svg onload=…>` and `<a href="javascript:…">` are all **refused** at filing. 01c's named browser test (markup printed as characters in the preview) does not exist → P4-1 |
| **SEC-10** the photo access log is scoped too | **MET for exposure**, with a side effect | `photo_log_query_conditions` (`:905-910`) registered in `hooks.py:644`. The table had no entry before. | **Proven by running**: an out-of-scope HR Manager gets `1=0`; an in-scope one gets a company-and-branch condition. **And proven by running: the filter hides 26 of 77 existing rows from HR Manager** — see P2-2 |
| **SEC-11** POST-only, with the CSRF token | **MET** | All five endpoints are `@frappe.whitelist(methods=["POST"])` (`:285, :508, :712, :811, :901`); no `allow_guest` anywhere in the module; **no new website page in the diff**, so the "posts to `/` with `cmd`" trap does not arise here. The portal posts to `/api/method/…` with `X-Frappe-CSRF-Token` (`portal.js:17598-17613`). | Verified in code. The ALV-343 trap (installed Frappe `auth.py:87` skips the check for a session holding no token) is unchanged and is not 088's |
| **PRIV-1** collect nothing new except the photo | **PARTIAL** | No PDF, no server copy of the content, nothing cached: the notice stores ids, a month and a hash (test `:786`). Photos live in one JS object until the call succeeds and the object URLs are revoked on close (`portal.js:7286-7310`, `:7196-7199`) — never `localStorage`, `IndexedDB` or a cache. Refusal sentences and the three security log lines carry ids and counts only (`:596-598`, `:694-696`, `:800-802`). **But:** an unhandled exception inside `record` writes **local variables** to the Error Log, because Frappe formats tracebacks with variables (installed Frappe `utils/error.py:68` → `get_traceback(with_context=True)` → `traceback_with_variables`, blocklist is password/secret/token-shaped names only, values truncated at 1,000 characters). `reason` — the worker's objection, in their own words — is well under 1,000 characters. | Verified in code; the Error Log path is **proven in installed Frappe source, not demonstrated end to end** on 088's path. **Neither of PRIV-1's two named tests exists** (no Error Log test, no browser-storage test) → P3-3 |
| **PRIV-2** what goes on paper | **MET** | `sheet_rows` (`:530-551`) prints the day, the three "added" sentences, what the day now counts, HR-or-named-manager, the date and `_reason_of(explanation)`. `alvoraa_review_note` appears **nowhere** in the module (grep: 0 hits). A leave or absence day cannot qualify at all — `qualifying_changes` requires `alvoraa_missing_time` or `alvoraa_set_aside` (`:219-221`). Another person's data cannot reach the page: one employee per sheet (`:563-596`). Footer "This page is only about you. Keep it private." (`portal.js:7292`; DOM test asserts it). Pay line only where the page holds a change that holds pay (`:589-590`, DOM test). | Verified in code. 01c's exact three-way negative test (HR note + a leave day + a colleague's change on one day) is not in the suite as written; the three are excluded structurally and separately tested |
| **PRIV-3** the photo is handled as the most sensitive thing here | **PARTIAL** | Follows SEC-6 and SEC-8. Never exported, never in a report, email, notification or model prompt (no such path exists in the diff), never shown to a line manager (proven by running). **"Every opening recorded" is not true** — see P2-3. And C1 (is it biometric data?) is still unanswered, so the handling rests on our own precaution, not on advice. | Verified in code; the gap proven by running |
| **PRIV-4** nothing deletes, and nothing is deletable by HR | **NOT MET** (one clause) | 088 adds no deletion path: the suite greps the module for `delete_doc`, `frappe.db.delete`, `DROP`, `TRUNCATE` and finds none (`:1181-1195`), and `on_trash` refuses the notice to every role including Administrator. **But the HR person who uploaded the photo can delete the photo**: installed Frappe `file.py:999` returns True for **any** permission type when `doc.owner == user`, and `_save_the_photo` saves the File as the session user, so the recorder owns it. | **Proven by running**: as the uploading HR Manager (roles: HR Manager, Employee, Desk User — not System Manager), `File.has_permission` is **True for read, write and delete**. See P2-1 |
| **PRIV-5** the employee app shows the same facts, about them only | **MET** | `my_changes` (`:901-960`) takes a month and nothing else; the person comes from `attendance_correction._me()` (Active only), so there is no id to swap. It carries the reason and the state, and no photo, file or address (tests `:1261`, `:1278`, `:1292`). | Verified in code |
| **PRIV-6** the print record lives as long as what it proves | **MET as a rule** | Nothing clears it: it is our DocType, deletion is refused, and Frappe clears none of ours by default (installed Frappe `hooks.py:522-538` — `Access Log` is not in the list either). The record stores employee and month so a future purge can work out its own date, and there is no `retain_until` field nobody has chosen (test `:1196`). | Verified in code. **The period itself is still 01c C2, unanswered by counsel** |

**Counts: 11 SEC → 7 MET, 3 PARTIAL, 0 NOT MET, 1 MET-with-a-side-effect.
6 PRIV → 3 MET, 2 PARTIAL, 1 NOT MET.**

## 4 · The things this codebase has been bitten by — each checked against this diff

| Trap | Result |
|---|---|
| **`has_permission` on a child table is always False** | **Handled correctly, and better than I expected.** The guard is on the parent only (`hooks.py:661`), and the two child tables carry empty `permissions` and no hook. I then checked what the framework does with a direct child-table query, because that is where a parent-only guard could be bypassed. **Proven by running:** Frappe 16.33.1 **joins the parent table and applies the parent's `permission_query_conditions`** — the generated SQL for an out-of-scope HR Manager was `… JOIN \`tabAlvoraa Register Notice\` ON … WHERE (1=0) LIMIT 3`, 0 rows. In-scope users get rows. So the row filter reaches the children. |
| **Website pages post to `/` with `cmd`** | Does not arise: **no new website page or endpoint file in the diff**. The portal's calls go to `/api/method/…`, and Frappe's `methods=["POST"]` check applies on either path. |
| **Security refusals were never logged (ALV-391)** | **Actually written, not merely called. Proven by running:** `access.security_logger()` raises the logger to INFO (`access.py:62-67`) and my probe line landed in `/home/frappe/frappe-bench/logs/security.log` (73 KB, not 0). The three 088 lines (`:596`, `:694`, `:800`) and `punch_fix:1131` are all `.info`, so they are written. Two tests assert the emission from a logger deliberately set back to ERROR first (`test_punch_fix_087.py:34-55`), which is the right shape of test. **Caveat I am keeping honest:** that handler rotates at 100 KB × 20, so it is recent-misuse evidence, not a year-later answer. The durable trail is the notice record. |
| **Field rights (ALV-215)** | Nothing restricted is exposed. The module reads only `name, employee_name, employee_number, branch, company, user_id` from Employee. `company`, `branch` and `user_id` are permlevel 2 (`employee_field_rights.py:52-56`), readable by HR roles, and only HR endpoints return them; the employee's own view returns none of them. No pay field, no `ctc`, no statutory id anywhere in the diff. |
| **`frappe.message_log` is a proxy** | No assignment anywhere: `grep "message_log"` in the diff → 0 hits. The suite uses the helper pattern. |
| **A photograph of a signed page** | Retention: nothing deletes, period still open (C2) → PRIV-6 MET as a rule, P3-4 as a risk. Who can read it: HR in scope only, **proven by running**. Access logged: **only through `open_photo`** → P2-3. Exportable: no export or report right on the notice, and no "download all" → MET. |

### ALV-436 — verified by running

I ran `punch_fix.refuse_if_the_words_would_be_lost` against 17 strings on `test_site`:

- **Refused** (because `sanitize_html` would change them): `<machine down>`,
  `Punch missed <not my fault>`, and every active payload I tried —
  `<img src=x onerror=…>`, `<script>alert(1)</script>`, `<svg onload=…>`,
  `<a href="javascript:…">`.
- **Allowed, unchanged**: `machine 9 > 8 was down & I told HR`, `a<b`,
  `Site A -> Site B`, `100%`, `<35 degrees>`, `forgot & left`, `it's ok`,
  `line1\nline2`, Hindi in Latin script, `<3`, and `<b>bold</b>`.

So the claim in the docstring holds, and the refusal is narrow: only `<` immediately
followed by a letter is eaten by Frappe, and only that is refused. `<b>bold</b>` survives
as markup on the record, and is escaped on every surface that renders it (`esc`,
`portal.js:265-270`) — so it prints as characters, which is what SEC-9 asks for.

The refusal is placed in `punch_fix.validate` **before** the column guard (`:418-421`),
so it covers the portal, the Desk, REST and an import on every site, migrated or not.
Two tests, both sides asserted, plus "nothing was written by the refused attempt"
(`test_punch_fix_087.py:989-1024`). **MET.**

### ALV-435 — the CI change

The change is correct for what it targets (a push to `dev` or `test` now scans everything
not yet on `main`), and `fetch-depth: 0` is already set on that job. Two notes, neither
blocking: the `elif` chain falls back to the narrow range if the `origin/main` fetch
fails — visibly, because the range is echoed — and the fix does **not** cover a
`workflow_dispatch` run or a brand-new branch. Which is exactly how this release was
built: see P1-1.

## 5 · Does this release discharge counsel's condition?

Counsel's 21 Nov position (relayed by Surbhi, unsigned, memory
`counsel-087-hr-punches-nov21`) clears DTC and Grace **if** four things hold, one of
which is **"a monthly notice for staff without the app"**. I am not a lawyer and this is
counsel's call, not mine. What I can say precisely is what the code does:

1. **Not on day one, anywhere.** The switch ships off and `notices_are_on` answers no
   where the column is missing. Nothing is printed, listed or shown until somebody ticks
   it per company.
2. **Only for changes filed through the 087 punch-fix request flow.** `qualifying_changes`
   (`:163-241`) requires a **submitted, Approved Attendance Request** carrying
   `alvoraa_missing_time` or `alvoraa_set_aside`, filed by somebody other than the
   employee, and it **excludes `Administrator`** (`:235`). A correction made by creating
   or editing `Employee Checkin` rows directly produces **no notice at all**. That is how
   corrections have actually been made on DTC to date — the October regularisation was
   2,007 hand-made check-ins and 1,315 Administrator edits (memory
   `dtc-october-backfill-not-a-gap`), none of which this feature would ever notice.
3. **And the list is empty on both live tenants today** even with the switch on, because
   the 087 punch-fix flow has never been used (caller's read-only measurement, 23 Nov).

So: **the mechanism counsel asked for now exists and works; it does not yet cover the way
HR actually corrects attendance, and it is switched off.** That is a question for Surbhi
and counsel — *is a monthly notice that only covers punch-fix requests the notice you
described?* — and it blocks a claim, not this release. **⚠ COMPLIANCE C4 (new).**

C1 (is a signed-page photo "biometric information" under the SPDI Rules while they
remain in force?), C2 (how long are the photo and the record kept, from when, and who
deletes them?) and C3 (is one photo per page enough evidence?) are all **still
unanswered** in 01c. C1 and C2 block switching the feature on at a customer, not this
release, because nothing is stored until the switch is ticked.

## 6 · Findings

Ranked P0–P4. Each one names the actor, the state, the path and what they see.

### P1-1 · The secret-scan gate did not cover this release — clear it before the push

**Proven by running.** CI run `45318596896` is green, and its Key guard job reports:

```
Scanning: -1 b4cf01a58d0b7a222a4c0681335589f77803a4af
```

`-1 <sha>` is **one commit**. The run was a `workflow_dispatch`, so `github.event_name`
was neither `pull_request` nor `push`; `ALV-435`'s new branch only triggers on a push to
`dev` or `test`; and `github.event.before` is empty, so the script fell through to the
last `else`. **17 of this release's 18 commits have not been through gitleaks.**

This is the gate that stopped the 22 Nov release, for this class of reason (memory
`release-2026-11-22`). A push to `main` *will* scan `f68f2333..b4cf01a5` — but after the
commits are on `main`, and a secret that reaches `main` is burned everywhere.

What I could do instead, and did: `scripts/check_no_demo_passwords.py` passes on the tree
(41 files), `check_tracked_keys.py` runs in the same green job, and my own grep of the
diff for password/secret/key/token/`AKIA`/`ghp_`/`sk-`/`BEGIN … PRIVATE KEY` shapes found
nothing but test fixture strings ("secret words about this person"). That is **weaker
than gitleaks** and I am not offering it as a substitute.

**Fix, before the push:** run the pinned gitleaks over `origin/main..HEAD` on this branch
(same version and SHA-256 as `ci.yml:316-318`), or push to `dev` first and let ALV-435's
own new path do it. Label: **temporary debt, removed by one command.** Owner: Surbhi.

### P2-1 · The HR person who records a signature can delete the photo of it

**Proven by running.** On `test_site`, for a real stored signature photo, as its owner —
an HR Manager login with roles `HR Manager, Employee, Desk User, All, Guest`, **not**
System Manager:

```
File read -> True     File write -> True     File delete -> True
```

The cause is in installed Frappe, `core/doctype/file/file.py:999`:
`if user != "Guest" and doc.owner == user: return True` — before any permission-type
check. `_save_the_photo` (`register_notice.py:674-699`) saves the File as the session
user, so the recorder owns it for ever.

*Scenario.* HR person B records Joginder's signed page, then changes their mind — a
dispute arrives, or a payroll query. From the notice's Desk form they remove the
attachment. `frappe.delete_doc` asks `File.has_permission("delete")`, gets True, the bytes
go from disk, and the notice's `pages` row still points at a URL that no longer resolves.
The notice itself survives (`on_trash` refuses it) and a `Deleted Document` row records
who did it (installed Frappe `delete_doc.py:237-246`) — so it is detectable, but the only
evidence that the worker actually signed is gone.

PRIV-4 says in so many words that HR cannot delete a photo. It can. 01c's R4 anticipated
the owner shortcut for **reading** and accepted that; it did not see the delete.

**Blocks:** switching the feature on, not this release. **Options** (not my call): refuse
the delete in a `File` `has_permission` or `on_trash` hook for files attached to a notice;
or set the File's owner to Administrator on save; or accept it in writing with the
`Deleted Document` row as the compensating control. Label: **dangerous debt if left
unnamed.** Owner: Surbhi, with the engineer on which shape is cheapest.

### P2-2 · The new row filter hides 26 of 77 photo-access-log rows from HR Manager — all of them joiner-export rows

**Proven by running.** On `test_site`, `Alvoraa Photo Access Log` grouped by source and
by whether `employee` is set:

| source | rows | `employee` empty |
|---|---|---|
| Day-fix evidence | 5 | 0 |
| Expense bill | 15 | 0 |
| **Joiner export (masked)** | 10 | **10** |
| **Joiner export (not masked)** | 5 | **5** |
| **Joiner purge** | 11 | **11** |
| Register signature photo | 31 | 0 |

`photo_log_query_conditions` filters on `employee` through `_scope_sql` (`:873-896`). A
joiner is not an Employee yet, so **every joiner export and purge row has no `employee`
and now matches nothing** for an HR Manager.

*Scenario.* An HR Manager at DTC opens the photo access log in the Desk to answer "who
exported that joiner's Aadhaar, and was it masked?". Before this release they saw the
rows (and also, wrongly, every other company's). After it they see none of them. The rows
are still there and a **System Manager still sees all of them** (`_scope_sql` returns ""
for System Manager and Administrator), and the subject's own "who opened mine" reader
goes through `ignore_permissions` (`expense_evidence.py:794-798`), so nothing is
destroyed — the audit trail becomes invisible to the role most likely to look.

This matters because that trail is the control behind "log every export" (counsel on the
joiner form, 31 Oct; Surbhi's 19 Nov decision to keep those rows for ever).

**Fix or accept:** make the condition also admit rows that carry no employee (scoped some
other way, or to HR Manager outright), or accept in writing that joiner export evidence is
a System Manager view. Label: **intentional trade-off if accepted, with a name and a
date.** Owner: Surbhi.

### P2-3 · A signature photo can be opened without a row saying who looked

**Proven by running.** As an in-scope HR Manager, `frappe.client.get_list` on
`Alvoraa Register Notice Page` with `parent="Alvoraa Register Notice"` returns, among
others:

```
{'name': '0e28vvb1o4', 'parent': 'RN-00070', 'photo': '/private/files/register-22-nov-9d8ae3d267.jpg'}
```

The same URL is on the notice's Desk form, because `photo` is an `Attach` field in a
child table the in-scope HR user may read. Fetching it succeeds (that user's
`File.has_permission("read")` is True — correctly, they are in scope). `log_view` is
called **only** from `open_photo` (`:826`), so **no `Alvoraa Photo Access Log` row is
written for that view.**

*Scenario.* HR Manager A, in scope, opens RN-00070 in the Desk, clicks the attachment,
and reads the worker's thumb print. The employee later asks who has looked at their
signature. The product's own answer — the photo access log — says nobody.

Two things soften this, and I want both on the record: the viewer is somebody who is
**permitted** to see it, so this is an **audit gap, not a confidentiality breach**; and
Frappe writes its own `Access Log` row for every private-file download (installed Frappe
`utils/response.py:305`), naming the user, the File and the time, and that table is not
in `default_log_clearing_doctypes`. So the fact of the view is recorded somewhere — just
not against the employee, and not where anyone would look.

01c's SEC-8 claim "the browser never gets a `/private/files` address" is therefore
**false as written**, and PRIV-3's "every opening recorded" is **not met**. There is also
no viewer screen in 088 (Surbhi's P-14 decision), which is why nobody noticed: the Desk
is the only way to look, and the Desk is the unlogged way.

**Fix or accept:** keep the URL out of the child table payload (store the File name and
resolve it server-side), or log at the private-file route for notice attachments, or
accept in writing that HR Desk views are covered by Frappe's `Access Log`. Label:
**temporary debt**; removed when a viewer screen is built, which is when it starts to
matter. Owner: Surbhi.

### P3-1 · SEC-2's named test does not exist

"Force the insert to fail and assert no content is returned" is the test 01c marked, and
there is no failure injection anywhere in the 088 suite. The **ordering** is proven in
code (`:572` before `:598`) and is structurally safe inside one request, so the control is
real; what is missing is the thing that stops a later refactor from moving the insert
after the return. **Intentional simplification if accepted; one test removes it.**

### P3-2 · The record dialog does not show the page reference

SEC-7's second half, and abuse case A4 (HR photographs Ravi's page and records it for
Joginder). The dialog names the person (`portal.js:7217-7227`); it does not print the
`ref` that is on the paper. With a two-page notice, nothing on screen helps HR tell page 1
from page 2 of the right person, or this month's page from last month's. The defence is
the month and reference printed on the page plus HR's eye — which is R2, already accepted
— but the design asked for the reference in the dialog and it is not there.

### P3-3 · PRIV-1's two named tests do not exist, and one of them would have found something

No test asserts that browser storage holds no image after a failed-and-retried record
(the code is right: `portal.js:7286-7310`), and no test forces an error and greps the
Error Log for the reason text. The second one matters: as read in installed Frappe, an
unhandled exception in `record` writes **local variables** into the Error Log, including
`reason` — the worker's own words about a change they dispute — in full, since the
truncation is 1,000 characters. Error Log is System Manager only and is cleared after 14
days (installed Frappe `hooks.py:523`). This is Frappe-wide and already true of 087's
`explanation` and 081's bills, so it is not 088's invention; but PRIV-1 claims otherwise,
and the claim is what I am marking. **Temporary debt.**

### P3-4 · Retention is still open, and every backup copies the photos

PRIV-6 holds as a rule and C2 is unanswered. Until it is answered, every
`bench backup --with-files` copies every signature photo, with no period and no purge.
01c's R7 named this; it is unchanged. **Temporary debt; removed by the purge slice after
C2.**

### P3-5 · `register_notice.py` is outside the `ignore_permissions` ceiling gate

The gate that can only go down is a per-file `CEILINGS` dict
(`test_portal_security_010.py:1050-1084`). `register_notice.py` is a new file and has **no
entry**, so its **12** `ignore_permissions` are uncounted, and so is the thirteenth
somebody adds next quarter. (087 solved this differently: `punch_fix.py` has a test that
asserts the string appears **nowhere** in it.) Each of the 12 is argued in a comment and
the scope is enforced by `permitted_employee_filters` either side of them, so this is
**decay risk, not exposure**. One line in `CEILINGS` closes it. **Temporary debt.**

### P3-6 · The compliance baseline I own is stale, and the feature map is a draft

`.claude/context/security-compliance-baseline.md` carries *"Verified 24 Aug 2026"* on the
DPDP and CERT-In sections — **92 days old today, past the file's own 90-day rule**, which
01c predicted as R8 and said I would re-verify before this review. **I have not
re-verified it**, and I am not going to do it inside a release review: the two live
questions it would touch (C1 biometric classification, C2 retention) are counsel's, not
mine, and a half-done re-verification is worse than a dated one.
`.claude/context/compliance-feature-map.md` is still *"Version 0.1 · 24 August 2026 ·
DRAFT"* with `?` in most of the Status column. Both are mine. **Dangerous debt only if it
gets quoted at a customer**; the honest move is to date-stamp what we say and re-verify
before the next questionnaire answer. Owner: me, scheduled by Surbhi.

### P4-1 · SEC-9's browser-level assertion is absent

Covered twice over by the refusal (ALV-436, proven by running) and by `esc`, so this is a
note, not a gap.

### P4-2 · `esc` does not escape the apostrophe, and ids go inside inline handlers

`portal.js:265-270` escapes `& < > "` but not `'`. The values placed inside
`onclick="rnOpenRecord(&quot;…&quot;)"` are server-generated ids (`RN-00070`,
`HR-EMP-…`), the attribute is double-quoted and the inner JS string is a decoded `"`, so
an apostrophe is inert there. It is a sharp edge, not a hole. Worth knowing if an id ever
becomes user-named.

### P4-3 · `list_people`'s docstring describes a gate the code no longer has

The docstring (`:300-310`) still says the list "is empty when the organisation has not
asked for **confirmations**" and attributes it to ALV-430's switch. The code reads
`notices_are_on` — 088's own switch — and a test exists precisely to say the confirm
switch does **not** decide the paper round (`:566`). Lesson 5: a wrong explanation sends
the next person to the wrong file. One comment.

### P4-4 · A failed record can leave an orphan image on disk

`_save_the_photo` writes bytes through Frappe's File save; if a later photo in the same
call is refused, the transaction rolls back and the File row goes, but the file on disk
may not. 081's orphan job filters its own kinds and does not cover notice attachments.
Unreachable by URL (no File row → `find_file_by_url` fails) and only on a failed
transaction. A data-remanence note.

## 7 · Worries — things I cannot yet state as a finding

Clearly separated, as the rule requires. None of these has an actor, a path and a result.

1. **Collusion.** Two HR people can record a page nobody signed. SEC-4 stops one person
   doing it alone; nothing stops two. That is 01c's R1, and it is not solvable by
   structure. A worker with no app has no way to see what was recorded about them.
2. **A fresh photo of an old page** passes the reuse check (R3). The month and reference
   on the paper are the only defence, and the dialog does not show the reference (P3-2).
3. **The first real signed page.** No real-photo legibility or weight measurement has
   been shown to me (01c OPS-8). If a real A4 page at 1,600 px and ≤ 1 MB turns out to be
   unreadable, the evidence is worthless and nobody finds out until a grievance.
4. **Tenant `Custom DocPerm`.** Every permission statement above is about the role rows in
   this diff, measured on a dev test site. A tenant that has edited `Custom DocPerm` on
   `Alvoraa Photo Access Log` or on `Attendance Request` could differ. I would need
   read-only access to each live site to say otherwise, and I did not take it.

## 8 · What I could not check, and what I would need

- **Nothing on production.** I did not connect. If you want the live answers — does the
  switch column exist at DTC and Grace, is it 0, are there any `Alvoraa Register Notice`
  rows, are the joiner rows in the access log the same shape there — that is a short
  read-only script, and it should run before the switch is ticked, not before the push.
- **Whether gitleaks finds anything in the 17 unscanned commits.** It is not installed
  locally and I did not install it. P1-1.
- **The Error Log leak end to end** (P3-3). I read the mechanism in installed Frappe; I
  did not force an exception in `record` and read the row.
- **Whether the "fails first" breaks in 01c were actually performed** for every control.
  Two are described in test docstrings. There is no test report (§0).
- **The SPDI Rules' own text and the gazette date** behind C1. That is counsel's, and
  01c's question for them is already written.

## 9 · Residual risk — proposed. Nothing is accepted until Surbhi says so

| # | Risk | From | Label | Owner / date |
|---|---|---|---|---|
| R1 | Collusion or forgery: two HR people record a page nobody signed | 01c, unchanged | intentional trade-off | **needs her name and date** |
| R2 | Wrong person's page recorded; the dialog does not even show the reference | 01c + P3-2 | acceptable simplification, now slightly worse | **needs her name and date** |
| R3 | A fresh photo of an old page passes the reuse check | 01c, unchanged | acceptable simplification | — |
| R4 | The uploading HR person owns the File for ever — and can **delete** it, not only read it | **new, P2-1** | **dangerous debt if left unnamed** | **Surbhi, before switch-on** |
| R5 | Once printed, the paper is out of our control | 01c, accepted 21 Nov 2026 | intentional trade-off | accepted |
| R6 | Joiner export and purge rows are now invisible to HR Manager in the access log | **new, P2-2** | intentional trade-off **if accepted in writing** | **Surbhi** |
| R7 | Photos kept with no deletion until C2 is answered; every backup copies them | 01c, unchanged | temporary debt | removed by the purge slice |
| R8 | The baseline is 92 days old and the feature map is a 24 Aug draft | 01c R8, now realised | temporary debt | **me, scheduled by Surbhi** |
| R9 | An in-scope HR Desk view of a signature photo writes no row in our own access log | **new, P2-3** | temporary debt | removed when a viewer is built |
| R10 | The notice covers only 087-flow punch fixes, so corrections made by editing check-ins directly produce no notice | **new, C4** | **a question for counsel, not a debt** | **Surbhi + counsel** |

## 10 · Subtract pass

I read this back asking only what I could delete.

**Removed:** a separate threat-model section (01c §2 is unchanged and re-stating it is
noise); a per-endpoint rate-limit table (the limits are asserted by four tests and nothing
about them changed); a DevOps paragraph on the migrate cost of the new index (not mine,
and `07-devops-inputs.md` owns it); a fourth worry about `frappe.get_cached_value` on a
just-created column (it fails closed, so there is nothing to say); and two P4s that were
really naming preferences.

**Kept, deliberately:** every "proven by running" line, because this review's whole value
is the difference between what 01c predicted and what the code and the framework actually
do — and on three points (the child-table join, the File owner's delete right, the
employee-less joiner rows) the prediction and the reality differ.

**I added no new requirement, no new gate and no new control.** P1-1 is one command,
P3-5 is one line in a dict that already exists.
