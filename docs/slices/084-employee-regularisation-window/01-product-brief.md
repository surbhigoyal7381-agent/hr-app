---
slice: 084-employee-regularisation-window
artifact: 01-product-brief
author: hrms-product-manager
date: 2026-11-19
status: draft
inputs: [01a-ux-opportunities.md, 07-devops-inputs.md §1]
---

# 084 Let HR set how far back an employee can ask to fix a day

**Risk tier: 2** (new setting, narrows something employees have today; no pay or data deletion). One tier up is fair, because it takes a right away from employees the moment HR types a number. **Rung on the ladder: 2 (a setting) plus 4 (a few lines of code in the existing check).** Recommendation only. Surbhi decides.

## Bottom line

1. **Build it: one setting, one shared check, bound on both employee paths, boundary shown before the employee types.** About the same size as the manager setting.
2. **Cap on requests per month: out of this slice.** Reasons in section 4.
3. **Bad news first, in bold:** **if only one employee path is bound, the limit is decoration.** The `#att-req` screen takes any date and checks nothing today. Also **Grace keeps its hidden 3-a-month script after this ships**, because the cap is out. So "HR stops writing Server Scripts" is only half true for Grace.
4. **Default is blank = no limit.** Every tenant keeps what it has today until HR chooses a number.

## What I checked, and what I could not

- **Read (proven):** `/Users/mac/hr-app`, branch `dev`. `attendance_correction.py` lines 1105-1130 (`raise_correction`: refuses end-before-start and future start only) and 1383-1459 (the manager window, its blank/0 reading and `manager_filing_from`); `hr_api.py` 2885-2902 (`submit_attendance_request`: no date check, `ignore_permissions=True`). The key string appears in 3 files (1 Python, 1 template, 1 JS). This agrees with your facts 1, 2 and 3. I found nothing to flag as wrong.
- **One detail to add to fact 3:** `raise_correction` also takes a `to_date`, so it is also a range on the server even though the day sheet only offers one day. The check must look at the **first** day of the range on both paths, as the manager check does (`from_date`).
- **Could not run:** `git rev-list --left-right --count dev...origin/dev`. This session has no shell tool. **I cannot say how far behind `origin/dev` this checkout is.** Your note and the DevOps note both name `a57764c4`; I am relying on that. Before anyone says "X is not built" from this brief, run the command.
- **Not checked:** Frappe HR's own `Attendance Request` for a back-date limit (Frappe HR source is not on this Mac; the DevOps note says the same). I looked for a bench copy and the search timed out. **I am not claiming standard Frappe HR has no such setting.** The engineer should grep it before building. If it does ship one, this slice becomes configuration plus the second path.
- **`docs/product/priorities/` is empty.** There is no earlier Kano review to carry a class from, so section 4 classifies it now.

## 1. Job to be done

**Persona: HR Manager** (sets it). **Employee** (lives under it). The CXO is not touched.

> "As an HR head, when an employee raises a day from three weeks ago, I want the company's own rule to decide, set by me in one place, so I do not need an engineer to write a hidden script."

> "As an employee who missed a punch, I want to be told the oldest day I can raise **before** I write three sentences, so I do not get refused after the effort."

## 2. Current pain (a story, not a statistic)

I have no count of refused requests and will not invent one. The story is real and dated:

On 19 Nov 2026 an employee at Grace could not regularise their joining day, 11 Nov. The product had no limit setting, so Grace had written its own Server Script (code kept inside the database, which nobody reads in a release). That script said "48 hours" but allowed three days, and it blocked a case a person would have waved through. The limit was taken off Grace that day; a cap of 3 per employee per month stays. **Whether any other tenant did the same is unknown** (section 9).

## 3. Competitors (whole products)

Source: the UX scan, searched 19 Nov 2026. I did not re-search. I add only the product lens.

| Capability | Keka | Zoho People | greytHR | Frappe HR standard | Us today |
|---|---|---|---|---|---|
| Admin sets days-back for employee regularisation | Yes (read, search summary of help pages, 19 Nov) | Yes, "Restrict requests within a number of days" (read, admin guide, 19 Nov) | Yes, date criteria (read, admin help, 19 Nov) | **Not checked** | **No** |
| Separate cap on requests per period | Yes (read, summary) | Yes (read) | Yes, in Attendance Policy (read) | Not checked | No (Grace has a private one) |
| Shows the employee the limit before they submit | Only the count balance, not the days-back (read, summary) | Not stated | Not stated | Not checked | No |
| Joiner or returning-from-leave exception | Not mentioned on pages I could read | Not mentioned | Not mentioned | Not checked | No |

Darwinbox: not found. Workday, BambooHR: not checked. Pricing tier for any of these: **not found**, so I say nothing about plans.

