# Slice 015 — Repository hygiene · security and privacy review

- **Date:** 2026-09-18
- **Reviewer:** security and privacy engineer agent
- **Branch reviewed:** `slice/015-repo-hygiene` (13 commits), in `.claude/worktrees/015-repo-hygiene`, on top of local `dev` `b7244c8`
- **Inputs:** `00-impact-analysis.md`, `03-implementation-notes.md`, and the scan at `C:/Surbhi-Git/hrlocal-data/security/2026-09-17-repo-history-scan.md`
- **Method:** read-only. No file changed, no commit, no push, no deploy, no server command, no network call. No secret value printed beyond its first characters.
- **Baseline freshness:** `security-compliance-baseline.md` was verified 24 Aug 2026 (§3a on 6 Sep). Both are inside the 90-day window, so nothing here is quoted from a stale entry.

---

## Verdict

# Ship with fixes

The slice does what it set out to do. The working tree is clean of the three demo
passwords, the brochure, the real directors' names, the origin IP address and the
leftover `init.sh.orig`. I checked each one by grepping the branch, not by reading the
notes.

Two things must be fixed before this is pushed, and one thing found during the review is
more urgent than the whole slice.

**Fix before push (Blockers, both cheap):**

1. The slice's own notes republish the three real names next to their invented
   replacements, in a tracked file, in a public repo. That undoes the change it
   documents.
2. The new CI check misses the exact password line the slice removed
   (`"new_password": "..."`), and misses a plain `password = "..."` as well. It is
   weaker than the notes claim.

**Found during the review, unrelated to this slice, and worse than anything in it:**

3. The 32 KB crypto-stealer is **live at the tip of two branches still on `origin`** —
   `claude/hr-app-sme-agent-h1cf1h` and `fix/deploy-workflow` — last touched 6 and 3
   September 2026. That is current code, not history. The scan missed these two; it
   only named the branch that has since been deleted.

---

## 1 · Does the slice close what the scan found?

| Scan item | What it was | State now | Evidence |
|---|---|---|---|
| **A1** — demo password `Hr@2…` in `demo/link_employee_users.py` | Public password for System Users on `dev.alvoraa.co` | **Closed in code. Closed on the tenant. Still in history.** | `demo/link_employee_users.py:20-30` now reads `HR_DEMO_PASSWORD` and calls `sys.exit` with a plain message if it is empty. No default. Read the file. The live logins were changed by the lead session on 2026-09-18 (86 accounts on `dev.alvoraa.co`). |
| **A2** — demo password `Ppj@…` in `demo/pp_jewellers/ppj_common.py` and the checklist | Public password for ~400 seeded PP Jewellers users, Owner included | **Closed in code. Closed on the tenant. Still in history.** | `demo/pp_jewellers/ppj_common.py:27-33`: `os.environ.get(...).strip()` then `sys.exit`. `import sys` is present at line 14, so the exit really works — I checked, because a missing import would have turned a clean stop into a `NameError`. `docs/pp_jewellers/11-cowork-execution-checklist.md:163-172` now tells the reader to export the variable. 403 logins changed on `ppj.dev.alvoraa.co` on 2026-09-18. |
| **A3** — were the secrets changed after the July–August malware window? | Unknown | **Not closed. Still unanswered, and now bigger.** | The slice never claimed this one. See §3 — because the malware is live on two branches dated 3 and 6 September, the window to worry about is not July–August. It runs to today. |
| **B1** — malware in three `postcss.config.js` files | Crypto-wallet stealer that also reads environment variables | **Partly closed, and the scan was incomplete.** | `origin/claude/pp-jewellers-hr-spec-yvmi2a` is gone from my remote-tracking refs and archived locally at `refs/archive/malware-evidence-pp-jewellers-hr-spec` (`9cd082d`) — verified by reading local refs. **But** `origin/claude/hr-app-sme-agent-h1cf1h` and `origin/fix/deploy-workflow` still carry the 32 KB files at their tips. `origin/dev`, `origin/main` and `origin/fix/nginx-wildcard-cert` carry the clean 66–75 byte versions. See §3. |
| **B2** — Grace Group brochure PDF | A real company's document, published without a record of consent | **Closed in the tree. Still in history.** | `git ls-files` finds no `Grace Group 2026.pdf` on the branch. Deleted in `a37b495`. |
| **B3** — real names of three Grace Group promoters with invented appraisal scores | Privacy and reputation risk | **Partly closed — and partly re-opened by this slice.** | The seed scripts and the four `Frappe Vibe Coding` docs are clean. But `docs/slices/015-repo-hygiene/03-implementation-notes.md:49-51` prints all three real names beside their replacements, and `New_req.md:524` and `:620` still name "Chaitanya" as the project sponsor for a named real client. See Blocker 1 and Major 1. |
| **B4** — origin server public IP `169.…` | Lets someone bypass Cloudflare | **Closed in the tree. Still in history. The firewall fix is not done.** | `git grep` for the address across the whole branch returns nothing. `demo/README.md:50` and `docs/slices/008-field-checkin/07-devops-inputs.md:47` now use a placeholder. The Contabo firewall restriction the scan recommended is not part of this slice and has not been done. |
| **C** — `hrms/docker/init.sh.orig`, the leftover file with local admin and DB root passwords | Low value, no job | **Closed.** | Not in `git ls-files` on the branch. Deleted in `a430e33`. The notes record the grep that proved nothing referenced it; I re-ran it and agree. |

