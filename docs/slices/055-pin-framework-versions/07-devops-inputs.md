# Slice 055 — Pin the framework versions (ALV-156)

DevOps inputs. **Advice only. Nothing here was deployed, no image was built, nothing was
pushed.** Every command in §5 is written for Surbhi to run or approve.

One artifact, one dated section per stage. Add a section; never rewrite an earlier one.

---

## §4 · Strategy — 2026-09-27

*Written after reading the Dockerfile, both workflows and the running containers.
Stage: the change is prepared on `slice/055-pin-framework-versions` and not pushed.*

### The answer first

**Production and dev are already running different framework code, from the same branch
name.** That is not a theory about drift; it is what the two servers report today.

| App | Production runs | Dev runs | `version-16` tip today | Same? |
|---|---|---|---|---|
| Frappe | **v16.34.0** (`c1f1e8e`, 15 Sep) | **v16.35.0** (`012667b`, 22 Sep) | v16.35.0 (`012667b`) | **No** |
| ERPNext | **v16.35.0** (`12cd563`, 15 Sep) | **v16.36.0** (`b30aa53`, 23 Sep) | v16.36.0 (`b30aa53`) | **No** |
| India Compliance | **v16.9.1** (`f309b0e`, 18 Sep) | **v16.10.0** (`93eca2f`, 24 Sep) | v16.10.0 (`93eca2f`) | **No** |
| Frappe CRM | *not in the image* | v1.84.0 (`0adc671`) | — (pinned tag) | n/a |
| Frappe WhatsApp | *not in the image* | `08bc1f6` (4 Aug) | — (pinned commit) | n/a |

**Fact.** Read on 2026-09-27 with `docker exec <backend> git -C apps/<app> log -1` and
`git describe --tags` inside `compose-backend-1` (production) and `devstack-backend-1`
(dev), over the Tailscale address, read-only. Upstream tips read the same day with
`gh api repos/<org>/<repo>/commits/version-16`. Tag→commit confirmed with
`gh api .../git/refs/tags/<tag>` — every running commit is **exactly** a release tag, not
a commit part-way between two, which is what makes tag pinning clean here.

Images: production `hr-app:prod-65878e8`, built **2026-09-20**. Dev
`alvoraa-app:dev-3bb22ac`, built **2026-09-27 06:09 UTC** — today, from the current tip of
`dev`. Both read with `docker image inspect --format '{{.Created}}'`.

### 🔴 P1 — the pin you write in the Dockerfile is ignored by CI today

**This is the finding that changes the shape of the work.**

`.github/workflows/build-image.yml` passed the versions again as `build-args`:

    build-args: |
      FRAPPE_BRANCH=version-16
      ERPNEXT_BRANCH=version-16
      CRM_TAG=v1.84.0
      WHATSAPP_COMMIT=08bc1f6af2e3

A `build-arg` **beats** the `ARG` default in the Dockerfile. So had anyone pinned
`deploy/Dockerfile` alone, the change would have looked applied, passed review, and done
nothing — every image would still have been built from `version-16`. **Fact**: read at
`build-image.yml:177-183` on `origin/dev` `3bb22ac`.

Note also that `INDIA_COMPLIANCE_BRANCH` was **never** in that list. That is how two
files came to disagree about three apps with nobody noticing.

There is a third place: `.github/workflows/ci.yml:313-314` sets its own
`FRAPPE_BRANCH: version-16` / `ERPNEXT_BRANCH: version-16` and builds a separate bench for
the Python tests. While that says `version-16`, **a red CI run can be caused by an
upstream commit nobody here made, and a green one proves nothing about the image.**

### What I recommend pinning to — and the one real conflict

**Tag, not commit.** Three reasons, and one of them is mechanical:

1. `bench init --frappe-branch` and `bench get-app --branch` pass the value straight to
   `git clone --branch`. **`git clone --branch` accepts a branch or a tag. It does not
   accept a bare commit.** So a commit pin needs the two-step dance already used for
   WhatsApp (clone a branch, then `git checkout <sha>`) — more moving parts, and the
   yarn install happens at the wrong state. **Fact**: read `App.__init__` /
   `get_app` in `/home/frappe/.bench/bench/app.py` inside `devstack-backend-1` today;
   line 189 is `branch = f"--branch {self.tag}" if self.tag else ""`.
