# Working alongside other sessions and developers

Read by every agent that changes code or tests: `hrms-fullstack-engineer` and
`hrms-test-automation-engineer`. It expands `CLAUDE.md` §1. (Written 2026-09-14.)

Several Claude sessions, and sometimes other developers, change this repository on the
same day. Treat that as the normal case, not the exception. Your job is to make sure
**no one's work is overwritten, dropped in a merge, or pushed without its owner's
knowledge** — including yours.

## What is shared, and why it bites

| Shared thing | What goes wrong | Seen |
|---|---|---|
| The main checkout `C:/Surbhi-Git/hr-app` | Every session's unsaved edits sit in the same folder. `git add -A`, `git stash`, `git checkout .` or `git reset --hard` there takes or destroys someone else's work. | 2026-09-11: another session's unfinished CLAUDE.md section, and its `field_checkin.py` and `hooks.py` edits, showed up in this session's `git status` and nearly went into its commit |
| The local bench `hrlocal-bench` | It runs code from the main checkout only (`alvoraa_portal/`, `hrms/`, `alvoraa_goals/` are mounted). Whatever is in that folder is what everyone is testing. | 2026-09-08: a hand-copied `subscription.py` mixed two sessions' work, and tests failed in a way that looked like a bug |
| `test_site` and `ppj.localhost` | Two test runs at once deadlock the database and fail for no real reason. | 2026-09-10: three suites run together gave false failures that were first reported as real |
| `origin/dev` | Pushes you did not see change the files under you. A quick second push cancels the first push's CI run. | 2026-09-07 and 2026-09-08: two sessions edited the same file; 2026-09-13: three commits never got their own CI run |
| The most-changed files | Two slices editing the same lines conflict, and a careless resolution silently drops one feature. | `hrms-employee.html` had 37 commits in 30 days |
| Forgotten worktrees | Work finished in a worktree but never brought into `dev` sits there unseen, and later looks like it was shipped. | 2026-09-14: three agent worktrees from 31 Jul–1 Aug still held 20 commits that never reached `dev` |

## 1. Start of work — before the impact analysis or test plan

1. `git fetch origin`, then `git log --oneline HEAD..origin/dev`. **Read the diff of
   every incoming commit** and say in your reply what came in (commits and files).
   Never absorb someone else's work quietly.
2. Run `git status` in the main checkout. **Every changed file you did not change
   belongs to someone else.** Do not stage it, revert it, reformat it or "tidy" it.
   List it in your notes as "another session's work in progress".
3. Read the work board, `.claude/work-in-progress.md` (git-ignored, so it lives only on
   this machine; create it if it is missing). It says who is working on what. Other
   developers on other machines cannot see it — for them, check
   `git log origin/dev --since="7 days ago" -- <files>` and **ask the user whether anyone
   else is working in those files.**
4. Work in a worktree — a separate working folder on its own branch, so your edits never
   mix with anyone's unsaved changes. `.claude/worktrees/` is git-ignored.
   - **Engineer, new slice:** create it.
     ```bash
     git worktree add .claude/worktrees/<slice-id> -b slice/<slice-id> origin/dev
     ```
     Or use the `EnterWorktree` tool.
   - **Test engineer:** work in the slice's **existing** worktree and branch (see the
     work board), so the tests travel with the code they prove. Do not start a second
     branch for the same slice.
   - `git worktree list` at the start of work, too. A worktree nobody claims on the board
     is not yours to delete — report it to the user.

## 2. The parallel-work check

The engineer adds it to `00-impact-analysis.md`; the test engineer repeats the
"who else is in them" part in `04-test-report.md`.

- **Files I will change**, and for each whether it is a hot file (section 6).
- **Who else is in them**: rows on the work board, incoming commits, other sessions'
  uncommitted edits, and what the user said about other developers.
- **The plan when there is overlap** — one of:
  - *Sequence*: the other change goes into `dev` first; you rebase on it, then build.
  - *Split*: you agree which part of the file each change owns, and neither touches the
    other's part.
  - *Ask*: both changes alter the same behaviour differently. That is a product decision,
    so the user decides.
- **The test that pins each existing feature you touch**, or the test you will add so a
  bad merge cannot drop it without CI failing.

