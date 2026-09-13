# Native app — auto-checkout on leaving site, and route tracking for drivers

**Written:** 13 Sep 2026 · **Updated:** 13 Sep 2026, adding route tracking and the
hybrid build route.
**Decision so far:** Surbhi chose **a native app** (option C) over the two
foreground-only shapes.
**Status:** not started. This is the plan and the decisions it needs.

---

## 0. The short version

- **Build it as a native shell around the web app we already have** (Capacitor),
  not as a rewrite. The screens, the device-token login, the punch API and the
  geofence are built, tested on a real phone, and demoed. Only background
  location needs to be native. This roughly halves the work.
- **Two background features**, both role-scoped and switched on per organisation:
  1. **Auto-checkout** when someone is outside their site for longer than a set
     time (default 5 minutes).
  2. **Route tracking** for roles whose job *is* moving — drivers, delivery,
     field sales — recorded only while on duty.
- **The long pole is store approval**, not code. Start the Google declaration in
  week one.

---

## 1. What was asked for

> An organisation can choose to auto-log-out an employee who moves outside the
> geographic boundary of their site for longer than a set time, defaulting to
> **5 minutes**. They must check in again manually when they return — from the
> phone app or the web application.

> Track the route taken by some roles, such as drivers.

## 2. Why a native app at all

A web page **stops running** when the phone locks or the user switches away. iOS
gives web apps no background location; Android's is unreliable and killed by most
Indian OEM battery managers. So a web app can only see someone move while it is
open on screen — which is not how a driver carries a phone.

Only a native app can register geofences with the operating system and keep
recording location in the background.

---

## 3. ⚠ This overrides a standing product rule — and route tracking widens it

`.claude/context/product-context.md` §6 lists **passive behavioural monitoring**
among things Alvoraa does not build.

- **Auto-checkout** needs background location but records only *inside or
  outside*, not a history. A narrow exception.
- **Route tracking records a movement history of a named person.** That is
  squarely what the rule was written about. It is a legitimate and common need
  for a driver — proof of delivery, fuel and mileage claims, safety, dispatch —
  but it is a **bigger** exception, and the line has to be drawn deliberately.

This is the user's decision and the user has made it. Write it into §6 so the
next request cannot reasonably say "we already track them":

| Allowed | Still refused |
|---|---|
| Route tracking **only for roles the organisation names**, whose work is movement | Route tracking for office or store staff |
| **Only while checked in** — never before a shift, after it, or on a day off | Any location recorded outside duty |
| Viewed by the person's **own manager or dispatcher, and HR** | Visible to colleagues |
| Used for routes, mileage, delivery proof, safety | Scoring, ranking or inferring anything about a person from where they went |
| Kept for a **set period**, then deleted | Kept indefinitely |
| **The employee can see their own route** | A record the person it is about cannot see |

The last row matters most. People accept being tracked for work far more readily
when they can see exactly what was recorded.

---

## 4. How to use the web features directly in the native app

This is the question that decides the whole estimate.

### The options

| Approach | What it is | Background location? | Reuses our web app? | Verdict |
|---|---|---|---|---|
| **Trusted Web Activity (TWA)** | Our PWA published on the Play Store, running in full Chrome | ❌ **No** — it is still a web page | 100% | Gets us into the store; does **not** solve the problem |
| **Capacitor** *(recommended)* | A native Android/iOS shell whose screens are our web app, with native plugins for what the web cannot do | ✅ via a native plugin | **Almost 100%** | **Recommended** |
| React Native or Flutter | Rewrite the screens natively | ✅ | ❌ rebuild everything | Only if the web UI proves too slow |
| Fully native (Kotlin + Swift) | Two separate apps | ✅ | ❌ | Two codebases; not justified here |

### Why Capacitor fits us specifically

- **`field-checkin.html` is already a self-contained mobile page.** It becomes the
  app's screen almost unchanged.
- **The whole ESS portal can come along** — leave, payslips, the org chart — so
  the driver app is the employee app, not a second thing to install.
