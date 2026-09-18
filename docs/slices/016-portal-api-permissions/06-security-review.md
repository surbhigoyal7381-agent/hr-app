# Slice 016 — security and privacy review

**18 September 2026 · Reviewed against local `dev` at `0e84d91` (slice = `b7244c8..0e84d91`).**
Author: security & privacy engineer. Read-only review. Nothing was changed, nothing pushed,
production was not touched. Dev server was read from over SSH only.

---

## Verdict: **Pass with fixes**

The three changes in this slice are real, they do what the commit messages say, and they
add no new way to reach anyone's data. I found no Blocker **introduced by this diff**.

Two things must be true before the push is worth doing, and one must stop being said:

1. **On dev, this change does nothing until two site configs are edited.**
   `dev.alvoraa.co` and `ppj.dev.alvoraa.co` both name `vendor` explicitly in their
   `features` list. An explicit list beats the new opt-in default, by design. So every
   one of the nine open Blockers from the 18 Sep analysis stays live on both of those
   sites after this push. Either remove `vendor` from those two configs in the same
   release, or write down that the risk is accepted, by whom, on what date.
2. **One of the three claims is only three-quarters true.** The customer's details are
   out of the ten files the test scans, and still in four files it does not — including a
   live customer email that names the wrong company (`scheduled_jobs.py:57`).
3. **The two open findings from slice 014 are NOT closed.** They are unreachable on a
   tenant without the feature, which is most of them from today. On a tenant with the
   feature they work exactly as before. "Gated" is not "fixed", and the slice notes are
   honest about this — the release notes must be too.

---

## 1 · What the slice claims, and what I verified

| Claim | Verified? | How |
|---|---|---|
| All 28 previously ungated endpoints now carry `@requires_feature("vendor")` | **Yes** | Parsed every `@frappe.whitelist` in `alvoraa_portal` with `ast`. All 37 endpoints in the vendor/driver surface (11 in `portal_api.py`, 17 in `controllers/`, 7 in `api/vendor_portal_api.py`, 2 in `api/auth.py`) carry the gate. Zero ungated. |
| The gate runs before the function body | **Yes** | `@frappe.whitelist()` sits above `@requires_feature(...)` everywhere, so Frappe's registry holds the wrapped (gated) function. `subscription.py:requires_feature` throws `frappe.PermissionError` before calling the body. |
| The gate has no role bypass | **Yes** | `subscription.py` — `has_feature` is a pure entitlement check. Administrator and System Manager are refused too. Fail closed, correct. |
| `vendor` is opt-in, so no plan and no fallback hands it over | **Yes** | `subscription.py:157` adds `"opt_in": True`; `plan_features()` filters opt-in out of every plan; `DEFAULT_ON` (`:418`) excludes opt-in, so a site with no `features` and no `subscription_plan` does not get it. |
| One customer's details are out of the source | **Partly — see finding M1** | Gone from `portal_api.py` and the nine controllers. Still present in four other live files. |
| Driving telemetry no longer feeds a performance score | **Yes** | `scorecard.py:224-248` and `delivery_partner.py:139-160`: the three SQL sums are deleted, not commented out. Grepped the whole live tree — no other file reads `harsh_braking`, `harsh_acceleration`, `speeding_alert` or writes `harsh_driving_detected` / `speeding_incidents`. Safety score (`scorecard.py:59-62`) now moves only on a human-recorded incident. |
| `frappe.get_all` ignores permissions *(the one claim the 18 Sep analysis could not verify)* | **Now verified** | Installed Frappe **16.34.0** on `devstack-backend-1`, `apps/frappe/frappe/__init__.py:1383-1384`: *"List database query via frappe.model.db_query. Will **not** check for permissions."* The read half of the earlier analysis stands. |
| `ignore_permissions` count did not rise in product code | **Yes, with a caveat** | 491 → 496 across `alvoraa_portal`. All five are fixtures in the new test file (`insert`/`delete_doc` with `ignore_permissions=True`). No product-code use was added. A future CI counter must count test files separately or it starts life red. |

