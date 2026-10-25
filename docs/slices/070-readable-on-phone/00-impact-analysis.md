---
slice: 070-readable-on-phone (YouTrack ALV-217)
artifact: 00-impact-analysis
author: hrms-fullstack-engineer
date: 2026-10-25
status: waiting for Surbhi's approval — no code written
base: slice/070-readable-on-phone at 6aaf9ffd (= origin/dev, fetched 25 Oct; nothing new came in)
inputs: [01-product-brief.md, 01b-ux-design.md incl. Decisions 25 Oct, prototype v1, 01c, 07 §1-§3, 02-functional-spec.md incl. Decisions 25 Oct, change-process.md, frappe-conventions.md, no-over-engineering.md, parallel-work.md, installed Frappe v16.33.1 (read-only, container hrlocal-213)]
---

# 070 · Impact analysis and strategy

## Read this first

- **Bad news first: the portal's `api()` helper has never told its callers about a failure.**
  The portal page loads Frappe's *website* version of `frappe.call` (`frappe/website/js/website.js`,
  v16.33.1, read in the installed source). That version **never calls `opts.error`**. So the
  error branch of all 61 `api()` calls that have one never runs on a 4xx, 5xx or lost network.
  That is why "Loading…" and "Submitting…" stay for ever. (Slice 034 learned this for the preview
  frame; `next-frame.js:215` says so. The old portal never got the fix.) This finding makes item 3
  cheaper than the spec feared: one fix in `api()` wakes up 61 error branches at once.
- **One spec line does not match today's code.** AC-32 and parity row P31 say a server refusal
  (overlap, balance) shows "as today, at the top of the form". Today it shows in **Frappe's own
  pop-up**, and the button stays on "Submitting…" for ever (the in-form branch never runs, see
  above). The prototype draws it at the top of the form. I propose to build it **as drawn** (top of
  the form, no Frappe pop-up) for the three send forms only. ⚠ **E1** below.
- **Size: M overall, at the top end of M.** "Every Loading… ends" is **M if it means the spec's
  AC-22 list** (about 25 places). If it means **every** "Loading" string in the portal (about 89:
  44 in `portal.js` and 45 more in nine templates, half of them in Performance, Appraisals, Goals,
  Org settings), it is **L — and the brief's kill rule applies.** I recommend the AC-22 list.
  ⚠ **E2** below.
- **Two files I will not touch, on purpose:** `panels.css` (two other unpushed slices are in it
  today) and `hr_api.py` (no server change is needed). `time_api.py` is not used by anything this
  slice changes.

**Rung: new code, client side only** (CSS in `frame.css`, logic in `portal.js`, small template
edits). Cheaper rungs rejected: no Frappe setting controls text size, labels, request time limits
or date format on a web page (`Holiday.weekly_off` is already there and is reused, not rebuilt);
a Client Script runs on desk forms, not on this `www` page.

---

## 1 · Parallel-work check

**Incoming:** `git fetch origin dev` on 25 Oct: `origin/dev` = `6aaf9ffd` = this branch's base.
**Nothing new came in.** Nothing touches `portal.js`, `frame.css`, `panels.css`, `hr_api.py` or
`time_api.py` since the branch was made.

**Local, unpushed work in the same files** (from `git cherry origin/dev <branch>` and the work board):

| Branch | Unpushed commits | Touches | Overlap with 070 | Plan |
|---|---|---|---|---|
| `slice/066-grooming` | 10 (today) | `portal.js` **`acPaint` (1 line) and `acRow` (1 line: `label += gmTag(x)`)**, `acDetail`, a new `gm*` block; `panels.css`; `attendance_correction.py`; `check_attendance_strip.js` | **Yes — same two functions as US-2 and US-10**, different lines | **Sequence.** If 066 reaches `dev` first, I rebase and keep their `gmTag` line; the phone two-line block shows their chip too because it reuses `label`. If 070 goes first, 066 rebases. Either way: no shared lines, and the grooming chip is pinned by their test. |
| `slice/069-wall-chart` | 11 | `portal.js` Positions section, `panels.css`, `positions.html` | No — I do not touch Positions or `panels.css` | None needed |
| `slice/062-widget-after-checkin` | 3 | `portal.js` `posSave`/`posDelete` | No | None |
| `slice/064-old-v2`, `064-old-chart` | 2 each | Positions section | No | None |
| `slice/063-dtc-leave` | 0 unique (already in dev) | — | — | — |

