# 008 — Field Check-in — DevOps inputs

**I advise. I decide nothing and I deploy nothing.** Every row below ends in a
Decision column that is yours to fill.

One section per stage. This one is written for a 12-hour window, so it folds the
brief, strategy and release-readiness views into one dated section. Later
sections get added below; nothing here gets rewritten.

---

# §1 · 12 September 2026 — brief, strategy and release readiness

## 🔴 Stop here first — the demo hostname has no certificate

**`ppj.dev.alvoraa.co` has no valid TLS certificate today, and without one the
app cannot work at all.**

Measured, 12 Sep 2026, read-only:

```
certbot certificates
  Certificate Name: alvoraa.co
    Domains: alvoraa.co demo.alvoraa.co dev.alvoraa.co
    Expiry: 2026-11-19 (67 days)

curl https://ppj.dev.alvoraa.co/api/method/ping
  SEC_E_WRONG_PRINCIPAL — the target principal name is incorrect
```

`deploy/nginx.conf` serves `*.dev.alvoraa.co` with the `alvoraa.co`
certificate. A Let's Encrypt certificate for `alvoraa.co` does **not** cover
`ppj.dev.alvoraa.co`, and `*.alvoraa.co` would not either — a wildcard covers
one label only. The nginx file already says so in a comment; it is still true.

Why this is fatal rather than untidy. A phone will not run a service worker,
will not give the page GPS, and will not open the camera unless the page came
over HTTPS from a name the certificate actually covers. Every one of P1, P3 and
P5 in the brief dies on the certificate error page. The user sees a red warning
screen, not the app.

The good news: everything else for that hostname is already in place. Measured
the same minute:

| Check | Result |
|---|---|
| DNS `ppj.dev.alvoraa.co` | resolves to 169.58.108.3 |
| HTTP on that name | 200 from nginx |
| ACME challenge path | served from the webroot (404 on a missing file, which is the right 404) |
| Frappe site exists in devstack | yes — `ppj.dev.alvoraa.co` is in the dev sites list |
| `/api/method/ping` with TLS verification off | 200 |

So it is one command, `deploy/add_tenant_cert.sh ppj.dev.alvoraa.co`, and that
command ends in `nginx -s reload` **on the container that serves production**.
It is a graceful reload of a stateless proxy, so production should not notice —
but it is production, and it is your call. It is OPS-1 below, and it is the
first thing that should happen, because certificate issuance is the only step
in this plan that depends on somebody else's servers.

| ID | Recommendation | Why | Cost of ignoring it | Strength | Decision |
|---|---|---|---|---|---|
| OPS-1 | Add `ppj.dev.alvoraa.co` to the `alvoraa.co` certificate with `deploy/add_tenant_cert.sh`, and do it first | Service worker, geolocation and camera all need a secure context | **There is no demo.** The customer sees a browser security warning | **Recommend — production-touching, needs your approval** | |

---

## 1 · What this change introduces, and what follows from it

| ID | What is new | Performance consequence | Security consequence | Strength | Decision |
|---|---|---|---|---|---|
| OPS-2 | **A guest-accessible web route, hit from phones on mobile networks** | Every punch is a full round trip on a weak link. The budget for an employee-facing phone surface is **p95 ≤ 2.5 s, skeleton within 300 ms** (`nfr-budget.md` §2). A photo upload will not meet 2.5 s unless the photo is small — see §2 | `allow_guest=True` on `register_device`, `field_checkin` and `field_status`. The code already does the three things that make that survivable: rate limit per employee ID, second phone lands as `Pending`, only the SHA-256 of the secret is stored. Recommend the security agent confirms no fourth guest endpoint is added later without the same three | Recommend | |
| OPS-3 | **base64 photo on every punch** | base64 inflates bytes by ~33 %. A 300 KB JPEG is a 400 KB request body. nginx allows 50 MB and gunicorn allows 120 s, so nothing breaks — it is the phone's uplink that decides the wait | The photo must never become a background-job argument. Redis would then hold employees' faces in plain bytes. It is synchronous today; recommend it stays synchronous (lesson 9) | Recommend | |
| OPS-4 | **Private `File` records, growing every working day** | Disk, and backup size. This is §2 | Private is already correct in `_attach_photo` (`is_private: 1`). Keep it. A DPDP retention duty follows — OPS-9 | Recommend | |
| OPS-5 | **A new doctype, `Alvoraa Field Device`** | Negligible. ~400 rows per tenant. `token_hash` and `employee` already carry `search_index: 1`, so the punch-time lookup is an index hit, not a scan. Nothing to fix | It stores a hash, never a secret. Permissions are System Manager / HR Manager / HR User. No Employee-role read — correct | FYI | |
| OPS-6 | **Three custom fields on `Employee Checkin`** | An `ALTER TABLE` per site at migrate. On dev today that table is small, so this is seconds. At PPJ scale after a year (~250,000 rows) it is still a one-off of well under a minute | All three are `read_only: 1, no_copy: 1`. Good | FYI | |
| OPS-7 | **A PWA with a service worker** | A service worker makes the second launch fast. It also makes a bad build permanent if the caching headers are wrong. This is §4 | A service worker is same-origin code with a long life. A stale one keeps talking to an endpoint you have retired | Recommend | |

