---
slice: 070-readable-on-phone (YouTrack ALV-217)
artifact: 01a-ux-opportunities.md
author: hrms-ux-designer (opportunities scan)
date: 2026-10-24
status: evidence for the PM's brief. Surbhi decides scope.
inputs: [docs/product/design-benchmark/2026-10-24-ux-benchmark.md, 2026-10-24-ux-priorities.md (candidate A), product-context.md §2 (primary segment, 24 Oct), ux-learnings.md, portal.js, time_api.py]
---

# 070 · Readable and honest on a cheap phone — UX opportunities

**Existing portal only. Colours stay per tenant. No new page, menu item or setting.**
Evidence is reused from the 24 Oct benchmark (ALV-213 build, local bench, 390 × 844 and
1440 × 900). Screenshots and `report3.json` are in
`C:/Surbhi-Git/hrlocal-data/ux-review/2026-10-24-benchmark/ours/`. No new captures today.

## 1 · Current screens and measured problems (Fact unless marked)

| ID | Problem | Where, measured | Cause in code |
|---|---|---|---|
| N3 | **11 px text on every screen** ("Hey there,", "At Risk", tile labels, payslip dates) | all 390 captures | token `--fs-xs:11px` in `design_system.html` |
| N2 | **Form fields at 13 px** — iPhones zoom in; hard to read | apply leave (5 fields), attendance request (3) | `--fs-base:13px` |
| N1 / H6 | **Buttons 19–38 px tall**: "+ Apply Leave" 25 px, drawer items 38 px, month arrows 24 × 25, "Details →" 19 px, payslip tabs 34 px | `report3.json` | per-control CSS |
| MA2 | **Weekly offs say "Holiday"** (Thursdays 1, 8, 15, 22, 29 Oct) — seen a third time | attendance month 390 | `acRow()` prints "Holiday" for any holiday; `time_api.py` already sends `weekly_off` per day |
| G6 | **Mixed dates**: `mm/dd/yyyy` in forms, `2026-08-03` split over three lines in the late table | apply leave, attendance request, leave 390 | browser date inputs; raw ISO in one table. `fmtDate()` ("24 Oct 2026") already exists |
| N4 | **"Loading…" never ends** when a call fails — no words, no retry; what was typed is at risk | Leave page, leave-type list, HR holidays card | 44 "Loading" strings in `portal.js`, no timeout |
| N5 | Raw Frappe text in a pop-up ("DocType … not found") | local bench only | likely a bench migration gap `[ASSUMPTION — check on ppj.dev]` |
| G1 | Desktop top bar says "Home" on every page | att-record 1440 | |
| G8 | Grey shadow down the right edge, phone too | every capture | |
| H5 | Holiday card shows a past holiday ("2 Oct" on 24 Oct) | employee home 390 | |
| N6 | Day table's WORK column clipped at 390 px | att-record 390 | |
| N7 | Home greets twice, shows the date twice, empty "Activity" card takes 200 px | home 390 | |

**Keep:** no sideways scroll anywhere (ALV-213 held); the payslip's **Why?**; tap a day →
"What went wrong?" inline. Nothing in this slice may weaken these.

## 2 · What competitors do (benchmark rows, store images seen 24 Oct 2026)

| Problem | Competitors | Benchmark row |
|---|---|---|
| Size and tap targets | Indian products: icon tiles, often worded, but small. Connecteam: one huge round button; factoHR: big PUNCH IN / PUNCH OUT with words | §3 "Check in"; §6 rejects small tile grids |
| Weekly off / dates | No competitor seen mislabelling an off day; Keka shows shift "General 9:00–5:30" | §3 "Check in"; §5 MA2 |
| Failed network | Keka and factoHR: offline **punch** (read, not seen); nobody shows offline **forms** | §3 "Poor network"; UXB-12 ranked "not needed" |
| Raw errors | Not visible in store images — no evidence either way | — |

**Our bar is our own NFR §7 rule (44 px, 16 px, nothing under 12 px), not parity.**

## 3 · Ideas by persona — within this slice only

| Persona | Idea | Job it serves | Evidence | Size |
|---|---|---|---|---|
| **Frontline worker** (wins any trade-off, product-context §2) | Phone floors: every control ≥ 44 px, fields 16 px, no text under 12 px (raise the tokens on phone widths, not per screen) | Read and tap first time on a ₹8,000 phone | N1–N3 | S |
| Frontline worker | "Weekly off" chip, distinct from a named holiday ("Diwali") | Trust the month view; stop asking HR "why holiday?" | MA2, `weekly_off` already sent | S |
| Frontline worker | Every wait ends by 10 s: *"We could not reach the office. Nothing was sent. [Try again]"*; the form keeps what was typed | Never stare at a dead screen; never retype | N4; nfr §2 | S |
| Frontline worker | One date format, "24 Oct 2026", in tables and as the label beside each date field | No `mm/dd` vs `dd/mm` mistakes on leave dates | G6 | S |
| **Supervisor** | Same floors on Team View and approvals; raw server text replaced by a plain sentence plus a short code to show HR | Approve on the floor between tasks | N1, N5 | S |
| **One-person HR** (also does accounts) | Page name in the desktop top bar (G1); HR holidays card ends its wait with Try again | Knows which page they are on across tabs; no frozen card at month-end | G1, N4 | S |
| **Owner** | Nothing new. Benefits only from readable text and honest errors when he opens a link from WhatsApp | — | — | — |
| All | Clean-ups: past holiday hidden (H5), right-edge shadow gone (G8), WORK column fits (N6), one greeting, empty Activity card hidden (N7) | Less to scroll before the one task | H5 G8 N6 N7 | S |

## 4 · Weekly off and ALV-92 — bundle?

**Fact:** ALV-92 (DTC's holiday list has no weekly off, so staff are marked absent on rest
days) was **Open** in the 1 Oct Kano review (Gate 0 #3). No commit on any branch names it.
**I could not check YouTrack.**
**Recommendation:** do **not** merge ALV-92's fix into this slice — it is a data and
holiday-resolution fix with its own owner (ALV-157/158, KI-4). But **release the label
change together with, or after, ALV-92**. If the label ships first, DTC staff would still
see "Absent" on rest days, and the new word would sit on the wrong data.
**Question for the PM:** is ALV-92 live on dev today? If yes, the label ships with 070.

## 5 · Not in this slice

Offline draft forms beyond "keep what was typed" (UXB-12); Hindi (separate slice); new
quick actions or bottom-bar items (H6 beyond size, PH2); desktop menu words (G2);
TV3/TV4 (slice D).

**Subtract pass:** removed a proposed "slow network" banner and a skeleton redesign — the
10 s end state meets the need. Kept the clean-ups only because they were bundled in candidate A.