2. `bench`'s own validation explicitly allows tags: `is_valid_frappe_branch` runs
   `git ls-remote --heads --tags <url> <value>` (**Fact**, same source, `utils/__init__.py:105`).
3. Every version now running sits **exactly on a tag**, so a tag loses nothing.
   A tag is also readable in a review; `012667b9c4e7` is not.

**A tag is almost as immutable as a commit, not quite.** Frappe has never moved a
released `v16.x` tag as far as I know, but a tag *can* be force-moved, and a commit
cannot. That residual risk is covered by writing the commit next to the tag in the
release notes (§5) so a rebuild can be checked, not by making the Dockerfile harder to
read. **[ASSUMPTION]** — I did not audit Frappe's tag history.

**Which versions?** This is the decision I most want Surbhi to make, because the ticket's
instinct and the evidence point different ways.

| | Option A — **dev's set** (my recommendation) | Option B — production's set (the ticket's instinct) |
|---|---|---|
| Pins | frappe `v16.35.0`, erpnext `v16.36.0`, india-compliance `v16.10.0` | frappe `v16.34.0`, erpnext `v16.35.0`, india-compliance `v16.9.1` |
| Has this combination ever run? | **Yes — dev, today, with the current tip of `dev`** | Yes on production, but **never with dev's 312 commits** |
| What ALV-137 then carries | our code + one upstream minor each | our code only, plus a framework **step backwards** from what dev proved |
| Risk it creates | one deliberate framework step, rehearsed | shipping a combination nobody has ever booted |

**Why I lean to A even though B sounds safer.** The ALV-137 release cannot be a framework
no-op whatever we choose: production's image has **no `crm` and no `frappe_whatsapp` app
at all** (Fact — `apps/crm` does not exist in `compose-backend-1`), and the release adds
both. So "change one variable at a time" is already off the table. Given that, the
combination that has actually been exercised beats the combination that has not.
Option B's appeal is real but it buys a *different* untested state, not a safe one.

**If Surbhi prefers B, it is a two-line change to the prepared branch and nothing else
moves.** Say the word and I will swap the three values.

### 🔴 P1 — one thing inside this choice needs eyes, whichever option wins

ERPNext **v16.36.0 adds three patches** that Frappe's migrate will run on every site,
including production:

    erpnext.patches.v16_0.enable_serial_no_wise_valuation
    erpnext.patches.v16_0.add_voucher_index_to_repost_item_valuation
    erpnext.patches.v16_0.mirror_select_perms_to_custom_docperm

**Fact** — read from `gh api repos/frappe/erpnext/compare/v16.35.0...v16.36.0`, the diff
of `erpnext/patches.txt`, today. Frappe v16.34.0→v16.35.0 changes **no** patches (same
method).

The third one writes **Custom DocPerm** rows. This project has two live pieces of work
about exactly that table — slice 047 (ALV-117 feedback permissions) and slice 048
(permission freeze check). **I have not read what that patch does.** It is already on dev,
so this is not a reason to prefer B; it is a reason to name it in the ALV-137 rehearsal and
to have the security engineer read it. `[Unknown — I could not check the patch body.]`

I did count the size of each step: frappe 106 commits / 86 files, erpnext 105 / 258,
india-compliance 99 / 117 (Fact, `gh api .../compare/...`, today). These are ordinary
weekly releases, not a version jump.

### Which world are we in — is pinning itself risky?

**Low risk, and the window is closing.** Production's image is 7 days old and one minor
behind on each app. Dev was rebuilt **this morning** and already sits on the tips. So:

- Pinning to Option A locks in what dev has today. Nothing on dev moves. Production moves
  one minor per app when ALV-137 ships — which it would do anyway on the next rebuild, only
  without anyone choosing it.
- **Left unpinned, the next dev build already drifts again**, because upstream ships a
  release roughly weekly (three in the last ten days, from the tag dates above).
- The one real risk of pinning is the opposite of drift: **we stop getting upstream
  security fixes by accident.** They have to be taken on purpose now. §4.4 is the answer to
  that and it is not optional.

### The change, prepared

On branch `slice/055-pin-framework-versions`, worktree
`C:/Surbhi-Git/hr-app/.claude/worktrees/055-pin-framework-versions`, off `origin/dev`
`3bb22ac`. **Not pushed. Not merged. No image built.**

| File | What changed |
|---|---|
| `deploy/Dockerfile` | `FRAPPE_BRANCH` → `FRAPPE_TAG=v16.35.0`, `ERPNEXT_BRANCH` → `ERPNEXT_TAG=v16.36.0`, `INDIA_COMPLIANCE_BRANCH` → `INDIA_COMPLIANCE_TAG=v16.10.0`, with a comment block in the style of `CRM_TAG` / `WHATSAPP_COMMIT` saying why. The three `RUN` lines follow the rename |
| `.github/workflows/build-image.yml` | the whole `build-args:` block **removed**, replaced by a comment saying why it must stay removed |
| `.github/workflows/ci.yml` | the `test-python` job's `env:` pinned to the same two tags; the cache key, the `bench init` line and the `get-app` line follow the rename |
| `alvoraa_portal/.../tests/test_crm_feature_040.py` | one assertion string that quotes `${ERPNEXT_BRANCH}` |
| `scripts/check_version_pins.py` | **new.** Fails if any pin is not a tag or a full commit, if `ci.yml` names a different version from the Dockerfile, or if a `build-args:` entry reappears |

**Why rename `..._BRANCH` to `..._TAG`.** A variable called `BRANCH` holding a tag is the
kind of quiet lie that costs a day. It also makes `check_version_pins.py` and any future
reader unambiguous. Cost: four extra one-line edits, all listed above.

**Measured today, in this worktree:**

    python scripts/check_version_pins.py --self-test    → 7/7 passed
    python scripts/check_version_pins.py                → OK (all five pins)

I also replayed the five Dockerfile assertions from `TestTheImageCarriesItPinned` by hand
against the edited file — all pass. **I did not run `bench run-tests`**: that test module
imports `alvoraa_portal`, which needs a bench, and I claimed no bench for this slice.

**Not wired into CI by me.** `ci.yml`'s lint job is a hot file that other sessions are
appending to. The one step to add, when someone owns it:

    - name: Version pins
      run: python scripts/check_version_pins.py

### The OPS rows

| ID | Recommendation | Why | Cost of ignoring | Level | Weight | Decision |
|---|---|---|---|---|---|---|
| **OPS-1** | Remove the `build-args:` block from `build-image.yml` in the same commit as the Dockerfile pin | A build-arg beats the `ARG` default | The pin looks applied and does nothing. The whole ticket silently fails | **P1** | Recommend | |
| **OPS-2** | Pin to Option A — frappe `v16.35.0`, erpnext `v16.36.0`, india-compliance `v16.10.0` | It is the only combination that has run with dev's code | We ship an untested mix, or keep drifting | **P1** | Recommend | |
| **OPS-3** | Pin `ci.yml`'s test bench to the same tags | CI must test the framework the image ships | A red build caused by upstream; a green build that proves nothing | **P1** | Recommend | |
| **OPS-4** | Add `scripts/check_version_pins.py` to the lint job | Three files must agree; they already did not | The same drift returns in a month, quietly | **P2** | Recommend | |
| **OPS-5** | Prove `bench init --frappe-branch <tag>` works before ALV-137, by dispatching **Build Image** on this branch | I read bench's source; I did not run it | A build failure discovered during a release instead of before one | **P1** | Recommend | |
| **OPS-6** | Have the security engineer read `mirror_select_perms_to_custom_docperm` before ALV-137 migrates production | It writes Custom DocPerm; slices 047/048 are about that table | A permission change lands on customer data unread | **P1** | Recommend | |
| **OPS-7** | Adopt the raising procedure in §4.4, with a named owner | Pinning stops drift *and* stops security fixes arriving | We sit on an old framework for a year and find out from a CVE | **P2** | Recommend | |
| **OPS-8** | Record the pinned tag **and its commit** in the release notes of every deploy | A tag can in principle be moved; a commit cannot | A rebuild that is not the software you released, undetectably | **P3** | Consider | |
| **OPS-9** | Keep `hrms` vendored and out of this mechanism | It changes only in a visible diff | — | **P4** | FYI | |

### §4.4 · How a pin gets raised later — the ALV-129 mechanism

Write it as a routine, because that is what makes it happen. **[ASSUMPTION]** on the
cadence and the owner: monthly and Surbhi, until she says otherwise.

1. **Someone looks, once a month.** `gh api repos/frappe/frappe/commits/version-16` and
   the same for erpnext and india-compliance. Also look at the release notes for anything
   marked a security fix. **Out of cycle**, a Frappe security advisory jumps the queue.
2. **One pull request raises the pins and nothing else.** Only `deploy/Dockerfile` and
   `ci.yml`. No app code in the same change — that is the entire point of the ticket. The
   description lists the tag, the commit, the commit count, and whether `patches.txt`
   changed in any of the three apps.
3. **CI proves the build.** A full `bench init` runs cold once (the cache key contains the
   tag), so expect a slow run. Then the normal test suite.
4. **Dev takes it first, on Surbhi's word.** Deploy to dev with migrations on, then leave
   it there for a working week. Someone uses the tenant. Dev is the only place a framework
   patch gets exercised before it meets a customer's data.
5. **Rehearse the migration on a copy**, per `REHEARSAL.md`, before production — always if
   `patches.txt` changed in any app, and always for ALV-137. Time it and write down how long
   it took.
6. **Tell the tenants (ALV-129).** The notice needs a version, a date and a plain sentence
   about what changes. That is only possible because the pin exists.
   The NFR budget asks for **≥ 72 hours notice** for planned maintenance
   (`nfr-budget.md` §3) — so the tenant notice goes out at step 4, not step 7.
7. **Production, on Surbhi's word, in a quiet window.** Never at month-end: payroll and
   attendance close then.
8. **Write the tag and commit in the release notes.** Next month starts from there.

### §4.5 · What pinning does NOT protect against — honestly

- **Pinning to something broken.** A pinned bad version is a bad version you keep. The
  protection is step 4 above, not the pin.
- **Old software.** The pin will rot if nobody raises it, and an unpatched framework is a
  security problem. This trade is real: we swap *silent change* for *deliberate staleness*.
  Only OPS-7 closes it.
- **The other three-quarters of the image.** `frappe/bench:latest` is the base image and is
  **still a moving tag** (`deploy/Dockerfile:24`). So are the Debian packages, the pip
  dependency tree inside each app, and every yarn package. Two builds of this commit can
  still differ — just not in the framework. **Out of scope for ALV-156, and worth its own
  ticket.** `[Not fixed by this change.]`
- **The sites volume.** A deploy does not refresh `sites/assets` by itself, so what a
  browser downloads can be older than what the image contains (already known, see the repo
  memory on stale assets). A framework pin says nothing about that.
- **`hrms`.** Vendored, so unaffected either way.
- **A tag being force-moved upstream.** Small, and mitigated by OPS-8, not by the pin.

### §4.6 · The NFR dimensions

| Dimension | Effect | Note |
|---|---|---|
| **Reliability** | **Improves, clearly** | A build becomes reproducible. A customer bug can be reproduced on the software they actually run. A rollback rebuild gets the old software back |
| **Maintainability** | **Improves** | One file owns the versions, and a check enforces it. Against that: someone must now raise the pins on purpose |
| **Security** | **Mixed, and say so** | Supply chain improves — `nfr-budget.md` §4 asks for "pinned dependencies", which this partly delivers. But upstream security fixes now need a human. OPS-7 is the control, and without it this row is a **downgrade** |
| **Performance** | Neutral | Same code, same size. One cold CI bench build per bump (15–25 min, per the comment at `ci.yml:289`) |
| **Scalability** | Neutral | |
| **Data integrity** | Neutral in itself; **the ERPNext patches are the live item** (OPS-6) | |
| **Compliance / privacy** | Small improvement | "Which version processed this person's data on that date" becomes answerable — useful for a DPDP or ISO questionnaire |
| **Release path** | **Improves, and this is why it goes first** | ALV-137 is 312 commits. Pinned, that release changes our code and a named framework step. Unpinned, it changes our code and *whatever upstream did that morning* |

### §4.7 · What could still go wrong with this change

| If | Then | What to do |
|---|---|---|
| `bench init` rejects a tag | The image build fails at step 1 | Fallback, already proven for WhatsApp: init on `version-16`, then `git -C apps/frappe checkout v16.35.0`. Prove which we need with OPS-5, before ALV-137 |
| A detached HEAD upsets a later bench step | Build or migrate oddity | Evidence it is fine: `crm` is already at a detached tag in the running dev image, and that stack is healthy (Fact, today) |
| Someone raises the Dockerfile but not `ci.yml` | CI tests a different framework | `check_version_pins.py` fails the build (OPS-4) |
| This lands on `dev` while another slice is mid-rebase | Conflict in `ci.yml` | My edit is in the `test-python` job's `env:`; slice 046 appends to the **lint** job. Different region, but say so at merge time |
| The change reaches `main` before a dev build has proved it | A release that cannot build | Dev build first. Always |

### §4.8 · Release path for this slice — commands, for Surbhi to approve

**None of these were run.** They are quoted, not reported.

    # 1. Land on dev (Surbhi's word), from the worktree
    git -C .claude/worktrees/055-pin-framework-versions fetch origin dev
    git -C .claude/worktrees/055-pin-framework-versions rebase origin/dev
    # then, in the main checkout, on dev:  git merge --ff-only slice/055-pin-framework-versions
    #                                      git push origin dev

    # 2. The build is automatic on a push to dev. Watch it:
    gh run watch --exit-status

    # 3. Prove the image really got what we pinned (the check that matters)
    ssh root@100.127.29.62 \
      'docker exec devstack-backend-1 bash -lc "for a in frappe erpnext india_compliance; \
         do printf \"%-18s\" \$a; git -C apps/\$a describe --tags; done"'
    # expect: v16.35.0 / v16.36.0 / v16.10.0

**Rollback for this slice is cheap:** revert the commit on `dev` and let the next build
run. No data changes, no migration. If a deployed dev stack must go back immediately,
redeploy the previous tag with migrations off:

    gh workflow run Deploy --ref dev \
      -f environment=dev -f image_tag=dev-3bb22ac \
      -f image_package=alvoraa-app -f run_migrations=false

`dev-3bb22ac` exists in `alvoraa-app` — it is what dev is running right now (Fact, read
from `docker ps` today). **Production is not part of this slice.** Production's framework
only moves when ALV-137 ships, and that is its own decision with its own rehearsal.

Expect the deploy to waste about 7 minutes on the `bench version` wait loop that is known
to crash on our image — that is pre-existing, not caused by this change.

### What I touched, and what I left alone

- **Wrote:** the five files listed above, in my own worktree only. One appended row on
  `.claude/work-in-progress.md` in the main checkout.
- **Server:** read-only. `docker ps`, `docker image inspect`, `docker exec … git log/describe`,
  and reading bench's own source inside `devstack-backend-1`. **Nothing was started,
  stopped, written or restarted. Nothing under `/var/www/html/hr-app` was touched.
  `deploy/server.env` was not read.**
- **Left alone:** `hrlocal-051`, site `test051`, and the worktrees `051-salary-screen`,
  `052-hr-optional-tenant`, `053-languages`, `054-upstream-wrappers`.
- **Left behind:** nothing. No container, no file on the bench, no changed site setting.
- **No secret** appears in this document.

### The label on the gap this leaves

**Intentional trade-off.** The base image `frappe/bench:latest` stays moving, and the pip
and yarn trees stay unpinned. Fixing those is a bigger change (a digest-pinned base, a lock
file discipline) and does not belong in the release path of ALV-137. **It should be a
ticket today, not a memory.**

### Sources and when I read them

| What | How | When |
|---|---|---|
| Running versions, production and dev | `docker exec … git -C apps/<app> log -1 / describe --tags`, over Tailscale, read-only | 2026-09-27 |
| Image build dates | `docker image inspect --format '{{.Created}}'` | 2026-09-27 |
| `version-16` tips, tag→commit, release diffs, `patches.txt` | `gh api` against `frappe/frappe`, `frappe/erpnext`, `resilient-tech/india-compliance` | 2026-09-27 |
| bench accepts a tag | `bench/app.py` line 189 and `bench/utils/__init__.py` line 105, read inside `devstack-backend-1` | 2026-09-27 |
| The three places the version is named | `deploy/Dockerfile`, `.github/workflows/build-image.yml`, `.github/workflows/ci.yml` on `origin/dev` `3bb22ac` | 2026-09-27 |
| The check script's own results | run in this worktree | 2026-09-27 |