- Native is added **only where the web cannot reach**:

| Native plugin | Replaces |
|---|---|
| Background geolocation | Nothing — the web cannot do this at all |
| OS geofencing | Nothing — same |
| Secure storage (Keychain / Keystore) | `localStorage` for the device secret — better, since it survives cache clears and is harder to extract |
| Push notifications | Nothing — "you were checked out at 3:12 pm" needs this |
| Camera (optional) | The web camera works today; native gives more reliable focus and exposure in sunlight |

- **One codebase for Android and iOS**, and the same web code keeps running in a
  browser, so the web app never falls out of step with the native one.

### How the web page and native code talk

The page calls native features through a small JavaScript bridge, and falls back
gracefully when it is running in an ordinary browser:

```js
if (window.Capacitor && Capacitor.isNativePlatform()) {
  // running inside the app: start background tracking
  await BackgroundGeolocation.start({ ... });
} else {
  // running in Chrome: behave exactly as the web app does today
}
```

So **one page serves both**, and nothing we have tested stops working.

### What to check before committing

- **The background-location plugin.** The strongest option on Android is a
  commercial plugin that needs a paid licence for release builds; free community
  plugins exist but are less battle-tested against Indian OEM battery managers.
  `[verify licence terms and current plugin maturity before choosing]`
- **Apple's "minimum functionality" rule** (guideline 4.2) rejects apps that are
  only a website in a wrapper. Background geofencing and push are real native
  features, which is the argument that it is not — but expect to make it.
- **The server address comes back.** The web app no longer asks for one, because
  a page knows where it came from. A single native app installed from the store
  does not. See N2.

---

## 4a. One app for every tenant — how it knows who it belongs to

**Decided 13 Sep 2026: one app for all tenants.** A single listing in each store,
not a build per customer.

That brings back a question the web app never has. A page opened at
`ppj.alvoraa.co/checkin` knows it belongs to PP Jewellers — it came from there. An
app installed from the Play Store does not. Something has to tell it.

Every tenant lives at `{subdomain}.alvoraa.co` (`tenant_api.create_tenant`), and
the control plane knows the full list. So the problem is only: **how does the phone
learn which subdomain?**

### The options

| | How | Driver types | Verdict |
|---|---|---|---|
| **A · QR code from HR** *(recommended)* | HR shows or prints a QR per employee. Scanning it opens the app already pointed at the right tenant, for the right person | **Nothing** | **Recommended** |
| **B · Tenant code** *(fallback)* | Type a short code such as `ppj`; the app looks it up | A few letters | Keep as the fallback when there is no QR |
| C · Phone number or email lookup | Enter a number; the platform finds the employer | A number | ❌ Tells anyone which company a phone number works for. Many drivers have no email |
| D · Build per customer | A separate app for each tenant | Nothing | ❌ Ruled out — one app for all |

### Recommended: an HR-issued enrolment QR

The QR carries a link of this shape:

```
https://ppj.alvoraa.co/enrol?t=<one-time token>
```

**It solves three problems at once**, which is why it is worth building properly:

| Problem | How the QR solves it |
|---|---|
| **Which tenant?** | The tenant's address is **in the link**. No lookup, no directory, no control plane in the path |
| **Which employee?** | The token is bound to one employee when HR generates it |
| **The HR approval pause** | HR generating the QR **is** the approval. Scanning it enrols and activates in one step. The "waiting for HR" screen disappears for anyone enrolled this way |

And one more that falls out for free: **the same QR works whether or not the app
is installed.** Android App Links and iOS Universal Links open the app when it is
there; when it is not, the link opens the web page, which works as the PWA it is
today and can offer to install the app.

### What keeps the QR from being a hole

A QR is a secret that can be photographed. So the token is built like the device
secret we already have:

- **Single use.** The first scan consumes it. A photo of a used QR does nothing.
- **Expires**, suggest **24 hours**. HR generates it when the person is about to
  set up, not weeks ahead.
