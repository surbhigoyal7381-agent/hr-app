---
slice: 079-pre-onboarding
artifact: 01b-ux-design-dialog-overhaul
author: hrms-ux-designer
date: 2026-11-04
status: draft
inputs: [01b-ux-design.md, 02-functional-spec.md, 03-implementation-notes.md, portal.js (ocsRows/ocsDialog/ocsSummary/ocsPreview), panels.css (.ocs-*), joining.html, people_settings.py, people_fields.py]
---

# "Details a new joiner is asked for" — overhauling the picker

**Prototype (clickable, open it first):**
`docs/slices/079-pre-onboarding/prototype-dialog-overhaul-v1.html`
Three versions side by side — **Before**, **After (the proposal)** and
**Option B (the cheapest fix)** — across all four lists, three device sizes, light and
dark. It holds no personal data.

**The short version.** The dialog is not badly drawn. It is doing three jobs with one
control and saying the same sentence six times. The overhaul is one structural change —
**the second tick stops being a tick inside a row and becomes a column** — plus words.
Everything else in it stays.

---

## 1 · Frame

A **System Manager or HR head**, on a laptop, in Organisation settings, deciding what a
new starter will be asked for before their first day. It is a once-or-twice-a-year job
with a long tail: the ticks sit there for months and nobody reads them again.

The same dialog serves four lists, and the redesign covers all four:

| `OCS.kind` | What it chooses | Rows | Second decision |
|---|---|---|---|
| `joiner` | the questions on the joining form | **6** (`MY_PROFILE_WRITE_FIELDS`) | "Must fill in" — blocks Send |
| `my` | what an employee may correct about themselves | **6** (the same six) | "Keep asking" — never blocks a save |
| `docs` | document types shown on a person's profile | **18** at PPJ, in 6 categories | none |
| `profile` | job details a Positions reader may see | **11** | none |

**Not in scope, and unchanged for them:** the **Employee** and the **joiner** never see
this screen — but every word in it decides what they see, which is the point of change 3
below. The **CXO** never opens it.

---

## 2 · Evidence

**Fact.** Read in the source on this branch: `portal.js` `ocsRows()` 7563–7615,
`ocsDialog()` 7618–7645, `ocsSummary()` 7651–7688, `ocsPreview()` 7742–7759, the change
handler 7784–7805; `panels.css` 2936–2996; `joining.html`; `people_settings.py`;
`people_fields.py`.

**Fact, measured on the bench (4 Nov 2026).** The PP Jewellers copy has **18** Employee
Document Types across six categories, 15 of them identity, statutory, verification,
employment or address. Read-only query through `bench console`; the names are
configuration, not anybody's data, so the prototype uses the real ones.

**I could not capture the dialog in a browser on the live bench.** The local bench serves
the main checkout, which is on `dev`, and `dev` has no `org-people-card` — slice 079 lives
only in this worktree. Signed in as the PPJ admin, `switchPanel('org-settings')` ran and
the card was absent. So the **Before** view in the prototype is built from the product's
own markup and its `.ocs-*` CSS copied verbatim, rendered and measured in Chrome — not
from the running site. Everything below that says "measured" was measured there.
Screenshots: `C:/Surbhi-Git/hrlocal-data/ux-review/2026-11-04/`.

**Assumed fixed:** **ALV-305** (raw column names). The whole design is drawn with the
plain words.

---

## 3 · Findings

Page prefix `OCS`. Severity uses the P0–P4 ladder.

