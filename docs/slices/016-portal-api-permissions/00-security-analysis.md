# Slice 016 — Vendor / driver / delivery portal API permissions

**Security analysis. 18 September 2026. Analysis only — no code was changed.**
Author: security & privacy engineer. Read against the code on branch `dev`, commit `b7244c8`.

---

## The short version

The vendor, driver and delivery portal has **37 whitelisted endpoints**. **23 of them
accept a record id from the caller and never check that the caller has anything to do
with that record.** Any person who can log in to that tenant — an ordinary employee, a
vendor, a driver, a departing employee whose session still works — can call them
directly from a browser console.

**Worst case in one sentence:** one logged-in user, with a handful of calls and no
special role, can list every vendor and every driver in the tenant, pull every vendor's
order history with customer names, phone numbers, addresses and order values, watch a
named driver's live GPS position, mark other people's deliveries as delivered, and file
star ratings that feed those drivers' performance scorecards.

**Who is hurt today: probably nobody.** Per the note of 17 September 2026 there is no
onboarded customer; PPJ is a demo. That is the only reason this is not an incident. It
stops being true at the first live tenant.

**Not cross-tenant.** Each tenant is a separate Frappe site (`deploy/provision_tenant.sh`
line 69, `bench new-site` per tenant). Everything below is within one tenant. That keeps
it off the top of the scale, but it is still every person in that tenant's delivery
operation.

---

## 1 · Threat model, in four lines

1. **Who wants this data, and what is the cheapest way to get it?** Not an outsider. A
   competitor's vendor with a portal login who wants to see what other vendors order and
   at what price. A curious employee who wants to know where a driver is. A driver who
   wants a better scorecard than the one he earned. The cheapest way is
   `frappe.call({method: "alvoraa_portal.portal_api.get_all_vendors"})` typed into the
   browser console on a page they are already allowed to open.
2. **Blast radius of one mistake.** Every vendor, every driver and every delivery in one
   tenant. Not cross-tenant.
3. **What does this make possible that was impossible before?** Nothing new — this code
   predates the HR product and has been like this since it was written. What is new is
   that the repository is public (note of 17 Sep 2026), so the endpoint names and the
   absence of checks are readable by anyone, and a first customer is expected soon.
4. **How would we find out?** We would not. There is no refusal log, no rate limit and
   no alert on any of these paths. `hrms/alvoraa_hr_core/access.py` has a refusal logger;
   none of this code uses it. Detection is the larger gap, not prevention.

---

## 2 · How I judged "checked" or "not checked"

Three mechanics decide whether a Frappe endpoint is protected. They are easy to confuse,
and the confusion is most of this report:

| Call | Does it check the caller's permission? |
|---|---|
| `frappe.db.get_value` / `frappe.db.set_value` / `frappe.db.sql` | **No, never.** |
| `frappe.get_doc(...)` (loading) | **No.** Loading a document runs no read check. |
| `frappe.get_all(...)` | **No.** `get_all` is the permission-ignoring variant; `get_list` is the checking one. |
| `doc.save()` / `doc.insert()` without `ignore_permissions` | **Yes** — write permission is checked. |
| `doc.save(ignore_permissions=True)` | No. |

⚠ **One claim here I could not verify in this repo:** that `frappe.get_all` ignores
permissions. The Frappe framework source is not checked into this repository and I was
told not to run bench. This is documented, long-standing Frappe behaviour, and the whole
"read" half of this report rests on it. **It must be confirmed on the bench against the
installed Frappe version before the fix is designed** — one line: call `get_all` on
`Delivery Order` as a plain Website User and see whether rows come back.

The doctype permission rules are the same on all eight delivery/vendor doctypes: only
**System Manager** and **HR Manager** have read or write. No row scoping, no `if_owner`.
So the only thing actually stopping an ordinary user anywhere in this module is a
`doc.save()` that was not told to ignore permissions.

---

## 3 · Full inventory

Guest column: **no endpoint in this area is guest-accessible** except `vendor_login`.
Both portal pages redirect a guest to the login page
(`www/driver_portal.py:7`, `www/vendor_portal.py:18`). "Any user" below means **any
logged-in user of that tenant, whatever their role.**

### 3.1 · `alvoraa_portal/alvoraa_portal/portal_api.py` — 11 endpoints

