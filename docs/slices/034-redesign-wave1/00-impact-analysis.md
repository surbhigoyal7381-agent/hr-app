---
slice: 034-redesign-wave1
artifact: 00-impact-analysis
author: hrms-fullstack-engineer
date: 2026-09-22
status: waiting for approval — no code written
inputs: [docs/slices/009-ess-portal-redesign/00-assessment-and-plan.md, 01b-ux-design.md, appendix-a-frame.md, 09-brand-assets.md, 00f-decisions-2026-09-22.md, prototype-v2.html, docs/slices/013-mobile-app/00-sequencing-recommendation.md, docs/slices/012-leadership-view/07-devops-inputs.md (OPS-26, OPS-31), docs/slices/030-store-hr-scoping/00-impact-and-fix.md, .claude/context/nfr-budget.md]
base: origin/dev 1c4e84c
---

# Wave 1 of the portal redesign: the new frame

## Bad news first

1. **This slice has no functional spec and no security, privacy or DevOps requirements
   yet.** The 009 folder holds the plan, the design and four appendices, but no `01c`,
   `02` or `07`. The Definition of Ready fails on at least four boxes. This analysis is
   written against appendix A and `01b` §5, which are detailed, but they are not a spec
   with acceptance criteria. **You decide whether those three documents come first
   (my recommendation) or whether appendix A stands in for them.** Question 1.
2. **The landing page weighs 1.04 MB, and it is sent uncompressed.** `deploy/nginx.conf`
   has no `gzip` lines (OPS-26 was never built). Now that the portal is the first page
   everyone sees, this matters more than anything the frame does. The frame itself can
   only add bytes; it cannot fix this. Compression is a DevOps change, outside this
   slice, and I recommend it goes in before the swap.
3. **The design's people search is wider than the rule you already set.** `01b` §5.5
   says an employee finds their team, their manager and "the leadership". Your decision
   Q-c (14 Sep) says **only their own reporting line, downwards**, and that is what the
   server enforces today (`_search_scope`). Building the design as drawn would widen
   what employees can see. I have not planned that. Question 5.
4. **Store-level HR can see beyond their store in two places the frame uses.** The
   approvals count and bell list (`goals_api._pending_approvals_scope`) and people search
   (`_search_scope`) both scope HR by company, not by store. Slice 030 fixed three
   readers and named these as next. The frame must not put their numbers and names on a
   bigger stage, so I propose fixing both here.
5. **Wave 1 is bigger than the plan's 6–8 days.** My estimate is **10–12 build days**.
   The extra comes from shipping it safely alongside two live tenants, the store-HR
   scoping, the five states, and teaching every existing check to read the split page.
   Breakdown in §8.
6. **I could not check four Frappe details, because the bench was off limits for this
   run.** Listed in §9. Each must be checked against the installed source before the step
   that relies on it.

---

## 1. What came in, and who else is working

**Base.** Worktree `.claude/worktrees/034-redesign-wave1` on `slice/034-redesign-wave1`,
from `origin/dev` at `1c4e84c`. Nothing edited except the two documents this run owns.

**Incoming since local `dev` (`3ab09f1`), 9 commits:** mobile app stage 1–2 and join
screens (013: `71e02c1`, `a473e22`, `debe06b`, `b6021ad`, `0233063`, `7c1d069`), worker
health (026: `97d2382`, `7b7a339`), the private image package (033: `1c4e84c`). Files:
`mobile/field-app/**`, `.github/workflows/*`, `deploy/compose/`, `deploy/envs/`,
`deploy/Dockerfile` (one line), `scripts/check_workers.sh`, runbooks, slice docs.
**None of them touches the portal page or any file this slice would change.**

**The main checkout** holds another session's staged Android files
(`mobile/field-app/android/**`). Not mine; not touched; not needed.

**The page's recent history.** `hrms-employee.html` is 18,429 lines and had 46 commits
in 14 days. The last two (21 Sep, ALV-17, the cheap bell count) were made under a
different git name ("Claude <noreply@anthropic.com>"), and three remote branches
(`origin/claude/*`) carry copies of that work. **That looks like another developer or a
cloud session. I cannot see who.** Question 11.

**Unmerged work on the page today:** none in local branches except
`release/2026-09-main` (a release branch, one commit already on dev). Work that is
*waiting* to edit the page: slice 012 push 2 (leader screen) and any 010 follow-ups —
both agreed to wait for the redesign (`013/00-sequencing-recommendation.md` §3).

**Work board.** Slice number 034 reserved, and a docs-only row added, before the
worktree was created.

---

## 2. Functional impact

### 2.1 Cross-module

| App | Touched? | How |
|---|---|---|
| `alvoraa_portal` | **Yes, most of it** | The page, new include files, a preview page, two new server modules (`frame_api.py`, `inbox_api.py`), one body change in `goals_api._pending_approvals_scope`, the design-system token, the brand-colour script, tests and check scripts |
| `hrms` (our own `alvoraa_org_structure`) | **Yes, one function body** | `_search_scope` narrows store HR to their branches, using `access.permitted_branches`. `access.py` itself is not changed |
| `alvoraa_goals` | No | — |
| `alvox_compensation` | No | — |
| `erpnext`, `frappe`, upstream `hrms` | **No edits** | We read `User.language` and write it for the caller only |

