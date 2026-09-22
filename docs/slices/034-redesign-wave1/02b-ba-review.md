---
slice: 034-redesign-wave1
artifact: 02b-ba-review
author: hrms-business-analyst (review of a spec written by the engineer who will build it)
date: 2026-09-22
status: ready
inputs: [02-functional-spec.md, 00-impact-analysis.md, 01c-security-privacy-requirements.md, 07-devops-inputs.md, ../009-ess-portal-redesign/00f-decisions-2026-09-22.md, ../009-ess-portal-redesign/01b-ux-design.md §3 §5 §9 §13 §14, ../009-ess-portal-redesign/appendix-a-frame.md, prototype-v2.html, .claude/context/definition-of-ready-done.md, .claude/context/handoff-contract.md]
---

# Review of the Wave 1 frame spec

## Verdict: **Not ready** — one revision away

**Four things in the spec would build the wrong thing, and I checked each one in the code
or on the local bench.** None of them needs a redesign. Two need a one-line decision from
Surbhi. The rest is the engineer tightening the spec.

1. **A tenant without payroll would lose expense claims.** AC-1 removes the whole Pay
   group. Today the Pay entry (`panel-finances`) holds three tabs: Salary Slips,
   **Expenses** and Leave Encashment (`hrms-employee.html:2788-2790`). `expenses` is a
   *required* feature on every plan (`subscription.FEATURES`). "Request advance" also sits
   under Pay (appendix A §B). So an employee on a no-payroll tenant would have no way to
   file an expense claim. The prototype never showed expenses, so the approved design did
   not see this. **Decision for Surbhi.**
2. **The language row would show 17 languages on every tenant, including Arabic.**
   AC-18 shows the row when "two or more languages are enabled". Frappe's Language record
   is enabled by default (`language.json`: `enabled` default `1`). On both local sites
   (`ppj.localhost`, `test_site`) **17 are enabled**: zh, tr, th, sv, sr-CS, sr, pt-BR, nb,
   my, hr, fr, fa, es, en, de, bs, ar. Hindi is not one of them. So the row would appear
   everywhere, and SEC-9's `set_my_language` would accept Arabic or Persian (right-to-left)
   for a portal with no translations. This is the opposite of decision 14. The impact
   analysis says "today no tenant does" — that was not checked. **Decision for Surbhi on
   the fix; my recommendation is below.**
3. **"HR with reports" and "HR without reports" cannot be told apart the way the spec
   assumes.** `hr_api.get_portal_context` sets `is_manager = True` for any HR user when
   *any* active employee in the tenant has no manager set (lines 118-124 — the HR
   "stand-in" rule). The owner at the top of every company has no manager. So almost every
   HR user, store HR included, counts as "has reports". They would get the Team group and
   the Home · Inbox · Company · **Team** bar — not the Home · Inbox · Company · **Time** bar
   that decision 8 gave store HR. The spec also uses "owner" and "CXO", but the code has no
   owner role; it treats System Manager as CXO. **The spec must say which flag decides each
   set.**
4. **AC-11's "next allowed page" has no order.** Two engineers would build two different
   bars. The spec must list the fallback order.

**One part is ready now:** US-10 (the page split, AC-36 to AC-39) is independent, testable
and fully traced to OPS-6 and OPS-7. It does not depend on any of the four points above.
It can go ahead as soon as the coordinator schedules the freeze (decision 11).

By the Definition of Ready rule ("if more than two boxes fail, the slice goes back"),
five boxes fail today (see §7). All five are fixable in the spec itself in one pass.

---

## 1. Required changes, ranked

### Blockers — they change what gets built

