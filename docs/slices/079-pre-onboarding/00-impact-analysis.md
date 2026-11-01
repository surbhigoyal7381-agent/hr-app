---
slice: 079-pre-onboarding
artifact: 00-impact-analysis
author: hrms-fullstack-engineer
date: 2026-11-01
status: written at the start of the build. Surbhi's 00-decisions.md §6b and the build
  instruction closed the three gates the spec left open (OQ-1, OQ-2, OQ-4), so this
  document records the strategy rather than asking for it again.
scope: 23 of 25 stories. US-11 and US-12 (the Aadhaar masker) are HELD.
---

# 079 · Pre-onboarding — impact analysis and strategy

## 0 · The answer first

**The slice is one `before_request` hook.** Everything else is ordinary work on code
that already exists. Today a signed-in account with no `Employee` record falls through
`auth.home_page_for` → `_portal_home_for` → `/hrms-employee`
(`alvoraa_portal/auth.py:41-49`, `410-427`), and `www/hrms_employee.py:get_context`
refuses only `Guest`. A joiner account is exactly that user, so **until the gate exists
the login is wider than the bearer link it replaces.** That hook is P1 and it is built
first.

**Three things I verified against the installed source before designing anything**
(Frappe v16.33.1, read in `hrlocal-078` on 1 Nov 2026):

