# Slice 015 — Repository hygiene · impact analysis and strategy

- **Date:** 2026-09-18
- **Source:** `C:/Surbhi-Git/hrlocal-data/security/2026-09-17-repo-history-scan.md` (outside the repo)
- **Approved by Surbhi:** 2026-09-18, as a small two-stage run (analysis, then build)
- **Scope limit:** the working tree only. **No history rewrite. No push. No deploy. No server command. No remote branch deleted.**

---

## 1. What this slice does

Five clean-ups the scan asked for, in the current files only:

| # | Change | Files |
|---|---|---|
| 1 | Demo passwords come from an environment variable and the script **stops** if it is not set | `demo/link_employee_users.py`, `demo/pp_jewellers/ppj_common.py`, `alvoraa_portal/alvoraa_portal/demo_setup.py`, `docs/pp_jewellers/11-cowork-execution-checklist.md` |
| 2 | Delete the real company brochure | `hrms/Grace Group 2026.pdf` |
| 3 | Real Grace Group directors renamed to invented people | `hrms/hrms/grace_group/setup_grace_group.py`, `hrms/hrms/grace_group/setup_onboarding_leaves.py`, `demo/setup_performance.py`, 4 markdown docs |
| 4 | Server public IP replaced with a placeholder | `demo/README.md`, `docs/slices/008-field-checkin/07-devops-inputs.md` |
| 5 | `.gitignore` covers the untracked things the scan flagged | `.gitignore` |
| 6 | A static check so a password literal cannot come back into `demo/` | new `scripts/check_no_demo_passwords.py`, one step at the **end** of the CI lint job |

Out of scope, on purpose: history rewrite, deleting the stale remote branch `claude/pp-jewellers-hr-spec-yvmi2a`, changing passwords on the dev tenants, the Contabo firewall, `hrms/docker/init.sh.orig`. All of those are Surbhi's calls and are listed in §7.

---

## 2. What came in from other people while I started

`git fetch origin` brought nothing new: `HEAD..origin/dev` is empty.

**Local `dev` is 12 commits ahead of `origin/dev`.** Those 12 are slice 014 (check-in and driver-location security, nginx forwarded-for) plus its notes, all built by another session and **not pushed**. My branch is based on local `dev` (`b7244c8`), as instructed, so it sits on top of 014.

Uncommitted work in the main checkout that is **not mine** and that I will not touch:

- `.claude/context/ux-learnings.md` (modified)
- `OBJECTIVES_KPI_REQUIREMENTS.md` (deleted), `backlog/KPI_AUTOMATION_BACKLOG.md`, `docs/slices/009-ess-portal-redesign/00-assessment-and-plan.md`
- `hrms/hrms/alvoraa_org_structure/alvoraa_position/alvoraa_position.py`
- untracked: `INDIA_PAYROLL_STRATEGY.md`, `OBJECTIVES_AND_KPI_SRS.md`, `SETUP-GUIDE.md`, `docs/product/legal/`, `docs/slices/013-mobile-app/`, `docs/slices/014-checkin-security-fixes/00-impact-analysis.md`, `docs/slices/_template/`, the four root PDFs, `.claude.backup-20260824-1203/`

I work in `.claude/worktrees/015-repo-hygiene` on `slice/015-repo-hygiene`, so none of that is at risk.

---

## 3. Parallel-work check

