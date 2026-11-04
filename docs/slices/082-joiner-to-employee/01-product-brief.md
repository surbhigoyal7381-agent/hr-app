---
slice: 082-joiner-to-employee
artifact: 01-product-brief
author: hrms-product-manager
date: 2026-11-04
status: draft
inputs: [079-pre-onboarding/02-functional-spec.md, 079-pre-onboarding/00-decisions.md, hrms/hrms/hr/doctype/employee_onboarding/employee_onboarding.py, alvoraa_portal/.../alvoraa_joiner_submission.py, alvoraa_portal/.../joiner_housekeeping.py, hrms/hrms/alvoraa_employee_documents/setup.py]
---

# 082 · One button: the joiner's own words become their personnel record

**Two inputs this brief should have had are missing.** There is no `01a-ux-opportunities.md`
and no `07-devops-inputs.md` §1 for this slice. I wrote the brief anyway because the change is
one button and three lines of text on a Desk form that HR already uses, and because the
document problem below is live. **Surbhi decides** whether the UX scan is skipped. My
recommendation: skip the UX scan, and record DevOps §1 as nil — no new app, no worker, no job,
no public page, and no extra storage (the files **move**, they are not copied).

---

## 0 · Bad news first, because it changes the size of this slice

**Today, hiring a joiner destroys the identity documents they uploaded, usually within 24
hours.** Confirmed by reading the code:

1. HR links the `Employee` on the submission → `_follow_the_employee` sets the status to
   *Made an employee* (`alvoraa_joiner_submission.py:114`).
2. The nightly job `_erase_the_redundant_copies` picks up every row in that status and calls
   `erase` (`joiner_housekeeping.py:95`).
3. `erase` calls `delete_the_documents`, which deletes every `File` on the row with
   `force=True, delete_permanently=True` — **the bytes, not a flag**
   (`alvoraa_joiner_submission.py:198`).

The comment says "the details are already their personnel record, so the copy is redundant".
That is true of the seven typed fields only if HR retyped them. **It is never true of the
uploaded files, because nothing copies them anywhere.** So the Aadhaar photo the joiner sent
from their phone is gone the next morning, and HR asks for it again on day one.

So this slice is not only about saving HR some typing. It closes a hole that loses the
customer's own records. [Confirmed]

---

## 1 · Job to be done

> "I have read what this person sent. I want it to become their employee record without me
> retyping seven fields and chasing their Aadhaar photo again — but I want to set the joining
> date myself."
> — HR Manager, one-person HR team (DTC shape). Written in the voice of §2 of
> `product-context.md`; **not a recorded quote** `[ASSUMPTION]`.

**Persona:** HR Manager. Primary and nearly sole user of this slice.

- **Employee (the new joiner):** their mobile number, address and emergency contact arrive
  **exactly as they typed them**. No typo on the way to payroll, no second request for the
  document they already sent.
- **CXO:** nothing changes. No new number, no new screen.
- **Line manager:** nothing changes.

---

## 2 · Current pain

I have no stopwatch figure. [Evidence required] The concrete story, from our own help text,
which Surbhi quoted back to us:

> "Read the record and create the Employee by hand, setting the joining date yourself."

So HR has two windows open and retypes seven fields: name, mobile, personal email, current
address, emergency contact name, relation, emergency phone. The mobile number is the one that
matters — it is what payslip and attendance messages go to. **A one-digit typo there is
invisible until somebody says they never got anything.** Then the documents are deleted
overnight (§0).

---

## 3 · Competitive analysis — whole products

| Capability | Frappe HR / ERPNext (standard) | Zoho People | Keka | What we do today |
|---|---|---|---|---|
| Pre-joining form filled by the candidate | No public joiner form; data comes via Job Applicant | Yes, "pre-onboarding"/new-hire portal | Yes, candidate onboarding portal | **Yes** (079) and ours needs no recruitment module |
| One action turns that record into an employee | **Yes** — `make_employee` on `Employee Onboarding` maps the record into an **unsaved** Employee form (read: `employee_onboarding.py:102`) | Yes `[recall — verify]` | Yes `[recall — verify]` | **No. HR retypes.** |
| Uploaded documents follow the person | Yes, via `Employee Document`-style attachments | Yes `[recall — verify]` | Yes `[recall — verify]` | **No. They are deleted.** |
| Joining date | Typed by HR on the Employee form | Often copied from the offer `[recall — verify]` | Copied from the offer `[recall — verify]` | Typed by HR, deliberately |

