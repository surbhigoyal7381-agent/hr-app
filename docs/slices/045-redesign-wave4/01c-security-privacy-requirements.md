---
slice: 045-redesign-wave4
artifact: 01c-security-privacy-requirements
author: hrms-security-privacy-engineer
date: 2026-09-24
revision: 1
status: draft — written after the functional spec, which is revision 1 by construction. Carries one P1 that must be settled before the two leave lists are built
inputs: [02-functional-spec.md (045, revision 1), ../043-redesign-wave3/01c-security-privacy-requirements.md, ../042-redesign-wave2/01c-security-privacy-requirements.md, ../034-redesign-wave1/01c-security-privacy-requirements.md revision 4, ../034-redesign-wave1/00g-decision-register.md (W1D-01 to W1D-23), ../009-ess-portal-redesign/01b-ux-design.md, .claude/context/security-compliance-baseline.md, .claude/context/compliance-feature-map.md, .claude/context/nfr-budget.md, the code at slice/045-redesign-wave4 6130045 read in this worktree on 2026-09-24]
---

# Wave 4 — Growth, Team and People: security and privacy requirements

**Numbering is per slice.** This slice runs `SEC-1` to `SEC-19` and `PRIV-1` to `PRIV-13`.
Cite them as **"045 SEC-4"**. Decisions are `W1D-nn` from
`../034-redesign-wave1/00g-decision-register.md`; the analyst's are `045 D-n` from `02` §21.

**Every claim carries a label.** *Verified in code* means I opened the file and read the
line, and it is named. *Inference* says what it rests on. `[ASSUMPTION]` is a working guess.
*Unknown* means I could not check it, and says what access I would need. Worries are in
their own list and are not requirements.

**I did not touch production, a bench or a live tenant.** Every line number below was read
in this worktree.

> **Written against `02` revision 1, then checked against revision 2 before committing.**
> While I was working, the analyst's **revision 2** landed **uncommitted** in this worktree,
> carrying two decisions Surbhi took on **25 September 2026**: **peer feedback is out of
> Wave 4 entirely** (ALV-116), and **the Team screen separates "Your team" from "You cover"**,
> which **closes `045 D-1`**. I read it and did not stage it — it is the analyst's work to
> commit. **Four things below are marked "revision 2" where they changed**: my **Q1 is
> answered** (PRIV-2), **Finding 4's peer-feedback half is moot and its doctype half is
> sharper**, **PRIV-2's rule is narrowed to match the decided one**, and there is **one new
> requirement, SEC-18**, for a surface revision 2 creates.

**What makes Wave 4 different from Waves 2 and 3.** Time and Pay were about one person's own
most sensitive record. **Wave 4 is the first wave whose whole point is one person looking at
another** — a manager reading a team, an HR person reading a store, a colleague looking
somebody up. Every requirement here is written from that fact. The failure mode is not a
stolen payslip; it is a screen that quietly shows fifty people something built to show
nineteen.

---

## Bad news first

**Two things, and the second is the one I would fix first.**

**1 · The `manager` key is real, and it is the smaller of the two.** *Verified in code:*
`hr_api.py:530` returns `"manager": emp`, where `emp` is `_get_employee()`'s whole row
(`hr_api.py:158-166`: `branch`, `reports_to`, `gender`, `date_of_joining`, `date_of_birth`,
`cell_number` alongside the six the screen needs). It goes **to the caller's own browser,
about the caller**. That is over-disclosure into a client surface, not a leak of somebody
else's data, and I am rating it honestly rather than loudly — **P2**. SEC-3 fixes it, and the
analyst's fixture rule is right; I am extending it.

**2 · The leave type is the P1, and the reason is not the mechanism — it is the
population.** *Verified in code:* `on_leave_today` (`hr_api.py:496-504`) and `month_leaves`
(`hr_api.py:517-525`) both select `leave_type` for everyone in `team_ids`. *Verified in
code:* `team_ids` comes from `team`, and `team` for an HR caller is
**`permitted_employee_filters()`'s HR scope, capped at 50** (`hr_api.py:406-437`), not their
direct reports. **W1D-20 changed who receives a health-adjacent field while deciding
something else entirely**, and `01b` §14 rule 9 and Wave 3 `02` §5 both already forbid it in
writing.

*The scenario, written the way a finding has to be written:* **Priya, store HR, no direct
reports, signed in, opens `#team`. `get_manager_dashboard` returns up to 50 named people in
her store and, for each of them who is off today or this month, the leave type — "Sick
Leave" — for people she does not manage and whose leave she does not approve.**

That is a purpose-limitation failure under DPDP: the type was collected to administer leave
and is being rendered to answer "who is around today". **PRIV-2 requires it dropped from both
reads.**

> **Revision 2 — this is now decided, and decided well.** `045 D-1` is **closed**. Surbhi's
> decision of 25 September 2026 splits the Team screen into "Your team" and "You cover", and
> the leave type survives **only on the approval row of a person's own direct report** and
> **nowhere else, for anybody** (`045 AC-76`). **That is narrower than my fail-closed default
> and narrower than my recommendation**, and I endorse it without reservation: an HR person in
> the "You cover" section sees no leave type at all.
>
> **PRIV-2 is narrowed to match it** — the rule is now `reports_to`-based, not
> `leave_approver`-based. **That creates one edge case somebody should look at**, and it is a
> should-know not a blocker: *an HR person who is the named `leave_approver` for somebody who
> is not their direct report must now decide that request without seeing the leave type.* Q4a.

**And it is a release note either way, which the decision already says.** HR lose something
they have had for months — tell them. What must not happen is that a narrowing this size is
simply absorbed.

**No P0 in this slice.** No cross-tenant path, no secret in a log, no personal data reaching
a model, and no live exposure of one person's data to another that I could demonstrate from
the code alone. **One candidate P0 I could not resolve is Finding 4 below** — and the reason
I could not is itself the finding.

---

## The four handed-over findings, assessed

### Finding 1 — `hr_api.py:530` returns the whole Employee row · **P2, fix in Wave 4**

*Verified in code.* Line 530, `"manager": emp`; `_get_employee` at `:158-166`.

| | |
|---|---|
| **Actor, state, path, data** | Any caller with an Active Employee record, signed in, loading `#team` → `get_manager_dashboard` → their **own** `date_of_birth`, `gender`, `cell_number`, `branch`, `reports_to`, `date_of_joining` in the JSON |
| **Blast radius** | **One person, and that person is the caller.** The bottom of the scale |
| **Why it still matters** | It is not the screen; it is everywhere the response goes afterwards — a browser cache on a shared floor phone, a screenshot in a WhatsApp group, a support ticket with the network tab pasted in, a proxy log. `date_of_birth` + `gender` + `cell_number` is a useful triple to somebody impersonating a person to a helpdesk |
| **Rank** | **P2 — fix before release.** The same shape and the same rank as Wave 3's `get_payslips` (`043 SEC-3`), and consistency matters more than drama |
| **Verdict** | **Fix it in Wave 4, as specified.** It is one hunk, it is on a screen this wave opens anyway, and leaving it while renaming the endpoint around it is how declared debt becomes permanent |

**I endorse the analyst's fixture rule and extend it three ways** (SEC-3):

1. The fixture populates **all six** forbidden fields. An empty fixture passes while the leak
   survives — Wave 3's exact near-miss.
2. The assertion is on the **serialised payload, searched recursively**, not on the `manager`
   key. A key-set assertion on one key passes if the same row is later added under a second
   key, which is precisely what a rename-and-re-dress commit does.
3. The replacement is **`frame_api.ME_FIELDS`** (*verified in code*, `frame_api.py:44` — the
   six keys exactly), reused as the helper, **not a hand-written dict in a second module**.
   Two copies of one key list drift, and this codebase has already proved it (SEC-6).

