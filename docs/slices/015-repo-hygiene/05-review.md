# Slice 015 — Repository hygiene · senior architect review

**Verdict: SHIP WITH FIXES** — the clean-up is real, careful and well documented, but the
new guard script writes two of the leaked passwords back into the tree, the fail-closed
check on the PP Jewellers scripts is wider than intended and breaks the verify step in the
same document it edits, and one real director's name is still in a tracked, public file.

`SHIP WITH FIXES` means: fix findings 1, 2 and 3, then it is ready to present for the
fold into local `dev`. It is not permission to push.

- **Reviewed:** `slice/015-repo-hygiene`, 13 commits on top of local `dev` `b7244c8`
- **Reviewer:** technofunctional reviewer, 2026-09-18, read-only
- **Base moved:** local `dev` is now `245e6b2` (slice 016). **No file overlap** with this
  slice, so the rebase should be clean — checked with `git diff --name-only b7244c8..dev`
  against this branch's file list: the intersection is empty.
- **What I ran:** `git log/diff/show`, `python scripts/check_no_demo_passwords.py`,
  `python -m py_compile` on all 7 changed Python files, `ruff 0.15.4` before and after on
  every changed Python file, and a purpose-built harness in the scratchpad that feeds the
  new check made-up files. No bench, no site, no server, no commit, no push.

---

## 1. Findings, worst first

### Major 1 — the guard script puts two leaked passwords back into the tree

`scripts/check_no_demo_passwords.py:68`

```python
# `Ppj@2026`, `Hr@2026` — a password quoted in a markdown sentence.
```

**Failure scenario.** The slice removes `Hr@2026` and `Ppj@2026` from every seed script
and doc. This one comment then re-adds both, in full, in a new file that goes to `dev` and
one day to `main`, in a public repository. A `git grep -E "Hr@2026|Ppj@2026|Grace@2024"`
over the whole branch returns exactly one hit, and it is this line. The file is not in its
own scan list (`SCAN_DIRS` / `SCAN_FILES`), so the check cannot catch itself.

It is a Major rather than a Blocker only because you changed both tenant passwords on
2026-09-18, so the values are no longer live. If they were still live this would be a
Blocker.

**Smallest fix.** Make the example fake, e.g.

```python
# `Abc@2026` - a password quoted in a markdown sentence.
```

---

### Major 2 — the PP Jewellers fail-closed check fires on scripts that create no users, and breaks the verify step in the same document

`demo/pp_jewellers/ppj_common.py:26-33`, and `docs/pp_jewellers/11-cowork-execution-checklist.md:163-164`

The `sys.exit` is at **module level** in `ppj_common.py`. Eleven scripts do
`from ppj_common import *`:

`seed_masters`, `seed_employees`, `seed_attendance`, `seed_payroll`, `seed_recruitment`,
`seed_onboarding`, `seed_policies`, `seed_performance`, `reset_payroll`,
`reset_performance`, **`verify_ppj`**.

Only two of them (`ppj_common.py:186`, `seed_employees.py:117`) ever use `DEMO_PASSWORD`.
All eleven now stop dead without `PPJ_DEMO_PASSWORD`.

**Failure scenario, straight from the edited document.** The checklist was changed in this
slice to read:

```
docker exec -e PPJ_DEMO_PASSWORD="$PPJ_DEMO_PASSWORD" compose-backend-1 bash /tmp/ppj/run_all.sh --site ppj.dev.alvoraa.co
docker exec compose-backend-1 bash -lc 'cd /home/frappe/frappe-bench/sites && PPJ_SCRIPT_DIR=/tmp/ppj ../env/bin/python /tmp/ppj/verify_ppj.py --site ppj.dev.alvoraa.co'
```

The second line has no `-e`. `docker exec` does not inherit the host shell's environment.
So a person who follows the checklist exactly seeds 400 users successfully, then the
verification step exits 1 with:

> `PPJ_DEMO_PASSWORD is not set. ... Nothing was changed.`

"Nothing was changed" is the opposite of the truth at that point — the seed just wrote
thousands of records. The same trap is in `reset_payroll.py` and `reset_performance.py`,
which wipe data and need no password at all.

**Smallest fix — either one.**

