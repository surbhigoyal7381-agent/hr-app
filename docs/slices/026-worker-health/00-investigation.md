# Why the background workers died — 2026-09-10

**Date of investigation: 2026-09-19. Read-only, over SSH, on the production host.**
Nothing was changed on any server while writing this.

---

## The answer in one paragraph

**The disk filled up.** At 06:32 server time (CEST) on 2026-09-10 the 193 GB root
disk hit 100%. Redis writes an append-only file to that disk, so it stopped
accepting *writes* and began answering every command with an error. The workers
write a heartbeat to redis on every job and do not retry it, so both of them quit
within three seconds of each other. Docker's restart policy then fired and
**failed**, because restarting a container also needs disk. Docker could not even
record that the restart had failed, so its saved state still said "running" — and
that is why `docker ps` reported "Up 12 days" for the next nine days while the
containers were empty shells.

This was not a redis hiccup, not an out-of-memory kill, and not an eviction
policy. Each of those was checked and ruled out with evidence.

---

## The chain, with the evidence for each link

All of this is **proven** unless marked otherwise. Source: the docker daemon's
journal on the host, the kernel log, and `docker inspect`.

### 1 · The disk hit 100% — proven

```
Sep 10 06:31:17 systemd-journald: Failed to create new system journal: No space left on device
Sep 10 06:31:16 dockerd: Health check for container 9769910594c1 error:
                 OCI runtime exec failed: write /tmp/runc-process1328971004: no space left on device
```

Every container's health check was failing on "no space left on device" from
06:31 onwards. The cause of the fullness is already recorded in this repository:
`.github/workflows/deploy.yml` carries a comment saying 43 tagged images at
11.2 GB each took the disk to 100% on 2026-09-10 and hung three deploys. The
image-cleanup block at the end of that file was written in response.

### 2 · Redis stopped accepting writes — proven

The worker's own traceback, recovered from the daemon journal (docker could not
write it to the container's log file, because the disk was full — so dockerd
logged the log line it failed to write, which is how it survived):

```
redis.exceptions.ResponseError: MISCONF Errors writing to the AOF file: No space left on device
```

Redis runs here with `--appendonly yes` (set in `docker-compose.app.yml`). When
it cannot write that file it refuses writes. **Reads still worked** — which is
why nothing user-facing broke and nobody noticed.

### 3 · rq quit rather than retried — proven

The traceback runs `redis/client.py → retry.py → connection.py`, inside the
heartbeat write that rq performs on every job
(`set_current_job_working_time → connection.hset`). rq logged "found an unhandled
exception, quitting" and the process exited **1**.

Both workers died at the same moment:

| Container | Exited (UTC) |
|---|---|
| `compose-worker-long-1` | 2026-09-10 04:32:00 |
| `compose-worker-default-1` | 2026-09-10 04:32:03 |

(Server time is CEST, UTC+2, so 06:32 local. The earlier note that `worker-long`
died on 7 September was the container's *creation* date, not its death.)

rq 2.6.1, redis-py 7.1.1, Python 3.14.7 — read out of the running image.

### 4 · The restart policy fired and failed — proven, and this is the important part

`restart: unless-stopped` was **already** on every worker, through the shared
`x-app` anchor. It did fire:

```
Sep 10 06:32:01 dockerd: restarting container ... restartCount=1 restartPolicy="{unless-stopped 0}"
Sep 10 06:32:02 dockerd: restartmanger wait error: failed to mount :
                 mkdir /var/lib/docker/rootfs/overlayfs/34a95f...: no space left on device
```

A restart needs disk to mount a root filesystem into. There was none. The restart
manager gave up after that one attempt and never tried again.

**So "add a restart policy" was not the missing piece. It was already there, and
a full disk defeats it.** That is the single most useful thing learned here.

### 5 · Why `docker ps` lied for nine days — proven

```
Sep 10 06:32:01 dockerd: failed to process event ... error="write .../.tmp-config.v2.json: no space left on device" event=exit
Sep 10 06:32:01 dockerd: failed saving state on start failure: write .../.tmp-config.v2.json931080203: no space left on device
```

Docker keeps each container's state in `config.v2.json`. It could not write the
new state, so the file kept saying `Running: true`. `docker ps` reads that.
`docker top` asks containerd for the actual processes, and containerd had already
deleted the task — hence "container is not running" from `docker top` on a
container `docker ps` called "Up 12 days".

---

## What was ruled out, and how

| Suspected cause | Verdict | Evidence |
|---|---|---|
| Redis eviction policy dropping queue keys | **Ruled out** | `maxmemory` is `0` (no limit) and `maxmemory-policy` is `noeviction`, checked live on 2026-09-19. Frappe's requirement is met. |
| Out-of-memory kill | **Ruled out** | `OOMKilled: false` and `ExitCode: 1` on both containers. No OOM entries in the kernel log for that window. 11.9 GB RAM, 6.3 GB available today. |
| Connection timeout on a long job | **Ruled out** | redis `timeout` is `0` (never close an idle connection). |
| One redis serving both cache and queue | **Not the cause here, but a live risk** | Production separates them by database: cache `/0`, queue `/1`. **Dev does not** — `devstack-backend-1` has `REDIS_QUEUE=redis://redis:6379` with no database number, so both land in database 0 and a cache flush on dev would delete queued jobs. See `OPS-6`. |
| A deploy, backup or migration at the moment of death | **Ruled out as the trigger** | A dev deploy ran 04:12–04:28 local. The workers died at 06:32, two hours later, alongside every other container's health check failing on disk. |
| An rq or redis-py version bug | **Not needed** | The exception is redis telling the truth about the disk. No library bug is required to explain any of it. |

---

## What is still inference, not proof

1. **What exactly consumed the last few GB at 06:31.** The image pile-up is
   documented in `deploy.yml` as the cause of that day's 100%; the journal for
   that window was itself partly lost to the full disk
   (`Dropped 98146 similar message(s)`). High confidence, not proof.
2. **Whether the scheduler kept enqueuing throughout.** It survived
   (`compose-scheduler-1` has run since 7 September, verified with `docker top`),
   and 700 jobs did accumulate, which is consistent. Not separately proven.

---

## The state today, 2026-09-19 (measured)

- Disk: **116 GB free of 193 GB (40% used)**. Images 68 GB, 45 GB reclaimable.
- Redis: `noeviction`, no `maxmemory`, `appendonly yes`, `timeout 0`.
- Both production workers registered in `rq:workers` with fresh heartbeats.
- `default` queue drained from 700 → 505 → 122 over the course of this
  investigation. `short` and `long` empty.
- Every other container answers `docker top` — there are no other zombies in
  either stack.
- **No log rotation configured anywhere** (`/etc/docker/daemon.json` does not
  exist). Container logs were not what filled the disk — the biggest is 67 MB —
  but they are the other thing on that partition with no ceiling.