Evidence labels: the Frappe HR row is **Confirmed** (I read the file). The three competitor
rows are `[recall — verify]` — I did not open their help centres today.

**What we will deliberately NOT do, and why it makes us better:**

1. **We will not copy the joining date from anything.** Every competitor that copies it from an
   offer letter inherits the back-dating trap. Ours makes the human type one date, once, on a
   form they are looking at.
2. **We will not add a recruitment pipeline** (Job Applicant → Job Offer → Employee Onboarding)
   to reach a joiner form. Our buyer is a one-person HR team; three records to create one
   employee is their whole afternoon.
3. **We will not mark a document Verified.** Receipt is a fact; verification is a judgement by
   the verifier role the document type already names.

---

## 3a · Three ways to solve it

| | What it is | Verdict |
|---|---|---|
| **Conventional** | Reuse the Frappe HR chain: create a `Job Applicant` and an `Employee Onboarding` from the submission, submit it, then press *Create Employee*. | **No.** `Employee Onboarding.job_applicant` is a mandatory Link and the doc is submittable with a Project and Tasks behind it. Three records, a submit and a task list to reach one Employee — for an HR team of one. It also drags recruitment into a product that says recruitment is a sibling app, not a module (`product-context.md` §1). |
| **Better (recommended)** | Reuse the *mechanism* Frappe HR uses, not its chain: a button that opens a **new, unsaved Employee form already filled in**, with no date in it. HR types the joining date and presses Save. Then, when HR links the Employee back on the submission — which they already do today — the uploaded files **move** to the Employee and tick its document checklist. | **Yes.** No new DocType, no new settings key, no new screen, no scheduled job. The field map already exists in our code. |
| **Reimagined** | Read the uploaded ID with AI, extract the number and the name, fill the fields. | **No.** A rule and a prefill do this job; AI would add cost, an error mode and an extraction we would have to review. Banned by `no-over-engineering.md` §2 when a well-placed field does it. |
| **Could we not build it at all?** | Honestly asked. We cannot: there is no configuration in Frappe that copies a row of one DocType onto a form of another. The nearest free option is HR downloading each file by hand before the nightly job, and a sticky note about it. That is where we are now, and it is losing records. |

**Cost ladder:** rung 4, new code — about 40 lines across two files that already exist. Rung 1
(already there) was rejected because `Employee Onboarding` needs the recruitment chain above.
Rung 2 (configuration) was rejected because no setting copies fields between DocTypes. Rung 3
(a Client Script alone) was rejected for one reason: the field map lives in Python
(`COLUMN_FOR_TICK`, `alvoraa_joiner_submission.py:51`) and a second copy in JavaScript is two
lists that drift. One small read-only endpoint keeps one map. Rungs 5 and 6 are not needed —
**no new DocType, no new app.**

---

## 4 · Kano class and demand

**Must-be (proxy).** Frappe HR itself ships `make_employee`, and the two Indian mid-market
products we lose deals to both convert a pre-joining record in one action. A buyer who has seen
any of them assumes it. Its absence earns us nothing and produces retyping and a lost document.

The one **Attractive** piece inside it: the joiner's upload arriving as a *Received* tick on the
Employee's document checklist, so the day-one chase list is already shorter. Few mid-market
products connect a candidate's upload to the employee document checklist `[recall — verify]`.

**What would change the class:** if HR tells us they would rather retype than trust a prefill
(it happens, where HR wants to read every field as they type it), this drops to Performance and
the slice shrinks to the document move only. One question to Surbhi's HR contact at DTC answers
it. [Needs validation]

---

## 5 · Persona enhancements through the portal

There is no `01a` to work from, so this table is mine, from the 079 flow.

