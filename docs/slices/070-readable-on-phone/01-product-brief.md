---
slice: 070-readable-on-phone (YouTrack ALV-217)
artifact: 01-product-brief.md
author: hrms-product-manager
date: 2026-10-24
status: recommendation. Surbhi decides: build, change or drop.
inputs: [01a-ux-opportunities.md, 07-devops-inputs.md §1, design-benchmark/2026-10-24-ux-priorities.md (candidate A), 2026-10-24-ux-benchmark.md, product-context.md §2, no-over-engineering.md]
---

# 070 · Readable and honest on a cheap phone

**Bad news first: at DTC, almost no worker will feel this yet.** Only 10 of 445 active staff
have portal logins (24 Oct); staff logins wait on ALV-117. Until then the users are DTC's HR
and managers, and staff at other tenants. The measures are built around that.
**Settled:** candidate A, rank 1 of 5 (24 Oct); existing portal only; colours stay per tenant.

## 1 · Job to be done
*"When I open the app on my phone between jobs, I want to read it and press the right button
first time — and if the signal drops, I want it to tell me, not just spin — so I don't have to
go and ask HR."* — a helper or driver on a ₹8,000 Android phone (**Frontline employee**).
**HR Manager:** fewer "app is stuck" / "why holiday?" questions; nothing taken away.
**CXO / owner:** nothing new; links opened from WhatsApp are readable. No harm.

## 2 · Current pain (measured on our own screens, ALV-213 build — Confirmed)
- Labels 11 px, fields 13 px (iPhones zoom in), "+ Apply Leave" 25 px tall. Our rule: 44 / 16 / 12.
- Weekly offs say "Holiday" (Thursdays in Oct). `time_api.py` already sends `weekly_off`; the screen ignores it.
- "Loading…" never ends when a call fails. Dates show three ways: `mm/dd/yyyy`, `2026-08-03`, "24 Oct 2026".

## 3 · Competitive headline (from the 24 Oct benchmark; store screenshots, seen)
| Area | Keka · Zoho People · greytHR · factoHR · Connecteam | Frappe HR standard | Us after 070 |
|---|---|---|---|
| Tap size | Small icon tile grids common; factoHR and Connecteam use one big worded punch button | Desk UI, not built for phones | Every control ≥ 44 px, worded |
| Weekly off | None seen mislabelling it | Holiday list has a weekly-off flag | "Weekly off" chip, apart from "Diwali" |
| Bad network | Keka, factoHR: offline *punch* in native apps (read) | Spinner | 10 s, plain words, Try again, form kept |

**We will NOT copy:** icon tile grids (small, need reading skill); web fonts, stock images or
illustrations (slow on 3G); an offline form queue (UXB-12, ranked not needed); automatic
retry loops (load on a sick server — DevOps OPS-4). Our bar is our own NFR rule, not parity.

## 4 · Kano class and demand
**Must-be (proxy; the ALV-13 survey is late November).** Evidence: **seen** — the measurements
above, "Holiday" on weekly offs three times, a stuck Leave page. **Evidence required:** no
customer complaint is recorded. Would change it: users who read and tap fine today.

## 5 · The thin slice
**Rung: new code** (portal CSS tokens, `portal.js`). Nothing cheaper: staff don't use desk forms; no setting exists.
1. **Phone floors:** raise the size tokens on phone widths, not screen by screen — every
   control ≥ 44 px, fields 16 px, no text under 12 px. No sideways scroll may return.
2. **"Weekly off" label** where the day is a weekly off; named holidays keep their name. It
   only shows where a tenant has weekly offs set up, so it cannot mislead DTC (ALV-92 is
   DTC's own policy choice, ruled 23 Sep; we advise only).
3. **Every wait ends by 10 s:** network or server failure shows a plain sentence and one
   **Try again** tap. The form keeps what was typed. **Validation messages from the server
   (e.g. "dates overlap") still show as today** — only failures are reworded.
4. **One date format**, "24 Oct 2026", in tables and as a label beside each date field.
5. **Clean-ups from candidate A:** page name in desktop top bar (G1), right-edge shadow gone
   (G8), past holiday hidden (H5), WORK column fits at 390 px (N6), one greeting and no empty
   Activity card (N7). *First to cut if the engineer sizes the slice above S–M.*

**Out of scope:** WhatsApp share (UXB-13) · Hindi (slice E) · offline draft forms (UXB-12) ·
new quick actions or bottom-bar items · desktop menu words (G2) · Team View fixes TV3/TV4
(slice D) · fixing DTC's holiday list (ALV-92, DTC's call) · any new font, image, page, menu,
setting or colour change · nginx or route changes.

