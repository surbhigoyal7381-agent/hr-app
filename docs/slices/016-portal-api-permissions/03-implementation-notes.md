# Slice 016 — implementation notes (phase 1)

Engineer. 18 September 2026. Built on the local instance only. Nothing pushed,
nothing deployed, no server command run.

Branch `slice/016-portal-api-permissions`, worktree
`.claude/worktrees/016-portal-api-permissions`, based on local `dev` `b7244c8`.

---

## 1 · The short version

Three things were asked for and three things were done.

| # | What | Where |
|---|---|---|
| 1 | All 28 ungated endpoints in the vendor / driver / delivery module now refuse a tenant whose plan does not include it, and `vendor` became opt-in so no tenant gets it by accident | `portal_api.py`, `controllers/*.py`, `subscription.py` |
| 2 | One customer's warehouse name, phone number, five named shops, ops mailbox and company name are out of the source; they come from the site's own config now | new `delivery_settings.py`, six files |
| 3 | Driving telemetry no longer becomes a performance score | `controllers/delivery_partner.py`, `controllers/scorecard.py` |

**The honest caveat, first:** this is an **entitlement** gate, not an ownership
one. On a tenant that does have the vendor feature, all 23 ownership holes in
`00-security-analysis.md` are still open. Phase 1 takes the module away from
tenants that never bought it. Phase 2 decides who may touch which record.

---

## 2 · File by file, and the mechanism for each

| File | Change | Mechanism | Why that one |
|---|---|---|---|
| `alvoraa_portal/subscription.py` | `"opt_in": True` on the `vendor` feature spec | **configure** | The mechanism already existed and is already tested. One key. |
| `alvoraa_portal/portal_api.py` | `@requires_feature("vendor")` on 11 endpoints; warehouse name, phone, hub point and vendor pins read from `delivery_settings` | **reuse + configure** | The decorator is the same one `api/vendor_portal_api.py` has used all along. No new gate was written. |
| `alvoraa_portal/controllers/delivery_assignment.py` | gate on 2 endpoints; two customer-branded email lines | reuse | |
| `alvoraa_portal/controllers/delivery_feedback.py` | gate on 1; two ops alerts now go through `send_ops_alert` | reuse | |
| `alvoraa_portal/controllers/delivery_order.py` | gate on 5; the outbound geocoder `User-Agent` no longer carries a customer's email | reuse | |
| `alvoraa_portal/controllers/delivery_partner.py` | gate on 3; **the telemetry → `safety_incidents` derivation deleted** | **delete** | Nothing replaces it. The field stays for a human to fill. |
| `alvoraa_portal/controllers/rating.py` | gate on 1; one ops alert, one branded line | reuse | |
| `alvoraa_portal/controllers/scorecard.py` | gate on 2; **the GPS safety block deleted**, and the two telemetry-only fields cleared on a regeneration | **delete** | |
| `alvoraa_portal/controllers/vehicle_compliance.py` | gate on 1; the per-record recipient still wins, otherwise the tenant's configured mailbox, otherwise no email | reuse | |
| `alvoraa_portal/controllers/vendor_order.py` | gate on 2; one ops alert, the warehouse-manager fallback list, one subject line and four branded lines | reuse | |
| `alvoraa_portal/controllers/delivery_tracking.py` | no endpoints — untouched, but named in the pin test so a future one is checked | — | |
| **new** `alvoraa_portal/delivery_settings.py` | six small readers over `frappe.conf` | **configure** | No DocType, no custom field, no migration. A site's config is something the tenant cannot edit, which is the right place for this. |
| `tests/test_subscription_access.py` | `vendor` out of the enterprise row of the plan matrix | — | The plan matrix genuinely changed. |
| `tests/test_opt_in_features.py` | `vendor` added to `SHIPPED_OPT_IN` | — | Same. |
| `tests/test_driver_location_014.py` | switches the vendor feature on for itself | — | Those tests are about who may post, not about the plan, and `test_site` is on the starter feature list. |
| **new** `tests/test_portal_module_gate_016.py` | 16 pin tests | — | §5. |

### The site-config keys, all optional