**What we will deliberately NOT do that they do:** (a) a monthly request cap in this slice; (b) a per-branch or per-employee window; (c) a "balance" widget. Reason: our buyer is a one-person HR on a small tenant. Each extra setting is one more box to get wrong, and we already have one blank-versus-0 trap to explain. **What we do that I found no source for:** the employee sees a **date**, built by the server, before they type. That claim is "I found no source", not "nobody does it".

## 3a. Three ways, and could we not build it?

| Way | What | Verdict |
|---|---|---|
| **Conventional** | A new setting, checked inside `raise_correction` only, with a refusal message | Rejected. Leaves `#att-req` open, so the setting does nothing for anyone who uses that screen |
| **Better (recommended)** | Same setting, one shared function that works out the oldest day, called by both employee paths and by both screens | The manager setting already works this way. Smallest thing that actually binds |
| **Reimagined** | A single "who can file for what, how far back, how many" policy record per tenant | Rejected. It is the rules engine the no-over-engineering file bans. Nobody has asked for it |
| **Build nothing?** | Leave HR to write Server Scripts | Rejected. That is the failure that started this. But note: **do nothing is the right answer for any tenant that has no limit**, and the blank default delivers exactly that |

## 4. Kano class and demand

- **Days-back limit: Performance, `proxy`** (not surveyed). Proxy reasoning: three Indian products I could read ship it (read, 19 Nov 2026), so absence will be noticed by a buyer comparing them; but I have **no lost deal, no support ticket and no survey** showing buyers are angry without it, so I do not call it Must-be. For the **employee**, it is a restriction and may read as **Reverse**. That is why the default is blank.
- **Demand evidence I actually have:** one tenant (Grace) built its own rule, and Surbhi asked for the setting. That is **one customer and one founder request**. **Evidence required:** a second tenant's answer. A survey kit is not worth writing for one setting; the question to ask DTC's HR is in section 9.
- **What would change the class:** if aahr, dtc, tft or demo each turn out to have their own script, it moves toward Must-be. If none do, it is a nice-to-have for one customer and the slice is smaller than it looks.

### Is the monthly cap in or out? **Out.**

| For | Against |
|---|---|
| Grace built one. Keka, Zoho and greytHR all ship one (read) | Surbhi did not ask for it, and the ask was explicit: "same as currently there is a setting for managers". That is a days-back window |
| Without it Grace keeps its hidden script | It is a different setting with a different failure ("you used 3 of 3"), a different place to count (requests per employee per month, on a doctype with two writers), and a different screen (balance) |
| | It is one tenant's rule. Counting also needs a decision (do refused or cancelled requests count?) that nobody has made |

**Recommendation: out. Trigger to revisit:** Grace asks to retire its script, or a second tenant asks. Then it is its own slice with its own brief. I name the cost plainly: **Grace stays on a hidden rule it cannot see in settings, and the real outcome is not reached for that tenant.** Surbhi may overrule this. If she does, it is a second setting, not an extension of this one.

## 5. Persona enhancements through the employee portal

| Persona | How the portal improves | Job it serves | In this slice? | Why |
|---|---|---|---|---|
| **Employee** | Day sheet shows one sentence with the oldest allowed date instead of a form that will fail; `#att-req` shows the same line under the title and greys older days | Not wasting effort | **Yes** | This is the WOW and the Grace lesson |
| **Frontline employee** | Same sentence, short, date as a value, fits a 360 px phone and Hindi | Same, on a cheap phone | **Yes** (wording only; Hindi text needs a UX check) | No extra build; the string is the work |
| **Line manager** | Nothing changes. They may see an oddity: manager window longer than employee window | None | **No** | Leave it, show both rows together in settings (below) |
| **HR Manager** | One new row in "Attendance rules"; label names who it binds; save line says the date ("Saved. From today an employee can ask about days back to Mon 16 Nov.") | Set it once, see its effect as a real date | **Yes** | Cheap. Stops the blank-versus-0 mix-up |
| **HR Manager** | Reword the manager hint, which will be **false on release day** ("does not limit ... an employee asking about their own day") | Truthful settings | **Yes, required** | That is the Grace drift again |
| **CXO** | Nothing | None | **No** | Not a CXO surface |
| Joiners / returning from leave | Refusal says "HR can still fix it" | Not giving up | **Sentence only** | See section 8, decision 1 |
| Refusal log, short-window warning, auto-forward to HR, per-branch windows | | | **No** | Not asked; each needs new storage or a new route |

## 6. The WOW

An employee opens the Attendance Request screen, or taps an old day on the sheet. Before any typing, a line sits under the title:

> **"You can ask about days from Mon 16 Nov. Older than that? HR can still fix it. Tell HR which day and why."**

