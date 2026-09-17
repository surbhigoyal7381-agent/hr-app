---
slice: 009-ess-portal-redesign
artifact: appendix-a-frame
author: hrms-business-analyst (read-only review, run 2026-09-14)
date: 2026-09-14
status: ready
inputs: [prototype a78f9f44 (p1-head.html, p2-shell.html, p4-core.js), hrms-employee.html, 003 phone assessment, 002 spec]
---

# Appendix A — The frame: menu, top bar, bottom bar, search, sheet, toast, theme, language

Read-only review. Line numbers refer to the code on 14 Sep 2026 (`dev` at `30e2d13`).
Prototype source parts live outside the repo in
`C:/Surbhi-Git/hrlocal-data/ux-review/2026-09-11/prototype/`.

## Bad news first

1. **The prototype's phone layout would break about 30 existing pop-ups.** It sets `container-type:inline-size` on the outer `.app` box (p1-head.html:73). That setting pins every `position:fixed` pop-up to that box instead of the screen. Almost all current pop-ups sit inside `.main-content` (hrms-employee.html:3202–4715). This is the same bug `test_portal_layout.py:1-30` guards against, but that test does not check `container-type` yet. **The frame must use `@media` rules. Container queries are only safe on small inner blocks.**
2. **The bell count is too slow for HR.** The only "pending" count today is `goals_api.get_pending_approvals` (goals_api.py:1123-1190). It loads every KPI and goal for every active employee, one at a time. As Kamal (HR, 403 employees) it took **11.6 seconds** (a second run in Appendix B took 16.4 s). It already fires 1.5 s after every page load (hrms-employee.html:~12220). The prototype puts a count in the rail, the top bar and the bottom bar. That needs a new count-only endpoint.
3. **Search shows everyone to everyone.** `search_people` (hrms/alvoraa_org_structure/api.py:546-558) and `search_employees` (performance_api.py:1459-1487) both use `frappe.get_all`, which skips permission checks (frappe `__init__.py:1383-1384`, v16.33.1). Any logged-in employee gets every active employee in every company, with job title, department and photo. It also ignores the org chart's own reach limit (`reach()`, api.py:569-598). Do not reuse either for global search.
4. **The owner/HR persona is not designed.** Kamal has 17 screens today. The prototype's Company group holds one item ("People"). Where Analytics, Org Settings, Performance Setup, Calibration and Policy compliance go is undecided.
5. **The prototype drops controls people need.** Log out and My Account come only from Frappe's website bar (frappe website_settings.py:181-182). Removing that bar (fix R1) removes log out. The prototype has no Switch-to-desk, no Tenant Admin, no profile menu, and no in-product place for the language or theme switch — those live only in the demo control bar (p2-shell.html:15-28).
6. **Punjabi does not exist anywhere in the stack.** Frappe's language list has no `pa` (languages.csv, 83 rows). Frappe, hrms and erpnext ship `hi.po` but no `pa.po`. On ppj the `hi` Language record exists but is disabled. The portal has zero `__()` calls and no `translations/` or `locale/` folder. Only 34 of about 230 server error messages are wrapped in `_()`.

## A. Requirements

