# ALV-213 — Employee portal uses the whole screen: impact analysis

Approved by Surbhi on 23 Oct 2026: "let's fix the design and leave the colors as
dynamic as they currently are." Prototype: portal-shell-prototype.html (artifact
HPHwuCocpyxhanXHARUjSN). Fixes 1-6 only; #7 (gather breakpoints) is out.

## Rung of the ladder

New code, the smallest kind: one context line, a few CSS rules, one small menu in the
phone header, and a card list next to the leave table. Nothing cheaper exists: Frappe
already offers `full_width` (rung 1, used for fix 1); the rest is portal markup that only
this app owns.

## What changes, and who else uses it

| File | Change | Other users |
|---|---|---|
| `www/hrms_employee.py` | `context.full_width = 1` | Only `/hrms-employee`. Frappe's `templates/web.html` drops the `container` class (and its padding) when set. |
| `public/css/ess/frame.css`, `panels.css` | Phone rules (fixes 2-6) | Loaded only by `www/hrms-employee.html`. `-next`, field-checkin, login and admin load other files, so they cannot change. |
| `templates/includes/ess/frame.html` | Phone avatar becomes a button with My Account / Log out | Included only by `hrms-employee.html`. |
| `templates/includes/ess/parts/attendance.html` + `portal.js renderLeaveApps` | A card list beside the table, shown under 640 px | `renderLeaveApps` has one caller (`loadLeaves`). DTC tenants (slice 063) replace the whole box with their own table + list and are untouched. |

Callers checked: `renderLeaveApps` (1, `loadLeaves`), `#mob-avatar` (portal.js 3980-4011
writes its initials; still works on a button). Tests reading these files:
`test_nav_consolidation_060` needs `id="leave-apps-tbody"` (kept),
`scripts/check_portal_trays.js` lists `nav.navbar` as frame (still there on desktop).

## What the Frappe navbar carries on a phone

Brand "Home" (link to `/`), and the avatar menu: My Account (`/me`), Log out
(`/logout`), Switch To Desk (desk users only). The new phone menu gives My Account and
Log out, as the prototype shows. Switch To Desk is already in the portal's own sidebar
(`#nav-switch-link`, decided by the server), which the phone opens with the menu button.

## Personas

CXO, HR Manager and Employee see the same frame; all three get the wider page and the
phone fixes. No data, permission or query changes.

## Non-functional verdicts

| Dimension | Verdict |
|---|---|
| Performance | Neutral. No new request; a few CSS rules; the leave list is drawn from rows already fetched. |
| Security | Neutral. No endpoint, no permission change. Log out uses Frappe's own `/logout`. |
| Reliability | Improves. Bottom padding works again (the broken `calc()` was ignored). |
| Scalability | Neutral. |
| Maintainability | Neutral. Rules go into the existing 768 / 640 px blocks; no new breakpoints. |
| Data integrity | Neutral. Display only. |
| Compliance / privacy | Neutral. The card list shows the same fields as the table, to the same person. |

## Parallel-work check

Fetched origin/dev at 30ac5192; nothing new came in. Hot files touched:
`portal.js` (one function body), `frame.html` (one element). Edits stay inside those
spots; no reformatting.

## Strategy

Fixes as approved. Brand colours and `brand_color.html` are not touched.