### Say this plainly: git history is untouched

This slice changes **only the current files**. Every old value — the three passwords,
the brochure, the three real names, the server IP — is still reachable in the repository
history, and 396 of those commits are on a **public** GitHub repo. Making the repo
private later does not undo that. Anything that was public should be treated as already
copied.

What that means in practice: **the passwords are fixed because they were changed on the
tenants, not because they were removed from the code.** The code change stops the next
one. The tenant change closed the live one.

---

## 2 · New risk introduced by the slice

### Blocker 1 — the slice republishes the three real names it removed

`docs/slices/015-repo-hygiene/03-implementation-notes.md:49-51`

```
| D.K. / D. K. Malhotra | V.P. / V. P. Rathore |
| Mukesh Mittal | Naresh Kamath |
| Chaitanya Malhotra | Aditya Rathore |
```

**The scenario:** anyone with a browser opens the public repo, reads this table, and
maps every invented appraisal score, goal and feedback line in `demo/setup_performance.py`
straight back to three named, real directors of a real company. Before this table they
would have had to dig through history to do it. Now it is a lookup table with a heading.

I am being proportionate about this: the names were already public for about eleven
weeks and are still in history, so the *incremental* exposure is modest. I still rank it
a Blocker for two reasons. It negates the stated purpose of the same commit set — a
control that the change itself undoes is not a control. And the fix is one table edit
that costs two minutes, before the push, versus never, after it.

**Fix:** replace the table with the invented names only, plus one line saying the real
names were removed and the mapping is held outside the repo (put the mapping in
`C:/Surbhi-Git/hrlocal-data/security/`, next to the password file). Do the same anywhere
else the mapping would be written down.

*(Verified by reading. `git grep` across the branch; the only three hits are those lines.)*

### Blocker 2 — the CI check does not catch the line it was written for

`scripts/check_no_demo_passwords.py:58-66`

I ran the check's own regexes against realistic lines. Results:

| Line | Caught? |
|---|---|
| `DEMO_PASSWORD = "Ppj@2026"` | yes |
| `doc.new_password = 'Grace@2024'` | yes |
| `"new_password": "Grace@2024",` | **no** |
| `password = "Hr@2026"` | **no** |
| `PASSWORD = "Hr@2026"` | **no** |
| `DEMO_PASSWORD = "MyPassword2026"` | **no** |
| `print("… / Grace@2024")` | **no** |
| Markdown: ``password … `Ppj@2026` `` | yes |

The third line is **the exact literal this slice removed from
`alvoraa_portal/.../demo_setup.py:26`**. If someone restored that file tomorrow, CI would
pass. The notes say the check was "proved both ways", but the proof used the assignment
form only, so the claim is broader than the evidence.