- **Bound to one employee** on one tenant. It cannot be pointed anywhere else.
- **Stored only as a hash**, never in clear.
- **Rate limited**, and every redemption lands in the audit trail with the device
  that used it.
- **Revocable** by HR before it is used.

### The fallback: a tenant code

For a driver with no QR to hand, the app asks for a short code.

- The app calls **one** lookup endpoint on the control plane:
  `resolve_tenant(code) → https://ppj.alvoraa.co`
- **Exact match only.** It never lists tenants, never suggests, and a wrong code
  gets the same answer as a code that does not exist, so it cannot be used to
  discover who our customers are.
- **Rate limited per caller.**
- Enrolment then continues as today: employee ID, **HR approves**. The code only
  identifies the tenant; unlike the QR, it proves nothing about the person.

### After the tenant is known

The app reads **that tenant's** manifest and branding — the endpoints already
exist — so one installed app still shows each customer's own name and colours.

The tenant address, device secret and branding are kept in native secure storage.

### Things this makes more urgent

- **The wildcard certificate** (`09-wildcard-certificate.md`). One app talking to
  every tenant subdomain needs HTTPS on all of them. Today each tenant needs a
  certificate command run by hand, and the platform stops at 100 tenants.
- **Custom domains.** `host_name` is already stored per tenant. If a customer later
  wants `attendance.ppjewellers.com`, the QR just carries that address instead —
  nothing in the app changes. The tenant-code lookup returns it too.

### Edge cases

- **An employee who works for two tenants.** Rare, but real for contractors. The
  app keeps one tenant at a time with a "switch organisation" option in settings;
  switching needs a fresh enrolment for the other tenant.
- **A lost phone.** HR blocks the device, as today. A new QR enrols the new phone.
- **An employee who leaves.** The device is blocked automatically, as today, and
  any unused enrolment QR for them is revoked.

---

## 4b. Which of our existing pages can go straight into the app — page by page

Written from the code, 13 Sep 2026, not from general advice.

### Two ways a page can live in a Capacitor app

| | **Bundled** | **Remote** |
|---|---|---|
| What | The HTML, JS and CSS ship **inside** the app | The app's web view opens `https://{tenant}.alvoraa.co/...` |
| Works with no signal | ✅ opens instantly, can queue punches | ❌ blank screen |
| Native features (background location, push) | ✅ always available | ⚠ only if the tenant host is allow-listed |
| Apple "just a website" rule (4.2) | Safer | **Riskier** |
| Server-rendered pages (Jinja) | ❌ nothing renders them | ✅ Frappe renders them as today |
| Login by session cookie + CSRF | ❌ breaks across origins | ✅ works — same origin |
| Login by device token | ✅ | ✅ |

**The deciding facts are how a page is rendered and how it logs in.**

### Our pages

| Page | Built with | Logs in by | Verdict |
|---|---|---|---|
| **`field-checkin.html`** — the phone app | Plain HTML + JS, 1,234 lines, **11** Jinja tags (tenant name, brand colours, notice facts) | **Device token.** No cookie, no CSRF | ✅ **Bundle it.** It is already nearly self-contained. See the list below |
| **`hrms-employee.html`** — the ESS portal | Plain HTML + JS, **17,085** lines, one Jinja include | **Session cookie + CSRF**, with a retry on a stale token | ⚠ **Load remotely** in a second tab. Too large and too tied to the session to bundle, and it does not need background features |
| `driver-portal.html`, `vendor-portal.html` | Plain HTML + JS, 2.5k and 1.5k lines, 4 includes, `frappe.call` | Session cookie | ⚠ Remote, same reasoning |
| `goals-portal.html` | 15 lines — a redirect to the ESS portal | — | Nothing to move |
| `alvoraa-login.html` | Plain HTML + JS | Login form → session cookie | Needed only so the remote tabs can sign in |

### The one outside our code worth knowing about