| ID | Finding | Impact · Kind · Size | Severity | Evidence |
|---|---|---|---|---|
| **OCS1** | **The same sentence on every row.** "Must fill in before they can send the form" is written six times. It is the most repeated text in the dialog and it is a rule, not information about any row. It also doubles every row's height, so the six names — the actual content — are about a quarter of the ink | High · Fix · S | **P2** | `ocsRows()` 7609; her screenshot |
| **OCS2** | **A tick inside a tick is the wrong control for two states of one choice.** "Asked for" and "compulsory" are not two independent options; they are three states: *not asked · asked, optional · asked, must fill in*. Nesting them costs three things: the row grows and shrinks as you tick, you cannot scan down the list to see which are compulsory, and the second box is a `<label>` inside a `<label>`, which is invalid HTML | High · Fix · M | **P2** | `ocsRows()` 7605–7611 |
| **OCS3** | **Every tick throws the keyboard focus away.** Because the second tick exists only on a ticked row, `ocsRows()` rewrites the whole list on every change. **Measured:** focus a row's checkbox, press Space — focus lands on `<body>`. A keyboard user has to tab back in from the top after every single tick, and at 18 document types the scroll position is lost too | High · Fix · S | **P2, WCAG 2.2 AA 3.2.2** | `portal.js` 7792–7796; measured in the Before view |
| **OCS4** | **The dialog never says what the joiner actually sees.** There is no lead sentence, no statement of what the form is, and the row says "Where they live now" while the joiner reads "Where you live now · Where post reaches you today". HR is ticking blind | High · New · S | **P2** | `joining.html` `LABELS` vs `OCS_MY_WORDS` |
| **OCS5** | **The preview names the wrong audience on two of the four lists, and shows raw columns on one.** "Preview what a reader sees" — nobody *reads* a joining form, and My Profile is the person's own page. Worse: `ocsPreview()` picks `OCS_PROFILE_KEY` for the joiner list, and `MPF_FIELDS` holds none of the six names, so the sheet lists `cell_number`, `personal_email`… **ALV-305 fixed in the rows does not fix this.** Open the Before view's preview in the prototype | High · Fix · S | **P2** | `ocsPreview()` 7745–7755; `MPF_FIELDS` 11342 |
| **OCS6** | **Three words for one idea.** The row says "Must fill in", the button says "compulsory", the joiner's form says "Needed". Slice 079's own design promised one word: *"Never 'mandatory' on one and 'required' on the other"* | Medium · Fix · S | **P3** | `01b-ux-design.md` §8; `ocsSummary()` 7675 |
| **OCS7** | **On a phone, what you see is not what you tab.** `.ocs-ft-b [data-ocs="ok"]{order:-1}` lifts OK to the top visually, while the DOM order stays Preview → Cancel → OK | Medium · Fix · S | **P2, WCAG 2.2 AA 1.3.2 / 2.4.3** | `panels.css` 2995 |
| **OCS8** | **There is no screen anywhere that sets the compulsory *documents*.** The card reports "1 document type must be answered for: Aadhaar card" read-only. `set_people_setting` accepts `alvoraa_joiner_required_documents`; nothing in any UI sends it. This is a fifth missing value beside ALV-304's four | Medium · New · S | **P3** | no `data-ocs` for it; `people_settings.py` 288 |
| **OCS9** | At 18 rows the column heading scrolls away, so the tick columns lose their meaning half way down the list | Medium · Fix · S | **P3** | measured, docs list |
| **Keep** | OK saves and Cancel writes nothing; Escape cancels; names not counts; the amber sentence rather than a red row; grouping documents by category with the category repeated on each row; the audience count; the consequence on the button; the 620 px measure; the full-screen sheet on a phone; the amber "You cannot invite anybody yet" block | — | — | 078 §17.4; all kept as they are |

---

## 4 · The change

Three changes. Nothing else in the dialog moves.

### Change 1 — the second tick becomes a column (fixes OCS1, OCS2, OCS3, OCS9)

One row per detail. The decision lives in **columns**, so the sentence written six times
becomes **one column heading**, and the heading **sticks** while the list scrolls.

```
Detail                                          Asked for    Must fill in
-------------------------------------------------------------------------
Mobile number                                       [x]           [x]
  The joiner reads: "Your mobile number"
Personal email                                      [x]           [ ]
  The joiner reads: "Your email"
Where they live now                                 [ ]
  The joiner reads: "Where you live now"
```

- **Nothing appears or disappears.** The "Must fill in" cell is always in the row; on a
  row that is not asked for it is `visibility:hidden` — empty, not a greyed box, and out
  of the tab order. So the list is **never redrawn**, focus never moves, and the scroll
  position survives. *(Measured in the prototype: Before loses focus to `<body>`; After
  keeps it on the checkbox.)*
- **An empty cell, never a disabled one.** There is nothing to decide about a detail
  nobody is being asked for.
- The whole cell is the 44 px target; the box inside it is 20 px, as today.
- Accessible name per box: `aria-label="Mobile number — Must fill in"`, plus
  `<th scope="col">`. A column heading alone is not a reliable name on a checkbox.

