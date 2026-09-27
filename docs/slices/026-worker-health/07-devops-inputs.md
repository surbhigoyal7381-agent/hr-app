# 026 · Worker health — DevOps inputs

**Advice only. Every Decision column is yours.**
Nothing here has been deployed, pushed or run against a server that changes it.

---

## §5 · Release readiness — 2026-09-19

### The recommendations

| ID | Recommendation | Why | Cost of ignoring it | Weight | Decision |
|---|---|---|---|---|---|
| **OPS-1** | Keep `restart: unless-stopped` and stop relying on it alone | It was already there on 10 Sep and **failed** — docker could not mount a root filesystem on a full disk, and gave up after one try | A false sense of cover. This is the belief that cost nine days | Recommend | |
| **OPS-2** | Add a health check to `worker-default`, `worker-long` and `scheduler` that asks redis whether this container has a live rq worker | Makes `docker ps` stop lying. Fails in all three shapes of 10 Sep: the exec cannot run, redis is unreachable or refusing writes, or the process is up but unregistered | "Up" keeps meaning nothing, which is the whole defect | Recommend | |
| **OPS-3** | Gate the deploy on `scripts/check_workers.sh` instead of `continue-on-error: true` | The existing step could not fail and nobody read it | A deploy can finish green with no worker on a queue | Recommend | |
| **OPS-4** | Run the same check every 15 minutes as a scheduled GitHub Actions job on the self-hosted runner | There were **no deploys** in those nine days. A check that only runs at deploy time would not have caught this | The nine-day gap stays open | Recommend | |
| **OPS-5** | Fail the deploy before the image pull if free disk is under 25 GB | The actual cause. Below ~20 GB docker cannot restart *anything*, so the recovery needs the disk the failure ate | The same outage, and the same inability to recover from it | Recommend | |
| **OPS-6** | Give dev's `REDIS_QUEUE` a database number (`/1`), as production has | Dev runs `redis://redis:6379` — no number — so cache and queue share database 0. A cache flush on dev silently deletes queued jobs | Queued work vanishes on dev with no error, and dev is where patches are proven | Recommend | |
| **OPS-7** | Cap container log size at 50 MB × 3 files | Not the cause on 10 Sep (largest log was 67 MB), but the other unbounded writer on the same partition | A second, slower route to the same full disk | Consider | |
| **OPS-8** | Leave redis on `appendonly yes` and `noeviction` | Turning durability off would have kept the workers alive on 10 Sep, at the price of losing queued jobs on any redis restart. Wrong trade for payroll and leave work | — | FYI | |
| **OPS-9** | Do **not** add anything that restarts a worker automatically (`autoheal` or similar) | A worker killed mid-job leaves half-done work. The contract in this repo is that scripts advise and a human decides | Slower recovery, deliberately | Recommend | |
| **OPS-10** | Confirm GitHub failure emails actually reach you before trusting OPS-4 | The whole signal rests on it. Settings → Notifications → failed workflows | A check nobody sees is the same as no check | Recommend | |

### What a dead worker does now

| Before | After |
|---|---|
| `docker ps` says "Up", forever | The container's own health check fails within ~3 minutes and `docker ps` says **"(unhealthy)"** |
| A deploy reports success | The deploy **fails** at "Background workers must be working", naming the queue and how many jobs are stuck |
| Nobody is told between deploys | The scheduled run fails within 15 minutes and GitHub emails it |
| Nothing recovers it | `restart: unless-stopped` still tries first; if the disk is the problem, the disk gate should have stopped the deploy before it got that bad |

**Nothing restarts itself beyond docker's existing policy.** That is on purpose
(OPS-9).

### How a human finds out — why this one and not the others

| Option | Why not |
|---|---|
| A scheduled Frappe job that writes an Error Log | **It cannot work.** The scheduler only *enqueues*; a worker executes. A dead worker can never run the job that reports it is dead |
| A systemd timer on the host | Works, but it is host configuration outside the repository, invisible in review, and needs a mail path the box does not have |
| `autoheal` container | Restarts unhealthy containers automatically. New third-party dependency, and it restarts mid-job. See OPS-9 |
| **A scheduled GitHub Actions job — chosen** | The runner is already on that box, the notification path already reaches you (that is how failed deploys arrive), it is in the repository where it gets reviewed, and self-hosted minutes are free on a private repo |

---

## What was proven, and where

### Proven on the running production host, read-only

| What | Result |
|---|---|
| The worker probe on the four live worker containers (production and dev), using the exact bytes from the compose file | **healthy** in all four |
| The same probe in a container that runs no worker | **unhealthy** — correct |
| The same probe with redis unreachable | **unhealthy** — correct |
| The scheduler probe on both schedulers | **healthy**; unhealthy with redis unreachable — correct |
| Cost of one probe | **0.77 s**, including `docker exec` overhead. At a 60 s interval that is about 1% of one core |
| `scripts/check_workers.sh compose` | **PASSED**, and correctly warned that the health checks are not deployed yet |
| `scripts/check_workers.sh devstack` | **PASSED**, and correctly reported dev's queue database as **0** (OPS-6) |
| The script against a project that does not exist | **FAILED**, exit 1 — correct |
| The script with the rq registration set renamed, so it sees no live workers | **FAILED** with *"queue 'default' has NO live worker. 97 jobs are waiting and nothing will run them."* — this is the message 10 September would have produced on day one |

The script was piped over SSH to `bash -s`. It was never copied onto the server,
and it only reads: `docker ps`, `docker inspect`, `docker top`, `printenv`,
`redis-cli` reads, `df`.

### Checked locally

- Both changed workflow files and the compose file parse as YAML.
- `bash -n scripts/check_workers.sh` passes.
- The health-check command was extracted **back out of the parsed compose file**
  before being tested, so what was proven is the exact string docker will run —
  not something retyped.

### Not proven, and only a real deploy will prove it

1. **That docker marks a worker `(unhealthy)` in practice.** The command is
   proven; docker running it on the interval is not. Same position as the nginx
   parse gate: the first deploy is its proof.
2. **The disk gate tripping.** There is 116 GB free, so it cannot be exercised
   honestly today.
3. **The scheduled workflow firing on cron**, and the email arriving (OPS-10).
4. **The deploy gate failing a deploy.** It passes today because the workers are
   healthy.
5. **Nothing was tested on the local bench.** Docker Desktop on this machine is
   down — `failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine`.
   No local stack was started, no container was killed locally.

### The one risk worth naming

The deploy gate can now fail a deploy **after** the code is already live and the
smoke test has passed. That is intended — a silent worker is what this slice is
about — but the "Rollback instructions" block will then print, and rolling back
is usually the wrong response. **Recommend**: if that happens, read the FAIL
lines first; a queue with no worker is nearly always fixed by recreating the
worker, not by rolling the release back.

---

## For the user to decide

1. **OPS-10** — does a failed GitHub Actions run actually email you? If not,
   OPS-4 is a dashboard nobody opens.
2. **Every 15 minutes, or less often?** Fifteen keeps the runner busy for a few
   seconds four times an hour. Hourly would still have caught 10 Sep 215 times
   over.
3. **OPS-7 (log rotation)** is the one change here that is not on the causal
   chain. It is two lines and it caps a real unbounded writer, but say if you
   want it dropped to keep this slice strictly to the incident.
4. **OPS-6** changes only the *example* env files. The real `deploy/envs/dev.env`
   lives on the server and is git-ignored — **changing it needs your say-so and a
   dev-stack restart.** Not done.
