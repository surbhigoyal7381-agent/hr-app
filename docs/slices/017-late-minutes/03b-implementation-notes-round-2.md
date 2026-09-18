# Slice 017, round 2 — the grace period, and the midnight bugs

Surbhi's decision, 2026-09-18: *"there will be a grace period and after that the deductions
would be as per that organisation's policies, we need to configure that manually. So make
even the grace period configurable."*

So the shape is option **B** from `00-impact-analysis.md` §7 — grace decides whether a day
reads as late — with the grace itself configurable, and the deduction rule left exactly as
it is. Read `00-impact-analysis.md` and `03-implementation-notes.md` first; this sits on top
of them.

Branch rebased onto local `dev` `28622cf`. What came in: slice 015's repo-hygiene work
(demo passwords taken out of scripts, the Grace Group brochure and `init.sh.orig` deleted,
invented director names), slice 016's notes, and four new legal policy documents under
`docs/product/legal/`. **None of it touches attendance, shifts, late minutes or the
deduction path.** The rebase was clean.

---

## 10. The rule now, in plain English

**A day counts as late only once the grace period has passed. How late the person actually
was is still shown on the day itself.**

The two are kept apart on purpose. `late_by_mins` is the fact — minutes past the shift
start. `is_late` is the judgement — whether that is more than the organisation forgives.
Running them together is exactly what made the month total disagree with the deduction card
beside it.

**Grace is answered in one order, and each step has a test:**

1. the **Shift Type**'s own `late_entry_grace_period`, when it is set
2. the **organisation's** default, `alvoraa_attendance_late_grace_mins`
3. **no grace**

A Shift Type's grace is an Int, so "not set" and "zero" are the same value. A zero therefore
falls through to the organisation's number. **To allow nothing at all, set the organisation
default to 0 and leave the shifts alone** — the code comment says so too.

## 11. Where the setting lives, and why there

**A Frappe default (`tabDefaultValue`), read with `frappe.db.get_default`** — key
`alvoraa_attendance_late_grace_mins`, declared next to `TOLERANCE_KEY` in
`attendance_analytics.py`.

I considered an HR Settings custom field and did not use it. Reasons, in order:

| Why | |
|---|---|
| **The sibling setting already works this way** | The short-day tolerance, `alvoraa_attendance_short_tolerance_mins`, is the same kind of organisation-wide attendance threshold. It sits in the same file, is read by the same modules, and is already returned in the same `month()` payload. Two neighbours stored two different ways is how a codebase becomes hard to reason about. |
| **No migration** | Every existing tenant gets the setting the moment the code ships. An HR Settings custom field needs a fixture or property setter and a `bench migrate` on every site. |
| **Upgrade-safe** | Nothing is added to Frappe HR's own HR Settings doctype, so `bench update` cannot conflict with it. |
| **The safe write path already exists** | Slice 012's `ALLOWED_ORG_SETTINGS` allow-list on `set_org_setting` is already reviewed, refuses anything not listed, and logs the refusal under SEC-18. |

`CLAUDE.md` §4 allows either — "Frappe Global Defaults or HR Settings" — so this is a choice
between two sanctioned options, not a departure.

**The allow-list now takes a number.** A value may be a tuple (a yes/no, as before) or a
`range`. For a range the input must match `[0-9]{1,3}` and fall inside it: **whole minutes,
0 to 240**. Anything else is **refused, not clamped** — a threshold that silently became
something else is worse than an error, because nobody finds out what was saved. A test
proves `kra_link_mandatory` is still validated as a yes/no, so adding a numeric key did not
loosen the old one.

The key grants **no visibility**. It moves a threshold on a screen the person can already
see, and it does not touch the deduction rule.

## 12. PPJ under the new rule — what she will actually see

PPJ's two shifts both carry a **15-minute** grace on the Shift Type. The deduction rule's
threshold is **60 minutes**, with the first violation each week free. Measured read-only on
the local `ppj.localhost` copy:

| | All time | August |
|---|---|---|
| Days the calendar called late **before this slice** | 22,570 — every punched day | 3,756 |
| After **round 1** (arithmetic fixed, no grace) | 8,280 | 3,756 |
| **Days it will call late now** (15-minute grace) | **2,477** | **1,113** |
| Late-arrival **violations actually recorded** by the rule | 341 | 170 |

