# Slice 018 — test the nginx config before the deploy restarts nginx

**DevOps advice and one build. Nothing was pushed, no deploy was run, and no server
was changed. Written 2026-09-18.**

---

## §1 What was wrong

**One bad character in `deploy/nginx.conf` could take the live site down, and the
deploy had no way of noticing.**

- One nginx container, `compose-nginx-1`, serves production `alvoraa.co` **and**
  `dev.alvoraa.co`. Its config is bind-mounted from `deploy/nginx.conf`.
- `.github/workflows/deploy.yml` restarted that container twice per deploy — once at
  the end of the Deploy step, once in "Restore service" — and never ran `nginx -t`.
- nginx reads its config only when it starts. A config it cannot parse means it does
  not come back. Every site then serves nothing until a human logs into the server.
- Because the file is shared, **a dev deploy could do this to production.**

Slice 014 changes that file (real client address plus the wildcard certificate paths),
and a production release is next. So the gate goes in first.

---

## §2 What was built

One new script and three call sites. No change to nginx's behaviour, the certificates,
or anything the config says.

### `scripts/check_nginx_parses.sh <nginx.conf> [cert-dir]`

Runs `nginx -t` on one config file in a throwaway container and exits non-zero if
nginx refuses it.

| Choice | Why |
|---|---|
| `nginx:alpine`, the same tag `docker-compose.app.yml` runs | If that tag ever stops accepting the config, we hear it *before* the deploy recreates nginx with it. Already on the server, so nothing is pulled. |
| Certificate directory (`TLS_CERT_DIR`, `/etc/letsencrypt`) mounted **read-only** at `/etc/nginx/ssl` | nginx loads certificates during `-t`, so a typo in a certificate path fails like a syntax error. Slice 014 changes exactly those paths. |
| `--network none`, with every host name from the config stubbed in the container's `/etc/hosts` | nginx resolves `upstream { server NAME:port; }` while loading the config, so a plain `nginx -t` fails with "host not found in upstream" — a failure about the network, not the file. Borrowing the running nginx's network namespace would fix that, but the check would then be unable to run when nginx is down, which is exactly when it matters most. The names are read out of the file itself, so a new upstream is picked up with no list to maintain. |
| `--entrypoint sh`, not the image's normal start-up | One of the image's start-up scripts runs `sed -i` over `/etc/nginx/conf.d` — it tries to edit the file under test. The read-only mount stops it, but a check has no business writing to the config. It also drops eight lines of noise. |
| The container **proves its own mount** by comparing byte counts before testing | See §4. A missing mount leaves the image's own tiny default config in place, which always parses. A pass that means nothing is worse than no check at all. |
| `--rm`, both mounts read-only | Nothing is left behind and nothing can be written. |

It takes about two seconds and prints four lines plus nginx's own verdict.

### Where it sits in the deploy

| # | Where | What it tests | If it fails |
|---|---|---|---|
| 1 | **New step `nginx config must parse`**, the first step of the deploy job, before the backup | The exact bytes about to be deployed, read with `git show origin/<branch>:deploy/nginx.conf`. The checker comes out of the same ref. | The deploy stops in about twenty seconds. Nothing pulled, nothing swapped, nothing restarted. |
| 2 | Inside the `Deploy` step, right after `git checkout --detach`, **before `trap cleanup EXIT` and before `up -d`** | The file now on disk. Needed because the checkout has a `|| git checkout --detach origin/main` fallback, so the file on disk is not always the one step 1 proved. | The job exits with no trap installed, so nothing restarts nginx. The running nginx keeps serving the config it read at start. |
| 3 | The `Restore service` step, which runs `if: always()` | The file on disk, again | nginx is **not** restarted, and the log says so loudly. This was the last hole: that step restarts nginx even after a failed deploy. |

**Why `git show` and not the working tree in step 1.** At that point the tree is still
at the previous release, so the file on disk is the old one. Reading from the ref tests
the right bytes and touches nothing — and it works before the thirty-minute image pull.

**Why step 3 refuses to restart rather than trying.** A running nginx is serving happily
from the config it parsed at start-up. Restarting it with a bad file is what turns a
failed deploy into an outage on every hostname. The cost of not restarting is that sites
pointing at recreated containers stay at 502 until a human looks. Dev at 502 is cheaper
than production down.

**One case deliberately left alone.** The `cleanup` trap inside `Deploy` still restarts
nginx unguarded. By the time it can fire, the config on disk has already been checked
twice and cannot change during the run.

---

## §3 The dev pre-deploy backup — decided: take one

**Recommendation: back dev up too. Done in this branch — the `if: needs.plan.outputs.environment != 'dev'`
condition is removed from the Backup step.**

The argument for skipping it was time. It does not hold:

| | Number | Source |
|---|---|---|
| Dev sites volume | 169 MB | measured 2026-09-18 (read-only listing, release plan §5) |
| Free disk on the server | 43 GB of 193 GB (79% used) | `df -h /`, read-only, 2026-09-18 |
| Added time | **estimate** 1–2 minutes | based on the volume size against a dev deploy that takes about 35 minutes |

