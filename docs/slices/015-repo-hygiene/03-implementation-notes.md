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


**The review round (2026-09-18).** Both reviews said *Ship with fixes*. They are committed with the slice (`f63650e`), redacted (`ff4ff67` — see §3). The fixes:

| Commit | Finding | What changed |
|---|---|---|
| `b0b0c20` | Code review: PP Jewellers failed closed at **import** | Eleven scripts do `from ppj_common import *`; only two create users. Exiting at import killed `verify_ppj.py` and the two reset scripts, so a good seed run was followed by a verification that died saying "Nothing was changed" — false by then. The check moved into `demo_password()`, called at the two places that set a new user's password (the shape `demo_setup.py` already used). |
| `cfb6c48` | `demo/README.md` never named the required variables | A short section names all three and shows how to pass one into the container. |
| `aadd120` | `New_req.md:524` and `:620` still named a real director | Renamed to the invented first name. This also made a claim in these notes untrue — corrected in §3. |
| `4e2e48b` | Nit: the rebrand plan still listed the deleted brochure | Two lines updated. |
| `0daea42` | **Security blocker**: the check itself carried the two leaked values in a comment, and did not scan itself; plus four real gaps in what it catches | See §4. |
| `ff4ff67` | **Security blocker**: the two review documents quoted the three real names | Replaced with `<real director 1/2/3>`. The findings read the same. |
| (this file) | The notes republished the real-to-invented mapping | Mapping moved out of the repo; see §3. |

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

The three real Grace Group directors are now **V.P. Rathore**, **Naresh Kamath** and **Aditya Rathore** — invented people.

**The mapping is deliberately not in this repository.** Printing the real names beside their replacements here would undo the change: anyone could read the table and put every invented appraisal score back onto a real person. The security review raised exactly that (Blocker 1). The mapping lives outside the repo, at `C:/Surbhi-Git/hrlocal-data/security/2026-09-18-slice-015-name-mapping.md`.

Two of the invented three still share a surname, the way two of the real ones did, so the family-run-business shape of the demo story survives. The local variable `dk` was renamed to `vp` as well — an initialism is still a name.

**Why the data still works:** the names are used only as `first_name` / `last_name` strings and as the keys that `_get_employee(first, last)` and `emp_map[...]` look them up by. I read `_make_employee()`: it builds no email, no user id and no record name from them. A consistent rename therefore keeps every lookup, every `reports_to` link and every goal row working. All six Python files still parse (`ast.parse`).

**Two things worth saying plainly:**

1. The four `Frappe Vibe Coding *.md` files (in the root and in `hrms/`) carried the same three names and were **not** in the scan's list. Leaving them would have made the rename pointless, so they were renamed too.
2. `GRACE_USER_MANUAL.md` and `hrms/Grace_Group_Vendor_Portal_UseCase.md` **are** named by the scan but no longer contain the names — I grepped and they are already clean, most likely from the Alvoraa rename work. Nothing to do there.

**Correction to what this document first claimed.** The first version said the final grep found **zero** matches. That was wrong: it found **two**. `New_req.md:524` and `:620` named one of the three directors as the project sponsor, in a tracked, public file that also carries the company's real shape. The code review caught it (Major 3). Both are now the invented first name.

The grep now really is clean. What it still matches, correctly left alone: "Dev Malhotra" in the slice 012 design and prototype, "Manpreet Malhotra" in the slice 010 rehearsal notes, and the Malhotra / Mukesh entries in the PP Jewellers demo data and its first-name pool — all invented people who happen to share a surname.

**The two review documents were redacted too.** `05-review.md` and `06-security-review.md` quoted the real names while reporting the problem. They now carry `<real director 1/2/3>` placeholders. The reviewers' findings read exactly the same; the names do not travel with them.

---

## 4. The check that keeps it fixed

`scripts/check_no_demo_passwords.py` — a text check, no bench, no database. It scans `demo/`, `docs/pp_jewellers/`, the two portal demo seeders and **itself**, for a password-shaped name given a literal value and for a password written between backticks in a document. Findings are printed masked.

**Why a script and not a unittest.** CI copies only `hrms/`, `alvoraa_goals/` and `alvoraa_portal/` into the bench (`ci.yml`, "Install this repo's apps"). `demo/` never gets there, so a `FrappeTestCase` could not open the files it is meant to guard and would quietly skip for ever — a test that can never fail is worse than no test. The repo already uses plain lint scripts for exactly this (`check_api_paths.py`, `check_app_integrity.py`, `check_nginx_conf.py`, `check_design_system.py`), and slice 013 adds `check_tracked_keys.py` the same way.

### What the reviewers found in the first version, and what it does now