| File I will change | Hot file? | Who else is in it | Plan |
|---|---|---|---|
| `demo/link_employee_users.py` | no | nobody on the board | mine |
| `demo/pp_jewellers/ppj_common.py` | no | nobody | mine |
| `demo/setup_performance.py` | no | nobody | mine |
| `demo/README.md` | no | nobody | mine |
| `alvoraa_portal/alvoraa_portal/demo_setup.py` | no | nobody (010 owns `performance_api.py`/`hr_api.py`/`goals_api.py`; 014 owns `field_checkin.py`/`portal_api.py`) | mine |
| `hrms/hrms/grace_group/setup_grace_group.py` | no | nobody | mine |
| `hrms/hrms/grace_group/setup_onboarding_leaves.py` | no | nobody | mine |
| `hrms/Grace Group 2026.pdf` (delete) | no | nobody | mine |
| `docs/pp_jewellers/11-cowork-execution-checklist.md` | no | nobody | mine |
| `docs/slices/008-field-checkin/07-devops-inputs.md` | no | nobody | mine |
| 4 × `Frappe Vibe Coding *.md` (root and `hrms/`) | no | nobody | mine |
| `.gitignore` | **yes** (`.claude/` family rule: only change when the task is about it — it is) | **slice 013** added key patterns and Android build output on its own branch, not yet in `dev` | **Split.** I append a new block at the end of the file. 013 appended its own block. Two appends to different ends of the same list conflict only textually and keep both intentions. |
| `.github/workflows/ci.yml` | **yes** | **slice 013** adds a whole new `key-guard` job; **slice 014** already added a step *before* Semgrep (in local `dev`) | **Split.** My step goes at the **very end of the `lint` job**, after Semgrep. Different place from both. |
| new `scripts/check_no_demo_passwords.py` | no | new file | mine |
| new `docs/slices/015-repo-hygiene/*` | no | new folder | mine |

**Board:** a row for 015 goes on `.claude/work-in-progress.md` before the build.

**Bench:** not needed. The demo scripts are not imported by the app, and the new check is a plain Python script. I will still check `docker exec hrlocal-bench pgrep -af run-tests` before touching anything shared — but I plan to touch nothing shared.

### Why the pin test is a lint script, not a unittest

CI copies only `hrms/`, `alvoraa_goals/` and `alvoraa_portal/` into the bench (`ci.yml`, "Install this repo's apps"). `demo/` never reaches the bench, so a `FrappeTestCase` could not see it and would silently skip forever. The repo already has the right pattern for this: `scripts/check_api_paths.py`, `scripts/check_app_integrity.py`, `scripts/check_nginx_conf.py`, `scripts/check_design_system.py` — plain scripts run by the lint job against the checkout. Slice 013 is adding `scripts/check_tracked_keys.py` the same way. So does this one.

---

## 4. Functional impact

**Cross-module:** none. `demo/` and `hrms/hrms/grace_group/` are seed scripts run by hand; nothing in `alvoraa_portal`, `alvoraa_goals`, `hrms` runtime, `hrms` app code or `erpnext` imports them. `alvoraa_portal/alvoraa_portal/demo_setup.py` is invoked only by `bench execute`.

**Grep of every caller of everything I change:**

- `DEMO_PASSWORD` is read in `demo/link_employee_users.py:58`, `demo/pp_jewellers/ppj_common.py:175` and `demo/pp_jewellers/seed_employees.py:117` (the last imports it from `ppj_common` via `from ppj_common import *`). All three keep working — the name and type do not change, only where the value comes from.
- `make_user()` in `demo_setup.py` is called inside the same file only.
- The director names are looked up by `_get_employee(first, last)` in `setup_grace_group.py` and `setup_onboarding_leaves.py`, and by `emp_map[...]` in `demo/setup_performance.py`. No email, user id, employee id or file name is derived from them, so a consistent rename keeps every lookup working. I checked `_make_employee()` — it builds no email.
- Nothing outside those files references the three names except documentation.

**HRMS domain:** untouched. No DocType, field, permission, workflow, hook, report or scheduled job changes. Leaves, attendance, payroll, appraisals and org structure are not involved.

**Personas:** no user-visible change for CXO, HR Manager or Employee. Nobody's screen, permission or data changes. The only people affected are whoever runs a seed script: they must now set an environment variable first, and they get a clear message if they forget.

---

## 5. Non-functional verdict