On the day sheet, a day older than that shows this sentence **instead of the form**. The date comes from the server, not a number in the text, so it can never say "48 hours" when the code says three days. For HR, the save line says the date too.

Honest note: this is a quiet moment, not a showpiece. The value is that the Grace failure cannot happen again: no refusal after the effort, no number that disagrees with the code.

## 7. Thin slice

| Pile | Item |
|---|---|
| **Needed to validate now** | The setting row (0-30 days, blank = no limit, 0 = today only, saves on change, same key mechanism as the manager one, written through the existing `set_org_setting`) |
| **Needed to validate now** | One function works out the oldest day (working days on the person's own holiday list, same counter as the manager window). `raise_correction` and `submit_attendance_request` both call it and refuse a request whose **first day** is older. A range that starts too early is refused whole, naming the oldest allowed day |
| **Needed before it ships** | Boundary date returned when the screen loads (one call per page load, not per row); day sheet and `#att-req` show it before typing; refusal wording uses the date and says HR can still fix it; the old "does not limit an employee" hint and the two code comments (UX scan C1, C2) are rewritten |
| **Needed before it ships** | Blank returns before any holiday lookup, so tenants with no limit pay one setting read (DevOps OPS-5, OPS-2) |
| **Worth doing later** | Joiner exception; "your window vs manager's window" side-by-side note |
| **Not doing** | Monthly cap; refusal log; per-branch or per-company window; auto-forward; hours-based rule; a "future date" check on `#att-req` (WFH and field work are legitimately raised ahead of time, and **the limit looks backwards only**) |
| **Out of scope, say so** | HR's own route, which stays unlimited; the Grace Server Script (see section 9) |

**Known limit, say it in the setting's hint:** a Frappe default has one value per tenant site. **A tenant with two companies cannot have two windows.** The manager setting has the same limit. Acceptable; no tenant I know of needs it, but I have not asked.

## 8. Decisions for Surbhi

1. **Joiners.** Recommend **a): the refusal sentence and HR's route only**, because HR can already fix any day. Cost to be honest about: this is the Grace case, and under a short window the joiner is refused again, then HR steps in. Option **b) never refuse the joining day** is one comparison plus one test. Choose b) if you do not want HR pulled in for it. Not **c)** (a first-sign-in date I did not look for).
2. **Sentence or a button to reach HR?** Recommend **sentence only**; no route for a message to land in was found.
3. **A range that starts outside the window:** recommend refuse the whole request. (UX Q3.)

## 9. Run side

DevOps §1 reads clean. **No new app, queue, worker, storage or money cost; about 4-5 small reads per submit; nothing to restart or clear.** It does not change the size of the slice. Adopt OPS-3 (read the Server Script before enabling on Grace) and OPS-5 (blank means no limit, 0 means today only).

## 10. Success measures

| Measure | Type | Baseline | Target | How |
|---|---|---|---|---|
| Both employee paths refuse a day older than the boundary, and the screen's date equals the refusal's date | Quality, leading | Today neither refuses | 100% in a test that presses Submit on both and reads the payload | Automated tests |
| Refusals after pressing Submit (wasted submissions) | Efficiency, leading | **Baseline unknown, measure first.** No refusal log exists today and I do not propose to build one | Falling, once a baseline exists | **Needs validation:** whether web server logs on dev keep the two endpoints' error replies long enough. Not checked |
| HR changes the value without an engineer | Adoption, lagging | Grace needed a script | One tenant has set a value in the screen and no hidden script enforces a time limit | Ask Surbhi; read Server Scripts on dev only |
| Tenants with their own hidden rule for this | Business, lagging | **Unknown** (only Grace confirmed) | 0 | Section 9 check |

"Fewer wasted submissions" is measurable once a baseline is taken. "HR stops writing Server Scripts" is the real outcome, and **only Grace can currently show it.** No logins or page views.

## 11. Thriving-workplace lens

| Lens | One line |
|---|---|
| Engagement | Clarity and agency: the limit is known before the effort. No effect on recognition |
| Collaboration | No effect |
| Inclusiveness | **Risk:** the new joiner, the person back from long leave, and the shift worker without a laptop who cannot wait for HR. Date shown, HR route named, blank default. Hindi length not tested |
| Transparency | The employee sees the rule and the exact date. Nothing about any person is revealed; the sentence carries a date only |

## 12. Regulatory read

1. **Regime:** employment practice; DPDP only lightly (no new personal data). **Not a lawyer.**
2. **Whose duty:** the employer's. The setting helps them apply their own written policy consistently.
3. **New:** one setting, one automatic refusal. It narrows a right employees have today, so **the employer should tell staff when it is turned on.** Counsel need not rule on this; HR should know.
4. **Honest downside:** the front-page version is "a software setting stops a worker fixing their pay-linked attendance". Defended by: HR's route stays open, the refusal names HR, and the default is no limit. **Risk:** a refused day that touches pay (missed punch -> absent). Show HR the date they are choosing before saving.