The first version had a real problem and four real gaps. All six are fixed in `0daea42` and every one was re-proved by running the script, not by reading it.

| Problem | Now |
|---|---|
| **The check leaked.** Its comment carried the two real values it was written to remove, and the file was not on its own scan list. | No example of the shape is written anywhere in the file — the shapes are described in prose. The file scans itself, so it cannot regress. |
| A "contains the word password" escape in `SAFE_VALUE` waved through a literal that merely contained that word. | That alternative is deleted. An environment read is excused explicitly instead. |
| The key pattern required a character **before** the word, so a plain `password` key was missed. | The prefix is optional, with a word-boundary guard. |
| A dict key — the exact shape removed from `demo_setup.py` — was missed, because a quote sits between the key and the colon. | An optional quote after the key. Caught. |
| An unquoted shell assignment, the shape that would appear in `run_all.sh` or a `docker exec` line, was missed entirely. | A second pattern for it. A quoted value is still left to the first pattern, so `-e VAR="$VAR"` does not fire. |
| The test-file skip was a substring match on the whole path, so `demo/latest_helpers/x.py` was skipped by accident. | Matched on path parts and on the file name. |
| Slice 016's new `alvoraa_portal/alvoraa_portal/demo_seeder.py` was not scanned. | On the list. |

### The proof

Probe files were written under `demo/_probe_015/` covering every shape, the real script was run over them, and the folder was deleted afterwards. **All six bad shapes were caught** (module constant, plain `password`, dict key, unquoted shell assignment, a password in a document, and a file in a folder whose name contains "test"), and **none of the four good shapes fired** (an environment read, `-e VAR="$VAR"`, an angle-bracket placeholder, and `demo_password()`). The two genuine test files were skipped, as intended. A second harness drove `scan_line()` over the same shapes line by line, with the same result. The tree itself is clean: 40 files scanned, nothing found.

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

**The rebase of 2026-09-18 (review round).** `git fetch origin` again brought nothing; `origin/dev` has not moved all slice. **Local `dev` had moved on by 20 commits** and the branch was rebased onto it. What came in, all other sessions' work, read before building on it:

- **Slice 014's review round** — `ac0841f`, `47fff8a`, `d40f085`, `2faedb1`, `f1bc270`, `b68ee87`, `8e86470`, `b73bea8`, `67bbbc7`: `portal_api.py`, `scheduled_jobs.py`, `deploy/nginx.conf`, the check-in redaction patch and its two test files.
- **Slice 016 (portal API permissions)** — `a923405`, `5eaea0f`, `f7bd448`, `db8db2e`, `0e84d91`, `182d2cc`, `0daaf8c`, `77ed55c`, `b04356e`, `245e6b2`: gating 28 portal endpoints, `subscription.py`, `setup_data.py`, `hooks.py`, the two portal `www` pages, a new `test_portal_module_gate_016.py`, and a **new `alvoraa_portal/alvoraa_portal/demo_seeder.py`**.

**The rebase was clean** — 14 commits replayed, no conflict. Nothing of theirs was touched: my files and theirs do not overlap. The one thing their work changed for me is that new `demo_seeder.py`, which is now on the check's scan list.

---

## 8. Commands run, and what they said

### First build

