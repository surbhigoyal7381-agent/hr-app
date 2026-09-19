# Slice 016 — senior architect review (step 5)

Reviewer: technofunctional reviewer. 18 September 2026. Read-only review; no file was
edited, no git write command and no bench command was run.

**Verdict: SHIP WITH FIXES.**

The three things the slice promised are all really done, and the gate is pinned by a test
that would genuinely fail if anyone removed it. Nothing in the diff makes anything worse.
What stops this being a plain SHIP is not the code — it is two things that have to happen
around the push, and three small fixes that are cheap enough to fold in now.

Scope note: the task described slice 016 as five commits `b7244c8..0e84d91`. Local `dev`
is actually at `8e86470`, a sixth commit of the same slice ("Opt-in feature list: vendor is
on it now"). That commit is needed — without it `test_opt_in_features.py` fails. Reviewed
range: `b7244c8..8e86470`.

The slice docs (`docs/slices/016-portal-api-permissions/00-impact-analysis.md` and
`00-security-analysis.md`) are committed in `a923405`, so the approved strategy ships with
the code. Good.

---

## 1 · Does the impact analysis match the code?

I checked each claim in `00-impact-analysis.md` §5 against the diff. It holds up, and it is
unusually honest — it says out loud that this is an entitlement gate and not an ownership
fix, and it names the consequences a tenant will notice. Three claims need a footnote:

| Claim in the analysis | What the code shows |
|---|---|
| "Security / permissions — improves" | True for our own endpoints. It does **not** close `/api/resource/...`: the doctypes exist on every site whatever the plan (the app is installed everywhere), and `hooks.py` registers no `permission_query_conditions` or `has_permission` for any delivery doctype. Doctype permissions are System Manager + HR Manager, so it is not an any-employee hole, but the gate is on our doors only. |
| "Privacy — improves" | True, and materially. But "one customer's details are out of the source" is **overstated** — see Major 1. |
| "Upgrade-safety — neutral / safe" | Correct on schema: no patch, no fixture, no migration. But the deploy is **not** neutral in effect — see Blocker-adjacent item "Before the push", item 1. |

---

## 2 · Findings, worst first

### Carried Blocker (not caused by this slice, but it survives the gate)

**B-1 · A delivery OTP and a named driver are written to the Error Log on every assignment.**
`alvoraa_portal/alvoraa_portal/controllers/delivery_assignment.py:36-40`

```python
frappe.log_error(
    f"Delivery assignment {doc.name} created for driver {driver_name}. OTP: {otp}",
    "Delivery Assignment Notification",
)
```

Failure scenario: an HR Manager creates a Delivery Assignment — from the desk, from
`/api/resource/Delivery Assignment`, or through `vendor_order._prepare_delivery_pipeline`.
`hooks.py:137` fires `after_insert`. A live delivery secret and an identified employee's
name land in the Error Log, which every System Manager on that site can read. The
house rule is that a secret or personal data in a log is a Blocker, and the security
engineer graded it B9.

Why I am not calling BLOCK on the slice for it:
- It predates `b7244c8`. It is already in local `dev`. Blocking 016 does not remove it.
- The security analysis records it as phase 2, and phase 1's scope was approved as three
  items.

Why it still belongs at the top of this review: **the entitlement gate does not protect
this path.** `doc_events` hooks are not whitelisted endpoints, so a tenant with no `vendor`
tick still leaks the OTP the moment a Delivery Assignment is inserted. And the engineer
edited *inside this same function* (line 49, the email signature) while the OTP line sat
twelve lines above it.

Smallest fix, and it is two lines: drop `OTP: {otp}` and the driver's name from the
message, or delete the `frappe.log_error` call entirely — it is a "notification" written to
an error log, which is the wrong place for it anyway. I would fold this into the push.

### Majors

**M-1 · "One customer's details are out of the source" is not true of the app, only of the
ten files the test looks at.**

The commit message and the impact analysis both say the customer's details are gone. They
are gone from `portal_api.py` and the nine `controllers/*.py` files. They are still in the
same installed app, in a public repository:

| Where | What |
|---|---|
| `alvoraa_portal/alvoraa_portal/hooks.py:5` | `app_email = "ops@gracedrinks.in"` |
| `alvoraa_portal/alvoraa_portal/frontend/src/pages/Account.jsx:24` | user-facing text telling the reader to email `ops@gracedrinks.in` |
| `alvoraa_portal/alvoraa_portal/setup_data.py:12,24,36` | three hub `contact_email` values at that domain |
| `alvoraa_portal/setup.py:8` | `author_email="ops@gracedrinks.in"` |
| `alvoraa_goals/alvoraa_goals/hooks.py:5`, `alvoraa_goals/setup.py:11` | `hr@gracedrinks.in` |
| `alvoraa_portal/alvoraa_portal/demo_seeder.py:11-23` | the five named shops **with their street addresses** |
| `alvoraa_portal/alvoraa_portal/demo_setup.py:189-258` | the same five shops, names and addresses |

The pin test `test_016_no_customer_name_phone_shop_or_mailbox_is_hardcoded` only reads the
ten modules in `MODULES` (`test_portal_module_gate_016.py:183-187`), so it passes while all
of the above stays. The five shop names are on the test's own BANNED list and are sitting in
`demo_seeder.py` right now.

None of these is a *runtime* leak on another tenant: `Account.jsx` is an unbuilt Vite app
with no build reference anywhere in the repo, and `setup_data.py`, `demo_seeder.py` and
`demo_setup.py` have **no callers at all** (I grepped `alvoraa_portal/`, `deploy/` and
`hrms/docker/`). So this is a public-repo disclosure and an inaccurate claim, not a live
data flow. That is why it is a Major and not a Blocker.

Smallest fix: point the test's `_sources()` at the whole app directory rather than the ten
modules, then delete the three dead files and neutralise the four `*_email` metadata lines.
Do not widen the test without doing the deletions — it will fail immediately, which is the
point.

**M-2 · Slice 014's driver-location fix is bypassable through an endpoint this slice
touched.** `controllers/delivery_assignment.py:190-225`

014 closed `portal_api.update_driver_location` so only the assigned driver may post a
position. `delivery_assignment.update_gps_location` is the second path to the same idea and
has **no ownership check at all**: any logged-in user on an entitled tenant passes any
`assignment_name`, and the code appends a fake position to `tracking_history`, saves with
`ignore_permissions=True`, broadcasts it over the websocket to whoever is watching, and — if
`eta_minutes <= 10` — sends an "arriving soon" email to that vendor's real mailbox. So it is
also an email-sending primitive for an arbitrary user.

016 added `@requires_feature("vendor")` here and deferred ownership to phase 2 (recorded as
M3 in the security analysis), so this is disclosed, not hidden. But 014 and 016 go to dev in
the same push, and 014's release note says the driver-location hole is closed. It is closed
on one path of two. Please do not let that sentence stand unqualified.

No fix required in this slice. It needs to be said in the push note, and it is the reason
the `vendor` tick should not go to a live tenant yet.

**M-3 · Nothing remediates the scores and warnings the telemetry already produced.**
`controllers/scorecard.py:224-248`, `:92-105`

Stopping the derivation is right and complete. But `_set_compensation_recommendations`
(`scorecard.py:92-105`) already wrote, on existing scorecards, `recommended_increment`,
`promotion_eligible`, and — at the Critical tier — `warning_issued = 1` with
`warning_type = "Written"`. Those came from a basis this slice has just declared we do not
use. The impact analysis says existing rows keep their numbers because rewriting a record
that justified a payment would be worse, and I agree with that reasoning. What is missing is
the other half: **nobody has counted the affected rows or decided what to do about an
automatic written warning derived from a driving-style number.**

This is a decision for the user, not a code change, and it wants a plain answer before the
module is ever ticked on for a live tenant. The query is one line:
`frappe.get_all("Delivery Performance Scorecard", {"harsh_driving_detected": [">", 0]})`.

**M-4 · An employee on a tenant without the feature can still open the portal, and sees a
broken screen.** `www/vendor_portal.py`, `www/driver_portal.py`

Both `get_context` functions only check for Guest. The page renders; then every
`frappe.call` gets a 403. `vendor-portal.html:871-881`'s `api()` helper has no user-visible
error path — it does `console.error` and, for most calls, nothing else. So after this slice,
on **every tenant until someone ticks `vendor`**, any logged-in employee who reaches
`/vendor-portal` gets a screen that never finishes loading plus a stack of Frappe error
dialogs reading "Vendor & Driver Portal is not included in your plan."

The impact analysis calls this out in §9 as "scruffy" and not a regression. Strictly true —
before the change there was no refusal at all. But the change makes it the normal case
rather than a corner case, and it is three lines to fix properly:

```python
from alvoraa_portal.subscription import has_feature
if not has_feature("vendor"):
    raise frappe.DoesNotExistError
```

That gives a 404, which is also the right answer for a module the tenant does not have — it
does not advertise a product they have not bought.

### Minors

**m-1 · Every vendor pin now lands on top of the warehouse.**
`delivery_settings.vendor_coords():123-134`

`VENDOR_COORDS` had five real coordinates and a Chandigarh default. Now an unconfigured
tenant gets `hub_coords()` back for every vendor, which is a truthy value, so
`vendor-portal.html:1215` draws a customer marker sitting exactly on the hub marker with a
zero-length route line. `vendor_coords` returning `(None, None)` would use the page's
existing no-position path, which is cleaner and is what the docstring claims happens
("vendor-portal.html already copes with no position at all"). Note this also visibly
degrades the PPJ demo map unless `portal_vendor_coords` is set on that site.

**m-2 · The warehouse-manager notification can now go nowhere, silently.**
`controllers/vendor_order.py:214-229`

`_get_warehouse_manager_emails()` used to end `or ["ops@gracedrinks.in"]` and now ends
`or delivery_settings.ops_recipients()`, so it can return `[]`. The `frappe.sendmail` at
`:287` is inside a `try`, and Frappe's queue builder returns early on an empty recipient
list, so nothing crashes — but unlike `send_ops_alert`, there is no "not sent" log line.
The only trace is the pre-existing `frappe.log_error` at `:335` that prints
`Notified managers: []`. Either route this through `delivery_settings.send_ops_alert` too,
or add the same fail-closed log line.

**m-3 · The behavioural half of the entitlement test proves nothing for 24 of the 28
endpoints.** `tests/test_portal_module_gate_016.py:122-138`

```python
with self.assertRaises(frappe.PermissionError, msg=name):
    try:
        fn()
    except TypeError:
        raise frappe.PermissionError
```

If the gate were deleted, `get_vendor_orders()` with no arguments would raise `TypeError`,
which this converts into the very `PermissionError` the test is asserting. So the test
passes whether the gate is there or not, for every endpoint that takes an argument. Only the
four zero-argument endpoints actually exercise the refusal.

This does **not** mean the gate is unpinned — `test_016_every_endpoint_carries_the_gate`
(`:96-109`) parses the source with `ast` and does fail if any decorator is removed, and I
traced that. The pattern is also inherited from the existing
`test_endpoint_entitlement.py:160-172`. But a test that looks like it proves refusal and
does not is worse than no test. Smallest fix: assert on
`getattr(fn, "__alvoraa_feature__", None) == "vendor"` in that loop instead of swallowing
`TypeError`, or build dummy arguments from `inspect.signature`.

**m-4 · Regeneration wipes a manually entered `harsh_driving_detected`.**
`controllers/scorecard.py:247-248`

`doc.harsh_driving_detected = 0` and `doc.speeding_incidents = 0` run unconditionally. Both
fields are editable in the desk (`delivery_performance_scorecard.json:286,292`), so a
manager who typed an observed value loses it on the next regeneration. The reasoning in the
comment is sound — these fields only ever came from telemetry — and `safety_incidents` is
correctly left alone. Low harm, worth a docstring line, or hide the two fields on the form
so nobody types into them.

**m-5 · Two sources of truth for what a tenant has, and the console reads the wrong one.**
`tenant_api.py:217,233` vs `:600-606`

`update_tenant` writes both `features` (ids — the authoritative list `enabled_features()`
reads) and `modules_enabled` (display labels). `list_tenants` returns only
`modules_enabled`, and the edit modal reconstructs its ticks from that via
`alvoraa-admin.html:1938-1948`. That reverse map covers `vendor`, so **`vendor` survives an
edit** — I checked, and this is not an 016 problem. But the same map is missing `portal`,
`tenure`, `tax_benefits`, `performance`, `late_rules`, `field_checkin` and every ERPNext key,
so editing a tenant for an unrelated reason strips those. Pre-existing; flagging it because
the console is now the only way anyone gets the vendor portal, so the console's accuracy
matters more than it did yesterday.

### Nits

- `subscription.requires_feature`'s docstring says the gate is applied "ABOVE
  `@frappe.whitelist()`". In the source `@frappe.whitelist()` is above and the gate below,
  which is the *correct* order (Python applies bottom-up, so the whitelist registry holds
  the wrapped function). The test at `:111-120` asserts exactly this. Only the wording is
  back to front.
- `test_driver_location_014.py:66` mutates `frappe.conf["features"]` in `setUpClass`. It
  restores in `tearDownClass`, but a hard failure between the two leaves the shared conf
  dirty for the rest of the run. Same pattern in `test_portal_module_gate_016.py:256`.

---

## 3 · Answers to the specific questions asked

### All 28 endpoints

I enumerated every `@frappe.whitelist` in the app with `ast` (including the two files with a
UTF-8 BOM that a naive parse skips). **All 28 are gated, and the count is exactly 28**:
`portal_api.py` 11, `delivery_assignment` 2, `delivery_feedback` 1, `delivery_order` 5,
`delivery_partner` 3, `rating` 1, `scorecard` 2, `vehicle_compliance` 1, `vendor_order` 2.
The seven in `api/vendor_portal_api.py` and the two in `api/auth.py` were already gated.

No open endpoint remains in the vendor/driver surface. Checks on the bypass routes asked
about:

| Bypass route | Result |
|---|---|
| Decorator order | Correct. `@frappe.whitelist()` outermost, so the registry holds the gated wrapper. Pinned by a test. |
| GET vs POST | No `methods=` restriction anywhere in this module, so both work — but the gate is inside the function, not in a method check, so it runs either way. |
| Guest access | No `allow_guest` in the 28. `api/auth.py:10 vendor_login` is guest and gated. |
| `cmd=` path | Resolves the module attribute, which is the wrapper. Gate runs. |
| `ignore_permissions` | Plenty of it inside the bodies, all pre-existing, none added by this slice. It sits *behind* the gate, so an unentitled tenant never reaches it. On an entitled tenant it is exactly the phase-2 problem. |
| Child-table write | `update_gps_location` writes `tracking_history` — gated by entitlement, not by ownership. See M-2. |
| `doc_events` hooks | **Not gated, by design and correctly** — `validate`, `after_insert`, `on_update` must hold for the desk and the REST API too. This is also how B-1 escapes the gate. |
| Scheduler jobs | Not gated. Server-side, no session. `generate_monthly_scorecards` will keep running on a tenant that no longer has the feature. Harmless (it writes the module's own doctype) but worth knowing. |

### The opt-in change

- **What breaks for tenants that had it through a plan:** every tenant provisioned by
  `deploy/provision_tenant.sh` loses the module the moment the new image is live.
  That script writes `subscription_plan` and never `features`, so those sites were running
  on `enabled_features()`'s fallback, and `vendor` is now excluded from both the fallback and
  from `plan_features()` for all four plans. This is the intended outcome and it is stated
  plainly in the analysis §6 — but it is an availability change, not a no-op.
- **Is it reversible?** Yes, cleanly. `tenant_api.update_tenant` writes `features` into the
  site config with `bench set-config -p`; `enabled_features()` reads `features` first and
  explicit always wins. The admin console lists opt-in features and badges them "opt in"
  (`alvoraa-admin.html:1716`), and the reverse label map includes `vendor`. One tick, and no
  migrate needed.
- **Is the default safe?** Yes, and it is the right direction: off unless named. Given the
  nine Blockers and twelve Majors still open in the security analysis for this module, "off
  by default" is exactly where it should be.

### "Drop one customer's details" and "stop scoring telemetry"

- **What stopped flowing:** four alert-email paths (`delivery_feedback` ×2, `rating`,
  `vendor_order`) no longer post a customer's name, address and order value to a third
  party's mailbox — they now fail closed with a log line naming only the document id. The
  outbound geocoder `User-Agent` no longer carries that address. The signature on six
  outgoing customer emails now comes from Global Defaults. That is a genuine privacy fix and
  the best thing in the slice.
- **Does anything still read the dropped fields?** No `KeyError` or broken screen. I traced
  every reader: `vendor-portal.html:1068` tests `warehouse_phone` for truth before drawing
  the Call button, and `:1215` tests `customer_lat && customer_lng`.
  `driver-portal.html:1755` has its own `hub_lat` fallback. `WAREHOUSE_NAME`,
  `WAREHOUSE_PHONE`, `VENDOR_COORDS`, `HUB_LAT` and `HUB_LNG` have no remaining references
  outside the worktrees. The one visible change is m-1 (pins on the hub).
- **Data left behind that should be cleaned:** yes, two piles, both intentionally left.
  (a) `safety_incidents` on existing `Delivery Partner` rows still holds a telemetry total
  from the last stats refresh, and nothing zeroes it — so a driver keeps a "safety incident"
  count nobody recorded. The code comment explains the choice (a refresh must not wipe a
  real recorded incident), and it is the right trade-off, but the pre-existing telemetry
  totals are now indistinguishable from human-recorded ones. (b) Existing scorecards keep
  `harsh_driving_detected`, `speeding_incidents`, the scores derived from them, and any
  auto-issued written warning — see M-3. The raw `Vehicle Tracking` rows are deliberately
  kept and retention remains an open question with no owner.

### Interaction with slice 014

016 **neither weakens nor duplicates** 014. The three 014 changes:
- *Driver-location owner check* — untouched. 016 added a decorator line above
  `update_driver_location`; the `_driver_partner_for` check at `portal_api.py:238-242` is
  intact and now runs behind an entitlement gate, which is strictly stronger. 016 did have
  to teach `test_driver_location_014` to switch the feature on for itself
  (`db8db2e`), which is correct — that test is about who may post, not about the plan. The
  one caveat is M-2: the *other* GPS path is still ownership-free.
- *Check-in error-log redaction* — different module (`field_checkin.py`), untouched. Note
  the contrast: 014 took names and positions out of check-in error logs while
  `delivery_assignment.py:36-40` still puts an OTP and a driver's name into one. Same rule,
  two answers, in the same push. That is B-1.
- *nginx change* — not touched by 016. No interaction.

### Upgrade order

- **No patch, no `patches.txt` entry, no DocType JSON change, no fixture, no new dependency,
  no schema change.** I verified: the diff is ten Python files plus two test files.
- **Nothing needs a migrate before the code is live.** Everything reads `frappe.conf` at call
  time.
- **What breaks between the image swap and anything else:** the entitlement flip takes effect
  the instant the new code is loaded. There is no window where the old behaviour persists —
  which means there is no window in which to tick the feature on *after* the swap without a
  gap. Tick first, swap second.
- `bench clear-cache` is not strictly required (no cached feature list), but `set-config`
  already runs one via `update_tenant`.

### The pin tests — would they fail if the gating were removed?

**Yes, for all three changes.** I read them line by line and did not run them.

| Change | Test that fails | Verified how |
|---|---|---|
| A decorator removed from any of the 28 | `test_016_every_endpoint_carries_the_gate:96` — `ast` walk, `missing` non-empty | Traced. Also catches a *new* ungated endpoint, which is the valuable part. |
| Decorator order inverted | `test_016_the_gate_runs_before_the_body:111` | Traced. |
| `opt_in` removed from `vendor` | `test_016_vendor_is_opt_in:140`, `test_016_a_site_with_no_feature_list_does_not_get_vendor:143`, `test_016_no_plan_bundle_hands_it_over_on_its_own:150`, plus `test_opt_in_features.py:121` | Traced. Four independent angles — good. |
| Telemetry SQL restored in `delivery_partner` | `test_016_a_stats_refresh_does_not_write_safety_incidents:298` and `test_016_the_scoring_code_no_longer_reads_the_telemetry_columns:326` | Traced. |
| Telemetry SQL restored in `scorecard` | `test_016_a_scorecard_carries_no_telemetry:318` | Traced. |
| Customer details put back in the ten modules | `test_016_no_customer_name_phone_shop_or_mailbox_is_hardcoded:189` | Traced — but see M-1 for what it does not look at. |
| A hardcoded address added to the ten modules | `test_016_no_bare_email_address_is_hardcoded:197` | Traced. Neat test. Only allows `example.com`. |

Two weaknesses: m-3 (the behavioural refusal test is vacuous for 24 endpoints) and the
`safety_incidents` test asserting the stats refresh does not *write* it — which it proves by
setting it to 0 first, so it would also pass if the code wrote 0 rather than not writing at
all. `test_016_a_recorded_incident_survives_a_stats_refresh:307` covers that gap properly.

No test asserts on a hard-coded document id, a real date, or a sleep. Fixtures use
`example.com` addresses and an obviously synthetic partner name. No real employee data.

---

## 4 · AC verification

The slice has no `02-functional-spec.md` and no acceptance criteria — it is a security and
privacy remediation slice driven by `00-security-analysis.md`, with three items approved in
the analysis §"Phase 1 scope". **This slice is unreviewable against formal ACs**, and that
is a process gap worth naming, not a defect in the code. I verified against the three
approved items instead.

| Approved item | Status | Evidence |
|---|---|---|
| 1 · Gate the whole vendor/driver/delivery module by plan | **Met** | All 28 endpoints carry `@requires_feature("vendor")`; `ast` enumeration of the whole app finds no ungated endpoint in the surface; `subscription.py:163` marks `vendor` opt-in; four tests pin it. |
| 2 · Remove the hardcoded customer details from that module | **Partial** | Removed from the ten module files and replaced with `delivery_settings` reading `frappe.conf`. Still present in seven other places in the same installed app, including the five shop names and addresses (M-1). |
| 3 · Stop driver telemetry feeding a performance score | **Met, with unremediated history** | Both derivations deleted (`delivery_partner.py:142-152`, `scorecard.py:224-248`); raw rows kept; `safety_incidents` now only human-set. Existing scores and auto-issued warnings untouched and uncounted (M-3). |

---

## 5 · NFR verification, seven dimensions before vs. after

I reasoned these from the code; I ran no benchmark and no test, because the bench is shared.

| Dimension | Analysis claimed | My finding |
|---|---|---|
| Performance | improves slightly | **Agree.** The gate is one `frappe.conf` dict lookup and short-circuits before the body. Two `SUM()` aggregates over `tabVehicle Tracking` — the fastest-growing table here, one row per GPS post — are deleted from the monthly scorecard path. At 10,000 employees on month-end this is strictly cheaper than before. |
| Scalability | improves | **Agree,** same reason. Nothing new grows with headcount. One caveat: on an entitled tenant with no `portal_ops_email`, every low rating and every escalation now writes an Error Log row instead of an email. Bounded by event volume, not by headcount. |
| Security | improves | **Agree, with the scope stated.** 28 server-side refusals added where there were none. Does not cover `/api/resource`, `doc_events`, or scheduler jobs, and adds no ownership check — all three correctly disclosed. No new `ignore_permissions`, no new raw SQL, no client-supplied doctype or field name, no new whitelisted endpoint. |
| Reliability | neutral, one watch point | **Agree.** The watch point (suppressed ops alerts) is real, deliberate and logged. I found one second-order case the analysis missed: `_get_warehouse_manager_emails()` can now return `[]` (m-2). No crash — Frappe's queue returns early and the call is inside a `try` — but silent. |
| Maintainability | improves | **Agree.** Six copies of a literal address become one lookup; one small settings module with a clear docstring; one decorator per endpoint. The comment blocks are long but they explain *why*, which is the useful kind. A new engineer would follow this in six months. |
| Data integrity | improves | **Agree** for new data. **Partial** for old: pre-existing telemetry totals now sit in `safety_incidents` looking like human judgements, and existing scorecards keep derived scores and warnings (M-3). |
| Compliance / privacy | improves | **Agree,** and this is the strongest part of the slice. One qualification: M-1 means the disclosure claim is overstated, and B-1 means a secret still reaches a log on a path the gate does not cover. |

Against `.claude/context/nfr-budget.md`: no new endpoint, no new query in any hot path, no
new payload field, no new synchronous external call. Nothing in the diff moves a budget
number in the wrong direction. Two SQL aggregates removed from a monthly job is the only
measurable change and it is favourable. I did not measure it.

---

## 6 · Compliance verification

Taken from the impact analysis §5 "Compliance obligations discharged". Three outcomes only.

| Obligation | Mechanism in this diff | Test that proves it | Verdict |
|---|---|---|---|
| Purpose limitation (DPDP) — telemetry not used for a performance purpose | Both derivations deleted: `delivery_partner.py:142-152`, `scorecard.py:224-248` | `test_016_a_stats_refresh_does_not_write_safety_incidents`, `test_016_a_scorecard_carries_no_telemetry`, `test_016_the_scoring_code_no_longer_reads_the_telemetry_columns` | **Discharged** for new derivations. **Partial** overall — the outputs already produced from that basis are untouched and uncounted (M-3). |
| FR-H7 — no passive behavioural monitoring as a performance input | Structural: the read is deleted, not disabled by a flag or a warning | the three tests above | **Discharged.** This is a guardrail by structure, which is the right kind. |
| Minimisation — third-party mailbox, customer name, phone and five named businesses out of shipped code | `delivery_settings.py`, and the ten module files | `test_016_no_customer_name_phone_shop_or_mailbox_is_hardcoded`, `test_016_no_bare_email_address_is_hardcoded` — **scoped to ten files only** | **Partial** (M-1). |
| Automated decisions — no increment, tier or written warning from passive telemetry | The derivation feeding `_calculate_composite_score` is gone | covered by the scorecard test | **Discharged** going forward. **Not discharged** for existing records (M-3). |
| Access rights — server-side entitlement check on every entry point | `@requires_feature("vendor")` ×28 | `test_016_every_endpoint_carries_the_gate` + `test_016_the_gate_runs_before_the_body` | **Discharged** at the entitlement layer. Row-level access rights are **not discharged** and are correctly declared phase 2. |
| Fail-closed on alert recipients | `delivery_settings.ops_recipients()` returns `[]` and `send_ops_alert` refuses to send | `test_016_an_unconfigured_tenant_sends_no_ops_alert` — asserts `sendmail` was not called | **Discharged.** Note this is a control *upgraded* to fail-closed, which is the direction we want. |
| Auditability of a refusal (M10) | none | none | **Not discharged**, declared phase 2. |
| Secrets and personal data out of logs | none in this diff | none | **Not discharged** — B-1. |
| Retention / purge of GPS history | none | `test_016_the_raw_tracking_rows_are_kept` deliberately proves the opposite, and says so | **Not discharged**, open question with no owner. |

The four residual risks in the security analysis §9 still have **no named accountable human
and no date**. The analysis itself says "an accepted risk with a name and a date is
governance; these four have neither yet. They need an owner before this slice closes." That
is still true, and only the user can supply the names.

---

## 7 · Before the push

Two things that are not code, and matter more than the code:

1. **Tick `vendor` on every site that should keep it, before the image is swapped.** The
   instant the new code loads, every site provisioned by `deploy/provision_tenant.sh` loses
   the module — including the demo sites. If PPJ is a sales demo of the vendor and driver
   portal, it goes dark. That is a dev-stage action on a dev tenant and therefore the user's
   call, not mine or the engineer's. The analysis flags the same thing and says the engineer
   would check the demo sites first; there is nothing in the commits recording that check.
2. **Know what the push carries.** Local `dev` is `8e86470`, which is six commits of 016 on
   top of twelve commits of 014. Pushing `dev` ships both slices. 014's "only the assigned
   driver may post" is true of one of the two GPS paths (M-2); please do not let the release
   note say it more broadly than that.

Fixes I would fold in now, all small:

- B-1 — drop the OTP and the driver's name from `delivery_assignment.py:36-40`. Two lines.
- M-4 — `has_feature("vendor")` check in the two `get_context` functions. Three lines each.
- m-1 — `vendor_coords` returns `(None, None)` instead of the hub for an unknown vendor.
- m-3 — replace the `TypeError` swallow with an assertion on `__alvoraa_feature__`.

Fixes that can wait, but should be written down with an owner: M-1's deletions, M-3's
decision, and the four unowned residual risks.

---

## 8 · What to delete

Recommending deletion is a review outcome, and there is a clear case here:

- `alvoraa_portal/alvoraa_portal/setup_data.py` — **no callers anywhere.** Dead, and it
  carries three of a real customer's hub mailboxes.
- `alvoraa_portal/alvoraa_portal/demo_seeder.py` and `demo_setup.py` — **no callers
  anywhere.** Together they hold the five named shops, their street addresses, and a set of
  demo passwords. If they are still wanted, they belong in the `demo/` folder, which has the
  `merge=ours` driver precisely so this material never reaches `main`.
- `alvoraa_portal/alvoraa_portal/frontend/` — an unbuilt Vite app with no build reference in
  the repo, whose `Account.jsx` tells the reader to email another company's ops mailbox.
- `app_email` / `author_email` in `alvoraa_portal/alvoraa_portal/hooks.py:5`,
  `alvoraa_portal/setup.py:8`, `alvoraa_goals/alvoraa_goals/hooks.py:5`,
  `alvoraa_goals/setup.py:11` — four lines of metadata pointing at a customer's domain.
- The `frappe.log_error(...)` at `vendor_order.py:333-337`, which logs a success as an error
  and prints the manager email list while doing it.

Nothing in the slice itself should be deleted. It built exactly one new module of 141 lines
with no DocType, no custom field, no migration, no feature flag and no abstraction beyond
what was needed. That is the right size.

---

## 9 · What was done well

Specifically, and worth copying:

- **Reusing `requires_feature` instead of inventing a gate.** Nothing new was built for the
  main change. The decorator already existed, was already tested, and is applied here in the
  same order as in `api/vendor_portal_api.py`. That is Frappe-first and no-over-engineering
  in the same decision.
- **The `ast`-based test that walks every whitelisted function in ten modules and fails if a
  new one arrives ungated.** This is the difference between fixing 28 endpoints and fixing
  the class of problem. It also, deliberately, includes `delivery_tracking` — a module with
  no endpoint today — so the day someone adds one it is checked. That is thinking a year
  ahead for the cost of one line.
- **Failing closed on the ops mailbox, and saying so in the docstring.** The easy answer was
  a "sensible default" address. The chosen answer is silence plus a log line naming only the
  document id, with the reasoning written down: "there is no safe default address". A
  control moved from warn-and-continue to fail-closed, which is the rare direction.
- **Deleting the derivation rather than disabling it.** FR-H7 is now enforced by the absence
  of the SQL, not by a setting somebody can turn back on. And `safety_incidents` was kept
  rather than dropped, with a clear explanation of why a human-recorded incident is a
  different thing from a phone's opinion of someone's braking.
- **Refusing to rewrite history silently.** Leaving existing scorecards as saved, and saying
  in the analysis that correcting them is a separate decision, is the right instinct about
  records that justified a payment.
- **The impact analysis says the uncomfortable thing twice** — that a plan gate is not a
  permission fix, and that pushing `dev` will carry slice 016 along with 014. Both are true,
  both were easy to leave out, and both are what made this review quick.

---

## 10 · Confidence

**High** on the diff itself. I enumerated every whitelisted function in the app with `ast`
(handling the two BOM files), read all ten changed files in full plus `subscription.py`,
`tenant_api.py`, both `www` page controllers, the two portal HTML pages at the relevant
lines, and both test files line by line. I traced every reader of every removed constant and
every changed function, and I confirmed the `doc_events` registration for B-1 in `hooks.py`.

**What I could not verify, and what I would need:**

- **I ran no tests and no linter.** The bench is shared and the task said not to run them.
  Everything I say about test behaviour comes from reading the source, not from output. To
  confirm, I would need the bench free and `bench --site test_site run-tests --app
  alvoraa_portal`.
- **Which sites currently have `features` in their config.** Site configs are not in the
  repo. This decides how many tenants the opt-in flip actually takes the module away from,
  and whether the PPJ demo survives. I would need `bench --site <site> show-config` on each
  site, which is a server action.
- **Whether `frappe.sendmail(recipients=[])` truly returns quietly** in the Frappe version
  running here. The framework source is not vendored in this repo. My reading of m-2 as
  "silent, not a crash" rests on the Frappe queue builder's early return, and the call is
  inside a `try` either way — so the conclusion holds even if I am wrong about the
  mechanism.
- **How the 403 actually renders** to a user on an unentitled tenant. I read the
  `api()` helper and the one modal that parses `_server_messages`; I did not open a browser.
  The finding (M-4) stands on the missing `has_feature` check in `get_context`, not on the
  exact appearance.
- **Whether the security review (06) and the DevOps release readiness (07 §5) exist for this
  slice.** Neither artifact is in `docs/slices/016-portal-api-permissions/`. I ran alongside
  them as the process says, and did not repeat their work — but if they were never run, the
  slice is missing two of its three parallel reviews, and B-1 and M-2 are exactly the kind of
  thing the security review is meant to sign off.