## 6 · Persona enhancements (from 01a)
| Persona | Enhancement | Job | In 070? | Why |
|---|---|---|---|---|
| Frontline employee | Floors, Weekly off, 10 s end, one date format | Read and tap first time | **Yes** | The point of the slice |
| Supervisor / line manager | Floors on Team View and approvals | Approve on the floor | Yes | Tokens cover it |
| Supervisor | Raw server text swept everywhere | — | No | N5 was local-only; item 3 covers real failures |
| HR Manager | Page name in top bar; HR holidays card ends its wait | Know the page; no frozen card | Yes | Cheap, approved in A |
| CXO / owner | Share summary to WhatsApp | — | **No** | UXB-13 blocked on a privacy check |

## 7 · The WOW
A driver applies for leave in the yard; the signal drops as he taps **Send**. Within 10 s, under
the still-filled form: *"We could not reach the office. Nothing was sent."* and a big
**[Try again]**. One bar returns, he taps, it goes through. He never retyped.

## 8 · Run-side (DevOps §1, Confirmed): nothing new to run, zero cost; `?v=asset_version` refreshes phones.

## 9 · Success measures
| Measure | Kind | Baseline | Target | How measured |
|---|---|---|---|---|
| Controls < 44 px, fields < 16 px, text < 12 px at 390 px | Quality, leading | In `report3.json` (e.g. 25 px button, 13 px fields, 11 px labels) | 0 / 0 / 0 | Re-run the UX phone script after the dev deploy |
| Screens still on "Loading…" after 10 s with the network cut | Quality, leading | Never ends (seen) | 0; typed text kept on every form | Test engineer cuts network on each page |
| First-time success: 5 real users each check in history, apply leave, read a payslip on their own phone | Adoption/efficiency | **Unknown — measure first, before build** | All 3 tasks with no help and no zoom | 15-min observation. Today: DTC HR/managers and staff at other tenants; DTC workers after ALV-117 |
| "App stuck" / "why holiday" questions to HR per month | Business, lagging | **Evidence required** — ask DTC and one other tenant's HR | Down by half | HR tally, one month before and after |

## 10 · Thriving lens and regulatory read
- **Engagement:** the worker knows whether something went through. **Collaboration:** no effect.
  **Inclusiveness:** the main gain — cheap phones, low vision, low literacy; contract staff once they have logins.
  **Transparency:** nothing new shown to anyone.
- **Regulatory:** none. No new data, visibility or automated decision. Front-page test: yes.

## 11 · Risks
- **Raising tokens globally may push something into sideways scroll** (ALV-213's win). Check every 390 px screen.
- Labels may clip at 12 px+ in tight cards. A 10 s cut-off may fire on a slow call that did
  succeed — Try again must not create a second leave application.

## Open questions
| Question | Owner | Blocks | Class |
|---|---|---|---|
| Which five people do we observe, given only 10 DTC logins? I suggest 2 DTC HR/managers + 3 staff from another tenant | Surbhi | Measure 3 baseline | Must know |
| Is a 10 s cut-off right for leave submit, or should submit wait longer than a page load? I assume 10 s for loads, 20 s for submits | Surbhi, with UX | Item 3 copy and timing | Should know |
| Will DTC and one other HR keep a one-month tally of these questions? | Surbhi | Measure 4 | Nice to know |

## Assumptions
- `[ASSUMPTION]` ALV-112 is live, so CSS/JS reaches phones (DevOps read the script, did not run it).
  Raising tokens on phone widths fixes most controls; a few need per-control CSS.
- `[ASSUMPTION]` Sizes are the UX designer's (S each, S–M together), not an engineer's. The Kano class is a proxy.

## Kill criteria
- The engineer sizes it above M, or bigger text cannot fit without a per-screen redesign — stop, ship only items 2–4.
- The 5-user observation shows people already read and tap first time — drop item 1, keep 2–4.

**Handoff note (UX):** design the failure state and the Weekly off chip first; floors are
mostly tokens. Keep "Why?" and the inline "What went wrong?" exactly as they are.
**Subtract pass:** removed a raw-error sweep (N5 is local-only), an office-employee row, a
long run-side section, and a "worker satisfaction" measure (no way to collect it before ALV-13).

## Decisions — Surbhi, 24 Oct 2026

- **Brief: build it.**
- **Who we watch:** DTC and Grace staff, once their portal logins are created ("soon" — both tenants are getting logins for all staff). The ALV-117 feedback-permission fix is already live on production, so the logins do not open performance feedback.
- **Time before "Try again":** **15 seconds** for every call, including sending a leave request (replaces the 10 s / 20 s proposal).