- Doc-only (one line): add `-e PPJ_DEMO_PASSWORD="$PPJ_DEMO_PASSWORD"` to the verify
  command too. Cheap, but leaves the reset scripts needing a password they never use.
- Better (small code change): keep `DEMO_PASSWORD = os.environ.get(...)` at module level
  but move the `sys.exit` into a `def demo_password():` and call it at the two places that
  build a User. Everything that does not create a user then runs without the variable, and
  the seed still fails before it writes anything, because both call sites are inside the
  user-creation path.

For contrast, `alvoraa_portal/.../demo_setup.py` already does it the second way and does it
well — see §6.

---

### Major 3 — a real Grace Group director is still named in a tracked, public file

`New_req.md:524` and `New_req.md:620`

```
... Champion (Chaitanya) to sponsor.
1. **HR & Chaitanya sign-off** on the blueprint ...
```

`New_req.md` is tracked and is on `origin/dev`, so it is public. The surrounding document
is titled "Grace Group: Multi-Level Cascaded Goals" and carries the company's real shape
(150–200 employees, 4 states, 15+ brands). "Chaitanya" is one of the three real promoters
the slice set out to remove, named as the project sponsor.

This also makes a claim in the notes untrue. `03-implementation-notes.md:62` says:

> Final grep across the repository ... **zero** matches for any of the three real names.

There are two. (The other `Malhotra` / `Mukesh` hits I found are invented PP Jewellers
demo people and a first-name pool in `generate_employees.py` — those are fine.)

**Smallest fix.** Replace both with `Aditya`, the invented name already chosen for that
person, and correct the sentence in the notes.

---

### Minor 4 — the check skips any value containing the word "password"

`scripts/check_no_demo_passwords.py:76-86`, the `SAFE_VALUE` pattern

The last alternative is a bare `PASSWORD`, unanchored, with `re.IGNORECASE`, matched with
`.search()`. So any literal containing that substring anywhere is treated as safe.

**Proved.** In a scratch tree, the check reports nothing for either of these:

```python
DEMO_PASSWORD = "Password123"
pwd = "Grace@2024Password"
```

**Smallest fix — delete that one line.** I ran the check against a full copy of the real
`demo/`, `docs/pp_jewellers/` and `demo_setup.py` with the `PASSWORD` alternative removed:
still `No demo or seed password literals found.` It is not carrying any weight — the
`^\$` rule already covers `PPJ_DEMO_PASSWORD="$PPJ_DEMO_PASSWORD"`.

### Minor 5 — the "skip tests" rule is a substring match on the whole path

`SKIP_PARTS = ("/tests/", "\\tests\\", "test_", ...)`, matched against the full path.

**Proved.** A file at `demo/latest_helpers/x.py` containing `DEMO_PASSWORD = "Ppj@2026"`
is silently skipped, because `latest_` contains `test_`. Any folder or file with `latest`,
`greatest`, `fastest_` and so on is a blind spot.

**Smallest fix.** Match on the file name, not the path: skip when
`os.path.basename(p).startswith("test_")` or a path *segment* equals `tests`.

### Minor 6 — two more shapes slip past, and they are shapes this repo uses

**Proved in the scratch harness:**

- Unquoted shell assignment in a `.sh` file — `PPJ_DEMO_PASSWORD=Ppj@2026` — is missed.
  `ASSIGN` requires quotes. `demo/pp_jewellers/run_all.sh` is exactly that kind of file.
- In a document, `` Log in with `Hr@2026` as the shared value. `` is missed, because
  `MARKDOWN_PW` needs the word "password" within 40 characters of the backtick.

Not a blocker — the check does catch the exact wording that leaked
(``Demo password for every seeded user: `Ppj@2026` `` is caught, I tested it). But the
notes should say this plainly alongside §9.4, and the shell case is worth one more
alternative in the regex.

### Minor 7 — the check only looks at three places

`SCAN_DIRS = ["demo", "docs/pp_jewellers"]` plus one named file. A new seeder anywhere else
is invisible to it. This is not hypothetical: slice 016 has just added
`alvoraa_portal/alvoraa_portal/demo_seeder.py` on local `dev`. I grepped it — **it is
clean**, no password at all — but the guard would not have noticed if it were not.