| Command | Result |
|---|---|
| `python scripts/check_app_integrity.py` | `app integrity: 580 checks — OK - all consistent` (doctype-shadowing check skipped: no bench) |
| `python scripts/check_api_paths.py --max 2` | `OK (within tolerance): 2 unresolved, maximum allowed 2` — the known upstream debt, unchanged |
| `python scripts/check_nginx_conf.py` | `OK … no caller-chosen addresses; Cloudflare ranges valid; all login paths limited` |
| `yaml.safe_load` on `ci.yml` | parses; lint job has 15 steps, mine last |
| `ast.parse` on every changed Python file | all parse |
| `ruff check --config hrms/pyproject.toml` on each changed Python file, against the same file on `dev` | **no new findings**: `setup_grace_group.py` 9 before and 9 after, `demo_setup.py` 1 before and 1 after (a pre-existing import-order warning; not reformatted, to keep other sessions' diffs clean) |

### After the review round (all re-run on the rebased branch)

| Command | Result |
|---|---|
| `python scripts/check_no_demo_passwords.py` | `No demo or seed password literals found (40 files scanned).` (exit 0) |
| the same, over probe files covering **every** shape the reviewers named | exit 1, **all six bad shapes caught**, masked; **none of the four good shapes fired**; both genuine test files skipped. Probes deleted afterwards. |
| a harness driving `scan_line()` over the same shapes | 8 of 8 as expected |
| a harness driving `_is_test_path()` | 4 of 4 as expected, including `demo/latest_helpers/x.py` no longer skipped |
| `python scripts/check_app_integrity.py` | 580 checks, OK |
| `python scripts/check_api_paths.py --max 2` | within tolerance |
| `python scripts/check_nginx_conf.py` | OK |
| `yaml.safe_load` on `ci.yml` | parses, 15 lint steps |
| `ast.parse` on `ppj_common.py` and `seed_employees.py` after the `demo_password()` move | both parse |

### What I did **not** run, and why

- **No `bench run-tests`.** Nothing that CI or the bench executes changed behaviour: `demo/` is never installed, and `demo_setup.py` is only ever started by hand. The one new guard is a text check, and it was run directly.
- **No bench at all** — not started, not migrated, no site touched, no `bench clear-cache`, no `docker cp`. I did not need `pgrep -af run-tests` because I never went near it, and the board row says "Bench in use: no".
- **No browser trace.** No UI changed.
- **No push, no deploy, no server command, no history rewrite, no remote branch deleted.**

---

## 9. Known gaps and shortcuts, declared

1. ~~The passwords are still live on the tenants.~~ **Closed.** Surbhi changed them on both dev sites on 2026-09-18; the new values are stored outside the repo. Taking them out of the code was only ever half the fix, and the other half is done. What remains is to have the new value in `HR_DEMO_PASSWORD` / `PPJ_DEMO_PASSWORD` / `PORTAL_DEMO_PASSWORD` whenever a seed script is run again.
2. **The old values are still in git history and on GitHub**, and anything that was public should be treated as copied. A rewrite was out of scope and the scan calls it optional.
3. **Already-seeded sites keep the old director names.** Re-running a seed script would create the invented people beside the real ones rather than renaming them. Cleaning that up means changing data on a site, which is dev-stage work and needs Surbhi's word. I deliberately did not do it.
4. **The check is still a regex.** It now catches every shape that has actually appeared here — module constant, plain local, dict key, unquoted shell assignment, and a password in a document — and it scans itself. It would still miss a password hidden in an ordinary sentence, or one built from pieces at runtime. The scan's own recommendation of `gitleaks` in CI still stands and is not this slice.
5. ~~`hrms/docker/init.sh.orig`~~ — **done.** Added to the slice on 2026-09-18 with Surbhi's approval and deleted in `a430e33`. See §4a.
6. **`.gitignore` root rule is `/*.pdf`.** A PDF dropped into a sub-folder is still committable. Narrow on purpose: `**/*.pdf` would hide legitimate documents in `docs/`.
7. **`link_employee_users.py` still creates every employee as a System User.** That is desk access for all 400 seeded people, which is more than a demo employee needs. Out of scope here — it is a behaviour change, not a hygiene fix — but it is the obvious follow-up and belongs in a slice of its own. Raised by the review round.

---

## 10. What needs Surbhi

1. ~~Change or disable the seeded logins on the two dev tenants.~~ **Done on 2026-09-18**, values kept outside the repo. What is left is the habit: export `HR_DEMO_PASSWORD`, `PPJ_DEMO_PASSWORD` or `PORTAL_DEMO_PASSWORD` before running a seed script, and pass it into the container with `docker exec -e`.
2. **Confirm scan item A3:** were the secrets changed after the July–August malware window?
3. ~~Delete the stale remote branch `claude/pp-jewellers-hr-spec-yvmi2a`~~ — **done on 2026-09-18 by the lead session**, archived locally first as `refs/archive/malware-evidence-pp-jewellers-hr-spec`.
4. **Decide on the history rewrite** and on the counsel question about Grace Group (scan §5).
5. **The Contabo firewall** change (scan §3) — DevOps to plan, Surbhi to approve.
6. **Whether to push.** The lead session is sequencing 014, 015 and 016 into one push; this branch is deliberately **not** folded into local `dev` yet.
7. **Two more origin branches still carry the obfuscated `postcss.config.js`** (about 32 KB each): `claude/hr-app-sme-agent-h1cf1h` (6 Sep) and `fix/deploy-workflow` (3 Sep). `dev`, `main` and `fix/nginx-wildcard-cert` are clean. The lead session verified this and has put deletion to Surbhi. Recorded here, not acted on — deleting a remote branch is out of this slice's scope.

**Done since the first hand-back, not by me:** the stale remote branch `claude/pp-jewellers-hr-spec-yvmi2a` (scan B1, the branch holding the 2026-09-08 copy of the malware) was **deleted from GitHub on 2026-09-18 by the lead session**, after archiving it locally as `refs/archive/malware-evidence-pp-jewellers-hr-spec`. So item 3 of the list above is closed. The local `archive/evidence/*` branches are unaffected and must still never be pushed.