| Line | Endpoint | Reads / writes | Caller check | Plan gate | What a hostile caller gets |
|---|---|---|---|---|---|
| 30 | `get_portal_context` | reads Vendor User, Delivery Partner | none needed for itself, **but returns `{"type": "admin"}` to anyone who is neither a vendor nor a driver** | none | The page then shows the admin bar with the vendor and driver pickers. Every ordinary employee is treated as an operator. This is the design flaw the other findings hang off. |
| 65 | `get_vendor_orders(vendor_id)` | reads Vendor Order, Delivery Assignment, Delivery Partner — `ignore_permissions=True` | **none** | none | Any user can read **every order of every vendor**: order dates, values, status, the assigned driver's name, vehicle registration **and the driver's personal mobile number** (line 97). |
| 104 | `get_order_live_location(vendor_order)` | reads Vendor Order, Delivery Assignment, raw SQL on Vehicle Tracking | **none** | none | Any user can get a named driver's latest GPS fix, speed, heading and a 20-point breadcrumb trail for any order. Worse: when the order has no vehicle, lines 153–159 fall back to **the most recent tracking row of any partner in the tenant**, so a caller who passes a made-up order id still gets a live driver position and name. |
| 225 | `update_driver_location(...)` | writes Vehicle Tracking, `ignore_permissions=True` | **yes — fixed in slice 014** (line 236) | none | Nothing. This is the shape the rest should copy, and the only endpoint here with a test (`tests/test_driver_location_014.py`). |
| 263 | `get_driver_deliveries(partner_id)` | reads Delivery Order, `ignore_permissions=True` | **none** | none | Any user can read **any driver's whole delivery list**: customer name, full delivery address, delivery coordinates, order value, on-time status. This is the single richest personal-data leak in the module. |
| 290 | `driver_advance_status(delivery_order, new_status)` | writes Delivery Order via `db.set_value` | **none** — the comment at line 293 says the check was deliberately skipped because "drivers are Website Users" | none | Any user can walk **anyone's** delivery through the status chain, including marking it **Delivered** and stamping an on-time result that feeds the driver's scorecard and commission. |
| 318 | `submit_order_rating(order_name, rating, comment)` | writes Order Rating (`ignore_permissions=True`), writes Vendor Order | **none** — no check that the caller is the vendor on that order | none | Any user can file a one-off, un-retractable star rating and free-text comment against any delivered order. Ratings roll into `Driver Rating Summary` hourly (`hooks.py` scheduler) and into the performance scorecard. A driver can rate their own deliveries five stars; a colleague can rate a rival one star. |
| 352 | `get_all_vendors()` | reads Vendor, `ignore_permissions=True` | **none** | none | The full customer list of the tenant, with account status. Enumeration seed for everything above. |
| 361 | `get_all_partners()` | reads Delivery Partner, `ignore_permissions=True` | **none** | none | Every driver's id, name and hub. Enumeration seed for the driver-side endpoints. |
| 370 | `get_delivery_route(delivery_order)` | raw SQL on Vehicle Tracking | **none** | none | Up to 200 GPS points for any delivery — a movement history of a named worker. |
| 381 | `get_drivers_performance()` | reads Delivery Partner + raw SQL, `ignore_permissions=True` | **none**, despite the docstring saying "Admin use only" | none | Every driver's name, hub, vehicle type, **personal phone number**, delivery volumes, on-time rate and average customer rating, ranked. A performance league table of named employees, handed to anyone who asks. |

### 3.2 · `controllers/` — 17 endpoints

