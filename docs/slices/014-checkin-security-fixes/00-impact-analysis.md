# 014 — Check-in security fixes — impact analysis and strategy

**Status:** analysis and strategy only. No code written, no worktree, no commit, no
bench, no docker. **Waiting for the user's approval** (change process step 3).

Written 2026-09-17 by the full-stack engineer, in the main checkout on branch `dev`
(local `dev` at `8a53522`). The user said "fix the security issue" about DevOps rows
**OPS-19** and **OPS-20** in `docs/slices/013-mobile-app/07-devops-inputs.md` §2.

---

## 0. Read this first

1. **Problem 1 is confirmed by reading.** Anyone can send a made-up `X-Forwarded-For`
   header and Frappe will believe it. Every Frappe limit that counts "per IP" can be
   dodged, a user's "Restrict IP" allow-list can be dodged, and the IP address in
   Frappe's session and login records can be faked. nginx's own limits are safe.
2. **Problem 2 is confirmed by reading, and it is worse than OPS-20 says.** It is not
   only 5xx errors:
   - A **rejected photo** (too big, not a JPEG, will not decode) writes an Error Log
     row on a **normal** request. That row's `metadata` holds the request fields in
     full: the whole photo text, latitude, longitude and accuracy. No crash needed.
   - **On dev, `DEVELOPER_MODE=1`** (`deploy/envs/dev.env.example:35`). In developer
     mode Frappe snapshots **every** error, 4xx included. So every refused punch on dev
     ("too far", "already recorded", "location too vague") writes photo and GPS to the
     Error Log and to the site's `frappe.log`.
   - This breaks **SEC-8** of slice 008, which was marked **Blocking** ("no personal data
     reaches any log … including Frappe's own unhandled-exception logging").
3. **The nginx fix changes production the moment it reaches `dev`.** One nginx serves
   production and dev, and it reads `deploy/nginx.conf` from the server checkout. A dev
   deploy restarts it. **A typing mistake takes every site down.** So the file is tested
   on this PC first, in a throwaway container, and the push needs the user's explicit
   word, at a quiet moment.
4. **Moving DNS to Cloudflare carries its own risk, separate from this fix.** If anyone
   turns Cloudflare's proxy on (the orange cloud) before nginx knows about Cloudflare,
   every visitor will look like a handful of Cloudflare addresses. nginx's login limit
   (5 a minute per address) would then lock out whole companies. The plan below makes
   nginx ready for that, and **the DNS records should stay "DNS only" (grey cloud)**
   until the nginx change is live.
5. **Found while reading, not asked about** (section 9): `register_device` answers
   differently for a real employee ID and a fake one, so IDs can be checked one by one —
   and problem 1 removes the only brake on that. This needs a decision: in this slice or
   a follow-up.

---

## 1. Start-of-work checks (parallel-work §1)

| Check | Result |
|---|---|
| `git fetch origin dev`, then `git log HEAD..origin/dev` | **Nothing came in.** Local `dev` is ahead of `origin/dev` (the unpushed 010 + 012 release train). |
| `git status` in the main checkout | Other sessions' uncommitted work: `.claude/context/ux-learnings.md`, deleted `OBJECTIVES_KPI_REQUIREMENTS.md`, `backlog/KPI_AUTOMATION_BACKLOG.md`, `docs/slices/009-ess-portal-redesign/00-assessment-and-plan.md`, `hrms/.../alvoraa_position.py`, and untracked files including `docs/slices/013-mobile-app/`. **None of them is a file this slice changes. I touched none of them.** |
| Work board | 010 fix round 2 owns the bench (`test_site`). 012 F1 done, not pushed. Release train: **no new slice commits on local `dev` until "010 group D + 012 push 1" is pushed.** |
| `git worktree list` | 010, 012-f1, 012 worktrees. None for 014 (not created — not approved yet). |
| Recent history of my files | `field_checkin.py`: last changed by slice 008 commits (`bca74ab` … `411536c`). `deploy/nginx.conf`: last `10eb812`. Nothing in the last 10 days from another slice. |
| Other developers | **Question for the user:** is anyone else, on another machine, changing `deploy/nginx.conf` or `field_checkin.py`? (Slice 012 has a *proposed*, not yet made, gzip change to `nginx.conf` — see section 7.) |

---

## 2. Problem 1 — forged `X-Forwarded-For`

### 2.1 Where it lives

| Place | What it does |
|---|---|
| `deploy/nginx.conf` lines 96, 107, 123, 132, 140 (production block `*.alvoraa.co alvoraa.co _`) and 177, 188, 207, 216, 224 (dev block) | `proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;` — nginx **keeps** whatever `X-Forwarded-For` the caller sent and **adds** the real address at the end. So Frappe receives `"<forged>, <real>"`. |
| Frappe v16 `frappe/auth.py`, `HTTPRequest.set_request_ip()` (lines 62–73, `version-16` at `c1f1e8e`, read 2026-09-17) | `frappe.local.request_ip = X-Forwarded-For.split(",", 1)[0].strip()` — takes the **first** entry, the forged one. Falls back to a `REMOTE_ADDR` header, then `request.remote_addr`. |
| Frappe v16 `frappe/__init__.py:415` `get_request_header` | Plain `request.headers.get(key)`. No trust check. |
| Frappe v16 `frappe/app.py:544` | `ProxyFix` is applied only when `USE_PROXY` is set, and it changes `request.remote_addr` only. `set_request_ip` reads the header directly, so **turning on `USE_PROXY` would not fix this.** |
| Frappe does **not** read `X-Real-IP` anywhere | So nginx's existing `X-Real-IP $remote_addr` line protects nothing. |

`set_request_ip` runs in `HTTPRequest.__init__`, before sessions, before
`before_request` hooks and before any endpoint.

### 2.2 What reads `frappe.local.request_ip` (grep of the Frappe files read, and of our apps)

| Reader | Effect of a forged address |
|---|---|
| `frappe/rate_limiter.py:140` — `@rate_limit(ip_based=True)` (the default) | Bucket key is `rl:<cmd>:<ip>`. A new forged IP = a fresh bucket. |
| Our `field_checkin.register_device` (`field_checkin.py:136`, 10 an hour) | Unlimited registration attempts. Each one for a real ID creates a **Pending device row** for HR to deal with. |
| Our `field_checkin.field_checkin` (`:221`, 60 an hour) | Needs a valid device secret, so only a phone holder can abuse it. Duplicates within 60 s are refused anyway. Low. |
| Our `field_checkin.field_status` (`:484`, 120 an hour) | Needs a valid secret. Low. |
| `frappe/auth.py:271` — login IP tracker (when System Settings "allow consecutive login attempts" is set) | The per-IP lock is dodged. The per-user lock still works. |
| `frappe/auth.py:463–501` — `validate_ip_address` (User → "Restrict IP") | Checks `request_ip.startswith(allowed)`. **A forged header passes the allow-list outright.** Runs at login and at session resume. Whether any user has Restrict IP set is a check (section 10). |
| `frappe/sessions.py:261, 293, 427, 441` — `session_ip`, User `last_ip` | Audit trail shows a made-up IP. |
| `frappe/monitor.py:75` | Monitor records a made-up IP. |
| `hrms/hrms/utils/__init__.py:14` `get_country` (guest) | Calls ip-api.com with the forged IP and caches the answer in a process-wide dict with no size limit. Every forged IP grows the dict. Low, but real. |
| Our `alvoraa_portal/api/auth.py` `vendor_login` | Calls Frappe's `authenticate`, so its IP tracker is dodged too. It has its own per-account lock. |

**Not affected:** nginx `limit_req` zones `kinexus_login` and `kinexus_api` use
`$binary_remote_addr`, the real TCP peer. nginx's access log also has the real peer.

### 2.3 How it is abused, who is affected, how bad

- **How:** `curl -H "X-Forwarded-For: 10.$RANDOM.$RANDOM.1" …` on every request.
- **Who:** every tenant on production and dev, all three personas. The realistic victim
  is an **Employee** whose ID is guessed (field check-in registration spam and ID
  checking), and **HR** who must clear fake Pending phones.
- **Severity: High on the audit side, Medium on the abuse side.** The nginx 120-a-minute
  limit still caps the raw volume per real address. But "IPs in logs can be faked"
  undermines CERT-In log duties (`nfr-budget.md`, ICT log retention) and any Restrict-IP
  control. Production has no live customers today (14 Sep 2026).

### 2.4 What I confirmed by reading, and what needs a test

| Claim | How known |
|---|---|
| nginx appends to the caller's header | Read in the **git copy** of `nginx.conf`. **The live file on the server was not read.** An old memory note says it once had TLS blocks not in git; commit `9f200b4` says it was made to match. Needs a check. |
| Frappe takes the first entry | Read in `version-16` source on GitHub (2026-09-17). **The bench's exact Frappe commit was not checked** (bench is in use). Needs a check. |
| A forged header gets a fresh bucket | Follows from the two lines above. **Not tested.** The local nginx test in section 6 proves it before and after. |

### 2.5 Fix options

| Option | What | For | Against |
|---|---|---|---|
| **A. nginx overwrites the header** — `proxy_set_header X-Forwarded-For $remote_addr;` in all ten `location` blocks | Frappe then gets exactly one address, the real one | One-line change per block. Frappe untouched. `limit_req` untouched. Right for "nginx is the only proxy", which is true today | Touches the file production reads. If a second proxy is ever put in front, it must be updated too — which option B handles |
| **B. A + nginx `realip` for Cloudflare** — at the top of the file: `set_real_ip_from <each Cloudflare range>;` and `real_ip_header CF-Connecting-IP;` | When a request arrives **from a Cloudflare address**, nginx sets `$remote_addr` to the visitor's real IP from `CF-Connecting-IP`. From anyone else, the header is ignored | Makes the Cloudflare move safe: `limit_req`, the access log and the new `X-Forwarded-For` all keep the real visitor. **Does nothing while DNS is "DNS only"**, because no request comes from a Cloudflare address | The Cloudflare list (about 15 IPv4 + 7 IPv6 ranges, `cloudflare.com/ips`) must be kept up to date. **If it goes stale, it fails safe**: the new Cloudflare address is treated as the visitor, so limits get stricter, never looser |
| C. Frappe side: a `before_request` hook that resets `request_ip` from the **last** header entry | Defence in depth, no nginx change | Runs **after** `set_request_ip` and after the session's Restrict-IP check, so it cannot fix that. Wrong again the day Cloudflare proxying starts. Two places to keep in step | **Not recommended** |
| D. Set `USE_PROXY` | — | — | Does not change `set_request_ip` (2.1). **Rejected** |
| E. Frappe rate limits keyed on something other than IP | Right for the mobile app (013 OPS-29) | — | That is slice 013's design, not this fix |

**Recommended: B** (which includes A). `X-Real-IP` stays as it is (already
`$remote_addr`). Leave nginx's default `underscores_in_headers off`, which already drops
a caller-sent `REMOTE_ADDR` header, and with A the `X-Forwarded-For` header is always
present, so Frappe never reaches that fallback.

**Found while reading, related (decision needed, section 12):** the login zone covers
only `location = /api/method/login`. Frappe v16 also accepts `/api/v2/method/login`,
which falls under `location /api/` (120 a minute, not 5). I have read the nginx file but
**not** proved the v2 route logs in; the local test can check it. Adding
`location = /api/v2/method/login` with the login zone is a two-block addition to the same
commit if the user wants it.

### 2.6 Rollout, test on this PC, rollback (the dangerous part)

Nothing below runs without the user's word.

| # | Step | Who / where |
|---|---|---|
| 1 | Edit `deploy/nginx.conf` in the 014 worktree | Engineer, local |
| 2 | **`nginx -t` in a throwaway `nginx:alpine` container on this PC** — the same command 012 `07-devops-inputs.md` §2a already wrote (fake host entries, self-signed certs, file mounted read-only). Also `nginx -V` to confirm the `realip` module is built in | Local PC only. **Needs the user's OK** (it is a `docker run`, though not on the bench) |
| 3 | **Behaviour test on this PC**: a second throwaway container runs a copy of the file with the upstreams pointed at a tiny echo server that returns the headers it received. Send requests with forged `X-Forwarded-For`, and with a forged `CF-Connecting-IP`. Expect: the echo shows **one** address, the real peer, every time. Run it against the **old** file too, to show the bug is real | Local PC only, same OK |
| 4 | Commit (section 8) — lands on local `dev` only after the release train is pushed | Engineer |
| 5 | Push to `dev` **on the user's explicit word**, at a quiet moment. This changes the production nginx too | Agent on the user's word |
| 6 | Watch the deploy. Then: dev answers (agent may check); **production answers `200` — the user checks**; `docker logs --tail 20 compose-nginx-1` shows no `emerg` (user) | Dev: agent. Production: user |
| 7 | Live proof on dev: call `register_device` 11 times with 11 different forged `X-Forwarded-For` values and a bad consent flag (so nothing is created) — the 11th must get `429` | Agent on the user's word, dev only |

**Two-step option (same as slice 012 used):** commit C1 changes the **dev** block plus the
Cloudflare lines (which do nothing today); commit C2 changes the **production** block and
goes out with the next `main` release. Safer for behaviour, but production stays open
until then. Parse risk is the same either way, because production reads the whole file.
**User decides** (section 12).

**Rollback:**
- **Normal:** `git revert` the nginx commit, push to `dev` on the user's word. The deploy
  restarts nginx with the old file. One deploy run.
- **nginx will not start:** every site is down. The fix is in the server folder
  `/var/www/html/hr-app`, which agents never touch. **Only the user** can: restore the
  previous `deploy/nginx.conf` from git there, `docker restart compose-nginx-1`, check
  `docker logs --tail 20 compose-nginx-1`. Step 2 exists so this never happens.
- The deploy's `docker restart compose-nginx-1 … || true` **hides** a failed start. The
  smoke test notices dev is down only after production is down too.

---

## 3. Problem 2 — photo, GPS and names in logs

### 3.1 How Frappe logs a failed request (Frappe `version-16`, read 2026-09-17)

| Step | Source | What gets written |
|---|---|---|
| Any exception reaches `app.handle_exception` | `frappe/app.py:448` | `if http_status_code >= 500 or frappe.conf.developer_mode: log_error_snapshot(e)` — **in developer mode, 4xx too** |
| `log_error_snapshot` | `frappe/utils/error.py` | Skips only `AuthenticationError`, `CSRFTokenError`, `SecurityException`, `InReadOnlyMode`. Calls `log_error()` and `frappe.logger(with_more_info=True).error(...)` |
| `log_error()` — **every** call, including our own `frappe.log_error(...)` | `utils/error.py` `get_error_metadata()` | Error Log `metadata` = JSON with `form_dict` passed through `sanitized_dict` — **the whole request, not shortened** |
| `log_error()` with no message | `frappe.get_traceback(with_context=True)` → `traceback_with_variables` | Error Log `error` = traceback **with the local variables of every frame**, each cut to 1,000 characters |
| `logger(with_more_info=True)` | `utils/logger.py` `SiteContextFilter` | `frappe.log` line with `Form Dict: <sanitized form_dict>` in full. Written to the bench `logs/frappe.log` (inside the container, lost on recreate) **and** `sites/<site>/logs/frappe.log` (in the `sites` volume, **survives deploys**). 100 KB × 20 rotated files |
| What is hidden | `sanitized_dict` | Only keys whose name **contains** `password`, `passwd`, `secret`, `token`, `key`, `pwd`. `photo`, `latitude`, `longitude`, `accuracy`, `captured_at`, `employee_id`, `device_label` are written as they are. The traceback sanitizer hides variables with those exact names only |
| Where the variables come from | `frappe/handler.py:86` `frappe.call(method, **frappe.form_dict)`; `frappe/__init__.py:1140` `call(fn, *args, **kwargs)` | The `kwargs` in Frappe's own `call` frame hold the photo and GPS. So **even if our code removes them, an exception that travels up through that frame prints them.** This is why "catch and re-raise with a safe message" is not enough |
| Retention | Frappe `hooks.py` `default_log_clearing_doctypes` | Error Log cleared after **14 days** by default (a tenant can change it in Log Settings). Log files rotate by size only. Database backups keep Error Log rows until the backup itself is deleted |

### 3.2 Where our code hits it (`alvoraa_portal/alvoraa_portal/field_checkin.py`)

| Line | Path | What leaks | Needs a crash? |
|---|---|---|---|
| 445–447, 453–455, 458–460 | `_attach_photo` rejects a photo: `frappe.log_error(f"... for {checkin.name}", "Field check-in")` | Error Log `metadata.form_dict`: **full photo text** (up to the 50 MB nginx body limit when it is the "too big" case), latitude, longitude, accuracy, captured_at, log_type. Token is hidden | **No.** A normal request with a bad photo |
| 476–477 | Photo save fails (`except Exception`) | Same as above | A file-save error |
| 222–311 | `field_checkin` raises anything unexpected (deadlock, lock timeout, DB error, a bug) → 5xx | Error Log `metadata` (photo, GPS) **and** `error` traceback with locals: `photo`, `latitude`, `longitude`, `lat`, `lon`, `accuracy`, `emp` (`employee_name`), the `kwargs` in Frappe's `call` frame. `frappe.log` gets the form dict | Yes on production. **No on dev** (developer mode): every "too far", "already recorded", "location vague", "not set up" refusal does it |
| 290 | `raise` after `_geofence_message` returns None | Same | Same |
| 137–214 | `register_device` 5xx (or any refusal on dev) | `employee_id` in form dict; `emp` local with `employee_name` | Same |
| 485–523 | `field_status` 5xx (or any refusal on dev) | `emp` with `employee_name` and `designation` | Same |
| Error Log title (`method`) | `str(exception)` for a snapshot | A database error text can quote a value | Rare |

The module's own docstring (line 16) says the photo "never reaches the error log". It does.

`purge_old_checkin_photos` (line 580) deletes `File` rows only. It never looks at
Error Log, log files or backups.

**Not a leak:** nginx access log (POST bodies are not logged; all three endpoints are
POST only). `Document.__repr__` prints only doctype and name
(`model/document.py:2002`). Sentry: `capture_exception` runs only if a DSN or telemetry
is set; `FRAPPE_SENTRY_DSN` is in none of `deploy/envs/*.example` — a check (section 10).

### 3.3 Who is affected, how bad

- **Employee (field worker)** is the data subject: face photo, exact position, name.
- **Readers of the copies:** anyone with **System Manager** on the tenant (Error Log is
  System Manager only) and anyone with server or backup access to `sites/<site>/logs`.
- **HR Manager / CXO:** no change in what they can read through the app.
- **Severity: High** (privacy). A face photo plus a timed GPS fix, outside the 90-day
  retention rule, outside the photo access log (PRIV-10), against a Blocking requirement
  (008 SEC-8) and `nfr-budget.md` ("personal data in logs: never"). On dev it is
  **every refused punch**, not a rare crash.

### 3.4 Confirmed by reading vs needs a test

| Claim | How known |
|---|---|
| Rejected photo writes photo + GPS into Error Log `metadata` | Read: our `log_error` calls + Frappe `get_error_metadata`. **Not reproduced.** |
| 5xx writes locals, including Frappe's `call` kwargs | Read in Frappe + `traceback_with_variables` (1,000-character cut). **Not reproduced.** |
| Dev snapshots 4xx | Read `app.py:448` + `dev.env.example`. **The live dev value of `developer_mode` was not checked.** |
| How many copies exist on dev / production today | **Unknown.** Needs read-only queries (section 10). |

### 3.5 Fix options

| Option | What | For | Against |
|---|---|---|---|
| a. Remove the fields from `frappe.form_dict` at the start of each endpoint | `frappe.form_dict.pop("photo")` etc. | Fixes the `metadata` copies and `frappe.log`, including the rejected-photo path | **Does not** fix the traceback locals — Frappe's `call` frame still holds them |
| b. a + catch **unexpected** errors, log a safe Error Log, re-raise a clean exception | — | — | The re-raised exception still climbs through Frappe's `call` frame, so its locals are printed. **Does not work** (3.1). Also does nothing for dev's 4xx |
| **c. a + a small wrapper that never lets an exception leave the endpoint** | Wrapper (below) on the three guest endpoints | Nothing reaches `handle_exception`, so no snapshot, no locals, on production **and** dev. Response shape kept the same, so `www/field-checkin.html` needs no change | About 50 lines of code that must copy Frappe's error response exactly. Needs a pin test on the response shape |
| d. Rename request fields so their names contain `key`/`secret` | e.g. `photo_key` | Uses Frappe's own mask | Hack. Breaks the page and 013's API. Locals named `lat`/`emp` still print. **Rejected** |
| e. Change Frappe's blocklist | — | — | Upstream edit or monkey-patch. Forbidden (`frappe-conventions.md`). **Rejected** |
| f. Turn `developer_mode` off on dev | Config | Removes the dev 4xx leak | Changes how dev behaves for everyone (tracebacks, DocType editing). Does not fix the photo-rejection path or 5xx. A user decision, not a fix on its own |

**Recommended: c.** In words:

```
_private_request(*fields)          # private to field_checkin.py; used on 3 endpoints
  on entry:  remove `fields` from frappe.form_dict      (metadata + frappe.log copies gone)
  call the endpoint
  expected refusal (frappe.ValidationError and its family, AuthenticationError,
                    PermissionError, TooManyRequestsError, DoesNotExistError):
      frappe.db.rollback()
      frappe.local.response.http_status_code = e.http_status_code
      frappe.local.response["exc_type"] = type(e).__name__
      return None           # the message frappe.throw queued is sent as _server_messages,
                            # exactly as today, so the page's text matching still works
  anything else:
      frappe.db.rollback()
      frappe.log_error(title="Field check-in: unexpected error",
                       message=<exception class + file:line list, no values, no str(e)>,
                       reference_doctype=DEVICE or "Employee Checkin",
                       reference_name=<device name if known>)
      frappe.msgprint(_("Something went wrong on our side. Please try again in a minute."))
      http_status_code = 500; return None
```

- Fields removed: `field_checkin` → `photo, latitude, longitude, accuracy, captured_at`;
  `register_device` → `employee_id, device_label, platform`; `field_status` → none
  (only `token`, already hidden) but it gets the wrapper for the locals.
- The wrapper sits directly under `@frappe.whitelist(...)`, so it also covers
  `requires_feature` and `rate_limit`. `inspect.signature` follows `functools.wraps`,
  so Frappe still matches arguments.
- A 500 still produces an Error Log row an operator can open: class, file and line,
  reference to the device. **No values.** That is the observability trade-off,
  stated: someone debugging a crash sees where, not with what.
- Transactions: `register_device` and `field_checkin` already commit part-way on
  purpose (`:209`, `:303`). The wrapper's rollback only undoes what was not yet
  committed. Same as Frappe's own rollback today.
- **Also:** change the three `_attach_photo` messages to keep only the check-in name
  (they already do) — with (a) in place their metadata no longer carries the photo.

### 3.6 Cleaning the copies that already exist

| Copy | How to find it | Recommended action |
|---|---|---|
| **Error Log rows** (each tenant DB, dev and production) | `metadata LIKE '%alvoraa_portal.field_checkin%'`, or `method`/`error` mentioning `field_checkin` or `Field check-in` | **One-time patch** in `alvoraa_portal/patches.txt` that **redacts in place**: in `metadata`, replace the values of `photo, latitude, longitude, accuracy, captured_at, employee_id, device_label` with `********`; in `error`, replace every variable line (`    name = value`) with `    name = ********`. Keeps the row (when and where something failed — useful, and part of the log record), removes the personal data. Safe to run twice. Logs a count only. Runs on every tenant at migrate, so nobody logs into a server |
| Alternative | — | Delete those rows instead. Simpler, but loses the record that errors happened. **User decides** (section 12) |
| **Site log files** `sites/<site>/logs/frappe.log*` (in the `sites` volume; survive deploys) | `grep -l "field_checkin" sites/*/logs/frappe.log*` inside the backend container | **Not a patch.** A patch runs in the migrate container and editing log files from app code is wrong. A short runbook for the **user** to run on dev, and on production only if they choose (production rule, CLAUDE.md §3). Rotation (100 KB × 20) means old copies age out fast once no new ones are written |
| Bench log `logs/frappe.log*` | Inside the backend container filesystem | Lost at every container recreate (every deploy). No action |
| Container stdout (`docker logs`), dev only | Developer mode prints tracebacks **without** locals | Low. No action beyond noting it |
| Database backups | Error Log table is in every backup | Cannot be cleaned. Ages out with backup rotation. **Record it** in the implementation notes as a known residue |

### 3.7 Other endpoints with the same exposure — in scope or not

The Frappe behaviour in 3.1 applies to **every** endpoint. These carry personal data in
the request:

| Endpoint | Data | Recommendation |
|---|---|---|
| `alvoraa_portal/hr_api.py:1358` `do_checkin(log_type, latitude, longitude)` | GPS, logged-in employees | **Follow-up.** Logged in, lower volume, no photo. Same wrapper when a third file needs it (then it moves to a shared module) |
| `hr_api.py:1752` `apply_leave(... reason ...)` | Leave reason (can be health) | Follow-up |
| `hr_api.py:1906` `submit_attendance_request(... reason, explanation)`; `attendance_correction.py:644` `raise_correction(... reason, explanation)` | Free-text explanation | Follow-up |
| `hrms/hrms/api/__init__.py:737` `upload_base64_file(content, filename, ...)` (Frappe HR's phone app) | Whole file as base64 in the request | Follow-up. Our fork of upstream code — wrapping it is an upgrade-safety question |
| Goal evidence (`hr_api.submit_goal_evidence_portal`, `goal_api.submit_goal_evidence`) | A file URL and extracted numbers, not the file itself (files go through Frappe's multipart upload) | Low; follow-up list only |
| **Developer mode on dev** | Every refused request on every endpoint is snapshotted with locals | **User decision** (section 12). The real cure for dev |

**Why not all now:** these are logged-in endpoints owned by slices 010/012 files that are
mid-release, and a general cure (one place that knows every sensitive field) would need
either an upstream change or a shared decorator on dozens of functions — an architecture
decision. The user asked about the check-in problem. I recommend a follow-up slice,
"015 personal data in error logs", with a PII-in-logs scanner (`nfr-budget.md` item 4).

---

## 4. Callers of every function this slice changes

| Function | Callers (grep of the whole repo, worktrees excluded) |
|---|---|
| `field_checkin.register_device` | `www/field-checkin.html:24, 657` (via `call()`); prototype/mock only otherwise. `subscription.py:175` names the feature, not the function |
| `field_checkin.field_checkin` | `www/field-checkin.html:25, 657` |
| `field_checkin.field_status` | `www/field-checkin.html:27, 657` |
| `field_checkin._attach_photo` | `field_checkin.py:293` only (message text unchanged) |
| New `_private_request` | New; used only in `field_checkin.py` |
| Hooks in `hooks.py:86, 97, 168, 172, 187, 224, 239` | Point at `log_photo_view`, `block_devices_for_leaver`, `checkin_query_conditions`, `checkin_has_permission`, `purge_old_checkin_photos`, `after_migrate` — **none of these change** |
| `deploy/nginx.conf` | Bind-mounted by `deploy/compose/docker-compose.app.yml:198`; restarted by `.github/workflows/deploy.yml:236, 277, 326, 395` |
| `frappe.local.request_ip` readers | Section 2.2 |
| Existing tests | `tests/test_opt_in_features.py:117` (feature list only), `tests/test_checkin_location.py` (portal `do_checkin`, not touched). **Field check-in endpoints have no tests today** |

Page contract kept: the page reads `body._server_messages` on a non-2xx and matches the
sentences (`field-checkin.html:1102–1119`). The wrapper keeps both the status codes and
the sentences, and adds one new sentence for the 500 case, which falls to the page's
existing "UNKNOWN" screen with the text shown.

---

## 5. Functional impact

| Dimension | Impact |
|---|---|
| Cross-module | `alvoraa_portal` (field_checkin.py, patches.txt, new patch, tests). `deploy/` (nginx.conf). `frappe`: no edit; behaviour of `request_ip` corrected for all apps, including `hrms` (`get_country`) and Frappe's login, session and Restrict-IP code. `alvoraa_goals`, `alvox_compensation`, `erpnext`: none |
| **CXO** | Nothing visible. Login, session and "last IP" records become true |
| **HR Manager** | No fake Pending phones from rate-limit dodging. No visible change in screens |
| **Employee** | Field worker: identical screens and messages. A server crash now shows "Something went wrong on our side. Please try again in a minute." instead of Frappe's raw text. Their photo and position stop being copied into logs |
| System Manager (tenant) | Error Log rows for field check-in keep the time, place in code and device name, but no photo, GPS or name |
| HRMS domain | Attendance (Employee Checkin written by the field app): unchanged. Leaves, payroll, appraisals, goals, org structure: none |

---

## 6. Tests I will add (each names the fix, so a bad merge fails CI)

New file `alvoraa_portal/alvoraa_portal/tests/test_checkin_security_014.py` (Frappe
`unittest`, run on `test_site` when the bench is free):

| Test | Proves |
|---|---|
| `test_014_rejected_photo_leaves_no_photo_or_gps_in_error_log` | Send a non-JPEG photo carrying a marker string and marker coordinates → newest Error Log rows (`method`, `error`, `metadata`) contain no marker |
| `test_014_server_error_in_punch_leaks_nothing` | Force an unexpected exception inside `field_checkin` (patch `_refuse_duplicate` to raise) → status 500, one Error Log row with the device reference, and no photo marker, no coordinate marker, no employee-name marker, no token anywhere in Error Log or in a captured `frappe.log` handler |
| `test_014_refusal_in_developer_mode_leaks_nothing` | Same, with `frappe.conf.developer_mode = 1` and a normal refusal ("already recorded") → no Error Log row, no log line with markers |
| `test_014_register_device_error_leaks_no_employee_id_or_name` | Forced error in `register_device` → no employee ID or name marker in any log |
| `test_014_refusal_response_shape_unchanged` | "Already recorded" still answers 417 with the same sentence in `_server_messages` and `exc_type` — the page's text matching keeps working |
| `test_014_endpoints_are_wrapped` | All three endpoints carry the wrapper (inspect the `__wrapped__` chain) — a merge that drops it fails |
| `test_014_redaction_patch` | An Error Log row with photo/GPS in `metadata` and variable lines in `error` is redacted; an unrelated Error Log row is untouched; running twice changes nothing |
| `test_014_nginx_never_trusts_caller_forwarded_for` | Reads `deploy/nginx.conf`: no `$proxy_add_x_forwarded_for` anywhere; every `X-Forwarded-For` line is `$remote_addr`; `real_ip_header CF-Connecting-IP` is present with only `set_real_ip_from` lines that parse as IP ranges (runs in CI, no nginx needed) |

Plus a local script `scripts/check_nginx_forwarded.sh` (the section 2.6 steps 2–3): it
**fails on the current file** (echo shows the forged address first) and passes on the new
one; it also sends 11 forged-address requests to a stub `rate_limit`-like counter keyed on
what Frappe would read, and expects one bucket. Run only on the user's OK.

Also run: whole `bench --site test_site run-tests --app alvoraa_portal` (known 14
failures expected, nothing new) and a hand trace of the field check-in page on the local
bench (register → HR approves → punch → refused punch → forced error screen).

---

## 7. Parallel-work check

| File | Hot? | Who else is in it | Plan |
|---|---|---|---|
| `alvoraa_portal/alvoraa_portal/field_checkin.py` | No | Nobody on the board. **Slice 013 (mobile app)** will change it heavily later (OPS-28 statuses, hash-keyed limits, join endpoints) — 013 is documents only today | **Sequence:** 014 first. 013's spec should reuse the wrapper for its new endpoints; I will say so in the implementation notes |
| `alvoraa_portal/alvoraa_portal/patches.txt` | **Yes** | Slice 010 added lines (in the unpushed release) | One line **at the end**, added after rebasing on the pushed release. On conflict keep both lines in commit order |
| New `alvoraa_portal/alvoraa_portal/patches/v?_?/redact_field_checkin_error_logs.py` | No | — | New file |
| New `tests/test_checkin_security_014.py` | No | — | New file, own record names (`_014` suffix) |
| `deploy/nginx.conf` | **Yes** (`deploy/` rule: only when the task is about it — it is) | **Slice 012 §2a proposes gzip lines** in the same file (not made yet). Same server blocks, different lines | **Split:** 014 changes only `X-Forwarded-For` lines and adds the Cloudflare block at the top. If 012's gzip lands first, rebase; if 014 lands first, 012 rebases. Either way one `nginx -t` covers the combined file |
| New `scripts/check_nginx_forwarded.sh` | No | — | New file |
| `docs/slices/014-checkin-security-fixes/*` | No | — | Own folder |
| `alvoraa_portal/www/hrms-employee.html` | **Yes** | 009 portal redesign is about to start there | **Not touched.** |
| `www/field-checkin.html` | No | — | **Not touched** (the wrapper keeps its contract) |
| `hooks.py`, DocType JSON | Yes | 010, 012 | **Not touched** |
| `test_portal_security_010.py` CEILINGS | Shared test | 010, 012 | Not touched: the slice adds no `ignore_permissions` |

**How it lands safely**

1. After approval: worktree `.claude/worktrees/014-checkin-security-fixes` on
   `slice/014-checkin-security-fixes` from `origin/dev`, and a row on the work board.
2. Build and run the tests that need no bench. **Wait for the bench** (010 has it) before
   `run-tests`; mark the board when I take it.
3. **Do not bring 014 into local `dev` until the "010 group D + 012 push 1" release is
   pushed** (release train rule). Then fetch, rebase, read what came in, fast-forward.
4. Before any push: list every commit that would go, mark mine, ask about the rest.

---

## 8. Size and commit order

**Size: small to medium.** About 1 day of build and tests, plus the rollout steps, which
depend on the user's timing.

| # | Commit | Contents | Can ship alone? |
|---|---|---|---|
| A | "Field check-in: keep photos, positions and names out of error logs" | `_private_request` wrapper on the three endpoints, form-field removal, safe 500, tests 1–6 | Yes. Normal app deploy, no nginx restart beyond the usual |
| B | "Redact field check-in data already in Error Logs" | Patch + one line at the end of `patches.txt` + test 7 | Yes, after A (so no new copies appear behind it) |
| C | "nginx: pass Frappe only the real client address" | `X-Forwarded-For $remote_addr` in all blocks, Cloudflare `realip` block, test 8, `scripts/check_nginx_forwarded.sh` | Yes. **Separate on purpose**: it can be reverted alone and pushed at a quiet moment. (Or C1 dev block + C2 production block — section 12) |
| D | Implementation notes | `03-implementation-notes.md` | — |

A and B together are the privacy fix. C is the rate-limit fix. They do not depend on each
other and can go to `dev` on different days.

---

## 9. Found while reading — not in the request

| # | Finding | Severity | Suggest |
|---|---|---|---|
| F1 | `register_device` returns a `token` key only when the employee ID is real and Active (`field_checkin.py:192–214`). Its own docstring promises an identical answer. So a caller can test IDs one by one; problem 1 removes the only brake | Medium | **Ask the user:** fix here (return an identical-looking answer either way, about 10 lines + a test) or follow-up. Product check needed: the page uses the token to start waiting for approval |
| F2 | 008 SEC-3 asked for a **site-wide** registration ceiling that alerts HR. I did not find one in `field_checkin.py` | Medium | Follow-up (fits 013's rate-limit design, OPS-29) |
| F3 | `_device_from_token` refuses only `Blocked` and `Pending` (013 OPS-28) | Low today, High once 013 adds statuses | Slice 013 |
| F4 | `/api/v2/method/login` is outside nginx's login zone | Medium | Optional two blocks in commit C — user decides |
| F5 | `hrms` `get_country` grows an unbounded in-memory dict per IP | Low | Follow-up; much smaller once C lands |
| F6 | Same log exposure on logged-in endpoints (3.7) and dev's developer mode | Medium | Follow-up slice 015 |

---

## 10. Checks to run later (need the bench, dev, or the server)

| # | Check | Where / who |
|---|---|---|
| K1 | `git -C apps/frappe describe --tags` and `set_request_ip` / `get_error_metadata` / `log_error_snapshot` match what I read | Local bench, when free — engineer |
| K2 | Live `/var/www/html/hr-app/deploy/nginx.conf` equals git (`git -C … diff --stat deploy/nginx.conf`) | Server — **user** (or security engineer on the user's word, read-only) |
| K3 | `developer_mode` on each dev and production site (`bench --site all … get-config`) | Dev: agent on word, read-only. Production: user |
| K4 | Log Settings: Error Log retention days per tenant | Same |
| K5 | Count of Error Log rows mentioning `field_checkin` per tenant (read-only query) — sizes the cleanup | Same |
| K6 | Any User with Restrict IP set | Same |
| K7 | `FRAPPE_SENTRY_DSN` / telemetry set on dev or production | User |
| K8 | Cloudflare: are any records proxied (orange) today? | User, in the Cloudflare dashboard |
| K9 | `nginx -V` shows `--with-http_realip_module` in the `nginx:alpine` image used | Local throwaway container, on the user's OK |
| K10 | Does `/api/v2/method/login` log in? | Local bench, when free |

---

## 11. Non-functional verdicts (for the recommended strategy)

| Dimension | Verdict | Why |
|---|---|---|
| Performance | **neutral** | One dict pop per request; `realip` is a CIDR match per request. No extra queries. The patch runs once per site at migrate (bounded: only matching Error Log rows, batched 500 at a time) |
| Security | **improves** | Frappe's per-IP limits, login IP tracker and Restrict-IP check start meaning something. No new `ignore_permissions`. No new endpoint |
| Reliability | **improves**, with one risk | Crashes return a clean 500 and a findable Error Log. **Risk:** a typo in `nginx.conf` takes every site down — handled by the local `nginx -t` and behaviour test before any push, and the rollback in 2.6 |
| Scalability | **improves** | Cloudflare-ready: without `realip`, proxying would collapse all visitors into a few shared addresses and trip nginx's limits for whole companies. Stale Cloudflare list fails strict, not open |
| Maintainability | **neutral** | ~50-line wrapper in one file, used three times, with tests. The Cloudflare list needs a yearly look (noted in the file and implementation notes) |
| Data integrity | **neutral** | Same transaction behaviour as Frappe's own rollback. Redaction patch edits only log rows, never business records, and is safe to run twice |
| Compliance / privacy | **improves** | Closes 008 SEC-8 for the field app; stops photo and GPS copies outside the 90-day rule; makes logged IPs truthful (CERT-In). **Residue:** copies inside existing database backups, and dev's developer mode on other endpoints (F6) |

---

## 12. Decisions needed from the user

1. **Approve the strategy** — fix 1 = option B (nginx overwrite + Cloudflare `realip`),
   fix 2 = option c (wrapper + field removal) with cleanup.
2. **nginx rollout:** one commit for both server blocks (production protected at the dev
   push), or **C1 dev block now + C2 production block with the next `main` release**?
   Either way the dev push changes the file production reads.
3. **OK to run the throwaway `nginx:alpine` containers on this PC** (`nginx -t`,
   `nginx -V`, header echo test)? Not the bench, not dev, not production.
4. **Existing Error Log copies:** redact in place (recommended) or delete?
5. **Log files on dev and production:** do you want a short runbook to clean
   `sites/<site>/logs/frappe.log*` yourself, or let rotation age them out?
6. **Dev's `developer_mode=1`:** keep it (and accept F6 on other endpoints until slice
   015), or turn it off on dev?
7. **F1 (employee-ID check through `register_device`):** fix in this slice or follow-up?
8. **F4 (`/api/v2/method/login` outside the login limit):** add to commit C or not?
9. **Cloudflare:** please keep DNS records "DNS only" (grey cloud) until commit C is live
   on the server.
10. **Other developers:** is anyone else changing `deploy/nginx.conf` or
    `field_checkin.py`?

---

## Sources read

- Repo: `deploy/nginx.conf`; `deploy/compose/docker-compose.app.yml`,
  `docker-compose.nginx-multienv.yml`; `deploy/envs/*.example`;
  `deploy/setup_wildcard_cert.sh`; `.github/workflows/deploy.yml` (nginx restarts);
  `alvoraa_portal/alvoraa_portal/field_checkin.py`, `www/field_checkin.py`,
  `www/field-checkin.html` (call and error handling), `hooks.py`, `hr_api.py`,
  `api/auth.py`, `attendance_correction.py`; `hrms/hrms/utils/__init__.py`,
  `hrms/hrms/api/__init__.py`; slice 008 `01c` (SEC-3, SEC-8) and `09`; slice 012
  `07-devops-inputs.md` §2a and §5; slice 013 `07-devops-inputs.md` §2.
- Frappe `version-16` on GitHub, commit `c1f1e8e` (2026-09-15), read 2026-09-17:
  `auth.py`, `app.py`, `handler.py`, `__init__.py`, `rate_limiter.py`, `sessions.py`,
  `monitor.py`, `utils/logger.py`, `utils/error.py`, `utils/__init__.py`,
  `utils/response.py`, `model/document.py`, `core/doctype/error_log/*`,
  `core/doctype/log_settings/log_settings.py`, `hooks.py`.
- `traceback_with_variables` `core.py` (1,000-character value cut).

**Not run:** no docker, no bench, no request to dev or production, no tests.

---

## Strategy approval (2026-09-17)

**Approved by Surbhi, with the recommended answers**, for building and testing on the local instance only (not deploying):

1. Strategy approved as written.
2. **One nginx commit covering both the dev and production server blocks** (they share one file and one nginx).
3. Throwaway nginx containers on this PC for `nginx -t` and header checks: **yes**.
4. Existing Error Log rows: **blank the personal data, keep the rows** (one-time patch).
5. Server log files: **a short runbook** for the user to clean them.
6. Dev developer mode: **keep it on**; the wrapper stops the logging.
7. `register_device` answering differently for real and fake employee IDs: **fix in this slice**.
8. Add `/api/v2/method/login` to nginx's login limit: **yes, in this slice**.
9. Cloudflare records stay **grey (DNS only)** until this fix is live on the server.
10. Nobody else is known to be editing `deploy/nginx.conf` or `field_checkin.py` (board shows no claim); check the board and incoming commits again before building.

Pushing to dev stays the user's decision, after the pending "010 group D + 012 push 1" release is on dev.

---

## Pre-push checks run (2026-09-17, read-only)

- **K12 — realip module:** present in `compose-nginx-1` (nginx 1.31.5, `--with-http_realip_module`). The new directives will not stop nginx starting.
- **K2 — live file vs git:** the live `/etc/nginx/conf.d/default.conf` (bind-mounted from `/var/www/html/hr-app/deploy/nginx.conf`) **matches `origin/main` exactly, not `origin/dev`.** `main` has d6613ea (2026-09-17, "use alvoraa-wildcard cert for alvoraa.co and dev.alvoraa.co"), which is **not on `dev`**. The server folder is checked out at dev's c27fb56 with `deploy/nginx.conf` **modified in place** to main's version (`git status`: ` M deploy/nginx.conf`).
- **Consequence:** the pending "010 D + 012 push 1" release does not change `deploy/nginx.conf`, so its deploy keeps the wildcard file. **Slice 014's `ff32b69` does change it and is based on the old `alvoraa.co` certificate paths** — pushing it as is would revert production to the old certificate, or make `git checkout --detach origin/dev` fail, and deploy.yml then falls back to checking out `origin/main` in the shared folder.
- **Required before 014 is pushed:** (1) bring d6613ea into `dev` locally; (2) rebase 014 so its nginx change keeps the `alvoraa-wildcard` paths; re-run `scripts/check_nginx_forwarded.sh` and `check_nginx_conf.py`; (3) at push time Surbhi clears the in-place edit in `/var/www/html/hr-app/deploy/nginx.conf` (production wall — user only), so the checkout is clean.

---

## Scope addition (Surbhi, 2026-09-17)

**Add the driver location fix to this slice:** `portal_api.update_driver_location` (whitelisted, `ignore_permissions`, no role or ownership check) lets any logged-in user write a location, speed and heading for any Delivery Order. Fix: accept a location only from the delivery partner/driver assigned to that order (and, if there is no link from the user to a delivery partner, refuse), with a pin test. Found by the security engineer while drafting the legal templates.
