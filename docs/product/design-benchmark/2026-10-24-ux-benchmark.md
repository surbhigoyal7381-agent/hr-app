---
date: 2026-10-24
author: hrms-ux-designer (evidence mode)
for: hrms-product-manager, who ranks these. Surbhi decides.
status: evidence only. No priority order, no prototype, no code.
inputs: [.claude/context/ux-learnings.md, product-context.md, nfr-budget.md §2 §7, 11 Sep 2026 review (65 findings), 2026-10-01-ux-evidence.md, docs/slices/003-ess-mobile-responsive]
---

# Portal UX against competitors, for non-tech staff — 24 Oct 2026

## The short answer

**The basics a shop-floor worker meets first are where we are weakest.** Our portal is English
only. On a phone the form fields use 13 px text. The main buttons are 25–28 px tall. Weekly
offs are still labelled "Holiday". When a call fails, the screen says "Loading…" for ever.
Every Indian competitor I looked at does better on at least two of these. greytHR offers
12 languages. Keka offers 6 and lets Android staff punch without a signal.

**On trust in money and in a single day's record, we are already ahead.** The payslip shows
both the rounded and the exact take-home, paid days, year to date, and a **Why?** button
beside the late-coming deduction. Tapping a day on the Attendance page opens "What went
wrong?" right there. None of the 12 competitor products shows a "why was my pay cut" step
in its public screens.

**Where we could lead and nobody does:** a phone-first, Hindi-first, one-job-per-screen
portal that explains every rupee and every red mark in plain words. Competitors show
charts and social walls. None of them shows the reason.

This file holds evidence and opportunities only. The PM ranks them.

---

## 1 · Who this is for, checked against product-context.md

- **Fact:** product-context §2 names the frontline and shift employee: "shared or low-end
  phone, poor connectivity", "their own language". §5 sets **English and Hindi at parity**
  on employee-facing surfaces. nfr-budget §2 sets **≤ 2.5 s on a 3G phone, with a skeleton
  within 300 ms**. §7 sets WCAG 2.2 AA, 360 px, and 200% zoom.
- **Mismatch to flag:** product-context positions the product for **50–1,000-person
  mid-market** buyers, with the HR head as the densest user. It does not name manufacturing,
  distribution or trading MSMEs, the one-person HR-plus-accountant, agency workers, or
  owners who check on WhatsApp. Memory notes for DTC, Grace Drinks, PP Jewellers and Sargam
  confirm that segment in practice. **Question for the PM:** should product-context §2 be
  updated to say so? It changes which persona wins a conflict.
- **Personas in scope:** frontline employee, line manager or supervisor, the one-person HR,
  the owner. Out of scope: security reviewer and DPO, except where privacy is involved.

## 2 · How the evidence was gathered

| Source | What | Where it is stored (outside the repo) |
|---|---|---|
| **Our portal, today** | The ALV-213 build (full width and phone layout) on the local bench `hrlocal-213` (`127.0.0.1:8213`, site `ppj.localhost`, read-only). Three real PPJ demo people: an employee (Rahul Kumar), a manager (Sandeep Sodhi) and the HR/owner (Kamal Gupta). Captured at 1440 × 900 and 390 × 844 with Playwright and Chrome, and measured. | `C:/Surbhi-Git/hrlocal-data/ux-review/2026-10-24-benchmark/ours/` (+ `report.json`, `report3.json`) |
| **Competitor screens** | 87 App Store India screenshots from 12 products, downloaded 24 Oct 2026 through the public iTunes search API, viewed as contact sheets | `.../2026-10-24-benchmark/competitors/` (list of sources in `SOURCES.txt`), sheets in `.../sheets/` |
| **Competitor help pages** | greytHR language page (fetched); Keka, Zoho, Darwinbox and uKnowva from search summaries (Keka help returns 403 to the fetcher) | links in §3 |
| **Earlier reviews** | 11 Sep 2026 review (65 findings), 1 Oct 2026 UX evidence, slice 003 phone audit | `.../ux-review/2026-09-11/`, worktree `priorities-2026-10-01` |

**Limits. Read these before quoting anything.**
- **Store screenshots are marketing.** They show the best screen, often with stock faces.
  "Seen" below means *seen in the vendor's own store image*, not tried in the product. No
  trial accounts were used.
