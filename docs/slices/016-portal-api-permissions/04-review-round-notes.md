# Slice 016 — the review round (18 September 2026)

Both reviews came back before the push: the code review said **ship with fixes**, the
security review said **pass with fixes**. Their reports are in this folder as
`05-review.md` and `06-security-review.md`. This document says what I changed, what I
left, and why. It continues `03-implementation-notes.md`.

---

## 1 · Fixed

| # | Finding | What I did | Commit |
|---|---|---|---|
| B-1 / R4 | A delivery OTP and a named driver went into the Error Log on every assignment | The log line now says only that an assignment was created and an OTP was issued. The record name is enough for a person to open it and read the OTP from the field. **The plan gate never covered this** — it is an `after_insert` doc_event, so it fires on a desk save and on `/api/resource` too, on any tenant | `72bb366` |
| M-1 / M1 | "One customer's details are out of the source" was true of ten files only | Cleared from seven more: the publisher and author mailboxes in both apps' `hooks.py` and `setup.py`, three hub mailboxes in `setup_data.py`, a line in the unused front end, the company name in a DocType field description and in a test fallback, and the five named shops with their street addresses in `demo_seeder.py` | `afbc30d` |
| M1 | `scheduled_jobs.py:57` told every tenant's customer another company's name | One line. The same sentence that was already fixed in `delivery_assignment.py`, in a second copy | `506d34e` |
| M3 / R9 | Switching the module off stopped the doors, not the letters | `if not has_feature("vendor"): return` at the top of the four scheduled jobs. Two of them email customers and drivers | `506d34e` |
| M-4 / Mi1 | `/vendor-portal` and `/driver-portal` still opened on a tenant without the feature, then failed call by call | Both `get_context` functions raise `DoesNotExistError` — a 404. A broken screen advertising a product they were never sold is worse than no page | `6e02997` |
| m-1 | Every vendor pin landed on top of the warehouse marker | `vendor_coords` returns `(None, None)`, which is the page's existing no-position path | `6e02997` |
| M2 / m-3 | The refusal test could not fail: `except TypeError: raise PermissionError` turned a missing-argument error into the very one it was asserting, for 25 of the 28 | It builds a real argument list from `inspect.signature`. A second test checks the arity, so the first cannot quietly go back to proving nothing | `afc6b05` |
| M1 | The customer-details scan read ten files | It walks every `.py`, `.js`, `.jsx`, `.vue`, `.html`, `.json` and `.md` in the app. Two files are skipped, each with its reason in the code. The e-mail scan has a named allow-list now, so a placeholder or a test fixture does not fail it and a real address does | `afc6b05` |
| m-2 | The warehouse-manager notice could go nowhere, silently | Already fixed in `4809c11` before the review landed: an empty recipient list writes a log line naming the order and skips the send | `4809c11` |

## 2 · Not fixed, and why

| # | Finding | Decision |
|---|---|---|
| M-1 (part) | `demo_setup.py` still holds the five shop names and addresses | **Slice 015 owns that file** and has it open with eleven commits on it. Editing it here would clash. The scan skips it by name with the reason written in the code. **Slice 015 should clear it** — the names are in a public repository. |
| M-2, 014 findings | `update_gps_location`, `get_delivery_route`, `get_order_live_location` and its fallback have no ownership check | Phase 2. See §3 — they are **gated, not fixed**. |
| M-3 / R6 | Existing scorecards keep scores, increments and auto-issued warnings derived from telemetry | See §4. Needs a count and a decision, not code. Count is zero. |
| m-4 | Regeneration clears a manually typed `harsh_driving_detected` | Left. Both fields only ever came from telemetry and the comment says so. Hiding them on the form is a UI change nobody asked for. |
| m-5 | The admin console's reverse label map is missing several feature keys | Pre-existing, in `alvoraa-admin.html`, outside this slice's claim. Worth its own small slice — and it matters more now that the console is the only way anyone gets this portal. |
| Mi2 | Turning the feature off revokes no vendor account and no session | Left deliberately. The gate is checked per call, so an existing session gains nothing. But "off" is not "revoked", and a security questionnaire will ask which one it is. That is a product decision. |
| Mi4, Mi5 | Realtime broadcast to the site room; proof-of-delivery accepts any file path | Phase 2. Both gated. |
| — | `support@kinexus.in` in `auth.py`, `tenant_api.py` and the login page | **Allow-listed in the scan, not removed.** It is our own support address, not a customer's. Changing what a user is told to write to is a product decision, not a tidy-up. |

## 3 · Slice 014's driver-location findings are **gated, not fixed**

Said plainly, because the temptation to tick them is real and because 014 and 016 go to
`dev` in the same push.