| File:line | Endpoint | Reads / writes | Caller check | What a hostile caller gets |
|---|---|---|---|---|
| `delivery_assignment.py:180` | `update_gps_location(assignment_name, lat, lng, eta_minutes)` | appends to Delivery Tracking, `save(ignore_permissions=True)` | **none** | Any user can write a fake position and ETA onto any assignment, broadcast it to the live tracking room, and — by passing `eta_minutes <= 10` — **make the system send an email to that vendor** saying the delivery is arriving. An outbound message to a third party, triggered by an unauthenticated-in-substance caller. |
| `delivery_assignment.py:218` | `verify_delivery_otp(assignment_name, entered_otp)` | reads and writes Delivery Assignment and Vendor Order via `db.*` | **none, and no attempt limit** | Unlimited OTP guesses against any assignment. On success the delivery and the vendor order are both marked Delivered. The OTP is six digits and there is no lockout, no delay and no log. |
| `delivery_order.py:218` | `update_delivery_status` | `get_doc` then `doc.save()` | **write permission only** — so HR Manager / System Manager, no ownership or hub scoping | An HR Manager in an unrelated part of the business can change any delivery's status. Medium, not high. |
| `delivery_order.py:281` | `assign_partner_to_order` | `doc.save()` | write permission only | Same class. Also emails the partner the customer name and address. |
| `delivery_order.py:334` | `mark_proof_of_delivery` | `doc.save()` | write permission only | Same class. Writes photo and signature references. |
| `delivery_order.py:349` | `get_partner_today_orders(partner_name)` | `frappe.get_all` | **none** | Today's orders for any driver, **including `customer_phone`** and special instructions. |
| `delivery_order.py:370` | `get_hub_live_summary(hub_name)` | `frappe.get_all` | **none** | Volume and status counts per hub. Low on its own. |
| `delivery_partner.py:46` | `get_partner_performance_summary(partner_name)` | `get_doc` + `db.get_value` | **none** | Any user gets a named driver's total deliveries, on-time percentage, customer rating, **safety incidents**, and from the latest scorecard **`commission_earned`, `bonuses_earned` and `net_amount`** — that person's pay. Plus their vehicle compliance alerts. |
| `delivery_partner.py:85` | `update_partner_stats_from_orders(partner_name)` | recomputes and `db.set_value`s on Delivery Partner | **none** | A write endpoint that anyone can fire. Not directly dangerous, but it rewrites the performance fields on an employee record with no audit entry. |
| `delivery_partner.py:157` | `get_today_orders_for_partner(partner_name)` | `frappe.get_all` | **none** | Same exposure as `get_partner_today_orders`. Two endpoints doing the same job is itself a finding. |
| `delivery_feedback.py:166` | `get_partner_feedback_summary(partner_name, month, year)` | `frappe.get_all` | **none** | A named driver's rating distribution and complaint counts, by month. |
| `delivery_tracking.py` | *(no whitelisted endpoint)* | helper only | — | Called by the vendor API, which does check ownership. |
| `rating.py:131` | `get_driver_ratings(driver_id)` | `frappe.get_value` | **none** | A named driver's average quality, timeliness and professionalism scores. |
| `scorecard.py:141` | `generate_scorecard_for_partner(partner, month, year)` | creates / overwrites Delivery Performance Scorecard, `save(ignore_permissions=True)` | **none** | Any user can regenerate — and therefore overwrite — a driver's monthly scorecard, including the commission figures on it. If the underlying data has moved, the old record is gone. There is no version history and no audit entry. |
| `scorecard.py:261` | `get_hub_performance_report(hub_name, month, year)` | `frappe.get_all` | **none** | Every driver in a hub ranked by score, with commission, bonuses and net amount. A pay league table. |
| `vehicle_compliance.py:154` | `get_compliance_dashboard(hub_name)` | `frappe.get_all` | **none** | Licence and insurance expiry per driver and vehicle. Moderate on its own; useful to an attacker building a picture of a named person. |
| `vendor_order.py:81` | `change_order_status(order_name, new_status, reason)` | `db.set_value`, emails, Comment | **yes — explicit role check** (lines 84–90: HR Manager or System Manager) | Nothing extra. **This is the one endpoint in the controllers that gets it right**, and it shows the team knows how. |
| `vendor_order.py:152` | `assign_delivery(order_name, driver_id, vehicle_reg, eta_time)` | creates Delivery Assignment, `insert(ignore_permissions=True)`, flips the order to Dispatched | **none** | Any user can assign any driver to any order, dispatch it, and cause an email to the vendor naming the driver and vehicle. Sits directly next to `change_order_status`, which checks. |

### 3.3 · `api/vendor_portal_api.py` — 7 endpoints. **These are the good ones.**

Every one is `@requires_feature("vendor")`, resolves the vendor from the session
(`_get_vendor_id`, line 13) and, where it takes an order id, calls
`_assert_vendor_owns_order` (line 23).

`get_vendor_orders`, `get_order_detail`, `create_vendor_order`, `submit_order_rating`,
`get_delivery_tracking`, `get_vendor_dashboard`, `get_vendor_notifications`.

Two small things, both Minor:

- `_get_vendor_id` matches `Vendor User.frappe_user`; `portal_api.get_portal_context`
  and `auth._portal_home_for` match `Vendor User.email`. Two rules for "is this user a
  vendor" will drift.
- `get_vendor_notifications` (line 257) picks the *first* Vendor User for the vendor, not
  the caller, so one vendor colleague can read another's unread notifications.

**The real problem is that `vendor-portal.html` does not use this module at all.** Its
`api()` wrapper (line 870) hardcodes `"alvoraa_portal.portal_api." + method`. The safe
API exists, is tested by `tests/test_endpoint_entitlement.py`, and is wired only to the
unused Vue front end in `frontend/src/services/api.js`. The page people actually open
calls the unsafe twin.

### 3.4 · `api/auth.py` — 2 endpoints

| Line | Endpoint | Guest | Finding |
|---|---|---|---|
| 8 | `vendor_login(email, password, otp)` | **yes** | **The OTP is never verified.** Line 57 only asks whether `otp` is empty. Passing `otp=1` with a correct password completes the login. Two-factor authentication on the vendor portal does not exist, it only appears to. Also: five failed attempts lock the account permanently (lines 44–45) with no unlock path in code, so anyone who knows a vendor's email can lock them out from the internet. |
| 65 | `vendor_logout` | no | Fine. |

---

## 4 · Findings ranked, and the data behind each

Every scenario below is **one logged-in user of the tenant, with no special role, calling
the endpoint directly.** All of them are **within one tenant** — there is no cross-tenant
finding in this module, because each tenant is a separate site.

