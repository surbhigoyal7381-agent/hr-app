# UX learnings — Alvoraa

**Owner:** `hrms-ux-designer` · **Started:** 11 Sep 2026
Read first by the UX designer on every run, and written to at the end of every run.
The rules for adding, promoting and retiring entries are in
`.claude/agents/hrms-ux-designer.md` → *The learning loop*.

**Status ladder:** `heard` → `applied` → `confirmed` → `principle` · or `retired`.
Nothing here holds personal data, passwords or screenshots. Evidence lives in
`C:/Surbhi-Git/hrlocal-data/ux-review/`, outside the repo.

---

## Principles — confirmed

Rules the user has stated, or that the evidence has settled. These override the
defaults in the agent file.

| # | Principle | Why | Source |
|---|---|---|---|
| P1 | Plain, everyday English in documents **and** on screens. | The user's standing rule. | `CLAUDE.md` §6 |
| P2 | Benchmark competitors' **whole products** — manager, HR, performance, analytics — not only their self-service pages. | The user corrected a narrow benchmark mid-task. | Surbhi, 11 Sep 2026 |
| P3 | Build on the Alvoraa design-system tokens. Do not invent a palette. | The project's own system comes before a designer's taste. | `design_system.html`; review 11 Sep 2026 |
| P4 | Measure phone layouts; do not eyeball them. Check width beyond the screen, tap targets under 44px, field text under 16px, text under 12px. | Five root causes found by measuring, not by looking. | Mobile audit, slice 003 |
| P5 | Check a fact in the data before calling it a UI bug. | "Holiday" on Thursdays turned out to be the store's weekly off. The real bug was the label. | Review 11 Sep 2026 |
| P6 | Every design run ends with a clickable prototype. No design check without one. | The user reviews by clicking, not by reading a document. | Surbhi, 11 Sep 2026 |
| P7 | Persona-by-persona ideas for the employee portal come before the brief, in the opportunities scan. | The PM needs UX evidence to shape the slice, not a design after it is fixed. | Surbhi, 11 Sep 2026 |
| P8 | The Android field app follows **Material Design 3** (the platform's own design language), built on Alvoraa's tokens and floors: 48 px targets, nothing under 12 px, 16 px field and button text. | She tested the app on a real phone and called the screens "very awkward"; she approved an M3 redesign. | Surbhi, 26–27 Sep 2026 |

---

## Patterns — applied, not yet tested with users

Used in the 11 Sep 2026 prototype. Promote to `confirmed` only after the user agrees,
a usability test shows it, or the same need comes up again.

| Pattern | What it solves | Where it was used | Status |
|---|---|---|---|
| **One screen per failure**, each with a picture, one sentence, numbered steps and one button | A driver cannot parse a toast or an inline error while standing in the sun | Slice 008, 12 states | applied |
| **The server's own sentence wins when it names a real number** ("You are about 140 m from PPJ Noida") | A generic heading plus the real figure beats a rewritten vague one | Slice 008, E5 | applied |
| **No action button where no action would work** (blocked, left, not in plan offer only "Go back") | A button that fails again teaches a person the app is broken | Slice 008, E9–E11 | applied |
| **Keep the captured photo across a retry** | A driver refused for distance or signal should not pose twice | Slice 008, punch retry | applied |
| **Degrade, do not block**: camera off still allows the punch, result says "Photo: Not taken" | A guard who turned up must be marked present; the photo is evidence, not the rule | Slice 008, D2 | applied |
| **Sample mode inside the shipped page**, woken only by the literal server address `demo`, with a state switcher | Lets the user click every state with no backend, without a second throwaway file | Slice 008 | applied |
| **State in words beside the colour on every chip and button** ("Not checked in yet today") | Sunlight and cheap panels destroy colour differences | Slice 008, Home | applied |
| **Needs you** strip at the top of Home | Nothing told people what was due (review H1) | Prototype, Home | applied |
| Labelled menu grouped **Me · Time · Pay · Growth · Team · Company** | Icon-only menu; five attendance entries (G2, G3) | Prototype, menu | applied |
| Bell on every screen plus an **Inbox** with "Waiting on me" and "My requests" | No approvals entry on desktop (G4) | Prototype, Inbox | applied |
| **Exceptions before lists** for managers, with inline Approve / Decline | Off-track goal buried at the bottom (MH1, MH2) | Prototype, manager Home | applied |
| **Act in place** — tap an absent day to apply leave or fix attendance | Absent days had no action (AL1) | Prototype, Time | applied |
| **Explain the money** — "Why ₹548?" walks through the late rule, day by day | Lateness shown but never explained (MA3) | Prototype, Pay and Late rule | applied |
| **Guided self-review** — 5 steps, guidance per step, autosave, check before sending | Two equal buttons and no guidance (PF2, PF3) | Prototype, Self-review | applied |
| Phone bottom bar with **short labels** ("Time", not "Attendance & leave") | Long labels wrapped onto two lines | Prototype, phone | applied |
| **Check In** as the largest control on a phone | Check-in is the phone's main daily job (PH3) | Prototype, phone Home | applied |
| **Sample** tag on every invented number or name | Keeps a prototype honest with real tenant data | Review and prototype | applied |
| Rules-based suggestion that explains why it appeared ("Because a new joiner has a full-quarter target") | Nudges without AI, each with its reason | Prototype, manager Home | applied |
| **One label for every hidden figure** ("Hidden to protect a small group") plus a "Why is this hidden?" sheet — never "Fewer than 5 people" on the cell | The next-smallest group is hidden too; a size-based label would be false there and would mark which group is small | Slice 012 prototype v1 | applied |
| **Hidden stays hidden on drill-down**, and a "vs parent" comparison is hidden when the parent minus the group is small | Tapping into a group hidden for subtraction reasons, or reading "branch vs company", undoes the subtraction rule | Slice 012, LD1 and LD2 | applied |
| **Doubtful data left out of the headline, said in words, one tap to see the raw figure** | A leader quotes the big number; it should be the believable one, and honest about what was removed | Slice 012, Attendance card | applied |
| **"Not recorded", never 0 or 0%**, applied to every place the figure appears | Missing data shown as zero reads as a fact | Slice 012, Leave and People cards | applied |
| **Privacy setting = bounded stepper + live impact line + required reason + confirm that names the effect + history nobody can edit** | A privacy change must be deliberate and provable; the read-only role sees the value as text, not a greyed control | Slice 012, Leader view privacy | applied |
| **Setup-problem page with a message to copy** for the administrator | Fail closed without looking broken; the person knows exactly what to ask for | Slice 012, no company or branch linked | applied |
| **Part period compares with the same days of the earlier period** ("Up 0.3 points on 1–13 Aug") | 13 days against a whole month flatters every count | Slice 012, every change line | applied |
| **"Not shared" in cells; "Not shared: too few people in this group for a fair picture" in full**, explanation leads with fairness, then "can point at one person" | The user's chosen wording (15 Sep 2026). Retires the wording of the "Hidden to protect a small group" row above; the one-label-per-cell idea stays | Slice 012 prototype v2 | confirmed (user's words) |
| **"Needs review", never "Not recorded", 0 or 0%**, for figures with missing or implausible data; the "Why?" sheet gives a concrete example and says HR is checking; **the label must lead somewhere for HR** (a Data to review list) | "Not recorded" sounds final and blames nobody; "Needs review" says the number is coming and who acts. Retires the wording of the "Not recorded" row above | Slice 012 prototype v2, Leave and People cards, HR Data to review | confirmed (user's words) |
| **Scope switcher for a person with several scopes**: phone = "Showing" label + chip opening a radio sheet; desktop = visible radio row (button + list at 6+); "All" = combined totals plus a comparison table; Home remembers the last choice | Fail-closed "shows nothing" for a real, legitimate leader looks broken; the user asked for both the total and the split | Slice 012 prototype v2, D7 | applied |
| **Privacy rules follow the switcher**: small-group rule across the person's own set; not shared in "All" stays not shared alone; comparison with the parent needs both parent-minus-set and parent-minus-item to pass | Every new way of choosing a scope is a new subtraction path | Slice 012 prototype v2, LD10 | applied |
| **Honest history copy**: say exactly who can delete an audit record ("only the Administrator account"), not "nobody" | A privacy promise that is not strictly true is worse than a precise one | Slice 012 settings, from DevOps OPS-23 | applied |
| **Check before you show, use only at the end**: a one-time code is checked (live, eligible) before any name appears, and used up only at the final "Agree" | Nobody reads a notice or sees a name for a join that cannot work; stopping half-way costs nothing | Slice 013 prototype v1, join flow | applied |
| **"Is this you?" with the least identity** (first name, surname initial, job, company) and a "This is not me" that cancels after a confirm | Catches a forwarded code without showing a record to a stranger | Slice 013 prototype v1 | applied |
| **Explain before the system asks**: one screen saying why, at the first moment the permission is needed (camera at first scan, location at first Check In), never at launch | An Android prompt out of nowhere gets "Don't allow" | Slice 013 prototype v1 | applied |
| **Screens chosen by error code, numbers passed as values, "Code for HR" line at the bottom**; unknown code → "may be out of date, check for an update" | Old installed versions keep working when server wording changes; support calls start from the code | Slice 013 prototype v1, §8 of `01b` | applied |
| **"You" only when true**: an audit line says "you" only to the person who did it; everyone else sees the name | A brief's wording written from one reader's view is false for the others | Slice 013 desk, joined line (D13) | applied |
| **No button where the rule says no**, on HR screens too: a plain reason and a link to the setting that decides it, instead of a greyed "Invite" | Same idea as hiding unusable tabs, applied to desk actions | Slice 013 desk, not a field worker / app off | applied |
| **One person, two roles, two lists**: someone who is both a manager and an HR person gets a "My team" list and an HR list, never one merged list with hidden rules. On the HR list, rows from their own reporting line lose the action buttons and gain a sentence saying who acts instead | A merged list forces the product to decide silently which hat the person is wearing; two lists let the person decide, and make the conflict-of-interest rule visible | Slice 009 prototype v2, owner/HR view | applied |
| **The approved figure is the headline; anything pending is named beside it, never folded in** ("₹3.1 L is waiting for Sakshi Verma … the figure above does not move until it is approved") | A single bar makes a person believe their number moved when it has not. Evidence-first has to be visible, not just true | Slice 009, KPI card | applied |
| **Ask for the increment, show the total**: "How much since your last update?" with the running total in the hint, and a "what happens next" line before the button | People given a box next to a progress bar type the running total | Slice 009, log progress sheet | applied |
| **A frozen copy says when it was frozen and what still moves** ("copied into your review on 1 Oct … your live goals keep moving on the Goals page") | Two numbers for one thing looks like a bug unless the screen explains which is which | Slice 009, self-review step 1 | applied |
| **A tolerance shows the true measure and the verdict separately** ("Late by 12 min (within grace)", neutral chip, not amber) | Hiding the minutes looks like a cover-up; colouring them amber punishes a day that did not count | Slice 009, Time and the day sheet | applied |
| **A feature the tenant has not bought lives in settings under "Not switched on for …", with "Ask about it"** — never in a menu, never greyed | A buyer can ask for it; a shop assistant never meets a door that will not open | Slice 009, Org settings, vendor and driver portal | applied |
| **Phone rules are `@media` in the product; a phone frame in a prototype is the *same* rules copied by script under a wrapper class** | Hand-copying the rules lets the prototype and the product drift; a container query on the app wrapper breaks every fixed pop-up | Slice 009 prototype v2, D1 | applied |
| **The review scaffolding carries the in-product switches only when they are not in the product**: language and theme moved out of the demo bar and into the profile menu, so the design gets reviewed, not the scaffolding | If a control lives only on the demo bar, nobody checks whether it has a home in the product | Slice 009 prototype v2, D2 | applied |
| **Status card: colour + icon + words, with the rule inside it** ("Checked in / since 9:12 am", "Check in within 200 m of …") | A person must know where they stand in one look, in sunlight, without reading a list | Slice 013 M3 redesign, Home | applied |
| **Meaning colours do not follow the tenant's brand**: success (green) and warning (amber) are fixed tones of the design system's `--green` and `--amber`; only primary, secondary and surfaces follow the brand | A brand in green or red would otherwise make "checked in" and "wrong" look the same | Slice 013 M3 redesign, tokens | applied |
| **Consent tick and Agree in a fixed bottom bar**, the whole row as the target, Agree never greyed (unticked → the error and focus move) | A wall of text with a small box at the end; a greyed button does not say why | Slice 013 M3 redesign, notice | applied |
| **The result says the measured truth** ("About 13.2 km from …", "accuracy 14 m"), never the configured place name as if it were the position | The old result said "At {site}" whatever the distance | Slice 013 M3 redesign, result | applied |
| **At 150%+ text, a labelled top-bar action keeps its icon and spoken name but drops the word** — the one exception to words beside icons | At 200% the word pushed the company name down to "PP J…" | Slice 013 M3 redesign, measured | applied |

---

## Anti-patterns seen in Alvoraa

Each one was seen on a real screen. Check new designs against this list.

| Anti-pattern | Where it was seen | Finding |
|---|---|---|
| The top bar title never changes ("Home" on every page) | All 34 desktop screens | G1 |
| Icon-only navigation | Portal sidebar | G2 |
| A 40-row people grid on Home | Employee Home | H2 |
| Red used for an ordinary count, or for a full leave balance | Performance, leave rings | PF4, AL2 |
| One idea under two names (weekly off shown as "Holiday") | My Attendance vs Home | MA2 |
| A raw failure shown to a user ("Could not load progress approvals") | Team View | TV1 |
| Two buttons of equal weight for one decision | Self-review | PF2 |
| A red Delete beside every row | Org Settings | OS2 |
| Analyst words for one person ("person-days") | Attendance Insights | AI3 |
| Greyed-out tabs a person cannot open | Attendance Insights | AI2 |
| A different default month on screens that show the same data | Attendance Insights vs My Attendance | AI1 |
| Desktop layout rules leaking onto the phone | Mobile audit causes R1–R5 | PH1 |
| A headline aggregate with no "data up to" date and no check for impossible days (3 days of 100% absent gave a 65.8% attendance rate) | HR Analytics, owner | LV1 (slice 012) |
| HR work queues ("Pending approvals", "Confirmations due") mixed into a page an owner reads as the state of the business | HR Analytics | LV8 (slice 012) |
| Greyed-out tabs — **seen a second time** (store in-charge, "Organisation") | Attendance Insights | AI2, LV11 |
| Red for an ordinary number — **seen a second time** (0.1% leave use; "Female" bar) | HR Analytics | PF4, LV9 |
| One idea under two names — **seen a second time** ("manager" in the notice, "supervisor" on the result) | Field check-in page (read in code, not on screen) | MA2, FC-2 (slice 013) |

---

## Checklist additions

Items learned the hard way. Add these to the standard pre-handoff check.

- [ ] Hindi and Punjabi strings run longer. Check the layout with them, not only English.
- [ ] Notification badges sit outside the icon, not on top of it.
- [ ] Keyboard hints like "Ctrl K" never wrap.
- [ ] Links in section headers use the same style everywhere (no stray underline).
- [ ] Stock photos and decorative illustrations are not competitor evidence.
- [ ] Label each competitor claim: seen / read with date / `[recall — verify]`.
- [ ] Every total or rate shows the date its data runs to, and says so when a day looks impossible.
- [ ] Any number about leave, absence, ratings, leavers or pay: check the smallest group it can be cut to, and how a hidden group could be worked out by subtraction.
- [ ] Run read-only data scripts on the bench through standard input. Never `docker cp` — CLAUDE.md gates it.
- [ ] A "hidden" or "not recorded" state reaches **every** place that figure appears: cards, tables, total rows, today strips, Home cards.
- [ ] Small-group checks cover drill-down pages and "compared with the parent" lines, not only the table where the group first appears.
- [ ] A figure for part of a period is compared with the same days of the earlier period.
- [ ] A user-chosen label is checked against **every** case it will appear in; where it would be untrue, raise a decision with both options instead of changing it quietly.
- [ ] Any "needs review" or "data looks wrong" label on one persona's screen has a matching place where the persona who can fix it sees what to do.
- [ ] Group sizes for privacy are the people inside the figure for its period, not today's headcount.
- [ ] Every new scope control (switcher, filter, drill-down) gets the small-group and subtraction check again.
- [ ] Before designing a screen behind a login, check the persona actually **has** that login (frontline staff often have no email or password).
- [ ] When two existing surfaces are combined (app tabs, embedded pages), look for duplicates: two bottom bars, two buttons for one job with different rules, one word naming two places.
- [ ] For anything shipped through an app store, check every server message and version check that assumes "reload the page" still has a way out for an old installed version.
- [ ] When reusing an existing screen, read every state's words, not only the happy path: a status line can be untrue in a state nobody drew (008 said "Not checked in yet today" after a check-out).
- [ ] When a design records something new about a person (a phone model, a join time), check the consent notice says so, and plan the "notice has changed" screen with the new version.
- [ ] Review controls in a prototype must wrap and must not be sticky: they made a 360 px page scroll sideways and covered the phone in slice 013.
- [ ] Anything that scans a QR in India: plan for a UPI payment code being scanned by mistake.
- [ ] Measure the **off-screen** parts of a phone layout too. The slide-out menu is hidden by a transform, so a 37 px menu link passed every earlier look and failed the first measurement.
- [ ] Apply the right target rule per device: **24 px** is WCAG 2.2 AA on a mouse, **44 px** is our phone rule. Measuring everything at 44 px produces a false list on desktop and hides the real failures.
- [ ] Text links inside a sentence ("Inbox →", "My team") are targets too: give them a minimum height, or they measure 16–20 px.
- [ ] When a behaviour changes under a design (a copy, an increment, a grace period), check every **derived** label as well as the main one: "Arrived on time" became "Arrived within grace"; "No record" became "Marked absent".
- [ ] When the portal becomes the landing page, design the **empty, first-morning** state deliberately and put the speed budget in the design, not the footnote.
- [ ] Before accepting a token from the design system, check it against our own floors. `--fs-xs` was 11 px against a 12 px rule; raise it as a decision rather than working around it per screen.
- [ ] When a palette is made from a tenant's brand colour, test **black, grey and pale** seeds as well as the real ones. Material's default recipe turns black into pink; use the monochrome recipe when the seed has almost no colour (chroma under 8). PPJ's local brand colour is black.
- [ ] For every consent or setting a person can give in the app, check there is a screen to take it back. The server had `withdraw_agreement`; the app had no button for it.
- [ ] A label about where someone was must come from the measured value the server returns, not from the configured place name.
- [ ] Before recommending a component library, check it is still maintained and measure its size. `@material/web` has been in maintenance mode since June 2024; 9 components = 173 KB minified / 35.5 KB gzip (27 Sep 2026).
- [ ] Test every phone design at 200% text as well as 360 px. Two faults showed only there: a truncated company name and an unbreakable error code.

---

## Open items for the human

| Item | Owner | Blocks |
|---|---|---|
| My Attendance marks a 09:25 arrival "25 min late", but the shift starts at 09:30. Likely an engineering bug, not a design issue. Not yet investigated. | Engineering | Trust in lateness numbers; the late-rule explanation |
| Hindi and Punjabi labels in the prototype are machine drafts. | Surbhi, or a native reviewer | Any language work shipping |
| Competitor scorecard is not verified with trial accounts. | Surbhi | Quoting the scorecard externally |
| None of the prototype patterns has been tested with real users yet. | Surbhi | Promoting patterns to `confirmed` |
| Slice 008: how long check-in photos are kept (a DPDP obligation, brief §6). The field app tells the driver who can see the photo but not for how long. | Surbhi | Nothing for the demo; a real obligation after it |
| Slice 008: the Hindi strings in the field app are machine drafts. The EN/हिं switch is built but Hindi is in the brief's backlog. | Surbhi, or a native reviewer | Showing Hindi to a customer |
| ~~Slice 012: how a branch head is identified, who may change the sensitive settings, the smallest group size.~~ Resolved by the user at the brief gate, 15 Sep 2026 (P1–P4). | — | — |
| Slice 012 design check: decisions D1–D16 in `01b` §13, including two new privacy rules (hidden stays hidden on drill-down; hide "vs company" when the rest is small) for security to confirm. | Surbhi, security | Design check, 01c |
| Slice 012 prototype v1 not yet reacted to by the user. | Surbhi | Promoting any slice 012 pattern |
| Slice 012: competitor claims read from search summaries only; no product screenshots viewed; Keka help is behind a sign-in. | Surbhi | Quoting the benchmark |
| Slice 012 round 2: D17 — the user's sentence "too few people in this group" is untrue for a large group hidden only to protect a smaller one; prototype v2 has a switch showing both. D18 — leavers "needs review" rule. D19 — leader linked to more than one company. | Surbhi (D18 with the engineer) | Final copy; access rule |
| Slice 012 round 2: prototype v2 not yet reacted to. The row "Slice 012 prototype v1 not yet reacted to" above is answered by the 15 Sep feedback. | Surbhi | Promoting the switcher and Data to review patterns |
| Slice 013: how a frontline employee with no email or password gets into the My HR tab (Q1 in `01a`). | Surbhi, with security | The My HR tab; the brief |
| Slice 013: current-state screens not captured (bench in use); competitor claims are read only, no screenshots viewed. | Designer, when the bench is free | The design step |
| Slice 013 design (17 Sep 2026): still no bench capture; design built from code. FC-1 (status line after check-out) should be confirmed on screen. | Designer, when the bench is free | Nothing in the design |
| Slice 013 design check: decisions D1–D20 in `01b` §11; D2, D3, D4, D8, D17 are security-shaped and need `01c`. D19 changes the consent notice (new version). | Surbhi, security, compliance owner | Design check; `01c`; consent version |
| Slice 013 prototype v1 not yet reacted to; not yet published (lead session publishes). | Surbhi | Promoting any slice 013 pattern |
| Slice 009 design check: decisions 1–7 in `01b` §13. Decision 5 (raise `--fs-xs` to 12 px in `design_system.html`) touches every page. Decisions 1 and 3 are privacy-shaped and want `01c`. | Surbhi; 2 and 5 with the engineer | The design check; Wave 1's spec |
| Slice 009: I disagree with the plan on three points (`01b` §10) — close Q15 as presence only, move Feedback to the end of Wave 4, and measure Hindi each wave rather than at Wave 5. | Surbhi | The wave order |
| Slice 009 prototype v2 not yet published (no artifact tool in that run) and not yet reacted to. | Lead session to publish; then Surbhi | Promoting any slice 009 pattern |
| Slice 009: no current-state capture taken on 19 Sep (bench untouched by instruction); evidence carried over from the 14 Sep appendices. | Designer, when the bench is free | Nothing in the design; it would confirm the carried-over figures |
| Slice 013 M3 redesign: decisions D-M3-1 to D-M3-7 in `01d-ux-redesign-m3.md` §13. D-M3-1 reopens D9 (pinned light); D-M3-4 and D-M3-6 need security. | Surbhi; security | CSS build, notice layout, sign-in copy |
| Slice 013 M3 redesign: prototype v1 not yet published (no artifact tool in that run) and not yet reacted to. The designer did not see her phone screenshots, only her description. | Lead session to publish; then Surbhi | Promoting any M3 pattern |
| Slice 013 M3 redesign: server needs E-1 to E-5 (`01d` §8): brand colour after sign-in, true distance and accuracy on a saved punch, the rule, notice part keys. | Engineer; E-4 with security | Brand colour, result screen, notice icons |

---

## Feedback log — newest first

| Date | Source | What was said | What it teaches | What changed | Status |
|---|---|---|---|---|---|
| 2026-09-27 | Own look (Playwright, measured), M3 prototype v1 | 48 screens at 360 px light, dark and 200% text: clean at the end; the first pass found an 11 px Sample tag, an unbreakable `PASSWORD_CHANGED_SIGN_IN_AGAIN` at 200%, and "PP J…" in the top bar at 200% | Large text is its own device size; long codes need a break rule | Two checklist items; a pattern for icon-only actions at 150%+ | applied |
| 2026-09-27 | Own measurement, M3 palette | PPJ's local brand colour is `#000000`; Material's tonal-spot recipe made it pink (`#8c4a60`) | The tenant's real setting can be the edge case; generate the palette, do not assume it | Monochrome rule under chroma 8; checklist item; D-M3-5 | applied |
| 2026-09-27 | Own reading of code, M3 redesign | The app ignores `brand_colour`; the result says "At {site}" whatever the distance; `withdraw_agreement` has no screen; Remove asks twice (screen + `window.confirm`) | A restyle brief hides behaviour gaps; read what each screen claims, not only how it looks | Findings M3-5, M3-6, M3-8, M3-9 in `01d`; two checklist items | heard |
| 2026-09-26 | Surbhi, tested the field app on a real phone | "the mobile application pages designs are very awkward. Use the best mobile applications design systems in present times to improve its design." Approved a Material Design 3 redesign on 27 Sep | Plain equal blocks and "Label · Value" rows read as unfinished on a phone. On Android, the platform's own design language is the bar people compare against | Principle P8; `01d-ux-redesign-m3.md`; prototype v1 | principle |
| 2026-09-19 | Own look (Playwright, measured), slice 009 prototype v2 | 42 renders, 3 people × 2 devices, plus Hindi, Punjabi and dark at 390 px: clean at the end, but the first pass found 37 px menu links in the phone drawer, 32 px rating buttons on the self-review, 18 px section links and 10–11 px hints | The drawer is hidden by a transform, so looking never catches it. And 44 px everywhere produces a false list on desktop — the rule is 24 px on a mouse, 44 px on a phone | Four checklist items; all fixed before handoff | applied |
| 2026-09-19 | Task instruction, slice 009 | Four behaviours changed under the plan: reviews work on copies, KPI progress is an increment, lateness has a per-tenant grace, the vendor portal is opt-in. "Build these in, do not design around the old behaviour" | A design written against last month's behaviour is worse than no design. Read the change list before the plan | Five patterns; §7 of `01b` written before anything else | heard |
| 2026-09-19 | Task instruction, slice 009 | "Anything in the plan you now think is wrong … say so with your reasoning rather than building it because it is written down" | Being handed an approved plan is not permission to stop thinking. Disagreement goes in the handoff note, not into a quietly different build | `01b` §10: three disagreements, each with a recommendation | heard |
| 2026-09-19 | Own design, slice 009 owner view | Kamal is both a manager and an HR person, and the plan gave him one review list | A merged list makes the product decide silently which hat someone is wearing. Two lists, plus a sentence where the conflict-of-interest rule bites, make it visible | Pattern "one person, two roles, two lists" | applied |
| 2026-09-19 | Own design, slice 009 | The portal becomes every tenant's landing page | The first screen after login has to be designed empty, and its speed budget belongs in the design document, not a footnote | `01b` §7.5; checklist item | heard |
| 2026-09-19 | Own reading of `design_system.html`, slice 009 | `--fs-xs` is 11 px; our own rule is nothing under 12 px | The design system is built on, not obeyed blindly — but a token change affects every page, so it is a decision, not a fix | Raised as Decision 5; checklist item | heard |
| 2026-09-17 | Own look (Playwright, measured), slice 013 prototype v1 | 47 phone screens at 390 and 360 px in English and Hindi, 14 desk screens at 1440 and 390 px: no target under 44 px, no text under 12 px, no script errors. But the review controls made the page scroll sideways at 360 px, a sticky panel covered the phone, and the agree tick carried over between codes | Measuring the product area is not enough; the review scaffolding around it needs the same check | Fixed before handoff; checklist item | applied |
| 2026-09-17 | Own reading of `field-checkin.html`, slice 013 design | After a check-out the page says "Not checked in yet today"; the notice says "manager", the result screen "supervisor" | Reused screens carry small untruths in states nobody drew; one idea, two words (MA2) seen again in a different page | FC-1, FC-2 in `01b`; checklist item | heard |
| 2026-09-17 | Brief §7 WOW wording, slice 013 | "Joined 9:01 am today · Redmi 12 · by QR you issued yesterday" | "You" is only true for the person who made the code; "issued" is office English | D13 raised with a prototype switch rather than changed quietly; pattern "You only when true" | applied |
| 2026-09-17 | Task instruction, slice 013 design | Tab bar "greyed or absent, your call, marked ⚠ DECISION" | A choice handed to design still gets both options shown when an anti-pattern is involved, so the user can see why | D1 with three options in the prototype; recommended no bar | applied |
| 2026-09-17 | Own reading of code, slice 013 scan | The field app exists because "a driver has no email address and no password", yet the planned My HR tab signs in with email/username and password | A tab that needs a login can be a locked door for the very persona the app is for. Check who has the credential before accepting "session login" as fixed | Checklist item; raised as ⚠ Q1 in `01a` rather than designing around it | heard |
| 2026-09-17 | Own reading of code, slice 013 scan | Portal Home has its own Check In (no photo, no accuracy check) and its own phone bottom bar with "Attendance" | Wrapping two existing surfaces creates duplicates nobody designed: two bars, two check-ins with different evidence rules, one word for two places | Checklist item; MA-16–18 in `01a` | heard |
| 2026-09-17 | Own reading of code, slice 013 scan | Server says "This screen is out of date. Close the app, open it again" and the page matches errors by English sentence | Web-page assumptions ("reload fixes it") break in a store-installed app; an old version needs an "Update the app" way out | Checklist item; MA-29–31 | heard |
| 2026-09-17 | Task constraint, slice 013 | Bench in use for another slice's release test: no docker, no bench, documents only | An opportunities scan can run from code and earlier measured audits, but must say plainly that nothing was captured today and list what to capture before design | Noted in `01a` §9; open item added | heard |
| 2026-09-17 | Benchmark, slice 013 (greytHR, Keka read) | Indian frontline-heavy products solve "no email" with mobile number + OTP; global ones assume email or SSO; SAP's 30-second QR assumes a logged-in desktop | Borrow the need, check the mechanism against our personas; a company-wide QR is just a tenant code as a picture | Options in `01a` Q1 and §4.4 | heard |
| 2026-09-15 | Own look (Playwright, measured), slice 012 prototype v2 | All 20 states at 400 px: no sideways scroll, no target under 44 px, no text under 12 px, no errors. Writing Station Road's banner showed the user's sentence heading contradicting its own body ("too few people" above "this branch has 42 people") | Rendering the chosen words on the hardest case is how a wording problem shows itself | Raised ⚠ D17 with a prototype switch; checklist item on checking user-chosen labels against every case | applied |
| 2026-09-15 | DevOps §2 (07-devops-inputs), slice 012 | Group size must be the people inside each figure (OPS-19); Administrator can delete `Version` (OPS-23); check-ins arrive late, show "last check-in received" (D11); doubtful-day rule wrong for tiny branches (OPS-22) | Engineering facts change privacy copy and rules; read DevOps' design notes before writing words about counts, freshness or audit | §7 rule 1, history wording, Today strip, D5 sheet changed in `01b`; two patterns and a checklist item | applied |
| 2026-09-15 | Surbhi, feedback on slice 012 prototype v1 (point 6) | "the leadership view must load per card … with a separate cheap Home call"; portal-wide speed fix planned separately by DevOps | Loading behaviour is a design requirement, stated per card, not per page; the number of calls stays with engineering | `01b` §17; loading state fills in card by card | heard |
| 2026-09-15 | Surbhi, feedback on slice 012 prototype v1 (point 5) | "Everything else in v1 is approved as recommended: D1–D4, D8–D16, including the database indexes" | First confirmation of the slice 012 patterns: inheritance on drill-down, hiding the parent comparison, same-days comparison, bounded privacy setting with reason and history, setup-problem page | Those patterns can be treated as confirmed by the user (not yet by a usability test); rows above left as written, per the append-only rule | confirmed |
| 2026-09-15 | Surbhi, feedback on slice 012 prototype v1 (point 4, D7) | "leaders linked to several branches get a branch switcher … 'All my branches' shows both combined totals … and a comparison table … Keep 'no company or branch linked' as the only nothing-shown state" | Fail-closed is right for a missing permission, wrong for a real multi-scope leader. Give the combined view and the split together | Pattern: scope switcher; privacy rules follow the switcher (5a–5c); D19 raised for several companies | applied |
| 2026-09-15 | Surbhi, feedback on slice 012 prototype v1 (points 2–3) | "'Not recorded' → 'Needs review' … the explanation sheet says in plain words why, with an example, and that HR sees what to review. Make sure HR's side has somewhere this leads." D5 approved; D6 approved with the new label | A data-gap label is a hand-off between personas: say who acts, and build the place they act | Pattern: "Needs review"; HR Data to review page; checklist item; brand-new tenant keeps "No figures yet" because HR has nothing to fix | confirmed |
| 2026-09-15 | Surbhi, feedback on slice 012 prototype v1 (point 1) | Replace "Hidden to protect a small group" with "Not shared: too few people in this group for a fair picture"; short "Not shared" in cells; lead the explanation with fairness | Leaders read "hidden" as something kept from them; "not shared … fair picture" frames it as a fairness rule. User stated wording, so it is applied at once | Pattern row added; v1 wording retired; conflict with the next-smallest case flagged as ⚠ D17, not changed quietly | confirmed |
| 2026-09-15 | Own look before handoff, slice 012 prototype | In the "data looks wrong" state the Leave card said "None recorded" while the branch table still showed "On leave today 3" | A data-honesty state is only honest if it spreads to every copy of the number on the page. Looking at one card is not enough | Checklist item; fixed in v1 before handoff | applied |
| 2026-09-15 | Own design, slice 012 | Station Road (42 people) is hidden only to protect a 4-person kiosk; tapping it would show its figures. A branch head's "Company 96.8%" leaks the other branch in a two-branch company | Subtraction attacks travel through navigation and comparison lines, not only through tables | Two patterns (inheritance; hide the comparison); checklist item; flagged to security in `01b` §7 | applied |
| 2026-09-15 | Brief §8 copy, slice 012 | "Fewer than 5 people — hidden to protect privacy" | A label that states the reason per cell can be false (next-smallest group) and can itself reveal which group is small | Pattern: one label for every hidden figure; ⚠ D2 raised with the user rather than changed silently | applied |
| 2026-09-15 | Brief §8 copy, slice 012 | "Late arrivals 149, 12 fewer than August" with data up to the 9th | Part-period counts compared with a full period always look better | Pattern and checklist item; ⚠ D13 | applied |
| 2026-09-15 | Own look (Playwright, measured), slice 012 | Text links 32 px and a breadcrumb link 18 px tall on the phone; an icon-only "What you can see" button | P4 caught it again; words beside icons applies to my own first build too | Fixed before handoff; no principle change | applied |
| 2026-09-15 | Task instruction, slice 012 | Prototype saved in the slice folder, not `hrlocal-data`; no bench, no `docker cp` | When a prototype holds **only invented data**, it may live in the repo. Real tenant data still never does | No principle change; noted in `01b` | heard |
| 2026-09-15 | Surbhi, brief gate decision (P1–P4) | Leadership role plus Company or Branch permission; System Manager only, every change recorded; minimum 5 (3–10) with subtraction blocking; fix wrong numbers first | Privacy settings in this product are owned by System Manager and must carry a change record — a design pattern for every future sensitive switch (pay totals, individuals) | Settings pattern above | heard |
| 2026-09-14 | Own data check, slice 012 scan | The owner's "65.8% attendance" came from three days where all 330 records were "Absent"; August was about 97% | A leader number spreads a data fault further than an HR screen does. P5 now covers aggregates too: check for impossible days before trusting a total | Two checklist items (data-up-to date; impossible days) and an anti-pattern | heard |
| 2026-09-14 | Own read of `attendance_analytics.summary`, slice 012 | The access review's "cheap start" (add a leader role to the org-roles setting) returns every person by name with leave types | A shortcut that reuses an HR view for a leader carries HR's names and reasons with it. Check what the endpoint returns, not what the page draws | Flagged LV5 in `01a`; no principle change | heard |
| 2026-09-14 | Benchmark, slice 012 (Culture Amp, Lattice, Workday — read) | Survey tools hide groups under 3-10 people and hide the next-smallest group too; HR suites I read say nothing about it for analytics | Small-group suppression is a pattern to borrow for any aggregate about leave, ratings, leavers or pay — including the subtraction case | Checklist item on smallest group and subtraction | heard |
| 2026-09-14 | Own process slip, slice 012 | Used `docker cp` to put a read-only script into the bench container | Evidence gathering is still bound by CLAUDE.md's gated commands. Removed the file and used standard input | Checklist item | applied |
| 2026-09-14 | Screens, slice 012 | Store in-charge saw a greyed "Organisation" tab; analytics used red for 0.1% and for "Female" | Second sighting of AI2 and PF4 | Marked "seen a second time" in anti-patterns; promote to a principle if seen a third time | confirmed |
| 2026-09-12 | Surbhi, via the session, slice 008 | "do not build a throwaway prototype … the prototype and the deliverable are the same artifact" | When the thing shipped is one HTML page, a separate mock wastes the clock and splits the truth. P6 is satisfied by shipping production code that is clickable. | Added a variation to P6: if the deliverable is itself a single page, design it as real code and mark the sample mode clearly. Sample mode pattern added. | heard |
| 2026-09-12 | Own look before publishing, slice 008 | The sample-state switcher sat on top of the Check In button; Playwright could not click it | A review aid that covers the main control is a bug, not a convenience. Measuring caught it; looking would not have. | Switcher became one scrolling row; the footer reserves space for it. Reinforces P4. | applied |
| 2026-09-12 | Slice 008 brief §2 | The user is "a driver or a security guard … may be barely literate in English, may never have used a work app" | The portal's 13 px base type is a laptop number. A field app needs its own scale. | Field pages use a 15/17/19/22/28/34 scale, nothing under 15 px, and pin the light theme because the screen is read in sunlight. | applied |
| 2026-09-12 | Slice 008, reading `field_checkin.py` | The server throws plain English sentences, not error codes | Matching errors on text is fragile. It works, but the wording and the UI must change together. | Logged as a risk in `01b`; a machine-readable error key went to the backlog. | heard |
| 2026-09-11 | Surbhi, chat | "It must create a prototype for review" | A written design is not something the user can react to | Principle P6: no design check without a clickable prototype; versions kept as v1, v2 | principle |
| 2026-09-11 | Surbhi, chat | "PM must also do the competitive analysis and using the support from the UX agent suggest how the user experience of this module can be enhanced by Employee Self Service Portal for different personas" | UX evidence should shape the brief, not arrive after it | Principle P7: new opportunities-scan mode writes `01a` before the brief | principle |
| 2026-09-11 | Surbhi, chat | "write a reverse prompt to create an agent for UX design … keep learning based on the feedbacks" | UX work needs a standing owner with memory kept in a file | Created this file and `hrms-ux-designer` | applied |
| 2026-09-11 | Own look before publishing | Search box wrapped; badge covered the bell; bottom-bar labels wrapped; one underlined link | Small layout slips show up only on a real render | Added four checklist items | applied |
| 2026-09-11 | Surbhi, chat | "Based on the feedback on the UX, design a new prototype" | A review is expected to lead to a clickable prototype | Added *Prototype* as a standard method step | applied |
| 2026-09-11 | Surbhi, chat | "don't just focus on employee self service only for the competitors application assessment" | Benchmark whole products | Principle P2 | principle |
| 2026-09-11 | Surbhi, chat | "complete end to end document of key improvements page by page", with screenshots | Reviews go page by page, with real screenshots as evidence | Findings table with page-prefixed IDs | confirmed |
| 2026-09-11 | Mobile audit, slice 003 | 22 phone gaps, mostly from 5 page-frame causes | Fix the frame before individual screens | Principle P4 | principle |
| standing | `CLAUDE.md` §6 | "Write in simple, plain English" | Applies to screens, not only documents | Principle P1 | principle |

---

## Archive

Nothing archived yet.
