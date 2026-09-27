---
slice: 043-ai-email-leads
artifact: 07-devops-inputs
author: hrms-devops-engineer
date: 2026-09-24
status: draft
inputs: [CLAUDE.md, .claude/context/nfr-budget.md, .claude/context/handoff-contract.md, 01-product-brief.md, 01c-security-privacy-requirements.md, 02-functional-spec.md (§4, §11, decisions D-1 to D-7), deploy/compose/docker-compose.app.yml, .github/workflows/deploy.yml, scripts/check_workers.sh, alvoraa_portal/requirements.txt]
---

# 043 — DevOps inputs

Written after the spec, brief and security requirements (the user chose that order). §1 to §3 are below; §4 (strategy) and §5 (release) come later. Every row: **Recommend / Consider / FYI**, a priority (P0–P4), and a **Decision** column left blank for the user.

**Labels.** *Fact* = I read the file, or the number was measured on 24 Sep 2026 (server facts handed to me by the caller: one Contabo VPS, 6 cores, 11 GB RAM, ~5 GB free, no GPU, 129 GB disk free, 15 containers, load ~1.0, Frappe 16.35). *Estimate* = not measured, basis stated. `[verify]` = a price or vendor number from memory.

**Bad news first.**

1. **The Anthropic key will be inside every backup, on the server and in S3 if `BACKUP_BUCKET` is set.** Fact: `deploy.yml` lines 304–329 tar every `sites/*/site_config.json` into `sites/site-configs-<stamp>.tgz` and sync it off-site. D-1 puts the key in `site_config.json`. So the backup becomes a secret store. Not a blocker for the demo; a P1 for a paying tenant (OPS-9).
2. **One worker process serves `default` and `short` together, one job at a time.** Fact: `docker-compose.app.yml` line 272, `bench worker --queue default,short`. The mail pull itself runs on `short` (spec G-1). A burst of 200 intake jobs at ~10 s each is ~33 minutes of serial work, and during it every other `default`/`short` job — including the next mail pull — waits behind them (OPS-2, OPS-6).
3. **No egress allow-list exists.** Fact: grep of `deploy/` and the runbook for iptables, ufw, egress, allow-list found nothing. Containers can reach any host. This slice adds the first outbound call to a model provider; nothing on the box restricts where the key can be sent (OPS-11).

---

## §1 · Brief — first look (2026-09-24)

**What this slice adds to the running system.** No new Frappe app, no new container. It adds: one new outbound HTTPS dependency (the Anthropic API); one background job per inbound email on an intake mailbox; one more consumer of the existing scheduler (a daily purge; the backfill in slice two); two to five new keys in `site_config.json` per tenant (D-1; SEC-12, SEC-19, SEC-21); one new table (`Alvoraa AI Action Log`, one row per email, ~2–4 KB with `model_output`); and a new Python dependency — an HTTP client or the Anthropic SDK. Fact: `alvoraa_portal/requirements.txt` has neither `anthropic` nor `httpx` today, so the image must be rebuilt (the slice 040 path).

