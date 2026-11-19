# 084 Employee regularisation window: UX opportunities scan

**Mode:** opportunities scan (recommend, do not decide). **Date:** 19 Nov 2026.
**Author:** `hrms-ux-designer`. **Risk tier:** 2 (a new setting that changes what an employee can do; not pay or data deletion). One tier up is fair, because it narrows something employees have today.

## 0. What I read, and what I did not

- **Read:** `/Users/mac/hr-app`, branch `dev` at `a57764c4`. Code only.
- **Not done: no browser capture.** `hrlocal-bench` is not running (`docker ps` showed other containers only), and the shared bench mounts the stale main checkout in any case (memory: shared-bench-cannot-test-a-branch). So every "today" below is **read in code, not seen on screen**, and I say prototype or code each time. No prototype exists for this slice yet.
- **Not seen:** the Grace screenshot. I rely on the brief's description of it.
- **Logins:** none used. Nothing on any tenant was touched.

## 1. Bottom line

1. **There are two employee screens, not one, and the brief names only one.** A limit set for one will leak through the other (section 2).
2. **The manager setting already shows the pattern we need.** On the day sheet, a day outside the manager's window shows a sentence with the exact oldest day, instead of a form that would fail. The employee version should reuse it. That is the answer to "tell them before they type".
3. **The text beside the existing manager field will become false.** It says the window "does not limit ... an employee asking about their own day". The day this slice ships, that sentence is wrong. That is the same drift that bit Grace.
4. **Competitors all let the admin set a number of days back (Keka, Zoho People, greytHR: seen in help pages, 19 Nov 2026).** None of the help pages I could read says what the employee is told when refused, and none mentions a joiner exception.

## 2. The screens as they are (code, 19 Nov 2026)

### 2.1 Org settings, "Attendance rules" card

`templates/includes/ess/parts/org-settings.html`, lines 120-152; JS `public/js/ess/portal.js` ~23400-23530 (**code**).

| Row | Words today |
|---|---|
| Switch `org-on-behalf-on` | "Let a manager ask for a day to be fixed for their team" |
| Sub-field `org-filing-window` (indented, number, 0-30, placeholder "No limit") | "How far back a manager can ask" |
| Its hint (about 100 words) | "...Counted in working days, using the employee's own holiday list... **It does not limit HR, and it does not limit an employee asking about their own day**... Use 0 to let a manager ask about today only." |
| Save message, blank | "Saved. There is no limit: a manager can ask about any past day." |

Facts that matter for design:
- Saves on change, no Save button. Confirmation is one coloured line at the top of the card.
- The box is greyed with the switch (`orgOnBehalfApply`). A limit on something nobody may do is hidden from use, on purpose.
- Whole card hidden unless HR Manager or System Manager. A store-scoped HR person sees it greyed with "Only HR with company-wide access can change these." (`orgLoadAttendanceRules`).
- Stored as a Frappe default, key `alvoraa_manager_filing_window_days`. Blank is no limit, 0 is today only. `attendance_correction.py:1405-1417`.

### 2.2 The employee side: two paths into the same doctype

| | **A. Day sheet, "Ask HR to fix this day"** | **B. `#att-req` "Attendance Request"** |
|---|---|---|
| Where | Attendance month, tap a day (`acForm`, `acSubmit`, portal.js ~6134-6350) | Sidebar item `nav-att-req`, panel in `parts/requests.html:39-85` |
| Server call | `attendance_correction.raise_correction` | `hr_api.submit_attendance_request` |
| Date input | A day already on the sheet. The person cannot type a date | **Two free date boxes, From and To. No `min`.** Today is pre-filled |
| Reasons | From the server (`reasons()`), each with help and "The day would be marked X" | Six fixed options in the HTML (Work From Home, On Duty, Field Work, Training, Outdoor Work, Other) |
| Date checks on the server | End not before start; not in the future (`attendance_correction.py:1125-1128`) | **None.** It builds the doc and inserts with `ignore_permissions=True` (`hr_api.py:2886-2903`) |
| Who sees the nav item | Part of Attendance | Only if `frappe.has_permission("Attendance Request","create")` (`hr_api.py:1688`). I did not check which roles hold it on PPJ or Grace |
| Words on refusal | `toast(e.message)` | `toast(e.message)` |
| After a refusal, is typed text kept? | Yes. The form closes only on success (`acState.open = null` after the call) | Yes. `clearForm` runs only on success |