Two causes, both one-line fixes:

- The key pattern is `[A-Za-z_][A-Za-z0-9_\-]*(?:password|…)…`. It needs at least one
  character *before* the word, so a bare `password` or `PASSWORD` never matches, and a
  quoted dict key (`"new_password":`) has a `"` between the key and the `:`, which the
  separator does not allow.
- `SAFE_VALUE` (line 83) contains a bare `PASSWORD` alternative with no anchor and
  `IGNORECASE`, so **any value containing the word "password" is treated as safe** —
  `"MyPassword2026"` passes.

**Fix:** allow a zero-length prefix and an optional quote around the key; anchor the
`PASSWORD` safe-value rule so it only matches a pure variable reference. Then re-run the
proof against all eight lines above and record the result.

*(Verified by reading, and by running the script's own compiled patterns against test
strings in memory. No file was changed.)*

### Things I checked and found fine

| Worry | Finding |
|---|---|
| Does the check print the password value into a public CI log? | It masks to the first two characters (`_mask`, line 105-107) — tighter than the four I would have required. And the check only fires when the value is already committed and therefore already public. **No new leak.** *(verified by reading)* |
| Does the variable name leak anything? | `HR_DEMO_PASSWORD`, `PPJ_DEMO_PASSWORD`, `PORTAL_DEMO_PASSWORD` are names, not values. Nothing prints the value. The end-of-run summary in `demo_setup.py` used to print the password next to every login; that was removed. **Improvement.** *(verified by reading the diff)* |
| Does anything fail open? | No. All three paths fail closed: `sys.exit` in two scripts, `frappe.throw` in `demo_setup.py` (correct choice — it runs inside `bench execute`, where `sys.exit` would be rude to the bench process). No fallback, no default. **This is the right shape.** *(verified by reading)* |
| Was a control downgraded to make a test pass? | No. The new CI step has no `continue-on-error`, so it blocks. It sits last in the `lint` job, which runs on push and PR to `dev`, `test` and `main`. *(verified by reading `.github/workflows/ci.yml:143-148` and the job header)* |
| Does `.gitignore` hide something that should be reviewed? | Mildly. `/*.pdf` hides the four reference PDFs in the repo root, which the scan flagged and never opened. Hiding them from git is right; it also means nobody will look at them. They are third-party documents sitting in a working folder — **move them out of the repo folder** rather than relying on an ignore rule. `.claude.backup-*/` is correctly ignored (it holds `settings.local.json`). `docs/product/legal/` is deliberately **not** ignored, with a comment saying so — I agree, but note it currently holds a DPA template, an employee privacy notice template and a README, and those become world-readable the moment they are committed. Read them before that happens. *(verified by reading `.gitignore` and listing the folder; I did not open the templates)* |
| Are the renamed people still traceable? | Yes, three ways: the rename commit `cdc3e10` shows old and new side by side; history still holds the originals; and Blocker 1 publishes the map. The first two cannot be fixed without a history rewrite. The third can and should. |
| Does the rename break the seed data? | The notes' reasoning is right — the names are only `first_name`/`last_name` strings and lookup keys, and `_make_employee()` derives no email or ID from them. I re-read `setup_grace_group.py` and `setup_performance.py` and agree. Not a security matter, but it would have been a nasty one to find later. *(verified by reading)* |
| `ignore_permissions` count | Unchanged. `demo_setup.py` keeps its existing seed-script inserts; nothing was added. *(verified by reading the diff)* |
| Personal data reaching a log, notification or model prompt | None. No runtime path changed. *(verified by reading the diff — nothing outside `demo/`, seed scripts, docs, `.gitignore` and CI)* |

### Major 1 — `New_req.md` still names a real client and a real person

`New_req.md:524` and `:620` name "Chaitanya" as the executive sponsor. Lines 12 and 630
describe Grace Group as a real client with revenue (₹180 cr), headcount (150–200), four
states and 15+ brands.

