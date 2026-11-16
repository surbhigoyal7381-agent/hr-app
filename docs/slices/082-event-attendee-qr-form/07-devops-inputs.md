# 082 - Event attendee QR form: DevOps inputs

Advice only. Every Decision cell is for the user. No deploy, dev or production command
was run for this file.

---

## §1 Brief - 13 Nov 2026

### Bad news first

**1. The ready-made Frappe Web Form will turn away attendees at a busy venue (P1).**
Fact (read in `apps/frappe/frappe/website/doctype/web_form/web_form.py` on the local bench,
Frappe 16.33.1): the save call `web_form.accept` carries
`@rate_limit(key="web_form", limit=10, seconds=60)`. In `frappe/rate_limiter.py` that key is
joined to the caller's IP address. So the limit is **10 submissions a minute per IP address
per form**. At a venue, most phones share one address: the venue Wi-Fi, or the mobile
carrier's shared address (CGNAT - many phones behind one public address)
`[ASSUMPTION: Indian carriers put many phones behind one address; not measured]`.
Three hundred people submitting in five minutes from one Wi-Fi would see about 250 refusals.
The same call then also hits our nginx `/api/` limit of 120 a minute per address, burst 30
(Fact, `deploy/nginx.conf` line 489, zone `kinexus_api`).
Unknown: whether the line is the same on the image pin, Frappe v16.35.0
(`deploy/Dockerfile` line 50). The engineer should re-read it there.

**2. Any change to `deploy/nginx.conf` changes the live production proxy (P1 if touched).**
One nginx container serves production and dev from that one file (lesson 13). If this slice
needs its own nginx limit, that edit restarts the live site's proxy on the dev push. It must
pass `scripts/check_nginx_parses.sh` first.

**3. Guest write into CRM is a door that cannot be shut later without breaking printed QR codes.**
Web Form inserts with `ignore_permissions=True` for guests (Fact, same file, line 829). That
is expected, but it means the only things between the internet and a tenant's lead list are
the form's field list and whatever limit we put on it. Whatever route we choose must never
read a lead back to a guest.

### What this adds to run

| Item | New? | Evidence |
|---|---|---|
| App | **None if Frappe CRM is used.** CRM is already in the image, pinned `CRM_TAG=v1.84.0` | Fact, `deploy/Dockerfile` line 67 |
| Per-tenant install | CRM is installed only on tenants that buy it, after the setup wizard | Fact, `deploy/provision_tenant.sh` lines 107-116 |
| Container, worker, queue | **None.** One insert per submission runs in the web request | Inference: a lead insert is a few queries; no long work |
| Scheduled job | None needed | - |
| Files | None, if the form has no upload field. Recommend no upload field | See OPS-6 |
| QR generation | **Nothing on the server.** A QR is just the form's address printed as a picture. Make it once per event with any generator, or with PyQRCode 1.2.1, which Frappe already ships for two-factor login | Fact, `pip show` on the local bench |
| Tenant routing | **No change.** nginx passes the Host header and Frappe picks the site from it | Fact, `deploy/nginx.conf` line 2 and every `proxy_set_header Host` |
| New public route | Yes - one guest page and one guest save call per tenant | - |

### Burst load - estimate, not measured

- Gunicorn on production: **4 workers x 2 threads = 8 requests at once, shared by every
  tenant on the stack** (Fact, `docker-compose.app.yml` lines 261-262).
- **Estimate:** a lead insert at 100-300 ms (based on similar single-document inserts; not
  timed). Then 8 slots handle roughly 25-80 saves a second. 300 people in 5 minutes is about
  1 a second on average, perhaps 10 a second at the peak. **This fits, if the 8 slots are
  not already busy** - for example with DTC biometric posts or month-end payroll.
- Database and Redis: 300 small rows and 300 rate-limit counters per event. Trivial.
- The heavier part is likely the **page load, not the save**: Frappe's web form page
  pulls its own scripts and styles. And this page falls through to nginx `location /`, which
  does **not** compress HTML (Fact, `deploy/nginx.conf` lines 334-335, the BREACH rule).
  The 3G budget is **≤ 2.5 s p95** (`nfr-budget.md`). Measure the page weight in §2.
- Side effects of each lead: CRM assignment rules or notification emails could send 300
  emails in five minutes through the `default` queue. Unknown until the CRM config is known.

### Rough run cost - estimate

- Infrastructure: **about zero extra.** No new container, no new app, no new storage.
  About 1-2 MB of database per 300-person event (estimate: a lead row plus its version and
  activity rows, a few KB each).
- The real cost is people time: one guest endpoint and maybe one nginx location to keep
  safe through every Frappe upgrade.
- `nfr-budget.md` has no per-tenant cost ceiling yet (`TODO`), so I cannot compare.

### Recommendations

| ID | Recommendation | Why | Cost of ignoring it | Level | Kind | Decision |
|---|---|---|---|---|---|---|
| OPS-1 | Before the brief is final, decide: stock Web Form (rung 1-2) or one small guest save call of our own (rung 4). Recommend the stock Web Form **only if** a test on dev shows 50 saves from one address in a minute all succeed. Otherwise use our own call with a limit keyed on the event, not the IP, reusing the existing hashed limiter in `alvoraa_portal/field_app_limits.py` (slice 013 already solved "400 phones on one Wi-Fi") | Fact: stock limit is 10 a minute per address per form | Attendees see "too many requests" at the event; leads are lost and cannot be recovered | P1 | Recommend | |
| OPS-2 | Make each event's form refuse submissions outside the event's open and close dates. Put the event's own code in the QR address | A printed poster lives forever and is photographed. A date window is the cheapest spam control there is | The URL keeps accepting junk for years; spam leads land in the tenant's CRM | P2 | Recommend | |
| OPS-3 | Anti-bot: start with the date window (OPS-2), a hidden "honeypot" field (a field people never see, so only bots fill it) and the rate limit. **No captcha** in the first version | A captcha (for example Cloudflare Turnstile) adds an outside service, a new data sub-processor and extra script weight on 3G. Nothing yet shows spam | Add it only if spam is measured | P3 | Consider | |
| OPS-4 | If an nginx limit is needed, add one `location` for the exact save path with its **own** zone (like `alvoraa_device`, 600 a minute, burst 100), not the shared `kinexus_api` zone. Run `scripts/check_nginx_parses.sh` and ship it as its own approved change | One nginx serves production and dev (lesson 13); the shared zone throttles a whole venue as one caller | A dev push restarts the live proxy with an untested file; or the venue is throttled at the front door | P1 if nginx is touched | Recommend | |
| OPS-5 | The guest response says "Thank you" and nothing else - no lead name, no echo of the data. No list, no edit, no "submit another and see yours" page (`allow_edit`, `show_list` off) | `data-doors.md`: a guest door must not read anything back | A guest can enumerate or confirm other attendees' details | P1 | Recommend | |
| OPS-6 | No file or photo upload field on the form. Keep "Allow guests to upload files" off in System Settings | A public upload is disk growth, backup growth and a malware route | Disk fills (lesson 16: a full disk stopped production workers on 10 Sep) | P2 | Recommend | |
| OPS-7 | The QR must encode the tenant's own address (`https://<tenant>.alvoraa.co/...`). Never a dev address on a printed QR. Never rename a tenant site that has printed QR codes in circulation | Host header picks the site. A dev URL sends real attendees' data to dev | Real personal data on dev; or every printed QR breaks after a rename | P2 | Recommend | |
| OPS-8 | Attendee details are personal data: the form needs a short notice at the top (who collects it, why, how long it is kept), and the brief needs a retention period for event leads. Nginx access logs must not hold the submitted data - keep it in the POST body, never the query string | DPDP; `nfr-budget.md` "personal data in logs: never" | A complaint we cannot answer; personal data sitting in nginx logs | P2 | Recommend | |
| OPS-9 | Before release, time 300 saves in 5 minutes from one address against dev (not production), with the CRM assignment rules switched on as the customer will use them | Every figure in "Burst load" above is an estimate | First real event is the load test | P2 | Recommend | |
| OPS-10 | Standardise on **Frappe CRM Lead**: it is in the image and slice 057 used it. ERPNext Lead also needs no install, but splitting leads across two record types per tenant doubles the guest surface to secure | Fewer doors | Two places to secure and report on | P3 | Consider | |
| OPS-11 | Agree whether the save path may queue CRM notification emails per lead. If yes, check the email volume per event with the customer | 300 emails in minutes through one default queue shared by every tenant | DTC jobs wait behind event emails | P3 | Consider | |