- **The local bench has a database gap.** Every person sees a raw pop-up, *"DocType Alvoraa
  Payroll Rule Set not found"*, on Home and Leave. Kamal also gets *"User … does not have
  doctype access via role permission"*. The Leave page then stays on "Loading…". **This is
  very likely a missing migration on this local copy, not the product on dev**
  `[ASSUMPTION — check on ppj.dev]`. I count it only as evidence of how the portal behaves
  when a call fails (see UXB-6).
- The demo data stops at about 11 Sep. "No record" on every October day is the data, not a
  bug.
- Load times on localhost (3.6–5.8 s until the network goes quiet, dev server) **are not a
  3G figure**. I could not measure 3G.

## 3 · Competitor by journey

Labels: **seen** = in the vendor's store screenshot, 24 Oct 2026 · **read** = help or store
text, with date · `[recall — verify]` = from memory.

| Journey | Keka | greytHR | Darwinbox | Zoho People | Zimyo | factoHR | HROne | sumHR | Connecteam / Deputy / Workday / SAP | **Alvoraa today (measured)** |
|---|---|---|---|---|---|---|---|---|---|---|
| **Sign in** | — | — | — | — | — | OTP for forgot password (read, store text) | **Employee code, mobile number or QR** on the first screen (seen) | **+91 phone number** first, email second (seen) | Face ID / fingerprint (read, Workday/SAP store text) | Email and password on the portal. The field app has join codes (slice 013). |
| **Check in** | Shift card ("General 9:00–5:30") + one **Clock in** button on Home; map with radius (seen) | Clock with shift name and **Sign Out** on Home (seen) | "Let's get to work! **Clock In**" card at the top (seen); photo + location check-in (seen) | Check-in timer on Home (seen) | Shift times + break + green **Clock In** (seen) | Map + green **PUNCH IN** / orange **PUNCH OUT**, words on both (seen) | — | Clock-in on a map (seen) | Connecteam: one huge round button (seen). Deputy: "8:45 am · **Starting in 15 mins** · Start shift at Kitchen" (seen). Workday: "**Remind me to check out at** 12:00 / 5:00 / Other" (seen) | Large white **Check In** inside a dark card, second block on Home. "Not checked in" status. No shift, no place, no reminder. |
| **Fix a missed punch** | "Adjustments" and "regularisation", from the Me › Time tab (read, search summary 24 Oct 2026) | Banner "**4 exception day(s) · Regularize**" above the form (seen); gap-day count on Home (read, search summary) | — | Home: "05 May 2025 has been **marked as absent** · **Apply Leave**"; Leave: "Absent 1 day · **Convert Leave**" (seen) | "Apply for" bottom sheet: Leave · Regularisation · WFH · On duty · Comp off… (seen) | — | — | — | — | **Tap a day → "What went wrong?" opens inline** (seen, 390 px). A separate "Attendance Request" page also exists, with mm/dd/yyyy dates and 13 px fields. |
| **Apply leave** | Form shows "**Also on leave during this period**" with faces (seen) | Big "Apply Now", Pending / History tabs (seen) | — | Balance tiles by type (seen) | One sheet for all request types (seen) | — | — | — | SAP: leave from Home, shows "Available" (seen) | Pop-up; leave type list stuck on "Loading…" here (bench gap); no balance, no "who else is off"; 13 px fields; mm/dd/yyyy |
| **See payslip and why it changed** | Pay mix chart + "**Protect sensitive salary data**" switch that hides amounts (seen) | List with month picker, View / Download (seen) | List of PDFs (seen) | — | — | "Payslip" tile (seen) | — | — | Workday: "Most recent pay", take-home and gross on one card, next pay date (seen) | **Take-home ₹44,052 · "Exact amount on the payslip ₹44,051.61" · Working 31 · Paid 31 · earnings · deductions with "Late Coming Deduction [Why?] ₹548" · year so far · Download PDF** (seen) |
| **Manager approves** | Inbox with Approve / Reject on each card (seen) | — | "Task awaiting you (5)" on Home; Approve / Reject (seen) | — | Approvals list grouped by type (seen) | — | Inbox "DUE IN 5 DAYS" chip (seen) | Pending counts by type (seen) | SAP: Approve / Decline on Home (seen). Deputy: "Late · On shift" list on Home (seen) | Manager Home = **30 goal cards, 4,340 px tall on a phone**; approvals at the **bottom** of Team View; Team View opens with four full-width tiles "19 / 0 / 0 / 0" |
| **HR's daily view** | — | — | — | — | Team overview: On Leave 4 · Absent 4 · On Duty · WFH · Late Arrival 4 (seen) | — | — | — | Deputy: Today **4 on shift · 1 on break · 1 late · 6 scheduled** (seen) | HR/owner Home = his own goal + 10 store goal cards. No "who is in today", no "who is not ready". HR Analytics and Data to review are one click away. |
| **Language** | **6 languages incl. Hindi** (read, App Store text, 24 Oct 2026) | **12 incl. Hindi, Tamil, Telugu, Marathi, Gujarati, Bengali, Odia** (read, help page "updated June 2026") | — | — | — | — (none found) | "multilingual" (read, store text) | — | — | **English only** in the portal (read: `portal.js` has one translation call). The field app has machine-drafted Hindi, not yet reviewed. |
| **Poor network** | **Offline punch on Android, uploaded later** (read, search summary); Kiosk stores offline (read) | — | — | — | — | "offline punching" listed (read, search summary) | — | — | — | Nothing (read: no offline handling in `portal.js`). A failed call leaves "Loading…" with no retry. |
| **Shared device, no phone** | **Kiosk with face recognition or PIN** (read, help centre) | — | — | — | Selfie attendance tile (seen) | Manager punches for staff (read) | QR login (seen) | — | Deputy: kiosk with face detection (read) | Biometric device punches flow in (DTC). No kiosk. |
| **WhatsApp** | — | — | Approvals and alerts on WhatsApp (read, People Matters, via search summary) | — | — | — | — | — | uKnowva (not on our list): apply leave, payslip, regularise on WhatsApp (read, vendor page) | Nothing for employees. (`ai_leads/whatsapp.py` is for sales leads, not HR.) |
| **Social / engagement** | Wall, birthdays, "Wish them" (seen) | Engage feed, polls (seen) | Birthdays, AI "Super Agent" chat (seen) | — | Workbox, surveys (seen) | — | Birthday feed, badges (seen) | "Late lately? **You've missed the bus 12 times**" (seen) | Connecteam: "**187/210 read the update**" (seen) | Activity card, empty ("No activity recorded yet.") |

