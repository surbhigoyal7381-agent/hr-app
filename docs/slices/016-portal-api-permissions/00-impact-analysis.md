# Slice 016 — impact analysis and strategy (phase 1 only)

Engineer. 18 September 2026. Written against local `dev` `b7244c8`.
Reads `00-security-analysis.md` (security engineer, same day).

Phase 1 scope approved by Surbhi on 18 September 2026, three items only:

1. Gate the whole vendor / driver / delivery module by plan.
2. Remove the hardcoded customer details from that module.
3. Stop driver telemetry feeding a performance score.

Everything else in the analysis — the shared ownership helper, per-endpoint
ownership rules, the 2FA/OTP fixes, the duplicate vendor-portal page, CI gates —
is phase 2 and is not started here.

---

## 1 · What I checked before opening a file

`git fetch origin` brought in nothing. `origin/dev` is at `9138251`; local `dev`
is `b7244c8`, **12 commits ahead** — all of slice 014, none of them mine.

Other sessions' uncommitted work in the main checkout (I touched none of it):
`.claude/context/ux-learnings.md`, `backlog/KPI_AUTOMATION_BACKLOG.md`,
`docs/slices/009-ess-portal-redesign/00-assessment-and-plan.md`,
`hrms/.../alvoraa_position.py`, a deleted `OBJECTIVES_KPI_REQUIREMENTS.md`, and a
pile of untracked PDFs and drafts.

Work board rows in flight that matter to me: `slice/015-repo-hygiene` (11 commits,
demo passwords, `.gitignore`, one `ci.yml` lint step), `slice/013-mobile-app`
(`mobile/`, a `key-guard` job in `ci.yml`), `slice/ci-fix-9138251` (test-site
limits in `ci.yml`). **None of them touch any file in this slice.**

Bench: `hrlocal-bench` up, `pgrep -af run-tests` empty, board shows no session
holding the bench.

---

## 2 · Parallel-work check

| File I will change | Hot file? | Who else is in it | Plan |
|---|---|---|---|
| `alvoraa_portal/alvoraa_portal/portal_api.py` | no, but slice 014 changed it last week (`update_driver_location`) | nobody now — 014 is finished and in local `dev` | I build on 014's commit. I do not touch its `update_driver_location` body, only add the decorator line above it. |
| `alvoraa_portal/alvoraa_portal/controllers/*.py` (9 files) | no | nobody | — |
| `alvoraa_portal/alvoraa_portal/subscription.py` | **yes** (hot-file list) | nobody today | One key added to the existing `vendor` spec. No signature changes, no new function. |
| `alvoraa_portal/alvoraa_portal/tests/test_subscription_access.py` | shared fixture | nobody | One entry removed from the `PLAN_MATRIX` expectation, because the plan matrix itself changes. |
| New `alvoraa_portal/alvoraa_portal/tests/test_portal_module_gate_016.py` | new | — | — |
| `docs/slices/016-portal-api-permissions/*` | new | — | — |

**Not touching:** `hooks.py`, `patches.txt`, any DocType JSON, `hrms-employee.html`,
`ci.yml`, `mobile/`, `demo/`, `deploy/`.

Pin tests for the three things I change are listed in §7.

---

## 3 · Functional impact

### Cross-module reach

- `alvoraa_goals`, `alvox_compensation`, `hrms`, `erpnext`: **no reach.** Grep for
  `portal_api` and `alvoraa_portal.controllers` outside `alvoraa_portal` returns
  nothing. This module is self-contained.
- Inside `alvoraa_portal`: the callers of the 28 endpoints are the two portal
  pages, `www/vendor-portal.html` and `www/driver-portal.html`, plus
  `hooks.py` `doc_events` and two scheduler jobs. The scheduler jobs call
  `scorecard.generate_monthly_scorecards` and
  `scheduled_jobs.update_delivery_tracking` — **server-side, not through the
  whitelist**, so the plan gate does not touch them.

### Callers of every function whose behaviour changes

| Function | Callers found | Effect of my change |
|---|---|---|
| all 28 whitelisted endpoints | the two portal pages, by name | refused when the tenant has no `vendor` feature |
| `scorecard._calculate_composite_score` | `before_save` hook on Delivery Performance Scorecard | unchanged code; its `safety_incidents` input stops being written from GPS |
| `scorecard.generate_scorecard_for_partner` | monthly scheduler + the whitelisted endpoint | stops writing three telemetry fields |
| `delivery_partner.update_partner_stats_from_orders` | the whitelisted endpoint only | stops writing `safety_incidents` |
| `portal_api.WAREHOUSE_NAME/PHONE`, `VENDOR_COORDS` | `get_vendor_orders`, `get_order_live_location`; read by `vendor-portal.html` lines 1068–1070 and 1215 | values now come from site config, with neutral fallbacks the page already handles |

