---
slice: 052-hr-optional-tenant
artifact: 01-product-brief
author: hrms-product-manager
date: 2026-09-27
status: draft
inputs: [repo verification (see §12), .claude/context/product-context.md, .claude/context/handoff-contract.md]
---

# Selling Alvoraa without HR

## 0 · Read this first

**Bad news, twice.**

**One: two of the input documents this brief is supposed to build on do not exist.**
There is no `01a-ux-opportunities.md` and no `07-devops-inputs.md` §1 for this slice.
The handoff contract allows step 1 to be skipped for a back-end-only slice if the brief
says so. This *is* a back-end and configuration slice — it changes provisioning and the
admin console, not an employee screen. So I have written the brief anyway and said so
here. **The DevOps run-side note is still genuinely missing and I have not guessed its
numbers.** `[Open question OQ-1]`

**Two: we have no customer for this today.** Alvoraa has one live client tenant (dtc,
going live early October) and one demo tenant (Sargam). Both bought HR. Nobody has asked
to buy Alvoraa without HR. Everything below is anticipation, and I have labelled it as
such. That materially changes my recommendation — see §7.

**My recommendation in one line:** remove the mandate at the configuration layer and fix
the three real breakages now (about a day of work, all of it bug-shaped and useful
anyway), and **refuse** to build graceful degradation of the employee portal until a
named non-HR deal exists.

---

## 1 · The job to be done

In Surbhi's words (2026-09-27):

> "There might be the cases where clients won't buy Frappe hr and Alvoraa HRMS. we need
> to handle that in tenant configuration to remove that mandate as well as also handle
> all the overriding cases accordingly"

Written as a job:

> **As the person selling and provisioning Alvoraa, when a prospect wants only the CRM
> (or only the vendor and delivery portal, or only ERPNext), I want to create their
> tenant without Frappe HR in it, so that I am not shipping them an HR system they did
> not buy, cannot use, and will ask awkward questions about.**

**Whose job is it?** None of the three product personas. This is the **platform
operator's** job — Surbhi in the admin console. That is important: it means this slice
is worth very little to an employee, an HR manager or a CXO, and a great deal to a
salesperson on a particular kind of call.

**What changes for the three personas:**

| Persona | What changes |
|---|---|
| Employee | On a no-HR tenant, **there is no employee self-service portal at all.** On every existing tenant, nothing changes. |
| HR Manager | Nothing. A no-HR tenant has no HR manager. |
| CXO | Nothing today. Later, a cleaner bill: they stop paying for modules they never open. |

---

## 2 · Current pain — a story, not a number

I have no ticket, no lost deal and no demo note to point at. I will not invent one.

The concrete pain that **is** verified is internal. Today, provisioning a tenant that
only wants the CRM still runs this, unconditionally
(`deploy/provision_tenant.sh` lines 84–86) — **Confirmed**:

```
bench --site $SITE_NAME install-app erpnext
bench --site $SITE_NAME install-app hrms
bench --site $SITE_NAME install-app alvoraa_portal
```

And the subscription registry marks five HR features `"required": True`, meaning they
cannot be unticked on any plan (`alvoraa_portal/subscription.py`, lines 63, 71, 79, 87,
95 — **Confirmed**): Employee Portal, Leaves, Shift & Attendance, Expenses, HR Setup.
`tenant_api.create_tenant` then re-adds them even if the console leaves them out
(line 291 — **Confirmed**).

So a CRM-only customer would today get: every HR doctype, an HR workspace hidden only by
a Module Profile (a UI-only block, as `subscription.py` itself says in its own header
comment), HR Manager and HR User roles created for their admin users
(`tenant_setup.py` line 96 — **Confirmed**), and a login page that sends anyone with an
Employee record to `/hrms-employee`.

**The honest size of that pain right now: zero customers affected.**

---

## 3 · What "no HR" actually means — three products, not one

This is the most useful part of the brief. The request says "Frappe HR and Alvoraa HRMS"
as if they were one thing. They are three, and they do not detach independently.

| Layer | What it is | Can it be dropped on its own? |
|---|---|---|
| **(a) `hrms`** — the Frappe HR app | Employee Checkin, Attendance, Leave, Expense Claim, Payroll, Appraisal | **Yes, in principle.** It is a separate app; not installing it means its tables never exist. This is the real gate. |
| **(b) Alvoraa's own HR modules** | `alvoraa_hr_core`, `alvoraa_late_rules`, `alvoraa_employee_documents`, `alvoraa_screening`, `alvoraa_org_structure`, `alvoraa_policy_library` | **No.** Verified: they live *inside* the `hrms` folder in this repo (`hrms/hrms/alvoraa_hr_core/…`). They go when `hrms` goes, and they cannot go while it stays. |
| **(c) `alvoraa_goals`** | Objectives, KPIs, evidence | **Already optional** — gated on the `goals` feature in provisioning, and it correctly declares `required_apps = ["frappe/hrms"]`. It can never be sold without `hrms`. |

