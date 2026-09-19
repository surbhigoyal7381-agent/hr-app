---
slice: 012-leadership-view
artifact: 01b-ux-design
author: hrms-ux-designer
date: 2026-09-15 (round 2)
status: draft — round 2, after the user's feedback on prototype v1
inputs: [01-product-brief.md (incl. Gate decision 2026-09-15), 01a-ux-opportunities.md, 07-devops-inputs.md §1 §2, user feedback on prototype v1 (15 Sep 2026), 009 appendix-a-frame.md, 009 00-assessment-and-plan.md, ux-learnings.md, product-context.md §2 §6, nfr-budget.md §2 §5 §7, handoff-contract.md, design_system.html, brand_color.html, hrms-employee.html (card, bottom bar, page header styles)]
---

# 012 · Leadership view — UX design

**I recommend. You decide.** Go, change or drop, after clicking the prototype.

## Read this first — round 2

1. **The v2 prototype is not published yet.** I do not have the Artifact tool in this run.
   The file is `docs/slices/012-leadership-view/prototype-v2/index.html`. v1 is kept
   unchanged beside it, so you can compare. The lead session publishes v2 and gives you
   the link. Both hold **only invented sample data** (a fictional "Kavya Retail").
2. **One thing in your wording is not true on some screens, so I am asking before I
   settle it (⚠ D17).** "Not shared: too few people in this group for a fair picture" is
   false for a big group that is hidden only to protect a smaller one. Station Road has
   42 people. Its figures are hidden only because the 4-person Hilltop Kiosk would
   otherwise fall out by subtraction. In table cells this does not matter: every cell
   says just "Not shared". It matters in the banner and card blocks on Station Road's own
   page. v2 uses your sentence everywhere, as you asked. The prototype has a switch,
   **"Wording on a large group (D17)"**, that shows a variant for that one case:
   *"Not shared: it would let someone work out a smaller group's figures"*. Please pick one.
3. **What changed from v1:**

   | # | Your feedback | What v2 does |
   |---|---|---|
   | 1 | New wording for hidden figures | "Not shared" in cells; the full sentence in blocks, banners, the "Why?" sheet, settings and the employee line. The sheet leads with fairness (§8.3) |
   | 2 | "Not recorded" becomes "Needs review" | Leave used, on leave today, requests waiting, leavers and attrition, everywhere they appear. Each has a "Why does this need review?" sheet with an example. HR gets a new **Data to review** page (§8.10) |
   | 3 | D5 approved; D6 approved with "Needs review" | Doubtful days keep the amber warning. D6 rule unchanged |
   | 4 | D7: branch switcher | "Showing: All my branches / each branch". All my branches shows combined totals **and** a by-branch table. Home shows the last choice (§8.8) |
   | 5 | D1–D4, D8–D16 approved, with DevOps' indexes | Marked approved in §13 |
   | 6 | Load per card; cheap Home call | New §17. The loading state now fills in card by card |
   | — | DevOps §2 notes | Groups counted by the people inside each figure; "Administrator can delete" history wording; "Last check-in received" time; doubtful-day check only for groups at or above the minimum |

4. **Three new decisions** (§13): D17 wording on a large group, D18 when leavers "need
   review", D19 a leader linked to more than one company.
5. **No new screens were captured.** I was told not to use the bench. Evidence about
   today's screens is still the 14 Sep capture behind `01a`.

**Learnings applied in round 2:** the checklist item "a hidden or not-recorded state
reaches every place that figure appears" was applied to both new labels ("Not shared",
"Needs review") across cards, tables, total rows, Today and Home; the pattern "hidden
stays hidden on drill-down" was extended to the branch switcher; P4 measured all 20
states at 400 px. The v1 pattern "one label for every hidden figure" still holds for
cells; its wording is retired (see the learnings log).

**Learnings applied in v1** (from `ux-learnings.md`): P1 plain words on screen; P3 built on
the design-system tokens and the tenant brand-colour clamp; P4 measured the phone layout
rather than looking at it; P6 clickable prototype; anti-patterns AI2 (no greyed tabs —
the branch head gets no Organisation tab) and PF4 (no red for an ordinary number — no
red anywhere on the leader pages); checklist items "every total shows its data-up-to
date and warns on impossible days" and "check the smallest group and the subtraction
case". The Slice 008 pattern "state in words beside the colour" is used on every hidden
and doubtful figure.

---

## 0 · How to review the prototype

Open the file. The dark strip at the top is not part of the product. Use **Screen** to
jump between states, or tap inside the product: branch rows, "Why?" links, "How is this
worked out?", the menu.

| Control | What it does |
|---|---|
| Screen | 20 states, listed in §6. New ones start with "NEW" |
| Device | Fit window · Phone frame (390 px) · Desktop |
| Theme | Auto · Light · Dark |
| Language | English · हिंदी (a partial machine draft, to test that longer words still fit) |
| Brand colour | Alvoraa default · two tenant colours, run through the same lightness clamp as `brand_color.html` |
| Wording on a large group (D17) | Your wording everywhere · the variant for big groups hidden to protect a smaller one |

**Try this:** open *System Manager*, lower the smallest group to 3, give a reason, save.
Then open *Company head · Company overview*. Hilltop Kiosk and Station Road now show
figures. The change history has your row at the top.

**Try this too (v2):** open *Leader of two branches · All my branches*. Tap **Riverside**
in the switcher (or the "Showing" chip on a phone). Then open *Home* for the same person:
the card now shows Riverside. Open *Data looks wrong* and tap any "Needs review", then
*HR Manager · Data to review* to see where it leads.

---

## 1 · Frame

**A company head or a branch head, on a phone before walking the floor or before a
review meeting, wants to see how their people side is doing — attendance, leave and
headcount — against the rest of the company, trusting the numbers and never seeing
any one person.**

| Persona | In scope? | Their job on this screen | What changes for them |
|---|---|---|---|
| **Branch head** (store manager, plant head) | Yes — lead persona, phone first | "Is my branch turning up, and how do we compare with the company?" | Opens Home and sees the answer in the first card. No need to borrow HR screens |
| **Area or cluster manager** (linked to several branches) | Yes — new in round 2 | "How are my branches doing together, and which one should I ask about?" | Same page with a switcher: all their branches added together, or one at a time |
| **Company head** (owner, MD — the CXO persona) | Yes, same screen at company scope | "One number I trust, and which branch to ask about" | Company overview with a by-branch table sorted by name. No need to hold HR Manager to see the business |
| **System Manager** | Yes, settings only | "Set the privacy rule once, and prove who changed it" | A settings page with a change history nobody can edit |
| **HR Manager** | Partly | "Leaders' numbers match mine, and I know what to fix" | Same calculation as HR Analytics (Step 0). Sees the settings and history read-only. Keeps every name list. New: a **Data to review** page listing each figure leaders see as "Needs review" or doubtful |
| **Employee / frontline employee** | Partly | "Know who sees what about me" | One line on My attendance and My leave. Nothing to do. Counted, never named |
| **Line manager** | No screen change | Must not be ranked | No league table of managers or teams. Nothing taken away |
| **DPO / security reviewer** | Reads it | "Privacy I can see in the product" | Hidden figures say why; the settings history shows who, when, before, after, reason |

**Left out on purpose:** a department head across branches, a leader of several
companies (see D19; several branches are now in, D7), Performance, Pay, Compliance, individual drill-down,
exports, the Monday email, HR's "preview as leader".

**Three-persona check (CLAUDE.md):**
- **CXO:** gets a company overview built for them. Still one company only in this slice.
- **HR Manager:** numbers match; can read, not change, the group minimum unless also System Manager.
- **Employee:** counted inside totals of 5 or more, never named; told so on their own page.

**One-way rule:** nothing here gives a leader something at an employee's cost. Leave
reasons never travel up. Small groups are hidden. The employee is told.

---

## 2 · Evidence

- **Today's screens:** captured 14 Sep 2026 on `ppj.localhost` as the owner and a store
  in-charge, at 1440 × 900 and 390 × 844. Stored outside the repo in
  `C:/Surbhi-Git/hrlocal-data/ux-review/2026-09-14-leadership/` (9 screenshots and
  `capture.json` with the measurements). Findings are in `01a` §2.
- **This run:** no bench, no tenant data. The prototype was rendered with Playwright
  (Chrome) at 400 × 844, 1280 × 900 and 1440 × 900, in light and dark. The look screenshots
  are in this session's scratch folder only; they hold invented data.
- **Measured on the prototype (P4):** no sideways scroll in any of the 16 states at
  400 px; no script errors; every button, link and summary on the phone is at least
  44 px tall after fixes; no text under 12 px inside the product area; field text 16 px.
