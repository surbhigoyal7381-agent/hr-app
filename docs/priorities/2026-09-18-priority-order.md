---
date: 2026-09-18
author: hrms-product-manager
status: recommendation — Surbhi decides
audience: founder
inputs: [009/00-assessment-and-plan.md, 010/*, 012/*, 013/00-sequencing-recommendation.md, 014/03-implementation-notes.md, 016/05-review.md, 016/06-security-review.md, .claude/work-in-progress.md, KNOWN_ISSUES.md, .claude/context/product-context.md, ux-learnings.md]
---

# What to do next, in order — for your yes or no

**Read this in ten minutes. Say yes, no or change against each number.**

Your two rules are built into the order:
1. **Nothing goes to production until the portal redesign (slice 009) is done and working.**
2. **The redesign starts as soon as the genuinely urgent items are done.**

So the only real question in this document is: **which items are genuinely urgent, and
which can wait.** My answer: **eleven items before the redesign, and they are about three
weeks of build, not three months.** Everything else waits.

**Bad news first, three things.**

- **One nginx serves both dev and production.** A dev push restarts it with dev's file.
  Slice 014 changes that file. So the very next push to dev can take `alvoraa.co` down —
  before any redesign, before any customer. This is the single largest risk on the list and
  it is not a feature.
- **I could not check git myself.** Command-line tools were switched off for this session.
  The "207 commits ahead of production" and "ready but not pushed" states come from your
  brief and from the work board. Confirm the counts before acting on item 4.
- **"Gated" is not "fixed" on the driver portal.** Slice 016 switched the vendor and driver
  portal off by default, but the two dev sites name `vendor` explicitly, so on
  `dev.alvoraa.co` and `ppj.dev.alvoraa.co` any logged-in person can still watch a named
  driver move. Two lines of config close that today (item 5).

---

## 1 · Before the redesign — eleven items

Sizes are build days for one engineer line, from the slice documents, not guessed by me.
"Blocks release" means production cannot go out without it.

| # | What, and why it is urgent | Days | Blocks release |
|---|---|---|---|
| 1 | **You test the new review screens and the leadership view on `ppj.dev.alvoraa.co`.** Slices 010 A–D, 012 push 1 and the F1 fix are on dev and nobody outside the team has used them. If they are wrong, the redesign builds on wrong screens. | your half day | Yes |
| 2 | **Tell HR the two changes on dev**: KPI numbers now move only when someone approves, and there is a new "Cumulative KPI Readings Check" report to run. Nothing to build. Without this, item 1's testing produces false bug reports. | 0 (a message) | No, but do it with item 1 |
| 3 | **Split dev's nginx from production's, and test the file before it deploys.** Today one file, one restart, both sites. Plus: production's file has an in-place edit and a wildcard-certificate commit that is on `main` and not on `dev`, so a dev deploy can silently overwrite it. | 1–2 | **Yes** |
| 4 | **Push what is already built and tested**: slice 014 (check-in security), 016 (vendor/driver gating), 015 (repo hygiene), the CI fix. Do it after item 3, once, at a quiet moment. It is finished work going stale in local branches, and the release rule stops everything else moving until it lands. | 0.5 | Yes |
| 5 | **Remove `vendor` from the features list on `dev.alvoraa.co` and `ppj.dev.alvoraa.co`.** Both tables are empty, so it costs nothing, and it is what makes item 4's gating real. | 1 hour | No |
| 6 | **Four small musts inside 016 before its push**: the daily arrival email still names another company to a customer; the test that pins the customer's details only scans ten files; one new test passes even with the fix removed; the release note must say the two 014 findings are gated, not fixed. | 0.5 | No |
| 7 | **Make deploys wait for the tests, and rotate the GitHub Actions secrets.** Deploys currently run whether tests pass or not. Secrets may never have been rotated after the July–August malware window, and the repo is public until your first customer. | 0.5–1 | Yes |
| 8 | **Wave 0b — the wrong numbers.** Late minutes are wrong for every employee (27 late days shown, 4 real), leave left is overstated, holidays come from the wrong list, "team this week" shows the wrong people, goal percentages mix cycles, the payslip PDF is Frappe's generic layout. **Late minutes drive a pay deduction.** Server files only, so it runs alongside the redesign — but it must not ship after it. | 3–4 | **Yes** |
| 9 | **Wave 0d — stop the page-load approvals check.** It runs on every page load for everyone and takes 11 to 16 seconds for an HR user. One day for the biggest speed win in the product. | 1 | No, but nearly |
| 10 | **Driver portal, the parts that are security not features**: an ownership check on the two GPS-trail endpoints, stop a driver posting a location after the trip ends, stop writing the delivery OTP in clear text to the error log, and make the four scheduled jobs respect the off switch (today an "off" tenant still emails customers). | 2–3 | Yes if any tenant gets this module |
| 11 | **Turn developer mode off on dev**, so error details stop reaching the browser. | 1 hour | Yes |

**Total: about 9 to 13 build days, plus your half day of testing.** Items 3, 4, 5, 6, 7, 11
are one work line's week. Items 8, 9, 10 touch server files only and can run beside the
redesign — I would still finish 8 early, because the redesign puts those numbers on bigger,
clearer screens.

**Deliberately not urgent, and why.** Driver-location retention (item 16) waits for your
lawyer's answer on the retention period; build the purge mechanism with a default the day
the answer lands. The four older minor portal gaps (lost draft manager feedback, a raw icon
in the stage bar, missing form labels) are real and small and the redesign rebuilds those
screens anyway — fixing them twice is waste.

---

## 2 · The redesign — slice 009

| # | What | Days |
|---|---|---|
| 12 | **UX designer run: prototype corrections D1–D8 plus a first owner/HR view, then your design check.** This is the gate before any screen is built. Wave 1 questions Q1–Q5 are already answered (17 Sep). | 2–3 plus your review |
| 13 | **Wave 1 — the frame** (menu, top bar, bottom bar, sheet, search, theme, log out, split the page into include files). Fold in OPS-31, the move of inline script and style into cached files, so the page is not restructured twice. This is also what the mobile app's My HR tab waits for. | 6–8 |
| 14 | **Wave 0c — the broken calls** (team approvals, create goal, goal check-ins, leave decline crash, encashment, expense approver, the old Attendance Request screen). Do only the "stop the error" parts; Wave 2 replaces the rest for good. | 2–3 |
| 15 | **Wave 2 — Home and Inbox.** The one place the product feels different: a real "needs you" list, one inbox for every approval, leave left that matches the ledger. | 7–9 |
| 16 | **Wave 3 — Time and Pay**, on the fixed late minutes, with "why was this deducted" following the real chain. | 6–8 |
| 17 | **Wave 4 — Growth, self-review, Team, People.** The largest single item inside it is peer feedback, which needs a new record type; it can be dropped from the wave. | 10–13 |
| 18 | **Wave 5 — Hindi and Punjabi.** Needs a native speaker and tenant HR to review the HR words. | 4–6 plus review |
| 19 | **The production release itself**: rehearse the migrate on a copy, take a backup, release notes, then push `main` on your word and check the live site. | 2–3 |

**Redesign total: about 38 to 53 build days, 8 to 11 weeks on one line**, roughly half that
with two lines under the parallel-work rules — but only one session may own
`hrms-employee.html` at a time, which caps how much parallel help actually shortens.

**A judgement call you should hear.** If your goal is a production release in weeks rather
than months, the release can go out after **Wave 2** with Waves 3–5 following. Waves 1 and 2
are the part that makes the portal usable on a phone and correct in its numbers. Waves 3–5
are improvement on a working product. That is a change to your rule, not my decision — it is
choice C in section 5.

---

## 3 · After the redesign

| # | What | Why it waits |
|---|---|---|
| 20 | **Mobile app, My HR tab** (slice 013). | It loads the portal; without Wave 1 it shows two menus and looks broken. The Attendance tab work carries on now on its own line. |
| 21 | **Slice 012 push 2, the leader screen.** | Same hot file as the redesign. One session at a time. |
| 22 | **The four older minor portal gaps.** | The redesign rebuilds those screens. |
| 23 | **Vendor/driver portal phase 2**: row scoping, 2FA actually enforced, the historical scorecards that telemetry helped set. | No customer has bought it. Item 10 covers the parts that are dangerous while it is on. |
| 24 | **Owner and HR screen designs** (D3). Kamal has 17 screens today and the prototype has one. | They keep working inside the new frame until designed. |
| 25 | **The Objectives and KPI backlog v2.0** — evidence-first, rating derivation, analytics. This is the actual product story, and none of it is in the redesign. | It needs a portal that works first. |

---

## 4 · Not now

| What | Why |
|---|---|
| Slice 011, and the compensation module | Parked and dropped. The only copy of compensation is on local archive branches — **never delete those branches**. |
| The `allabouthr` tenant | No demand today. |
| `backlog/KPI_AUTOMATION_BACKLOG.md` | Superseded; do not plan from it (product-context §3). |
| Any feature-parity race with Keka or Darwinbox | Refused in product-context §6, item 10. |
| Emotion, voice or facial analysis; AI-set ratings; behaviour monitoring as a performance input | Refused permanently, and Article 5 of the EU AI Act has banned the first of these in workplaces since February 2025. Not negotiable, however the request arrives. |

---

## 5 · Kano, only where it changes the order

Three notes, all **proxy** — we have no survey and no customer evidence. PP Jewellers is a
demo tenant.

- **Correct numbers and a phone-usable portal are Must-be.** Their absence causes anger and
  earns nothing when present. That is why items 8 and 9 and Wave 1 outrank everything in
  section 3. An HR page that takes 16 seconds and a leave balance that disagrees with the
  ledger lose a customer you already have.
- **The mobile app is Performance, close to Must-be, for frontline-heavy buyers.** Keka,
  greytHR, Darwinbox and HROne all ship one (read, 17 Sep 2026). It helps you win a demo.
  An app that opens a broken portal is worse than no app.
- **The vendor and driver portal is Indifferent to an HR buyer** — nobody in the target
  market asks for it — and its telemetry version was **Reverse**, which is why the
  performance scoring from driving behaviour was removed rather than improved.

Everything in the Objectives and KPI backlog is where the **Attractive** features live
(rating derivation you can replay, showing an employee how their rating was reached). They
are the reason to build this product, and they still come after the floor is solid.

---

## 6 · What your first customer needs that we do not have

The shortest honest list. No customer is live, and one is expected around now.

1. **A deploy that cannot take the live site down** — item 3. Today it can.
2. **A rehearsed backup and restore on a real tenant.** Dev deploys take no backup at all.
3. **A phone-usable portal** — Waves 1 and 2. A large share of employees are phone-only, and
   the portal takes 18 seconds on 3G today.
4. **Correct late minutes, leave balance and payslip** — item 8. These touch pay.
5. **Retention and deletion answers in writing** for anything we store about a person, plus
   your lawyer's answers on review copies and driver tracking. The product deletes a
   check-in photo after 90 days and keeps a driver's minute-by-minute movement for ever.
   A security reviewer will find that inconsistency first.
6. **Entitlement that is actually enforced**, so a tenant only gets what they bought
   (product-context §10, risk 2). Item 4 makes this true for the vendor portal only.
7. **A named person who owns compliance and incident response**, and a path that can meet
   CERT-In's six-hour clock. The clock starts at the first live tenant, not later.
8. **The repo private**, and the CI secrets rotated — item 7.
9. **Support basics**: HR told how the KPI approval change works, and a one-page runbook.

Items 1 to 4 are on the list above. Items 5 to 9 are mostly your decisions and an
afternoon's work each, not a build.

---

## 7 · The risks of redesigning before releasing

Stated plainly, because you asked.

1. **207 unreleased commits become one release.** The more that accumulates, the harder the
   rollback and the vaguer the cause when something breaks. Mitigation: rehearse the migrate
   on a copy of production data, and write release notes per slice, not one list.
2. **Production and dev drift apart in the one file that can break both.** `main` holds the
   wildcard-certificate change that `dev` does not, and the live file has an in-place edit.
   Item 3 must resolve this before any push, not during the release.
3. **The redesign owns `hrms-employee.html` for weeks.** Slice 012 push 2 and any slice 010
   follow-up wait in a branch. Long-lived branches on a file that big rebase badly. Keep
   them short or park them properly.
4. **Slice 013's My HR tab is blocked for four to five weeks.** Testers use the Attendance
   tab only and open a browser for leave and payslips.
5. **Legal answers will land mid-redesign** and create build work on review-copy retention
   and driver tracking. Leave slack for two to three days of unplanned work.
6. **Demo risk.** For weeks you demo a portal that is half old and half new. Decide which
   tenant is the demo tenant and keep it on one state.
7. **The old version stays live.** Every fix in items 8 to 11 sits on dev, unreleased, while
   production runs the code with wrong late minutes. Nobody is using production, so this
   costs nothing today — it costs from the first customer.

---

## 8 · You decide — eight choices, one line each

| # | Choice | My recommendation |
|---|---|---|
| A | Accept the eleven "before the redesign" items as the urgent set? | **Yes.** About two weeks of one line's work. |
| B | Item 3 (split dev and production nginx) before any push to dev? | **Yes.** It is the one item where the downside is the live site. |
| C | Release to production after **Wave 2**, with Waves 3–5 following? | **Recommend yes**, if a customer is close. It changes your rule, so it is your call. |
| D | Push 014, 015, 016 and the CI fix as one release after item 3? | **Yes**, once, at a quiet moment, with 016's four musts done and a manual backup taken first. |
| E | Remove `vendor` from the two dev sites' features, or accept the risk with your name and a date? | **Remove it.** Both tables are empty; it costs nothing. |
| F | Drop peer feedback from Wave 4 for now (about 4 of its 10–13 days)? | **Yes.** It needs a new record type and nobody has asked for it. |
| G | One work line or two through the redesign? | **Two**, with line B never opening `hrms-employee.html`. Two lines roughly halve the calendar. |
| H | Date for the 009 design check, so the UX run can be scheduled? | **Pick one this week.** Wave 1 cannot start without it, and the mobile app waits on Wave 1. |

---

## Open questions

| Question | Owner | What it blocks |
|---|---|---|
| Confirm the git counts: 207 commits ahead of production, and exactly what is in local dev but not pushed | Surbhi (I could not run git this session) | Item 4, and the release notes |
| Legal basis, retention period and driver notice for continuous location tracking | Your lawyer | Shipping the driver portal to any live tenant |
| Retention period for review copies | Your lawyer | Item 16's build work |
| Who owns compliance and incident response, by name | Surbhi | The first customer, and every compliance flag |
| Does the production nginx have the realip module (`nginx -V`), and has the in-place edit been cleared? | Surbhi, on the server | Item 3 and item 4 |
| Is the expected first customer signed, and when do they go live? | Surbhi | Whether choice C is urgent or theoretical |

## Assumptions

- `[ASSUMPTION]` The states in your brief and on the work board are current as of 18 Sep 2026.
  I read the slice documents; I could not verify branches with git.
- `[ASSUMPTION]` Build-day sizes come from the slice documents and assume one engineer line
  with decisions answered before each wave.
- `[ASSUMPTION]` No customer is live and PPJ is a demo tenant (recorded 17 Sep 2026). If that
  changes, items 5 to 9 of section 6 move to the top of the list immediately.
- `[ASSUMPTION]` The Objectives and KPI backlog v2.0 in YouTrack (KIN) is still the plan for
  section 3, item 25. I could not read YouTrack.

## What would change this order

- **A customer signs with a go-live date** → choice C becomes yes, and section 6 items 5 to 9
  jump ahead of Waves 3 to 5.
- **Item 1's testing finds the review screens wrong** → fixing them comes before the design
  check, because Waves 2 and 4 build on the same endpoints.
- **The lawyer says driver location may not be kept at all** → item 10 becomes "switch the
  module off everywhere", which is cheaper and faster than fixing it.

I am not a lawyer, and nothing here is legal advice. I recommend; you decide.