**Which combinations are sellable, and which are nonsense:**

| Combination | Verdict |
|---|---|
| ERPNext + `alvoraa_portal`, no `hrms` | **Sellable.** This is the real target: a CRM-only, Finance-only or Selling/Stock tenant. |
| ERPNext + `alvoraa_portal` + vendor/delivery portal, no `hrms` | **Sellable.** Those doctypes (Vendor Order, Delivery Order, Delivery Partner, Order Rating) belong to `alvoraa_portal`, not to HR. **Confirmed** from `hooks.py` `doc_events`. |
| The field / delivery **attendance app**, no `hrms` | **Nonsense.** The check-in app writes `Employee Checkin`, which is an `hrms` doctype (`hrms/hrms/hr/doctype/employee_checkin/`, referenced nine times in `field_checkin.py` — **Confirmed**). A "field-app-only tenant" still needs `hrms`. This kills one of the tenant shapes the ask assumed. |
| `alvoraa_goals` without `hrms` | **Nonsense**, and already refused by its own `required_apps`. |
| `alvoraa_portal` removed | **Never.** See §4. |

---

## 4 · The hard question: can the portal survive without HR?

**Yes — but the *employee* portal cannot. Those are two different things, and the name
hides it.**

`alvoraa_portal` is not an HR app. Its own description calls it a "Multi-brand vendor
portal with order tracking and delivery management", and it carries most of the
platform: the branded login page, the tenant branding, the control-plane admin console
(`/alvoraa-admin`), tenant provisioning (`tenant_api.py`), the subscription and
entitlement registry (`subscription.py`), health and usage reporting, and the AI lead
intake for the CRM. **Every tenant needs it, HR or not.** It must stay mandatory.

What *is* purely HR inside it is the **employee self-service portal** — the
`/hrms-employee` page and the APIs behind it (`hr_api.py`, `performance_api.py`,
`team_api.py`, `growth_api.py`, `attendance_analytics.py`, `data_review.py`). Those
exist to show a person their leave, their attendance, their goals and their review.
**Without `hrms` there is nothing for them to show.**

**So the product rule I recommend we adopt, plainly:**

> A tenant without HR has no employee self-service portal. It has the desk, and it may
> have the vendor and driver portals. `/hrms-employee` is simply not offered.

This is not a gap to fix later. It is the correct answer, and it shrinks the slice from
"make 60-odd endpoints degrade gracefully" to "do not offer the page". `[Recommendation]`

---

## 5 · What is actually broken, verified

I re-checked every claim I was handed. Two were right, one was wrong, and I found one
more.

| # | Claim | Verdict |
|---|---|---|
| 1 | `alvoraa_portal/hooks.py` declares `required_apps = ["frappe/erpnext"]` and does **not** declare `hrms`, yet imports it in dozens of places | **Confirmed** (line 7). |
| 2 | Only two of those imports are top-level, so the rest only fail when used | **Confirmed.** Exactly two outside tests: `hr_api.py:12` and `performance_api.py:24`. All other production imports are inside functions. (Five test modules also import at the top — they would fail *collection*, not runtime.) |
| 3 | `branch_scope.after_migrate` is **not** guarded | **Wrong — it is guarded.** `branch_scope.py` line 62 filters every doctype through `frappe.db.exists("DocType", dt)`. No change needed. |
| 4 | `data_review.add_indexes` is not fully guarded | **Confirmed, and this is the one real installer break.** The two-column loop checks `has_column`; the **single-column loop does not check anything** (`data_review.py` lines 124–134). It would try to create a property setter and an index on `Employee Checkin`, which does not exist without `hrms`. `bench install-app alvoraa_portal` would fail. |
| 5 | Hooks hung on HR doctypes are inert when the doctype is absent | **Needs validation.** Frappe resolves a `doc_events` entry only when a document of that type is saved, and no such document can exist. I could not run a bench to prove it (not permitted in this session), so it stays `[Needs validation]` for the engineer. |
| 6 | Scheduler jobs behave unknown with no HR | **Needs validation.** Seven daily/hourly/cron jobs. Several are already written to return early on a site that has not switched the feature on (AI intake, health, usage). The attendance ones (`data_review.enqueue_morning_checks`, `scheduled_jobs.check_compliance_alerts`, `field_app_photos.purge_old_checkin_photos`) are the ones to check. A failing scheduled job is noisy, not fatal — but it fills the error log every day. |
| 7 | **New finding:** `tenant_setup.create_default_users` assigns the roles `HR Manager` and `HR User` (line 96) | **Confirmed.** Those roles are shipped by `hrms`. Creating a tenant without HR would try to grant a role that does not exist. |
| 8 | **New finding:** `tenant_api.create_tenant` prepends a legacy `"hrms"` marker to every module list (lines 278–285) and re-adds all `REQUIRED` features (line 291) | **Confirmed.** The mandate lives here as much as in the shell script. |

