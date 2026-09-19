# Driver location and telemetry tracking policy

**Status:** approved by Surbhi 2026-09-18, on legal advice. This is the authoritative rule for the product; code and slices follow it.
**Legal verdict received:** "Highly compliant" — the retention ladder satisfies DPDP s.8 storage limitation, and shift-only tracking with a visible indicator and upfront notice mitigates off-hours monitoring risk.

## Purpose and lawful basis
Location data is processed under the **legitimate use of employment**, strictly to ensure delivery efficiency, process payroll, and safeguard organisational assets.

## Data collected
GPS coordinates, timestamps, and active delivery status.
**Prohibited:** device sensor telemetry for driving behaviour (harsh braking, speeding, phone handling). It must be **technically disabled**, not merely unused.

## Operational safeguards
- **Shift-bound tracking:** only while an active delivery is assigned and open.
- **Off-hours privacy:** the app halts tracking and the **server rejects connections** outside designated working hours.
- **Transparency:** a persistent visual indicator on the driver's device whenever tracking is active.

## Retention and erasure
| Data | Kept | Then |
|---|---|---|
| Minute-by-minute GPS trail | **30 days** from the delivery date | automatically erased |
| Per-delivery summary (total distance, time) | **12 months**, for payroll and billing reconciliation only | automatic permanent hard deletion |

No indefinite retention. No soft deletion.

## What this changes in the code (gap list, 2026-09-18)
1. `portal_api.update_driver_location` still stores `speed`, `heading` and `speeding_alert` — **behaviour telemetry, now prohibited**. Stop collecting and storing them; drop or stop writing the fields.
2. No retention exists for `Vehicle Tracking`: no setting, no purge job, no summary table. Build the 30-day purge, the 12-month summary, and the hard delete.
3. No off-hours rule exists on the server; any assigned delivery accepts positions at any hour, and posting continues after Delivered/Cancelled (slice 014 m3).
4. No persistent indicator in the driver page.
5. Visibility is being narrowed to the driver, their manager, HR and leadership (slice 016 phase 2 decision, same day).

---

## Amendment (Surbhi, 2026-09-18): telemetry is kept, for a limited period

**Decision:** we do **not** stop collecting speed, direction and the speeding flag for now. They stay, under the same limited retention as the rest of the location data (30 days detailed, then a 12-month summary, then hard deletion).

**⚠ This differs from the policy text above**, which says behaviour telemetry is "strictly prohibited and technically disabled". Two things follow, and they must not be lost:

1. **The policy text and the lawyer's verdict must be re-checked.** The "highly compliant" verdict was given on a policy that banned behaviour telemetry. Keeping it is a different position, so the lawyer should confirm it before the first customer. Until then, treat the ban as *not* in force and this amendment as the current rule.
2. **The mitigation that makes it defensible must hold:** behaviour telemetry may **not** drive any automated decision about a person — no scoring, no automated written warnings, no pay recommendations (slice 016 already removed the scoring path; the performance policy allows only on-time %, customer ratings, human-recorded incidents and attendance). It is kept for delivery efficiency, payroll and asset safeguarding only, is shift-bound, is visible to the driver, and is erased on the schedule above.

Everything else in this policy stands and is approved for build: the 30-day / 12-month / hard-delete ladder, the off-hours rule (server rejects positions outside working hours and after a delivery is Delivered or Cancelled), the persistent on-screen indicator while tracking, and visibility limited to the driver, their manager, HR and leadership.