| What | What the source says | What it changes |
|---|---|---|
| **⚠ D4 / AC-17** — can the sign-in page tell "ended" from "wrong password"? | **Yes, and Frappe already does it.** `frappe/auth.py:282-289`: a wrong password fails with `"Invalid login credentials"`; a **correct** password on a disabled account fails with `"User disabled or missing"`. Both reach the browser as `message` on `/api/method/login` | `JOIN-ENDED` is a real state with no server change. The login page reads the message |
| **⚠ OQ-8 / AC-15** — the lockout numbers | `allow_consecutive_login_attempts = **10**`, `allow_login_after_fail = **60 seconds**` (site `test078f`, and Frappe's own shipped defaults) | **The design's "Locked for 30 minutes" is wrong.** The copy is generated from the settings, so it says 10 tries and one minute. Departure from `01b` §4.2, recorded |
| **⚠ S3 / AC-7** — `allow_login_using_mobile_number` | The field exists (`system_settings.json`) and `User.find_by_credentials` resolves it against **`User.mobile_no`** (`user.py:831-843`). It is **`0`** on this site | The assumption in the spec is confirmed. It is **not patched** — it is a deliberate tenant change, so `make_sign_in` refuses a mobile login id while it is off and names the setting |
| **AC-8** — is a sign-in attributable? | **Yes.** `add_authentication_log` writes an `Activity Log` row per attempt, success and failure (`activity_log.py:72-81`) | §14's detection claim stands |

## 1 · Which rung of the ladder, and why every cheaper rung was rejected

| Piece | Rung | Why not cheaper |
|---|---|---|
| The joiner account | **2 · configuration** — a stock `Website User` | Nothing cheaper exists; rung 1 has no "account that opens one page" |
| The joiner role | **2 · configuration** — one `Role`, `desk_access = 0`, **in no permission row anywhere** | A role with rows would be a permission surface, and Frappe would create it *with* desk access (`announcements.py:565-578`) |
| Eight new settings keys | **2 · configuration** — `DefaultValue` keys through the existing `ACCESS_GRANTING` path | A settings DocType buys a permission surface, a migration and a list view and does nothing a key with a `Version` row does not |
| **The one-page gate** | **3 · customisation** — a copy of `lock_until_password_chosen`'s shape, failing closed | Rung 1: Frappe has no "this role may reach one page" switch — `Role.home_page` decides a landing, not a boundary. Rung 5: a per-route permission DocType for a list of ten strings |
| Session-bound endpoints | **4 · new code**, replacing new code | The token machinery it replaces is bigger than what replaces it |
| The second retention pass | **4 · new code**, one function in the job that already runs | One setting cannot express two periods. Verified: `erase()` deletes files **and** fields together |
| The `Version` sweep | **4 · new code**, two lines plus a delete | `track_changes: 0` would lose HR's own edit history, which §14 promises |
| **No new DocType, no new app, no new page, no new scheduled job** | — | Nothing in the 23 stories needs one |

## 2 · Functional impact

### 2.1 Cross-module reach, and a grep of every caller I change

| Function I change | Callers found (grep, whole repo, 1 Nov) | What I do about it |
|---|---|---|
| `auth.home_page_for` | `auth.on_login`, `auth.get_portal_redirect`, `auth.route_the_bare_root`, `auth.update_password`, `hooks.get_website_user_home_page`, and 9 test modules | **One branch added at the top.** Signature unchanged, behaviour for every existing user unchanged |
| `joiner_invite.invite_joiner` | `alvoraa_joiner_submission.js`, `test_joiner_078.py` (×14 through `_Base._invite`) | Replaced by `make_sign_in(submission)`. The Desk button and the tests move with it |
| `joiner_invite._web_form`, `_drop_request` | `joiner_public._open`, `joiner_invite.cancel_invite`/`purge_submission`, `joiner_housekeeping.expire_the_dead_links` | **All deleted.** No token, no anchor record, no clear-text key |
| `joiner_public.open_invite` / `submit_invite` / `upload_invite_file` | `www/joiner.html` only, plus tests | Rewritten onto the session |
| `alvoraa_joiner_submission.erase` | `joiner_housekeeping` (×3), `joiner_invite.purge_submission` | Extended, not changed in shape |
| `my_profile.get_my_profile` / `save_my_profile` | `portal.js` (`mypLoad`, `mypSaveDetails`), tests | `get` gains `required`; `save` is untouched in rule |
| `people_settings.get_people_settings` / `set_people_setting` | `portal.js` (`ocsLoad`, `ocsSave`), tests | Four keys added to the allow-list |
| `people_fields.LIST_KEYS` | `settings._set_access_setting`, `people_fields.allowed`/`off_list`, `my_profile._ticked`, `people_settings` | Three keys added. Every reader intersects, as today |

| App / module | What this slice does to it |
|---|---|
| **`alvoraa_portal`** | `auth.py` (the gate, one landing branch), `hooks.py` (one hook, one route), `joiner_invite.py` (rewritten), `joiner_public.py` (rewritten), `joiner_housekeeping.py` (one pass, one ending), `www/joiner.*` → `www/joining.*`, `www/alvoraa-login.html` (a joiner state), `my_profile.py`, `people_settings.py`, `public/js/ess/portal.js`, the submission doctype and its JS, one patch |
| **`hrms`** | `alvoraa_org_structure/settings.py` (eight keys, their ranges, their labels), `people_fields.py` (three list keys). **No HR doctype is touched** |
| **`erpnext`** | **Nothing.** No `Employee` is created, read or written by anything a joiner can reach |
| **`frappe`** | A `User` row, one `Role`, `Activity Log`, `Notification Log`, `Version`, `File`, `Sessions`. **No framework file is edited.** `System Settings.allow_login_using_mobile_number` is a tenant change we refuse to patch |
| **`alvoraa_goals`, `alvox_compensation`** | Nothing |
| **HRMS domains** | Org structure (the settings card) and employee records (My Profile). **Attendance, leaves, payroll, appraisals, goals and learning are untouched** — and that is load-bearing: no `Employee` row means no `Attendance` row, which is the whole of decision 1 (the DTC back-dated-joining trap) |

### 2.2 Personas

| Persona | What changes |
|---|---|
| **CXO** | Nothing on screen. One sentence on HR's screen is their answer: a joiner is not a seat, not headcount, not on the chart |
| **HR Manager** | Gains "Make the sign-in" with a six-line message shown once, and a refusal until the employer's own values are set. **Loses `report` and `export`** on the submission doctype (counsel 9) |
| **HR User** | **Loses `report`.** Keeps read |
| **System Manager** | Four new pickers and four new values on the Organisation Settings card. The only remaining `export` |
| **Employee** | My Profile: `Needed` marks that never block a save, and two columns |
| **New joiner** | A login that opens one page. A new persona this product has never had |

### 2.3 What narrows, and what widens

**Nobody gains sight of anybody else.** Four changes, three of them narrowing:

1. **Narrows:** HR Manager and HR User lose the Desk report view and export on the doctype.
2. **Narrows:** the public surface goes from one guest page and three guest endpoints to **zero of each**.
3. **Narrows:** `Version` rows stop carrying the joiner's typed values at all.
4. **Widens, by one object:** one `User` row per invited joiner, holding their name and
   their number. Visible to System Manager in a user list. **Erasure must delete it**, and
   does.

## 3 · The data doors, named before the build

`data-doors.md`: a rule that lives only in our portal code is not a rule. The record limit
here lives in **three** Frappe-enforced places, and our page adds nothing on top:

1. **The role holds no permission row anywhere** — so `/api/resource/*`, `reportview.get`,
   `frappe.client.*`, link search, reports, share, assign and comment all have nothing to
   return. There is no scope to get wrong, because there is no read.
2. **`Website User`** — Frappe refuses it at `/app` by construction.
3. **The gate** — a `before_request` allow-list, failing closed, covering `"/"` with a
   `cmd` as well as every path.

The joiner's own row is reached by server code bound to `frappe.session.user`, never by
their own permissions and never by an argument they can post.

**Bypass count.** `079-SEC-7` demands the number go **down**. My plan, argued per bypass:

| File | Before | After | Why |
|---|---|---|---|
| `joiner_public.py` | 5 | **2** | With a session and a bound row, three go: the two reads that found what the token was bound to become one read of the caller's own row, and the submission save keeps one because the `Employee`-less joiner holds no write on the doctype. The `File` insert keeps one — nobody holds create on `File` for a row they cannot read |
| `joiner_invite.py` | 4 | **3** | The `Web Form` anchor and the `Web Form Request` row go with the token. The `User` and `Role` inserts arrive (HR Manager holds neither) |
| `joiner_housekeeping.py` | 6 | 7 | One more read for the document pass. A job with no session |
| the controller | 4 | 6 | The `Version` sweep and the `User` delete |
| `www/joiner.py` → `www/joining.py` | 0 | 0 | Reads no submission at all |

Net for the two modules the requirement names: **9 → 5.** The two that grow are the
scheduler and the erase path, which run with no session at all and were already counted.

## 4 · Non-functional verdict, dimension by dimension

| Dimension | Verdict | Why |
|---|---|---|
| **Performance** | **neutral for staff, improves for the joiner** | The gate costs one string `startswith` and, on `"/"` only, one dict read — then `frappe.get_roles()`, which is cached. **It must add no database read for a member of staff**, and the ordering is what guarantees that. The joiner's page loses a `Web Form` lookup and a `Web Form Request` read per call and gains one indexed read of its own row |
| **Security** | **improves, materially** | A bearer URL becomes an identified account; the public write surface goes to zero; two export doors close; the bypass count in the two modules the requirement names halves. **It degrades in exactly one way, and the gate is what answers it:** an account inside the site is a bigger thing than a URL, so the gate is P1 and fails closed |
| **Reliability** | **improves** | The gate fails **closed**, deliberately unlike its ancestor — a false denial costs one person a phone call, a false allow puts an unidentified account in the portal. The five account endings happen in one transaction. The daily job stays safe to run twice |
| **Scalability** | **neutral** | Tens of rows per tenant per year. One `User` per invited joiner, deleted with the row. No new query runs per employee or per request |
| **Maintainability** | **improves** | The token machinery, the `Web Form` anchor, `_web_form()`, `_drop_request`, the fragment handling and 078-SEC-19's recorded deviation all **go**. That is the slice's largest subtraction and it is a deletion, not a replacement |
| **Data integrity** | **improves** | `erase()` stops leaving the joiner's values in `tabVersion` and stops leaving a named `User` row behind. Both clocks measure from a stored stamp, never from `modified` |
| **Compliance / privacy** | **improves** | Counsel's rulings 3, 4, 6, 8 and 9 each gain a mechanism. The joiner's tick ships empty; the notice is the employer's words and the page refuses without them |

**The one budget this slice could have blown is the masker's**, and it is held. Nothing
else here is unmeasured.

## 5 · Risks, trade-offs, and the consequences nobody asked about yet

| # | Risk | What I do about it |
|---|---|---|
| R1 | **The gate locks out a staff member** if its role check is wrong | It keys on one role name, checked after `Guest`/`Administrator` are returned. The fail-closed branch only fires for a session **that holds the joiner role** — an exception while *reading* the roles returns early for everybody else. A test proves a staff session is unaffected |
| R2 | **`allow_login_using_mobile_number` is site-wide.** Every employee at that tenant can then sign in with their mobile number | Surbhi accepted it with that named (decision 6b). **I do not patch it.** `make_sign_in` refuses a mobile login id while it is off and names the setting, so a tenant turns it on deliberately or uses the email route |
| R3 | **A word-style password is weaker than a hash** | Built as the design asks, because every string on the sign-in page promises that format. 96³ × 100 ≈ 88 million, against a 10-try lockout and a 7-day life. **Flagged for the security reviewer** — it is D3 and it is theirs |
| R4 | **The draft now lands server-side before Send** | Resolved against 079-PRIV-5 in the spec's C2. The row already exists from the invite, so this is not a new object. Both clocks already cover an unsent row; a test ages one |
| R5 | **Dropping `web_form_request` leaves rows on dev sites** | A patch deletes any `Web Form Request` row for this doctype and the anchor `Web Form`. There are no live rows anywhere — the form ships off |
| R6 | **`Custom DocPerm` is the real table** on any site that has touched permissions (27 Oct lesson) | The patch removes the rows from **both** `DocPerm` and `Custom DocPerm` |
| R7 | **US-20 changes a page that has already shipped** | Surbhi's own decision (6b), her own fault to fix, one release instead of two. The change is two CSS rules and a DOM reorder; the DOM order is the reflow order, so no `order:` override |

## 6 · Parallel-work check

| | |
|---|---|
| **Incoming while I worked** | `94b1862c` ALV-278 — `alvoraa_portal/alvoraa_portal/tests/fixtures_078.py`, test fixture only, 8 lines. Read in full: it re-reads the `Employee` before each child-row save and asserts a file landed. Nothing of mine touches it. **Rebased onto it before starting** |
| **Files I will change that somebody else is in** | **None.** ALV-278 owns `tests/fixtures_078.py` and I do not open it. My own joiner fixtures go in a new `fixtures_079.py` |
| **Hot files I touch** | `hooks.py` (one line in `before_request`, one in `website_route_rules`), `portal.js`, the submission DocType JSON, `patches.txt`. Each a small, additive edit at a named place |
| **Plan** | Sequence, not split. My branch is `slice/078-positions-faces` in my own worktree; I rebase on `origin/dev` before every commit; I do not push |
| **The bench** | `hrlocal-078`, site `test078f`. The shared `hrlocal-bench` is not touched |

## 7 · Strategy — the order of the build

1. **The settings layer** — eight keys, their ranges, their labels, the three list keys.
2. **The account** — the role, the credential, the five endings, the preconditions.
3. **The gate** — `home_page_for`'s branch, then the `before_request` allow-list, failing closed.
4. **The endpoints** — onto the session, the token machinery deleted.
5. **Erasure and the two clocks** — the `Version` sweep, the `User` delete, the document pass.
6. **The doctype** — two fields, two permission rows, the patch.
7. **The screens** — `/joining`, the sign-in's joiner state, My Profile's marks and columns, the fourth picker.
8. **Hindi**, then the tests, then the subtract pass.

## 8 · What I will not build, and said out loud

- **US-11 and US-12, the Aadhaar masker.** Held by Surbhi pending counsel. **No stub, no
  dead configuration, no half-masker**: the Aadhaar document type is simply not offered,
  and `masked_with` is the only field this slice lands for it — because the
  affected-record query it exists for cannot be retrofitted onto files already stored.
  *(Even that is a judgement: see the implementation notes' subtract pass.)*
- **An unmasked bytes-included export** (dropped in the spec §3).
- **A record that HR read a submission** (dropped, named debt R-6).
- **Any mail or SMS channel for the credential.**
- **A consent tick, a welcome-back page, a forced password change, a navigation.**