| Persona | How this makes the module better | The job it serves | In this slice? | Why |
|---|---|---|---|---|
| **HR Manager** | One button fills the Employee form; the documents arrive on the record and tick the checklist | "Make this person an employee without retyping or chasing" | **Yes** | This is the slice |
| **Employee / new joiner** | Their own words reach their record unchanged; their ID is not asked for twice | "I sent it once already" | **Yes**, as a consequence — no screen for them | Free. No new code serves it |
| **Frontline joiner** (helper, driver, agency staff) | The biggest winner: no second trip with a photocopy | "Don't make me come back" | **Yes**, same consequence | Same |
| **Line manager** | Nothing | — | No | No job here |
| **CXO** | Nothing | — | No | A conversion count is a vanity metric |
| **HR Manager, bulk** | Convert twenty joiners at once | Peak-season intake | **No — later** | Nobody has twenty. Buy the evidence first |

---

## 6 · The WOW

**Where:** the `Alvoraa Joiner Submission` form in Desk, straight after HR saves the Employee and
picks it on the submission.

One green line on the form's dashboard:

> **"Everything Rakesh sent is now on his personnel record — 7 details and 3 documents.
> His joiner sign-in is closed."**

And when HR opens that Employee's **Documents** tab, three rows already read **Received**, with
today's date and HR's name against them. Nothing says *Verified* — that is still HR's call.

Counts are real, computed from what moved. Never "all details copied".

---

## 7 · The thin slice

**In — needed to validate this now**

1. A button **"Make their employee record"** on the submission form, shown only when the status
   is *Submitted* and no Employee is linked. It opens a **new, unsaved Employee form**, filled
   with the six mapped fields (the inverse of the existing `COLUMN_FOR_TICK`) plus the full name
   into `first_name`, exactly as Frappe HR's own `make_employee` does. **Nothing is saved by
   this button.**
2. **No date of any kind in the prefill.** Not joining, not birth. HR types the joining date on
   the form in front of them, and Frappe's own mandatory check on `Employee.date_of_joining`
   refuses the save without it. [Needs validation — `erpnext` is not in this worktree, so I
   could not confirm `reqd: 1`. The engineer must confirm it before building; if it is not
   mandatory, the button must not exist in this shape.]
3. One line of guidance on the form, next to the button: **"It will not fill in the joining
   date. Type the real first working day — a date in the past marks them absent for every day
   since."**
4. When HR links the Employee and saves (the step that exists today), **the uploaded files move
   to the Employee**: the `File` rows are re-pointed to the Employee, `is_private` unchanged, and
   each file's matching `Employee Document` row is set to **Received** with `attachment`,
   `received_on` and `received_by`. The document type comes from our own file name,
   `joiner-<row>-<type>.<ext>`. A type with no matching checklist row still gets its file moved
   as a plain attachment — nothing is dropped silently (`product-context.md` §6.5).
5. The green confirmation line of §6, with real counts.

**Before it can ship**

6. 078-SEC-12 replaced by the narrower rule in §8, with a test that **fails** if a date ever
   appears in the prefill payload — asserted on what the button *sends*, not what it draws.
7. One test that hires a joiner with a file and runs the nightly job: the Employee keeps the
   file, the submission keeps nothing.

**Worth doing later** — bulk convert; the joiner's photograph (see OQ-2 if Surbhi says no);
prefilling designation or grade; anything about the staff login.

**Not doing**

- **The staff login stays a separate account.** 079-AC-79 stands: a new account on their real
  address, no joiner role, the joiner account closed and never promoted. This slice does not
  touch it.
- No automatic creation. No endpoint that creates an Employee. HR's own Save is the only
  writer, through Frappe's normal `create` permission.
- No `Job Applicant`, no `Job Offer`, no `Employee Onboarding` record.
- No bank, salary, CTC or statutory field — the joiner is never asked for them (078-PRIV-9) and
  this slice adds nothing.
- No change to the public joiner form, no new settings key, no new DocType, no retention number
  in code, no *Verified* marking, no mobile work.

---

## 8 · What 078-SEC-12 becomes