**Hot-file rule** (`parallel-work.md` §6): `api()`, `gpFetch`/`gpSend`/`gpErr` and the tokens are
shared helpers. They change **in a commit of their own** that says so.

**Question for Surbhi:** is any other developer (not a Claude session) working in `portal.js`,
`frame.css`, `home.html` or `request-modals.html` this week?

---

## 2 · Files and functions I will change

| File | What changes | Hot? |
|---|---|---|
| `public/css/ess/frame.css` | One `@media (max-width:768px)` block: the 01b §5 token and control sizes, the failure box style, the phone day block, the date-in-words line. G8 shadow fix | no |
| `public/js/ess/portal.js` | `api()`, `gpSend`/`gpErr` (shared, own commit); one new failure-box helper; ~25 load sites; leave send (`submitLeaveApp`, `lpSubmit`); expense (`submitExpenseClaim` area, `:6030`); advance (`:6642`); `fmtDate`, `gpFmtDate`, leave cards (`:5436`), payslip line; date-in-words; `acRow`, `acPaint`; `_renderHolMonth`/`_renderHolYear`; `renderActivityFeed`; `switchPanel` (page name) | **yes** (shared helpers) |
| `templates/includes/ess/parts/home.html` | Remove "Hey there," (`:14`) and the clock date (`:27`) | no |
| `templates/includes/ess/parts/request-modals.html` | Empty line under each date box; a message area above the buttons | no |
| `templates/includes/ess/parts/requests.html` | Empty line under the attendance-request date boxes (`ar-from-date`, `ar-to-date`) | no |
| `alvoraa_portal/tests/portal_leave_063_test.js` | Line 281 pins the old sentence AC-34 removes; update it | no |
| New `alvoraa_portal/tests/portal_phone_070_test.js` + one line in `scripts/run_dom_tests.js` | The pin test for this slice | no |

**Not changed, and must stay unchanged:** `design_system.html` (shared by seven pages: login,
admin, driver portal, field check-in, vendor portal, portal-next and this portal — AC-6),
`panels.css`, `next-*.css`, `next-*.js`, `hrms-employee-next`, `hr_api.py`, `time_api.py`,
`attendance_correction.py`, `deploy/`, any DocType. Only `www/hrms-employee.html` loads
`frame.css`, `panels.css` and `portal.js` (grepped), so a change there reaches no other page.

### Every caller, grepped

| Function | Callers | What the change does to them |
|---|---|---|
| `api()` (`portal.js:5`) | 75 calls in `portal.js`, none elsewhere. 61 pass an error callback; 14 do not | Offline → error callback at once, nothing sent. 15 s → error callback once; a late answer still reaches the success callback (D10). A real failure now reaches the error callback. Frappe's own pop-up for server messages stays exactly as today for all 75 |
| `gpFetch` / `gpSend` (`:8990`, `:8975`) | 60 calls in `portal.js`; tests `test_portal_call_paths.py`, `test_browser_call_args_045.py`, `test_data_review_page_012.py`, `portal_salary_test.js` read its call shape | Same offline and 15 s rules. On a time-out the error carries the still-running answer, so the failure box can replace itself when it lands (AC-21). Call shape unchanged, so those tests are unaffected |
| `gpErr` (`:8927`) | 4 calls, all inside `gpFetch` | **SEC-4:** stops reading `r.exc` (the traceback) and the HTTP status text. Server messages (`_server_messages`) unchanged; otherwise one fixed sentence |
| `fmtDate` (`:28`) | 31 calls in `portal.js`. `vendor-portal.html:827` has its **own** `fmtDate` — not touched | Returns "6 Nov 2026" built from the ISO parts. All 31 change from "06 Nov 2026" to "6 Nov 2026" — that is the requirement |
| `gpFmtDate` (`:8916`) | 16 calls | Uses `fmtDate`; still returns "—" when empty. Today it can print "Sept" |
| Other date sites | `:3188`, `:3281-3283` (month labels — stay), `:5436` (leave cards, D4), `:5458-5465` (day labels "1 Oct Thu"), `:7389`, `:7401`, `:7928` (short dates without year — stay unless they print a full date) | Only full dates are routed through `fmtDate` |
| `acRow` (`:3823`) | `acPaint` only; `scripts/check_attendance_strip.js` extracts it | "Weekly off" or the holiday's own name; a second line shown only on phones |
| `renderLeaveApps` (`:5421`) | `loadLeaves` | Dates through `fmtDate`; its "Loading…" ends via the load failure box |
| `get_leave_summary` (`hr_api.py:2306`) | `portal.js:5092`, `:5181`, `:5253`; plus the new check. No other caller in the repo | **Not changed.** The check reuses it as is |
| `apply_leave` (`:2475`) | `portal.js:5381`, `:5869`; tests | Not changed on the server |
| `apply_expense_claim` (`:2429`) | `portal.js:6038`; tests | Not changed on the server |
| `submit_advance_request` (`:2796`) | `portal.js:6642` | Not changed on the server |

