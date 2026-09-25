---
slice: 042-redesign-wave2
artifact: 06-security-review
author: hrms-security-privacy-engineer
date: 2026-09-25
status: verification of 01c against the code on slice/042-redesign-wave2 @ a3a0902
---

# Wave 2 — security and privacy verification

**Conflict of interest, said first.** I wrote `01c` for this wave. I am now marking my own
requirements. Where a verdict below is "met", a second pair of eyes on the four marked
**[self-marked]** would be worth the ten minutes.

**Four waves late.** This verification should have run in Wave 2's review round. It did
not, and nothing in Waves 3–5 re-checked Wave 2's requirements either.

## Verdict in one line

**No Blocker. No P0.** The two controls most likely to have been theatre — the peer card's
minimum group size and the `{}`-means-everybody filter — are **real, and I read the code
that makes them real.** Three requirements are not met, and one of them (SEC-15) is a
requirement I would now write differently rather than a defect.

## Requirement by requirement

| ID | Verdict | Evidence |
|---|---|---|
| SEC-1 | **met** | `tests/test_frame_endpoint_registry_034.py:41` lists `home_api.py`, `inbox_api.py` in `MODULES`; `_module_files()` reads the module, and `:209` fails if the list is empty |
| SEC-2 | **met** | `home_api.py:64` `HOME_KEYS`, `:712`/`:762` return `{key: home[key] for key in HOME_KEYS}`; `me` is `frame_api.ME_FIELDS` (`home_api.py:58`) |
| SEC-3 | **met** | `inbox_api.py:219-234`: a `Part` built with an empty scope string **raises at construction**. Structural, not a comment |
| SEC-4 | **met** | `access.py:242-249` `NO_EMPLOYEES` / `ALL_EMPLOYEES`; `permitted_employee_filters` (`:275-286`) returns one or the other and never `{}`. `inbox_api.no_rows():154-161` the same |
| SEC-5 | **met in fact, gate missing** | No Wave 2 test patches the gate (checked). **The static check `01c` asked for does not exist**, and ten older tests do patch `subscription.has_feature` (`test_data_review_012.py:34` and others), so the habit is in the repo. **P3** |
| SEC-6 | **not re-verified** | Out of time in this pass. Say so rather than tick it |
| SEC-7 | **not re-verified** | As above |
| SEC-8 | **open by design** | D-2 unanswered; fail-closed default (no new decider) still in force |
| SEC-9 | **met** | `tests/test_week_presence_retired_042.py` — the name is assembled in pieces so the file does not trip its own scan, the walk asserts `scanned > 50` first, and the second test asserts the attribute is gone. This is the shape I want copied |
| SEC-10 | **met** for `home_api`/`inbox_api` | `test_frame_endpoint_registry_034.py:267-271`, over `_code_only()` so a docstring cannot satisfy it |
| SEC-11 | **met for this slice's modules** | `hr_api._get_employee:254-262` filters `status = "Active"`. **Outside the slice it is still false in nine places** — `goals_api.py:24,411,1248`, `performance_api.py:66,577,5045,5192,5265`, `field_app_records.py:64`, `auth.py:40` query Employee by `user_id` with no status. Lesson 3 is still live off the wave path. **P2, owner: engineer** |
| SEC-12 | **met** | `scripts/check_js_translation_calls.py` (Wave 5) enforces it for the panel scripts; run in this pass, 246 calls, clean |
| SEC-13 | **met** | Same registry test, `:248-265`, bans a module-level dict/list/set by AST |
| SEC-14 | **met** | `home_api.get_home:667-670` refuses Guest explicitly, and a caller with no Active Employee returns early rather than querying with `None` |
| SEC-15 | **NOT met — and I would rewrite it** | `get_home`, `get_nav_counts`, `get_inbox` are plain `@frappe.whitelist()`, so GET is allowed. **But none of them takes an argument**, so nothing personal can reach a URL. The requirement's *reason* is satisfied; its *letter* is not. **P4** |
| SEC-16 | **not re-verified** | |
| PRIV-1 | **met** | Counts carry numbers only — `TEAM_TODAY_KEYS` (`home_api.py:79`) and the payload test at `test_home_api_042.py:341-348` |
| PRIV-2 | **met, and it is genuinely good** | `home_api._suppress:418-457`. `MIN_GROUP = 5` (`:85`). Complementary suppression is real: one hidden → the next smallest goes with it (`:449-452`), with the reasoning for *why not always two* written out. `test_home_api_042.py:388-419` walks a five-row table |
| PRIV-3 | **not re-verified** | |
| PRIV-4 | **fail-closed default held** | Own work anniversary only; no joiners list (commit `afdc4ae`) |
| PRIV-5..9 | **not re-verified** | |

## Findings

**F1 · Minor (P3) — a zero is never suppressed.** `home_api._suppress:442` hides a category
only when `0 < v < MIN_GROUP`. In a peer group of exactly five, `away: 0` is published, so
the caller learns that none of their four peers is on leave today. That is a true statement
about four named-by-elimination people. Co-presence already discloses it and I do not think
it is worth changing the rule for, but it is the edge the rule does not cover and it should
be a written acceptance rather than an oversight. *Owner: Surbhi, decide by 2026-10-31.*

**F2 · Minor (P3) — the gate-patching ban has no gate.** SEC-5 required a static check that
no test in this slice patches `has_feature`. It was not written. The substance holds today.

**F3 · Minor (P4) — SEC-15's POST rule.** As above: satisfied in spirit, not in letter.

## Worries — not findings

* `access.permitted_branches:233` still treats a Branch User Permission scoped to a
  *different doctype* as "no branch restriction", i.e. company-wide. Every scope
  requirement in this wave stands on it. It is R4 in `01c` and it is still open.
* One shared `Administrator` login reaches every tenant, so a read cannot be traced to a
  person (`ALV-93`).

## Residual risk

| # | Risk | Owner | Date | State |
|---|---|---|---|---|
| R1 | No detection on a successful over-read | Security & privacy engineer with DevOps | 2026-10-15 / 2026-11-30 | carried, unchanged |
| R2 | No repo-wide `ignore_permissions` counter in CI | Security & privacy engineer | 2026-10-31 | **carried since Wave 1 and now four waves old.** 901 occurrences across our two apps. Either it is built or the date moves with Surbhi's name on it |
| R4 | `permitted_branches` fails open on a doctype-scoped Branch permission | Live check Surbhi / fix engineer | 2026-09-30 / 2026-11-15 | open |
| R6 | The peer card is an inference channel; minimum-n bounds it, it does not remove it | Surbhi | not yet accepted | **still not accepted in writing** |
| R7 | Decide-in-place makes a decision cheaper to take | Surbhi | review 30 days after dev | not yet accepted |