| # | Where | Problem | Required change |
|---|---|---|---|
| **B1** | AC-1, AC-10, matrix row "Pay" | Hiding Pay hides Expenses (a required feature) and Request advance on a no-payroll tenant | Surbhi decides. **My recommendation:** the Pay group exists when *any* of its pages is allowed. Without payroll it shows **Expenses** (and Request advance where `advance_request` is true) and hides Salary Slips, the payslip search result and "My pay". Leave Encashment follows its own flag. The bottom bar for a no-payroll employee stays Home · Time · Inbox · Goals (decision 2 is not touched). Rewrite AC-1 as: "no Salary Slips tab, no My pay entry, no payslip search result; Expenses is still reachable from Pay". Add one AC that an employee on a no-payroll tenant can open Expenses from the menu |
| **B2** | AC-18, SEC-9, §7 | "Enabled Language" is the wrong test (17 enabled by default) | Define **offered languages** = English, plus each language that is enabled on the site **and** has a portal translation file shipped in `alvoraa_portal`. In Wave 1 that is English only, so the row is hidden on every tenant. `set_my_language` accepts only an offered language. Add an edge case and an AC for a user whose `User.language` is already something else (set in the desk, e.g. `de`): in Wave 1 the frame shows English, with no half-translated labels from Frappe's own files `[UNVERIFIED — engineer to confirm how `_messages` would fill for such a user]` |
| **B3** | AC-10, matrix columns, §4 "a CXO gets the HR set" | Personas are not defined in flags the code has | Add a **persona resolution table** — flags in, bar out, with precedence. Say which "has reports" means: direct reports only (`reports_to = me`, Active), **or** today's `is_manager` including the HR stand-in. My recommendation: **direct reports only** for the bar and the Team group, because that is what decision 8 meant by "HR with no reports". Name the CXO rule (System Manager, per `access.permitted_companies`). Say what wins when a person matches two rows (e.g. System Manager with direct reports). Say which page the **Company** button opens — the prototype opens HR analytics (`bnavItems`, line 866) — and what it opens when analytics is off |
| **B4** | AC-11 | "Next allowed page" is undefined | Give one fallback order, e.g. Home → Inbox → Time → Goals → Pay → Team → Company, skipping pages already in the bar and pages not allowed. Say what happens when fewer than four are allowed (a System Manager with no Employee record): fewer buttons, More always last. Add a test per persona |

### Majors — testability and traceability

| # | Problem | Required change |
|---|---|---|
| **M1** | Security and privacy items traced to ACs that do not test them | **SEC-2** (traced to AC-7, 8, 40): none tests Guest or wrong-role refusal. Add: each of `get_frame`, `get_nav_counts`, `set_my_language` called as Guest returns HTTP 403 (`PermissionError`). **SEC-6** (traced to AC-8, 18): add "takes no doctype, field or method argument" and "the `ignore_permissions` count in CI does not rise". **SEC-9** (traced to AC-18): the row is hidden, but the endpoint is still callable by hand. Add: a disabled, unknown or not-offered language is refused and `User.language` is unchanged; a `user` argument is ignored or refused. **SEC-10** (traced to AC-42, logo only): add "a job title of `<script>alert(1)</script>` shows as text in search, rail and profile menu". **PRIV-2**: AC-27 checks the screen; add the payload oracle — each result's keys are exactly `employee, name, title, department, image`, and `employee` is never shown. **PRIV-3**: add "the frame asks for 12; `limit=500` returns at most 50". **PRIV-4**: add "the counts payload holds only numbers and part keys — no names, no reasons, no document ids". **PRIV-5**: this is testable by log capture; make it an AC rather than "no user-facing AC" |
| **M2** | Decisions without an AC | 00f decision 1 (Wave 1 counts attendance corrections where they sit today — HR's queue — and the manager's count does not include them yet): no AC. Strategy decision 7 (store-HR **search**): only covered by AC-26's "follow §2"; add an explicit two-store AC plus a head-office employee with no branch (01c SEC-4). Strategy decision 4 (swap timing): not an AC, but list it in the spec as a release gate with the user's decision recorded |
| **M3** | The count is not specified in the spec | Add a table of count parts: part, doctype, filter, who gets it, the Inbox row wording, and where the row links. 00 §4 step 5 has most of it — bring it into the spec, with the field names marked `[UNVERIFIED — engineer to confirm]` until checked (00 §9 item 4). Add the rule: **only count what the portal can act on today** (so, for example, Expense Claims to approve are not counted unless there is a portal screen for them — say which). Say what the bell does when pressed (open `#inbox`, as the prototype does). Say what "the bell list" in AC-21 now means. Add: after a decision in a panel, the count refreshes without a page reload |
| **M4** | Five states are not covered per persona | See §3. Missing: search failing (people search down, pages still shown); what "0" looks like (no badge, and the screen reader hears "Inbox, nothing waiting"); a System Manager with no Employee record — today's count helper throws "No Employee record found for your account" (`goals_api._require_employee`), which would put the card-error state on that person's screen every time; session expired or user disabled (must go to login, not the page-error state); an unknown address such as `#nonsense` |
| **M5** | Edge cases missing | See §4 |
| **M6** | Out of scope is not stated in the spec | The spec has one "Drop from Wave 1" row. The build can drift. Copy 00 §7's list into the spec, and add 01b §14 items 5–12 (review copies, KPI increments, grace, reporting-line note on reviews, absence reasons, small-group suppression, Needs review, data dates) as "later waves — not Wave 1" |
| **M7** | Oracles too loose | See §2 |
| **M8** | Differences from the approved prototype are not listed | The Definition of Done needs "every difference agreed by the user". Five are real: (a) the prototype shows **Switch to the full desk** to managers; the code returns nothing for a non-HR manager, and the label comes from the server ("Switch to Admin" / "Switch to HR Core", `module_access.get_switch_target`), not "Switch to the full desk"; (b) Tenant admin shown to the owner in the prototype, control-plane only by decision 9; (c) the language row hidden by decision 14; (d) the search empty-state copy — the prototype says "your own team, your manager", which decision Q-c does not allow; (e) Company › People for everyone in the prototype, gated by `plan_org_structure` in the spec. List each with the decision that covers it. (a)'s label needs Surbhi's word or a server label change |