| ID | What the person sees or does | Personas | Existing code (verified) | Status | Work needed | Size | Risk / open question |
|---|---|---|---|---|---|---|---|
| FR-01 | Menu grouped under labels Me · Time · Pay · Growth · Team · Company | All | Sidebar is hand-written HTML with groups Main / Management / Requests / Tools (hrms-employee.html:2293, 2325, 2336, 2346). Items are `<div onclick>`, so a keyboard cannot reach them | partial | Client: one list of menu entries (group, label key, icon, panel, tab, visibility rule) that draws the rail, bottom bar, title and search pages | M | Hot file. The menu list changes once, in its own commit |
| FR-02 | Menu items appear only when plan, role and features allow | All | `applyPlanNav` 7650-7666, `loadAvailableFeatures` 7668-7704, `loadPortalContext` 7580-7635 | exists | Move each rule into its menu entry's visibility function. Keep `plan_analytics !== false` | S | `test_waves_5_6.py:189-222` greps `applyPlanNav()` by name and needs 3+ mentions |
| FR-03 | One start-up step: context and features load together, then the menu draws once | All | Two calls race (comment 7641-7649). `loadHomePolicies` (5386-5388) and `loadMyDocuments` (5574) read `window._features` before it may have arrived | partial | Client: `Promise.all`, then draw menu and home cards | S | Same race as the Organisation bug, now on Home |
| FR-04 | Counts next to menu items (Inbox, Team, Policies) | Emp, Mgr, HR | Counts set only after each panel opens (7061-7065, 8367-8369, 9683-9685, 5391-5392) | partial | Server: new count-only `get_nav_counts()`. Client: fetch once at start and after each decision | M | Must not call `goals_api.get_pending_approvals` |
| FR-05 | Search "people and pages", Ctrl K / ⌘K | All | Prototype p4-core.js:192-217, 253. Portal: only org chart search (`ocSearch` 5232-5255) | missing | Client: pages from menu list, filtered by visibility. Server: new scoped people search | M | Scope rules need a decision |
| FR-06 | Top bar: group, page title, back link on deep pages, search, bell with count | All | Phone header only (2385-2403), shows tenant name, hidden above 768px (620-627) — **desktop has no bell** | partial | Client: title and breadcrumb from menu list | S | Full-screen panels need a breadcrumb |
| FR-07 | Inbox page | Emp, Mgr, HR | Bell panel lists KPI and goal updates only (12195-12219) and sets `_pfIsManager = true` for anyone whose call succeeds | missing | Frame: page slot and count only; Inbox wave fills it | L | — |
| FR-08 | Phone bottom bar: 4 buttons + More | Emp, Mgr | 3 fixed buttons: Home, Attendance, Finances (4788-4803) | partial | Client: build from menu list per persona | S | HR set not designed. No-payroll tenant must not get Pay |
| FR-09 | Side sheet on desktop, bottom sheet on phone | All | Several one-off drawers (4817-4828, 4830-4843, 4846-4857, `#gp-detail-panel`), ~30 centred pop-ups | partial | Client: one shared sheet — Esc closes, focus trapped and returned, `aria-labelledby` | M | Prototype sheet does not trap or return focus. Closed drawers cast a shadow (M19) |
| FR-10 | Toast announced to screen readers | All | `toast(msg,type)` 4877-4884; `#toast-wrap` (4810) has no `aria-live` | partial | Add `role="status"`, keep signature | S | Many callers; don't rename |
| FR-11 | Focus and keyboard on navigation; Esc closes menu and sheets | All | No focus handling in `switchPanel` (5281-5333) | missing | Client | S | — |
| FR-12 | Phone layout that does not shrink content (R1–R3) | All | `nav.navbar` pinned at 42; `.emp-app{margin-top:52px}` 43; collapsed style beats phone rule (68 vs 626); `main.container` padding (frappe web.html:17) | partial | Template: empty `{% block navbar %}`; `full_width` context or `page_container` override; drop `sb-collapsed` below 768px | S | Must ship with FR-13 or log out disappears |
| FR-13 | Profile menu: name, log out, My Account, Switch to desk, Tenant Admin, language, theme | All | Switch link 2361-2366 + `get_switch_target`; Admin link 2367-2371; log out only in Frappe's bar | partial | Client menu at bottom of rail | S | Not in prototype |
| FR-14 | Theme Auto / Light / Dark, remembered | All | Dark tokens exist (design_system.html:14-31). Nothing sets `data-theme`. No switch | partial | Set `data-theme` before first paint; save; re-run brand colour | S | `brand_color.html` writes colours once (63-65, 115-117) |
| FR-15 | Pay group hidden without payroll | Emp | Finances item has no plan check (2301); server refuses payslips with `@requires_feature("payroll")` (hr_api.py:1425, 1458) | partial | Payslips tab uses `plan_payroll` | S | Starter-plan tenant sees a failing tab today |
| FR-16 | URL per page; back button works | All | No `location.hash` or `popstate` | missing | `#time/requests` routes calling `switchPanel` | S | Emails could deep-link |
| FR-17 | Language switch EN / हिं / ਪੰ | All | None | missing | See E | L | Blockers in E |
| FR-18 | Tenant mark and name in rail | All | `get_branding()` (hrms_employee.py; 2283-2286) | exists | Keep | S | Prototype `--tenant` tokens not in design_system.html |
| FR-19 | Remove duplicate "Checkin Log" item | All | 2347 opens same panel as 2297 | exists (bug) | Becomes a tab under Time | S | — |