**What the market shows, in one line each:**
- Indian products copy each other on Home: **greeting → clock-in card → grid of coloured icon
  tiles**. The icons often have words; the tiles are small.
- **Languages are now table stakes** in the Indian frontline segment (greytHR 12, Keka 6).
- **Nobody explains a number.** Payslips are lists, PDFs or doughnut charts. Attendance shows
  status words ("Absent", "On Duty") with no reason.
- The global frontline apps (Deputy, Connecteam, Workday) do three things the Indian ones
  don't show: the **shift in plain words** ("Starting in 15 mins"), a **check-out reminder**,
  and **"today" counts for the supervisor**.

## 4 · Where we already lead — honestly

| ID | What | Evidence | Kind |
|---|---|---|---|
| L1 | **The payslip explains itself.** Both figures (ALV-90), paid days, year so far, and a **Why?** on the late deduction | `x-employee-payslip-detail-390.png` | Keep |
| L2 | **Act where you see the problem.** Tapping a day opens "What went wrong?" inline. Zoho is the only competitor with something close ("Convert Leave") | `x-employee-daysheet-390.png`; was AL1 / MA4 | Keep |
| L3 | **The day table** (in, out, worked, expected, arrival, one line per day) is denser and clearer than any competitor attendance screen I saw | `employee-att-record-1440-fold.png`; MA1 | Keep |
| L4 | **Rules in plain words** under the table: "A day counts as short only once it is more than 30 minutes under the shift…" No competitor shows its rule | `employee-att-record-390-full.png` | Keep |
| L5 | **No sideways scroll** on any of the 14 phone screens measured (scrollWidth − width = 0). The old PH1 causes are fixed | `report.json` | Keep |
| L6 | **A phone bottom bar with words** (Home · Attendance · Finances) and a bell in the phone header | every 390 capture | Keep |
| L7 | **Leave page says what lateness has cost**, and says when the late rules are off ("…so nothing new is deducted") | `employee-attendance-390-full.png` | Keep |