It cannot be deleted: the reason behind it is a real, paid-for fault (a back-dated joining date
makes Frappe mark the person Absent for every day since, and deleting the rows does not help).
But the rule as written — *no code path anywhere creates an Employee from a submission* — is
wider than its reason. **Recommendation:** replace it with three narrower rules.

| ID | Rule | How it is proven |
|---|---|---|
| **082-SEC-1** | **No code may write `Employee.date_of_joining`, and no value a joiner typed may reach it.** The prefill carries no date field at all. The Employee is created by HR pressing Save on a form it can see. | A test asserts the prefill payload contains no `date_of_joining` and no other `Date` field, and fails if one is added |
| **082-SEC-2** | **Nothing a joiner can reach creates, reads or writes an `Employee`.** The prefill endpoint is HR-only: it checks `read` on the submission and `create` on `Employee` before it returns a single field. | Door tests as a joiner session, a plain staff login and a manager, through `/api/method` — not through the screen |
| **082-SEC-3** | **No `ignore_permissions` on the Employee side.** The file move runs inside HR's own save of the submission, with HR's rights. | Counted against the CI ceiling in `test_portal_security_010` |

082-SEC-1 is the part that keeps the protection real. The old rule protected the joining date by
banning everything; the new one protects the joining date by name.

---

## 9 · Access expectations

The data this slice moves: the six mapped personal fields, the person's name, and the uploaded
identity documents. **No new field is created.**

| Data | Employee (self) | Frontline employee | Line manager | HR Manager | CXO | Outside party |
|---|---|---|---|---|---|---|
| Their six personal details, on the submission | **See own.** Purpose: it is their own record. Already built (079) | Same | **Must not see.** No purpose — the person is not yet on their team | **See, change, move to the Employee.** Purpose: making the personnel record. **Kano-must** | **Must not see** the row; summaries only. No named purpose | **None** |
| The same details, once on the `Employee` | **See own, correct six of them** (existing My Profile rule) | Same | **Must not see** address, personal email or emergency contact. Purpose test fails: attendance and leave approval need none of it | **See and correct** across their company | **Must not see** individually | **None** |
| **Uploaded identity documents** | **See own.** Purpose: "what do you hold about me" | Same | **Must not have. Kano-must — a breach if wrong.** Counsel, 1 Nov 2026: passport and health are not for managers. An Aadhaar photo is the same class | **See and verify**, per the verifier role the document type already names | **Must not see.** No purpose | **None** |
| The prefill payload itself | — | — | **Must not call it** | **May call it**, for their own company's submission | **No** | **No** |

**One conflict to flag for Surbhi:** the `Employee Document` child table. Our own 30 Oct lesson
is that `has_permission` on a child table is always False, so the guard must sit on the parent
`Employee`. If any role can read an `Employee` row it can read that row's documents. **Question:
does any manager-ish role at DTC hold read on `Employee` today?** If yes, moving identity
documents onto `Employee` exposes them to that role, and the move needs a field-level rule
first. Owner: Surbhi, with the security engineer's count. **This blocks the document move, not
the button.**

**The five questions from `data-doors.md`, in plain words:**

1. **Who can read this, and which door stops everyone else?** HR Manager, by role permission on
   `Alvoraa Joiner Submission` and on `Employee` — the same doors as today. The prefill endpoint
   checks both before it returns anything.
2. **Tested as a plain staff login through the API?** It must be: the prefill endpoint and the
   moved files, as a joiner session, a plain staff login and a manager.
3. **Fresh site and real tenant?** Fresh site for the tests; a read-only count at DTC of how
   many logins hold read on `Employee` before the document move ships.
4. **How many bypasses?** Target zero new ones. The file move uses HR's own rights.
5. **What could a manager change or share?** Nothing new on the submission. On the Employee,
   whatever they can already do — which is exactly the question above.

---

## 10 · Regulatory read

1. **Regime:** DPDP 2023 — personal data, and identity documents, which are the sensitive end of
   what we hold.
2. **Whose duty:** our customer's. They are the Data Fiduciary; we supply the tool and the
   settings. This slice helps them discharge "hold the document you verified, and only while you
   need it" — it does not only protect us.