### Questions

**Must know (blocks the strategy, not this brief):**
1. *Will attendees mostly be on venue Wi-Fi or on their own mobile data?* My reading: both,
   and both share addresses. This decides OPS-1 (stock Web Form or our own call). Default if
   unanswered: assume shared addresses and plan for our own call with an event-keyed limit.

**Should know:**
2. *Does every event customer already buy CRM?* If not, CRM install becomes part of their
   onboarding (existing path, `provision_tenant.sh`). Default: yes, CRM is sold with this.

### What I did not check

- I did not read the Frappe CRM source: CRM is not installed on the local bench (Fact,
  `ls apps`). So I do not know what CRM runs when a lead is inserted.
- I did not re-read the rate limit on Frappe v16.35.0, the version the image pins.
- No timing was taken. Every load and cost number above is an estimate.
- I did not check Cloudflare's settings or whether its free plan rate rules fit. Nginx
  reads the real caller address from Cloudflare (Fact, `real_ip_header CF-Connecting-IP`).

### Left behind

Nothing. I only read files and ran read-only `grep`, `sed` and `pip show` inside
`hrlocal-bench`. No container, file or setting was changed.

### Subtract pass

Removed: a separate row recommending a background queue for saves (no number shows the
insert misses the 500 ms budget), a row for a server-side QR generator (not needed), and a
row on a CDN for the form page (wait for the §2 page-weight measurement).

---

## §2 Design - 13 Nov 2026

Sources read: `01-product-brief.md`, `01b-ux-design.md`, `prototype-v1.html`, and the CRM
v1.84.0 source inside the local container `hrlocal-328` (`crm/www/crm_form.html`,
`crm_form.py`, `crm/api/form.py`, `crm/hooks.py`), plus Frappe's `website/path_resolver.py` and
`page_renderers/template_page.py` in the same container. All reads were read-only. CRM is not
installed on any local site, so **nothing below was timed in a browser**.

### Bad news first

**1. The stock page loads Google Fonts. That alone probably breaks the 2.5 s budget on 3G (P2).**
Fact (`crm_form.html` lines 8-13): the page links to `fonts.googleapis.com` (Inter, 4 weights)
as a stylesheet that blocks the first draw. That stylesheet then pulls font files from
`fonts.gstatic.com`. So the phone has to reach two extra hosts, each with its own name lookup
and secure connection, before it can show any text. It also sends every attendee's IP address
to Google, a third party the notice does not name.

**2. A CRM Lead form can publish up to 500 staff names to anyone who has the link (P1).**
Fact: CRM Lead has a Link field to `User` (the lead owner). `grant_guest_link_access`
(`crm/api/form.py` lines 268-323) lets any Sales Manager give Guest `select` on `User` with
one click. The public page then puts up to 500 user names into a dropdown (`crm_form.py`,
`MAX_LINK_OPTIONS = 500`). The grant is a permission row for the whole site, not a form
setting, so it stays after the form is deleted.

**3. `web_include_css` and `web_include_js` cannot change this page.** Fact: `crm_form.html` is
a complete HTML file. It does not extend Frappe's base template, so those hooks never load on it.

### Page weight and load time - estimate

| Part | Size | Label |
|---|---|---|
| HTML with its CSS and script written inside the page. No app bundle, no Vue | Template 27.8 KB. About 30-35 KB once 7 fields are filled in | Fact for the template (`wc -c`). Estimate for the filled-in page |
| Compression | None from our nginx (`location /` has `gzip off` because of the BREACH rule) | Fact, `deploy/nginx.conf` line 336. Cloudflare may compress it on the way out. Unknown: I could not check the tenant DNS setting |
| Google Fonts stylesheet | About 1-8 KB. Blocks the first draw. Separate host | Estimate |
| Inter font files | About 25-50 KB per character set. `display=swap`, so text is not held back while they load | Estimate, not downloaded |
| Images, video | None on the stock page. The QR card is drawn in the organiser's browser | Fact (template). Design §6 |
| Hindi text | Inter has no Hindi letters, so the phone's own font draws them. No download | Inference |

**Load estimate on Chrome's "Fast 3G" profile** (about 560 ms per round trip, 1.4 Mbps; my
arithmetic, not a measurement): our HTML needs about 4 round trips plus 0.2 s to transfer, so
**about 2.4 s, right at the 2.5 s limit**. The Google Fonts stylesheet adds about 3-4 more round
trips to a new host before the first draw, so **about 4-4.5 s for the stock page**. Without the
font link the page fits the budget. With it, it probably does not.

### Caching

| What | Cache? | Why |
|---|---|---|
| The form page | **Never.** Keep `no_cache = 1`, which is already set (`crm_form.py` line 10) | It holds a session CSRF token (a one-session code that proves the request came from this page). The design also shows the organiser's QR box only to a signed-in Sales Manager. A cached copy would hand that box or a stale token to someone else |
| The submit (`POST`) | **Never** | It writes a lead |
| The "closed / unknown" card | **Never** | A form can be published again. A cached "closed" would turn people away from a live event |
| Font files, if we serve them ourselves under `/assets/` | Yes. Already `expires 30d`, `immutable` | Fact, `deploy/nginx.conf` lines 214-215 |