- **Round 2 (v2):** rendered with Playwright (Chrome) at 400 × 844 and 1440 × 900, light
  and dark. Measured in all **20** states at 400 px: no sideways scroll, no button or link
  under 44 px, no text under 12 px, no script or console errors. Clicked through the
  switcher (sheet on phone, radio buttons on desktop), Home remembering the last choice,
  and the D17 wording switch. Screenshots hold invented data only and stay in this
  session's scratch folder.

---

## 3 · Benchmark (carried from 01a, not re-run)

Nothing new was researched in this run. The labels from `01a` §3 stand: everything is
**read (14 Sep 2026)** from help and product pages, or `[recall — verify]`. **Nothing is
seen** in a live product. Two points shaped this design:

- **Small-group protection comes from survey tools** (Culture Amp default 5; Lattice 3–10
  plus "hide the next-smallest"; Workday Peakon hides overlapping segments) — read, 14 Sep
  2026. No HR suite I read claims it for attendance, leave or headcount dashboards.
- **Scope × data** is the common access model (SAP SuccessFactors, Rippling, HiBob — read).
  Here scope = one company or one branch; data = totals only.

**What we deliberately do not copy**

| Seen elsewhere | Why not |
|---|---|
| Per-person attrition "risk score" (Keka, Darwinbox — read) | Scores a named person on a guess, visible to their boss |
| Branches ranked best to worst; sortable result columns | A ranking of stores is a ranking of their managers. Sorted by name only (D12) |
| Red and green for every rise and fall | Red means wrong or overdue. A 0.3-point dip is neither. Arrows plus words, neutral colour (D10) |
| Gender, age or manager filters | In small groups they point at people |
| CSV export | Walks around every rule on this page |
| A 20-chart analytics page | One number per area, one trend, one table |

---

## 4 · Findings

IDs from `01a` are reused where the problem is the same. `LD` IDs are new design findings
from building the prototype.

| ID | Finding | Impact | Kind | Size | Evidence | Handled in this design |
|---|---|---|---|---|---|---|
| LV1 | Headline attendance dragged to 65.8% by three all-absent days; no data-up-to date | High | Fix | M | 01a DB check | Doubtful-day warning, days left out, "Data up to" on every card (§8.4) |
| LV2 | Leave use divides by allocations from every year | High | Fix | S | `hr_api.py` 442-449 | "This leave year only" in words, with the dates (§8.3) |
| LV3 | Two attendance formulas | High | Fix | M | 01a | Explanation sheet says "HR Analytics uses exactly this calculation" — only true after Step 0 |
| LV8 | Owner's page mixes HR work queues with business numbers | Medium | Improve | S | 01a screenshots | Leaders get counts only ("Requests waiting more than 3 days: 4 — managers and HR see who") |
| LV9 | Red for ordinary numbers | Medium | Fix | S | 01a | No red on leader pages. Amber only for doubtful data |
| LV11 | Store in-charge sees a greyed Organisation tab | Low | Fix | S | 01a | Menu shows only what the person can open |
| LV13 | Phone text under 12 px, targets under 44 px | Medium | Fix | — | `capture.json` | Measured: none in the prototype |
| LV14 | Insights maths is honest ("the rota, not the people") | — | **Keep** | — | `attendance_analytics.py` | Reused on the branch "Last 7 days" card |
| LV15 | Org health explains every flag in words | — | **Keep** | — | `metrics.py` | Every card has "How is this worked out?" |
| LV17 | A small-group rule already exists (upward feedback < 3) | — | **Keep** | — | appendix D | Same idea, stronger rule |
| LD1 | A branch hidden only for subtraction reasons leaks if its own page shows figures | High | New rule | S | Prototype, Station Road | Hidden stays hidden on drill-down (§7 rule 4) |
| LD2 | "Branch vs company" leaks the rest of the company when the rest is small | High | New rule | S | Prototype, two-branch company | Comparison hidden when company minus branch is below the minimum (§7 rule 5) |
| LD3 | "Fewer than 5 people" wording is false for the next-smallest group and marks the small one | Medium | Wording | S | Prototype | One label for every hidden figure (D2) |
| LD4 | A part month compared with a whole month flatters every count | Medium | Fix | S | Brief §8 WOW copy | Same days last month (D13) |
| LD5 | "Leave not recorded" and "on leave today: 3" on the same page contradict each other | Medium | Fix | S | Found in my own look at the prototype | When leave is not recorded, every leave figure on the page says so, including the table and Today |
| LD6 | A leader with the role but no company or branch needs to find out why they see nothing | Medium | New | S | Decision P1 | Menu entry stays for Leadership role holders; page explains and gives a message to send |
| LD7 | The top-bar "What you can see" button was icon-only in the first build | Low | Fix | S | Own look | Words beside the icon on desktop; a text link on the phone |
| LD8 | The user's hidden-figure sentence ("too few people in this group") is false for a large group hidden only to protect a smaller one | Medium | Wording | S | v2, Station Road (42 people) page | ⚠ D17; cells stay "Not shared" either way |
| LD9 | "Needs review" on a leader page leads nowhere unless HR has a place that lists what to review | High | New | M | User feedback 2 | HR **Data to review** page (§8.10) |
| LD10 | A leader of several branches can rebuild a branch figure from "all my branches" minus the other branches, and "the rest of the company" from the company comparison | High | New rule | S | v2, switcher | Small-group rule runs across the leader's own set; inheritance on the switcher; comparison rule 5b (§7) |
| LD11 | "Nobody can delete it, including System Managers" is not true for Administrator | Low | Wording | S | 07 §2 OPS-23 | History copy now says only the Administrator account can delete (§9) |
| LD12 | A group's size today is not the number of people inside a past figure | High | Rule | S | 07 §2 OPS-19 | Group counted by the people inside each figure for its period (§7 rule 1); settings impact line says "about" |
| LD13 | "Counts as of 10:40" suggests live check-ins, but devices sync late | Low | Wording | S | 07 §2 D11 | "Last check-in received 10:32" |

---

## 5 · Where it lives in the slice 009 frame

| Place | Branch head | Company head | Why |
|---|---|---|---|
| Menu group | **Company › Branch overview** | **Company › Company overview** | One entry, one page, same place for both; the label names the scope. ⚠ D1 |
| Home | The **WOW card** on top, then "Today", then their own Home from slice 009 | Same, at company scope | Monday morning job answered without a tap |
| Phone bottom bar | Home · Time · **Branch** · Inbox · More | Home · Time · **Company** · Inbox · More | 009 rule: four buttons plus More; short labels |
| Page title | "Branch overview" | "Company overview"; a branch page is titled with the branch name and a "Company overview ›" breadcrumb | Title names the page (anti-pattern G1) |
| Settings | — | — | **Company › Org settings › Leader view privacy**, for System Manager and HR Manager only |
| Leader of several branches | Same entry, **Company › Branch overview**, bottom bar "Branch" | — | One page; the switcher changes the scope, not the menu |
| Data to review | — | — | **Company › Data to review** for HR Manager (and store HR, for their branch), with a count. Also a line at the top of HR analytics and an item in HR's "Needs you" strip |

Someone **without** the Leadership role never sees the entry. Someone **with** the role
but no company or branch sees "Leader overview" and an explanation (§6, LD6).

---

## 6 · Flows and every state

**Happy path, branch head, phone, two taps or none:**
Home → WOW card answers "attendance vs company" → tap **Open branch overview** → cards,
trend, last 7 days, by department → tap **How is this worked out?** or **Why?** for any number.

**Company head:** Home → **Open company overview** → by-branch table → tap a branch →
the same page at branch scope, with its departments → breadcrumb back.