3. **What becomes possible that was not:** an identity document **crosses from the joiner
   retention clock (`alvoraa_joiner_document_days`, 30–60 days) to the employee record**, where
   it lives under the employer's own document retention. That is a real change of clock and it is
   the compliance event in this slice.
   **⚠ COMPLIANCE — needs one line from Surbhi, after counsel.** Decides: whether the files move
   at all. My recommendation, as a product manager and **not a lawyer**: move them. Counsel's 29
   Oct ruling 4 set a short clock for *a candidate's* document; a person who has joined is a
   different purpose, and the `Employee Document` checklist that already ships is the employer's
   lawful home for it. If counsel says no, the slice still stands on the button alone, and HR
   downloads the files — I would then want a warning before the nightly deletion.
4. **Front page test:** yes, we would defend it. "The document you sent us before you joined is
   on your personnel record, and we did not ask you for it twice."

---

## 11 · Thriving-workplace lens

| Lens | Answer |
|---|---|
| **Engagement** | Small but real for the joiner: what they typed is what their record says. Nobody rings them to re-read their own address back. |
| **Collaboration** | The joiner's five minutes on a phone become HR's finished checklist. That is one person's work arriving useful to another, at the moment it matters. |
| **Inclusiveness** | Best for the people usually worst served — the driver or helper who would otherwise make a second trip with a photocopy. Nothing here needs a laptop or English: the joiner's side does not change at all. |
| **Transparency** | It makes visible to HR what the person already sent. It makes nothing visible to a manager — and §9 flags the one place where it could, which is why the document move waits on a count. |

---

## 12 · Success criteria

| Measure | Baseline | Target | Instrumented by |
|---|---|---|---|
| Joiner details retyped by HR | **7 of 7 today** [Confirmed from the flow] | **0 of 7** — the Employee's six fields plus the name match the submission character for character on the first 10 real hires | A read-only comparison script run once at DTC, and a test on a fresh site |
| Uploaded documents surviving the hire | **0** — deleted by the nightly job (§0) | **100%** appear on the Employee, matching rows marked *Received* | The existing log line plus a before/after count at DTC |
| Minutes from "submission read" to "Employee saved" | **baseline unknown — measure first** (stopwatch, 5 hires, with HR) | under 2 minutes | Stopwatch with DTC HR. No analytics code |
| Employees created with a joining date not typed by HR | 0 | **0, and provably impossible** | 082-SEC-1's test on the payload |

No AI in this slice, so no acceptance or override rate. No logins, no page views.

---

## 13 · Risks and the honest downside

| # | Risk | Cheapest way to find out first |
|---|---|---|
| 1 | **`Employee.date_of_joining` turns out not to be mandatory.** Then HR can save with it blank, and the whole protection rests on a sentence on screen. | Read `erpnext/.../employee.json` in the bench. Five minutes, before any code. **Blocks the slice.** |
| 2 | **The document move exposes identity documents to a manager-ish role** (the child-table trap, §9). | A read-only count at DTC of roles holding read on `Employee`. Before the move ships. |
| 3 | **The checklist row does not exist**, because `Employee.employee_documents` is filled from the types that apply to the **grade**, and the prefill sets no grade. Then the file moves but ticks nothing. | Create one Employee with no grade in the local bench and look at the tab. Likely outcome: file moves as a plain attachment, no tick — acceptable, and the green line must then say "3 documents, 1 not on the checklist" rather than claim a tick that is not there. |
| 4 | **HR presses the button, fills the form, then abandons it.** Nothing is saved, no Employee exists, the submission is untouched. Safe by design — worth one test. | The test. |
| 5 | **HR links the wrong Employee.** Then one person's documents move onto another person's record, and the nightly job then erases the submission. **This is the worst outcome in the slice.** It exists today too, but today nothing moves, so the damage was recoverable. | Make the link step show the name it is about to merge into, and confirm. One line, in scope. |
| 6 | **10x:** twenty joiners in a week. Nothing here is per-record expensive; the move is a handful of row updates. Neutral. | — |
| 7 | **Support tickets this would create:** "why is the joining date blank?" — answered by the line of text in §7.3. | — |

