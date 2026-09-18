# Slice 015 — Repository hygiene · implementation notes

- **Date:** 2026-09-18
- **Branch:** `slice/015-repo-hygiene`, in `.claude/worktrees/015-repo-hygiene`
- **Based on:** local `dev` at `b7244c8` — **12 commits ahead of `origin/dev`**, all of them slice 014 (check-in and driver-location security, the nginx forwarded-for work) built by another session and not pushed.
- **Nothing was pushed, deployed, migrated or run against a site. No history was rewritten. No remote branch was deleted.**

---

## 1. What was built, file by file

Ten commits, smallest first. `demo/` changes are kept in their own commits so the `merge=ours` driver (CLAUDE.md §5) can do its job.

| Commit | Files | Mechanism | Why |
|---|---|---|---|
| `fa83445` Demo seed scripts: password from the environment | `demo/link_employee_users.py`, `demo/pp_jewellers/ppj_common.py` | **configure** | Read `HR_DEMO_PASSWORD` / `PPJ_DEMO_PASSWORD`; `sys.exit` with a plain message if unset. No default, so a forgotten variable can never seed a password that is written down somewhere public. |
| `9ccfaa7` Vendor portal demo setup | `alvoraa_portal/alvoraa_portal/demo_setup.py` | **configure** | `PORTAL_DEMO_PASSWORD` or `frappe.throw`. `frappe.throw` rather than `sys.exit` because this one runs inside `bench execute`. Also stopped the end-of-run summary printing the password beside each login. |
| `ae8f435` PP Jewellers checklist | `docs/pp_jewellers/11-cowork-execution-checklist.md` | doc | The password is gone; the reader is told to export the variable and pass it in with `docker exec -e`. |
| `a37b495` Remove the brochure | deleted `hrms/Grace Group 2026.pdf` | delete | A real company's document with no record of their agreement to publish it. |
| `cdc3e10` Invented directors | `hrms/hrms/grace_group/setup_grace_group.py`, `hrms/hrms/grace_group/setup_onboarding_leaves.py`, 4 × `Frappe Vibe Coding *.md` | rename in place | See §3. |
| `063bbb3` Grace performance seed | `demo/setup_performance.py` | rename in place | The same three people, kept consistent across both scripts. |
| `5eaa487` Origin address out of the devops notes | `docs/slices/008-field-checkin/07-devops-inputs.md` | doc | Replaced with a pointer to `deploy/server.env` and the Tailscale rule. |
| `7e827e7` Demo README | `demo/README.md` | doc | `root@<server-ip>`. |
| `dac6817` `.gitignore` | `.gitignore` | configure | `.claude.backup-*/` and root-level `*.pdf`. A comment says in the file that `docs/product/legal/` is **not** ignored on purpose. |
| `a430e33` Delete `hrms/docker/init.sh.orig` | deleted `hrms/docker/init.sh.orig` | delete | A stale copy of the local container start-up script, carrying local admin and database passwords. Added after the first hand-back, approved by Surbhi on 2026-09-18. See §4a. |
| `6c21492` The check | new `scripts/check_no_demo_passwords.py`, one step at the end of the `lint` job in `.github/workflows/ci.yml` | **build** (small) | See §4. |

---

## 2. Passwords found while grepping — all values masked

| Where | Value | Public? | What was done |
|---|---|---|---|
| `demo/link_employee_users.py:23` | `Hr@…` | yes, `origin/dev` and `origin/main` | Now `HR_DEMO_PASSWORD`, fails closed |
| `demo/pp_jewellers/ppj_common.py:22` | `Ppj@…` (the default) | yes, `origin/dev` | Now `PPJ_DEMO_PASSWORD`, fails closed |
| `docs/pp_jewellers/11-cowork-execution-checklist.md:167` | `Ppj@…` | yes | Removed, replaced with the instruction |
| `alvoraa_portal/alvoraa_portal/demo_setup.py:26` and 5 print lines | `Gra…` | yes | **Extra find beyond the named scope.** The scan filed it under "fine — targets `hrms.localhost` only", but it is the same pattern in the same public repo, so it got the same treatment |
| `alvoraa_portal/.../tests/test_provision_guards.py`, `test_tenant_setup.py`, `test_tenant_access_log.py`, `test_checkin_security_014.py` | several | yes | **Left alone, on purpose.** These are made-up values used as test input; they are never seeded onto a site. The check explicitly skips test files. |
| `hrms/.github/**`, `.github/workflows/ci.yml` (`--admin-password …`) | `admi…`, `test…` | yes | **Left alone.** Upstream Frappe CI and our own throwaway CI database, exactly as the scan judged. |