### Minors — format and completeness

| # | Problem | Change |
|---|---|---|
| m1 | Stories: only US-1, 2, 3, 6 have "As a… I want… so that…"; personas are "any user"; sizes are S/M, not points; no prototype screen link; no YouTrack table | Rewrite in the standard form with personas from `product-context.md` (Rahul, Sandeep, Kamal, store HR). Size in points. Link each to its prototype screen. Split the "must not" rules into their own stories — e.g. *"As Rahul, I must not find a colleague outside my own line in search, so that the directory is not a staff list for anyone who logs in."* |
| m2 | Matrix: "Me, Time, Growth ✓ for everyone" | Growth needs the `goals` flag (app installed **and** plan). Me and Time for someone with no Employee record: say which pages show. System Manager is `is_hr = True` in `get_portal_context`, so "Org settings — unless HR" for a tenant System Manager is wrong; it is ✓ |
| m3 | Plan flags when the key is missing | AC-2 covers analytics only (`!== false`). Say the rule for every flag used (`plan_payroll`, `plan_policy_library`, `plan_org_structure`, `goals`) when entitlement cannot be read and the keys are absent |
| m4 | Compliance section is short | Add the obligations table (DPDP minimisation, access rights, logging — from 01c), one open compliance question line ("none" is fine), and the line "The analyst is not a lawyer; nothing here is a legal ruling." Retention: add the theme choice (device only) |
| m5 | Toast and message copy not listed | List every frame message with exact words: page-error sentence, count-error sentence, search-error sentence, "All clear", no-permission sentence, the empty search per scope (§2, AC-29) |
| m6 | AC-43 covers three pages | Decision 5 says six pages include `design_system.html`. Add: login, admin console and field check-in render with no visual change (the token has 0 uses there, 00 §2.2). The vendor and driver pages 404 without the `vendor` feature, so the 390 px check must run on a tenant with `vendor` on |
| m7 | Open questions numbered 1, 3, 2 | Renumber |
| m8 | OPS-11 says the token change rides in its own commit | Add that to AC-43 |

---

## 2. Acceptance checks — testable or not

Pass means a person or a test can say yes or no without asking anyone.