**All four lists get the same table.** `docs` and `profile` have **one** tick column
("Shown"), so for them the only change is that their single column gains a heading and
the document groups become table rows. Their rows, hints, grouping and category chips are
untouched.

### Change 2 — the dialog explains itself, in three sentences (fixes OCS4, OCS6)

A **lead sentence** under the title, per list. For the joiner list:

> These are the questions on the joining form a new starter fills in before their first
> day. A joiner is asked for nothing at all until you tick it here.

A **tie line**, which is the only place three words become one:

> A detail you tick under **Must fill in** shows the joiner a `Needed` beside the
> question, and they cannot send the form until they have filled it in. Everything else
> they may leave blank.

And on every joiner row, under the name, **the question the joiner will actually read**:
*The joiner reads: "Where you live now"*. That line is the cheapest honest answer to "what
does this tick do to somebody else's screen", and it costs the same vertical space the
repeated sentence used.

For `my`, the same shape with its own truth: *"Keep asking" never blocks a save.*

### Change 3 — the footer says what it does (fixes OCS5, OCS7)

| | Today | Proposed |
|---|---|---|
| Preview, joiner | "Preview what a reader sees" | **"Show me the form a joiner fills in"** — and it shows a facsimile of the real form screen: the step list, the "Anything marked Needed…" line, each ticked question in the joiner's own words with its hint and its `Needed` chip |
| Preview, my | "Preview what a reader sees" | **"Show me the employee's own page"** |
| Preview, docs / profile | "Preview what a reader sees" | **"Show me what a reader sees"** (unchanged in meaning) |
| Save, joiner | "OK - a joiner is asked for 6 details, 6 of them compulsory" | **"Save — 6 asked for, 6 must be filled in"** — the same words as the two column headings, so the button is readable at a glance |
| Save, joiner, nothing ticked | "OK - a joiner is asked for 0 details, 0 of them compulsory" | **"Save — ask a joiner for nothing"** |
| Save, my | "OK - 6 details an employee may change, 1 we keep asking for" | **"Save — 6 they may change, 1 we keep asking for"** |
| Save, docs | "OK - 3 document types, seen by 7 people" | **"Save — 3 document types, seen by 7 people"** (word only) |
| Phone order | `order:-1` lifts OK to the top | **Delete the rule.** Stacked in DOM order: Preview, Cancel, Save. Save ends up at the bottom — where the thumb lands — *and* the tab order matches |

**One new summary line**, only when it is true: if details are asked for but none is
compulsory, *"Nothing has to be filled in, so a joiner can send the form back empty."*
The existing sensitive-documents warning is unchanged.

---

## 5 · Option B — the cheapest rung, drawn so it can be chosen

In the prototype as **"Option B — smallest possible fix"**. Today's two nested ticks,
untouched; the repeated sentence hoisted out of the rows and written once; the row label
shortened to "Must fill in".

**What it buys:** OCS1, OCS4 and OCS6, for about ten lines of change and no new CSS.
**What it leaves:** OCS2, OCS3 and OCS9 — the tick still appears and disappears, the list
is still redrawn on every tick so focus is still thrown away, and you still cannot scan
which rows are compulsory.

**Recommendation: the table.** OCS3 is an accessibility defect, not a preference, and no
amount of rewording reaches it. But Option B is a real option and it is one click away in
the prototype.

---

## 6 · The four settings ALV-304 is about — my answer

**They belong on the card, not in this dialog.** ⚠ **DECISION 1** — owner: whoever holds
ALV-304, with you.

1. **The dialog's job is one sentence.** It chooses which details are asked for. The
   notice text, two retention periods and an HR phone and email are not details asked
   for. Putting them in the picker gives it two jobs and breaks "OK saves the ticked
   list" — what would Cancel undo?
2. **The card already states the problem.** The amber block says *"You cannot invite
   anybody yet"* and names exactly what is missing. Our own rule is to act where the
   problem is stated, not on another screen.
3. **The card already shows the result.** Four hint lines report all four values the
   moment they are set. Nothing new is needed to close the loop.

