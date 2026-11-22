# 088 Register notice and statutory forms: UX opportunities scan

**Mode:** opportunities scan, no prototype. **Author:** hrms-ux-designer. **Date:** 21 Nov 2026.
**Tier (usage-discipline §1):** 1 for the notice (it gates pay lock and carries personal data); 2 for the exports.
**Read:** `ux-learnings.md`, `usage-discipline.md`, counsel memory `counsel-087-hr-punches-nov21`.
**Looked at:** the code in worktree `088-register-notice-and-forms` (dev `bad23ce0`) and the 087 design and field names in worktree `087-attendance-follows-punches` (HEAD `5debebc7`). **I did not open the running portal and took no screenshots.** Every "today" line below is from code, not from a screen. No login or tenant was used.

## 1. Frame
Employee with no app (and one with an app) learns, on paper or on the phone, that someone else changed their day; HR and an inspector get a register in the statutory layout. Counsel's conditions for Grace: Forms C and D alongside Form IX, mandatory reasons, a monthly notice for non-app staff (counsel, 21 Nov, relayed by Surbhi; unsigned).

## 2. Current state (Fact, from code unless marked)
| Surface | What it does today | Source |
|---|---|---|
| Employee Time page, month view | Month picker (`acBar`, previous/next, select). Day sheet shows punches. No "changed by someone else" list for the month. | `portal.js` ~5640 |
| Payslip in portal | Take-home, working days, paid days, Held-days banner with dates, earnings, deductions, "Download PDF". No line about changed punches. | `portal.js` ~11990-12030 |
| Payslip PDF | Org's default Salary Slip print format via Frappe's print pipeline. Not changed by us. | `hr_api.py` `download_payslip` |
| Daily Attendance Workings (Script Report, HR Manager, HR User, System Manager) | Columns: Date, Day, In, Out, Minutes, (-/+) Min, Break (min), Status, Quarters, Red, Green, Leave, Fine, Remarks, Shift, Shift (min). No who-added column, no sign column. | `daily_attendance_workings.py` `_columns` |
| Salary Components and Workings (Script Report, same roles) | Exists; not opened in detail. **Not checked.** | report folder |
| Monthly Attendance Sheet | Stock HRMS report in `hrms/hrms/hr/report/monthly_attendance_sheet` (P, A, HD/P codes). Not Alvoraa code. | `monthly_attendance_sheet.py` |
| Print formats in `alvoraa_portal` | **None found** (searched the app for print format and print folders). HRMS ships only salary slip, job offer and appointment letter formats. | find |
| "Muster roll" | Appears only in comments about DTC's own sheet (PP/AA, no half days). No muster-roll output exists in the portal. | `shift_standard.py`, `payroll_rules.py` |
| Printed register that staff sign | **Not found.** Searched: portal.js (`window.print` hits are other pages), the two reports, print_format folders. | |
| 087 fields | `alvoraa_fix_added_request`, `alvoraa_fix_aside_request` on Employee Checkin; `alvoraa_confirmed_by/on`, `alvoraa_replaces` on Attendance Request. Not on dev. Signed-on-register design: 087 `01b` F-5. | 087 files |

