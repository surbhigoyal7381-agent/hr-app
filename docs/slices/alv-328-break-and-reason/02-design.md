# ALV-328 - Design: break per day, and the "why" for a day

| | |
|---|---|
| Slice | ALV-328 (builds on ALV-326, branch `slice/alv-326-shift-hours`) |
| Stage | Design - waiting for Surbhi's design check |
| Author | `hrms-ux-designer`, 12 Nov 2026 |
| Reads | `01-product-brief.md` (approved 12 Nov 2026, four decisions final) |
| Next | `hrms-security-privacy-engineer`, then `hrms-business-analyst` |
| Prototype | `docs/slices/alv-328-break-and-reason/prototype.html` (not published: no Artifact tool in this run) |

**Bad news first.**

1. **I did not capture the live screens this run.** Two earlier runs stopped before writing,
   so I drew from the real code and CSS instead (`portal.js` `acRow`, `acDetail`,
   `aiPerson`; `panels.css`; `frame.css`). Every "Fact" below is read in code, not seen in a
   browser. The prototype copies the real class names and tokens.
2. **The existing "Missing punch" tag can disagree with the pay engine.** `month()` counts
   the raw punches (`attendance_correction.py` 784-788). The engine first folds repeat scans
   within 2 minutes. So "In 09:02, In 09:03, Out 18:10" shows "Missing punch" on screen, but
   the engine sees a clean two-punch day. This slice's break figure follows the engine. The
   tag is outside this slice; see finding A4 and question Q1.
3. **The Insights one-person table already runs wider than a phone** (5 columns,
   `white-space:nowrap`, no scroll wrapper). Adding a sixth column makes it worse, so the
   design wraps it in the existing `.tbl-wrap` (finding I2).

---

## 1 · Frame

**An employee (often on a ~360 px Android) opens the Attendance page in pay week, taps a
day that cost them a quarter, and wants to see how long their breaks were and why the day
cost what it did - without asking HR.**

| Persona | In scope? | What changes |
|---|---|---|
| Employee, incl. frontline | Yes, primary | Each day row shows the break; the opened day shows the stored reason and when it was worked out |
| Line manager | Yes | Sees the same break and reason on a team member's month (already allowed to see their punches) |
| HR Manager | Yes | Same as manager, for anyone in their companies; stops reading the reason out of the Desk form |
| CXO | No | Nothing changes. No break on any team, company or leader view |

## 2 · Evidence

- **Fact (read in code):** the Attendance page draws one row per day (`acRow`), a phone block
  of two lines (`.ac-l1` date + tags, `.ac-l2` "In · Out · worked · arrival"), and an opened
  day under the row (`acDetail`) with fact tiles (`.ac-facts`), punch chips (`.ac-punch`),
  help lines (`.ac-help`) and the correction form.
- **Fact:** the engine writes the reason as one paragraph: `" ".join(verdict.reasons)` into
  `alvoraa_rules_why`, and the time into `alvoraa_evaluated_on` (`payroll_rules_apply.py`
  481-482). Sentences look like "Breaks: 55 minutes. The first 40 are allowed, so 15
  deducted." and "Slab 90-97%: 1 quarter(s) off, no red."
- **Fact:** with "count shift hours only" on, the engine counts only the part of each break
  inside the shift (`_worked_percent`, line 205). A screen sum of raw gaps would disagree
  on a day where someone stepped out before the shift start.
- **Fact:** the break allowance can be overridden per employee category (docstring, line 93).
  The screen needs the allowance **for that person**, not the rule set's.
- **Fact:** Attendance Insights' one-person list (`aiPerson`) shows only short days, as a
  5-column table, without a scroll wrapper.
- **Fact:** the phone breakpoint is `max-width:768px`, where `--fs-xs` rises to 12 px and
  `--fs-sm` to 13 px (`frame.css` 332).
- Screenshots: none taken this run. The folder would be
  `C:/Surbhi-Git/hrlocal-data/ux-review/2026-11-12/`.

Benchmark: skipped for this thin slice; the brief's two lines stand (Keka and Zoho show break
time per day `[recall - verify]`; nobody shows a plain reason per deduction).

## 3 · Findings

