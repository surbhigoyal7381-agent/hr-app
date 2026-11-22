# 088 Register notice and forms: product brief

**Author:** hrms-product-manager. **Date:** 21 Nov 2026. **Status:** recommendation, not a decision. **Risk tier:** 1 (pay gate, personal data, retention). **Slice name:** 088 = the monthly change notice. The statutory forms become **088b**.

**Read:** 01a, 07-devops §1, counsel memory (`counsel-087-hr-punches-nov21`), 087 spec "Confirm redesigned" (line 813 on). **Could not check:** this session had no shell, so I did not run `git rev-list dev...origin/dev` and did not grep `hrms/` or `erpnext/`. The UX and DevOps scans read worktree dev `bad23ce0` and found no print format and no register output in `alvoraa_portal`. I am relying on that, and on nothing newer. Frappe HR standard registers: only the stock Monthly Attendance Sheet (P/A codes), per 01a; not re-checked.

## Bad news first
1. **The notice alone does not clear Grace.** Counsel's condition 1 is "Forms C and D alongside Form IX". No layout exists. The notice unblocks **086 and counsel's condition 3**. Forms stay open until the layouts arrive.
2. **Forms C and D may not be attendance registers.** The rule text 01a opened says C is the Register of Employees and D the Register of Wages (Indian Kanoon, secondary source, garbled). Counsel called them attendance registers. If I build to the wrong reading, we ship a wrong legal document.
3. **Photo storage can reach 108 GB per tenant** if every employee has a photo every month for 5 years. The thin slice avoids this (below). Nothing deletes at year 5: the erase job is off.

## 1. Job to be done
Persona: **Employee** (with no app). *"When someone else changes my attendance, I want to see it in plain words on paper and sign or thumb-print it, so I know what I am being paid for before it is locked."*
- HR Manager: gets one list of who has signed before payroll, and one place to record a signature.
- CXO: nothing changes.
- Line manager: nothing new in this slice (see persona table).

## 2. Pain
No story from a live customer is on file for this; the driver is counsel's reply of 21 Nov (relayed by Surbhi, unsigned). Plain picture: at Grace, a floor worker has no app. A supervisor's note changes her Tuesday. Today she finds out when her pay is short. **No data on how many people this touches: baseline unknown, measure first.**

## 3. Competitors (read via search snippets, 21 Nov 2026, per 01a; no product screen seen)
| Capability | greytHR | Keka | Zoho People | Us |
|---|---|---|---|---|
| Statutory registers | Admin downloads, state by state | not found | not found | none |
| Employee told of a change by others | not found | not found | not found | none |
| Employee sign-off | not found | lock at cut-off, no sign-off found | no acknowledgement found | notice with signature |
Frappe HR standard, Darwinbox, CatalystOne: not checked.
**Headline (inference, not fact):** in what I found, registers are an admin-only download and the employee is never shown the change. **Deliberately not doing:** admin-only registers with no employee view, red warnings or timers on an unsigned month, hiding "not counted" scans from the audit log.

