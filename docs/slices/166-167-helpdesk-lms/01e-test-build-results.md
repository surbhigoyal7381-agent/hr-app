# Throwaway build results — ALV-166 Helpdesk, ALV-167 LMS

**Author:** hrms-fullstack-engineer · **Date:** 28 Sep 2026 · Approved by Surbhi on
28 Sep 2026 to answer the P1 blocker in `01d-devops-first-look.md`.

**What this is:** a one-off, disposable container test. Nothing here touched
`hrlocal-*`, the main checkout, dev, or production. No server commands were run
against anything shared. The container, its throwaway MariaDB/Redis and the network
were all removed at the end of this session; only this document and the logs it
quotes survive.

**Base image used:** `alvoraa-app:local-042` (present locally, contains Frappe
`v16.35.0`, ERPNext, HRMS, CRM, india_compliance, frappe_whatsapp, alvoraa_goals,
alvoraa_portal — confirmed by `git describe --tags` inside the image before starting).

---

## 1 · Pins re-verified today (28 Sep 2026) via the GitHub API

All four pins from `01d-devops-first-look.md` still exist, unchanged:

| App | Pin | Verified sha |
|---|---|---|
| Payments | `version-16` branch | `cca07d9f9392e2ea0e521c5975151db9e4b6c321` |
| LMS | `version-16` branch, commit `87168fc7` | `87168fc7b2f24559e474ea4702cf1aa63b0db4e8` |
| Helpdesk | tag `v1.30.1` | `1c3361cc0019deec6f84035a9352270b4e4eb5cb` |
| Telephony | `develop` branch, commit `039cf39f` | `039cf39f245d6818ead03cf94eea6ce7f9c1e1f7` |

Fetched inside the container with `bench get-app --branch <branch> <app> <url>` land
exactly on these commits with no extra checkout step needed — `git log -1` inside each
app folder after `get-app` matched the pinned sha character for character. Helpdesk's
`v1.30.1` tag also resolved to the same commit.

## 2 · Pass/fail per app

| App | get-app | build | Result |
|---|---|---|---|
| Payments | OK, 22s | included in get-app, no separate frontend | **Pass** |
| LMS | OK | Vite build succeeded, `✓ built in 2m34s` | **Pass** |
| Telephony | OK, 16s | no frontend, esbuild only, 853ms | **Pass** |
| Helpdesk | OK | Vite build (desk) succeeded, `✓ built in 1m42s` | **Pass** |

All four `bench get-app` commands, which each also ran `bench build --app <name>` as
part of the fetch, exited 0. No manual retry, no patch, no workaround was needed for
any of the four.

## 3 · The P1 question — does the `frappe-ui` git submodule matter?

**No. It is not used by the build, in either app.**

Both LMS and Helpdesk declare a `frappe-ui` git submodule in `.gitmodules`
(`path = frappe-ui`, pointing at `github.com/frappe/frappe-ui`). After `bench get-app`,
that folder exists but is **empty** — 0 files — in both apps. `bench get-app` does not
run `git submodule update --init` and I did not need to run it either, because:

- LMS's `frontend/package.json` lists `"frappe-ui": "1.0.0-beta.29"` as a normal
  **npm dependency**. `yarn install` inside `frontend/` pulled it from the npm
  registry into `frontend/node_modules/frappe-ui` (a real, populated package — 14
  top-level entries, not a symlink to the empty submodule).
- Helpdesk's `desk/package.json` lists `"frappe-ui": "1.0.0-beta.24"` the same way, and
  `desk/node_modules/frappe-ui` is likewise populated from npm.

The Vite build reads `frappe-ui` from `node_modules`, never from the submodule path,
so the empty submodule folder is silently irrelevant. The devops doc's P1 fear — a
missing-module Vite failure that looks like a code problem — **did not happen, and
would not happen even with the submodule left uninitialised.**

**Recommendation for the real Dockerfile change:** no `git submodule update` line is
needed for either app. This removes one of the two items the devops doc listed as
"must-answer-before-Dockerfile." I would still add a one-line comment in the Dockerfile
next to the `LMS_COMMIT`/`HELPDESK_TAG` ARGs saying *why* no submodule step is there,
so a future engineer bumping the pin doesn't "fix" a problem that doesn't exist.