### Finding 2 — the leave type, widened by W1D-20 · **was P1; decided 25 Sep, now a build requirement**

Assessed in "Bad news" above. Requirement **PRIV-2**. **Revision 2 closes `045 D-1`**, so this
is no longer waiting on anybody: it is a thing to build and a thing to test. **The rank does
not drop** — an unbuilt decision is still a leak — but it is no longer a question. Three things
to add, and the first two survive revision 2 unchanged.

- **The same payload also carries `description`.** *Verified in code:* `hr_api.py:508-516`,
  the `pending_approvals` read selects `leave_type` **and `description`** — the employee's own
  free-text reason for the leave — for every Leave Application where `leave_approver == user`.
  **Nobody named this, and revision 2 still does not:** `AC-76` names "Sick Leave" and "Casual
  Leave" and says nothing about the reason text. **PRIV-2 names both**, because a decision
  taken about `leave_type` will otherwise be applied to a field nobody mentioned — in whichever
  direction happens to be easiest. Under the decided rule the reason follows the type: it
  survives **only** on an own-direct-report approval row.
- **Drop it at the read, not at the renderer.** A field filtered out in JavaScript is still in
  the response, still in the browser cache and still in the proxy log. The column comes out of
  the SQL and out of the `fields` list.
- **This is narrower than today, so it needs its own commit and its own release-note line.**
  `02` release gate 3 already says so; I am making it a requirement.

### Finding 3 — the raw SQL in `on_leave_today` · **not an injection finding today; P2 as a shape**

*Verified in code*, `hr_api.py:495-504`. The comment on line 495 says *".format() only
inserts `%s` placeholders — no user data in the format string; safe."* **I read it, and the
comment is correct.** `",".join(["%s"] * len(team_ids))` uses `team_ids` for its **length
only**; every value travels in the parameter tuple. **There is no injection here today.**

**The risk is the shape, not the instance** — the same argument that made Wave 3's `SEC-5`
worth writing. A `.format()` on a SQL string is safe exactly as long as it has one careful
author. The next person who needs a second column or an extra condition will add it by
formatting, because that is what the line in front of them teaches.

**And there are two of them, not one.** *Verified in code:* the identical shape is at
`hr_api.py:1172-1181`, inside **`get_team_scorecard`** (`:1098`) — which `02` §1 lists as a
function Wave 4 **extends**. The analyst named only `:496-504`. **SEC-5 covers both**, and
AC-14's static check must be written against the module, not against one line number.

| | |
|---|---|
| **As injection** | **P4 — note it.** No user data reaches the format string in either instance |
| **As a shape** | **P2.** One careful author each; Wave 4 gives both a second |
| **As performance** | DevOps's, in `07`. The ×5 slope `nfr-budget.md` now bans |
| **Verdict** | **There is no trade to make here.** The subquery AC-14 already requires removes the `IN (...)`, the `.format()` and the slope in one change. SEC-5 additionally stops the shape being reintroduced |

### Finding 4 — `Employee Performance Feedback` · **no-go agreed, and it is bigger than peer feedback**

*Verified in code*,
`hrms/hrms/hr/doctype/employee_performance_feedback/employee_performance_feedback.json`.
The `Employee` role row is:

> `read, write, create, submit, cancel, email, export, print, report, share` — **and no
> row-scope of any kind.**

The analyst named eight of those. There are **ten**: `report` and `email` are also on, so the
desk's report builder and "send by email" both work on it. *Verified in code*,
`hrms/hrms/hooks.py:150-158`: the `permission_query_conditions` map holds nine doctypes and
**this is not one of them**; `has_permission` at `:162-169` holds six and **this is not one of
them either**.

**My verdict on that permission shape: it is wrong, and it is wrong in the worst way — wrong
by default, silently, on a doctype about people's performance.** I agree with the no-go,
unconditionally. Extending it would give every employee in the tenant `export` on every
colleague's feedback, and the control would be "nobody thought to look".

**But the reason to escalate is not peer feedback. It is that we already write to it.**
*Verified in code*, `hrms/hrms/alvoraa_org_structure/dotted_line.py:125-136`:
`request_dotted_line_feedback` **inserts `Employee Performance Feedback` records with
`ignore_permissions=True`** whenever a manager puts a score on an appraisal, on any tenant
where the `org_structure` feature is on (`dotted_line.py:26-34`).

*The scenario:* **Rahul, a sales executive holding the `Employee` role, signed in with a
desk-capable account on a tenant with `org_structure` on, opens
`/app/employee-performance-feedback` — or calls `frappe.client.get_list` — and receives every
feedback record in the tenant: who it is about, who wrote it, the `feedback` free text and
`total_score`. `export` and `report` let him take the lot as a spreadsheet.**

**Blast radius: the whole tenant.** One step below the top of the scale.

**Unknown — and this is the finding.** Whether that scenario is live turns on two things I
could not check:

1. **Are ordinary employee logins on `dtc` and `aahr` System Users?** *Verified in code:*
   `tenant_setup.py:41` creates users as `"System User"`, but that path provisions a tenant's
   admin and HR users; `demo_setup.py:43` creates `"Website User"`. I could not establish
   which shape an ordinary employee has.
2. **Has `module_access` written Custom DocPerm rows that override this?** *Verified in code*,
   `module_access.py:245-263`: once **any** Custom DocPerm row exists for a doctype, its
   standard permissions are ignored entirely — so a tenant's module selection may already have
   closed this, or may never have touched it.

**Access I would need:** a read of `User.user_type` and `Has Role` for one ordinary employee
on each client tenant, `frappe.db.count("Employee Performance Feedback")`, and
`frappe.get_all("Custom DocPerm", {"parent": "Employee Performance Feedback"})`. **A dev-stack
copy of a tenant answers all three.** I did not probe production and will not.

| Rank | Condition |
|---|---|
| **P1 — blocks the release** | If employees are System Users **and** `org_structure` is on **and** no Custom DocPerm overrides it |
| **P3 — after release** | If any one of those three is false |

**What I require now** (SEC-17): **the check is run before Wave 4 ships**, on a dev copy, and
the answer is written down. It is fifteen minutes and it decides between P1 and P3. Wave 4
does not touch this doctype and does not have to wait for the *fix* — but it must not be the
thing that surfaced the question and then put it back in the drawer.

**And on peer feedback itself:** no-go, agreed — **and revision 2 went further than a no-go.**
Surbhi removed it from Wave 4 entirely on 25 September; it becomes an HR-run process with a
stated purpose and its own specification (**ALV-116**). **I think that is the better answer
than the one I was going to give**, and for a privacy reason nobody has said out loud yet: a
feedback *programme* that HR starts, for a stated purpose, with a beginning and an end, **has
a purpose tag and a retention answer by construction**. An always-available "give feedback"
button has neither, and would have had to grow both.

**When ALV-116 is specified, three conditions, and I will not soften them** — **a DocType of
our own; its `permission_query_conditions` and `has_permission` written in the same commit as
the DocType, not as a follow-up; and its own `01c`**, because it is still the only thing in
this programme that creates a new personal record about one person written by another.

**And one consequence of the removal that cuts the other way, so it is said plainly.** Peer
feedback was going to be the slice that forced somebody to look at this doctype's permissions.
**It is gone, and the permission shape is still there, on a doctype we already write to.**
That is why SEC-17 and R3 are not optional and why they carry dates. **A finding that loses
the slice it was attached to is a finding that quietly stops existing**, and this is the moment
that would happen.

---

## Threat model — four questions, answered for this slice

**1 · Who would want this data, and what is the cheapest way to get it?**