Slice `050-erpnext-restore` is about ERPNext being *present* and does not interact with
this. I am not touching it.

---

## 6 · Three ways to solve it, and the fourth question

**Conventional.** Make every HR surface degrade gracefully: guard all 66 imports, make
each portal card check for HR, write empty states. Weeks of work, permanently more code
to maintain, and it builds a product nobody has bought.

**Better (what I propose).** Treat HR as a pack that is either installed or not. Do not
install it; do not create its roles; do not offer its page. Guard the one installer that
breaks and move the two top-level imports inside their functions. The 64 lazy imports
need no change, because no one can reach the endpoints that use them.

**Reimagined.** Stop shipping one image with everything and let the customer's plan pick
the app set at build time. That is a real answer for a much bigger company than this
one, and it would not make a single current customer's day better.

**Could we not build this at all?** Partly, yes — and this is the honest answer. Nothing
stops us from selling a CRM-only tenant *today*: we would provision it as we always do,
untick everything in the console, and the buyer would get hidden HR modules they never
see. It would work. It would just be dishonest on the invoice and slightly slower to
provision. **So the only part that is genuinely urgent is the part that is already a
bug:** the unguarded installer, the two top-level imports, and the undeclared dependency.

---

## 7 · Kano class and demand

**Class: Indifferent today. Must-be the day a non-HR deal exists.** Marked `proxy` — we
have no survey and no customer request.

- Not **Attractive**: no buyer is delighted by an app they cannot see.
- Not **Performance**: nobody compares vendors on this.
- **Indifferent now**: zero of two live tenants care. `[Confirmed]`
- **Must-be later**: the moment someone buys CRM-only, "do not install HR" stops being a
  nicety. You cannot ship an HR system to a company that refused to buy one and expect
  their security reviewer to be relaxed about it. Our buyers gate on security review
  (`product-context.md` §9).

**Kano drift runs the wrong way here.** This does not become more valuable with time; it
becomes valuable *instantly*, on one phone call. That argues for keeping the work small
and ready, not for building it out.

**Evidence that would change the class:** one named prospect who wants Alvoraa without
HR, with a plan and a date. That is a single fact and only Surbhi has it.
`[Open question OQ-2]`

**Competitive note.** Zoho and Keka sell HR as the product, so the question does not
arise for them. Frappe/ERPNext itself already does exactly what I am proposing — apps are
installed per site, and `hrms` is optional in stock Frappe. **We are the ones who added
the mandate.** So this is not a feature; it is us giving back a property the framework
already had. `[read — Frappe app model, not re-verified against upstream docs today]`

---

## 8 · The thin slice

**One outcome, end to end: Surbhi can create a tenant with no HR in it, and it works.**

In scope:

1. **The console offers HR as a pack that can be unticked.** The five `required: True`
   HR features stop being unconditionally required; `portal` stays required.
   `tenant_api` stops force-adding them and stops prepending the legacy `"hrms"` marker
   when HR is not sold.
2. **Provisioning skips `hrms`** (and therefore `alvoraa_goals`) when HR is not sold,
   using the `has_feature` pattern the script already uses for four other apps.
3. **No HR roles are created** on a no-HR tenant (`tenant_setup.py`).
4. **`alvoraa_portal` installs cleanly with no `hrms`.** Guard the single-column index
   loop in `data_review.py`. Move the two top-level `hrms` imports inside their
   functions. Correct `required_apps` in `hooks.py` to say what is true.
5. **`/hrms-employee` is not offered** on a no-HR tenant — the login redirect and the
   menu do not send anyone there.
6. **One proof:** a test tenant provisioned with CRM only, no `hrms`, that installs,
   migrates, logs in, and runs a scheduler day with a clean error log.