## 4 · `required_apps`, read from the fetched `hooks.py` files

Matches the devops doc exactly:

- `apps/lms/lms/hooks.py`: `required_apps = ["frappe/payments"]`
- `apps/helpdesk/helpdesk/hooks.py`: `required_apps = ["telephony"]`
- `apps/telephony/telephony/hooks.py`: `# required_apps = []` (commented out, i.e. none)

Install order used — `erpnext → hrms → payments → lms → telephony → helpdesk` — worked
with a single `bench --site test.local install-app <list>` command, in that order, no
errors.

## 5 · Build times (measured, this container, this run)

| Step | Time |
|---|---|
| `get-app` payments (incl. build) | 22.1s |
| `get-app` lms (incl. yarn install + Vite build + translations) | 9m 12.9s |
| `get-app` telephony (incl. build) | 16.4s |
| `get-app` helpdesk (incl. yarn install + Vite build + translations) | 3m 39.0s |
| `bench new-site` | 54.1s |
| `install-app` all six apps together | 3m 51.7s |
| **Total, cold, this container** | **~18.5 minutes** |

This is lower than the devops doc's +30–50 min interpolated estimate for a cold build
touching both apps — but it is **not directly comparable**: this run had warm yarn/pip
caches already present in the base image's Python env and no Docker layer/BuildKit
overhead, and it skipped the CRM/ERPNext/HRMS build steps entirely (those apps were
already built into the base image). The real Dockerfile build starts from a clean
runner each time, so **the devops estimate should still be the one used for CI-minutes
planning**; treat this 18.5 minutes as a lower bound, not the number to budget from.

## 6 · Image-size delta (measured, `du -sh` inside the container)

| What | Size | Counts toward final image? |
|---|---|---|
| `apps/payments` | 892 KB | Yes |
| `apps/lms` (source + `frontend/node_modules` 762 MB + built `public/` 79 MB) | 1.1 GB | Yes — the Dockerfile does not strip `node_modules` (checked: no such step exists today) |
| `apps/telephony` | 696 KB | Yes |
| `apps/helpdesk` (source + `desk/node_modules` 421 MB + built `public/` 52 MB) | 522 MB | Yes |
| **Apps subtotal (what ships in the image)** | **~1.62 GB** | — |
| Yarn's global download cache (`~/.cache/yarn`) | 3.1 GB | **No** — the real Dockerfile mounts this as a BuildKit cache (`--mount=type=cache,target=/home/frappe/.cache/yarn`, same pattern already used for CRM/WhatsApp), so it never lands in an image layer. This container built without that mount, so the 3.1 GB shown here is a build-time artefact only, not a shipping cost. |
| Python `env/` (site-packages) | 710 MB total after all installs | Baseline-dominated; the four apps are editable pip installs (`uv pip install -e`), which add almost no new files here |

**Bottom line: ~1.6 GB is the real, durable image-size delta for adding all four apps**
(Payments + Telephony are negligible; LMS and Helpdesk's own `node_modules` are the
bulk of it). This is consistent with the devops doc's "modest but real" qualitative
call, and confirms it was not an under-estimate.

## 7 · Site creation and app installs

A throwaway `mariadb:10.8` and `redis:alpine`, each in their own container on a private
Docker network (`hdlms-throwaway`), were enough to create a site and install every app.
No `hrlocal-*` container, volume or network was used or touched.

- `bench new-site test.local` — succeeded in 54.1s (scheduler disabled by default, as
  is normal for a fresh site; not started for this test).
- `bench --site test.local install-app erpnext hrms payments lms telephony helpdesk` —
  all six installed in sequence, **exit code 0**, 3m 51.7s.
- `bench --site test.local list-apps` confirms all six present:
  `frappe 16.35.0, erpnext 16.36.0, hrms 17.0.0-dev, payments 0.0.1, lms 2.63.0,
  telephony 0.0.1, helpdesk 1.30.1`.

  Note the LMS package version string is `2.63.0` even though this is the pinned
  `version-16` branch commit — that field comes from `lms/__init__.py`'s own
  `__version__`, unrelated to the branch name, and is not evidence of being on the
  wrong branch (the commit sha check in §1 is the authoritative proof).

## 8 · LMS Settings — the privacy defaults, confirmed live on a real site