Not an outsider. For **Growth** the wanted thing is a colleague's rating before it is
released, or a manager's private note about them, and the cheapest path is a list endpoint
that forgot to exclude a column — exactly what appendix D recorded on 14 September. For
**Team** the wanted thing is why somebody is off, and it is being handed over today (PRIV-2).
For **People** the wanted thing is a colleague's phone number, and the defence is that
`staff_api.ROW_KEYS` (*verified in code*, `staff_api.py:63`) is five keys and holds no contact
field at all.

The second and more likely attacker is the **over-scoped HR person**: entitled to a store,
handed a payload built for a manager of nineteen.

**2 · What is the blast radius of one mistake?**

| Scale | What sits here in Wave 4 |
|---|---|
| **Cross-tenant** | Nothing — provided no module-level cache and no module-level dictionary (SEC-13). Wave 4 adds two new modules, which is when that gets introduced |
| **Whole tenant** | `Employee Performance Feedback` (Finding 4), **which Wave 4 does not touch and did surface**; and `permitted_employee_filters()` if it ever returned `{}` (SEC-6) |
| **One HR scope, up to 50 people** | The leave type and the leave reason (PRIV-2). **The top of the scale for anything Wave 4 actually builds** |
| **One manager's line** | The person sheet's contact fields (PRIV-3); a team payload carrying an unreleased rating (PRIV-5) |
| **One person, themselves** | The `manager` key (SEC-3) |

**3 · What does this make possible that was impossible before?**

**No new collection.** Everything Wave 4 renders already exists. Three things are new as
*visibility*, and one is the one to watch: **the trajectory chip puts a named person on a
manager's list, computed with no human involved.** It is not a rating and it moves no money,
but it decides whose name a manager reads first, and that reliably shapes a conversation.
`02` §19.4 refuses a ranking and a per-person attention history in writing; **PRIV-9 turns
both refusals into tests**, because a refusal in prose survives exactly until the next person
who has not read it.

**4 · How would we find out?**

**We would not, and that is unchanged and still the biggest gap in the programme.** Refusals
are logged through `access.log_refusal`; **successful over-reads are not logged at all.** If
the leave type stays and somebody uses the Team screen to work out who is having treatment,
there is no record that they looked. Wave 1 accepted this with dates (R3: a logging first step
by **2026-10-15**, a detection slice by **2026-11-30**). **Wave 4 is the wave that makes it
bite**, because it is the first wave built for one person to look at another. It is carried
below as R1, and I am not re-accepting it quietly.

**One more, added this week, and it belongs here.** A permission helper was found **failing
open** — a caller with no employee id and `is_hr=True` was handed every active person in the
site's companies — and a count that capped at 1,000 names stopped being right above that
without failing or warning. **Both are the same shape: a control that is silent when it is
wrong.** *Verified in code*, both are now closed in this worktree and the code says why:
`home_api.py:318-326` (`_filter_list` keeps `permitted_employee_filters()`'s fail-closed
`["name", "in", []]` instead of letting a `dict.update()` overwrite it) and `home_api.py:360-369`
(`_presence_counts` counts in the database and is **never capped**).

**Where else could the same thing be hiding? I looked, and found one.** **`hr_api.py:410`
rebuilds `_filter_list` by hand** — `[[f, c[0], c[1]] for f, c in permitted_employee_filters(user).items()]` —
a second implementation of the helper that was just fixed. It is correct today. It is also the
copy that will not be fixed next time. SEC-6.

---

## Data inventory

| Data | Where in Wave 4 | Sensitivity class | Purpose | Kept | Who may see it |
|---|---|---|---|---|---|
| Caller's `employee`, `employee_name`, `designation`, `department`, `image`, `company` | the `me` block on all three screens | Personal, low | Show who is signed in | Not stored | The caller |
| Caller's `date_of_birth`, `gender`, `cell_number`, `date_of_joining`, `reports_to`, `branch` | **Never in any Wave 4 payload** (SEC-3) | Personal, higher | — | — | — |
| A colleague's name, designation, department, image | Team cards, staff list, search, person sheet | Internal | Work together | Unchanged | Inside the caller's scope only |
| A colleague's `cell_number`, `personal_email`, `company_email`, `gender` | **Never** (PRIV-3), until `045 D-7` says otherwise with consent | Personal, and the thing people most object to sharing | Contact | Unchanged | Nobody, through the portal |
| A colleague's **leave type** | **PRIV-2 — out of both leave reads** | **Sensitive** — can imply a medical or family circumstance | Leave administration | Unchanged | **Nobody but the person, and the named approver of that one request** |
| A colleague's leave **reason** (`description`) | the approval row only | **Sensitive** | Decide that one request | Unchanged | **The named `leave_approver` of that application, and nobody else** |
| Own self-review free text | Growth wizard | **Sensitive** — a person writing about themselves puts health, family and grievance content in a box nobody asked for | Performance management | **Employment + 6 months, then erased** (counsel, 18 Sep 2026) | The employee; their manager once sent |
| `manager_internal_notes`, `potential_rating`, unreleased `overall_rating` | **Never in an employee-facing payload** (PRIV-5) | **Sensitive** | Performance management | As above | The manager and HR, on the desk |
| Goal progress, evidence, `trajectory` | Growth and Team | Internal, **and sensitive in aggregate** — a trajectory is a judgement about a person | Performance management | As above | The person, and their own line |
| Upward feedback about a manager | Growth | **Sensitive**, and the author must stay hidden | Management development | As above | Totals only, minimum three responses |
| Open action items | Growth | Internal | Performance management | As above | The person and their manager |
| `date_of_joining` ("New this month") | Team, People | Internal | Say hello | Unchanged | Inside the caller's scope |

**Nothing new is collected and nothing new is stored.** *Inference*, resting on `02` §9 and
§15 and on my own read of the endpoints this wave reuses. **`045 D-7` is the only path to a
new field, and it is a consent flag** — which collects nothing about a person beyond their own
choice, and is the correct shape if the answer is yes.

---

## Who must NOT see what

| Who | Must not see |
|---|---|
| **Any colleague, any manager, any HR person, on the Team or People screens** | Why somebody is away — the leave type or the reason. **One exception, and only one:** the approval row for the caller's **own direct report**, per `045 D-1` as closed on 25 Sep 2026. **An HR caller's "You cover" section carries no leave type at all** (PRIV-2, `045 AC-76`) |
| Any employee | Another person's draft self-review, at any stage, including their own manager's before it is sent |
| **Any employee, about themselves** | `manager_internal_notes`, `potential_rating`, or `overall_rating` before release (PRIV-5) |
| Anyone at all | Who wrote a piece of upward feedback, or any upward-feedback detail below three responses (PRIV-6) |
| Anyone at all | A ranking, a league table, an ordering by performance, a "most improved", or a stored history of who was on "needs attention" (PRIV-9) |
| A manager or an HR person | Anyone outside `permitted_employee_filters()`'s scope or their own `reports_to` line — in the list, in a count, in a search, in "New this month" or in "Needs attention" (SEC-6) |
| Anyone, through the portal | Another person's phone number, personal email or employee number (PRIV-3) |
| Anyone | A leaver. `status = "Active"` is on the query, not applied afterwards (SEC-12) |
| A caller with no Employee record | Everything, by explicit refusal rather than by an absent filter (SEC-14) |
| A tenant without the `staff_list` switch | The People screen and `get_staff_list`, refused on the server in wording identical to a not-allowed refusal (SEC-2) |
| Guest | Anything |
| A log, an error message, a notification body or a push preview | Any review content, any rating, any manager note, any leave type, any goal figure (PRIV-7) |

---

## Obligations engaged, with the date each was last verified

**None stale.** The baseline entries relied on here were verified **24 Aug 2026** (31 days
old) and **6 Sep 2026** (§3a). Counsel's note is dated **18 Sep 2026** and is a set of binding
retention periods plus fourteen still-open questions.

**I am not a lawyer.** Nothing here is legal advice. Where the answer turns on law I have
written a question for counsel instead of a requirement.