**Suggestion.** Add `alvoraa_portal/alvoraa_portal/` to the scanned roots (the app already
passes: I checked with `git grep` for password literals across `alvoraa_portal`,
`alvoraa_goals`, `hrms/hrms` and `scripts` outside tests — none), or scan the repo with a
skip list instead of an allow list.

### Minor 8 — `demo/README.md` never says the variables are now required

`demo/README.md` is the "how to run" page for this folder. The slice edits it (the IP
placeholder) but does not add the one new thing a person must do. The script docstrings do
say it, and the failure message is clear, so someone will find out — but they will find out
by hitting the error.

**Smallest fix.** One line under "How to run": *set `HR_DEMO_PASSWORD` (and
`PPJ_DEMO_PASSWORD` for the PP Jewellers scripts) before running anything that creates
users; there is no built-in default.*

### Minor 9 — expect a text clash in `ci.yml` and `.gitignore` when slice 013 lands

Both branches append. In `ci.yml`, 015's step is the last step of the `lint` job and 013's
`key-guard` job goes immediately after the `lint` job — the same few lines of the file. Git
may merge them without complaint. **The thing to check by eye after that rebase is
indentation:** if 013's job-level block ends up indented under `steps:`, the workflow stops
parsing and every CI run fails at once. Keep both blocks, then run a YAML parse before
pushing.

`.gitignore` is the same story and harmless either way.

### Nits

- `REBRAND_GRACE_TO_ALVORAA_PLAN.md:169,234` still name `Grace Group 2026.pdf`, now
  deleted. A dangling reference in a historical plan document; leave it or add "(removed,
  slice 015)".
- `03-implementation-notes.md` §10 item 1 still reads as if the tenant passwords have not
  been changed. They were, on 2026-09-18. Worth a line saying so, and saying where the new
  values live (outside the repo), without the values.
- Running `py_compile` left `__pycache__` folders in the worktree. They are covered by
  `.gitignore:3`, `git status` is clean, nothing to do — noted so nobody is surprised.

### Out of scope, but worth a follow-up

`demo/link_employee_users.py:72` still creates every employee login as
`"user_type": "System User"`, which gives desk access. The scan named that as half of why
A1 mattered ("The users are **System Users**, so they get desk access"). The slice fixed
the password; it did not narrow the user type. Not a defect in this slice — a separate
decision for you.

---

## 2. Does it work — the checks I actually ran

| Question | Answer | How I checked |
|---|---|---|
| Do the three scripts still work when the variable is set? | Yes, by reading — `DEMO_PASSWORD` keeps the same name and type, only its source changed. Not run against a bench. | Read all three call sites: `ppj_common.py:186`, `seed_employees.py:117`, `link_employee_users.py:73`, `demo_setup.py:44` |
| Do they fail with a clear message when it is not set? | Yes, and the message is plain English. `link_employee_users.py` exits **before** `frappe.init`, so no connection is opened. | Read |
| Does `demo_setup.py` fail before writing anything? | **Yes, cleanly.** `make_user` returns early for an existing user and calls `_demo_password()` *before* `doc.insert`, and the five `make_user` calls are the first thing `execute()` does, before the first `frappe.db.commit()` at line 203. No half-written state. | Read `execute()` and the commit points |
| Does the fail-closed check hit scripts that don't need it? | **Yes — see Major 2.** | Grepped all `ppj_common` importers |
| Any other caller or doc still passing the old password? | No. `git grep -E "Hr@2026\|Ppj@2026\|Grace@2024"` over the whole branch returns one line — the guard script's own comment (Major 1). | Grep |
| Does the rename break a lookup? | **No.** `_make_employee()` builds no email, user id or record name from the names; `_get_employee(first, last)` filters on `first_name`/`last_name`/`company`; `emp_map` is keyed on the same `full_name` strings the file defines. The rename is consistent in all six files, and `reports_to` wiring was updated with it. | Read `_make_employee`, `_get_employee`, `emp_map` construction; read the full rename diff |
| Anything still referencing the deleted files? | Only `REBRAND_GRACE_TO_ALVORAA_PLAN.md` naming the brochure (nit). `init.sh.orig`: nothing but this slice's own notes. `docker-compose.yml` runs the real `init.sh`. | `git grep` |
| Is the server IP gone? | Yes. No `169.*` anywhere in the branch. | `git grep -E "169\.[0-9]+\.[0-9]+\.[0-9]+"` |
| Do the changed Python files still parse? | Yes, all 7. | `python -m py_compile` |
| Any new lint findings? | **None.** Per-file `ruff` counts are identical before and after: 1/1, 1/1, 3/3, 29/29, 11/11, 3/3. (I used ruff 0.15.4, not the pinned 0.6.9 — a stricter version, and still no change.) | `ruff check --config hrms/pyproject.toml` on the base and the branch copies |
| Does the new check pass on this tree? | Yes — `No demo or seed password literals found.`, exit 0. | Ran it |
| Does it really fail when a password comes back? | Yes for the shapes that leaked; no for four other shapes — Minors 4, 5, 6, 7. | Scratch harness with made-up files |