| # | State (Screen menu) | Who | What they see | Why it is designed this way |
|---|---|---|---|---|
| 1 | Branch head · Home | Arjun, Lakeside Mall | WOW card, Today counts, own Home below | The brief's WOW moment |
| 2 | Branch head · Branch overview | Arjun | Today; Attendance, Leave, People cards; 6-month trend; last 7 days with weekday pattern; by department with 2 of 4 hidden | Full view at branch scope |
| 3 | Company head · Home | Meera | WOW card at company scope | Same card, wider scope |
| 4 | Company head · Company overview | Meera | By branch: Hilltop Kiosk (4 people) and Station Road (42) hidden | The subtraction rule made visible |
| 5 | › Lakeside Mall | Meera | Branch page with "Company 96.8%" and departments | Drill-down, totals only |
| 6 | › Station Road | Meera | Headcount and joiners only; banner in your wording (or the D17 variant), with a body that says sharing it would reveal a smaller branch | LD1, D17 |
| 7 | Data looks wrong | Meera | Amber warning; attendance with doubtful days left out and a link to see the figure with them; leave, on leave today, requests waiting, leavers and attrition say **Needs review** everywhere, each with a "Why?" sheet | D5 approved; D6 approved with the new label |
| 8 | Two branches, one tiny | Kabir, Meadow Foods | Both branches hidden for sensitive figures; headcount shown; "With two branches, showing one would reveal the other" | Brief handoff asked for this case |
| 9 | Head of a 4-person branch | Farah | Headcount and joiners; everything else hidden; pointer to My team | The rule applies to leaders of small groups too |
| 10 | No company or branch linked | Rohan | "Your leader view is not set up yet", why, and a message to copy for the System Manager | P1: fail closed, but explain |
| 11 | NEW · Leader of two branches · Home | Neha, Old Market + Riverside | WOW card for her last choice (first time: All my branches), with a "Change" link in the eyebrow | D7 as decided |
| 12 | NEW · Leader of two branches · All my branches | Neha | "Showing" switcher; combined Today, cards and trend; by-branch table sorted by name, total row "Your 2 branches, together"; "Company 96.8%" because the rest of the company (168) passes the minimum | D7 |
| 13 | NEW · › Old Market | Neha | Same page for one branch; breadcrumb "Branch overview ›"; departments with Alterations (4) and Security (6) not shared | Inheritance on the switcher |
| 14 | NEW · Large and tiny branch | Dev, Hilltop Kiosk (4) + Station Road (42) | Combined figures for 46 people shown; both branch rows "Not shared"; choosing either branch alone shows headcount and joiners only | Small-group rule across the chosen set |
| 15 | Loading | Arjun | Skeletons within 0.3 s; Today, then each card fills in on its own; "Play again" | §17; nfr §2 |
| 16 | One card failed | Arjun | Attendance card: "Attendance figures did not load. Your people and leave figures are up to date." + Try again | One failure does not blank the page; no raw server error |
| 17 | System Manager settings | Vikram | Stepper 3–10, live impact line ("about"), what is not shared / always shown / never shown, required reason, confirm dialog, leader access list, change history | P2 |
| 18 | HR Manager settings | Priya | Same page, value as text, "Only a System Manager can change this setting." History visible | P2; no greyed controls |
| 19 | NEW · HR Manager · Data to review | Priya | Three items: doubtful days (amber), leave used (Needs review), leavers (Needs review); what leaders see; one or two actions each | Where "Needs review" leads (§8.10) |
| 20 | Employee | Sunil | "Who can see your attendance and leave" on My attendance | Brief §5 |

The v1 state "Linked to two branches — shows nothing" is **gone**. The only state that
shows nothing is "Leadership role, no company or branch linked".

**Other unhappy paths, specified but not clicked in the prototype:**

| Case | Behaviour |
|---|---|
| A long branch name ("Head Office and Central Warehouse, Gurugram Sector 44") | Wraps in the table cell and the phone row; never truncated with no way to read it |
| 400 people in one branch, 40 departments | Department list is sorted by name; phone rows are 64 px each; no pagination needed below ~60 rows. Above that, paginate at 50 [ASSUMPTION] |
| Hindi runs ~30% longer | Checked with the partial Hindi draft: card headings wrap to two lines on a 400 px phone, no overflow |
| A brand-new tenant with no attendance yet | Attendance and Leave cards say "No figures yet. They appear after the first full day of attendance." People card works from day one. **Not "Needs review"**: there is nothing wrong for HR to fix, and the label would send HR looking for a problem that does not exist |
| Leader linked to 6 or more branches | Desktop switcher becomes the same "Showing" button as the phone, opening a list (a row of 6+ buttons wraps badly). Branch table as usual |
| Remembered branch no longer linked | Home and the overview fall back to All my branches, with no message |
| Leader linked to every branch of the company | Treated as company scope: title "Company overview", no switcher, no company comparison |
| Company permission plus Branch permissions | The branches win (the narrower scope), as in v1 |
| Data up to date is more than 3 days old | The "Data up to" line turns into an amber chip: "Attendance is 5 days behind. HR has been told." [ASSUMPTION — threshold] |
| Leader's own scope changes (moved branch) | Next page open shows the new scope; nothing cached per person (OPS-2 keys by scope) |
| Plan without `analytics` | No menu entry, no Home card. ⚠ brief P6 is open |
| Offline or timeout on every card | Page shows "Could not load your figures. Check your connection and try again." + Try again. Nothing stale is shown without its "as of" time |

---

## 7 · The small-group rule, as the design assumes it (for 01c to confirm)

1. **Do not share** a sensitive figure for a group with fewer people than the minimum
   (default 5, allowed 3–10). **The count is the distinct people inside that figure for
   its period**, not today's headcount (07 §2 OPS-19). Slice 011 keeps the branch an
   attendance record was saved with, so a branch with 6 people today may have September
   attendance from only 4. Headcount and joiners are counted as they are shown.
2. **Subtraction:** if any group in a set is hidden, keep hiding the next-smallest group
   until at least two groups are hidden **and** the hidden groups together reach the
   minimum. (Lakeside departments: Security 4 is hidden, so Stock room 9 is hidden too.)
3. **Sensitive figures:** attendance %, late arrivals, short days, days absent, on leave
   today, leave used, requests waiting, leavers, attrition. **Always shown:** headcount,
   joiners. **Never shown to leaders at any size:** names, days, leave types or reasons, pay.
4. **Inheritance (new, LD1):** a group hidden in a parent table stays hidden on its own
   page, and so do all groups inside it.
5. **Comparison (new, LD2):** a branch head's "Company x%" is hidden when the company minus
   their branch is below the minimum.
5a. **Several branches (round 2, LD10):** for a leader linked to several branches, rules 1
   and 2 run across **their own set** of branches. "All my branches" is shown when the set
   together reaches the minimum. A branch not shared in their table **stays not shared**
   when they choose it alone in the switcher (rule 4, applied to the switcher). Its
   departments are then not shared either.
5b. **Company comparison for several branches:** "Company x%" is shown only when **both**
   the company minus all their branches **and** the company minus the branch on screen
   reach the minimum. If their branches are the whole company, they get company scope and
   no comparison. *Why both:* the leader already sees their set and each branch, so the
   company figure reveals "the rest of the company" by subtraction.
5c. **The multi-branch rule is per leader, not per company.** A branch not shared in the
   company head's table (Station Road, to protect Hilltop Kiosk) can be shown to a leader
   whose set does not include the kiosk. That leader cannot see the kiosk's neighbours, so
   nothing can be worked out. This matches a single branch head seeing their own branch.
6. **Today counts** are not shown for a group below the minimum.
7. **Server side:** a hidden figure is not in the response at all. The explanation sheet says so.
8. **Residual risk to record, not solve here:** two leaders pooling what each can see (a
   branch head of Station Road plus the company head) can rebuild a hidden figure. The
   design cannot prevent collusion. Also, a group moving above and below the minimum from
   month to month could leak through the trend. The trend is only shown for groups at or
   above the minimum today; 01c should say whether that is enough. Round 2 adds one more
   pooling case: an area manager and a branch head inside the same set. Same answer —
   record it, do not solve it here.

---

## 8 · Screen specs with the exact words

English is the source. Hindi is a **machine draft for native review** (see the
learnings file; slice 009 Wave 5 owns Hindi). Numbers below are sample.

### 8.1 WOW card (Home, top)

| Element | English | Hindi (draft) |
|---|---|---|
| Eyebrow | Lakeside Mall · September so far | लेकसाइड मॉल · सितंबर में अब तक |
| Headline | Attendance 96.1% | हाज़िरी 96.1% |
| Change | ↑ Up 0.3 points on 1–13 Aug · Company 96.8% | ↑ 1–13 अगस्त से 0.3 अंक ज़्यादा · कंपनी 96.8% |
| Second line | Late arrivals 41, 12 fewer than 1–13 Aug | देर से आए 41, 1–13 अगस्त से 12 कम |
| Company scope extra line | 288 people · 48 joined and 31 left in 12 months | 288 कर्मचारी · 12 महीनों में 48 जुड़े, 31 गए |
| Freshness | Data up to 13 Sep · as of 10:40 | डेटा 13 सितंबर तक · 10:40 बजे तक |
| Button | Open branch overview / Open company overview | शाखा का सारांश खोलें / कंपनी का सारांश खोलें |
| Doubtful-data line (inside the card when state 7 applies) | ⚠ 3 days in September look wrong and are left out. HR can see this too. | ⚠ सितंबर के 3 दिन गलत लगते हैं, इसलिए गिने नहीं गए। HR को भी यह दिखता है। |
| Company scope line when leavers need review | 288 people · 48 joined in 12 months · leavers need review | 288 कर्मचारी · 12 महीनों में 48 जुड़े · छोड़ने वालों की जाँच बाकी है |
| Eyebrow, several branches | All my branches (Old Market and Riverside) · September so far · **Change** | मेरी सभी शाखाएँ (…) · सितंबर में अब तक · **बदलें** |
| Own scope not shared | 🔒 Not shared: too few people in this group for a fair picture · "4 people · 1 joined in 12 months" | साझा नहीं: इस समूह में लोग बहुत कम हैं, इसलिए सही तस्वीर नहीं बनती |