### Persona impact

| Persona | Before | After |
|---|---|---|
| **CXO** | Could call every delivery endpoint on any tenant, whatever the plan | On a tenant with `vendor` switched on: no change. On every other tenant: the endpoints refuse. The desk and the HR product are untouched. |
| **HR Manager** | Same | Same |
| **Employee (incl. a vendor or a driver)** | Any logged-in user could call all 28 | On a tenant without `vendor`: all 28 refuse. On a tenant with it: unchanged — **phase 1 does not add ownership checks**, so an ordinary employee on an entitled tenant can still call them. That is the whole point of phase 2, and it must be said plainly rather than implied away. |

### HRMS domain impact

None. Leaves, attendance, payroll, appraisals and org structure do not read or
write anything in this module. The only performance object involved is
`Delivery Performance Scorecard`, which is the delivery module's own and is not
linked to Frappe HR's Appraisal.

---

## 4 · The three changes, and the mechanism for each

### 4.1 Plan gate (item 1)

**Mechanism: reuse the existing decorator.** `subscription.requires_feature`
already exists, is tested, and is applied the same way in
`api/vendor_portal_api.py` and `api/auth.py`. Nothing new is built.

- Add `@requires_feature("vendor")` under `@frappe.whitelist()` on all 11
  `portal_api.py` endpoints and all 17 `controllers/*.py` endpoints. Decorator
  order copied exactly from `vendor_portal_api.py`, so the gate runs before the
  body and Frappe's whitelist registry sees the gated function.
- Mark `vendor` as `"opt_in": True` in `subscription.FEATURES`.

**Why `opt_in` matters, and the consequence nobody has asked about yet.**
`enabled_features()` falls back to "everything that is not opt-in" for a site
with no `features` key, and `plan_features()` excludes opt-in keys from a plan
bundle. `deploy/provision_tenant.sh` sets `subscription_plan` but never sets
`features`. So today every provisioned tenant has `vendor` on by fallback.
Marking it opt-in flips that: **a tenant only has the module if its
`site_config.json` names `vendor` explicitly.** That is the desired end state,
and it is exactly one tick in the admin console to grant.

It also means the local demo sites lose it unless their config names it. I will
check `hrms.localhost` and `ppj.localhost` before I claim the demo still works,
and if a demo site needs the tick, that is a site-config change and therefore
Surbhi's call, not mine.

One existing test encodes the old plan matrix:
`test_subscription_access.PLAN_MATRIX["enterprise"]["features"]` lists `vendor`.
`plan_features("enterprise")` will no longer return it, so that entry comes out.
`test_subscription.test_enterprise_has_everything_we_sell` compares against
`DEFAULT_ON`, which is derived, so it stays green by itself.

### 4.2 Hardcoded customer details (item 2)

**Mechanism: configure, not build.** Site config keys with neutral fallbacks —
no new DocType, no new custom field, no schema change.

What is actually in the code (I grepped wider than the analysis did, and found
more):

| Value | Where | Sensitivity |
|---|---|---|
| `"Grace Warehouse"` | `portal_api.py:7` | customer name |
| `"98761-00099"` | `portal_api.py:8` | a phone number — masked here as `987…099` |
| five named shops + coordinates | `portal_api.py:21-27` | five real businesses and where they are |
| `ops@gracedrinks.in` | `delivery_feedback.py:116`, `:144`, `rating.py:49`, `vehicle_compliance.py:123`, `vendor_order.py:107`, `:218` — **six places, five files** | a customer's internal mailbox, used as the *fallback recipient* for alert emails |
| `"GraceVendorPortal/1.0 (ops@gracedrinks.in)"` | `delivery_order.py:45` | the same address, sent as an HTTP `User-Agent` to an outside geocoding service |
| default customer point `(30.7333, 76.7794)` | `portal_api.py:125` | a Chandigarh coordinate; not identifying, but it is the same hardcoding habit |

The email one is the serious one, and it is worse than "an embarrassment in a
review": on any other tenant, a delivery complaint or a compliance alert —
carrying a customer name and address — is **emailed to a third party's mailbox.**

Plan:

- `_setting(key, default)` helper in `portal_api.py`, reading `frappe.conf`.
  `warehouse_name` defaults to the translated word "Warehouse"; `warehouse_phone`
  defaults to empty, and `vendor-portal.html:1068` already tests it for truth
  before showing a Call button, so an empty value degrades to the existing
  no-phone path rather than breaking.
- `VENDOR_COORDS` deleted. Coordinates now come from an optional site-config map
  `portal_vendor_coords` (empty by default), falling back to the hub point, which
  itself becomes configurable. `vendor-portal.html:1215` already handles a null
  customer position.