## 3a. Three ways
- **Conventional:** all four statutory forms, payslip lines, per-person PDFs for everyone, photo per person.
- **Better:** one page per person with only the changed days, browser print, no PDF engine.
- **Reimagined:** app Confirm for everyone and no paper. Rejected: counsel requires a non-app route.
- **Could we not build it?** No. No register output exists and counsel's condition needs a paper to sign.
**Proposal: Better.** Ladder rung: **new code** (one portal page with print styling, reusing 087's fields). Cheaper rungs rejected: configuration and print-format edits do not exist for this (no print format in `alvoraa_portal`; the stock slip format would differ per tenant, DevOps OPS-2).

## 4. Kano (proxy) and demand
- **Must-be, proxy** for Grace: counsel made it a go-live condition. For other tenants, **Attractive, proxy**: no competitor I found shows the employee changes made by others.
- Demand evidence: **seen**, one source: counsel's conditions, relayed. Prospect demand: none on file. Evidence that would change this: a Kano survey of non-app floor staff and HR, or Grace saying they want the notice dropped.

## 5. Persona enhancements
| Persona | Idea | In this slice? | Why |
|---|---|---|---|
| Employee, no app | Printed one-page month notice, large print, English + Hindi, signature or thumb box | **Yes** | The job itself |
| Employee, with app | Same list under the month view, with the existing 087 Confirm | **Yes**, same data, a few lines | Counsel: show on register or payslip; the list is the same query |
| HR Manager | Print button, "signed on the register" recording, unsigned count | **Yes** | It is the pay gate from 087 |
| Line manager | Print a whole store's sheets | **Later** | Privacy risk; HR prints for now |
| CXO | Signed vs unsigned share | **No** | Not needed to unblock |
| Payslip lines | Changes on the payslip | **No** | Differs per tenant; DTC pays outside the portal |
| Statutory forms | IX, C, D, Delhi G/H | **Later (088b)** | Layouts missing |

## 6. The WOW
HR prints a notice for a worker with a changed day. It reads: *"Thu 13 Nov. Your punch-out time 14:40 was added by HR. HR approved. I have read this. Signature or thumb print: ______ Date: ______"* The worker signs in two minutes with no phone. The HR person photographs the page; the day turns **Confirmed** and drops off the "Before payroll" list.

## 7. Thin slice
**Needed to validate and ship (in 088):**
- One notice per person per month: only that person's own days, only **valid hours**, only days changed by someone else that need confirmation, with who filed it and the mandatory reason.
- Opened from the portal, printed by the browser. No PDF engine, no background job.
- HR records "Signed on the register" (087 mechanism) with one photo of that person's page.
- Printed only for people who have changes, not all 600. That is how photo storage stays small (rough guess: a few photos a month per tenant; **evidence required**).
- Export is logged (who, when, which person).

**Deliberately out:** Forms IX, C, D, Delhi G/H (088b, waits for layouts); payslip changes; store-manager printing; reminders and chasing; CXO tiles; a form builder; the 5-year deletion job; Hindi without native review.
**Honest consequence:** Form IX is an electronic register we also do not yet output. Grace stays blocked until 088b.

## 8. Run-side (DevOps §1)
Browser print adds no worker load. Photos stay `is_private`, reuse the 5 MB cap and checks in `employee_photo.py`, shrunk on the phone. Time one real signed-page photo before build (OPS-8). The 088b register is one background job on `long`, about 24 pages for 600 people, estimated, not measured.

## 9. Success measures
| Measure | Baseline | Target | How |
|---|---|---|---|
| Changed days confirmed (app or signed) before pay lock | unknown, measure first | all of them, or the slip is blocked (087 rule) | count of 087 confirmation fields at lock |
| Time to sign one notice | unknown | under 2 minutes on the floor | watch two HR runs at Grace |
| Employee disputes after pay on a changed day | unknown | fewer than before; compare month on month | HR note count |
| Photo storage per tenant per year | none | under 1 GB | file size query |

## 10. Risks (red team)
- **Other people's names on a page:** one person per sheet, own data only. HR-only printing.
- **Thumb print may be biometric data under DPDP:** unanswered, see counsel Q4. Until answered, the photo is HR-only and logged.
- **A worker cannot read:** large print plus Hindi; HR reads it aloud. Pressure to sign is real. Notice says "if this is not right, tell HR before you sign".
- **Employee leaves mid-month, or the manager changes:** notice is by employee; a leaver's last month still prints.
- **Photo missing or blurry:** HR cannot confirm; slip stays blocked. This could cause HR tickets.
- **Wrong tenant config:** if the 087 gate is off, the notice is just information.
- **Cheapest check:** print one dummy notice for three Grace staff before building the layout.

## 11. Thriving lens
- Engagement: a worker is told, not surprised. Collaboration: HR and floor see the same facts.
- Inclusiveness: no-app, low-literacy staff are the target; Hindi needs native review.
- Transparency: shows the worker what others did to her record. Safe: own data only, no ranking, no reasons for absence.

## 12. Regulatory read (not a lawyer; ⚠ COMPLIANCE)
1. Code on Wages 2019 and Wages Rules 2026 (Form IX); Punjab Shops and Commercial Establishments Rules 1958; DPDP for the photo.
2. The register duty is the employer's. The notice helps the customer discharge it.
3. New: a signature or thumb photo kept 5 years; a printed sheet of personal data.
4. Front-page test: defensible if one person per sheet and photos are restricted. Not defensible if thumb prints sit in open files.

## 13. Subtract pass
Removed: payslip lines, store printing, per-page photo batching (needs counsel), the CXO share, any form code. Kept: one notice, one record, one photo.

## Open questions (recommendation in brackets)
Counsel questions to send, in order:
1. Are Punjab/Haryana Forms C and D attendance registers, or employee and wage registers? Please supply the layout. Same for Delhi G/H and Form IX. **Owner: Surbhi/counsel. Blocks 088b.** [Rec: get the layouts this week; build 088b only from them.]
2. Does the monthly notice go to **every** non-app employee, or only to those with a change? **Blocks print scope and photo volume.** [Rec: only those with a change.]
3. Is one photo per employee's signed notice needed, or one photo per register page, or can HR keep the signed paper and record a tick? **Blocks storage.** [Rec: paper kept plus one photo per person with a change.]
4. Is a thumb-print image biometric data under DPDP? Who may open it? **Owner: counsel, then security engineer.** [Rec: HR-only, logged.]
5. Retention of the signed notice and photo: 5 years from the last entry? Who runs the deletion? **Owner: Surbhi.** [Rec: name an owner now; build in 2031-era slice, not now.]
6. Is Form IX valid with no employee signature when electronic? [Rec: ask; do not assume.]
Also for Surbhi: should 088 ship alone, with Grace still waiting on 088b? [Rec: yes; it clears 086 and condition 3 at once.] Is HR "signed on register" needs a second person (087 rule) enough for small branches? [Rec: yes, keep 087's rule.]

## Assumptions
- [ASSUMPTION] Counsel's "monthly register notice" means a per-person notice, not a shared page.
- [ASSUMPTION] Browser print is acceptable to counsel as "printed".
- [ASSUMPTION] A few photos a month per tenant, not hundreds.
- [ASSUMPTION] Counsel's replies are accurate as relayed; they are unsigned.

## Kill criteria
Stop if: counsel requires one photo per employee for all staff and rejects page batching (storage cost changes the slice); counsel says a thumb print needs biometric-class handling we cannot yet provide; or an HR run at Grace takes over 5 minutes per notice.

## Brief gate — Surbhi's decision, 21 Nov 2026

**Build it, with every recommendation taken:**
- 088 is the monthly change notice only. It ships alone.
- Grace waits for 088b, the statutory forms, which starts once the official layouts arrive.
- Surbhi gets the layouts of Forms IX, C, D and Delhi G/H from counsel, and sends counsel the open questions.