Rules: down arrows and up arrows carry words ("Up", "Down", "Same as"). No green or red.
The company comparison appears only for a branch or several-branch scope, and only when
rule 5 or 5b allows it.

**Home for a leader of several branches:** the card shows the **last scope they chose**
on the overview. The first time, it shows **All my branches**. "Change" opens the same
"Choose what to show" sheet. The choice is saved per user on the server (a Frappe user
default), so it follows the person from phone to laptop. It holds only a branch name,
nothing sensitive. If that branch is no longer linked, the card falls back to All my branches.

### 8.2 Today strip

"Today, Monday 15 Sep · Lakeside Mall" · **51** in so far, of 61 expected · **3** on leave ·
**10** not checked in yet · "Last check-in received 10:32. No names." · Why? →

Why sheet: "In so far: people with a check-in today. Expected: people on today's rota who
are not on leave or a weekly off. Not checked in yet: expected minus in so far. It may
still be early in their shift. Last check-in received 10:32: check-ins arrive when the
attendance device sends them, which can be a few minutes after people walk in. If a
branch has had no check-ins for 7 days, only 'on leave' is shown."

D11 **approved**, with the DevOps indexes on `Employee Checkin` (OPS-20). When leave needs
review, the "on leave" box says **Needs review**. For several branches the heading reads
"Today, Monday 15 Sep · All my branches".

### 8.3 Cards

**Attendance** — "How is this worked out?"
- Big: **96.1%** · "present, September so far"
- "↑ Up 0.3 points on 1–13 Aug" · "Company **96.8%**"
- Rows: Late arrivals **41** — "12 fewer than 1–13 Aug"; Short days **14** — "2 more than 1–13 Aug"
- Footer: "Data up to 13 Sep"
- Sheet (wording must match the Step 0 formula): "Present % = days people were present,
  divided by days they were expected to work… A half day counts as half. Work from home
  counts as present. Weekly offs, holidays and approved leave are not expected days…
  Comparisons use the same days last month… HR Analytics uses exactly this calculation."

**Leave**
- Big: **3** · "on leave today"
- "Leave used this leave year **18%**" · "281 of 1,536 days · 1 Apr 2026 to 31 Mar 2027" · bar · "Company 19%"
- "Requests waiting more than 3 days **1**" · "Managers and HR see who. You see the count only."
- Footer: "Leave reasons and types are never shown"

**People**
- Big: **64** · "people today" · "↑ Up 4 from 60 a year ago"
- Joined, last 12 months **11** · Left, last 12 months **7** · Attrition, last 12 months **11.3%** · "Approximate for a branch. Company 11.1%."
- Footer: "Headcount and joiners are always shown"
- Nobody left: "0 — Nobody left this branch in the last 12 months." ("these branches" for several). Only when the leavers data does not need review.
- Leavers need review (D18): Left **Needs review** · Attrition **Needs review** · "14 people are marked as left with no leaving date." · *Why does this need review?*

**Figure not shared (every place)** — wording chosen by the user, 15 Sep 2026
- Inline, in table cells and short rows: 🔒 **Not shared** (lock icon + the words)
- Block on a card: 🔒 **Not shared: too few people in this group for a fair picture** · names what is not shared · *Why is this not shared?*
- Table footer: "Sorted by name. Totals only, no names. **2 of 6 branches: figures not shared.** Why?" · two branches: "With two branches, sharing one would reveal the other."
- Company comparison line: "🔒 Company comparison not shared: it would let someone work out a small group's figures. Why?"
- Sheet title: **Why is this not shared?**
- Sheet text:
  > **Not shared: too few people in this group for a fair picture.**
  > When fewer than 5 people are counted in a figure, one person's days can swing the whole
  > number. It would not be a fair picture of the group. A small total can also point at one person.
  > The count is the people inside that figure for its period, not today's headcount. A branch
  > with 6 people today may have September attendance from only 4 of them.
  > So that nobody can work out a figure by subtraction, the next-smallest group is not shared
  > either. That is why a larger group can also show "Not shared".
  > Headcount and joiners are always shown. Company totals still include every group.
  > *Figures that are not shared are never sent to your phone or computer, so they cannot be
  > found in the page. The minimum is set by your organisation's System Manager.*
- Hindi (draft): "साझा नहीं" · "साझा नहीं: इस समूह में लोग बहुत कम हैं, इसलिए सही तस्वीर नहीं बनती" · "यह साझा क्यों नहीं है?"

**Banner, large branch not shared to protect a smaller one** (Station Road, 42 people):
- Heading: the sentence above — **or**, if you choose the D17 variant, **"Not shared: it would let someone work out a smaller group's figures"**.
- Body: "This branch has 42 people, but sharing its totals would let anyone work out the figures
  for a smaller branch by subtraction. Headcount and joiners are still shown. Company totals
  include this branch."

**Own branch below the minimum:** heading in the user's sentence. Body: "Fewer than 5 people
are counted in this branch's figures. One person's days would swing each total, so it would
not be a fair picture, and a total could point at one person. Headcount and joiners are
still shown. If you manage these people, you can see their days in My team."

### 8.4 Doubtful data (Step 0, P4)

Banner, amber, above the cards:

> ⚠ **Some attendance days look wrong**
> On 8, 9 and 10 Sep almost everyone is marked absent. This is usually missing check-in
> data, not real absence. These 3 days are left out of the attendance figures below until
> HR fixes or confirms them. HR sees the same warning.
> *How doubtful days are found* · *Show attendance with those days*

Hindi draft: "**कुछ दिनों की हाज़िरी गलत लगती है।** 8, 9 और 10 सितंबर को लगभग सभी को
गैरहाज़िर दिखाया गया है। ऐसा आमतौर पर चेक-इन डेटा न आने से होता है, असली गैरहाज़िरी से नहीं।
HR के ठीक करने या पुष्टि करने तक ये 3 दिन नीचे की हाज़िरी में नहीं गिने गए हैं। HR को भी यही चेतावनी दिखती है।"

On the Attendance card: chip "⚠ 3 doubtful days left out" and a link "Show the figure with
those days (71.4%)". When shown: chip "⚠ Includes 3 doubtful days, likely wrong", the change
line is removed, and the link reads "Leave the 3 doubtful days out again". The trend bar for
September is striped, with the note "September is striped: 3 doubtful days are left out."

Rule sheet: "A working day is marked doubtful when 95% or more of the people expected at
work are marked absent, and fewer than 5% checked in… Doubtful days are left out of
attendance, late arrivals and short days until HR fixes the data or confirms the absence was
real. If HR confirms it, the day is counted again. The check is only made for groups of at
least 5 expected people, so a small team's real day off is not left out." D5 and D5b
**approved**. The small-group limit follows DevOps OPS-22; in a tenant with no check-ins at
all, the rule is "95% absent" alone. Doubtful days keep the **amber** warning.

**Needs review (replaces "Not recorded", user decision 15 Sep 2026)**

