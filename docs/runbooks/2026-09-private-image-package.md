# Moving the image to a private package — September 2026

**Advice and a plan. Every command marked USER needs your own hands. Nothing here
touches production until you release to `main`.**

Written 2026-09-22 (slice 033, plan A approved by you that day).

---

## 0. Answer first

**The image moves from `ghcr.io/surbhigoyal7381-agent/hr-app` (public) to
`ghcr.io/surbhigoyal7381-agent/alvoraa-app` (private).** Then, and only after
production has run from the new one, you delete the old package.

**Bad news first: the automatic dev deploy keeps using the old package until this
reaches `main`.** GitHub runs the Deploy workflow from `main`'s copy of the file,
whatever branch is being deployed (see `making-the-repo-private.md`, "The trap"). So
the proof on dev needs one deploy triggered by hand with `--ref dev`. Until the
release, every build is pushed to **both** packages so neither kind of deploy breaks.

Three things make the changeover safe:

| What | Where | Why |
|---|---|---|
| Push to both packages while `main` still reads the old one | `build-image.yml`, step "Which package does main's deploy read?" | The automatic dev deploy (main's workflow) keeps finding its image in `hr-app`. Stops by itself the moment `main` names `alvoraa-app`. |
| Copy the old releases into the new package | `build-image.yml`, step "Copy old releases into the new package" | A rollback to `prod-65878e8` or `prod-d99ba99` works from `alvoraa-app` like any other tag — before and after the old package is deleted. |
| Put the old pin back if a pull fails | `deploy.yml`, Deploy step | A failed pull must not leave the pin file naming an image the server does not have. |

---

## 1. Why a new package, and why this name

- The repository has been private since 18 Sep. The package was not: an anonymous
  token and manifest request both answered **200** on 22 Sep. Anyone could pull the
  image and read the application.
- **GitHub will not make a public package private again.** Its documentation: "Once you
  make a package public, you cannot make it private again." You tried the switch twice
  on 22 Sep; it stayed public.
- A package first pushed by a workflow "inherits the visibility and permissions model of
  the repository where the workflow is run" (GitHub docs, *Publishing and installing a
  package with GitHub Actions*, read 2026-09-22). This repository is private, so the new
  package is private from its first push, and linked to this repository, so the deploy
  job's own token can read it.
- **Name: `alvoraa-app`.** It is the product's name, not the repository's, so the image
  name no longer changes if the repository is renamed. It is not in use (the account
  had one container package, `hr-app`, on 22 Sep). It does not contain `hr-app`, so no
  old pattern can match it by accident — which is also why the disk clean-up in
  `deploy.yml` now names both.
- The image holds code, not client data. That is why this is careful rather than urgent.

---

## 2. What changed

| File | Change |
|---|---|
| `.github/workflows/build-image.yml` | `IMAGE_NAME` is `surbhigoyal7381-agent/alvoraa-app`. New changeover step (push to both while main reads the old name). New copy step for rollback tags. Trivy scan signs in (`TRIVY_USERNAME` / `TRIVY_PASSWORD`), because a private image cannot be scanned anonymously. |
| `.github/workflows/deploy.yml` | `IMAGE_NAME` is the new name. The plan job builds the full image reference once (`full_image`). New optional dispatch input `image_package` (`alvoraa-app` default, `hr-app` only as an escape hatch). Typed inputs reach the script through `env:`. The pin file is restored if the pull fails. The disk clean-up matches both names. Rollback text updated. |
| `deploy/envs/*.env.example` | Example `KINEXUS_IMAGE` uses the new name. |
| `deploy/Dockerfile`, `ARCHITECTURE.md`, `DEPLOYMENT_RUNBOOK.md`, `REHEARSAL.md` | Example image names. |
| `docs/runbooks/making-the-repo-private.md`, `docs/runbooks/2026-09-production-release.md` | Dated follow-up pointing here. |

`deploy/compose/*.yml` name no image — they read `KINEXUS_IMAGE` from the pin file.
`scripts/` names no image. Slice notes under `docs/slices/` are history and are left as
written.

---

## 3. Rollback — before, during and after

"Before" = today, until the release that carries this change reaches `main`.
"During" = after that release, while the old package still exists.
"After" = once you have deleted the old package.