**Feasibility, plainly:** nothing here is hard to run. The whole slice is
additive — new endpoints, one new table, three new columns, and static files.
There is no new service, no new dependency and no change to anything that
already exists. That is why the rollback in §5 is genuinely cheap, and it is
the best fact about this release.

---

## 2 · Storage growth — the number you asked for

**Short answer: at the photo size I recommend, PPJ costs about 64 MB a day,
1.6 GB a month and 20 GB a year. At the cap the code carries today it would be
1.6 GB a day and about 500 GB a year, which does not fit on the disk.**

**Measured on the server, 12 Sep 2026, read-only:**

| What | Value |
|---|---|
| Root filesystem | 193 GB total, 81 GB used, **112 GB free, 43 % used** |
| `devstack_sites` volume (all dev sites and their files) | **147 MB** |
| All docker local volumes | 2.365 GB |
| Docker images | 73.32 GB, of which 47.49 GB reclaimable |

Context worth keeping in view: this disk hit **100 % full on 2026-09-10** and
killed three deploys in a row. There is room today; there is not room for a
careless photo size.

**The arithmetic.** 400 employees × 2 punches = **800 photos a day**. A working
month is ~26 days, a working year ~313 days. All figures are **estimates**,
based on typical JPEG sizes at the stated resolution — nobody has yet measured a
real photo from a real PPJ phone.

| Photo size | Per day | Per month (26 d) | Per year (313 d) | Verdict |
|---|---|---|---|---|
| 50 KB — 640 px longest edge, quality 0.6 | 40 MB | 1.0 GB | **12.5 GB** | Comfortable |
| **80 KB — 720 px, quality 0.6 (recommended)** | **64 MB** | **1.6 GB** | **20 GB** | Recommended |
| 250 KB — 1280 px, quality 0.8 | 200 MB | 5.2 GB | 63 GB | Over half the free disk in a year, for one tenant |
| 2 MB — **the cap in the code today** (`MAX_PHOTO_BYTES`) | 1.6 GB | 42 GB | **500 GB** | Does not fit. 112 GB free |

Add roughly 250,000 `File` rows and 250,000 `Employee Checkin` rows per tenant
per year — about 100 MB of database. Not a problem; worth knowing.

**The multiplier nobody costs in:** the deploy pipeline runs
`bench --site all backup --with-files` before every non-dev deploy
(`.github/workflows/deploy.yml`). Private files go into that tar. At 20 GB of
photos, every production deploy writes a 20 GB+ backup, and the offsite sync
carries it. At the 2 MB cap it would be 500 GB. **The photo cap is a backup
decision as much as a disk decision.**