## B. Where each current panel goes

The frame wave keeps every panel's HTML and loader. It only moves the entry point, title and route.

| Current panel (id, line) | Loader | Gate today | New group › page | What changes in the frame wave |
|---|---|---|---|---|
| `home` 2409 | `loadHome` 6473 | none | Me › Home | Title from menu list |
| (new) Inbox | — | — | Me › Inbox | Empty slot plus count |
| `attendance` 2566 (+ Checkin Log 2347) | `loadAttendance`, `loadLeaves` | none | Time › Attendance & leave | One entry; Checkin Log becomes a tab |
| `att-record` 2657 | `acOpen` 5971 | none | Time › My days (tab) | Reached from Time |
| `attendance-insights` 2644 | `aiOpen` 5670 | `attendance_analytics.views()` | Time › Insights (mine); Team › Attendance; Company › Attendance (HR) | One panel, opened with a starting view |
| `shift-req` 2968 | `loadShiftReqPanel` 7732 | `features.shift_request` | Time › "Change shift" | Stays a panel for now |
| `att-req` 3005 | `loadAttReqPanel` 7779 | `features.attendance_request` | Time › "Fix attendance" | Stays for now (retire in Time wave) |
| `adv-req` 3053 | `loadAdvReqPanel` | `features.advance_request` | Pay › "Request advance" | Same |
| `finances` 2724 (salary / expenses / leave-enc) | `loadSalary` | leave-enc: `features.leave_encashment` | Pay › My pay | Add `plan_payroll` to salary tab |
| `goals` 3083 (overview, tree, reviews, team, hr, calibration, distribution) | `loadGoalsPanel` → `_gpBoot` 9680 | `features.goals` | Growth › Goals & reviews; Team › Goals; Company › Performance (HR tabs) | Same panel opened with a tab |
| `pms-review` 3647 (full screen) | 14321, 15196 | inside Performance | Growth › Self-review | Breadcrumb; keep scroll reset (5321-5332) |
| `mr-review` 3700 (full screen) | 13289 | manager | Team › Give feedback | Breadcrumb |
| `scorecard` 3722 (full screen) | `openEmpScorecard` 7912 | manager/HR | Team › [person] | Breadcrumb from `_scBackPanel` |
| `appraisal-setup` 3602 | 16263, 16368 | HR | Company › Performance setup | Breadcrumb |
| `team` 2784 | `loadTeamPanel` | `ctx.is_manager` | Team › My team | Count from FR-04 |
| `analytics` 2898 | `loadAnalyticsPanel` | `is_hr && plan_analytics !== false`; server `@requires_feature("analytics")` | Company › HR analytics | Unchanged |
| `org-chart` 2679 | `ocLoad` | `plan_org_structure` | Company › People | Directory vs chart undecided |
| `policies` 2698 (read, manage, compliance) | `polLoad` | `plan_policy_library`; manage `can_write`; compliance `is_hr` | Company › Policies | Count = to acknowledge |
| `org-settings` 3516 | `orgLoad`, `orgLoadDocuments` | `ctx.is_hr` | Company › Org settings | HR only |
| Drawers (payslip 4818, employee 4831, goal 4847, gp-detail) | — | — | Stay | Move to shared sheet screen by screen |

## C. Gating to keep