| AC | Testable? | Change needed |
|---|---|---|
| AC-1 | Yes, but wrong (B1) | Rewrite per B1 |
| AC-2 | Yes | — |
| AC-3 | **Always passes** — no vendor item exists in any menu today (00 §2.3) | Replace with: on a tenant **with** `vendor`, a Vendor User still lands on `/vendor-portal` and a Delivery Partner on `/driver-portal` (routing unchanged, `auth._portal_home_for`); on any tenant, the menu list has no vendor or driver entry |
| AC-4 | Yes | Name the oracle: *Team › My team* opens `team`; *Company › Reviews (HR)* opens `goals` on its `hr` tab, the list that calls `hr_list_appraisals` (slice 010, decision 37) |
| AC-5 | Yes | — |
| AC-6 | Loose | Oracle: no element in the rail, top bar, bottom bar or search results has `disabled`, `aria-disabled="true"` or a disabled class, for every persona fixture |
| AC-7 | Yes | — |
| AC-8 | Loose | List the personas it runs for (employee, manager, company HR, store HR, System Manager with and without an Employee record, control-plane operator) |
| AC-9 | Three checks in one, no oracles | Split into three, each with a value: Home's team-goals card has rows for a manager fixture; the notes filter lists the manager's reports; HR's Data to review badge shows the same number as `_with_review_count` |
| AC-10 | Wrong for most HR (B3) | Rewrite from the persona table |
| AC-11 | Undefined (B4) | Rewrite with the order |
| AC-12 | Yes | Say which screens: every page reachable from the menu, per persona |
| AC-13 | Loose | List the deep pages (self-review, manager review, scorecard, appraisal setup — appendix A §B) |
| AC-14 | Loose | Add a route table: every menu entry → its address. Add the unknown-address rule |
| AC-15 | Yes | — |
| AC-16 | Loose | Oracle: after Log out, `frappe.auth.get_logged_user` returns 401 and the browser is on `/login` |
| AC-17 | Loose | "Role" is not a field. Say: Employee `designation`, or nothing if blank. Say what shows for someone with no Employee record (User full name, no role line) |
| AC-18 | Wrong (B2) | Rewrite per B2 |
| AC-19 | Loose on "no flash" | Oracle: the inline script that sets `data-theme` comes before `design_system.html` in the page source; "Match my phone" follows a change of the phone's setting without reload |
| AC-20 | Loose | "The menu" — which item? Say: the Inbox menu item, the bell and the Inbox bottom-bar button show the same total. Say what the Team and Policies badges count, if any (FR-04 names three) |
| AC-21 | Yes | Add the company-wide HR half: the same fixture shows both stores to company-wide HR |
| AC-22 | Yes | Add: a person who is their own leave approver (possible for an owner) sees their leave once, under "my requests" |
| AC-23 | Loose | Needs the part table (M3) for wording and links |
| AC-24 | Mostly | Say how p95 is taken (e.g. 20 warm calls, drop none) and for which persona (company-wide HR, the worst case) |
| AC-25 | Yes | — |
| AC-26 | Yes | Add the store-HR and head-office cases (M2) |
| AC-27 | Yes | Add the payload oracle (M1) and the no-photo case (§4) |
| AC-28 | Yes | Add 12 / 50 (M1) |
| AC-29 | Covers one scope only | Give the sentence for each scope: employee or manager, company-wide HR, store HR, System Manager |
| AC-30 | Yes | — |
| AC-31 | No number | Oracle: the shell and skeleton are in the server-rendered HTML (checkable without timing); the 300 ms figure is measured and recorded (OPS-9) |
| AC-32 | Yes | — |
| AC-33 | "Short reference" undefined | Say what it is (e.g. the time and a short code that matches an Error Log entry) and that it holds no personal data |
| AC-34, 35 | Yes | — |
| AC-36 to AC-39 | Yes | — (ready now) |
| AC-40 | Yes | Say the status codes: 403 for a logged-in non-System-Manager, redirect to `/login` for Guest. 01c open question 1 (403 or 404) must be closed first |
| AC-41 | Yes | — |
| AC-42 | Yes | — |
| AC-43 | Yes | See m6, m8 |

---

## 3. Personas × the five states

✓ = the spec has a check. **Gap** = missing, and the persona can hit it.

| Persona | Loading | First time (nothing due) | No permission | Card error (counts, search) | Page error |
|---|---|---|---|---|---|
| Employee (Rahul) | ✓ AC-31 | ✓ AC-23 (Inbox); **gap:** badge at 0 | ✓ AC-30 (e.g. `#team`) | counts ✓ AC-32; **search: gap** | ✓ AC-33 |
| Employee, no payroll | ✓ | ✓ | **gap:** `#pay` opened by address (after B1: `#pay` salary tab) | as above | ✓ |
| Manager (Sandeep) | ✓ | ✓ | ✓ (`#company/…`) | as above | ✓ |
| HR with direct reports | ✓ | ✓ | n/a | as above | ✓ |
| HR without direct reports | ✓ | ✓ | **gap:** `#team` — depends on B3 | as above | ✓ |
| Store HR | ✓ | ✓ | **gap:** Org settings Save (see open question 3) | as above | ✓ |
| Owner who holds HR (Kamal) | ✓ | ✓ | n/a | as above | ✓ |
| Manager and HR in one person | ✓ | ✓ | n/a | as above | ✓ |
| System Manager, no Employee record | ✓ | **gap** | **gap:** which Me/Time pages are hidden | **gap:** today's count helper throws for no Employee | **gap** |
| Tenant without `vendor` | n/a — no frame difference (see AC-3) | | | | |
| Anyone whose session ends mid-use | — | — | — | — | **gap:** must go to login, not "page failed" |