| ID | Page | Finding | Impact | Kind | Size | Severity |
|---|---|---|---|---|---|---|
| A1 | Attendance | No break figure anywhere; a person adds up 4-6 punches in their head | High | New | S | - |
| A2 | Attendance | The stored reason reaches no screen (brief, ALV-326 security review M3) | High | New | S | - |
| A3 | Attendance | Punch chips, fact tiles and the inline open day already work well on a phone | - | Keep | - | - |
| A4 | Attendance | "Missing punch" tag counts raw punches; the engine folds 2-minute repeats first, so the tag can say "missing" on a day the engine paid normally | Medium | Fix | S | P3 (out of this slice; Q1) |
| A5 | Attendance | The reason is HR-worded English ("slab", "rule set") | Medium | Improve | M | P3 (later ticket, Surbhi's decision 3) |
| I1 | Insights, one person | No break column | Medium | New | S | - |
| I2 | Insights, one person | Table wider than a 390 px phone, page scrolls sideways | Medium | Fix | S | P3; fixed here because the new column makes it worse |
| I3 | Insights, one person | Dates show as "2026-11-04" while the Attendance page says "4 Nov" | Low | Improve | S | P4, not in this slice |

## 4 · Screen 1 - Attendance page (`panel-att-record`)

### Day row - phone first

The second line (`.ac-l2`) gains one item at the end, after the arrival word:

```
4 Nov Wed   [Present]                                  ›
In 09:12 · Out 18:20 · 8.2h worked · On time · Break 55 min (15 over)
```

- **Fact:** `.ac-l2` wraps, so the extra item drops to a new line at 360 px rather than
  pushing the page wider.
- "(15 over)" is bold in `--red`, the same `.hi` class the page already uses for short
  hours. The words carry the meaning; the colour is extra.

### Day row - desktop

One new column, **Break**, between "Worked" and "Expected". Cell text is the same as the
phone item, without the word "Break" (the header says it). Empty is "—", like every other
cell. The opened day's `colspan` goes from 9 to 10.

### Opened day

Two additions, nothing removed:

1. **Fact tiles** (`.ac-facts`): a **Break** tile after "Worked", and an **Allowed** tile
   right after it, only on days where a break was measured.
2. **"Why this day"** block, after the punches and the missing-punch help, before the
   correction form. The stored text as written, then one quiet line: "Worked out on
   4 Nov 2026 at 23:40". The block is a `<section>` with an `<h3>` so a screen reader can
   jump to it.

Order inside the open day, top to bottom: facts → punches → missing-punch help → **Why
this day** → correction. **Recommendation:** the reason sits above the correction form on
purpose: a person reads why, then decides whether to ask for a fix.

## 5 · Screen 2 - Attendance Insights, one person (`aiPerson`)

- New **Break** column after "Worked", same cell words as the Attendance page desktop.
- The table is wrapped in the existing `.tbl-wrap`, so on a phone the table scrolls
  inside itself and the page does not.
- No reason here (brief). No break on the people list, the team list, the weekday strip or
  any tile. No sort by break.

## 6 · States and exact words

"Allowance" below = the break allowance for that person's category, else the rule set's.

| # | State | Row (phone `.ac-l2` item / desktop cell) | Opened day | Insights cell |
|---|---|---|---|---|
| S1 | Normal break (even count, 4+ punches, at or under allowance) | **Break 32 min** / `32 min` | Tiles: Break `32 min` · Allowed `40 min` | `32 min` |
| S2 | Over the allowance | **Break 55 min (15 over)** / `55 min (15 over)`, "(15 over)" in `.hi` | Tiles: Break `55 min (15 over)` · Allowed `40 min` | `55 min (15 over)` |
| S3 | Odd count after folding repeats ("a punch is missing") | **Break not measured** / `Not measured` | Help line: "**Break not measured.** A punch is missing from the middle of the day, so nobody can tell which gap was a break. No break is deducted." No Break or Allowed tile | `Not measured` |
| S4 | One or two punches (muster-roll day, held day) | nothing / `—` | No break tile. The reason shows if stored (e.g. "Held: only one punch…") | `—` |
| S5 | Leave, absent, holiday, weekly off, no record | nothing / `—` | No break tile. The reason shows if stored ("Approved leave. No quarters…") | row not listed (not short) |
| S6 | No reason stored yet | unchanged | No "Why this day" block at all. No "not worked out yet" message (brief) | - |
| S7 | Break allowance off (0) for this person | nothing / `—`, column hidden | No break tile | column hidden |
| S8 | Reason stored, day later corrected | unchanged | Reason shows with its "Worked out on" date, so a date before the correction is visible (brief R3) | - |
| S9 | Loading / failed | existing page states, unchanged | - | existing |
| S10 | 0-minute break (back within the same minute) | **Break 0 min** | Tiles as S1 | `0 min` |

**S7, Recommendation:** when no break rule applies, show no break at all, and hide the
desktop column. The figure exists here to explain pay. Without a break rule it explains
nothing, and to a manager it is only a record of how long someone was away. That is a
behaviour signal with no purpose (product-context §6). It is also the smaller build. If the
tenant has the rule on for some categories and off for others, the desktop column shows
when any visible day has a break figure; days without one show "—".

**Why "Break not measured" and not "Break: a punch is missing":** the row already carries
the "Missing punch" tag. Saying it twice in one row is noise; the opened day says why.

### Exact words, English and Hindi

Hindi is machine-drafted. It needs a native review before release.

| Key | English | Hindi (draft) |
|---|---|---|
| row item | Break {0} | ब्रेक {0} |
| over | ({0} over) | ({0} ज़्यादा) |
| not measured | Break not measured | ब्रेक नापा नहीं जा सका |
| column / tile | Break | ब्रेक |
| tile | Allowed | छूट |
| help, odd count | Break not measured. A punch is missing from the middle of the day, so nobody can tell which gap was a break. No break is deducted. | ब्रेक नापा नहीं जा सका। दिन के बीच की एक पंच नहीं है, इसलिए पता नहीं चल सकता कि कौन-सा अंतर ब्रेक था। कोई ब्रेक नहीं काटा गया। |
| heading | Why this day | यह दिन ऐसा क्यों गिना गया |
| when | Worked out on {date} at {time} | {date} को {time} बजे गिना गया |
| reason text | as stored, English only | not translated (Surbhi's decision 3) |

Minutes use the page's own `acMins` ("55 min", "1h 25m"). The "over" figure is a bare
number under an hour, as in Surbhi's example ("15 over"), and `acMins` from an hour up
("1h 5m over"). The whole item never breaks across lines (`white-space:nowrap`). Dates use `acNice` ("4 Nov 2026").
Times are 24-hour, as the punch chips already are.

## 7 · Accessibility and privacy

**Accessibility (WCAG 2.2 AA, nfr-budget §7):**
- "Over" is said in words; red is never the only signal (1.4.1).
- The reason block is a `<section aria-labelledby>` with an `<h3>`; the text is plain text
  with `white-space:pre-line`, never HTML (it is escaped with `gpEsc`).
- No new controls, so no new tap targets. The existing day button stays 52 px tall.
- Phone text: the new items use `.ac-l2` (13 px) and `.ac-help` (12 px), both at our floor.
- Contrast: `--red` on `--surface` and `--text3` on `--surface2` are the page's existing
  pairs; nothing new.

**Privacy - flag: both screens show another person's data.**
- Attendance page: a manager sees a report's break and reason; HR sees anyone in their
  companies. This uses `month()`'s existing `_subject` check, no new door.
- Insights one-person list: `person()`'s existing reports-to and organisation check.
- The reason text holds only that person's own times and rule figures (brief §6).
- **Not shown anywhere:** break on a team list, a company list, a tile, a sort, a filter or
  a leader view. Per person, per day only.
- **For the security engineer (data-doors rule):** the reason field is at permission level 0
  on Attendance. A staff login can probably read its own through `/api/resource/Attendance`
  already; confirm it, and confirm it cannot read a colleague's. This design adds no endpoint.

## 8 · Parity table

Each element in `prototype.html`, and where it lives in the code.

| Prototype element | Code home | New or existing |
|---|---|---|
| Page title "Attendance", sub "Your record · November 2026" | `policies.html` `#panel-att-record`, `acPaint` sets `#ac-sub` | existing |
| Six tiles (Days present … On leave) | `acPaint` `.ac-tiles` | existing, unchanged |
| Day row, phone block (`.ac-day`, `.ac-l1`, `.ac-l2`) | `acRow` | existing; **one new `.ac-l2` item** "Break …" |
| Day row, desktop **Break** column | `acRow` + header in `acPaint` | **new column** |
| "(15 over)" in red bold | `.ac-tbl .hi` / `.hi` | existing class, new use |
| Opened day facts (`.ac-facts`) | `acDetail` | existing; **new Break and Allowed tiles** |
| Punch chips (`.ac-punch`) | `acDetail` | existing, unchanged |
| "Break not measured…" help | `acDetail`, `.ac-help` | **new line** |
| "Missing punch" tag | `acRow`, `.ac-tag.warn` | existing, unchanged (see A4) |
| **Why this day** block and "Worked out on…" | `acDetail` | **new block**; a few lines of CSS in `panels.css` beside `.ac-help` |
| Correction form placeholder | `acForm` | existing, drawn as a stub |
| Insights one-person table | `aiPerson`, `.ai-tbl` | existing; **new Break column**, wrapped in `.tbl-wrap` |
| "← Back to the list" | `aiPerson`, `.oc-up` | existing |
| Values: `break_minutes`, `break_over`, `break_state`, `rules_why`, `evaluated_on` per day | `attendance_correction.month()`; `break_minutes`, `break_over`, `break_state` in `attendance_analytics.person()` | **new per-day keys** (names are the analyst's to settle) |
| Review bar (person, device, theme, language, state jump) | prototype only | not in product |

## 9 · Prototype

- File: `docs/slices/alv-328-break-and-reason/prototype.html`, one self-contained page, made-up
  names and times only, every figure tagged "Sample".
- Controls: viewer (employee "Rohan Mehta" / his manager "Kavita Rao"), device (phone 390 /
  desktop), theme (light/dark), language (English/Hindi for the new words), allowance on/off,
  and a screen switch (Attendance / Insights one person).
- Each state S1-S7 is a real day in the sample month; open any day to see it.
- **Not published:** this run had no Artifact tool. The calling session should publish it
  and give Surbhi the link.
- Kept inside the worktree's slice folder as asked; it holds no tenant data.
- Looked at once, at 390 px and 1440 px, light and dark. Measured: page width 390 at 390
  on both screens (nothing wider than the phone), no text under 12 px, no script errors.
  Fixed after that look: the "Day" header alignment, "(15 over)" splitting across lines,
  and the Sample tag at 11 px.

## 10 · For the analyst - turn these into acceptance criteria

1. The break per day equals the engine's for the same day: same punches, same 2-minute
   fold (`collapse_duplicate_punches`), same gaps (`break_gaps`), **same clip to the shift
   when "count shift hours only" is on**. Test every DTC November day (brief kill criterion).
2. "Over" uses the allowance for that person's employee category, falling back to the rule
   set's. `over = max(0, break - allowance)`; "(N over)" only when N > 0.
3. Odd count **after folding** → "Break not measured", never a number (S3).
4. One or two punches, leave, absent, holiday, weekly off, no record → no break (S4, S5).
5. Allowance 0 for the person → no break shown; desktop column hidden when no visible day
   has a figure (S7).
6. "Why this day" shows only when `alvoraa_rules_why` is set; the text is escaped and shown
   as written; "Worked out on" uses `alvoraa_evaluated_on` (S6, S8).
7. A manager sees a direct or indirect report's break and reason through `month()`; a staff
   login cannot reach a colleague's through `month()`, `person()` or `/api/resource/Attendance`.
8. Insights: the Break column exists only on the one-person list; no break on any group view.
   The table scrolls inside `.tbl-wrap` at 390 px; the page itself does not scroll sideways.
9. Night shift (brief R2): the engineer confirms DTC has none, or both screens use the
   engine's day grouping.
10. Phone, 360 px: no page width beyond the screen; new text at least 12 px.

### Usability test plan (A1, A2 are High impact)

Five DTC staff, own phone, own November. Tasks: (1) "How long were your breaks on
<a cut day>?" (2) "Why did that day cost you?" (3) "Was any day's break over the limit?"
Success: each answered in under a minute without help. Would change the design: if three of
five cannot read the reason text, the staff-wording ticket moves ahead of release.

## 11 · Not in this slice

- A month total of break time (Surbhi's decision 1).
- Rewriting the reason in staff words or Hindi (decision 3).
- Splitting the reason into one line per sentence (it would mean guessing sentence ends;
  "97.5%" breaks a naive split).
- Fixing the "Missing punch" tag to fold repeat scans (A4, Q1).
- A "worked out before your correction" warning (S8 shows the date; that is enough for now).
- Human dates on the Insights table (I3).

## 12 · Subtract pass

Removed while drafting: a "not worked out yet" line (brief already removed it); a separate
"Break" tooltip explaining the allowance (the Allowed tile does it); a strip colour for
over-breaks on `.ac-strip` (the words do it); the reason on Insights (brief); a month break
tile; a per-day "over" tag in the tag row (it would duplicate the line-2 item).
Kept the Allowed tile: without it "15 over" has no visible base on the opened day.

## Open questions

- **Q1 (not blocking):** should the "Missing punch" tag fold 2-minute repeats too, so it
  never disagrees with the break line? Owner: `hrms-product-manager`. Until then, a row can
  show "Missing punch" next to a normal break figure.
- **Q2 (not blocking, confirm):** S7 - hide break where no break rule applies. Owner: Surbhi.

## Design agreed (12 Nov 2026)

Surbhi agreed the design and prototype as drawn ("looks good"), including hiding the break where no break allowance is set.