### Blockers

| # | Finding | File:line | Data exposed |
|---|---|---|---|
| B1 | **Any user reads any driver's full delivery list** | `portal_api.py:263` | Customer names, full delivery addresses, delivery GPS coordinates, order values. Personal data of the tenant's customers, plus the movement pattern of a named employee. |
| B2 | **Any user reads every vendor's order history, with the driver's mobile number** | `portal_api.py:65`, phone at `:97` | Order values and dates for every vendor; driver name, vehicle registration and **personal phone number**. |
| B3 | **Any user tracks a named driver live** | `portal_api.py:104` and `:370` | Latitude, longitude, speed, heading, timestamp, 20- to 200-point trails. Location of an identified worker, continuously. The fallback at `:153` leaks a live position even for an invented order id. |
| B4 | **Any user changes the delivery status of anyone's delivery** | `portal_api.py:290` | Not a data leak — an integrity and fairness failure. Marking Delivered writes `on_time_status`, which drives the scorecard, which drives `commission_earned`. Someone's pay moves. |
| B5 | **Any user files a performance rating against any driver** | `portal_api.py:318` | Ratings feed `Driver Rating Summary` and the monthly scorecard. One shot per order, no way to retract, no record of who filed it. This is a performance record about a person created by an unidentified party — exactly the thing a grievance turns on. |
| B6 | **Any user reads a named driver's pay** | `delivery_partner.py:46`, `scorecard.py:261` | `commission_earned`, `bonuses_earned`, `net_amount`, plus safety incidents and ratings. Compensation data is the most sensitive class in the product (compliance feature map F4). |
| B7 | **Any user overwrites a driver's monthly scorecard** | `scorecard.py:141` | Destroys the record that justifies a commission payment, with no version and no audit entry. Deleting decision-bearing data. |
| B8 | **The vendor portal's two-factor authentication does not verify the OTP** | `api/auth.py:57` | Any caller with a stolen password completes the login. The control exists in the UI only. |
| B9 | **Delivery OTPs are written to the error log in clear text** | `delivery_assignment.py:28-31` | `frappe.log_error(... "OTP: {otp}")` on every assignment. A secret in a log is a Blocker, not a Major, by our own rule. Compounded by `verify_delivery_otp` having no attempt limit (`:218`). |

### Majors

| # | Finding | File:line |
|---|---|---|
| M1 | Any user enumerates every vendor and every driver in the tenant | `portal_api.py:352`, `:361` |
| M2 | Any user can dispatch an order and assign a driver, triggering an email to the vendor | `vendor_order.py:152` |
| M3 | Any user can write fake GPS onto an assignment and trigger an "arriving soon" email to a vendor | `delivery_assignment.py:180` |
| M4 | `get_portal_context` returns `admin` to everyone who is not a vendor or driver | `portal_api.py:62` |
| M5 | Any user reads today's orders with `customer_phone`, twice over | `delivery_order.py:349`, `delivery_partner.py:157` |
| M6 | Any user reads a driver's rating history and complaint counts | `rating.py:131`, `delivery_feedback.py:166` |
| M7 | Any user reads licence and insurance expiry for every driver | `vehicle_compliance.py:154` |
| M8 | Any user rewrites the performance fields on a Delivery Partner record, unaudited | `delivery_partner.py:85` |
| M9 | Write endpoints protected only by "HR Manager can write Delivery Order" — no hub, company or ownership scoping | `delivery_order.py:218`, `:281`, `:334` |
| M10 | No refusal is logged anywhere in this module. `hrms/alvoraa_hr_core/access.py:log_refusal` exists and is unused here. We would not know this had happened. | whole module |
| M11 | No rate limit on any endpoint, including `verify_delivery_otp` and `vendor_login` | whole module |
| M12 | An unauthenticated caller can permanently lock a vendor account by failing login five times | `api/auth.py:42-46` |

### Minors

- The safe vendor API is unused by the page that needs it (`vendor-portal.html:870`).
- Two different rules for "is this user a vendor" (`email` vs `frappe_user`).
- `get_vendor_notifications` returns the first Vendor User's notifications, not the caller's.
- `portal_api.py:7-8` hardcodes a warehouse name and phone number; `vendor_order.py:107`
  and `:218` hardcode `ops@gracedrinks.in`. Customer-specific data in shared code.
- `VENDOR_COORDS` (`portal_api.py:21`) hardcodes five named businesses and their
  coordinates in a public repository.

### Worries, not findings

Things I could not turn into "this actor, in this state, sees this data", kept separate
on purpose:

- **Vehicle Tracking records `harsh_braking`, `harsh_acceleration`, `sharp_turn`,
  `speeding_alert`, `idle_duration` and `battery_level`, and `delivery_partner.py:133`
  feeds them into `safety_incidents` on the employee record, which the scorecard scores.**
  That is passive behavioural monitoring used as a performance input, which
  `product-context.md` §6.4 (FR-H7) says we deliberately do not do. I cannot call it a
  security finding. It is a product-policy conflict that needs a decision, and if this
  module ships to a live tenant it needs a DPIA before it does.
- `Delivery Partner` stores **PAN and Aadhaar** (fields 41–42). No endpoint I found
  returns them. But the doctype has no field sensitivity class, no masking and no reveal
  log, so any future endpoint or export will inherit the loosest treatment. This is the
  A1 gap from the compliance feature map, showing up in a corner nobody is watching.
- `hooks.py` registers no `permission_query_conditions` or `has_permission` for any
  delivery or vendor doctype. Row-level security for this module does not exist at the
  framework level, only in whatever each endpoint does for itself.

---

## 5 · Who is affected today

**Most likely nobody.** Three things support that, and one qualifies it.

1. **No onboarded customer.** Per the note of 17 September 2026, no client is live and
   PPJ is a demo. No real vendor, driver or customer data is at risk right now, and no
   reporting duty is engaged.
2. **This module is sold, not default-on for new tenants.** `vendor` is a feature in
   `subscription.py:151`, included only in `_ENTERPRISE` (`:234`). A starter or business
   tenant is not entitled to it.
3. **But entitlement does not protect these endpoints, because they are not gated.**
   `@requires_feature("vendor")` is applied to all seven endpoints in
   `api/vendor_portal_api.py` and both in `api/auth.py`. **It is applied to none of the
   11 endpoints in `portal_api.py` and none of the 17 in `controllers/`.** So plan gating
   is irrelevant to every finding above: a starter-plan tenant's employee can call
   `get_drivers_performance` today. The panel is hidden; the door still opens. That is
   the exact mistake `requires_feature`'s own docstring (`subscription.py:630`) was
   written to stop — the fix was applied to one file and not the others.
4. **The fallback grants `vendor` to old tenants.** `enabled_features` (`:494`) falls
   back to "everything except opt-in" when a site has no `features` key, and `vendor` is
   not marked `opt_in`. `provision_tenant.sh` sets `subscription_plan` but never sets
   `features` (line 110; the comment at 122 says `tenant_api` writes it later). So any
   site provisioned by the script and never touched by the admin console has `vendor`
   enabled by plan — and if the plan key were also missing, by the fallback.
5. **The app is always installed.** `alvoraa_portal` is installed on every tenant
   (`provision_tenant.sh:86`), so the doctypes and the routes `/vendor-portal` and
   `/driver-portal` exist on every site whatever the plan.

**What I could not verify without the bench, and would need to:**

- Which live sites exist, and what each one's `features` and `subscription_plan` keys
  actually say. `site_config.json` is not in the repository.
- Whether any tenant has real `Vendor`, `Delivery Partner` or `Delivery Order` rows, or
  whether they are all demo records.
- Whether `frappe.get_all` ignores permissions in the installed Frappe version (§2).
- Whether any Module Profile blocks the Alvoraa Portal module for a tenant — and it would
  not help anyway, since module profiles gate the desk, not whitelisted endpoints.
- Whether the `/vendor-portal` and `/driver-portal` routes are reachable on the live
  dev and demo sites. I did not probe them, and will not.

---

## 6 · The shape of the fix

### 6.1 · One helper, not twenty-three checks

Mirror `hrms/alvoraa_hr_core/access.py` — same file, same style, same refusal logger.
Add a portal-side module, `alvoraa_portal/access.py`, with a small, boring surface:

```
who_am_i()                     -> ("vendor", id) | ("driver", id) | ("operator", None) | None
require_vendor()               -> vendor id, or PermissionError
require_driver()               -> partner id, or PermissionError
require_operator()             -> or PermissionError   (an explicit role list, not "everyone else")
assert_vendor_owns_order(...)  -> or PermissionError
assert_driver_owns_delivery(...) -> or PermissionError
assert_driver_is_self(...)     -> or PermissionError
```

Four rules that make it work rather than decorate:

1. **One identity rule.** `who_am_i` is the only place that decides who a caller is, and
   both `Vendor User` matches (`email` and `frappe_user`) collapse into it.
2. **"Operator" is a role, never a default.** Today anyone who is not a vendor or a
   driver is an admin. Replace that with an explicit list — Logistics Manager, HR
   Manager, System Manager — and deny everyone else. This one change closes about half
   the findings on its own.
3. **Every refusal is identical and logged.** Same message whether the record does not
   exist, has no owner, or belongs to someone else — the slice 014 pattern
   (`portal_api.py:232-240`), so the answer does not reveal which records exist. Every
   refusal goes through `access.log_refusal` with a rule number, so M10 closes with the
   same edit.
4. **Fail closed.** No owner recorded, no identity resolved, unknown state → deny.