| Key | Default when unset |
|---|---|
| `portal_warehouse_name` | the translated word "Warehouse" |
| `portal_warehouse_phone` | nothing — the page already only draws a Call button when it has a number |
| `portal_ops_name` | the tenant's own company from Global Defaults, then "Operations" |
| `portal_ops_email` | **nothing, and the alert is not sent** |
| `portal_hub_coords` | the point this module has always centred on; it names nobody |
| `portal_vendor_coords` | empty — a vendor pin falls back to the hub |

---

## 3 · What was asked for, and how each is satisfied

| Asked | Satisfied by | Proof |
|---|---|---|
| `@requires_feature("vendor")` on all the unprotected endpoints (28 counted) | 28 added, exactly the count in the analysis | `test_016_every_endpoint_carries_the_gate` walks all ten modules and found 28 |
| Follow the existing pattern in `vendor_portal_api.py` and `subscription.py` | Same decorator, same order, same import | `test_016_the_gate_runs_before_the_body` |
| Mark `vendor` so tenants that did not buy it cannot reach any of it | `"opt_in": True` | `test_016_vendor_is_opt_in`, `test_016_a_site_with_no_feature_list_does_not_get_vendor`, `test_016_no_plan_bundle_hands_it_over_on_its_own` |
| Remove the warehouse name, phone and the five named shops | Gone; read from config | `test_016_no_customer_name_phone_shop_or_mailbox_is_hardcoded` |
| Do not break the demo flow | The map still centres on the hub; the Call button degrades to absent; email goes only where a tenant configures it | §6 — one demo caveat, honestly stated |
| Grep for other real-looking values and report | §4 | — |
| Stop telemetry feeding a performance score | Both derivations deleted | `test_016_a_stats_refresh_does_not_write_safety_incidents`, `test_016_a_scorecard_carries_no_telemetry`, `test_016_the_scoring_code_no_longer_reads_the_telemetry_columns` |
| Keep the raw `Vehicle Tracking` rows | Untouched | `test_016_the_raw_tracking_rows_are_kept` |
| Say exactly what is disabled and what a customer notices | §6 | — |

---

## 4 · What the wider grep found

The analysis listed a warehouse name, a phone number, five shops and
`ops@gracedrinks.in` at three lines. Grepping the whole module found more. All of
it is fixed except the last row.

| Value | Count | Where | Now |
|---|---|---|---|
| `Grace` + ` Warehouse` | 1 | `portal_api.py` | config |
| `987…099` (phone, masked here) | 1 | `portal_api.py` | config |
| Five named shops with coordinates | 5 | `portal_api.py` | deleted; optional config map |
| `ops@` + `gracedrinks.in` | **6, in five files** — not three | `delivery_feedback.py` ×2, `rating.py`, `vehicle_compliance.py`, `vendor_order.py` ×2 | config; no email when unset |
| The same address in an outbound HTTP `User-Agent` | 1 | `delivery_order.py` | `AlvoraaPortal/1.0` |
| `Grace Drinks Operations` / `Grace Operations System` signed in emails | **6** | `delivery_assignment.py` ×1, `rating.py` ×1, `vendor_order.py` ×4 | the tenant's own name |
| "Your `Grace Drinks` order will arrive…" in a vendor email | 1 | `delivery_assignment.py` | "Your order will arrive…" |
| `[Grace Vendor Portal]` email subject | 1 | `vendor_order.py` | `[Vendor Portal]` |

**The email one was not cosmetic.** On any tenant other than the original
customer, a delivery complaint, a low rating, a compliance expiry and a new order
under review — each carrying a customer name, address or order value — were being
emailed to that one company's mailbox. That is a third-party disclosure on every
site the app is installed on, which is every site.

**Found and not fixed, on purpose:**

- `alvoraa_portal/demo_seeder.py` still holds the five shop names, their street
  addresses and their record ids, and `demo_setup.py` holds similar demo data.
  They are demo seeding scripts, not the module, and slice 015 is already working
  in that area (`demo_setup.py` is on its claim list). Changing them here would
  clash. **It should be picked up — the five real businesses are still in a
  public repository through those files.**
- The `www/vendor-portal.html` and `www/driver-portal.html` pages were not read
  for customer branding. Out of scope for the three approved items.

---

## 5 · Tests

New file `alvoraa_portal/tests/test_portal_module_gate_016.py`, 16 tests in three
classes — one class per approved item.