No CDN rule, no page cache, nothing new. The page is small enough without them.

### Q-UX1: can we change `/crm-form` without editing CRM?

Fact from Frappe's source: a `www` page is looked up in installed apps, **last installed
first** (`template_page.py` line 53). A `page_renderer` hook is tried before every built-in
renderer (`path_resolver.py` lines 70-78).

| Option | Does it work? | Upgrade risk |
|---|---|---|
| **A. Our own page at a new address** (for example `/event-form/<route>`) in `alvoraa_portal/www`, reading CRM's own Web Form record | Yes, on every tenant, whatever the install order | **Low.** It reads two CRM fields (`crm_published` and the field list). If a CRM upgrade renames them, our page breaks, so one test should check they still exist. It lets us drop Google Fonts, the Discard button and the English 404, and own the save call (OPS-1) |
| B. Same file name, `www/crm_form.html`, in our app, to hide CRM's copy | Only where our app was installed **after** CRM. Tenants get CRM after the setup wizard (`provision_tenant.sh`), so CRM usually wins | High. Fails without any error, and differs from tenant to tenant |
| C. A `page_renderer` hook that takes every `/crm-form/*` address | Yes, always | High. It takes over CRM's page on every tenant, including its draft preview and embed mode. Every fix CRM makes to that page is lost without anyone noticing |
| D. `web_include_css` / `web_include_js` | **No.** The page does not load them | - |
| E. `update_website_context` hook | Changes text values only (for example the button label), not the layout | Low, but it cannot deliver the design |
| F. nginx rewrite or text swap | Yes | **Rejected.** One nginx serves production and dev (lesson 13) |

### Recommendations

| ID | Recommendation | Why | Cost of ignoring it | Level | Kind | Decision |
|---|---|---|---|---|---|---|
| OPS-12 | For Q-UX1, prefer option A: our own small page at a new address, using CRM's Web Form record for its data. This is rung 4 (new code). Rungs 1-3 are rejected because the stock page breaks the 3G budget and the rate limit, and D and E cannot change the layout. Engineer to confirm | The only option that works on every tenant without touching CRM | B or C break without warning on a CRM upgrade or on a tenant's install order | P2 | Recommend | |
| OPS-13 | Our page uses the phone's own fonts. No Google Fonts link, no font download | Saves 3-4 round trips on 3G, and stops sending attendee IP addresses to Google | First draw around 4-4.5 s, outside the 2.5 s budget. A third party missing from the notice | P2 | Recommend | |
| OPS-14 | No Link fields on an event form. Before each deploy, and on each tenant that uses the form, list Guest permission rows (`Custom DocPerm` where the role is Guest) and confirm none is on `User`, `Employee` or `CRM Lead` | `grant_guest_link_access` can publish up to 500 staff names. That door sits outside the form | Staff names public through a link printed on a poster (`data-doors.md`) | P1 | Recommend | |
| OPS-15 | The organiser's "Download QR card" box (D1-B) must be decided on the server: put it in the page only when the signed-in user is a Sales Manager or System Manager. Never hide it with CSS | A box hidden with CSS is still in the page every guest downloads | Organiser tools and the draft flag visible to every attendee | P2 | Recommend | |
| OPS-16 | Measure before the strategy gate: on dev, open the stock page and our page with DevTools "Fast 3G" and record the bytes transferred and the time to first draw | Every number in this section is an estimate | A design choice made on a guess | P2 | Recommend | |
| OPS-17 | Keep images off the form. If an organiser ever wants a logo, cap it at 20 KB | Each image costs time on 3G | One photo uses up the budget | P4 | FYI | |

### What I did not check

- I did not open the page in a browser or time it. CRM is not installed on any local site.
- I did not check whether Cloudflare proxies and compresses the tenant hostnames.
- I did not check whether a Guest can call `frappe.desk.search.search_link` or
  `/api/resource/User` once Guest `select` on `User` exists. The security engineer's door
  tests should cover both.
- I did not count Guest permission rows on any dev or production tenant.

### Left behind

Nothing. I ran read-only `cat`, `sed`, `grep` and `wc` inside `hrlocal-328`. No file, site or
setting was changed there.

### Subtract pass

Removed: a row proposing a CDN for the page (30-35 KB does not need one), a row on caching the
page at Cloudflare (it holds a token and must not be cached), and a row on a server-drawn QR
image (the design already draws it in the browser).

---

## §3 Requirements - 13 Nov 2026

Sources read: `01-product-brief.md`, `01b-ux-design.md` (including §13), §1 and §2 above,
`alvoraa_portal/field_app_limits.py`, `field_app_errors.py`, `deploy/nginx.conf`,
`deploy/compose/*.yml`, `deploy/provision_tenant.sh`, `DEPLOYMENT_RUNBOOK.md`,
`.github/workflows/worker-health.yml`. Docker was not running on this machine today, so
**nothing was run or timed for this section**. Every number is an estimate or a proposal.

### Bad news first

**1. The limiter we agreed to reuse has a fixed one-hour window (P1 if copied as is).**
Fact (`field_app_limits.py` line 40): `WINDOW_SECONDS = 60 * 60`, used by every `_limited`
endpoint. Frappe's limiter counts in a fixed window: once a key is over its limit, every call
is refused until the window ends. With a one-hour window, an event that hits its limit stays
shut for up to an hour, and the agreed message "wait 10 s, press Send again" (D2-A) would be
untrue. The event limit needs a 60-second window (OPS-19).

**2. The guest save goes through nginx's shared `/api/` limit, and nginx refuses with 503, not
429.** Fact (`deploy/nginx.conf` lines 489-490): `location /api/` uses zone `kinexus_api`,
120 a minute per address, burst 30, and sets no `limit_req_status`, so nginx answers **503**
(its default). Only the login location sets 429 (line 391). The page must treat 503 as "too
many" (OPS-20). Whether 120 a minute per address is enough for one venue Wi-Fi is the load
test's question (OPS-32).

### Requirements for the analyst to trace