### 6.2 · Per-endpoint rules

| Endpoint group | Rule |
|---|---|
| `get_driver_deliveries`, `get_partner_today_orders`, `get_today_orders_for_partner`, `get_delivery_route`, `driver_advance_status`, `update_driver_location`, `mark_proof_of_delivery` | The caller is that driver, **or** an operator. A driver may never pass another driver's id — ignore the argument entirely for a driver caller and use their own. |
| `get_vendor_orders`, `get_order_live_location`, `submit_order_rating`, `get_delivery_tracking` | The caller is that vendor, or an operator. `submit_order_rating` additionally: the order is Delivered, not yet rated, and belongs to the caller's vendor. Record **who rated** on the Order Rating row — it does not today. |
| `get_all_vendors`, `get_all_partners`, `get_drivers_performance`, `get_hub_performance_report`, `get_compliance_dashboard`, `get_hub_live_summary`, `get_partner_performance_summary`, `get_driver_ratings`, `get_partner_feedback_summary` | Operator only. Scope to the operator's own hub or company where the data has one. |
| `generate_scorecard_for_partner`, `update_partner_stats_from_orders`, `assign_delivery`, `assign_partner_to_order`, `update_delivery_status` | Operator only, plus an audit entry naming the caller. Scorecard regeneration must keep the superseded version, not overwrite it. |
| `verify_delivery_otp`, `update_gps_location` | The assigned driver only. Plus §6.4. |
| `get_portal_context` | Return `operator` only for a real operator role; everyone else gets a refusal, and the page shows "no portal access". |

### 6.3 · What may keep `ignore_permissions`, and what may not

Keep it **only where the caller has already been proved to own the record**, and say so
in a comment on the same line — the pattern `update_driver_location` now uses. That is:
the Vehicle Tracking insert, the Order Rating insert, the Delivery Order status write,
the Delivery Tracking append.

**Remove it entirely from the read paths.** `get_all` with `ignore_permissions=True` on
`Vendor`, `Delivery Partner`, `Vendor Order` and `Delivery Order` has no defensible use
once the caller is scoped: filter by the caller's own vendor or partner id and the flag
is unnecessary. Every remaining use gets a one-line justification, and the count goes
into the `ignore_permissions` counter gate (§6.6).

### 6.4 · Guest endpoints and rate limits

- **Guest surface is small and should stay that way.** Only `vendor_login` is guest-
  accessible in this area. Fix the OTP check (verify it, or delete the flag and stop
  claiming 2FA — an unverified factor is worse than an absent one, because people rely
  on it). Replace the permanent account lock with a time-boxed lockout and rate-limit by
  IP as well as by account, so M12 stops being a denial-of-service lever.
- **`verify_delivery_otp`:** attempt counter on the assignment, lockout after five, and
  `frappe.rate_limit` on the endpoint. Stop logging the OTP (B9) — log that an OTP was
  issued, never its value.
- **Rate limits generally:** `frappe.rate_limit` on the location-write and OTP endpoints
  first. A driver's phone posts a position every few seconds; pick the ceiling from real
  traffic, not from a guess.

### 6.5 · Order of work

Each step is independently shippable and leaves the module safer than it was.

| Step | Work | Rough size |
|---|---|---|
| **0** | Confirm the `frappe.get_all` behaviour on the bench (§2) and list the live sites with `vendor` enabled. **Everything else is scoped by this answer.** | half a day |
| **1** | **Gate the whole module by plan.** Add `@requires_feature("vendor")` to all 28 ungated endpoints, and mark `vendor` as `opt_in` in `subscription.py` so no tenant gets it by fallback. This is one mechanical change that switches the module off for every tenant that has not bought it — which may be all of them — and it buys the time to do steps 2–5 properly. | half a day |
| **2** | Build `alvoraa_portal/access.py` with the six helpers and the refusal log, plus its own tests. No endpoints changed yet. | 1 day |
| **3** | Apply it to the 11 `portal_api.py` endpoints — the ones the live pages actually call, and where B1–B5 live. | 1–1.5 days |
| **4** | Apply it to the 17 controller endpoints, including the scorecard and pay exposures (B6, B7) and the OTP path (B9). | 1.5–2 days |
| **5** | Auth fixes: verify the OTP, time-box the lockout, rate limits (B8, M11, M12). | 1 day |
| **6** | Point `vendor-portal.html` at `api/vendor_portal_api.py` and delete the duplicate `portal_api` reads, so there is one vendor API rather than two. | 1 day |
| **7** | CI gates: the `ignore_permissions` counter, and a portal permission suite that runs as a real non-privileged user. | 1 day |

**Total roughly 7–9 engineer-days**, plus review. Step 1 alone, at half a day, removes
most of the practical risk and can ship on its own.

### 6.6 · The gates that stop this coming back