**The scenario:** a competitor, or Grace Group themselves, reads a public repo that
names them as a customer, states their turnover and headcount, and names an individual
executive as the sponsor of a project — none of which anyone agreed to publish.

This is the same finding as B3, in a file the scan did not list. It was outside the
slice's agreed scope, so it is not the engineer's miss. It should be a follow-up, and it
is cheap: rename the person, and either genericise the client or confirm Grace Group
agreed to be named.

*(Verified by reading. `git grep` on the branch.)*

### Minor 1 — the archive ref must never be pushed

`refs/archive/malware-evidence-pp-jewellers-hr-spec` holds the malware for evidence.
A normal `git push` will not send it. **`git push --mirror` or `git push --all --follow-tags`
with a wide refspec would.** Worth one line in the runbook: never mirror-push this repo.

*(Verified by reading local refs.)*

---

## 3 · What is still exposed right now

### First, and above everything else in this review

**Two branches on `origin` carry the crypto-stealer at their tip, right now.**

| Branch | Tip commit | Date | The three `postcss.config.js` files |
|---|---|---|---|
| `origin/claude/hr-app-sme-agent-h1cf1h` | `2f35c61` | 2026-09-06 | 32,379 / 32,387 / 32,387 bytes |
| `origin/fix/deploy-workflow` | `cab7d1d` | 2026-09-03 | 32,379 / 32,387 / 32,387 bytes |
| `origin/dev`, `origin/main`, `origin/fix/nginx-wildcard-cert` | — | — | 66 / 74 / 75 bytes — clean |

I confirmed the shape without printing the payload: the file is 15 lines; line 14 is
`};` followed by about 500 spaces and then **31,711 characters of code**, pushed far
enough right that it looks like a blank line in an editor. The first four characters of
the payload are `glob…`. That is the same hiding trick the scan described for the
deleted branch.

**Why this matters more than the rest of the review.** The cleanup commit `c844eac`
(18 Aug) fixed `main` and `dev`. These two branches were created or updated **after**
that and carried the bad files forward. So:

- The exposure window is **not** 31 July – 18 August. It runs to **today**.
- Anyone — a person, a session, an agent, a CI job — who checks out either branch and
  runs `yarn`/`npm install` or a build runs a stealer that reads environment variables.
- Scan item A3 is therefore not a question about a closed window. It is a question about
  a window that is still open.

**One caveat, and it is real:** these are my local remote-tracking refs. If the branches
were deleted on GitHub without a `--prune` fetch here, my copy is stale and the finding
is already closed. **Needs a check**, and it takes ten seconds:

```
git ls-remote --heads origin "claude/*" "fix/*"
```

If they are listed, treat them as live.

### The rotation list, in priority order

If A3 cannot be confirmed — and given the 3 and 6 September dates above, I would not
confirm it — rotate in this order. This is a recommendation; the doing is the user's
call and is server-stage work.

| # | What to rotate | Why it is here |
|---|---|---|
| 1 | **GitHub Actions repository secrets** — every one in the repo's Settings → Secrets. From the workflows: the deploy SSH key / host credentials, the object-storage bucket keys, and any token used by `deploy.yml` | Available to any workflow run during the window. The exact list should be read off the Settings page, not guessed from a workflow file |
| 2 | **GitHub personal access tokens** for the account(s) that build this repo, plus any fine-grained token with write access | The stealer read environment variables; a token in a shell profile is an environment variable |
| 3 | **SSH keys on any machine that ran a build** — the deploy key on GitHub, and `~/.ssh` keys on this PC and on the server | Direct path to the server |
| 4 | **Server `.env` values in `deploy/`** — database passwords, mail passwords, any API secrets. Do not open the file to check; rotate the values at their source | Named in the cleanup commit's own warning |
| 5 | **Frappe site `encryption_key` for every site**, and the MariaDB root password | These decrypt stored credentials inside Frappe |
| 6 | **Tailscale auth keys**, and any Cloudflare API token | Both give network reach to the server |
| 7 | **Demo tenant logins** | Already done on 2026-09-18 for `dev.alvoraa.co` (86) and `ppj.dev.alvoraa.co` (403). Non-seeded accounts were untouched — **those still have whatever they had.** Worth a sweep |