| ID | Recommendation | Why | Cost of ignoring it | Strength | Decision |
|---|---|---|---|---|---|
| OPS-8 | **Downscale on the phone to 720 px longest edge, JPEG quality 0.6, and lower `MAX_PHOTO_BYTES` in `field_checkin.py` from 2 MB to 400 KB** | Keeps PPJ at ~20 GB a year instead of ~500 GB, and keeps the upload inside the 2.5 s phone budget on a weak link | The disk that filled on 10 Sep fills again, and every deploy backup gets huge | **Recommend** | |
| OPS-8b | **When the photo is over the cap, refuse the punch with a clear message rather than dropping the photo** | `_attach_photo` currently logs and returns, so the punch is recorded with no evidence and nobody finds out. The whole point of the photo is that a supervisor can check it | Silent loss of the one piece of evidence the feature exists to capture | Recommend | |
| OPS-9 | **A retention/purge job is needed before PPJ go-live, not before the demo** | A demo makes tens of photos — storage is irrelevant this week. But photos of employees' faces kept for ever is a DPDP retention problem, and the brief already flags it in §6 | A finding on the first security review, and 20 GB a year that never shrinks | Recommend — **after** the demo | |
| OPS-9b | When it is built: daily job on the **`long`** queue, default 90 days, configurable in Org Settings, deletes the `File` and blanks `alvoraa_checkin_photo`, keeps the punch | The punch is the attendance record and must survive. Only the photo expires | An erasure path that quietly deletes attendance history | Consider | |

**Dev volume for the demo itself: no concern.** 112 GB free, and a demo will add
a few megabytes.

---

## 3 · Image and Compose impact — nothing changes, and that matters

**You are right. No new Python package. No `deploy/Dockerfile` change. No
Compose change. No new service.**

Verified on the running dev container, 12 Sep 2026:

```
docker exec devstack-backend-1 env/bin/pip show Pillow
  Name: pillow   Version: 12.3.0
  Python 3.14.7
```

- `field_checkin.py` imports `base64`, `binascii`, `hashlib`, `secrets` and
  `frappe`. All standard library or already present.
- No `dlib`, no OpenCV, no face model. That is what the brief's §5 rejection of
  `face_app` bought us.
- Pillow is already in the image via Frappe, so any image handling the File
  doctype does is already covered. Nothing in this slice needs it directly.
- The new doctype and the new page live inside `alvoraa_portal`, which the
  Dockerfile already `COPY`s and installs editable. They ship automatically.

**What this materially changes about the deploy:**

| ID | Consequence | Strength | Decision |
|---|---|---|---|
| OPS-10 | The image still has to be **rebuilt** — it bakes the app code — but no new layer is added, so the GitHub Actions cache stays warm. **Estimate 20–40 minutes**, based on the 90-minute CI timeout and `cache-from: type=gha` in `build-image.yml`. **I have not timed this build. Time it once and write the number down** | FYI | |
| OPS-11 | **Serve the field app as a Frappe website page** (`alvoraa_portal/.../www/field-checkin.html` plus a `website_route_rules` entry) rather than as a new bundled Vue app. Two reasons: no new `bench build` step, so no new way for the image build to fail in the 12-hour window; and the page's headers come from the backend, so **`deploy/nginx.conf` never has to be touched** — and that file is bind-mounted and shared with production | **Recommend** | |
| OPS-12 | **`deploy/nginx.conf` changes are not free.** They require a reload of `compose-nginx-1`, which serves production. Avoid one if you can; if you cannot, it is the same approval as OPS-1 | Recommend | |

---

## 4 · The PWA's caching and the service worker

**The trap is real and it is already in `deploy/nginx.conf`:**

```nginx
location ^~ /assets/ {
    alias /devstack-sites/assets/;
    expires     30d;
    add_header  Cache-Control "public, immutable";
}
```

**Anything served under `/assets/` is frozen on the phone for 30 days and marked
`immutable`, which tells the browser not even to ask.** Frappe HR's own PWA
lives at `/assets/hrms/frontend/` — its `sw.js` and `manifest.webmanifest` sit
under that rule today. If the field app's service worker is put there, a phone
that installs it during the demo keeps that exact build for up to a month, and
there is no way to push a fix to it. `^~` also beats regex locations, so you
cannot simply add a regex override; it needs an exact-match `location =` block,
which means editing the shared nginx file.

**So the cheapest correct answer is not to put the service worker under
`/assets/`.** Serve it from a Frappe route, where `location /` proxies to the
backend and the backend sets the headers.

**The headers each file needs:**

