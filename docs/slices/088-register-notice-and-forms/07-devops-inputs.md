# 088 DevOps inputs

## §1 Brief, 21 Nov 2026

Read: worktree 088-register-notice-and-forms, branch slice/088-register-notice-and-forms, dev bad23ce0. Nothing run on any server. Tier 1 (personal data, retention). Advice only; Decision column is the user's.

**Bad news first.** (a) A thumb-print or signature photo, kept 5 years, for every employee every month, is the biggest new thing to run here. It is personal data, possibly biometric. (b) Today nobody has timed a PDF on our image. (c) Nothing deletes files at 5 years: the erase job is off.

**Facts (read, not run):** wkhtmltopdf 0.12.x is in the base image (ARCHITECTURE.md:50). The only PDF path is Frappe's `download_pdf` for payslips (hrms/hrms/api/__init__.py:789), on the web tier: 4 gunicorn workers x 2 threads = 8 slots, 120 s timeout (slice 043 OPS-W3-6; payslip PDF time was never measured). alvoraa_portal has no PDF code. Photo upload exists: employee_photo.py, 5 MB cap, `is_private: 1` (line 239), nginx body limit 50m. Backups use `bench backup --with-files` (DEPLOYMENT_RUNBOOK.md).

**Run-cost estimates (not measured, based on the 1-3 s per PDF figure in slice 043):**
- Register: 600 people at about 25 rows per page is about 24 pages. ONE PDF, one background job on `long`, maybe 5-15 s. Cost: nothing extra.
- Per-person notices as 600 separate PDFs: 10-30 min of CPU per month. Not on the web tier. Avoid it.
- Photos, if one per employee per month at 3 MB: 600 x 12 x 3 MB = about 21 GB a year, about 108 GB over 5 years, and every backup copies all of it. If one photo per register page (about 24 a month, 5 MB cap): about 1.4 GB over 5 years. The disk here is 3% used, but the server's free disk is **unknown, I could not check**; a full disk has already killed workers (lesson 15, 16).
- Print: about 24 sheets a month per tenant for the register. About 600 sheets if each person gets a notice page. Paper is the customer's cost.

| ID | Recommendation | Why | Cost of ignoring | Level | Decision |
|---|---|---|---|---|---|
| OPS-1 | Ask counsel if one photo per register PAGE meets "a photo of the signed page, for every employee". If yes, store one private file per page, linked to its employees | Cuts storage and backup growth by about 25x | About 100 GB per tenant over 5 years in every backup | Recommend, P2 | |
| OPS-2 | Put the notice of corrections as rows/columns on the register. No separate per-person PDF and no payslip change for now | Cheapest rung: one surface, works for DTC (pays outside the portal) and Grace alike. Payslip lines would differ per tenant | 600 PDFs a month, or a payslip print-format edit for one tenant | Recommend, P3 | |
| OPS-3 | Generate the register in one background job on the `long` queue, never in a web request. Time one 24-page file on the local bench first | Over 2 s of work is background (nfr-budget §2); 8 web slots are shared by all tenants | Portal stalls for everyone when HR prints | Recommend, P2 | |
| OPS-4 | Photos: private files, reuse the employee_photo.py checks (type, 5 MB cap), shrink on the phone before upload | Reuse beats new code; a phone photo is 3-5 MB | Backup and disk growth | Recommend, P2 | |
| OPS-5 | Retention needs a deletion step at 5 years, and its owner must be named. Ask the PM before building it | Erase job is off; no job exists for this class of file. Also check it does not clash with the 180/45-day and other retention rules counsel gave | Files kept past the legal period, or deleted early | Recommend, P1 | |
| OPS-6 | Ask counsel whether a thumb-print image is biometric data under DPDP, and who may open the photo | Narrower rights, access logging and "export is logged" rule apply (security-compliance-baseline) | A breach of a worse class than a payslip | Recommend, P1, to security engineer | |
| OPS-7 | Statutory forms (IX, C, D, Delhi G/H): the layout must come from counsel's exact text per state; one template per form, no form builder | One-off layout work is small; a generic engine is the over-build | A rebuilt layout when the Act text differs | Consider, P3 | |
| OPS-8 | Before the build: time one PDF at 600 rows, and size one real signed-page photo | These are the two numbers that decide OPS-1 and OPS-3 | Guessing | Recommend, P2 | |

**Priority change suggested:** none for the idea. The photo-and-retention part (OPS-1, 5, 6) should be decided before the brief is finalised, because it sets the storage and deletion work.