**Shape:** one button inside the amber block — **"Set what a joiner is told"** — opening a
small dialog with five fields (your own words; keep details of somebody who does not join
for N days; delete a photograph of an identity card after N days; a phone number; an email
address). Drawn in the prototype: press the button on the card in the After view. **It is
a recommendation, not a build** — this slice's change is the picker.

**And OCS8 with it:** the compulsory *documents* have no UI either. Their natural home is
a second tick column in the **documents** picker — *"Must be answered for"* — which the
table in Change 1 gives for nothing. **That is a separate recommendation and not part of
this change**, because it widens what the joiner is asked for and the security note in
`01c` should see it first.

---

## 7 · States

| State | What it says |
|---|---|
| Nothing ticked (joiner) | Rows all unticked; the "Must fill in" column is empty down the page; button **"Save — ask a joiner for nothing"**. The card behind already says *"Nothing. A joiner is asked for no details at all until you tick something here."* |
| Ticked, none compulsory | Amber line: *"Nothing has to be filled in, so a joiner can send the form back empty."* |
| Document types, none ticked | Unchanged: *"Nothing ticked. Nobody will be able to open an employee's documents from the Positions page."* |
| Sensitive documents ticked | Unchanged amber sentence, now also naming the roles |
| Loading the document-type list | Unchanged (the dialog opens after the fetch) |
| Save fails / no answer | Unchanged, including the "It may have gone through" wording |
| Not a System Manager | Unchanged: the card is not rendered |
| 18 rows | Grouped by category, body scrolls, **heading sticks** |

---

## 8 · Accessibility, privacy, performance

**Measured** (Chrome, 4 Nov 2026; 3 versions × 4 lists × 1100 / 390 / 195-at-200%, light
and dark, 36 renders): **no console or page errors; nothing wider than the frame; no
target under 44 px; no text under 12 px.**

- **WCAG 2.2 AA.** OCS3 (3.2.2) and OCS7 (1.3.2 / 2.4.3) are fixed by the change. Every
  box has its own accessible name; `<th scope="col">` on both tick columns; focus rings
  on the cell, not only the box; Escape still cancels; focus goes to the heading on open
  and back to "Add or remove details" on close. Colour is never the only signal: the
  `Needed` chip carries the word.
- **200 % text (195 CSS px).** Looked at as well as measured. Names wrap to three lines,
  the two tick columns stay on screen, nothing overlaps and nothing is cut. Acceptable; I
  did **not** add a separate stacked layout for it, because the measured result does not
  need one.
- **Privacy.** The dialog shows no person's data, and the change does not widen what
  anybody can see. It makes one exposure **easier to understand** before it is saved: the
  sensitive-documents sentence now names the roles as well as the count.
- **Performance.** Strictly better: today one tick re-renders up to 18 rows of HTML; after
  the change a tick writes one class and one cell.

---

## 9 · Check before handoff

- **Heuristics.** *Match with the real world:* the joiner's own question now sits on the
  row. *Recognition over recall:* you can see which rows are compulsory without ticking
  anything. *Consistency:* one word per idea, and the button repeats the column headings.
  *Error prevention:* the preview shows the other person's screen before you save.
- **Persona walkthrough.** HR head, "make the mobile number compulsory": today — find the
  row, tick it, the row grows, a second tick appears, tick it, the list redraws, focus
  gone (2 ticks, focus lost twice). After — tick the cell in the "Must fill in" column
  (1 tick, focus kept).
- **Red team.** *Brand new:* the lead sentence says what the screen is for. *Expert in a
  hurry:* the columns are scannable, the button names the result. *Too much data:* 18 rows
  grouped, heading sticks. *Network drops:* unchanged, including "it may have gone
  through". *Not allowed to see it:* unchanged, the card is absent.
- **Refusals.** Nothing here shows one person's data to another, nothing is AI, nothing
  is a dark pattern. Removing an exposure still costs one click; adding one still keeps
  the dialog and the warning.
- **No usability test plan.** This is a settings dialog used by one or two people per
  tenant, a handful of times a year. Five-person testing would cost more than the change.
  The prototype is the test.

---

## 10 · The subtract pass

Removed on the final read, having been drawn or written first:

1. **A "Needed" chip on every row.** The "Must fill in" column already says it. The chip
   survives only in the tie line, where it ties our word to the joiner's.