| ID | Requirement | Why | Cost of ignoring it | Level | Kind | Decision |
|---|---|---|---|---|---|---|
| OPS-18 | **The guest save stays synchronous.** One request inserts one CRM Lead and answers "saved" or a refusal. No background job, no new queue, no new worker. Revisit only if the load test (OPS-32) measures save p95 above 500 ms (`nfr-budget.md`, whitelisted API call) | "Thank you" must mean the lead exists; a queued save could fail after Thank you. A queue is banned without a measured miss (`no-over-engineering.md` §2). Estimate: one insert is a few queries | Leads lost silently after the attendee has left | P2 | Recommend | |
| OPS-19 | **Per-event limit: 300 saves per 60 seconds per event form**, keyed on the hashed form route, not the address (`ip_based=False`). Reuse `_limited` from `field_app_limits.py` with one change: a window argument whose default stays 3,600 s, so slice 013's endpoints do not change. Over the limit the call answers **HTTP 429**, code `TOO_MANY_TRIES`, through the existing `refuse()`. The page shows the D2-A words and keeps every answer. Proposal; the security engineer sets the final number (brief Q5) | 300 a minute lets a whole 300-person hall through even if everyone presses Send in the same minute, and caps a photographed poster at 300 junk leads a minute. A 60 s window makes "wait 10 s" mostly true (worst case 60 s) | One-hour lockout at a live event (bad news 1); or no cap on spam | P1 | Recommend | |
| OPS-20 | **Per-address limit: no new one.** Keep nginx's existing `kinexus_api` (120 a minute per address, burst 30, answers 503) and add no address limit in our code. The page maps **429 and 503** to the D2-A "too many" message, and every other failure to "Not sent". If OPS-32 shows more than 1% of saves refused at the front door, stop and bring back the options: OPS-4 (own nginx location and zone, its own approved change) or a lower expectation. Do not send the save through `POST /` with `cmd` to dodge the nginx limit | Fact: zone and status in `deploy/nginx.conf`. Estimate: a 10-a-second peak for 10 s from one Wi-Fi gets about 50 of 100 through on the first press; the rest get through on the second press after 10 s, since the bucket refills 2 a second | A 503 shown as "Not sent, check your signal" sends people away; or an untested nginx edit restarts the live proxy (lesson 13) | P2 | Recommend | |
| OPS-21 | **Route rules.** The page is `/event-form/<route>`, served by our app (a `website_route_rules` entry and a `www` page). It falls to nginx `location /` (no limit, `gzip off`). The save is one `POST /api/method/alvoraa_portal.<module>.<function>`, guest-allowed, POST only; attendee data travels in the body, never the query string. **No change to `deploy/nginx.conf` in this slice.** The review checks that `git diff origin/dev -- deploy/nginx.conf` is empty | One nginx serves production and dev (lesson 13). nginx logs keep the full address line, so data in the query string would land in the logs | The live proxy restarts on a dev push; or personal data in nginx logs | P1 | Recommend | |
| OPS-22 | **Never cached:** the form page, the save answer and the closed/unknown card each send `Cache-Control: no-store` (Frappe's `no_cache = 1` for the page). A test reads the header on all three | Agreed in §2. A cached "closed" turns people away; a cached page carries a session token and the organiser box | People refused at a live event; the organiser box served to guests | P2 | Recommend | |
| OPS-23 | **Test site with CRM, local first.** Build a fresh local site the way production builds one: Frappe v16.35.0 and CRM v1.84.0 (the image pins, `deploy/Dockerfile`), ERPNext and our apps, setup wizard finished, **then** `install-app crm` (that order is required: `provision_tenant.sh` lines 107-118, CRM seeds fake users if present during the wizard). Use your own stack, not `hrlocal-bench` (it mounts a stale checkout). On it, re-read Frappe's `rate_limiter.py` and CRM Lead's insert hooks | No local site has CRM today. A copied site hides missing setup (lesson 6, ALV-249) | Door tests and timings run against the wrong versions, or not at all | P1 | Recommend | |
| OPS-24 | **List what a lead insert sets off.** On the OPS-23 site the engineer lists every `doc_events` hook and every enqueue on CRM Lead insert (assignment rules, notification emails, SLA, activity rows), with the queue each uses, and counts the emails 300 leads would send. Nothing may enqueue a job per lead with attendee data as job arguments | §1 OPS-11 is still open; I could not read CRM's hooks today. Jobs on the shared `default` queue wait in line with DTC's | 300 emails in minutes delaying DTC jobs; personal data stored in Redis job arguments (lesson 9) | P2 | Recommend | |
| OPS-25 | **Backups and retention.** No new volume or file storage: leads and the new Custom Fields live in the site database and are covered by the existing database backups and the pre-deploy `bench --site all backup --with-files` (Fact, `DEPLOYMENT_RUNBOOK.md` lines 41, 176). A lead deleted under the retention rule (brief Q4) still sits in older backups until they age out, and the notice must say so. **Unknown:** I could not find where the scheduled backup retention period is set, so I cannot give the number | DPDP: the notice must be true about how long data is kept | A notice that promises deletion we do not do | P2 | Recommend | |
| OPS-26 | **Monitoring: one log line per refusal.** Each refused save writes one line through `frappe.logger("event_form")`: time, hashed route, reason (`limit`, `closed`, `banned_field`, `invalid`). No name, phone, email or answer. During the first live events, the operator counts refusals with a written read-only command (that log, plus 429/503 lines for the save path in the nginx container's log). No automatic alert in v1 | The user must be able to tell a live event is being refused. The brief's success measure (leads ÷ save presses) needs the refusal count. Today nothing would show it | Refusals at an event stay invisible until the organiser complains | P2 | Recommend | |
| OPS-27 | **Automatic alert, only if wanted:** add a refusal count to the existing hourly `worker-health.yml` check rather than any new tool, once the first events show refusals matter | Reuses what already runs; no new monitoring stack | Someone must watch by hand at each event | P3 | Consider | |
| OPS-28 | **No personal data in logs, errors or Redis.** Limiter keys hold the route hash only (as `_limited` already does). If the save fails, it logs the route and the error type, never `form_dict`. A test forces a failure on the OPS-23 site and checks that the Error Log row and the log file hold none of the submitted values | `nfr-budget.md`: personal data in logs "never". **Unknown:** whether Frappe v16.35.0 copies the request into the Error Log on an uncaught error | A traceback full of attendee phone numbers | P1 | Recommend | |
| OPS-29 | **Secrets: none new.** The guest call carries no key or token of ours; nothing is added to `server.env` or any compose file; no captcha key (OPS-3) | Nothing to rotate or leak | - | FYI | FYI | |
| OPS-30 | **Guest permission check before every deploy of this slice, and on each tenant before an event form goes live** (OPS-14 made a gate). Read-only, per site, printed as PASS (zero rows) or FAIL: Guest rows in `tabCustom DocPerm` and `tabDocPerm` on `User`, `Employee`, `CRM Lead`. Also list which roles can read `CRM Lead` (role, read, export, share). **No command was run:** the engineer writes the two read-only `select` statements (run through `bench --site <site> mariadb`) and proves them on the OPS-23 site first, with one Guest row added on purpose so the check is seen to FAIL (lesson 19: a zero from a failed command looks like a clean zero) | `grant_guest_link_access` adds a site-wide Guest row with one click (§2) | Up to 500 staff names public on a poster link | P1 | Recommend | |
| OPS-31 | **Page speed measurement (OPS-16 made a gate).** Chrome DevTools, cache disabled, a custom throttling profile written out in numbers (1.6 Mbps down, 750 kbps up, 562.5 ms latency, the classic "Fast 3G" values, so a renamed preset cannot change the test). Five loads of `/event-form/<route>` with a 10-field form (7 standard plus 3 extras). Record bytes transferred, first draw and load. **Pass: the slowest of five within 2.5 s** (`nfr-budget.md`, 3G p95). First on the OPS-23 local site, then on dev before release. Also confirm no request leaves the tenant's own host (no Google Fonts, OPS-13) | Every figure in §2 is arithmetic, not a measurement | A page that misses the budget on the phones it is for | P2 | Recommend | |
| OPS-32 | **Release gate: 300 saves in 5 minutes on dev, from one address.** One dev tenant with CRM, one published event form. A plain script (curl or Python already on the machine; no new tool) sends 300 saves from one machine: 60 in the first 10 s, the rest spread over 5 minutes; a refused save is retried once after 10 s, as an attendee would under D2-A. CRM assignment and email settings on as the customer will use them (OPS-24). **Pass:** at least 297 stamped leads; save p95 within 500 ms; no 5xx other than the limit answers; no new Error Log rows; both queues still have live workers afterwards (`scripts/check_workers.sh`). Run it outside DTC's busy hours and not during a deploy, because dev shares the server with production. Afterwards, delete the test leads by their event stamp. Changing a dev tenant's data needs the user's word (CLAUDE.md §1) | Every load figure so far is an estimate. Dev does not carry production's tenants, so a pass is needed but does not prove production headroom (inference: production shares 4 workers x 2 threads, §1) | The first real event becomes the load test | P1 | Recommend | |
| OPS-33 | **A test that CRM's fields still exist.** One test checks the CRM Web Form fields our page reads (`crm_published` and the field list, §2 OPS-12). It runs in the normal suite, so a CRM pin change that renames them goes red in CI | Our page reads another app's record | The form silently breaks for attendees after a CRM upgrade | P3 | Recommend | |

### Questions

**Must know:** none blocks the spec. Defaults are in the rows.

**Should know:**
1. *Is 300 a minute per event the right cap?* My reading: it lets a full hall through in one
   minute and caps spam. The security engineer may want it lower. Default: 300 per 60 s.
2. *Where is the scheduled backup retention set, and for how long?* It changes the notice
   text (OPS-25). I could not check it. Default: the notice says "and in backups for up to
   N days", with N filled in before switch-on.

### What I did not check

- Nothing was run: Docker was not running on this machine. No limit, timing or page weight
  was measured.
- Frappe's limiter and CRM Lead's hooks on the pinned versions (OPS-23, OPS-24).
- Whether Frappe's general per-address limit (`rate_limit` in site config) is set on dev or
  production. If it is, it is one more limit in front of the save; OPS-32 would show it.
- Scheduled backup retention (OPS-25). Dev's gunicorn worker count.
- The OPS-30 check has not been run anywhere.

### Left behind

Nothing. I only read files and ran `grep`, `sed` and `ls` on the checkout. No container,
site or setting was touched.

### Subtract pass

Removed: an app-level per-address limit (nginx already has one; add only if OPS-32 says so),
a request-size limit row (the field types and the security engineer cover it), a new
dashboard or alert service for refusals (a log line and the existing hourly check do it), a
separate staging load test (dev is enough as a gate), and a backup change (the database
backup already covers the new rows).

---

## §4 Strategy - 13 Nov 2026

Sources read: `00-impact-analysis.md` (engineer, base `origin/dev` c3885fad), the worktree
`.claude/worktrees/082-event-form` (clean, no product code yet), `.github/workflows/ci.yml`,
`.github/workflows/worker-health.yml`, `deploy/Dockerfile`, `scripts/check_version_pins.py`,
`patches.txt`. Read-only reads inside the engineer's container `hrlocal-qr082` (Frappe
v16.35.0, CRM v1.84.0): `frappe/modules/utils.py`, `frappe/permissions.py`,
`custom_docperm.py`, `frappe/installer.py`, `frappe/modules/patch_handler.py`,
`frappe/utils/logger.py`, `crm/api/form.py`, `helpdesk/.../hd_ticket.py`, and one read-only
`select` on `qr082.localhost`. Decisions already made by the user: R1 = option A (300 per 60 s
per event, no address limit in our code); OPS-27 alert = yes (AC-73, threshold 30 to confirm).

### Bad news first

**1. CI does not install Frappe CRM, so every test that needs CRM Lead will skip in CI (P1).**
Fact: `ci.yml` lines 470-475 install only `erpnext`, `hrms`, `alvoraa_portal` and
`alvoraa_goals` on `test_site`; there is no `get-app crm` anywhere in the file. The slice 057
tests skip when CRM is missing (Fact, `test_ai_leads_whatsapp_057.py` line 50). So the guest
save, the door tests (AC-61 to AC-64), the CRM Lead variant of the Guest-row hook and the
OPS-33 "CRM fields still exist" test would all pass in CI by skipping. A gate that cannot fail
proves nothing. The engineer's analysis does not mention this. See OPS-36.

**2. The OPS-27 alert cannot see the refusal most likely to happen (P2).** The app's
`event_form` log only records refusals that reach Frappe. A venue Wi-Fi refused by nginx's
`/api/` limit gets a **503 from nginx, and Frappe never sees the request** (§3 bad news 2).
§3 estimated that as the likeliest refusal at a busy event; the app's own 300-a-minute limit
should rarely trigger. Counting only the app log would stay green while a hall is being
turned away. See OPS-38.

**3. The alert is hourly and best-effort, so it is not a live alarm.** Fact
(`worker-health.yml` lines 27-31 and the `cron: "0 * * * *"` line): it runs once an hour and
"can be late by several minutes". A two-hour event can be over before the first alert. And an
alert only reaches an inbox if "Send notifications for failed workflows only" is on, which
the same file still marks "⚠ CONFIRM ONCE". I could not check that setting.

### Agree or disagree with the engineer

| Engineer's point | My view | Evidence |
|---|---|---|
| No image, Compose or nginx change; no new package (PyQRCode and pypng are in the image) | **Agree** | Fact: `CRM_TAG=v1.84.0` already in `deploy/Dockerfile` line 67; no compose edit in the plan; §3 OPS-21 |
| Fields by a patch guarded on CRM Lead existing, plus `after_app_install` for tenants that get CRM later; never a fixture | **Agree** | Fact: `frappe/installer.py` lines 363-364 call every app's `after_app_install(name)` on `install-app`, which is how `tenant_api` adds CRM after the wizard |
| The `Custom DocPerm` validate hook is low risk to migrate | **Agree, with the evidence below** | See "Migration risk" |
| A `window` argument on `_limited` with the default unchanged, pinned by tests | **Agree** | 31 callers, none passes `window` (engineer's count, not re-counted by me) |
| CEILINGS row for `event_form.py` = 1; the `frappe.db.delete` clean-up listed in `03`, not in the gate | **Agree** | The gate counts only the word `ignore_permissions` (engineer). Listing it is the right minimum |
| Caught errors logged with a message, so Frappe does not add local variables | **Agree** | Engineer read it on v16.35.0; the OPS-28 test proves it |
| OPS-27 alert only runs after a release to `main` | **Agree, and it is worse than "inert on dev"** | See OPS-37 |
| (Not raised) CI has no CRM | **Add** | Bad news 1 |
| (Not raised) the alert misses nginx's 503 | **Add** | Bad news 2 |
| (Not raised) our patch runs before model sync | **FYI** | See "Migration risk" |

### Install order

1. **Deploy and migrate, every tenant.** Our patch runs. Where CRM Lead exists, it creates the
   five Custom Fields (an `ALTER TABLE` on `tabCRM Lead`; small table, estimate seconds).
   Where CRM is absent, it does nothing and is marked done.
2. **A tenant that gets CRM later** (`tenant_api` installs it after the setup wizard):
   `after_app_install("crm")` creates the same fields. `ensure_fields()` must run safely twice
   (`create_custom_fields` updates a field that exists).
3. **The page and save need nothing else.** No site config, no scheduler, no new job.

**Prove on the local site before commit:** install CRM *after* our app on a fresh site and
see the five fields appear; run `migrate` twice and see no error and no duplicate field.

### Migration risk

| Risk | Reading | Label |
|---|---|---|
| Our patch runs **before** model sync | `patches.txt` has no `[pre_model_sync]`/`[post_model_sync]` headers, so Frappe treats every line as pre-model-sync (`patch_handler.py` lines 122-126). Safe here because CRM Lead already exists on every CRM tenant. **Do not ship this slice in the same release as a `CRM_TAG` change**, or our fields could be written before CRM's own table changes | Fact (code); inference (safe) |
| Five new columns on CRM Lead on every CRM tenant | Empty columns; a slow `ALTER` only on a large table. I do not know which tenants have CRM or how many leads they hold | Unknown - counted before release (OPS-35) |
| The Guest-row hook stops a migrate | Frappe's customisation sync writes `Custom DocPerm` with `db_insert()` (`modules/utils.py` line 163), which **skips validate hooks**, so a shipped `custom/*.json` cannot trip it. No app in the image ships a Guest row in a `custom/*.json` (grep across every app's `custom` folder: none). The only code that grants Guest rows: CRM's `grant_guest_link_access` (meant to be stopped), Helpdesk on `HD Ticket` only (not in the hook's list), and a Frappe test. The Role Permission Manager saves through `update_custom_docperm` → `doc.save()` (`custom_docperm.py` line 47), so the hook does catch hand edits | Fact (code) |
| The hook breaks an existing tenant | Only when an existing Guest `read`/`select` row on User, Employee or CRM Lead is **saved again**. `qr082.localhost` has 0 Guest rows in `tabDocPerm` and `tabCustom DocPerm`, but it holds only Frappe and CRM. Dev and production not counted | Measured 13 Nov on `qr082.localhost`; unknown elsewhere |
| Rollback | Redeploy the previous tag with migrations off (lesson 20). The five fields stay, empty, harmless. The hook goes away, so CRM's Guest-grant button works again as it does today. Leads saved meanwhile stay | Inference. Whether the previous tag exists in the package: §5 |