Two supporting actions in the same window:

- **Delete GitHub Actions logs and artifacts** from 31 July onward. The scan never read
  them, and a build log can echo an environment variable.
- **Check GitHub's audit log** for token creation, deploy-key additions and new
  collaborators since 31 July. That is how you find out whether the stealer was used,
  rather than assuming.

*(All of the above: needs-a-check. I did not contact GitHub or any server.)*

### Still world-readable in the current tree, before the repo turns private

| # | What | Where | Priority |
|---|---|---|---|
| 1 | The three real names, with the mapping | `docs/slices/015-repo-hygiene/03-implementation-notes.md:49-51` | Before push (Blocker 1) |
| 2 | A named real client with turnover and headcount, and a named sponsor | `New_req.md:12, 524, 620, 630` | Before going private |
| 3 | Grace Group named as a real client across other docs | `ARCHITECTURE.md`, `GRACE_USER_MANUAL.md`, `REBRAND_*.md`, `order_tracking.md`, `hrms/Grace_Group_Vendor_Portal_UseCase.md`, `hrms/Grace_HRMS_Design_Theme_Guide.md` | Decide once: is naming them agreed, or not? Then apply it everywhere |
| 4 | The malware on two branch tips | see above | **Today** |
| 5 | The `docs/product/legal/` templates (a DPA and an employee privacy notice) | untracked today; deliberately not ignored | Read them before the first commit. A DPA draft can carry a counterparty name |

Nothing else in the current tree looks exposed. I re-ran the scan's own checks on this
branch: no public IP addresses outside the private ranges, no old password literals, no
brochure, no `init.sh.orig`.

---

## 4 · Is a history rewrite needed?

**My recommendation: do not rewrite. Rank it below four cheaper things that matter more.**

Why not:

- **No real key is in history.** The scan checked every added line of all 484 commits
  for provider key formats, private keys, high-entropy strings and risky file names, and
  GitHub's own secret scanning shows zero alerts. What is in history is three demo
  passwords, all three of which have now been changed on the tenants, so the history
  copies are dead values.
- **A rewrite does not retrieve anything.** The material was public for about eleven
  weeks. Copies, forks and clones cannot be recalled. Old commits also stay reachable on
  GitHub by their ID until GitHub support purges them, so even a perfect rewrite leaves
  a gap you cannot close yourself.
- **It is expensive here.** Every commit ID changes. That breaks every worktree, every
  slice branch, and every parallel session — and this repo has several running at once,
  with unpushed work in the main checkout and twelve unpushed slice-014 commits on local
  `dev`. The risk of losing someone's work is higher than the risk it removes.

If it is done anyway, here is the shape:

- **What it would cover:** the brochure blob, the three real names, the three demo
  passwords, the origin IP, and the three malicious `postcss.config.js` blobs — with the
  malware evidence kept as a local archive ref first.
- **When:** after the repo is private, after the malware branches are deleted, after all
  rotations are done, with **every session stopped and every worktree closed**, in one
  planned window, on a fresh mirror clone, with the old mirror kept as a backup until it
  is proven good.
- **The risks:** lost unpushed work; broken worktrees; branch protection and open PRs
  needing rebuilding; GitHub still serving the old commit IDs; and a day of everyone
  being blocked.

**The two things I would do instead, today:** delete the two malware branches, and
rotate the list in §3. Those remove live risk. A rewrite only tidies dead risk.

**Not legal advice.** Whether Grace Group must be told that their brochure, their
directors' names and their business figures were published in a public repository for
about eleven weeks — with invented performance ratings attached to the named
individuals — is a question for counsel or for the relationship owner. The question to
put, because it is the one that decides whether a rewrite is needed:

> *"We published a client's company brochure, three named directors, and their turnover
> and headcount in a public code repository from roughly 1 July to 18 September 2026.
> The directors' names were attached to invented appraisal scores. Do we have a duty to
> notify them or anyone else, and does the git history have to be purged?"*

