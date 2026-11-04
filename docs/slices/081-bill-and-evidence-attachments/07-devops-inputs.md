# Slice 081 — DevOps inputs

One section per stage. Never rewrite an earlier section; add a dated follow-up.

---

## §1 · Brief — first look · 3 November 2026

**Read first, because it is the only bad news that could change the brief:
mandatory bills become a business record, and this installation has no copy of
them anywhere but one server disk.** `gh secret list` shows `DEPLOY_HOST`,
`DEPLOY_SSH_KEY`, `DEPLOY_USER` and nothing else — **`BACKUP_BUCKET` is not
set** (Fact, read today). `deploy.yml` L322–328 therefore prints
*"BACKUP_BUCKET not set — backups exist only on the server"* on every deploy,
and Frappe's own `delete_temp_backups(older_than=23)` runs at the **start** of
every `bench backup` (Fact, `frappe/utils/backups.py` L651–662), so yesterday's
backup set is deleted by today's. Today that risk costs the database. From the
day a bill is mandatory it also costs **every expense receipt DTC has**, which
is a tax and audit record, not an app file. See **OPS-1**.

**Second, and it is not in the brief at all: an iPhone cannot upload a photo
through this path today.** Pillow in the running image is 12.3.0 with
**no HEIC support** and `pillow_heif` is not installed (Measured today in
`hrlocal-078`, the current dev image `dev-3830ed3`). HEIC is the iPhone camera
default. On an optional field that is a shrug; on a **mandatory** one it is a
person who cannot file a claim at all. See **OPS-11**.

**The good news, so the design is not over-built:** nginx needs **no change**
(OPS-5), Frappe's own file ceiling needs no change (OPS-6), the compression is
fast enough to run inline (OPS-4), storage growth is small (OPS-2), and the
stale-assets trap is already covered by the deploy (OPS-9). Nothing in this
slice needs a new container, a new job, a queue, object storage or a CDN.

---

### 1 · What I measured, and where

Everything below was run **today, 3 November 2026**, inside the local Docker
bench containers (`hrlocal-078` and `hrlocal-bench`), both on the current dev
image `ghcr.io/…/hr-app:dev-3830ed3`. **I ran nothing against dev or
production.** One attempt to read the server's free disk (read-only `df -h`)
was **blocked by policy** — see "What I could not check".

**Compression (your question 3).** One Pillow call, the `employee_photo.py`
shape: `Image.open` → `convert("RGB")` → `thumbnail((edge, edge), LANCZOS)` →
`save(JPEG, quality=82, optimize=True)`. Source: a synthetic 4032 × 3024
(12 MP) JPEG of **4.28 MB** — the size band a current phone produces. Median of
five runs:

| Long edge | Stored size | Median time | Min–max |
|---|---|---|---|
| 512 (today's profile photo) | 8 KB | **498 ms** | 364–717 ms |
| 1280 | 78 KB | **933 ms** | 850–1401 ms |
| **1600 (my recommendation)** | **145 KB** | **1407 ms** | 1187–1499 ms |
| 2000 | 274 KB | **1623 ms** | 1488–1786 ms |

**Measured**, with one honest caveat: my source is machine-generated and
low-detail, so the **stored sizes are optimistic**. A real photographed bill at
1600 px typically lands at **250–600 KB** `[ESTIMATE]`. The *timings* are not
optimistic — decode of a 12 MP frame dominates them and does not care what the
picture is of.

**The upload path (your question 4).** `deploy/nginx.conf`, read today:
`client_max_body_size 50m` at **both** HTTPS server blocks (L164, L365). The
only tighter caps are three named `location` blocks — the WhatsApp webhook and
`field_checkin` at `1m` (L237, L254, L440, L457) and the device calls at `16k`
(L273, L475). **`/api/method/upload_file` matches none of them**; it falls to
the general `/api/` prefix and so inherits **50 MB**. Frappe's own ceiling:
`frappe/core/api/file.py` L85–91 — System Settings `max_file_size` (MB), else
`conf`, else **25 MB**. On the local site `max_file_size` is **0** and `conf`
has no value (Measured), so **25 MB applies**. A 4–5 MB raw photo and a 3 MB
PDF both pass, with room. **No nginx change, no config change.**

**Serving (your question 5).** `employee_documents_read.open_employee_document`
reads the whole file with `get_content(encodings=[])` and hands it to
`frappe.local.response` (Fact, read the code). Production serves on
**4 gunicorn workers × 2 threads = 8 request slots**, `--timeout 120`
(Fact, `docker-compose.app.yml` L261–263). One file per tap, ≤1 MB (3 MB for a
PDF), is 1 of 8 slots for a few hundred milliseconds. Fine.

**CI (your question on effort).** Measured from `gh run view` on the last six
CI runs: the **Python tests** job ran **63 to 90 minutes**, and the most recent
run's `Run tests` step alone took **85 min 49 s** (03:08:27 → 04:34:16 UTC,
3 Nov) against the job's own `timeout-minutes: 90` plus ~4 minutes of setup
before it. **Headroom to the cap is about four minutes.** This slice's own
image tests cost **seconds**, not minutes (1.4 s per re-encode, Measured). So
081 does not materially worsen CI — but it is being added to a job that is
already within four minutes of being killed by its own timeout, and that is
worth knowing before anyone blames this slice. See **OPS-8**.