### Recommendations

| ID | Recommendation | Why | Cost of ignoring it | Level | Kind | Decision |
|---|---|---|---|---|---|---|
| OPS-34 | **No image, Compose or nginx change in this slice.** The review confirms `git diff origin/dev -- deploy/` is empty, and `scripts/check_version_pins.py` stays green (unless OPS-36 adds a CI pin) | The plan needs none; any edit to `deploy/nginx.conf` restarts the live proxy (lesson 13) | An unplanned production change rides a dev push | P1 | Recommend | |
| OPS-35 | **Before the release, a read-only count per tenant on dev and production:** which tenants have `crm` installed, how many CRM Lead rows each holds, and the OPS-30 Guest-row check. Counts only, run on the user's word | Tells us where the `ALTER` and the hook land, and whether the hook will refuse a row that already exists (engineer R4) | A tenant's next permission edit fails with no warning; or a slow `ALTER` mid-deploy | P2 | Recommend | |
| OPS-36 | **Make the CRM tests run in CI.** Recommend: in `ci.yml`, `bench get-app --branch "$CRM_TAG" crm` and `install-app crm` on `test_site` after our apps (the wizard-then-CRM order from `provision_tenant.sh`), with `CRM_TAG` added to `check_version_pins.py` so CI and the image cannot drift. Measure the extra CI minutes on the first run. If the cost is too high, the fallback is to run `test_event_form_082` on the engineer's local CRM site before every push and paste the output in the review. The fallback does not catch a future `CRM_TAG` bump | Bad news 1. OPS-33's field test exists only to catch a CRM upgrade in CI | Every CRM test "passes" by skipping; a CRM upgrade silently breaks event forms | P1 | Recommend | |
| OPS-37 | **Test the OPS-27 step on dev by hand; expect nothing from the schedule until `main`.** Fact: the workflow's only triggers are `schedule` and `workflow_dispatch`; GitHub runs a scheduled workflow from the default branch's copy (lesson 14), and `actions/checkout` then fetches `main`'s script too. So **no scheduled alert covers the dev load test (OPS-32) or any event before the release to main.** During OPS-32, watch with the OPS-26 manual command. After it, the user may start one run of dev's copy (`gh workflow run "Worker health" --ref dev`, for the user to approve). That run reads both stacks, production included, read-only | The automatic run never sees dev's file | The alert ships to production untested; or someone believes dev is watched when it is not | P2 | Recommend | |
| OPS-38 | **Count nginx's 503s too.** The alert script also counts 503 answers for the save path in the nginx container's log for the last hour, and prints counts only, never log lines (they hold IP addresses). nginx sees one path for every event, so this count is per stack, not per form | Bad news 2 | The alert stays green while nginx turns a hall away | P2 | Recommend | |
| OPS-39 | **The alert step must not hide the worker check.** Make it a separate step with `if: always()`, kept inside the job's 10-minute timeout (the worker check can wait 180 s per stack). Its error line names "event form refusals", so a red run says which check failed | The worker check is the reason the workflow exists (10 Sep incident) | A red run from an event is read as a worker failure, or a worker failure is skipped | P2 | Recommend | |
| OPS-40 | **Read the rotated logs and use one clock.** Frappe's logger rotates at 100 KB and keeps 20 files (Fact, `utils/logger.py` lines 38-45), so the script reads `event_form.log*`. The log time is the container's clock; the script must work out "the last 60 minutes" in that same zone. Prove it on the local site with planted lines at known times, including one that must make it FAIL (lesson 19) | A zero from a missed file looks like a clean zero | An alert that can never fire | P2 | Recommend | |
| OPS-41 | **Threshold: 30 refusals per form per hour (AC-73), plus the nginx 503 count against the same 30.** 30 is 10% of a 300-person hall, the engineer's number. Estimate only; no event has run | Something must turn a count into a red run | Too low: alerts on a photographed poster after the event. Too high: a lost hall | P3 | Consider | |
| OPS-42 | **Keep the CRM pin and this slice tied.** A comment beside `ARG CRM_TAG` in `deploy/Dockerfile` names slice 082's dependence on `crm_published`, `module = "FCRM"` and the builder's field list, and any `CRM_TAG` change re-runs `test_event_form_082` on a CRM site | Our page reads another app's record (engineer's main trade-off) | A CRM bump breaks the form with nobody told | P4 | Consider | |
| OPS-43 | **FYI for the security engineer:** Frappe's stock `/<route>` and CRM's `/crm-form/<route>` stay open for every published CRM form (engineer, W3). They save through `accept()`, which skips our consent checks, our event stamp and our limit (it has its own 10 a minute per address) | One form, three doors | Leads without our consent check, through a door the organiser does not know about | P2 | FYI | |