**The two numbers still differ, and that is what the decision asks for.** The calendar
answers "was this person late, by the organisation's grace?" — 15 minutes. The deduction
card answers "did it cost anything under the organisation's rule?" — more than 60 minutes,
first one free. 2,477 against 341.

**If you want the calendar and the card to agree, set the grace to the same number as the
rule's threshold**: put 60 on the Shift Type, or clear the Shift Type's grace and set the
organisation default to 60. The calendar then shows 594 against the card's 341, and the
remaining gap is only the free violation each week and the Present-only filter, both of
which the card already explains. **That is a configuration change, not a code change — which
is the point of making it configurable.**

## 13. The two midnight bugs in the pay path — both real money

The rule compared **times of day**, and times of day wrap at midnight.

| | Before | Now |
|---|---|---|
| Day shift ending 18:30, clock-out **00:30** | **1,080 minutes "early exit"** — a quarter-day deduction for four hours of *extra* work | not early at all |
| Night shift starting 22:00, clock-in **00:10** | minus 1,310, so **counted as on time** — a 130-minute late arrival hidden | 130 minutes late, counted |

Both ends of the shift are now anchored to the attendance date, the same shape Frappe HR's
own `shift_type` uses when it decides `late_entry`. Seconds are still dropped exactly as
before, so nothing else about the arithmetic moves. A clock-out *before* the shift began is
treated as bad data and ignored rather than deducted against.

`_minutes_between` is gone, replaced by `_whole_minutes`, `_shift_window` and `_as_datetime`.
The new helpers read a bare time as being on the attendance date, so older or hand-made rows
still work.

## 14. The portal now answers the question the job answers

`current_week_projection` and `_late_rule_for` skipped three conditions the weekly job
applies — **exempt grades**, the rule's **`process_from`**, and the employee's **date of
joining** — so somebody could be shown projected days that were never going to be taken off
them. There is now one `covers()` helper used by both, and the projection returns
`covered: False` with zeros rather than a figure it cannot honour. **The weekly job's own
logic is untouched** — it is money and it works.

`get_team_late_list` took the **first** report's rule and applied it to everybody, so a team
split across shifts was judged by one person's thresholds. Each report is now judged by
their own rule, and anyone no rule covers is left out of the list rather than given a number.

**Query count did not grow.** The team query now also reads the four Employee fields the
rule lookup needs, and the rule is cached per company-and-shift for the request, so the
per-person cost is unchanged. The redundant extra `current_week_projection` call that used to
compute `week_start` at the end is gone. A test asserts the rows still carry **no** grade,
joining date, company, shift or pay — the extra fields stay on the server (PRIV-3).

## 15. Files changed in round 2

| File | Change |
|---|---|
| `alvoraa_portal/.../attendance_analytics.py` | `LATE_GRACE_KEY`, `DEFAULT_LATE_GRACE_MINS`, `org_late_grace()`, `_shift_grace()`; `_shift_row` also reads `late_entry_grace_period` |
| `alvoraa_portal/.../attendance_correction.py` | `_day` sets `is_late` and `grace_mins`; `_totals` counts `is_late`; `month()` returns `late_grace_mins` |
| `alvoraa_portal/.../hr_api.py` | allow-list takes a `range`; `set_org_setting` validates it; `_late_rule_for` gains coverage plus optional row and cache; `get_team_late_list` uses each report's own rule |
| `hrms/hrms/alvoraa_late_rules/late_rules.py` | `_whole_minutes`, `_shift_window`, `_as_datetime`, `covers()`; `violations_for` anchored to the date; `current_week_projection` honours coverage |
| `alvoraa_portal/.../www/hrms-employee.html` | arrival column uses `is_late`; day detail shows "(within grace)" and "Grace allowed" |
| `alvoraa_portal/.../tests/test_late_minutes_017.py` | five new classes; money fixture split into `_MoneyBase` |
| `scripts/check_attendance_strip.js` | sample data carries `is_late` and `grace_mins`; new "late, but inside the grace period" case |

Still untouched: no DocType, no hook, no patch, no `ignore_permissions`, and none of the
other session's files.

## 16. Tests added in round 2