| Obligation | Source, and date verified | What Wave 4 must do | Requirement |
|---|---|---|---|
| **DPDP s.8 — minimisation** | baseline §2, §5 · 24 Aug 2026 | Fixed payload key lists on every new endpoint; the six-key `me` block; five keys on a staff row | SEC-3, SEC-4 |
| **DPDP — purpose limitation** | baseline §2 · 24 Aug 2026 | **The leave type was collected to administer leave. "Who is around today" is a different purpose** | **PRIV-2** |
| **DPDP s.11 — a person's right to information about their own data** | baseline §2 · 24 Aug 2026 | Growth **is** the access path to a person's own review for 400 people with no desk login. This slice discharges an obligation rather than creating a risk | PRIV-8 |
| **DPDP s.8(7) / Rule 8 — storage limitation** | counsel's note, 18 Sep 2026 | **Performance records: employment + 6 months, then erased.** Wave 4 creates no second copy and no derived store, so the period applies unchanged — **and I could find no job enforcing it** | PRIV-10, R4 |
| **DPDP — grievance redressal** | baseline §2 · 24 Aug 2026; counsel records the product route as *"Not built. Handled by hand"* | **Wave 4 must not draw a "contest this" control that leads nowhere** | PRIV-11 |
| **GDPR Art 22 — automated decisions** | baseline §4 · 24 Aug 2026. ⚠ **Applicability still unconfirmed** — the founder has not said whether we process EU data | The trajectory chip is **not** Art 22: it decides nothing and moves nothing. It is close enough that PRIV-9 pins the boundary rather than trusting it | PRIV-9 |
| **GDPR Art 15 / DPDP s.11 — access** | baseline §4 · 24 Aug 2026 | The employee sees the same chip, with the same words, that the manager sees. **A manager must not read a judgement about a person that the person cannot see** | PRIV-9 |
| **CERT-In — log content** | baseline §3 · 24 Aug 2026; residency gap 6 Sep 2026 | No review content, rating, note or leave type in any log | PRIV-7 |
| **OWASP ASVS 5.0 L2 — access control** | baseline §5 · 24 Aug 2026 | Scope checked **before** any `ignore_permissions`, order proved by test, not presence | SEC-10 |
| **ISO 27001 A.8.11 data masking / A.8.12 DLP** | baseline §5 · 24 Aug 2026 | Fixed key lists are this product's masking mechanism until feature-map A1 exists | SEC-4 |
| **EU AI Act** | baseline §4 · 24 Aug 2026 | **Not engaged.** Nothing in this slice is AI-shaped; the Article 5 prohibitions are not approached | PRIV-13 |

---

## Abuse cases

| # | Actor, state and path | What must happen |
|---|---|---|
| **A1** | **Priya**, store HR with no reports, signed in, opens `#team` | She sees her store. **She does not see why anybody is away** (PRIV-2). The screen says "Your HR scope", not "your team" |
| **A2** | **Sandeep**, a manager, signed in, taps a report on the person sheet | Name, designation, department, branch, image. **No `cell_number`, no `personal_email`, no `gender`** — *verified in code*, `get_employee_scorecard:932-937` and `get_employee_detail_for_manager:1234-1239` return all three today (PRIV-3) |
| **A3** | **Sandeep** calls the person-sheet endpoint with an employee id from outside his line, taken from a search result | Refused, with a sentence, in wording **identical** to "that person does not exist" — so the answer cannot be used to enumerate the tenant (SEC-8) |
| **A4** | **An employee with no `reports_to`** is opened by whoever `get_hr_manager_employee()` happens to return | *Verified in code:* `alvoraa_goals/permissions.py:64-71` — `get_effective_manager` **falls back to the first active HR Manager** when `reports_to` is empty, and `hr_api.py:923` uses that as the **access gate** on `get_employee_scorecard`. So an employee with no manager is gated to an arbitrary person. **SEC-7:** the person sheet's gate must be `permitted_employee_filters()` **or** an explicit `reports_to` match — never a fallback that invents a manager |
| **A5** | **Rahul**, a plain employee, calls `get_manager_dashboard` by hand | Refused, or an empty scope by explicit refusal. `permitted_employee_filters()` returns `NO_EMPLOYEES` for him (*verified in code*, `access.py:259-269`) — **and the caller must not then rebuild the filters in a way that loses it** (SEC-6) |
| **A6** | **A tester** patches `has_feature` to `True` so the `staff_list` gate test passes | **Forbidden.** The gate tests call the real function on a tenant whose `features` list genuinely lacks the key. Wave 3's `043 SEC-2` rule, restated because Wave 4 has a gate too (SEC-2) |
| **A7** | **A bulk import** lands 400 employees with no `reports_to` | Nobody's Team screen becomes the tenant. This is the leak W1D-20 closed and Wave 4 rebuilds on top of (SEC-6, `045 AC-71`) |
| **A8** | **A leaver** with an enabled login opens Growth | Their own record until the login stops. They appear in **nobody's** team list, staff list, search result, "New this month" or "Needs attention" (SEC-12) |
| **A9** | **An employee** calls a Growth read with a colleague's appraisal name | Refused identically to a name that does not exist. *Verified in code*, `performance_api.submit_employee_review:4419` already checks `ap.employee != me` on the write; **the reads must be checked the same way and tested the same way** (SEC-9) |
| **A10** | **An employee** reads their own Growth payload looking for their unreleased rating | Absent. **And absent because the query did not select it**, not because Python dropped it afterwards — *verified in code*, `hr_api.py:1174-1181` reads `overall_rating` for the whole team and filters on `review_status` in Python at `:1183-1185` (PRIV-5) |
| **A11** | **A curious manager** asks for their team sorted by how far behind they are | No such payload, no such ordering, no such export. "Needs attention" is a list of **goals behind their own dates**, in the order the goals appear (PRIV-9) |
| **A12** | **A developer** adds a third presence calculation, or a second `_filter_list` | Must fail a test rather than a review. There is already one hand-rolled copy at `hr_api.py:410` (SEC-6) |
| **A13** | **A developer** adds a column to `on_leave_today` by extending the `.format()` | The function no longer exists in that shape. No `.format()`, f-string or `%` concatenation on SQL in any Wave 4 module (SEC-5) |
| **A14** | **A support engineer** reads a portal error report from the Growth screen | A time and a short reference matching an Error Log entry. **No review text, no rating, no employee name** (PRIV-7) |
| **A15** | **Anyone** whose Employee record has a designation of `<img src=x onerror=alert(1)>` appears in a team list, a staff list or a search result | Rendered as text. Wave 1's `esc()` discipline extended to Wave 4's three new panels, and tested, not assumed (SEC-16) |
| **A16** | **Rahul**, holding the `Employee` role, opens `/app/employee-performance-feedback` | **Unknown today. SEC-17 requires the answer before this wave ships** (Finding 4) |

---

## Requirements

### Security