### CI gates, in order

| Gate | Exists? | For this slice |
|---|---|---|
| `scripts/check_app_integrity.py` | Yes (`ci.yml` lines 93, 504) | Run locally with a bench before every commit too (lesson 7) |
| `TestSec16IgnorePermissionsCeiling.CEILINGS` | Yes | One row: `event_form.py` = 1 |
| Limiter pins (`test_field_app_step6_013` and the 078/076 tests) | Yes | The 4-part tuple stays; the window stays 3,600 s for all 31 existing uses. New pin in `test_event_form_082`: `("event_form_key", "route", 300, 60)` |
| Hook pins (route rule, `Custom DocPerm` validate, CRM Lead `after_delete`, `after_app_install` list holding 057's entry and ours) | New, in `test_event_form_082` | Agree with the engineer |
| CRM-dependent tests | **Skip in CI today** | OPS-36 |
| `check_version_pins.py` | Yes, knows `CRM_TAG` | Add CI's CRM pin if OPS-36 is chosen |
| `check_nginx_parses.sh` | Yes | Not needed: `deploy/nginx.conf` unchanged (OPS-34) |

### Questions

**Must know:** none blocks the strategy gate.

**Should know:**
1. *Add CRM to CI (OPS-36), or run the CRM tests by hand before each push?* My reading: CI,
   because the OPS-33 test exists to catch a CRM upgrade, and a hand run will be forgotten.
   It costs CI minutes I have not measured. Default: add it, measure the first run.
2. *Is "Send notifications for failed workflows only" on for the repository owner's account?*
   Without it the OPS-27 alert is a page someone must go and look at. I could not check.

### What I did not check

- Dev and production: which tenants have CRM, lead counts, Guest rows. Nothing was run there.
- The extra CI minutes for installing CRM.
- The container clock zone on dev and production (OPS-40).
- Whether nginx writes an access log for `/api/` to the container log on the server. The
  config has no global `access_log` line, so it uses nginx's default `[ASSUMPTION: the image
  sends it to the container's output]`.
- I did not re-count the 31 `_limited` callers.

### Left behind

Nothing. In `hrlocal-qr082` I ran `grep`, `sed` and one read-only `select` on
`qr082.localhost`. I read the worktree without changing it. No container, site or setting
was changed.

### Subtract pass

Removed: a row asking for a new alert channel (the hourly workflow and GitHub's email are
enough once the setting is confirmed); a row splitting `patches.txt` into pre/post sections
(not needed for this slice; it would touch every existing patch); a separate CI site just for
CRM (one install on `test_site` is enough, if it does not break other suites); a dev burst to
prove the alert fires (planted log lines on the local site prove it more cheaply).

---

## §5 Release readiness - 14 Nov 2026

Sources read: `git diff 0b0cff7b..43da6e4b` in `.claude/worktrees/082-event-form` (18 files),
`03-implementation-notes.md`, `04-test-report.md`, `.github/workflows/ci.yml`,
`worker-health.yml`, `deploy.yml`, `scripts/check_event_refusals.sh` (header). Read-only
`gh` calls: CI run history for `dev`, job timings of run 43530285150, the `dev` branch head,
and the `alvoraa-app` package tag list. Nothing was run on dev, production or any container.

### Bad news first

**1. The test report still says Fail (P1).** `04-test-report.md` was written at 29ffb45b
and found D1 (an erased lead leaves copies of its notes and tasks) and D2 (a limit window
that never ends). Commit 43da6e4b says it fixes both, but no re-test is written down. Not
ready to push until the test engineer re-runs `test_event_form_082` on 43da6e4b and records it.

**2. CRM-in-CI has never run (P1 until it does).** The branch is not pushed, so the new
`install-app crm` step, the new cache key and the 057 tests that used to skip have never run
on a runner. The first green CI run on `dev` is the real proof of OPS-36.

**3. A dev deploy restarts the one nginx that also serves production.** Fact: `deploy.yml`
restarts `compose-nginx-1` on every deploy (lines 204, 390, 577). This slice does not change
`deploy/nginx.conf` (Fact: `git diff 0b0cff7b..43da6e4b -- deploy/` is empty), so production
gets the same file back. Expect the usual short blip, not a change.

### What a dev push changes

| Thing | Changes? | Evidence |
|---|---|---|
| `deploy/nginx.conf`, compose files, `Dockerfile`, `server.env` | **No** | Fact, empty `deploy/` diff |
| Image | Yes, `dev-43da6e4` (app code only; no new package) | Fact, `deploy.yml` line 151 |
| Every dev tenant with CRM | `migrate` runs `after_migrate` → `ensure_fields`: five Custom Fields on CRM Lead (an `ALTER TABLE`). Nothing without CRM | Fact, `hooks.py` diff |
| Every dev tenant | New hooks live: Guest rows on User / Employee / CRM Lead refused on `Custom DocPerm` save; delete hooks on CRM Lead, CRM Task, FCRM Note, CRM Call Log | Fact, `hooks.py` diff |
| Static assets | **None.** The page loads no `/assets/` file, so the stale `sites/assets` volume trap does not apply | Fact, grep of `www/event-form.html`; empty `public/` diff |
| The refusal alert | **Nothing.** `worker-health.yml` runs on schedule from `main`'s copy only (lesson 14). Live only after a release to `main` | Fact, workflow triggers |
| CI on every later push | Longer, see below | Estimate |

### Install and migrate order

1. Deploy the image; `deploy.yml` runs `bench --site all migrate` on dev (`migrate=true`).
2. On each site, `after_migrate` runs `ensure_fields` after the model sync. There is no patch
   row, so the §4 `pre_model_sync` risk no longer applies.
3. A tenant that gets CRM later: `after_app_install` adds the fields. A new site that already
   had CRM: `after_install` adds them.
4. Still true: **do not ship this in the same release as a `CRM_TAG` change.**
5. Proven only on the engineer's test082 (built in CI's order). The fresh-site proof is CI.

