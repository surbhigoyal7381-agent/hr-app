# Output templates

Two deliverables. Pick by what was asked; when asked for both, produce the
feature specification first and the implementation strategy after it.

Write both in plain English per `CLAUDE.md` §6. Short sentences. Lead with the
answer. Bad news first, in bold.

---

## A. Feature specification

```markdown
# <Feature name>

## 1. What this is
One paragraph. What the user can do after this ships that they cannot do today.

## 2. Why now
The problem, in the words of the person who has it. Who is blocked, how often,
and what they do instead today.

## 3. Does Frappe already do this?
| Candidate | Where | Verdict |
|---|---|---|
| <doctype / feature> | Frappe HR / ERPNext / India Compliance / this repo | reuse as-is / extend / not suitable because … |

**Decision:** reuse / extend / build new — and the one-line reason.
*(If "build new", justify against all four goal/appraisal homes and any stock
doctype that comes close. See hr-app-product.md §4.)*

## 4. Scope
**In scope:** …
**Out of scope:** … (say what a reader would reasonably assume is included)

## 5. How it works — by persona
### CXO
### HR Manager
### Employee
For each: what they see, what they can do, what they cannot do.

## 6. Data model
| Doctype | New or existing | Key fields | Submittable? | Child of |
|---|---|---|---|---|

Reuse existing doctypes wherever possible. For every new field on a stock
doctype, say whether it is a Custom Field (fixture) or a fork edit.

## 7. Rules and edge cases
- Approval chain and who can approve their own request
- Backdated entries
- Cancel and amend behaviour
- Multi-company
- Employee who leaves mid-cycle
- Empty state (no data yet)

## 8. Permissions
Role by role. Which rows each role can read and write, and how that is enforced
(role permissions / User Permission / query conditions). Name any
`ignore_permissions` use and justify it.

## 9. Reports and notifications
What is reported, to whom, on what schedule.

## 10. Compliance and privacy
PII touched, retention, who can export it. Indian statutory angle if any
(payroll statutory vs GST — see india-compliance.md §1).

## 11. Success measures
How we will know it worked. Numbers, not adjectives.

## 12. Open questions
Things the product team must decide before build starts.
```

---

## B. Implementation strategy

```markdown
# <Feature name> — implementation strategy

## 1. Approach in one paragraph

## 2. Impact analysis

### 2.1 Functional
| Dimension | Impact |
|---|---|
| Cross-module (hrms / alvoraa_goals / alvoraa_portal / ERPNext) | |
| Persona (CXO / HR Manager / Employee) | |
| HRMS domain (leaves / attendance / payroll / appraisals / org structure) | |

Every function being changed, with its callers listed. Grep first; list the
files and line references.

### 2.2 Non-functional
| Dimension | Improves / Degrades / Neutral | Why |
|---|---|---|
| Performance — query count, payload size, render time, N+1, cache hit rate | | |
| Security — permission checks, injection surface, data exposure, `ignore_permissions` scope | | |
| Reliability — error handling, edge cases, graceful degradation, hook side-effects | | |
| Scalability — high employee count, multi-company, concurrent requests | | |
| Maintainability — readability, coupling, duplication, testability | | |
| Data integrity — stale data, cache invalidation, transaction boundaries | | |
| Compliance / privacy — PII exposure, role-based scoping | | |

## 3. Design
Doctypes, fields, controller methods, hooks (`doc_events`, `scheduler_events`,
`override_doctype_class`), whitelisted APIs, UI surfaces (desk / PWA / roster /
portal). Frappe-native mechanisms only.

## 4. Risks and trade-offs
Each risk with its mitigation. Include, where relevant:
- Cache invalidation strategy — defined in this document, not deferred
- Hook side-effects and re-entrancy
- Scheduler singleton assumptions (see hr-app-product.md §5)
- Migration and patch plan for existing data
- The duplicate-doctype hazard on Employee / Department / Designation / Branch /
  Company / Holiday List (see erpnext.md §2)

## 5. Files to change
| File | Change |
|---|---|

## 6. Test plan
- `bench run-tests --app <app>` for each changed Python module
- Unit cases, including the edge cases from spec §7
- UI flows to trace manually, per surface
- What "verified" looks like before deploy approval is requested

## 7. Rollout
Migration/patch order, data backfill, what happens to in-flight documents,
rollback path.

## 8. What I need from you
The explicit decisions or approvals required before implementation starts.
```