Against that: releases carry data patches that rewrite rows and cannot be undone — slice
014's `redact_field_checkin_error_logs` is one. **Dev is where a patch is proven before
production runs it.** Without a backup, a patch that eats dev data leaves nothing to
restore and nothing to compare against, so the bug is found on production instead.

The backup also captures `site_config.json`, which holds each site's encryption key. A
database dump alone cannot be restored without it.

**One thing to watch, not fixed here:** nothing prunes old backups in either stack's
sites volume. At 169 MB per dev set and 43 GB free that is months away, but it is real.
See OPS-3 below.

---

## §4 Proof — run by hand, on this PC, 2026-09-18

Every run used throwaway containers with `--rm`. **All were removed; nothing was left
behind, and nothing ran against any server.** Certificates were self-signed throwaways
in the scratchpad, laid out as `live/alvoraa-wildcard`, `live/alvoraa.co`, `live/alvox.in`
to match the real directory (verified read-only that those three exist on the server).

| Config tested | Result | nginx said |
|---|---|---|
| `origin/main:deploy/nginx.conf` — what production serves today | **PASS** | syntax is ok / test is successful |
| `origin/dev:deploy/nginx.conf` | **PASS** | syntax is ok / test is successful |
| local `dev:deploy/nginx.conf` — slice 014's version | **PASS** | syntax is ok / test is successful |
| slice 014's, with one semicolon removed | **FAIL**, exit 1 | `[emerg] directive "real_ip_header" is not terminated by ";" ... default.conf:47` |
| slice 014's, with `alvoraa-wildcard` misspelt in the certificate path | **FAIL**, exit 1 | `[emerg] cannot load certificate ... No such file or directory` |
| the mount guard, run the way Git Bash mangles it | **FAIL**, exit 3 | "container sees 1072 bytes, host file is different" |

**Bad news worth recording: the first version of this check passed everything, including
the deliberately broken file.** Git Bash rewrites paths inside a `docker run -v`
argument, docker accepted the result as an anonymous volume, nothing mounted, and nginx
cheerfully tested its own built-in config. A safety check that always passes is worse
than no check. That is why the container now compares byte counts before it tests
anything, and why the script converts paths and turns the rewriting off on Windows.

Also checked, read-only, on the server: nginx is 1.31.5 built
`--with-http_realip_module`, the running container's image is `nginx:alpine` and that
tag is already on the box, `TLS_CERT_DIR=/etc/letsencrypt` in both `production.env` and
`dev.env`, and `/etc/letsencrypt/live` holds `alvoraa-wildcard`, `alvoraa.co` and
`alvox.in`.

Also run: `python scripts/check_app_integrity.py`, and the workflow was parsed as YAML
with every step's shell checked by `bash -n`.

### What I could not prove without a real deploy

- **The gate has never run on the self-hosted runner.** The commands are the ones I ran
  by hand, but the runner's docker, its permission to read `/etc/letsencrypt`, and the
  `git show` against the freshly fetched ref are only proved by a real run.
- I did not run the check on the server. That means creating a container there, which is
  a server action and the user's to take. The release plan's **OPS-R1** is exactly this
  command for her hands.
- A `test` environment deploy would fail at the gate for a different reason:
  `deploy/envs/test.env` does not exist on the server (only `test.env.example`), so the
  certificate directory falls back to `/etc/letsencrypt`. That environment has other
  gaps already and is not in use.

---

## §5 Rows for the decision table

| ID | Recommendation | Why | Cost of ignoring it | Weight | Decision |
|---|---|---|---|---|---|
| OPS-1 | Merge this branch before the next production release | Today a bad `nginx.conf` takes every site down at the end of a deploy, and slice 014 changes that file | One missing character is a full outage that only a human on the server can end | **Recommend** | |
| OPS-2 | Keep the dev backup on (the `if` removal in the Backup step) | Dev releases carry irreversible data patches and dev is where they are proven | No rollback point for dev data; the patch bug is then found on production | **Recommend** | |
| OPS-3 | Give the sites volumes a backup retention rule in a later slice | Nothing prunes old backups in either stack, and dev now adds a set per deploy | Slow, quiet disk growth on a disk already 79% full | Consider | |
| OPS-4 | Still split dev's and production's nginx into separate containers and config files (a later slice, already raised as OPS-R10) | This gate makes the shared file safe to *parse*; it does not stop a dev change altering production's proxy | A dev decision keeps being able to change production's behaviour | Consider | |
| OPS-5 | Leave `ci.yml` alone for this | Slice 014's `scripts/check_nginx_conf.py` text check is already in the lint job, and a docker parse test in CI would need certificates that do not exist there | Duplicated checks, and a clash with the three other sessions editing `ci.yml` | FYI | |

---

## §6 Honesty notes

- Everything in §4 was **run**, on this PC, today. The three server facts are
  **measured** read-only over Tailscale.
- Timings are **estimates**: the gate at about two seconds from my local runs, the dev
  backup at one to two minutes from the volume size. Neither is measured on the runner.
- I did not run CI, the test suite, or any deploy. Nothing here touches Python that the
  bench executes, so no bench run applies.
- I did not touch `deploy/nginx.conf` (slice 014 owns it), `ci.yml`, or local `dev`.