### 2.2 Callers of everything I would change (grep, not guesswork)

| Function | Callers found | Effect of the change |
|---|---|---|
| `goals_api._pending_approvals_scope` | `get_pending_approvals` (goals_api.py:1198), `get_pending_approvals_count` (:1277) | Both narrow to `permitted_employees()` for store HR. The bell list and the count keep agreeing. Tests: `test_review_fixround_010d.py` (6 mentions) must still pass |
| `hrms.alvoraa_org_structure.api._search_scope` | `search_people` (api.py:565) only | Org-chart search for store HR narrows to their store. Page caller: `ocSearch` (hrms-employee.html:5377) |
| `hr_api.get_portal_context` | page :7726; `vendor-portal.html:951` calls **`portal_api`'s** function of the same name, not this one | **Not changed.** `get_frame` calls it |
| `hr_api.get_available_features` | page :7817; `tests/portal_notes_test.js` stub | **Not changed.** `get_frame` calls it |
| `hr_api.get_switch_target` | page :7764 | **Not changed.** `get_frame` calls it |
| `design_system.html` `--fs-xs` | 313 uses in the employee portal, 19 in the driver portal, 20 in the vendor portal; 0 elsewhere | Text set with this token grows by 1 px on those three pages |
| `brand_color.html` | included by `design_system.html`, so six pages | Exposes a "run again" function so the theme switch can re-apply the tenant colour. No change to what it draws |
| `switchPanel(name, el)` | every panel, many buttons | **Kept, same name and signature.** The new router calls it. Moved into a shared include, not rewritten |
| `toast(msg, type)` | many callers | **Kept, same signature.** Gains `role="status"` on its container |
| Anything reading `hrms-employee.html` as a file | 11 Python tests, 7 check scripts, 5 JS DOM tests, CI step | All taught to read the page with includes expanded (§5.3) |

### 2.3 Personas

| Persona | What changes |
|---|---|
| **Employee** (Rahul) | A new menu (Me · Time · Pay · Growth · Company), four phone buttons plus More, a bell and search on desktop too, a profile menu with log out. No Pay group where the tenant has no payroll. Same screens inside. Slightly larger small text |
| **Manager** (Sandeep) | Adds Team. Phone buttons Home · Team · Inbox · Time. The Inbox count covers approvals, policies and their own requests |
| **HR Manager, company-wide** | Adds the Company group (HR analytics, Reviews (HR), Policies, Org settings, Data to review). Reviews come from two separate places: **Team › My team** for their own reports, **Company › Reviews (HR)** for everyone else (decision 37) |
| **Store-level HR** | Same as HR, but **their counts and search now stop at their store**. Today they do not |
| **Owner who holds HR** (Kamal) | Home · Inbox · Company · Team on the phone (decision 2) |
| **CXO across companies** | Not designed (`01b` §11). Gets the HR frame, scoped by `permitted_companies`. Named as a gap, not solved |
| **Vendor / driver** | Nothing. They land on their own portals, and only where the tenant has the `vendor` feature (`auth._portal_home_for`). The feature appears in no menu |

### 2.4 HRMS domain

No business rule changes. Leave, attendance, payroll, appraisals and goals keep their
logic. The frame only changes how people reach them, and what is counted:

- **Leave:** approvals waiting on me (`leave_approver = me`, Open) and my own open requests.
- **Attendance corrections:** counted where they sit **today** (HR's queue). Decision 1
  (the manager decides) changes the routing in Wave 2, and the count follows it then.
- **Shift requests:** counted only where the tenant has shift types.
- **Goals and KPIs:** pending updates, from the existing scope helper.
- **Policies:** unacknowledged, published policies the person may read.
- **Payroll:** the Pay group depends on `plan_payroll`. Today the Finances item has no
  plan check, so a tenant without payroll shows a tab that fails (FR-15). Fixed here.

---

## 3. How it ships without breaking the two live tenants

`dtc.alvoraa.co` and `aahr.alvoraa.co` run `main`. Nothing reaches them until you release
`main`. The real risk is therefore not a single push. It is this: **every production
release takes everything on `dev`.** If Wave 1 is half-built on `dev` when a production
fix is needed — and the first client goes live in the first week of October — the
release carries a half-built frame, or waits.

### The three options

| Option | How | For | Against |
|---|---|---|---|
| **A. Feature flag** | One setting per site: old frame or new | Instant per-tenant rollback without a deploy | Both frames live in the product for as long as the flag exists; every panel change is tested twice; CLAUDE.md §4 says no flags; a flag like this rarely gets removed |
| **B. Change in place, step by step** | Each step edits the live page | Simple; one frame at all times | `dev` holds a half-new portal for about two weeks. Any production release in that time ships it to live tenants, or the release waits. It also means HR users see the portal change several times |
| **C. Parallel page, one swap** *(recommended)* | Build the new frame at a preview address. Both pages share the same panel code. When it is proven on dev, one commit makes `/hrms-employee` use the new frame and deletes the preview | `dev` stays releasable every day. The live address never shows a half-built frame. The swap is one commit, so the rollback is one `git revert` | Two frames exist in the code for 2–3 weeks. The preview address exists on production if a release happens mid-wave |

### Why C

- The release train stays open. Slice 013, the 010 follow-ups and the go-live fixes can
  go to production at any time without waiting for the frame.
- The live address changes exactly once, on a day you choose.
- It is **not a feature flag**: nothing decides at run time which frame someone gets. The
  preview page is a normal page that is deleted in the swap commit.
- The panels are **not** duplicated. After step 1 (§5), every panel lives in its own
  include file, and both pages include the same files. Only the frame differs.

### The details of C

- **Preview address:** `/hrms-employee-next`, a new `www` page with the same login guard.
  Frappe routes `www` pages by file name, so `hooks.py` does not change.
- **Who may open it:** I recommend **System Manager only** until the swap, with one check
  in its `get_context` that is deleted with the page. On production that means a tenant's
  own admin could open it, and nobody else. Every endpoint it calls keeps its own
  server-side checks, so this is about not showing unfinished screens, not about data.
  Question 3.
- **The old frame is frozen.** No new work goes into the classic sidebar, header or
  bottom bar during the wave. Fixes to panels go into the shared panel files and reach
  both pages at once.
- **The swap commit:** `/hrms-employee` switches its frame includes to the new ones; the
  preview page and the classic frame files are deleted; the tests that pin the classic
  frame (`test_brand_logo_025`, `test_waves_5_6`'s `applyPlanNav` tests) are repointed at
  the new frame in the same commit, on purpose, so somebody has to read them.
- **Rollback:** `git revert` of the swap commit, then a normal deploy. How long a
  production deploy takes decides the real rollback time. The DevOps engineer should
  state it in `07` §4. Question 4 asks when the swap reaches production relative to the
  first client's go-live.
- **What I recommend against:** keeping a "classic" link or a per-tenant fallback after
  the swap. That is option A by the back door.

---

## 4. The strategy — how the frame is built

The build order follows appendix A §G, adapted to option C. Each step is its own commit
in the worktree, with its tests.

### Step 1 — Split the page into include files. Nothing changes on screen.

- The page today is one CSS block (lines 12–2308), the HTML (2311–4994) and one script
  block (4995–18425). The script has four top-level wrappers (IIFEs — functions that run
  once and keep their variables private); the goals one runs from line 9888 to 18400.
- **Jinja includes are pure text.** `{% include %}` pastes the file where the tag is.
  So a file can end in the middle of a wrapper and the page still renders the same bytes.
  That is what makes a big split safe.
- **Files** go in `alvoraa_portal/templates/includes/ess/`, cut at the section banners
  the page already has, one owner area per file:
  `frame/` (shell, sidebar, phone header, bottom bar, overlays — the classic frame),
  `shared/` (helpers `api`, `toast`, `fmtDate`, `gpFetch`, `switchPanel`, form helpers),
  and one folder per area — `home`, `time` (attendance, my days, insights, late rule,
  leaves, shift and attendance requests), `pay` (finances, salary, expenses, encashment,
  advance, payslip drawer), `team` (team panel, scorecard, charts, employee drawer),
  `company` (analytics, data to review, org chart, policies and documents, org settings,
  appraisal setup), and `growth` (the goals wrapper, split at its five existing banners).
  About 25 files, each with a CSS part, an HTML part and a JS part where it has them.
- **JS and CSS include files hold no Jinja** (checked: no `{{` or `{%` in either block),
  so a later move to cached files (OPS-31) is a rename, not another restructure.
- **Proof, in the same commit:** a test renders the page's includes as text and compares
  it with the original file. **It must be byte-for-byte identical** apart from the
  include tags. If it is not, the commit does not go.
- **Every existing check learns to follow includes in the same commit** (§5.3). If this
  is skipped, checks keep passing while reading only a shell — the worst outcome, because
  it looks like safety.
- Add `container-type` to the layout test's banned properties (the designer's handoff).

### Step 2 — The preview page and the frame shell

- `www/hrms-employee-next.html` + `.py`: the same `get_context` as today (login guard,
  CSRF token, `get_branding()`), plus the System Manager check (Question 3).
- **Frappe's website bar is removed** (empty navbar block) **in the same commit as the
  profile menu**, so log out never disappears (`01b` §14 item 3).
- **The rail:** tenant mark from `brand_mark_url` with the letter underneath and
  `onerror="this.remove()"` (`09-brand-assets.md`), tenant name as text, `alt=""`. No
  asset path written in the template.
- **The top bar:** group, then page title in words; on a deep page the group is a link
  back; search and bell on desktop and phone.
- **The profile menu:** name, role, tenant; **Language**; **Light or dark**; My account
  (`/me`, Frappe's own page); Switch to the full desk (from `get_switch_target`, only when
  it returns a target); Tenant admin (**only** for a System Manager on the control plane,
  exactly as today — Question 9); **Log out**.
- **Phone layout with `@media (max-width: 760px)`**, never a container query (D1).
- **`--fs-xs` 11 → 12 px** in `design_system.html`, in a commit of its own, with a visual
  pass at 390 px on the employee, driver and vendor portals (decision 5).

### Step 3 — The menu list, one start-up call, the bottom bar, routes

- **One list** of entries — group, label, icon, panel, tab, and a visibility rule — draws
  the rail, the bottom bar, the title and page search. An entry exists only if the
  person's role, plan and features allow it. No greyed items.
- **Where each current panel goes:** appendix A §B, unchanged, plus decision 37: *Team ›
  My team* opens `team`; *Company › Reviews (HR)* opens `goals` on its `hr` tab through
  the existing `gpShowTab`. Someone who is both sees both, under different groups, with
  different titles. The duplicate "Checkin Log" item becomes a tab under Time (FR-19).
- **Visibility rules move from `applyPlanNav` / `loadPortalContext` into the entries.**
  The rules themselves are kept exactly: `plan_analytics !== false` (absent is not
  "not bought"), `plan_policy_library`, `plan_org_structure`, `goals`, the request
  features, `is_hr`, `is_manager`. New: Pay needs `plan_payroll`.
- **One start-up call, `frame_api.get_frame()`**, returns what three calls return today
  (`get_portal_context`, `get_available_features`, `get_switch_target`) by calling those
  same functions on the server. Three round trips become one, and the race between two of
  them (FR-03) disappears. The old endpoints stay for their other callers.
- **Bottom-bar sets** (four plus More), from the menu list:

  | Person | Buttons |
  |---|---|
  | Employee, tenant has payroll | Home · Time · Pay · Goals |
  | Employee, no payroll | Home · Time · Inbox · Goals |
  | Manager | Home · Team · Inbox · Time |
  | Owner / HR with reports | Home · Inbox · Company · Team (decision 2) |
  | HR **without** reports (e.g. store HR) | **Not designed.** I propose Home · Inbox · Company · Time. Question 8 |

  If a button's page is not allowed for that person, the set falls back to the next
  allowed page, so a button never opens a refusal.
- **Routes:** `#time`, `#time/requests` and so on; the back button works; the router
  calls `switchPanel`. Focus moves to the page heading; Escape closes the menu and sheets.
- **The loaders stay where they are.** Home still calls its current loaders. The new boot
  runs what `loadPortalContext` does for panels today (team goals on Home, the notes team
  map, the Data-to-review badge), so nothing on Home is lost.

### Step 4 — One shared sheet, and an announced toast

- `ess.openSheet(title, body, foot)`: side sheet on desktop, bottom sheet on phone,
  `role="dialog"`, `aria-labelledby`, Escape closes, **focus is trapped and returned** to
  the control that opened it (FR-09 — the part the prototype does not do).
- `toast()` keeps its signature; its container gets `role="status"`.
- Existing drawers are **not** moved into the sheet in Wave 1. Each screen's wave does
  that. The frame uses the sheet for the profile menu and search.

### Step 5 — The Inbox count and the Inbox slot

- **New `inbox_api.py`** holds the definition of each thing that can wait on someone, in
  one place, so the count now and the list in Wave 2 cannot disagree:

  | Part | Source | Scope |
  |---|---|---|
  | Leave to approve | Leave Application, `leave_approver = me`, Open | personal |
  | Goal and KPI updates to approve | existing count queries | `_pending_approvals_scope`, now store-scoped |
  | Attendance corrections to decide | Attendance Request, draft, waiting | today's rule (`_may_review`), under the caller's permissions, not their own; store-scoped for HR |
  | Shift requests to approve | Shift Request, `approver = me`, Draft | personal, only if the tenant has shift types |
  | Policies to acknowledge | Policy Document, published, readable, not acknowledged | the policy library's own read rules |
  | My own open requests | my leave, my corrections, my shift requests, still waiting | own records only |

- **`get_nav_counts()`** returns a number per part and a total. The bell, the menu and the
  bottom bar show the same total. Counted live on each page load and after each
  decision. **Not cached**, so there is nothing to invalidate.
- **The policy part is batched.** Today's `get_my_policies` checks each policy in a loop.
  The count uses one query for readable policies and one for this person's
  acknowledgements.
- **The 1.5-second delay goes.** The count arrives with the page.
- **The Inbox page in Wave 1** is honest and small: one row per part that has something,
  with its number and a link to the screen where it is acted on today (Team, the goals
  approvals list, Policies, Attendance). A number never points at an empty page. Wave 2
  replaces the rows with the real list and decisions. Question 6.
- **Fix in the same step:** `_pending_approvals_scope` uses `permitted_employees()` for
  HR, so store HR's count **and** the bell list stop at their store. Question 7.

### Step 6 — Scoped search

- **Pages** come from the menu list, so search can never offer a page the person cannot
  open.
- **People** come from `search_people`, whose scope the server already enforces. The one
  change: `_search_scope` narrows HR with `permitted_branches`, so store HR finds only
  their store.
- **What a result returns:** name, job title, department, photo — never phone, email or
  a displayed employee number. The Employee record name travels as the link key only.
- **Where a person result goes in Wave 1:** there is no person sheet or directory until
  Wave 4. I propose it opens the org chart on that person where the tenant has
  `org_structure`; where it does not, search shows pages only. Question 5.
- The empty state says what you *can* find, matching the scope actually enforced.

### Step 7 — Theme and language

- **Theme** (Match my phone · Light · Dark): saved on the device; `data-theme` set in the
  page head **before** the design system and the brand colour run, so there is no flash;
  on a change, the brand-colour script runs again (it reads the theme once today).
- **Language:** the choice saves `User.language` for the caller only (new
  `frame_api.set_my_language`, refusing any language that is not enabled on the site)
  and reloads. Frame strings are wrapped in `__()` and English only in Wave 1.
- **The language row shows only when the tenant has more than one language enabled.**
  Today no tenant does (Hindi is disabled on PP Jewellers, Punjabi does not exist), so
  in practice the row is hidden in Wave 1 rather than offering choices that do nothing.
  Question 14.

### Step 8 — The five states

| State | How the frame does it |
|---|---|
| Loading | The shell and a page skeleton are in the HTML itself, so they paint before any call returns. No spinner on a blank screen |
| First time | Frame side only: empty Inbox reads "All clear". Home's own first-time state is Wave 2 |
| No permission | The item is not in the menu. A link to a page the person may not open lands on "This page is not part of your access. Ask HR if you think it should be." |
| One card fails | Frame-owned cards (counts, search) say what failed and offer Try again; the rest keeps working. Panels keep their current error handling until their wave |
| Whole page fails | If `get_frame` fails: one sentence, a Try again button, and a short reference the person can read out to HR. Never a server error |

### Step 9 — The swap

As in §3. Plus the measurements in §6, before and after, on the local copy.

### The mobile app (slice 013)

Wave 1 **leaves room** and builds nothing speculative: the bottom bar and top bar are
single elements that one class on the page root hides, and Check In is one entry in the
menu list. How the portal knows it is inside the app is for 013's My HR spec to define;
adding it then is a few lines. Building the detection now, with no agreed contract, would
be guessing.

---

## 5. The big page: how it is split without colliding with other work

### 5.1 The order

1. **Before the split:** every session with page work lands it on `dev` or holds it. I
   ask you to confirm nobody else is mid-edit in the page (Question 11). The split is a
   move of the whole file, so any branch with page edits made before it will not rebase
   cleanly.
2. **The split itself:** one commit, done in one sitting (about half a day), proven
   byte-identical, pushed to `dev` **on your word** as soon as it passes, so other
   sessions rebase onto it early. It is safe to release: it changes nothing on screen.
3. **After the split:** a branch that still holds old page edits re-applies them in the
   matching include file. I will write a table in the implementation notes: old line
   range → new file, so this is mechanical.
4. **From then on,** each wave and slice works in its own files. Wave 1 works only in
   `frame/`, `shared/` and the preview page.

### 5.2 What the work board must claim

**Phase A — the split window (hours):**

| Files | Claim |
|---|---|
| `www/hrms-employee.html` | **Exclusive, whole file.** Nobody else edits it until the split is on `dev` |
| `templates/includes/ess/**` (new) | Created by this slice |
| 11 Python tests, 7 scripts, 5 JS tests that read the page (§5.3) | Only the lines that open the file |

**Phase B — the rest of Wave 1:**

| Files | Claim |
|---|---|
| `templates/includes/ess/frame/*`, `ess/shared/*` | This slice |
| `www/hrms-employee-next.html`, `hrms_employee_next.py` (new) | This slice |
| `www/hrms-employee.html` | **Include lines only** (the swap) |
| `templates/includes/design_system.html` | The `--fs-xs` line only, own commit |
| `templates/includes/brand_color.html` | The re-run export only, own commit |
| `alvoraa_portal/frame_api.py`, `inbox_api.py` (new) | This slice |
| `goals_api.py` | `_pending_approvals_scope` body only |
| `hrms/hrms/alvoraa_org_structure/api.py` | `_search_scope` body only |
| New tests `*_034.py`; `test_portal_layout.py` (TRAPS line) | This slice |
| **Not claimed:** every panel include file | Other waves and slices may edit panels in parallel |

### 5.3 Checks that must follow the includes

| Kind | Files |
|---|---|
| Python tests | `test_brand_logo_025`, `test_data_review_page_012`, `test_org_settings_allowlist_012`, `test_portal_call_paths`, `test_portal_csrf`, `test_portal_layout`, `test_portal_security_010`, `test_review_page_010d`, `test_store_hr_scoping_030`, `test_waves_5_6`, plus the route checks in `test_home_page_024` and `test_module_access` (route only, no change) |
| Scripts in CI | `check_design_system.py`, `check_portal_handlers.js`, `check_undefined_js.js`, `check_contrast_rendered.py`, `check_attendance_strip.js`, `check_rating_bands.js`, `check_api_paths.py` (to confirm) |
| JS DOM tests | `alvoraa_portal/tests/portal_*_test.js` (take a file path; they get the expanded page) |

One Python helper (`tests/portal_source.py`) and one Node helper (`scripts/lib/portal_source.js`)
expand the includes. Every check above calls one of them. A check that finds no include
tags where the page has them fails loudly, so none can silently check less.

---

## 6. Non-functional assessment

| Dimension | Verdict | Why |
|---|---|---|
| **Performance** | **Improves**, with one honest caveat | Start-up calls drop from four (context, features, switch target, the delayed count) to two (`get_frame`, `get_nav_counts`), with no 1.5 s wait. Budget I will assert in tests: `get_frame` ≤ 15 queries warm, `get_nav_counts` ≤ 15 queries whatever the team size, both ≤ 500 ms p95 at 1,000 employees. **Caveat:** the page still weighs about 1.04 MB and is sent uncompressed; the frame adds roughly 30–40 KB. The 300 ms skeleton and 2.5 s-on-3G targets cannot be met by the frame alone. They need OPS-26 (compression) and OPS-31 (cached files). I will measure first paint and full load on a throttled 3G profile, before and after, on the local copy |
| **Security** | **Improves** | Store HR's count, bell list and search stop at their store. New endpoints are whitelisted, refuse Guest, take no client-chosen doctype or field, and check scope on the server. Page search comes from the same visibility rules as the menu. `ignore_permissions` count does not rise. New risk: the preview page is reachable by URL until the swap — mitigated by the System Manager check and by every endpoint's own checks |
| **Reliability** | **Improves**, with a new-code risk | One start-up call removes the race that hid menu items. Frame-level error and loading states are new. Risk: new code on the page everyone lands on — mitigated by the preview period and a one-commit revert |
| **Scalability** | **Neutral** | Counts are single COUNT queries. `permitted_employees()` builds a list of names (up to 2,000) for HR — one query, bounded; slice 030 accepted the same trade-off |
| **Maintainability** | **Improves** (degrades for 2–3 weeks) | The page becomes about 25 files, one per area, so sessions stop colliding. For the preview period two frames exist, and the checks gain an include step |
| **Data integrity** | **Neutral** | The only write is the caller's own `User.language`. Counts are live, not cached, so nothing can go stale. `get_frame` reuses `get_portal_context`'s existing cache and its existing hook-based clearing |
| **Compliance / privacy** | **Improves** | Store-level scoping on counts and search. Search returns no phone, email or visible ID. Counts are numbers only. Logs carry document names and user ids, never names or reasons. No visibility is widened: the design's wider search (manager and leadership) is not built without your decision |

---

## 7. What I am NOT doing in Wave 1

- **Home, Inbox list and decisions** (Wave 2), including decision 1's routing change for
  attendance corrections, decision 6's check-in rule, "Needs you", birthdays, announcements.
- **Time, Pay, Growth, Team and People screens** (Waves 3–4), the staff directory and the
  person sheet. Panels move into the frame as they are.
- **Moving the existing drawers and ~30 pop-ups into the shared sheet.** Each screen's wave.
- **Hindi and Punjabi text, fonts, and dates in other languages** (Wave 5). Only the
  plumbing and `__()` on frame strings.
- **Compression (OPS-26)** — a DevOps nginx change. I recommend it is done before the swap.
- **Moving JS and CSS into cached files (OPS-31)** — see Question 12. The include files are
  shaped so it is a rename later.
- **Frappe's own heavy web assets (OPS-33).**
- **The owner/HR screens' redesign** (calibration, performance setup, policy compliance).
  They keep their current look inside the new frame.
- **The CXO multi-company view** (slice 012 owns leader views).
- **The mobile app's in-app mode** — room left only.
- **Tenant admin for a tenant's own owner** — no such page exists; not invented.
- **The vendor and driver portal** — unchanged; it appears in no menu.
- **`approve_kpi_update` and the other company-scoped performance endpoints** listed by
  slice 030. Only the scope feeding the count and bell list is fixed here.

---

## 8. Size

| Step | Build days (with tests) |
|---|---|
| 1. Split into includes, checks follow includes, byte-identical proof | 1.5 |
| 2. Preview page, shell, website bar removed, profile menu, `--fs-xs` with visual pass | 2 |
| 3. Menu list, `get_frame`, bottom-bar sets, routes, titles, focus | 2 |
| 4. Shared sheet and toast | 0.5 |
| 5. `inbox_api`, counts, Inbox slot, store-HR scope fix | 1.5 |
| 6. Scoped search | 1 |
| 7. Theme and language plumbing | 1 |
| 8–9. Five states, measurements, swap, test repointing, full suites | 1.5 |
| **Total** | **about 11 (range 10–12)** |

Not included: the missing `01c`, `02` and `07` (one run each for the security, analyst and
DevOps agents), your review time, and waiting for the bench. The full `alvoraa_portal`
suite (about 1,525 tests) runs at least twice: after step 1 and before the swap.

---

## 9. Things I could not check, and will check before the step that needs them

1. **The block names in the installed `frappe/templates/web.html` and `base.html`**
   (`navbar`, `page_content`, full-width context) — step 2.
2. **How to fill `frappe._messages` on a website page** so `__()` works (appendix A §E
   says it is empty there) — step 7.
3. **Whether the website context has a build version** for cache-busting, if OPS-31 is
   taken into Wave 1 — Question 12.
4. **Field names on Shift Request and Attendance Request** used by the count
   (`approver`, `status`) — step 5.

If any of these is not what I expect, I stop and say so rather than guess.

---

## 10. Tests that pin this work

| Test (new) | What it pins |
|---|---|
| `test_portal_split_034` | Every include exists; the rendered text equals the pre-split file (step 1 only); the page and helpers agree on the include list |
| `test_frame_menu_034` | Menu entries per persona: employee, no-payroll employee, manager, HR, store HR, owner; Pay absent without payroll; vendor absent always; Analytics shown when the plan flag is absent |
| `test_nav_counts_034` | Each count part per persona; store HR counts only their store; own requests never counted as approvals; query ceiling |
| `test_frame_search_034` | Employee finds only their own line downwards; store HR only their store; no phone, email or ID fields; under two letters returns nothing |
| `test_frame_api_034` | `get_frame` equals the three old calls combined; Guest refused; `set_my_language` refuses a disabled language and writes only the caller |
| Repointed at the swap | `test_brand_logo_025` (no broken image, letter visible), `test_waves_5_6` plan-gate tests (from `applyPlanNav` to the menu entries) |

Each is shown to fail without the change it pins, as the earlier slices did.

---

## 11. Questions you must answer before code starts

| # | Question | My recommendation |
|---|---|---|
| 1 | Write `01c` (security/privacy), `07` §1–3 (DevOps) and a short `02` spec for Wave 1 first, or let appendix A and `01b` §5 stand as the spec? | **Write them first.** One run each; the security review of search and counts matters |
| 2 | Ship by parallel preview page and one swap commit, with no per-tenant flag? | **Yes** (§3, option C) |
| 3 | Who may open the preview page until the swap? | **System Manager only** |
| 4 | When does the swap reach production, given the first client goes live in the first week of October? | Swap on `dev` when ready; to `main` either at least 3 working days before go-live, or after the first week has settled — **not in go-live week** |
| 5 | People search: keep your Q-c rule (own line downwards), or widen to "manager and leadership" as the design shows? And in Wave 1, should a person result open the org chart (where the tenant has it)? | **Keep Q-c in Wave 1**; decide any widening with Wave 4's directory and a privacy review. **Yes** to the org chart, pages-only where there is none |
| 6 | Inbox in Wave 1: a small page of counted rows linking to today's screens, or hide Inbox until Wave 2 and keep today's bell? | **The small page.** Honest now, replaced in Wave 2 |
| 7 | Fix store-HR scoping in the approvals count and bell list inside this slice? | **Yes** |
| 8 | Phone buttons for HR with no direct reports (e.g. store HR), and for a CXO? | **Home · Inbox · Company · Time** for both |
| 9 | Tenant admin in the profile menu: the prototype shows it to the owner, but `/alvoraa-admin` refuses tenant owners | **Keep today's rule:** control-plane operators only |
| 10 | Decision 5 changes text on the driver and vendor portals too (39 uses) | Confirm that is intended — I read "every page" as yes |
| 11 | Is anyone else — another developer, or the sessions committing as "Claude" (ALV-17) — working in `hrms-employee.html`? May I ask for a short freeze for the split? | **A freeze of about half a day**, announced on the board |
| 12 | OPS-31 (move JS/CSS into cached files) inside Wave 1, or as its own small step right after the swap? | **Right after the swap**, as its own step, so a delivery problem and a frame problem are never tangled together |
| 13 | Compression (OPS-26): ask the DevOps engineer to prepare it before the swap? | **Yes** — it is the biggest speed win available and needs no portal code |
| 14 | Language choice: hide the row until a tenant has a second language enabled? | **Yes** — no choices that do nothing |

## Assumptions

- `[ASSUMPTION]` The Jinja environment pastes includes as plain text on `www` pages, as it
  already does for `design_system.html`. Step 1's byte-identical test proves or disproves
  it before anything builds on it.
- `[ASSUMPTION]` Line numbers are as of `origin/dev` at `1c4e84c`.
- `[ASSUMPTION]` Nobody outside this machine is editing the page (Question 11).
- `[ASSUMPTION]` Frappe version is v16.33.1, as the appendices say. Not re-checked today.

## Handoff note

**To you:** fourteen questions, most with a one-word answer. Questions 1, 2, 4 and 5 shape
the plan; the rest adjust it.

**To the DevOps engineer (`07` §4):** please give your view on option C, the rollback
time on production, compression before the swap, and OPS-31's timing. Where you disagree,
say so; she decides.

**To the security engineer (`01c`):** the three things to look at are the store-HR scope
on counts and search, the preview page's exposure on production, and the search result
fields.

---

## Revision note · 2026-09-22 (later the same day)

The strategy above was approved, but three reviews and the user's decisions changed
details in it. **Where this document and the revised `01c`, `02` and `07` disagree, they
win.** The differences, so nobody builds from the older text:

| Where above | Now |
|---|---|
| §4 step 3: `get_frame` "calls those same functions" | It still does, but it returns a **fixed field list** and role booleans only — never the caller's date of birth, gender, phone, joining date, manager or branch (`01c` SEC-12) |
| §4 step 3: Pay needs `plan_payroll` | The **Pay group stays** without payroll, with Expenses, Leave encashment and Request advance. Only the salary parts are hidden (decision 1) |
| §4 step 3: bottom-bar sets by role | Decided by **`has_reports`** (somebody is recorded as reporting to this person) and `is_hr`, with a precedence order — `02` §2 (decision 2) |
| §4 step 5: counts | Each part names the scope helper it reuses, and a test proves the count equals the list it links to. `attendance_correction.to_review` is store-scoped in this slice (decision 5) |
| §4 step 6: search | Store HR finds their store **plus their own reports** (decision 7); the caller must be Active (leaver fix, decision 6); wildcards escaped; one shared filter helper in `access.py` |
| §4 step 7: language | **`set_my_language` is not built in Wave 1** (decision 4). A language is offered only when it is enabled *and* the portal ships a translation |
| §3: rollback is `git revert` and a deploy | Rollback is **redeploying the previous image, about 10 minutes** (OPS-14, decision 10). The revert follows afterwards |
| §6 Performance: "2.5 s on 3G" | Measured on **Chrome "Slow 4G" with 4× CPU** (OPS-17, decision 9) |
| §5.2 claims | Add `hrms/hrms/alvoraa_hr_core/access.py` (new `permitted_employee_filters`), `alvoraa_portal/attendance_correction.py` (`to_review`'s filter) and the Org settings panel's Save controls (decision 3) |
| §7 not doing | Also not doing: `set_my_language`; the org-chart company scope (**ALV-86**, Critical, before DTC go-live); the wider leaver fix (**ALV-87**) |
| §8 size, about 11 days | Unchanged in shape, but the added work (store-scoped corrections queue, leaver fix, count-matches-list fixtures, the read-only Org settings line, Hindi fixtures) is **about 1.5 days more**: call it **11–13 days** |

---

## Second revision note — 23 September 2026 (after the two re-reviews)

The analyst's re-review (`02c-ba-rereview.md`) and the security re-review
(`06b-security-rereview.md`) both closed with notes, and Surbhi took six decisions on them
the same day. They are recorded in **`00g-decision-register.md`** as **W1D-13 to W1D-18**,
together with the twelve decisions of 22 September (**W1D-01 to W1D-12**) that these
documents had been citing as bare numbers with no file behind them. **Cite decisions as
`W1D-nn` from now on.** `01c` is at revision 3 and `02` is at revision 3; where they
differ from anything above, **they win**.

| Where above | Now |
|---|---|
| Every bare "decision n" in the table above | Read as `W1D-nn` — decision 1 is W1D-01, decision 10 is W1D-10, and so on. The two sets in `00f` are "009 design decision n" and "009 strategy decision n" |
| §5.2 claims | **Add `alvoraa_portal/alvoraa_portal/hr_api.py`** — `get_manager_dashboard`'s no-manager list is narrowed to `permitted_employees()` (W1D-13, `01c` SEC-13, `02` AC-72). This is a **hot file**; claim it on the work board before the first edit and make the change as its own early commit |
| §4 the preview page | It is gated on **`frappe.conf` `portal_preview: 1`** as well as the role, so it **does not exist on production** (W1D-15, `01c` SEC-1, `02` AC-74). The flag is set on the local bench and dev only. Residual risk R5 is removed rather than accepted |
| §4 step 5: `to_review` is store-scoped | Only **when the caller is HR** (W1D-14). A reviewer who is not HR but holds submit permission on Attendance Request keeps today's queue — `_may_review()` tests the permission, not a role |
| §4 step 6: the shared filter helper | It must **never return an empty filter dict** — in Frappe that means every record. An explicit refusal, with a test that the return value is never `{}` (security note N1, `02` AC-73) |
| §8 size, 11–13 days | **13–15 build days.** The added work is +0.5 for the Team-panel query, +0.75 for the Inbox counts (capped count plus the two caller paths), +0.25 for the filter helper's refusal and +0.25 for the preview-page flag. `02` §20 has the breakdown. Day 1 is still the page split and the critical path is unchanged |
| §6 Compliance | `01c` PRIV-7's visibility table is now written — 18 rows, **six narrower than today, none wider** |

## Third revision note — 23 September 2026, later the same day

Surbhi took **three more decisions**, recorded as **W1D-19, W1D-20 and W1D-21** in
`00g-decision-register.md`. `01c` and `02` are now at **revision 4**; where they differ
from anything above, **they win**.

| Where above | Now |
|---|---|
| The desk link | **HR and System Manager only; a plain manager gets none**, with the server's labels "Switch to HR Core" and "Switch to Admin" (W1D-19). **No code change** — the code was already right and the prototype was wrong. `02` AC-75, `01c` SEC-7 |
| The second revision note's §5.2 row — "`hr_api.py`, the no-manager list narrowed" | **Replaced.** W1D-20 supersedes W1D-13: for an HR caller `get_manager_dashboard` is **rebuilt** on `access.permitted_employees()` and the no-manager block is **deleted**. Same file, same hot-file rules, bigger change — still its own early commit. `01c` SEC-13, `02` AC-72 |
| §5.2 claims | **Add `alvoraa_portal/alvoraa_portal/subscription.py`** (one new `opt_in` key in `FEATURES`) and the plan gate in `alvoraa_portal/alvoraa_portal/www/hrms-employee.html:7813`, which splits into two flags (W1D-21, `01c` SEC-16, `02` AC-76). The staff-list screen is new work inside the frame files this slice already claims |
| §8 size, 13–15 days | **15–18 build days.** W1D-20 replaces W1D-13's +0.5 with +1.0 to +1.25; W1D-21 adds +1.5 to +2.0 for the switch and the list screen; W1D-19 adds +0.25 for its test. `02` §20 has the breakdown **and the note that the quarter-day Surbhi was quoted for W1D-20 is too low — it is about half a day more than W1D-13, not a quarter** |
| §6 Compliance, "none wider" | **One row is now wider** — a tenant System Manager's Team screen becomes the whole tenant, because `is_hr` includes System Manager and `permitted_employees()` gives them everyone. No new data (the desk already lists everyone for them), but a wider screen. It is `02` open question 6 and `01c` open question 6, raised rather than assumed |