**Consequence (proven by reading both functions).** A limit enforced only inside `raise_correction` would not stop path B at all. And path B accepts a **range** ("From" to "To"), so one request can reach back further than the limit on its first day. The slice has to say which of the two it binds. My recommendation: **both, with one boundary worked out in one place** (`manager_filing_from` is the existing example: "ONE derivation for the guard and for both screens", `attendance_correction.py:1422`). I have not checked how a range that straddles the boundary should behave; see question Q3.

⚠ DECISION 1 for the brief: does the limit bind path A, path B, or both? Owner: Surbhi, with `hrms-fullstack-engineer` on whether B can share the check. Blocks: every acceptance criterion.

### 2.3 What an employee sees today for an old date

- Path A: any past day on the sheet has the form. Pressing "Ask HR to fix this day" sends it. Nothing refuses (**code**; the endpoint has no past limit and a comment says so: "an employee raising their OWN day ... is not bounded").
- Path B: pick any date, in the past or today. Nothing refuses.
- **So there is no refusal wording today to look at.** The only existing refusal wording is the manager's, and it is good (section 2.4).

### 2.4 The pattern to reuse: the manager's day sheet

When `can_request` is true and the day is older than the server's boundary, the day sheet **replaces the form with one sentence** (portal.js 6200-6209, **code**):

> "This day is outside the window a manager can file within, so it is HR's to correct. The oldest day you can raise here is **{date}**, counted in {basis}."

Why this is the right model for employees:
- The boundary comes **from the server** (`can_request_from`, `can_request_basis`), not re-worked in the browser. The JS comment says why: "picking the wording here would eventually disagree with the refusal".
- It names a **date**, not a count. A date cannot drift from the behaviour; "48 hours" and "3 days" can.
- No form is drawn, so nobody writes three sentences first.

The manager's server refusal also names a way out: "ask HR to correct it" and "The oldest day you can file for is {date}". (`attendance_correction.py:1455-1460`.)

## 3. Why Grace happened, as a UX failure (from the brief)

| What went wrong | The design fault | Fix to recommend |
|---|---|---|
| Message said 48 hours, code allowed 3 days | Words written by hand beside a rule coded separately. Nothing derives one from the other | The sentence is **built from the boundary date the server returns**. Never a typed-in number in a string |
| Three sentences typed, then refused | The refusal arrived after the effort | Show the limit **before** the form (section 5.2) |
| New joiner blocked on their own joining day | The rule knows nothing about joiners; a human would have waved it through | Refusal leads to HR with a route, not a dead end (5.3, 5.4) |

## 4. Competitors (whole products, what is documented)

Method: web search and fetch on 19 Nov 2026. No trial accounts. **Read** = a help page I opened or a search summary of one; **recall** = from memory, needs checking. I could not open Keka's own article (HTTP 403, as the checklist warned); its details come from search summaries of its help-centre pages, which I label that way.

| Product | What the admin can set | What the employee sees | Label |
|---|---|---|---|
| **Keka** | Tick "Let employees regularize up to X days after the incident" in the capture scheme. A separate tick for adjusting past-dated time entries. A separate cap on number of requests per period | Employees see **their remaining balance when they submit**: total allowed, used, remaining, and a validation error if over. This is the "show it before" idea, applied to the count cap | read (search summary of help.keka.com articles, 19 Nov 2026). Exact refusal wording not seen |
| **Zoho People** | "Restrict Requests Within a Specific Number of Days" (their example: 7), "Limit Regularization Requests Per Time Period" (example: 1 day per week), "Allow Regularization Requests for Future Dates and Times". Another admin guide example uses 2 days | Not stated on the page I opened | read (Zoho People administrator guide, opened 19 Nov 2026) |
| **greytHR** | Under Workflows, Regularization and Permission policy, Date Criteria: "Employee can apply for past date(s)" or future date(s), and the number of days. A separate monthly cap field in Attendance Policy | The page I opened has no employee-facing error text. Their ESS help says the Quick Add button works only for past exception days | read (greytHR admin help, opened 19 Nov 2026). No joiner exception mentioned on that page |
| **uKnowva, Akrivia** (not in your list) | A "block backdated regularization" threshold in days (example: 3). A per-month cap and a separate "back days" | Not checked | read, search summary only |
| **Darwinbox** | I **could not find any Darwinbox page** on a back-dating window or a monthly cap. That is "I did not find it", not "it is not there". Darwinbox help is mostly behind a customer login | Not known | not checked |
| **Workday** | Not checked. `[recall: verify]` Workday time entry is usually controlled by calendar and period lock rather than "N days back" | Not known | recall, not checked |
| **BambooHR** | Not checked. `[recall: verify]` BambooHR time off and timesheets are not built around "regularisation" as an Indian HRMS means it | Not known | recall, not checked |

