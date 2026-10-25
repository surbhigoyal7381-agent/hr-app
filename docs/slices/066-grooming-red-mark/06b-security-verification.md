---
slice: 066-grooming-red-mark
artifact: 06b-security-verification
author: hrms-security-privacy-engineer
date: 2026-10-25
code: branch slice/066-grooming, worktree .claude/worktrees/066-grooming-build, diff against origin/dev (head 4758a774, 31 files, +4,113)
requirements: 01c-security-privacy-requirements.md (SEC-1 to SEC-12, PRIV-1 to PRIV-7) plus Surbhi's later decisions in 01-product-brief.md and 05-implementation-notes.md section 10
status: verification only. No code edited.
---

# 066 · Security verification: the grooming red mark

**I wrote 01c.** So I am checking a build against my own requirements. Four mechanisms in it were my
choices, not the brief's: cancel-never-delete (PRIV-3), the slip submit check (SEC-9), one `may_mark`
(SEC-1) and the 3% cap (SEC-10). **Someone other than me should look at those four.** The later
decisions ("Other" free text, the review note the manager reads, the raise route, the 3-mark cap) were
not mine, and I check them here for the first time.

How I checked:
- **Read in code:** every changed file. File and line are named below.
- **Ran it:** one probe script on the engineer's own test site (`hrlocal-066g`, site `test066g`,
  the same code as the branch, same file checksum). It used the test's own G066 people and
  **rolled everything back**. Nothing touched the shared bench, dev or production. The script is
  `C:\Users\Dell\AppData\Local\Temp\claude\c--Surbhi-Git-hr-app\67b461e9-84fe-425b-b761-79423d0b7215\scratchpad\probe066.py`.
- **Read the installed Frappe source** (16.33.1) in that container for the REST, upload and tag paths.
- I did **not** run the slice's test suites again. Test results are the engineer's (05 section 7 and 10:
  55 + 25 OK).

---

## 0 · Bad news first

**Three things block the build. All three are small fixes. None is live anywhere: nothing is on dev,
and DTC's rule set is off.**

**B1. A manager can read a mark they are not allowed to read, by saving it with no changes.**
*(Verified by running it.)* Blocker, P1.
- *Who, what, how:* Ravi manages Rahul. HR (Ritika) marked Rahul two days ago with reason "Other" and
  some typed text. Ravi may not read that mark (SEC-4 point 3: a manager sees today's marks only). The
  normal read is refused: `frappe.client.get` gives PermissionError. But
  `POST /api/method/frappe.client.set_value` with an empty change (or `PUT /api/resource/Grooming Mark/<name>`
  with `{}`) **returns the whole mark**: reason, the typed "Other" text, who marked it, the date.
- *Probe output:* `{"reason": "Other", "other_reason": "PROBE-TEXT", "owner": "ritika@g066.test",
  "mark_date": "2026-10-23", "marked_as": "HR", "modified_by": "ravi@g066.test"}`.
- *Second harm:* the empty save writes **`modified_by` = the manager** on HR's mark. That spoils the audit
  trail the record relies on.
- *Why:* `grooming.py:470-472` gives the current direct manager **write** (and submit) on every mark of
  their reports, so the raise can be written on an HR mark. `grooming_mark.py:57-60` returns early and
  allows the save when nothing changed. Frappe's REST save paths (`frappe/api/v1.py:50-64`,
  `frappe/client.py:184-217`) return the document after a save **without a read check**.
- *The same door* also returns the full mark after a raise sent straight through REST.
- *Fix (engineer to choose and test):* refuse an after-submit save that changes nothing; and accept a
  raise only from `raise_with_hr` (for example, a flag that endpoint sets, which REST cannot set).
  `raise_with_hr` already returns only the mark's name.
- *Test that must exist:* as the manager, `set_value(MARK, hr_mark, {})` and a REST raise on an HR mark
  from another day → refused, and the record's `modified_by` is unchanged.