**Frappe HR ships its own mobile app at `/hrms`** (`hrms/frontend`), built with
**Vue 3, `@ionic/vue` 7, Vite and frappe-ui**, with an `ionic.config.json` already
present.

Ionic is made by the same company as Capacitor, and an Ionic app is designed to
be wrapped by it. **It is the most native-ready code anywhere in our stack.**

The catch: it is **upstream Frappe code**. Adding native plugins means carrying a
fork that has to be re-merged at every Frappe HR release. Worth it only if we
decide the employee app should *be* Frappe HR's app rather than our ESS portal.

### What `field-checkin.html` needs to be bundled

Small, and all of it known:

| Today | For the app | Why |
|---|---|---|
| API calls are relative: `/api/method/...` | `BASE + "/api/method/..."` — `BASE` from the enrolment QR, or `location.origin` in a browser | A bundled page has no server origin to be relative to |
| Tenant name rendered by Jinja (6 places) | Read from the `manifest` endpoint at start-up | It already returns the name and colours |
| Brand colours via `{% include brand_color.html %}` | The same logic as a plain `.js` file, fed by the manifest values | Nothing renders a Jinja include inside an app |
| Notice facts (retention days, notice version) rendered by Jinja | A small `app_config` endpoint | So the notice stays truthful per tenant |
| Device secret in `localStorage` | Native secure storage | Survives cache clears; harder to extract |
| — | **CORS** on Frappe, allowing **only** Capacitor's origins | A bundled page calls the tenant from a different origin |

**On CORS specifically:** these endpoints authenticate by device token, **not** by
cookie. So allowing cross-origin calls does not create a CSRF risk — a hostile
website has no ambient credential to borrow. It should still be an allow-list of
the Capacitor origins, never `*`.

**The page stays one file.** It checks whether it is running inside the app and
uses `BASE` and native storage if so; in a browser it behaves exactly as it does
today. Nothing already tested stops working.

### Recommendation

**A hybrid app with two tabs:**

1. **Attendance** — `field-checkin.html`, **bundled**. The part that needs
   background location, push, and to work with no signal.
2. **My HR** — the ESS portal, **loaded remotely**. Leave, payslips, the org chart.
   Works as it does today; no rewrite.

That gets drivers a real app in weeks without rebuilding a 17,000-line portal,
keeps the web app and the native app running the **same** attendance code, and
leaves the Frappe HR Ionic app as an option to revisit rather than a fork to
maintain from day one.

---

## 5. What this actually costs

### The long pole is the stores

Android's `ACCESS_BACKGROUND_LOCATION` needs a **written declaration**, a **video**
showing the in-app disclosure appearing **before** the permission prompt, and
review. It takes **days to weeks** and is **commonly rejected first time**,
usually over the disclosure screen. Fleet and delivery tracking is an accepted
use case, which helps route tracking; auto-checkout alone is a weaker argument.

Apple requires `Always` location with a clear purpose string, and reviews it.

**Treat store review as the schedule.**

### Indian handsets will fight it

Xiaomi, Oppo, Vivo, Realme and OnePlus kill background apps by default. Each
handset needs **Autostart** on and **battery optimisation** off, by hand. For PPJ's
drivers that is a rollout task — someone physically sets up each phone — and it is
the single most likely reason this "does not work" in the field. Code cannot fix it.

### Battery — auto-checkout and route tracking are very different

| | Auto-checkout | Route tracking |
|---|---|---|
| How | OS geofence — the phone wakes the app only when a boundary is crossed | Location samples while moving |
| Battery | **Negligible** | **Real** — must be managed |
| Design rule | Never poll GPS for this | Sample by distance moved, not by clock; stop when stationary; stop entirely on check-out |

A route tracker that polls GPS every few seconds all day will be uninstalled by
lunchtime.

### Data volume

A driver sampled every ~50 m over an eight-hour shift is a few hundred to a few
thousand points a day. Store **routes as simplified polylines**, not raw points
forever — keep full resolution for the retention period, then keep only the
summary (distance, start, end) or nothing.