2. **A three-segment control** (`Not asked · Optional · Must fill in`) — my first idea. A
   new bespoke control, two of the four lists cannot use it, and two checkboxes in two
   columns say the same thing with components we already have.
3. **A count or progress indicator for the 18-row list.** The button already carries the
   count.
4. **A separate stacked layout for 200 % text.** Measured; not needed.
5. **A confirm step on Save.** Would be a nag; the consequence is on the button.

Not removed, and worth your eye: the per-row *"The joiner reads: …"* line is the one piece
of genuinely new content. It costs one line per row on one of the four lists and it is the
only thing in the dialog that answers "what does this do to somebody else's screen". I
recommend keeping it. If you would rather not, delete that line and the design still
stands — the preview covers it, less well.

---

## 11 · What the business analyst must turn into acceptance criteria

1. The picker renders one row per item with the decisions as **columns**; the heading row
   is sticky; `joiner` and `my` have two columns, `docs` and `profile` one.
2. Changing any tick **does not re-render the list**. A test must assert that the focused
   element after a keyboard Space is still the same checkbox.
3. On a row that is not asked for, the second cell is **empty and not focusable**;
   unticking "Asked for" clears "Must fill in" in the saved value, as today.
4. Each checkbox has an accessible name containing the item name **and** the column name.
5. The phone footer renders Preview, Cancel, Save in that order in **both** the DOM and
   on screen. `order:-1` is deleted.
6. The preview button and sheet are per list: the joiner's preview shows **the joiner's
   own labels and hints**, not the Positions map and not raw column names. This needs one
   shared source for the six labels (today they exist twice — `OCS_MY_WORDS` in
   `portal.js` and `LABELS` in `joining.html`); recommend the server returns them.
7. The exact strings in §4 and §7, verbatim.
8. The word **"compulsory" does not appear**. HR reads "Must fill in"; the joiner reads
   "Needed"; the tie line is the only place both appear.

---

## Open questions

| # | Question | Owner | Blocks |
|---|---|---|---|
| ⚠ **DECISION 1** | The four ALV-304 values: on the card (my recommendation, §6) or in this dialog? | Surbhi, with ALV-304's owner | Where ALV-304 builds |
| ⚠ **DECISION 2** | The table (recommended) or Option B? | Surbhi | The build |
| ⚠ **DECISION 3** | Keep the per-row *"The joiner reads: …"* line? | Surbhi | Row height on the joiner list |
| ⚠ **DECISION 4** | OCS8 — compulsory documents as a second column in the documents picker. Widens what a joiner is asked for, so security should see it | Surbhi; `hrms-security-privacy-engineer` | A separate change, not this one |
| 5 | The six labels live in two files. One shared source, or accept the duplication and a test that compares them? | `hrms-fullstack-engineer` | AC 6 |

## Assumptions

- `[ASSUMPTION]` **ALV-305 is fixed** and `ocsWord()` knows the joiner key. Everything is
  drawn with the plain words.
- `[ASSUMPTION]` The audience figure "7 people (HR Manager, System Manager)" in the
  prototype is a **Sample**. The real figure comes from `position_readers()`.
- `[ASSUMPTION]` The document "given so far" counts in the prototype are **Sample**; the
  18 type names and categories are real, read from the PPJ copy on 4 Nov 2026.
- `[ASSUMPTION]` No tenant has a joiner list longer than six, because `joiner_choices` is
  `MY_PROFILE_WRITE_FIELDS` by identity. The table is drawn to survive 18 anyway.

## Handoff note

**Read the prototype before this document.** The one thing a document cannot show is
OCS3: open **Before**, click into a row's checkbox, press Space, then press Tab — you are
back at the top of the page. Do the same in **After** and you are still on the checkbox.
That defect, not the repetition, is why I recommend the table over Option B.

**One disagreement with the task as handed to me,** stated rather than quietly built: I
was asked to judge whether the four ALV-304 values belong here. I think they do not, and
§6 says why in three lines. If you decide they do, the picker needs a different shape
again — "OK saves the ticked list" cannot also mean "OK saves five text fields" — so
please settle DECISION 1 before the spec is written.

Nothing in this document changes who can see whose data. `01c` does not need to be
reopened for Changes 1–3; **DECISION 4 does need it** if you take it.
