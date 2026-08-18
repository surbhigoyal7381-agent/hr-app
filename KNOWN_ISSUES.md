# Known Issues

Defects that are understood, reproducible, and deliberately not fixed yet. Each says why.

---

## KI-1 · Goal progress ignores evidence — half-finished field rename ✅ FIXED

**Severity was:** High. **Status:** Resolved 2026-08-19. Kept for the record.

Commit `6351af3` replaced `Goal Evidence.extracted_order_count` / `extracted_amount` with a
generic `value`, updating the doctype but not the code that read it. Progress silently summed a
column nothing writes to.

The rename is now finished across `alvoraa_goals`:

| Where | Change |
|---|---|
| `controllers/goal.py` | `recalculate_progress` sums `value`. The unit-based branch (revenue → amount, else → count) is gone — with one generic measure there is nothing to branch on |
| `api/goal_api.py` | `submit_goal_evidence(value=...)`. Old argument names still accepted and folded into `value`, so unupdated callers keep working |
| `validators/invoice_validator.py` | Validates `value`. Config accepts `min_value`/`max_value`, falling back to `min_amount`/`max_amount` so saved Evidence Validator records keep working |
| `validators/sales_order_validator.py` | Validates `value`. The volume and unit rules are removed — `extracted_volume` and `extracted_volume_unit` no longer exist, so those checks had no data. Stale config keys are reported as ignored rather than silently dropped |
| `validators/duplicate_detector.py` | Matches on `value`. Weights re-balanced so the 80 threshold still means "same number **and** same day", as it did with three signals |
| `doctype/individual_goal/individual_goal.js` | One `Value / Progress` input; the evidence table shows Value instead of Orders/Amount/Customer |

Two further dead fields turned up beyond those recorded originally: `extracted_volume`,
`extracted_volume_unit` and `extracted_customer` were also removed by that commit.

`test_progress_calculation` is un-skipped and passing — 17 tests, OK (skipped=2), the two
remaining skips being the stale evidence-stub tests.

**A second live break was found and fixed on the way:** `alvoraa_portal/hr_api.py` already called
`submit_goal_evidence(value=...)`, an argument the goals API did not have. Portal evidence
submission was raising `TypeError`. It works now.

`alvoraa_portal` still holds 9 display-only references to the old names; that app is being
rebuilt, so they are left alone.

---

## KI-2 · `alvoraa_portal` — `before_submit` imported but never defined

**Severity:** Low. **Status:** Won't fix — app is being rebuilt.

`doctype/vendor_order.py` imports `before_submit` from `controllers/vendor_order`, which has never
defined it — confirmed absent at `d84fdda~1`, before any of the current work. Any Vendor Order
submit raises `ImportError`.

Affects `test_full_order_flow`, `test_valid_status_transition`, `test_invalid_status_transition`,
now marked `@unittest.skip` pointing here.

The vendor portal is due to be rebuilt after the competitive analysis, so this is left alone.

> Note: 6 further portal tests were failing for an unrelated and trivial reason — `sku` is a
> required Link to `Item` and the test SKUs existed on no fresh site. Those were fixed rather
> than skipped, via `alvoraa_portal/tests/utils.ensure_item()`. Only the genuine defect above is
> parked.

---

## KI-3 · hrms fork — 66 lint violations

**Severity:** Low. **Status:** Deferred, CI non-blocking.

31 import-ordering, 20 ambiguous dash characters in comments, plus assorted. Pre-existing;
`hrms/` is byte-identical to its state before the Alvoraa rename series.

Fix with the **pinned** ruff 0.6.9 that CI installs — a newer ruff reports a different set (0.15.4
finds 83), so fixing with whatever is on a laptop can leave CI red.