| File | `Cache-Control` | `Content-Type` | Note |
|---|---|---|---|
| `sw.js` (the service worker) | `no-cache, max-age=0, must-revalidate` | `application/javascript` | Browsers cap service-worker script caching at 24 h anyway, but `immutable` is honoured — do not rely on the cap. Register with `{updateViaCache: 'none'}` |
| `manifest.webmanifest` | `no-cache` (or `max-age=3600`) | **`application/manifest+json`** | nginx's default `mime.types` has **no** entry for `.webmanifest`, so serving it off disk gives `application/octet-stream`. Serving it through Frappe lets you set the type |
| The app shell HTML | `no-store` | `text/html` | Otherwise a phone keeps yesterday's shell. `driver_portal.py` already sets `context.no_cache = 1` — do the same |
| Hashed JS/CSS (`app.a1b2c3.js`) | `public, max-age=31536000, immutable` | | Safe **only** if the filename changes when the content does |
| Icons | `public, max-age=604800` | `image/png` | |

Also, in the service worker itself: call `self.skipWaiting()` and
`clients.claim()`, and **never cache a POST to `/api/method/...`**. A cached
punch response is an attendance record that never happened.

**Three more things in that file that would bite:**

| ID | Finding | Strength | Decision |
|---|---|---|---|
| OPS-13 | **`add_header` does not inherit.** If anyone adds an `add_header` inside a new nested `location`, nginx silently drops `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy` and the rest for that location. If `nginx.conf` is edited at all, **repeat the whole security header block** | Recommend | |
| OPS-14 | **`Permissions-Policy "geolocation=(self), camera=()"` on the `alvoraa.co` block disables the camera API.** The `*.dev.alvoraa.co` block has no `Permissions-Policy` at all, so **the demo is unaffected** — but the same app on production would find `getUserMedia()` blocked. Recommend phase 1 uses `<input type="file" accept="image/*" capture="environment">` instead of `getUserMedia`. A file input is not gated by that header, it works on iOS Safari, and it removes the need to change a production header later | **Recommend** | |
| OPS-15 | **Rate limit: `/api/` is capped at 120 requests per minute per source IP, burst 30.** Field staff on one mobile carrier can share one NAT address. A handful of demo phones is fine. **400 people punching between 08:55 and 09:05 through carrier NAT is not** — they would get HTTP 429 and think the app is broken. Raise before PPJ go-live, not before the demo | Recommend — after the demo | |
| OPS-16 | `client_max_body_size 50m` and `proxy_read_timeout 120s` are both comfortable for a 400 KB photo. Nothing to change | FYI | |

---

## 5 · The release plan for a 12-hour window

**Read this first:** the dev deploy on this repo is **automatic**. A push to
`dev` triggers `Build Image`, and `Deploy` runs when that build completes. You
do not run a deploy command — **the push to `dev` IS the deploy.** Treat
`git push origin dev` as the deploy approval, because it is one.

One more thing that surprises people: `Deploy` is triggered by `Build Image`,
not by `CI`. **A failing CI job does not stop the deploy.** That removes a risk
from today's window and removes a safety net at the same time.

### Phase A — start the certificate now, in parallel with everything else

This is the long pole. It depends on Let's Encrypt, not on us.

```bash
# A1 · dry run first — it costs nothing and does not burn a rate-limit slot
#      ⚠️ FOR THE USER TO APPROVE — the real run touches production nginx
cd /var/www/html/hr-app
deploy/add_tenant_cert.sh ppj.dev.alvoraa.co --dry-run
```

```bash
# A2 · the real issuance. This ends in `nginx -t` + `nginx -s reload`
#      on compose-nginx-1, which SERVES PRODUCTION.
#      ⚠️ FOR THE USER TO APPROVE — production-touching
deploy/add_tenant_cert.sh ppj.dev.alvoraa.co
```

A reload is graceful: existing connections finish, no restart, no dropped
requests. It is still production. Limits worth knowing: a Let's Encrypt
certificate holds at most 100 names, and "duplicate certificate" is capped at
5 per week — so do not run this repeatedly to experiment.

```bash
# A3 · verify — read-only, safe
curl -sS -o /dev/null -w '%{http_code}\n' https://ppj.dev.alvoraa.co/api/method/ping
# expect 200, with no certificate warning
```

### Phase B — local, on `hrlocal-bench` (the bulk of the 12 hours)