Once the strategy is approved, **add a row to the work board**:

```markdown
| Slice | Worktree / branch | Files and areas | Bench in use | Started | Updated |
|---|---|---|---|---|---|
| 012-payslip-view | .claude/worktrees/012 · slice/012 | hr_api.py (get_payslip*), hrms-employee.html (#panel-payslip, ps* functions) | no | 2026-09-14 10:05 | 2026-09-14 11:30 |
```

Keep it current. Remove the row when the work is pushed or abandoned.

## 3. While you work

**Commit small and often in the worktree**, one logical change each. A committed change
can be rebased and recovered; an uncommitted one in a shared folder can be lost by
anyone.

**Rebase on `origin/dev` often** — at the start of every sitting, before testing on the
bench, and before handing off:

```bash
git fetch origin
git rebase origin/dev
```

A small conflict today is easy. A week of drift is where features get lost.

**Never, in the main checkout:** `git add -A`, `git add .`, `git commit -a`, `git stash`
without a path, `git checkout .`, `git restore .`, `git reset --hard`, `git clean`, or a
rebase or pull with `--autostash`. Each of these takes or destroys changes that are not
yours. **Stage by path.** When a file also holds someone else's uncommitted edits, stage
only your part: write your hunks to a patch and run `git apply --cached <patch>`
(`git add -p` is not available here).

**Never copy files** into the main checkout, the bench, or a container to "sync" them.
Code moves only through git commits.

**Do not change line endings, reformat, reorder or rename code** in a file unless that is
the task. Whole-file noise turns every parallel change to that file into a conflict.

## 4. Testing on the local bench

The bench runs the main checkout's `dev`, so the commits have to be in local `dev` for
the bench to run them.

1. Check the work board. If "Bench in use" is marked by someone else, wait or ask.
2. Check the main checkout has no uncommitted changes in the files you are bringing in.
   If it does, they belong to someone mid-test — stop and ask.
3. Bring the commits in without overwriting anything:

   ```bash
   git rebase dev                                        # in the worktree: on top of local dev
   git -C C:/Surbhi-Git/hr-app merge --ff-only slice/<slice-id>
   ```

   `--ff-only` makes no merge commit and refuses if `dev` moved in the meantime; rebase
   again and repeat. It can never discard someone's commit.
4. Mark "Bench in use" on the board, test, then clear it.
5. **One test run at a time** on the bench, across every session, whichever container it
   runs in. Check both, because neither check alone is enough:

   ```bash
   docker exec hrlocal-bench pgrep -af run-tests   # a run started inside the shared bench
   docker ps                                       # another session's own container
   ```

   `pgrep` inside `hrlocal-bench` **cannot see a session running in its own container**
   against the same `test_site`. Two sessions walked into this on 2026-09-19, one from
   each side.

6. **Claim the board before every run, including a single module.** The rule is not
   courtesy, it is what keeps the results honest:

   - **The Redis hook cache is shared by every container**, and it is rebuilt by whichever
     code ran last. A run started from `hrlocal-bench` runs the main checkout, so it
     silently strips another branch's hooks out of the cache that the other session's
     throwaway container is using. Their tests then fail for a reason that is not in their
     code — on 2026-09-19 three of slice 013's tests failed "ValidationError not raised"
     and passed alone straight afterwards.
   - **The database is shared too.** Concurrent runs deadlock each other's `tearDown`; one
     collision left a run dead on a lock timeout having executed nothing, and another
     deadlocked three teardowns.
   - **Both runs become untrustworthy, not just the other one.** A pass inside a disturbed
     window proves nothing. Re-run it properly rather than relying on it.

   Anything longer than one module: use a throwaway container with its own site, so it
   contends with nobody.
7. Anything that restarts the bench, changes its sites or data, or runs `bench use` affects
   every session. Say so on the board first, and ask the user if in doubt.
8. A fix found while testing is made in the worktree, committed, and brought in the same
   way. Never edit the main checkout directly to "just try something".

## 5. When a rebase or merge conflicts

1. **Stop writing new code.** Find out what the other side meant:
   `git log --oneline -3 -- <file>` and `git show <their-commit> -- <file>`.