**The plan gate**

- `test_016_every_endpoint_carries_the_gate` — parses every module with `ast` and
  fails if any `@frappe.whitelist` function lacks the decorator. This is the one
  that stops the next endpoint being forgotten.
- `test_016_the_gate_runs_before_the_body` — `@frappe.whitelist()` must be above
  the gate, or the registry would hold the ungated function.
- `test_016_a_tenant_without_the_feature_is_refused_on_every_one` — table-driven
  over all 28, starter plan, `PermissionError` each time.
- `test_016_vendor_is_opt_in`, `test_016_a_site_with_no_feature_list_does_not_get_vendor`,
  `test_016_no_plan_bundle_hands_it_over_on_its_own`,
  `test_016_a_tenant_that_has_it_is_not_refused_by_the_plan` — the last one
  matters most: switching it on must still work, or this is a deletion dressed up
  as a gate.

**The hardcoded values**

- `test_016_no_customer_name_phone_shop_or_mailbox_is_hardcoded` — greps the
  module's own source for all nine strings.
- `test_016_no_bare_email_address_is_hardcoded` — any literal address at all,
  because the next one will be the wrong somebody's too.
- `test_016_the_settings_come_from_site_config` and
  `test_016_an_unconfigured_tenant_sends_no_ops_alert` — the fail-closed
  behaviour, with `frappe.sendmail` mocked and asserted not called.

**The telemetry**

- `test_016_a_stats_refresh_does_not_write_safety_incidents`
- `test_016_a_recorded_incident_survives_a_stats_refresh` — a person's judgement
  is not passive monitoring, and a refresh must not wipe it either.
- `test_016_a_scorecard_carries_no_telemetry`
- `test_016_the_scoring_code_no_longer_reads_the_telemetry_columns` — the SQL is
  gone, not merely unused.
- `test_016_the_raw_tracking_rows_are_kept` — we stopped scoring it, not storing
  it, and the test says which question this slice answered.

### Commands run, and what they said

All on `hrlocal-bench`, site `test_site`, one run at a time, with
`pgrep -af run-tests` checked first and the work board marked.

| Command | Result |
|---|---|
| `bench --site test_site run-tests --app alvoraa_portal --module …test_portal_module_gate_016` | 16 tests, **OK** (first attempt: 1 failure — my own comment contained `SUM(harsh_braking)`, so the grep test caught it; the test now ignores comment lines) |
| `… --module …test_endpoint_entitlement` | 13 tests, OK |
| `… --module …test_subscription` | 32 tests, OK |
| `… --module …test_subscription_access` | 56 tests, OK |
| `… --module …test_opt_in_features` | 11 tests, OK (first attempt: 4 failures, all because `SHIPPED_OPT_IN` did not yet name `vendor`) |
| `… --module …test_driver_location_014` | 5 tests, OK |
| `… --module …test_vendor_order` | 4 tests, OK (2 skipped, both pre-existing KI-2 skips) |
| `… --module …test_integration` | 1 test, OK (1 skipped, pre-existing KI-2) |
| `… --module …test_subscription_record` | 2 tests, OK |
| `bench --site test_site run-tests --app alvoraa_portal` (whole app) | see §9 |

`python -m py_compile` on all eleven changed source files: clean.

---

## 6 · What a tenant would notice — and exactly what is disabled

### Switched off

**For a tenant whose `site_config.json` does not name `vendor`:** the whole
vendor and driver module. `/vendor-portal` and `/driver-portal` still open, and
then every action fails with "Vendor & Driver Portal is not included in your
plan." That includes tenants that were only ever entitled by the fallback — which
is most of them, because `provision_tenant.sh` never wrote a feature list.
Switching it back on is one tick in the admin console.

**Alert emails with no configured mailbox:** low ratings, issue escalations,
vehicle compliance expiry, and the "new order under review" note are not sent.
A line goes to the error log naming the document — never its contents.

**Telemetry scoring, in precise terms.** These stop being written:

| Field | On | Was derived from |
|---|---|---|
| `safety_incidents` | Delivery Partner | `SUM(harsh_braking) + SUM(speeding_alert)` |
| `harsh_driving_detected` | Delivery Performance Scorecard | `SUM(harsh_braking) + SUM(harsh_acceleration)` |
| `speeding_incidents` | Delivery Performance Scorecard | `SUM(speeding_alert)` |
| `safety_incidents` | Delivery Performance Scorecard | the two above added together |

