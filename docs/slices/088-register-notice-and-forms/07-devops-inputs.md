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