2. **Keep both intentions.** Never resolve a whole file with `--ours` or `--theirs`. Never
   delete their lines to make yours work.
3. **Prove nothing was lost.** For every incoming commit that touched the file, check that
   the lines it added are still there:
   `git show <their-commit> -- <file> | grep '^+' | grep -v '^+++'`, then grep the
   resolved file for the key ones.
4. Run **the whole app's test suite**, not the modules you guess are affected. Their pin
   tests are what catch a dropped feature.
5. If the two changes want different behaviour, **stop and ask the user.** Do not pick a
   winner yourself.
6. Never undo a conflict by resetting `dev` past commits that are not yours. To take your
   own change back out, use `git revert`.

## 6. Hot files — how to edit them without clashing

| File | Rule |
|---|---|
| `alvoraa_portal/www/hrms-employee.html` (~17,000 lines, the most-changed file) | A new screen is its own block: its own panel, its own name prefix for functions and CSS (as `ac…` and `ai…` do), and one line in `switchPanel()`. Do not move, re-indent or rename existing code. Shared helpers (`gpFetch`, `api`, `switchPanel`, the design tokens) change only in a commit of their own that says so. |
| `hooks.py` | Lists such as `after_migrate`, `after_install`, `doc_events` and `scheduler_events`: one entry per line, yours added at the end with a comment. Never rewrite the block. On conflict, keep every entry from both sides. |
| `patches.txt` (in `hrms`, `alvoraa_portal`, `alvoraa_goals`) | Add at the end only. Never reorder or remove a line. On conflict, keep both lines, in commit order. |
| DocType JSON | One slice per DocType at a time — claim it on the board. If two slices must change one, resolve by hand keeping both sets of fields, check the JSON still parses, then migrate locally and confirm both sets exist. |
| Custom fields created by code (`after_migrate` installers) | A name prefix unique to the feature (e.g. `alvoraa_review_*`). The installer must be safe to run twice. |
| `subscription.py`, `tenant_api.py`, `hr_api.py`, `module_access.py` | Add a new function rather than change an existing signature. If a signature must change, fetch first, then grep every caller in the whole repository. |
| Shared test fixtures and `test_site` setup | Add your own records with names unique to your tests. Never change a fixture other tests rely on without running the whole suite. |
| `.github/workflows/`, `deploy/`, `CLAUDE.md`, `.claude/` | Not part of a feature slice. Change them only when the task is about them. |

## 7. Features must not disappear in a merge

**Every feature and every bug fix ships with a test that names it.** If an overlapping
change or a bad conflict resolution drops it, CI fails instead of a user finding out.
Examples already in the repo: `test_portal_call_paths.test_the_three_that_were_broken_stay_fixed`
and `test_portal_csrf.py`. A feature with no such test is not done — the engineer writes
it with the code, and the test engineer checks it exists.

## 8. Handing off and pushing

Pushing still needs the user's explicit word (`CLAUDE.md` §1). When it comes:

1. `git fetch origin`, rebase, bring the commits into local `dev` as in section 4, and run
   the whole suite once more.
2. List exactly what would be pushed: `git log --oneline origin/dev..dev`. **Mark each
   commit as yours or not.** If someone else's commits would go too, say so and ask —
   pushing `dev` pushes everything in it.
3. Push once, as one batch. Do not push again while that push's CI or deploy is running:
   a second push cancels the first CI run, and deploys queue behind each other.
4. Check that the newest CI run passed and that dev is running the new image.
5. Tell the user which files changed, so other sessions rebase before they carry on.
6. Clean up: remove the row from the work board, then
   `git worktree remove .claude/worktrees/<slice-id>` and `git branch -d slice/<slice-id>`.
   `git branch -d` refuses to delete a branch whose commits are not in `dev` — if it
   refuses, the work was not shipped. Stop and tell the user; never force it with `-D`.

## When to stop and ask

- Another session or developer is changing the same lines or the same behaviour.
- A conflict needs a choice between two people's intentions.
- A push would carry commits that are not yours.
- The bench is marked in use, or the main checkout holds someone else's uncommitted
  changes in files you need to bring in.
- You find a worktree or branch nobody has claimed.