Everything downstream still works the same way — `safety_score`,
`overall_delivery_score`, `performance_level`, `recommended_increment`,
`promotion_eligible` and the automatic written warning are untouched. They just
no longer have a telemetry number feeding them.

### Still on

- The raw `Vehicle Tracking` rows, including `speeding_alert`, which
  `update_driver_location` still sets on each position. Retention is a separate
  question for counsel and is not touched here.
- `safety_incidents` as a field and as part of the score, when a person records
  one. That is a human judgement, not passive monitoring.
- Existing scorecards keep the numbers they were saved with. Nothing is
  recomputed backwards, because rewriting a record that justified a commission
  payment would be worse than leaving it. **If the history should be corrected,
  that is a patch and a separate decision.**

### What people will see

| Who | What changes |
|---|---|
| A delivery manager | "Harsh driving detected" and "Speeding incidents" read 0 on new scorecards. Next month's overall scores are **higher** than last month's for any driver who previously lost safety points. On a regenerated old scorecard, those two fields are cleared. |
| A driver | Their score is no longer moved by how their phone judged their driving. |
| A vendor | On an entitled tenant: nothing, unless the tenant has not configured a warehouse phone, in which case the Call button on an order is gone. Map pins fall back to the hub until coordinates are configured. |
| Whoever read the ops alerts | They arrive at `portal_ops_email` or not at all. |

### The demo caveat

The demo sites have no `features` key or a starter one, so after this change the
demo vendor and driver flow needs `vendor` in the site config. **Changing a
site's config is a stage action, so it is Surbhi's call, not mine.** I did not
touch any site config. The demo map still draws because the hub point is kept;
the five shop pins are gone until `portal_vendor_coords` is set.

---

## 7 · The seven non-functional dimensions, against the code actually written

| Dimension | Before → after | Verdict |
|---|---|---|
| **Performance** | 28 endpoints ran unbounded `get_all` and raw SQL for anyone → on an unentitled tenant they short-circuit on one `frappe.conf` dict lookup. Two `SUM()` aggregates over `tabVehicle Tracking` are deleted from the monthly scorecard job. Query count on an entitled tenant is unchanged, endpoint for endpoint. | **improves** |
| **Scalability** | The deleted aggregates scanned every tracking row per partner per month — the fastest-growing table in the module. Nothing new grows with headcount. | **improves** |
| **Security** | 28 endpoints gained a server-side refusal. `ignore_permissions` count unchanged — I removed none and added none, because removing them safely needs the ownership scoping that is phase 2. **The 23 ownership holes are still open on an entitled tenant.** | **improves, incompletely** |
| **Reliability** | The decorator adds no new failure mode. The one real change is the ops-email fallback: a tenant that never configures a mailbox stops receiving those alerts. Deliberate, logged, and named here. Both derivations removed were read-only aggregates; removing them cannot half-write anything. | **neutral** |
| **Maintainability** | Six copies of a literal email address became one lookup; four copies of a company name became one. One decorator line per endpoint. One new 120-line module with a docstring that says why it exists. | **improves** |
| **Data integrity** | Telemetry no longer rewrites a person's performance fields behind their back. Existing scorecards are left exactly as saved. The regeneration path clears only the two fields nothing but telemetry ever wrote, and deliberately does not clear `safety_incidents`, which a person may have filled. | **improves** |
| **Compliance / privacy** | A named third party's mailbox is out of six outbound-email paths and one HTTP header. Five named businesses, a warehouse name and a phone number are out of a public repository. Passive driving behaviour no longer becomes a performance record about a person (FR-H7, and purpose limitation). | **improves** |

Also: **accessibility** neutral (no UI change, though an unentitled tenant now
sees a raw error rather than a clean panel — §10); **upgrade-safety** neutral and
safe (everything in our own app, no fixture, no patch, no migration);
**internationalisation** improves slightly (the refusal message is already
translated, and the new "Warehouse" fallback is wrapped).

### Compliance obligations discharged, and the mechanism