## 3. Statutory forms (Question: I could not get gazette text)
- **Form IX** (Wages (Central) Rules 2026, rule 51, notified 8 May 2026, title corrected 15 Jul 2026): Employee register, wages register and Form IX attendance register-cum-muster roll; paper or electronic. Source: [Mondaq](https://webiis08.mondaq.com/india/employee-rights-labour-relations/1788486/notified-code-on-wages-central-rules-2026-what-employers-need-to-know) (read via search, not opened). A practitioner rendering at [taxclue](https://www.taxclue.in/blog/forms-i-iv-ix-code-on-wages-central-rules-2026-employee-wage-and-attendance-registers/) (opened) lists In/Out for days 1 to 31, days worked, overtime hours, tour details, and register keeper signature "required in case the register is maintained physically". **That is a publisher's table, not the gazette.** Why it matters: it says an electronic Form IX needs no signature. The employee's signature on paper is then counsel's condition, not the form's. Layout to be supplied by counsel or Surbhi (G.S.R. 343(E)).
- **Forms C and D** (Punjab rules 1958, rule 5): the opened [Indian Kanoon](https://indiankanoon.org/doc/193622947/) text says C is the **Register of Employees**, D is the **Register of Wages**, E the register of deductions. The extract of C shows daily hours, overtime, leave and a signature of employer and employees; extract is garbled. **Risk: counsel called these attendance registers; the rule text says C is an employee register with hours columns.** Which version applies in Haryana is not checked. Layout to be supplied by counsel or Surbhi.
- **Delhi Forms G/H:** not searched. Layout to be supplied by counsel or Surbhi.

## 4. Competitors (whole products; nothing here seen in a running product)
I opened no competitor product page this run. These are search results only, so label: read via search snippet, 21 Nov 2026.
- **greytHR:** state-by-state statutory registers (muster roll, Form II Maharashtra, Form 1 Gujarat) generated by admin from Reports Gallery, with a Wiki page per form ([greytHR wiki](https://greythr.com/wiki/compliances/central-muster-roll), [help](https://greythr.freshdesk.com/support/solutions/articles/1060000049216-how-can-admin-download-the-muster-roll-cum-wage-register-report-)). Admin-only. Whether the employee sees anything: not found.
- **Keka:** HR or manager can regularise on an employee's behalf; attendance can be locked at cut-off ([Keka help](https://help.keka.com/hc/en-us/articles/39946902651921-How-to-regularize-attendance-on-behalf-of-employees)). No employee sign-off step found.
- **Zoho People:** employee-raised regularisation with a reason ([Zoho help](https://help.zoho.com/portal/en/kb/people/administrator-guide/attendance-management/settings/articles/attendance-regularization-zp)). No acknowledgement step found.
- **Darwinbox, saral, Spine, CatalystOne, Frappe HR:** not checked.
- **Reading:** in what I found, registers are an admin download and a changed day is not shown back to the employee. That gap is where Alvoraa can be different. Experiment, not fact.

## 5. Ideas by persona
| Persona | Idea | Job | Evidence | Size |
|---|---|---|---|---|
| Employee with app | In the month view, one line "3 days changed by others this month" opening a list: date, time, what, who filed, "HR approved". Same lines under the payslip total. Counsel's text: show it on register or payslip. | Know what was done to my day without asking HR | Counsel; 087 F-8 wording | M |
| Employee with no app | A printed month page: their own days, the changes in words, a signature or thumb box beside each changed day. Large print, English and Hindi. | Understand and sign in 2 minutes without a phone | Counsel condition 3; 087 F-5 | M |
| Store manager | A print button for the whole store, one page per person, and a count "4 of 31 not yet signed". Exceptions first. No ranking. | Collect signatures on the floor | One-way rule: must not cost the employee | S-M |
| HR | One "Before payroll" list already designed in 087 (unconfirmed changes). Add: the register export lives on the same page, with a clear "Valid hours only" note. Signature recorded by a second HR person with photo (087). | Close the month once | 087 `01b` | M |
| CXO | Nothing new. One number only if wanted: signed vs unsigned share, aggregated, small groups hidden. | Trust | Product-context §2 | S, optional |
| Inspector (external, paper or PDF) | Form IX, C, D exports with the company header, month, and a "Not counted scans are kept in the audit log" footnote only if counsel agrees. | Open the register and read it | Counsel | M |
| Customer IT / DPO | Printed register carries only the person's own data when handed out; export is logged (who, when). | Privacy | `joiner-audit` pattern | S |

## 6. Findings
| ID | Finding | Impact | Kind | Size | Severity |
|---|---|---|---|---|---|
| R1 | No printed register exists; counsel's non-app route has nothing to sign | High | New | M | P1 for Grace go-live |
| R2 | Payslip and month view say nothing about others' changes | High | New | S-M | P2 |
| R3 | Daily workings has no "who added" or "signed" column | Medium | Improve | S | P3 |
| R4 | Form C/D meaning conflicts between counsel's note and the rule text | High | Question | none | P2 until counsel answers |
| R5 | Form IX needs no employee signature when electronic, per one secondary source | Medium | Question | none | P3 |
| R6 | A printed register shows other staff names if one page holds many people | High | Risk | S | P1 privacy: one person per sheet or tear-off |
| K1 | Held-days banner on the payslip says what, which dates, who decides | Medium | Keep | none | none |

## 7. Words (Recommendation, English first; Hindi to be machine-drafted and reviewed natively)
- Employee line: "3 days this month were changed by someone else. See them."
- Row: "Thu 13 Nov. Time 14:40 added by Anil Sample (HR). HR approved."
- Printed foot: "I have read these changes. Signature or thumb print: ______  Date: ______"
- Not shown to colleagues or the printed manager copy: reasons for absence.

## 8. What not to copy
- Admin-only download with no employee view (greytHR as found): it is the thing counsel's condition 3 removes.
- A timer or red warning on an unsigned month: presses on the least powerful person (087 `01b` fairness risk).
- Hiding "not counted" scans from the audit log to tidy the register: counsel says keep them.

## 9. Not in this slice (decide yourself)
Delhi forms if no Delhi tenant now; a CXO signing chart; reminders by SMS; a one-page-per-person bulk print for 400 staff beyond the first store.

## 10. Open decisions
- **⚠ DECISION 1** (owner: Surbhi, with counsel): what are Forms C and D in Haryana and Punjab, and is Form C the attendance register? Blocks the export layout.
- **⚠ DECISION 2** (owner: Surbhi/counsel): the official Form IX, C/D and Delhi G/H layouts. Blocks all export work.
- **⚠ DECISION 3** (owner: hrms-business-analyst): a manager's added punch needs no employee signature; confirm the notice is still shown for it.
- **⚠ DECISION 4** (owner: security engineer): printed sheet scope (one person per sheet) and who may print.

## 11. Subtract pass
Removed: a CXO tile, a month-row tag, notification pushes, a pending-signature chase, a per-form preview screen. Kept only what counsel's conditions need.

## 12. Checks
Verified by reading: portal.js lines above; `_columns`; the 087 field names; two statutory sources opened (taxclue, Indian Kanoon; both secondary). Not checked: running portal, Salary Workings report detail, Delhi forms, any competitor product screen.