| Gate | Source (verified) | Where the new frame must use it |
|---|---|---|
| Role flags `is_hr`, `is_manager`, `is_system_manager`, `is_control_plane` | `hr_api.get_portal_context` 94-152 (cached per user 1 h; cleared by hooks.py:75) | Team, Company items, Tenant Admin |
| Plan flags `plan_<feature>` | `hr_api.get_available_features` 1134-1227 (loops `subscription.FEATURES`); `goals` = app installed AND plan | Analytics, Policies, Org chart, Goals, Employee documents, Attendance scoring, Payroll. Missing flag = "not answered yet" |
| Server refusals | `@requires_feature` (subscription.py:621-650) | New endpoints (counts, search) check plan for plan-bound data |
| Config/permission feature flags | `shift_request`, `leave_encashment`, `attendance_request`, `advance_request` (1154-1199) | Time and Pay actions |
| Attendance views | `attendance_analytics.views()` 84-100 | Insights entries under Time, Team, Company |
| Desk switch | `module_access.get_switch_target` 784-800 | Profile menu |
| Org chart reach | `api.reach()` 569-598 | New people search |

Tests pinning these: `test_waves_5_6.py:115-222`, `test_endpoint_entitlement.py`.

## D. Phone-audit gaps (slice 003)

- **Fixed by the frame alone:** R1/M07 and most of M01 (navbar block removed + log out in profile menu); R2/M03 (labelled drawer, no collapsed style on phones); R3/M08 (`full_width`); M16 (bottom padding); M20 (bottom bar from menu list); M11 (one 16px input rule on phones, must beat `.form-control`).
- **Partly fixed:** M10, M18, R5 (frame controls can be 44px/12px+, but the prototype itself uses 10px labels, 38px icon buttons, 36px/30px buttons, 11px chips); M12, M19 (only with shared sheet); R4, M06 (frame gives a scrolling tab style; each screen must use it).
- **Not fixed by the frame:** M02, M14, M22, M04, M05, M13, M15, M21 (each screen's wave); M09 (Home); M17 (login page); F1–F4.

## E. Languages

**How Frappe does it (checked in v16.33.1):** a logged-in user's language is `User.language`, then System Settings (translate.py:33-83, 96-106) — the switch must save `User.language` and reload. Translations come from each app's `translations/<lang>.csv`, compiled `.mo` files from `<app>/locale/*.po`, then Translation records (translate.py:135-190; gettext/translate.py:17, 45-62). JS `__()` on website pages reads `frappe._messages`, which is **empty on website pages** — only Web Form fills it via `context.translated_messages` (web_form.py:344-483). `bench generate-pot-file` scans `**.html` and `**.js` including inline `__("…")`; text joined with `+` is not found.

**Prototype mapping:** keys become English source text; `T(k)` becomes `__()`; the `hi`/`pa` tables become `alvoraa_portal/locale/hi.po` and `pa.po`. It covers ~29 labels only.

**Approach:** fill `frappe._messages` in `hrms_employee.get_context` with the portal's own strings only; wrap strings in `__()` wave by wave, and server `frappe.throw` in `_()`; `.po` files (Dockerfile must compile `.mo` — unconfirmed that `bench build` does); new `set_my_language(lang)` allowing only enabled languages; enable `hi`, create `pa` Language via a patch.

**Size:** ~1,200–1,500 client strings (rough grep); ~230 server throws, 34 wrapped. Frappe HR's own Hindi file is partial; no Punjabi at all, so Punjabi users see English server errors.

**Blockers:** native-speaker review of HR terms in both languages (prototype uses "नमस्ते" for all three greetings); fonts (no Noto files loaded; 10px unreadable); dates use `en-IN` everywhere (`fmtDate` 4888-4892).

## F. Non-functional notes

- **Performance:** today's start-up makes ~5 calls plus the 1.5 s bell call (11.6–16.4 s for HR). Frame should add only `get_nav_counts` (~5 count queries) and remove the bell call. People search: min 2 chars, 220 ms debounce, 8–12 results.
- **Security:** new `search_directory(q)` via `frappe.get_list` or explicit filters — same company (CXO/HR: permitted companies), active only, fields name/title/department/photo, respects `reach()` or an explicit decision. No phone, email or ID. Page search uses menu visibility. ppj has one company — multi-company scoping must be tested on `test_site`.
- **Accessibility:** menu items as links/buttons with `aria-current`; bell and avatar as buttons (today `<div>`s, 2390, 2402); sheets trap/return focus; toast `aria-live`; 44px targets, 16px inputs on phones. **Prototype `--text3:#8E857D` is 3.36:1 on `#F8F6F3`, failing slice 002's 4.5:1 rule** — keep `#736D65` (4.74:1). Keep `prefers-reduced-motion`.
- **Structure for parallel sessions:** do not move JS/CSS to `public/` yet (needs `bench build`, a deploy command; local `sites/assets/alvoraa_portal` is a static copy). **Recommended: Jinja includes** like `design_system.html` — e.g. `templates/includes/ess/frame_css.html`, `frame_shell.html`, `frame_js.html`, `nav_registry_js.html`, one file per later wave, JS wrapped in `{% raw %}`. Cost: every check that reads raw `hrms-employee.html` must follow includes — `test_waves_5_6.py`, `test_portal_layout.py:33-39`, `test_portal_call_paths.py`, `test_portal_csrf.py`, `scripts/check_portal_handlers.js`, `scripts/check_undefined_js.js`, `scripts/check_design_system.py:44`, CI step ci.yml:109. Add `container-type` and `backdrop-filter` to the layout test's banned wrapper properties.

## G. Build order inside the frame wave

1. Page template: remove navbar block, `full_width`, profile menu with log out/switch/admin (FR-12, FR-13). Ships alone.
2. Split into includes + teach checks to follow them. No behaviour change.
3. Menu list + `applyPlanNav` + one start-up step (FR-01–03, FR-15, FR-19).
4. Router `go(page, tab)` wrapping `switchPanel`, hash routes, top bar title/breadcrumb, focus (FR-16, FR-06, FR-11).
5. Shared sheet and toast (FR-09, FR-10).
6. `get_nav_counts` + bell → Inbox slot; stop the 1.5 s bell call (FR-04, FR-07).
7. Scoped people search + page search (FR-05).
8. Theme switch with brand colour re-run (FR-14).
9. Language plumbing: `_messages`, `set_my_language`, frame strings in `__()` (FR-17).

**Plug-in points later waves need:** a menu-list entry, a panel id, `ess.onOpen(page, fn)`, `ess.openSheet(title, body, foot)`, `toast()`, `ess.counts` refresh, `__()`, the phone breakpoint, and shared tokens in design_system.html (`--sunk`/`--border-strong` as names for `--surface2`/`--border2`, plus `--on-primary`, `--scrim`, `--tenant*`).

## H. Open questions

| # | Question | Blocks |
|---|---|---|
| H-1 | Owner/HR screens: one Company group with sub-sections, or a separate Admin group? Calibration under Growth or Company? | Menu list |
| H-2 | Bottom-bar buttons for HR and for an employee without payroll? | FR-08 |
| H-3 | People search scope: whole company by name/title, or org-chart reach only? CXOs across companies? | FR-05 |
| H-4 | Where language and theme switches live; theme per device or per user? | FR-13, FR-14, FR-17 |
| H-5 | Company › People: directory or today's org chart? What without `org_structure`? | FR-01 |
| H-6 | Who writes and reviews Hindi/Punjabi; may HR edit wording per tenant? | FR-17 |
| H-7 | Inbox count: include policy acknowledgements and own open requests, or approvals only? | FR-04 |
| H-8 | Punjabi for server error messages too, or English first? | E |

## Open questions / Assumptions / Handoff note

- **Open questions:** H-1 to H-8 above (owner: product owner).
- **Assumptions:** [ASSUMPTION] line numbers are as of `30e2d13`. [ASSUMPTION] Jinja includes render identically to inline code on www pages (to be proven in step 2).
- **Handoff note:** the frame is mostly client work, but it touches the most-changed file. Do the include split as its own no-behaviour commit, and teach every static check to follow includes in that same commit, or the checks silently check less.