**What the evidence supports (and no more):**
- Three of the three Indian products I could read let the admin set **a number of days back**, in days. Keka and Zoho pair it with a **separate count cap** per period. The count cap is what Grace also had (3 per month). **It is not in this slice's request; see section 7.**
- The only product where I saw the employee's moment described is Keka, and only for the count cap (balance shown at submit). I found no source that shows "before they type" for the days-back limit. That is a gap in what I could read, not proof that nobody does it.
- No help page I opened mentions joiners or people returning from leave. I did not look for it elsewhere.

## 5. Ideas by persona

Lowest rung on the ladder first (`no-over-engineering.md`). Every idea below is rung 3 or 4 (existing setting mechanism, a few lines of code on existing screens). None needs a new DocType, page or settings screen.

### 5.1 HR Manager: understanding what they are setting without a second read

| Idea | Job | Evidence | Size |
|---|---|---|---|
| **One new row, same card, same mechanism.** "How far back an employee can ask about their own day", number 0-30, placeholder "No limit", saves on change, a Frappe default like the manager key | Set it once, same as the manager one | The manager field is the template (2.1) | S |
| **Name the person in the label, always.** "...a manager can ask" / "...an employee can ask about their own day". The label alone should say who it binds | The 100-word hint exists because the label does not say enough | 2.1 | S |
| **Say the date in the save line.** "Saved. From today an employee can ask about days back to Mon 16 Nov." (worked out by the server with the same counter) | HR sees the effect of "3" as a real date, and the blank/0 trap shows itself | The manager save line says only "last 3 working days". Blank and 0 are opposite ends and are easy to mix up | S to M |
| **Cut the hint to what is not obvious**: working days on the employee's own holiday list; HR is never limited. Drop the long "does not limit ..." sentence, now that the label carries it | Less to read | The hint is 100 words today | S |
| **Place it as its own row, not under the manager switch.** The manager box is greyed when the manager switch is off. The employee box has nothing to do with that switch and must never grey with it | No false link between two settings | `orgOnBehalfApply` greys by the manager switch only | S |

### 5.2 Employee: finding out before typing

| Idea | Where | Evidence | Size |
|---|---|---|---|
| **Path A: the day sheet shows the sentence instead of the form** for a day past the boundary, exactly like the manager's sentence in 2.4 but in the person's own words | Day sheet | Pattern exists and is proven for managers | S |
| **Path B: a one-line note under the page title** saying the oldest day, and `min` on both date boxes so the phone's date picker greys older days | `#att-req` | Android and iOS date pickers honour `min` `[recall: verify]`. But greying is silent, so the note must say why | S |
| **Say it with a date, never a count of hours or days.** "You can ask about days from Mon 16 Nov." | Both | Section 3: 48 hours vs 3 days | S |
| **The refusal from the server stays as the backstop** and keeps what they typed (it does today on both paths) | Both | 2.2 | S |
| **Put the refusal beside the button, not only in a toast.** Both paths use `toast(e.message)` for server errors. A toast goes away; a refused person needs to reread it, and Hindi runs about 30% longer | Both | Toast code read; its on-screen time **not checked** | S |

### 5.3 Employee told so they go to HR instead of giving up

What I found when I searched: there is **no "contact HR" action** on either screen. Surfaces I searched: the day sheet (`acForm`, the manager's outside-window sentence), `#att-req`, and `portal.js` / the ESS templates for the phrases "Ask HR", "Contact HR", "Message HR" (only plain text hints such as "Ask HR if this is wrong"; no button or form). I did not search the Desk or the Frappe helpdesk, and I did not check whether HR has a request route that bypasses the window (the code comment says HR's own manual route is unbounded; I took that as given).