| Class | Covers |
|---|---|
| `TheGracePeriod` | the resolution order, all three steps; a day inside grace shows its minutes but is not late; a day past it is; **exactly on** the grace is forgiven; the month total counts only past-grace days |
| `ConfiguringTheGracePeriod` | HR sets and reads it; zero is a real answer; `15.5`, `abc`, `-5`, `" 15"`, `"15 "`, `999`, `""`, `1e2` and an Arabic-Indic digit are all refused and the good value survives; the yes/no setting is still a yes/no |
| `MidnightAndTheMoney` | working past midnight is not an early exit and **costs nothing**; a real early exit still costs **₹500 exactly**; a night-shift arrival after midnight is counted at 130 minutes |
| `WhoTheRuleActuallyCovers` | exempt grade, a week before `process_from`, and a joiner after the week — each shown nothing rather than a threat |
| `TheTeamList` | two reports, two rules, 45 minutes each: the 60-minute rule says 0, the 30-minute rule says 3; and no grade, joining date or pay reaches the row |

## 17. UI copy added — plain English

- `Late by 12 min (within grace)` — the minutes are real, and forgiven
- `Grace allowed 15 min` — shown whenever a grace applies, so the employee reads the rule
  rather than inferring it
- The arrival column reads `On time` inside the grace, and `20 min late` past it

## 18. Static checks run in round 2

| Check | Result |
|---|---|
| `python scripts/check_app_integrity.py` | **590 checks, "OK - all consistent"** |
| `node scripts/check_attendance_strip.js` | **13 cases draw cleanly**, including the new grace case |
| `node scripts/check_undefined_js.js` | **ok, no undefined identifiers** |
| `node scripts/check_portal_handlers.js` | **ok, all handlers reachable and callable** |
| `python scripts/check_api_paths.py` | **FAIL, 2 unresolved — pre-existing known debt** in `hrms/overrides/employee_payment_entry.py` (two functions missing `@frappe.whitelist`), recorded on the work board as "2/2 known debt". Not touched here. |
| API verification | `frappe.clear_document_cache` confirmed at `frappe/model/document.py:2320` and re-exported at `frappe/__init__.py:1598`; `db.set_value` confirmed to accept a dict of fields; `db.get_default`/`set_default` confirmed. Frappe **v16.33.1**. |

## 19. Non-functional, re-assessed against round 2's code

| Dimension | Verdict | Why |
|---|---|---|
| **Performance** | **neutral / slightly improves** | `_shift_row` reads one extra column, no extra query. `get_team_late_list` batches the rule lookup and drops a redundant projection call, so per-person cost is unchanged despite doing strictly more work. |
| **Security** | **improves** | The settings allow-list gains a key that grants no visibility, and gains range validation that refuses rather than coerces. The existing yes/no validation is pinned by a new test. |
| **Reliability** | **improves** | Midnight no longer wraps, in either direction. A clock-out before the shift start is ignored instead of charged. |
| **Scalability** | **neutral** | No new per-row work. |
| **Maintainability** | **improves** | One `covers()` answers coverage for both the portal and the job, instead of two places disagreeing. |
| **Data integrity** | **improves** | Nothing stored changes, and the deduction rule is untouched; two classes of wrong violation can no longer be created. |
| **Compliance / privacy** | **improves** | The employee is told the rule (grace allowed) as well as the fact. The team list is proven to carry no grade, joining date or pay. |

## 20. Still owed, and what I stopped on

1. **Nothing in round 2 has been run on a site.** The bench was held by another session for
   the release head's full pass, and I was asked to check before taking it and not to start
   a full run until it is free. Everything above is static checks, compilation and read-only
   queries on `ppj.localhost`.
2. **Owed: the new module, the fail-without-fix proof, and one clean full `alvoraa_portal`
   and `alvoraa_goals` pass.** `alvoraa_goals` has not been run at all in this slice.
3. **No browser look yet** at the corrected Time screen — it needs the bench.
4. **`Q20` / `F-7` is still open** and untouched: the rule counts `minutes > threshold` while
   some copy says "60 or more". The grace decision does not settle it.
5. **A judgement call worth flagging:** grace applies per **day**, not per month or per week.
   Nobody asked for a monthly allowance and the deduction rule already has its own weekly
   "free violations" mechanism, so a second monthly pool would be two policies fighting. If a
   monthly allowance is wanted, say so — it is a different feature, not a setting.