| | Rollback to `prod-65878e8` | Rollback to `prod-d99ba99` |
|---|---|---|
| **Before** | Exactly as today. `main`'s workflow reads `hr-app`, where the tag lives. | Same. |
| **During** | Pulls the **copy** in `alvoraa-app`. Same digest as the one on the server, so the pull fetches almost nothing. | Same. |
| **After** | Same as During. The copy does not depend on the old package. | Same. |
| **Escape hatch** (a tag that was never copied) | During only: add `-f image_package=hr-app`. After: impossible — that release is gone. The deploy stops at the pull, puts the old pin back, and changes no container. | Same. |

Commands — **USER, for you to approve**. Code-only rollback, no migration:

```
# Before (main does not know image_package yet - do not pass it)
gh workflow run Deploy --ref main -f environment=production -f image_tag=prod-65878e8 -f run_migrations=false

# During and after
gh workflow run Deploy --ref main -f environment=production -f image_tag=prod-65878e8 -f run_migrations=false -f image_package=alvoraa-app
```

Swap `prod-d99ba99` for the other tag. If a migration ran, the backup restore in
`2026-09-production-release.md` §3.2 still applies — the package move changes nothing
about data.

**Before you delete the old package, both copies must be proven** (§6, check 3).

---

## 4. Proving it on dev (after the push to dev)

The push itself is yours to approve. After it:

1. **Build Image runs.** Its log shows the warning "pushing to BOTH packages" and the
   copy step prints `copied from surbhigoyal7381-agent/hr-app` for `prod-65878e8` and
   `prod-d99ba99`. The Trivy scan passes (it would fail with 401 without the sign-in).
2. **The automatic Deploy runs `main`'s old workflow and pulls `hr-app:dev-<sha>`.**
   That should pass — it is the reason for the dual push. It does not prove the new
   package.
3. **USER — the real proof, one hand-triggered dev deploy from dev's own workflow:**

   ```
   gh workflow run Deploy --ref dev -f environment=dev -f image_tag=dev-<sha> -f run_migrations=false
   ```

   `run_migrations=false` because step 2 already migrated this exact image.
4. **Checks (read-only):**

   ```
   # the package exists and is private
   gh api user/packages/container/alvoraa-app --jq '.visibility, .repository.full_name'
   #   expect: private / surbhigoyal7381-agent/hr-app

   # the copies exist
   gh api "user/packages/container/alvoraa-app/versions?per_page=100" \
     --jq '.[].metadata.container.tags[]' | grep -E '^(prod-65878e8|prod-d99ba99|dev-<sha>)$'

   # a stranger is refused
   curl -s -o /dev/null -w '%{http_code}\n' \
     "https://ghcr.io/token?scope=repository:surbhigoyal7381-agent/alvoraa-app:pull"
   #   expect 403
   ```

   **Read the 403 with the first check, not alone.** ghcr gives a stranger the same 403
   for a package that does not exist (tested 22 Sep with a made-up name). The 403 proves
   privacy only once the first check shows the package exists.

   In the hand-triggered run: the Parameters step prints
   `Image : ghcr.io/surbhigoyal7381-agent/alvoraa-app:dev-<sha>`; every step is green;
   on the server `docker ps --filter label=com.docker.compose.project=devstack` shows every
   app container on that one image and healthy; `dev.alvoraa.co` and
   `ppj.dev.alvoraa.co` answer 200 on `/api/method/ping`.

---

## 5. Production order

1. **The next release to `main` carries this change.** Nothing extra to do: the build on
   the `main` push sees that `main`'s workflow names `alvoraa-app` and pushes there only.
   The public package gets nothing new from this point.
2. **The automatic production deploy pulls `alvoraa-app:prod-<sha>`.** Watch the
   Parameters step for the new name.
3. **Verify** (read-only): every `compose-*` app container reports the same
   `alvoraa-app:prod-<sha>` image (lesson 2); `alvoraa.co`, `dtc.alvoraa.co`,
   `aahr.alvoraa.co` answer 200; the worker gate passed.
4. **Watch one more ordinary dev push** go through automatically. It proves the automatic
   path now reads the new package.
5. **Only then**, §6.

---

## 6. Deleting the old package — USER only

**Do not delete before §5 step 4.** Once deleted, nothing can pull from `hr-app`, and
GitHub keeps the name reserved for 30 days in case you restore it.

Checks first — every one must pass:

| # | Check | How | Must see |
|---|---|---|---|
| 1 | Production runs from the new package | On the server: `docker ps --format '{{.Names}} {{.Image}}' \| grep '^compose-'` | Every app container on `…/alvoraa-app:prod-…`. None on `hr-app`. |
| 2 | Both pin files name the new package | On the server, in `deploy/compose`: `cat .image.env .image.dev.env` | Both say `alvoraa-app`. |
| 3 | The rollback copies exist | `gh api "user/packages/container/alvoraa-app/versions?per_page=100" --jq '.[].metadata.container.tags[]' \| grep -E '^prod-(65878e8\|d99ba99)$'` | Both tags. |
| 4 | No build pushed to the old package after the release | `gh api "user/packages/container/hr-app/versions?per_page=5" --jq '.[] \| [.created_at, (.metadata.container.tags\|join(","))] \| @tsv'` | Newest version older than the release. |
| 5 | Nothing else still names `hr-app` | `grep -n KINEXUS_IMAGE deploy/envs/production.env deploy/envs/dev.env` on the server (reads only that key) | No line, or a line you have changed to `alvoraa-app`. The pin file wins today, but a stale line here is a trap for anyone running compose by hand. |
| 6 | The local bench no longer needs the old package | `docker images \| grep hr-app` on your machine | Anything you still need, re-pull from `alvoraa-app` after `docker login ghcr.io` with a personal token that has `read:packages`. Existing local images keep working. |

Then:

1. github.com → your profile → **Packages** → `hr-app`.
2. **Package settings** → **Danger zone** → **Delete this package**. Type `hr-app` to
   confirm.
3. If GitHub refuses: it will not delete a public package if any version has more than
   5,000 downloads. Then contact GitHub Support. I could not check the download count —
   the API does not report it for container packages.
4. Confirm it is gone:

   ```
   curl -s -o /dev/null -w '%{http_code}\n' \
     "https://ghcr.io/token?scope=repository:surbhigoyal7381-agent/hr-app:pull"
   #   expect 403 (it was 200)
   ```

Afterwards (optional, a small dev commit): remove the `hr-app` choice from
`image_package`, the `OLD_IMAGE_NAME` / `CARRY_TAGS` lines and the two changeover steps
from `build-image.yml`, and `hr-app` from the clean-up pattern in `deploy.yml` once no
`hr-app` image is left on the server. None of these is harmful if left — the changeover
steps already do nothing once `main` names the new package.

---

## 7. Decisions for you

| ID | Recommendation | Why | Cost of ignoring it | Recommend / Consider / FYI | Decision |
|---|---|---|---|---|---|
| OPS-1 | Push slice 033 to `dev`, then run one hand-triggered dev deploy with `--ref dev` | The automatic dev deploy cannot prove the new package until `main` has the change | The first real use of the new package would be the production release | Recommend | |
| OPS-2 | Carry this change in the next `main` release, not a release of its own | It only changes where the image lives; the dual push keeps every path working until then | Every build keeps publishing code to the public package until `main` has it | Recommend | |
| OPS-3 | Delete the old package only after §6's six checks | Once deleted, nothing can pull from it, and nothing can undo that within the day | A rollback or a stray reference fails with no way back | Recommend | |
| OPS-4 | Copy more old releases than the two named, if you want a longer rollback window | Only `prod-65878e8`, `prod-d99ba99` and whatever `main` points at are copied | Older releases disappear with the old package | Consider | |

---

## 8. Honesty notes

- **Checked 22 Sep:** the account's container packages (`hr-app`, public, linked to this
  repository); `prod-65878e8` and `prod-d99ba99` both in it; anonymous token and
  manifest for `hr-app` = 200; anonymous token for `alvoraa-app` and for a made-up name
  both = 403; that every recent Deploy run is `workflow_run` on `main`'s head
  (`65878e8`), including the dev deploys.
- **GitHub documentation read 22 Sep:** public packages cannot be made private; a
  package published by a workflow inherits the repository's visibility; a deleted
  package can be restored for 30 days and its name is held; public packages with more
  than 5,000 downloads of a version cannot be deleted.
- **Not tested by me:** the build and deploy themselves; `imagetools create` copying
  between the two packages; Trivy signing in with the job token. Section 4 is where each
  is first seen working.
- **Not read:** `deploy/envs/production.env` on the server (it holds secrets) — hence
  check 5.