**Needed before it can ship (not in this slice):** a decision on whether an existing HR
tenant may ever be *downgraded* to no-HR. My recommendation is **no, never uninstall** —
the script already says this about `alvoraa_goals`, for the good reason that dropping an
app drops the customer's data.

**Worth doing later:** pricing and plan names for a no-HR bundle; the admin console
warning copy; a no-HR landing page for the desk.

**Not doing:** graceful degradation of the employee portal; guarding the other 64 lazy
imports; making the field attendance app work without `hrms`; any new module, dashboard
or settings page.

---

## 9 · What it is NOT — scope I am refusing

- **Not** a rewrite of the entitlement model. `FEATURES` already has the shape we need.
- **Not** a promise that every HR-shaped screen shows a polite empty state. It shows
  nothing, because the page is not offered.
- **Not** an uninstall path.
- **Not** a new "non-HR plan". Until a real deal names one, the console tick is enough.
- **Not** touching `hrms`'s own hooks. Slice 050 owns that file.

---

## 10 · The WOW

This slice has no employee-facing moment, and I will not pretend otherwise. The one
moment worth designing is for the operator:

> In the admin console, unticking **People & HR** replaces the feature list with one
> plain line: *"This tenant will have no employees, no leave, no attendance, no payroll
> and no employee portal. Frappe HR will not be installed, and it cannot be added later
> without support."*

It is achievable inside the slice, it is one sentence of copy, and it prevents the single
most expensive mistake available here — unticking HR on a tenant that wanted it.

---

## 11 · Thriving-workplace check

| Lens | Answer |
|---|---|
| Engagement | No effect. No employee's day changes. |
| Collaboration | No effect. |
| Inclusiveness | **A small real gain.** A worker at a CRM-only customer stops having an unusable HR portal and an unexplained HR role attached to their login. |
| Transparency | **A gain, for the buyer.** What they bought is what is installed. Today the invoice and the database disagree. |

## Regulatory read

1. **Which regime?** Data protection — India's DPDP Act 2023.
2. **Whose obligation?** The **customer's**, as employer. This helps them discharge it.
3. **What does it make possible?** Less, not more. An organisation that never bought HR
   never gets `Employee`, `Attendance`, `Employee Checkin` (with GPS and photographs) or
   `Salary Slip` tables on their site. That is data minimisation by construction, and it
   is the kind of answer a security reviewer likes. No new data is collected, no new
   visibility is granted, no decision is automated.
4. **The honest downside?** None I can see. I am not a lawyer; no counsel ruling is
   needed for this slice.

No AI is involved. No refusal in `product-context.md` §6 is engaged.

---

## 12 · Success criteria

| # | Measure | Baseline | Target | How it is instrumented |
|---|---|---|---|---|
| S1 | A tenant provisioned with HR unticked installs, migrates and serves its login page | **Impossible today** — provisioning installs `hrms` unconditionally | Works, proved once on a throwaway site | The slice's own test: provision, migrate, hit the login page, `bench install-app alvoraa_portal` on a site with no `hrms` |
| S2 | Scheduler errors on a no-HR tenant, over 24 hours | baseline unknown — measure first | Zero HR-caused entries in the Error Log | Count Error Log rows on the test tenant after one scheduler day |
| S3 | Every existing tenant is byte-for-byte unaffected | n/a | No change to the installed app list, roles or feature list on dtc, Sargam or `test_site` | Compare `installed_apps`, `Has Role` counts and `features` before and after migrate |
| S4 | Provisioning time for a no-HR tenant | baseline unknown | Lower than a full tenant; report the real number | Time the script |

**Not a success measure:** number of no-HR tenants. There will be zero until a deal
exists, and that is not this slice's fault.

---

## 13 · Risks and the honest downside