**Could not check without the bench:** that a seed run end-to-end still produces the same
data with the invented names, and that `sys.exit` inside `bench --site X console < seed.py`
behaves the same as under `env/bin/python` (it raises `SystemExit`; under
`bench console` the shell reports a non-zero exit, which is what `run_all.sh` relies on with
`set -euo pipefail`). Neither is likely to surprise, but neither was run.

---

## 3. Against the scan — what is done, deferred, missed

| Scan item | Status | Evidence |
|---|---|---|
| **A1** `Hr@2026` in `link_employee_users.py` | **Done in code.** Live half is yours (done 2026-09-18). | `demo/link_employee_users.py:28-35` |
| **A2** `Ppj@2026` default in `ppj_common.py` + checklist | **Done**, with Major 2 attached | `ppj_common.py:26`, checklist:167 |
| **A3** were secrets rotated after the malware window | **Not in scope, still open.** Correctly listed for you. | notes §10.2 |
| **B1** stale remote branch `claude/pp-jewellers-hr-spec-yvmi2a` | **Done by the lead session**, 2026-09-18, archived first | notes §10 |
| **B2** delete `Grace Group 2026.pdf` | **Done** | commit `a37b495` |
| **B3** rename the three real directors | **Done in 6 files + 4 extra files the scan missed — but `New_req.md` is missed (Major 3)** | commits `cdc3e10`, `063bbb3` |
| **B4** server public IP | **Done in both named files**; no other occurrence anywhere | grep |
| **C** `init.sh.orig` | **Done**, with a proper "nothing references it" check first | commit `a430e33`, notes §4a |
| **C** vendor portal `Grace@2024` | **Done, beyond the named scope** — a good call | commit `9ccfaa7` |
| **§3** untracked files not gitignored | **Done** (`.claude.backup-*/`, `/*.pdf`); `docs/product/legal/` deliberately left visible with the reason written in the file | `.gitignore` |
| **§4.4** a secret scanner in CI (gitleaks) | **Not done, and correctly not claimed.** The new check is a pin for one known shape, not a scanner. | notes §9.4 |
| **§5** history rewrite | **Deliberately out of scope.** Still your decision. | notes §10.4 |
| Already-seeded site data (old names, old passwords on tenants) | **Deliberately out of scope**, declared clearly and in the right place | notes §9.1, §9.3 |

**On the 2026-09-18 password change.** The docs do say what a person must set — the three
variable names are in `00-impact-analysis.md` §7.1 and `03-implementation-notes.md` §10.1,
and the checklist tells the reader to export `PPJ_DEMO_PASSWORD`. The values are **not** in
any repo file — I checked; they live in `C:/Surbhi-Git/hrlocal-data/security/2026-09-18-demo-passwords.txt`,
outside the repo, which I did not open. What the docs do **not** yet say is that the change
already happened and where the values live (nit, above), and `demo/README.md` never
mentions the variables at all (Minor 8).

---

## 4. Guardrails

