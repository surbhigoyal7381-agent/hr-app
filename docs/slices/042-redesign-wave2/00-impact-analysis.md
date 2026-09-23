---
slice: 042-redesign-wave2
artifact: 00-impact-analysis
author: hrms-fullstack-engineer
date: 2026-09-24
status: written before any file was opened for editing
inputs: [02-functional-spec.md revision 2, 01c-security-privacy-requirements.md, 07-devops-inputs.md, ../034-redesign-wave1/03-implementation-notes.md]
---

# Wave 2 — Home and Inbox: impact analysis and strategy

## Said first

**This branch now sits on top of Wave 1, not on `dev`.** `slice/042-redesign-wave2`
was rebased onto `slice/034-redesign-wave1` (`1f3ffdd`). Wave 2's code imports
`inbox_api`, `frame_api`, `ess_part()` and the static frame files, all of which exist
only on Wave 1's branch. **034 must reach `dev` before 042 can.** Nothing here is
pushed, merged or deployed.

**One thing in the spec is not built: D-2.** Who may decide an attendance correction,
and from when. The approved design says the manager decides and HR steps in after two
working days; the code sends every correction to whoever holds submit permission on
Attendance Request (`attendance_correction._may_review:240`). That is a permission
change wearing a routing change's clothes, and it is with Surbhi. **The fail-closed
default is what is built: no new decider.** The corrections part counts and lists
exactly the rows Wave 1 already counts, through `review_queue_filters` unchanged. No
two-working-day rule, no "with <manager> until <date>" label, no new scope.

---

## 1. Functional impact

### 1a. Cross-module reach

| App | Touched how |
|---|---|
| `alvoraa_portal` | **All the work.** `inbox_api.py` **extended** (Wave 1 wrote it; Wave 2 adds `parts()`, `rows()` and `get_inbox`). New `home_api.py`. `hr_api.py` — `get_week_presence` **deleted** (SEC-9 / AC-59). `public/js/ess/portal.js` and `templates/includes/ess/parts/home.html` — the old week-grid card removed with it. New markup parts, CSS and JS for Home and Inbox |
| `hrms` (our fork) | **Read only.** `alvoraa_hr_core/access.py` (`permitted_employees`, `permitted_companies`, `refuse_own_decision`) and `alvoraa_policy_library/access.py` are called, not changed |
| `erpnext` | Read only — Employee, Attendance, Holiday, Leave Application, Shift Assignment |
| `frappe` | Read only |
| `alvoraa_goals` | Read only, through `goals_api` |
| `alvox_compensation` | Not touched, not installed |

### 1b. Every caller of every function being changed — grepped, not assumed