Used whenever a figure is replaced because its data looks missing or implausible. Never 0
or 0%. Neutral colour (it is not the leader's fault and not an error on the page), with a
clipboard icon and the words.

| Where | Shows |
|---|---|
| Leave card, big number | 📋 **Needs review** · "Leave used this leave year" · "Only 3 leave requests have been entered this leave year, for 288 people with 6,912 days of leave between them. A percentage would mislead, so HR is asked to check the leave data first." |
| Leave card rows | On leave today **Needs review** · Requests waiting more than 3 days **Needs review** · *Why does this need review?* |
| People card | Left **Needs review** · Attrition **Needs review** (D18) |
| Today strip | "on leave" box: **Needs review** |
| Tables and total row | On leave today, Leave used, Left (12 mo): **Needs review** · footer "Needs review: HR is checking the data behind leave and leavers. Why?" |
| Home WOW card, company scope | "288 people · 48 joined in 12 months · leavers need review" |

Sheet **"Why leave needs review"**:
> **Needs review** means the data behind a figure looks incomplete, so Alvoraa does not show a
> number that could mislead. It is never shown as 0 or 0%.
> **For example:** 288 people have 6,912 days of leave between them this leave year, but only 3
> leave requests have been entered. "Leave used 0%" would suggest nobody took any leave, which is
> very unlikely. Leave is probably being recorded somewhere else.
> So leave used, on leave today and requests waiting all say "Needs review", everywhere on this page.
> **What happens next:** HR sees this in *Data to review*, with what to check. Once HR enters the
> missing leave, or confirms the figure is right, the number appears here.

Sheet **"Why leavers need review"**:
> **Needs review** means the data behind a figure looks incomplete… It is never shown as 0.
> **For example:** 14 people are marked as left but have no leaving date. Without a date, nobody
> can tell whether they left in the last 12 months, so leavers and attrition would come out too low.
> **What happens next:** HR sees these 14 records in *Data to review*. Once each has a leaving
> date, leavers and attrition appear here.

Hindi (draft): "जाँच बाकी है" · "इसकी जाँच क्यों बाकी है?"

Rules: D6 (leave taken under 1% of leave given, 3 or more months into the leave year) is
approved. D18 (below) sets the leavers rule. A brand-new tenant with no data says "No
figures yet", not "Needs review" (§6).

### 8.5 By branch / by department

- Heading "By branch" (company) or "By department" (branch). Company table adds "Tap a branch to open it".
- Desktop columns: Branch · People · Joined (12 mo) · Attendance · Late arrivals · On leave today · Leave used · Left (12 mo). Last row: "Kavya Retail, all branches" / "Lakeside Mall, whole branch".
- Phone row: name ›, "64 people · 11 joined in 12 months", "Late 41 · On leave today 3 · Leave used 18%", right side **96.1%** "attendance" — or 🔒 Hidden.
- Footer: see "Figure not shared" in §8.3.
- Several branches: heading "By branch", hint "Tap a branch to look at it alone", total row "Your 2 branches, together". Tapping a row changes the switcher to that branch.
- Department rows do not open anything. There is no individual level in this slice.

### 8.6 "What you can see" sheet

"**Where:** Lakeside Mall, 64 people. **What:** totals for people, attendance and leave.
**Never:** anyone's name, their days, why they were away, or pay. **Small groups:** figures
are not shared when fewer than 5 people are counted. **You are counted too:** your own attendance and leave are inside
these totals. Your access comes from the Leadership role and a link to your branch, set by
your System Manager. Your employees see a line on their own attendance page that tells them this."

### 8.7 No company or branch linked

Title: **Your leader view is not set up yet** (आपका लीडर व्यू अभी सेट नहीं है)
Body: "You have leader access, but your account is not linked to a company or a branch.
Until it is, this page shows nothing. That keeps everyone's information safe."
"**What to do:** ask your System Manager to link your account to your company or your
branch. You can send them this message:" — quote box — **Copy message** · Go to Home.
Message: "Please link my Alvoraa account (Rohan Das) to my company or my branch, so my
leader overview works. I have the Leadership role, but no company or branch is linked."

### 8.8 Linked to several branches — the branch switcher (D7, decided 15 Sep 2026)

**Who:** Leadership role plus Branch User Permissions on two or more branches of one company.

**The switcher** sits at the top of the page, above the subtitle. It has a visible label.

| | Phone | Desktop |
|---|---|---|
| Control | Label **Showing** + a chip button "▤ All my branches ›" (44 px tall) | Label **Showing** + a row of radio buttons: "All my branches · Old Market · Riverside" |
| Opens | A bottom sheet **Choose what to show** with one radio row per option (56 px each) | Nothing; one click changes the scope |
| 6 or more options | Same sheet | The phone's button and a list, so the row never wraps across lines |
| Keyboard | Sheet traps focus, Esc closes, focus returns to the chip | Radio group: Tab reaches it once, arrow keys move, Enter or Space picks (roving focus) |

Sheet rows (sorted: All my branches first, then branches by name):
- **All my branches** — "Old Market and Riverside · 120 people, added together"
- **Old Market** — "71 people"
- **Riverside** — "49 people"
- Below: "Home shows your last choice. Figures that are not shared stay not shared, whichever you choose." · **Cancel**

**All my branches** shows:
- Title "Branch overview". Subtitle "All my branches: Old Market and Riverside · 120 people · September so far".
- Today strip, Attendance, Leave and People cards, and the 6-month trend, **for the branches added together**.
- Comparison: "Company 96.8%" only under §7 rule 5b. People card: "Approximate for a group of branches."
- **By branch** table, exactly like the company head's, limited to their branches: sorted by name, no ranking, no sorting by result, tap a row to look at that branch alone. Total row "Your 2 branches, together". Hint "Tap a branch to look at it alone".
- Small-group rules across the set (§7 rule 5a). Example in the prototype: Dev Malhotra has Hilltop Kiosk (4) and Station Road (42). Together (46) is shown; both rows say "Not shared"; choosing either branch alone shows headcount and joiners only.

**One branch chosen** shows the normal branch page with its departments, title = the branch
name, breadcrumb "Branch overview ›" back to All my branches, and the switcher still visible.

**Home:** see §8.1 — last choice, first time All my branches.

**Out of this slice (D19):** a leader linked to more than one **company**.

### 8.9 Loading and error — per card (see §17)

- Frame and skeletons appear within 0.3 s: a skeleton for Today, each of the three cards, the trend, the week card and the table.
- **Each card fills in on its own** as its figures arrive. A slow or failed card never holds up or blanks the others.
- Screen readers hear "Loading your branch figures" at the start and "All branch figures loaded" at the end, not one message per card.
- One card fails: "**Attendance figures did not load.** Your people and leave figures are up to date. This is usually a short network problem." · **Try again** (reloads only that card). Success toast: "Attendance figures loaded".
- Home: the WOW card has its own skeleton and its own small call. It never waits for the overview.

### 8.10 HR side — Data to review (where "Needs review" leads)

**Place:** Company › **Data to review** (count badge), for HR Manager; store HR sees only
items for their own branch, using the same scoping as HR analytics after slice 011's fix.
Also a line at the top of HR analytics — "**3 figures need review.** Leaders see 'Needs
review' until they are fixed. Open Data to review" — and an item in HR's "Needs you" strip on Home.

**Intro:** "These figures show **Needs review** to company and branch heads until you fix the
data or confirm it is right. Leaders see the label and a short reason, not these details."

| Item | Chip | What HR reads | "Leaders see" line | Actions |
|---|---|---|---|---|
| Doubtful days | ⚠ Doubtful days (amber) | "On 8, 9 and 10 Sep, 96–99% of the people expected at work are marked absent, and fewer than 2% checked in. This usually means the check-in device did not send its data." "These days are left out of attendance, late arrivals and short days, for HR and for leaders." | an amber warning, "3 doubtful days left out", and attendance without those days | **Open attendance for these days** · **The absence was real** (confirm: "Count 8, 9 and 10 Sep as real absence? … Attendance for September will drop to about 71.4%. This is recorded with your name." · Keep them left out / Count them) |
| Leave used | 📋 Needs review | "Only 3 leave requests have been entered this leave year, for 288 people with 6,912 days of leave between them." "Leave is probably being recorded somewhere else, so 'leave used 0%' would mislead." | "Needs review" for leave used, on leave today and requests waiting | **Open leave requests** · **The figure is right, show it** (confirm: "Leaders will see leave used as 0.2% … Only do this if leave really is recorded in Alvoraa. This is recorded with your name." · Keep "Needs review" / Show it) |
| Leavers | 📋 Needs review | "14 people are marked as left but have no leaving date. Without a date, nobody can tell whether they left in the last 12 months." | "Needs review" for leavers and attrition | **Open these 14 people** (the Employee list, filtered; HR already sees names). No "it is right" button: a missing date is always a gap |

Each item ends with when it was found and when it is checked again ("Found 11 Sep, 06:00 ·
Checked again every morning"; "Clears by itself once every leaver has a leaving date").
Footer: "Every 'the figure is right' confirmation is kept with who made it and when."

An item disappears from the list, and the leader label goes, when the rule no longer fires
or HR confirms it. Nothing here is shown to leaders.

---

## 9 · Settings: Leader view privacy (System Manager; HR Manager reads)

**Place:** Company › Org settings › tab **Leader view privacy**. Title "Leader view privacy".
Intro: "These rules decide what company heads and branch heads can see. They apply to every
leader in Kavya Retail."

**Card 1 — Smallest group shown**
- "Leaders see totals, never individuals. When fewer people than this number are counted in
  a group's figure, its attendance, leave and leaver figures are not shared: too few people
  for a fair picture. The next-smallest group is not shared either, so nobody can work the
  figure out by subtraction."
- Stepper: "Hide groups smaller than" [−] **5 people** [+] · "Allowed: 3 to 10. Default: 5. Now saved: 5."
- Live impact: "With 5: about 2 of 6 branches and 14 of 26 departments have figures not shared" — updates as the stepper moves, before saving. Under it: "'About', because this uses today's headcount. Leader figures count the people inside each figure for its period, so a group that has shrunk can have a few more figures not shared."
- Three boxes: *Not shared below the minimum* · *Always shown* · *Never shown to leaders*.
- Field: "Why are you making this change?" · "Required. Kept in the change history below."
- Buttons: **Save change** · "Keep 5" (appears only after a change).
- Errors: "Choose a different number first. The saved value is already 5." · "Add a short reason. It is kept with the change."
- Lower-limit taps: toast "3 is the lowest allowed" / "10 is the highest allowed" (the button is never greyed).
- Confirm dialog, lowering: title "Change the smallest group from 5 to 3?" · "Leaders will start to see figures for groups of 3 or 4 people. In small groups, people can often guess who a figure is about. This change is recorded with your name and reason." · **Keep 5** · **Change to 3**.
- Confirm dialog, raising: "Leaders will stop seeing figures for groups of 5 people. This change is recorded with your name and reason."
- Toast after saving: "Saved. Leaders see the new rule the next time they open their overview." (OPS-4: clear the cache on settings change.)
- **HR Manager:** the value as text, "🔒 Only a System Manager can change this setting." No field, no button.

**Card 2 — Who has leader access** (read-only list)

| Leader | Linked to | What they see |
|---|---|---|
| Meera Nair | Company: Kavya Retail | Company overview |
| Arjun Mehta | Branch: Lakeside Mall | Branch overview |
| Farah Khan | Branch: Hilltop Kiosk | Headcount and joiners only (fewer than 5 people) |
| Neha Iyer | Branches: Old Market, Riverside | Branch overview for 2 branches, together or one at a time |
| Dev Malhotra | Branches: Hilltop Kiosk, Station Road | Branch overview for 2 branches. Totals together only; each branch's figures not shared |
| Rohan Das | No company or branch | ⚠ Nothing yet. No company or branch linked |

Footer: "Leader access = the Leadership role plus a User Permission on a company or on one
or more branches. Change it in Desk, User Permissions. Frappe keeps its own record of those changes."
· **Open User Permissions**. This list shows problems before a leader meets them.

**Card 3 — Change history**
"Every change to these settings is kept here, with who made it and why. Nobody can edit
these records. System Managers and HR Managers cannot delete them; only the site's
Administrator account can." (Round 2: v1 said "nobody can delete it", which is not true for
Administrator — Frappe `Version` records, 07 §2 OPS-23.) Columns: When · Who · Change · Reason given. Newest first. Example:
"12 Sep 2026, 16:40 · Vikram Shah · Smallest group: 6 → 5 · Back to the default after the
security review." First row ever: "System (set up) · Smallest group: set to 5".

---

## 10 · Employee line (My attendance and My leave)

Collapsed row under the page header: 👁 **Who can see your attendance and leave** ›
Expanded:
- "**You, your manager and HR** see your days, your times and your leave, including the type of leave."
- "**Your branch head and company head** see only totals for Lakeside Mall and the company. They never see your name, your days, or why you were away."
- "Totals for groups of fewer than 5 people are not shared: too few people for a fair picture, and a total could point at you."
- Round 2: "Your branch head and company head" becomes "Your branch head, area manager and company head" when a leader of several branches covers the employee's branch.

The branch name and the number come from the real settings. If the tenant has no leaders
set up, the second bullet is left out. ⚠ D14: the first bullet must be checked against the
real permissions (does a store HR person see leave types? It should say "HR at your branch"
if slice 011 scoping applies).

---

## 11 · Accessibility (WCAG 2.2 AA — target per nfr-budget §7; not re-checked this run)

| Item | How the design meets it |
|---|---|
| Colour never the only signal | Not shared = lock icon + "Not shared"; needs review = clipboard icon + "Needs review" (neutral colour); doubtful = warning icon + words + stripes on the bar; change = arrow + "Up/Down"; switcher choice = filled radio + tinted row, not tint alone |
| Switcher | Visible "Showing" label tied to the control; desktop is a `radiogroup` with `aria-checked` and roving focus; phone chip has `aria-haspopup="dialog"`; the sheet is a radio group with the same labels |
| Contrast | Text uses `--text`, `--text2`, `--text3` (#736D65, 4.74:1 — the 009 appendix rule). Brand colours go through the existing lightness clamp. Amber chip text #9A6510 on #FBF1E0 [ASSUMPTION ≥ 4.5:1 — verify with a checker] |
| Target size | 44 px on phone for every button, link, tab and stepper (measured). Desktop menu items 40 px, above the 24 px AA minimum |
| Keyboard | Every control is a `button`, `select`, `summary` or `textarea`. Sheets and the dialog trap focus, close on Esc, return focus to the opener. Page title takes focus after navigation |
| Screen readers | Cards are `section` with `aria-labelledby`; tables have `scope` headers and a caption; charts are `role="img"` with every value in the label; toasts are `role="status"`; the confirm is `alertdialog`; loading has a status message |
| Forms | Reason field has a visible label, hint linked by `aria-describedby`, `aria-invalid` and a linked error |
| Zoom and 360 px | Grid collapses to one column; no fixed widths; no sideways scroll at 400 px (measured) |
| Motion | Skeleton shimmer and sheet slide are turned off under `prefers-reduced-motion` |
| Language | `lang` set on the app; Hindi fonts in the font stack (Noto Sans Devanagari, Nirmala UI) |

---

## 12 · Privacy, screen by screen

| Screen | Who can see it | Least they need? | Small groups |
|---|---|---|---|
| WOW card, Today, overview | Leadership role + one Company or Branch permission | Totals only; no names, days, leave types, pay | Rules 1–6 of §7 |
| Branch drill-down | Company head only | Totals; departments with the same rule | Inheritance rule |
| Several branches (switcher) | Leadership role + two or more Branch permissions | Totals for their branches, together and each | Rules 5a–5c of §7 |
| No-permission | The person themselves | Their own name only | — |
| Data to review | HR Manager; store HR for their branch | Counts and dates on the page; names only after "Open these 14 people", in lists HR already sees | — |
| Remembered scope | The leader | A branch name saved as a user default; no figures | — |
| Settings | System Manager (edit), HR Manager (read) | Leader names and their scope; no employee data | — |
| Change history | System Manager, HR Manager | Who, when, before, after, reason | — |
| Employee line | The employee | Describes access; shows no one else's data | Quotes the minimum |

No names, pay or scope values in URLs (OPS-11): the prototype's drill uses an ID in
memory; the build should send the branch in the request body.

---

## 13 · Decisions for you

**Round 2 status (15 Sep 2026):** D1, D3, D4, D8–D16 **approved as recommended**, with
the DevOps indexes. D5 **approved**. D6 **approved with the label "Needs review"**. D2
**decided by the user with new wording**. D7 **decided: branch switcher**. New: D17–D19.

### New decisions — round 2

| # | ⚠ DECISION | Options | My recommendation | Owner | Blocks |
|---|---|---|---|---|---|
| D17 | Wording on a **large** group not shared only to protect a smaller one (e.g. Station Road, 42 people) — banner and card blocks only; cells say "Not shared" in both options | (a) your sentence everywhere: "Not shared: too few people in this group for a fair picture"; (b) that case only: "Not shared: it would let someone work out a smaller group's figures" | **(b)** (a) states something untrue on that page, and the page body then contradicts its own heading. Headcount is shown beside every group anyway, so naming the reason reveals nothing new. Try both with the prototype switch | Surbhi | Banner and block copy |
| D18 | When leavers and attrition "need review" | (1) anyone in scope marked Left with no leaving date; (2) nobody in the whole tenant has a leaving date in the last 12 months; (3) both | **(3) both.** (2) is v1's "none recorded anywhere" rule; (1) catches the partial gap the v2 example shows | Engineer + Surbhi | People card, tables, HR Data to review |
| D19 | Leader linked to **more than one company** (brief: "a person heading two companies waits") | (a) show the company on their own Employee record, plus a line "You are linked to 2 companies. Viewing more than one company is planned for later."; (b) a switcher of companies with no combined view; (c) show nothing | **(a)** Keeps "no company or branch linked" as the only empty state, as you asked, without building the multi-company switcher the brief put later. Different companies can have different leave years and rules, so no combined totals | Surbhi | Access rule, settings list |

### Decisions from round 1 (status updated)

| # | ⚠ DECISION | Options | My recommendation | Owner | Blocks |
|---|---|---|---|---|---|
| D1 | Where the view sits | (a) Company › Branch/Company overview; (b) Team › My branch for branch heads | **(a)** — **approved** | Surbhi (also answers 009 H-1 in part) | Menu list |
| D2 | Wording on hidden figures | (a) one label, "Hidden to protect a small group"; (b) brief's "Fewer than 5 people — hidden" | **Decided 15 Sep: neither.** "Not shared" in cells; "Not shared: too few people in this group for a fair picture" in full. See D17 for one case | Surbhi | All copy |
| D3 | Subtraction rule detail | (a) keep hiding until ≥ 2 hidden and together ≥ minimum; (b) hide only one extra group | **(a)** (b) can leave two tiny groups that sum below the minimum | Security (01c) | Server rule |
| D4 | Two-branch company, and branch-vs-company | (a) general rule: hide both only when one is small; hide a branch head's company comparison when the rest of the company is below the minimum; (b) brief: never split two branches | **(a)** Protects the same people and keeps useful figures for two large branches | Surbhi + security | Tables, comparison line |
| D5 | Doubtful day threshold | 95% absent and almost no check-ins; or 90%; or "every record absent" | **95% and fewer than 5% with a check-in** | Engineer (Step 0) + Surbhi | Warning, headline |
| D5b | Doubtful days in the headline | (a) leave them out, say so, one tap to see with them; (b) show the raw figure with a warning | **(a)** A leader will quote the big number. It should be the believable one, labelled | Surbhi | Attendance card, HR Analytics |
| D6 | When leave counts as "needs review" (v1: "not recorded") | e.g. leave taken under 1% of allocated, 3+ months into the leave year | **That rule**, same for HR and leaders — **approved, label "Needs review"** | Engineer + Surbhi | Leave card |
| D7 | Leader linked to more than one branch (or company) | (a) fail closed with an explanation; (b) combine the branches; (c) add a branch picker | **Decided 15 Sep: (b) and (c) together** — a switcher with "All my branches" (combined totals plus a by-branch table) and each branch. Companies: D19. Company + Branch permission together = the branches (the narrower scope) | Surbhi | Access rule, settings list |
| D8 | Reason required when changing the minimum | Required / optional | **Required** | Surbhi + security | Settings |
| D9 | HR Manager sees the change history | Yes / no | **Yes, read-only** | Surbhi | Settings |
| D10 | Colour on rises and falls | Neutral with arrows and words / green-red | **Neutral** | Surbhi | Cards |
| D11 | "In so far today" count | Show if DevOps confirms cost; else on leave today only | **Show, pending OPS-13 check** | DevOps | Today strip |
| D12 | Sorting tables by a result column | By name only / sortable | **By name only** in this slice | Surbhi | Tables |
| D13 | Month-in-progress comparison | Same days last month / whole last month | **Same days last month** | Surbhi | Every change line, WOW copy |
| D14 | Exact "who sees your leave" wording | Driven by real roles incl. store HR scope | Build from real permissions; review with security | Security + BA | Employee line |
| D15 | Company head by department across all branches | (a) not in v1 prototype; (b) add a "By department" tab on Company overview | **(b)** — approved as recommended, but **not drawn in v2**: round 2 was limited to the feedback points. Spec: a "By branch · By department" tab pair on Company overview; departments with the same name across branches added together; same small-group rules; rows do not open | Surbhi | Company overview |
| D16 | Head of a branch below the minimum | Show the page with most figures hidden / hide the menu entry | **Show it**, with the explanation. Silence would look broken | Surbhi | Tiny branch state |

---

## 14 · Checks before handoff

**Nielsen's heuristics (where they apply)**
1. Visibility of status — "Data up to", "as of 10:40", loading skeleton, "Saved" toast.
2. Match with the real world — "on leave today", "left, last 12 months"; no "person-days" or "utilisation".
3. User control — "Keep 5" and a confirm before a privacy change; sheets close with Esc.
4. Consistency — one hidden label, one date style ("13 Sep 2026"), 24-hour times, same cards at both scopes.
5. Error prevention — reason required; stepper bounded 3–10; confirm dialog names the effect.
6. Recognition over recall — every number carries its explanation one tap away.
7. Flexibility — WOW card answers the top question with zero taps; drill-down for more.
8. Minimal design — three cards, one trend, one table.
9. Recover from errors — card-level retry; setup problems give a message to send.
10. Help — "How is this worked out?", "Why is this hidden?", "What you can see".

**Persona walkthrough (top task)**

| Persona | Task | Today (01a) | With this design |
|---|---|---|---|
| Branch head | "Attendance vs company this month" | Borrow Attendance Insights "everyone below"; no company figure; wrong rate possible | 0 taps — WOW card on Home |
| Company head | "Which branch should I ask about?" | Needs HR Manager; HR Analytics unscoped, no branch table | 1 tap — Company overview, by branch |
| Company head | "Leavers this year" | Not available | 1 tap — People card |
| System Manager | "Lower the minimum and prove who did it" | No setting | 5 actions — stepper, reason, save, confirm; history row |
| Employee | "Who sees my leave?" | Nowhere | 1 tap on My attendance |
| Area manager (2 branches) | "How are my branches doing, and which one is behind?" | v1: nothing shown | 0 taps for the combined figure on Home; 1 tap for the by-branch table |
| HR Manager | "Why do leaders see 'Needs review', and what do I fix?" | Nowhere | 1 tap from HR analytics or Home to Data to review; 1 more to the records |

**Frontline bar:** a store head answers "attendance vs company", "on leave today" and
"leavers this year" in under 2 minutes on a phone — first two on Home, third one tap away.
To be proved in the test below (brief S4).

**Refusals:** no ranking (sorted by name), no individual watching (totals only, reasons
never), no AI, no dark patterns (no nagging, nothing pre-ticked, "Keep 5" is as visible as
"Change to 3"), no forced curve (no ratings in this slice). None crept in.

**Plain-language test:** every screen reads without knowing Alvoraa or Frappe, except the
settings footer "User Permissions", which is the Frappe name a System Manager needs to find.

---

## 15 · Usability test plan (High impact)

**Who (5):** 1 owner or MD; 2 branch heads on their own Android phones (one of them, if
possible, an area manager with two or more branches); 1 HR Manager; 1 System Manager or IT person. Moderated, 30 minutes each, the prototype on their device.

| # | Task (said aloud) | Success | What would change the design |
|---|---|---|---|
| T1 | "How is your branch's attendance this month compared with the company?" | Correct answer from Home in under 30 s, unaided | If 2+ look for it in the menu first → move the comparison into the page title area too |
| T2 | "How many people are on leave today, and who are they?" | Gives the count, and says the names are not shown | If 2+ think the view is broken → add "No names" beside the count, not only below |
| T3 | "How many people left in the last 12 months?" | Finds it in under 1 minute (brief S4: three questions under 2 minutes) | If slower → move leavers into the WOW card at company scope |
| T4 | "Station Road shows Not shared. Why? How many people are late there?" | Explains it in their own words and does not guess a number | If 2+ say "but it has 42 people" or find the wording false → choose the D17 variant; if 2+ read "Not shared" as someone refusing them → add "for privacy" to the cell |
| T4b | Data-looks-wrong state: "What is leave used this year?" then "What happens next?" | Says it needs review and that HR is checking | If 2+ think *they* must review something → change to "HR is checking" on the card itself |
| T4c | Area manager: "Show me only Riverside, then go back to both" | Done unaided in under 20 s on a phone | If the chip is missed → put the switcher in the page title ("Branch overview: All my branches ▾") |
| T5 | Data-looks-wrong state: "How was attendance in September?" | Quotes 96.8% and mentions the left-out days | If they quote 71.4% or ignore the banner → put the warning inside the WOW card too, not only on the overview |
| T6 | System Manager: "Allow groups of 3, and show me where that change is recorded" | Completes with a reason and finds the history row | If the reason field is skipped or annoying → keep required but offer common reasons |
| T7 | HR Manager: "Can you change the group size?" | Says no, and knows who can | If they think the page is broken → add the System Manager's name |
| T8 | All: "Name one thing you would do after seeing this." | A concrete action ("move a Saturday shift", "ask HR about the 3 days") | **Kill criterion** from the brief if fewer than 3 of 5 can |

---

## 16 · For the business analyst — behaviours to turn into acceptance criteria

1. A user with the Leadership role and **no** Company or Branch User Permission gets the "not set up" page and **no** figures in any response.
2. A user with Leadership + one Branch permission sees only that branch; the response holds no other branch's figures.
3. Company + Branch permission together behave as those branches (D7). Two or more Branch permissions in one company → the branch switcher: "All my branches" plus each branch, sorted by name (D7). Branches in every branch of the company → company scope. More than one company → D19.
3a. "All my branches" returns combined Today, Attendance, Leave, People and trend for exactly the linked branches, plus one table row per linked branch, sorted by name, and no other branch's figures.
3b. Small-group rules run across the leader's own set (§7 rule 5a); a branch not shared in their table is not shared when chosen alone, and nor are its departments.
3c. "Company x%" for several branches appears only when company minus the set **and** company minus the branch on screen both reach the minimum (§7 rule 5b).
3d. The last choice is saved per user and shown on Home; first time, and when the saved branch is no longer linked, Home shows All my branches.
4. A user without the Leadership role sees no menu entry and no Home card; the endpoints refuse them.
5. Every sensitive figure (list in §7 rule 3) for a group below the minimum is **absent from the response**, not just hidden in the page. Group size = distinct people inside that figure for its period (§7 rule 1), not today's headcount.
5a. Wording: cells say "Not shared"; blocks, banners and the sheet use "Not shared: too few people in this group for a fair picture" (or the D17 variant, once chosen). No screen says "Hidden" or "Fewer than 5 people" on a cell.
6. Subtraction rule (§7 rule 2) on every set: branches in a company, departments in a branch.
7. Inheritance (§7 rule 4): opening a branch hidden in the company table returns headcount and joiners only, and hides all its departments.
8. Comparison rule (§7 rule 5).
9. Headcount and joiners are returned for every group at any size.
10. No leave type, leave reason, name, employee ID or pay appears in any leader response or log line.
11. Every card shows "Data up to <date>" and the "as of" time; both match the server.
12. A doubtful day (D5 threshold) is excluded from attendance, late and short-day figures for **both** HR Analytics and the leader view, and both show the warning with the dates.
13. "Show the figure with those days" returns the raw figure, labelled "likely wrong".
14. When leave needs review (D6), every leave figure on the page — leave used, on leave today, requests waiting, table columns, total row and Today — says "Needs review", never 0 or 0%, with a "Why does this need review?" sheet.
15. When leavers need review (D18), Left and Attrition say "Needs review" everywhere they appear, including the table, total row and Home; a branch with a true zero (data not needing review) says "0".
15a. Every "Needs review" and doubtful-day case appears as an item on HR's Data to review page, scoped like HR analytics; the item goes when the rule stops firing or HR confirms it; each confirmation is stored with who and when.
15b. A tenant with no attendance at all shows "No figures yet", not "Needs review".
16. Change lines compare with the same days of last month (D13).
17. Tables are sorted by name; no sort by result; no export.
18. Settings: only System Manager can save; HR Manager gets read-only; any other role gets nothing. Server rejects values outside 3–10 and an empty reason.
19. Every saved change writes a history row (who, when, before, after, reason) that no role can edit and that System Manager and HR Manager cannot delete (only Administrator can, OPS-23); the history is visible to System Manager and HR Manager, without giving HR Manager read access to all `Version` records.
20. After a change, the next leader page load applies the new minimum (cache cleared, OPS-4).
21. The "Who has leader access" list flags "no company or branch", and describes several-branch leaders as "Branch overview for N branches".
22. The employee line on My attendance and My leave states the current minimum and names the employee's branch.
23. One failing card does not blank the others; retry reloads only that card; no raw server error text. Each card leaves its skeleton on its own as its data arrives; Home's leader card uses its own call and makes no call for users without the Leadership role (§17).
24. Phone: no sideways scroll at 360 px; every control ≥ 44 px; no text under 12 px; skeleton within 300 ms.
25. The branch head has no Organisation tab or any greyed menu item (LV11).

---

---

## 17 · Page speed — how the leader pages load (round 2, user decision 15 Sep 2026)

**Rule: the leadership view loads per card.** The frame and skeletons appear first; each
card fills in on its own. Home's leader card has its own separate, cheap call.

| Part | Behaviour the design needs | Budget (nfr-budget §2) | Notes from DevOps (07 §2) |
|---|---|---|---|
| Home leader card (WOW + Today) | One small call of its own, **only for users with the Leadership role** (decided from roles already on the page). Skeleton, then the card | Skeleton ≤ 300 ms | OPS-15: under 5 KB, cached 3 min |
| Overview frame | Title, switcher, subtitle and "Data up to" line appear with skeletons for every card | Skeleton ≤ 300 ms; page ≤ 3 s | — |
| Each card (Today, Attendance, Leave, People, trend, last 7 days, table) | Fills in independently; its own error and "Try again"; a slow trend never holds up the cards | ≤ 500 ms per call | OPS-16 suggests grouping into 2 calls (summary, trend) with a per-section error field, to save web request slots. **The design works either way**: grouped or not, each card must show its own state. How many calls is for the engineer and DevOps |
| Switching scope | Only the figures reload, with the same per-card skeletons; the switcher and title change at once | Same | Cache keys include the scope (OPS-2, OPS-17) |
| Leader script | Sent only to Leadership users | ~30 KB before compression (OPS-24) | Do not ship the prototype's code |

**Not in this slice:** DevOps is planning a portal-wide speed fix separately —
compression, caching the page shell, and later loading portal sections on demand in slice
009. The page the Home card sits on is 970 KB today (07 §2, measured file size), so the
Home card can still feel slow on 3G until that fix lands. This design does not depend on
it, but the brief's "two minutes on a phone" test (S4) should be run after it.

---

## Open questions

| # | Question | Owner | Blocks |
|---|---|---|---|
| Q1 | D17, D18, D19 (new). D1–D16 are settled | Surbhi (D18 with the engineer) | Design check |
| Q1b | D15's department-across-branches tab: can a department total across branches, minus the per-branch departments a company head sees on drill-down, reveal a group that is not shared? | Security (01c) | D15 build |
| Q1c | The brief's kill criterion says "more than half the cards say 'not recorded'". It should now read "Needs review" | PM | Wording only |
| Q2 | Is the collusion and month-to-month trend risk (§7 rule 8) acceptable as residual risk? | Security (01c), then Surbhi | 01c PRIV requirements |
| Q3 | Does the tenant brand colour change the dark hero's accent text (`--hero-accent`)? Today `brand_color.html` leaves it purple | Engineer | Visual polish only |
| Q4 | Plan gating (brief P6) — hide the menu entry and Home card when `analytics` is off? | Founder | Gating |
| Q5 | Hindi and Punjabi copy review | Native reviewer; slice 009 Wave 5 | Any language work shipping |

## Assumptions

- `[ASSUMPTION]` The Step 0 attendance formula counts half days as half, work from home as present, and does not count leave, holidays or weekly offs as expected days. The explanation text must be rewritten if Step 0 decides otherwise.
- `[ASSUMPTION]` Late arrivals include HR's grace time, as today's late-rule code suggests. Not re-read in this run.
- `[ASSUMPTION]` The leave year runs 1 Apr to 31 Mar. Real tenants set their own; the card shows the tenant's dates.
- `[ASSUMPTION]` Branch heads can manage the people in a small branch through My team. If not, the pointer in the tiny-branch message goes.
- `[ASSUMPTION]` Department lists above ~60 rows need paging at 50.
- `[ASSUMPTION]` A "data up to" date more than 3 days behind deserves an amber chip.
- `[ASSUMPTION]` The amber chip colours meet 4.5:1 in both themes. Not measured with a checker.
- `[ASSUMPTION]` WCAG 2.2 AA is still the current target; taken from `nfr-budget.md` §7, not re-checked today.
- `[ASSUMPTION]` All benchmark claims are carried from `01a` (read 14 Sep 2026), not re-verified.

## Handoff note — round 2

To you (Surbhi): please click v2 and rule on **D17** (the prototype has a switch for it),
**D18** and **D19**. Everything else from round 1 is marked as you decided. I followed
your wording everywhere, including the one case where I think it says something untrue
(D17); I did not change it quietly.

To the security engineer (01c): three additions to §7 — rule 1 now counts the people inside
each figure (OPS-19); rules 5a–5c cover leaders of several branches, including the new
"company minus their set" comparison check; and Q1b for the D15 department tab. Rule 8's
pooling risk now also covers an area manager plus a branch head.

To the business analyst: §16 items 3–3d, 5–5a, 14–15b, 19, 21 and 23 are new or changed.
§8.8 (switcher), §8.4 (Needs review) and §8.10 (Data to review) hold the exact words.

To DevOps and the engineer: §17 states the loading behaviour. The switcher adds a scope
to every cache key and one saved user default per leader. Data to review needs a stored
record per item with HR's confirmation (it can share the doubtful-day store from OPS-21).

## Handoff note — round 1

To the security engineer (01c) first: please write §7 as PRIV requirements, and rule on
the two new rules I added — **inheritance on drill-down** and **hiding the company
comparison** — plus D3 and the residual risk in rule 8. Without inheritance, tapping a
branch undoes the subtraction rule. To the business analyst: §16 is the list; §8 and §9
hold the exact words, and the prototype is the reference for layout. To DevOps (07 §2):
the page loads Today first and each card separately, so plan for one call per card, and
confirm D11 (a today-only check-in count). To the engineer: the explanation sheets promise
"HR Analytics uses exactly this calculation" — that sentence is only true once Step 0 ships,
so ship them together. I disagree with the brief in four small places (D2, D4, D13 and the
comparison rule). They are design-level, flagged with both options, and do not change the
slice's scope, so I did not stop; please rule on them at the design check.

---

## Design check decision (2026-09-15)

**Design agreed with prototype v2** (https://claude.ai/artifact/F2TamgEUgiUfudiXcLsgKJ, version 2).
The user accepted every recommendation:

- D1–D16 as recorded above, with the round-1 changes: wording "Not shared: too few people in this
  group for a fair picture" (short form "Not shared" in table cells); "Needs review" instead of
  "Not recorded"; D7 is a branch switcher with "All my branches" showing combined totals and a
  by-branch comparison.
- **D17** — for a group that reaches the minimum and is hidden only to protect a smaller one, banners
  and card boxes say "Not shared: it would let someone work out a smaller group's figures". Table
  cells stay "Not shared".
- **D18** — leavers and attrition show "Needs review" when anyone is marked Left with no leaving date,
  or nobody in the company has a leaving date in the last 12 months.
- **D19** — a leader linked to more than one company sees the company on their own employee record,
  plus "Viewing more than one company is planned for later". No combined totals.
- The database indexes DevOps recommended are approved.