### CI time

Measured with `gh` on 14 Nov: the last six `dev` CI runs took 67-96 minutes; the last green
run's "Python tests" job took **72 min** of its 120-minute limit. **Estimate** for CRM: the
first run rebuilds the bench cache (new key), roughly +5-10 min once, inside the bench step's
45-minute limit; every later run adds `install-app crm` plus the 057 and 082 tests that now
run instead of skipping, roughly +3-8 min. Based on one more app clone and install and the
test count; not measured. Headroom to 120 min looks enough. Read the real figure off the
first run.

**Is CI the right place for the full suite? Recommend yes.** Docker Desktop stopped twice
today under memory pressure, and the shared bench competes with other sessions. The runner is
a fresh machine, builds a fresh site the way the data-doors rule asks, and its result is
visible to everyone. Locally, run only the slice's module and `test_portal_security_010`.
The cost: a failure shows up 70+ minutes after the push, and a second push to `dev` cancels
the running CI, so push once and wait.

### Recommendations

| ID | Recommendation | Why | Cost of ignoring it | Level | Kind | Decision |
|---|---|---|---|---|---|---|
| OPS-44 | **Re-test 43da6e4b before the push.** The test engineer re-runs `test_event_form_082` (51 tests) and `test_portal_security_010` on test082 and adds a dated follow-up to `04` | The only written verdict is Fail | D1 is a PRIV-5 privacy duty; D2 can hold an event's saves shut | P1 | Recommend | |
| OPS-45 | **Push once, then wait for CI to finish before any other `dev` push.** Check `gh run list --branch dev` is idle first | A new push cancels the running CI | OPS-36 never gets its first honest run | P1 | Recommend | |
| OPS-46 | **Before the push, the OPS-35/37 read-only checks on dev** (on the user's word): per dev site, is `crm` installed, CRM Lead row count, and `scripts/check_guest_rows.sh` (PASS / FAIL / ERROR; an ERROR is not a PASS) | A dev site with a Guest row already will have its next save of it refused; a big CRM Lead table makes the `ALTER` slow | A permission edit fails with no warning; a slow migrate mid-deploy | P2 | Recommend | |
| OPS-47 | **After the dev deploy, prove it landed:** `.image.dev.env` names `dev-43da6e4`; every devstack app container reports that tag (lesson 2); `scripts/check_workers.sh` green on both stacks; on one CRM dev site a published form opens at `/event-form/<route>`; the five fields exist on CRM Lead | A green deploy can hide an old tag | Testing old code and calling it proved | P1 | Recommend | |
| OPS-48 | **OPS-32 load test on one dev CRM tenant, outside DTC's busy hours, never during a deploy.** (a) 300 saves in 5 min, 60 in the first 10 s, one retry after 10 s. Pass: at least 297 leads, save p95 within 500 ms, no 5xx except limit answers, no new Error Log rows, workers alive. (b) **450 saves from one address** in 5 min. Expect nginx's 120 a minute per address to answer some with 503; record how many get through after one retry. If more than 1% are lost after the retry, stop and bring OPS-4 back as its own change. Watch with `check_event_refusals.sh devstack` during the run. Delete the test leads by event stamp afterwards | Every load figure is an estimate | The first real event is the load test | P1 | Recommend | |
| OPS-49 | **Phone checks on dev (AC-2, AC-8, OPS-31):** the page at 360 and 390 px wide with no sideways scroll; five loads under the custom profile in §3 (1.6 Mbps down / 750 kbps up / 562.5 ms), cache off; pass if the slowest is within 2.5 s; no request leaves the tenant's host | Never run; needs a real browser | A page that misses the 3G budget | P2 | Recommend | |
| OPS-50 | **One hand run of dev's alert copy after OPS-48:** `gh workflow run "Worker health" --ref dev` (for the user to approve). Reads both stacks, read-only. Expect the event step to report the load test's refusals | The schedule never runs dev's file | The alert reaches production untested | P2 | Recommend | |
| OPS-51 | **At the `main` release:** confirm "Send notifications for failed workflows only" is on for the owner's account (still unconfirmed), and read the first scheduled Worker health run to see the event step ran | Without it a red run reaches nobody | People turned away, nobody told | P2 | Recommend | |

### Rollback

- **Dev:** re-run Deploy by hand on `dev` with image tag `dev-0b0cff7` and migrations off,
  e.g. `gh workflow run Deploy --ref dev -f image_tag=dev-0b0cff7 -f run_migrations=false`
  plus the environment input **(for the user to approve; quoted, not run; check the input
  names in the Deploy form first)**. Fact: `dev-0b0cff7` exists in `alvoraa-app` (read 14 Nov).
- **Code:** `git revert` of the slice commits on `dev`, then the normal push.
- **What stays:** the five CRM Lead fields (empty, harmless) and any leads saved meanwhile.
- **Time:** plan about 15 minutes; every deploy wastes about 7 on the `bench version` wait
  (lesson 22).

### Monitoring

- Before the `main` release, nothing automatic watches an event. A person runs
  `bash scripts/check_event_refusals.sh <stack>` by hand during it.
- After `main`: the hourly Worker health event step (counts and route hashes, no personal
  data), threshold 30 per form per hour (OPS-41, still an estimate).

### Go / no-go for the push to dev

| # | Check | State 14 Nov |
|---|---|---|
| 1 | Re-test of 43da6e4b recorded; D1 and D2 pass (OPS-44) | **Open** |
| 2 | Reviewer and security review of 43da6e4b with no open P0/P1 | Not seen by me |
| 3 | `deploy/` diff empty | Pass (Fact) |
| 4 | Branch fast-forwards onto `origin/dev` | Pass at 0b0cff7b (Fact, `gh`); re-check just before the push |
| 5 | `check_app_integrity.py`, `check_version_pins.py --self-test`, `check_event_refusals.sh --self-test` green on 43da6e4b | Engineer reported; not re-run by me |
| 6 | No CI run on `dev` in progress (OPS-45) | Check at push time |
| 7 | OPS-46 read-only checks on dev | Open; needs the user's word |
| 8 | No `CRM_TAG` change in the same push | Pass (Fact) |

**The user's own gates:** (a) the word to push to `dev`; (b) the word to run the read-only
checks, the load test and the test-lead deletion on a dev tenant; (c) approving one hand run
of dev's Worker health copy; (d) later, the word for `main`, which is what turns the alert on.

### What I did not check

- Whether 43da6e4b really fixes D1 and D2. CI time with CRM. Dev's CRM tenants, lead counts
  and Guest rows. The dev container clock zone (OPS-40). The notification setting.
- The exact input names of the Deploy form for the rollback command.

### Left behind

Nothing. Only file reads, `git diff`/`log`, and read-only `gh` calls. This section was added
to this file in the main checkout and is not staged.

### Subtract pass

Removed: an nginx parse step (no nginx change); an asset refresh step (the page has no static
file); a CI timing trial before the push (the first real run measures it); restating OPS-30's
SQL (the script now exists).