**What it blocks:** the history-rewrite decision, and whether a notification clock is
already running.

---

## 5 · Claims in this review, and how each was established

| Claim | Status |
|---|---|
| The three passwords are gone from the current tree, and all three scripts fail closed | **verified by reading** the three files and the diff |
| `import sys` exists in `ppj_common.py`, so `sys.exit` works | **verified by reading** line 14 |
| The brochure, `init.sh.orig` and the origin IP are absent from the branch | **verified by reading** — `git ls-files` and `git grep` |
| The three real names are absent from the seed scripts and the four vibe-coding docs | **verified by reading** — `git grep` on the branch |
| The three real names are present in `03-implementation-notes.md:49-51` | **verified by reading** |
| "Chaitanya" and Grace Group business figures are present in `New_req.md` | **verified by reading** |
| The new CI step is blocking and runs on push/PR to `dev` | **verified by reading** `ci.yml` |
| The CI check misses four realistic password forms | **verified by running** the script's own compiled patterns against test strings, in memory, changing nothing |
| The stale branch `claude/pp-jewellers-hr-spec-yvmi2a` is gone and archived locally | **verified by reading** local refs — but whether GitHub really deleted it is **needs-a-check** (`git ls-remote`) |
| Two other `origin` branches carry the 32 KB malware at their tip | **verified by reading** the blobs in the local clone. Whether those branches still exist on GitHub is **needs-a-check** (`git ls-remote`) |
| The demo logins were changed on both dev tenants on 2026-09-18 | **needs-a-check** — I was told this, and I did not contact any server. Someone with desk access should confirm the old values no longer work |
| A3 — secrets rotated after the malware window | **needs-a-check**, and see §3: the window is probably still open |
| No real API key, token or private key is in the git history | **needs-a-check** — taken from the 2026-09-17 scan, which I did not repeat. The scan's own caveat stands: a proper tool (`gitleaks`) has still never been run here |
| Nothing in the slice touches a runtime permission, a DocType or personal data at run time | **verified by reading** the full diff |

---

## 6 · Residual risk

Nothing below is accepted yet. An accepted risk needs a name and a date in this table.

| # | Risk | Status | Owner | Date |
|---|---|---|---|---|
| R1 | Malware live at the tip of two `origin` branches; anyone building them runs a stealer | **Open — today's job** | Surbhi | — |
| R2 | Secrets exposed to the malware not rotated (A3), and the window runs to today, not to 18 August | **Open** | Surbhi | — |
| R3 | The real-name mapping published in this slice's own notes | **Open — fix before push** | Engineer, then Surbhi to confirm | — |
| R4 | The CI password check misses the dict-key and bare-`password` forms | **Open — fix before push** | Engineer | — |
| R5 | Every old value stays in git history and on GitHub; going private does not undo it | Cannot be undone without a rewrite, and only partly then | Surbhi to accept or reject | — |
| R6 | Grace Group named as a real client, with figures and a named sponsor, across several tracked docs | **Open** | Surbhi + counsel (question in §4) | — |
| R7 | Origin server reachable directly, bypassing Cloudflare; the firewall restriction is not done | **Open** | DevOps to plan, Surbhi to approve | — |
| R8 | Already-seeded sites still hold the real directors' names as employee records | **Open** — dev-stage data work, deliberately not done here | Surbhi | — |
| R9 | Non-seeded accounts on the dev tenants were not part of the 2026-09-18 password change | **Open** | Surbhi | — |
| R10 | `gitleaks` has still never been run against this repo; the new check is a narrow regex | **Open** — the scan's standing recommendation, not this slice | Security agent, next slice | — |

---

## 7 · What must happen before this branch is pushed

1. Fix Blocker 1 — take the name mapping out of `03-implementation-notes.md`.
2. Fix Blocker 2 — widen the CI check and re-prove it against all eight forms in §2.
3. Decide R1 and R2 first. They are live; the slice is not.

A push of local `dev` also carries the twelve unpushed slice-014 commits. That is
someone else's work and someone else's review, and it should be a separate, deliberate
decision.