**Subtract pass:** removed the idea of a queue per tenant, CDN/object storage and a PDF service (not needed at these numbers). Kept nothing optional.

---

## §2 Design, 21 Nov 2026

Read: worktree 088-register-notice-and-forms, branch slice/088-register-notice-and-forms, HEAD 87a8e614; `01b-ux-design.md` with Surbhi's design gate (D-1 to D-4 taken); `prototype-v1.html` (41,308 bytes); `alvoraa_portal/alvoraa_portal/employee_photo.py`; `deploy/nginx.conf`; `hooks.py` scheduler block. Nothing run on any server or bench. Tier 1. Advice only; Decision column is the user's.

**Bad news first.**
1. **The signed-page photo cannot reuse the profile-photo shrink as it stands.** `employee_photo.py` re-encodes to 512 px (line 83, `STORED_EDGE`). That is a face. A page with a signature or thumb print at 512 px is unreadable, and an unreadable photo keeps the pay slip blocked (brief risk). It needs its own, larger shrink.
2. **Nobody has timed a 100-person print in a browser.** The design says so too. The cap of 100 is a guess.
3. **Nothing deletes the photo at year 5.** The erase job pattern exists (hooks.py daily list: joiner, grooming, expense evidence), but there is none for this file class.

**Facts (read, not run):**
- The prototype has no external request: 0 `http(s)://` strings, so no font, script or image comes from outside. 41 KB of one file. Weight is not the problem.
- Devanagari relies on the computer's own font (Noto Sans Devanagari, then Nirmala UI). If the printing PC has neither, the Hindi lines print as empty boxes. **Not checked on Grace's HR computer.**
- nginx body limit is 50m on the main servers (lines 164, 383), gzip is on (line 89, level 5). A 3-5 MB phone photo is accepted by nginx today.
- Private-file path to reuse: `_store()` in employee_photo.py sets `is_private: 1` (line 239); 5 MB cap checked on the base64 string first (line 67-70).

**Estimates (not measured):**
- Print data for 100 people at up to 5 changes each: about 150 KB of JSON before gzip, about 30 KB after [ESTIMATE, 100 x 5 x 300 bytes]. Small.
- The browser cost is layout: 100-200 A4 pages in one document. Likely a few seconds on a laptop; on a phone it may freeze. [ASSUMPTION, to time.]
- Signed-page photo after a 1,600 px, quality 75 shrink: 250-400 KB [ESTIMATE, typical document-photo JPEG; the only measured figure here is the profile photo: 30-82 KB at 512 px, per OPS-42 in employee_photo.py].
- 3G upload: a raw 4 MB camera photo takes about 30-60 s at 0.5-1 Mbps [ESTIMATE]. At 300 KB it is 3-5 s. The NFR page budget is 2.5 s (nfr-budget); an upload is not a page load, but 60 s on a floor phone will be retried and abandoned.

| ID | Recommendation | Why | Cost of ignoring | Level | Decision |
|---|---|---|---|---|---|
| OPS-9 | Shrink the signed-page photo **on the phone before upload** to about 1,600 px long edge, JPEG quality about 75, and re-check size on the server. Keep the 5 MB cap and magic-byte check from employee_photo.py; do not reuse its 512 px edge | A face and a page need different sizes. Phone-side shrink is what makes 3G work | Unreadable photos, or 4 MB uploads that fail on mobile data | Recommend, P2 | |
| OPS-10 | Photos stay `is_private: 1`, served only through a permission-checked method, never a `/files/` URL. A test fetches the URL with no login and with a non-HR login and expects refusal | Private file URLs under `/private/files` need a session, but the check must be proved, not assumed. Same rule as the employee photo | A signature or thumb print readable by anyone with the link | Recommend, P1 | |
| OPS-11 | The print preview and the list are **not cached** (no `Cache-Control: public`, no server cache of the notice data). The month list may be fetched fresh on each open | One person's changed days are personal data; a cache keyed wrongly shows one worker's page to another. Query is small | A cross-person leak, or a stale page after a late change (design N4) | Recommend, P1 | |
| OPS-12 | Keep the 100-person cap; **time a 100-person batch** on a mid-range Windows laptop and a phone before release, on Chrome. Report seconds and whether the tab froze. If it is slow, lower the cap, do not add a PDF engine | Cheapest rung; the cap is already in the gate | Hung browser during pay week | Recommend, P2 | |
| OPS-13 | **Print the dummy three-person notice on a real printer in Hindi and English, from the Windows machine HR will use**, before the build is called done | Font fallback and A4 fit are unchecked (01b §6) | Blank Hindi boxes on a paper a worker signs | Recommend, P1 | |
| OPS-14 | No new web font, no CDN, no object storage | Not needed at these numbers | New dependency to patch for ever | FYI | |