## 13. Risks (red-team)

| Risk | Answer |
|---|---|
| Only one path bound | Both bound; test presses both |
| Grace's script and the new setting both fire; the stricter wins silently | OPS-3: read the script first; set the same value and delete it in the same release, or leave blank until it is gone |
| Script counts calendar days, ours working days; differ by a day at weekends | Show the date, not a count |
| Typing 0 to "turn it off" closes it to today only | Placeholder "No limit"; save line says the date |
| Joiner refused again | Decision 1 |
| Employee window shorter than manager's looks backwards | Show both rows together; do not block |
| Employee leaves or manager changes mid-flow | Check uses the employee record, not the manager. Not affected |
| 10x data | Flat per submit (DevOps). Compute once per page load |
| Support tickets | "Why can't I raise Monday?" Answer is on the screen as a date |

## Subtract pass

**Removed from my own draft:** a monthly cap (to "later" with a trigger); a joiner rule (to a decision, default sentence only); a boundary endpoint and a cache for the setting (DevOps removed these too); a survey kit; a refusal counter; a "warning on a very short window". **Not removed:** the second employee path, because without it the slice does not do its job.

## Kill criteria

Stop and tell Surbhi if any of these is seen:
- Frappe HR already ships this setting (then it is configuration plus the second path, not new code).
- The check cannot be shared between `hr_api.submit_attendance_request` and `raise_correction` without touching the doctype or adding a hook on `Attendance Request`.
- Tenant checks show **no one but Grace** ever wanted a limit **and** Grace is happy with its script: then ship nothing and keep the Server Script visible instead.
- Fewer than a handful of employees use `#att-req` and the day sheet already has the sentence: bind only what is used.

## Open questions

| # | Question | Owner | Blocks |
|---|---|---|---|
| 1 | **Did aahr, dtc, tft or demo write their own rule?** Reading other tenants' scripts was refused as unauthorised. Smallest route: ask each HR contact, or the engineer greps **dev** only | Surbhi (who may ask) | Demand, Kano class, the "0 hidden rules" measure |
| 2 | Joiners: a), b) or c) | Surbhi | AC for the joining day |
| 3 | What happens to Grace's 3-a-month script and the cap (OPS-3) | Surbhi with Grace | Release on Grace |
| 4 | Does Frappe HR's `Attendance Request` ship a back-date limit? | Engineer, grep | Rung choice |
| 5 | Is `#att-req` used on Grace and DTC, and by which roles? | Surbhi / engineer on dev data | How much the second path matters |
| 6 | Is the checkout current? Run `git rev-list --left-right --count dev...origin/dev` | Whoever has a shell | Every "not built" claim here |

## Assumptions

- `[ASSUMPTION]` Blank stays the default and means no limit; 0 means today only (matches the manager setting and OPS-5).
- `[ASSUMPTION]` Working days on the person's own holiday list, same counter as the manager window.
- `[ASSUMPTION]` HR's own route stays unlimited (a code comment says so; I did not trace it).
- `[ASSUMPTION]` One window per tenant is enough (no two-company tenant asked).
- `[ASSUMPTION]` The Kano class (Performance, proxy) stands on three read help pages and one tenant's script. No survey.
- `[ASSUMPTION]` The day sheet can reuse the manager's "server returns the oldest day" pattern (UX scan section 2.4, read in code, not seen on screen).

---

## Gate 1 — Surbhi's decision, 19 November 2026

**Approved: build it.** With one change to the recommendation.

**The joining day is ALWAYS allowed.** Option (b), not the PM's recommended (a).
An employee may raise a regularisation for their own date of joining however
old it is, whatever the window says. The window applies to every other day.

Why it matters: this is the case that started the slice. A Grace joiner could
not fix their 11 November first day, and a human would have waved it through.
Relying on "ask HR" would have refused them again.

**Still open, and NOT answered at this gate** — carried into the spec:

1. Grace's remaining hidden rule (max 3 regularisations per employee per month).
   Retire it, or leave it running beside the new setting?
2. Whether aahr, dtc, tft or demo also wrote their own rules. Reading their
   Server Scripts was refused as unauthorised access to other tenants. Faster
   asked of each HR contact than found in code.
3. Whether `#att-req` is used on Grace and DTC, and by which roles.

**Raised at this gate and NOT part of this slice:** `hr_api.submit_attendance_request`
accepts any `from_date` and `to_date` a browser sends, checks neither, and inserts
with `ignore_permissions=True`. True today, before any of this work. Needs its own
ticket.