| Finding | State |
|---|---|
| `portal_api.get_delivery_route` (`:383`) — any logged-in user reads a driver's GPS trail | **Open.** Refuses when the feature is off. No ownership check. |
| `portal_api.get_order_live_location` (`:105`) — the same, plus speed and heading | **Open.** Same. |
| The demo fallback at `portal_api.py:155-172` — an invented order id still returns the most recently moved driver's name and live position | **Open, deliberately deferred.** There is now a comment naming it as finding B3 and pointing at phase 2. A comment is honest; it is not a control. |
| `delivery_assignment.update_gps_location` (`:191`) — any logged-in user writes a fake position to any assignment and can make a customer's phone buzz | **Open.** Gated only. No ownership check, no rate limit. |

In one sentence: **on any tenant where the portal is switched on, a curious colleague can
still watch a named driver move.** Slice 014's release note must not say the
driver-location hole is closed without that qualification.

What 016 *did* do for 014: `update_driver_location` keeps its owner check, keeps 014's
`methods=["POST"]` restriction, and now sits behind an entitlement gate as well. That is
strictly stronger. It is one of two GPS paths.

## 4 · The telemetry already written

Nothing in this slice recomputes or deletes what the old derivation produced. On an
existing scorecard that means `harsh_driving_detected`, `speeding_incidents` and
`safety_incidents`, plus everything downstream of them: `safety_score`,
`overall_delivery_score`, `performance_level`, `recommended_increment`,
`promotion_eligible`, and at the Critical tier an automatically issued **written warning**.

The count is one query:

```
frappe.db.count("Delivery Performance Scorecard", {"harsh_driving_detected": [">", 0]})
```

**Measured on `test_site`: 0.** The security review measured the dev stack independently
and found **0 rows in all nine vendor and delivery tables on every site**. So there is
nothing to remediate today.

**Recommendation, for the user to accept or change:** keep the existing rows exactly as
saved, stop counting them as evidence of anything, and write that down. Rewriting a record
that justified a payment is worse than leaving it — and there are no records. If the module
is ever switched on for a live tenant, revisit this **before** the first scorecard is
generated, not after.

## 5 · The privacy gap both reviewers led with

**A photograph of a face is deleted after 90 days. A minute-by-minute movement history of
the same person is kept for ever.**

| Object | Retention rule |
|---|---|
| Field check-in photo | 90 days, configurable, `0` means keep, a daily purge job, and a legal-hold flag on the record (`field_checkin.py:643-750`, wired at `hooks.py:186`) |
| `Vehicle Tracking` — a driver's continuous location, speed and heading | **No rule. No purge job. No config key.** |
| `Delivery Tracking` child rows | **No rule.** |

All nine vendor and delivery tables are **empty on every dev site today**, so nothing is at
risk this minute. That protection ends at the first live tenant, not at a date of our
choosing.

**This blocks the module for a real customer.** The check-in purge job is a working pattern
to copy and copying it is about half a day. But the prior question is for counsel and
engineering cannot answer it:

> On what legal basis do we process a driver's continuous location, for how long may we
> keep it, and what must the driver be told before the first point is recorded?

Ask it before the first customer, not after.

One related thing the slice did **not** stop: `portal_api.update_driver_location` still
writes `speeding_alert = 1 if speed > 60` onto each `Vehicle Tracking` row. The scoring is
gone, which was the FR-H7 breach. The judgement is still being recorded about a named
person, with no purpose tag and no retention rule.

## 6 · Release notes

- **No patch, no `patches.txt` entry, no migration, no fixture, no new dependency.**
  Everything reads `frappe.conf` at call time.
- **One DocType JSON changed**, and only a field *description* on `Delivery Partner` that
  named the customer. No field added, removed or retyped. A migrate would refresh the help
  text in the desk; nothing depends on it.
- **Tick `vendor` on every site that should keep the portal *before* the image swap.** The
  flip takes effect the instant the new code loads, so there is no window to do it
  afterwards without a gap. Every site provisioned by `deploy/provision_tenant.sh` loses
  the module at the swap, **including the demo sites**. If PPJ demonstrates the vendor and
  driver portal, it goes dark.
- **The opt-in flip changes nothing on the two dev sites that matter.** The security review
  measured them: `dev.alvoraa.co` and `ppj.dev.alvoraa.co` both name `vendor` explicitly in
  `features`, and an explicit list beats the default by design. Every open finding in this
  module stays live on those two sites unless `vendor` is removed from their config. Both
  are empty of data, so removing it costs nothing. **That is a dev-stage decision for
  Surbhi, not mine, and I have not touched any site config.**
- **A push of local `dev` carries slice 014 and slice 016 together.** See §3 for the
  sentence 014's note must not say unqualified.
- **Rollback** is the previous image, plus putting `vendor` back into a site's `features`
  if it was removed. There are no data changes to undo.

## 7 · Residual risks that still have no owner

The security review lists eleven (`06-security-review.md` §8) and the earlier analysis four.
**An accepted risk with a name and a date is governance; these have neither.** The two that
need an answer soonest:

1. **R2** — the two dev sites keep the feature, so every open finding stays live on them
   after this push. A decision for today, not for the slice that closes phase 2.
2. **R5 / R11** — no retention rule for driver location, and no answer from counsel on the
   legal basis. This blocks a live customer.

Only the user can supply the names and the dates.