### The 44 "Loading" strings in `portal.js` (plus 45 in templates)

| Group | Sites | In AC-22's list? | What 070 does |
|---|---|---|---|
| Home: check-in status, Activity, holidays (incl. the HR card), goals and leave cards | ~6 | yes | Failure box + Try again |
| Attendance (`:3515`), Leave page (rings, table, cards, late list) | ~6 | yes | Failure box + Try again |
| Apply leave types (`:5148`, `:5248`), expense types (`:5994`) | 3 | yes | AC-23 box under the select |
| My Finances: payslips, expenses, encashment | ~4 | yes | Failure box + Try again |
| Team View (grid, on leave, late, pending, month, notes) | ~6 | yes | Failure box + Try again |
| Requests / approvals history (4 `api()` calls with no error callback) | ~3 | yes | Failure box + Try again |
| Performance, Appraisals, Goals, calibration, Org settings, Positions, Policies, Analytics | ~45 | **no** | They get the 15 s limit and offline check from the helpers, so their **existing** error text now shows instead of hanging. No new box |

---

## 3 · Persona impact

| Persona | What changes |
|---|---|
| **Employee / frontline** (the main user) | Bigger text, fields and buttons on phones; "Weekly off"; one date format; a date in words under date boxes; every load and send ends in 15 s with plain words and one Try again; the leave form keeps what was typed; two-line attendance days; a cleaner Home |
| **Line manager** | Same phone sizes on Team View and approvals; Team View loads end. No permission change |
| **HR Manager** | Same as above on a phone. On desktop: the top bar names the page; the HR holidays card ends its wait. Applying leave on behalf: the check reads that employee through the existing `employee_id` path (`_hr_target_employee`, company scope as today) |
| **CXO** | Phone sizes only. Nothing new to see; nothing taken away |

Nobody sees anything they could not see before (spec §17: visibility delta none).

## 4 · HRMS domain impact

| Domain | Impact |
|---|---|
| Leaves | Send states, the check before a resend, dates. No change to any rule, balance or Leave Application state. Frappe HR's `validate_leave_overlap` stays the server backstop |
| Attendance | Label and phone layout only. Reads `weekly_off`, already sent by `attendance_correction._day` (`:643-648`) |
| Payroll | Payslip date line only. No figure |
| Expenses / advances | Lost-answer and offline words. No server change |
| Org structure | Holiday list read only |
| Appraisals, goals, compensation | Phone tokens only, plus the helper time limit on their calls |

---

## 5 · Proposed approach

### 5.1 The two transports (shared helpers — their own commit)

- **`api()` stays on `frappe.call`.** Switching it to `fetch` would also be correct, but it would
  lose Frappe's pop-up for server refusals on all 57 callers that do not show the message
  themselves (a SEC-5 regression), and it would break the `frappe.call` stubs in seven jsdom test
  files. So `api()` gets three things only:
  1. `navigator.onLine === false` → error callback at once with `{offline: true}`; nothing sent.
  2. A 15 s timer → error callback once with `{timeout: true}`. The request is **not** cancelled,
     so a late answer still runs the success callback (D10, AC-21).
  3. Frappe's `always` hook (the only one website `frappe.call` really calls) → error callback
     once on a failed answer, with the parsed body (or `{status}` when empty). Frappe's own pop-up
     for `_server_messages` stays exactly as today.
  `[UNVERIFIED]` the order in which website `frappe.call` runs `always` and the 200 callback.
  I will prove it in a real browser before building on it; the fallback is to tell success from
  failure by the body (`message` present and no `exc`).