| Function | Callers found | What happens to them |
|---|---|---|
| `hr_api.get_week_presence` | `public/js/ess/portal.js:1589` only (one call site, in the old portal's Home) | **Both go.** The endpoint is deleted and `loadHomeWeek()` with it. No other tracked file names it |
| `inbox_api._leave_approvals` and its five siblings | `inbox_api.get_nav_counts` only | Reshaped into parts; `get_nav_counts` keeps its exact payload shape |
| `inbox_api.get_nav_counts` | `public/js/ess/next-frame.js`, `tests/test_inbox_counts_034.py`, the registry test | Payload unchanged. Wave 1's tests must still pass unedited — that is the regression proof |
| `attendance_correction.review_queue_filters` | `inbox_api._attendance_fixes`, `attendance_correction.to_review` | **Unchanged.** D-2 is not built |
| `goals_api.get_pending_approvals_count` | `inbox_api._goal_updates`, the old bell | Still called for the count; Wave 2 adds a rows query beside it using the same scope helper |
| `goals_api.get_pending_approvals` | the old bell path | Left alone. A test pins that no portal boot path calls it |
| `attendance_correction.raise_correction`, `withdraw`, `decide` | the old Time screen | Reused, unchanged. Wave 2 adds no second write path |

### 1c. Persona impact

| | Rahul (employee) | Sandeep (manager) | Priya (store HR) | Kamal (HR + reports) | Asha (no Employee record) |
|---|---|---|---|---|---|
| **Gains** | a Home that leads with what needs him; his own gaps as a list he can fix; his own requests and their state | one queue instead of three, the number matching the list | the same, scoped to her store | the same | a working Home and an Inbox that says "All clear" |
| **Loses** | the old Home's week grid, which named up to 40 department colleagues and their per-day away state | the same grid | the same | the same | nothing |
| **Unchanged** | who may decide his correction | who may decide a correction | her store scope | — | — |

The loss is deliberate and is the security review's SEC-9. It is the one user-visible
narrowing in this slice and it needs saying out loud at the gate, because somebody will
notice the grid has gone.

### 1d. HRMS domain impact

Leaves (approve, apply, balances — read and act through existing actions), attendance
(check-in, corrections, gap detection — new read-only query), appraisals and goals
(status read only; **never** `get_my_review`, which creates a row), payroll (one
read-only "payslip is ready" row, behind the real `plan_payroll` gate), policies
(acknowledgement count and list), org structure (who reports to whom, for scope only).

**No new DocType, no custom field, no patch, no migration, no `bench migrate`.**

---

## 2. Non-functional verdict — seven dimensions

| Dimension | Verdict | Why |
|---|---|---|
| **Performance** | **improves** | The old bell took 16.4 s for HR because `get_pending_approvals` walked one employee at a time. Wave 2's portal never calls it. `get_home` drops `counts`, so the six parts are computed **once** per page load, not twice (OPS-W2-6). Risk to watch: a Part must not run its filter twice when `count()` and `rows()` are both asked |
| **Security** | **improves** | A whitelisted endpoint returning named per-day absence for 40 department colleagues is deleted. Every new endpoint ships its Guest, wrong-persona and scope tests in the same commit. No scope helper may return `{}`. The list and the action share one scope function, and an **undrawn** row is proved refusable by hand |
| **Reliability** | **neutral to improves** | One card failing no longer fails the page — each Home card has its own error state. No new background job, no new external call. Risk: `get_home` gathers from six sources, so one throwing must degrade that card, not the call |
| **Scalability** | **degrades if built naively, neutral if built as specified** | The gap rule and the team summary both grow with headcount. Everything is a set-based query with an `in` list and a cap of 50; no query inside a loop. The honest position: **the 1,000-employee fixture does not exist**, so every number in the spec's §13 is a target nobody has measured (OPS-W2-8) |
| **Maintainability** | **improves** | Six hand-written filter pairs become one `parts()` helper with one filter per part. A part with no scope declaration raises at import, so the next person cannot add a silent one |
| **Data integrity** | **improves** | The count and the list come from one filter. Nothing is cached to disk. The browser never decrements a stored number — counts are re-read from the server after every decision |
| **Compliance / privacy** | **improves, with one new disclosure refused** | Fixed payload key list on `get_home`. Counts carry no names and no ids. Presence counts only, minimum group of five with complementary suppression. **The joiners card is not built** — D-8 is unanswered and the fail-closed default is own anniversary only |

---

## 3. Parallel-work check

| Question | Answer |
|---|---|
| **What came in while I was away** | `git fetch origin dev` → nothing new since `8718f27`. The rebase onto `slice/034-redesign-wave1` replayed four docs-only commits with no conflict |
| **Files I will change that somebody else is in** | `inbox_api.py` — Wave 1's session wrote it and is **done locally** (board: 8 commits, not pushed). I extend it on top of its final commit. `portal.js` and `parts/home.html` — Wave 1's board says explicitly "NOT touched", so they are free; 043 (Wave 3) has its own worktree and its spec puts the Time and Pay screens there, not Home |
| **The one collision this slice was warned about** | Two sessions writing `inbox_api.py`. Avoided by rebasing onto Wave 1 and **extending** the file rather than recreating it. Wave 1's `test_inbox_counts_034.py` is left unedited and must still pass |
| **Plan** | Sequence, not split. Wave 1 first (done), then Wave 2 on top |
| **Bench** | **My own container `hrlocal-042` and site `test042`**, with its own redis and its own sites volume. `hrlocal-bench` is not touched. One `bench run-tests` at a time |
| **Board** | Claimed by path before the first edit |

---

## 4. Strategy

**Build order, and why.**

1. **`inbox_api.parts()` first.** Every number on both screens comes out of it. One
   filter expression per part, a `count()` and a `rows()` on it, and a **scope
   declaration as data** — a part built without one raises at import. Then `get_inbox`.
   Wave 1's `get_nav_counts` payload does not change shape, so Wave 1's tests are the
   regression proof.
2. **`home_api.get_home` second**, with the fixed key list enforced on the way out, the
   same discipline as `frame_api.FRAME_KEYS`.
3. **Retire `get_week_presence` in its own commit with the new presence card**, because
   AC-59 is a same-commit rule.
4. **The panels last** — markup parts, static CSS and JS, no new Jinja include.

**Trade-offs I am taking, and the consequences nobody asked about yet.**

- **No cache.** The counts are computed live on every page load. A cache would need an
  invalidation on five different doctypes' submit and cancel hooks, and a stale badge is
  exactly the "number that does not match the list" this slice exists to remove. The
  cost is that `get_nav_counts` stays a real query on every load; the frame already calls
  it once per load, not once per panel.
- **`get_home` carries no `counts`.** Decided in the spec (§8). The cost is one extra
  HTTP call. The benefit is one source for the badge. DevOps recommended the other way
  and that is recorded.
- **The corrections part keeps today's routing.** D-2 blocks the change, not the part.
- **The joiners card is not built at all**, rather than built and hidden. A hidden card
  is still a live query.
- **Deleting `get_week_presence` removes a working card from the old portal.** That is
  the honest cost of SEC-9 and it belongs in front of Surbhi, not in a footnote.

**What I cannot prove at this stage:** every number in §13. The 1,000-employee and
20-person fixtures do not exist. I will assert query counts and payload bytes on the
fixtures I build, and say plainly which budgets remain untested.