**Subtract pass:** removed a "photo compression service", a CDN, and any caching layer. Kept only: phone-side shrink, private serving, no cache, one timing.

---

## §3 Requirements, 21 Nov 2026

Same read as §2. Tier 1. Every row below is for the BA to trace into a user story and the engineer to build or test. Rows marked **OPS-R-n** need Surbhi's decision before the spec is final; the rest are requirements on their own.

**Bad news first.** (a) The 5-year retention has no legal number behind it yet: counsel said attendance and wage records "at least 5 years from the last entry" (memory `counsel-087-hr-punches-nov21`, relayed, unsigned) and has not answered brief Q4/Q5 for the signed photo. (b) The erase job is off on every tenant for this class of file, and **a "5 years" rule with no deleter and no owner is a rule that will not be kept**. (c) The print log is the only proof a notice was shown; if it can be edited, it proves nothing.

| ID | Requirement | Measure / how to prove it | Level | Decision |
|---|---|---|---|---|
| OPS-15 | **Photo storage.** Store each signed-page photo as a private File attached to the notice record, shrunk per OPS-9. Log the stored size on every upload (employee_photo.py already does this for faces) | Query `tabFile` size per tenant per month; target under 1 GB per tenant per year (brief §9). At 350 KB: 100 photos a month is 0.4 GB a year; 600 a month is 2.5 GB a year [ESTIMATE] | P2 | |
| OPS-16 | **Backup growth.** `bench backup --with-files` already copies private files (runbook line 176). Add nothing. Before release read the free disk on dev and, with the user's access, on the server; the server's free disk is **unknown, I could not check**. Release gate: free space over 20% after adding 5 years of the 600-a-month case (about 13 GB) | `df -h` on dev read-only; for production the user runs or approves it | P2 | |
| OPS-17 | **Restore proof.** Once, on dev, restore a backup that includes one signed-page photo and open it as HR | A backup never restored is not a backup (priority 1) | P2 | |
| OPS-18 | **Retention is recorded, not assumed.** Each notice record stores `retain_until` (last entry date + 5 years) at the time the photo is saved. No deleter is built in 088 | Field exists, filled, shown to no one. Smallest thing: a date, not a job | P3 | |
| OPS-R-1 | **Decision for Surbhi: the retention period and who runs the deletion.** Options: (A) 5 years from the last entry, deleter built later, a named owner today (recommended, brief Q5); (B) 8 years to match tax and PF audit reach (counsel said 6 to 8 for those); (C) keep for ever, against the 18 Sept rule that nothing is kept for ever. Risk if it waits: the photo is kept past the legal period or the date is set wrong and cannot be fixed later | Her word, then counsel | P1 | |
| OPS-19 | **The erase job stays OFF.** When it is built it follows the pattern already in hooks.py: a daily entry, an `*_erase_enabled` site-config switch defaulting to off, legal hold wins, one log line with the count and no names. **Never switch it on without a dry-run count first** (1,780 queued deletes once stopped a migrate halfway) | A test that the switch absent means nothing deleted | P2 | |
| OPS-R-2 | **Decision for Surbhi: is a thumb-print photo biometric data under DPDP (brief Q4)?** Until counsel answers: HR-only, opening it is logged, no export, no viewer (design §7). If yes, the narrower rights and logged-access rules apply and may add work. Risk if it waits: a breach of a worse class than a payslip. Owner: counsel, then `hrms-security-privacy-engineer` | Written reply | P1 | |
| OPS-20 | **Print log.** One row per person per Press of Print, written **before** the browser print window opens: who, when, person, month, list of change ids, page count, tenant. Never the reason text or the hours. Rows are insert-only: no edit, no delete in the UI, not even for System Manager; write through the document API so audit trail stays | Test presses Print and asserts the row (design item 9). A second test tries to edit it and is refused | P1 | |
| OPS-21 | **Print log retention.** Keep as long as the photo it relates to (5 years, OPS-R-1). A batch of 100 is 100 rows; at 600 people a month that is at most 36,000 rows a year [ESTIMATE, upper bound]; fine for MariaDB with an index on (month, person) | Row count query | P3 | |
| OPS-22 | **Rate limits.** Use Frappe's `rate_limit` already used in the app (`field_app_limits.py` hashes the key so nothing sensitive reaches Redis; I read its header, not its whole code). Suggested numbers [ESTIMATE, to confirm on the build bench]: print-log call, 10 batches a minute per user; photo upload, 20 a minute per user; list fetch, 60 a minute per user. Key on the user, **not on the IP**: a whole store shares one Wi-Fi address (same reasoning as field_app_limits). No nginx change; the existing 50m body limit already allows the photo | Test that the 11th call in a minute gets a 429-style refusal with no personal data in the message | P2 | |
| OPS-23 | **Print and record are HR-roles only.** A non-HR print is refused and logged (design item 4). The record-signature call refuses when the signer filed a covered change | Security engineer's tests; not mine to design, listed so it is traced | P1 | |
| OPS-24 | **Monitoring.** Log lines, not a new tool: count of prints, count of photo uploads, stored size, count of refusals, per tenant per day, with no names. Alert (on the control plane view that `health.collect_scheduled` already feeds) when: disk free under 20%; refusals over 20 in an hour; a photo over 2 MB stored (shrink failed). Disk alert is the one that already cost a day (lessons 15, 16) | One daily log line exists and the three thresholds are in the release plan | P2 | |
| OPS-25 | **No new container, queue, worker, scheduler job, volume or dependency** in 088. Browser print, no PDF engine, no background job (brief §7). Pillow is already in the image (used by employee_photo.py) | Image diff shows no new package | P2 | |
| OPS-26 | **Migration.** 088 adds a record type and fields; run the migrate dry run on a copy of a real tenant per `REHEARSAL.md`, and check the job queue is empty first (migrate-queue trap, 5 Nov). Our app adds no Frappe or ERPNext doctype copy: run `scripts/check_app_integrity.py` | Dry run log read, time recorded | P1 | |
| OPS-27 | **Release order: 087, then 088, then 086.** Reasons (read, not run): 088 reuses 087's confirm fields, its "Signed on the register" dialog, its dispute (D-2) and its send bar (D-3), so it cannot land first. 086 is the bulk-filing slice that makes more of 087's changes (memory `slice-086-after-087`), so the paper route must exist before 086 raises the volume of confirmations. Rebase 088 on 087's final SHA after 087's review round; **never merge**. Each in its own night window (00:30-06:00 IST, her word each time), not together, with the tenant's 087 gate setting recorded before and after | Pin file, container tag and the file itself, as in `deploy-pipeline-traps.md`; asset `assets.json` compared volume vs image | P1 | |
| OPS-R-3 | **Decision for Surbhi: is Hindi English-only until D-1 is cleared, or does the release wait?** The gate says a Hindi reader checks before any sheet is printed for a customer. Recommend: ship the code with English-only printing switched by one site setting, and turn Hindi on after the review, so the release is not blocked on a reader. Risk if it waits: 088 and then 086 are held behind a language check | Her word | P2 | |
| OPS-R-4 | **Decision for Surbhi: who may open the photo.** Recommend HR roles only, opening logged, no export (design §7). A different answer (an inspector, a branch manager) changes OPS-10 and OPS-20 | Her word, with counsel's reply to OPS-R-2 | P1 | |
| OPS-28 | **Rollback.** The change is one slice with a new record type: rollback is "redeploy the previous tag with migrations off", the record type stays in the database empty. The tag must exist in `alvoraa-app`, the package production pulls from (lesson 17, 20). Measured rollback time is about 7 minutes because of the `bench version` wait (lesson 22) | I will check the tag exists at §5 | P2 | |

**Conflict to name.** Photo volume (OPS-15) pulls against the paper process: one photo per page is what counsel-style records want; fewer photos is what the disk wants. The numbers say disk is not the constraint (a few GB over 5 years). Weighed by the priority order, the data and counsel come first and disk is not at risk; so no conflict needs escalating beyond OPS-R-1.

**Subtract pass:** removed a deletion job (OPS-18 is one date field), a photo viewer, a separate log table beyond the print row, an nginx rate zone, a new alert tool. Kept: private files, phone-side shrink, insert-only print log, three thresholds on what already reports.

**Left behind:** nothing. No container, no file outside this one, no setting changed. `prototype-v1.html` shows as modified in git status from before this run; I did not touch or stage it.