- **`gpSend`/`gpFetch`** get the same offline check and 15 s timer. On a time-out the rejected
  error carries `.late` (the still-running answer), so the failure box can replace itself.
- **`gpErr` (SEC-4)** drops the `r.exc` and status-text fallbacks. A server message shows as
  today; anything else is one fixed sentence by kind (offline / no answer / 5xx).

### 5.2 One failure box, used at each AC-22 load site

One small helper writes the 01b box (amber edge, `role="alert"`, heading, reason line, Try again)
into the element that said "Loading…". Try again puts "Loading…" back and calls that panel's own
loader once. A second failure says "Still could not reach the office." No timer ever calls a
loader again (AC-24, OPS-R3). Each site needs two to four lines.

### 5.3 Leave send — one state flow shared by both forms

`submitLeaveApp` (most tenants) and `lpSubmit` (DTC) share one small send step with the §6 states
(form → Sending… → success / server message / failA / failB → Checking… …). Rules:

- Button disabled while Sending… or Checking… (SEC-1, AC-38).
- Offline → nothing sent, failA (AC-26). Try again from failA sends straight away.
- Time-out, dropped connection or 5xx **after** sending → failB "may have gone through" (AC-27).
- Try again from failB → `get_leave_summary` (with `employee_id` **only** when HR is applying on
  behalf — the same id passed to `apply_leave`) → a match on **leave type + from date + to date +
  status Open or Approved** → the normal success, no resend (AC-28). No match → send once.
- **`half_day` is not used in the match.** On every tenant except DTC, `get_leave_summary` removes
  `half_day`, `half_day_date` and `leave_approver` from each row before returning it
  (`hr_api.py:2354-2357`). One rule for both tenants keeps it simple. Frappe HR's overlap check
  refuses a full day on a date that already has a half day, so a wrong "match" can never create a
  second record. It can only, in that rare case, show success for the request that already exists.
- Late answer → success once (a flag, AC-33). Form values never cleared by a failure (PRIV-1:
  page memory only).
- **E1:** the three sends (leave, expense, advance) and the check go through `gpFetch`, so a
  refusal shows at the top of the form as the prototype draws (P31), with no Frappe pop-up beside
  it. Their arguments are plain values, so the JSON body `gpFetch` sends is read the same way by
  the server. `portal_leave_063_test.js` then stubs `fetch` for those calls.

### 5.4 Expense and advance (D2)

Offline → "Nothing was sent" + Try again (nothing left the phone, so no duplicate risk). Lost
answer → "No answer from the office. It may have gone through." / "Look in your list before you
send it again." + **Close** only (AC-41, AC-42). No resend control.

### 5.5 The rest (small, independent)

- **Phone sizes:** one `@media (max-width:768px)` block in `frame.css` with the 01b §5 values.
  Nearly every size in the portal already uses the tokens (490 uses in `panels.css`, 301 in
  `portal.js`; one hard-coded 11 px, print only). Risk: a `panels.css` phone rule with the same
  weight loads later and wins. Where measurement shows that, I raise the weight of my selector in
  `frame.css` (e.g. `.emp-app .btn`), not edit `panels.css`.
- **Weekly off:** `acRow` reads `x.weekly_off` ("Weekly off") or the holiday text, escaped and with
  tags stripped (AC-9).
- **Phone day blocks (D3/D11):** `acRow` adds one line-2 element, hidden on desktop; on phones CSS
  hides the other cells and the strip. Openable rows get `tabindex="0"`, `role="button"`, a spoken
  name and Enter/Space (AC-52). Desktop table unchanged.
- **Dates:** `fmtDate` from ISO parts with a fixed English month list (no `Sept`, no time-zone
  shift). Date-in-words line under the five date boxes the spec names (leave from/to, attendance
  request from/to, expense).
- **Home:** remove the two lines; hide the Activity card when empty; drop holidays before today;
  "No more holidays in October." when none are left.
- **Top bar (G1):** `switchPanel` sets the page name. `[UNVERIFIED]` the element is Frappe's
  website navbar (`nav.navbar`, `frame.css:30`); I locate the exact text node in the browser
  before writing the line. **G8:** cause not yet found; candidates are the fixed sidebar's
  `box-shadow:var(--sh2)` (`frame.css:42`) while it sits off screen. Found in the browser, fixed
  in `frame.css`.