Nothing else matched. The value characters are masked here and the check masks them in its own output too.

---

## 3. The rename

| Real person | Invented replacement |
|---|---|
| D.K. / D. K. Malhotra | V.P. / V. P. Rathore |
| Mukesh Mittal | Naresh Kamath |
| Chaitanya Malhotra | Aditya Rathore |

Two of the three still share a surname, so the family-run-business shape of the demo story survives. The local variable `dk` was renamed to `vp` as well — an initialism is still a name.

**Why the data still works:** the names are used only as `first_name` / `last_name` strings and as the keys that `_get_employee(first, last)` and `emp_map[...]` look them up by. I read `_make_employee()`: it builds no email, no user id and no record name from them. A consistent rename therefore keeps every lookup, every `reports_to` link and every goal row working. All six Python files still parse (`ast.parse`).

**Two things worth saying plainly:**

1. The four `Frappe Vibe Coding *.md` files (in the root and in `hrms/`) carried the same three names and were **not** in the scan's list. Leaving them would have made the rename pointless, so they were renamed too.
2. `GRACE_USER_MANUAL.md` and `hrms/Grace_Group_Vendor_Portal_UseCase.md` **are** named by the scan but no longer contain the names — I grepped and they are already clean, most likely from the Alvoraa rename work. Nothing to do there.

Final grep across the repository (excluding the untracked `.claude.backup-*` folder and the unrelated PP Jewellers demo people, who are invented): **zero** matches for any of the three real names.

---

## 4. The check that keeps it fixed

`scripts/check_no_demo_passwords.py` — a text check, no bench, no database. It scans `demo/`, `docs/pp_jewellers/` and `alvoraa_portal/alvoraa_portal/demo_setup.py` for a password-shaped name assigned a non-empty literal, and for a password written between backticks in a document. Test files are skipped. Findings are printed masked.

**Why a script and not a unittest.** CI copies only `hrms/`, `alvoraa_goals/` and `alvoraa_portal/` into the bench (`ci.yml`, "Install this repo's apps"). `demo/` never gets there, so a `FrappeTestCase` could not open the files it is meant to guard and would quietly skip for ever — a test that can never fail is worse than no test. The repo already uses plain lint scripts for exactly this (`check_api_paths.py`, `check_app_integrity.py`, `check_nginx_conf.py`, `check_design_system.py`), and slice 013 is adding `check_tracked_keys.py` the same way.

**Proved both ways.** It passes on the tree as it stands. With a password literal put back into `demo/link_employee_users.py` and another into the checklist document, it exits 1 and names both, masked.

---

## 4a. The leftover `init.sh.orig`

Scan item C: a stale copy of `hrms/docker/init.sh`, kept beside the real one. It holds a local container admin password and a database root password (masked in the scan as `admi…` and a 3-character value). They are for throwaway local containers only, but the file has no job.

**Checked before deleting.** `git grep` across every tracked file, and a plain grep over the working tree, for `init.sh.orig` and for `.orig`: **nothing references it.** `hrms/docker/docker-compose.yml` runs `bash /workspace/init.sh` — the real file, which stays. No Dockerfile, compose file, script, workflow or document names the `.orig` copy. The only mentions anywhere were the two lines in this slice's own documents saying it had been left behind.