## 5 · Our gaps — status of the 11 Sep findings, plus new ones

Checked on screen today unless marked.

| ID | 11 Sep finding | Today | Evidence |
|---|---|---|---|
| G1 | Top bar says "Home" on every page | **Still open** (desktop: "Home" above the Attendance page) | `employee-att-record-1440-fold.png` |
| G2 | Icon-only desktop menu | **Still open** | every 1440 capture |
| G3 / RQ1 | Time split over many entries; three look-alike request pages | **Partly fixed.** Attendance and Leave now; Shift Request, Attendance Request and Request Advance are still three menu items | `NAV` lists in `report.json` |
| G4 | No bell or approvals on desktop | **Phone fixed** (bell in header). Desktop: **no bell seen** at 1440 | home 1440 vs 390 |
| G6 | Dates change format | **Still open:** form dates show `mm/dd/yyyy`; the late table shows `2026-08-03` broken over three lines | apply-leave, att-req, leave 390 |
| G8 | Grey shadow down the right edge | **Still open**, on phone too | every capture |
| H1 | Nothing says what needs me | **Still open** | employee home |
| H2 | 40-person grid on employee Home | **Fixed** | employee home |
| H5 | Empty or past holiday card | **Partly.** Shows "October 2026 Holidays: 2 Oct" on 24 Oct, a holiday already past | employee home 390 |
| H6 | Only one quick action | **Still open** ("+ Apply Leave" only, 111 × **25 px** on phone) | `report3.json` |
| MH1 | Exceptions buried under healthy goals | **Still open:** manager phone Home is 4,340 px; Kabir Anand's 0% "Off Track" is the last card | `manager-home-390-full.png` |
| MH2 | No approvals on manager Home | **Still open** (bottom of Team View) | `x-manager-team-390.png` |
| AL1 / MA4 | Absent day has no action | **Fixed** (inline "What went wrong?") | L2 |
| MA2 | Weekly off labelled "Holiday" | **Still open** (Thursdays 1, 8, 15, 22, 29 Oct say "Holiday") | att-record 390 |
| MA3 | Lateness not explained | **Fixed for pay** (Why? on the slip). Rule line on Attendance | L1, L4 |
| FN1 | Payslip page explains nothing | **Mostly fixed** in the detail view; the list still opens first with green amounts and no change from last month (Aug ₹44,052 vs Jul ₹32,200, unexplained) | finances 390 |
| TV1 | Raw server error on Team View | **Fixed** ("No pending progress approvals") | manager team |
| TV3 | Grey dashes when nobody checked in | **Still open:** 19 cards with "—" | manager team 390 |
| TV4 | First names only | **Still open:** two Nehas, two Manpreets in the charts | manager team 390 |
| PH2 | Bottom bar: Home, Attendance, Finances only | **Still open:** no Leave, no Requests | 390 |
| PH3 | Check In largest on the phone | **Partly:** large button, but placement is not shown before the tap | home 390 |
| PH4 | English only | **Still open** | code |

**New today**

| ID | Finding | Evidence | Severity |
|---|---|---|---|
| N1 | **Phone controls below 44 px:** "+ Apply Leave" 25 px; drawer menu items 38 px; month arrows 24 × 25; "Full Portal →" and "Details →" 19 px; payslip tabs 34 px | `report3.json` | P2 |
| N2 | **Phone form fields at 13 px** (apply leave: all five; attendance request: three). Under 16 px, iPhones zoom in, and it is hard to read for anyone | `report3.json`, `report.json` | P2 |
| N3 | **11 px text** on every screen ("Hey there,", "At Risk", "of 8", tile labels, payslip date range). Same token as slice 009 Decision 5 (`--fs-xs`), still open | `report3.json` | P3 |
| N4 | **A failed call never ends:** Leave page and leave-type list stay on "Loading…"; HR's holidays card the same. No error, no retry | leave 390, apply-leave 390, hr-home 1440 | P2 |
| N5 | **Raw Frappe messages reach people** in a pop-up ("DocType … not found", "does not have doctype access via role permission"), on this bench | home captures | P1 if seen on dev, else P3 `[check on dev]` |
| N6 | **The day table is cut off on the phone:** the WORK column is clipped inside its card at 390 px | att-record 390 | P3 |
| N7 | **Home repeats itself:** "Good evening, Rahul!" then "HEY THERE, Rahul Kumar"; date shown twice; an empty "Activity" card takes 200 px before goals | home 390 | P3 |

