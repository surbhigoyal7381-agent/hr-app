---
slice: 078-positions-faces
artifact: 07-devops-inputs
author: hrms-devops-engineer
date: 2026-10-31
status: draft
inputs: [the idea as given, docs/slices/064-organogram-improvements/*, docs/slices/070-readable-on-phone/07-devops-inputs.md, docs/product/design-benchmark/2026-10-24-ux-priorities.md, .claude/context/nfr-budget.md, deploy/nginx.conf, deploy/compose/docker-compose.app.yml, .github/workflows/deploy.yml]
---

# DevOps inputs — 078 Positions faces and mini profile

Advice only. Every row ends in a **Decision** column that is yours, left blank.

Everything below was read or measured in this worktree at `d3afcaa5` or on the local
bench (`hrlocal-bench`, image `dev-3830ed3`, site `ppj.localhost`) on **31 October
2026**. Nothing was run on dev or production. Nothing was changed anywhere — all reads
and one read-only `bench execute` of an existing endpoint.

---

## §1 Brief — 31 October 2026

### Answer first

**Bad news first, three things.**

1. **The Positions hierarchy is not loaded a level at a time. It arrives in one
   payload.** **Measured:** `register.position_table` returns **120 seats and 403
   people in a single call — 141,816 bytes raw, 10,717 bytes gzipped** (local bench,
   31 Oct). The hierarchy view is drawn from those same rows client-side
   (`portal.js:2667`). So "faces on the hierarchy" means **about 400 photographs in one
   page, not twenty**.

2. **Every one of those photographs would be fetched by a Python worker, not by
   nginx.** Employee photos upload **private** by default, so their URL is
   `/private/files/…`. `deploy/nginx.conf` has a static location for `/assets/` and
   proxies `/files/`, but **`/private/files/` is not named at all** — it falls through
   to `location /` and is answered by Frappe (`frappe/app.py:163`). The app runs
   **gunicorn with 4 workers x 2 threads = 8 concurrent requests for the whole site**
   (`docker-compose.app.yml:261-262`). One HR user opening a DTC-sized chart would
   queue ~400 permission-checked requests through those 8 slots. Two at once and the
   site stalls for everybody.

3. **The "only these document types" rule cannot be enforced by a file URL.**
   `Employee Document` is a **child table** (`istable: 1`) hung on Employee as the
   `employee_documents` field (`alvoraa_employee_documents/setup.py:30`). Its
   `attachment` is therefore attached to the **Employee** record. Frappe's private-file
   gate falls back to `ref_doc.has_permission("read")` on that parent
   (`frappe/core/doctype/file/file.py:1009-1025`). So anyone who may read an Employee
   record may fetch **every** file attached to it by URL, whatever the mini profile
   chooses to list. This is the same child-table trap as ALV-256 (30 Oct): a rule
   written at the row never reaches the file.

**The good news.** Faces are already wired, so the chart work is smaller than it looks:
`ocAvatar` already renders `<img src=p.image>` when a photo exists (`portal.js:276-279`)
and both chart endpoints already ship `image` (`api.py:177`, `api.py:550`). **Measured:
0 of 403 employees on `ppj.localhost` have an image, and the whole site has 2 `File`
rows.** Nothing is drawing a face today because no photo exists.

**And the thing nobody is deciding in this slice:** the employee-facing **Organisation**
page uses the same card renderer and the same `image` field. The moment photos are
uploaded, faces appear there too, for every employee, on a phone, with no further
change. That is where the 3G cost actually lands.

### 1 · What this adds to run

| | Today (measured) | With faces on every card (estimate) |
|---|---|---|
| Hierarchy data, one call | 141.8 KB raw / **10.7 KB gzipped** | +~20 KB raw / +~2 KB gz for 403 URL strings — negligible |
| Page code, first visit | `portal.js` **284 KB gz** (1.12 MB raw), `panels.css` **36 KB gz**, `frame.css` 6.6 KB gz => **~330 KB gz** | unchanged |
| Images, first visit | **0 bytes** | **~16 MB** (403 x ~40 KB) |
| Images, repeat visit | 0 | ~400 conditional requests → 304s. nginx sets **no** `Cache-Control` on `/files/` and nothing at all on `/private/files/`, so the browser revalidates. **~400 round trips, still through the 8 app slots** |
| Requests answered by Python | ~3 | **~403** |

The ~40 KB per photo is an **estimate** with a measured basis: Frappe's uploader turns
`optimize` on by itself for any image over 200 KB (`FileUploader.vue:435`) and the
server then resizes to about 1024x768 at quality 85 (`frappe/utils/image.py:48`). A
1024x768 JPEG at q85 is roughly 80–150 KB; many HR-supplied photos are smaller and pass
through untouched. **40 KB is the optimistic middle. Under 200 KB nothing is resized at
all, so a 199 KB photo is stored and served as 199 KB — five times my estimate.**

Each face is displayed in a **24 px** circle on the chart (`panels.css:2141`) and a
34 px circle on a card (`panels.css:1855`). A 48x48 thumbnail is about **2–3 KB**. We
would be shipping **15–60x more bytes than the screen uses**.

**Run cost in money: effectively nil** — no new container, no new service, no new
dependency, and the storage sits on a disk we already pay for. The cost is **capacity
and page weight**, not the bill.

### 2 · 3G and the phone

`docs/product/design-benchmark/2026-10-24-ux-priorities.md:161` warns off "stock photos
and illustrations — slow on 3G, mean nothing to a low-literacy reader". Faces of real
colleagues are not stock photos; they do mean something. The weight is the same, though.

The NFR budget is **≤ 2.5 s p95 on a 3G phone, skeleton within 300 ms**
(`nfr-budget.md` §2).

| Scenario | Bytes | Slow 3G (400 kbit/s) | Fast 3G (1.6 Mbit/s) |
|---|---|---|---|
| Positions page today, first visit | ~330 KB gz + 10.7 KB data | **~7 s** | ~1.8 s |
| Positions page today, repeat visit | ~11 KB (assets cached 30 d, `nginx.conf:214`) | **< 1 s** | < 1 s |
| With 403 faces, first visit | ~16.3 MB | **~5 min 30 s** | **~1 min 25 s** |
| With 403 faces at 48 px thumbnails | ~1.3 MB | ~27 s | ~7 s |
| Mini profile only, one face + up to 18 document names | ~40 KB | ~1 s | < 1 s |

Times are **estimates**: bytes divided by throughput, Chrome's standard Slow/Fast 3G
profiles, no allowance for the 400 ms round trip each image also pays. They are the
floor, not the forecast. The first row shows the page is **already over the 2.5 s budget
on a first visit** before any photograph — that is existing debt, caused by one 1.12 MB
`portal.js` shared by the whole portal, and it is not this slice's to fix.

**Who is actually on this page matters.** `Alvoraa Position` ships read to **HR Manager
and System Manager only** (`alvoraa_position.json`), and who may open the page is each
tenant's own choice in Role Permissions Manager (`register.py:66-86`). On
`ppj.localhost` the effective set is **System Manager alone** — there are `Custom
DocPerm` rows for that doctype, and once any exist Frappe ignores the shipped `DocPerm`
rows entirely (`frappe/permissions.py:528-529`). **I could not check DTC's rows; that is
production.** So the frontline 3G risk is not this page. It is the **Organisation** page,
which every employee can open and which will start loading whatever photos exist.

### 3 · Private files — exactly how each thing is served today

All **Fact**, read in the running image:

- **Employee photo.** `Employee.image` is an attach field. Frappe's uploader marks an
  upload **private unless the doctype sets `make_attachments_public`**
  (`FileUploader.vue:444`); **Employee does not set it**. So a normal Desk upload lands
  at `/private/files/…`.
- **Serving a private file.** `/private/files/…` is handled by
  `frappe.utils.response.download_private_file` (`frappe/app.py:163`), which checks
  `File.has_permission` → not private? allow; owner? allow; shared? allow; **else the
  parent document's read permission** (`file.py:989-1026`).
- **What that means here.** `Employee` read is held by the **Employee** role itself
  (**measured** on `ppj.localhost`: `DocPerm` row `Employee / read=1`), narrowed per
  tenant by User Permissions (**measured:** 412 `User Permission` rows allowing
  Employee). So whether a colleague's photo — or a colleague's scanned PAN card — is
  fetchable by URL today depends entirely on each tenant's User Permission rows, not on
  anything this slice draws. Per the 26 Oct note, DTC's rows are deliberately narrow and
  per-doctype.
- **Thumbnails: do not use Frappe's.** `File.make_thumbnail` always writes to
  `public/` — `frappe.get_site_path("public", thumbnail_url)` (`file.py:561`). For a
  private source it either fails (the directory does not exist) or, with a public
  source, publishes a face at a guessable address. Either way it is the wrong tool.
- **EXIF.** `strip_exif_metadata_from_uploaded_images` is **on** (measured on
  `ppj.localhost`; Frappe's default is 1) — but the code only strips `image/jpeg`
  (`file.py:813-819`). **A PNG or HEIC upload keeps its metadata, GPS included.**
- **Nothing in this slice needs to be public,** and nothing should become public. A
  public thumbnail folder is the cheapest way to make the chart fast and the worst
  thing to do with 400 employees' faces.

### 4 · Storage and backup

- **Photos:** 403 x ~40 KB ≈ **16 MB per tenant** (estimate on a measured headcount).
  The dev sites volume is **169 MB** today (quoted in `deploy.yml:302`), so about +10%.
  Not a problem on its own.
- **Documents are the real growth, and they are already provisioned.** **Measured:
  6,469 `Employee Document` rows exist on `ppj.localhost` across 18 document types —
  16.1 per employee — and `0` of them have an attachment.** The checklist is waiting to
  be filled. At 500 KB a scan that is **~3.2 GB per tenant**; at 1 MB, 6.5 GB. This
  slice does not create those uploads, but it is the screen that will make people start
  making them.
- **Every deploy copies all of it.** `.github/workflows/deploy.yml:312` runs
  `bench --site all backup --with-files` as the rollback point, and the disk gate
  **fails the deploy below 25 GB free and warns below 45 GB** (`deploy.yml:280-290`) —
  that gate exists because of the 10 September outage. Good news: `bench backup` prunes
  its own folder first, anything older than 23 hours
  (`frappe/utils/backups.py` → `delete_temp_backups`), so backups do not pile up. The
  cost is a **second full copy of every file, written at every deploy**, plus the S3
  sync of the file tarballs if `BACKUP_BUCKET` is set — **I could not check whether it
  is; that is a repository secret.**
- **No new volume, no object storage and no CDN is needed at this size.** 16 MB of
  faces does not justify a new moving part. Several GB of identity documents would be a
  separate conversation, later, with a measured number.

### 5 · Red flags

**The idea as stated is sound apart from one thing: faces on every card at once.**
Everything else — mini profile from three places, an admin-chosen field list, an
admin-chosen document-type list — is cheap and low risk if the file gate is right.

- **Zoom.** The Positions chart has CSS zoom from **0.4 to 2.0** (`portal.js:1597`),
  plus Reset and Fit-to-width. At 0.4 a 24 px face renders about **10 px** — a 150 KB
  download for ten pixels. Keying faces to a zoom threshold does cut the bytes and I can
  support it, with two warnings: **(a)** CSS zoom keeps every card in the DOM, so
  `loading="lazy"` only helps cards scrolled off-screen, and zooming **out** puts *more*
  faces on screen, not fewer; **(b)** the wall-chart print path (slice 069) renders the
  whole tree and prints immediately — lazy or zoom-gated images print as **blank
  circles**. I could not find the zoom rule you described in the idea text given to me,
  so I have not costed it. See Open question Q2.
- **N+1 per seat, and it is already there.** `api.py:177` reads the photo with **one
  `frappe.db.get_value` per person, per node, per expansion**, and `_card`
  (`api.py:548`) does one read per person as well. `position_table` is the well-behaved
  one — two queries for 403 people. Faces on the table must ride on that same batch, and
  the mini profile must be one read, not one per field. The NFR gate is that the query
  count is **the same for twenty people as for a thousand** (`nfr-budget.md` §2).
- **The field list is not a permission.** `employee_field_rights.py` puts bank,
  statutory IDs and salary at permlevel 1, HR Manager only. If an administrator can tick
  "show on Positions" against any Employee field, the list must be filtered by permlevel
  server-side as well, or the page becomes a way around ALV-215. Security's call; I am
  flagging it so it is not discovered at review.
- **Photos must never reach an AI path.** `nfr-budget.md` §6 and the EU AI Act's
  Article 5 ban on emotion inference in the workplace, in force since 2 Feb 2025. Faces
  in a payload make that easy to do by accident later. Say "never" now.
- **Local bench will not run this today.** `register.position_table` raises on
  `ppj.localhost` for a plan reader: `Replacement Plan` is not migrated on that site
  (`DocType Replacement Plan not found`, via `plans.table_view`). **Fact**, seen today —
  and `bench execute` reported it as `NameError: name 'hrms' is not defined` on stdout,
  which is lesson 8 exactly. Whoever builds this will lose an hour to it.

### 6 · Recommendations

| ID | Recommendation | Why | Cost of ignoring it | Weight | Decision |
|---|---|---|---|---|---|
| OPS-1 | **Faces in the mini profile and the "Change this seat" dialog; initials on the chart cards.** `candidates_for` already caps at 50 rows (`register.py:1069`). | One face per click instead of 403 per page. Meets "clicking a name opens a mini profile" in full. | ~16 MB and ~400 Python-served requests per page open; the site's 8 concurrent slots exhausted by one HR user. | **Recommend · P1** | |
| OPS-2 | If faces on the chart are wanted anyway, they need a **stored 48 px thumbnail**, generated once on upload, **not** Frappe's `make_thumbnail`. Cost: ~30 lines in a hook, ~2–3 KB per employee, one Pillow call per upload. Still ~400 requests, so pair it with OPS-3. | 15–60x fewer bytes. Frappe's own helper writes thumbnails into `public/` (`file.py:561`). | A 5-minute first load on 3G, or 400 faces published at public URLs. | **Recommend · P1** | |
| OPS-3 | Name `location ^~ /private/files/` in `deploy/nginx.conf` **only if** the engineer adds an X-Accel-Redirect path, and never without `scripts/check_nginx_parses.sh` passing first. **My own advice is to avoid touching nginx in this slice entirely** (OPS-1 makes it unnecessary). | One nginx container serves dev **and** production from one file; a dev deploy carrying it restarts the live proxy (lesson 13, 18 Sep). | The live site's proxy changed and restarted by a dev push. | **Recommend · P1** | |
| OPS-4 | **Stream employee documents through our own whitelisted endpoint** that checks (a) the viewer may see this employee on this page and (b) the document type is one of the ticked ones — then returns the file. Do not hand the browser a `/private/files/…` URL. | Frappe's gate is the **parent** document's read permission (`file.py:1009-1025`); a child-row rule never reaches it. | The ticked-types list is decoration. Identity documents readable by URL by anyone who may read the Employee record. | **Recommend · P1** | |
| OPS-5 | Keep the two setting lists on the **configuration rung**: a `show_in_positions` **Check on `Employee Document Type`** (it already carries `verifier_roles`, `applies_to_grades`, so HR sets it where it already works), and the visible-field list as a **Global Defaults key** read by the existing Org Setup page (`alvoraa_org_structure/settings.py` does exactly this today). | Rungs 2–3. A new Settings DocType and a new setup screen are rung 5 and buy nothing here. | A new doctype, a new permission surface, a new screen, a migration — maintained for years. | **Recommend · P2** | |
| OPS-6 | **Batch the photo read.** One `get_all` keyed by employee for the table and the chart; never one read per seat. Assert the query count is the same for 20 employees as for 400. | `api.py:177` and `api.py:548` are already one query per person. | The count grows with headcount; it passes every local test and crawls at DTC. | **Recommend · P2** | |
| OPS-7 | Decide **where photos come from** before the design (Q1). If employees upload from the phone, cap the upload and resize **server-side** — a phone photo is 3–8 MB, `max_file_size` is unset on `ppj.localhost` so Frappe's default applies, and nginx allows 50 MB (`nginx.conf:164`). | The uploader only auto-optimises above 200 KB and only in Desk; a portal upload path may not pass `optimize` at all. | Multi-megabyte originals in the sites volume, in every backup, for ever. | **Recommend · P2** | |
| OPS-8 | **Strip metadata for every image type, not just JPEG.** Convert on upload, or refuse PNG and HEIC. | **Measured:** the EXIF strip is on but only runs for `image/jpeg` (`file.py:813`). | A staff photo carrying the GPS location of someone's home. | **Consider · P2** | |
| OPS-9 | **FYI:** this slice changes `portal.js` and `panels.css`, which the sites volume shadows. The release will need the asset refresh and an `assets.json` bump, or every browser keeps the old file. | Memory, 23 and 28 Oct: deploys do not refresh `sites/assets`; `?v=` is one timestamp. | A green deploy serving last release's chart. | **FYI · P2** | |
| OPS-10 | **FYI:** nothing here needs a new container, queue, worker, cache, CDN or bucket, and I am not proposing one. | Docker Compose, one small team. | — | **FYI · P4** | |
| OPS-11 | **FYI, ops debt, not this slice:** the Positions page already misses the 3G first-load budget because `portal.js` is 1.12 MB (284 KB gz) for the whole portal. Worth its own slice some day, with a measurement. | Measured today. | Nothing new; it is already true. | **FYI · P3** | |

**Known gaps, labelled:** OPS-11 is **temporary debt** — removed only by splitting
`portal.js`, which needs its own slice. The private-file parent-permission behaviour
(OPS-4) is **dangerous debt if the document list ships without a server gate**; it is at
the top of this section for that reason. Everything else is an **intentional
trade-off** you are being asked to make.

### Subtract pass

I removed three things before handing this over: a proposed page-weight CI gate (no
number to defend yet — it belongs in §2 once the design exists), a recommendation to add
`Cache-Control` to `/files/` (the browser already revalidates with 304s, and OPS-1 makes
the request count small enough not to care), and a run-cost table in rupees (the honest
figure is "nil", which is one sentence, not a table). I also dropped my first instinct to
recommend an image-resize job on the queue — there is no measured number that needs one,
and a hook on upload is one rung cheaper.

### Open questions

| # | Question | Owner | Blocks |
|---|---|---|---|
| Q1 | **Who uploads the photos, and from where** — HR in Desk, or the employee from the ESS phone page? My reading is HR in Desk, because that is the only upload path that exists for `Employee.image` today, and it gets Frappe's automatic resize above 200 KB. If employees upload from phones instead, OPS-7 becomes P1 and the design needs an upload screen nobody has drawn. **Default if you want me to keep moving: assume HR in Desk.** | User | Design (§2) sizing, OPS-7 |
| Q2 | **What is the zoom rule?** The idea text I was given does not mention zoom, but the page has CSS zoom 0.4–2.0. If the rule is "faces only above 80%", say so and I will cost it in §2 — including what the wall-chart print does. | User / UX | §2, OPS-2 |
| Q3 | **Do any employee photos exist at DTC today?** If not, the benefit of this slice is zero until someone uploads 442 of them, and that is a person-weeks job nobody has costed. **I could not check: that is production.** | User | Whether this is worth building now |
| Q4 | **May the admin's visible-field list include a permlevel-1 field** (bank, PAN, salary)? My recommendation is that the server filters by permlevel regardless of what is ticked. | `hrms-security-privacy-engineer` | Requirements (§3) |
| Q5 | **Is `BACKUP_BUCKET` set?** It decides whether every photo and document also leaves the server on every deploy. I could not check a repository secret. | User | §5 only |

### Assumptions

- `[ASSUMPTION]` A DTC-sized chart is roughly the shape of `ppj.localhost`: ~400 seated
  people. DTC's own seat count I could not read.
- `[ASSUMPTION]` ~40 KB per stored photo. Basis: Frappe resizes above 200 KB to about
  1024x768 at q85; below 200 KB nothing is touched. The true spread is 20–200 KB.
- `[ASSUMPTION]` 500 KB per scanned employee document, for the 3.2 GB figure.
- `[ASSUMPTION]` Chrome's Slow 3G (400 kbit/s) and Fast 3G (1.6 Mbit/s) represent a DTC
  frontline phone. Round-trip latency is not included, so the times are floors.
- `[ASSUMPTION]` DTC's Positions page audience is HR and the owners, as at PPJ. Its real
  permission rows are on production and I did not look.

### Handoff note

To the **product manager** writing `01-product-brief.md`: the expensive half of this
idea is "faces on the hierarchy", and it is expensive for one reason — the chart arrives
in a single payload of 120 seats and 403 people, so faces mean ~400 image downloads
served by the app's own Python workers, about 16 MB and minutes on a 3G phone. The mini
profile, opened on a click from three places, costs almost nothing and delivers most of
the value. **If the brief has to cut something, cut faces on the chart cards, not the
mini profile.** Please also carry Q3 into the brief: if no photographs exist at DTC
today, this slice ships an empty feature until someone uploads 442 of them.

To **security** (§4 and `01c`): the one thing I cannot fix with infrastructure is that
`Employee Document` is a child table, so its attachment belongs to the **Employee**
record and Frappe's private-file check asks the parent. The ticked-document-types list
is cosmetic until a server endpoint streams the file. See OPS-4.

I have not touched anything. No container was created, nothing was written to the bench,
no site setting changed. One read-only `bench execute` of an existing endpoint was run on
`ppj.localhost`; it reads and returns, and its output went to `/tmp` inside the
container. No secret, and no path to one, appears above.

---

## §3 Requirements — 31 October 2026

Advice only. Every row ends in a **Decision** column that is yours, left blank.

Read `01-product-brief.md` revision 2 and `01b-ux-design.md` prototype v4 (§5 and §6.3.1)
before this section. Everything new below was read or measured **today, 31 October 2026**,
on the PPJ local copy (database `_33a7090c6c978fc6`, site `ppj.localhost`, image
`dev-3830ed3`) or in this worktree. **Nothing was run on dev or production. Nothing was
changed anywhere.** One `gh secret list` (read-only, names only — no value was read or
printed). The decisions of §1 are not reopened; this section makes them run.

### Answer first

**No P0. Three things at the top.**

1. **The designer's load-bearing number is safe, but not for the reason given. I measured
   it.** First paint of the Positions hierarchy on PPJ's 120 seats and 403 people is
   **16 boxes and 16 faces** — not 30, and not 403. The reason is **not** lazy loading.
   It is two constants already in the code: `POS_OPEN_DEPTH = 1` (`portal.js:476`, set by
   slice 064) and `POS_NAMES_SHOWN = 3` (`portal.js:802`). Lazy loading contributes almost
   nothing at first paint, because **on a 3G connection Chrome's lazy threshold is 2,500 px
   from the viewport**, and a 16-box chart fits inside that. So the design is affordable,
   with room to spare — and it is affordable because of a constant anyone could raise back
   to 2 without realising what it costs. **OPS-21 is that guard.**

2. **`BACKUP_BUCKET` is not set. I checked.** `gh secret list` returns exactly three
   secrets — `DEPLOY_HOST`, `DEPLOY_SSH_KEY`, `DEPLOY_USER` — and the `dev`, `production`
   and `test` environments have none of their own (**Fact**, 31 Oct 2026). So the deploy
   prints *"BACKUP_BUCKET not set — backups exist only on the server"* (`deploy.yml:332`),
   and there is no scheduled backup anywhere else: the only copy is made at deploy time, on
   the same disk, and `bench backup` deletes anything older than 23 hours. **This slice is
   the first to invite 442 people to upload identity documents into that single copy.**
   Full answer and what each option means in **§3.7**.

3. **The one genuinely tight number is the table, not the chart and not the enlargement.**
   Measured: the table view draws **215 faces across 120 rows**. On a 3G phone the 2,500 px
   lazy threshold reaches about 60–70 rows, so roughly **125 photos are requested nearly at
   once** — and `http2 on` is set in nginx (lines 142, 155, 356), which removes the
   browser's old six-connections-per-host limit. 125 Python-served requests arriving
   together at **8 gunicorn slots** is where a driver's check-in post waits in the queue.
   **OPS-19.**

**The enlargement is a rounding error, and I can say so with a number.** One hover is
**one request for one 512 px file, about 30–60 KB**. Ten people enlarged in a minute is ten
requests — fewer than one chart repaint (16). Five HR users each enlarging at the same
moment occupies 5 of the 8 slots for roughly 50–150 ms. The request budget is intact.
Details in §3.3.

### 3.1 What I measured today, in one table

All on the PPJ local copy, 31 October 2026. The chart itself still does not render on this
site (`Replacement Plan` not migrated — §1 §5), so the box and face counts are computed
from the real position tree plus the drawing rules read in `portal.js`. That makes them
**Measured data, Inference on the drawing** — and the arithmetic is simple enough to check.

| What | Number | How |
|---|---|---|
| Seats · people · assignments | **120 · 403 · 403** | `tabAlvoraa Position`, `tabAlvoraa Position Assignment` |
| Boxes and people by level | d0 **1/1** · d1 **15/15** · d2 **39/54** · d3 **40/116** · d4 **25/217** | recursive query on `reports_to_position` |
| Levels drawn on first paint | **1 level of children** (`POS_OPEN_DEPTH = 1`) | `portal.js:476` |
| Names shown per box | **3**, then "+N more" | `POS_NAMES_SHOWN`, `portal.js:802`, `posFew` |
| **Faces on first paint, hierarchy** | **16** | 16 boxes × 1 person each, measured |
| Faces if the whole tree is drawn open (any filter is on) | **≤ 215** | `posAnyFilter()` opens everything (`portal.js:1285`), 3-name cap applies |
| **Faces in the table view** | **215** across 120 rows | `SUM(LEAST(people, 3))` |
| Organisation page, one expansion (`subtree`, depth 3 from the root) | **94 boxes, 185 people, no 3-name cap** | `portal.js:4231`, `ocNodeCard` lists every person |
| Employee Document rows · types · with a file attached | **6,469 · 18 · 0** | `tabEmployee Document` |
| Pillow in the running image | **12.3.0, JPEG/PNG/WEBP/GIF only — no HEIF/HEIC** | `python -c` inside `hrlocal-bench` |
| `allow_guests_to_upload_files` | **0** (off), allow-list empty | System Settings |
| `max_file_size` (System Settings) | **0** → Frappe's default **25 MB per file** | `frappe/core/api/file.py:85-90` |
| nginx body limit · API rate limit | **50 MB** · **120 r/m per IP, burst 30, on `location /api/`** | `nginx.conf:164, 292-293` |
| Private file cache header | **`Cache-Control: no-cache`** | werkzeug `utils.py:493`; Frappe passes no `max_age` |
| Cost of one `/private/files/` request | **~31 ms of Python** (refused, so no permission check); `/api/method/ping` 55 ms | 20 curl requests each, inside the container |
| Gunicorn capacity | **4 workers × 2 threads = 8** | `docker-compose.app.yml:261-262` |
| `BACKUP_BUCKET` | **not set** | `gh secret list`, and no environment secrets |
| Chrome lazy-load threshold on 3G or slower | **2,500 px** from the viewport, hardcoded | web.dev, read 31 Oct 2026 |

**The one measurement I could not take honestly:** concurrency. The local bench runs
`frappe serve`, a single-process development server, so the ~31 ms figure is a
**per-request floor**, not a queueing measurement. A real permission-checked private file
loads the `File` row and then the parent `Employee` row, so my **estimate** is 40–80 ms
each on the server. Anything I say about 8 slots under load is arithmetic on that estimate,
not a timing from production.

### 3.2 Why the 48 px copy is allowed — the measured exception

`no-over-engineering.md` asks for a number before an extra mechanism. Here it is.

| What the chart fetches | Bytes, first paint (16 faces) | Slow 3G (400 kbit/s) |
|---|---|---|
| The stored 512 px photo (≈45 KB) | **~720 KB** | **~14 s** |
| A 48 px copy (≈2–3 KB) | **~48 KB** | **~1 s** |

Two orders of magnitude, against a budget of 2.5 s on the employee-facing page. **The 48 px
copy earns its place.** Everything else about faces reuses what exists.

**And one option I rejected, with the number that killed it.** Carrying the thumbnail inside
the chart payload as a data URI would remove every extra request — but
`register.position_table` is **one call that returns all 403 people**, not just the 16 drawn
(measured in §1: 141.8 KB raw). Inlining would add 403 × ~3.4 KB ≈ **1.4 MB** to a payload
that is 10.7 KB gzipped today, and base64 JPEG does not compress. So: a URL per face, lazy,
as the design says. This answers the brief's ⚠ DECISION 2 option (c) — **it is worse, and
here is why.**

### 3.3 What this does to the 8 slots

**Estimate throughout**, built on the measured 31 ms floor and a 40–80 ms working figure.

| Who is doing what | Requests, roughly at once | Python time | My reading |
|---|---|---|---|
| One HR user opens the hierarchy | 16 | ~0.8 s spread over 8 slots | **Fine.** Below one second of total worker time |
| The same user expands five boxes, one at a time | 16 → ~29 per repaint (see OPS-18) | ~1.5 s per repaint | **Fine**, and noticeable only if it coincides with a punch burst |
| One HR user opens the **table** on a phone | **~125** | ~6–10 s of worker time, arriving together over HTTP/2 | **This is the one to bound.** OPS-19 |
| One employee expands the **Organisation** chart from the top | up to **185** | ~9–15 s of worker time | **Employee-facing, so the 2.5 s / 3G budget applies.** OPS-20 |
| Five people each enlarge one photo | 5 | ~0.25 s | **A rounding error.** No action |
| Twenty documents opened in an hour by HR | 20, spread | one file in memory per request | **Fine**, if the file size is capped — OPS-24 |

**What competes with it.** The biometric check-in endpoint has its own nginx rate zone but
the **same backend pool**. A 9 a.m. punch burst and an HR user opening the Positions table
on a phone draw from the same 8 slots. That is the whole reason OPS-19 exists.

### 3.4 OPS requirements — the thumbnail work

| ID | Recommendation | Why | Cost of ignoring it | Weight | Decision |
|---|---|---|---|---|---|
| OPS-12 | **Make the 48 px copy in one more handler on `Employee`'s existing `on_update` chain** (`hooks.py:174-186`), guarded by `doc.has_value_changed("image")`. One Pillow call, inside the request. **No queue, no scheduled job, no new service.** | One function covers every upload path there will ever be — HR in Desk, the employee in the portal, a script. Pillow 12.3.0 is already in the image (measured). A resize of one bounded JPEG is tens of milliseconds, once per upload. | A portal-only hook misses HR's Desk uploads, so half the chart has no thumbnail and nobody knows which half. | **Recommend · P1** | |
| OPS-13 | **The handler must never fail an Employee save.** Catch everything, write to Error Log, leave no thumbnail. The renderer falls back: thumbnail → full photo → initials. | `Employee.on_update` fires on every save of 403 records, including during payroll work. A photo must not be able to block one. The design's measure 3 already gives the fallback for free. | One unreadable image makes an unrelated HR edit fail with a Python error. | **Recommend · P1** | |
| OPS-14 | **Accept `image/jpeg`, `image/png`, `image/webp` only, checked on the server, and store everything as JPEG** (longest edge 512 px, quality 82, as the design says). Refuse anything else in plain words. **Do not add `pillow-heif`.** | **Measured: Pillow 12.3.0 in this image has no HEIF support.** A HEIC file cannot be read, resized **or stripped of metadata** — and Frappe's EXIF strip only runs for `image/jpeg` anyway (§1 OPS-8). A new image library is a permanent thing to patch and upgrade; phones usually hand over a JPEG when the page asks for one. | A stored file nobody can process, keeping the GPS location where the photo was taken. | **Recommend · P1** | |
| OPS-15 | **Replacing or clearing a photo deletes the old thumbnail File row and its bytes.** | Otherwise one orphan per re-upload, for ever, in the sites volume and in every backup. | Slow, invisible growth that nobody can attribute later. | **Recommend · P2** | |
| OPS-16 | **No backfill and no patch.** Measured 0 photos at PPJ; Surbhi has confirmed 0 at DTC. There is nothing to convert, and OPS-13's fallback means there never will be: a photo without a thumbnail simply shows the full photo. | My §1 subtract pass removed the queue instinct. **You asked whether the backfill changes my mind: it does not, because the backfill is empty.** | — | **FYI · P3** | |

### 3.5 OPS requirements — the private-file route

| ID | Recommendation | Why | Cost of ignoring it | Weight | Decision |
|---|---|---|---|---|---|
| OPS-17 | **Hold the line from §1: no change to `deploy/nginx.conf` in this slice.** | Three measured reasons. (a) First paint is **16 requests of ~3 KB** — it does not need help. (b) One nginx container serves dev *and* production from that one file (lesson 13), so a dev deploy carrying it restarts the live proxy. (c) **The public form needs no nginx change either** — `location /api/` already carries `limit_req zone=kinexus_api` at 120 r/m per IP with burst 30 (`nginx.conf:292-293`). **What would change my mind:** a measured p95 over 1.5 s on the Positions table at DTC scale, or documents becoming a routine daily surface. Then the step is `X-Accel-Redirect` — Frappe already supports it and sets `Cache-Control: private, max-age=3600` on that path (`frappe/utils/response.py:334-340`), which would also fix OPS-18 — behind `scripts/check_nginx_parses.sh`, in its own slice. | A dev push changes production's proxy and restarts it. It has happened. | **Recommend · P1** | |
| OPS-18 | **Know that a repaint re-requests every visible face, and accept it at this size.** Private files go out with `Cache-Control: no-cache` (werkzeug `send_file` sets it when no `max_age` is passed, and Frappe passes none — read in the running image today). So every `posPaint()` revalidates every drawn photo: 304s with no body, ~30–50 ms of Python each. At 16–29 faces that is acceptable. **It is the second reason the table needs bounding.** | Zoom does not repaint (it only sets `style.zoom`), but every expand, filter and arrange does. | Nothing today. At 125 faces it is 125 conditional requests per repaint. | **FYI · P2** | |
| OPS-19 | **Bound the table's faces explicitly. Do not rely on `loading="lazy"`.** Measured: 215 faces over 120 rows; the 3G lazy threshold of 2,500 px reaches ~60–70 rows, and `http2 on` lets them all leave at once. Cheapest options, in order: **(a)** faces only in the first 25 rows, with the rest on scroll — or **(b)** an IntersectionObserver with a 200 px margin (~15 lines) instead of the browser's own threshold. | ~125 simultaneous Python-served requests against 8 slots, competing with the morning punch burst. | The HR table becomes the slowest page in the product, and its cost lands on check-ins. | **Recommend · P2** | |
| OPS-20 | **Decide the Organisation page's expansion count on purpose.** Measured: one expansion from the root is **94 boxes and 185 people**, and that renderer has **no 3-name cap**. Either apply the same cap of 3 or accept the number knowingly. **This is the employee-facing page, so this is where the ≤ 2.5 s / 3G budget actually applies** — not to Positions, which is HR and CXO. | The brief already notes that faces arrive here "for free". The bytes are not free. | The one page every frontline employee can open becomes the heaviest, on the worst connection. | **Recommend · P2** | |
| OPS-21 | **Keep `POS_OPEN_DEPTH` at 1 and `POS_NAMES_SHOWN` at 3, and assert the face count on first paint** in the jsdom suite that already runs in CI (`scripts/run_dom_tests.js`, `ci.yml:235-238`). Suggested assertion: **no more than 60 `<img class="av">` on a first paint** of the PPJ-shaped fixture. | These two constants, not lazy loading, are what makes the whole design affordable (§3 answer 1). Raising `POS_OPEN_DEPTH` to 2 takes first paint from 16 boxes to 55 and from 16 faces to ~70, and nothing would warn anybody. No new gate — one assertion in a suite that exists. | A later UX change quietly multiplies the request count by four. | **Recommend · P1** | |

### 3.6 OPS requirements — documents and the public form

| ID | Recommendation | Why | Cost of ignoring it | Weight | Decision |
|---|---|---|---|---|---|
| OPS-22 | **The streaming endpoint, built on the pattern already in this repo:** `frappe.local.response.filecontent` / `.filename` / `.type = "download"` (`hr_api.py:2184`, the payslip PDF). One file per call, named by its `Employee Document` row, never by a file URL. **Say out loud what it costs:** one Python request per file, with **the whole file held in one worker's memory for the length of the download**. On a 3G phone a 25 MB scan holds 1 of 8 slots for about eight minutes. | §1 OPS-4: `Employee Document` is a child table, so Frappe's private-file gate asks the **parent Employee's** read permission and the ticked-types list never reaches it. | The ticked-types list is decoration, and identity documents are fetchable by URL by anyone who may read the Employee record. | **Recommend · P1** | |
| OPS-23 | **Limits on that endpoint:** one file per request; no "all documents" call; `@rate_limit(limit=60, seconds=3600)` per user (the pattern at `field_checkin.py:512`); the viewer check **and** the ticked-type check both server-side; and the field-rights check as well, because 15 of the 18 types are identity, statutory or financial. **Reuse candidate for security to rule on:** the `Alvoraa Photo Access Log` and `field_app_access.log_photo_view` already record who looked at a face — the same pattern would record who opened a document. If it is not used, the requirement should say plainly that document views are **not** logged. | Compliance expects "who read this" to be answerable for identity documents. We already built that mechanism once. | Either an unanswerable question after an incident, or a second mechanism built later for the same job. | **Recommend · P1** | |
| OPS-24 | **Cap the stored file size: System Settings `max_file_size = 5` (MB).** Measured today it is **0**, which means Frappe's fallback of **25 MB per file**, while nginx allows a 50 MB body. **Say the side effect out loud: this setting is site-wide** and applies to every upload on the site, not only to documents. | 5 MB is a generous phone photo of a document and a tenth of what is allowed now. It also bounds OPS-22's memory cost to seconds instead of minutes. | A 25 MB scan per row, 6,469 rows, in one worker's memory on demand, and in every backup. | **Recommend · P1** | |
| OPS-25 | **Do not turn on `allow_guests_to_upload_files` without setting `allowed_doctypes_for_guest_uploads` in the same change.** Measured: it is **off** today and the allow-list is **empty**. On with an empty allow-list means **any guest may upload a file attached to any doctype on that site**. If the form is built as a Frappe Web Form, that switch must go on — so the allow-list is not optional. **The alternative, which I prefer on risk:** one own whitelisted endpoint with `allow_guest=True` that takes the token and the file, so the global switch stays off and the limits, the size cap, the type check and the resize all live in one place we control. | This is the product's first public upload path. The switch is site-wide; the allow-list is the only thing that narrows it. | A public, unauthenticated upload into any doctype on a live tenant. | **Recommend · P1** | |
| OPS-26 | **Per-token limits, using the module that already exists for exactly this problem:** `alvoraa_portal/field_app_limits.py`. It wraps Frappe's `rate_limit` and **hashes the token first**, because Frappe's limiter writes the key's value into Redis in clear. Suggested numbers, all adjustable: open the link **20/hour** per token; submit **3 per 24 hours** per token; upload **12/hour** per token; **at most 6 files and 20 MB in total** per token; link valid **7 days**; one submission, as the design says. | A tokenised link is not an open door — but the token check, the submit and the upload are all guest-reachable, and per-IP limits do not separate 400 joiners behind one depot's Wi-Fi from one abuser. Per-token does. | The secret in Redis in clear (the exact fault slice 013 found), or an unbounded upload path. | **Recommend · P1** | |
| OPS-27 | **No nginx change for the form, and do not add its page to the compressed-HTML list.** `location /api/` already rate-limits every `/api/method/...` call at 120 r/m per IP. The form page itself falls through to `location /`, which does **not** gzip HTML on purpose (the BREACH rule, `nginx.conf:302-326`). Leave it there. | Adding a page to that list means editing the file that serves production, and the rule exists because a signed-in page carries the CSRF token. | A shared-file edit for a form page that is a few kilobytes. | **FYI · P1** | |
| OPS-28 | **The invariant worth watching: submissions ≤ links issued.** Count both, and count refusals. A day where submissions exceed links issued, or where one token uploads more than 6 files, means a link has been shared or replayed. | It is one comparison between two numbers we already have, and it catches the abuse case the brief red-teamed. No new tool. | A forwarded link used by strangers, invisible until HR notices records for people they never invited. | **Recommend · P2** | |
| OPS-29 | **Nothing is stored before the token is validated** — no partial row, no file. And **document bytes must never be kept in `localStorage`.** The design's "your answers are kept on this phone" should mean the typed answers only. | A joiner may be on a borrowed phone. An image in `localStorage` also blows the quota and fails silently. | Identity scans left on someone else's phone, and an upload that fails for a reason nobody can explain. | **Recommend · P1** | |
| OPS-30 | **What stops someone filling the disk, in one place:** the per-token file count and byte cap (OPS-26), the 5 MB per-file cap (OPS-24), the 7-day one-use token, and the **hourly** disk alarm that already runs (`scripts/check_workers.sh`: fail below 20 GB, warn below 40 GB, checked every hour by `worker-health.yml`). **Without the per-token byte cap**, the existing 120 r/m per IP allows about **3 GB a minute** at today's 25 MB limit. | You asked what stops the disk filling. These four things, and the first two are the ones this slice has to build. | A full disk, which is the one failure that defeats a restart policy (lesson 16). | **Recommend · P1** | |

### 3.7 Backup, disk, and your `BACKUP_BUCKET` question

**It is not set.** `gh secret list` returns `DEPLOY_HOST`, `DEPLOY_SSH_KEY`, `DEPLOY_USER`
and nothing else; the `dev`, `production` and `test` environments have no secrets of their
own (**Fact**, read 31 Oct 2026 — names only; no value was read). So today every deploy
prints the warning at `deploy.yml:332` and **no file ever leaves the server.**

**What each answer means, so you can decide once.**

| | **Leave it unset** (today) | **Set it** |
|---|---|---|
| Where the only copy lives | One server disk. The pre-deploy backup is on the **same disk**, and `bench backup` deletes anything older than 23 hours | Also an S3 bucket, synced before every deploy |
| If the server or the disk is lost | **Every photo and document ever uploaded is gone**, along with the database | Recoverable to the last deploy |
| Privacy surface | Simple. PII stays in one place under one set of controls | **A second place holding identity documents** — needs its own encryption, retention, access list, region (India) and a DPDP record. Plus AWS credentials on the server |
| Cost | None | Storage and transfer, monthly, growing with the documents |

**My recommendation: do not set it as part of this slice**, and do not treat it as a
blocker for photos. Treat it as a blocker for *documents at volume*, and decide it on its
own with the three things below. Setting it quietly would move identity documents offshore
without a privacy decision, which is worse than leaving it off.

| ID | Recommendation | Why | Cost of ignoring it | Weight | Decision |
|---|---|---|---|---|---|
| OPS-31 | **Three things must be true before the documents part ships.** (1) A **dated reading of free disk on the server** — I cannot take it, that is production. (2) **One restore proved** from a backup set that includes `--with-files`, on dev, written down. (3) **A decision on `BACKUP_BUCKET`**, yes or no, recorded. | Priority order, rule 1: a backup you have not proved you can restore is not a backup. This slice is the first to put irreplaceable, employee-supplied, identity-grade content into the files tree. | A document a joiner uploaded and HR never copied exists in exactly one place, with a backup at most one deploy old, on the same disk. | **Recommend · P1** | |
| OPS-32 | **The arithmetic to put beside the disk reading.** The 3.2 GB-per-tenant figure from §1 now has a measured basis: **6,469 `Employee Document` rows** × 500 KB. The deploy's own `bench --site all backup --with-files` writes a second copy at every deploy, and the gate **fails below 25 GB free and warns below 45 GB** (`deploy.yml:280-290`). The last figure written into that file was "43 GB free" (~23 Sep). **3.2 GB live plus 3.2 GB of tarball, per tenant, is inside that headroom for one or two tenants and not for five.** | Documents are the only part of this slice that grows without limit. Photos are ~16 MB per tenant. | The deploy gate starts failing, which is the gate working — but at the worst moment. | **Recommend · P2** | |

### 3.8 Monitoring — what should be watched that is not watched today

**Good news first: disk is already watched hourly.** `worker-health.yml` runs
`scripts/check_workers.sh` against both stacks every hour, and that script fails below
**20 GB** free and warns below **40 GB** (lines 56-57, 211-217). The growth this slice
invites is therefore already alarmed, and **I am not proposing anything new for disk.**

| ID | Recommendation | Why | Cost of ignoring it | Weight | Decision |
|---|---|---|---|---|---|
| OPS-33 | **Two new numbers, both from data we will already have, no new tool:** (a) **pre-onboarding submissions and refusals per day**, with the alert being *submissions > links issued* or *uploads > 6 for one token* (OPS-28); (b) **files-tree size per tenant, read at each release rather than continuously**, because the hourly disk alarm already covers the dangerous case. | A public endpoint is the first thing in this product that strangers can reach. Nothing watches guest traffic today. The threshold is an invariant, not a guess at a rate. | A forwarded link quietly used by strangers, or a tenant's documents growing past the backup window with nobody looking. | **Recommend · P2** | |
| OPS-34 | **Do not build monitoring for the thumbnail hook.** Its failures land in Error Log, and its visible symptom is "the faces are missing", which HR will report within a day. | An alarm on a cosmetic, self-announcing failure trains people to ignore alarms. | Nothing. | **FYI · P3** | |

### 3.9 What the deploy pipeline must know

| ID | Recommendation | Why | Cost of ignoring it | Weight | Decision |
|---|---|---|---|---|---|
| OPS-35 | **Migrations: nothing special.** Every branch deploy already sets `migrate=true` (`deploy.yml:159`), and maintenance mode wraps it. The schema change here is small — one Check field on `Employee Document Type` (18 rows) and, for the form, one new doctype. The two settings lists are **Global Defaults keys**, which need no migration at all. | Rung 2 of the ladder, as §1 OPS-5 recommended. | — | **FYI · P2** | |
| OPS-36 | **The `assets.json` trap does not apply to the pipeline — I checked, and this downgrades my own §1 OPS-9.** `scripts/refresh_bench_files.sh` copies the bundles first and **`assets.json` last** (lines 55-68), and the `?v=` on `portal.js` comes from `get_build_version()`, which reads that file's timestamp (`www/hrms_employee.py:28`, used by `hrms-employee.html:75`). So a real deploy bumps the version by itself. **The trap bites only a manual `docker cp` on the bench or a hotfix** — which is exactly how the 28 October lesson was learned. | §1 OPS-9 said the release "will need" the bump. It does not; the pipeline does it. Saying so removes a step from the release plan. | A release plan with a step nobody needs, which is how real steps get skipped. | **FYI · P2** | |
| OPS-37 | **Order of operations, and the one thing worth sequencing:** the photo upload must be switched on **before** faces are worth looking at, and the privacy sentence (design ⚠ DECISION 8) gates switching it on at a tenant. Both the UX designer (§15) and the PM say the same. Everything else in this slice ships in any order. | Until photographs exist, every face in the design is a pair of initials. | A release that changes nothing anyone can see, and a photo collected before the notice exists. | **Recommend · P2** | |
| OPS-38 | **One pre-release check to run on dev, read-only:** open Positions on `dev` and **count the `<img class="av">` on first paint**, and confirm the figure against OPS-21's assertion. Nobody has rendered this chart — the local bench cannot (`Replacement Plan` not migrated) and the designer could not either (`01b` §15). | The whole design rests on a count that has never been observed in a browser. My 16 is arithmetic on measured data, not a render. | A number everybody trusts and nobody has seen. | **Recommend · P1** | |

### 3.10 Where I disagree with the design, in writing

1. **§5 measure 1 is credited with the saving, and it does not do the work.** Lazy loading
   defers almost nothing at first paint, because Chrome's threshold on 3G is 2,500 px. The
   saving comes from `POS_OPEN_DEPTH = 1` and the 3-name cap. **This matters because it
   moves the guard**: the design asks the engineer to measure the on-screen box count; what
   actually needs protecting is two constants and the table's row count. I agree with
   keeping `loading="lazy"` — it costs nothing and helps the table — but it is not the
   reason this is affordable.
2. **§6.3.1's "cached for the rest of the session" will not happen by itself.** Private
   files are sent with `Cache-Control: no-cache`, so the browser revalidates. If the
   enlargement should not re-request, the JS has to keep the element or the blob. One
   sentence in the spec; otherwise it is a promise the HTTP headers contradict.
3. **§5.6 says "only the rows on screen fetch a photo — about 15 of 120."** On a 3G phone
   it is more like 60–70 rows and ~125 photos, for the reason in point 1. The figure in the
   design is the desktop figure.

### 3.11 Subtract pass

Read back once asking only *what can I delete and still meet the requirement?*

**Removed before handing this over:**

- **A new CI gate.** My first draft had one for page weight. The assertion in OPS-21 goes
  into a jsdom suite that already runs; nothing new is added to `ci.yml`.
- **A files-tree size alarm.** The hourly disk check already catches the dangerous case.
  Reading the size at each release is enough, and it is not a new tool.
- **A recommendation to set `BACKUP_BUCKET`.** It would move identity documents to a second
  place without a privacy decision. Replaced by "decide it, separately, and prove a restore
  first".
- **A per-tenant switch for the chart faces.** Nobody asked for one, and the photo upload
  switch already controls whether any face exists.
- **An X-Accel-Redirect design.** Written, then deleted down to one sentence inside OPS-17,
  because the measured first-paint figure does not need it and the file is shared with
  production.
- **A monitoring row for private-file 403s and 404s.** The symptom is a missing face, which
  the user reports faster than a dashboard would.
- **My own data-URI thumbnail idea.** Measured against the real payload and rejected in
  §3.2 — kept only as the rejection, so it is not re-proposed as cheap.
- **A queue, a worker, a cache, a bucket and a CDN.** None is proposed. Still true from §1.

**Nothing was added that does not already exist in the repo, except:** the thumbnail hook
(one handler on a chain that is already there), the document streaming endpoint (the
payslip-PDF pattern), and the form's own limits (the `field_app_limits` wrapper).

### 3.12 Escalations

**One, and it is yours alone.**

> **Decision needed:** whether the documents part of this slice ships before a restore has
> been proved and free disk on the server has been read.
> **Context:** `BACKUP_BUCKET` is not set (measured), there is no scheduled backup, and the
> only copy of an uploaded document is on one disk with a backup at most one deploy old.
> **Conflict:** "production stays up and its data stays safe" (priority 1) against release
> speed (priority 7).
> **Who is affected:** every employee whose identity document is uploaded, and HR, who
> would have to ask 442 people for them again.
> **Options:** (a) ship photos and the mini profile now, hold documents until OPS-31's
> three things are done — **my recommendation**; (b) ship everything and accept the risk in
> writing; (c) hold the whole slice.
> **Risk if it waits:** none to the product. Photos, the mini profile, My profile and the
> settings card are all unaffected.
> **Owner:** you. It touches production storage.

Everything else in this section is advice on work that has not started, and needs no
decision from anyone but you at the requirements gate.

### 3.13 Known gaps, labelled

- **Temporary debt:** private files are served by Python with no browser caching
  (OPS-17, OPS-18). Removed by `X-Accel-Redirect` in its own slice, when a measured number
  asks for it.
- **Intentional trade-off:** 16 Python-served requests on a chart paint, and ~125 on the
  table unless OPS-19 is taken. Both are measured and both are yours to accept.
- **Acceptable simplification:** no monitoring for the thumbnail hook (OPS-34).
- **Dangerous debt if the documents part ships as it stands:** the single-copy backup
  (OPS-31). That is why it is in §3.12 rather than only in a table.

### 3.14 What I could not check

- **Free disk on the server.** Production. I could not look, and the last figure written
  into `deploy.yml` is from about 23 September.
- **DTC's position tree.** Every box and face count above is PPJ's shape. **The 3-name cap
  means DTC's face count per box is capped at 3 whatever its headcount**, which is the
  reassuring part; the number of boxes drawn at DTC I do not know.
- **Concurrency.** The local bench is a single-process development server. The 31 ms figure
  is a per-request floor, not a queueing measurement.
- **Whether the 48 px and 512 px sizes really come out at 2–3 KB and 30–60 KB.** Both are
  estimates from the design; no photograph exists anywhere to measure.
- **Whether a phone really hands over a JPEG rather than a HEIC file** when the page asks
  for `image/jpeg`. Usually it does; I have not tested it on an iPhone, and OPS-14's
  server-side refusal is what makes it safe either way.
- **Chrome's current lazy threshold in the browser our users have.** 2,500 px on 3G is from
  web.dev, read today; the page itself says the value is hardcoded and may change.

### 3.15 Open questions

| # | Question | My reading, and the default if you want me to keep moving | Owner | Blocks |
|---|---|---|---|---|
| Q6 | **Does the documents part ship with this slice, or after OPS-31's three things?** | My recommendation is after. **Default: build it, switch it off, and turn it on once a restore has been proved.** | You | §3.12 |
| Q7 | **Web Form, or our own guest endpoint, for the form's uploads?** | The PM and the designer both chose Frappe's Web Form, which means the **site-wide** guest-upload switch must go on, with the allow-list set in the same change. Our own endpoint keeps the switch off and puts the limits in one place. **Default: Web Form plus a set allow-list, because it is the decided design and the allow-list closes the hole.** | You, with `hrms-security-privacy-engineer` | OPS-25, OPS-26 |
| Q8 | **Is the 5 MB site-wide file limit acceptable?** | It applies to every upload on the site, not just documents. **Default: 5 MB.** | You | OPS-24 |
| Q9 | **Are document views logged?** | The mechanism exists (`Alvoraa Photo Access Log`). My recommendation is yes, reusing it. If not, the spec should say so plainly rather than leave it unstated. | `hrms-security-privacy-engineer` | OPS-23 |

### 3.16 Handoff note

**To `hrms-business-analyst`,** the operational requirements that must become user stories
with acceptance criteria, shortest first:

- **Queues and workers: none.** Nothing in this slice goes on a queue. Say so in the spec so
  nobody adds one later "for safety".
- **Rate limits:** OPS-23 (60 document opens per hour per user) and OPS-26 (the five
  per-token numbers). These are testable with the patterns in
  `tests/test_field_app_step6_013.py`, which already exercises Frappe's limiter.
- **Route rules: none.** No nginx change (OPS-17, OPS-27). That is a requirement in itself —
  a story that says "the form needs no change to the shared proxy" is worth writing down.
- **Upload limits:** type (OPS-14), size (OPS-24), count and total bytes per token (OPS-26).
  Each needs an acceptance criterion with the plain-English refusal in it, per the
  28 October lesson: **test what it sends, not just what it draws, and show the server's
  real refusal.**
- **Backups and retention:** OPS-31's three preconditions, and counsel's retention number
  for a joiner who never joins (design ⚠ DECISION 9) — which is a requirement, not a note.
- **Monitoring:** the one invariant, *submissions ≤ links issued* (OPS-28).
- **Secrets:** no token, code or secret in a job argument, a log, a URL or a Redis key — the
  reason `field_app_limits.py` hashes first (OPS-26).
- **The guard that protects the whole design:** OPS-21's face-count assertion.

**To `hrms-security-privacy-engineer`:** three things are yours and I have only flagged
them — the child-table file gate (§1 OPS-4, now OPS-22), whether document views are logged
(OPS-23), and the guest-upload switch (OPS-25). The one measured fact you will want:
**Pillow in the running image cannot read HEIC**, so a HEIC upload is stored unprocessed and
keeps its metadata, GPS included, because Frappe's EXIF strip only runs for `image/jpeg`.

**To `hrms-fullstack-engineer`, for the strategy gate:** the two numbers to re-measure on
dev are the `<img>` count on a first paint of Positions (OPS-38) and the same count on the
table view. My figures are 16 and 215. If either is wrong, OPS-19 and OPS-21 change, and
nothing else does.

### Before I handed this over

1. **Commands:** every command behind a number above was **run by me** today, read-only,
   except the `X-Accel-Redirect` line in OPS-17, which is **quoted from the code** and not
   exercised.
2. **Numbers:** measured today on the PPJ local copy unless the row says estimate. Byte
   sizes for photos are estimates — no photograph exists to measure.
3. **No deploy command appears in this section.** §5 is where those belong, and they will be
   marked for your approval.
4. **No rollback is named here** for the same reason.
5. **What breaks at the wrong moment:** the table's ~125 requests, if HR opens it during the
   9 a.m. punch burst (§3.3). That is OPS-19.
6. **Nothing left behind.** No container, no file in the bench, no site setting changed.
   Three read-only MySQL queries, three timed `curl` loops inside the existing container,
   one `python -c` to read Pillow's version, and `gh secret list` (names only).
7. **No secret, and no path to one, appears above.** `BACKUP_BUCKET`'s **existence** is
   reported; its value was never read.
8. **Every recommendation is phrased as advice, and every Decision column is blank.**

---

## §4 Strategy — 31 October 2026

Advice only. Every row ends in a **Decision** column that is yours, left blank. **No
command in this section was run by me against dev or production, and none will be.**

Read `00-impact-analysis.md` (938 lines, today) before this section. §1 and §3 above are
not reopened; where a measurement I took today changes one of my own earlier numbers, I
say so in the row.

**What I did today, so you can judge the evidence:** read `deploy/nginx.conf`,
`deploy/Dockerfile`, `deploy/compose/*.yml`, `.github/workflows/{deploy,build-image,ci}.yml`,
`REHEARSAL.md`, `DEPLOYMENT_RUNBOOK.md` and six `scripts/check_*` files in this worktree;
ran four read-only measurements inside the existing `hrlocal-bench` container (Pillow
timings, one `EXPLAIN`, `bench restore --help`, `bench version`); and ran two read-only
`gh api` calls listing image tags. Nothing was written anywhere. Nothing was left behind.

### Answer first

**No P0. Four things at the top, two of which delete work.**

1. **I agree with the engineer's option (c), and I can now give the logging reason as a
   measurement rather than an argument.** I confirmed independently that
   `deploy/nginx.conf` sets **no `log_format`**, so nginx uses its default `combined`
   format, which carries `$request` — the whole request line including the query string —
   and `access_log off` appears on only three locations (`/healthz`, and `/assets/` in both
   server blocks: lines 125, 213, 416). I also found something that was not in the
   engineer's trace and that makes option (c) safe rather than merely better: **Frappe's
   error snapshot redacts any `form_dict` key whose name contains `key`, `token`, `secret`,
   `password`, `passwd` or `pwd`** (`frappe/utils/logger.py:115-134`, read in the running
   image today). `web_form_request_key` contains `key`, so a token posted in the **body**
   under that exact name appears as `********` in Error Log. And `frappe.monitor` records
   `frappe.request.path`, which excludes the query string, and is not enabled anyway. **So
   with option (c) there is no place left on our side where the token is written down.**
   The one condition: **keep the parameter named `web_form_request_key`.** Rename it to
   `invite` or `code` and the redaction silently stops working. **OPS-39.**

2. **Two deletions, and the second is mine to offer.** Option (c) plus our own token-checked
   upload endpoint means **`allow_guests_to_upload_files` never has to be switched on at
   all.** It stays `0`, the allow-list stays empty, and the site-wide guest-upload hole is
   never opened — not even for a minute. My own OPS-25 asked for both values to be set in
   one change; **with option (c) the right change is no change**, and AC-103/AC-104 become
   "assert both are still off", which is a cheaper and stronger test. **OPS-40.** The other
   deletion is the spec's ⚠ DECISION E: I measured it, and the `File`-row answer wins, so
   there is **no custom field on `Employee`, no `after_migrate` installer and no migration**
   (**OPS-43**).

3. **The rollback for every risky part of this slice needs no deploy, and that is worth
   saying out loud because the NFR budget asks for it** (`nfr-budget.md` §3: *"Rollback
   ≤ 15 min, feature-flagged where possible — no deploy required to disable a feature"*).
   Faces disappear if no photo exists. The documents section shows nothing while **no
   document type is ticked**, and the ticked list ships **empty**. The form ships **off**
   and cannot be switched on without a retention period. **Three levers, all data, all
   instant, none needing a release.** That is the best property of this design and nobody
   has written it down yet.

4. **Bad news, and it is small but it is a measurement against the spec.** The spec sets a
   guard of **"p95 ≤ 50 KB" for the stored 512 px photo**. I measured the pipeline today:
   **a worst-case detailed source at 512 px / quality 82 comes out at 82 KB**, not 30–60 KB.
   A real face will usually be inside 30–60 KB; a busy background will not. **The parameters
   do not guarantee the guard.** Keep 512/82 — the numbers are right — and make 50 KB a
   figure we record rather than an assertion that fails the build on an unlucky photograph.
   **OPS-42.** The good news from the same measurement: **the 48 px copy is 0.4–0.7 KB, not
   2–3 KB**, so first paint is **~10 KB of faces, not 48 KB**. The design is cheaper than
   anyone has claimed.

### 4.1 Where I agree with the engineer, and where I do not

Plainly, because silent divergence is how teams ship the wrong thing confidently.

| # | The engineer's position | My view |
|---|---|---|
| 1 | **§0.1 option (c)** — Frappe's `Web Form Request` as the token store, our own hardened page, token in the fragment, posted in the body | **Agree, and it is the one I would pick on logging alone.** I confirmed the access-log finding myself and added the redaction finding above. A fragment is never sent to the server at all, so there is nothing to log, nothing in `Referer` (browsers strip the fragment from `Referer`, whatever our `Referrer-Policy: strict-origin-when-cross-origin` at `nginx.conf:172` does), and nothing for me to have to clean out of a log later. **I cannot clean a log.** The nginx container's logs are not even size-capped — see OPS-51 |
| 2 | **§0.5 no `has_permission` hook, on `File` or on `Employee`** | **Agree, without reservation.** It is the right call for a reason that is mine as well as his: a hook on `Employee` would run inside every one of the 20 endpoints in his §0.2, including `hrms.api.get_all_employees` with `limit=999999`. That is a per-row Python call on an unbounded read, in a site with **8 gunicorn slots**. It would be the most expensive thing in this slice and it would buy a gate that still does not cover the file URL |
| 3 | **§0.2 twenty surfaces, not ten** | **Agree.** Not my artifact to change, and it changes nothing I recommend, but it does change one operational fact: `send_work_anniversary_reminders = 1` on dev means **photo URLs go out in email**. Mail is a path I own at release time. See the watch list, OPS-49 |
| 4 | **§4.3's disagreement with my OPS-5** (settings keys in `settings.py`, **not** a Check on `Employee Document Type`) | **He is right and I withdraw OPS-5.** His reason is a permission row, not taste: `Employee Document Type` ships `write: 1` to HR Manager, who **is** the DTC Positions audience, so a Check there would let the audience widen its own view. `ACCESS_GRANTING` gives System-Manager-only, a logged refusal and a `Version` row for free. Rung 2 either way; his rung 2 is the safe one |
| 5 | **§4.3's partial disagreement with my OPS-25** (the upload endpoint must be ours whichever form is used) | **Agree, and I go further** — see point 2 of the answer. With our own endpoint the global switch stays off, which is better than setting it safely |
| 6 | **§8's build order** (photo first, documents fifth, pre-onboarding last) | **Agree with the order.** Two changes, both mine: **(a)** his step 5 gate "OPS-31's remaining two" is overtaken by your decision — documents ship with the rest, and the restore proof runs **in parallel during the build**, not as a gate (OPS-46). **(b)** I would add one thing to step 1: the photo upload is the first thing in this product to do ~0.25 s of CPU inside a user's request (measured, §4.8). It is fine, and it belongs in the implementation notes so the next person does not discover it in a flame graph |
| 7 | **§3's "Performance: degrades, bounded on purpose"** | **Agree, and after today's measurements I would say "degrades less than we thought".** First paint is ~10 KB of faces. The table at ~125 requests is still the number to bound, and OPS-19 is still the answer |
| 8 | **§10 item 7 "no migration, no patch, no backfill"** | **Confirmed, with one correction that makes it more true, not less.** §4.5 |
| 9 | **§11 item 6 "nothing added to `ci.yml`"** | **Confirmed for `ci.yml` itself. But three existing gates will fail unless a file moves with the code**, and one of them (`EXPECTED_BROWSER_TESTS`) fails the build by design. §4.6 |
| 10 | **§0.6 `portal.js` had 83 commits in 14 days; the hot-file table should name it** | **Agree the table is stale, and it is not this slice's to fix.** §4.6, OPS-50 |
| 11 | **§12 Q1, the two `064-old-*` worktrees** | **Not mine to answer, and I will not guess.** One ops observation only: `git worktree list` shows **120 worktrees**. That is disk and confusion on your machine, not on any server, and clearing it is a decision, not a chore |

**Nothing in the impact analysis is something I would block.** There is no P0 and no P1
disagreement between us.

### 4.2 Install order

**Nothing is installed.** No new Frappe app, no new module, no new workspace, no new
container, no new service, no new volume, no new broker, no new dependency.
`.claude/context/new-frappe-app-checklist.md` **does not apply to this slice** — I read it
to be sure, and its rows are about an app the image would have to fetch, patch and upgrade
for ever. There is none here.

What arrives, in the order it must arrive:

| # | What | Where it comes from | Needs |
|---|---|---|---|
| 1 | Code — endpoints, `portal.js`, `panels.css`, HTML parts, one `hooks.py` line | the image, built by `build-image.yml` on push | nothing but the normal deploy |
| 2 | Two fields on `Alvoraa Photo Access Log`, one new DocType | DocType JSON in `alvoraa_portal`, synced by `bench --site all migrate` | `migrate=true`, which **every branch deploy already sets** (`deploy.yml:159`) |
| 3 | Four settings keys | `DefaultValue` rows written when a System Manager uses the settings card | nothing at deploy time. **They start unset, which is the off state** |
| 4 | `max_file_size = 5` | **a System Settings value, set by hand, per site** | **your explicit word** — a dev-stage and then a production-stage action, not part of a push (OPS-52) |
| 5 | Document types ticked | HR, per tenant, after the release | your word per tenant. **Empty = the documents section shows nothing** |
| 6 | A retention period, then the form switched on | HR, per tenant | your word, and counsel's answer first |

**The order that matters is 1 → 2 → 4 → 5 → 6, and only steps 1 and 2 are a deploy.**
Everything else is data, done afterwards, reversible in seconds, and each one is yours.

### 4.3 Image and Compose changes

**None. Confirmed by reading the files rather than remembering them.**

| Question | Answer | How I know |
|---|---|---|
| New Python dependency? | **No.** Pillow **12.3.0** is already in the image | `./env/bin/python` inside `hrlocal-bench`, today. The slice refuses HEIC rather than adding `pillow-heif`, which is the right trade: a new image codec is a thing to patch for ever |
| New npm dependency? | **No.** No new bundle; the new code goes into `portal.js`, which is a plain static file, not a build target | `deploy/Dockerfile:282` already builds `alvoraa_portal` |
| Dockerfile change? | **No** | Nothing is fetched, nothing is installed, no `ARG` moves |
| Compose change? | **No.** No new service, no new volume, no new port, no change to 4 workers × 2 threads | `docker-compose.app.yml`, read today |
| Image size or build time? | **Unchanged to within noise.** A few hundred KB of text in an ~11 GB image | Estimate, from the size of the diff-to-be |
| nginx change? | **No, and this is the one I would defend hardest.** OPS-17 and OPS-27 hold. I re-read the two things that could have forced one, and neither does. **(a)** The `location ~ ^/(hrms-employee\|…)?$` block at lines 326 and 500 only controls **gzip** — it and `location /` proxy identically, and the security headers are set at **server** level (lines 169-173, 370-373). So the new public page inherits the headers and correctly goes out **uncompressed**, which is what the BREACH rule wants for a page carrying a token. **(b)** `location /api/` already rate-limits every `/api/method/...` call at **120 r/m per IP, burst 30** (lines 292-293, 489-490), which covers the form's endpoints and our upload endpoint | `deploy/nginx.conf`, read today |

**So the one file that can take production down is not touched, and the deploy's own nginx
gate (`scripts/check_nginx_parses.sh`, run twice in `deploy.yml`) has nothing to catch.**

### 4.4 Version pinning

| What | Position |
|---|---|
| **Frappe and ERPNext** | Pinned: `FRAPPE_TAG=v16.35.0`, `ERPNEXT_TAG=v16.36.0` (`deploy/Dockerfile:50-51`, set by ALV-156 / slice 055 at commit `3153eb9c`, 27 Sep). **Both `origin/dev` and `origin/main` carry that pin** — checked with `git merge-base --is-ancestor`. `build-image.yml` passes **no `build-args`**, on purpose, so the Dockerfile's values are what ships. `scripts/check_version_pins.py` runs in CI and fails a pin set back to a branch name |
| **This slice** | **Changes no pin, and should not.** Raising a framework pin to get a feature is a decision of its own, and we need none: the feature already exists in the pinned version |
| **⚠ The one gap, and it is cheap to close** | The engineer verified `Web Form Request` in **`hrlocal-bench`, which runs Frappe v16.33.1** — I confirmed the version myself (`frappe/__init__.py`, and `git describe` → `v16.33.1`). **Dev and production run images built with `v16.35.0`.** Two patch releases apart. The feature is older than both, so it will be there; what I cannot promise from v16.33.1 is that `get_web_form_request()` and `accept(..., web_form_request_key=…)` have the **same signature** in v16.35.0. **OPS-41** |
| **Everything else in the image** | Already pinned to tags or full commits — india_compliance, crm, whatsapp, payments, lms, telephony, helpdesk. No change |

### 4.5 Migration, patch and backfill risk

**The engineer is right: no migration, no patch, no backfill. I confirm it, and I found one
thing that makes it more true than his analysis claimed.**

| Claim | My verdict |
|---|---|
| **No patch, `patches.txt` untouched** | **Confirmed.** There is nothing to convert. 0 photos at PPJ (measured, §1), 0 on dev with 363 active employees (measured by you), 0 known at DTC. A patch for data that does not exist is banned by `no-over-engineering.md` §2 |
| **No backfill** | **Confirmed, and it can never be needed**, because the renderer falls back thumbnail → photo → initials (OPS-13). A photo with no thumbnail shows the photo |
| **No schema change to `Employee`** | **Confirmed — and I measured the thing that could have broken it.** The spec's ⚠ DECISION E left open whether the 48 px URL lives in a `File` row or a custom field, on the grounds that a per-person `File` lookup might defeat OPS-6's batching. **It does not.** `tabFile` carries a composite index `attached_to_doctype_attached_to_name_index (attached_to_doctype, attached_to_name)` — read today — so one batched read over 403 employee ids is index-covered. Measured: the whole statement, with a 403-value `IN` list, **13.4 ms** on the local bench. One extra statement, flat in headcount. **So the `File` row wins: no custom field, no `after_migrate` installer, no migration.** OPS-43 |
| **The two new fields on `Alvoraa Photo Access Log`** | **Safe.** `bench migrate` adds two nullable columns to a small table. And the spec's "make `checkin` optional" is a **no-op**: I read the JSON and `checkin` has **no `reqd`** today. Nothing is being relaxed, so nothing can be tightened back |
| **The one new DocType** | **Safe.** A new table, no Guest permission row, nothing else reads it. The only genuinely one-way thing in this slice is the data it will eventually hold, not its schema |
| **Does any of it run twice safely?** | Yes. DocType sync is declarative; the settings keys are `DefaultValue` writes. **There is no imperative migration step at all**, which is why there is nothing to undo at the schema level — see the rollback table |
| **Where the real risk sits instead** | **In the three CI scripts that name `#pos-editor`** (the engineer's §6). That is a test-integrity risk, not a data risk, and his three rules are the right answer. I have nothing to add except that it must be **one commit**, as he says |

**What breaks if this lands at the wrong moment.** Nothing new. The only new write path
inside a deploy window is the photo upload, which is a user action, and the deploy already
wraps `migrate` in maintenance mode. The 26 October lesson still applies unchanged: the
deploy pause refuses biometric posts for about a minute. This slice does not make that worse.

### 4.6 CI gates — three must change with the code, and I still want none added

**`ci.yml` itself needs no new step, and I am not asking for one.** But three existing
gates will fail unless a file moves with the code, and saying so now is the difference
between a five-minute fix and a confusing red build at 11 p.m.

| Gate | What it will do | What must change with the code |
|---|---|---|
| **`scripts/run_dom_tests.js`** (`ci.yml:235-238`) | **Fails the build by design** when a new `*_test.js` appears. It compares the files on disk against its own `RUN` list, and then against `EXPECTED_BROWSER_TESTS = 19` (line 122) | Add each new DOM test to `RUN` **and raise the number**, with the slice named in the comment, as every previous slice did. **This is the gate working.** And per the engineer's §6 trap: OPS-21's face-count assertion must live in a case that does **not** inherit `check_positions_tree.js:1244-1246`'s `POS_NAMES_SHOWN = 1000` override, or it passes for the wrong reason |
| **`scripts/check_portal_assets_gate.py`** (`ci.yml:221-224`) | Reads `hrms-employee.html`, finds every `/assets/alvoraa_portal/...` it loads, and **fails if `deploy.yml`'s "Portal assets must be served" step does not name it** | **Only if the slice adds a new css or js file.** The plan puts everything in `portal.js` and `panels.css`, which are already named, so **nothing changes**. If that changes, `hrms-employee.html` and `deploy.yml` move in the **same commit** |
| **`scripts/check_api_paths.py --max 0`** (`ci.yml:86-87`) | Every dotted path the front end calls must resolve to a real whitelisted function. Zero tolerance | Nothing to do, as long as each new endpoint is whitelisted before the JS that calls it lands |
| `check_scope_traps.py`, `check_tag_balance.py`, `check_undefined_js.js`, `check_portal_trays.js`, `check_brand_spelling.py`, `check_design_system.py` | All already run and all already cover this ground | Nothing. The engineer's plan is written against them |
| **The deploy's own gates** | nginx parse (twice), disk ≥ 25 GB, `--with-files` backup, asset materialisation, smoke test, **the three portal asset files**, workers alive | Nothing. All pass unchanged |

**One gap this slice creates that no gate watches: the new public page.**
`check_portal_assets_gate.py` looks **only** at `hrms-employee.html`. If the joiner's page
loads an `/assets/alvoraa_portal/...` file and that file 404s, **the joiner sees a dead form
and nothing appears in any log** — the exact failure shape slice 034 built that gate for, on
the one page used by people who cannot ring our helpdesk. The cheap answer is the one the
engineer already chose: **no external asset, everything inline on that page.** If that
changes, add the page to the gate's `PAGES` tuple and to the deploy's asset step together.
**OPS-44.**

**The hot-file table.** `parallel-work.md` §6 names `hrms-employee.html` as "the most-changed
file" and sets exactly the right rule — own block, own prefix, one line in `switchPanel()`,
do not re-indent. Slice 034 moved the script **out** of that page into `portal.js`, so the
rule now names the wrong file while the right one takes 83 commits a fortnight. **The table
should say `portal.js` and `panels.css`. It should not be changed by this slice**, because
that same table's last row says `.claude/` is not part of a feature slice — a rule I am not
going to break in order to improve it. **OPS-50: a one-line change of its own, on `dev`,
whenever you want it.**

### 4.7 The `assets.json` question — the final answer

**No step. The pipeline does it. Unchanged from §3 OPS-36, and I re-read the code to be
sure.**

`scripts/refresh_bench_files.sh` copies every bundle directory first and writes
`assets.json` **last** (lines 53-67, read today), and the `?v=` on every portal file comes
from `get_build_version()`, which is that file's modified time (`www/hrms_employee.py:28` →
`hrms-employee.html:46, 47, 75`). A new image carries a new `assets.json`, so **a real
deploy bumps the version by itself.**

**The 28 October lesson still bites in exactly two places, and neither is in this release
plan:** a manual `docker cp` onto a bench, and a hotfix applied by hand. If anyone does
either during this slice, the bump is theirs to do.

### 4.8 What I measured today that changes a number in the spec

All inside the existing `hrlocal-bench` container, 31 October 2026. Pillow **12.3.0**.
Synthetic images only — **no photograph of a person exists anywhere to measure**, so the
source is deliberately the worst case: full-colour noise, which is the hardest thing JPEG
has to compress.

| What | Measured | The number it replaces | What follows |
|---|---|---|---|
| **512 px / q82 output size**, from a 10.5 MB 4000×3000 noisy source | **82 KB** | spec §19: "about 30–60 KB", **guard p95 ≤ 50 KB** | A real face will usually land in 30–60 KB. A busy one will not. **The guard is not guaranteed by the parameters.** OPS-42 |
| **48 px / q82 output size** | **0.4–0.7 KB** | the design and `07` §3.2: "2–3 KB" | **Better than claimed.** First paint of 16 faces is **~10 KB**, not 48 KB. On slow 3G that is well under a second |
| **Making the 512 px copy** — decode 10.5 MB, resize, re-encode | **~240 ms** (median 243, min 234, 5 runs) | engineer §4.3: "tens of milliseconds" | **A quarter of a second in the uploader's own request, in one of 8 slots.** Fine for one upload. It is not "tens of ms" and the implementation notes should say so |
| **Making the 48 px copy from the stored 512 px file** | **~4 ms** (median 3.9, 7 runs) | — | **This is the `on_update` handler's real cost, and it vindicates OPS-12 with a number: 4 ms inside the request. No queue. No job.** The expensive decode happens once, in the upload |
| **The batched thumbnail lookup**, 403 employee ids, on `attached_to_doctype` + `attached_to_name` | **13.4 ms**, index `attached_to_doctype_attached_to_name_index` present | spec ⚠ DECISION E, unresolved | **Resolved: the `File` row. No custom field, no migration.** OPS-43. Honest caveat: `tabFile` holds 2 rows on this site, so `EXPLAIN` chose a full scan and the 13.4 ms is mostly the cost of **parsing a 403-value `IN` list**. With real rows the index is used; my estimate is the same order, 10–30 ms |
| **A bulk Employee import carrying photographs** (spec E14, ⚠ DECISION K) | **~240 ms per row at the worst case** → **~1 min 40 s for 403 rows**, inside one import job | spec: "tens of milliseconds and bounded" | **I agree with DECISION K — leave it in the request, do not add a queue.** But the release note should say *"importing photographs adds roughly two minutes per 400 rows"*, which is a fact, rather than "will be slow", which is a shrug |
| **`bench version` on our image** | **Exits 1**: `module 'alvoraa_goals' has no attribute '__version__'` | lesson 22, previously read from run logs | **Confirmed at the source.** `deploy.yml`'s readiness loop is `seq 1 60` with `sleep 5`, so it runs all 60 turns: **~5 minutes of pure waiting on every deploy and every rollback.** One line fixes it. **Not this slice.** OPS-48 |

### 4.9 OPS rows — §4

| ID | Recommendation | Why | Cost of ignoring it | Weight | Decision |
|---|---|---|---|---|---|
| OPS-39 | **Take option (c), and keep the parameter named `web_form_request_key`.** Token in the URL fragment, posted in the request body, under that exact name. | Three measured reasons, all mine to own. **(a)** nginx logs the full request line — no `log_format`, so the default `combined`, which carries `$request`; `access_log off` only on `/healthz` and `/assets/`. **(b)** Frappe's error snapshot redacts `form_dict` keys containing `key`/`token`/`secret`/`password`/`passwd`/`pwd` (`frappe/utils/logger.py:121-128`), and `web_form_request_key` matches — **rename it and the redaction stops**. **(c)** A fragment never reaches the server, so it cannot reach a log, a `Referer` or a proxy. `frappe.monitor` logs `request.path` without the query string, and is off. | A live bearer token for a Restricted payload, written into an **uncapped** access log on the server (OPS-51), plus browser history and sync. | **Recommend · P1** | |
| OPS-40 | **With option (c), leave `allow_guests_to_upload_files` at `0` and the allow-list empty — and change AC-103/AC-104 from "set both together" to "assert both are still off".** | Our own token-checked endpoint does the uploads, so the site-wide switch is never needed. **This withdraws the setting half of my own OPS-25.** A test that asserts a hole is shut is stronger than a procedure for opening it carefully. | The first public upload path in the product's history opened site-wide when it did not have to be. | **Recommend · P1** | |
| OPS-41 | **Re-read `web_form.py` and `web_form_request.py` in a container built from `FRAPPE_TAG=v16.35.0` before writing against them.** Cheapest route: read them read-only in the dev container at the start of step 6, or in a throwaway container from the current `dev-<sha>` image. | The engineer verified v16.33.1 (`hrlocal-bench`); **dev and production build v16.35.0** (`Dockerfile:50`, on both `dev` and `main`). The feature predates both, so it will exist — the signature of `get_web_form_request()` and `accept(..., web_form_request_key=…)` is what needs confirming. | Half a day lost to a `TypeError` that only appears on dev, after the code is written. | **Recommend · P2** | |
| OPS-42 | **Keep 512 px / quality 82. Record the stored size; do not assert `≤ 50 KB`.** A ceiling of about 120 KB is a defensible build-failing number; 50 KB is a good target. | Measured today: a worst-case detailed source at 512/82 is **82 KB**. A face on a plain background will be 30–60 KB. The parameters are right; the guard is a guess that reads as proof — the thing `nfr-budget.md` §2 warns about by name. | A red build caused by one employee's photograph, which teaches people to raise the number rather than look. | **Recommend · P2** | |
| OPS-43 | **Store the 48 px URL in a private `File` row, as the spec recommends. Resolve ⚠ DECISION E that way and move on.** | Measured: `tabFile` has a composite index on `(attached_to_doctype, attached_to_name)`; one batched lookup over 403 ids is **13.4 ms**, one extra statement, flat in headcount. **So it does not defeat OPS-6's batching**, which was the only reason a custom field was on the table. It also keeps "no schema change, no installer, no migration" true. | A column on the HR master, an installer that must be safe to run twice, and a migration — for 13 ms. | **Recommend · P2** | |
| OPS-44 | **Keep the joiner's page free of `/assets/` files — inline its css and js.** If that cannot be done, add the page to `check_portal_assets_gate.py`'s `PAGES` **and** to `deploy.yml`'s "Portal assets must be served" step, in the same commit. | That gate reads **only** `hrms-employee.html`. A 404 on a file the joiner's page needs gives a dead form with **nothing in any log** — the failure slice 034 built the gate for, on the one page used by people who cannot ring our helpdesk. | A public form that renders and does nothing, discovered by a joiner. | **Recommend · P1** | |
| OPS-45 | **Every new DOM test goes into `run_dom_tests.js`'s `RUN` list and raises `EXPECTED_BROWSER_TESTS` (19 today), in the same commit**, with the slice named in the comment. And OPS-21's face-count case must not inherit the harness's `POS_NAMES_SHOWN = 1000` override. | The runner fails the build when its list and the files on disk disagree — deliberately. The override trap is the engineer's §6 finding, and it is the difference between a real assertion and one that passes at 1000 names per box. | A red build that looks like a bug, or worse, a green assertion that proves nothing. | **Recommend · P1** | |
| OPS-46 | **Prove one `--with-files` restore on dev while the build is happening, not as a gate in front of it** — per your decision that documents ship with the rest. Commands in §4.10.1, for you to approve. | OPS-31's first condition is now met (**111 GB free, 43% used**, measured by you). This is the second. `BACKUP_BUCKET` is still **not set** (measured, §3), so the pre-deploy tarball on the same disk is the only copy of an uploaded document — and `REHEARSAL.md` has **never** exercised a files restore: its §5 restores a database dump only. | Priority rule 1. The first identity document a joiner uploads would live in one place, and we would be guessing that we can get it back. | **Recommend · P1** | |
| OPS-47 | **Write the rollback tag down from the pin file at the moment of the deploy, never from memory.** `cat .image.dev.env` / `.image.env` on the server **before** the release, and put the value in the release note. | **Fact, 31 Oct:** the newest production image in `alvoraa-app` is `prod-3618269` (28 Oct 22:09 UTC); before it, `prod-0aa8385`. **That will have moved by the time this ships.** `prod-latest` moves too, so it is not a rollback target. 135 tagged versions exist in the package, so a real tag will be there — but name the one that is actually running. | A rollback that pulls the wrong release, or a tag that is not in the package it is pulled from (lesson 20). | **Recommend · P1** | |
| OPS-48 | **One line in `alvoraa_goals/alvoraa_goals/__init__.py`: `__version__ = "0.0.1"`. Not in this slice — a change of its own, whenever you want it.** | **Measured today:** `bench version` exits 1 on our image (`module 'alvoraa_goals' has no attribute '__version__'`), so `deploy.yml`'s readiness loop runs all 60 turns at 5 s each: **about 5 minutes wasted on every deploy and every rollback.** `alvoraa_portal` has `__version__`; `alvoraa_goals` has an empty `__init__.py`. | Five minutes of every rollback, during the window where every minute is the one that matters, for ever. | **Consider · P2** | |
| OPS-49 | **Watch five things after the release, with the thresholds in §4.11. Build nothing new for them.** | Four of the five come from data we already have; the fifth is an hourly check that already runs. A public write path and ~400 new private files are both new shapes of failure, and neither is watched today. | A forwarded invite link used by strangers, or photo URLs going out in anniversary mail, noticed by a customer first. | **Recommend · P2** | |
| OPS-50 | **Update `parallel-work.md` §6's hot-file row to name `portal.js` and `panels.css` — in a separate one-line change on `dev`, not inside this slice.** | The rule in that row is right; the filename is three slices out of date. **83 commits in 14 days on `portal.js`, 46 on `panels.css`** (the engineer's count). The same table says `.claude/` is not part of a feature slice, so this slice must not touch it. | The next three sessions collide in the file nobody was warned about. | **Recommend · P3** | |
| OPS-51 | **FYI, pre-existing, not this slice's to fix: the nginx container has no log size cap.** The 50 MB × 3 limit lives in the `x-app` block (`docker-compose.app.yml:49-53`); nginx defines its own service without it (line 318). So nginx's access log grows unbounded on the disk that hit 100% on 10 September. | It is the log the whole option (c) argument is about — I cannot clean it, cap it or redact it. Worth knowing before anyone proposes putting a secret anywhere near a URL. | Nothing today (111 GB free). It is one more unbounded writer on a partition that has already failed once. | **FYI · P3** | |
| OPS-52 | **`max_file_size = 5` is a per-site setting change, set by hand, with your word — once on dev, later on production. Verify it from outside afterwards.** Commands in §4.10. | Measured 0 on both PPJ and dev → Frappe's 25 MB fallback, while nginx allows 50 MB. **Site-wide: it applies to every upload on the site, not only documents.** You have accepted that (engineer's Q6). | 25 MB per row in one of 8 worker slots on demand, and in every backup. | **Recommend · P1** | |
| OPS-53 | **FYI: nothing in this slice goes on a queue except the one daily erase job the spec already names.** No worker count change, no new queue, no cache, no bucket, no CDN, no container. Still true from §1 and §3, and now with a measurement behind it: the 48 px copy is **4 ms** inside the request. | `no-over-engineering.md` §2. A queue would have needed a measured number, and there is none. | — | **FYI · P4** | |

### 4.10 The release plan — local → dev → main

**Every command below is written for you to approve and run, or to approve for someone to
run. I have run none of them against dev or production, and I will not.**

#### Stage 1 — local, during the build

| # | Step | Command | Who |
|---|---|---|---|
| L1 | The whole suite once at the end, not per step | `bench --site test_site run-tests --app alvoraa_portal`, then `--app hrms` — **read both batch summaries** (tailing the output hides a whole batch) | engineer |
| L2 | The script gates, all local, no bench needed | `python scripts/check_app_integrity.py` · `python scripts/check_scope_traps.py` · `python scripts/check_api_paths.py --max 0` · `python scripts/check_portal_assets_gate.py` · `node scripts/run_dom_tests.js` | engineer |
| L3 | **The restore proof, in parallel (OPS-46).** Not on the local bench — it needs a real `--with-files` set, so it runs on the server in the **rehearsal** project, which `REHEARSAL.md` §1 isolates by `COMPOSE_PROJECT_NAME=rehearsal` | §4.10.1 | **for you to approve** |

#### 4.10.1 The restore proof — for you to approve, never run by me

`REHEARSAL.md` §5 restores a **database dump only**. A files restore has never been done
here, so this is new work and these commands are **quoted, not exercised**. `bench restore`
does take the two flags — I read its `--help` in the running image today:
`--with-public-files <tar>` and `--with-private-files <tar>`.

```bash
# On the server. Read-only against dev; everything else lands in the `rehearsal`
# project, which has its OWN sites volume. Confirm that before anything else.
cd /var/www/html/hr-app/deploy/compose

# 1. a backup of dev that INCLUDES the files. Note the three paths it prints.
docker exec devstack-backend-1 bash -lc \
  "cd /home/frappe/frappe-bench && bench --site dev.alvoraa.co backup --with-files"

# 2. start an isolated rehearsal stack on the tag dev is running
cp ../envs/dev.env.example rehearsal.env       # then edit KINEXUS_IMAGE=<the dev-<sha> tag>
COMPOSE_PROJECT_NAME=rehearsal \
  docker compose --env-file rehearsal.env -f docker-compose.app.yml up -d configurator backend
docker volume ls | grep rehearsal              # MUST show rehearsal_sites, and nothing live

# 3. new site, then restore the database AND both file tarballs
REH=rehearsal-backend-1
docker exec $REH bash -lc "cd /home/frappe/frappe-bench && bench new-site rehearsal.alvoraa.co \
    --db-root-password '<DB_ROOT_PASSWORD>' --admin-password '<pick-one>' --no-mariadb-socket"
docker cp <dump>.sql.gz        $REH:/tmp/dump.sql.gz
docker cp <files>.tar          $REH:/tmp/public-files.tar
docker cp <private-files>.tar  $REH:/tmp/private-files.tar
docker exec $REH bash -lc "cd /home/frappe/frappe-bench && bench --site rehearsal.alvoraa.co \
    --force restore /tmp/dump.sql.gz \
    --with-public-files /tmp/public-files.tar \
    --with-private-files /tmp/private-files.tar \
    --db-root-password '<DB_ROOT_PASSWORD>'"

# 4. the proof. A row count is not proof - look at a private file's BYTES.
docker exec $REH bash -lc \
  "ls -l /home/frappe/frappe-bench/sites/rehearsal.alvoraa.co/private/files | head"

# 5. tear it down. The -v is safe ONLY because the project is `rehearsal`.
COMPOSE_PROJECT_NAME=rehearsal docker compose --env-file rehearsal.env \
  -f docker-compose.app.yml down -v
docker volume ls | grep rehearsal              # expect nothing
rm rehearsal.env
```

**Write down the date, the tag, how long step 3 took, and whether any file was missing.**
That record is what a security questionnaire asks for, and `nfr-budget.md` §3 asks for it
quarterly. **If it fails, the documents part still does not need holding back** — tick no
document type and the section shows nothing. That is the lever, and it needs no deploy.

#### Stage 2 — dev

**Your word first.** Passing tests is not permission.

| # | Step | Command or check | Marked |
|---|---|---|---|
| D1 | Read the pin **before** anything, so the rollback tag is a fact, not a memory | `cat /var/www/html/hr-app/deploy/compose/.image.dev.env` | **for you to approve** |
| D2 | Push once, as one batch | `git push origin dev` | **for you to approve** |
| D3 | Watch the automatic Deploy. **Lesson 14: `workflow_run` runs `main`'s copy of the workflow.** Nothing in this slice changes `deploy.yml`, so the automatic run is the right one. If `deploy.yml` ever does change, exercise dev's copy by hand: `gh workflow run Deploy --ref dev` | — | — |
| D4 | **Prove the landing three ways, not one.** A green deploy of an old tag hides everything | the pin file holds the new `dev-<sha>`; **every** app container on `devstack` reports that same tag (`docker compose ps`); and one changed line is present in the container's own copy of `portal.js` | **for you to approve** |
| D5 | **OPS-38, still the most valuable single check in this slice:** open Positions on `dev` and count `<img class="av">` on first paint. Expected **16**. Nobody has ever rendered this chart | browser, read-only | — |
| D6 | Count the faces on the table view the same way. Expected **215** rows' worth, bounded by OPS-19's observer to roughly the first 25 | browser, read-only | — |
| D7 | **OPS-52:** set the file-size cap, then verify it from outside | `bench --site dev.alvoraa.co set-config -p max_file_size 5`, then try a 6 MB upload and read the refusal in the browser | **for you to approve** |
| D8 | Upload **one** photograph and time it. Expect about 0.25 s of server work (§4.8). Confirm the 48 px `File` row appeared, and read its size | — | **for you to approve** |
| D9 | Leave every document type **unticked** and the form **off**. Confirm the drawer shows no Documents section | browser | — |

#### Stage 3 — main

**Your word again, after you have used dev.**

| # | Step | Command or check | Marked |
|---|---|---|---|
| M1 | Read production's pin and write the tag into the release note | `cat /var/www/html/hr-app/deploy/compose/.image.env` | **for you to approve** |
| M2 | Merge and push | on `main`: `git fetch origin && git merge --ff-only dev`, then `git push origin main` | **for you to approve** |
| M3 | The deploy runs with `migrate=true` inside maintenance mode. **Expect the ~1-minute pause to refuse biometric posts**, and the ~5 minutes of `bench version` waiting (OPS-48) | — | — |
| M4 | Prove the landing the same three ways as D4, on the `compose` project | — | **for you to approve** |
| M5 | The deploy's own gates do the rest: smoke test, the three portal asset files, workers alive. **If "Portal assets must be served" fails, do not announce the release** — the workflow says so itself | — | — |
| M6 | `max_file_size = 5` on each production site, verified from outside | as D7, per site | **for you to approve** |
| M7 | Nothing else is switched on. Document types stay unticked and the form stays off until you say otherwise, per tenant | — | **yours** |

#### Rollback

| Situation | What to do | How long |
|---|---|---|
| **Code only, no migration ran** | Actions → Deploy → Run workflow: `environment: <dev\|production>`, `image_tag: <the tag read at D1/M1>`, `run_migrations: false`, `image_package: alvoraa-app` | **~2 minutes of work, plus the pull, plus ~5 minutes of `bench version` waiting.** Measured basis: 6 min 54 s on dev and 7 min 09 s on production (22 Sep run logs), and today's confirmation that `bench version` still exits 1 |
| **The migration ran** | **There is nothing to undo at the schema level** — this slice has no patch and no data rewrite (§4.5). Two nullable columns and one new table are harmless to leave behind. **So: redeploy the previous tag with migrations off, and leave the schema alone.** Do **not** restore a backup for this slice; it would throw away real work for no gain | as above |
| **One part of the slice misbehaves** | **No deploy.** Untick the document types; clear the ticked field list; leave the form off; an employee removes their own photo. Three levers, all data | **seconds** |
| **The tag is not in `alvoraa-app`** | It will be — 135 tagged versions, newest `prod-3618269` and `dev-e9dcf69` today. Only if a tag is genuinely absent, and only per `docs/runbooks/2026-09-private-image-package.md`, is `image_package: hr-app` the answer — the old public package, which is to be deleted | — |

### 4.11 What to watch after the release, and at what number

Five things. **Nothing new is built for any of them.**

| # | What | Threshold that means "look now" | Where it comes from |
|---|---|---|---|
| 1 | **Submissions vs invite links issued** (OPS-28) | **submissions > links issued**, on any day; or **one token with more than 6 uploads** | Two counts on the new DocType. An invariant, not a guessed rate |
| 2 | **Error Log rows from the thumbnail handler** | **more than about 5 in a day**, or any row that is not an unreadable image | Error Log. No alarm — the symptom is a missing face and HR reports it (OPS-34) |
| 3 | **Free disk** | Already alarmed hourly: `check_workers.sh` **warns below 40 GB, fails below 20 GB**, run by `worker-health.yml` against both stacks. **111 GB free today** | Already running. Nothing to add |
| 4 | **The files tree, per tenant, read once per release** | **above about 5 GB for one tenant** — the point at which the pre-deploy `--with-files` tarball starts to matter against the deploy's 25 GB gate | `du -sh` inside the backend container, at release time only |
| 5 | **Photo URLs in outbound mail** | **Any** anniversary or birthday mail carrying a `/private/files/` URL to a colleague. `send_work_anniversary_reminders = 1` on dev today (your measurement); `send_birthday_reminders = 0` | New because the photos are new. It is the engineer's §0.2 finding landing in a path I own. One look at the Email Queue after the first photographs exist |

**Capacity.** Unchanged: 4 workers × 2 threads = **8 concurrent requests** for the whole
site. First paint of the chart is now **~32 requests, of which 16 are half-kilobyte faces**
— about 10 KB and well under a second of worker time. The table's ~125 is still the one
bounded by OPS-19. An upload costs about 0.25 s of CPU, so **442 joiners all uploading
within an hour is roughly 110 seconds of total CPU**, spread out, which is nothing. **I am
not asking for more workers, and no measured number asks for them.**

### 4.12 Subtract pass

Read back once asking only: *what can I delete and still meet the requirement?*

**Removed on this pass — six things:**

- **My own OPS-5.** Withdrawn in favour of SEC-5, on the engineer's permission-row argument.
  One fewer competing recommendation for the analyst to reconcile.
- **The setting half of my own OPS-25.** Option (c) plus our own upload endpoint means the
  guest-upload switch is never turned on, so a careful procedure for turning it on is dead
  weight. Replaced by "assert it is still off", which is cheaper and stronger.
- **A page-weight CI gate.** The third time I have written and deleted this. Measured first
  paint is ~10 KB of faces; no number asks for a gate.
- **A `Cache-Control` recommendation for `/private/files/`.** Still not worth touching the
  shared nginx file for 16 requests of half a kilobyte.
- **A files-tree size alarm.** Reduced to one reading per release (watch item 4). The hourly
  disk alarm already covers the dangerous case.
- **A proposal to fix the `bench version` waste inside this slice.** It is a one-line change
  in another app and it is not this slice's business. It survives only as OPS-48, for you to
  decide separately.

**Added that does not already exist in the repo: nothing.** Every recommendation in §4 is a
change to a file that is already there, a command for you to run, or a withdrawal of
something I asked for earlier.

### 4.13 Known gaps, labelled

- **Intentional trade-off:** the document file URL is still gated only by the parent
  Employee's read permission (R1). The engineer proved no hook closes it; you have accepted
  it; the tripwire has an owner. Nothing in infrastructure improves on that at a
  proportionate cost.
- **Temporary debt:** private files are served by Python with no browser caching
  (OPS-17, OPS-18). Removed by `X-Accel-Redirect`, in its own slice, when a measured number
  asks for it. Today's numbers do not.
- **Temporary debt:** `BACKUP_BUCKET` unset, so the only copy of an uploaded document sits
  on one disk with a backup at most one deploy old. Removed by a recorded decision, not by
  this slice. The restore proof (OPS-46) is what makes the single copy honest rather than
  hoped.
- **Acceptable simplification:** no monitoring for the thumbnail hook (OPS-34), and no alarm
  for the four new numbers beyond the invariant in watch item 1.
- **Ops debt, not this slice:** the uncapped nginx log (OPS-51), the 5-minute `bench version`
  wait (OPS-48), the stale hot-file table (OPS-50), 120 worktrees, and `portal.js` at
  1.12 MB.
- **Nothing in this section is dangerous debt.** The one item that was — documents shipping
  with no proved restore — is answered by your decision plus OPS-46 running in parallel, and
  by the fact that an unticked list shows nothing.

### 4.14 Escalations

**One, and it is small, and it is yours.**

> **Decision needed:** whether `max_file_size = 5` is set on **production** as part of this
> release, or afterwards.
> **Context:** measured `0` on both PPJ and dev, so Frappe's 25 MB fallback applies while
> nginx allows a 50 MB body. The setting is **site-wide** and applies to every upload on
> the site, not only to documents. You have already accepted the number itself.
> **Conflict:** correctness of the release (priority 4) against a configuration change on
> production made in the same window as a code release (priorities 1 and 3).
> **Who is affected:** anyone uploading anything on that site, including surfaces this slice
> does not touch.
> **Options:** **(a)** set it on dev at D7 and on production at M6, in the same window —
> **my recommendation**, because the document endpoint's memory cost depends on it and the
> release is when attention is on the site; **(b)** set it on production a day later, once
> the release is proved; **(c)** leave it at 25 MB and accept the endpoint's worst case.
> **Risk if it waits:** low, while no document type is ticked. It becomes real the moment
> one is.
> **Owner:** you. It changes a live site's configuration.

Everything else in §4 is advice on work that has not started.

### 4.15 What I could not check

- **Anything on production.** No command above was run against it. The disk figure (111 GB),
  the dev row counts and the DTC statements are **yours**, used as given.
- **Whether `v16.35.0` has the same Web Form Request signature as `v16.33.1`.** I read
  v16.33.1 in `hrlocal-bench`. That is OPS-41.
- **The real size of a photograph of a person at 512 px / q82.** None exists anywhere. My
  82 KB is a worst-case synthetic; 30–60 KB is the estimate for a real face.
- **Queueing under load.** The local bench is a single-process development server, so every
  statement about 8 slots is arithmetic on a per-request figure.
- **Whether the files restore in §4.10.1 works. It has never been done here.** The commands
  are quoted from `bench restore --help`, which I did read in the running image. That is
  precisely why OPS-46 exists.
- **How large the nginx access log currently is.** That is on the server.

### 4.16 Handoff note

**To you, at the strategy gate:** I would approve this strategy. There is no P0 and nothing
I would block. The two things I would change before a line is written are both subtractions:
**take option (c) and keep the parameter named `web_form_request_key`** (OPS-39), and
**leave the guest-upload switch off rather than setting it carefully** (OPS-40). The one
open decision I own is in §4.14, and it is about when a file-size cap lands on production.

**To `hrms-fullstack-engineer`:** four of your numbers change, all in my §4.8, and two of
them are in your favour. The 48 px copy is **4 ms and about half a kilobyte**, not "tens of
ms and 2–3 KB" — that is the number that justifies OPS-12 having no queue. The 512 px copy
costs **~240 ms**, not tens of ms, and it belongs in the implementation notes. ⚠ DECISION E
is **resolved by measurement in favour of the `File` row** (13.4 ms, index-covered), which
keeps "no migration" true. And the thumbnail guard needs one more clause:
**`has_value_changed` returns `True` whenever there is no previous document**
(`frappe/model/document.py:699-706`, read today), so it is `True` on every insert —
including every Employee created during tenant provisioning. Guard on
**`doc.has_value_changed("image") and doc.image`**, or the handler runs on every new
employee who has no photograph.

**To `hrms-test-automation-engineer`:** three of mine are testable and one is a trap.
AC-103/AC-104 should become "both guest-upload values are still off" (OPS-40). The stored
photo size should be **recorded, with a ceiling of about 120 KB**, not asserted at 50 KB
(OPS-42). Every new DOM test must be added to `run_dom_tests.js`'s `RUN` list **and**
`EXPECTED_BROWSER_TESTS` raised from 19, in the same commit. The trap is the harness's own
`POS_NAMES_SHOWN = 1000` override at `check_positions_tree.js:1244-1246`.

**To `hrms-technofunctional-reviewer` and `hrms-security-privacy-engineer`, for the review
round:** the one logging fact worth carrying into the security review is that Frappe's error
snapshot redacts `form_dict` keys containing `key`, `token`, `secret`, `password`, `passwd`
or `pwd` — and nothing else. **The parameter name is a control.** A reviewer should check
that it has not been renamed for tidiness.

### Before I handed this over

1. **Commands:** every number in §4.8 came from a command **I ran** today, read-only, inside
   the existing `hrlocal-bench` container. Every command in §4.10 is **quoted for you to
   approve** and was **not** run. The files-restore flags are quoted from
   `bench restore --help`, which I did run.
2. **Numbers:** measured today where the row says measured; the rest are estimates and say
   so. The disk, dev and DTC figures are yours and are attributed to you.
3. **Stacks, sites, pin files:** dev = project `devstack`, overlay
   `docker-compose.devstack.yml`, pin `.image.dev.env`, host `dev.alvoraa.co`. Production =
   project `compose`, overlay `docker-compose.nginx-multienv.yml`, pin `.image.env`, host
   `alvoraa.co`. Read out of `deploy.yml:108-118` today, not remembered.
4. **Rollback:** written, and its tag is read from the pin file at the time rather than named
   here — because the tag I can see today (`prod-3618269`) will not be the one running when
   this ships. 135 tagged versions exist in `alvoraa-app`.
5. **At the wrong moment:** a mid-deploy upload meets maintenance mode, as every other write
   does. Month-end is payroll, which this slice does not touch. A full disk is alarmed
   hourly and gated before the image pull. **The one new thing: importing 400 photographs
   adds about 100 seconds to that import job.**
6. **Left behind:** nothing. No container created, no file written in the bench, no site
   setting changed. Four read-only measurements inside a container that was already running,
   all in memory, and two read-only `gh api` calls listing image tags.
7. **No secret and no path to one appears above.** `BACKUP_BUCKET`'s **absence** is reported;
   no value was read. The `DB_ROOT_PASSWORD` in §4.10.1 is a `<placeholder>` for you to fill
   from the env file — **I did not read it, and I will not write a generated secret from
   here.**
8. **Every recommendation is advice, and every Decision column is blank.**
