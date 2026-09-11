# Employee Self Service on a phone: current state

Assessed 2026-09-11 on the local instance (`ppj.localhost`, build dev-3830ed3 plus local changes).
Assessment only. Nothing has been changed.

## The short answer

**The portal is not usable on a phone today.** Four tasks cannot be finished at all. Most other
screens work, but they are cramped and fiddly.

Most of the 22 layout gaps come from **five causes in the page frame**, not from each screen.
Fixing those five first should clear most of the list in one go.

Along the way the run also found **three server-call bugs** that affect desktop too.

## How it was tested

- Phone: iPhone 13 size (390 × 844), touch on, in Chromium's phone emulation.
- People, each seeing only their own menu:
  - Kamal Gupta — owner with the HR role, 17 screens.
  - Sonia Kumar — plain employee, 11 screens.
  - Gurpreet Dhillon — manager of 6 people, 12 screens.
- Inside the screens: every tab, 8 pop-ups, opening a day in My Attendance, searching the
  org chart, and tapping Check In.
- Each screen was measured for:
  - content cut off
  - the page growing wider than the phone
  - tap targets under 32px
  - text under 12px
  - fields that make an iPhone zoom in (text under 16px)
  - console and server errors
- Writes: one check-in, for Kamal, on the local copy. No forms were submitted.
- **Not tested:**
  - a real iPhone (Safari) or Android phone
  - landscape
  - dark mode
  - Policies (PP Jewellers has not bought it)
  - submitting forms

Screenshots and raw numbers: `C:/Surbhi-Git/hrlocal-data/mobile-audit/2026-09-11/`
(`kamal/`, `kamal-pass2/`, `persona-sonia-employee/`, `persona-gurpreet-manager/`).
Scripts: `C:/Surbhi-Git/hrlocal-data/mobile-audit/`.

## The five causes

| # | Cause | Where | What it breaks |
|---|---|---|---|
| R1 | The Frappe website bar ("Home" plus an empty button) sits on top of the app, fixed, above everything | Page extends `templates/web.html`; `hrms-employee.html:42` pins `nav.navbar` at z-index 1100 | An extra 52px bar on every screen; it covers buttons (Calibration Sign Off cannot be tapped) |
| R2 | The desktop "collapsed sidebar" style still applies on a phone | `body.sb-collapsed .main-content{margin-left:56px}` (line 68) outranks the phone rule `.main-content{margin-left:0}` (line 626); the class is added whenever the sidebar is not pinned (line 17056) | Content squeezed; menu opens as a strip of unlabelled icons |
| R3 | Two layers of side padding stack up | `main.container` from `web.html` adds 24px each side, on top of the 16px phone padding | With R2, a 96px blank gap on the left; content gets 254 of 390px |
| R4 | A few rows neither wrap nor scroll, so the whole page grows wider than the phone | Goals tab bar (710px); Finances tab bar (`flex-shrink:0`, line 649); Attendance Insights Organisation table (684px) | Pages 461–807px wide; pop-ups centre on that wider page and open cut off; later tabs are off screen |
| R5 | Controls sized for a mouse | Small buttons 24–26px tall; field text under 16px; labels at 11px (`--fs-xs`) | Hard to tap; iPhone zooms in on every field |

## Gap register

Severity:
- **Blocks** — the task cannot be done on a phone.
- **Hard** — it can be done, but it is painful.
- **Polish** — it looks wrong.