```bash
# B1 · ⚠️ FOR THE USER TO APPROVE — bench migrate on the local bench
docker exec hrlocal-bench bash -lc \
  "cd /home/frappe/frappe-bench && bench --site <local site> migrate" > /tmp/migrate.log 2>&1
```

```bash
# B2 · ⚠️ FOR THE USER TO APPROVE — bench build, then materialise assets
docker exec hrlocal-bench bash -lc \
  "cd /home/frappe/frappe-bench && bench build --app alvoraa_portal"
docker exec hrlocal-bench bash -lc "bash /workspace/materialise_assets.sh"
```

`bench build` inside a live container re-creates the asset symlinks in the sites
volume — `materialise_assets.sh` is what turns them back into real files.
`deploy/Dockerfile` §4b says so in its own words.

```bash
# B3 · if you ran `bench use`, restart the bench or requests keep hitting
#      the old site.  ⚠️ FOR THE USER TO APPROVE
docker restart hrlocal-bench
```

```bash
# B4 · run the CI gates locally BEFORE pushing. Read-only, no approval needed.
python scripts/check_app_integrity.py
python scripts/check_api_paths.py --max 2
node   scripts/check_portal_handlers.js
node   scripts/check_undefined_js.js
ruff check alvoraa_portal --config hrms/pyproject.toml
```

Two of those scan **every** `.html` in `alvoraa_portal/alvoraa_portal/www`
automatically, so a new `field-checkin.html` is covered whether you ask for it
or not. `check_design_system.py` uses an explicit page list and will **not** see
the new page — so the field app is not held to the design-token count unless
somebody adds it to `PAGES`. That is a deliberate call for you to make later,
not today.

### Phase C — the migration dry run (`REHEARSAL.md`), ~30 minutes

Do this before pushing. It is the only way to see the migration hit real PPJ
data without putting it on the demo site.

```bash
# C1 · take a dump of the demo site. READ-ONLY on the dev stack.
#      ⚠️ FOR THE USER TO APPROVE — it is a dev-stage action
docker exec devstack-backend-1 bash -lc \
  "cd /home/frappe/frappe-bench && bench --site ppj.dev.alvoraa.co backup"
```

```bash
# C2 · a THROWAWAY stack. The project name is what keeps it off the real volume.
#      ⚠️ FOR THE USER TO APPROVE
cd /var/www/html/hr-app/deploy/compose
COMPOSE_PROJECT_NAME=rehearsal docker compose \
  -f docker-compose.app.yml --env-file rehearsal.env up -d configurator backend
docker volume ls | grep rehearsal      # expect rehearsal_sites. If not, STOP.
```

```bash
# C3 · restore, then migrate, capturing BOTH streams.
#      `bench execute` prints its own fallback on stdout and hides the real
#      error — never trust a bare run.  ⚠️ FOR THE USER TO APPROVE
docker exec rehearsal-backend-1 bash -lc \
  "cd /home/frappe/frappe-bench && bench --site rehearsal.alvoraa.co --force restore /tmp/dump.sql.gz --db-root-password '<pw>'" > /tmp/restore.log 2>&1

docker exec rehearsal-backend-1 bash -lc \
  "cd /home/frappe/frappe-bench && bench --site rehearsal.alvoraa.co execute alvoraa_goals.deploy_utils.premigrate_rename" > /tmp/pre.log 2>&1

docker exec rehearsal-backend-1 bash -lc \
  "cd /home/frappe/frappe-bench && bench --site rehearsal.alvoraa.co migrate" > /tmp/mig.log 2>&1
```

**What to look for in `/tmp/mig.log`:**

- `Orphaned DocType(s) found:` — `Mode of Payment` is expected and pre-existing.
  **Any Alvoraa doctype in that list is a stop.**
- How long the migrate took. That is your maintenance window on the real deploy.

**Then verify, in the rehearsal console:**

```python
frappe.db.exists("DocType", "Alvoraa Field Device")                      # True
[frappe.db.exists("Custom Field", {"dt": "Employee Checkin", "fieldname": f})
 for f in ("alvoraa_checkin_photo", "alvoraa_gps_accuracy", "alvoraa_checkin_offline")]
frappe.db.count("Employee Checkin")    # must match the live ppj site
```

```bash
# C4 · tear the rehearsal down when done.  ⚠️ FOR THE USER TO APPROVE
COMPOSE_PROJECT_NAME=rehearsal docker compose -f docker-compose.app.yml down -v
```