---

## 4. Edge cases the spec misses

| Case | What the spec must say | Evidence |
|---|---|---|
| **No photo** | Rail, profile menu and search show initials. A broken image URL falls back to initials, as the logo does | `search_people` returns `image`, may be empty |
| **Very long name, job title or tenant name** | Cut with "…" on one line in the rail and top bar; full text in the profile sheet and in the accessible name; no sideways scroll at 390 px. Give a test value, e.g. "Venkata Satya Lakshmi Narasimha Subrahmanyam Chakravarthy", title "Senior Assistant Manager – Customer Relationship (Bridal Jewellery)" | — |
| **No manager** (`reports_to` empty) | Search finds only themselves and anyone below; nothing breaks. If this person has HR, B3 decides whether they are "with reports" | `_search_scope` |
| **No branch** | Covered for store HR (AC-21, AC-26). For everyone else, no change — say so | `permitted_branches` docstring |
| **Second language on a tenant** | B2. Also: a user whose `User.language` is already not English | 17 enabled on local sites |
| **Person in two companies** | (a) HR with User Permissions on two companies: counts and search cover both — spec has it. (b) One user linked to two Employee records (rehired, or moved company): **the three "who am I" helpers disagree** — `hr_api._get_employee` takes the Active record only; `goals_api._employee_id` and `alvoraa_org_structure._me` take any record, which could be the old Left one. `get_frame` and `get_nav_counts` could then describe two different people. Say which helper the frame uses, and use it in both endpoints `[UNVERIFIED — engineer to confirm whether Employee allows the same user_id on two records]` | `hr_api.py:87-95`, `goals_api.py:20-24`, `api.py:782-783` |
| **Store HR who also holds System Manager** | Not narrowed — System Manager sees everyone (`permitted_employees`). Say this is intended, so a tester does not file it | `access.py:257` |
| **HR User (not HR Manager)** | Also refused by `set_org_setting` today (030 test "an HR User is still refused"). Same question as store HR's Org settings | `00-impact-and-fix.md` (030) §6 |
| **Store HR as an HR stand-in** | If B3 keeps today's `is_manager`, store HR's Team panel lists the top-level people with no manager (often the owner, at head office, no branch) — outside their store. State the rule so it is not a new visibility leak | `get_portal_context:118-124` |
| **Administrator user** | Sent to the desk (`home_page_for` returns nothing for someone with no Employee record). If they open `/hrms-employee` directly, same as System Manager with no Employee | `auth.py` |
| **Role change while logged in** | Spec has it (hooks clear the cached context; at most one hour). Fine |
| **Two tabs, one decision** | After a decision in one tab, the other tab's count is stale until its next load. Say that is accepted in Wave 1 | — |

The usual HR edge cases (mid-period joiners, back-dating, balances, time zones, cancelled
documents) do not apply to a frame that changes no business rule. **Say so in one line**,
so the Ready box can be ticked.

---

## 5. Traceability check