---

## 2 · Who can call the vendor/driver surface now

Tenant with `vendor` **off** (the new default — all plans, and any site with no
`features` key):

| Caller | Reach |
|---|---|
| Guest | Nothing. `vendor_login` is guest-allowed but gated, so it refuses. Both portal pages redirect a guest to login (`www/driver_portal.py:7`, `www/vendor_portal.py:8`). |
| Any logged-in employee | Nothing through the 37 endpoints. All refuse with `PermissionError`. |
| A vendor user / a driver | Nothing. They can still log in and still land on `/vendor-portal` or `/driver-portal` (`auth.py:35-42`), where the page renders and every call fails. |
| HR Manager / System Manager | **Still full, unscoped read and write** on all 21 delivery/vendor DocTypes through the ordinary desk API (`/api/resource`, report view). The feature gate does not touch that path; DocType permissions do, and they grant System Manager `rwcd` and HR Manager `rwc` on every one, with **no row scope, no `if_owner`, and no `permission_query_conditions`** (`hooks.py:167-173` registers row-level security for `Employee Checkin` only). Unchanged by this slice, and correct to leave for phase 2 — but it means "switched off" is not "no one can read it". |

Tenant with `vendor` **on** (today: `dev.alvoraa.co`, `ppj.dev.alvoraa.co`):

**No change from before the slice.** Any logged-in user of that site can still call all
37 endpoints, and ownership is enforced server-side in exactly two places:
`portal_api.update_driver_location` (`portal_api.py:242-245`, the slice-014 fix, intact)
and `vendor_order.change_order_status` (`vendor_order.py:95-101`, a role check). The
seven endpoints in `api/vendor_portal_api.py` resolve the vendor from the session and
check ownership — but `vendor-portal.html:873` still hardcodes
`"alvoraa_portal.portal_api." + method`, so the page people open calls the unsafe twin.

Cross-tenant: still not an issue. Each tenant is a separate Frappe site
(`deploy/provision_tenant.sh:69`), and I confirmed four separate sites on the dev stack.

---

## 3 · The two slice-014 findings: **not closed**

Stated plainly, because the temptation to tick them is real.

| 014 finding | State at `0e84d91` |
|---|---|
| Any logged-in user reads a driver's GPS trail — `portal_api.py:383 get_delivery_route`, `portal_api.py:105 get_order_live_location` | **Open.** Both now refuse when the feature is off. Neither gained an ownership check. Raw SQL straight onto `tabVehicle Tracking`, keyed on a caller-supplied id. |
| The demo fallback that reveals the most recently moved driver's name and position | **Open, and deliberately deferred.** `portal_api.py:155-172` still falls back to the newest tracking row for *any* partner and then looks up that person's `partner_name` and `vehicle_type`. The code now carries a comment at `:111-113` naming it as finding B3 and pointing at phase 2. Comment-as-control: honest, but not a control. |
| `controllers/delivery_assignment.py:191 update_gps_location` — any logged-in user appends a GPS point to any assignment and triggers an "arriving soon" email to a customer | **Open.** Gated only. No ownership check, no rate limit. The email body no longer names the wrong company (good), the send is unchanged. |

What is left, in one sentence: on any tenant where the portal is on, a curious colleague
can still watch a named driver move and can still make a customer's phone buzz.

---

## 4 · Findings, ranked

No Blocker is introduced by this diff. These are ranked by what should happen before or
alongside the push.

### Major

**M1 · The customer-details removal is incomplete, and the test that pins it cannot see
the gap.**
`tests/test_portal_module_gate_016.py:184-188` scans only the ten modules in `MODULES`
(`portal_api` plus the nine controllers). Still in the live tree at `0e84d91`:

- `alvoraa_portal/alvoraa_portal/scheduled_jobs.py:57` — the daily
  `send_arrival_notifications` job emails the vendor *"Your Grace Drinks order will
  arrive in approximately N minutes"*. This is the same message
  `delivery_assignment.py:218` was fixed for, in a second copy the scan does not reach.
  Every tenant with data would tell its own customers another company's name.
- `alvoraa_portal/alvoraa_portal/hooks.py:5` — `app_email = "ops@gracedrinks.in"`. The
  app's publisher address; it surfaces in the About dialog and in a public repository.
- `alvoraa_portal/alvoraa_portal/setup_data.py:12,24,36` — three hub contact mailboxes at
  that customer's domain. The file is dead code (nothing calls it), which is why this is
  Major and not worse.
- `alvoraa_portal/alvoraa_portal/frontend/src/pages/Account.jsx:24` — *"contact Grace
  Group operations at ops@gracedrinks.in"* in the unused Vue front end.

Demo and seed scripts (`demo_setup.py`, `demo_seeder.py`) also carry the names. Those are
demo data and I would leave them.

*Fix:* extend `_sources()` to every `.py`, `.html` and `.jsx` in the app, not a
hand-written module list, and fix `scheduled_jobs.py:57` in this slice. The one-line
email fix is the load-bearing part.

**M2 · One of the new tests cannot fail.**
`test_portal_module_gate_016.py:139-152`:

```python
with self.assertRaises(frappe.PermissionError, msg=name):
    try:
        fn()
    except TypeError:
        raise frappe.PermissionError
```

Almost every endpoint takes required arguments. With the gate present, the decorator
throws `PermissionError` first and the test passes for the right reason. **Remove the
gate and `fn()` raises `TypeError` for missing arguments, which this code converts into
the very exception it is asserting** — so the test still passes. It is green either way
for ~25 of the 28 endpoints. The `ast` test above it (`:117-131`) does the real work, so
the gate is still pinned; but this test reads like a second, independent proof and is
not one. Either pass dummy arguments, or assert on
`getattr(fn, "__alvoraa_feature__", None)` and delete the `except TypeError`.

**M3 · Switching the feature off does not stop the scheduler or the document hooks.**
`requires_feature` guards whitelisted endpoints only. On a tenant with the portal off,
these still run against whatever rows exist: `scheduled_jobs.calculate_driver_ratings`
(hourly), `scheduled_jobs.send_arrival_notifications` (daily, **sends mail to a
customer**), `vehicle_compliance.check_all_compliance_alerts` (daily, **sends mail naming
a driver and a vehicle**), plus every `doc_events` entry at `hooks.py:127-160`, which
includes the OTP generation and the vendor emails on `Delivery Assignment` insert. So
"off" means the doors are locked while the building keeps posting letters. It is harmless
today because every dev site has zero rows in these tables, and it will not be harmless
on a tenant that once used the module and then turned it off.
*Fix:* an early `if not has_feature("vendor"): return` at the top of the four scheduled
jobs. Half an hour, and it makes the off switch mean what it says.

### Minor

- **Mi1 · `hooks.py:33-34` still routes `/vendor-portal` and `/driver-portal` on every
  tenant.** With the feature off the page renders for any logged-in user and every call
  fails. No data leaks, but the failure is a stack of silent API errors rather than
  "this is not part of your plan". `www/vendor_portal.py` and `www/driver_portal.py`
  check for Guest only.
- **Mi2 · Turning the feature off revokes no account and no session.** Vendor Users and
  their linked Website Users stay enabled, `Vendor User.account_locked` is untouched, and
  `auth._portal_home_for` still sends them to a dead portal. Nothing residual *works* —
  the gate is checked per call, not per session, so an existing session gains nothing —
  but "off" is not "revoked", and a security questionnaire will ask which one it is.