**B2. Files and tags can be attached to a mark. SEC-8 closed only comments, assignment and sharing.**
*(Upload gate and tag verified by running it; the full file upload was not run because it writes to
disk.)* Blocker, P1.
- *Who, what, how:* anyone with write on a mark can attach a file (`upload_file`) or add a free-text tag
  (`frappe.desk.doctype.tag.tag.add_tag`). Write is given to: the subject on their own mark, the marker,
  the manager on today's marks, HR in scope, **and the manager on any mark of a report (B1's rule)**.
  So a manager can attach a photo of the person to a fine, or tag it "beard not trimmed".
- *Probe output:* `check_write_permission` (the gate `upload_file` uses, `frappe/handler.py:221-235`)
  **passes** for the manager on HR's unreadable mark and for the subject on their own mark.
  `add_tag("probe tag beard", "Grooming Mark", <HR's mark>)` as the manager **succeeded**.
- *Why it matters:* a file can be uploaded as **public**, which anyone can open by its URL. A tag
  creates a site-wide `Tag` name (seen in every user's tag search) and a `Tag Link` row carrying the
  person's name as its title. Both carry free text or a photo outside every guard in this slice, which
  is what PRIV-1 ("no photo") and SEC-8 ("no free text can be attached") forbid.
- *Fix:* add `File` (`attached_to_doctype`) and `Tag Link` (`document_type`) to `refuse_side_record`
  (`grooming.py:533-544`) and its `doc_events` in `hooks.py`. That is two hook lines and two field names.
- *Test that must exist:* `upload_file` and `add_tag` on a mark → refused, and 0 File and 0 Tag Link rows.

**B3. The "Other" word check misses the words 01c SEC-11 names.** *(Verified by running it.)* Major,
P1. It blocks the build because the slice's own test bans these words in the fixed list
(`test_grooming_066.py:443-447`) but the free-text check does not.
- *Who, what, how:* a manager marks a Sikh or Muslim employee "Other: Beard not trimmed". It is
  accepted, stored on the fine, and shown to the person, HR and the marker.
- *Probe output:* `clean_other` **accepted** "Beard not trimmed", "Hair too long", "Moustache untidy",
  "Jewellery not allowed", "Head covering wrong colour", "Dupatta missing", "Tattoo showing",
  "Smells bad", "Limping, wrong shoes". It refused "Turban untidy" and "Sick looking".
- *Why:* `NOT_ABOUT_CLOTHES` (`grooming.py:57-60`) has no hair, beard, moustache, jewel, head, dupatta,
  pagdi, tattoo, smell, odour, disab, limp or unclean.
- *Fix:* add at least the 01c SEC-11 words, and have the test use **one** list for the fixed reasons and
  the free text. **A word list is a floor, not a control.** Free text about a person's appearance cannot
  be made safe by a filter. That stays a decision for Surbhi with counsel (section 4).

**Two more things to fix before release, or to accept in writing:**
- **M1 · Pricing does not enforce the 3-mark rule.** (Major, P2.) The marking stop counts and then
  inserts, with no lock (`grooming.py:398-410`). Two marks at the same moment (the manager today, HR on
  a past day) can both pass at 2 live marks. Then the slip charges **4** days, because
  `payroll_slip.py:140-145` counts every distinct marked date and only the 3% cap applies
  (`payroll_month.py:220-230`). *Verified by running it:* 4 raw marks gave `grooming_days: 4` (the 3%
  cap bit at ₹348.39 in that case, so the law held). For a Junior on a full month with Basic of at least
  ₹13,334, 4 × ₹100 = ₹400 fits under 3% and **would be charged**. DTC's rule is "3, for everyone".
  *Fix:* one line, cap the count at 3 in `month_summary`, plus a test with 4 raw marks.
- **M2 · A manager or HR person who has left keeps reading every mark they ever made.** (Minor, P2.)
  `may_read` (`grooming.py:443-444`) and the list gate (`grooming.py:483`) let the **owner** read with
  no Active check. ERPNext does not disable a leaver's login (lesson 3). *Verified by running it:* with
  Ravi's Employee set to Left and his login still enabled, he still listed and opened his mark. 01c §4
  says a leaver reads nothing. Blast radius: the marks that person made. *Fix:* the owner path needs
  the caller's Active Employee, or HR scope.

---

## 1 · Requirement by requirement

"Met" means I saw the mechanism in the code and a test that would fail without it.

| Req | State | Mechanism (file:line) | Test that proves it |
|---|---|---|---|
| **SEC-1** one `may_mark`, every door, capacity derived | **Met** | `grooming.py:324-434`; controller `grooming_mark.py:33-48` runs it on validate (also on submit); `marked_as` set at `:44`; screens call `_decide` (`grooming.py:1049`, `:1162`) | `test_ac46_sec1_who_may_not_mark` (skip-level, other team, colleague, System Manager alone, HR out of company, out of branch, HR linked to a Left Employee, Left manager; portal and REST); `test_ac10b_a_sent_capacity_is_ignored`; `test_sec1n_the_screens_flag_equals_may_mark_for_every_row` |
| **SEC-2** one live mark a day; pay counts days | **Met** | `grooming.py:394-396`; `payroll_slip.py:140-145` (distinct dates) | `test_ac10a_sec2_one_live_mark_a_day_and_mark_again_after_removal`; `test_ac53_sec2c_distinct_days_and_no_charge_on_a_full_day_leave` |
| **SEC-3** day rules, site time zone | **Partly** | `grooming.py:368-392`, `nowdate()` throughout | `test_sec3_the_day_rules_for_each_capacity`, `test_ac46_a_draft_from_yesterday_cannot_be_submitted_today`, `test_ac42`, `test_ac43`. **Not tested:** the 00:10 IST clock case (05 section 4). Code uses `nowdate()`, the site time zone (verified in code) |
| **SEC-4** the record's own read gate, fails closed | **Partly - B1, M2** | `grooming.py:439-493`; `hooks.py` permission_query_conditions and has_permission; `ignore_user_permissions` on `employee`; not in `SCOPED_DOCTYPES` | `test_ac68`, `test_ac69` (no User Permission rows, the DTC shape), `test_ac70` x2, `test_sec4_link_search_follows_the_gate`, `test_ac72`, `test_sec4g`. **Broken by B1** (write without read returns the record) and **M2** (leaver owner) |
| **SEC-5** removal rules; subject never | **Met** | `grooming_mark.py:107-124` | `test_sec5_who_may_not_remove`, `test_ac20`, `test_ac22_ac22a`, `test_ac28`, `test_ac44` |
| **SEC-6** nothing where the rule set is off | **Met** | `grooming.py:338-339`; `today()` `:1015`; `month_lines` `:1092-1093`; slip check `payroll_slip.py:324-326` | `test_sec6_rule_set_off_or_absent_refuses_on_every_door` (disabled draft and none), `test_ac6_ac2a`, `test_ac52` |
| **SEC-7** ₹0 refused; grade is HR's | **Partly** | `grooming.py:379-383` | `test_ac39_ac41` (Contract, blank, zero). **Release check (e) not met:** `dtc_grade` is a site field, not in the repo, and ALV-215 / 063 SEC-17 has no commit on dev or this branch. On 24 Oct it was level 0 at DTC. **Blocks switch-on** |
| **SEC-8** no free text attached; no share, assign | **Partly - B2** | `grooming.py:533-544` covers Comment, ToDo, DocShare; no share/email/print DocPerm; no import, rename, views | `test_ac76`, `test_ac77`, `test_ac79`. **Not covered:** File attachments and Tags (B2) |
| **SEC-9** slip and marks agree; nothing after submit | **Met** (see M1) | `payroll_slip.py:314-342` (refuses an open ask and a stale line); R11 `grooming.py:362-366`; `_refuse_if_closed` `grooming_mark.py:129-139` | `test_ac50_ac51`, `test_ac44`, `test_an_open_ask_holds_the_slip_and_a_raise_does_not`, `test_ac52`; plus the engineer's Payroll Entry run (05 section 10: two slips held, as designed) |
| **SEC-10** never above 3% (interim) | **Met** | stop at marking `grooming.py:411-416` (full Basic); back-stop on the slip `payroll_month.py:220-230` (earned Basic) | `test_the_three_percent_backstop_stops_a_senior_earlier`, `test_ac50_capped_figure_and_the_why`, `test_ac49`. Race: the back-stop holds the law even if two marks pass together (probe: capped at ₹348.39) |
| **SEC-11** fixed clothing-only list | **Partly - B3** | `grooming.py:47`, validate `grooming_mark.py:34-36` | `test_sec11_reasons_are_the_fixed_clothing_only_list`. The fixed list is right. **"Other" reopens it** and its word check misses the 01c words (B3) |
| **SEC-12** no new bypass; purpose fence | **Met** | 0 `ignore_permissions` in new code (the three hits are comments); ceilings added, `payroll_slip.py` held at 2 (`test_portal_security_010.py:825-836`); fence `test_ac73` | `test_sec16_ignore_permissions_does_not_grow`; `test_ac73_the_record_is_named_only_where_it_belongs`. Review check (c): each `frappe.get_all` on the mark in `grooming.py` (`today` `:1018`, `month_lines` `:1102`, `flag_for` `:595`, `pending_reviews` `:636`, `may_raise` `:709`) sits behind its own gate and returns only what that reader may see |
| **PRIV-1** least fields; random name | **Met**, as changed by decisions | `grooming_mark.json`: `other_reason` (100), raise and ask fields added by decision; `autoname: hash` | `test_ac79_least_fields_a_random_name_and_a_locked_reason`. B2 is the gap ("no photo") |
| **PRIV-2** told the same day; honest about who is not | **Partly** | bell `grooming.py:793-811`, fixed words, subject only, enabled and Active (`:767-772`); told-in-person tick R13 `:418-420` | `test_ac33`, `test_ac33a`, `test_ac13_r13_no_login_needs_the_told_tick_on_every_door`, `test_the_text_never_reaches_a_notice...`. **Gap:** the live portal has no list of notices (05 bad news 6), so even a manager with a login sees the bell only in the desk. At DTC everyone is told in person, on a self-ticked box |
| **PRIV-3** cancel, never delete | **Met** | no delete DocPerm; removal is cancel with a fixed reason `grooming_mark.py:107-124`; `reason` locked after submit | `test_ac28` (0 new Deleted Document rows, a Version row), `test_ac79`, `test_it_cannot_be_changed_after_the_mark_is_made`. B1 can overwrite `modified_by` |
| **PRIV-4** no purge; no "keep for ever" | **Met** (no purge code), **retention open** | no delete, purge or retention code in the diff (grep) | review check. The new **Grooming Review** note has no retention answer either |
| **PRIV-5** one purpose | **Met** | fence `test_grooming_066.py:896-925`; only HR's Inbox, the slip and the reports read it | `test_ac73`. Limit: the fence looks for the text "Grooming Mark", so a file that imports `grooming.MARK` is not caught (inbox_api does, and is allowed) |
| **PRIV-6** HR sees marks per marker | **Partly** | three Report Builder views (HR roles only, through the read gate) and the "Grooming Review Pending" script report | `test_ac66_ac67`, `test_priv6_a_branch_hr_sees_only_its_branch`, `test_y4_the_pending_report_and_the_inbox`. **Missing:** the "marker by person" view. "People with grooming reds" groups by `employee_name`, so two people with one name merge. The 3-mark cap now limits what one marker can do to one person, so this is P3 |
| **PRIV-7** no personal content in logs | **Met** | `refuse()` logs ids and rule only (`access.py:28-53`); the notice failure logs the mark name only (`grooming.py:762-764`); `clean_other` never repeats the text | `test_priv7_a_failed_notice_keeps_the_mark_and_logs_no_name`, `test_priv7_a_refusal_logs_ids_and_rule_only` |

---

## 2 · The later decisions, checked

| Decision | State | What I found |
|---|---|---|
| "Other" + 100 characters | Built; **B3** | Stored on the mark only. Length is enforced in code (`grooming.py:68-69`) and in the field (`length: 100`). It never reaches a notice, the Inbox, the pending report or a saved view (tests above; I read every notice builder, `grooming.py:793-869`). It does reach the Today card and the month for readers of the mark, by design. Output is escaped on screen (`gpEsc`, portal.js). Frappe also strips HTML from Data fields on save |
| Review flag at whichever limit comes first | **Met** | `_raise_point` `grooming.py:549-563`; `test_ac55_y1...` (Senior flagged at mark 2), `test_ac55_ac56...` (Junior at 3), `test_ac60` |
| Manager reads the review note | **Met** | `review_has_permission` and `review_query_conditions` (`grooming.py:496-530`): HR in scope and the **current Active direct manager**; never the subject. `month_lines` gives the note to `is_manager` and `is_hr` only (`:1181`, `:1216`). `test_ac64...`: Rahul (subject), Om (System Manager), Olga (other HR), Neha (other manager), Sunil (skip-level), Deepa (colleague) get nothing; Ritika and Ravi read it. A marker who is not the manager gets the date only (`:1210-1220`) |
| Employee sees only "Action agreed on {date}" | **Met** | `_review_payload` gives the subject `state` and `on` only (`grooming.py:1214-1220`). The note is never selected for them (`with_note` is false) |
| Option A raise-it-with-HR, fixed reasons | **Met, except B1** | `may_raise` `grooming.py:696-721`; reasons exclude "Other" (`:692`); once a month; current Active manager only; drops when the person leaves or the manager changes (`:574-581`). Employee told in fixed words with no reason (`:853-854`); HR's bell carries no reason. Tests: `TestRaiseWithHR` (6). B1 is the manager-write rule this route needed |
| 3 marks for everyone | **Met at marking; M1 at pricing** | R12 `grooming.py:406-410`, HR included; `test_three_marks_a_month_is_the_most_for_everyone`; `test_hr_records_the_talk_and_still_nobody_adds_a_fourth` |
| 3% back-stop | **Met** | SEC-10 above |

---

## 3 · Who can read a mark and the review note (tried, not assumed)

| Actor | Mark | Review note | Evidence |
|---|---|---|---|
| Employee (subject), Active | Own marks, all of them | No. "Action agreed on {date}" only | test_ac68, test_ac64 |
| Subject who has left | Nothing (fails closed) | No | `may_read` needs an Active Employee |
| Marker | Their own marks, for ever | Date only, unless also the manager or HR | test_ac68 |
| Marker who has left, login enabled | **Still their own marks (M2)** | No | probe P5 |
| Direct manager | Today's marks of direct reports, plus own marks. **Any report's mark through an empty save (B1)** | Yes, own direct reports | test_ac68, test_ac70; probe P1 |
| Skip-level manager | Nothing; no grooming key in the month | No | test_ac68 (Sunil), test_sec4g |
| HR in scope | Everything in scope | Yes | test_ac68 (Ritika) |
| HR out of company or branch | Nothing | No | test_ac68 (Olga, Anil), test_priv6 |
| HR linked to a Left Employee | Nothing | No | test_ac68 (Lalit) |
| Owner or System Manager with no HR role | Nothing | No | test_ac68 (Om), test_ac64 |
| System Manager **with** an HR role | **Every company** (`access.py:274-275`) | Yes | Read in code. One company at DTC, so not a leak today. D7 says an owner with an HR role counts as HR |
| Colleague | Nothing | No | test_ac68 (Deepa, Neha) |
| Guest | Nothing; nothing in this slice is `allow_guest` | No | Read in code (grep) |

---

## 4 · Findings ranked

| # | Level | Urgency | Finding | Kind |
|---|---|---|---|---|
| B1 | Blocker | P1 | Manager reads any report's mark through an empty save; `modified_by` overwritten | dangerous debt - fix in this slice |
| B2 | Blocker | P1 | File and Tag can be attached to a mark (free text, photo, public file) | dangerous debt - fix in this slice |
| B3 | Major | P1 | "Other" check misses hair, beard, jewellery, head covering, tattoo, smell, disability | dangerous debt - fix the floor now; the free text itself goes to counsel |
| M1 | Major | P2 | Slip does not hold the 3-mark rule; a race can charge 4 | temporary debt - one line removes it |
| M2 | Minor | P2 | Leaver who marked keeps reading their marks | temporary debt - one condition removes it |
| m3 | Minor | P3 | PRIV-6 "marker by person" view missing; "People with grooming reds" groups by name | acceptable simplification, given the 3-mark cap |
| m4 | Minor | P3 | Tests skip on days 1-3 of a month (`test_three_marks...` `:49-50`; others on day 1). A CI run then proves less and says "OK" | temporary debt - fix the dates in the fixture |
| m5 | Minor | P4 | `_decide` says "No such employee" and "not switched on for this company" before it checks the caller's capacity (`grooming.py:334-339`). It tells an outsider whether an employee id exists | security debt |

---

## 5 · What blocks switching it on at DTC (not the build)

1. **ALV-215 / 063 SEC-17.** `dtc_grade` and `employment_type` must be HR-only. Today a marked manager
   can make themselves unmarkable (`External`) or halve the fine. No commit exists for it.
2. **Counsel on "Other" free text (Q-C3).** It is a judgement about a person's appearance, in the
   marker's own words, on a wage-fine record. B3 only sets a floor.
3. **How people are told (PRIV-2).** 438 of 445 DTC staff have no login. The live portal has no notice
   list, so even the managers see the bell only in the desk. Telling them relies on a self-ticked box.
   Surbhi to accept in writing, or choose the live-bell option in 05 section 10.
4. **Retention (Q-C2)** of marks **and** of the new Grooming Review note. The note is close to counsel's
   "performance record, employment + 6 months, then erase". No owner named.
5. **The ordinary red marks** may also be fines with no cap (01c §11.1). Still open with counsel.
6. Release checks: the rule set enabled, the GRV component present at the company, a structure row at ₹0.

---

## 6 · Worries (not findings yet)

- **The review note is free text with no limit and no word check**, read by the manager. HR could write
  health or family details there. No path leaks it beyond HR and the manager that I found.
- **A new manager reads every old review note** for a report, including ones written under a previous
  manager. That may be more than Surbhi meant.
- **A System Manager can read `Version` rows** (Frappe's own DocPerm). These hold removal reasons, ask,
  keep and raise changes for a mark name, but no employee name. Draft edits of `other_reason` through
  REST would also land there. "System Manager alone is not HR" is a default, not a wall: a System
  Manager can give themselves an HR role.
- **The purpose fence looks for text only.** A new reader that imports `grooming.MARK` passes it.

---

## 7 · What I could not check

- **The full file upload and a public file URL.** I proved the permission gate passes. I did not upload,
  because that writes a file to disk that a rollback cannot remove. Needed: one run on a throwaway site.
- **`dtc_grade` permission level at DTC today.** It needs a read-only query on dtc.alvoraa.co. Its state
  on 24 Oct was level 0.
- **A real two-request race** for the 3-mark stop. The count-then-insert with no lock is read in code;
  the result of 4 marks is shown by the probe.
- **The time-zone clock case** (SEC-3 e).
- **Whether the 7 DTC managers can open the desk bell at all.** That needs their roles on the site.

---

## 8 · Subtract pass

Removed on the final read: a finding that the review note has no `track_changes` (that is correct, and
it is on purpose); a finding about `employee_name` in HR bells (HR may see it); a section restating the
threat model from 01c; a separate table of the notice texts (section 2 covers it).

The build itself: I found **no surface it did not need** - no new public route, no export beyond HR
Manager's, no cache, no copy of personal data beyond `employee_name`. The extra write right in B1 is the
one piece of surface the raise route added, and it is the one that leaks.

---

## Residual risk

| Risk | Kind | Level | Who accepts | Date |
|---|---|---|---|---|
| B1, B2, B3 | Must be fixed in this slice | P1 | Not acceptable as a risk | - |
| M1 slip can charge a 4th mark after a race | Temporary debt | P2 | Surbhi, or fix (one line) | open |
| M2 leaver reads own marks | Temporary debt | P2 | Surbhi, or fix | open |
| Grade editable by its owner (ALV-215) | Dangerous debt | P1 for switch-on | Surbhi | open |
| "Other" free text on a fine | Dangerous debt | P1 for switch-on | Surbhi with counsel | open |
| Staff told only in person | Temporary debt | P1 for switch-on | Surbhi | open |
| No retention for marks or review notes | Temporary debt | P3 | **No owner named** | open |
| Ordinary reds may be uncapped fines | Dangerous debt | P1 for the first DTC payroll | Surbhi with counsel | open since 24 Oct |
