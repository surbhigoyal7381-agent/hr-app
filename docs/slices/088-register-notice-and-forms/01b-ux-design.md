---
slice: 088-register-notice-and-forms
artifact: 01b-ux-design
author: hrms-ux-designer
date: 2026-11-21
status: draft v1, for Surbhi's design gate
inputs: [01-product-brief.md incl. Surbhi's gate, 01a-ux-opportunities.md, 07-devops-inputs.md, 087 prototype-v5.html, 087 01b v5, ux-learnings.md]
---

# 088 Register notice: UX design (v1)

**Risk tier 1** (pay gate, personal data, a photo kept for years). **Prototype:** `prototype-v1.html` in this folder; copy at `/Users/mac/hrlocal-data/prototypes/088-register-notice-and-forms/prototype-v1.html`. **Not published: I have no publish tool in this run.** Every name, time and figure in it is **Sample**. Hindi is **machine-drafted** and needs a Hindi reader before any sheet is printed for real.

**Serves:** the **employee with no app** (they hold the paper) and **HR** (they print, record). **Changes for the others:** CXO, nothing. Line manager, nothing (printing stays HR-only; the brief says "later"). Employee with the app, one small line (section 5).

**What I read:** the brief and its gate, 01a, 07 section 1, `ux-learnings.md`, 087 `prototype-v5.html` (its dialog code and strings) and 087 `01b` v5. **What I did not do:** I did not open the running portal or any login, and I opened no code under `alvoraa_portal`. The "HR Attendance page" placement is taken from 087 v5, which drew the "Before payroll" card there; I have not re-checked that page in code. This is a design, not a statement about what the portal does today.

**Applied from `ux-learnings.md`:** "A control that records a person's act is never offered to the person who filed the change; show a sentence, not a greyed button" (087, 21 Nov); "Any attach-a-photo-of-a-page step is a privacy surface" (087, 21 Nov); "Colour is never the only signal"; "Hide what a person cannot use"; "Build the heavy dataset into the prototype" (the 14-change person); "Count surfaces before drawing a new one" (nothing new is a page: one card, one dialog, one preview). Nothing contradicts the request.

## 1. The design in one paragraph

HR opens the **Change notices** card on the page it already uses for "Before payroll", picks a month, and sees only the people who have a day that someone else changed and that still needs confirming. HR prints one person (or ticks several and prints them together). The browser prints **one A4 page per person**: only that person's changed days, only counted hours, who filed each change and why, and one box to sign or press a thumb. The worker signs. HR photographs the page, presses **Signed on the register** (the same dialog 087 v5 drew), and every change on that page becomes confirmed. Nothing is built that the brief did not ask for: no new page (a card on an existing page), no PDF engine, no reminders.

**Ladder rung:** new code, as the brief says. A print format could not do it: the notice is per person, filtered, and its printing must be logged. Nothing cheaper was found, and I have not searched `hrms/` for a print format.

## 2. Findings that shaped it

| ID | Finding | Impact | Kind | Size | Severity |
|---|---|---|---|---|---|
| N1 | A notice that says "tell HR if this is not right" gives HR no way to **record** a "not right" (087 only records a yes, or a dispute made in the app). The record becomes one-sided. See ⚠ D-2 | High | Question | S | P2 |
| N2 | Long notices: 14 changes cannot be read on one page. Five rows is the most that fits at large print (measured, section 6) | Medium | Decision | S | P3 |
| N3 | The filer's reason prints in full on paper that is handled on a shop floor. It can hold something sensitive or an accusation. See ⚠ D-3 | High | Risk | S | P1 until decided |
| N4 | After printing, a new change can be filed. The paper no longer matches the screen | Medium | New | S | P2 |
| N5 | 087 and the brief draw "Thu 13 Nov". In 2026, 13 Nov is a **Friday**. The prototype computes real weekdays. Check the 087 build does too | Low | Fix | S | P3 |
| K1 | **Keep:** 087 v5's dialog and its rule that the filer cannot record the signature | | Keep | | |

## 3. Flow

**HR (laptop or phone):** Attendance page > Change notices > month (default: this month) > list of people > **Print notice** on one row, or tick several and **Print selected** > A4 preview > **Print** (the browser's print window) > the worker signs on paper > HR presses **Signed on the register** > photo > **Record signature** > the row shows a green tick.

**Employee with no app:** gets the page, reads it (HR can read it aloud), signs or presses a thumb, hands it back. No screen.

**Employee with the app:** sees the same days in the month view (section 5) and uses 087's Confirm or "Not right". Nothing else.

### States (every one drawn in the prototype unless marked)

| State | What the person sees |
|---|---|
| Loading | Three grey rows, "Loading the list" read out to a screen reader. Skeleton within 300 ms (nfr-budget §2). |
| Empty (a month with no changes) | "No changed days in October 2026" and one sentence on who gets a notice. No button, nothing to do. |
| Error | "Could not load the list. Nothing was changed." and **Try again**. No server text. |
| No permission | The card is **not shown** to anyone who is not HR Manager or HR User. No greyed card. [ASSUMPTION: same roles as 087's HR card; the BA confirms.] |
| First time | Same as normal. The intro sentence is always on the card. |
| 400 people with changes | The list needs paging ("Showing 25 of 400" and **Show more**, the portal's existing footer pattern). **Not drawn**: the prototype has 7 rows. Select all means "all that are loaded"; see section 7 for the print cap. |
| Row, not printed | "Not printed yet" + **Print notice** |
| Row, printed | "Print opened on 19 Nov by Kavita Sample. Waiting for the signature." + **Signed on the register**, **Print again**. It says "print opened", not "printed", because the product cannot know the paper came out. |
| Row, changed after printing | Amber triangle plus words: "1 change added after the page was printed. It is not on that page. Print again." |
| Row, signed | Green tick plus words: "Signed on the register on 20 Nov. Recorded by Kavita Sample." No buttons. |
| Row, confirmed in the app | Green tick plus words, no buttons. |
| Row, HR filed one of the changes on the page | A sentence instead of the button: "You filed a change on this page, so another HR person records the signature." |
| Network drops while recording | Not drawn. **Recommendation for the build:** keep the chosen photo on the phone, say "Not saved yet. Try again", never clear the photo. (nfr-budget §3 and the ux-learnings pattern "keep the captured photo across a retry".) |

## 4. Screens and the exact words

English first; Hindi is in the prototype and in the table below for the paper. **Machine-drafted, needs a Hindi reader.**

### 4.1 HR card "Change notices" (laptop, works at 390 px)

- Heading: **Change notices**. Line under it: "One page for each person whose attendance someone else changed. Print it, let the person read it and sign or give a thumb print, then record it here."
- Month: previous and next arrows (44 px), the month in words, "November 2026". Next is off at the current month. Arrows have labels ("Earlier month", "Later month").
- Summary: "7 people have changed days in November 2026. 2 are done. 5 still need a signature or a confirmation."
- **Select all 5** (counts only people with something left to confirm). **Print selected (n)** appears only when something is ticked.
- Row: tick box (44 px, named "Select Ravi Sample"), name, employee number, branch, "3 changed days", status line, buttons. People who are done have no tick box.
- Foot line: "Every time a notice is opened for print, we keep your name, the date and the person."
- On a phone the row stacks: name, buttons, then the status.

### 4.2 The A4 notice

One person, one page, black on white, no colour needed (it must work on a black-and-white printer). English with the Hindi line under it. Type: 11 pt body, 12 pt for days and for the line the worker reads, 16 pt for the name, 19 pt title. Measured: five changed days fit with the sign box and footer (section 6).

| Part | English | Hindi (machine draft) |
|---|---|---|
| Top left / right | Company name / "Ref EMP-0207/2026-11/1-3" | संदर्भ ... |
| Title | Changes to your attendance · November 2026 | आपकी हाज़िरी में बदलाव · नवंबर 2026 |
| Name block | Name, "Employee no. EMP-0123 · Store A" | कर्मचारी क्र. ... |
| Intro | Someone else changed these days in your attendance. Please read each one. | आपकी हाज़िरी के इन दिनों को किसी और ने बदला है। कृपया हर एक पढ़ें। |
| Columns | Day · What changed · Who filed it · Why | दिन · क्या बदला · किसने किया · कारण |
| A change | "Fri 13 Nov" · "Out time 14:40 added" · "This day now counts 8 h 20 m." · "Anil Sample, HR · 14 Nov" · the reason as the filer wrote it | ... "बाहर जाने का समय 14:40 जोड़ा गया" ... |
| Rule, boxed | If something here is not right, tell HR before you sign. | अगर यहाँ कुछ ठीक नहीं है, तो दस्तख़त से पहले HR को बताएँ। |
| Pay line, dashed, **only if the tenant's 087 gate is on** | Your salary slip for this month waits until each change is confirmed. | जब तक हर बदलाव की पुष्टि नहीं होती, इस महीने की आपकी सैलरी स्लिप रुकी रहेगी। |
| Read line | I have read the changes on this page. | मैंने इस पन्ने के बदलाव पढ़ लिए हैं। |
| Boxes | Signature or thumb print (26 mm tall, wide) · Date | दस्तख़त या अंगूठे का निशान · तारीख़ |
| Foot | "Printed by Kavita Sample on 21 Nov 2026. Page 1 of 3." and "This page is only about you. Keep it private." | यह पन्ना केवल आपके बारे में है। इसे निजी रखें। |

Kinds the sentence can take (all four are templated, so Hindi is exact): "Out time {time} added", "In time {time} added", "Back after break at {time} added", "Scan at {time} not counted".

**What is deliberately not on the page:** any other person's name (except the filer, who is the actor, section 8), the reason for any absence, the scans the system did not count (they stay in the audit log; the page says nothing about them), pay amounts, and anything about attendance that was not changed by someone else.

**Several pages.** More than five changes go on a second sheet, then a third. Every sheet is complete by itself (name, boxes, footer, "Page 2 of 3") and is signed separately. **One** "Signed on the register" record covers all the sheets of that print and takes **one photo of each page**. For almost everyone this is one page and one photo.

### 4.3 Preview (A4)

A bar above the sheets: **Back to the list**, **Print 2 sheets** (or "Print 1 sheet"), and a line: "Preview at A4. One person on each page. Only hours that were counted are shown. Printing is logged: Kavita Sample, 21 Nov 2026." Below it the pages, scaled to fit the screen. The Hindi lines carry a review tag in the bar (screen only, not on paper): "Hindi lines: machine draft, not yet read by a Hindi speaker". The checkbox "Salary-slip line on the sheet" is a **prototype control** to show both versions; in the product the line follows the tenant's 087 setting.

**Printing is logged when HR presses Print**, before the browser's own window opens: who, when, which person, which month, which changes were on the page. The row then reads "Print opened". Real print and PDF-save are the browser's.

### 4.4 Dialog "Signed on the register" (087 v5's dialog, reused)

Same shape: a bottom sheet on a phone, a centred dialog on a laptop; Escape closes it. What changed from 087 v5, and why:

| 087 v5 | 088 | Why |
|---|---|---|
| "...signed next to this change on the printed register" | "Record this only if Joginder signed or gave a thumb print on this notice." (several pages: "...on every page of this notice (3 pages)") | The page is the unit now |
| One change named | "This records 2 changes as signed:" and the list, one line each | One signature covers the page |
| Photo hint: "Show only this person's line. Other people's names are on the page." | "Take the whole page, with the signature box. The page has only Joginder's own details, nobody else's." | One person per page removes the privacy problem 087 ⚠ D-3 raised |
| Photo name shown | A **preview of the photo** and "Look at the photo. Can you read the signature or thumb print? If not, take it again." | A blurry photo makes the slip stay blocked and costs an HR ticket (brief risk) |
| One photo | One per printed page; "Add 3 photos, one for each page. You added 1." if short | Each page carries its own signature |
| "Your name, today's date and the photo are kept with the request." | "...kept with these changes. Only HR can open the photo." | Same, plus who |
| After printing, a later change | "1 change added after printing is not covered. It stays open." | N4 |

Buttons: **Cancel**, **Record signature**. Empty photo: "Add the photo of the signed notice first." The camera opens first on a phone. Recording sets the same fields 087 v5 drew (signed by, on, photo) on each change listed. After it, the row shows the green tick and the change leaves 087's "Before payroll" list.

**Rule kept from 087:** the person who filed any change on the page cannot record the signature; another HR person does. Drawn as a sentence on the row.

## 5. Employee with the app: one small addition

On the month view of Time: a card line "3 days this month were changed by someone else." and **See them**. It opens the list inline: day and what, who filed it, the date, and one of three states ("Not confirmed by you yet." / "You confirmed it." / "You signed for it on the register."). Tapping a row opens the **existing 087 day sheet**, where Confirm and Not right already live. No new page, no button of its own, no print.

**Recommendation, and the one thing I would cut:** this card is the cheapest item in the slice to delete. 087's Home row and day sheet already carry Confirm. I kept it because the brief marked it "Yes", and because after Confirm it is the only place that lists the month's changes in one place. If Surbhi wants the smallest slice, delete section 5; nothing else depends on it.

Everything the employee sees about a register signature ("You signed for it on the register") is 087 v5's words, unchanged.

## 6. Checks run (what I measured, and what I did not)

Run by script in headless Chrome on `prototype-v1.html`, laptop and 390 px, English and Hindi, light and dark: **nothing wider than the screen, no button or tick box under 44 px, all A4 sheets fit** (14 changes make 3 sheets of 5, 5 and 4: all fit). Looked at four screens once: the list, the dialog on a phone, the Hindi list on a phone, the A4 sheet. **Not done:** a real print to paper (the print styles are in the file; I did not send them to a printer); Devanagari on a Windows HR computer (the font on the sheet falls back to Noto Sans Devanagari, then Nirmala UI, which Windows ships; unchecked); a screen reader; 200% zoom; a printed black-and-white test. Field text: the file chooser is set to 16 px. Screenshots are in `/Users/mac/hrlocal-data/ux-review/2026-11-21-088/` (Sample data only).

## 7. ⚠ DECISIONS and assumptions

- **⚠ D-1 (owner: Surbhi) Hindi must be read by a Hindi speaker before any sheet is printed for a customer.** The sheet is bilingual by design. Option A: ship bilingual after a native review (recommended). Option B: ship English-only until the review is done (the sheet still works). **Risk if it waits:** a wrong Hindi sentence on a paper a worker signs. Blocks release, not the build.
- **⚠ D-2 (owner: Surbhi, then the BA) the notice says "tell HR if this is not right", and HR has no way to record it.** 087 can record a "yes" on paper, but a "no" only through the app. Recommend adding one second button in the same dialog, "Says it is not right", with a required reason, creating 087's existing dispute. It reuses what 087 built. If you decline, HR handles a "no" by hand, outside the product, and the printed sentence stays. **Risk if it waits:** the record holds only the signatures, never the objections. That is the one-way rule (never improve HR's convenience by degrading the worker's voice).
- **⚠ D-3 (owner: `hrms-security-privacy-engineer`) the filer's reason prints in full.** It is the filer's free text, on paper on a shop floor. Recommend one hint line under the filer's reason box in 087's send bar: "The person will read this on paper." That changes a 087 screen, so it needs Surbhi's yes (parity rule). Not drawn in this prototype.
- **⚠ D-4 (owner: BA) manager-added changes are not on the notice.** The brief says only changes that need confirmation. A manager's addition needs none (087 v5), so a worker is not told on paper. Recommend keeping it out: a "no signature needed" row on a signing page confuses a worker who reads little.
- **Assumption: five changed days per sheet; at most 100 people per batch print.** Both are guesses. The brief's cheapest check applies: print a dummy notice for three Grace staff before building. A batch of 100 notices is a large page for the browser; **time one on the build bench** (07 OPS-8, nfr-budget §2: a core HR view is 1.5 s). If over the cap, the screen says: "You picked 140. Print up to 100 at a time, then the rest." **[ASSUMPTION]**
- **Assumption: counsel accepts one photo per printed page.** The brief's counsel Q3 is open; this design follows your instruction for one photo per page. **[ASSUMPTION]**
- **Open with counsel (brief Q4, Q5):** whether a thumb-print photo is biometric data, and how long it is kept. Until answered: photo HR-only, opening it logged, no export. This design draws **no viewer for the photo**: it is kept, not shown. An inspector asking to see it is a later decision.

## 8. Privacy and accessibility

**Privacy.** One person per page, so no other worker's name or data is on it. The filer's name and role (HR or manager) are on the page because the brief asks "who filed each"; that is the actor, not a colleague's record, but the BA should confirm with counsel. The company name is the tenant's. The printer's name is in the footer. The list shows people only to HR roles; branch scope follows whatever HR already has (not drawn; the BA states it). The list shows no reason and no photo. Printing is logged with who, when, which person. No personal data in any error text. **Not printed for people without a change** (that is also what keeps photos few: the storage worry in 07 §1).

**Accessibility (WCAG 2.2 AA, nfr-budget §7).** Every tick box has a name. Every status is a word plus an icon, never colour alone (amber triangle with "added after the page was printed"). Targets 44 px or more. Dialog: focus stays in it, Escape closes, labelled. The paper is black on white at 11 pt or more. Hindi is a second language on the paper itself, so a worker who reads Hindi needs nothing else. Not tested with a screen reader (section 6).

**Plain-language test.** The only technical words on screen are "register" and "notice", which are the words counsel and the worker already use.

## 9. Heuristics, red team, frontline bar

- **The one-way rule:** the notice can only add to a worker's knowledge. It does not make HR faster by hiding anything from them. The gap is N1 / D-2.
- **Frontline bar (two minutes):** for the worker: read (HR reads it aloud), sign, hand back: under two minutes for five changes [ASSUMPTION, to measure in the HR runs at Grace]. For HR: print, collect, photo, Record: five taps and one photo per page.
- **A worker who cannot read:** the sheet is large print, bilingual; the pay line is factual and says nothing like "you must". The pressure to sign is real: the rule line "tell HR before you sign" is boxed above the signature.
- **Employee leaves mid-month:** still on the list; the last month still prints.
- **Photo missing or blurry:** the preview in the dialog catches it before saving.
- **100x data:** the list pages; batch print is capped (assumed).
- **Network drops:** see states table.
- **Gate off:** the pay line is not printed; the notice is information only (brief risk).

## 10. Usability test plan (High impact: pay and a signature)

Five HR users at Grace and five floor workers, one run each. Tasks: HR prints three notices and records one signature from a real photo; a worker reads a printed notice (EN+HI) and says what changed and what happens to the slip. **Success:** HR finishes a notice in under five minutes (the brief's kill line); a worker names the changed day and who changed it without help; nobody signs without understanding the sentence "tell HR before you sign". **What changes the design:** two workers misread a row, or HR needs more than five minutes (the brief's kill criterion).

## 11. For the business analyst: acceptance criteria to write

1. **Who is on the list:** people with at least one change filed by someone else that still needs confirmation (087's rule: HR-filed or any set-aside), for the chosen month, in the HR user's scope; those done this month show as done.
2. **Sheet contents:** only that person's own changes, valid hours only, filer name and role, the reason as written, a sign box and a date box; no other person's data; footer with printer, date, page n of m, a reference; the pay line only if the 087 gate is on.
3. **Layout:** one person per page, A4, five changes per page then a further page; every page self-contained; prints legibly in black and white; Hindi and English together.
4. **Print is logged** (who, when, person, month, change list) before the browser's print window opens; a print by a user who is not HR is refused and logged.
5. **List states** as in section 3, including "changed after printing" and the filer rule (the filer cannot record; the sentence is shown).
6. **Record signature:** photo required, one per printed page; type and size checks and the private-file rule from `employee_photo.py` (07 OPS-4); records signer, date, photo against every change the page covered; later changes stay open; refuses if the signer filed any covered change; the photo is HR-only, opening it is logged, no export.
7. **Employee with the app:** the month card and the three states; reuses 087's day sheet.
8. **Decisions:** D-1 to D-4 and the two open counsel questions carried into the spec as stated.
9. **Test what it sends:** a test that presses Record with a photo and asserts what is stored (ux-learnings, 28 Oct), and one that presses Print and asserts the log row.

## Not in this slice (for you to decide)

A "can confirm in the app" tag on each row so HR can skip people who have the app; a viewer for the photo; a reminder when a notice stays unsigned; HR filtering the list by branch; a line manager printing their own store (the brief says later); a count for the CXO; a signature pad on a tablet in place of paper; the statutory forms (088b).

## Subtract pass

Removed from my first draft: a separate page for the list (it is a card on an existing page), a per-person "history of notices" screen, a sign box per changed day (one per page is enough and is what the dialog records), an "unsigned count" chip on the page header, a language chooser on the paper (it is always both), and a printable list of everyone for the whole store. **Kept only** the card, the A4 page, the preview, the reused dialog and one line for the app user (cuttable, section 5).

## Prototype and parity

`prototype-v1.html` (this folder). Use the grey bar at the top: **Show** jumps to each of the five screens; **HR login** switches between Kavita and Anil (Anil filed Ravi's changes, so he sees the sentence instead of the button for Ravi's page); **List state** shows loading and error; Device, Language and Theme as in 087. Month arrows show the empty state (October). **Print** opens the browser's real print window for the sheets.

| # | 087 v5 / the brief | 088 v1 | Needs |
|---|---|---|---|
| P-1 | "Signed on the register" records one change | Records every change on the printed page | one photo file linked to many changes |
| P-2 | Dialog wording | Reworded as in 4.4 | same component, new copy |
| P-3 | Photo with other people's names (087 ⚠ D-3) | Page has one person only | none |
| P-4 | Brief: "a sign or thumb box" | One box per page, not per day | Surbhi's yes if she meant per day |
| P-5 | Brief: Thu 13 Nov | Real weekday (Fri) | none |

## Open questions

- Does Surbhi want a sign box per changed day or one per page? **[Rec: one per page]**
- Is the list's default month this month or last? **[ASSUMPTION: this month; HR moves with the arrows.]**

## Assumptions

Marked inline: five rows per sheet, 100 per batch, counsel accepts one photo per page, HR roles for the card, workers sign in under two minutes. Hindi is a machine draft.

## Handoff note

For `hrms-business-analyst`: section 11 and the ⚠ list. For `hrms-security-privacy-engineer`: D-3, the photo (who opens it, logging, retention, brief Q4/Q5), and the printed reason. For the session that ran me: **publish `prototype-v1.html` and put the link here**; the design gate is Surbhi's.

## Design gate — Surbhi's decision, 21 Nov 2026

**Go with prototype-v1** (https://claude.ai/artifact/HkursyZu1uRPkmGMZz86Q2), with every recommendation:
- **D-4:** manager-added changes ARE on the notice. Counsel allowed a manager's addition without Confirm because it is shown on the monthly register.
- **D-2:** the record dialog gets a second action that records the employee's dispute, reusing 087's dispute.
- **D-3:** the filer's reason prints in full. 087's send bar gets a hint that the reason is printed on the employee's notice.
- **D-1:** a Hindi reader checks the wording before any sheet is printed for a customer.
- **Assumptions accepted:** up to 5 changes per page, and a batch of up to 100. Both are checked on a real printer.