### Phase D — take a restore point, because a dev deploy does not

**Bad news, stated plainly: the deploy pipeline skips the backup step on dev.**
`deploy.yml` guards it with `if: needs.plan.outputs.environment != 'dev'`. So
pushing to `dev` migrates `ppj.dev.alvoraa.co` **with no restore point taken**.

```bash
# D1 · ⚠️ FOR THE USER TO APPROVE — take one by hand first
docker exec devstack-backend-1 bash -lc \
  "cd /home/frappe/frappe-bench && bench --site ppj.dev.alvoraa.co backup --with-files"
# note the path it prints — this is your rollback point
```

### Phase E — the deploy

```bash
# E1 · fetch and rebase first. More than one session works this repo.
git fetch origin dev && git rebase origin/dev
# read the incoming diff before you build it
```

```bash
# E2 · THE DEPLOY.  ⚠️ FOR THE USER TO APPROVE — this push IS the dev deploy
git push origin dev
```

Then wait. Build ~20–40 min (**estimate**), deploy ~5–10 min after it.

### Immediately after the deploy — check these six things

All read-only.

```bash
# 1 · EVERY container in the dev stack on the SAME image tag.
#     A worker left behind on the old image is how tenant provisioning
#     broke on 2026-08-23.
docker ps --format '{{.Names}}\t{{.Image}}' | grep devstack
#     all six must show the SAME dev-<sha>, and it must be the new one

# 2 · worker-long is alive. It is the queue that carries the slow work.
docker ps --format '{{.Names}}\t{{.Status}}' | grep devstack-worker-long

# 3 · the dev stack is pinned by its OWN file
cat /var/www/html/hr-app/deploy/compose/.image.dev.env    # must be dev-<sha>

# 4 · nginx was restarted after the container swap (the workflow does this).
#     If it was not, every dev site 502s from a healthy backend.
curl -sS -o /dev/null -w '%{http_code}\n' https://ppj.dev.alvoraa.co/api/method/ping

# 5 · the three columns actually landed on the demo site — open
#     Employee Checkin in the desk and look for Check-in Photo,
#     GPS Accuracy (m) and Recorded Offline

# 6 · nobody left in maintenance mode. Three dev deploys in a row have
#     finished 'success' with one tenant stuck at 503.
for s in ppj.dev.alvoraa.co dev.alvoraa.co allabouthr.dev.alvoraa.co; do
  curl -sS -o /dev/null -w "$s %{http_code}\n" https://$s/api/method/ping
done
```

Then, by hand, the thing no check covers: **register a real phone, take a real
photo, punch, and see the row appear in `Employee Checkin`.**

### Rollback — and why it is cheap here

**Everything this slice adds is additive.** A new doctype, three new columns,
new endpoints, a new page. Nothing existing is altered or dropped. So rolling
the image back leaves the extra table and columns sitting there unused, which is
harmless. **You do not need to restore the database to roll back.** That is
unusual, and it is worth knowing at 2 a.m.

```
Actions → Deploy → Run workflow
  environment    : dev
  image_tag      : dev-3830ed3        ← what dev runs today, 12 Sep 2026
  run_migrations : false
```

Time: about 2 minutes plus the image pull. That tag is inside the retention
window — the pipeline keeps the three most recent `dev-` tags.

If the demo breaks in the room and there is no time even for that: **the fastest
rollback is to stop showing the app.** The reception-machine attendance story on
`ppj.dev.alvoraa.co` is unaffected by any of this.

### What to watch during the demo itself

| Watch | Where | What bad looks like |
|---|---|---|
| Backend errors | `docker logs -f devstack-backend-1` | Any 500 on `/api/method/alvoraa_portal.field_checkin.*` |
| Rate limiting | same log | HTTP 429 — several phones behind one office wifi or one carrier NAT |
| The punches | `Employee Checkin` list on `ppj.dev.alvoraa.co` | Rows missing, or present with no photo |
| Disk | `df -h /` | Should not move. If it does, something is wrong with the photo cap |
| Geofence | the message on the phone | It should name the real distance and the real place |