| ID | Requirement | How it is tested |
|---|---|---|
| **SEC-1** | **Every whitelisted function in `growth_api.py` and `team_api.py` is safe on its own, from the commit that adds it**, with its Guest-refused, wrong-persona and out-of-scope cases in the same commit | A registry test enumerating the functions **from the module**, not from a hand-written list (`045 AC-53`) |
| **SEC-2** | **The People screen's `staff_list` gate is enforced on the server, and no test may patch it.** An absent switch hides the entry **and** refuses the endpoint. No test in this slice patches `has_feature`, `requires_feature` or `enabled_features` to `True` | `045 AC-51`, extended: a tenant whose `features` list genuinely lacks `staff_list`; **plus a static check that no Wave 4 test patches the gate**; plus a decorator-order check |
| **SEC-3** | **The caller's own block is `frame_api.ME_FIELDS` and nothing else**, on `get_manager_dashboard` and on every Wave 4 endpoint that returns one. `date_of_birth`, `gender`, `cell_number`, `date_of_joining`, `reports_to` and `branch` are absent. **The helper is reused, not re-typed** | `045 AC-6`, strengthened three ways: the fixture **populates all six**; the assertion **searches the serialised payload recursively**, not one key; **plus a static check that no Wave 4 module passes a `_get_employee()` result into a payload** |
| **SEC-4** | **Every Wave 4 payload is a fixed key list, defined once per module as a constant**, in the shape of `frame_api.FRAME_KEYS:49`, `ME_FIELDS:44` and `staff_api.ROW_KEYS:63`. A new key is then a visible act somebody reviews | Exact key-set assertion **per persona** on `get_growth`, `get_team` and the person sheet (`045 AC-20`). A test asserting "these keys are present" rather than "these and no others" does not satisfy this |
| **SEC-5** | **No SQL string in any Wave 4 module is built by `.format()`, an f-string or `%` concatenation** — including the `IN ({placeholders})` shape, which is safe today and teaches the unsafe habit. **Both live instances are replaced, not one:** `hr_api.py:496-504` (`on_leave_today`) and **`hr_api.py:1172-1181` (`get_team_scorecard`)**, which `02` §1 says this wave extends. The scope goes in as a subquery | `045 AC-14`, with the static check written against **the module**, not a line number, and run over both functions. *Stated for the record: neither instance is injectable today; the comments on `:495` and `:1172` are correct* |
| **SEC-6** | **One scope helper, one filter builder, and neither may produce an empty filter.** `permitted_employee_filters()` never returns `{}` (*verified in code*, `access.py:259-261`); the conversion to a condition list happens in **one** place. **`hr_api.py:410` is a hand-rolled second copy of `home_api._filter_list` and must be replaced by a call to it.** Every Wave 4 scoped read goes through it | A unit test that a caller with no HR entitlement and no `reports_to` yields a filter **matching nothing**, asserted on the generated condition list; a static check that no Wave 4 module builds employee filters from `permitted_employee_filters()` inline; **and a test that a caller with no employee id and `is_hr` true returns nothing** — the exact fail-open shape found and fixed this week |
| **SEC-7** | **The person sheet's access gate is a scope or an explicit `reports_to` match — never `get_effective_manager`.** *Verified in code*, `alvoraa_goals/permissions.py:64-71` falls back to the first active HR Manager when `reports_to` is empty, and `hr_api.py:923` uses the result as a permission decision. **A helper written to answer "who do we notify" must not decide "who may read"** | A fixture with an employee whose `reports_to` is empty: the person who happens to be the first active HR Manager is **refused** unless the scope allows them; a static check that no Wave 4 module uses `get_effective_manager` in a permission branch |
| **SEC-8** | **Every refusal on all three screens reads identically, whatever the cause.** "Not allowed", "does not exist", "outside your scope" and "your tenant did not buy this" are one message and one status code, so the answer cannot be used to enumerate people or tenants | Four causes, one byte-identical message, asserted together in **one** test, so changing any one of them fails |
| **SEC-9** | **Every Growth read is ownership-checked the way the write already is.** *Verified in code:* `submit_employee_review:4419` checks `ap.employee != me`. The reads Wave 4 builds carry the same check, and the "HR step inside your own reporting line" refusal (slice 010 decision 34) applies to reads as well as actions | Per-persona test on every Growth read: own review; a report's sent review; a report's **draft** review (refused); a stranger's review (refused identically) |
| **SEC-10** | **Ownership or scope is checked before `ignore_permissions` is raised, and the test proves the order, not its presence.** `growth_api.py` and `team_api.py` carry **no** `ignore_permissions` of their own | For each reused helper, call it as a caller who fails the check and assert the refusal happens **before** any read — assert on the query count as well as on the exception (`045 AC-54`) |
| **SEC-11** | **Each deletion ships in its own commit and is proved gone from the whitelist**: `l2_reports` / `l2_size` (`045 AC-16`) and `goals_api.get_upward_feedback` (`045 AC-35`) | A call-by-hand test expecting a missing method for the endpoint; a repository search proving no reader for the keys |
| **SEC-12** | **Every "who am I" lookup resolves an Employee with `status = "Active"`, through one helper**, and a rehire with two records resolves to the Active one everywhere. Every scoped list carries `status = "Active"` **in the query** | `045 AC-58`; a static check that no Wave 4 module queries Employee by `user_id` without `status` |
| **SEC-13** | **No module-level cache and no module-level mutable state in `growth_api.py` or `team_api.py`**, because one worker serves several sites. Any cache uses `frappe.cache()` or `frappe.local`, keyed by site **and** user | Static check on both modules (`045 AC-54`) |
| **SEC-14** | **A caller with no Employee record is refused explicitly, not filtered by an absent value.** No Wave 4 query runs with an employee filter of `None` | Per endpoint: call as a user with no Employee record; assert refusal **and** assert the scoped query did not run |
| **SEC-15** | **The person sheet is one endpoint.** Four entry points, one whitelisted function, one key list. *Verified in code:* there are two today (`get_employee_scorecard:915` and `get_employee_detail_for_manager:1218`) with the same over-wide field list. **The second must be removed or gated in the same slice**, or Wave 4 narrows one door and leaves the other open | `045 AC-19`, extended: a test asserts exactly one whitelisted person-sheet function **and** that the retired one is no longer callable |
| **SEC-16** | **Everything drawn from data is escaped, in Jinja and in the browser.** Wave 4 adds three panel scripts; `034 SEC-10`'s check must be **extended to them**, not assumed to cover them. Designation, department and company-value names are all tenant-editable text | A DOM test with an employee whose designation is `<img src=x onerror=alert(1)>`, rendered on all three screens; a scan for `innerHTML` receiving API data without `esc()` |
| **SEC-17** | **Before Wave 4 ships, somebody establishes whether `Employee Performance Feedback` is readable tenant-wide today**, on a dev copy: are ordinary employees System Users, does `org_structure` create rows on the client tenants, and is there a Custom DocPerm override. **The answer is written down either way.** *Revision 2:* peer feedback left the wave on 25 September, so **this check is now the only thing keeping the question alive** | Not a code test — a recorded check, with a date and a name. It decides whether Finding 4 is P1 or P3 |
| **SEC-18** *(revision 2)* | **Revision 2's action matrix is a permission matrix, and it must be enforced on the server.** §6a gives "Your team" and "You cover" different action sets — eleven rows. **`045 AC-77` already says the right thing** — *"Absent from the payload, not disabled on the screen… and when the matching endpoints are called by hand as Priya, each refuses on the server"* — and I am making it a requirement rather than one acceptance criterion, because **eleven UI rows are eleven server-side checks**, and a matrix is the shape where one row gets missed. **The section a person is in is derived, not stored** (`reports_to = me` versus the HR scope minus that), so **the server must re-derive it on every action** and never trust a section name sent by the client | Every one of the eleven rows called **by hand** as a caller for whom it is a covered row: each refuses on the server, logged without personal content. **Plus** a test that passing a `section` or `basis` argument to any action endpoint changes nothing — the server derives it. **A test that only checks the payload's absent keys satisfies AC-77 and not this** |
| **SEC-19** *(revision 2)* | **`alvoraa_decided_as` must be written by the server from the caller's real relationship, never from the request.** Revision 2 adds a Select on `Attendance Request` recording whether an approval was made as the manager or as HR (`045 AC-82`). **This is the best audit change in either spec** — it is exactly the field that answers a grievance a year later, when `reports_to` has since changed and the capacity can no longer be worked out. It is also a field a client could lie about if it is ever accepted as an argument | A test that the field is set from the server's own derivation; a test that supplying `decided_as` in the request body does not change what is stored; and a test that the stored value survives a later change to `reports_to` |