| Risk | What breaks | Cheapest way to find out first |
|---|---|---|
| **We build optionality for a customer who never arrives.** | A day of work and permanently more branching in provisioning and the subscription registry. This is the biggest risk in the brief. | Ask Surbhi whether a real deal exists (OQ-2). If not, do items 4 and 5 of the thin slice only — they are bug fixes and pay for themselves. |
| **Unticking HR on a tenant that wanted it.** | Catastrophic and near-unrecoverable — we do not uninstall, so the reverse is also awkward. A customer goes live with no HR. | The §10 warning line, plus a confirm step. Make HR ticked by default. |
| **The two top-level imports move, and something imports them at load anyway.** | A portal page 500s on every existing tenant. | A migrate plus the full `alvoraa_portal` suite on an ordinary HR tenant — the regression test is the existing suite, not a new one. |
| **The unguarded index loop is not the only installer that breaks.** | `bench install-app` fails half way and leaves a broken site. | The engineer installs `alvoraa_portal` on a bare ERPNext site once. That single command answers it. |
| **Scheduler jobs log an error every day.** | Error Log fills; health reporting to the control plane gets noisy; a real problem hides behind it. | Run the test tenant for one scheduler day (S2). |
| **A tenant later buys HR.** | Installing `hrms` into a live site with existing users and Module Profiles is not a path we have tested. | Decide it is a support task, not a product feature (OQ-3). Say so in the warning copy. |
| **At 10× tenants** | No change — this is per-site configuration, not per-user. | — |
| **Bad or missing data** | A tenant whose `features` list is empty falls back to "everything the registry has" (`subscription.py` header). **That fallback would re-enable HR features on a no-HR site.** The engineer must check what the fallback does when `hrms` is not installed. | Read `enabled_features()` before designing. |

---

## Open questions

| # | Question | Owner | Blocks | My recommended assumption if you want me to keep moving |
|---|---|---|---|---|
| OQ-1 | The DevOps §1 run-side note for this slice does not exist. Do you want it before the design step? | Surbhi | The handoff contract's step 2 input | Skip it — this slice removes apps rather than adding them, so run cost falls. |
| OQ-2 | **Must know.** Is there a named prospect who wants Alvoraa without HR, with a date? | Surbhi | Whether this is built now in full, or trimmed to the bug fixes | No prospect. Build items 4 and 5 only; hold 1–3 until one appears. |
| OQ-3 | **Must know.** Do we ever need to remove HR from a tenant that already has it, or only never install it? | Surbhi | The size of the slice, by a lot | Never uninstall. Same rule as `alvoraa_goals`. |
| OQ-4 | **Should know.** Do you accept "no HR means no employee self-service portal" as the product rule? | Surbhi | §4, and therefore most of the scope | Yes. |
| OQ-5 | Should `alvoraa_portal`'s `required_apps` be corrected to declare `hrms` (honest today, blocks the whole idea tomorrow), or left as-is and the two imports moved? | Surbhi / engineer | One line in `hooks.py` | Move the imports; leave `required_apps` as `erpnext` only, which then becomes true. |

## Assumptions

- `[ASSUMPTION]` `alvoraa_portal` must be installed on every tenant, including one with
  no HR, because it carries the login page, branding, provisioning API and control-plane
  reporting. Verified by reading the files; not verified by running a site without it.
- `[ASSUMPTION]` Frappe never fires a `doc_events`, `permission_query_conditions` or
  `has_permission` hook for a doctype that does not exist, so the HR hooks in
  `hooks.py` are inert rather than broken. **The engineer must prove this.**
- `[ASSUMPTION]` A no-HR tenant still wants ERPNext. Every non-HR shape I can justify
  (CRM, Finance, Selling, vendor/delivery) sits on ERPNext, and `hrms` depends on it
  anyway, so ERPNext stays unconditional.
- `[ASSUMPTION]` The vendor and driver portals genuinely have no `hrms` dependency.
  Their controllers are in `alvoraa_portal`; I did not read every line of them.

## Kill criteria

Stop this slice if any of these turns out to be true:

1. **No non-HR prospect exists and none is expected this quarter** (OQ-2) — then do the
   four bug fixes as maintenance and drop the rest.
2. **Installing `alvoraa_portal` on a bare ERPNext site turns out to need more than the
   two import moves and the one index guard** — if the engineer finds a third or fourth
   structural dependency, the cost stops matching a customer who does not exist.
3. **The employee portal turns out to be reachable and load-bearing for a no-HR tenant**
   — if the vendor or driver portal shares the HR frame, §4's clean cut is wrong and the
   whole brief needs rewriting.

## Handoff note

To whoever picks this up: the single most valuable thing in this brief is §4 — the
employee portal *is* an HR product, and accepting that turns a multi-week job into a
one-day one. The second most valuable is §5, where one of the four claims I was handed
was wrong (`branch_scope` is already guarded) and two new problems appeared (HR roles in
`tenant_setup.py`, and the `"hrms"` marker in `tenant_api.create_tenant`). **Do not plan
from the original list; plan from §5.** Before any design work, get answers to OQ-2 and
OQ-3 — they change the size of this slice more than anything else in the document.

I have not run a bench and have not written code. Every "Confirmed" above comes from
reading the files named; everything I could not check is marked `[Needs validation]`.