Read via `bench --site test.local console`, not just the repo's JSON (closes the
devops doc's "Inference, not measured" gap):

| Field | Live default on this fresh install |
|---|---|
| `allow_guest_access` | **1 (ON)** — matches the devops doc's repo-read finding exactly |
| `disable_signup` | **1** — matches |
| `allow_job_posting` | **1** — matches |

**Proved the fix works:** set `allow_guest_access = 0` via `frappe.get_doc(...).save()`
(System Manager path, `ignore_permissions=True` since no user session existed in the
console), committed, and read it back — persisted as `0`. This confirms the DevOps
doc's recommended fixture (write `LMS Settings` with `allow_guest_access=0,
disable_signup=1, allow_job_posting=0` on install) is a normal single-doctype write,
nothing exotic, and will work the same way from a fixture or an `after_install` hook.

## 9 · `/lms` and `/helpdesk` respond

Started `bench start` inside the container only (gunicorn + socketio + scheduler +
watcher), waited 8s, then curled from inside the same container:

```
curl -H 'Host: test.local' http://localhost:8000/lms       → HTTP 200
curl -H 'Host: test.local' http://localhost:8000/helpdesk   → HTTP 200
curl -H 'Host: test.local' http://localhost:8000/app        → HTTP 301 (login redirect, expected)
```

Both apps' website routes serve through Frappe's own router with no separate app
server — this **confirms** (not just infers) the devops doc's §6 call that no new
nginx `location` block is needed for either app on a real deploy, provided the site's
own `test.local` (or the real tenant hostname) routing already works the way `ppj.dev`
etc. do today.

I stopped `bench start` (killed gunicorn/esbuild/socketio) immediately after this
check — it was not left running.

## 10 · Background queues — the other open item from §6 of the devops doc

Grepped both apps' own Python source for `enqueue(...queue=`:

- LMS: `queue="long"` (search index build, lesson progress recalculation) and
  `queue="short"` (transactional email)
- Helpdesk: `queue="long"` (search index build)
- Telephony: no `enqueue` calls with an explicit queue found

Both `long` and `short` are queues the existing compose stack's `worker-default`
(`default,short`) and `worker-long` already listen on. **No new worker is needed** —
this confirms the devops doc's inference with an actual grep, not a guess.

## 11 · What the real Dockerfile change will need — summary for the strategy stage

1. **No submodule step.** Confirmed unnecessary for both apps (§3). Add a one-line
   comment explaining why, not a `git submodule update` command.
2. **Pin exactly as recommended** in `01d-devops-first-look.md`: `PAYMENTS_COMMIT`,
   `LMS_COMMIT` as commits on `version-16`; `HELPDESK_TAG=v1.30.1`;
   `TELEPHONY_COMMIT` on `develop`. All four re-verified today, still current.
3. **No new nginx location block, no new worker queue** — both confirmed live in this
   test, not just inferred.
4. **Image size:** budget ~1.6 GB durable growth. Node_modules for LMS's `frontend/`
   and Helpdesk's `desk/` account for nearly all of it (762 MB + 421 MB); neither
   Dockerfile step should be changed to strip them unless a later size crunch forces
   it — that would be a bigger, separate decision (the app expects its own built
   `public/` assets, which come from these `node_modules`, at runtime).
5. **The yarn cache mount matters.** Use the same `--mount=type=cache,target=/home/frappe/.cache/yarn`
   pattern already in the Dockerfile for these two `get-app` layers, or the 3.1 GB
   yarn download cache will land in an image layer instead of being discarded — this
   is exactly the CRM disk-exhaustion lesson already on record.
6. **The LMS Settings fixture is not optional** — §8 proves the write path works
   cleanly; ship it in the same commit that adds LMS to `provision_tenant.sh`, before
   any tenant can reach the app with guest access still on.
7. **Build time:** use the devops doc's +30–50 min interpolated estimate for CI-minutes
   planning, not this run's faster warm-cache numbers (§5) — they are not comparable.

## Cleanup performed

- `bench start` processes killed inside the container before removal.
- `docker rm -f hdlms-app hdlms-mariadb hdlms-redis`
- `docker volume rm hdlms-sites`
- `docker network rm hdlms-throwaway`
- No `hrlocal-*` container, the main checkout, dev, or production was started, stopped,
  or modified at any point in this session.