### Privacy

| ID | Requirement | How it is tested |
|---|---|---|
| **PRIV-1** | **Pay never appears on a Team or People surface, for any persona including HR.** Wave 3's rule, restated because Wave 4 renders a person sheet, and a person sheet is where a salary figure gets added | Serialise-and-search over every Wave 4 payload for any salary, component or net-pay key |
| **PRIV-2** *(narrowed in revision 2 to match the decided rule)* | **A colleague's leave type and leave reason leave the Team screen.** `leave_type` comes out of the `on_leave_today` SQL (`hr_api.py:498`) and out of `month_leaves`'s `fields` list (`hr_api.py:520`) — **at the read, not at the renderer.** `leave_type` **and `description`** survive **only** on an approval row for the caller's **own direct report**, per `045 D-1` as closed on 25 Sep 2026 — **not** on a covered row, and **not** for an HR caller. `045 D-1` is closed, so there is no default to fall back to: this is the rule | `045 AC-33` and `045 AC-76`, with one addition: **a second assertion proves `description` is absent from every non-approval row**, which neither AC names. The assertion names **"Sick Leave" and "Casual Leave" and every other Leave Type on the fixture**, against the **serialised payload**, for Sandeep **and** for Priya. It must go **red on today's code** first |
| **PRIV-3** | **No phone number, personal email, company email, employee number or gender about anybody but the caller, in any Wave 4 payload.** *Verified in code*, both person-sheet endpoints return `cell_number`, `personal_email`, `company_email` and `gender` today | `045 AC-20`, with the fixture **populating all four**, asserted for every persona including a manager about a direct report |
| **PRIV-4** | **The People search and staff list stay inside Wave 1's scope**, with designation matching added inside the same scope, `%` and `_` still escaped, and the call still POST so a colleague's name never reaches a URL or a browser history | Wave 1's scope tests re-run unchanged; a new test that a designation match does not cross a store boundary (`045 AC-27`) |
| **PRIV-5** | **`manager_internal_notes`, `potential_rating` and an unreleased `overall_rating` never reach an employee-facing payload — and the released-status condition is in the query, not in Python afterwards.** *Verified in code:* `hr_api.py:1174-1181` selects `overall_rating` for the whole team and filters on `review_status` at `:1183-1185`. The payload is correct; the data is in the worker. One `return rows` away is not a control | `045 AC-32` with **all three populated** in the fixture, plus a query-level assertion that an unreleased rating is not read at all on a team path |
| **PRIV-6** | **Upward feedback stays totals-only, with a minimum of three responses, and no author name anywhere.** `goals_api.get_upward_feedback:1113`, which has no minimum and no caller, is **deleted** | `045 AC-35`, plus a call-by-hand test proving it is off the whitelist |
| **PRIV-7** | **No review content, rating, manager note, leave type, goal figure or employee name reaches a log, an error message, a notification body or a push preview.** The send notification (`045 AC-36`) carries the employee's name and the cycle and **nothing from inside the review**; the page-error code is a time plus a short reference | Log-capture on a normal, a refused and a failed call for all three screens; a mail-capture test on the send path asserting the body against a fixture whose review text contains a distinctive string |
| **PRIV-8** | **Growth is the employee's own access path to their own performance record, and it must not be narrower than the record.** A person must be able to read everything about them that is not a legitimately withheld manager field | A test that every field on the employee's own review other than PRIV-5's three is reachable from their own screen |
| **PRIV-9** | **The trajectory chip is not a decision, and it is kept that way by structure.** Three parts: **(a)** the employee sees the **same chip, with the same words and the same "as of" date**, on their own Goals screen — the wording lives in one place so the two cannot drift; **(b)** **no ranking** — no sorted-by-performance list, no ordering by progress, no percentile, no "most improved", in any payload, on any screen, behind any flag; **(c)** **no per-person attention history** — nothing records who was on the list on which day | (a) a test that the manager's chip string and the employee's chip string come from one constant; (b) a static check that no Wave 4 payload contains a list of more than one employee sorted by any progress or trajectory field, plus a payload check for a rank, position or percentile key; (c) a static check that no Wave 4 endpoint writes on a read path and that the slice adds no DocType, field or log line recording an attention state |
| **PRIV-10** | **Wave 4 stores no second copy of a performance record and creates no derived store**, so counsel's "employment + 6 months, then erased" applies unchanged. The chosen-values answer goes in the existing `page_data` JSON on the existing extension | Assert the slice adds no DocType, no custom field and no patch — **except** `045 D-7`'s single consent `Check` field if that decision is yes, which is a preference and not a performance record |
| **PRIV-11** | **No control on any Wave 4 screen may claim a route that does not exist.** There is no recorded, clocked grievance route in the product (counsel, 18 Sep 2026: *"Not built. Handled by hand"*). The "What your manager will see" block and every explanatory sentence must be true of the code on the day it ships | `045 AC-41`, extended: a static check that no Growth or Team module contains a sentence asserting a behaviour the product does not have, **and** that no control is labelled "contest", "dispute" or "appeal" unless something is actually recorded |
| **PRIV-12** | **Minimum-group suppression is `home_api._suppress` and `MIN_GROUP = 5`, reused** — a second implementation fails the test — **and the next-smallest group is suppressed with it**, or the suppressed number is recoverable by subtraction | `045 AC-34`, with a four-person group and a table where a second small group makes the first recoverable |
| **PRIV-13** | **Nothing in this slice is AI-shaped.** No model, no inference, no emotion, voice or facial analysis, no passive behavioural monitoring, no individual-level surveillance. **There is no model anywhere in this slice, so there is no redaction boundary to build** — said plainly so nobody later assumes one exists | A static check that no Wave 4 module imports or calls a model client |

---

## Questions

### Must know — these block a requirement or a commit

| # | Question | My reading, and the fail-closed default meanwhile | Owner | Blocks |
|---|---|---|---|---|
| **Q1** | ~~**`045 D-1` — may a colleague's leave type and leave reason stay on the Team screen?**~~ **ANSWERED 25 Sep 2026** | **Closed, and closed tighter than I asked for.** Surbhi's two-section Team screen keeps the leave type on an own-direct-report approval row and nowhere else, for anybody. **Nothing is blocked. PRIV-2 is narrowed to match**, and the only thing left is to build and test it — including the `description` field, which the decision's acceptance criteria still do not name | — | **Nothing. Build it** |
| **Q2** | **Is `Employee Performance Feedback` readable tenant-wide on `dtc` and `aahr` today?** Three facts decide it and I could check none of them from the repository | **Run the check on a dev copy before Wave 4 ships** (SEC-17). **Until it is answered I am treating the shape as unsafe**, which is why peer feedback is a no-go regardless | Surbhi, with the engineer | Nothing in Wave 4's build. It decides whether this is a P1 for the **product**, and it must not be dropped |
| **Q3** | **`045 D-7` — may a colleague's work phone number and email appear in the person sheet, and does that need an opt-in under DPDP, or is it employment context?** | **Not in Wave 4.** Ship `staff_api`'s five keys. If it is wanted, it is one `Check` field on Employee, default 0, plus a row on the person's own account screen. **The default is "no contact detail", which is what ships today** | Surbhi, **with an advisor** | Nothing — the default is the safe one |

### Should know

