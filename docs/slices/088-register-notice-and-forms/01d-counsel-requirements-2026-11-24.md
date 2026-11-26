---
slice: 088-register-notice-and-forms
artifact: 01d-counsel-requirements-2026-11-24 (update to 01-product-brief.md)
author: hrms-product-manager
date: 2026-11-24
status: draft. Recommendations only. Surbhi decides. I am not a lawyer.
risk tier: 1 (personal data, retention and deletion, pay evidence)
inputs: [01-product-brief.md, 01c-security-privacy-requirements.md, 02-functional-spec.md (header), 05-review.md and 06-security-review.md (read from the release worktree, see below), register_notice.py, counsel's answers of 24 Nov relayed by Surbhi]
---

# 088 · What counsel's four answers change

## 0 · Bad news first

1. **The monthly notice, as built, does not do what counsel needs.** Counsel says it does not clear the condition, because about 3,300 direct punch additions and edits in October never reach it. I agree, and the code confirms it (section 1).
2. **Fixing that is not a tweak. It is its own slice.** It adds a new source of changes, a mandatory reason on a shared, busy table (the punch feed), and a decision about Administrator.
3. **I recommend holding the release of the dormant 088 code.** Reasons in section 7.
4. **Counsel's answer on thumb prints contradicts its own "switch it on."** The photo can hold a thumb impression. Counsel called that biometric. The code treats a signature and a thumb print the same. The people this feature is for are the ones most likely to use a thumb. I recommend a blocking question to counsel (section 4).
5. **Counsel's note is not on letterhead and may be a typed summary.** Everything below rests on it as relayed. If it is a summary, the wording of each answer matters and we have not seen it.

**What I read.** The worktree `/Users/mac/hr-app/.claude/worktrees/counsel-reqs-nov24` (the coordinator says `2d768a9b`). **I had no shell**, so I did not run `git rev-list`, `git rev-parse` or `git show`. For `05-review.md` and `06-security-review.md` I read the files in the release worktree `/Users/mac/hr-app/.claude/worktrees/release-088-alv436/docs/slices/088-register-notice-and-forms/` instead. Of 06 I read the requirement table (about lines 100-116) and section 5 (lines 162-192). Of 05 I read only search hits. I did not read the whole of either file. Labels: **proven** = I read the line this session; **inferred** = reasoned from what I read; **not checked** = said so.

## 1 · Scope change forced by answer 4

**Counsel's ask (as relayed):** the monthly notice must pull every manual punch addition and every direct edit from the audit log, and each must carry a reason code.

**What the code does today (proven).** `qualifying_changes` in `alvoraa_portal/alvoraa_portal/register_notice.py` (lines 160-229 in this worktree; 06 cites `:235` on the release branch) lists only changes that are:
- an Attendance Request, submitted, `alvoraa_review_status` = Approved;
- carrying `alvoraa_missing_time` or `alvoraa_set_aside`;
- filed by someone who is not the employee;
- **not filed by `Administrator`** (line 225: `r.owner == "Administrator"` is skipped).

A correction made by creating or editing `Employee Checkin` rows directly appears nowhere. (Proven by reading; the query never touches Employee Checkin.)

**How big is the change (my read).**

| Piece | What it means | Size, label |
|---|---|---|
| New source of changes | The notice must also read direct check-in additions and edits. Edits: Employee Checkin has `track_changes: 1` (`hrms/hrms/hr/doctype/employee_checkin/employee_checkin.json:288`), so edits should leave Version rows. **Proven for the flag; not checked** that the rows exist at DTC. Additions: Frappe records owner and creation time on the row, but **I do not know how a hand-made check-in is told apart from a machine or phone punch.** Someone separated 2,007 hand-made ones in October (memory `dtc-october-backfill-not-a-gap`); I did not read how. | Medium. The engineer must find that rule first. |
| A reason on every one | No field for it that I know of on Employee Checkin. **Not checked exhaustively.** It must be a fixed list (a "reason code"), not free text, which also avoids the personal-detail and markup problems free text caused on the paper. Rung: a Custom Field of type Select plus a check in code. A new "Reason Code" DocType is rejected: a short fixed list does not need one. | Small to build, **large in risk** (next row). |
| Making the reason compulsory | Employee Checkin is written by biometric machines, the field phone app, the 087 flow, Desk, imports and repair scripts (`alv291_attendance_fix.py` alone mentions it 20 times). A rule that refuses a write without a reason, applied carelessly, **refuses a machine punch and loses it.** Memory `dtc-biometric-sync-facts`: an unknown code is skipped for good. So the rule must apply to people only, never to the sync or phone accounts. Every future repair script then needs a reason argument. | **The risky part. Tier 1.** |
| Administrator | Today excluded on purpose (087 AC-104: break-glass is not "a person filing"). Counsel's wording has no exception. 1,315 of October's 3,322 changes were Administrator edits (the coordinator's count; matches memory). **A worker cannot be told "Administrator changed your day".** And a shared account cannot answer "who". | Needs a decision (section 1a). |
| Volume | October: 3,322 changes. Against roughly 600 staff that is about 5 per person on average (**inferred**; October was a deliberate catch-up, so a normal month is probably far less, **baseline unknown, measure first**). If it is even a fraction, the notice changes from "a few people a month" to most of the floor. The brief's photo-storage argument (print only for people with changes, "a few photos a month") **no longer holds** (inferred). | Changes the cost and the page count. |
| Pay gate | Today a signed notice unblocks a slip for changes made through 087. Counsel's wording asks for a notice and a reason; it does not say the worker's signature must gate pay for direct edits. DTC pays outside the portal (memory `dtc-payroll-outside-portal-oct26`). | **Ask counsel**; my lean is notice only, no new pay gate (section 8, Q4). |

### 1a · Administrator, my view
**Recommendation.** Do not exempt it. Count Administrator edits in the notice and require the reason code from it too. But the notice must say who. If the account is shared, the honest line on paper is "HR (shared account)", and the real fix is a process one: from the switch-on date, manual corrections are made under a named login. That is for Surbhi to tell the customer's HR, not code. **Owner: Surbhi. Blocks:** the wording on the page and the Administrator test.

### 1b · A smaller option worth one question to counsel (the "reimagined" route)
Instead of reading the audit log, **close the side door**: refuse any human write to Employee Checkin except through the 087 punch-fix flow, which already has a reason, an approval and a filer who is not the worker. Then `qualifying_changes` already covers everything and needs almost no change. **It is much smaller to build, and much bigger for HR: it takes away how they fix pay at month end** (**inferred**: 087's flow "has never been used" on either live tenant, per the coordinator, and HR used direct edits in October). Break-glass Administrator edits would still bypass it. Counsel asked for the audit-log notice; I do not know whether door-closing satisfies them. **Recommendation:** ask counsel the one question. Plan on counsel's literal words (audit log plus reason code) until she answers.

## 2 · The backlog problem (open question)

October's 3,322 changes have no recorded reason, and **we cannot make one up honestly.** Choices:

| Option | What it means | My view |
|---|---|---|
| A. Start at switch-on | Reasons required from a stated date. October stays as it is. | **My lean.** Counsel's condition is about the notice going forward. |
| B. Mark the past honestly | Audit view shows "No reason recorded: before 24 Nov 2026" on old rows. A true statement, not an invented reason. Cheap if the list is built to show a blank. | Do this under A. It costs almost nothing and stops a blank looking like a loss. |
| C. One-off disclosure to affected staff | Print October's changes for the people involved. | Only if counsel says so. It is a big print and photo run and a worker would be asked to sign for a month that is already paid. |
| D. One reason for the whole batch ("Oct 2026 regularisation, HR decision") | Honest only if the employer states it. | Employer's statement, not ours. Do not stamp it ourselves. |

**Question for counsel (via Surbhi): does the requirement start at switch-on, or does October need a one-off disclosure?** Blocks: the backlog part only. Does not block the going-forward build.

## 3 · Retention and the paper archive (answers 2 and 3)

**Retention, counsel's rule.** 5 years from the end of the wage month the notice relates to. The employer authorises deletion, Alvora executes, unless a legal hold applies.

**Do I agree that this resolves PRIV-4?** **Partly, and not enough.** PRIV-4 was NOT MET because the HR person who uploaded the photo can delete it (06, proven by running: Frappe's `file.py:999` returns True for any right when the file's owner is the user). A system job at expiry fixes *who is meant to delete*. It does not stop the uploader deleting the photo today. So 088 still needs the guard on that File (06's P2-1), and then the expiry job needs its own controlled way past the guard and past `on_trash`, which today refuses every role including Administrator (06, SEC-5 row). Counsel's rule and 06's fix go together.

**What this needs (smallest version, our own DocType, so new code, not a new DocType):**
- A date on the notice: `retain_until` = last day of the notice's month + 5 years. **There is none today** (06, PRIV-6 row: "no `retain_until` field"). Set when the notice is made, so the clock never has to be worked out later.
- A "legal hold" tick on the notice. A held row is never purged. Who may tick it: the employer's HR Manager or System Manager, and the tick records who and when.
- A daily job that deletes the photo (and the record, if counsel says the record goes too) after `retain_until`, skipping held rows, and writes one log row per run (count, date). Reuse the pattern the joiner purge already uses; I did not re-read it.
- **Timing, my view.** The earliest expiry for any notice made now is the end of Nov 2031. The job cannot do anything for five years. I recommend: build the `retain_until` date and the hold tick now (cheap, and a wrong clock is expensive to fix later), and build the job with a dated YouTrack ticket before the first expiry. **Counsel said "automated workflow" and I do not know whether she meant at switch-on.** Ask.
- **The employer's authorisation** is a standing instruction: contract or data-processing text, not a button. The product only needs to log each run. (Contract work, not ours.)

**Conflict to put to counsel.** 21 Nov (relayed): "at least 5 years from the last entry; 6 to 8 for tax and PF audits". 24 Nov: "5 years from the end of the wage month", then delete. Is 5 years a **minimum or a maximum**? If tax audits need 6 to 8, deleting at 5 destroys evidence. This needs an answer before the job is built, not before the date field. **Also: does the record go at 5 years, or only the photo?** The 088 design keeps the print record "as long as what it proves" (PRIV-6).

**The paper archive.** Counsel: HR must keep the original signed paper for 5 years, because court may ask for the original under the Bharatiya Sakshya Adhiniyam 2023. **This is the employer's offline duty and the product cannot check it.** What we can do, and all of it small:
- One sentence in the "record signature" dialog: "Keep the signed paper for 5 years from the end of {month}. The photo does not replace it."
- The same sentence in the Company switch's description text (the field's `description`, rung: configuration).
- **Not doing:** a paper-tracking field, a shelf-location log, a reminder job. Nobody asked, and we could not verify any of it.

## 4 · The thumb-print question (blocking, for counsel)

**Evidence (proven).**
- Counsel: a signature photo is not biometric under the SPDI Rules 2011. A thumb impression is biometric data under the DPDP Act 2023. Switch the feature on.
- `register_notice.py:10` says the person gives "a signature or a thumb print". The app also says it to HR: `portal.js:7105` ("Signature or thumb print"), `:7221` and `:7234`. I searched all of `alvoraa_portal` for "thumb print", "thumb-print" and "thumbprint" and found those lines, a comment in `punch_fix.py:897` and a test. **Nothing in the code tells the two apart.** One photo per page, whichever was used.
- 01c (our own security engineer, 21 Nov) wrote that the DPDP Act has no special category for biometric data (secondary source, not checked by me). Counsel says the opposite for thumb impressions. I cannot settle that. It matters because **we do not know what counsel means the consequence to be**: consent, a notice at collection, shorter retention, stricter safeguards, or only careful handling.

**Why it blocks.** The people with no app, on the shop floor, are the likeliest to use a thumb. So the group this feature exists for is the group whose photos may be biometric. Counsel's "switch it on" was, as the coordinator notes, given without that in front of her (as far as we can tell).

**Inference that sharpens it.** The in-app privacy notice never reaches a worker with no app (the notice DocType I read about in 01c is the app's). So "disclose in the employee privacy notice" fails for exactly these people. **The disclosure has to be on the paper they sign.** Cheap: one line in the page footer, such as "We photograph this page and keep it for 5 years." **Wording is counsel's, not ours.** I would not print it until counsel has approved the sentence.

**What stays true now (already built).** HR-in-scope-only access, every opening logged, no export (06: SEC-8 PARTIAL, PRIV-3 PARTIAL; 06 found a gap here: the photo's address is readable from the child table, and openings are not all logged). Whether those 06 findings are fixed on the release branch **I did not check.**

**Question to counsel (one, sharp).** "If the signed page we photograph carries a thumb impression, what does the employer, and what does Alvora as processor, have to do beyond what we do for a signature? Is a notice on the page enough, or is consent needed? Is a shorter retention needed for those pages?"

**Do not take** the cheap-looking way out of "signature only" for non-app staff. It excludes the people the feature is for.

## 5 · The "three-layer shield", for 088 only

Counsel's general advice is reasonable and I have no reason to doubt it. For this slice I am applying the ladder.

| Layer | Real engineering here? | My view |
|---|---|---|
| 1. Contract (employer-of-record, no legal advice, custom-configuration indemnity, liability cap) | **No.** Contract work for Surbhi and counsel. | Not ours. The one product link: the screens must not say anything the contract denies (for example, no wording that sounds like legal advice). |
| 2a. Compliant defaults | Partly. The notice switch ships **off**, which is the opposite of a compliant default. | Do not change this now. It is off because the feature does not yet meet counsel's condition. Revisit once the new slice lands: whether it defaults on for new tenants is Surbhi's. |
| 2b. Override-acknowledgement modal naming the client | **No new framework.** 088 has exactly one switch (`alvoraa_print_change_notices` on Company, read in `register_notice.py:54`). | Smallest version: a fuller `description` text on that field saying what the employer takes on when it is off or unused, plus the fact that a change to it is recorded. **I did not check** whether Company keeps Version rows (`track_changes`). If it does, user, name and time are already recorded for free. A general "statutory default" override framework is a new abstraction for a requirement that has one case. **Not proposed.** |
| 2c. In-app checklist for offline duties | One duty: keep the paper. | One sentence in the dialog and the switch description (section 3). No checklist feature. |
| 3. Immutable audit trail | Mostly there. The notice record cannot be edited after an answer and `on_trash` refuses deletion to every role (06 SEC-5). | Do not call it "immutable": a System Manager can still change a notice in Desk (01c allowed it; Version records it). Say "tamper-evident". |

**IP address: flag.** Logging the admin's IP address on every switch change is **new personal data about our customer's staff, collected to protect us**, not to serve them or the workers. It brings its own purpose, retention and notice questions, and it is the kind of thing counsel's own 18 Sep position (do not keep personal data for ever) leans against. **Inferred, not checked:** Frappe's login records may already hold the IP at the time of sign-in, so the IP at the moment of a change could be worked out from the login log plus the timestamp, with nothing new collected. **Recommendation:** do not add an IP column. If counsel insists, the engineer first checks that login-log route. **Owner: Surbhi and counsel.** ⚠ COMPLIANCE.

## 6 · Recommended slice shape

**Not one slice. Two, plus a few small items in the existing one.**

| Where | What | Why |
|---|---|---|
| **088 (existing, small additions)** | `retain_until` and the legal-hold tick on the notice; the File-delete guard (06 P2-1, which PRIV-4 needs anyway); the paper-keeping sentence; the thumb line **if counsel approves wording**. | They all touch the notice record and photo, already in 088. Small. |
| **New slice (I will call it 088c; Surbhi names it)** | The notice reads direct check-in additions and edits, with a reason code on each; Administrator handled (1a); the going-forward start date; "no reason recorded: before the start date" on old rows. Also the door-closing alternative (1b) if counsel prefers it. | It is a new source, a new mandatory field, and a risk to the punch feed. It needs its own design (where does HR pick the code?), security work (Tier 1) and test of "a machine punch is never refused". |
| **088b (already named)** | Statutory forms C, D, IX. Unchanged. | Still waits for layouts. |
| **A purge job slice or ticket, dated** | The expiry job. | Cannot act for five years; build before the first expiry, after counsel answers the min-or-max question. |

**Honest consequence.** 088 on its own never reaches the condition. The release unit is **088 plus 088c**, with 088b still pending for Grace.

## 7 · Should the release of the dormant 088 code be held?

**Yes. I agree with the coordinator's recommendation to hold.**

- The code is not unsafe (switch off, list empty on both live tenants, the coordinator's measurement). That is not the reason.
- **Counsel has said, in writing as relayed, "hold release."** Shipping on the argument that the code is dormant reads badly later. If this is later questioned, "we released it after counsel said not to" is a weak sentence. I would not want to defend it on the front page.
- **088c edits the same file** (`register_notice.py`) and the same query. Releasing first means changing live code that an HR user may already have switched on.
- Still open on the release branch (I read the 06 table, not all of 06): P2-1 (the uploader can delete the photo), P2-2 (the photo-log filter hides 26 of 77 existing rows from HR Manager), P2-3 (a photo address readable from the child table, and not every opening logged). **Whether they are fixed I did not check.**
- **A cost the coordinator should weigh.** The release branch is named `release/088-alv436`, and 06 describes ALV-436 (refusal of markup in reasons) and ALV-435 (the CI secret-scan change) as part of it. Holding 088 may hold those too. **I did not check how entangled they are.** If either is wanted now, it should be split out and released alone.
- A second cost: nothing, for customers. The feature is off and empty.

## 8 · The brief, updated (what changes in `01-product-brief.md`)

- **Job to be done** unchanged. Add: "and I want to be told of any change a person made to my punches, not just the ones filed through the app."
- **Kano:** still Must-be for Grace and DTC (proxy). The evidence is now stronger: counsel's written hold.
- **WOW** unchanged for 088. For 088c the moment is: HR prints a notice and a direct punch edit appears on it with a plain reason ("Machine was down"), no matter how it was made.
- **Success measures (add for 088c):** share of manual punch changes in a month that appear on a notice (baseline: 0 of 3,322 for October; target: all from the start date; instrument: count of audit rows against count of notice rows); share with a reason code (target: 100% from the start date); **machine or phone punches refused by the new rule (target: zero; this is the guard rail).**
- **Thriving lens, new lines.** Transparency: the worker sees direct edits too. Safe if one person per page and reasons come from a fixed list. Inclusiveness: the thumb question (section 4). A worker is not penalised for an edit she did not make.
- **Regulatory read.** (1) DPDP Act 2023 (thumb impression, retention, notice), SPDI Rules 2011 (signature), Bharatiya Sakshya Adhiniyam 2023 (original paper), Code on Wages and state rules (records). (2) Employer's obligations; our product helps discharge them. (3) New: a reason on every manual punch; a date that makes personal data expire; a deletion job; possibly IP addresses. (4) Front-page test: defensible if release is held until counsel's condition is met and thumb pages are disclosed; not defensible if released over written advice.
- **Kill criteria, added.** Stop 088c if the reason rule refuses any machine or phone punch in a test, or if counsel says the notice must also gate pay for direct edits (that makes it a different, larger slice).

## 9 · Subtract pass

**Removed:** a general override-warning framework; a paper-tracking field; an IP column; a "Reason Code" DocType; a purge job for now (only the date and the hold now); a per-employee backlog notice (held back for counsel's say). **Kept:** one fixed-list field, one date, one tick, one sentence, one new slice.

## Open questions

**For counsel (via Surbhi)**
1. **Thumb impressions (blocks switch-on).** What must the employer and Alvora do beyond ordinary handling, and is a footer line enough? Wording of any line on the page is counsel's.
2. Does the requirement start at switch-on, or does October need a one-off disclosure? (Blocks the backlog part only.)
3. Is 5 years a minimum or a maximum (21 Nov said "at least 5, 6 to 8 for tax and PF")? Does the record go at 5 years, or only the photo? Does "automated workflow" mean it must exist at switch-on? (Blocks the purge job, not the date field.)
4. Is a notice plus reason code enough for direct edits, or must the worker's signature also gate pay for them? (Blocks 088c's shape.)
5. Would closing the direct-edit door (1b) meet the requirement?
6. Is IP address logging required, or is the existing login record enough? ⚠ COMPLIANCE

**For Surbhi**
7. Hold the release of 088, and if so split out ALV-436 and ALV-435 if they are wanted now? (My recommendation: hold, and split.)
8. Administrator: named logins for manual corrections from the switch-on date? Whose job is it to tell the customer's HR?
9. Who proposes the fixed list of reason codes, and who approves it? (Not mine to invent as a legal list.)
10. Name for the new slice, and whether the purge job is its own ticket with a dated due date.

## Assumptions
- `[ASSUMPTION]` Counsel's four answers are as relayed. The document is not on letterhead and may be a typed summary.
- `[ASSUMPTION]` A normal month has far fewer manual punch changes than October's 3,322 (a deliberate catch-up). Baseline unknown.
- `[ASSUMPTION]` "Employer authorises" is a standing instruction in the contract, not a per-run approval.
- `[ASSUMPTION]` The notice for direct edits is information, not a new pay gate, until counsel says otherwise.
- `[ASSUMPTION]` Machine and phone punch accounts can be told apart from people reliably. **Not checked.**

## Kill criteria
Covered in section 8. Add: stop the whole 088 line and rethink if counsel says a thumb impression cannot be photographed and stored at all.

## Handoff note
To whoever writes the next spec: **do not start 088c's build until two things are answered: how a hand-made check-in is told from a machine one, and counsel's Q4.** Do not copy the Administrator exclusion into the new source. Test that a machine punch is never refused, and make that test fail first. The expiry job must get past `on_trash` and the File guard by a controlled flag, not by weakening either.