---

## 6. Shape of the build

| Piece | Notes |
|---|---|
| **App shell** | Capacitor, wrapping `field-checkin.html` and optionally the ESS portal |
| **Enrolment** | Unchanged: employee ID, HR approves the device. The secret moves to native secure storage |
| **Tenant** | See N2 — a tenant code at first launch, or a build per customer |
| **Auto-checkout** | On check-in, register the site's geofence with the OS. On an exit event, start the grace timer; if still outside when it fires, call `auto_checkout`. On check-out, remove the geofence |
| **Re-entry** | **Nothing automatic.** The employee checks in again by hand, from the app or the web portal. An automatic check-in would credit time nobody confirmed |
| **Route tracking** | Only for designations the organisation names, only while checked in. Batched uploads to a `route_points` endpoint, so a dead zone does not lose a route |
| **Server** | `auto_checkout` and `route_points` endpoints; a Route record per shift; checkouts marked **automatic** and visible to HR and the employee |
| **Settings (Org Settings)** | `auto_checkout_enabled`, `grace_minutes` (5), `route_tracking_designations`, `route_retention_days` |
| **Views** | Employee: their own route and any automatic checkouts. Manager/dispatcher: their team's routes. HR: all. **Never colleagues** |
| **Web app** | The boundary **already works** on the web portal — Frappe HR enforces the radius on every `Employee Checkin` insert. Only the wording needs the friendlier rewrite the phone app has |

---

## 7. Decisions needed before anyone starts

| # | Decision | Why it blocks |
|---|---|---|
| **N1** | ~~React Native or Flutter?~~ **Capacitor wrapping the web app** — recommended in §4. Confirm | Sets the whole estimate |
| **N2** | ~~One app or a build per customer?~~ **One app for all tenants** — decided 13 Sep 2026. Identified by an HR-issued enrolment QR, with a tenant code as fallback. See §4a | — |
| **N3** | Is auto-checkout time **paid**? | Pointless if nobody acts on it, harmful if it silently docks pay. Needs a policy, not just a setting |
| **N4** | Does the employee **see their own** route and exits? | **Strongly recommend yes.** It is the difference between a tool and surveillance |
| **N5** | Tracking **only while checked in**? | **Strongly recommend yes.** Off-duty location is very hard to defend |
| **N6** | Which designations get route tracking, and who decides per customer? | Scope, and the §3 boundary |
| **N7** | How long are routes kept? | Suggest 90 days full resolution, then summary only — aligned with photo retention |
| **N8** | Commercial or free background-location plugin? | Licence cost vs reliability on Indian handsets |
| **N9** | Keep shipping the web app? | **Recommend yes** — no store approval, works today, and the fallback when a handset kills the native one |
| **N10** | QR token lifetime — suggest **24 hours** | How far ahead HR can prepare enrolment for a batch of new drivers |

---

## 8. Suggested order

1. Decide N1–N9 and write the §6 exception (a day or two).
2. **Start both store submissions early with a throwaway build.** The Google
   declaration can be rejected; find that out in week one, not week five.
3. Capacitor shell around the existing field app. Move the device secret into
   secure storage. **Should run on a phone within days**, because the screens exist.
4. Auto-checkout: OS geofence plus the exit timer.
5. Route tracking for named designations, with batched uploads.
6. Views: the employee's own route, the manager's team, HR.
7. Pilot on **five** PPJ phones across different handset makes, battery settings
   done by hand, for two weeks. Count missed exits and gaps in routes.
8. Only then roll out.

**Estimate: 3–5 weeks** with Capacitor, of which perhaps two are store review.
A React Native or Flutter rewrite would add roughly two to three weeks on top.

---

## 9. What to tell a customer until it ships

Attendance is marked at check-in and check-out. The geofence is enforced **at the
moment of each punch**, from the phone app and the web portal. Nobody is tracked
between punches.

That is true today, and it is a good story on its own.