| # | Question | Owner |
|---|---|---|
| Q4a *(revision 2)* | **An HR person who is the named `leave_approver` for somebody who is not their direct report must now decide that request without seeing the leave type.** The decided rule is `reports_to`-based; the approval duty is `leave_approver`-based, and the two do not always coincide. **My reading: accept it.** A person deciding leave can see the dates, the balance and the person, and "why" is the field rule 9 exists to withhold. **But somebody should check whether that combination actually occurs on the client tenants** before HR meets it on a Monday. *Access I would need: a count of Leave Applications whose `leave_approver` is not the employee's `reports_to`, on a dev copy* | Surbhi, with the engineer |
| Q4 | **`045 D-10` — does a plain employee get the staff directory at all?** It is a visibility decision, not a menu decision, and it is one line either way. The scope already gives an employee their own line and nothing more (W1D-07), so I see no new exposure and I would say yes | Surbhi |
| Q5 | **Is "employment + 6 months, then erased" being enforced on Appraisal, its extension, Individual Goal and Goal Evidence today?** Counsel set the period on 18 Sep 2026. **I could not find any job that enforces it** in this repository. **Access I would need:** a read of the scheduler events and any purge job on a dev copy | Surbhi, with me — R4 |
| Q6 | **For counsel.** Does a stored trajectory shown to a manager, which puts a named person on a list the manager acts on, engage any obligation to explain or contest under Indian law — and does the answer change if GDPR applies? It decides nothing and moves no money, which is why I think the answer is no. I will not guess it | **Counsel, commissioned by Surbhi** |

---

## Worries — not findings

Each of these is a concern I cannot yet write as *this actor, in this state, calling this
path, sees this data*. They are here so they are not lost, and they are **not** requirements.

1. **740 `ignore_permissions` in `alvoraa_portal` alone, 70 of them in `hr_api.py`, 976
   across the three apps.** Counted today. SEC-10 covers the helpers Wave 4 touches. **The
   repo-wide counter that can only go down is still not built** — R2, and it is the control
   that would make every requirement above survive two quarters rather than one.
2. **`field_app_access.py:116` builds a `permission_query_condition` from an f-string.** It
   looked safe on a read — the interpolated value is a doctype name — but a permission
   condition assembled by formatting is the worst place in a Frappe app for that shape, and it
   is not Wave 4's file. Worth somebody's ten minutes.
3. **`get_team_goals` loops per person (22 queries for 19 people on 14 Sep) and `my_view`
   walks the tree a step at a time (31).** Not a privacy risk. They are the two calls most
   likely to be rewritten in a hurry, and a hurried rewrite is where a scope gets dropped.
4. **The demo data cannot show most of Growth working.** Slice 028's lesson: the HR conflict
   flag read 0 on all 806 appraisals because no review had reached the stage the rule guarded.
   Until an open cycle with a real review, pending evidence and open action items is seeded,
   **a passing Growth test proves very little.** The table below says what must exist.
5. **The org chart and `reports_to` disagree on the demo tenant** (`045 D-9`). AC-25 makes the
   code choose `reports_to`, which is right. Two screens naming two different managers is still
   a fault somebody will read as a permission bug.

### What must exist in the data before each control is observable

| Control | What the data must contain |
|---|---|
| SEC-3 | A caller whose Employee record has **all six** of `date_of_birth`, `gender`, `cell_number`, `date_of_joining`, `reports_to`, `branch` populated |
| PRIV-2 | Somebody off **today** on a named Leave Type; somebody on leave that **began last month and is still running**; a leave application with a non-empty `description` — plus an HR caller whose scope holds people who are not their reports |
| PRIV-3 | A direct report with `cell_number`, `personal_email`, `company_email` and `gender` all populated |
| PRIV-5 | A review with `manager_internal_notes`, `potential_rating` and an **unreleased** `overall_rating` all populated |
| PRIV-6 | Upward feedback with exactly **two** responses |
| PRIV-12 | A group of **four**, and a second small group in the same table |
| SEC-6 | A caller with HR roles but **no** permitted company; and 400 employees with an empty `reports_to` |
| SEC-7 | An employee whose `reports_to` is empty, on a tenant that has a first active HR Manager |
| SEC-12 | A rehire with two Employee records, one Left and one Active |
| SEC-16 | An employee whose designation contains a tag |

---

## Residual risk — each with an owner and a date

| # | Risk | Owner | Date | State |
|---|---|---|---|---|
| **R1** | **A successful over-read leaves no signal.** Refusals are logged; successes are not. **Wave 4 is the wave that makes this bite**, because it is the first wave built for one person to look at another | Security & privacy engineer, with DevOps | Logging first step **2026-10-15**; detection slice **2026-11-30** | **Carried from Wave 1 R3 and Wave 3 R1, and re-stated rather than re-accepted quietly.** If the leave type stays (Q1), there is no record of anybody using the Team screen to work out who is unwell |
| **R2** | **No repo-wide `ignore_permissions` counter in CI.** 976 across the three apps today, counted | Security & privacy engineer (feature map B4 / I3) | Baseline script **2026-10-31**; blocking gate on the next commit after | **Carried from Wave 1 R4 and Wave 3 R2.** Wave 1 recorded the gate as due **before Wave 2 added endpoints**. Waves 2, 3, 4 and 5 are all here. **Temporary debt that is becoming permanent — this is the date I would defend** |
| **R3** | **`Employee Performance Feedback` grants the `Employee` role ten actions on the whole doctype with no row scope, and we already write rows to it** through `dotted_line.py:125-136` | Security & privacy engineer, with the engineer | **Check by 2026-10-05** (SEC-17); fix scheduled once the check says P1 or P3 | **Not accepted — open, and new.** **Sharper after revision 2:** peer feedback was the slice that would have forced somebody to look at this, and it left Wave 4 on 25 September. The finding must not leave with it. It is not Wave 4's to fix and it must not be Wave 4's to forget |
| **R4** | **No retention job for performance records.** Counsel set employment + 6 months on 18 Sep 2026; I could find nothing enforcing it | Security & privacy engineer, with Surbhi | **Confirm by 2026-10-31**; a job by **2026-12-15** | **Not accepted — open.** Wave 4 adds no new record, so it is not made worse. Nobody else owns it |
| **R5** | **The org chart shows every company and store** (`ALV-86`, Critical). Wave 4 does not touch the chart and does not work around it | Fullstack engineer | Before DTC go-live | **Carried from Wave 1 R1.** Named here because Wave 4 puts a People screen next to it |
| **R6** | **Store HR whose Branch User Permission is narrowed to a single doctype is treated as company-wide** (`access.py:233` fails open) | Live check: Surbhi. Code fix: engineer, `ALV-86` | Live check **2026-09-30**; fix **2026-11-15** | **Carried from Wave 1 R6 and Wave 3 R6.** Wave 4 is the wave where it decides how many people are on Priya's Team screen |
| **R7** | **Alvoraa staff reach client tenants through one shared `Administrator` login**, so a read cannot be traced to a person | Surbhi, with me | `ALV-93` | **Recorded (W1D-18).** Re-stated because Wave 4's data is performance and review content |
| **R8** *(new)* | **The trajectory chip is a judgement about a person that a manager acts on, computed with no human involved.** PRIV-9 keeps it honest and visible to the person. It remains one product decision away from a ranking | Surbhi | Decide at the strategy gate; re-read at any request for "top performers" | **Proposed for acceptance, with PRIV-9's three tests as the condition.** My recommendation: accept |

**Debt this document leaves behind, labelled.**
**Intentional trade-off** — Wave 4 renders a stale trajectory with its date rather than
recomputing on a read path (`045 D-3`); the nightly recompute is its own ticket.
**Temporary debt** — R2's `ignore_permissions` gate, removed the day the counter lands; R4's
retention job, removed when the job exists.
**Acceptable simplification** — the person sheet gated by scope rather than by a purpose tag,
because feature-map A1 does not exist yet.
**Dangerous debt** — **R3.** Ten permissions on a whole doctype about people's performance, on
a doctype we already write to, on tenants nobody has checked. It is not sitting quietly in a
table: it is Q2, SEC-17 and R3, and it has a date.

---

## Assumptions and unknowns