Deleted in commit `a430e33`, on its own. The lint checks were run again afterwards and are unchanged (§8).

## 5. The seven dimensions, re-checked against the code that was written

| Dimension | Before → after | Verdict |
|---|---|---|
| Performance | One environment read at the top of three scripts that are run by hand. No query, payload or render path touched. | neutral |
| Security | Three shared passwords in public code → none, and a CI step that fails if one returns. The scripts fail **closed**: no variable, no run. | **improves** |
| Reliability | A missing password used to mean "seed 400 users with the committed default". It now means "stop before writing anything, and say why". | **improves** |
| Scalability | Nothing here grows with headcount, months or transactions. | neutral |
| Maintainability | One rule in three places plus a check that keeps it true; the invented names are consistent across both seed scripts. | **improves** |
| Data integrity | No schema, no cache, no transaction boundary. Already-seeded sites are untouched — see §7. | neutral |
| Compliance / privacy | A real company's brochure and three real directors' names, attached to invented performance scores, removed from a public repository; the origin address out of the docs. | **improves** |

**Compliance mechanisms, named:** *minimisation* — the brochure and the real names are deleted, not masked, because nothing in this repository needs them. *Fail closed on anything about a person* — an unset password variable denies the run rather than falling back. No obligation was approximated and nothing needed an architectural change.

**Visibility:** nothing was widened. No field was added to a list view, an export, a notification, a report or an API response.

---

## 6. NFR notes

- **Query counts, indexes, background jobs:** none added or changed. No DocType, field, hook, permission, workflow, report or scheduled job was touched.
- **Permission enforcement points:** unchanged. `demo_setup.py` keeps its existing `ignore_permissions=True` inserts — it is a hand-run seed script, and the count did not go up, so the `test_sec16_ignore_permissions_does_not_grow` ceiling is unaffected (the file is not on that list in any case).
- **Sensitive fields:** none read or written. The only personal data involved was removed.
- **Fallbacks:** deliberately none. A demo password has no safe fallback.
- **Personas:** no change for CXO, HR Manager or Employee. Nobody's screen, permission or data moves. The only person affected is whoever runs a seed script.

---

## 7. What else moved while I worked

- `git fetch origin` brought **nothing** new: `HEAD..origin/dev` was empty at the start and at the end.
- Local `dev` is **12 commits ahead of `origin/dev`** — slice 014, another session's, unpushed. My branch sits on top of it, as instructed. **A push of local `dev` would carry slice 014 as well as this slice.**
- No conflicts, because nothing came in. Nothing of anyone else's was touched.
- Uncommitted work in the main checkout belonging to other sessions was left exactly as it was: `.claude/context/ux-learnings.md`, `OBJECTIVES_KPI_REQUIREMENTS.md` (deleted), `backlog/KPI_AUTOMATION_BACKLOG.md`, `docs/slices/009-ess-portal-redesign/00-assessment-and-plan.md`, `hrms/hrms/alvoraa_org_structure/.../alvoraa_position.py`, and the untracked files and folders. Only the work-board row was added in the main checkout, which is what the board is for.
- **Two hot files were appended to**, and slice 013 appends to both on its own branch: `.gitignore` (013 adds key patterns and Android build output) and `.github/workflows/ci.yml` (013 adds a whole new `key-guard` job; slice 014 added a lint step *before* Semgrep). My step is the **last** step of the lint job, and my `.gitignore` block is at the **end** of the file. Both intentions are additive: whoever rebases second keeps both blocks.

---

## 8. Commands run, and what they said