**Have one spare phone already registered and tested before the customer walks
in.** Registration is the step with the most ways to go wrong, and it is the
worst one to debug in front of a customer.

---

## 6 · The traps this repo has already paid for — which ones apply

| # | Lesson | Applies here? | What to do |
|---|---|---|---|
| 1 | **Never hand-list services on `docker compose up`.** A list missing `worker-long` left tenant provisioning queued for an hour | **Yes** | The Deploy workflow already uses a bare `up -d --remove-orphans`. **Do not "help" by naming services.** If anyone runs Compose by hand on this box, bare `up -d` only — `nginx` is kept out of dev by its `never-in-dev` profile |
| 2 | **After a deploy, every app container in a stack reports the same image tag.** A worker on an old image crashed on a new argument | **Yes** | Check 1 in the list above. Today all six dev containers are on `dev-3830ed3` — measured 12 Sep. After the deploy they must all be on the new tag, not five of six |
| 3 | **Each stack pins its own image file.** Dev uses `.image.dev.env` | **Yes** | Check 3 above. Never edit `.image.env` for a dev change — that is production's pin, and it is read when nginx is recreated |
| 4 | **Restart nginx after replacing the backend** or it 502s from a healthy backend | **Yes** | The workflow does it. Verify with check 4. Note it restarts `compose-nginx-1`, which is production's proxy — about two seconds, and it is the one part of a dev deploy production notices |
| 5 | **Health checks must name a site that exists in that stack** (`HEALTH_HOST`) | **Yes** | The dev backend is healthy today, so `HEALTH_HOST` is set correctly in `envs/dev.env`. Do not change it. The compose default is `alvoraa.co`, which does not exist in devstack |
| 6 | **Test on a fresh site built the way CI builds one** | **Yes** | CI builds with `bench install-app` and never migrates. That is exactly why `field_checkin.after_migrate` is wired into **both** `after_migrate` and `after_install` in `hooks.py`. It is correct today — do not remove one half |
| 7 | **Our apps never redefine a Frappe or ERPNext doctype** | **Yes** | `Alvoraa Field Device` is a genuinely new name, and the three fields on `Employee Checkin` are Custom Fields, not a shadow copy of the doctype. Run `scripts/check_app_integrity.py` anyway — step B4 |
| 8 | **`bench execute` swallows the real error** and prints its own fallback | **Yes** | Every `bench execute` in Phase C redirects `> file 2>&1`. Keep it that way |
| 9 | **Secrets never go into job arguments, command lines or logs** | **Yes — the sharpest one here** | The device token and the base64 photo must never become arguments to an enqueued job, because Redis would then hold them. Keep the photo save synchronous. The offline queue (P11) must send the photo in the request body, never via `frappe.enqueue(photo=...)` |
| 10 | **Never hardcode the bench path** — use `frappe.utils.get_bench_path()` | Not yet | No code in this slice touches paths. Watch it if the retention job (OPS-9) writes files |
| 11 | **No fallback secrets** | **Yes** | The device secret must have no default and no "dev mode" bypass. An employee ID on its own must never punch — the brief already says so |
| 12 | **Restart `hrlocal-bench` after `bench use <site>`** | **Yes** | Step B3. Otherwise you will spend an hour testing a site you are not looking at |
| + | **The disk hit 100 % on 2026-09-10** and killed three deploys | **Yes** | 112 GB free today. OPS-8 is what keeps it that way |

---

## Open questions for you

| Question | Why it needs you |
|---|---|
| **Is `deploy/add_tenant_cert.sh ppj.dev.alvoraa.co` approved?** It reloads production's nginx | Nothing in this slice works without it, and it touches production |
| Photo cap — 400 KB server-side, 720 px on the phone? (OPS-8) | Sets the storage and backup cost for the life of the feature |
| Retention period for check-in photos — 90 days? (OPS-9) | A DPDP obligation. It does not block the demo; it does block go-live |
| `<input capture>` rather than `getUserMedia`? (OPS-14) | Avoids changing a production security header later |

---

*Measurements in this section were taken on 12 September 2026 by read-only
commands against the server and the dev stack. Nothing was changed. Every figure
marked "estimate" is arithmetic on typical values, not an observation — and the
photo size is the one worth replacing with a real measurement from a real PPJ
phone as soon as one exists.*