---

## Open questions

| # | Question | My recommendation if you want me to keep moving | Owner | Blocks |
|---|---|---|---|---|
| **OQ-1** | **Must know.** May the uploaded identity documents move to the Employee record, leaving the 30-day joiner clock for the employer's own document retention? (§10.3) | **Yes, move them.** A person who joined is a different purpose from a candidate | Surbhi, after counsel | The document half of the slice. The button can ship without it |
| **OQ-2** | **Must know.** Does any role at DTC other than HR hold read on `Employee`? (§9) | Assume yes until counted, and hold the document move until the count is in | Surbhi + security engineer | The document move |
| **OQ-3** | **Should know.** The joiner's photograph (`__photo__`) is deleted by the same nightly job. Does it move to the employee photo surface in this slice? | **Yes, in the same move** — it is the same loss. But 078's photo surface has its own access log, so the security engineer confirms the rules first | Surbhi | One line of the move |
| **OQ-4** | **Should know.** Is `01a-ux-opportunities.md` skipped for this slice? | **Skip it.** One Desk button, three lines of copy | Surbhi | The next gate |
| **OQ-5** | **Nice to know.** Would DTC's HR rather retype than trust a prefill? (§4) | Assume they want the prefill | Surbhi's DTC contact | Nothing. It would reclassify the Kano |

## Assumptions

- `[ASSUMPTION]` `Employee.date_of_joining` is `reqd: 1` in ERPNext. **Not verified** — `erpnext`
  is not checked out in this worktree. Risk 1.
- `[ASSUMPTION]` The joiner's full name can go into `Employee.first_name` whole, as Frappe HR's
  own `make_employee` does, and HR splits it on the form if they want. Splitting a name in code
  is a guess, and we do not guess names (`product-context.md` §6.5).
- `[ASSUMPTION]` The file-name convention `joiner-<row>-<type>.<ext>` is reliable enough to
  recover the document type — it is our own naming, read by `_sent_types` already.
- `[ASSUMPTION]` The three competitor rows in §3 are current. Labelled `[recall — verify]`.
- `[ASSUMPTION]` The job-to-be-done sentence in §1 is written in HR's voice, not quoted.

## Kill criteria

- **Counsel says the documents may not move** *and* DTC's HR says they prefer to retype. Then
  there is no slice — only a warning before the nightly deletion, which is a two-line change to
  an existing job, not a slice.
- **`date_of_joining` is not mandatory on `Employee`.** Then a prefill button makes a silent
  back-date easier to produce than it is today, and 078-SEC-12 was right as written. Stop.
- **The prefill cannot be done without writing an Employee server-side.** If the only workable
  shape is an endpoint that creates the record, stop and come back: HR's own Save being the only
  writer is what makes this safe.

## Handoff note

To the UX designer, if OQ-4 says you run: there is **no new screen**. The whole design is a
button label, one line of guidance about the joining date, a confirmation line with real counts,
and a confirm step on the link that names the person. Resist adding a wizard.

To the security engineer: the two things worth your time are 082-SEC-2 (the prefill endpoint as
three different logins, through `/api/method`) and OQ-2 (who holds read on `Employee` at DTC,
counted read-only). The child-table trap of 30 Oct applies — guard the parent.

To the engineer: **verify Risk 1 before anything else.** The slice depends on it.

## Subtract pass

What I removed on this pass, having written a longer version first:

- A new "Converted on" / "Converted by" stamp field on the submission. Frappe's own `Version`
  and the existing `status` already answer who linked the Employee and when.
- A "review what will be copied" preview dialog before the button. The unsaved Employee form
  **is** the preview — HR looks at every field before pressing Save.
- A bulk "convert selected" action. Nobody has twenty joiners.
- Prefilling designation, department, grade and company. Three of the four are HR's own decision
  and not on the submission at all; prefilling company from the submission would be a guess.
- A new settings key for "move documents on hire, yes or no". One behaviour, decided once by
  OQ-1. A switch is a second thing to test and support.
- A notification to the joiner saying "you are now an employee". Their staff login arriving is
  that message, and it belongs to 079.