| Command | Result |
|---|---|
| `python scripts/check_no_demo_passwords.py` | `No demo or seed password literals found.` (exit 0) |
| the same, with a password literal put back in a script and a document | exit 1, both named and masked — the check really fails |
| `python scripts/check_app_integrity.py` | `app integrity: 580 checks — OK - all consistent` (doctype-shadowing check skipped: no bench) |
| `python scripts/check_api_paths.py --max 2` | `OK (within tolerance): 2 unresolved, maximum allowed 2` — the known upstream debt, unchanged |
| `python scripts/check_nginx_conf.py` | `OK … no caller-chosen addresses; Cloudflare ranges valid; all login paths limited` |
| `yaml.safe_load` on `ci.yml` | parses; lint job now has 15 steps, mine last |
| `ast.parse` on all six changed Python files | all parse |
| `ruff check --config hrms/pyproject.toml` on each changed Python file, against the same file on `dev` | **no new findings**: `setup_grace_group.py` 9 before and 9 after, `demo_setup.py` 1 before and 1 after (a pre-existing import-order warning; not reformatted, to keep other sessions' diffs clean) |

### What I did **not** run, and why

- **No `bench run-tests`.** Nothing that CI or the bench executes changed behaviour: `demo/` is never installed, and `demo_setup.py` is only ever started by hand. The one new guard is a text check, and it was run directly.
- **No bench at all** — not started, not migrated, no site touched, no `bench clear-cache`, no `docker cp`. I did not need `pgrep -af run-tests` because I never went near it, and the board row says "Bench in use: no".
- **No browser trace.** No UI changed.
- **No push, no deploy, no server command, no history rewrite, no remote branch deleted.**

---

## 9. Known gaps and shortcuts, declared

1. **The passwords are still live on the tenants.** This slice takes them out of the code; it does not change a single login on `dev.alvoraa.co` or `ppj.dev.alvoraa.co`. Until Surbhi changes or disables those users the risk is exactly what the scan described. **This is the second half of the fix, not the whole one.**
2. **The old values are still in git history and on GitHub**, and anything that was public should be treated as copied. A rewrite was out of scope and the scan calls it optional.
3. **Already-seeded sites keep the old director names.** Re-running a seed script would create the invented people beside the real ones rather than renaming them. Cleaning that up means changing data on a site, which is dev-stage work and needs Surbhi's word. I deliberately did not do it.
4. **The check is a regex.** It catches the shape of the problem that actually happened — a password-looking name with a literal value, and a password in backticks in a document. A password hidden in an ordinary sentence, or built from pieces at runtime, would slip past. The scan's own recommendation of `gitleaks` in CI still stands and is not this slice.
5. ~~`hrms/docker/init.sh.orig`~~ — **done.** Added to the slice on 2026-09-18 with Surbhi's approval and deleted in `a430e33`. See §4a.
6. **`.gitignore` root rule is `/*.pdf`.** A PDF dropped into a sub-folder is still committable. Narrow on purpose: `**/*.pdf` would hide legitimate documents in `docs/`.

---

## 10. What needs Surbhi

1. **Change or disable the seeded logins** on `dev.alvoraa.co` and `ppj.dev.alvoraa.co`, and set the new values into `HR_DEMO_PASSWORD`, `PPJ_DEMO_PASSWORD` and `PORTAL_DEMO_PASSWORD` wherever the scripts get run. Dev-stage work — her word.
2. **Confirm scan item A3:** were the secrets changed after the July–August malware window?
3. ~~Delete the stale remote branch `claude/pp-jewellers-hr-spec-yvmi2a`~~ — **done on 2026-09-18 by the lead session**, archived locally first as `refs/archive/malware-evidence-pp-jewellers-hr-spec`.
4. **Decide on the history rewrite** and on the counsel question about Grace Group (scan §5).
5. **The Contabo firewall** change (scan §3) — DevOps to plan, Surbhi to approve.
6. **Whether to push.** A push of local `dev` carries slice 014 too.

**Done since the first hand-back, not by me:** the stale remote branch `claude/pp-jewellers-hr-spec-yvmi2a` (scan B1, the branch holding the 2026-09-08 copy of the malware) was **deleted from GitHub on 2026-09-18 by the lead session**, after archiving it locally as `refs/archive/malware-evidence-pp-jewellers-hr-spec`. So item 3 of the list above is closed. The local `archive/evidence/*` branches are unaffected and must still never be pushed.