## 6 · What not to copy, and why

| Seen at | Pattern | Why not, for our people |
|---|---|---|
| Keka Kiosk, Deputy | **Face recognition** to clock in | Biometric data under DPDP; product-context §6 refusal 3 bars facial analysis. Ask the security agent before any face-based identity. DTC already has biometric devices |
| sumHR | "Late lately? **You've missed the bus 12 times**" | Guilt-trip wording, a dark pattern on our refusal list. We explain the rule, we don't tease |
| Darwinbox | AI "Super Agent" chat as the main way in | A chat box assumes typing and reading English; it hides the reason behind a conversation. A rule, a default or a button does the job (no-over-engineering §2) |
| Keka, greytHR, HROne | Social wall, birthday confetti, polls, as the first thing on Home | Pushes the one task (check in, fix a day) below the fold on a ₹8,000 phone |
| greytHR, Darwinbox, Connecteam | Decorative illustrations and stock photos on every screen | Weight on 3G (2.5 s budget); no meaning for a low-literacy reader |
| Keka | Doughnut chart of the salary mix | Looks clever, answers nothing. "Why is it less than last month?" is the question |
| Zimyo, factoHR | Grid of 9–12 small icon tiles | Small targets, and icons need reading skill. Words beside icons is our rule |

## 7 · Improvement opportunities (unranked — the PM ranks)

Each one improves the **existing** portal (`hrms-employee.html`, `portal.js`,
`parts/*.html`, `css/ess/*`). No new frame, no menu item that leads to "coming soon".
Size: S = days, M = a week or two, L = more. **Pattern** = a competitor does it. **None do it**
= a possible advantage for our segment.

