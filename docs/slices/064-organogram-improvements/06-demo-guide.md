# 064 · Try the new Positions page (local demo)

**This is a throwaway local site with made-up people, shaped like DTC.** It is not DTC, dev or
production. The passwords below work only on this one demo site.

## How to open it

| From | Address |
|---|---|
| Your PC | http://localhost:8065/alvoraa-login |
| Over Tailscale (phone or another device) | http://100.99.86.42:8065/alvoraa-login |

Sign in; the portal opens. The page is **Positions** in the menu.

| Who | Login | Password | What they are |
|---|---|---|---|
| Ritika | hr@pos064.test | Hr@064demo | HR Manager. Positions Read and Write, as DTC will have after release |
| Vikas | owner@pos064.test | Owner@064demo | The Owner. Role "Org Structure Editor", no HR role. Positions Read, Write and Delete given on Frappe's permission screen, as at DTC |
| Dinesh | head@pos064.test | Head@064demo | Store head, Delhi. Positions Read only, limited to the Delhi branch |
| An RSO | employee@pos064.test | Emp@064demo | Employee. Cannot open Positions |

Use a private browser window for each person, or sign out in between. The shape: 92 seats,
about 446 active people, the Owner with 22 seats under it, a CFO with 18 people who name him as
manager on their records, a 36-person Back Office pool, 82 people in no seat (19 with no manager),
seven branches (two are look-alike Pitampura records) and a small department tree.

## Try these

**1 · The opening view.** As **Ritika**, on a 1440-wide window. Positions opens on **Reporting
lines**: the Owner, its 22 seats below, and **No reporting manager** pinned in the top-right corner
of the chart, with no line. The tiles answer: 92 seats, 3 to fill, 1 leaving, 82 in no seat,
19 no manager.

**2 · A big family is one group.** The Owner's 22 seats sit in one labelled group, "22 seats
report to Owner…", with **Nobody under them · 17** first and **Lead a team · 5** last. Press
**Show the 21 below** under *Manager - Management - Delhi*: its family opens below the whole
group under an **Under …** strip, joined by its own line. Open another lead: the first folds.

**3 · By branch and By department.** Switch **View**. Branches (or departments) sit in rows that
fit the screen. Select one: it opens below the row under its own strip; select another and the
first folds. Inside, open a team lead the same way. **Open every level** opens the first of each.
The *DTC - PITAMPURA* box says "Second branch record for DTC Pitampura".

**4 · Find.** Type **RSO** (seats), then part of a person's name, e.g. **Vaneet**. Choosing a
result opens the path to it and outlines it, with "Showing … Clear".

**5 · People lists, HR only.** As **Ritika**, press the **82 in no seat** tile (grouped by branch,
with the matching seat) and the **No reporting manager** box ("Set manager" opens the employee
record). Sign in as **Vikas** or **Dinesh**: no such tiles, no box, and Find does not find people
in no seat. The CFO's box shows "18 report here on their records" and the Back Office pool "Holds
people of 3 managers" - for Ritika only.

**6 · The crash that is fixed.** Open *Manager - Delhi* (step 2), switch to **By branch**, press
**Open every level**, switch back. The approved prototype failed here; the page does not.

**7 · A hire placed in their seat.** *Meera Placed* was hired through Job Opening HR-OPN-2026-0001
three days ago: she already sits in *Cashier - Sales - Noida* with "New hire placed", and that
opening is **Closed**. Now do one yourself as **Ritika** in the desk
(http://localhost:8065/app/employee/new): first name, gender, date of birth, company *DTC Demo*,
date of joining (today or later), **Job Applicant = Arjun Applicant**, Save. The message says he
is now in *Greeter - Sales - Ambala*, and Job Opening HR-OPN-2026-0002 closes (its one place is
filled). Positions shows him from his joining date.

**8 · Delete a seat.** As **Vikas**, open *Mali - Back Office - Chandigarh Sector 34* → Change this
seat → Delete: refused, with the reason in the box (somebody is in it). Then open *Spare seat (made
by mistake)* under Delhi → Delete: it goes.

**9 · The phone.** On a phone (Tailscale address) or a window under 640 px: an outline, one level
at a time - tap the Owner, then a lead; "Up one level" comes back; "No reporting manager" is a
dashed row.

**10 · Window width.** Make the window narrower: the groups go from 5 boxes per row to 4 to 3
(about 1440, 1280 and 1024-wide windows), and nothing scrolls sideways.

**And:** as the **employee**, there is no Positions in the menu; going there anyway says the page
is open only to the roles the organisation has chosen.

## What the demo shows only partly

- **Seat names are long** ("RSO - Sales - Noida"), because seats are named by their title and that
  is DTC's own naming. It is how DTC's chart will read too.
- **Names are invented**, and the counts are DTC's shape, not DTC's records.
- **The hire in step 7** uses the desk Employee form directly. At DTC it would usually start from a
  Job Offer's "Create Employee"; the hook is the same either way. Emails are switched off.
- **Delete** is given to the Owner role here so step 8 can be shown; at DTC that is a setting
  (Frappe's Delete right on Alvoraa Position), not decided yet.
- **"Plan a replacement"** and **"Print this view"** are not in 064 (slice 065, and later).
- **Hindi** is not switched on.
- The site runs on a development server: the first page load after a while can take a few
  seconds.
