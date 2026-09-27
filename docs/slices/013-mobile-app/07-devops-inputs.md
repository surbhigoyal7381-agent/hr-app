# 013 — Mobile app (step 1) — DevOps inputs

**I advise. I decide nothing and I deploy nothing.** Every row ends in a Decision
column that is yours to fill.

One dated section per stage. Later sections are added below; nothing here gets
rewritten.

---

# §1 · 17 September 2026 — Brief

Scope read for this section: step 1 only. A Capacitor app (a native shell whose screens
are our web pages), Android first and iPhone in parallel, two tabs:

- **Attendance** — `field-checkin.html` shipped inside the app, logging in by device token.
- **My HR** — the ESS portal `/hrms-employee`, loaded from the tenant's server, logging in
  by session cookie and CSRF token (a secret that proves a request came from our page).

One app for all tenants, joined by an HR-issued enrolment QR, tenant code as fallback.
No background location in step 1.

Nothing was run for this section. No docker, no bench, no requests to any server. I read
the repo and public web pages only.

## Read this first

1. **Apple may reject step 1 as "just a website in a wrapper" (App Store guideline 4.2).**
   The native features that made the case against that — background location and push —
   are step 2, not step 1. Step 1 is a bundled page, a remote portal, secure storage and a
   camera. Plan for iPhone to reach staff through TestFlight (Apple's test channel) until
   step 2, and do not promise a public App Store date for step 1.
2. **Store accounts are the long pole, not code.** A *personal* Google Play account made
   after Nov 2023 must run a closed test with 12 testers for 14 days in a row before it can
   publish. An *organisation* account skips that, but it needs a D-U-N-S number (a free
   company ID from Dun & Bradstreet). Apple's organisation account needs one too. Start
   this in week one.
3. **Frappe's own CORS switch opens every endpoint, with cookies.** CORS is the browser rule
   that decides which other websites may call our server. In Frappe version 16,
   `allow_cors` applies to every `/api` route and always sends
   `Access-Control-Allow-Credentials: true` (read in the Frappe source on 17 Sep 2026). So
   turning it on "for the app" would also let those origins make logged-in calls to the
   portal. Do CORS in nginx, only on the device-token paths, or avoid CORS entirely (OPS-1,
   OPS-2).
4. **The remote My HR tab must not get the app's native powers.** If the portal loads inside
   the same web view as the app's native bridge, any script injection in the 17,000-line
   portal could read the device secret or use the camera. Capacitor's own docs say the
   setting that allows remote pages (`allowNavigation`) is not meant for production (OPS-3).
5. **The app cannot talk to any dev tenant today.** `*.dev.alvoraa.co` is not on the
   certificate (`deploy/nginx.conf` says so). Android and iOS apps refuse a bad certificate
   with no "continue anyway" button. The wildcard certificate is still blocked on the DNS
   decision (`008/09-wildcard-certificate.md`) (OPS-9).
6. **Our repo is public, and nothing stops a signing key being committed.** No `.gitignore`
   entries for key files and no secret scan in CI (checked). A leaked key is published to
   the world. Fix this before the first key exists (OPS-6).
7. **Every Attendance fix becomes a store release.** The bundled page only changes when
   people update the app. A web deploy that changes a field-checkin argument breaks every
   phone that has not updated — at 9 am, with a fix that waits on store review (OPS-8).

## The answer in short

- **Run cost on our servers: close to zero** (estimate). No new container, no new queue.
  A few small tables (enrolment tokens), one daily clean-up job, a few nginx lines.
- **The new cost is operating an app:** two store accounts, signing keys, a release train
  separate from web deploys, old app versions to keep working, and a Mac for iPhone work.
- **Money for step 1: about ₹10,500 a year plus ₹2,100 once** for the two store accounts,
  plus test phones, plus a Mac only if you cannot borrow one. Builds can be free (see below).
- **Two decisions block testing:** the wildcard certificate, and the store account type.

## What this adds to build and run

| New thing | What it involves | Where it runs |
|---|---|---|
| Android build | Android Studio and the Android SDK | This Windows PC for development; CI for releases |
| iPhone build | Xcode — **only runs on macOS** | A Mac, or a hosted Mac in CI |
| Signing keys | Android upload key; Apple distribution certificate and profiles | Password manager + CI secrets. **Never the repo** |
| App release train | Version numbers, store review, staged rollout | Separate from web deploys |
| Old app versions | Server must keep answering what old phones send | Tenant servers |
| App Links / Universal Links | Two small files on every tenant host so a QR link opens the app | nginx |
| Enrolment tokens | Issue, expire, redeem, clean up | Tenant site + a daily scheduled job (default queue) |
| Tenant-code lookup | One endpoint on the control plane | **Production** control plane — see "For the product manager" |
| Test devices | Low-end Android handsets from several makers, one iPhone | Desk drawer |

## Where the builds run — options and rough cost

Prices checked 17 Sep 2026 (sources at the end).

| Option | Android | iPhone | Cost | Fit |
|---|---|---|---|---|
| **This Windows PC** | ✅ Android Studio, emulator, USB phone | ❌ Xcode needs macOS | Free | Development and Android pilot builds |
| **GitHub Actions, hosted runners** | ✅ Linux runner | ✅ macOS runner | **Free while the repo is public.** If it goes private: Linux US$0.006/min, macOS US$0.062/min. **Estimate** US$1–1.5 per iPhone release build (15–25 min) | Release builds for both, run by hand |
| **Codemagic** (a hosted build service for apps) | ✅ | ✅ | 500 free macOS minutes a month on a personal account; US$0.10/min after | Only if the repo goes private and GitHub's Mac minutes add up |
| **A Mac on the desk** | ✅ | ✅ | Borrow: free. Buy a Mac mini: Indian listings I found disagree (₹79,900 and ₹99,900 for a base model) — check before buying | **Still needed** for first-time iPhone setup and debugging on a real phone. CI alone makes that painful |
| **A rented cloud Mac** | ✅ | ✅ | I could not confirm a current price | Fallback if nobody can lend a Mac |

## Signing keys — where they live

- **Android:** use **Play App Signing**. Google keeps the key that signs the app; we keep an
  *upload key*. If the upload key is lost, Google can reset it. Without Play App Signing, a
  lost key means the app can **never be updated** — a new listing, and every user reinstalls.
- **Apple:** distribution certificate, provisioning profiles and an App Store Connect API key.
  Apple can reissue them; losing them costs a day, not the app.
- **Storage:** a password manager with **two named people** who can open it, plus GitHub
  environment secrets that only a protected, manually started workflow can read. Pull
  requests from forks of a public repo do not receive secrets, which is good.
- **Never in the repo:** `*.jks`, `*.keystore`, `*.p12`, `*.mobileprovision`, `*.p8`,
  `google-services.json`, `GoogleService-Info.plist`.

## How app releases relate to web deploys

| Part | Updates when | What can break |
|---|---|---|
| **Attendance tab** (bundled) | Only when the person installs an app update. Store review: hours to days | A web deploy renames or removes an argument of a field-checkin endpoint → every older app fails to punch |
| **My HR tab** (remote) | Every web deploy, straight away | Nothing app-specific — unless the portal starts to rely on something only newer apps provide |
| **Server endpoints** (manifest, `app_config`, enrolment, punch) | Every web deploy | The contract that old apps depend on |

**The rule this needs:** field-checkin endpoints only ever *add*. They never rename or drop
an argument while an app version that sends it is still supported. `app_config` returns a
minimum app version, so the server can show "please update" instead of failing
mysteriously. The app sends its version on each call, so logs show which versions are still
in use and when an old one can be dropped.

**And one more:** build app releases only from a commit already on `main`. A build from
`dev` can ship a page that calls an endpoint production does not have yet.

## Server-side changes and their risk

| Change | Risk | How to keep it small |
|---|---|---|
| **CORS for Capacitor origins** — iOS sends `capacitor://localhost`, Android sends `https://localhost` (Capacitor 8 defaults) | **High if done with Frappe's `allow_cors`** (every endpoint, credentials allowed). Also, `https://localhost` is the origin of any local web server in an ordinary browser | nginx, exact origins, only `/api/method/alvoraa_portal.field_checkin.*`, **no** `Allow-Credentials`, answer `OPTIONS`. Or skip CORS with Capacitor's native HTTP (OPS-1, OPS-2) |
| nginx edit | **One nginx serves production and dev, and a dev deploy restarts it** (012 §2a point 4). A typing mistake takes `alvoraa.co` down. A `location` block with its own `add_header` silently drops the security headers (012 OPS-30) | Repeat the security headers in the new block. `nginx -t` before any push (012 OPS-27, approved) |
| `manifest` and new `app_config` endpoints | Low. Guest `GET`, no personal data. Must not reveal anything the host name does not already reveal | Add a rate limit; `app_config` carries no personal data |
| **Enrolment QR token** | A photographed QR, or a token in a log | Single use, 24 h expiry, stored only as a hash, bound to one employee, revocable, audited (008/10 §4a). **Put the token in the link's `#fragment`, not `?t=`** — nginx access logs record the query string, and a fragment is never sent to the server (OPS-13) |
| **Tenant-code lookup** on the control plane | Lets someone guess our customer list | Exact match, same answer for wrong and unknown codes, rate limited (008/10 §4a) |
| **Rate limits** | **Existing limits are per IP address.** nginx: 120 requests/min per IP on `/api/`. Frappe: `register_device` 10/hour, `field_checkin` 60/hour, per IP (Frappe's default key, read in source). Indian mobile networks put many phones behind one public IP (carrier-grade NAT), and a site's Wi-Fi puts every worker behind one | Key the device endpoints on the device, not only the IP (OPS-10). **Not measured** |
| App Links / Universal Links files | Low. Same file for every tenant | Static `location` in nginx for the two `/.well-known/` files (OPS-11) |

## Certificates and domains

- **What fails without a valid certificate:** Android's WebView and native network calls, and
  iOS App Transport Security (Apple's rule that apps use valid HTTPS), both **refuse the
  connection**. There is no warning page to click through. Result: a blank tab or "network
  error".
- **Today:** production tenants `<tenant>.alvoraa.co` are on a named-host certificate that
  needs a hand-run script per new tenant and stops at 100 names. Dev tenants such as
  `ppj.dev.alvoraa.co` are **not covered at all**.
- **So:** with the wildcard (option A in `09-wildcard-certificate.md`), every tenant works in
  the app the moment it is provisioned. Without it, every new customer is unreachable from
  the app until someone runs `add_tenant_cert.sh`, and dev testing needs a stopgap.
- **Do not weaken the app to cope.** A release build must never allow plain HTTP or trust a
  self-signed certificate. For the local bench, allow HTTP in *debug builds only*.
- **Custom domains later** (`attendance.customer.com`) each need their own certificate and
  their own App Links files. Out of step 1.

## Performance on phones

Budget: employee surface on a 3G phone, p95 **≤ 2.5 s**, skeleton within 300 ms
(`nfr-budget.md` §2).

| Tab | Today, 3G (measured in 012 §2a, browser) | With compression (OPS-26, approved, not built) | In the app |
|---|---|---|---|
| **Attendance** (bundled, 72 KB file) | n/a | n/a | **Page costs no download.** Only the API calls travel. **Estimate:** inside budget, set by API response time (budget ≤ 500 ms) |
| **My HR** first open | **18.4 s**, 3.6 MB | **Estimate** 6–7 s | Same as the browser. A new install is a first visit |
| **My HR** every later open | **5.7 s** — the 977 KB page is `no-store` and downloads each time | **Estimate** 1.5–2 s | Same as the browser, if the web view keeps its cache (I did not verify this) |

What this means:

- **The app does not fix the portal's weight.** My HR in the app is exactly as heavy as in
  Chrome. Compression (OPS-26) is what brings daily opens inside budget.
- **First opens stay at ~6–7 s** until the larger piece (012 OPS-33) is done.
- **Mobile data:** 3.6 MB for a first My HR open is real money on a prepaid plan. Compression
  cuts the page itself from 977 KB to about 209 KB.
- **The portal HTML must stay uncached** (it holds the user's email and CSRF token, 012 §2a
  point 5). The app must not add its own cache for it.

## Costs

Checked 17 Sep 2026 unless marked.

| Item | Cost | Note |
|---|---|---|
| Apple Developer Program | **US$99 a year** (~₹8,300) | Same price for personal and organisation. Needed for TestFlight, push, and any iPhone that is not a developer's own |
| Free Apple ID | ₹0 | App **stops opening after 7 days**, max 3 devices, no TestFlight, no push. Developer testing only |
| Google Play Console | **US$25 once** (~₹2,100) | Price not re-checked today |
| D-U-N-S number | Free | 1–5 business days per sources; **estimate** it can take longer |
| Firebase App Distribution | Free | Android test builds to named testers without the store. iPhone builds through it still need the paid Apple account |
| GitHub Actions | ₹0 while the repo is public | See the build table if it goes private |
| Mac | ₹0 borrowed; buy price unclear (see above); cloud rental not confirmed | |
| Test phones | **Estimate** ₹8,000–15,000 each for low-end Android; 3 makers (e.g. Xiaomi, Realme, Samsung); 1 iPhone, ideally borrowed | Indian handsets behave differently; this matters more in step 2 |
| Push notifications (later) | Firebase Cloud Messaging free; Apple push included in the US$99 | Adds a credential to keep secret and a send job |
| Background-location plugin (later) | Possibly a paid licence (008/10 N8) | Not step 1 |
| **Server run cost** | **Estimate** close to zero | No new container or queue |

## Recommendations, ranked

| ID | Recommendation | Why | Cost of ignoring it | Level | Decision |
|---|---|---|---|---|---|
| OPS-1 | **Recommend:** do not set Frappe's `allow_cors`. If the bundled page needs CORS, add it in nginx: exact origins `capacitor://localhost` and `https://localhost`, only on `/api/method/alvoraa_portal.field_checkin.*`, no `Access-Control-Allow-Credentials`, `OPTIONS` answered, security headers repeated in the block. Security engineer to confirm. | Frappe v16 `allow_cors` covers every endpoint and always allows credentials (source read 17 Sep 2026). The device-token endpoints need neither. | Portal session endpoints accept logged-in calls from `localhost` origins; the only defence left is the cookie's SameSite setting and the CSRF check. | Recommend | |
| OPS-2 | **Consider:** skip CORS entirely by sending the bundled page's calls through Capacitor's native HTTP (`CapacitorHttp`), so no server CORS change is needed. The engineer to compare. | Native requests are not subject to CORS. It is off by default and, when on, changes every `fetch` in the app. | A server change that could have been avoided — or an app-wide switch whose side effects nobody checked. | Consider | |
| OPS-3 | **Recommend:** the remote My HR tab runs **without** the native bridge — a separate web view or in-app browser — unless the security engineer signs off otherwise. | Capacitor's docs say `allowNavigation` is not for production. A remote page with the bridge turns any script injection in the portal into access to the device secret and camera. | One web bug becomes a device-level compromise on every installed phone. | Recommend | |
| OPS-4 | **Recommend:** open **organisation** accounts on Google Play and Apple, and apply for the D-U-N-S number now. | Personal Play accounts made after Nov 2023 need 12 testers × 14 days before publishing; organisation accounts do not. Apple organisation enrolment needs D-U-N-S. The listing then shows the company, not a person. | At least 2–3 weeks added to the first release, found late. | Recommend | |
| OPS-5 | **Recommend:** Android development on this PC. Release builds of both apps on GitHub Actions hosted runners, started by hand, from a commit already on `main`, behind a protected environment. Borrow a Mac for first iPhone setup; decide on buying one only after that. | Hosted runners, macOS included, are free for public repos. A build from `dev` can ship calls production does not support. | Mac bought before it is needed; or an app release that fails against production. | Recommend | |
| OPS-6 | **Recommend:** before any key is created, add the key and config file patterns to `.gitignore` and add a secret scan to CI. Use Play App Signing. Keep keys in a password manager with two named holders, and in GitHub environment secrets. | The repo is public. No ignore entries and no secret scan exist today (checked). | A committed key is public at once. Without Play App Signing, a lost key means the app can never be updated. | Recommend | |
| OPS-7 | **Recommend:** separate app IDs for dev and release builds (both can sit on one phone). The release build only accepts tenant hosts ending in `.alvoraa.co` (later, custom domains the control plane lists). Plain HTTP allowed in debug builds only, with a CI check that the release build has none. | A QR is just a link; anyone can print one. | A planted QR points the app at someone else's server, which then receives photos and location. Or a release build ships with HTTP allowed. | Recommend | |
| OPS-8 | **Recommend:** a written compatibility rule — field-checkin endpoints only add; `app_config` returns a minimum app version; the app sends its version on each call; a test calls the endpoints the way the oldest supported app does. **Estimate:** support each app version for at least 90 days. | Old app versions stay installed for months. | A web deploy stops punches on every older phone at shift start, and the fix waits on store review. | Recommend | |
| OPS-9 | **Recommend:** make the wildcard certificate decision (option A) before app testing on dev tenants. Stopgap if it slips: add the specific dev tenant hosts needed for testing to the current certificate. | Apps refuse bad certificates with no bypass. `*.dev.alvoraa.co` is not covered. | The app cannot reach any dev tenant; each new production tenant is unreachable in the app until a script is run by hand. | Recommend | |
| OPS-10 | **Recommend:** rate-limit device endpoints by device (and keep a looser IP limit), and review the nginx 120/min-per-IP limit for app traffic. Measure at the pilot. | All current limits are per IP. Many phones share one IP on Indian mobile networks and on site Wi-Fi. **Not measured.** | A 60-person site at 9 am gets "too many requests" on check-in. | Recommend | |
| OPS-11 | **Recommend:** serve `/.well-known/assetlinks.json` and `/.well-known/apple-app-site-association` from nginx for every tenant host. Test with `nginx -t` before any push (012 OPS-27). | QR links open the app only if these files exist on the host in the link. | QR opens the browser instead of the app. Or an nginx typo, pushed to dev, takes production down. | Recommend | |
| OPS-12 | **Recommend:** build compression (012 OPS-26, already approved) before the app pilot, and measure the My HR tab on a throttled phone at the pilot. | The app does not make the portal lighter. | My HR takes 5.7 s on every open on 3G, and the app gets the blame. | Recommend | |
| OPS-13 | **Recommend:** put the enrolment token in the link's `#fragment`, not in `?t=`. The app and the web page read it and send it in a POST body. Clean up expired tokens with a daily job. | nginx access logs record query strings; a fragment never reaches the server. Lesson 9: secrets never in logs. | Live enrolment tokens sit in access logs for 24 hours. | Recommend | |
| OPS-14 | **Consider:** crash reporting (for example Firebase Crashlytics, free) from the first pilot. If used, add Google to the sub-processor register and keep personal data out of crash reports. | Without it, "the app closed" reports from the field cannot be traced. | Pilot bugs cannot be reproduced; or personal data sent to a third party without being declared. | Consider | |
| OPS-15 | **FYI:** Google Play requires new apps and updates to target Android 16 (API 36) since 31 Aug 2026. The bar rises every August. | Recurring yearly work, even with no feature changes. | Updates rejected until the app is rebuilt for the new level. | FYI | |
| OPS-16 | **FYI:** Android developer verification starts 30 Sep 2026 in Brazil, Indonesia, Singapore and Thailand, and goes worldwide in 2027. Apps on Google Play are registered automatically; APKs shared outside Play will need our developer registration. | Sideload and Firebase test builds to Indian phones are affected from 2027. | Test builds stop installing on certified phones in 2027. | FYI | |
| OPS-17 | **FYI:** keep `X-Frame-Options: SAMEORIGIN`. It means My HR cannot be put in an iframe inside the bundled app — use a web view instead. | The header protects against clickjacking (a hidden page tricking clicks). | Someone removes the header to make an iframe work. | FYI | |
| OPS-18 | **FYI:** production's `Permissions-Policy` sets `camera=()` (008 OPS-14). It does not affect the bundled Attendance page, which nginx does not serve. It would block any camera use in the remote My HR tab on production. | Known from slice 008. | A future camera feature in My HR works on dev and fails on production. | FYI | |

## For the product manager, before sizing

1. **iPhone "in parallel" means a Mac and US$99 from day one**, for anything beyond one
   developer's own phone. A free Apple ID build stops opening after 7 days.
2. **Plan iPhone step 1 as TestFlight only.** Public App Store approval is at real risk until
   step 2 adds background location and push (Read this first, point 1).
3. **Budget store time into every Attendance change.** After launch, a fix is a web change
   *and* an app release *and* a review wait, and old versions must keep working (OPS-8).
4. **Two decisions gate the schedule:** the store account type (OPS-4) and the wildcard
   certificate (OPS-9). Neither is code.
5. **The tenant-code fallback runs on the production control plane.** Dev and pilot builds
   need either their own lookup on dev, or the QR route only. Decide which before sizing.
6. **How the My HR tab is embedded (OPS-3) changes the effort.** A bridge-free web view or
   in-app browser is slightly more work and a slightly less seamless feel than the simplest
   setup.
7. **Promise the pilot nothing about My HR speed** until compression is live (OPS-12).

## What I did and did not check

| Checked | How |
|---|---|
| Plan and page facts | Read `008/10-native-app-background-geofence.md`, `008/09-wildcard-certificate.md`, `008/07-devops-inputs.md` OPS-14, `012/07-devops-inputs.md` §2a |
| nginx headers, rate limits, certificate coverage | Read `deploy/nginx.conf` in git. **The live server file was not read** (production wall) |
| Rate limits on field-checkin endpoints | Read `alvoraa_portal/alvoraa_portal/field_checkin.py` |
| The page uses relative API paths, `credentials: "omit"`, and `localStorage` | Read `field-checkin.html` |
| CI, build and deploy | Read `.github/workflows/ci.yml`, `build-image.yml`, `deploy.yml` (header); `deploy/Dockerfile` (Frappe `version-16`) |
| Repo is public | `gh repo view` (reads GitHub, not our servers) |
| No key patterns in `.gitignore`, no secret scan in CI | grep |
| Frappe CORS and rate-limit behaviour | Frappe `version-16` source on GitHub, 17 Sep 2026 |
| Prices, store rules, Capacitor defaults | Web sources below, 17 Sep 2026 |

**Not checked:** Frappe's session cookie SameSite setting; how Frappe picks the client IP
behind nginx; whether an app web view keeps its HTTP cache like Chrome; the Google Play fee
today; a current Mac mini or cloud Mac price; whether wildcard App Links verify cleanly for
`*.alvoraa.co` on Android and iOS. Nothing was run on the local bench, dev or production.

## Sources (read 17 Sep 2026)

- [Frappe v16 `app.py` — `set_cors_headers`](https://raw.githubusercontent.com/frappe/frappe/version-16/frappe/app.py)
- [Frappe v16 `rate_limiter.py`](https://raw.githubusercontent.com/frappe/frappe/version-16/frappe/rate_limiter.py)
- [Capacitor configuration (v8) — schemes, `allowNavigation`](https://capacitorjs.com/docs/config)
- [Capacitor HTTP API](https://capacitorjs.com/docs/apis/http)
- [GitHub Actions billing — free standard runners on public repos, per-minute rates](https://docs.github.com/en/billing/concepts/product-billing/github-actions)
- [GitHub — reduced hosted runner pricing, 1 Jan 2026](https://github.blog/changelog/2026-01-01-reduced-pricing-for-github-hosted-runners-usage/)
- [Codemagic pricing docs](https://docs.codemagic.io/billing/pricing/)
- [Play Console — testing requirements for new personal accounts](https://support.google.com/googleplay/android-developer/answer/14151465?hl=en)
- [Play Console — target API level requirements](https://support.google.com/googleplay/android-developer/answer/11926878?hl=en)
- [Android developer verification](https://developer.android.com/developer-verification)
- [Apple — program enrolment](https://developer.apple.com/help/account/membership/program-enrollment/)
- [Apple — membership comparison (free vs paid)](https://developer.apple.com/support/compare-memberships/)
- [Apple Developer account cost in India, 2026](https://colorleaves.in/blog/apple-developer-account-cost-india/)
- [Firebase pricing](https://firebase.google.com/pricing)
- [Mac mini India price report](https://www.techlusive.in/news/mac-mini-now-starts-at-rs-79900-in-india-as-apple-removes-cheaper-model-1660397/)

---

# §2 · 17 September 2026 — Design

Read for this section: `01-product-brief.md` with its gate decision, `01b-ux-design.md`,
`prototype-v1/index.html`, §1 above, `nfr-budget.md`, `www/field-checkin.html`,
`www/field_checkin.py`, `field_checkin.py`, `subscription.py` (`requires_feature`) and
`deploy/nginx.conf` in git. Frappe `version-16` source on GitHub for logging, rate limits
and client IP, read 17 Sep 2026.

Nothing was run. No docker, no bench, no request to any server, no app build. Every size
and time below is an **estimate** unless it says "read in code".

## Read this first

1. **Frappe's per-IP rate limits can be dodged by anyone, on dev and production, today.**
   Our nginx *adds* the caller's address to any `X-Forwarded-For` header the caller sends
   (`$proxy_add_x_forwarded_for`). `X-Forwarded-For` is the header that tells the app
   server who the real caller is. Frappe trusts the *first* address in it
   (`frappe/auth.py`, `set_request_ip`). So a caller who sends a made-up address gets a
   fresh Frappe rate-limit bucket on every request. This hits `register_device` (10 an
   hour) and `field_checkin` (60 an hour) now, and every Frappe IP limit the join endpoints
   would add. It also means IP addresses in Frappe's own logs can be faked. nginx's own
   limits (`limit_req`) use the real address and are not affected. **Read in the git copy
   of `nginx.conf` and Frappe source. Not tested. The live server file was not read**
   (memory says it has TLS blocks not in git, so it may differ). Production has no live
   customers (14 Sep 2026). Security engineer to confirm (OPS-19).
2. **A server error during a punch writes the photo and the GPS position into the logs.**
   On any 5xx error, Frappe writes the request's fields to `logs/frappe.log`. It hides only
   fields whose *name* contains `password`, `secret`, `token`, `key` or `pwd`. So `photo`
   (the whole picture as text, about 50 KB), `latitude` and `longitude` go in as they are.
   The Error Log record also keeps local variables, cut to 1,000 characters each: GPS and
   the employee's name among them. These copies are not deleted by the photo retention job.
   **Read in Frappe source (`utils/logger.py`, `utils/error.py`, `utils/__init__.py`). Not
   reproduced.** The join endpoints would add the QR token to this path unless its field
   name contains `token` (OPS-20).
3. **Today's device check lets any new status through.** `_device_from_token` refuses only
   `Blocked` and `Pending`. D3 (Replaced), D10 (Removed) and D5 (Stopped) add new statuses.
   Unless the check becomes "only `Active` passes", a replaced or removed phone keeps
   punching (read in code; OPS-28).
4. **At a busy depot, today's limits refuse workers.** The punch limit is 60 an hour *per
   IP*. Behind one site Wi-Fi or one mobile-network address, the 61st punch in an hour is
   refused. nginx allows 120 API requests a minute per IP (burst 30). **Estimate:** 400
   workers each opening the app and punching within 5 minutes is about 160 requests a
   minute, which nginx refuses too (OPS-29).
5. **The prototype loads Google Fonts from the internet.** Fine for a review file. The app
   must not: it would tell Google every worker's IP address at every open and fail with no
   signal. Today's web page already uses the phone's own fonts (OPS-22).

## The answer in short

- **Install once: about 5–8 MB** from the Play Store. The Attendance page itself costs no
  download after that.
- **Joining uses under 20 KB.** The first check-in adds one photo, about 35–80 KB on the wire.
- **Every later open: one small call**, about 1–2 KB. The web page downloads its 72 KB page
  on every open today.
- **Photo: keep today's size.** Long edge at most 640 px, JPEG quality 0.6, aim under 60 KB,
  never over 150 KB from the phone.
- **Five screens make a server call:** checking the code, "This is not me", "Agree and
  finish", opening the app, and Check In/Out. Everything else works from memory.
- **The design decisions are cheap to run.** Their risks are in enforcement: statuses that
  slip through (point 3), a block that the desk can undo, and a notice change that locks
  out web-page phones.

## 1. App size and first-open speed

### What goes inside the app

| Part | In the app | Size, **estimate** | Note |
|---|---|---|---|
| Attendance page (HTML, CSS, JS, words in EN and HI) | Yes | 72 KB today (read). **120–180 KB** with the join, problem and settings screens. Stored compressed in the package, about 40–60 KB | Loaded from the phone's storage. No network |
| Icons | Yes, as inline SVG (small drawings written into the page) | A few KB | Keep the web page's way. No icon font |
| Fonts | **No.** Use the phone's own (Roboto; Android's built-in Devanagari font) | 0 | Bundling Inter plus Noto Sans Devanagari would add **300–600 KB** for a look few people notice |
| Capacitor runtime and Android code, shrunk by R8 (Android's build step that removes unused code) | Yes | **3–5 MB** | Based on one public case: a Capacitor app fell from 13.1 MB to 5.9 MB, and that included Firebase and 1.65 MB of web files (Sep 2023 post). Not measured by us |
| QR reader: Google ML Kit barcode scanning | Yes | **+2.4 MB** if the reading model is inside the app; **+200 KB** if Google Play services downloads it (Google's figures, read today) | See OPS-23 |
| Secure storage plugin | Yes | Small | Holds the device secret in Android's Keystore (the phone's locked key store) |
| Splash and app icons | Yes | ~0.2 MB as WebP | PNG splash images are the usual bloat |

**Expected download from Play: about 5–8 MB (estimate).** Play sends each phone only the
parts for its processor. A test APK (the Android install file) shared through Firebase
holds every processor type and can be **2–3 MB larger**. Build test APKs for ARM phones
only (`arm64-v8a`, `armeabi-v7a`). Low-end phones often run 32-bit Android.

### First open on a low-end phone

| Step | Network | Time, **estimate** |
|---|---|---|
| Tap icon → first screen drawn | None | **1–2.5 s** on a low-end phone. Mostly Android starting the WebView (the built-in browser engine the app runs in). Not a network cost. Measure on the three pilot phones |
| First launch → "Scan the QR code" | None | Instant once drawn. Nothing is fetched before the scan |
| Every later open → Attendance screen with today's punches | One call, 1–2 KB | **About 1.5–2.5 s** on 3G: a new secure connection costs about 3 round trips, then the call, then the server's ≤ 500 ms. Show the saved screen at once, mark it "updating", then fill in |

Budget check (`nfr-budget.md` §2: ≤ 2.5 s p95 on 3G, skeleton within 300 ms): **likely inside
it**, because the page never travels. The risk is WebView start-up on cheap phones, not the
network. The pilot measures it.

### Data for the first check-in, compared with today's web page

Throttling profile used for times: 750 kbps upload, the same profile 012 §2a measured with.

| Step | App, **estimate** | Web page today, **estimate** |
|---|---|---|
| Install | 5–8 MB once, ideally on Wi-Fi | Nothing to install. "Add to Home Screen" instead |
| Open the page | 0 KB | 72 KB (read; nginx sends it uncompressed — no `gzip` in `nginx.conf`, 012 OPS-26 approved but not built), plus manifest, icon, service worker |
| Join | Check the code 3–5 KB (includes the notice rows in two languages) + Agree and finish ~2 KB + connection set-up ~5 KB | Register ~2 KB, then waits for HR |
| First check-in | Photo 35–80 KB on the wire + ~1 KB | Same photo, same size |
| Upload time for the photo | **0.5–1 s** at 750 kbps; 1.2 s at 400 kbps | Same |
| **Each later day, two opens** | ~4 KB of calls | ~150 KB of page downloads, every day |

Over a month a web-page user downloads about **3–4 MB of page** before any photo. The app
pays back its install in data in about two months, and it is faster from day one.

**The punch takes longer than the network.** Getting a GPS fix can take several seconds
(the page waits up to 18 s). The network part of a punch is about 1–2 s. Speed complaints
at the pilot will most likely be GPS.

### The photo

**Today (read in code):** the page takes a 640 × 640 camera stream, draws it 480 px wide,
saves it as JPEG quality 0.6, and sends it as base64 text (a way to send a picture inside
JSON, 33% bigger than the file). The server refuses anything over 400 KB. The server
comment says "about 80 KB"; nobody has measured it. The page comment still says "2 MB";
that is out of date.

**Recommend:**

| Setting | Value | Why |
|---|---|---|
| Size | **Long edge at most 640 px, short edge at most 480 px.** Never make a small picture bigger | A face at 480 px wide is easy for HR to recognise. More pixels add bytes, not proof |
| Quality | **JPEG 0.6** | Today's setting. Enough to tell two people apart |
| Target | **Under 60 KB** as a file (about 80 KB as text) | ~1 s upload on 3G |
| Phone-side cap | **If over 120 KB, save again at quality 0.45. Never send over 150 KB** | A bright, busy background can double the size |
| Server backstop | **Keep 400 KB** | Already built |
| Measure | Server records **photo size only** (number of bytes, no picture, no name) per app version during the pilot | Replaces two guesses with a number |

**Storage, estimate:** 400 field workers × 2 punches × 26 days × 50 KB ≈ **1 GB a month**.
With the 90-day retention the steady state is about **3 GB per tenant**, and every
`bench backup --with-files` copies it again.

## 2. Calls per screen, and what the phone may keep

### Join flow

| Screen | Server call | What the answer must carry, so the next screens need no call |
|---|---|---|
| First launch, camera explained, scanner, "not an Alvoraa code", "no QR in picture" | **None** | Host check is done on the phone (OPS-7) |
| Checking (`checking`) | **1 POST** — check the code, use nothing | Eligibility code, or: first name + initial, designation, company, brand colour, **the notice rows in EN and HI with their version**, retention days, minimum app version |
| Is this you? (`confirm`), notice (`notice`) | **None** | From the checking answer |
| This is not me → Cancel this code | **1 POST** | — |
| Agree and finish (`joining`) | **1 POST** — use the code, set up the phone | Everything the welcome and home screens need: workplace name, radius, today's punches (none) |
| Welcome | **None** | From the answer above |

### Attendance tab

| Moment | Server call | Rule |
|---|---|---|
| App opens | **1 POST** (`field_status`) | Carry the gate facts in the same answer: device state, minimum app version, current notice version. **One call on open, not two** |
| App comes back to the front | **1 POST**, at most once a minute | Today's page calls on every return. With a camera flipping in and out this adds up |
| Check In / Check Out | **1 POST** with photo | The answer includes today's punches, so home does not call again |
| Settings, "What this app records" | **None** | From saved values |
| Remove this phone | **1 POST** | Needs signal (D10) |
| Any call | — | **Phone-side timeout 30 s.** nginx waits 120 s (read), far too long for a person holding a phone. Retry only when the person taps Try again. The server's 60-second duplicate window (read) catches a retry after a lost answer |

### What the phone may keep, and what never

| May keep (app-private storage, left out of Android backup) | Never kept |
|---|---|
| Tenant host, company name, brand colour | **Device secret** anywhere except secure storage (Keystore). Never Preferences, `localStorage` (where the web page keeps it today) or WebView storage |
| Name, designation, workplace name and radius | **QR token**: in memory only, from scan to "Agree and finish" or leaving the flow. Never saved, never put in the page address or history, never in a crash or console log |
| Language choice | **Photo**: taken inside the page, held in memory, sent, then dropped. Never a file, never the gallery, never the cache. "Try again keeps your photo" means memory only; if Android closes the app, the photo is gone, which is fine |
| The notice text and version agreed, and when | **GPS position**: in memory for the one request |
| Today's punch times, shown as "last updated" with no signal | **Workplace latitude and longitude.** `field_status` sends them (read), but neither the page nor the app uses them. Do not store them |
| Last seen minimum app version | The **QR picture** chosen from photos: read into memory to decode, never copied |

Two more rules:

- **Take the photo inside the page (`getUserMedia`, as today), not with a native camera
  plugin.** A native camera plugin writes a file first and may save to the gallery. If one
  is ever needed: `saveToGallery: false`, and delete the file as soon as it is read.
- **Every device and join endpoint answers `Cache-Control: no-store`**, so no copy sits in
  the WebView's disk cache.

## 3. Error codes, minimum version and the 90-day window

**How the pieces fit:**

1. **The server sends `{code, values, message}` with a fixed HTTP status.** `code` is the
   contract. `message` stays English, for logs and **for today's web page, which still
   matches English text (MA-30)**. Do not change the English until the web page reads
   codes too, or the web page breaks.
2. **The app decides by `code` only.** When the answer is not JSON it decides by HTTP status:

   | What arrives | App shows |
   |---|---|
   | nginx 429 page (HTML) | `TOO_MANY_TRIES`, wait 60 s |
   | 502 / 503 / 504 page (HTML) | `SERVER_ERROR`, Try again |
   | A 200 HTML page — a Wi-Fi login page at a station or hotel (a captive portal) | `NO_INTERNET` |
   | JSON with a code this version does not know | `unknownCode` → check for an update |

3. **Frappe's own rate-limit refusal is English-only.** Wrap it so it also carries
   `TOO_MANY_TRIES` and `retry_after_s`.
4. **The app sends its version on every call** in a header, e.g. `X-Alvoraa-App-Version`.
   Every device endpoint compares it with the minimum and answers `APP_TOO_OLD`. No header
   means the web page, which is allowed.
5. **The minimum version lives in one constant in code**, so raising it goes through review
   and a deploy. The same image serves every tenant, so one number is enough.
6. **The 90-day promise (gate decision 7) sets when the minimum may rise:** only when the
   replacement build has been available for 90 days. The one exception is a security
   problem, and that is your call each time.
7. **Unknown code → "update the app" is the safety net, not a licence.** Inside the 90
   days the server may add a code only if an older app showing "Something went wrong,
   check for an update" is acceptable for it. Any code that asks the person to *do*
   something — like `NOTICE_CHANGED` — must be in version 1.
8. **CI keeps one contract file per released app version**: the requests it sends and the
   codes it understands. A test replays them. A file is deleted 90 days after the next
   version is out. The daily count by app version (OPS-34) shows when nobody is left on it.

## 4. What must never be public or logged

| Item | Rule | Where it could leak |
|---|---|---|
| **QR token** | Only in the link's `#fragment`; sent in a POST body; stored as a hash; the field name contains `token` | Query string in nginx logs; a GET URL used to draw the QR image; a URL shortener (it receives the whole link, fragment included); a Frappe Print Format or PDF; a field on the invite record (Frappe's Version history copies fields) |
| **Device secret** | Secure storage on the phone; hash on the server | Rate-limit keys (Frappe writes the key's value into Redis in clear, read in source); a field name without `token`/`secret`, which Frappe will not hide in logs |
| **Photos** | Private file on the check-in (already); never in logs | Request fields in `frappe.log` on a 5xx (Read this first, point 2) |
| **GPS** | Only on the check-in record | Same as photos; also the Error Log's local variables |
| **Employee names** | Never in logs, error titles or counters. Log the document name | Exception text; Error Log local variables; outcome counters (OPS-34 counts codes, not people) |
| **Printed QR sheet (D14)** | Printed **from the browser** out of the invite dialog. The server never makes a PDF or a stored file. No "email this" button. No employee ID | A Frappe print or PDF route would need the token on the server and may save a copy. A sheet left on a desk is a live code until it runs out or is used |
| **`/enrol` page** (S13) | Loads nothing from other sites; its script never reads the fragment | Google Fonts or analytics on that page would hand visitor IPs to third parties |

Note on "Copy link": WhatsApp fetches a link preview, but it never sends the fragment, so the
token stays out of that request. The picture of the QR sits in WhatsApp and the gallery. That
is accepted: it stops working once used, cancelled or run out.

## 5. Rate limits for the new endpoints

**Why not only IP:** many phones share one address, and Frappe's IP can be faked (point 1).
**Why not the raw token:** Frappe's `rate_limit(key=…)` puts the key's value into Redis in
clear. The code already avoids this (read: comment on `field_checkin`).

**Recommend:** a small counter keyed on the **SHA-256 hash** of the token or device secret.
The hash is already what the database stores, and it cannot be used to log in. Plus a real-IP
ceiling in nginx.

| Endpoint | Per code or phone (hash-keyed), **starting numbers** | Per real IP (nginx) |
|---|---|---|
| Check the code (`checking`) | 20 an hour per code | New zone for `/api/method/alvoraa_portal.field_checkin.*` only: **600 a minute, burst 100** |
| Agree and finish | 5 an hour per code | Same zone |
| This is not me | 5 an hour per code | Same zone |
| `field_status` | 60 an hour per phone (the app asks at most once a minute) | Same zone |
| Punch | 30 an hour per phone | Same zone |
| Remove this phone | 5 an hour per phone | Same zone |
| Unknown or wrong codes, per site | Alert when above a threshold, set after the pilot | — |

The code must hold at least 128 random bits, so guessing is hopeless with or without limits.
The limits protect the server and keep logs quiet. **All numbers are starting points; measure
them on a shared Wi-Fi at the pilot.** nginx is shared by production and dev: `nginx -t`
before any push, and repeat the security headers in the new block (012 OPS-27, OPS-30).

## 6. Design decisions with a run-side effect

| Decision | How to enforce it on the server | How fast | Run-side note |
|---|---|---|---|
| **D3** new phone replaces old | In the same database transaction as "Agree and finish": lock the employee's device rows, set the old one to `Replaced` | Old phone is refused at its next call | Needs OPS-28, or `Replaced` still passes |
| **D4** no unblock | The device controller refuses `Blocked` → any other status, from the desk form, list edit, data import and API. Not just a hidden button | Immediate | Mistakes cost HR a new code. Cheap |
| **D5** switching off stops joined phones | **Check at request time** on every device call: the setting, the plan, and the employee's *current* designation. **Do not rewrite device rows** | **Next call from the phone, seconds.** A phone already on the home screen finds out when it punches or comes back to the front. No push needed | Keeps "who was active" intact, and turning the setting back on restores those phones with no new codes. If you want switch-off to be permanent instead, that is a product decision. Plan changes use `has_feature`; how fast those reach the tenant I did not check |
| **D17** one code at a time | Making a code locks the employee's invite rows and cancels the waiting one in the same transaction | Immediate | The table stays tiny (employees × reissues). Keep rows for the audit history; a hash of a dead code is harmless |
| **D19** notice version change | Server sends the notice rows and version (section 2). **The app never hardcodes the version** | — | If the version is built into the app, every wording change is a store release, and older apps fail within the 90 days |
| **D19** phones joined on the web page | Today `field_checkin` does not check a device's notice version (read). If the server starts refusing old versions with `NOTICE_CHANGED`, **the web page has no screen for it and those phones stop punching** | At the deploy | Ship the web page's "read it again" screen in the **same deploy** as the check, or apply the check to app phones only. No live customer is affected today; PPJ's demo phones would be |

## OPS rows (continuing from §1)

| ID | Recommendation | Why | Cost of ignoring it | Level | Decision |
|---|---|---|---|---|---|
| OPS-19 | **Recommend:** stop Frappe trusting a caller-supplied `X-Forwarded-For`. In nginx, send only the real address (`proxy_set_header X-Forwarded-For $remote_addr;`) in every `location`, on production and dev. **This changes the production nginx, so it needs your explicit go-ahead.** Security engineer to confirm and to check the live file first. | nginx appends to the caller's header; Frappe takes the first entry (source read today). | Every Frappe IP rate limit, including the new join limits, can be bypassed, and logged IPs can be faked. | Recommend | |
| OPS-20 | **Recommend:** keep photo, GPS, names and codes out of error logs. Remove `photo`, `latitude` and `longitude` from the request fields as soon as the endpoint reads them. Turn expected failures into coded 4xx answers (Frappe does not write request fields to the log for those). Name every secret field with `token` or `secret` in it. Add a test that forces a 5xx in a punch and in "Agree and finish", then checks `frappe.log` and the Error Log for none of: photo text, coordinates, token, employee name. | Frappe writes request fields on 5xx and local variables to the Error Log; it hides only names containing `token`, `secret`, `key`, `password`, `pwd` (source read today). | Photos and positions sit in logs beyond the photo retention period, against `nfr-budget.md` §5 ("personal data in logs: never"). | Recommend | |
| OPS-21 | **Recommend:** photo at long edge ≤ 640 px, short edge ≤ 480 px, JPEG 0.6, re-save at 0.45 if over 120 KB, never send over 150 KB; keep the 400 KB server backstop; record photo byte size (only) per app version in the pilot. | Today's size already works for HR and 3G; the sizes in code comments disagree and nobody has measured. | Bigger photos slow punches and grow storage and backups; or photos too small to recognise a face. | Recommend | |
| OPS-22 | **Recommend:** the app loads **nothing from the internet** except our tenant's API: phone fonts, inline SVG icons, no Google Fonts, no analytics. Add a CI check that the bundled files contain no outside URLs, and a CI size ceiling: **fail if the release package is over 10 MB**. Test APKs for ARM only. | Prototype imports Google Fonts; the web page does not. Size creeps without a gate. | Google receives every worker's IP at every open; screens break with no signal; a slow drift to a 20 MB app. | Recommend | |
| OPS-23 | **Consider:** put ML Kit's QR-reading model **inside the app** (+2.4 MB), rather than letting Google Play services fetch it (+200 KB, then a download at first scan unless install-time download is set). Decide after trying both on the three pilot phones. | The first scan is the WOW moment, on 3G. Phones without Google Play services cannot fetch the model at all. | A spinner at the first scan, or a scan that never works on some phones. | Consider | |
| OPS-24 | **Recommend:** the call plan in section 2: one call on open carrying device state, minimum version and notice version; "check the code" returns everything for the confirm and notice screens; answers carry the next screen's data; refresh at most once a minute; 30 s phone-side timeout; retry only on tap. | Each extra call on 3G costs about half a second to a second. | Slower opens and joins on the phones that matter most, and more load at 9 am. | Recommend | |
| OPS-25 | **Recommend:** the storage rules in section 2: secret in Keystore-backed secure storage only; QR token, photo and GPS in memory only; photo taken inside the page, not by a camera plugin that writes files; `Cache-Control: no-store` on device and join endpoints; Android backup switched off for the app (`allowBackup="false"` and data-extraction rules); do not store workplace coordinates. | The web page keeps the secret in `localStorage` today; Android backup copies app data to Google Drive, and a restored Keystore secret does not work on a new phone anyway (D3 needs a new code). | A secret or photo left in a file, the gallery, a cache or a cloud backup. | Recommend | |
| OPS-26 | **Recommend:** the error contract in section 3: `{code, values, message}`, fixed HTTP statuses, English kept for the web page until it reads codes, non-JSON answers mapped by status (429, 5xx, captive-portal HTML), Frappe's rate-limit refusal wrapped with a code. All codes in one server file, with a test that each one exists in the app's table. | The app has no other way to tell a Wi-Fi login page from a server fault, or a rate limit from a crash. | "Something went wrong" for problems a person could fix; a wording change breaks the web page. | Recommend | |
| OPS-27 | **Recommend:** minimum version as described in section 3: version header on every call; `APP_TOO_OLD` from every device endpoint; one constant in code; raise it only 90 days after the replacement build is available, except for security, which is your call; one contract file per released version replayed in CI; codes that ask for an action must exist from version 1. | Gate decision 7 promises 90 days. | Either a web deploy stops old phones at shift start, or old versions can never be retired. | Recommend | |
| OPS-28 | **Recommend:** `_device_from_token` lets **only `Active`** through; every other status is refused with its own code. A test per status. | It refuses only `Blocked` and `Pending` today (read). D3, D5 and D10 add statuses. | A replaced or removed phone keeps punching. | Recommend | |
| OPS-29 | **Recommend:** the rate limits in section 5: hash-keyed per code and per phone; a separate nginx zone for field check-in paths at a higher per-IP rate; an alert on wrong-code spikes per site; measure at the pilot on shared Wi-Fi. Depends on OPS-19 for any Frappe IP limit to mean anything. | Current limits are per IP (60 punches an hour) and Frappe's IP can be faked. **Estimate** only. | A depot's 61st worker is refused; or limits that stop nobody. | Recommend | |
| OPS-30 | **Recommend:** D5 at request time (setting, plan, current designation), never by bulk-editing device rows; D3 and D17 inside one locked transaction; D4 enforced in the device controller for every entry path. | Section 6. | Stopped phones that still punch; two "live" codes; a block undone through list edit or import. | Recommend | |
| OPS-31 | **Recommend:** for D19, the server sends the notice rows and version; the app never hardcodes the version. Ship the web page's "read it again" screen in the same deploy as any server check of the notice version, or apply that check to app phones only. | Section 6. | Every notice change needs a store release; or web-page phones stop punching the moment the version changes. | Recommend | |
| OPS-32 | **Recommend:** QR handling in the desk: QR drawn in the browser from the POST answer; no GET URL, Print Format, PDF or stored file carrying the code; browser print only; no email button; no URL shortener; no token field on the invite record (hash only); the `/enrol` page loads no outside resources and never reads the fragment. | Section 4. | Live codes end up in access logs, Version history, a third party's database or a saved PDF. | Recommend | |
| OPS-33 | **Consider:** send the photo as a binary upload instead of base64 text, as an *added* endpoint later, not now. | Saves about a third of each upload (15–25 KB per punch, estimate). | Nothing urgent; a small data saving left on the table. | Consider | |
| OPS-34 | **Consider:** a daily count per site of outcome codes and app versions, with no names and no device IDs, sent up with the existing control-plane error-count pull (`hooks.py`). | Success measure 1 needs "first-tap saves"; retiring an old version needs "nobody left on it". Gate decision 6 chose server counts over a crash tool. | The pilot has no numbers, and old versions cannot be retired with confidence. | Consider | |
| OPS-35 | **FYI:** photos grow storage by about **1 GB a month per 400 field workers**, about 3 GB steady at 90 days' retention, copied again in every backup with files. **Estimate.** | Section 1. | Backups and disk fill faster than planned once a real tenant goes live. | FYI | |
| OPS-36 | **FYI:** first open on a cheap phone is set by WebView start-up (estimate 1–2.5 s), not the network. Measure it on the three pilot phones next to success measure 1. | Section 1. | The app is blamed for slowness nobody measured. | FYI | |

## What I did and did not check

| Checked | How |
|---|---|
| Photo size, format and server limits; storage of the secret; refresh on return; device status check; site coordinates unused | Read `www/field-checkin.html` and `field_checkin.py` |
| Plan gate | Read `requires_feature` in `subscription.py` |
| nginx headers, rate limits, timeouts, no `gzip` | Read `deploy/nginx.conf` in git |
| Frappe client IP, log field hiding, Error Log local variables, rate-limit key | Frappe `version-16` source: `auth.py`, `utils/logger.py`, `utils/error.py`, `utils/__init__.py`, `rate_limiter.py`; `traceback_with_variables` source (1,000-character cut), 17 Sep 2026 |
| ML Kit size | Google's ML Kit barcode page, 17 Sep 2026 |
| Prototype outside requests | Read `prototype-v1/index.html` (Google Fonts import) |

**Not checked:** the live server's nginx file; whether Frappe really logs a punch's photo on a
5xx (source read, not reproduced); real APK size (no build exists); real photo sizes on any
phone; WebView start-up time; how fast a plan change reaches a tenant; whether CapacitorHttp
keeps any response cache. Nothing was run on the local bench, dev or production.

## Sources (read 17 Sep 2026)

- [Frappe v16 `auth.py` — `set_request_ip`](https://raw.githubusercontent.com/frappe/frappe/version-16/frappe/auth.py)
- [Frappe v16 `utils/logger.py` — `SiteContextFilter`, `sanitized_dict`](https://raw.githubusercontent.com/frappe/frappe/version-16/frappe/utils/logger.py)
- [Frappe v16 `utils/error.py` — `log_error`, `log_error_snapshot`](https://raw.githubusercontent.com/frappe/frappe/version-16/frappe/utils/error.py)
- [Frappe v16 `utils/__init__.py` — `get_traceback`, sanitizer](https://raw.githubusercontent.com/frappe/frappe/version-16/frappe/utils/__init__.py)
- [Frappe v16 `rate_limiter.py`](https://raw.githubusercontent.com/frappe/frappe/version-16/frappe/rate_limiter.py)
- [traceback_with_variables `core.py`](https://raw.githubusercontent.com/andy-landy/traceback_with_variables/master/traceback_with_variables/core.py)
- [ML Kit barcode scanning on Android — bundled vs unbundled size](https://developers.google.com/ml-kit/vision/barcode-scanning/android)
- [Cutting a Capacitor Android build in half (Sep 2023)](https://dev.to/indiecoredev/cutting-a-capacitor-android-build-in-half-59h9)

---

# §3 · 17 September 2026 — Requirements

Read for this section: `01-product-brief.md` (Gate decision), `01b-ux-design.md` (Design check
decision: D1–D20 accepted), `prototype-v1/index.html`, §1 and §2 above, `nfr-budget.md`,
`definition-of-ready-done.md`. In git on `origin/dev`: `.gitignore`, `.github/workflows/`,
`deploy/nginx.conf`, `deploy/compose/docker-compose.app.yml`, `field_checkin.py`,
`alvoraa_field_device.json`, `alvoraa_portal/hooks.py`. Firebase and GitHub help pages, read
17 Sep 2026.

Nothing was run. No docker, no bench, no build, no request to any server. I fetched `origin/dev`
to read it; nothing else changed.

**What this section is.** The approved design turned into numbered OPS requirements that the
business analyst can trace into user stories. Each row says how to test it. Rows are ranked by
**when they block**: before any key exists → before server code reaches dev → before the first
pilot build → during the pilot → rollout and rollback.

**Depends on slice 014 (`014-checkin-security-fixes`).** OPS-19 (forged `X-Forwarded-For`) and
OPS-20 (photo, GPS and names in 5xx logs) are fixed there and are not re-specified here. The 014
folder has no artifacts yet (checked), so its date is not known.

## Read this first

1. **The pilot cannot start before you say "push to dev" for the server work.** The pilot tenant
   is on dev, so the new endpoints must be there. Pilot builds on GitHub Actions also need the app
   code on GitHub, and only `dev` is pushed (CLAUDE.md §1). Until then: debug builds against the
   local bench only.
2. **Rolling the server code back can let replaced and removed phones punch again.** Today's
   check refuses only `Blocked` and `Pending` (read). Once `Replaced` and `Removed` rows exist, a
   revert to today's check lets those phones through. So "only `Active` passes" (OPS-50) ships in
   the first server change and is never reverted. **Rollback is the settings switch, not a code
   revert** (OPS-65).
3. **Any caller can send a 50 MB body to the check-in endpoints today.** nginx allows
   `client_max_body_size 50m` on every path, on production and dev (read in the git copy; the live
   file was not read). The server refuses a big photo only after reading it. Not tested. Production
   has no live customers (14 Sep 2026). OPS-45 caps it per path.
4. **There is still no guard against a key file being committed.** Re-checked on `origin/dev`
   today: no key patterns in `.gitignore`, no secret scan in CI. GitHub's push protection (free and
   on by default for public repos, per GitHub, read today) looks for known **token patterns**. It
   does not stop a binary Android keystore file (OPS-37).
5. **Four things need your word, not an engineer's:** a Firebase account (a new vendor); a
   password manager for the keys, if you do not have one; buying the pilot phones; and **who gets
   the alerts** for this slice. For slice 012 you said "company leader", and it was never settled
   whether that means Alvoraa's own leader or each tenant's head. Please answer again for this
   slice (OPS-61).

## The answer in short

- **Before any key:** ignore rules, a CI check for tracked key files, a secret scan (OPS-37).
- **Three build types:** debug (this PC, local bench only), pilot (GitHub Actions, Firebase, HTTPS
  only), release (from `main`, not in step 1) (OPS-38).
- **Server:** six device endpoints under one module path. Each has a hash-keyed limit, a body cap,
  `no-store`, and coded refusals (OPS-44 to OPS-53).
- **Pilot:** 5 phones, a demo tenant on dev, invented employees, testers invited by name (OPS-54,
  OPS-56, OPS-57).
- **Server run cost stays close to zero** (estimate, as in §1). One daily clean-up job on the
  existing `default` queue, which `worker-default` already listens on (read in compose).
- **Rollback in under a minute, with no deploy:** untick "Field workers can use the app" (OPS-65).

## Endpoints for step 1 — the contract

Names are working names; the engineer names them. **All device endpoints live under one module
path** (for example `/api/method/alvoraa_portal.field_checkin.*`), so one nginx rule covers them.

| # | Endpoint (screen) | Caller proves itself with | Limit per hash (Frappe) | Body cap (nginx) | Server p95 | Answer ceiling | Codes it may send |
|---|---|---|---|---|---|---|---|
| E1 | Check the code (`checking`) — uses nothing | QR token | 20 / hour per code | 16 KB | ≤ 500 ms | 8 KB | QR_EXPIRED, QR_USED, QR_CANCELLED, APP_OFF_FOR_FIELD, NOT_FIELD_ROLE, FEATURE_OFF, APP_TOO_OLD, TOO_MANY_TRIES, SERVER_ERROR. Unknown token → the code security picks in `01c` |
| E2 | This is not me → cancel (`notMe`) | QR token | 5 / hour per code | 16 KB | ≤ 500 ms | 1 KB | As E1 |
| E3 | Agree and finish (`joining`) — uses the code, returns the device secret **once** | QR token | 5 / hour per code | 16 KB | ≤ 500 ms | 4 KB | E1 codes + NOTICE_CHANGED, EMPLOYEE_NOT_ACTIVE |
| E4 | App start (extends today's `field_status`) — device state, minimum version, notice version, today's punches | Device secret | 60 / hour per phone | 16 KB | ≤ 500 ms | 4 KB | APP_TOO_OLD, NOT_SET_UP, DEVICE_BLOCKED, DEVICE_REPLACED, EMPLOYEE_NOT_ACTIVE, APP_OFF_FOR_FIELD, NOT_FIELD_ROLE, FEATURE_OFF, NOTICE_CHANGED, TOO_MANY_TRIES, SERVER_ERROR |
| E5 | Punch (`field_checkin`) | Device secret | 30 / hour per phone | **1 MB** | ≤ 500 ms target, **at risk** (photo file write). A miss gets a dated exception, as `nfr-budget.md` requires | 4 KB | E4 codes + GPS_NOT_EXACT, OUTSIDE_WORKPLACE, ALREADY_RECORDED |
| E6 | Remove this phone (`leaveConfirm`) | Device secret | 5 / hour per phone | 16 KB | ≤ 500 ms | 1 KB | E4 codes |
| E7 | Make a code (desk, HR, logged in) — returns the QR token **once** | Session + HR role | 30 / hour per HR user | Default | ≤ 500 ms | 2 KB | Frappe permission error; NOT_FIELD_ROLE, APP_OFF_FOR_FIELD, FEATURE_OFF |
| E8 | `/enrol` page (never redeems) | None | nginx only | n/a (GET) | ≤ 300 ms | 10 KB | — |

E1–E6 are all guest `POST`, answer `Cache-Control: no-store`, and share one nginx per-IP zone:
**600 a minute, burst 100** (starting number from §2). Every number is a starting point to
measure at the pilot.

## OPS rows (continuing from §2)

### A · Before any signing key exists (week 1)

| ID | Recommendation | Why | Cost of ignoring it | Level | Decision |
|---|---|---|---|---|---|
| OPS-37 | **Recommend:** three guards, landed and green on `dev` before anyone creates a key. **(1)** `.gitignore` entries: `*.jks`, `*.keystore`, `*.p12`, `*.p8`, `*.cer`, `*.mobileprovision`, `keystore.properties`, `local.properties`, `google-services.json`, `GoogleService-Info.plist`, `ExportOptions.plist`, `xcuserdata/`, `*.local.xcconfig`. **(2)** A CI step that fails if `git ls-files` lists any file matching those patterns. This catches a file added with `git add -f`. **(3)** A pinned secret scanner on every push and pull request. Also confirm GitHub push protection is on in the repo settings (your setting). **Test:** a throwaway branch that force-adds an empty `test.jks` fails CI. | Public repo. None of the three exists today (checked on `origin/dev`). Push protection matches token patterns, not binary key files. | A signing key is public the moment it is pushed. A leaked pilot key lets anyone build an APK that installs as an update over our pilot app. | Recommend | |
| OPS-38 | **Recommend:** three build types, each with its own app ID and rules. **Debug:** app ID ending `.debug`; built on this PC; Android's debug key; plain HTTP allowed only to the local bench address; installed by USB on developers' own phones only. **Pilot:** app ID ending `.pilot`; built on GitHub Actions from a commit on `dev`, started by hand, in a protected environment `mobile-pilot` that needs your approval; signed with a **pilot key**, not the Play upload key; HTTPS and `*.alvoraa.co` only; sent through Firebase. **Release:** the store app ID; from a commit on `main`; the upload key; environment `mobile-release`. Not built in step 1. **Test:** CI builds all three, and the OPS-55 checks run on the built pilot and release files. | Keeps test keys, test hosts and plain HTTP out of anything a worker installs. Three app IDs can sit on one phone. | A debug build with HTTP allowed reaches a tester. Or the store key gets used for throwaway pilot builds. | Recommend | |
| OPS-39 | **Recommend:** key storage and backup. A named holder makes each key once, **never inside any git folder** (including `.claude/worktrees/`). Stored in a password manager with **two named holders**, plus one encrypted offline copy. In CI: environment secrets only, written to the runner's temp folder, deleted in a step that always runs, never printed. Write each key's signing-certificate SHA-256 fingerprint (public) into the repo. **Test:** before the pilot, the second holder restores the key from the backup and signs a build; its fingerprint matches the recorded one. | A backup that was never restored is a hope. The fingerprint is needed later for App Links (OPS-11). | Lost pilot key: every tester uninstalls and joins again. Lost upload key without Play App Signing: the store app can never be updated (§1). | Recommend | |
| OPS-40 | **Recommend:** version rules. `versionName` is `MAJOR.MINOR.PATCH`. `versionCode` = MAJOR × 1,000,000 + MINOR × 10,000 + PATCH × 100 + build number (0–99), from one file in the repo. The app sends `versionName` in the `X-Alvoraa-App-Version` header. The server compares the three numbers, never the text. iPhone uses the same two values. **Test:** CI fails if `versionCode` is not higher than the last pilot or release build, or if `versionName` does not match the pattern. | Play and Firebase refuse or muddle builds whose number does not rise. One formula means one number answers "which build is this?" | Two builds with one version, so a tester cannot tell whether they updated. A text comparison says "1.10" is older than "1.9". | Recommend | |
| OPS-41 | **Recommend:** builds that can be repeated. Commit the lock file and install with `npm ci`. Pin Node, JDK, Gradle (the wrapper with its checksum), Android build tools, Capacitor and every plugin version in one file. Each pilot release note in Firebase carries the git commit and the APK's SHA-256. **Byte-identical builds are not a goal in step 1.** **Test:** building the same commit twice in CI gives the same version, the same permission list and the same bundled web files (file hashes compared). | Without pins, a rebuild months later pulls different plugins. | A bug report for "build 34" that nobody can rebuild or match to code. | Recommend | |
| OPS-42 | **Recommend:** iPhone on a borrowed Mac with a free Apple ID (S14). The team ID and bundle ID go in a local, git-ignored settings file, not in the Xcode project. **Never commit** the Apple ID, the team ID, `*.mobileprovision`, `*.p12`, `*.cer`, `xcuserdata/` or `ExportOptions.plist`. Leave no keys, GitHub token or pilot QR codes on the borrowed Mac: sign out of the Apple ID in Xcode and delete the clone when done. The build stops opening after 7 days (§1), so rebuild weekly. **Test:** a CI check fails if the iOS project file contains `DEVELOPMENT_TEAM` with a value. | The Mac belongs to someone else. The Xcode project file quietly stores the team ID. | A personal Apple ID linked from a public repo; our code and logins left on a lent machine. | Recommend | |

### B · Before server code reaches dev

| ID | Recommendation | Why | Cost of ignoring it | Level | Decision |
|---|---|---|---|---|---|
| OPS-43 | **Recommend:** slice 014 (OPS-19, OPS-20) is on dev **before** any new join or punch endpoint goes to dev. | E1–E3 put the QR token on the request path that OPS-20 cleans. Any Frappe IP limit means nothing until OPS-19 is fixed. | New endpoints ship with the same log and rate-limit holes. | Recommend | |
| OPS-44 | **Recommend:** the endpoint table above is the contract. Every device endpoint: in one module path; guest `POST` only; `Cache-Control: no-store`; its body cap, limit and answer ceiling; argument lengths checked on the server (for example phone name ≤ 80 characters, platform from a fixed list, version header ≤ 20 characters and in the version pattern). The device secret (E3) and the QR token (E7) each appear in exactly one answer, ever. **Test:** one test per endpoint for method, cache header, each length limit, and answer size under the ceiling. | Gives the analyst one line per endpoint to trace, and the reviewer one place to check. | Endpoints drift apart: one cacheable, one on GET, one without a limit. | Recommend | |
| OPS-45 | **Recommend:** request size limits in nginx, per path, in **both** the production and dev server blocks: punch path 1 MB, other device paths 16 KB. Today every path allows 50 MB (read). Repeat the security headers in the new block, and run `nginx -t` before any push (012 OPS-27, OPS-30). The app treats nginx's 413 answer ("body too large") as `SERVER_ERROR`. **This changes the nginx that also serves production, so it needs your go-ahead.** **Test:** on the local bench, a 2 MB body to the punch path gets 413 and never reaches Frappe; a 20 KB body to E1 gets 413. | A photo leaves the phone under 150 KB (OPS-21), and the server refuses anything over 400 KB. Nothing needs 50 MB. | Anyone can make the app server read 50 MB bodies on a guest endpoint, again and again. | Recommend | |
| OPS-46 | **Recommend:** rate limits keyed on the **SHA-256 hash** of the QR token or device secret. Never the raw value, never IP alone (OPS-29 made testable). Frappe's own rate-limit refusal is wrapped so it carries `TOO_MANY_TRIES` and `retry_after_s`. Plus the nginx zone above. **Tests:** (1) 400 simulated phones from **one** IP, 160 requests a minute for 5 minutes, on the local bench: zero refusals, p95 ≤ 500 ms. (2) The 31st punch in an hour from one phone gets `TOO_MANY_TRIES` with `retry_after_s`. (3) After the tests, no Redis key contains a raw token or secret. | Many phones share one IP on Indian mobile networks and site Wi-Fi. Frappe writes the key value into Redis in plain text (§2). | A depot is refused at 9 am, or raw secrets sit in Redis. | Recommend | |
| OPS-47 | **Recommend:** CORS (the browser rule on which other sites may call us). Never set Frappe's `allow_cors` (OPS-1). The engineer picks native HTTP (OPS-2) or a narrow nginx rule on the device path only, with no credentials; security confirms. **Tests:** (1) a bench test asserts `allow_cors` is not set in site or common config. (2) After each dev deploy, a preflight from `Origin: https://example.org` to `/api/method/frappe.auth.get_logged_user` gets no `Access-Control-Allow-Origin`. (3) If the nginx rule is chosen, a preflight from `capacitor://localhost` to a non-device path also gets none. | `allow_cors` opens every endpoint, with credentials (§1). | Logged-in portal calls become possible from other origins. | Recommend | |
| OPS-48 | **Recommend:** minimum app version (OPS-27 made testable). One constant in code. Every device endpoint answers `APP_TOO_OLD` with `min_version` when the header is below it or malformed. **No header means today's web page, which is allowed.** A versions file in the repo lists each released version and the date it became available. **The 90-day promise starts at the first store release, not at the pilot** (OPS-58). **Tests:** (1) per endpoint: below → `APP_TOO_OLD`; equal → normal; missing → normal; `"abc"` → `APP_TOO_OLD`. (2) CI fails if the constant rises above a version whose replacement is less than 90 days old, unless the commit is marked as a security exception you approved. (3) One contract file per released version is replayed against the endpoints (§2, section 3 point 8). | Gate decision 7 (90 days). A rule without a check gets broken on a busy day. | A web deploy stops old phones at shift start, and the fix waits on store review. | Recommend | |
| OPS-49 | **Recommend:** error-code contract (OPS-26 made testable). Every refusal is JSON `{code, values, message}` with **one fixed HTTP status per code**, listed in a single server codes file. `message` stays English for logs and for today's web page (MA-30). A 5xx carries only `SERVER_ERROR`, with no detail. **Tests:** (1) each code in the codes file has a test that triggers it and checks status, code and value names. (2) Every server code exists in the app's table; the app-only codes in `01b` §8 are listed separately. (3) Today's web page flows still pass unchanged. | The app has no other way to choose a screen (`01b` §8). | Screens fall back to "Something went wrong"; a wording change breaks the web page. | Recommend | |
| OPS-50 | **Recommend:** device status rule (OPS-28 made testable). Only `Active` passes; each other status gets its own code. When a device leaves `Active`, its secret hash is **cleared in the same save**, so no later edit can bring it back. `Blocked` cannot change to anything (D4), enforced in the device controller for desk, list edit, data import and API. **Ships in the first server change and is never reverted** (Read this first, point 2). **Tests:** one per status (`Pending`, `Blocked`, `Replaced`, `Removed`, and any "stopped" status the engineer adds); list edit and data import of `Blocked` → `Active` both refused. | Today only `Blocked` and `Pending` are refused (read). D3, D5 and D10 add statuses. | A replaced or removed phone keeps punching. | Recommend | |
| OPS-51 | **Recommend:** locked transactions for D3 and D17 (OPS-30 made testable). E3 and E7 both lock the **Employee row first**, then the invite rows, then the device rows — always in that order, so two requests cannot wait on each other for ever — and commit once. E3: the invite must still be waiting; mark it used; set the old `Active` device to `Replaced` and clear its hash; create the new `Active` device with the notice version and time. E7: cancel the waiting invite and create the new one. **Tests:** (1) two E3 calls with one code at the same moment, from two database connections: exactly one succeeds, the other gets `QR_USED`. (2) E7 twice at once for one employee: exactly one waiting code remains. (3) E3 during E7 for the same employee: no deadlock error. | `01b` §6 edge cases: two people scan one code; HR makes a second code. | Two phones joined on one code; two live codes for one person; random deadlock errors on a busy joining day. | Recommend | |
| OPS-52 | **Recommend:** retention and clean-up. **At the moment of change, not by the job:** a used, cancelled or "not me" invite loses its token hash; a device leaving `Active` loses its secret hash (OPS-50). **A daily job** on the `default` queue: no arguments, batched, safe to run twice, logs counts only. It (1) marks waiting invites past expiry "Ran out" and clears the hash; (2) deletes invites that have been in a final state longer than the retention period; (3) counts any non-`Active` device or non-waiting invite that still has a hash, and alerts if the count is above 0. **Retention for invite history: the compliance owner decides; starting point 12 months** [ASSUMPTION]. Device rows stay while any check-in points at them. Daily counters (OPS-59) are kept 13 months. **Tests:** seeded expired, used and old rows → after one run, states and hashes are as above; a second run changes nothing. | D17 keeps history for HR. A dead hash is harmless; a live hash on a dead row is not. | Old codes stay usable in the data; the invite table grows for ever; or HR's history is deleted too early. | Recommend | |
| OPS-53 | **Recommend:** the settings are the switch. On migrate, existing tenants get **an empty field-worker designation list**, so nobody is eligible until HR picks designations. The endpoints can then reach dev and main with no effect on anyone. "Field workers can use the app" is checked **at request time** on every device call (D5). A settings change takes effect on the **next call, within 60 seconds** (cache cleared on save). The designation check applies to **app-joined** phones only; web-page phones set up before this rule keep working (brief Q4). **Tests:** (1) after a fresh migrate, E7 refuses everyone with `NOT_FIELD_ROLE`. (2) Untick the switch → the next E4 and E5 get `APP_OFF_FOR_FIELD` within 60 s, and waiting codes get it on E1; tick it again → the same phones work with no new code. (3) A web-page device still punches with the switch off. | Makes "deployed" and "switched on" two separate steps, and makes rollback a tick box. | A deploy switches the app on for every tenant; or turning it off needs a deploy. | Recommend | |

### C · Before the first pilot build is sent

| ID | Recommendation | Why | Cost of ignoring it | Level | Decision |
|---|---|---|---|---|---|
| OPS-54 | **Recommend:** the pilot environment. The pilot uses **a demo tenant on dev** (for example `ppj.dev.alvoraa.co`) with **invented employees only**, and photo retention on that tenant set to **7 days**. **Depends on the wildcard certificate (OPS-9).** Stopgap if it slips: add that one host to the current certificate — **this touches production's certificate and nginx, so it needs your go-ahead.** **Fallback until then:** debug builds against the local bench over plain HTTP, debug only. The debug allowance names the bench's exact LAN or Tailscale address and nothing else — **never the server's Tailscale address**. Changing the demo tenant's settings is a dev-stage action and needs your word (CLAUDE.md §1). | Apps refuse a bad certificate with no way round it (§1). Testers' photos are personal data, even on dev. | The pilot cannot reach dev; testers' faces stay on dev for 90 days; or a debug build can reach the production server over its private address. | Recommend | |
| OPS-55 | **Recommend:** pilot and release builds talk only to `https://<name>.alvoraa.co`. **In the app:** the host check accepts only `https`, no port, no user part, and a host ending in `.alvoraa.co` with one or two labels in front (tenant, or tenant + `dev`). **In Android's network settings:** no plain HTTP, no user-installed certificates. **In the app config:** no `server.url`, no `cleartext`, no `allowNavigation`; web view debugging off. **Tests:** (1) unit tests: `https://ppj.alvoraa.co` passes; `http://ppj.alvoraa.co`, `https://evilalvoraa.co`, `https://alvoraa.co.evil.com`, `https://x.alvoraa.co@evil.com` and `https://x.alvoraa.co:8443` all go to `notAlvoraa` with no network call. (2) CI inspects the **built** pilot and release files: not debuggable, no plain HTTP allowed, no remote URL or navigation allowance in the bundled config. **Consider as well:** the store release build also refuses `*.dev.alvoraa.co`. | A QR is just a link; anyone can print one (OPS-7). Checking the built file catches a setting that only looked right in the source. | A planted QR sends photos and positions to someone else's server; a pilot build ships with HTTP allowed. | Recommend | |
| OPS-56 | **Recommend:** Firebase App Distribution for pilot builds — **a new vendor account, so it needs your word.** Owned by a company Google account with **two owners**; the engineer gets the App Distribution admin role only. Testers are **invited by email** into one group (`pilot-013`). **No public invite links.** The app contains **no Firebase code** (no in-app tester alerts), so nothing from Google runs inside it. To remove a tester: take them out of the group (this removes access to releases they had through it, per Firebase) **and** block their phone in the desk, because an installed app keeps working. Limits (Firebase, read today): releases leave the tester page after **150 days**, but installed apps keep running; invitations expire after **30 days**; 500 testers per project, 200 per group. **No APKs by WhatsApp or Drive** — they cannot be taken back. **Test:** a removed tester no longer sees the release, and their blocked phone gets `DEVICE_BLOCKED`. | Named access that can be removed, and a record of which build each tester has. | Builds pass from hand to hand; an ex-tester keeps punching into the demo tenant. | Recommend | |
| OPS-57 | **Recommend:** the pilot phone list — **5 phones**. P1 low-end **Xiaomi / Redmi** (its own permission wording). P2 low-end **Realme** (strict battery rules). P3 low-end **Samsung Galaxy A or M** (One UI). One of P1–P3 runs **the oldest Android the app says it supports**, and one is **32-bit** if we can find one. P4 a current **Android 16** phone (target-level behaviour, OPS-15). P5 a **borrowed iPhone**, free Apple ID, outside Firebase (OPS-42). Record for each: maker, model, Android version, RAM, processor type, Google Play services yes or no. Record models in the repo; **keep tester names out of the public repo.** **Estimate:** ₹8,000–15,000 each for P1–P3 (§1) — **new spending, your call.** | Measure 1 and the stop rule need 3 makers (brief §10). Cheap phones differ most in permissions, camera and web view start-up. | "Works on my phone" from a mid-range developer handset; the stop rule is judged on the wrong phones. | Recommend | |
| OPS-58 | **Recommend:** the "Update the app" link per build type is **built into the app, never sent by the server.** Pilot → the Firebase tester page for this app. Release → the Play Store listing. Debug → the line "Ask the developer". During the pilot the minimum version **may rise without the 90-day wait**, with testers told a day ahead; the 90-day window starts at the first store release (OPS-48). **Test:** on the local bench, set the minimum above the pilot build's version. Only the `update` screen is reachable, and its button opens the tester link. The same test on a release build opens the Play listing. | A server-sent link lets one wrong tenant setting send every worker to any download page. | Testers pressing "Update in Play Store" for an app that is not in the store; or a download link anyone with desk access can redirect. | Recommend | |

### D · During the pilot — monitoring, logging, performance

| ID | Recommendation | Why | Cost of ignoring it | Level | Decision |
|---|---|---|---|---|---|
| OPS-59 | **Recommend:** daily counts per site (OPS-34 made a requirement, as gate decision 6 chose server counts). No names, no employee IDs, no device IDs. **Count:** joins completed (E3); code checks refused, by code (including unknown token); "This is not me" cancels; codes made, cancelled, ran out; punches saved, by app version; punch refusals **by code and app version**; `APP_TOO_OLD` answers; **share of app starts by app version** (the old-version share); rate-limit refusals (Frappe and nginx 429); 5xx on device paths; photo size p50 and p95 by app version (OPS-21). Sent up with the existing control-plane error-count pull (`hooks.py`). **Test:** after a scripted run of each outcome, each counter moved by exactly one, and a scanner finds no name, ID or token in the stored counter rows. | Measures 1–3 need these numbers. Retiring a version needs "nobody is left on it". | The pilot ends with opinions, not numbers; an old version is retired while people still use it. | Recommend | |
| OPS-60 | **Recommend:** what must never be logged, with a test. **Never:** the QR token, the device secret, the photo, the GPS position, the person's name — not in `frappe.log`, the Error Log, nginx access logs, Version history, Redis keys, counters or error text. The token travels only in a POST body, never in a query string. **Depends on slice 014 (OPS-20)** for the 5xx path. **Test:** after the full test suite and after a scripted pilot day on the local bench, a scanner searches all those places for the seeded token, secret, photo text, coordinates and name, and fails on any hit. | `nfr-budget.md` §5: personal data in logs — "Never". | Photos and positions outlive the retention job inside log files. | Recommend | |
| OPS-61 | **Recommend:** named alerts with named owners (`nfr-budget.md` §8). **Alerts:** the clean-up job failed, or its self-check found a live hash (OPS-52); more than 5 server errors (5xx) an hour on device paths for one site; punch refusals above 10% of punches in a day for one app version; refused code checks above a threshold per site (**estimate** 50 an hour, to be set after the pilot). **Owner: your answer is needed.** The 012 answer "company leader" was left unclear (Alvoraa's own leader, or each tenant's head). In step 1 these alerts go to Alvoraa, not to tenants. **Test:** each alert fires once from a seeded condition on the local bench. | An alert nobody owns is noise. | A broken clean-up job or a failing app version goes unseen until a tester complains. | Recommend | |
| OPS-62 | **Recommend:** server speed per endpoint (the table above). p95 ≤ 500 ms (`nfr-budget.md` §2) at "Typical" volume: 250 employees and 90 days of check-ins. Each endpoint's **query count is asserted** in a test; the ceiling is set at the first green run, and the build fails if it rises. No query inside a loop. **Tests:** timed integration tests on the local bench, plus the one-IP load test in OPS-46. | The API budget. E4 runs on every app open. | Opens slow down as a tenant's history grows, and nobody notices until 9 am. | Recommend | |
| OPS-63 | **Recommend:** phone-side budgets, **measured on P1–P3**, 10 runs each, 3G profile (750 kbps up, as in 012 §2a). **(1) Cold start**, tap to first screen: ≤ 2.5 s p95 (estimate today 1–2.5 s, OPS-36). **(2) Saved Attendance screen** within 300 ms of the page being ready; fresh data ≤ 2.5 s. **(3) Scan → "Is this you?"** ≤ 2.5 s. **(4) Agree → Welcome** ≤ 2.5 s. **(5) Punch, network part** (after the photo and GPS fix) ≤ 2.5 s; GPS time recorded separately. **(6) Photo** as OPS-21: long edge ≤ 640 px, JPEG 0.6, saved again at 0.45 if over 120 KB, never over 150 KB; server backstop 400 KB. **(7) Download size** ≤ 10 MB; CI fails above it (OPS-22). **Test:** a results table per phone in the pilot report; a CI unit test feeds a busy 4000 × 3000 picture to the photo code and gets ≤ 150 KB. | `nfr-budget.md` §2: 3G p95 ≤ 2.5 s, skeleton within 300 ms. The §2 figures are estimates nobody has measured. | The stop rule is judged on feel, not numbers; photos creep up in size. | Recommend | |

### E · Rollout and rollback

| ID | Recommendation | Why | Cost of ignoring it | Level | Decision |
|---|---|---|---|---|---|
| OPS-64 | **Recommend:** rollout order, each step on your word. **1.** OPS-37 guards on dev, before any key. **2.** Slice 014 on dev (OPS-43). **3.** Server endpoints, device statuses, settings and clean-up job: local bench first, then dev — **with the empty designation list, so nothing changes for anyone** (OPS-53). Any nginx change (OPS-45, CORS) gets `nginx -t` first, because one nginx serves production and dev. **4.** On the demo tenant on dev: pick designations, tick the switch, set 7-day photo retention (a dev-stage action). **5.** First pilot build from `dev` through `mobile-pilot` → Firebase → P1–P4. **6.** Pilot: 5 working days, at least 20 punches per phone (brief §10). **7.** Server code to `main` only after the pilot and your word; it does nothing on production tenants (empty list). **8.** Store builds from `main` — a later increment. At each dev deploy, check "Lessons already paid for" 1–5 and 8. | Separates "code is deployed" from "app is switched on", so each step can be checked on its own. | Two unknowns land together, and a failure cannot be traced to either. | Recommend | |
| OPS-65 | **Recommend:** rollback. **First choice — no deploy, under a minute:** untick "Field workers can use the app" on the tenant. Then: no new codes; waiting codes stop working; **joined phones show "The app is not switched on for field staff", with "Remove",** at their next call; attendance already marked stays; photos are deleted on the normal retention; device rows are not changed, so ticking the box again restores the same phones with no new codes (D5). Field workers fall back to the web check-in page. **If the pilot ends for good (stop rule):** also block each pilot phone in the desk with the reason "Other" and the note "pilot ended" (this cannot be undone, D4), and delete the Firebase releases. **Revert code** only if the switch cannot fix the problem, and **never back past OPS-50** (Read this first, point 2). New doctype fields stay in the database after a revert, because Frappe does not drop columns; that is harmless. **Test:** the OPS-53 switch test, run on dev after step 4 and before the first tester joins. | Meets `nfr-budget.md` §3: rollback ≤ 15 minutes, no deploy needed. | A bad pilot day needs a deploy to stop it; or a revert quietly lets replaced phones punch again. | Recommend | |
| OPS-66 | **FYI:** new data is small — invites and device rows, a few KB per employee. Photos are the growth (OPS-35). Nothing new for backups, the scheduler or the worker count in step 1. Logs for the new paths fall under the existing log retention (CERT-In, 180 days, `nfr-budget.md` §4). | Run cost stays close to zero (§1). | — | FYI | |

## What I did and did not check

| Checked | How |
|---|---|
| No key patterns in `.gitignore`; no secret scan in CI | Read `.gitignore` and `.github/workflows/` on `origin/dev`, 17 Sep 2026 |
| nginx: `client_max_body_size 50m` in the production and dev blocks; per-IP zones of 5 a minute (login) and 120 a minute (API); no device-path rules | Read `deploy/nginx.conf` in git. **The live server file was not read** |
| Today's limits: `register_device` 10 an hour, `field_checkin` 60 an hour, `field_status` 120 an hour, all per IP. Device statuses `Pending`, `Active`, `Blocked` | Read `field_checkin.py` and `alvoraa_field_device.json` on `origin/dev` |
| A daily photo-purge job exists; `worker-default` listens on `default,short`; one scheduler | Read `hooks.py` and `docker-compose.app.yml` on `origin/dev` |
| Slice 014 has no artifacts yet | Listed `docs/slices/014-checkin-security-fixes/` |
| The 012 alert-owner answer | Read `012/00-impact-analysis.md`, line 654 |
| The pilot "Update" button opens the tester link | Read `prototype-v1/index.html` (notes for the `update` screen) |
| Firebase tester and release limits; GitHub push protection | Web pages below, 17 Sep 2026 |

**Not checked:** whether Android testers need a Google account signed in on the phone; Capacitor
8's lowest supported Android version; whether an Android network-security rule can name a
Tailscale address cleanly; any real build, phone, timing or size. Nothing was run on the local
bench, dev or production.

## Sources (read 17 Sep 2026)

- [Firebase App Distribution — manage testers (500 per project, 200 per group; removal)](https://firebase.google.com/docs/app-distribution/manage-testers)
- [Firebase App Distribution — troubleshooting and FAQ (150-day release expiry, 30-day invitations)](https://firebase.google.com/docs/app-distribution/troubleshooting)
- [GitHub Changelog — secret scanning coverage updates, 7 Aug 2026](https://github.blog/changelog/2026-08-07-secret-scanning-coverage-updates/)
- [GitHub Secret Protection](https://github.com/security/advanced-security/secret-protection)

---

## User answers (Surbhi, 2026-09-17)

- **Firebase App Distribution:** use Surbhi's Google account for now.
- **Password manager for signing keys:** none in use today. Recommended: **Bitwarden (free plan, open source)**, plus a second offline encrypted copy of the keystore (e.g. KeePassXC file on a USB drive kept safely). Awaiting Surbhi's OK.
- **Pilot phones:** some in hand; the rest borrowed.
- **Alert owners (OPS-61, and slice 012 OPS-59):** **technical alerts to Alvoraa (Surbhi)**; **data alerts** (e.g. doubtful attendance days) **to the customer's HR**.
- **QR lifetime:** default **24 hours**, organisation may set up to 7 days.
- **Wildcard certificate:** already live on the server (main commit d6613ea, 2026-09-17; `alvoraa-wildcard` covers `alvoraa.co`, `*.alvoraa.co`, `*.dev.alvoraa.co`). The pilot tenant on dev is no longer blocked by certificates.

---

# §4 · 17 September 2026 — Strategy

Read for this section: `00-impact-analysis.md` (all of it, incl. §12 C-1 to C-17);
`02-functional-spec.md` and `01c-security-privacy-requirements.md` ("User decisions",
"Consent gate", "Changing their mind"); §1–§3 and "User answers" above;
`014/00-impact-analysis.md` ("Pre-push checks run"); `014/03-implementation-notes.md` (on
branch `slice/014-checkin-security-fixes`); `.github/workflows/ci.yml`, `build-image.yml`,
`deploy.yml`; `deploy/Dockerfile`; `deploy/compose/docker-compose.app.yml`;
`deploy/provision_tenant.sh`; `.gitignore`; `REHEARSAL.md` headings; `nfr-budget.md` §4 and
§9; `.claude/work-in-progress.md`; 012 `07-devops-inputs.md` OPS-74.

**What I ran:** `git fetch origin` and read-only `git log` / `git rev-parse`; `gh run list`,
`gh run view` and `gh api` (these read GitHub, not our servers); web pages for versions.
**Not run:** no docker, no bench, no server command, no install, no build, no commit.

## Read this first

1. **The repo is public, and a comment in our own `build-image.yml` says the repo history
   holds customer data.** I confirmed the repo is public (`gh api`, 17 Sep 2026). I did
   **not** scan the history, so I do not know if the comment is true. Production has no live
   customers (14 Sep 2026). Security engineer to check with a one-off history scan (OPS-87).
2. **Push A is already on `origin/dev`.** `origin/dev` = local `dev` = `9138251`, pushed
   17 Sep 12:37 UTC (18:07 IST). CI and Build Image were still running when I checked. The
   engineer's §10.1 ("114 commits ahead") is out of date. **Slice 014 is next** once Push A
   is green.
3. **A production Deploy has been waiting for approval since 10:39 UTC (16:09 IST)**, for
   `main` at `2fc623c`. Production and dev deploys share **one server folder and one nginx**.
   Whichever deploy runs last decides the live `nginx.conf` for both. So: approving that run
   while a dev deploy is running makes two jobs fight over one folder; and approving **any**
   `main` deploy after Push B puts back the old nginx (the forged-address hole 014 closes)
   for production and dev until the next dev deploy. **Decide that run before Push B**
   (OPS-68).
4. **A CI key check on a public repo only tells you after the key is already public.** CI
   goes red after the push, and by then anyone can download the key. What actually stops it
   is local: ignore rules committed before `npx cap add android`, the same check run before
   each push on this PC, and keys made outside any git folder (OPS-71).
5. **jsQR, the engineer's first pick for reading QR codes, has had no release since April
   2021** (last commit August 2021). I agree with reading the QR inside the page. I do not
   agree with picking an unmaintained library without a side-by-side test. The main
   alternative, `zxing-wasm`, **downloads its decoder from a CDN by default** (a CDN is a
   service that serves files from servers close to the user). That would break OPS-22 unless
   the file is bundled (OPS-78).
6. **After Push D, never roll back by redeploying an older dev image.** `deploy.yml` has an
   "image tag" input made for rollback. Using it after Push D is exactly the "revert past
   OPS-50" mistake: replaced and removed phones could punch again. Roll back with the
   settings switch (OPS-82).

## The answer in short

- **Five pushes, in order:** A (done) → B slice 014 → C 013 server group 1 + CI guards →
  D the rest of 013's server stories, switched off → E nginx alone. Then a pilot build (a
  button in GitHub, not a push), then switch-on on the demo tenant. `main` only after the
  pilot.
- **No image or Compose change** for any server story (confirmed below).
- **Migrations are small**, with two real risks: a migrate that saves HR Settings and trips
  `alvoraa_goals`' check, and a consent check that catches web-page phones by mistake.
- **CI gates, in order:** web-page pin tests → key guard → `build-image.yml` skips `mobile/`
  → `mobile.yml` app checks → built-file checks → signed pilot build later.
- **Run cost stays close to zero** (estimate, unchanged from §1). CI minutes are free while
  the repo is public.

## 1. Where I agree and disagree with the engineer

Disagreements first.

| # | Engineer's plan | My view | Why |
|---|---|---|---|
| 1 | **QR read by jsQR** (§8.4, C-11) | **Agree with a JS reader, disagree with jsQR as the default.** Test jsQR 1.4.0 against `zxing-wasm` 3.1.4 (reader only, about 1.04 MB decoder file) on P1–P3 in the A6 spike. Pick on scan time. If `zxing-wasm` wins, bundle its decoder file and point `locateFile` at it (OPS-78) | jsQR: last release April 2021. Scanning is the first thing a worker does. An unmaintained library is acceptable only if it is clearly good enough on the cheap phones |
| 2 | **A second copy of the camera, photo and GPS code** in the app (§8.3, C-12) | **Agree for step 1, disagree with leaving it open-ended.** Put the copy in one app file that names its source. Add a CI check that fails when the web page's copied functions change, until someone updates the app copy too. Put a dated follow-up after the pilot: move both to one shared file (OPS-80) | The engineer marks maintainability "degrades". Without a check, a photo-size fix lands in one copy only, and web and app photos quietly differ. Our existing JS checks (`check_undefined_js.js`, `check_portal_handlers.js`) do not look at `mobile/` either |
| 3 | **Start the key guard and the `mobile/` skeleton before 014 lands** (§10.3 step 4, C-14) | **Agree to start locally now. Disagree with anything reaching `origin/dev` before Push B is green**, and with running `npx cap add android` before the ignore rules are committed in that worktree. The key guard goes out as the first commits of Push C. No pilot key is made until Push C is green | Local work harms nobody. A push before B would restart the shared nginx again in the middle of 014's release. A skeleton generated before the ignore rules can pick up `local.properties` or a build folder by accident |
| 4 | **`build-image.yml` ignores `mobile/**`** (C-13) | **Agree, narrowly.** Ignore `mobile/**` and `.github/workflows/mobile.yml` in `build-image.yml` only. **Do not** add a path filter to `ci.yml`: the key guard lives there and must run on app pushes. `deploy.yml` needs no change, because it only runs after Build Image (OPS-72) | A filter on `ci.yml` would switch the key check off for exactly the pushes that could carry a key. A push that mixes server and app files still builds, which is right |
| 5 | **Native HTTP instead of CORS** (§8.6, C-10) | **Agree, strongly**, with conditions: CapacitorHttp's global switch off, so only explicit calls go native and a stray `fetch` fails; Capacitor's cookie handling off; refuse any redirect; 30 s timeouts set in code; a CI check of the app config (OPS-79) | It avoids any CORS change to the nginx that also serves production. **Not verified:** that explicit CapacitorHttp calls work with the global switch off. Check in the A6 spike |
| 6 | Hash-keyed limits replace the per-IP limits (§8.1 step 3; asks DevOps to confirm) | **Agree.** Between Push D and Push E, nginx's existing `/api/` limit (120 a minute per address, burst 30) still caps a flood of random secrets. That is fine for 5 pilot phones. **Push E must be live before any site with about 50 or more workers on one Wi-Fi uses the app** (estimate) | One indexed lookup per bad secret is cheap, and a per-address cap still exists at every stage |
| 7 | US-4, US-1, US-2 first, never reverted (§8.1 step 1) | **Agree, and make it its own push (C)** | Web-page phones on dev tenants can be checked against the new statuses and codes before five more weeks of changes pile on top |
| 8 | All new tests in `alvoraa_portal/tests`; step 0 pins today's web page first | **Agree.** This is the first gate to add (section 4) | CI runs `alvoraa_portal` tests and blocks on them. It does not run `hrms` tests (012 OPS-74, still open) |
| 9 | Pilot builds from `dev` through a protected `mobile-pilot` environment | **Agree** (OPS-38) | — |
| 10 | Debug builds reach the bench at its LAN address (§8.3) | **Consider a safer route:** `adb reverse` over the USB cable, so the debug build talks to `localhost` only (OPS-84) | Nothing listens on the Wi-Fi, and the debug network rule names one host: `localhost` |

## 2. Install and rollout order

Each push needs your word. "Green" means every item in its row is true before the next push
starts. At every dev deploy, check lessons 1–5 and 8 ("Lessons already paid for").

| Push | What it carries | Before pushing | Green before the next push |
|---|---|---|---|
| **A** — 010 group D + 012 push 1 + F1 (**pushed 12:37 UTC, by the other session**) | 010, 012 commits up to `9138251` | Done | CI all three jobs green; Build Image and Deploy (dev) succeeded; **every dev app container on `dev-9138251`**; dev and production answer 200; 012 §5 checks E1–E19 and 010's release checklist done |
| **Decide** the waiting production Deploy run (`2fc623c`) | — | Approve or cancel it, **not while any dev deploy runs** | The shared server folder is back on `origin/dev` after any main deploy (OPS-68) |
| **B** — slice 014 | `d6613ea` brought onto `dev` by cherry-picking that one commit (OPS-69); 014's five commits rebased on it | Rebase done and read; `check_nginx_conf.py` and `check_nginx_forwarded.sh` re-run on the exact file; 014's owed Frappe tests (13 + full `alvoraa_portal` and `alvoraa_goals`) and `test_site` migrate; hand trace of `/checkin`; manual backup of dev sites (dev deploys take none); **you clear the in-place edit in the server folder right before the push** (OPS-70) | CI green incl. 014's nginx lint step; deploy succeeded; server folder at the pushed commit with a clean `git status`; `compose-nginx-1` logs show no `emerg`; production and dev answer 200; redaction patch ran on every dev site; 11 forged `X-Forwarded-For` calls give one bucket (on your word) |
| **C** — 013 server group 1 + CI guards | Step 0 web pin tests; codes module and wrapper additions; device statuses, fields, permissions, controller, one revoke function; patch M2 + M4; leaver hook; 014 test 417 → 400; **`.gitignore` key rules, tracked-key check, pinned secret scan, `build-image.yml` path filter, `mobile.yml`**; `mobile/` skeleton if ready | Rebased on B; full suites green locally; key check proven locally with a throwaway `test.jks` (no push needed); dry run on a copy (section 3); manual dev backup | CI green incl. pin tests and key check; deploy succeeded; patches ran on all dev sites (counts in the log); web page on a dev demo tenant: register, HR activates, punch, one refusal — same screens as before (on your word); Custom DocPerm on dev tenants re-checked read-only (as 010 decision 24); a `mobile/`-only commit, if any, ran CI and **did not** start Build Image |
| **D** — the rest of 013's server stories, **switched off** | Steps 2–4 of §8.1: HR Settings section, consent doctype and backfill, notice version bump, invites, E1–E3, E4/E5 extensions, E6, E9, hash-keyed limits, desk section, alerts, `/enrol`, daily job, counts, report, web page rows. **Not nginx** | Dry run on a copy repeated for the new patches; fresh `test_site` both with and without `alvoraa_goals`; manual dev backup; spec updated for the consent decisions (C-15) | CI green; deploy succeeded; every dev tenant's designation list is empty, so nobody can join; web-page phones still punch (they must not meet the consent gate); daily job ran once with a clean self-check; no Redis key holds a raw token |
| **E** — nginx body caps and zone (US-24) **alone** | `deploy/nginx.conf` only, on top of B | Both 014 scripts plus the new body-cap checks in a throwaway container; `nginx -t`; quiet moment | Production and dev 200; 2 MB body to the punch path on dev gets 413; security headers present on a device-path answer; no `emerg`. **No `main` deploy until this is on `main` too, or you accept the revert** (OPS-68) |
| Pilot build (not a push) | Manual `mobile-pilot` workflow run from `dev` | A–E green; Bitwarden and the offline key copy ready; pilot key made outside any git folder | Built-file checks pass; Firebase testers invited by name |
| Switch-on (a dev-stage action) | Demo tenant: designations picked, switch ticked, 7-day photo retention | Your word | OPS-53 switch test passes on dev before the first tester joins |
| **F** — `main` | 014 + 013 server + nginx | After the pilot and your word. Rehearsal and exact commands go in §5 | — |

**One more rule for B to E:** push each at a quiet hour, and push nothing else while one is
deploying. Every dev deploy restarts the nginx that production uses.

## 3. Image, Compose and migrations

### Image and Compose: no change (confirmed)

| Question | Answer | How I know |
|---|---|---|
| Does `mobile/` get into the image? | **No.** The Dockerfile copies only `hrms`, `alvoraa_goals` and `alvoraa_portal` | Read `deploy/Dockerfile` lines 51–53 |
| Build context | There is no `.dockerignore`, so `mobile/` is uploaded to the build and ignored. Small: `node_modules` and build outputs are git-ignored, and CI's checkout has none | Read |
| New queue or worker? | **No.** Daily job on `default`, alerts on `short`; `worker-default` listens on both | Read compose line 180 |
| New Redis? | **No.** Counters use the existing Redis (`noeviction`, append-only file on). Keys need an expiry (OPS-83) | Read compose line 84 |
| New server dependency? | One small QR **drawing** file in `alvoraa_portal/public/js/` for the desk. Pin its version and licence in the file. **Not checked:** whether Frappe's desk already ships a QR generator. Check before adding one | — |
| nginx | Only in Push E. nginx is a bind-mounted file, not Compose | 014 notes |

### Migrations — what runs, the risk, and what to check

| Change | What migrate does | Risk | Check on the copy |
|---|---|---|---|
| New doctypes `Alvoraa App Invite`, `Alvoraa App Consent`, `Alvoraa Field Worker Designation` | Creates three empty tables | Low. `test_invoicing` fails if the names are not added to `TENANT_DOCTYPES` | Tables exist; the test passes |
| `Alvoraa Field Device`: new statuses, fields, permissions | Adds columns to a table with a handful of rows; new Select options need no data change | **Custom DocPerm rows on a tenant override the JSON**, so create and delete could survive | Patch M4 removes them; count before and after |
| HR Settings custom fields (via `after_migrate`) | HR Settings is a Single, so no table change | **If any migrate code saves the HR Settings document, `alvoraa_goals`' `validate_hr_settings` runs and can refuse it on a tenant with incomplete review settings. That site's migrate then fails** | Set defaults with field defaults or a direct single-value write, never a document save. Fresh site with and without `alvoraa_goals`: `provision_tenant.sh` installs `alvoraa_goals` only on a condition, and after `alvoraa_portal` |
| `Employee Checkin.alvoraa_mock_location` | Adds a column to **the busiest table** (machine punches) | MariaDB can usually add a column without copying the table. **Not measured** | Time the migrate on the ppj copy; record the row count |
| `Employee.alvoraa_field_app_html` | HTML field, no column | None | — |
| Patch M2 + M4 (join method, hash moves, DocPerm) | Updates a few rows | Low. Must be safe to run twice | Run migrate twice; the second run changes 0 rows |
| **Patch M3 — consent backfill (C-4)**: phones joined on the web page count as already agreed | One `Agreed` / `Backfill` row per existing web phone | Duplicate rows on a second run; the wrong set of phones | Rows = web phones; second run adds 0 |
| **D19 notice version bump** | `CONSENT_VERSION` changes | **Web-page phones stop punching at deploy if the consent check reaches them** | Rule: the gate applies only where `join_method = App`. Only E3 writes `App`; an empty value counts as web. Pin test: a web phone whose row is for the old version still punches after the bump. Also check whether the page's service worker caches the page: a cached old page must still register, so the server must not require the page to send a version |
| Window between `up -d` and migrate in `deploy.yml` | New code runs against the old schema for seconds to about 5 minutes | A device call can fail on a missing column. Dev only; demo phones | Push at a quiet hour. No code workaround needed |

**Dry run on a copy, before Push C and again before Push D** (bench and your word needed,
following what slice 010 did on `ppj.localhost`, `REHEARSAL.md` §6–7): back up
`ppj.localhost`; migrate and time it; read the patch counts; migrate a second time; save HR
Settings once from the desk; trace the web check-in page (register, activate, punch,
refusal). Also build a fresh `test_site` the way CI does (lesson 6). A rehearsal on a copy
of production data belongs to §5, before Push F.

## 4. CI gates — what to add, in this order

| Order | Gate | Where | When it must exist |
|---|---|---|---|
| **1** | **Web page pin tests** (step 0): today's register, activate, punch, each refusal sentence, `field_status` keys | `alvoraa_portal/tests` — already run and blocking in CI | First commit of Push C. **This is the first gate**: slice 008 has no Python tests, and it costs no CI change |
| 2 | **Key guard**: ignore rules; a script that fails if `git ls-files` lists a key pattern; pinned secret scanner | Script in `scripts/`, one step at the end of `ci.yml`'s lint job, after 014's step; the same script before each push on this PC | Committed in the 013 worktree **before `npx cap add android`**; on `dev` with Push C, before any pilot key |
| 3 | **`build-image.yml` path filter** | `paths-ignore: mobile/**, .github/workflows/mobile.yml` | Push C, before any `mobile/`-only push |
| 4 | **`mobile.yml` app checks** (no keys needed): `npm ci`; `node --test`; outside-URL scan (including `jsdelivr` and `unpkg` strings inside JS); `innerHTML` lint; dependency deny-list (analytics, crash, ads, Firebase); codes table vs the server codes file; drift check on the copied capture code; Gradle wrapper validation | New workflow. Runs on `mobile/**` **and** on changes to the server codes file and contract files | From the first `mobile/` push |
| 5 | **Built-file checks**: build an unsigned release APK; read its manifest with `apkanalyzer`: only the five allowed permissions; not debuggable; no plain HTTP; backup off; network rules; bundled `capacitor.config.json` has no `server.url` or `allowNavigation`; host check allows only `https` and `.alvoraa.co`; APK ≤ 10 MB | `mobile.yml`, same job | Before the first pilot build |
| 6 | `allow_cors` never set | Bench test in `alvoraa_portal/tests` (OPS-47) | Push C or D |
| 7 | Contract replay per released app version | `mobile.yml` + `alvoraa_portal/tests` | From the first pilot build |
| 8 | **Signed pilot build** | Manual workflow, `mobile-pilot` environment, you approve | Before the pilot (A12) |
| — | iPhone builds in CI | Not in step 1. The `DEVELOPMENT_TEAM` check arrives with `ios/` (US-47) | Later |

**Should app builds run in CI now or later?** **Now**, unsigned, from the first `mobile/`
push: they are free while the repo is public and they catch permission and config drift
early. **Signed** pilot builds come later, just before the pilot. Store and iPhone builds are
not part of step 1.

**`hrms` tests and slice 008.** CI runs only the `alvoraa_goals` and `alvoraa_portal` test
suites. 013 edits no `hrms` file. It reuses Frappe HR's geofence check, so pin that reuse
through a field check-in test in `alvoraa_portal/tests`. 012 OPS-74 (run `hrms` tests in CI)
stays open, but it does not block this slice.

**Good news, checked through GitHub's API on 17 Sep 2026:** secret scanning and push
protection are **on** for this repo. Non-provider patterns and Dependabot security updates are
**off**.

## 5. Version pinning

Checked 17 Sep 2026.

| Tool | Recommend | Source / note |
|---|---|---|
| `@capacitor/core`, `/cli`, `/android` | **Exactly 8.5.2**, all the same, no `^` or `~`. `@capacitor/ios` only with US-47 | Latest on npm, published 11 Sep 2026 (GitHub release) |
| Secure storage plugin | Exact version, **only after** the spike confirms Capacitor 8 and 32-bit phones | Not checked (security's W4) |
| QR reader | Exact: jsQR 1.4.0 **or** zxing-wasm 3.1.4, after the spike. Lock file with integrity hashes | npm, 17 Sep 2026. jsQR: last release April 2021. zxing-wasm: MIT licence |
| Android Gradle Plugin (AGP, Android's build plugin) | **The version Capacitor 8.5.2 generates.** Capacitor's template on GitHub today: AGP 8.13.0 with Gradle 8.14.3. **Do not accept Android Studio's "upgrade AGP" prompt** | Newest AGP is 9.4.0 (Android docs, Sep 2026), a major version. Move only when Capacitor does |
| Gradle wrapper | Committed, with `distributionSha256Sum`; wrapper validation in CI | — |
| SDK levels | compileSdk 36, targetSdk 36, minSdk 24 | Capacitor template; Play needs target 36 since 31 Aug 2026 (OPS-15) |
| Build Tools | Write the exact version the first build uses into the pin file; install the same in CI | Which version AGP 8.13 picks by default: not checked |
| JDK (Java) | **21**: Android Studio's bundled copy on this PC; Temurin 21 in CI. Point `JAVA_HOME` or `org.gradle.java.home` at Studio's copy | AGP 8.13 needs 17 or newer. **Java 25 on this PC's PATH is likely too new for Gradle 8.14** (not tested). Studio's bundled version: check in Studio |
| Node | **24 LTS**: `.nvmrc` and `"engines"` in `mobile/field-app/package.json` | This PC 24.13.1; CI already uses 24; Capacitor 8 needs 22+; newest 24.x on nodejs.org is 24.21.0 |
| Android Studio | **2025.2.1 or newer, stable channel** | Capacitor 8 docs |
| Xcode (borrowed Mac) | 26.0 or newer | Capacitor 8 docs |
| Secret scanner | gitleaks **v8.30.1**, binary download checked against its published SHA-256 | GitHub release, 21 Mar 2026 |

**This PC (16 GB memory, Docker running the bench).** Test on a **USB phone, not an
emulator** (the engineer agrees). Keep Gradle's memory at about 2 GB in
`gradle.properties`. Do not build while a full bench test run is going: check the work board
first. Studio and the SDK need about 10–15 GB of the 115 GB free.

## OPS rows (continuing from §3)

| ID | Recommendation | Why | Cost of ignoring it | Level | Decision |
|---|---|---|---|---|---|
| OPS-67 | **Recommend:** the push order and the green checks in section 2: A → decide the waiting production run → B → C → D → E → pilot build → switch-on → F. One push deploying at a time, at quiet hours. | Each push changes one kind of thing, so a failure points at one cause. Every dev deploy restarts production's nginx. | Two unknowns land together; a broken deploy cannot be traced; production blinks during busy hours. | Recommend | |
| OPS-68 | **Recommend:** decide the production Deploy run waiting since 10:39 UTC before Push B, and never approve it while a dev deploy runs. After Push B, and again after Push E, approve no `main` deploy until the same nginx commit is on `main` — or approve knowing the fix is undone. | One server folder and one nginx serve both. A `main` deploy checks out `main`'s `nginx.conf` and restarts nginx. | 014's forged-address fix, or 013's body caps, silently disappear from production and dev. | Recommend | |
| OPS-69 | **Recommend:** bring `d6613ea` onto `dev` by cherry-picking that one commit, not by merging `main`. Then rebase 014 on top of it. | `main` also has `42c165d` (empty demo stubs that must not land on `dev`) and two merge commits. CLAUDE.md §1: rebase, never merge. | Demo stubs or merge commits on `dev`; 014 still built on the old certificate paths. | Recommend | |
| OPS-70 | **Recommend:** at Push B, you (not an agent) copy the live `/var/www/html/hr-app/deploy/nginx.conf` to a safe place, clear the in-place edit, push straight away with no nginx restart in between, then confirm the server folder is at the pushed commit with a clean `git status`. Exact commands go in §5, **for you to approve**. | `deploy.yml` falls back to checking out `main` without failing if the `dev` checkout is refused. A dev deploy could "succeed" on the wrong files. | nginx starts on the old certificate paths, or dev runs `main`'s Compose and nginx files unnoticed. | Recommend | |
| OPS-71 | **Recommend:** keep keys out locally, not only in CI. In the 013 worktree, before `npx cap add android`, commit the OPS-37 ignore rules plus `*.apk`, `*.aab`, `android/app/release/` and `android/app/build/`. The tracked-key script runs in CI **and** by hand (or as a local pre-push hook) before every push. gitleaks v8.30.1 pinned by checksum scans pushed commits in CI. | Public repo: a key is public the second it is pushed, whatever CI says afterwards. Push protection catches token patterns, not keystore files. | A pilot or upload key published to the world, with CI red after the damage. | Recommend | |
| OPS-72 | **Recommend:** `build-image.yml` gets `paths-ignore: [mobile/**, .github/workflows/mobile.yml]`. `ci.yml` gets **no** path filter. `deploy.yml` unchanged. **Test:** a `mobile/`-only commit starts CI but not Build Image. | App-only pushes should not rebuild the image or restart production's nginx. The key guard must still run. | Needless production nginx restarts on every app commit; or the key guard skipped on app pushes. | Recommend | |
| OPS-73 | **Consider:** also skip Build Image for pushes that change only `docs/**`. | Docs are not in the image. Today every docs-only push to `dev` rebuilds (about 8–14 min) and restarts production's nginx. | Extra restarts and deploys, and deploys that cancel each other on busy days (as on 10 Sep). | Consider | |
| OPS-74 | **Recommend:** `mobile.yml` from the first `mobile/` push: `npm ci`, `node --test`, outside-URL scan (also inside JS), `innerHTML` lint, dependency deny-list, codes table vs server codes file, capture-code drift check, Gradle wrapper validation. Runs on `mobile/**` and on changes to the server codes and contract files. | The app sits outside every existing check. The codes contract spans server and app. | Drift between app and server, or an outside URL, found by a tester instead of CI. | Recommend | |
| OPS-75 | **Recommend:** the built-file checks in section 4, gate 5, on an unsigned release APK, before the first pilot build. Read the built APK with `apkanalyzer`, not the source files. | Plugins add permissions and settings when the files are merged; only the built file shows the truth. | A pilot build ships with background location, plain HTTP, debugging or backup switched on. | Recommend | |
| OPS-76 | **Recommend:** the first test gate is the step 0 web-page pin tests, in the first commit of Push C. All 013 server tests go in `alvoraa_portal/tests`, including one that pins Frappe HR's geofence reuse. | Slice 008 has no Python tests. CI does not run `hrms` tests (012 OPS-74). | AC-35 ("the web page keeps working") protected by nothing. | Recommend | |
| OPS-77 | **Recommend:** the pins in section 5. Exact versions; lock file and `npm ci`; wrapper checksum; JDK 21 from Studio, not the Java 25 on PATH; no AGP upgrade ahead of Capacitor; Node 24 in `.nvmrc`. | OPS-41. A rebuild months later must pull the same tools. | "Works on my PC" builds; a Studio prompt moves AGP to 9.x and plugins stop building. | Recommend | |
| OPS-78 | **Recommend:** in the A6 spike, time jsQR 1.4.0 against zxing-wasm 3.1.4 on P1–P3, scan to "Is this you?" (≤ 2.5 s, AC-232). If zxing-wasm: bundle its decoder file and set `locateFile`, and let the outside-URL scan prove nothing loads from jsDelivr. Pin the winner exactly. | jsQR is unmaintained since 2021. zxing-wasm loads from a CDN by default (its README, read today). | A slow first scan on cheap phones; or a CDN request that leaks worker IPs and fails with no signal. | Recommend | |
| OPS-79 | **Recommend:** native HTTP with: CapacitorHttp's global switch off (explicit calls only); Capacitor's cookie handling off; redirects refused; 30 s timeouts set in code; a CI check on `capacitor.config`; a server test that device endpoints ignore cookies (AC-139). **To verify in the spike:** explicit calls work with the global switch off. | Keeps CORS off the shared nginx, and keeps every other request under the web view's normal rules. | A stray `fetch` bypasses the rules; a redirect sends the secret to another host; a hung request holds a worker at the gate. | Recommend | |
| OPS-80 | **Recommend:** the copied camera, photo and GPS code lives in one app file that names its source commit. A CI drift check fails when the web page's copied functions change without the app copy being reviewed. A dated follow-up after the pilot: one shared file for both. Photo size per channel in the daily counts. | The engineer's own verdict: maintainability degrades. | Web and app photos drift apart in size and quality, and nobody notices until HR complains. | Recommend | |
| OPS-81 | **Recommend:** migration rules from section 3. Never save the HR Settings document during migrate. The consent gate applies only where `join_method = App`. Backfill and patches must be safe to run twice. Time the `Employee Checkin` column on the ppj copy. Dry run before Pushes C and D. Build fresh sites with and without `alvoraa_goals`. | Two failures are likely without these: a site's migrate refused by `alvoraa_goals`, and web phones blocked by the notice bump. | A dev deploy half-migrated across tenants; demo web phones stop punching at deploy. | Recommend | |
| OPS-82 | **Recommend:** after Push D, never roll back by redeploying an older dev image or reverting past Push C. Roll back with the settings switch (OPS-65). Take a manual backup of the dev sites before Pushes B, C and D. | `deploy.yml`'s image-tag rollback makes the dangerous choice easy. Dev deploys take no backup. | Replaced or removed phones punch again; or no restore point on dev. | Recommend | |
| OPS-83 | **Recommend:** every Redis key 013 adds (rate counters, daily counts) has an expiry: counters at their window; daily counts about 3 days, because the daily pull stores the history elsewhere. | One Redis, `noeviction`, append-only file on. Nothing removes keys without an expiry. | Redis grows for ever; a full Redis stops queues and cache for every tenant. | Recommend | |
| OPS-84 | **Consider:** debug builds reach the local bench through `adb reverse tcp:8010 tcp:8010` over USB, so the app uses `http://localhost:8010`. The debug network rule allows plain HTTP to `localhost` only. CI checks that pilot and release bundles contain no `localhost` allowance. After any `bench use`, restart `hrlocal-bench` (lesson 12). | Nothing is exposed on Wi-Fi or Tailscale, and the phone does not need the same network. | A debug rule naming a network address that is later reused; or a debug host left in a pilot build. | Consider | |
| OPS-85 | **FYI:** on this PC, point Gradle at Android Studio's Java, keep Gradle's memory near 2 GB, test on a USB phone, and do not build during full bench test runs (check the work board). | 16 GB shared with Docker; Java 25 on PATH. | Slow builds, a frozen bench run, or a confusing Gradle Java error. | FYI | |
| OPS-86 | **FYI:** Push A reached `origin/dev` at 12:37 UTC on 17 Sep (`9138251`). CI and Build Image were in progress when checked. The engineer's §10.1 is out of date; 014 is next once A is green. | Read with `git fetch` and `gh run list`. | Planning against a release state that no longer exists. | FYI | |
| OPS-87 | **Recommend (security engineer):** run a one-off secret and personal-data scan of the full git history (gitleaks, by hand), triage the results, and report before any new code is pushed. Make full-history scanning blocking only after triage. | Repo is public (checked). A `build-image.yml` comment says the history holds customer data. **Not verified.** | Personal data or old credentials stay public, and a blocking scan jams CI on day one. | Recommend | |
| OPS-88 | **Consider:** turn on Dependabot alerts for `mobile/field-app` (npm and Gradle), alerts only, no automatic update pull requests. | Security updates are off today (checked). The app adds a new set of dependencies that ship to phones. | A known hole in a plugin found late, after it has been installed on workers' phones. | Consider | |

## What I did and did not check

| Checked | How |
|---|---|
| `origin/dev` = local `dev` = `9138251`; `main`-only commits `2fc623c`, `d6613ea`, `42c165d`, `d99ba99`; 014 is five commits on `8a53522`, which is on `origin/dev` | `git fetch`, `git log`, `git merge-base` |
| CI and Build Image running for `9138251`; production Deploy for `main` pending since 10:39 UTC | `gh run list`, `gh run view` |
| Repo public; secret scanning and push protection on; Dependabot security updates off | `gh api repos/.../hr-app` |
| Image copies only three apps; no `.dockerignore`; workers and queues; Redis `noeviction` | Read `Dockerfile`, `docker-compose.app.yml` |
| `ci.yml` runs only `alvoraa_goals` and `alvoraa_portal` tests; `deploy.yml` falls back to `main` and restarts the shared nginx; dev deploys take no backup | Read workflows |
| New tenants install `alvoraa_goals` after `alvoraa_portal`, on a condition | Read `provision_tenant.sh` |
| Capacitor 8.5.2; its Android template AGP 8.13.0, Gradle 8.14.3, SDK 36/36/24; Capacitor 8 needs Studio 2025.2.1+, Node 22+, Xcode 26+ | npm registry, GitHub, capacitorjs.com, 17 Sep 2026 |
| jsQR 1.4.0 (April 2021; last commit August 2021); zxing-wasm 3.1.4, MIT, 1.04 MB decoder, CDN by default | npm registry, GitHub, zxing-wasm README, 17 Sep 2026 |
| AGP 9.4.0 newest; Node 24.21.0; gitleaks v8.30.1 | Android developer docs, nodejs.org, GitHub, 17 Sep 2026 |

**Not checked:** whether the git history really holds customer data; whether Push A's CI and
deploy ended green; whether explicit CapacitorHttp calls work with the global switch off;
which Build Tools version AGP 8.13 uses; which Java Android Studio bundles; whether GitHub's
Ubuntu runner already has SDK 36 installed; whether Frappe's desk ships a QR generator; how
long the `Employee Checkin` column takes on real data; what the web page's service worker
caches; whether git refuses the server-folder checkout when the local edit matches the
target. Nothing was run on the local bench, dev or production.

## Sources (read 17 Sep 2026)

- [Capacitor — environment setup (v8)](https://capacitorjs.com/docs/getting-started/environment-setup)
- [npm — @capacitor/core latest](https://registry.npmjs.org/@capacitor/core/latest)
- [Capacitor Android template — build.gradle](https://raw.githubusercontent.com/ionic-team/capacitor/main/android-template/build.gradle)
- [Capacitor Android template — variables.gradle](https://raw.githubusercontent.com/ionic-team/capacitor/main/android-template/variables.gradle)
- [Capacitor Android template — gradle-wrapper.properties](https://raw.githubusercontent.com/ionic-team/capacitor/main/android-template/gradle/wrapper/gradle-wrapper.properties)
- [Android Gradle plugin release notes](https://developer.android.com/build/releases/gradle-plugin)
- [npm — jsqr](https://registry.npmjs.org/jsqr)
- [npm — zxing-wasm latest](https://registry.npmjs.org/zxing-wasm/latest)
- [zxing-wasm README](https://github.com/Sec-ant/zxing-wasm)
- [Node.js release index](https://nodejs.org/dist/index.json)
- [gitleaks releases](https://github.com/gitleaks/gitleaks/releases)