**Storage, as far as this installation can tell me (your question 1).**

| What | Number | Label |
|---|---|---|
| Expense claims on the local demo site (`ppj.localhost`) | **0** | Measured |
| Active employees there | 403 | Measured |
| `private/files` on that site | **empty** (4 KB dir) | Measured |
| `private/backups` on that site | 11 MB | Measured |
| Attendance Requests | 1 | Measured |
| Expense claims at DTC | **unknown — production, I may not look** | Unknown |

**So the honest answer to "real numbers from this installation" is that this
installation holds no expense claims and no private files at all.** The only
place a real claim rate exists is DTC, on production. I did not look. The
command to get it is in "For you to decide", and it is a read.

---

### 2 · The storage answer, with the estimate marked as one

Per-claim stored size, using the measured compression and the settled caps:

| Case | Stored | Basis |
|---|---|---|
| Image, 1600 px long edge | **250–600 KB** | `[ESTIMATE]` from the measured 145 KB on a low-detail source |
| Image at the cap | 1 MB | Settled rule |
| PDF | 1–3 MB, average ~1.5 MB | `[ESTIMATE]` |

DTC headcount is **442** (from the project record, 25 Oct). Claims per month is
the number I cannot derive, so here is a band rather than a figure:

| Claims / month `[ESTIMATE]` | Average 400 KB | Worst case (1 MB + 10% PDFs at 3 MB) |
|---|---|---|
| 150 | 60 MB/mo → **0.7 GB/yr** | 180 MB/mo → 2.2 GB/yr |
| 300 (the brief's figure) | 120 MB/mo → **1.4 GB/yr** | 360 MB/mo → 4.3 GB/yr |
| 450 | 180 MB/mo → **2.2 GB/yr** | 540 MB/mo → 6.5 GB/yr |

**Verdict: storage growth is not material and must not shrink the slice.** A
few gigabytes a year, against a deploy gate that wants **25 GB free** and a
warning at 45 GB (Fact, `deploy.yml` L277–291). The brief's kill criterion
*"DevOps shows storage growth that needs a new store or a job"* is **not
triggered** — no object storage, no CDN, no retention job needed for volume.

**What grows and does matter is the pre-deploy backup.** Every deploy runs
`bench --site all backup --with-files` (Fact, `deploy.yml` L312) and that tars
the whole private-files tree for every site. JPEGs do not compress, so the tar
is roughly the data size and the time is throughput-bound: **about 10–20 s per
GB** `[ESTIMATE]`. After a year at the middle band that is **under a minute**
added to each deploy; at the worst band after two years, **2–3 minutes**. Worth
watching, not worth acting on yet.

**Restore, as it actually is.** `bench restore` of the database **plus**
`--with-private-files` from the same backup set, plus the settings merged back
from `site-configs-*.tgz` (Fact, `DEPLOYMENT_RUNBOOK.md` L519, L613–614). The
files are not in the database; a database-only restore brings back claims whose
bills are **gone**, and every approver would see a broken link. That is already
true of employee documents; mandatory bills make it routine.

**The "deploys never refresh the sites volume" trap has no bearing on the
files, and is already fixed for the assets.** Private files live on the named
`sites` volume (Fact, `docker-compose.app.yml` L43, L345) and a deploy never
touches them — which is exactly what you want. Since 23 September the deploy
calls `scripts/refresh_bench_files.sh` before swapping containers, and then
asserts `/assets/alvoraa_portal/js/ess/portal.js` is actually served (Fact,
`deploy.yml` L492–499, L748–757). The new file control lives in that file, so
**that step is the one that makes this slice visible** — it is in place, and
nothing extra is needed.

---

### 3 · The recommendations

Decision column is yours. Priority label is mine.

| ID | Recommendation | Why | Cost of ignoring it | Weight | Decision |
|---|---|---|---|---|---|
| **OPS-1** | **Before the mandatory rule ships, decide where a copy of these files lives off this server.** Either set `BACKUP_BUCKET` (the deploy already syncs to it, `deploy.yml` L322–326 — no code) or accept in writing that bills exist on one disk only | `gh secret list` has no `BACKUP_BUCKET` (Fact), and every `bench backup` deletes backup sets older than 23 hours (Fact). Mandatory means DTC's expense evidence is a tax record held in one place | Disk loss, a bad restore or a wrong `rm` destroys evidence for every claim ever filed. RPO ≤ 1 h and RTO ≤ 4 h in `nfr-budget.md` §3 are not met for files today | **Recommend · P1** | |
| **OPS-2** | **Do not shrink the slice for storage.** Keep one file, keep the caps, no object storage, no CDN, no retention job for volume | 0.7–6.5 GB/year against a 25 GB deploy gate (Measured gate, estimated growth) | Needless cost, and a kill criterion fired on a guess | **Recommend · P3** | |
| **OPS-3** | **Resize long edge 1600 px, JPEG quality 82**, and if the result still exceeds 1 MB, re-encode once at 1280 and once at 1024 before refusing. This is the one number the brief asked DevOps to set | Measured: 1600 px costs 1.4 s and stores 145 KB on a clean source, 250–600 KB `[ESTIMATE]` on a real bill — comfortably inside 1 MB while keeping a printed amount legible. 512 px (today's profile value) is far too small for a bill | Either an unreadable bill (too small) or refusals at the cap (too large). Both land on a driver at a pump | **Recommend · P2** | |
| **OPS-4** | **Run the compression inline, in the request. Do not add a background job** | Measured 1.4 s of CPU on a 4.3 MB 12 MP photo, in this image, on one of 8 request slots; gunicorn's timeout is 120 s. DTC's claim rate is a few an hour, not a few a second | A job queue for a 1.4 s task is a new moving part, and the employee would have to wait for a result they cannot see | **Recommend · P3** | |
| **OPS-5** | **Change nothing in `deploy/nginx.conf`** | Both server blocks already allow 50 MB and `upload_file` is in no capped location (Fact, read today) | **One nginx serves dev and production** from this one file. An unnecessary edit restarts the live proxy for no gain | **Recommend · P1 (as a "do not")** | |
| **OPS-6** | **Do not implement the 1 MB rule as System Settings `max_file_size`.** Enforce it in our own code, after compression. If you want a site-wide ceiling, set it at 10 MB and treat it as its own decision | That setting is site-wide: at 1 MB it would refuse the **raw** 4 MB photo before we ever compress it, and break every other attachment (employee documents chose 5 MB). It is currently 0 → Frappe's 25 MB default (Measured) | Slice 078's outstanding "apply the per-file ceiling" item, done the obvious way, breaks this slice on the day it lands | **Recommend · P1** | |
| **OPS-7** | **One file per tap on the reviewer's queue. No thumbnails, no preloading, no "open all".** Keep the existing stream-and-log pattern | The endpoint reads the whole file into memory in one of 8 slots (Fact). A 20-row queue that preloaded thumbnails would be 20 MB through those slots on one page view | A manager's queue page becomes the slowest page in the product, and the 3G budget of ≤ 2.5 s (`nfr-budget.md` §2) is missed on the surface that matters most | **Recommend · P2** | |
| **OPS-8** | **Raise the Python test job's `timeout-minutes` (or split it) in this slice or before it.** It is a one-line config change | Measured: `Run tests` took 85 min 49 s against a 90-minute job cap, with ~4 minutes of setup ahead of it. The slice's own image tests cost seconds, so 081 is not the cause — but it will be blamed | CI starts failing on a timeout that looks like a test failure, during this slice's build. That costs a day of looking in the wrong place | **Recommend · P2** | |
| **OPS-9** | **Nothing to do for assets — but keep the deploy's `refresh_bench_files.sh` and the portal-asset check in the plan at §5.** They are what make the new file control reach a browser | Fact, read `deploy.yml` L492–499 and L748–757 | The old failure returns: a deploy that "succeeded" while the portal still runs August's JavaScript | **FYI · P3** | |
| **OPS-10** | **One real phone photo committed once as a fixture; generate the rest.** A 12 MP 2.94 MB JPEG generates in **~0.5 s** (Measured), so every size and refusal case can be generated at test time | The brief rightly wants a genuine photo (real EXIF, real camera noise, the HEIC question). That needs one real file. It does not need ten | Either a weak test (all synthetic) or tens of megabytes of binaries in git and in every image build, for ever | **Recommend · P3** | |
| **OPS-11** | **Decide what happens to an iPhone photo before the design gate.** My recommendation: **do not add `pillow_heif`**; refuse an unreadable file in plain words that name what to do, and test one real iPhone upload end to end at the design check | Measured: Pillow 12.3.0, `heif` feature **False**, `pillow_heif` **missing** in the running image. `employee_photo.py`'s own docstring records the same thing. iOS *usually* converts to JPEG when a photo is chosen through a web form, but that is `[ASSUMPTION]` and nobody here has tested it | A mandatory field that an iPhone user cannot satisfy. They cannot file a claim at all, and the message they see today would be a Pillow error | **Recommend · P1** | |
| **OPS-12** | **A per-user upload rate limit on the new path**, reusing `field_app_limits._limited` as the brief already suggests | `upload_file` with `is_private=1` is reachable by any logged-in staff member. Mandatory attachments multiply legitimate traffic, which makes abuse harder to spot | A bored or buggy client fills the sites volume. A full disk is the failure that took production down for nine days on 10 September, and it defeats restart policies | **Recommend · P2** | |
| **OPS-13** | **Say in the spec what deletes these files** — on claim cancellation, on employee erasure, and against which retention clock | Nothing in this slice deletes a file. Storage only grows, and counsel's two retention clocks already bind us | An erasure request we cannot honour, and a "delete my data" answer that is not true. This is the security engineer's D6, flagged from the run side | **Recommend · P2** | |
| **OPS-14** | **Watch the deploy's backup duration once this is live** — it is in the run log already, no new tooling | The pre-deploy backup is the one thing that grows with file volume: ~10–20 s per GB `[ESTIMATE]` | A deploy that quietly gets slower, on top of the ~7 minutes already wasted waiting for `bench version` | **Consider · P3** | |

**Known gaps, labelled the way the engineer labels theirs:**

- **Dangerous debt — escalate now:** no off-server copy of private files
  (OPS-1). It is dangerous *today*; mandatory bills only widen the blast.
- **Acceptable simplification:** compression inline rather than in a job
  (OPS-4), and no HEIC support (OPS-11) **provided** the refusal is honest.
- **Temporary debt:** the CI timeout headroom (OPS-8). Removed by one config
  line.

---

### 4 · Rough run cost

| Item | Cost | Label |
|---|---|---|
| Extra storage, DTC, year one | 0.7–2.2 GB typical; 6.5 GB worst | `[ESTIMATE]` |
| Extra storage, all tenants, year one | under 10 GB | `[ESTIMATE]` |
| New infrastructure | **none** — no container, volume, bucket, CDN or dependency | Inference from the measurements above |
| Added CPU per claim | ~1.4 s once, at filing | Measured |
| Added deploy time | under a minute in year one | `[ESTIMATE]` |
| Off-server backup, if you choose OPS-1 | a few GB of object storage a year; the sync code already exists | `[ESTIMATE]` |

**So the money answer is: this slice costs almost nothing to run. The only
spend it argues for is a backup destination, and that spend was already
overdue.**

---

### 5 · What I could not check

- **Anything on the server.** DTC's claim count, the real `private/files` size
  on production or dev, and the server's free disk. I tried one read-only
  `df -h` over SSH and **it was refused by policy** — correctly. Every figure
  that needed it is marked `[ESTIMATE]`.
- **Whether `max_file_size` is set in System Settings on dev or production.**
  Local is 0. Slice 078 recorded this as still outstanding. **This matters to
  OPS-6** — if someone has already set it to 1 or 5 MB, raw photo uploads break
  before this slice writes a line of code.
- **A real iPhone upload.** OPS-11 rests on a measured absence of HEIC support
  plus an assumption about what Safari sends.
- **A real bill photo's compressed size.** My source was synthetic. The brief's
  own §13 answer — five real bills from a DTC supervisor — is still the right
  first test, and it now has a measured pipeline to run them through.

---

### 6 · For you to decide — three reads, and I have not run them

**These are commands for you, or for someone with your say-so. I ran none of
them.** All three are read-only; none changes a server.

```bash
# 1 · DTC's real claim rate and file volume (production read).
#     Answers the one number this section had to estimate.
ssh <server> "cd /var/www/html/hr-app/deploy/compose && \
  docker compose -f docker-compose.app.yml -f docker-compose.nginx-multienv.yml \
    --env-file ../envs/prod.env --env-file ../envs/.image.env \
  exec -T backend bench --site dtc.alvoraa.co execute frappe.client.get_count \
    --kwargs \"{'doctype':'Expense Claim','filters':{'creation':['>','2026-10-01']}}\""

# 2 · The per-file ceiling that is actually in force on each stack (OPS-6).
#     Run the same shape with --site dev.alvoraa.co for dev.
#     bench execute hides the real error on stdout - capture stderr too.
... bench --site dtc.alvoraa.co execute frappe.client.get_single_value \
      --kwargs "{'doctype':'System Settings','field':'max_file_size'}" 2>&1

# 3 · Free disk and the current sites volume size (the 10 September failure).
ssh <server> "df -h / ; du -sh /var/lib/docker/volumes/compose_sites/_data/*/private/files"
```

**And one decision that is not a command: OPS-1.** Setting `BACKUP_BUCKET`
means choosing a destination and paying for it. The deploy already knows what
to do with it. **My recommendation is to settle it before the mandatory rule
ships, not after** — the moment every claim carries a bill is the moment "it is
only on one disk" stops being survivable.

---

### 7 · Where I disagree with the brief, or make it cheaper

| Brief says | My reading |
|---|---|
| *"If DevOps says storage growth is still material, the fix is a smaller re-encode, not a smaller slice"* | **It is not material.** Keep the slice. OPS-3 sets the width at 1600 px for legibility, not for size |
| Kill criterion: *"DevOps shows storage growth that needs a new store or a job"* | **Not triggered.** No new store, no job |
| §8: *"the per-file ceiling actually applied on dev and then production (slice 078's OPS-24/52, now at 1 MB)"* | **Cheaper and safer not to.** Doing that through System Settings `max_file_size` would refuse the raw photo before compression and break other attachments (OPS-6). The 1 MB rule belongs in our code, after the re-encode |
| §3.2 treats compression as settled reuse | **One thing it does not cover: HEIC.** The reused call cannot open an iPhone photo in this image (OPS-11). Mandatory makes that a blocker rather than a shrug |
| §13: *"The 1 MB stored cap bounds it"* | Agreed, and measured. **What it does not bound is the pre-deploy backup time or the absence of an off-server copy** (OPS-1, OPS-14) |

---

### 8 · Subtract pass

I removed: a background-job design for the compression (measured fast enough
inline); a monitoring recommendation for disk and file growth (the deploy's own
25 GB gate and the run log already carry it — a new alert is a new thing to
maintain); a CDN and object-storage comparison (growth is gigabytes, not
terabytes, so neither needed a paragraph); a per-location `client_max_body_size`
for `upload_file` (the server block already allows 50 MB, and a needless nginx
edit restarts the live proxy); and a nightly file-count check. Fourteen rows is
what survived, and five of them are "change nothing".

**Hand-off checks:** every command in §6 is **quoted, not run**. Every number
is labelled Measured today / `[ESTIMATE]` / Unknown. No deploy command appears
here except as a read for you to approve. **Left behind: nothing** — the three
scratch scripts I copied into `hrlocal-078` and `hrlocal-bench` have been
deleted and the deletion was confirmed; no site setting, container or file in
the bench was changed. **No secret and no path to one appears in this
document.**

---

## §2 · Requirements — operational requirements · 3 November 2026

§1 stands as written. Nothing in it is withdrawn. **One number in it is now
wrong in the slice's favour, and it is the headline of this section.**

**No P0. One P1 is carried, not re-argued: ALV-299** — no off-server copy of
any backup, and each backup deletes the previous set. That ticket came out of
§1/OPS-1 and the decision is Surbhi's. **Everything below assumes the files
live on one disk until ALV-299 is settled**, which is the single biggest reason
OPS-15's tidy-up matters: on one disk, rubbish is not harmless.

---

### 2.1 What the design changed in my figures

**The phone now does the work, so the server's share of it collapses.**
Measured today, 3 November 2026, in `hrlocal-294` on the dev image
`ghcr.io/…/hr-app:dev-3830ed3` (the containers I used this morning had been
stopped by another session; same image):

| What the server re-encodes | In | Out | Median | Range |
|---|---|---|---|---|
| **A device-shrunk 1600 px JPEG — the normal case now** | 546 KB | 546 KB | **46 ms** | 44–51 ms (7 runs) |
| A raw 12 MP photo — the fallback case | 3.0 MB | 546 KB | **529 ms** | 501–613 ms (7 runs) |

Read against §1's 1407 ms for a 4.28 MB source: **the canvas step takes the
server's cost per claim from roughly 0.5–1.4 s down to about 46 ms — a factor
of 10 to 30.** The spread between 529 ms and 1407 ms for "a raw 12 MP photo" is
two different synthetic sources on two containers with the host under different
load; treat the raw path as **0.5–1.5 s** and the device-shrunk path as
**under 100 ms**.

**Three things follow, and one of them is new work for the test engineer.**

1. **OPS-4 stands and is now easy: keep the re-encode inline.** 46 ms in a
   request needs no job, no queue and no worker. At 8 request slots
   (4 gunicorn workers × 2 threads, Fact) the upload path stops being a
   capacity question at any claim rate DTC can produce.
2. **The storage figures in §1 do not change.** What is stored is the output of
   the server's re-encode at 1600/q82, which is what it was before — 546 KB on
   today's source, 250–600 KB on a real bill `[ESTIMATE]`. The caps are
   unchanged, so §1's 0.7–2.2 GB/year typical and 6.5 GB/year worst case stand.
3. **New, and it changes a test rather than the code: the picture is now
   re-encoded twice** — once on the phone, once on the server. Measured: the
   second pass at the same recipe returned 545,951 bytes from 546,000, so size
   barely moves, but **JPEG generation loss does accumulate**. So the
   five-real-bills legibility test (brief §16, design §5) must be run on the
   **device-then-server** output, not on one pass. If the amount is legible
   after one pass and not after two, we would ship the kill criterion
   unnoticed. **OPS-24.**

**Two calls instead of one costs nothing I can measure** — one extra HTTP round
trip of about a kilobyte. What it costs is in the next two rows.

---

### 2.2 The operational requirements

For the business analyst to trace into user stories. Decision column is
Surbhi's. Where an existing design item already covers something I asked for in
§1 (the rate limit, magic bytes, the caps living in our endpoint), I do not
repeat it.

| ID | Requirement | Why | Cost of ignoring it | Weight | Decision |
|---|---|---|---|---|---|
| **OPS-15** | **Something must delete orphan uploads, and it must be a query inside a daily job that already runs — not a new scheduled job, container or queue.** My recommendation: delete `File` rows that are **private**, have **no `attached_to_name`**, came from the expense/regularization upload path, and are **older than 24 hours**; bounded to a few hundred rows per run; log one count line. **Never** touch a file that has a parent, and never one younger than two hours | **Confirmed: nothing tidies these today.** I read `frappe/hooks.py` `scheduler_events` — no Frappe job deletes unattached files. With two calls and a mandatory field, an abandoned claim at a petrol pump leaves a real file on the volume for ever | The sites volume fills with files nobody can see, nobody can reach and no retention clock covers. On one disk (ALV-299) that is the failure that took production down for nine days on 10 September | **Recommend · P1** | |
| **OPS-16** | **Say in the spec what each clock is anchored to.** A kept file's clock runs from **its claim**, not from its upload. An orphan's only clock is OPS-15's window. Both belong in D6, and **the retention story must name which anchor it uses** | The design's §12.1 is right that a file landing first starts a clock earlier. If the clock is anchored to the upload, a file attached to a claim three minutes later inherits an arbitrary start; if nothing is anchored, an orphan has no clock at all | An erasure answer that is not true, and two files on one claim with different expiry dates | **Recommend · P2** | |
| **OPS-17** | **The second call must set `attached_to_doctype` and `attached_to_name` on the `File` row**, and the acceptance criteria must assert it on the stored row, not on the response | Until a file has a parent, Frappe's private-file gate falls back to `owner == user` (the trace is in `employee_documents_read`'s own docstring). So an unparented bill is **invisible to the approver, absent from Desk's sidebar, and unreachable by any sweep that walks the claim** | The slice's WOW moment shows "no bill" to the one person who needs it, and every retention or erasure job built on "the files of this claim" silently misses it | **Recommend · P1** | |
| **OPS-18** | **Every refusal and every server-side failure on this path writes one Error Log or one counted log line, with a reason and no file name.** The reasons, separately countable: no file at submit · over the cap after re-encode · unreadable or HEIC · magic-byte mismatch · rate-limited | **Mandatory means a broken upload path blocks pay-affecting claims.** The daily `health.collect_scheduled` job already pulls each tenant's `errors_24h` to the control plane (Fact, read `health.py`), so a path that throws is visible within a day — **only if it throws rather than swallowing** | A silent failure on the one surface where silence costs a driver his money, found when somebody telephones | **Recommend · P2** | |
| **OPS-19** | **One invariant, read on demand, HR-only, reusing the `joiner_counts` shape from slice 078 (OPS-28). No dashboard, no alert plumbing, no new tool.** Two numbers: **submitted expense claims with no attached file — must be 0**, and **orphan uploads in the last 7 days** | Those two queries catch both failure modes this slice can have: the rule not firing (a claim through some door with no bill) and the path half-failing (people uploading and never filing). The second number is also OPS-15's own health check | Either the mandatory rule quietly stops applying on some door, or people fail at the last step and we never learn. Brief §12 asks for exactly this measure | **Recommend · P2** | |
| **OPS-20** | **No browser beacon for a failed upload, and I recommend against one being added later.** The honest position: when the network drops mid-upload the failure happens on the phone and **we cannot see it, by design**. The orphan count (OPS-19) is the proxy and it is enough | A beacon is a new endpoint, new personal data in transit and a new thing to rate-limit, to learn something we can infer from a count we already have | Somebody builds telemetry for this later and nobody remembers it was declined on purpose | **Recommend · P3 (a "do not")** | |
| **OPS-21** | **nginx stays untouched** (carried from OPS-5). If anybody proposes a per-location cap for `upload_file`, it must pass `scripts/check_nginx_parses.sh` in a throwaway container **before** it goes near a deploy — and whoever proposes it must know **one nginx serves dev and production from one file** | The server block already allows 50 MB, and the upload is now a few hundred KB (Measured) | A dev-only change restarts the live proxy and reconfigures the live site | **Recommend · P1 (a "do not")** | |
| **OPS-22** | **At release, read `System Settings.max_file_size` on dev and on production and confirm it is not 1 or 5.** The caps live in our endpoint (design §12, EC5 — agreed), but a value already set on a stack would refuse the raw photo **before** our code runs | Local reads 0 → Frappe's 25 MB default (Measured). **I have not read dev or production. This requirement rests on an unverified number** — command 2 in §6 | A release that works on local, on CI and on a fresh site, and refuses every upload at DTC | **Recommend · P1** | |
| **OPS-23** | **Raise the Python test job's `timeout-minutes` from 90 to 120 — in its own change, with its own ticket, landing before 081's build starts. Not folded into this slice** | Measured: `Run tests` took 85 min 49 s against a 90-minute cap. 081's own image tests cost **seconds** (46 ms–1.5 s per re-encode), so this slice is not the cause — but it will be the suspect. Keeping it separate keeps the evidence clean | A timeout that reads as a test failure, in the middle of this build, costing a day of looking in the wrong place. I agree it must not be folded in silently | **Recommend · P2** | |
| **OPS-24** | **The legibility test runs on the device-then-server output**, and the one committed real photo goes through both passes (carried and sharpened from OPS-10) | Measured today: the picture is now re-encoded twice. Generation loss is real even though the size barely moves | The kill criterion — "five real bills come back unreadable" — gets tested against something the product never produces | **Recommend · P2** | |
| **OPS-25** | **The iPhone path is a release test, not a code change.** The canvas conversion (design EC4, option a) is the right answer and costs nothing. **Add one real iPhone upload, end to end, to the release-readiness checks** — nobody here has ever run one — and the server backstop must refuse a HEIC that arrives anyway in plain words | Measured in the running image: Pillow 12.3.0, `heif` **False**, `pillow_heif` **missing**. The canvas makes the normal case a JPEG; it does not cover an old browser or a file picked out of a file manager | A mandatory field an iPhone supervisor cannot satisfy, found at UAT by the persona most likely to be in the room | **Recommend · P1** | |
| **OPS-26** | **Capacity: nothing to do.** 8 request slots; 46 ms of CPU per claim in the normal case; a few hundred KB per upload. **The only capacity risk in this slice is on the reviewer's side**, and OPS-7's "one file per tap, no thumbnails, no preloading" already answers it — the design carries it as HQ1 and criterion 21 | Measured today, plus `docker-compose.app.yml` L261–263 (Fact) | A queue page that preloads becomes the slowest page in the product | **FYI · P3** | |

**Known gaps, labelled:**

- **Dangerous debt — escalate:** ALV-299 (no off-server copy). Not mine to
  re-argue; it is why OPS-15 is P1 rather than P3.
- **Acceptable simplification:** no beacon for browser-side upload failures
  (OPS-20); no alerting beyond an on-demand invariant (OPS-19).
- **Temporary debt:** the CI timeout (OPS-23). Removed by one line, in its own
  change.
- **Unverified, and marked as such:** OPS-22 rests on a number I did not read.

---

### 2.3 Release order, and what to check after it lands

**Local → dev → main, and each step is Surbhi's word.** I have run none of
this. Every command below is written for approval.

| | |
|---|---|
| **Migrations** | The attachment half needs **none** — the file is a standard `File` row and no doctype changes. **If the approver role ships in this slice** it brings one Custom Field and therefore a patch; a Custom Field is additive, so a rollback can leave it in place harmlessly |
| **New assets** | **Yes, and this is the step that makes the slice visible.** The file control lives in `portal.js` and the portal CSS. The deploy's `scripts/refresh_bench_files.sh` copies the image's built assets onto the sites volume before containers swap, and a later step asserts `/assets/alvoraa_portal/js/ess/portal.js` is served (Fact, `deploy.yml` L492–499, L748–757). **Without that step the volume keeps the old JavaScript and the form ships with no file control while the deploy reports success** |
| **nginx** | **Untouched.** No restart needed for this slice (OPS-21) |
| **New scheduled work** | One entry in the existing daily job list, for OPS-15. **It only ever runs if the scheduler is alive**, so the post-deploy check must look at the scheduler rather than assume it |
| **Rollback** | Redeploy the previous tag with migrations off. **The tag must exist in the package the server pulls from (`alvoraa-app`)** — confirm that before the release, not during it. Measured previously by others: a deploy or a rollback wastes about 7 minutes waiting on `bench version`; budget for it |

**After it lands on dev — the checks, in order:**

1. The pin file holds the tag you deployed, **and every app container in the
   stack reports that same tag.** A worker left behind on the old image has
   cost this project a day before.
2. `scripts/check_workers.sh` — and **not `docker ps`**. A container can report
   "Up" while its process is dead.
3. The deploy's portal-asset check is green, and then **open the claim form in
   a browser and see the file control.** Asset freshness is the one thing this
   slice cannot be proven without.
4. File one claim with a real photo from a real phone: the picture is shown
   back, the stored file is **under 1 MB**, and the claim's `File` row has
   `attached_to_name` set (OPS-17).
5. File one claim with **no** file and read the server's own sentence on screen.
6. Open the bill as the approver and confirm **no `/private/files/…` URL
   appears** in the network tab.
7. Confirm the scheduler is ticking, then that OPS-15's tidy count appears in
   the job's log the next day — and that **nothing attached was deleted**.
8. Read OPS-19's two numbers. Submitted claims with no file must be **0**.

**Before main:** the same list on dev first, plus the five-real-bills
legibility check through both re-encodes (OPS-24) and one real iPhone upload
(OPS-25). **And a decision on ALV-299**, because the day the rule becomes
mandatory is the day "one disk" stops being survivable.

---

### 2.4 The three read-only commands

**§6's three commands stand exactly as written, and I have still not run any of
them.** Which requirements rest on them:

| Command | What rests on it | If it comes back differently |
|---|---|---|
| 2 · `max_file_size` on dev and production | **OPS-22 — marked unverified** | A value of 1 or 5 refuses uploads at DTC on day one, whatever our endpoint does. **This is the one that turns a requirement into a blocker** |
| 1 · DTC's October claim count | §1's storage band, and OPS-15's 24-hour window only loosely | A much higher rate makes OPS-15 more valuable, not different. No requirement changes |
| 3 · Free disk and volume size | ALV-299's urgency, not a requirement here | Low free disk makes OPS-15 and ALV-299 urgent rather than important |

---

### 2.5 Subtract pass

Removed before handing this over: an alerting design (an email on a failed
upload, a threshold on the orphan count, a health-page tile) — OPS-19's two
on-demand numbers plus the existing daily `errors_24h` pull do the job, and an
alert nobody has agreed to answer is noise; a browser beacon for upload
failures (OPS-20 now records the decision **not** to build it); a dedicated
daily job for the orphan sweep, reduced to one query inside a job that already
runs; a dashboard of claim-attachment rates (brief §12 is measured from counts,
not from a screen); and a capacity model for concurrent uploads, which 46 ms
per claim made pointless. Twelve rows survived, and three of them are "change
nothing".

**Hand-off checks:** every command here is **quoted, not run**. Numbers are
labelled Measured today / `[ESTIMATE]` / Unverified. No deploy command appears
except as a step for Surbhi to approve, and nothing here changes a server.
**Left behind: nothing** — the one scratch script copied into `hrlocal-294` was
deleted and the deletion confirmed; no site setting, container or bench file
was changed, and **no site config file was read** this round. No secret or path
to one appears in this document.