Recommendation (words, not a new feature):

> "This day is older than your company allows you to raise yourself. HR can still fix it. Tell HR which day and why. The oldest day you can raise yourself is **Mon 16 Nov**."

- Names **HR** and says HR **can** fix it. "Cannot" without "but HR can" is how people give up.
- Says what to tell HR.
- Ends on the one number they can act on.

⚠ DECISION 2: is a sentence enough, or must there be a way to reach HR from the refusal (a pre-filled message, a link)? A sentence is the smallest thing. A button needs a place for the message to land that I have not found. Owner: Surbhi, with `hrms-fullstack-engineer` on what exists. Recommendation: **the sentence only** in this slice.

### 5.4 Joiners and people returning from leave

What the code does (proven by grep for `date_of_joining` in `attendance_correction.py`: **no hits**): the window counts back from **today** and knows nothing about joining, leaving or leave. Three people it touches:

| Person | The risk | Options (I recommend; you decide) |
|---|---|---|
| **New joiner, first day missed** (e.g. biometric not yet enrolled; the Grace case) | Their own first day is the day most likely to be wrong, and the day nobody has set up yet. A short window refuses exactly this day | **a)** do nothing special; the refusal says "HR can still fix it" (5.3). **b)** never refuse the employee's joining date. **c)** count the window from the later of the day and the account's first sign-in. a) is the smallest. b) is one comparison but needs a rule to be written and tested. c) needs a first-sign-in date I did not look for |
| **Returning from long leave** | A day missed in the first days back is inside the window. A day missed **before** the leave (and found late) is outside it, and nothing says why | a) as above. A second idea, "start counting from the return date", needs the leave dates read; I have not checked how |
| **Someone who has left** | Not in the brief | Not designed |

⚠ DECISION 3 (Surbhi, with the PM): joiners. My recommendation is a), the sentence and HR's route, because the Grace failure was "no human wave-through", and the sentence in 5.3 points to the human. If you want b), say so and the BA writes it as one extra rule with its own test. I would not do c) without first knowing how many joiners are really blocked.

## 6. Contradiction risks when both settings are on

| # | Risk | Why it reads wrong | Recommendation |
|---|---|---|---|
| C1 | **The old hint becomes false.** "It does not limit ... an employee asking about their own day" | A statement of what the setting does that stops being true on release day, with no test to catch it | Reword in this slice. Add to the BA's acceptance criteria that no string says "does not limit an employee" once the setting exists |
| C2 | **Code comments say the opposite too.** `attendance_correction.py` (the block above `MANAGER_ON_BEHALF_KEY`) and the "Never applied to somebody's own day" comment near line 656 | Whoever opens the code later reads the old rule | Engineer to update with the change |
| C3 | **Employee window shorter than manager window** (e.g. employee 2, manager blank) | "My own manager can ask about last month for me, but I cannot." Looks backwards | Say plainly where they sit side by side. The label of each names its person. HR sees both rows next to each other. I would **not** block the combination: HR may want it, since a manager vouches in someone's name and HR sees who vouched |
| C4 | **Different units** | Manager is "working days"; if the employee one were hours or calendar days they could not be compared | **Working days on the person's own holiday list, for both**, from the one existing counter (`_working_days_away`) |
| C5 | **Blank versus 0, twice** | Two boxes with the same trap. Someone who types 0 to "turn it off" on one box closes it to today only | Same placeholder "No limit" and the same save sentence, which says the date, on both |
| C6 | **A manager's window longer than the employee's** also means a manager can fix **for** someone a day the person cannot raise themselves | An odd route to HR | Same as C3. Leave it, but show both rows together |
| C7 | **Manager's switch off, employee's window on** | Nothing contradicts: the employee row stays live. But the manager row is greyed beside it and a reader may think both are greyed | Place the employee row **above** the manager switch, or visibly separate (own heading "Employee, own day") so it is not read as part of the indented group |
| C8 | **The manager's refusal says "ask HR"; the employee's says "HR can still fix it"** | Same idea in two voices | Use one phrase for HR's route in both |

## 7. Not in this slice (for you to decide; I recommend none of them now)

