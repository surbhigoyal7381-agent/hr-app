---
slice: 013-mobile-app
artifact: 00-sequencing-recommendation
author: hrms-product-manager
date: 2026-09-17
status: draft — recommendation only; Surbhi decides
inputs: [009/00-assessment-and-plan.md, 003/00-current-state-assessment.md, 013/01a-ux-opportunities.md, 013/07-devops-inputs.md §1, 008/10-native-app-background-geofence.md]
---

# Redesign first, or app first?

## 1. Recommendation

**Neither waits for the other in full: start the app now with the Attendance tab only, and add the My HR tab after slice 009 Wave 1 (the new portal frame) is on dev.**

- **The full redesign is 8–11 weeks of build.** Waiting for all of it holds back the part of the app that is already built and demoed (photo check-in).
- **The slowest app work is not code.** D-U-N-S number, store accounts and the wildcard certificate take weeks. They should start this week either way.
- **The Attendance tab does not touch the portal.** It uses `field-checkin.html` and `field_checkin.py`, not `hrms-employee.html`.
- **The My HR tab does need Wave 1.** Without it the app shows two bottom bars, a menu that does not work on a phone (M03), and an extra "Home" bar (M07). That looks like a broken website, and Apple's 4.2 review would see it.
- **Wave 1 is small (6–8 build days)** and fixes 7 of the 22 phone gaps. It is the only part of 009 the app needs.
- **No client is live, so nothing forces a rush.** We can build this in the right order.

## 2. What depends on what

| App part | Needs the redesign? | Why |
|---|---|---|
| Attendance tab, QR joining, "update the app" screen | No | Separate page and server file |
| D-U-N-S and store accounts, wildcard certificate, signing-key guard (OPS-6), build pipeline | No | Paperwork, DNS, CI. No portal files |
| Compression fix (OPS-26) | No | nginx only. Helps the browser portal today too |
| Moving inline JS/CSS out (OPS-31) | **Do it inside Wave 1**, step 2 (split into includes) | Both change the same file. Doing it twice means conflicts |
| My HR tab: hide the portal's own bars, send portal Check In to the Attendance tab | **Yes — Wave 1** | Both are frame changes in the hot file |
| Leave apply that works well on a phone (M12), pop-ups cut off (M02) | Waves 2–3, not Wave 1 | **Even after Wave 1, some phone tasks stay awkward** |

## 3. Suggested order (next ~6 weeks, two work lines)

| Weeks | Line A — owns `hrms-employee.html` | Line B — never opens `hrms-employee.html` |
|---|---|---|
| 1 | 010 and 012 push 1 to dev (on your word). 009 prototype fixes D1–D4, then your design check | You: apply for D-U-N-S, decide certificate. Engineer: signing-key guard, compression fix, 013 brief |
| 2–4 | 009 Wave 1 frame, with OPS-31 folded in. Wave 0b–0d server fixes alongside (server files only) | App shell (Android), Attendance tab bundled, QR joining, version check. Test APK through Firebase on the demo tenant |
| 5–6 | 012 push 2 once its text is ready — after the include split, in its own include file | My HR tab added: hide portal bars in the app, Check In hand-over, blocking a phone ends its My HR session. iPhone on TestFlight |

**If there is only one work line:** do Wave 1 first, then the app. Start the paperwork now anyway.

## 4. What we lose or risk

- **For about 4–5 weeks, app testers use Attendance only.** For leave and payslips they still open the portal in a browser.
- **If Wave 1 slips, My HR slips with it.** The design check and Wave 1 questions Q1–Q5 are still open.
- **Two work lines need discipline.** One slip into `hrms-employee.html` from line B causes clashes.
- **An Attendance-only app is a weaker case for Apple.** This is fine for now: iPhone is TestFlight only until step 2 anyway (DevOps §1).
- **The portal stays slow on phones** (18.4 s first visit on 3G) until compression is built.

## 5. Kano and value note — all proxy, no survey, no customer evidence

- **A phone-ready portal is Must-be (proxy).** Every employee, manager and HR person uses it daily. Broken phone screens cause anger and support calls. It decides whether a customer **stays**.
- **An app in the store is Performance, close to Must-be, for frontline-heavy buyers (proxy).** Keka, greytHR, Darwinbox and HROne all ship native apps (read, UX scan, 17 Sep 2026). It helps **win** the demo.
- **Photo check-in with a plain consent notice is our Attractive part (proxy).** It is built already.
- **My view:** to keep a first customer, the phone-ready portal matters more. An app that opens a broken portal is worse than no app. We have **no seen demand** for either. PP Jewellers is a demo tenant.

## 6. Decisions for you

| # | Decision | Blocks |
|---|---|---|
| 1 | Accept the split: Attendance first, My HR after Wave 1? | Order of 009 and 013 |
| 2 | One work line or two? | Whether weeks 2–4 run in parallel |
| 3 | Apply for D-U-N-S and open organisation store accounts now (OPS-4) | Any store release |
| 4 | Wildcard certificate, option A (OPS-9) | App testing on dev tenants |
| 5 | **How does a field worker with no email sign in to My HR?** (UX Q1) Your new "default Yes" setting assumes they can. Today they cannot | The My HR tab, not the Attendance tab |
| 6 | Date for the 009 design check, and answers to Wave 1 Q1–Q5 | Wave 1, and so My HR |

## Assumptions

- [ASSUMPTION] Wave 1 lands in about 3–4 calendar weeks, including the design check.
- [ASSUMPTION] Two engineer sessions can run under the parallel-work rules.
- [ASSUMPTION] Competitor app claims are vendor pages, read not seen.

## Kill criteria

- If the Android test build on a low-end phone cannot check in reliably, stop the app work. Put line B on Wave 0 fixes.

---

## User decisions (2026-09-17)

- **Field workers:** an organisation setting marks which roles are field workers, and a setting says whether field workers can sign in to the app (default **Yes**). **Photo check-in applies to field workers only.**
- **PP Jewellers is a demo tenant; no client is onboarded yet.**
- **Sign-in for field workers without email:** the **enrolment QR** signs them in to both tabs. HR issues it for one named employee; it works once. Blocking the phone ends both Attendance and My HR on it. Needs a security design before build.
- **QR lifetime:** Surbhi asked for **up to one week** instead of 24 hours (trade-off and recommendation in the reply of 2026-09-17; to confirm).
- **QR-signed-in users** should be able to use other employee features such as **expense claims**, subject to their role, their organisation's plan and permissions (to confirm in the brief).
- **Wave 1 of slice 009** answers recorded in `docs/slices/009-ess-portal-redesign/00-assessment-and-plan.md`.
- **Accepted (2026-09-17):** the split — Attendance tab first, My HR tab after slice 009 Wave 1 is on dev; **two work lines** (line A owns `hrms-employee.html`, line B never opens it); apply for D-U-N-S and company store accounts now (not needed for development); QR lifetime as an organisation setting, **default 7 days**, single use, HR sees who joined and can block.
- **Wildcard certificate:** Surbhi does the browser steps herself (Cloudflare account, copying DNS records, GoDaddy nameservers), with guidance. Server steps (plugin install, `setup_wildcard_cert.sh`, nginx switch) still need server access and the user's explicit go-ahead.
