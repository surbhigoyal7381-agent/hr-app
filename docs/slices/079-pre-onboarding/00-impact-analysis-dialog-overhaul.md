---
slice: 079-pre-onboarding
artifact: 00-impact-analysis-dialog-overhaul
author: hrms-fullstack-engineer
date: 2026-11-04
tickets: [ALV-310, ALV-305, ALV-304]
status: strategy proposed
inputs: [01b-ux-design-dialog-overhaul.md, prototype-dialog-overhaul-v1.html,
         01c-security-privacy-requirements.md, 02-functional-spec.md,
         portal.js (ocs*), panels.css (.ocs-*), people_settings.py,
         hrms/alvoraa_org_structure/settings.py, joiner_invite.py, joining.html]
---

# Three tickets, one screen, one change

ALV-310 (the table), ALV-305 (raw column names) and ALV-304 (the settings that cannot
be set) all change the people-settings card and the one picker dialog it opens.
Building them three times would mean writing the row markup three times. They go in
together.

Surbhi approved the design on 4 Nov 2026 ("Table - implement it for all such
dialogs"), with the ALV-304 fields **on the card, not in the picker**.

---

## 1 · Which rung of the ladder

**Rung 4 — new code in two existing files**, plus one extra field on an existing
endpoint's reply. No new DocType, no new endpoint, no new app, no new dependency.

| Cheaper rung | Why it was rejected |
|---|---|
| 1 · Already there | Frappe ships no picker of this shape. The card and dialog are ours. |
| 2 · Configuration | There is no setting that changes a bespoke page's layout, and the four missing values are exactly the configuration nothing can reach today. |
| 3 · Customisation | A Client Script or Property Setter acts on Desk forms. This screen is a `www` page with its own JavaScript; neither applies. |

The ALV-304 build also stays on rung 4 **because the back end already exists**:
`people_settings.set_people_setting` already accepts all five keys and already hands
them to `org_settings.set_cover_setting`, which owns the System-Manager rule, the
range check and the `Version` row. Only the form is missing. **No new server
validation, no new endpoint, no new key.**

---

## 2 · Functional impact

### Cross-module reach

| App / module | Reach |
|---|---|
| `alvoraa_portal` | `public/js/ess/portal.js` (`ocs*`), `public/css/ess/panels.css` (`.ocs-*`), `people_settings.py` (one output field) |
| `hrms` (`alvoraa_org_structure`) | **Read only.** `settings.py` `set_cover_setting`, `_set_access_setting`, `DEFAULTS`, `ACCESS_GRANTING`, `_DAYS` ranges — all unchanged |
| `alvoraa_goals`, `alvox_compensation`, `erpnext` | None. No shared DocType, hook, field or report touched |
| `joining.html` (the joiner's own page) | **Read only.** Its six `LABELS` are copied into the picker so the dialog can say what the joiner reads. Nothing on the joiner's page changes |

### Every caller of every function I will change

Grepped across the whole repository (`*.js`, `*.html`, `*.py`):

| Function | Callers | Risk |
|---|---|---|
| `ocsWord(key, field)` | `ocsPaint` ×3, `ocsRows`, `ocsPreview` — all inside the `ocs` block in `portal.js`. Nothing outside it | None. Adding the joiner key to its first branch cannot change the two keys it already answers |
| `ocsRows()` | `ocsDialog()` only | Its return value becomes a `<table>`. The only other reader was the change handler's `body.innerHTML = ocsRows()` — which this change **deletes**, because the whole point is to stop redrawing |
| `ocsDialog()`, `ocsSummary()`, `ocsPick()`, `ocsPreview()`, `ocsSave()`, `ocsClose()` | The card's own click handler, and `portal_joiner_079_test.js` (which calls `ocsLoad`, `ocsPick`, `ocsSave` by name and asserts they are reachable) | The test's assertions about the nested tick must change — see §6 |
| `get_people_settings()` | `portal.js` `ocsLoad()`; `test_people_settings_078.py`, `test_joiner_078.py`, `test_joiner_079.py`, `portal_joiner_079_test.js` fixture | Adding a key to the returned dict cannot break a reader of the other keys. The existing `not_hired_days` / `document_days` keys keep their present meaning and values |
| `set_people_setting()`, `set_cover_setting()`, `_set_access_setting()` | Unchanged — I add callers, not parameters | None |

### Persona impact

| Persona | Before | After |
|---|---|---|
| **CXO** | Never opens Organisation settings; the card is System Manager only | **No change.** Nothing about what a CXO sees or can do moves |
| **HR Manager** | Can see neither the card nor these settings (`_require_system_manager`, and all but the two contact keys are in `ACCESS_GRANTING`) | **No change.** The new button is inside a card an HR Manager is never served, and the server refuses the write regardless. The two contact keys stay HR-settable through the existing Org Setup page, as today |
| **Employee** | Never sees this screen | **No change to any right.** One second-order effect, which is the point of ALV-304: once a System Manager sets the four values, HR can invite joiners, so the joining form becomes reachable. That is the gate working, not a widening |
| **The joiner** (not a persona, but the person the words are about) | Reads "Needed" on their own form | Unchanged. The picker now *shows HR* those exact words before they save |

### HRMS domain impact

Leaves, attendance, payroll, appraisals and org structure: **none.** No DocType, no
hook, no scheduled job, no report. The only domain object in reach is the joiner
submission, and nothing about it changes — the values the gate reads can now be set,
which is what the gate was waiting for.

---

## 3 · The seven non-functional dimensions

| Dimension | Verdict | Why |
|---|---|---|
| **Performance** | **Improves** | Today a tick rewrites up to 18 rows of HTML (`body.innerHTML = ocsRows()`). After the change a tick writes one class on one `<tr>`, one `checked` property, the summary line and the button. Query count unchanged: the card is still one `get_people_settings`, the document list still one `get_document_type_choices`. ALV-304's dialog adds **no fetch to open** — it draws from the payload the card already holds — and up to 5 POSTs on save, only for fields that changed |
| **Security** | **Neutral** | No new endpoint, no new whitelisted function, no new key, no new role, **no new `ignore_permissions`** (count added: **zero**). Every write still goes through `set_people_setting` → `set_cover_setting` → `_set_access_setting`: System Manager only, refusal logged with its rule id, `Version` row in the same transaction. The two contact keys keep their deliberate HR-Manager path. Doors (`data-doors.md`): the only server change is one extra output field on an endpoint already gated by `_require_system_manager`, and it carries **setting key names**, not values and not anybody's data |
| **Reliability** | **Improves** | The ALV-304 dialog validates nothing itself as a gate — it marks the inputs with their range so the browser helps, and **the server's refusal is what decides**. On refusal the dialog stays open with what was typed and shows the server's own sentence. After a save the card repaints **from the server** (`ocsLoad()`), never from what was typed, so the amber block can never say "ready" because a browser thinks so. A partial save of independent settings leaves the gate still closed and the card still saying what is missing — fail-safe |
| **Scalability** | **Neutral / slightly improves** | The longest list is 18 document types and will not grow with headcount. Removing the per-tick redraw makes the 18-row case cheaper, not dearer. Nothing here scales with employees, months or transactions |
| **Maintainability** | **Improves** | One row-building function for all four lists instead of a row builder plus a nested second control; the repeated sentence becomes one column heading; one word for one idea. Six strings deleted. Against that, the picker gains one duplicated label map (§5, OQ5) with a test that pins it |
| **Data integrity** | **Neutral** | No cache, no denormalised field, no new transaction boundary. Each setting is still one `set_default` plus one `Version` row in one transaction, as today. The "compulsory ⊆ asked" rule keeps all three of its existing layers (browser prune, setter refusal, reader intersection) — §4 explains how, now that the row is no longer redrawn |
| **Compliance / privacy** | **Improves** | Nothing personal is shown, logged or widened; no field is added to a list, export, notification, report or API reply that carries a person's data. Two real improvements: the card stops printing a retention number the employer never chose (ALV-304's second half — the gate reads the value raw on purpose, so a printed default was the screen contradicting the gate), and HR can finally discharge 079-PRIV-1 (document clock) and 079-PRIV-3 (the employer's own notice) through a screen instead of a `bench` command |

### Security and privacy requirements this change must meet

Read `01c-security-privacy-requirements.md`. Every item below is already met by the
path I am reusing; none needs new code:

- **079-SEC-1** (the tick lists decide what a stranger is asked for) — unchanged
  setter, unchanged `ACCESS_GRANTING` membership, unchanged refusal and `Version` row.
- **079-PRIV-1** (the document clock) — same setter, same 30–60 range, now reachable.
- **079-PRIV-3** (the employer's own notice) — same setter, now reachable. Still a
  hard precondition: no text, no form.
- **078-SEC-5** (System Manager only) — enforced server side in two places already
  (`_require_system_manager` on the read, `_set_access_setting` on the write). The new
  button hides nothing and grants nothing; hiding a button is not a permission.
- **079-SEC-1's "compulsory ⊆ asked"** — three layers kept, see §4.

---

## 4 · Before the first line of code

### Race conditions

- **Two System Managers in the dialog at once.** Last save wins, with a `Version` row
  each, so the change is attributable and recoverable. This is today's behaviour and
  this change neither improves nor worsens it. Adding a lock would be new mechanism
  for a screen used a handful of times a year by one or two people.
- **The picker's two-step save** (asked, then required) is unchanged, including its
  deliberate order: the setter refuses a compulsory name that is not asked for, so
  asked must land first.
- **ALV-304's multi-field save.** Five independent settings, so I send **only the
  fields that changed**, one after another, and stop at the first refusal with that
  field's own message. A partial save cannot produce a half-valid state: each key is
  independently valid or refused, and the gate stays closed until all four are set.
- **A tick arriving while a save is in flight.** Unchanged: the OK button is disabled
  for the duration, as today.
- **Cache between an invalidation and a write.** None. `frappe.db.set_default` clears
  Frappe's own defaults cache; I add no cache of my own.

### Edge cases

- **None, one, many.** 0 ticked (all four lists), 1, 6 (joiner / my), 11 (Positions),
  18 in 6 groups (documents).
- **A document-type list that is empty** — a site with no `Employee Document Type`.
  Today that renders nothing; a table would render headings over an empty body, which
  is a heading that lies. The dialog says so in a sentence instead.
- **A row that is not asked for.** Its second cell is empty (`visibility:hidden`), so
  it is not clickable and not in the tab order — not a greyed box, because there is
  nothing to decide about a detail nobody is being asked for.
- **A person with no employee record, no company, no shift** — irrelevant here; this
  screen is about settings, not about anybody.
- **A value the employer has not chosen.** Blank input, placeholder giving the range,
  and the card says it is not set rather than printing our default.
- **Only one of phone and email.** The gate passes on either (`joiner_invite.hr_contact`
  also falls back to the Company's own email), so the dialog must not claim both are
  needed. Its hint says either one is enough.
- **A back-dated or mid-month anything** — no dates are computed here.

### State transitions

- **A detail: not asked → asked, optional → asked, must fill in**, and every step
  back. The transition the spec forgot is *must fill in on a row that is not asked
  for*. It cannot be reached by hand, and if it is reached any other way it is pruned
  in `ocsSave`, refused at the setter and intersected again at every reader. All three
  layers survive, and the second and third are the ones that hold whatever a future UI
  does.
- **Untick "Asked for" on a row whose "Must fill in" was ticked.** Today the redraw
  removed the box. With no redraw I must, in place: clear `OCS.need[field]`, uncheck
  that row's box, and add the row's `off` class. Those three together are the whole
  behaviour change, and the existing pin test for it is rewritten to assert the box is
  **present, unchecked and out of the tab order** rather than **absent**.
- **The joiner gate: blocked → can invite.** Only a complete set of four values moves
  it, the server decides, and the card repaints from the server afterwards.
- **Cancel, Escape and the cross** still write nothing, in both dialogs.

---

## 5 · What I will build

Smallest version of each ticket, in two files plus one line of Python.

**ALV-305 — two one-line fixes, two surfaces.**
`ocsWord()` treats the joiner key like the My-Profile key (they are the same six
fields by identity). `ocsPreview()` stops falling back to the Positions map for the
joiner list. Both, because fixing the rows does not fix the preview.

**ALV-310 — the table.**
`ocsRows()` returns `<tbody>` rows for all four lists; `ocsDialog()` wraps them in a
`<table>` with `<th scope="col">` headings that stick. The second decision is a
column, always present, empty on a row that is not asked for. The change handler
stops rewriting the body. Footer: the preview button names the screen it opens, the
save button repeats the column words, and `.ocs-ft-b [data-ocs=ok]{order:-1}` is
deleted so the phone's visual order is its tab order. One word for one idea:
**"Must fill in"** on HR's screens, **"Needed"** on the joiner's and the employee's,
the tie line the only place both appear, and the word "compulsory" gone from the UI.

**ALV-304 — one button, one small dialog, on the card.**
In the amber block, inside the section that already says what is missing. Five fields
with the design's own words. It saves through `set_people_setting`, field by field, in
the order the card lists them. And the card stops printing a retention number nobody
chose: `get_people_settings` gains **one** output field, `joiner_not_ready_keys` (the
key names behind the labels it already returns), so the card can tell "set to 180" from
"defaulted to 180" — which is the distinction the gate already makes deliberately.

**Open question 5 from the design, answered.** The six joiner-facing labels live in
`joining.html` as Jinja-translated strings and are needed in `portal.js`. One shared
source would mean a new server-side constant exposed through two different translation
mechanisms — more code than the duplication. **I duplicate the six labels in
`portal.js` and add a static test that fails if the two lists ever disagree.** Declared
as an acceptable simplification.

### Not in scope, deliberately

- **The compulsory-documents column (OCS8 / design DECISION 4).** The designer
  proposed it and Surbhi agreed in principle, but it decides what a stranger is asked
  to hand over and it has not had the security review. The table makes it nearly free
  to add later; it is not added now, and `01c` should see it first.
- **ALV-311** — choosing documents and fields separately per place. Parked until 081.
- **Slice 082** — the joiner-to-Employee button.
- Nothing else on the card, and no refactor of the three sections the tickets do not
  name.

---

## 6 · Parallel-work check

### Files I will change

| File | Hot? | Rule I am following |
|---|---|---|
| `alvoraa_portal/alvoraa_portal/public/js/ess/portal.js` | Hot by nature (the portal's single script), though not in the hot-file table | I touch only the `ocs*` block (≈7320–7830) and its own name prefix. No shared helper (`gpFetch`, `drT`, `esc`, `hmOpenSheet`, `switchPanel`) is changed. No re-indentation, no renaming, no reordering outside that block |
| `alvoraa_portal/alvoraa_portal/public/css/ess/panels.css` | No | New rules appended inside the existing `ocs-` section; one rule deleted (`order:-1`), which is the ticket |
| `alvoraa_portal/alvoraa_portal/people_settings.py` | Listed as a shared API file in spirit | **One new output field.** No signature changed, no function removed |
| `alvoraa_portal/tests/portal_joiner_079_test.js` | No | Existing assertions about the nested tick are rewritten to the approved behaviour; the intention each one pinned is kept (see below) |
| New: a DOM test for the table, the words and the ALV-304 dialog | — | New file, registered in `scripts/run_dom_tests.js` with `EXPECTED_BROWSER_TESTS` bumped in the same commit |

### Who else is in them

- **Incoming from `origin/dev` since this worktree's base:** nothing. My base **is**
  `f40e368b`, today's head — the design and prototype commit itself.
- **Landed on dev in the last hours, read before starting:** `aefb68d0`, `174c6c2f`,
  `99e436b2`, `4de0c01b` (ALV-302, the biometric sync account and far-dated machine
  punches — `attendance` and `auth`, no overlap); `ccfeab34` (ALV-303, removed a camera
  emoji from a button in `portal.js` — a different block, no overlap, and the reason
  the design-system emoji gate matters); `aaa55c5b`, `55b4a698` (CI and slice 081 docs).
- **The main checkout holds other sessions' uncommitted edits**, including in
  `portal.js`, `hooks.py`, `auth.py` and `people_settings.py`. **I have not touched
  them and will not.** I work only in `.claude/worktrees/083-dialog-overhaul`, and I
  will not bring anything into local `dev` or onto the bench without saying so, because
  doing that would mix their work into a test run.
- **Slice 081** is mid-CI in `.claude/worktrees/081-bill-evidence`. Not entered.
- **Other developers:** unknown to me. `git log origin/dev --since="7 days ago"` on
  `portal.js` shows this repository's usual several-sessions-a-day traffic. **Worth
  asking Surbhi whether anybody else is in the `ocs` block right now**; nothing on the
  work board claims it.

### The plan where there is overlap

**Split.** `portal.js` is edited by many sessions but almost never in the same block.
I own the `ocs*` block and the `.ocs-*`/`.oc2-*` CSS for this change and touch nothing
else in either file, so a concurrent change elsewhere in the file merges cleanly.
`people_settings.py` gets one added line in one dict — additive, so a concurrent change
to another part of that file merges.

### The test that pins each existing feature I touch

| Feature I touch | Pinned by |
|---|---|
| Only a ticked row can be compulsory; unticking clears it | `portal_joiner_079_test.js` — rewritten to the new shape, same intention, plus `test_joiner_079.test_a_compulsory_detail_nobody_is_asked_for_is_refused` (server, untouched) |
| The picker offers the six the code allows, never bank or IFSC | `portal_joiner_079_test.js` — unchanged assertion, still passing |
| Asked saves first, required second | `portal_joiner_079_test.js` — unchanged assertion |
| The card names what is missing on every visit | `portal_joiner_079_test.js` §5 — unchanged |
| Both of counsel's periods are stated separately | `portal_joiner_079_test.js` AC-92 — kept, and extended so it also proves a number the employer never chose is **not** printed |
| The plain words, not the database columns (ALV-305) | **New**, asserting the *visible text* of a row and of the preview sheet — the old test asserted `data-ocs-v`, which legitimately is `cell_number`, so it passed while the screen was wrong |
| Focus survives a tick (ALV-310's real defect) | **New**: press Space on a row's box and assert `document.activeElement` is still that box |
| The four values can be set from a screen (ALV-304) | **New**, asserting **what the dialog sends** — the keys and values in the POSTs — not what it draws |
| The six joiner labels match `joining.html` | **New** static test |

---

## 7 · Risks and trade-offs

| Risk | Size | What I do about it |
|---|---|---|
| The rewritten pin test is where a feature could quietly disappear | Medium | Each rewritten assertion keeps its sentence and its AC number, and the behaviour it pinned is re-proved in the new shape. The server-side refusal that really enforces it is untouched |
| A `<table>` inside a dialog at 200% text on a 390 px phone | Low | The designer measured 36 renders at 1100 / 390 / 195-at-200% in both themes: nothing cut, nothing under 44 px, nothing under 12 px. I build the same CSS the prototype measured |
| `check_design_system.py` counts colours, font sizes, shadows, radii and emoji with a limit of 0 for loose colours and emoji, and it expands `portal.js` into the page it scans | Medium — one camera emoji cost a whole CI run today | The new CSS uses only existing tokens and adds no colour, shadow, radius, gradient or font size. The em-dash and curly quotes in the copy are typographic, not emoji. I run the gate locally before committing |
| The ALV-304 dialog is drawn in the prototype only as a recommendation sheet, not as product chrome | Low | I build its five fields and their words exactly as drawn, inside the existing `.ocs-back` / `.ocs-dlg` dialog the picker already uses, rather than inventing a second dialog shape. Declared as a departure in the notes |
| ALV-304 lets HR switch the joiner form on for the first time, so a path that has never run in anger becomes reachable | **Worth Surbhi's eye** | Not a code risk in this change — the gate, the form and the retention jobs all shipped in 079 and are tested. But this is the change that makes them reachable at a tenant, so the first switch-on should be deliberate and watched. `ALV-215` is still open against switch-on |

---

## 8 · What I recommend

Build all three as one change, in the order ALV-305 → ALV-310 → ALV-304, so each
commit is testable on its own. Then run the full suites named in the task
(`test_joiner_078`, `test_joiner_079`, `test_browser_call_args_045`,
`test_portal_security_010`, `test_people_settings_078`, the DOM suite) and the Lint
job's static gates, on a container of my own so no other session's run is disturbed.

Nothing here needs a push, a deploy, a migration or a bench command on a shared site.

**Two things I would like Surbhi's word on, and neither blocks the build:**

1. Is anybody else working in the `ocs` block of `portal.js` today?
2. ALV-304 makes the joiner form switchable-on for the first time. Should the card's
   amber block go away silently once the four values are set, or should switching the
   form on stay a separate, deliberate act? **Today it already is** —
   `alvoraa_joiner_form_on` is a separate setting and I am not touching it, so the
   answer is "it stays separate" unless she says otherwise.