| ID | Severity | Screen | Gap | Cause | Evidence |
|---|---|---|---|---|---|
| M01 | Blocks | Performance › Calibration | Sign Off cannot be tapped: the top bar sits over it. Opened by script, the sign-off panel appears off screen and leaves a blank page. | R1, R4 | `kamal-pass2/06`, `21` |
| M02 | Blocks | Performance, My Finances | Four pop-ups open cut off on the right: Create Goal, New KPI, New Review Cycle, New Expense Claim. The close button and the right side of every field are off screen. | R4 | `kamal-pass2/17`, `18`, `19`, `20` |
| M03 | Blocks | Menu (all people) | The menu opens as a 56px strip of icons with no labels. The last items (Checkin Log) sit below the screen and the strip does not scroll. Tenant Admin has zero size. | R2 | `probe-menu-open.png` |
| M04 | Blocks | My Performance Review | Step labels run into each other ("EMPLOYEEMANAGER"), step 5 is cut off, and the desktop two-column layout stays, so the right column shows two letters. | R2, R3, no phone layout | `kamal/09` |
| M05 | Hard | My Attendance › open a day | The opened day is cut off on the right: Expected hours, the Out punch, the reason hint and the status column. | Table not in a scroll box; R2, R3 | `persona-sonia-employee/13` |
| M06 | Hard | Performance, My Finances | Tabs after the third are off screen (Reviews, Team, HR Setup, Calibration, Distribution; Leave Encashment), with no sign that more exist. | R4 | `kamal-pass2/01`, `08` |
| M07 | Hard | Every screen | An extra bar reading "Home" on every screen, with an empty button at the right. It takes 52px and its title never changes. | R1 | `kamal-pass2/08` |
| M08 | Hard | Every screen | Content uses 254 of 390px. Long titles break one word per line (Objectives tree). | R2, R3 | `kamal-pass2/02` |
| M09 | Hard | Home | The Check In / Check Out button pokes 13px out of its card. After a tap the card slides sideways and cuts the name ("amal Gupta"). The check-in itself saved. | R2, R3; hero card has no room | `kamal-pass2/26`, `persona-sonia-employee/01` |
| M10 | Hard | Every screen | Tap targets too small. Buttons are 24–26px tall, month arrows 24×25, holiday arrows 17×21, org chart expand toggles 20px, team member names 19px, pop-up close 30×30. The HR Setup tab has 812 controls under 32px. The usual minimum is 44px. | R5 | metrics.json `tap_samples` |
| M11 | Hard | Every form | The iPhone zooms in when you tap a field, because field text is under 16px: Leave 5 fields, Expense 4, Create Goal 9, New KPI 9, Attendance Request 4, Shift Request 3, Advance 2, Login 2. | R5 | metrics.json `inputs_zoom_on_ios` |
| M12 | Hard | Apply for Leave pop-up | The pop-up is 667px tall. Submit sits below the fold (1 of 3 buttons visible), and you must scroll the dim background to reach it. | No phone height rule | `kamal-pass2/16` |
| M13 | Hard | Org Settings | The Company Values table is cut off; the description column is clipped mid-word. | Table not in a scroll box | `kamal/16` |
| M14 | Hard | Attendance Insights | The Organisation view table (684px) makes the page 780px wide. The weekday strip drops Sunday, and the view switcher wraps. | R4 | `kamal-pass2/15` |
| M15 | Hard | Team View | Tab labels wrap to two lines. The stat tiles stack one per row, so the team list starts far down. | No phone layout for tiles | `kamal-pass2/11` |
| M16 | Polish | Home, My Attendance | The end of the page cannot scroll clear of the bottom bar (3px on Home, 19px on My Attendance). | Bottom padding too small | probe |
| M17 | Polish | Login | The brand panel shows only a copyright line on a black block. The show-password eye is 26×26, and "Forgot password?" is 15px tall. | Desktop two-panel login stacked | `kamal/00` |
| M18 | Polish | Every screen | Text under 12px: from 26 to 1,242 pieces of text per screen. | R5 | metrics.json `text_under_12px` |
| M19 | Polish | Every screen | A dark shadow strip along the right edge, cast by two closed side panels parked just off screen (`#gp-detail-panel`, `#emp-drawer`). | Closed panels keep their shadow | every screenshot |
| M20 | Polish | Bottom bar | The bottom bar has only Home, Attendance and Finances. Performance, My Attendance and the request screens are reachable only through the icon menu (M03). | Bottom bar content | `kamal-pass2/08` |
| M21 | Polish | My Attendance | Month arrows are 24px; the person picker text is cut; the stat tiles are ragged (1, 2, 1, 2 per row). | R5, grid | `kamal/04` |
| M22 | Polish | Performance › Overview, Reviews | The progress stepper cuts "4 Completed" by 30px. The team review cycle picker is cut by 64px. | Fixed-width rows | metrics.json `clipped_inside_page` |

## Bugs found on the way (not phone-only)

| ID | Where | What happens | Cause |
|---|---|---|---|
| F1 | Team View › Team Attendance (Kamal, Gurpreet) | Server error 500 | `hr_api.py:1940` imports `get_pending_approvals` from `alvoraa_goals.api.goal_api`, but the function lives in `alvoraa_portal/goals_api.py:1124` |
| F2 | Performance › Create Goal | A call fails with 417 | `hrms-employee.html:9718` calls `pf("kra_api.get_my_kras")`, which builds a path that does not exist |
| F3 | Organisation chart (Sonia, Gurpreet) | 403 on every visit; the chart still loads | `hrms-employee.html:5140` asks for the HR-only `org_health` numbers for every user |
| F4 | Tests | F2 was not caught | `test_portal_call_paths` skips dotted names such as `kra_api.get_my_kras` |

## What already works on a phone

- Home, My Attendance, Org Settings, Team View and the three request screens do not scroll sideways.
- The Apply for Leave, Company Value and Review Principle pop-ups fit the width.
- Sign-in, check-in with location, the org chart search, and opening a day all work.
- The phone header (menu button, notifications, avatar) and the bottom bar do appear.

## Suggested next step

Fix the five causes first, as one small change to the page frame. Then re-run the same scripts,
and list what is left before touching individual screens. F1–F4 are separate small fixes.
A strategy will follow for approval before any code changes.
