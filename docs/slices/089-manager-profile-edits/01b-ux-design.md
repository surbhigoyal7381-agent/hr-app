---
slice: 089-manager-profile-edits
artifact: 01b-ux-design
author: hrms-ux-designer
date: 2026-11-22
status: draft
inputs: [01a-ux-opportunities.md, 01-product-brief.md (with Surbhi's decisions, 22 Nov 2026), 07-devops-inputs.md §1, .claude/context/ux-learnings.md]
---

# 089 · Manager reports a leaver; managers see and change a little more

**Prototype v3 (current, after Surbhi's rounds 1 and 2):** `docs/slices/089-manager-profile-edits/prototype-v3.html`; v1 and v2 are kept beside it. Add `#example,reported,profile` to the address to open straight on the dialog. Copies in `/Users/mac/hrlocal-data/prototypes/089-manager-profile-edits/`. **I have no Artifact tool, so I could not publish it.** The coordinator session publishes it. Open the file in any browser. It holds only invented data, each tagged "Sample".

**Risk tier (my view): 1.** Who can change what, personal data, and a date that stops pay.

## 0. What I looked at, and what I did not

- **Proven:** I read `team.html`, `team_api.ACTION_MATRIX`, `org-settings.html` (the 078 card), `people_fields.py` (`POSITIONS_PROFILE_FIELDS`, `MY_PROFILE_WRITE_FIELDS`, `NEVER`) in this worktree at 16c68b2f.
- **Not checked: I did not open the running portal or Desk.** No login, no tenant, no screenshots. The Team screen, the "Details" button and the Desk screens are drawn from code and from how Frappe Desk usually looks. The prototype page itself I rendered once in Chrome (desktop). I did not measure it on a phone and did not test 200% text.
- **Not checked:** what the existing "open record" action (`ACT_OPEN_RECORD`) opens today in Team. I drew a "Details" button for it. The BA must confirm.

## 1. Frame

A store manager, on a shared or low-end phone, reports that a person has left, in under a minute. Someone with the confirmer role confirms it in Desk. **Serves: line manager (frontline supervisor).** What changes for the others:

- **Employee:** sees one line at the top of My profile when they are reported, with the manager's name. Nothing changes for them until it is confirmed. They see "Changed by your manager" if a manager edits their emergency contact.
- **HR Manager (or whoever the setting names):** gets a ToDo and confirms in Desk, as normal.
- **Administrator:** one new card, three rows.
- **CXO:** no change.

**One-way rule check:** nothing makes the manager's job easier by hiding something from the employee. Every manager action on a person is shown to that person.

## 2. Words rule (Surbhi, 22 Nov 2026)

**No screen names the confirmer.** The confirmer is whatever role the setting names. So: "Report that Ravi left", "Sent for confirmation", "Reported, not yet confirmed". Never "payroll". The only place a role name appears is the Administrator's setting, where it is the value being chosen. One word for the person: "manager". One term for the date: "last working day" (never "relieving date" on a portal screen; Desk keeps its own label).

## 3. The three biggest decisions

1. **The manager only reports. A person with the confirmer role sets Left, in Desk.** Nothing on the manager's screen says "done". The row says "Reported, not yet confirmed" until someone confirms.
2. **The ToDo carries the facts; no new record.** The "reported, not yet confirmed" state is the open ToDo. The reported date is **not** written to the Employee's relieving date, so it cannot leak into the Positions "leaving" flag (slice 059) before anyone has confirmed.
3. **One card, one dialog pattern, both lists empty.** Managers see no personal details and change nothing until an Administrator ticks something. The "change" list offers **one item only, Emergency contact**. Personal phone and home address are never offered to change.

## 4. Flows

### 4.1 Manager reports (phone, 360 px)

1. Team View. Each direct report's card shows the **name as the tap target** (opens the person's dialog, see 4.6) and a **small exit icon beside it** (22 px icon, no border, no fill, grey; a 44 × 44 px tap target; accessible label and hover tip "Report that Ravi left", with the name so four cards never share one label). There is **no Details link** (round 2). Presence is plain words under the name ("Sales Associate · Present today"). When a report is open, one grey line "⏳ Reported, not yet confirmed" shows under the name and the icon is gone.
2. Tap: a bottom sheet, `role=dialog`, focus on the date. Title "Ravi Kumar left?". Field **Last working day** (date, today by default, 16 px). A preview line: "You are reporting: Ravi Kumar · last working day 22 Nov 2026." Then: "This is sent for confirmation. Until it is confirmed, nothing changes for Ravi: Ravi stays on your team and is shown as working." Button **Report that Ravi left**. Link **Not now**.
3. Sent: "✓ **Sent for confirmation.** You reported this on 22 Nov 2026. Ravi shows as working until it is confirmed. Wrong person or date? Ask HR." Button **Done**.
4. The row now shows one grey line: "⏳ Reported, not yet confirmed" (words and a clock mark, no colour block). The icon is gone from that row (no second report). The last working day and the reported date are in the dialog (4.6).
5. Confirmed: Ravi drops off the Team list, and the manager sees a plain line "✓ Confirmed: Ravi Kumar left on 30 Nov 2026" (see ⚠ DECISION 3).
6. Closed without confirming: the row returns to normal and a line says "The report about Ravi was closed without being confirmed, on 24 Nov 2026. Ravi stays on your team. Ask HR why."

**No undo, no withdraw** (brief: Later). Wrong person or date: "Ask HR".

### 4.2 Failures (each is a real sentence, drawn in the prototype via "When sending")

| Case | Words | Button |
|---|---|---|
| No signal | "Not sent. We kept your date. Try again when you have signal." | Try again |
| Not their direct report (server) | "Ravi Kumar does not report to you, so you cannot report this. Ask HR." | none (nothing would work) |
| Already reported | "You already reported Ravi Kumar on 20 Nov 2026. It has not been confirmed yet." | none |
| Date too old | "The last working day cannot be more than 31 days ago. Check the date." | stays on sheet |
| Date too far | "The last working day cannot be more than 60 days ahead. Check the date." | stays on sheet |

The server's own sentence wins when it names a fact (ux-learnings, slice 008 pattern). The 31 and 60 days are my proposal: ⚠ DECISION 4. Never "Something went wrong".

### 4.3 The confirmer in Desk

- Desk shows a standard **ToDo**: "Confirm that **Ravi Kumar** left. Last working day 30 Nov 2026. Reported by Meena Sharma on 22 Nov 2026." Assigned to every enabled user holding the role. A link goes to the Employee.
- On the Employee, a timeline line: "Meena Sharma reported that Ravi left, last working day 30 Nov 2026 · 22 Nov 2026".
- To confirm, they set Status to Left and fill Relieving Date, then Save: the normal Employee save, with all today's leaver steps. **The ToDo closes by itself on that save** (build item). They may enter a different date than the manager's. The manager sees the confirmed date.
- To refuse, they close the ToDo. No reason box (Not in this slice). The manager sees the "closed without being confirmed" line.
- **Desk is Frappe's own screen. I draw it only to show the flow; we change nothing in Desk except the one ToDo and its auto-close.** The prototype's "Save" with Status left on Active shows nothing changes and the ToDo stays open.
- If the setting's role is held by nobody, the Administrator cannot save it (4.5). A ToDo with no one to see it must not be possible.

### 4.4 Employee (phone)

Top of My profile, only while a report is open, as a quiet note (thin grey left edge, no amber box): "Your manager Meena Sharma reported that your last working day is 30 Nov 2026. It has not been confirmed yet. Nothing about your pay or sign-in has changed. Not right? Speak to HR." **Words only, no button:** I found no screen an employee could open to dispute this, and a button that goes nowhere is worse. (Recommendation: the BA checks whether an existing HR contact or grievance route can be linked.) The line goes when it is confirmed or closed. After confirmation, what the person can still open follows the existing Left rules (not drawn).

An employee with no login (agency staff) sees nothing and is not harmed: the manager acts and the confirmer decides.

If a manager changed the emergency contact: under that row, "Changed by your manager Meena Sharma on 22 Nov 2026. Not right? You can correct it here, or speak to HR." (the employee can already correct it, slice 078).

### 4.5 Administrator (desktop, System Manager only, absent for everyone else, never greyed)

One new card: **What managers can see and change about their team**. Same tag-list, button and dialog pattern as slice 078 (ux-learnings: "chosen-list setting"). Three rows:

| Row | Shows | Button |
|---|---|---|
| Managers can see | Tags. Empty: "None. Managers see no personal details of their team." | Change what managers see |
| Managers can change | Tags. Empty: "None. Managers change nothing." | Change what managers change |
| Leaver notices are confirmed by | A role list, default **HR Manager**; "2 enabled people hold HR Manager" | (the list saves on pick) |

- **"See" dialog:** four ticks: Personal phone, Personal email, Home address, Emergency contact. Each hint: "Staff can already correct this on My profile." The sentence: "Pay, bank, ID numbers and date of birth are never offered." Summary line live, and the Save button names the effect: "Save — managers see 2 details about 45 people". (The 45 is a Sample count; the build uses the real count.)
- **"Change" dialog:** one tick, Emergency contact. The sentence: "A manager can change only what they can also see. Personal phone and home address can never be changed by a manager." Ticking it when it is not in the "see" list adds it, and the summary says "Managers will also be able to see it." Removing it from "see" also removes it from "change", and says so.
- **Role row:** a role no enabled user holds is refused: "Nobody holds Accounts team, so nobody would be told. Pick a role that someone holds. Nothing was saved."
- A line under the card: "Changed by <name> on <date>" (the 078 `ocs-changed` pattern).
- This card is **new**. The 078 card (work details) stays as is. The "see" list here is only the personal details, because those six are on `NEVER` for the 078 Positions list. A separate allow-list is needed: ⚠ DECISION 2.

### 4.6 The person's dialog (the "see" and "change" half, and the reported line)

**What opens today (proven, read in `portal.js`, `drawers.html`, `panels.css` at this worktree):** the 078 mini profile, `mpfOpen` → `mpfPaint`, in the shared `#emp-drawer`: a side drawer 480 px wide (full width at 360 px), `role=dialog`, `aria-modal`. Header: round avatar with initials, name, "Job role · Branch", a Close button. Body: an optional "leaves on {date}" note, a list of the ticked work rows (Job role, Department, Branch, Reports to, In the company since and so on), the promise line, and a Documents section that is absent unless the organisation ticked document types. Today it is opened from Positions (`data-pos-who`) only.

**Round 2: the new information goes inside this dialog, and there is no new link.** Tapping a name in Team opens it. Inside it:

1. **Reported line**, at the top, only while a report is open. It reuses the existing amber-edged note style (`.mpf-left`, the same note the dialog already uses for a leaving date): "Reported, not yet confirmed. You reported on 22 Nov 2026 that Ravi's last working day is 30 Nov 2026. Ravi stays on your team until it is confirmed." It is not written to `relieving_date`, so the dialog's own "leaves on" sentence is not triggered by it.
2. **Personal rows**, added to the same list as extra rows (Personal phone, Home address, Emergency contact and so on), only for what the Administrator ticked. None ticked: no rows, nothing drawn.
3. **Change emergency contact**, one outlined 44 px button under the list, only when "change" is ticked and no report is open. It opens the three fields **in place**, in the dialog (Name, Relation, Phone, all labelled, 16 px), with "Save emergency contact for Ravi" and Cancel. It is not a second dialog. After saving, the dialog stays open and a toast says "Saved. Ravi will see that you changed it."
4. **The promise line must change.** Today it says personal contact details "are never shown here" (`mpfPromise`, read). That becomes false the moment a manager can see them. When any personal row is ticked it reads: "These are the details your organisation chose to show. Personal contact details are shown here only because your organisation chose them. Pay, bank details, identity numbers and date of birth are never shown here." When none is ticked, today's sentence stays. This is a copy change in existing code and needs a test.

**⚠ DECISION 6, a conflict with what Team does today (proven in `portal.js`, `renderTeamPanel`: the Team card's `onclick` is `openEmpScorecard`):** tapping a Team card opens the **Scorecard page**, not this dialog. Surbhi's round-2 words ("the current dialog ... when clicking on employee name") ask for the dialog. I drew that. If the name now opens the dialog, **the managers lose their quickest way to the Scorecard**. Options: (A) the name opens the dialog and the Scorecard is reached from inside it by one existing-style button (it is a link, which round 2 asked me not to add, so this is hers to allow); (B) the name keeps opening the Scorecard and the new rows go into the Scorecard's header (not "the dialog"); (C) the name opens the dialog and the Scorecard is dropped from Team (a loss for managers, I advise against it). **Recommendation: A.** Owner: Surbhi. Not drawn in v3.

**Risk, P1 for the build: the dialog is not open to a plain manager today.** `get_positions_profile` calls `_guard`, which needs `may_view()` (Frappe Read on Alvoraa Position) and `employee_in_scope` (read in `positions_profile.py` and `register.py`). A store manager may not hold Read on Alvoraa Position (the permission table was **not checked**; it is site data). So "name opens the dialog" needs a server change: let a direct manager read their own report's profile. That is a permission change and goes to `hrms-security-privacy-engineer`.

## 5. Findings table (current state, from code)

| ID | Impact | Kind | Size | Severity | Finding |
|---|---|---|---|---|---|
| T1 | High | New | M | P1 if missed | A manager has no way to report a leaver. `ACTION_MATRIX` has no such action (read). |
| T2 | High | Keep | – | – | `ACTION_MATRIX`/`allowed()` is the one place that decides who gets an action. The new action goes in it for direct reports only. |
| T3 | Medium | Fix | S | P2 | The leaving date reaches a manager only as a sentence from `relieving_date` (read in `positions_profile`). A reported date must not be written there. |
| T4 | Medium | Keep | – | – | 078 card pattern and mini-profile component exist; reused. |
| T5 | Medium | New | S | P3 | Words: the product uses "manager" and "supervisor" in places (ux-learnings MA2). Use "manager". |
| T7 | High | Fix | S | P2 | `mpfPromise` says personal contact details are "never shown here". It must change when managers can see them (4.6). |
| T8 | High | Fix | M | P1 | A Team tap opens the Scorecard, and the profile dialog is gated by Read on Alvoraa Position. See 4.6. |
| T6 | High | Fix | S | P2 | A ToDo for a role nobody holds fails silently. The role setting refuses an empty role. |

## 5a. Round 1 feedback (Surbhi, 22 Nov 2026) and what v2 changes

"Design is not optimal ... it shouldn't be so highlighting. It can be an icon beside the name, not this loud." Changed in v2: (1) the report action is a quiet icon beside the name; (2) "Reported, not yet confirmed" is a grey line, not an amber pill; (3) sheet preview, "Sent" message, Team result lines, the employee's note, the emergency-contact "Changed by" line and the admin summary line lost their coloured boxes; (4) presence is plain words. **Kept loud on purpose:** error boxes (red, a refusal must be seen) and the one primary button in each sheet.

**Risk, P3: an icon alone is easy to miss, and our frontline rule says words beside icons.** Surbhi's call wins for a rare action. Mitigations: the sheet title says the words, the label and hover tip carry them, and the usability test below has a task "find how to report that someone left". If two of five cannot find it, add the words back as a small text link, not a button.

## 6. Prototype parity table (what is drawn, and whether it is built exactly)

Every row below is built exactly as drawn, unless it says otherwise. The viewer bar (view, device, theme, language, "When sending", "Settings: example", "Start again") is **not** part of the product.

| Drawn | Built as drawn? |
|---|---|
| A small icon (44 px target, label "Report that Ravi left") beside the name; the name opens the dialog; one grey status line when reported | Yes. No Details link |
| The person's dialog: header, work rows, personal rows, the reported line, in-place emergency contact form, the changed promise line | Yes, subject to ⚠ DECISION 6 and the permission risk above. Documents and the photo are the existing parts and are not drawn |
| Report sheet, preview line, failure sentences | Yes |
| Hindi strings for the manager and employee words | Machine draft. **Needs native review before store use** |
| Desk ToDo, timeline line, auto-close | Yes (the Desk look is Frappe's own, not ours) |
| Employee line and "Changed by your manager" line | Yes |
| Administrator card, two dialogs, role list, refusal of an empty role | Yes |
| The 45-people count, "Raj Kumar", "Surbhi Goyal on 22 Nov" | **Sample**; real values in the build |
| 31 days back, 60 days ahead | Only if ⚠ DECISION 4 is yes |

## 7. Accessibility and privacy

- WCAG 2.2 AA. Every input has a visible label. The sheets are `role=dialog`, `aria-modal`, move focus in, trap Tab, close on Escape and return focus to the button that opened them. Status is words plus colour. Touch targets are 44 px and field text 16 px in the prototype (set in CSS; **not measured** in a browser). Contrast follows the design-system tokens, light and dark (not measured).
- Long names wrap (`overflow-wrap:anywhere`). Hindi runs longer and the buttons wrap rather than clip. **200% text: not tested.**
- Privacy: who sees a reported date? The reporting manager, the confirmer, the person reported. Nobody else. A colleague, or a manager of another team, sees nothing. No reason for leaving is collected. A report is never shown as a leaving flag on Positions.
- ⚠ COMPLIANCE: a manager seeing a report's personal phone, email and address is a new exposure. See ⚠ DECISION 2.

## 8. Heuristics, walkthrough, red team

- **Visibility of status:** the chip and line on the row; the employee's line. **Match with real world:** "last working day", "Report that Ravi left". **Error prevention:** nothing sets Left on a tap; the preview names the person and date. **Recovery:** the failure table above. **Minimalist:** no reason box, no history page.
- **Frontline bar:** open Team, tap Report, check the date, tap Report: 3 taps and zero typing if the date is today. Under a minute: yes on paper, **not tested with a person**.
- **Before / after:** before, a call or a message. After, 3 taps.
- **Red team:** a wrong person (the confirmer closes it; the employee saw it) · a manager reporting in anger (a request only, and the employee is told) · a brand-new manager (no tutorial needed, the sheet explains) · 400 reports (the list is the existing Team list, one query set, DevOps OPS-5) · network drops (draft date kept, Try again) · a report who has reports of their own (not drawn; decided by the dry run, Q5) · a manager who is also HR (two lists, never merged; the ToDo must not make them the only confirmer of their own report) · a person set Left by HR while a report is open (the ToDo should close itself; the spec must say so).

## 9. Usability test plan (High impact: the report sheet)

Five store managers on their own phones, 360 px class. Tasks: find how to report that someone left (no hint); report one person as left with a date three days ahead; find out whether it has been confirmed; recover from a wrong date. Success: four of five finish in under a minute with no help, and all five can say "nothing has changed for him yet". A result that changes the design: two or more think the person has already left, or look for a "withdraw" button.

## 10. Not in this slice (for Surbhi to decide, not drawn)

Withdraw or undo · a reason box when closing · a bell line to the manager on confirm or close (see DECISION 3) · "Report" for HR-covered people · a history page · notice period or exit steps · reporting a transfer or shift change · Hindi for Desk.

**Subtract pass.** I removed: the Details link and the separate sheets for profile and edit (v3), the full-width report button on every row (v2), the amber and green colour blocks (v2), a second confirm dialog on Send (the preview is the check), a reason for leaving, a withdraw button, any listing of "my past reports", a "personal email" change tick (see below), and personal phone and address from the change list. I kept both lists in one card and the role in the same card, so there is no new settings screen.

## 11. For the business analyst: turn these into acceptance criteria

0. Team: the name opens the 078 dialog (4.6) for a direct report; no Details link; no new screen. The reported line, personal rows and the Change button are rows in that dialog. The promise line changes as in 4.6. A direct manager may read a direct report's profile on the server; nobody else gains access.

1. "Report that {name} left" appears only on a direct report's row, never on HR-covered rows, never for oneself, never for a person already reported or already Left. The server refuses the same cases with the sentences in 4.2.
2. Sending writes **no** change to Status or Relieving Date. It creates one ToDo per enabled user holding the setting's role, and one timeline line on the Employee. No new DocType.
3. "Reported, not yet confirmed" = an open ToDo of this kind. It reads for the reporting manager, the confirmer and the employee only. It never feeds the Positions leaving flag.
4. Saving the Employee as Left with a Relieving Date closes the ToDo. Closing the ToDo unconfirmed shows the manager the "closed" line. HR setting Left first closes the ToDo.
5. The role setting defaults to HR Manager and refuses a role no enabled user holds. A manager who is the reporter is not the only possible confirmer of their own report's exit.
6. Both lists default empty. The "see" candidates: personal phone, personal email, home address, emergency contact. The "change" candidates: emergency contact only. Phone and address are never in the change list. Change implies see. Pay, bank, ID, date of birth stay on `NEVER`.
7. A manager's save of the emergency contact passes ALV-266 only through `MANAGER_EDITABLE`, only for a direct report, writes a Version row, and shows "Changed by your manager" to the employee.
8. The two settings Save buttons name the effect and the real count.
9. Every string above exists in English; the Hindi strings are marked for native review before store use.
10. 360 px, 44 px targets, 16 px field text, no sideways scroll, Escape and focus return on every sheet.

## ⚠ Decisions for Surbhi

0. **⚠ DECISION 6 (new, round 2): where does the Scorecard go once the Team name opens the dialog?** See 4.6. Recommendation A. Also needs a permission change for a plain manager (security).

1. **⚠ DECISION 1: fallback.** If this runs long, ship the leaver report with "see" only. Owner: Surbhi. Recommendation: keep it. The "change" half is one item (emergency contact), which I would also be happy to drop.
2. **⚠ DECISION 2 / ⚠ COMPLIANCE: personal phone, email and address visible to managers.** A new list is needed because the six are on `NEVER`. Owner: `hrms-security-privacy-engineer`, then Surbhi. Does the staff notice need a line? The "Staff can see that you can" caption is my answer; counsel has not ruled. Recommendation: the "see" list may offer only phone, address and emergency contact, with personal email left out.
3. **⚠ DECISION 3: tell the manager the result?** Without it, a confirmed leaver quietly drops off the list and a closed report quietly returns. I drew a line on the Team page that stays until the manager next opens it, and I do not know how long it should live. Option A: one bell line on confirm or close (a Notification Log row; whether the bell shows this kind is **not checked**). Option B: nothing (the row simply changes). Recommendation: A. Owner: Surbhi, engineer.
4. **⚠ DECISION 4: date limits.** Not more than 31 days ago, not before joining, not more than 60 days ahead. My proposal, not a rule I found. Owner: Surbhi.
5. **⚠ DECISION 5: "Not right? Speak to HR" has no button.** I found no screen for an employee to dispute it. Owner: Surbhi, BA.

## Open questions

| # | Question | Owner | Blocks |
|---|---|---|---|
| 1 | What does "open record" in Team open today? Is "Details" the right door to the mini profile? | BA / engineer | Section 4.6 |
| 2 | Retention of the ToDo and timeline line (brief Q4, open for counsel) | Surbhi, counsel | Release |
| 3 | Does the bell show this kind of notification? | engineer | DECISION 3 |
| 4 | A leaver's own reports: what happens to Reports To? (brief Q5, dry run) | engineer | Build |

## Assumptions

- `[ASSUMPTION]` Team View's row card is the place for the button; I have not seen the running grid.
- `[ASSUMPTION]` A role name in the setting is enough for a System Manager to pick (roles are listed by name).
- `[ASSUMPTION]` Agency staff with no login are reported by their manager the same way.

## Handoff note

For the BA and the security engineer: the one rule that matters most is that **sending a report writes nothing to the Employee's status or relieving date**; read section 11, items 2 and 3 twice. The words rule in section 2 binds the build: no screen may name "payroll" or any fixed confirmer. I did not open the running portal or Desk, so the Team row layout and the Desk look are drawn from code and are unconfirmed. The prototype v3 was rendered in Chrome at the 360 px phone frame (Team row and the dialog) and measured in three states (default, personal rows with a report open, personal rows). Result: nothing under 44 px, no sideways scroll (358 of 358 px), no field under 16 px. The sheet, employee, Desk and admin views of v3 were not re-measured with a browser, only rendered once on desktop. If the design runs long, section 4.6 (the "see and change" half) is the part to drop.

## Design gate: Surbhi's decisions, 22 Nov 2026

**Prototype v3 approved** (published at https://claude.ai/artifact/DLGyV4ejTmxdw3gFnErQbZ, version 4 of that page). It took three rounds:
- Round 1: the leaver action was too loud. It became a quiet icon beside the name.
- Round 2: no separate Details link. The details appear in the existing dialog that opens when the name is tapped.

**Her decisions:**
- **Opening the dialog (choice 1a):** the dialog lets a manager open THEIR OWN reports' profiles without Read on Alvoraa Position. Managers do NOT get Position read. At DTC only 2 of 9 managers with logins hold it today (read on production, 22 Nov 2026).
- **Scorecard:** a "Scorecard" button inside the dialog opens the person's Scorecard page, which a card tap opens today. Added to prototype v3 by the coordinator, so the prototype matches the build.
- **D1 fallback:** kept. If this runs long, ship "see" only.
- **D2 managers seeing a report's phone and address:** allowed if the Administrator ticks them, subject to the security engineer's review. Personal email is never offered.
- **D3:** tell the manager the outcome (confirmed, or closed without confirming) with one bell line.
- **D4 last working day:** not before the joining date, no more than 31 days back and no more than 60 days ahead.
- **D5:** "Not right? Speak to HR" stays plain text, with no button.