- One `_ops_recipients()` helper in a new tiny module shared by the five
  controllers, reading `portal_ops_email` from site config. **When nothing is
  configured, the email is not sent** and a line goes to the error log naming the
  document. Failing closed is the only defensible answer: the alternative is
  posting a customer's address to a stranger. This is a behaviour change a tenant
  can notice, and it is stated in §6.
- `User-Agent` becomes `AlvoraaPortal/1.0`.

### 4.3 Stop telemetry scoring (item 3)

**Mechanism: delete the derivation, keep the field and the raw rows.**

Exactly two places turn driving telemetry into a performance number:

1. `delivery_partner.update_partner_stats_from_orders`, lines 132–139 and 148:
   `SUM(harsh_braking) + SUM(speeding_alert)` → `safety_incidents` on the
   **Delivery Partner** record.
2. `scorecard.generate_scorecard_for_partner`, lines 215–233: a GPS aggregate →
   `harsh_driving_detected`, `speeding_incidents` and `safety_incidents` on the
   **Delivery Performance Scorecard**, which `_calculate_composite_score` then
   turns into `safety_score`, `overall_delivery_score`, `performance_level`, and
   through `_set_compensation_recommendations` into `recommended_increment`,
   `promotion_eligible` and an automatic written warning.

Both derivations go. What stays:

- The raw `Vehicle Tracking` rows, including `speeding_alert`, which
  `update_driver_location` still sets. Retention is a separate question for
  counsel (analysis Q8) and is not touched here.
- The `safety_incidents` field itself, on both doctypes, and its place in the
  score. A human who records a real safety incident is making a human judgement,
  not passive monitoring, and FR-H7 is about the passive kind. With the telemetry
  feed gone the field is only ever set by a person — which is the rule we wanted.

**The consequence, stated up front:** with no telemetry feeding it,
`safety_incidents` is 0 for everyone who has not had one recorded by hand, so
`safety_score` is full marks and **every affected driver's overall score goes up
at the next scorecard run.** Scores are not recomputed retrospectively — existing
scorecard rows keep the numbers they were saved with, because silently rewriting
a record that justified a commission payment would be worse than leaving it. If
Surbhi wants the history corrected, that is a patch and a separate decision.

---

## 5 · Non-functional verdict

| Dimension | Verdict | Why |
|---|---|---|
| **Performance** | **improves, slightly** | The gate is one dict lookup on `frappe.conf` and short-circuits before the body — so on a tenant without the feature, 28 endpoints that ran unbounded `get_all` and raw SQL now do nothing. Query count per call on an entitled tenant is unchanged. Two SQL aggregates over `tabVehicle Tracking` (the biggest-growing table here) are deleted from the scorecard path, so the monthly job gets cheaper. |
| **Scalability** | **improves** | Same reason: the deleted aggregates scanned every tracking row per partner per month. Nothing new grows with headcount. |
| **Security / permissions** | **improves** | 28 endpoints gain a server-side refusal they did not have. It is an **entitlement** gate, not an ownership gate — on an entitled tenant the 23 ownership holes are all still open. Phase 2 closes those. I would rather say that than let a gate look like a fix. |
| **Privacy** | **improves** | Removes a named third party's mailbox from six outbound-email paths and from an outbound HTTP header. Removes five named businesses and a phone number from a public repository. Stops passive driving behaviour becoming a performance record about a person, which is the FR-H7 line and a DPDP purpose-limitation problem. |
| **Reliability** | **neutral, with one watch point** | The decorator adds no failure mode the existing gated endpoints do not already have. The watch point is the ops-email fallback: a tenant that never configures `portal_ops_email` stops receiving those alerts. That is deliberate and logged, not silent. |
| **Observability** | **improves, slightly** | A suppressed alert email writes an error-log line naming the document (no personal content). No refusal logging is added — that is phase 2 (M10), and I am not pretending otherwise. |
| **Accessibility** | **neutral** | No UI change. The refusal surfaces through the pages' existing error path. A tenant without the feature sees an error message rather than a clean "not in your plan" panel; that is worth fixing in phase 2 and is not a regression, because before there was no refusal at all. |
| **Upgrade-safety** | **neutral / safe** | Everything is in our own app. No upstream file, no fixture, no patch, no migration. |
| **Internationalisation** | **improves, slightly** | The refusal message is already translated by the decorator. The new "Warehouse" fallback is wrapped for translation. |
| **Maintainability** | **improves** | One decorator per endpoint, one helper for site settings, one helper for alert recipients — six copies of a literal email address become one lookup. |
| **Data integrity** | **improves** | Telemetry no longer rewrites a person's performance fields behind their back. Existing scorecards are left exactly as saved. |