| ID | Journey | Persona | Opportunity | Evidence | Size | Source |
|---|---|---|---|---|---|---|
| **UXB-1** | All | Frontline employee | **Hindi in the portal, starting with the five frontline journeys** (Home, check-in, the day sheet, apply leave, payslip). A language switch in the profile menu, not a demo bar. Native review before switching it on (ALV-150 lesson) | PH4; greytHR 12, Keka 6; product-context §5 parity | L | Pattern |
| **UXB-2** | All forms | Frontline employee | **Phone floors on what exists:** 44 px for every control on 390 px, 16 px for fields, nothing under 12 px. Fixes N1–N3 in CSS only | N1–N3, P4, nfr §7 | S | Ours (our own rule) |
| **UXB-3** | Fix a missed punch | Frontline employee | **Exceptions count on Home:** "2 days need fixing" with the dates, each opening the existing inline day sheet. One tap from Home to "What went wrong?" | greytHR "4 exception day(s) · Regularize", Zoho "marked as absent · Apply Leave"; H1 | S | Pattern |
| **UXB-4** | Check in | Frontline employee | **Shift in plain words on the check-in card:** "Your shift: 9:30 am – 6:30 pm · starts in 15 min · weekly off Thursday". Use the existing shift data; no new record | Deputy "Starting in 15 mins", Keka "Shift today"; PH3, H8 | S | Pattern |
| **UXB-5** | Pay | Frontline employee | **"Why is this month different?"** on the payslip list: one line per change against last month ("3 fewer paid days · ₹548 late deduction · ₹12,400 incentive"). Builds on L1, using slip data that already exists | FN1; Aug ₹44,052 vs Jul ₹32,200 shown with no reason; no competitor explains | M | **None do it** |
| **UXB-6** | All | Everyone | **Honest failure states:** every "Loading…" ends in 10 s with plain words and **Try again**; raw server text never reaches a person (map it to "Something went wrong on our side. HR has not been told yet. Try again, or show this code to HR"). | N4, N5; ux-learnings pattern "screens chosen by error code" | S | Ours |
| **UXB-7** | All | Frontline employee | **Words that match the record:** "Weekly off", never "Holiday", for the store's off day; one date format ("24 Oct 2026") in every field and table | MA2, G6 | S | Ours |
| **UXB-8** | Apply leave | Employee, manager | **Show the decision facts in the leave form:** balance for the chosen type, and "Also off these days: Neha S., Kabir A." (names only, never reasons) | Keka "Also on leave during this period"; AL3 | M | Pattern |
| **UXB-9** | Manager approves | Line manager / supervisor | **Manager Home leads with what needs them:** approvals with Approve / Decline inline, then "2 of 30 goals need attention" by name, with the healthy goals folded | SAP and Darwinbox approvals on Home, Keka inbox; MH1, MH2 | M | Pattern |
| **UXB-10** | HR daily view | One-person HR / supervisor | **"Today" strip** for HR and supervisors: In 14 · Not in yet 3 · On leave 2 · Late 1, each a tap to the names; "No check-ins yet today" instead of 19 dashes | Deputy, Zimyo team overview; TV3, MH3 | S | Pattern |
| **UXB-11** | Check out | Frontline employee | **Check-out reminder on the existing card:** after check-in, "Remind me at 6:30 pm" (default = shift end). Needs a missed-check-out count on DTC first (1 Oct open item) | Workday "Remind me to check out at"; ALV-161 | M | Pattern |
| **UXB-12** | All | Frontline on 3G | **Keep the person's draft:** a leave or day-fix form survives a dropped connection (kept on the phone, "Not sent yet — will send when you are back online"). Portal only; offline check-in stays in the field app | Keka offline punch, factoHR offline; nfr §2 3G | M | Pattern (for forms: **none show it**) |
| **UXB-13** | Pay, attendance | Owner on WhatsApp; employee | **Share a plain-words summary** of a day, a slip explanation or a team "today" strip by the phone's own share sheet (text, no link to personal data). No WhatsApp integration | Owners check on WhatsApp (target segment); Darwinbox WhatsApp is approvals only | S | **None do it** this way `[ASSUMPTION — needs a privacy check]` |
| **UXB-14** | Menus | Employee | **One "Requests" entry:** Shift, Attendance and Advance requests become one page with a type picker and one history, reached from a "Requests" item in the phone bottom bar | RQ1, PH2; Zimyo "Apply for" sheet | M | Pattern |
| **UXB-15** | Desktop | HR, manager | **Page name in the top bar, and words beside the menu icons** on desktop | G1, G2 | S | Ours |

**What changes for each persona (the CLAUDE.md three-persona check):**
- **Employee / frontline:** UXB-1 to 7, 11 to 14 are theirs. They finish in fewer taps, in
  Hindi, and know why.
- **HR manager (often one person who also does the accounts):** fewer "why was I cut"
  calls (UXB-5, 7), a today strip (UXB-10), fewer request screens to support (UXB-14).
- **CXO / owner:** UXB-10 and UXB-13 give one trusted figure he can forward. Nothing here
  shows him a person's absence reason. The one-way rule holds: no manager gain costs the
  employee anything.

## 8 · Decisions and questions for the PM

1. **⚠ DECISION — product-context §2 does not describe the MSME segment** (§1 above).
   Owner: hrms-product-manager with Surbhi. Blocks how UXB-1 and UXB-13 are weighed.
2. **N5 on dev?** One look on ppj.dev as Rahul settles whether raw "DocType" pop-ups are real
   (P1) or only this bench (P3). Owner: whoever next opens dev.
3. **UXB-13** touches pay and attendance text leaving the product. **⚠ COMPLIANCE**: needs
   `hrms-security-privacy-engineer` before design.
4. **UXB-1** needs a native Hindi reviewer named (open since 11 Sep). Without one it should
   not ship (ALV-150 lesson).
5. **UXB-11** waits on a missed-check-out count from DTC data (a read-only query).

## 9 · Not in this scan (for Surbhi to decide whether to look)

- The field app (slice 013 M3 redesign) was not re-captured; it already has Hindi drafts and
  a large check-in.
- Performance and self-review journeys, org chart, HR Analytics were not compared.
- No test with real staff. Every "easier" above is a judgement until five people try it.

**Subtract pass:** I removed a sixteenth idea (a kiosk / shared-tablet mode), because it
overlaps biometric devices DTC already uses and runs into the face-recognition refusal. I
also removed a "celebrations" idea (H7), because it does not help a non-tech worker finish a
task.