- A **cap on the number of requests per month** (Grace had 3). Keka, Zoho and greytHR all offer one (read). It is a different setting with a different failure ("you used 3 of 3"). It was not asked for here.
- A **warning when HR sets a very short window**. Not asked.
- **A count of refusals** for HR or the CXO ("12 requests refused this month"). Would show whether the limit is too tight. Not asked, and would need a place to store refusals that does not exist today as far as I read.
- **Per-branch or per-employee windows.** Not asked.
- **Auto-forward the refused request to HR.** A different feature (5.3).

## 8. Personas: what changes

| Persona | What changes |
|---|---|
| **Employee** (the one this affects) | Loses an unlimited ability they have today **if HR sets a number**. With the default blank, nothing changes. They see the boundary before they type. One-way rule check: HR chooses it, not the manager. A **manager's convenience is not being bought with the employee's**: HR owns it and HR's own route stays unlimited |
| **Frontline / shift employee** | Same screens on a 360 px phone. The sentence must fit at 200% text and in Hindi, with the date as a value in the string (`drT` with an argument, as the existing code does). Not tested; no browser capture was possible |
| **Line manager** | Nothing changes on their screen. They may meet "your employee cannot raise this day" only as the C3 oddity |
| **HR Manager** | One new row, same card, same behaviour as the manager row. A save line that says the date. HR's own route is untouched |
| **CXO** | Nothing. This is not a CXO surface and I would not add one |

## 9. Subtract pass

Removed from my own draft ideas: a live preview widget on the settings row (the save line says the date already), a "who this binds" table inside the card (the label does it), an HR-side refusal log, a joiner auto-exemption, and a monthly cap. Kept: one row, one sentence, one boundary date. I removed nothing else.

## 10. Questions that change what gets built

| # | Question | Why it matters | My temporary assumption |
|---|---|---|---|
| Q1 | Which employee path does the limit bind: A, B or both (⚠ DECISION 1)? | B has no checks today | Both |
| Q2 | Is `#att-req` in use on Grace and DTC? Which roles can see it? I read the gate, not a tenant | If nobody uses B, binding it costs little; if many do, it is the main path | Unknown, not checked |
| Q3 | A range (From to To) that starts outside the window and ends inside it: refuse the whole request, or only the old part? | Only B has ranges | Refuse the whole request and name the oldest allowed day |
| Q4 | Joiners (⚠ DECISION 3) | See 5.4 | Option a) |
| Q5 | Is a sentence enough for the refused person (⚠ DECISION 2)? | See 5.3 | Yes |
| Q6 | Is the Grace Server Script to be removed once this ships? Its hidden rule and the new setting would both run | Two rules, two sets of words, one person's screen | `hrms-business-analyst` / Surbhi to settle with Grace |

## 11. Accessibility and privacy notes for the next stage

- The new input needs a real `<label>` (the card uses `gp-label`), and the refusal sentence needs `role="status"` or equivalent, as `org-attrules-msg` has.
- Never show the reason someone was absent to anyone, and never put an employee's name in the refusal. The sentence needs the boundary date only.
- Grey dates on a date picker (`min`) are colour-and-position only. The sentence beside it is the non-visual signal.

## 12. Verification record

- **Proven (read in `/Users/mac/hr-app`, `dev` at `a57764c4`):** all file and line references in 2.1, 2.2, 2.4, 6; that `attendance_correction.py` has no mention of `date_of_joining`; that `submit_attendance_request` has no date checks.
- **Inferred:** that path B's range lets a request reach back past the boundary (from reading `submit_attendance_request`, which stores both dates unchanged); that the toast disappears quickly (not measured).
- **Not checked:** any live screen; which tenant uses `#att-req`; the Grace screenshot; Darwinbox, Workday and BambooHR; Keka's own article text; what HR can see of a refused request.
- **Sources (opened 19 Nov 2026):** [Zoho People regularization settings](https://help.zoho.com/portal/en/kb/people/administrator-guide/attendance-management/settings/articles/attendance-regularization-zp); [greytHR regularization and permission policy](https://www.greythr.com/help-admin/workflows/regularization-permission-policy/); [Keka: restrict regularizations for past days](https://help.keka.com/hc/en-us/articles/39946614770321-How-can-an-employee-Regularize-his-attendance) (page blocked; read through search summaries only); [uKnowva](https://docs.uknowva.com/hr-and-admin/leaves-and-attendance/attendance/280-how-to-block-backdated-attendance-leave-regularization-in-uknowva) (search summary only).