### Compliance obligations discharged

| Obligation | Mechanism in this slice |
|---|---|
| Purpose limitation | Driving telemetry is no longer read for a performance purpose. The read is deleted, not warned about. |
| Minimisation | Third-party mailbox, customer warehouse name and phone, and five named businesses removed from shipped code. |
| Automated decisions | A scorecard number, an increment recommendation and an automatic written warning can no longer be produced from passive telemetry. |
| Access rights | Server-side entitlement check on all four entry points for 28 endpoints. |

Not discharged in phase 1, and I want it on the record: **auditability** (no
refusal log yet, M10), **breach readiness** (no affected-record query for this
module), and the row-level access rights that phase 2 carries.

---

## 6 · What a tenant would notice

| Who | What changes |
|---|---|
| A tenant that does not have `vendor` in `site_config.json` | `/vendor-portal` and `/driver-portal` still open, and then every action fails with "Vendor & Driver Portal is not included in your plan." Today those tenants can use the whole module. **This includes tenants that were only ever entitled by the fallback**, so the tick in the admin console becomes required. |
| A tenant that does have it | Vendor and driver flows unchanged. The Call button on an order shows the configured warehouse name and number, or no Call button if none is configured. Map pins for vendors fall back to the hub unless coordinates are configured. |
| Anyone relying on the ops alert emails | Delivery complaints, low ratings, compliance expiry and order-status alerts go to the address in `portal_ops_email`. If that is not set, they are not sent, and the error log says so. |
| Delivery managers reading scorecards | "Harsh driving detected" and "Speeding incidents" stop filling in. Safety incidents only appear if a person records one. Next month's overall scores will be higher than last month's for drivers who previously lost safety points. Existing scorecards keep their old numbers. |

---

## 7 · Pin tests

New file `tests/test_portal_module_gate_016.py`:

1. **`test_every_portal_endpoint_is_feature_gated`** — walks `portal_api` and all
   nine `controllers/*` modules with `ast`, asserts every `@frappe.whitelist`
   function carries `requires_feature("vendor")`, and asserts it found at least
   28. This is the test that stops the next endpoint being forgotten.
2. **`test_a_tenant_without_the_feature_is_refused`** — table-driven over all 28,
   the shape of `test_endpoint_entitlement.TestVendorIsDenied.test_starter_cannot_call_them`.
3. **`test_vendor_is_opt_in`** and **`test_a_site_with_no_features_key_does_not_get_vendor`**.
4. **`test_no_customer_details_are_hardcoded`** — greps the module's source for
   the warehouse name, the phone number, the five shop names and the
   `gracedrinks.in` domain, and fails if any comes back.
5. **`test_telemetry_does_not_create_safety_incidents`** — insert Vehicle Tracking
   rows with `harsh_braking` and `speeding_alert` set, run both derivations, and
   assert `safety_incidents` on the partner and on the scorecard stays 0, and that
   the scorecard's `harsh_driving_detected` and `speeding_incidents` stay 0.
6. **`test_the_raw_tracking_rows_are_kept`** — the same rows are still readable
   afterwards, so "we stopped scoring it" is not quietly "we stopped storing it".

Existing suites to re-run: `test_endpoint_entitlement`, `test_subscription`,
`test_subscription_access`, `test_opt_in_features`, `test_subscription_record`,
`test_driver_location_014`, `test_portal_security_010`, then the whole
`alvoraa_portal` app.

---

## 8 · Risks, and the two things I want said out loud

1. **A plan gate is not a permission fix.** After this slice, on an entitled
   tenant, every one of the 23 ownership holes in the analysis is still open. The
   value of phase 1 is that it takes the module away from every tenant that did
   not buy it. If the answer to the analysis's Q1 is "we do not want this module
   at all", phase 2 never needs to happen.
2. **Testing this needs the bench, and the bench runs local `dev`.** The release
   train note on the work board says no new slice commits go into local `dev`
   until the pending release is pushed — but slice 014 has already gone in, which
   is why local `dev` is 12 ahead. To run the tests I have to bring 016 in the
   same way, and then **a push of local `dev` would carry slice 016 as well as
   slice 014.** Surbhi should know that before she says "push". I will not push.

## 9 · Recommendation

Do all three, in the order above, on the local instance only. They are
independent: the gate is mechanical, the hardcoded values are a tidy-up with one
real privacy fix inside it, and the telemetry change is a product decision that
is already made (Q6, "stop scoring it").

The one thing I would add to the approved scope, and am **not** doing without a
word: nothing in phase 1 makes the two portal pages show a clean "not in your
plan" message. On an unentitled tenant they will show raw errors. It is not a
regression, but it is scruffy.