- `[ASSUMPTION]` `permitted_employee_filters()` behaves as its docstring and slice 030's tests
  say. *Verified in code* that it exists and that its fail-closed branch is real
  (`access.py:252-282`).
- `[ASSUMPTION]` `page_data` on the Appraisal extension is a Text field of about 64 KB. The
  analyst's `045 AC-40` measures it. **Not verified — no bench.**
- `[ASSUMPTION]` Slice 010 groups A–D are on `origin/dev` and the Growth write paths are
  ownership-checked. *Verified in code* for `submit_employee_review:4419`; **the reads are not
  verified, which is why SEC-9 exists.**
- **Unknown — I could not check these, and each names the access I would need:**
  - **Whether ordinary employees on `dtc` and `aahr` are System Users**, and whether
    `Employee Performance Feedback` has rows and a Custom DocPerm override. *Access: a dev copy
    of either tenant.* **This is Q2 and it is the sharpest unknown in this document.**
  - **Whether any job enforces counsel's performance-record retention period.** *Access: the
    scheduler events on a dev copy.* Q5, R4.
  - **Whether the notification paths elsewhere in Growth carry review content.** *Access: a
    mail capture on a bench.* PRIV-7 tests it; I could not pre-read it.

---

## Verdict for this slice

**Ready to build, with seven spec changes — and that is a better verdict than the one I
started writing.**

**Against revision 1 this was "not ready to build the two leave lists", with one P1 waiting on
a decision.** Revision 2 closed that decision on 25 September, tighter than I recommended.
**The P1 is now a build requirement rather than an open question**, and it stays a P1 until it
is built, because an undecided leak and an unbuilt fix look identical from the outside.

**Two things I want on the record about revision 2, because they are unusually good.** The
two-section Team screen **closes `045 D-1` by changing the structure rather than by adding a
rule** — an HR person sees no leave type because there is no place on their section for one,
not because a filter removed it. That is the shape I ask for every time and rarely get. And
`alvoraa_decided_as` records the **capacity** an approval was made in, which is precisely the
field that answers a grievance a year later when the reporting line has since changed (SEC-19).

**And one thing revision 2 adds that needs watching:** an eleven-row action matrix is an
eleven-row permission matrix. `AC-77` says the right thing about server-side refusal; **SEC-18
makes it a requirement**, because a matrix is the shape where one row gets missed and the miss
is invisible until somebody presses it.

**What must change in `02` before code:**

1. **`AC-33` and `AC-76` / PRIV-2** — revision 2 already covers Priya and both Leave Type
   strings, which is right. **It still does not cover `description`**, the employee's own
   free-text reason, which travels in the same payload at `hr_api.py:508-516`. Add it, or the
   decision will be applied to the type and not to the reason.
2. **`AC-14` / SEC-5** — the static check must cover **`get_team_scorecard`'s raw SQL at
   `hr_api.py:1172-1181`** as well as `on_leave_today`. `02` names one instance; there are two,
   and Wave 4 extends both functions.
3. **`AC-6` / SEC-3** — the assertion must search the **serialised payload recursively**, not
   the `manager` key, and the replacement must reuse `frame_api.ME_FIELDS` rather than re-type
   the six names in a new module.
4. **`AC-32` / PRIV-5** — add a **query-level** assertion. The payload is already correct; the
   unreleased rating is read into the worker and dropped in Python at `hr_api.py:1183`. The
   condition belongs in the query.
5. **`AC-19` / SEC-15** — "one person-sheet endpoint" must include **retiring
   `get_employee_detail_for_manager`**, or Wave 4 narrows one door and leaves its twin open
   with the identical over-wide field list.
6. **A new check for SEC-7** — the person sheet's gate must not be `get_effective_manager`,
   which invents a manager for anybody whose `reports_to` is empty.
7. **`AC-23` / PRIV-9** — the "needs attention" wording must come from **one** constant shared
   with the employee's own Goals screen, so the manager's words and the person's words cannot
   drift.
8. **`AC-77` / SEC-18 and `AC-82` / SEC-19** *(revision 2)* — the action matrix needs a
   by-hand server test **per row**, and the section must be **derived by the server**, never
   taken from the request. `alvoraa_decided_as` likewise.

**Decisions for Surbhi, not requirements — and this list is now down to four:**

| # | Decision | Why it is hers |
|---|---|---|
| 1 | **Contact details on the person sheet, and whether consent is needed** (Q3, `045 D-7`) | It turns partly on DPDP, so it needs an advisor, and partly on what she wants the product to be |
| 2 | **Whether a plain employee gets the directory at all** (Q4, `045 D-10`) | A visibility decision no code answers |
| 3 | **Accepting R8** — the trajectory chip as a judgement a manager acts on | An accepted risk with a name and a date is governance; the same risk unnamed is an accident waiting for an owner |
| 4 | **Commissioning Q6 to counsel** | Only she can |

**`045 D-1` has come off this list** — it was decided on 25 September, and decided tighter than
I asked for. Everything else on the analyst's list is a design or build choice with a safe
default already written into a check, and it does not need her.

**No P0.** The three handed-over defects rank **P1 (the leave type — decided, not yet built),
P2 (the `manager` key and the SQL shape), P4 (the SQL as injection — it is not one).**
Finding 4 is **P1 or P3, and Q2 decides which**; it is not Wave 4's to fix, **and peer
feedback leaving the wave is exactly why SEC-17 has a date**.

---

## Handoff note

**To the analyst:** the seven spec changes above. Every `045 SEC-n` and `045 PRIV-n` needs an
acceptance criterion; PRIV-8, PRIV-9(a) and PRIV-11 are the three hardest to write as
observable checks, so ask me rather than guessing the oracle. **And `02` §19.3's row describing
the W1D-20 widening is the best-written paragraph in either spec — do not let it be softened in
revision 2.**

**To the engineer:** three things, in this order. **Replace `hr_api.py:410` with a call to
`home_api._filter_list`** before you write anything else — it is a second copy of the helper
that was just found failing open, and Wave 4 is the commit that gives it more callers. **Drop
`leave_type` and `description` at the SQL and at the `fields` list**, not in the renderer; a
field filtered in JavaScript is still in the response and in the cache. And **resolve the person
sheet's gate from the scope, never from `get_effective_manager`** — a helper written to decide
who to notify is currently deciding who may read.

**To the test engineer — six tests here are easy to write so they prove nothing.**
**SEC-3** needs a fixture with **all six** fields populated and a **recursive** search of the
serialised payload. **PRIV-2** must name "Sick Leave" **and "Casual Leave"** against the
serialised payload, run as **Priya** as well as Sandeep, cover **`description`** as well as the
type, and go **red on today's code** — `hr_api.py:498` and `:520` select it, so it will.
**PRIV-5** needs the **query-level** assertion, not only the payload one. **SEC-2** must not
patch the feature gate — a patched gate makes every entitlement test pass while proving
nothing. **SEC-6** must include the caller with no employee id and `is_hr` true. **SEC-10** must
assert the **order** by counting queries, not the presence of a check. **And SEC-18** must call
each of revision 2's eleven action rows **by hand on the server** — asserting that a button is
absent from a payload proves the screen, not the rule.

**To the DevOps engineer:** SEC-5 and your `07` want the same change for different reasons, and
there are **two** instances, not one — `hr_api.py:496-504` and `hr_api.py:1172-1181`. The second
is inside `get_team_scorecard`, which also reads every appraisal-extension row for every team
member with no limit and filters in Python.

**To me, at review:** PRIV-2 first (is the leave type genuinely out of the read?), then SEC-6
(is there still only one filter builder?), then SEC-7 (what gates the person sheet?), then
SEC-3's recursive assertion, then Q2's answer. **And I specified SEC-3, SEC-5 and PRIV-2 against
code I read myself — if I am asked to review my own requirement being met, I will say so and ask
for a second pair of eyes on those three.**