- **`ignore_permissions` counter that can only go down.** 491 uses in `alvoraa_portal`
  today, 15 of them in the files in this slice. There is no such gate in
  `.github/workflows/ci.yml`.
- **A permission suite that runs as a real user.** The existing portal tests are good,
  but nothing probes this module.
- **Fix the semgrep step.** The CI step is called "Semgrep (Frappe security rules)"
  (`ci.yml:136`) but points at `hrms/semgrep`, which contains one file,
  `test-correctness.yml`, with three rules about `frappe.db.commit()` in tests. It is
  also `continue-on-error: true`. It is not a security gate and its name says it is.
  Either add real rules — `ignore_permissions` on a whitelisted read, `get_all` on a
  person-bearing doctype in a whitelisted function — and make it blocking, or rename it.

---

## 7 · What to check before any of it ships

### Pin tests — one per endpoint, and the refusal is the test

Every endpoint gets at least two: the owner succeeds, a stranger is refused with
`PermissionError` **and nothing is written or returned**. Follow
`tests/test_driver_location_014.py`, which already does this well.

| Test | Asserts |
|---|---|
| `test_driver_sees_only_own_deliveries` | Driver B calling `get_driver_deliveries(partner_A)` raises, and returns no rows. |
| `test_vendor_sees_only_own_orders` | Vendor B calling `get_vendor_orders(vendor_A)` raises. |
| `test_plain_employee_is_not_an_operator` | A user with no vendor, driver or operator role gets a refusal from `get_portal_context`, `get_all_vendors`, `get_all_partners`, `get_drivers_performance`. |
| `test_status_cannot_be_advanced_by_a_stranger` | `driver_advance_status` on someone else's order raises and the status is unchanged. |
| `test_rating_only_by_the_vendor_on_the_order` | Stranger raises; the vendor succeeds; the row records who rated. |
| `test_location_endpoints_refuse_a_stranger` | `get_order_live_location`, `get_delivery_route`, `update_gps_location` all raise. |
| `test_live_location_has_no_fallback_leak` | `get_order_live_location` with an unknown order id returns nothing and never another partner's position. |
| `test_pay_fields_need_an_operator` | `get_partner_performance_summary` and `get_hub_performance_report` refuse a non-operator. |
| `test_scorecard_regeneration_is_operator_only_and_keeps_history` | Stranger raises; an operator's regeneration leaves the previous record retrievable. |
| `test_otp_is_rate_limited_and_never_logged` | Six wrong guesses lock; the Error Log contains no six-digit OTP. |
| `test_vendor_login_requires_a_correct_otp` | Correct password plus wrong OTP fails. |
| `test_every_portal_endpoint_is_feature_gated` | Walk `portal_api` and `controllers` with `inspect`, assert every `@frappe.whitelist` function carries `__alvoraa_feature__`. This one test stops the next endpoint being forgotten. |
| `test_refusals_are_logged` | Each refusal writes one security line with the rule number, and no field values. |

### What a human must check by eye

A test cannot see these:

1. **Open the driver portal as a plain employee** on the local bench. The admin bar with
   the driver picker must not appear, and the page must say plainly why.
2. **Open the vendor portal as vendor A** and confirm vendor B's orders are not reachable
   — including by editing the request in the browser console, not just by clicking.
3. **Read the error log after creating a delivery assignment.** No OTP, no phone number,
   no address.
4. **Read one outbound email of each kind.** Confirm the recipient is entitled to the
   customer name, address and driver phone number in it.
5. **Confirm the driver portal still works end to end** after the change. A permission
   fix that breaks the driver's own flow gets reverted in a week, and then we are back
   here.
6. **Decide, with eyes open, whether the behavioural telemetry keeps feeding the
   scorecard** (§4, worries). That is a product call, not a code review.

---

## 8 · Open questions for Surbhi

Each has a recommended default, so a "yes, do that" is enough to unblock.