| Obligation | Mechanism | Not just an intention because |
|---|---|---|
| Purpose limitation | The telemetry read is deleted | `test_016_the_scoring_code_no_longer_reads_the_telemetry_columns` |
| Minimisation | Customer details out of shipped code | `test_016_no_customer_name_phone_shop_or_mailbox_is_hardcoded` |
| Automated decisions | No score, increment or automatic warning can be produced from passive telemetry | `test_016_a_scorecard_carries_no_telemetry` |
| Access rights | Server-side entitlement check on every endpoint | `test_016_a_tenant_without_the_feature_is_refused_on_every_one` |

**Not discharged in phase 1, and on the record:** auditability (no refusal log in
this module — M10), breach readiness (no affected-record query), and row-level
access rights. All three are phase 2.

---

## 8 · NFR notes

- **Query counts.** Unchanged per call on an entitled tenant. Zero on an
  unentitled one. The monthly scorecard job loses two `SUM()` queries per partner
  per run; on a 50-driver hub that is 100 fewer full scans of `tabVehicle
  Tracking` a month.
- **Indexes.** None added. Nothing new is filtered or joined.
- **Background jobs.** `generate_monthly_scorecards` and
  `update_delivery_tracking` are called server-side, not through the whitelist,
  so the plan gate does not touch them. That is deliberate: a scheduled job has
  no session and gating it would break it. It also means **the scheduler still
  runs for unentitled tenants**, which is a phase-2 question, not a leak — it
  writes the tenant's own records and returns nothing to anyone.
- **Permission enforcement points.** 28 whitelisted endpoints, at the decorator.
- **Sensitive fields touched.** None read or written that were not before. The
  slice *removes* three person-level derived fields and stops one mailbox
  receiving customer names and addresses.
- **Fallbacks.** Warehouse name → a word. Phone → no button. Ops name → the
  tenant's own company. Hub point → the existing constant. Vendor pin → the hub.
  Ops email → **no email**, which is the one that fails closed rather than open.

---

## 9 · What else moved while I worked

- `git fetch origin` at the start and again before the merge into local `dev`:
  **nothing came in.** `origin/dev` stayed at `9138251` throughout.
- Local `dev` was 12 commits ahead of `origin/dev` when I started — all slice
  014, none of mine. My six commits sit on top of them.
- **No conflicts.** No file I touched is claimed by `slice/015-repo-hygiene`,
  `slice/013-mobile-app` or `slice/ci-fix-9138251`. I did not go near `ci.yml`,
  `hooks.py`, `patches.txt`, any DocType JSON, `hrms-employee.html`, `demo/` or
  `deploy/`.
- Other sessions' uncommitted work in the main checkout was left alone; I staged
  by path every time. The one thing I removed was an untracked copy of
  `docs/slices/016-portal-api-permissions/00-security-analysis.md` that blocked
  the fast-forward. I checked the hashes first: it was byte-identical to the copy
  I had committed on the slice branch (`5fbbb9a…` both), so nothing was lost.

---

## 10 · Gaps, shortcuts and what I would fix with more time

Declared, not hidden.

1. **Ownership is still wide open on an entitled tenant.** That is phase 2 by
   design, but it is the single most important thing to say about this slice.
2. **An unentitled tenant sees a raw error, not a clean "not in your plan"
   panel.** The pages do not check entitlement before rendering. Not a
   regression — before, there was no refusal at all — but scruffy, and a
   five-line fix in phase 2.
3. **The demo seeding scripts still name the five real shops**, with street
   addresses and record ids, in a public repository. Left alone to avoid clashing
   with slice 015, which is in that area. Someone should pick it up.
4. **No refusal is logged.** M10 in the analysis. The gate denies silently, so we
   still would not know an attempt had happened.
5. **Existing scorecards keep their telemetry-derived numbers.** A patch could
   clear `harsh_driving_detected` and `speeding_incidents` on historic rows, but
   that rewrites records that justified payments, so it needs a decision first.
6. **`portal_vendor_coords` is a site-config map, which is a slightly odd place
   for coordinates.** The proper home is latitude and longitude fields on the
   `Vendor` doctype — but that is a schema change, and phase 1 was meant to be
   small. If the module survives the "do we want this at all" question, do it
   properly then.
7. **I did not check the two portal HTML pages for customer branding.** Outside
   the three approved items.