- **Mi3 · `delivery_settings.ops_recipients()` is the right shape, and it fails closed
  correctly** (empty list → no send, one log line, `delivery_settings.py:76-93`). One
  gap: `vendor_order.py:229` (`_get_warehouse_manager_emails`) now returns `[]` when
  nothing is configured, and `frappe.sendmail(recipients=[])` will raise inside a
  `try/except` at the call site. Not a leak; a silent no-send where the old code sent to
  the wrong place. Worth a log line so the tenant learns the mailbox is missing.
- **Mi4 · `frappe.publish_realtime` with no `room` and no `user`** at
  `controllers/vendor_order.py:70,79` and `controllers/delivery_order.py:276` broadcasts
  to the site room — "all Desk users" per Frappe 16.34.0 `frappe/realtime.py`. The
  payload is an order id and a status, so this is low, but it is a broadcast nobody
  intended. The custom `room=f"delivery_order_{name}"` is unreachable by any client
  (Frappe's socketio only joins doc and user rooms), so that one is dead code, not a leak.
- **Mi5 · `mark_proof_of_delivery` (`delivery_order.py:346`) stores whatever string the
  caller passes as the photo and signature path,** with no check that the file belongs to
  this order. Gated, and only reachable by a caller who already has the feature. Phase 2.

### Worries, not findings — kept separate on purpose

- The scorecard code no longer *writes* telemetry-derived scores, and clears the two
  telemetry-only fields on regeneration. But **no patch recomputes scorecards already
  written**, and `overall_delivery_score`, `performance_level` and
  `recommended_increment` were stored, not derived on read. A tenant with history would
  keep pay recommendations that a phone's accelerometer helped set. Zero rows on every
  dev site today, so this is a worry now and a data-fix later — but it must be written
  down before a live tenant ever uses the module.
- **Collection of the behavioural signal continues.** `portal_api.py:261` still computes
  `"speeding_alert": 1 if spd > 60 else 0` from the driver's own posted speed and stores
  it on `Vehicle Tracking`; `demo_setup.py:171` seeds the same. The slice stopped the
  scoring, which was the FR-H7 breach. It did not stop the judgement being recorded about
  a named person with no purpose tag and no retention rule.

---

## 5 · Privacy — what the portal still exposes, and the DPDP view

I am not a lawyer. What follows is engineering requirement derived from published
sources, with the question for counsel stated at the end.

### Personal data in this surface, as it stands

| Data | Where | Sensitivity | Purpose tag | Retention rule | Who may see it today (feature on) |
|---|---|---|---|---|---|
| Customer name, full delivery address, delivery GPS | `Delivery Order`, returned by `get_driver_deliveries`, `get_partner_today_orders`, `get_today_orders_for_partner` | Sensitive (third-party personal data) | none | **none** | any logged-in user |
| Customer phone | `Delivery Order.customer_phone`, returned by the two "today's orders" endpoints | Sensitive | none | **none** | any logged-in user |
| Driver name, personal mobile, vehicle registration | `Delivery Partner`, returned by `get_vendor_orders` (`portal_api.py:97`) and `get_drivers_performance` | Sensitive | none | **none** | any logged-in user |
| Driver continuous location, speed, heading, breadcrumb trail | `Vehicle Tracking`, `Delivery Tracking` | Sensitive — location of an identified worker | none | **none at all** | any logged-in user |
| Derived driving-behaviour flags (`harsh_braking`, `harsh_acceleration`, `speeding_alert`, `sharp_turn`, `idle_duration`) | `Vehicle Tracking` | Sensitive, behavioural | none | **none** | any logged-in user, via the trail endpoints |
| Driver pay — `commission_earned`, `bonuses_earned`, `net_amount` | `Delivery Performance Scorecard`, returned by `get_partner_performance_summary`, `get_hub_performance_report` | Highest class in the product (feature map F4) | none | **none** | any logged-in user |
| Licence and insurance expiry per driver | `Vehicle Maintenance Compliance`, `get_compliance_dashboard` | Sensitive | none | **none** | any logged-in user |
| PAN and Aadhaar | `Delivery Partner` fields 41-42 | **Statutory ID** | none | **none** | no endpoint returns them today; no masking, no reveal log, so the next one that touches the doctype inherits the loosest treatment |
| Delivery OTP | `Delivery Assignment.delivery_otp`, **and written in clear text to the Error Log** (`delivery_assignment.py:36-39`) | Secret | n/a | Error Log default | anyone who can read the Error Log |

**Minimisation:** the slice improved this in one concrete way — customer names, addresses
and order values are no longer posted to a third party's mailbox by every tenant
(`delivery_settings.ops_recipients()` returns `[]` and sends nothing rather than guessing
an address). That is a genuine, checkable reduction. Nothing else about minimisation
changed: the endpoints still return whole rows rather than the fields a caller needs.

**Purpose limitation:** the slice's best privacy win. Removing the telemetry-to-score
path means data collected to run a delivery is no longer reused to set someone's pay.
That is purpose limitation enforced by structure — the SQL is gone, not merely unused —
and it is the right shape. It is only unwound on **historical** scorecards, per the worry
above.

**Retention: the gap is unchanged and it is stark.**

| Object | Rule |
|---|---|
| Field check-in photo | 90 days, configurable, `0` = keep for ever, daily purge job, and a legal-hold flag on the record (`field_checkin.py:643-750`, wired at `hooks.py:186`) |
| `Vehicle Tracking` — a driver's continuous location | **No rule. No purge job. No config key.** Grepped the whole tree: the only deletions are test fixtures. |
| `Delivery Tracking` child rows | **No rule.** |

So the product deletes a photograph of a face after 90 days and keeps a minute-by-minute
movement history of the same person for ever. That inconsistency is the clearest thing a
reviewer will find, and the cheapest to fix: the check-in purge job is a working pattern
to copy.

**DPDP Act 2023 / DPDP Rules 2025** (baseline verified 24 Aug 2026 and 6 Sep 2026 —
within 90 days, not stale). Engaged here: notice, purpose limitation, minimisation,
storage limitation, and reasonable security safeguards. Nothing is due *today*: per the
recorded note of 17 September 2026 there is no onboarded customer, PPJ is a demo, and I
confirmed every vendor and delivery table on every dev site is empty. **No reporting duty
is engaged and no Data Principal is affected.** That protection expires at the first live
tenant, not at some later date of our choosing.

**Question for counsel, unchanged from the 18 Sep analysis and still unanswered:** on
what legal basis do we process a driver's continuous location; for how long may it be
kept; and what must the driver be told before the first point is recorded? It blocks
shipping this module to any live tenant. A recommended default is not an answer to it.

**CERT-In:** nothing in this slice touches the 6-hour clock or the 180-day India-resident
log gap. The OTP in the Error Log (`delivery_assignment.py:36-39`) is a secret in a log
and stays a Blocker by our own rule — carried from the earlier analysis, untouched here.

---

## 6 · Does the opt-in change actually switch the portal off?

**For endpoints, yes — properly.** The check is per call, reads the site's own config
which a tenant cannot edit, has no role bypass, and rejects before the function body.
An existing session, an old browser tab or a saved `frappe.call` gains nothing: the gate
is not a session flag.

**But it switches nothing off on the two dev sites that matter.** Measured read-only on
`devstack-backend-1`:

| Site | `subscription_plan` | `features` key | `vendor` in it? | Effect of this slice |
|---|---|---|---|---|
| `dev.alvoraa.co` | `enterprise` | present, 14 entries | **yes** | **none — portal stays fully on** |
| `ppj.dev.alvoraa.co` | `custom` | present, 13 entries | **yes** | **none — portal stays fully on** |
| `allabouthr.dev.alvoraa.co` | `custom` | present, 8 entries | no | already off; stays off |
| `test_site` | none | absent | no | now off by fallback (was on) |

An explicit `features` list wins over the opt-in default, and that is the documented,
deliberate design (`subscription.py:500-523`) — a tenant that was given something keeps
it. The consequence for this release is simply that the fix does not reach the two sites
where it would matter.

**Residuals when it is off:** the four scheduled jobs and all `doc_events` still run
(M3); the two routes still resolve and the pages still render (Mi1); vendor and driver
accounts stay enabled and still get redirected to a dead portal (Mi2); HR Manager and
System Manager keep unscoped desk access to every delivery and vendor DocType. No token,
link, or public file keeps working — there are no public files in this surface and no
bearer tokens; `vendor_login` is the only guest entry point and it is gated.

---

## 7 · Dev sites: what this release should clean up

Read-only, counts only, nothing copied.

| Item | Count |
|---|---|
| Sites on the dev stack | 4 (`dev.alvoraa.co`, `ppj.dev.alvoraa.co`, `allabouthr.dev.alvoraa.co`, `test_site`) |
| Sites with `vendor` enabled through an explicit `features` list — **to clean up** | **2** (`dev.alvoraa.co`, `ppj.dev.alvoraa.co`) |
| Sites with `portal_ops_email` configured (so ops alerts can be sent at all) | 0 of 4 |
| Sites with `portal_warehouse_name` configured | 0 of 4 |
| Rows in `Vendor`, `Vendor User`, `Vendor Order`, `Delivery Partner`, `Delivery Order`, `Delivery Assignment`, `Vehicle Tracking`, `Order Rating`, `Delivery Performance Scorecard` | **0 in every table, on all three real sites** |

So there is **no personal data to clean up** in this surface on dev. The only cleanup is
two lines of config. That is also why every finding above is a future risk rather than a
present incident.

One consequence of the zero-row result worth saying out loud: the new telemetry tests
create their own fixtures, so they prove the code path — but nobody has exercised this
module against realistic data since the change, and the module's own end-to-end flow
(driver posts location → vendor sees it) has not been re-walked by a human on a site with
the feature on. That check is on the list in §9.

---

## 8 · Residual risk

| # | Risk | Remains because | Accepted by | Date |
|---|---|---|---|---|
| R1 | On a tenant with the portal on, any logged-in user can read every vendor's orders, every driver's deliveries, a driver's live position and pay, and can change other people's delivery statuses and ratings (Blockers B1-B7 of the 18 Sep analysis) | Ownership and row scope are phase 2; this slice gated entitlement only | | |
| R2 | `dev.alvoraa.co` and `ppj.dev.alvoraa.co` keep the feature, so R1 is live on both after this push | Explicit `features` beats the opt-in default, by design | | |
| R3 | Vendor portal 2FA is advertised and not enforced — `api/auth.py:57-59` only checks the OTP is non-empty | Phase 5 of the plan; unchanged here | | |
| R4 | Delivery OTP written in clear text to the Error Log; `verify_delivery_otp` has no attempt limit and no rate limit | Phase 4/5; unchanged here | | |
| R5 | A driver's GPS history has no retention limit and no purge, while a check-in photo is deleted after 90 days | No retention engine for this module (feature map A6) | | |
| R6 | Historical scorecards keep scores, performance levels and pay recommendations that telemetry helped set | No back-fix patch shipped; zero rows today | | |
| R7 | PAN and Aadhaar on `Delivery Partner` have no sensitivity class, no masking, no reveal log | Depends on A1 field sensitivity classification, not built | | |
| R8 | No refusal anywhere in this module is logged or alerted. `hrms/alvoraa_hr_core/access.py:log_refusal` exists and is unused here, so we would not learn that anyone tried | Detection is phase 2 | | |
| R9 | Scheduled jobs and document hooks ignore the feature gate, so an "off" tenant still emails customers and drivers | M3, not yet fixed | | |
| R10 | HR Manager and System Manager have unscoped read/write on all 21 delivery and vendor DocTypes through the desk API, whatever the plan | DocType permissions have no row scope; `permission_query_conditions` is registered for `Employee Checkin` only | | |
| R11 | The legal basis, retention period and driver notice for continuous location tracking are undecided | Question for counsel, unanswered | | |

**An accepted risk with a name and a date is governance; these eleven have neither yet.**
R2 in particular is a decision for today, not for the slice that closes phase 2.

---

## 9 · What must happen before the push

**Must (in the slice):**

1. Fix `scheduled_jobs.py:57` — the daily arrival email still names the wrong company to
   a customer. One line.
2. Widen the customer-details scan in `test_portal_module_gate_016.py` from the ten-module
   list to every `.py`, `.html` and `.jsx` in the app, and clear what it then finds
   (`hooks.py:5`, `setup_data.py:12,24,36`, `frontend/.../Account.jsx:24`).
3. Fix `test_016_a_tenant_without_the_feature_is_refused_on_every_one` so it cannot pass
   with the gate removed (drop the `except TypeError` conversion).
4. Say in the slice notes and the release note that the two slice-014 findings are
   **gated, not fixed**, and that the demo fallback leak is deliberately deferred. Do not
   let them be ticked.

**Must (with the release, as a dev-stage action the user approves separately):**

5. Decide on `dev.alvoraa.co` and `ppj.dev.alvoraa.co`: remove `vendor` from `features`,
   or accept R2 with a name and a date. Both tables are empty, so removing it costs
   nothing today.

**Should (next, small, in this slice or the one after):**

6. `if not has_feature("vendor"): return` at the top of the four scheduled jobs (M3).
7. A retention rule and a daily purge for `Vehicle Tracking` and `Delivery Tracking`,
   copying the check-in photo pattern, including its legal-hold flag (R5).
8. Stop writing the OTP to the Error Log (R4). It is one line, it is a secret in a log,
   and by our own rule it is a Blocker not a Major.

**Cannot be closed by engineering:** R11, the counsel question on continuous location
tracking. Ask it before the first customer, not after.

---

## Verification record

| Item | Source | Date |
|---|---|---|
| Endpoint inventory and gate coverage (37/37) | `ast` parse of `alvoraa_portal` at `0e84d91` | 18 Sep 2026 |
| Decorator order, no role bypass, opt-in semantics | `subscription.py:481-528`, `:628-665` | 18 Sep 2026 |
| `frappe.get_all` ignores permissions | Installed Frappe 16.34.0, `apps/frappe/frappe/__init__.py:1383-1384`, `devstack-backend-1` | 18 Sep 2026 |
| `publish_realtime` default room = site room | Installed Frappe 16.34.0, `apps/frappe/frappe/realtime.py` | 18 Sep 2026 |
| DocType permissions and guest exposure on all 21 delivery/vendor DocTypes | The doctype JSON files | 18 Sep 2026 |
| Dev site `features` / `subscription_plan`, and row counts in nine tables | Read-only SSH to `100.127.29.62`, `devstack-backend-1` | 18 Sep 2026 |
| Telemetry no longer read anywhere in the live tree | grep across `alvoraa_portal`, `hrms`, `alvoraa_goals` | 18 Sep 2026 |
| No retention or purge for `Vehicle Tracking` / `Delivery Tracking` | grep across the tree; `field_checkin.py:643-750` for the contrast | 18 Sep 2026 |
| `ignore_permissions` 491 → 496, all five in test fixtures | `git grep -c` at both commits | 18 Sep 2026 |
| DPDP / CERT-In obligations cited | `.claude/context/security-compliance-baseline.md` (verified 24 Aug and 6 Sep 2026 — not stale) | 18 Sep 2026 |
| No onboarded customer; PPJ is a demo | Recorded note of 17 Sep 2026, plus zero rows measured on dev | 18 Sep 2026 |

Production was not touched or probed. No file in the repository was modified, nothing was
committed, nothing was pushed.

**I am not a lawyer.** R11 is a question for counsel, not an answer.