| # | Question | What it blocks | Recommended default |
|---|---|---|---|
| Q1 | **Do we still want this module at all?** It predates the HR product, it carries one customer's warehouse name, phone number and five named shops in the code, and it is not mentioned anywhere in the product positioning. | Everything. If the answer is no, steps 2–7 are wasted work. | **Switch it off first, decide second.** Do step 1 (half a day), then take the decision without a clock running. |
| Q2 | **May I switch it off for every tenant that does not use it, immediately?** Marking `vendor` as `opt_in` plus gating the 28 endpoints. | Step 1. | **Yes.** It is the cheapest large risk reduction available and it is reversible with one tick in the admin console. |
| Q3 | **Is any tenant actually using the vendor or driver portal today?** I could not check site configs or data without the bench. | How urgent steps 3–5 are. | Assume yes until checked. If no tenant uses it, this becomes a tidy-up rather than a fix. |
| Q4 | **Who counts as an "operator"?** Today it is "everyone who is not a vendor or a driver". I propose Logistics Manager, HR Manager, System Manager. | Step 2. | That list, with Logistics Manager as the intended one and the other two as fallbacks. |
| Q5 | **Should the vendor portal keep two-factor authentication?** Right now it claims it and does not do it. | Step 5. | **Turn the claim off** unless someone will build real OTP delivery. A factor that is advertised and not enforced is worse than none. |
| Q6 | **Does driver behavioural telemetry keep feeding the performance scorecard?** Harsh braking, speeding and idle time currently become `safety_incidents` and then a score. This contradicts FR-H7. | The DPIA, and whether this module can ship to a live tenant. | **Stop scoring it.** Keep the raw safety data for safety purposes with a purpose tag; do not let it into a performance rating. |
| Q7 | **Do the hardcoded values go?** `Grace Warehouse`, `98761-00099`, `ops@gracedrinks.in`, five named shops with coordinates, in a public repository. | Nothing — but it is a five-minute fix and an embarrassment in a security review. | Move to site config in the same slice. |
| Q8 | **Not a lawyer, so this one is for counsel if a customer goes live:** continuous GPS tracking of named employees, retained indefinitely, is a notice-and-purpose question under DPDP. The question that needs answering is: *on what basis do we process a driver's continuous location, for how long do we keep it, and what does the driver have to be told before we start?* | Whether this module can ship to a live tenant at all. | Ask it before the first customer, not after. There is no retention policy on `Vehicle Tracking` today. |

---

## 9 · Residual risk after the recommended work

| Risk | Remains because | Who accepts it | Date |
|---|---|---|---|
| A tenant with the vendor feature on still trusts operators completely — no hub or company scoping inside an operator role | Out of scope for a permission fix; needs a row-scope design | *unassigned* | *undecided* |
| Driver GPS history has no retention limit or purge | No retention engine exists for this module (compliance feature map A6, status unknown) | *unassigned* | *undecided* |
| PAN and Aadhaar on `Delivery Partner` have no sensitivity class, no masking, no reveal log | Depends on A1 field sensitivity classification, not yet built | *unassigned* | *undecided* |
| No detection: even after the fix, an attempt to reach someone else's data is refused but nothing alerts | The refusal log is a file, not a monitor | *unassigned* | *undecided* |

**An accepted risk with a name and a date is governance. These four have neither yet.**
They need an owner before this slice closes.

---

## Verification record

| Item | Source | Date checked |
|---|---|---|
| Endpoint inventory, ownership checks, `ignore_permissions` uses | The code, branch `dev`, commit `b7244c8` | 18 Sep 2026 |
| Doctype permission rules (System Manager + HR Manager only, no row scope) | The eight doctype JSON files | 18 Sep 2026 |
| Plan gating and the `features` fallback | `subscription.py`, `deploy/provision_tenant.sh` | 18 Sep 2026 |
| Tenant = separate site | `deploy/provision_tenant.sh:69` | 18 Sep 2026 |
| No onboarded customer; PPJ is a demo | Recorded decision of 17 Sep 2026 | 18 Sep 2026 |
| CI gates present | `.github/workflows/ci.yml`, `hrms/semgrep/` | 18 Sep 2026 |
| DPDP / CERT-In obligations cited | `.claude/context/security-compliance-baseline.md` (verified 24 Aug and 6 Sep 2026 — within 90 days, not stale) | 18 Sep 2026 |
| **`frappe.get_all` ignores permissions** | **Not verified in this repo — framework source absent. Must be confirmed on the bench.** | — |

**I am not a lawyer.** Q8 is a question for counsel, not an answer.

---

## Who may see a driver's location (Surbhi, 2026-09-18)

**Decision:** a driver's location and route must **not** be visible to any logged-in colleague. Limit it to:

- **the driver themselves** (their own route and trips);
- **their manager** (the reporting line above them, as elsewhere in the product);
- **HR** (HR User / HR Manager, scoped to the companies they look after);
- **company leadership** (the Leadership role from slice 012 / System Manager treated as CXO for now).

This applies to every read path, not just the obvious one: `portal_api.get_delivery_route`, `get_order_live_location` (including its demo fallback that returns the most recent driver's name and position for an invented order id), the driver performance screens, and any realtime broadcast.

**To settle while building (recommended answers):**
- **A dispatcher / logistics operator** who is not the driver's line manager: allow only if the organisation names a Logistics Manager role, not "anyone who is not a driver or vendor" as today.
- **The customer** tracking their own delivery: only through a per-order link or token that shows the vehicle position for that order, never a named driver or their history.
- **The vendor** whose order it is: same as the customer — that order only, no driver identity beyond a first name if needed.

This is **phase 2** of slice 016 (the shared ownership/role helper). Phase 1 gated the whole module by plan and it is now off on both dev sites, so nothing is reachable today.