| Guardrail | Result |
|---|---|
| No secret value in the slice's docs | **Pass.** Every value is masked (`Hr@…`, `Ppj@…`, `Gra…`). |
| No secret value in the tree | **Fail — Major 1.** `scripts/check_no_demo_passwords.py:68`. |
| No secret value in a commit message | **Pass.** All 13 subjects read clean. |
| `demo/` changes in their own commits | **Pass.** `fa83445`, `063bbb3`, `7e827e7` touch `demo/` only; no commit mixes `demo/` with app or doc files. The `merge=ours` driver can do its job. |
| Nothing touching `www/hrms-employee.html` | **Pass.** Not in the diff. |
| Nothing touching another session's claimed files | **Pass.** Cross-checked the full file list against the work board: no overlap with 010, 012, 013, 014, 016 or `ci-fix-9138251`. 016's row even records "NOT touching demo_setup.py — slice 015 owns it". |
| No push, deploy, migrate, `docker cp`, server command | **Pass**, as far as I can see from the repo and the notes. |
| Fails closed, never warn-and-continue | **Pass** — and the CI step has no `continue-on-error`, so it is a blocking gate, unlike ruff and Semgrep above it. |

---

## 5. Seven dimensions — the analysis's claim beside my finding

| Dimension | Analysis claimed | My finding |
|---|---|---|
| Performance | neutral | **Agree.** One `os.environ.get` at import in three hand-run scripts. |
| Security | improves | **Agree in direction, with a deduction.** Three shared passwords leave the code and a blocking CI gate keeps them out — real improvement. But Major 1 puts two of the literals back, and Minors 4–7 mean the gate is narrower than the wording suggests. Net: improves. |
| Reliability | improves | **Partly disagree.** Failing before any write is better than seeding a known password — true. But Major 2 makes eight scripts that need no password fail, including verification and the two reset scripts, and the message they print ("Nothing was changed") can be false. Net: neutral until Major 2 is fixed. |
| Scalability | neutral | **Agree.** |
| Maintainability | improves | **Agree.** One rule in three places, consistent invented names, a check that holds it. |
| Data integrity | neutral | **Agree.** No schema, cache, hook or transaction boundary. Already-seeded sites untouched, and that is stated. |
| Compliance / privacy | improves | **Agree, with Major 3.** A real company's brochure and its named directors, tied to invented appraisal scores, are gone from the seed code — that is minimisation done properly (deleted, not masked). One real first name survives in `New_req.md`. |

**NFR budget:** `nfr-budget.md` has no number this slice can move. No endpoint, query,
payload, render path or background job changed. Nothing to measure.

---

## 6. Compliance verification

The slice carried no formal compliance-impact sub-analysis (there is no `02-functional-spec.md`
— this is a hygiene slice driven straight from the scan, which is reasonable). So I am
verifying against the scan's own action list and `security-compliance-baseline.md`, not
inventing an analysis.

| Obligation | Mechanism in the diff | Proof | Verdict |
|---|---|---|---|
| Minimisation — no third-party personal data without a purpose | Brochure deleted; three directors renamed in 6 files | grep returns zero for two of three names | **Partial** — `New_req.md` (Major 3) |
| No shared credential in code | Env-var read with no default, in all three scripts | `scripts/check_no_demo_passwords.py` in the CI `lint` job, blocking | **Discharged** for the three known files; **partial** as a general rule (Minors 4–7) |
| Fail closed on anything about a person | `sys.exit` / `frappe.throw` before any write | Read the code paths; `demo_setup.py` proven to throw before the first insert | **Discharged** |
| No secret value printed at runtime | The five password-bearing `print` lines in `demo_setup.py` removed | Read the diff | **Discharged** |
| Reduce attack surface on the origin | IP replaced with a placeholder in both docs | grep | **Discharged** (the firewall half is still yours) |
| Secrets stay out of the tree by accident | `.gitignore` for `.claude.backup-*/` and root PDFs | Rules read and reasoning written in the file | **Discharged** |

There is **no** control here downgraded to warn-and-continue, no new personal-data field, no
visibility widening, no logging of personal data, no AI surface. Nothing to report on those.

---

## 7. What to delete

Almost nothing — this slice is itself a deletion slice, and it did not over-build. Two
things:

1. The `PASSWORD` alternative in `SAFE_VALUE` (Minor 4). Proved unnecessary and actively
   harmful.
2. Nothing else. I specifically looked for the usual over-engineering — no new DocType, no
   new setting, no feature flag, no abstraction, no shim, no dependency. The guard is 159
   lines of plain Python with no imports beyond the standard library, placed alongside four
   existing scripts that work the same way. That is the right size for the job.