| ID | Recommendation | Why | Cost of ignoring | Level | Decision |
|---|---|---|---|---|---|
| OPS-1 | **Add the site-config ceiling (`alvoraa_ai_daily_call_ceiling`, SEC-19) to slice one**, even though the tenant cap is slice two (D-7). Read it at the top of the job; when hit, take the fallback path. | It is the only cost stop in slice one. Frappe pulls up to `initial_sync_count` (100–500) old mails on first sync, so "switch on" alone can fire hundreds of calls. | An unbounded bill from one spam flood or one mis-ticked mailbox. Estimate at Haiku-class prices: 500 emails ≈ ₹115 `[verify]` — small, but with no ceiling the number is "whatever arrives". | Recommend · P1 | |
| OPS-2 | **Run the intake job on `default` with `timeout=60`, and put the model call inside it with a 30 s HTTP timeout** (spec §11). Do not add a queue in slice one. | The compose file staffs only `default,short` and `long`. A new queue name with no worker is lesson 1: jobs wait for ever, and `check_workers.sh` cannot see a queue no container serves. | Silent queueing. | Recommend · P1 | |
| OPS-3 | **Rate-limit at the source: at most one call in flight per site, at most N calls per minute per site (default 20), enforced with a redis counter.** Backoff on 429/5xx per SEC-20 (3 tries, jitter, then leave the email for the next run). Towards IMAP: change nothing — Frappe's 10-minute pull and its "disable after 5 failures" rule stay as they are. | Anthropic returns 429 when a workspace's per-minute token limit is hit `[verify limits for the tier]`; with one worker process, a retry that sleeps blocks that process for every tenant. | Retries pile up in the one worker; the mail pull for every tenant stalls. | Recommend · P2 | |
| OPS-4 | **Idempotency key = (`site`, `Communication.name`).** Before the call, insert the log row with `outcome = "In progress"` under a unique index on `feature` + `reference_name`; a retried job that finds the row skips the call. Update the log and create the lead in one transaction. Never key on `message_id` alone — two accounts can pull the same message. | rq re-runs a job after a worker death; the spec's AC-24 covers two emails racing, not one job running twice. | Two leads, two model bills, one email. | Recommend · P1 | |
| OPS-5 | **Pin the new dependency to an exact version and rebuild the image before local testing.** Prefer the official SDK if it handles retries and tool-use parsing; either way pin it. | One image serves all sites; a floating version changes production silently on the next build. | A build that passes on the bench and fails on CI, or different behaviour per deploy. | Recommend · P2 | |
| OPS-6 | **Headroom on this box for a 200-email burst: fine on memory, tight on time.** Estimate: one rq worker holds ~200–350 MB; the model call is network-bound, near-zero CPU; the burst is serial (OPS-2), so peak added memory is one worker's, well inside the ~5 GB free (fact, 24 Sep). Time: ~33 min for 200 at 10 s each (estimate). The 15-minute p95 in spec §11 holds for a trickle, not a burst — say so in the spec. | Otherwise the first backfill will look like an outage. | A day when "the CRM stopped" is really 200 jobs queued behind each other. | FYI · P3 | |
| OPS-7 | **Do not host a model on this box** (agrees with D-2). Fact: no GPU, ~5 GB free of 11 GB, both stacks and mariadb already here. | A 7B model needs 5–8 GB RAM alone, quantised, and would starve mariadb and redis. | A production outage from memory pressure. | FYI · P0 if attempted | |

**Effort and run cost — estimate.**

| Item | Slice one | Slice two | Basis |
|---|---|---|---|
| Build effort | ~31 story points (spec §8: US-1, 2, 3, 4, 7, 10, 11, 12, 13, 15) ≈ 2–3 engineer weeks | ~15 points (US-5, 6, 8, 9, 14, 16) ≈ 1–1.5 weeks | The spec's own points; I did not re-size |
| Model cost per email | ₹0.20–0.25 Haiku-class; ₹0.70–0.80 Sonnet-class | same | 1,500 in + 250 out tokens; $1/$5 and $3/$15 per million tokens; ₹84/$ — all `[verify]` |
| Run cost per tenant per month | ≤ ₹1,500 at the 200/day cap on Haiku-class; realistic Sargam volume (~8 leads a week, maybe 40 emails a day) ≈ ₹300 | same | spec §11; brief §7 |
| Server cost | ₹0 extra | ₹0 extra | No new container or volume; the log table grows ~1 MB per 300 emails |
| Ops effort | Provisioning sets 2–5 site-config keys per tenant; one new CI gate (SEC-22) | Purge-job monitoring | |

**Second server for a local model — sizing note, order of magnitude, all `[verify]`.**

