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

---

## KI-4 · Half-day leave is broken in the hrms fork — wrong `is_holiday` signature ✅ FIXED

**Severity was:** High — the feature did not work at all. **Status:** Fixed 2026-08-20, with
sign-off, since the fix edits vendored HR code. Kept for the record.

`leave_application.py` line 23 imports:

```python
from hrms.hr.doctype.employee.employee import get_holiday_list_for_employee, is_holiday
```

That `is_holiday` is declared as:

```python
def is_holiday(holiday_list, date=None, daily_wages_applicable_for_holiday=False, raise_exception=True)
```

but it is called with an `employee` keyword in **two** places:

| Line | Function | Effect |
|---|---|---|
| 916 | `validate_half_day_date` | validating a half-day application raises |
| 985 | `get_number_of_leave_days` | counting days for a half-day raises |

Both raise `TypeError: is_holiday() got an unexpected keyword argument 'employee'`, so any
half-day leave fails — through the portal, the desk, or the API.

This is a half-finished refactor. The fork carries **two** holiday systems: the old
`Employee.holiday_list` field, and a newer submitted `Holiday List Assignment` doctype
resolved by `hrms/utils/holiday_list.py`. The call sites were updated to the employee-based
signature; the import was not.

**Proposed fix** — resolve the list, then call with it:

```python
from hrms.utils.holiday_list import get_holiday_list_for_employee   # the as_on-aware one

hl = holiday_list or get_holiday_list_for_employee(
    employee, raise_exception=False, as_on=half_day_date
)
... and not is_holiday(hl, date=half_day_date)
```

`get_number_of_leave_days` already accepts a `holiday_list` argument, so it should be
preferred when supplied rather than re-resolved.

**Applied**, but not as first proposed. Rather than re-resolving the holiday list, both call
sites now use `get_holiday_dates_between_range(employee, date, date, skip_weekly_offs=True)` —
the helper `get_holidays()` already uses. That way the half-day check and the day count read
holidays through the same path and cannot disagree. `skip_weekly_offs=True` preserves the old
meaning: a weekly off is not "a holiday" for this purpose. `is_holiday` is no longer imported
here; `get_holiday_list_for_employee` still is, and is used elsewhere in the file.

Covered by three tests: the preview arithmetic, an actual half-day application (0.5 days), and
a half-day on a holiday still being rejected — two distinct call sites, so a passing preview
alone would not have proved it.

**What could not be verified:** hrms's own `test_leave_application` module does not run on a
fresh site — discovery fails with `Mode of Payment`, and it fails identically with the original
file, so it is pre-existing and unrelated. Also untested: the weekly-off branch, because the
fixture holiday list deliberately contains no weekly offs.

**Also worth knowing:** setting `Employee.holiday_list` alone does nothing in this version.
Holidays resolve through a **submitted** `Holiday List Assignment`. The test fixtures create
one — see `alvoraa_portal/tests/leave_fixtures.py`.