---

## 8. What was done well

- **The reasoning for a lint script over a `FrappeTestCase` is correct and was written
  down.** `demo/` never reaches the bench, so a unittest there would have skipped silently
  forever. Naming "a test that can never fail is worse than no test" is the right instinct,
  and it followed the four existing `scripts/check_*.py` instead of inventing a pattern.
- **The CI step is blocking.** Three of the steps above it are `continue-on-error`. This one
  is not, and it sits at the end of the job where it clashes with nobody.
- **`demo_setup.py` fails closed in the right place** — inside `make_user`, before the
  insert, so there is no half-seeded state and no password needed when all five users
  already exist. That is a better design than the module-level exit used in `ppj_common.py`,
  and it is the pattern Major 2 should copy.
- **The scan was exceeded where it made sense, and the excess was declared:** the four
  `Frappe Vibe Coding` docs and `demo_setup.py` were not on the list, and leaving them would
  have made the rename and the password work pointless.
- **Things the scan named but that were already clean were reported, not silently skipped**
  (`GRACE_USER_MANUAL.md`, `Grace_Group_Vendor_Portal_UseCase.md`). Saying "I checked, there
  was nothing there" is worth as much as a fix.
- **`init.sh.orig` was grepped for before deleting**, and the compose file checked to
  confirm it runs the real `init.sh`.
- **The commit split respects the `merge=ours` rule** without being asked twice, and the
  `.gitignore` carries a comment saying what is deliberately *not* ignored and why — the
  next person will not "helpfully" add `docs/product/legal/`.
- **The known gaps in §9 are honest**, including "the check is a regex" and "this is the
  second half of the fix, not the whole one".

---

## 9. What a human must still do

1. **Fix Majors 1, 2 and 3** before this goes into local `dev`. All three are small.
2. **Set the variables wherever the scripts are run.** Nothing inherits them:
   - `HR_DEMO_PASSWORD` — for `demo/link_employee_users.py` (pass with `docker exec -e …`)
   - `PPJ_DEMO_PASSWORD` — for every PP Jewellers script, *including* `verify_ppj.py` and
     the two `reset_*` scripts, until Major 2 is fixed
   - `PORTAL_DEMO_PASSWORD` — for `alvoraa_portal.alvoraa_portal.demo_setup`
   Keep the values where they are now, outside the repo.
3. **Decide on the history rewrite** and the counsel question about Grace Group (scan §5).
   Nothing in this slice touches history; the old values and the brochure are still
   reachable on GitHub by commit id.
4. **Confirm scan A3** — were tokens, SSH keys and server `.env` values changed after the
   July–August malware window? Still unanswered.
5. **The Contabo firewall** (scan §4.3) — restrict 80/443 to Cloudflare. Not started.
6. **Decide whether to fold this into local `dev` now.** The release-train note on the work
   board says no new slice commits go into local `dev` until the "010 group D + 012 push 1"
   release is pushed. Local `dev` has since moved to `245e6b2` and already carries 014 and
   016, so that rule is being stretched by others. **A push of local `dev` now would carry
   014, 015 and 016 together** — including `deploy/nginx.conf`.
7. **Optional, separate:** should `link_employee_users.py` keep creating System Users?

---

## 10. Confidence

**High** on everything I could read: the diff, the call sites, the renames, the grep
results, the lint results, and the guard script's behaviour (which I exercised with made-up
inputs rather than trusting the regex by eye).

**Low / not checked:**

- No bench was run, so no seed script was executed end to end. The "still works when the
  variable is set" answer is from reading, not running. To raise this I would need
  `ppj.localhost` and your word to touch it.
- I did not open `C:/Surbhi-Git/hrlocal-data/security/2026-09-18-demo-passwords.txt`, so I
  cannot confirm the new tenant passwords are strong or different from each other.
- I could not verify from here that the demo passwords no longer work on
  `dev.alvoraa.co` / `ppj.dev.alvoraa.co` — that needs someone with desk access.
- Slice 013's branch exists locally but I did not diff its `ci.yml`; the conflict warning in
  Minor 9 is based on the work board's description of it.