| Option | Spec | Fit for 200 emails/day | Monthly cost |
|---|---|---|---|
| CPU-only VPS | 8 vCPU, 32 GB RAM; 7–8B model, 4-bit | ~30–90 s per email at 1,750 tokens; OK for a trickle, not bursts; accuracy below hosted Haiku-class on messy mail (estimate) | €40–80 `[verify]` |
| Rented GPU | 1 × 24 GB GPU (L4 / A10 class), 8 vCPU, 32 GB | ~3–8 s per email; bursts fine | $150–400 `[verify]` |

Either needs its own patching, TLS, monitoring and a private link to the app box (Tailscale is already in use). It beats Anthropic on cost only above roughly 2,000 emails a day at Haiku-class prices (estimate: 2,000 × ₹0.23 × 30 ≈ ₹14,000 ≈ $165 a month). Below that the hosted model wins on cost and effort; the reason to switch would be data residency (01c Q-4), not money.

## §2 · Design — run-side notes (2026-09-24)

No `01b` exists; the screens are the CRM's own list, the lead page, `FCRM Settings` and `Email Account`. Nothing new is public. Page weight and 3G load time are unchanged by this slice. One row:

| ID | Recommendation | Why | Cost of ignoring | Level | Decision |
|---|---|---|---|---|---|
| OPS-8 | The `Alvoraa AI Action Log` list view must not show `model_output` (JSON) as a list column; keep it on the form. | 20 rows × 3 KB is fine; a report view with it selected is 60 KB a page. | A slow log list for the Sales Manager. | Consider · P4 | |

## §3 · Requirements — for the analyst to trace into ACs (2026-09-24)

| ID | Recommendation | Why | Cost of ignoring | Level | Decision |
|---|---|---|---|---|---|
| OPS-9 | **Treat the key in `site_config.json` as backed-up data.** (a) One Anthropic workspace key per tenant (SEC-12), so a leaked backup revokes one tenant; (b) rotate the key when a backup leaves the server or a tenant is offboarded; (c) the pre-deploy tgz and any S3 copy inherit backup retention — write that into the sub-processor and backup notes. Alternative for later: the key from an environment variable on the worker — **not** for slice one, because the compose env is shared by every site and would give all tenants one key. | Fact: `deploy.yml` 304–329 copies every site config into a tarball and, when `BACKUP_BUCKET` is set, to S3. Dev backs up too (slice 018). Frappe's own `bench backup` also writes a `site_config_backup.json` beside the dump `[verify on this version]`. | A key in an old backup nobody remembers, still valid. | Recommend · P1 for a paying tenant; P3 for the demo | |
| OPS-10 | **Provisioning sets the keys; nobody writes them from a session.** Deploy step, for the user to run later: `bench --site <site> set-config alvoraa_ai_api_key <value>` typed by the user, then a read-only check that prints only "set / not set", never the value. | Lesson 21. | A key in a chat transcript or a shell history. | Recommend · P1 | |
| OPS-11 | **State in the requirements that there is no egress allow-list, and name the one host the pipeline may call** (`api.anthropic.com`) as a constant, with a test that the client's base URL equals it. A firewall rule is later ops work and needs its own decision, because it also touches Brevo, IMAP hosts, ghcr.io and S3. | Fact: no outbound restriction on the box. A prompt-injected "call this URL" is stopped by SEC-1 (no tools), not by the network. | A false sense that the network stops a leak. | Consider · P3 | |
| OPS-12 | **Monitoring — four named alerts, one owner each:** (1) provider errors: ≥ 5 `AI_UNAVAILABLE`, or any 401/403, in an hour → ops alert (SEC-20 breaker); (2) queue depth: `check_workers.sh` already warns above 500 on `default` (fact, line 197) — add a warning at 100 for 30 minutes; (3) cost per day per site: `cost_inr` today ≥ 80 % of the ceiling → one notice; (4) review-queue age: oldest "Needs review" lead older than 2 working days → the reviewer, then the Sales Manager. Channel: the same as `worker-health.yml` (fact: hourly cron; failures email through GitHub) `[ASSUMPTION — a site-level check needs a new read-only endpoint or a scheduled job that writes an Error Log; the engineer says which]`. | nfr §8: named alerts, named owners. "AI refusal rate falling" does not apply — extraction only. | A dead key or a full review queue found by the customer. | Recommend · P2 | |
| OPS-13 | **Backup and restore of the new data:** the log table and the custom fields ride in the normal `bench backup --with-files` (fact: deploy.yml 312). Nothing extra. State in the spec that a restore from before switch-on loses log rows but not the Communications (they exist on their own). The purge job (AC-38) must respect a legal hold `[ASSUMPTION — 01c PRIV-5/6 defines it]`. | RPO ≤ 1 h (nfr §3); the pre-deploy backup is the only rollback point (fact). | A restore that quietly removes audit rows the DPDP log needs. | FYI · P3 | |
| OPS-14 | **Every AI call logs `latency_ms` and `cost_inr`; the daily purge runs on `long`** at 02:00 site time, never in a deploy window. | nfr §6 and §10; `long` has its own worker (fact, compose line 277). | The purge blocking the interactive worker. | Recommend · P3 | |
| OPS-15 | **Rollout:** local bench with a stub provider (fixed JSON, no network) → dev on `sargam.dev.alvoraa.co` with a real key on the demo mailbox only (D-6) → main. **Rollback:** the site-config switch `alvoraa_ai_enabled=false` (SEC-21) stops calls in seconds with no deploy — that is the real rollback and meets nfr §3's 15 minutes. Image rollback (redeploy the previous tag, migrations off — lesson 20) is for code defects only; the custom fields and the log table stay and are harmless with the feature absent from `features`. | A rollback that needs a 40-minute deploy to stop a bill is not a rollback. | Money spent while the deploy loop waits its 7 minutes (lesson 22). | Recommend · P2 | |
| OPS-16 | **Timing:** never switch a tenant on during a deploy or a month-end run; the first sync can queue hundreds of jobs on the shared worker (OPS-2). | Lessons 15–16: a long queue and a dead worker look the same from `docker ps`. | Payroll-week jobs stuck behind a mailbox backfill. | FYI · P3 | |