| Dimension | Verdict | Why |
|---|---|---|
| Performance | neutral | No query, payload or render path changes. One extra environment read at script start. |
| Security | **improves** | Three shared passwords leave public code. The scripts fail closed with no built-in default, so a forgotten variable can never quietly seed a known password again. A CI check stops the literal coming back. |
| Reliability | **improves** slightly | The scripts now stop at the top with a clear message instead of seeding hundreds of users with a password nobody meant to use. Failing before any write is safer than failing halfway. |
| Scalability | neutral | Nothing grows with headcount here. |
| Maintainability | **improves** | One rule ("read it from the environment, or stop") in three places, plus a check that keeps it true. |
| Data integrity | neutral | No schema, no cache, no transaction boundary. Already-seeded sites keep the users they have — see the risk in §6. |
| Compliance / privacy | **improves** | Removes a real third party's brochure and its named directors from a public repository, and takes the origin IP out of the docs. This is minimisation: data with no purpose in this repo is deleted, not masked. |

**Compliance mechanisms used** (per `compliance-feature-map.md` wording): *minimisation* — the brochure and the real names are removed rather than redacted, because there is no purpose that keeps them. *Fail closed* — an unset password variable denies the run. No control is approximated; nothing here needs an architectural change.

---

## 6. Risks and trade-offs

1. **The passwords are still live on the tenants.** Taking them out of the code does nothing to `dev.alvoraa.co` and `ppj.dev.alvoraa.co`. Until Surbhi changes or disables those logins, the risk is exactly as it was — the scan's own point. This slice is the second half of the fix, not the first.
2. **The old values are still in git history and on GitHub.** A history rewrite is out of scope and the scan says it is optional; anything that was public should be treated as copied.
3. **Renaming the directors does not rename them on any site that was already seeded.** `ppj.localhost`, `hrms.localhost` and the Grace demo tenants keep the records they have. Re-running a seed script creates the new people beside the old ones rather than renaming them. **I will not touch any site's data** — that is dev-stage work and needs Surbhi's word. Called out in the notes.
4. **`demo/` must never reach `main`** (CLAUDE.md §5, `merge=ours` driver). So the demo changes go in their **own commits**, separate from the app and doc changes, and if a `main` merge ever happens the driver keeps `main`'s side. `alvoraa_portal/demo_setup.py` is *not* in `demo/` and is a normal file.
5. **Two hot files.** `.gitignore` and `ci.yml` are both being appended to by slice 013 on its own branch. Textual conflicts are likely when 013 lands; both intentions are additive, so the resolution is "keep both blocks". Flagged for whoever rebases second.
6. **The four `Frappe Vibe Coding` docs are an extra find**, not named in the scan. They carry the same three real names, in four tracked copies. Leaving them would make the rename pointless, so I rename there too and say so.
7. **`GRACE_USER_MANUAL.md` and `hrms/Grace_Group_Vendor_Portal_UseCase.md`** are named by the scan but **no longer contain the names** — I grepped; they are already clean, probably from the Alvoraa rename. Nothing to do, reported rather than silently skipped.

---

## 7. What still needs Surbhi (not in this slice)

1. Change or disable the seeded logins on `dev.alvoraa.co` and `ppj.dev.alvoraa.co`, and set the new value into `PPJ_DEMO_PASSWORD` / `HR_DEMO_PASSWORD` / `PORTAL_DEMO_PASSWORD` wherever the scripts are run. Dev-stage work — her word.
2. Confirm scan item A3 (were secrets changed after the July–August malware window).
3. Delete the stale remote branch `claude/pp-jewellers-hr-spec-yvmi2a`.
4. Decide on the history rewrite and on the counsel question about Grace Group (scan §5).
5. The Contabo firewall change (scan §3), planned by DevOps.
6. Whether `hrms/docker/init.sh.orig` should be deleted — the scan suggests it, it is outside this slice's list.

---

## 8. Recommended path

Do exactly the six changes in §1, in six small commits, in the worktree, on top of local `dev`. Run the new static check and the repo's other lint scripts locally. Do not run the bench, do not touch a site, do not push. Then hand back with the list above.
## Scan item A3 answered (Surbhi, 2026-09-18)

**The secrets were changed after the malware incident.** So the rotation list in `06-security-review.md` is not outstanding as a whole. Note for the record: the two branches still carrying the obfuscated `postcss.config.js` were updated on 3 and 6 September and were deleted from GitHub on 2026-09-18 (archived locally as `refs/archive/malware-evidence-*`), so if any secret was last changed before early September it is still worth a second look.