### 5.6 Size

| Piece | Estimate (lines changed in `portal.js`/CSS) | Size |
|---|---|---|
| Helpers (`api`, `gpSend`, `gpErr`) | ~45 | S |
| Failure box helper + ~25 AC-22 sites | ~110 | M |
| Leave send flow, both forms | ~90 | M |
| Expense / advance | ~30 | S |
| Dates | ~40 | S |
| Phone CSS block + day blocks + weekly off | ~90 | S–M |
| Home, top bar, G8 | ~25 | S |
| **Total** | **~430 lines, plus tests** | **M (top end)** |

**Kill rule:** the slice as specified (AC-22's list) is M, so it does not trigger. Making every
one of the ~89 "Loading" strings in the portal end with the new box would add ~45 sites in
Performance, Appraisals, Goals and Org settings: that is **L, and the brief says ship items 2–4
only**. I recommend AC-22's list (E2).

---

## 6 · How each requirement is met

| ID | How |
|---|---|
| SEC-1 | Button disabled while busy; check-before-resend; Frappe HR overlap check as backstop. Tested with "server saves, answer dropped" |
| SEC-2 | Expense/advance: Close only after a lost answer. Grep: no timer calls `api()`/`gpFetch` after a failure |
| SEC-3 | Reuses `get_leave_summary` unchanged; `employee_id` only on HR on-behalf. No new `@frappe.whitelist` |
| SEC-4 | `gpErr` stops reading `exc`/status text; `api()` failures use fixed sentences; test with a forced 500 as a System User |
| SEC-5 | Refusals: top of the form for the three sends (E1); Frappe's pop-up as today everywhere else; never "may have gone through", never resent |
| PRIV-1 | Form values in page memory only; 0 new uses of `localStorage`/`sessionStorage`/IndexedDB/URL |
| PRIV-2 | No new `console.*` or `frappe.log_error` with values or bodies |
| OPS-R1 | No new file; `frame.css`/`portal.js` already carry `?v={{ asset_version }}` (`hrms-employee.html:26,55`); `test_portal_split_034.py`, `test_panel_source_042.py` run |
| OPS-R2 | No font, image, nginx or gunicorn change |
| OPS-R3 | No automatic retry anywhere; Try again is one tap; leave checks first |
| OPS-R4 | §5.4 |
| OPS-R5 | No new argument; the existing `employee_id` path already returns the caller's own rows for non-HR (`hr_api.py:2308-2313`). See clash 1 |
| OPS-R6, R7 | Release steps for DevOps §5; no patch, no DocType JSON |
| OPS-R8 | Surbhi said yes: count nginx 499s on dev for a week. No code |
| Parity P1–P38 | Built as drawn. Two not drawn and taken from the spec's words: P37 (5xx) and P38 (expense/advance). P31 per E1 |

### The two clashes the analyst raised

1. **OPS-R5 ("no employee argument") vs SEC-3 ("pass `employee_id` on HR on-behalf") —
   resolved, both are met.** OPS-R5's aim is "no new reader, no foreign rows". The argument is
   not new, and the server already ignores it for a non-HR caller and limits HR to their companies.
   Without it, HR's on-behalf check would read HR's own leave, never match, and resend; Frappe HR
   would then refuse the overlap, so still no duplicate — just a worse message. **I build SEC-3.**
   DevOps should confirm in §4 that OPS-R5 means "no new argument".
2. **OPS-R3 ("Try again on leave only") vs D2 (expense/advance Try again when nothing left the
   phone) — resolved.** OPS-R3 exists because an abandoned request still commits. When the phone
   is offline nothing is sent, so there is nothing to commit twice. **I build AC-43 as specified.**
   DevOps to confirm in §4.

---

## 7 · Non-functional verdicts

| Dimension | Verdict | Why |
|---|---|---|
| Performance | **neutral** | ~4–6 KB more CSS/JS before gzip, no new file. One indexed read only when someone taps Try again after a lost leave answer. No new query on any normal path |
| Security | **improves** | Tracebacks stop reaching the screen (SEC-4). No new endpoint, argument or permission |
| Reliability | **improves** | Every call ends by 15 s; 61 error branches that never ran now run; a lost leave answer cannot become a second request |
| Scalability | **neutral** | No automatic retry, so a sick server is not hammered. Nothing grows with headcount |
| Maintainability | **neutral** | +~430 lines in a 17,650-line file, but one failure helper replaces many silent hangs, and the send flow is shared by both leave forms instead of written twice |
| Data integrity | **improves** | No duplicate leave from a retry; no resend control on expense/advance after a lost answer |
| Compliance / privacy | **improves (slightly)** | No new data; typed reason stays in page memory; no traceback text shown to HR |

---

## 8 · Risks and trade-offs

1. **Error callbacks that never ran will now run.** Some only `toast("Failed…")`. On a refusal a
   caller outside the AC-22 list may now show Frappe's pop-up **and** its own toast. Acceptable,
   and better than hanging; I will trace each of the 61 once.
2. **`always` ordering in website `frappe.call`** — unverified; proven in the browser first (§5.1).
3. **CSS weight against `panels.css`** — handled in `frame.css` only (§5.5).
4. **066-grooming in the same two functions** — sequence, keep both (§1).
5. **AC-21 on `gpFetch`** — a settled promise cannot settle again, so the late answer travels on the
   error (`.late`). One property, read by one helper.

## 9 · Tests I will add or run

- New jsdom test `portal_phone_070_test.js`: `fmtDate` cases (AC-11/12), weekly-off label (AC-8–10),
  leave flow with a stub that saves and drops the answer → exactly one send (AC-38–40), offline →
  no send (AC-26), SEC-4 forced 500 with `exc` → fixed sentence only (AC-45), no storage APIs.
- Updated `portal_leave_063_test.js` (old sentence gone, AC-34).
- `bench run-tests --app alvoraa_portal` for `test_portal_split_034`, `test_panel_source_042`,
  `test_leave` (non-HR `employee_id` returns own rows, AC-48), `test_portal_call_paths`.
- Real browser on the local bench at 390 and 360 px: the 01b measuring rules (AC-1–4), offline and
  held-answer runs (AC-17–24). The test engineer owns the full set.

---

## 10 · Decisions for Surbhi

- ⚠ **E1 — where a server refusal shows on the leave, expense and advance forms.**
  (a) **Recommended:** at the top of the form, as the prototype draws, with no Frappe pop-up (send
  through the existing `gpFetch`). (b) Frappe's pop-up as today, and the button comes back to
  Submit. *Changes:* which helper those three sends use; one jsdom test.
- ⚠ **E2 — how far "every Loading… ends" goes.**
  (a) **Recommended:** AC-22's list (~25 places, M); the other ~45 get the 15 s limit and show their
  existing error text. (b) All ~89 — L; the brief's kill rule then says ship items 2–4 only.
- **Other developers** in `portal.js`, `frame.css`, `home.html` or `request-modals.html` this week?

Not blocking, written down for later: four more date boxes have no words line (`le-date`,
`sr-from/to`, `tn-*`, `tv-from/to`, `pos-p-until`); 01c W1 (HR branch scope in
`get_leave_summary`) still wants a ticket.

## Subtract pass

Removed: a plan to move `api()` onto `fetch` (more change and a SEC-5 loss for no gain); a
separate failure helper per panel type; an abort of the timed-out request (it would break the late
answer); `half_day` in the match (not available on most tenants; the overlap check covers it); any
edit to `panels.css` or `hr_api.py`. Nothing else found to remove.

## Strategy approved — Surbhi, 25 Oct 2026

"1 top, 2a, 3 no".
- **E1:** a server refusal shows at the top of the form, as the prototype draws; the button unlocks. Leave, expense and advance submit through the existing `gpFetch`.
- **E2:** the full end state (plain words + Try again) on AC-22's ~25 places; every other call still ends at 15 s with its existing error text.
- **No human developer** is editing the portal this week.
- **Added from DevOps §4, binding:** OPS-S3 — a late answer after a time-out is ignored, and a time-out never re-enables a write button for a blind resend; OPS-S4 — time the five possibly-slow reads on ppj.localhost before choosing their limit, plus one jsdom test answering at 16 s for a read and one for a write; OPS-S2 — move the R-48 stub to `gpFetch`.