## Open questions

| # | Question | Owner | Blocks |
|---|---|---|---|
| OQ-A | Ceiling in slice one (OPS-1) — yes or no? | Surbhi | The engineer's `00`; whether slice one may touch a real mailbox |
| OQ-B | Is `BACKUP_BUCKET` set on production and dev, and what is its retention? **I could not check that** (no server access in this task). | Surbhi / ops | OPS-9's real exposure |
| OQ-C | Anthropic per-minute limits for the workspace tier, and current prices — I did not fetch them. | Engineer, day one | OPS-3 numbers; the cost line |
| OQ-D | A second `default` worker container when slice two ships backfill? (~300 MB; fits the 5 GB free.) | Surbhi | Slice two capacity |

## Assumptions

- `[ASSUMPTION]` ~1,500 input and ~250 output tokens per email; prices and exchange rate as marked `[verify]`.
- `[ASSUMPTION]` rq runs one job at a time per worker container on this stack (Frappe's default; not counted on the server).
- `[ASSUMPTION]` The dev overlay staffs the same queues as production; I read `docker-compose.app.yml` in full and only the header of the devstack file.
- `[ASSUMPTION]` The demo mailbox receives only what the team sends (brief, PRIV-12), so slice one without a ceiling is safe for the demo alone.

## Handoff note

To the engineer (`00`): design around three run-side facts — one shared worker process (keep the job short: one call, no long sleeps inside retries), an idempotency row written before the call (OPS-4), and the key living in backups (OPS-9: per-tenant workspace key, no fallback key — lesson 11). I disagree with nothing in the spec; I push back on the brief only where it lets slice one run without any ceiling (OPS-1). I ran no command on any server; every server number here was handed to me as measured on 24 Sep 2026, and every file fact names its line.
