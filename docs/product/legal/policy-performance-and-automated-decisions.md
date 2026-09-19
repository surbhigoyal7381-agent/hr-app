# Employee performance and automated HR decisions policy

**Status:** approved by Surbhi 2026-09-18, on legal advice. Authoritative for the product.
**Legal verdict received:** "Needs optimisation" — processing is legitimate use for employment, but disciplinary flags and scorecards may **not** be kept indefinitely, and because the system makes automated decisions affecting pay and employment status, employees must be able to see the underlying data and raise a grievance about it.

## Purpose and lawful basis
Performance data is processed under the **legitimate use of employment**, to evaluate staff fairly, manage compensation, and enforce operational standards using objective metrics.

## Data collected
On-time percentage, customer ratings, **human-recorded** safety incidents, and attendance records.

## Automated processing and employee rights
- The software generates **automated pay-increment recommendations and written warnings** for performance tiering.
- **Right to access and correction:** an employee may request a summary of the underlying data behind these automated decisions, and may use the internal **grievance redressal** mechanism to challenge inaccuracies.

## Retention and erasure
| Stage | Rule |
|---|---|
| During employment | Scorecards, automated warnings and appraisal ratings are retained |
| After exit (termination or resignation) | **6 months only**, to resolve full-and-final settlement queries or labour disputes |
| After the 6-month buffer | **Automatic permanent erasure.** Indefinite soft deletion is prohibited |

## What this changes in the code (gap list, 2026-09-18)
1. No post-employment deletion job exists for scorecards, warnings, appraisal ratings or review copies. Build it: 6 months after the relieving date, hard delete.
2. Automated warnings and `recommended_increment` still derive partly from **driver telemetry**, which the driver policy now prohibits. Only on-time %, customer ratings, human-recorded incidents and attendance may feed them.
3. No employee-facing "the data behind this decision" summary and no grievance route in the portal — both are now required.
4. Slice 016 recorded "keep existing scorecard telemetry values, stop counting them". Revisit: values derived from prohibited telemetry should be cleared, not kept.
5. Soft-delete/cancel patterns must be checked; the policy forbids indefinite soft deletion.