| Source | Item | Spec's AC | My finding |
|---|---|---|---|
| 01c | SEC-1 | AC-40 | covered |
| 01c | SEC-2 | AC-7, 8, 40 | **gap** — M1 |
| 01c | SEC-3 | AC-21 | covered; add company-wide half |
| 01c | SEC-4 | AC-26 | **weak** — M2 |
| 01c | SEC-5 | AC-20, 21, 22 | covered once M3's table exists |
| 01c | SEC-6 | AC-8, 18 | **gap** — M1 |
| 01c | SEC-7 | AC-17 | covered; label differs from prototype (M8 a) |
| 01c | SEC-8 | AC-17 | covered; name both site types in the AC |
| 01c | SEC-9 | AC-18 | **gap** — M1, B2 |
| 01c | SEC-10 | AC-42 | **gap** — job-title case (M1) |
| 01c | SEC-11 | AC-25 | covered |
| 01c | PRIV-1 | AC-26 | covered |
| 01c | PRIV-2 | AC-27 | **weak** — payload oracle |
| 01c | PRIV-3 | AC-28 | **weak** — 12 / 50 |
| 01c | PRIV-4 | AC-23 | **weak** — payload shape |
| 01c | PRIV-5 | none | **gap** — make it an AC |
| 01c | PRIV-6 | AC-19 | covered |
| 01c | PRIV-7 | AC-26, 27 | covered (review) |
| 07 | OPS-1 | release gate | acceptable as a gate; say who checks it and when |
| 07 | OPS-2 | AC-40, 41 | covered |
| 07 | OPS-3 | AC-40, 41 | **partial** — the rollback *time* is unmeasured until 07 §4 |
| 07 | OPS-4, 5 | release plan | acceptable; OPS-4 waits on open question 1 |
| 07 | OPS-6, 7 | AC-36–38 | covered |
| 07 | OPS-8 | decision 12, not in slice | covered (user's decision recorded) |
| 07 | OPS-9 | AC-24, 31 | **weak** — AC-31 has no number |
| 07 | OPS-10 | AC-40 | covered |
| 07 | OPS-11 | AC-43 | add "own commit" |
| 00f | Design decisions 1–7 | — | 1: **gap** (M2). 2: AC-10. 3, 4, 6, 7: later waves — list under out of scope. 5: AC-43 |
| 00f | Strategy decisions 1–14 | — | 1: done. 2, 3: AC-40, 41. 4: release gate. 5: AC-26, 27. 6: AC-23. 7: AC-21 + **gap** for search. 8: AC-10 (B3). 9: AC-17. 10: AC-43. 11: process. 12, 13: out of slice. 14: AC-18 (B2) |
| 01b §14 | items 1–4, 13, 14 | AC-1, 6, 16, 18, 19, 20, 31 | 13: 2.5 s depends on OPS-1 — say so in the AC. 14: open question 2 |
| 01b §14 | items 5–12 | — | later waves — list as out of scope (M6) |
| Prototype | rail, top bar, bottom bar, search sheet, profile sheet, Inbox | — | **no story links a screen** (m1); five differences to record (M8) |

---

## 6. The three open questions — my recommendations

### Q1 · What does "go-live has settled" mean? (OPS-4, blocks the production swap)

**Recommendation:** make it three things anyone can check on a calendar, and let Surbhi
name the date once they are true.

1. **At least 10 working days** have passed since `dtc.alvoraa.co` went live. One week is
   too short: the first full week of check-ins and the first leave approvals only show
   their problems in the second week.
2. **No open portal issue from the client that stops someone working** — cannot check in,
   cannot apply for leave, cannot see a payslip — and none raised in the last 5 working
   days.
3. **Not inside the client's payroll close.** Keep the swap out of the last 3 working days
   of the month and the first 3 of the next, because the frame moves the Pay entry and
   the attendance screens that payroll depends on.

Plus the two things the swap needs anyway: compression is live on production (OPS-1),
and the new frame has run on `dev` for at least 5 working days with every persona in
§3 tried by hand.

### Q2 · Measure every Wave 1 screen at 390 px in Hindi now? (AC-12, AC-43)

**Recommendation: yes, but only the frame's own words, and only in a test.**

- The designer's bad-news point 3 and `01b` §14 item 14 both say leaving it to Wave 5 is
  too late. The frame is the part every later wave hangs off. Measuring now is cheap;
  finding in Wave 5 that the bottom bar breaks in Hindi is not.
- Use the machine-drafted Hindi strings that already exist in the prototype, loaded by a
  **test fixture only**. Ship no Hindi to users. Nothing in the menu offers Hindi (B2).
- Measure the rail, the top bar titles, the bottom bar, the profile sheet, the Inbox rows
  and the five state sentences. Pass = the same checks as AC-12: labels 12 px or larger,
  wrap to at most two lines, no clipping, nothing scrolls sideways.
- Pin the font in the test browser, and say which one. No Devanagari font is loaded today
  (appendix A §E), so the result depends on the phone's own font.
- The prototype also has Punjabi strings. Running them costs almost nothing extra. I would
  add them, but that is optional.

### Q3 · Store HR's Org settings: keep read-only, or hide?

**Recommendation: keep it, but do not show a Save button that is going to fail.**

- Store HR can read the settings today (`get_org_setting` is not guarded), and reading
  them is useful: store HR needs to know the grace minutes and the late rule.
- But today the panel shows Save controls, and the server refuses the save (slice 030,
  decision 4). That is the one thing the frame promises never to do — "no buttons that
  fail on click" (`01b` §5.1, AC-6).
- **The same happens to an HR User** (not HR Manager), who is refused as well. So this is
  not only a store-HR question.
- Small fix: `get_frame` says whether this person may save settings. The panel hides its
  Save controls when they may not, and shows one line: *"Only company-wide HR can change
  these settings."* Add one AC for it.
- If Surbhi wants Wave 1 to leave panels completely untouched, the other honest option is
  to write this down as a known exception to AC-6, with her decision recorded. Hiding the
  item is the weakest choice: store HR loses a page they can use today.

---

## 7. Definition of Ready — as it stands

| Box | State | Why |
|---|---|---|
| Brief approved | ✓ | 009 plan and decisions (there is no `01` for 034; the 009 plan stands in — say so in the spec header) |
| Clickable prototype reviewed | ✓ | Design check 22 Sep |
| Every state designed | ✓ in `01b` §5.7 | Specified per persona: **✗** (§3) |
| `01c` written | ✓ | **Not yet reviewed by the security engineer** |
| `07` §1–3 written | ✓ | **Not yet reviewed by the DevOps engineer**; §4 missing |
| Gap analysis verified in source | **✗** | The spec says "No" itself; and B1, B2 show the cost |
| Stories: named personas, INVEST, sized, linked to prototype, "must not" stories | **✗** | m1 |
| Every story has Given/When/Then with an observable oracle | **✗** | §2 |
| Traceability complete | **✗** | §5 |
| Permission matrix with negatives | Partly | Negatives are in `01c`; matrix has errors (m2, B3) |
| Edge cases | **✗** | §4 |
| NFR numbers | ✓ | — |
| Migration stated | ✓ | None |
| Compliance sub-analysis | Partly | m4 |
| No prohibited capability | ✓ | Nothing AI-shaped; no monitoring |
| Open questions owned, none blocks day 1 | ✓ | Day 1 is the split, which is ready |

**Five boxes fail. The slice is not ready, except US-10 (the split).**

---

## Open questions

| # | Question | Owner | Blocks |
|---|---|---|---|
| 1 | B1: on a no-payroll tenant, does Pay stay with Expenses only, or move Expenses somewhere else? | Surbhi | AC-1, AC-10, the menu list |
| 2 | B2: accept "offered languages = enabled **and** shipped by the portal"? | Surbhi | AC-18, SEC-9 |
| 3 | B3: does "has reports" mean direct reports only, or today's HR stand-in rule? | Surbhi, with the engineer | AC-10, the Team group, the matrix |
| 4 | M8 (a): keep the server's desk labels ("Switch to Admin", "Switch to HR Core") or use the prototype's "Switch to the full desk"? Should managers get it at all? | Surbhi | AC-17 |
| 5 | The spec's three questions: go-live settled, Hindi measurement, store HR Org settings | Surbhi | See §6 |
| 6 | 01c open question 1: 403 or 404 for the preview page | Security engineer | AC-40's oracle |

## Assumptions

- `[ASSUMPTION]` The enabled-language count on `dtc` and `aahr` production is the same
  Frappe default as on the two local sites (17). I could not check production, and should
  not.
- `[ASSUMPTION]` Line numbers are as of the worktree at `fbf5c21`.
- `[ASSUMPTION]` The prototype's `bnavItems()` is the approved behaviour for which page the
  Company button opens (HR analytics).

## Handoff note

**To the engineer (spec owner):** fix B1–B4 first; they change code, not just words.
Then M1–M8 in one pass. §2 gives the exact rewording per AC, so most of this is copying.
On your three handoff questions: AC-11 needs the order in B4; AC-18 needs B2, and the
wording "Given two or more *offered* languages" once offered is defined; AC-23 needs the
part table from M3 — the idea is sound and matches decision 6. The page split (US-10) can
go ahead on the coordinator's schedule; nothing here touches it. When the revised spec is
back, I will re-review only the changed rows.
