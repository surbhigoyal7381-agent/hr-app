---
slice: 078-positions-faces
artifact: 04-test-report
author: hrms-test-automation-engineer
date: 2026-10-31
status: TESTED. Verdict FAIL - two defects caused by this slice turn CI red, and both fixes are small. Separately, neither app's suite completed on the throwaway site (portal terminated part-way, hrms ran zero tests), so CI is where the rest must be answered.
worktree: .claude/worktrees/078-positions-faces on slice/078-positions-faces, head 30660e28
tested: a378af03..30660e28 (13 commits), against origin/dev d3afcaa5
note: the worktree moved to 363758d3 (six defect-fix commits) WHILE this run was in progress. None of those commits is tested here - see the Postscript.
epic: ALV-260
---

# 078 · Test report

---

## ⚠ Postscript · fixes landed after this run, and I have NOT tested them

**Everything in this report was produced against `30660e28`.** While I was
running the suites, the engineer acted on these findings. By the time I finished
writing, the worktree had moved to **`363758d3`**, six commits ahead, and a test
run of its own was in flight on the bench.

| Commit | Claims to fix |
|---|---|
| `9aa4d115` | **D-1** — classifies `Alvoraa Joiner Submission` as **tenant-side**, per Surbhi, 31 Oct 2026, with its three Link fields checked for access widening |
| `daca7224` | **D-2** — **teaches the gate to read a raw `fetch`** instead of excusing the endpoint in `NO_ARG_CALL`, and raises `MIN_CALL_SITES` 200 → 201 |
| `5ab76ebd` | **D-3**, **D-5(b)**, **D-7** — an empty form can no longer lose the link, and **J4 exists** |
| `1c61b5e1` | **D-5(a, c, d)**, **D-6** — the portal parity gaps, built as drawn |
| `3eda205a` | the **P4** in §14 — pins the 48 px thumbnail as private, not only the 512 px file |
| `363758d3` | the implementation notes for all of the above |

**I have verified none of them.** Not one line of this report's evidence comes
from that code. Two of those commits change a **test** rather than the product
(`daca7224` edits the gate itself, and the D-1 fix is a list entry), and a fix
that edits the test it failed is exactly the kind that needs an independent
eye — I read `daca7224`'s reasoning and think it took the **right** option, the
stronger one, but reading is not running.

**What this does to the verdict.** The verdict below stands **for `30660e28`,
which is what I tested.** It is not a verdict on `363758d3`. Before release
somebody must re-run against the new head and confirm:

1. The full `alvoraa_portal` suite is green **to the end** — including batch 3,
   which never finished here (§2.2).
2. `test_browser_call_args_045` passes **and still catches a genuinely unread
   endpoint** — the gate must not have been loosened to go green. `MIN_CALL_SITES`
   going 200 → 201 is the right sign; confirm the new reader finds the site and
   checks its arguments.
3. The new J4 screen and the parity fixes behave — **none of them has been seen
   in a browser.** My joiner-page harness (§5.3) was written against a page with
   **no J4**, so it does not cover the new screen.
4. D-4 is unchanged by any of this: **cross-company isolation is still untested**
   for the two new read endpoints.

---

## 0 · The answer first

**Verdict: Fail.** Not because the feature is bad — most of it is unusually well
proved — but because **two things this slice added make the existing test suite
go red**, and a red suite is a blocked release. Both fixes are small. Neither is
a security hole.

**And a second, separate point that is not the slice's fault but must not be
glossed over: neither app's suite completed.** The `alvoraa_portal` run was
terminated part-way through its third batch, and the `hrms` suite ran **zero
tests** because ERPNext's test bootstrap cannot build master data on this
throwaway site. **So "the rest of the suite is unverified against this branch"
is still partly true** — less true than before, since 1118 portal tests did run
and are fully attributed, but true. §2.2 and N-1b.

**There is no stop-the-line finding.** No cross-tenant leak, no permission
bypass, no statutory identifier in a log, no personal data reaching a model. I
looked for all four and name the evidence below.

| # | What | Rank |
|---|---|---|
| **D-1** | **The new `Alvoraa Joiner Submission` DocType is classified as neither control-plane nor tenant-side.** Nobody has decided whether a joiner's personal data is inside the tenant access derivation. Fails `test_invoicing.py::test_every_billing_doctype_is_named_as_control_plane_only` | **P1 — blocks** |
| **D-2** | **A new endpoint is named in `portal.js` with no readable call site**, so its arguments are unchecked by the 045 gate. Fails `test_browser_call_args_045.py::test_no_endpoint_is_named_but_never_read`. The call itself is correct — this is a gate hole, but it still reds CI | **P1 — blocks (as a red build)** |
| **D-3** | **A joiner can submit a completely empty form.** Nothing is mandatory anywhere — not in the browser, not on the server, not on the DocType. The status becomes `Submitted`, the token is burned and its row purged, so the link **cannot be reopened** to correct it. HR gets an empty row and the joiner has no way back | **P2** |
| **D-4** | **Cross-company isolation is untested for the two new read endpoints** — the mini profile and the documents. The fixtures build one company, deliberately; branch scoping is tested, company scoping is not, and **no CXO persona appears anywhere in this slice's tests**. The chart/register path *is* company-tested on the hrms side | **P2 — untested control** |
| **D-5** | **Four prototype-parity gaps**: the seat tray never opens the mini profile (two of three drawn entry points exist); the joiner's J4 photo screen is not built at all; My Profile has three cards, not the four the design drew — the documents card was never moved; and the enlarged photo never closes when the pointer leaves it | **P2** |
| **D-6** | The picker's laptop footer renders **OK · Preview · Cancel**; the design asks for **Preview · Cancel · OK**. The primary action sits where Cancel is expected | **P3** |
| **D-7** | `www/joiner.py` computes `context.joiner_on` on every public page load — a settings read on the most-attacked surface in the product — and **the template never reads it** | **P3** |
| **D-8** | Three ACs are wrong as worded (AC-101, AC-112, AC-125) and one AC id in the implementation notes (**AC-72a**) **does not exist in the spec** | **P3 — spec defect** |

**Three things the engineer flagged as unproven, that I have now proved:**

- **The Frappe fork patch applies cleanly to `v16.35.0`** — the tag CI and the
  Dockerfile actually pin — 3 of 3 edits, idempotent, and the patched file
  compiles. §5.4. D1 is much smaller than it was.
- **The joiner's public page has now been rendered in a real browser**, driven
  through all four steps. **46 assertions, 0 failures.** §5.3. D2 is largely
  cleared.
- **OPS-41 / T5 is settled.** `get_web_form_request`'s signature on v16.35.0 is
  exactly what the build assumed. §5.4.

---

## 1 · What I could NOT check — read this before the coverage tables

Named here, at the top, not in a footnote. Each of these is **unproven**, not
passed.

| # | Not checked | Why |
|---|---|---|
| **N-1** | **The Positions chart, the seat tray and the chart card have never been rendered in a real browser.** `browser_check_positions.js` is still unexecuted | Two reasons, and the second is the real one. It needs a served site and a login, and the test container publishes no port — but more to the point, **`test078` holds `0` rows in `tabAlvoraa Position`** (533 employees, 3 photographs, no seats). The chart would have had **nothing to draw**, so every check would have failed for want of data rather than for want of correctness. jsdom covers the markup with synthetic data (404 + 225 + 116 checks); **a real browser against real seats does not exist yet.** This needs dev, or a purpose-seeded throwaway — not this site |
| **N-1b** | **The `hrms` suite ran ZERO tests**, twice, and the `alvoraa_portal` suite **did not finish** — its third batch was terminated part-way. So neither app's suite is fully verified against this branch | ERPNext's test bootstrap cannot build master data on `test078`; and a `Terminated` on the portal run. Both are environment, not code — §2.2 has the evidence and the restoration I did. **CI, on a fresh site, is where this gets answered** |
| **N-2** | **No image has been built from this commit.** The patch is proved against the exact v16.35.0 source, and both build steps are correctly wired — but the Docker build and the CI run themselves have not happened | A real image build is a deploy-stage action and needs approval |
| **N-3** | **Hindi is unprovable in this repository.** AC-141, AC-142, AC-143 cannot pass: there is no Hindi file anywhere (`translations/` holds only `en.csv`), and the joiner's page is not wrapped in `drT()` at all | A site-level `Translation` import, which no commit here can supply |
| **N-4** | **Nothing was checked on dev or production.** AC-34, AC-72, AC-130, AC-135, OPS-38 and every release/monitoring OPS item are untouched | Release-stage, and not mine |
| **N-5** | **No performance number was measured at volume by me.** Every NFR figure in §9 is the engineer's, re-reported as theirs | The query-count gate is asserted in code and passes; wall-clock at 400 employees was not re-measured |
| **N-6** | **Dark theme (AC-133) and the a11y focus traps** were not swept | No automated a11y tooling in this repo; the drawer's focus trap does not exist to test (§7) |
| **N-7** | **The joiner page's real HTTP response headers** were not observed | I rendered the template, not a server response. The three headers are set in a `try/except Exception: pass`, so a failure to set them is silent — see §8 |

---

## 2 · The commands I ran, and what they said

Everything below ran **today, 31 October 2026**, in the worktree
`C:\Surbhi-Git\hr-app\.claude\worktrees\078-positions-faces` at head
**`30660e28`**, working tree clean apart from `.claude/context/ux-learnings.md`,
which belongs to the UX designer and is in none of this slice's commits.

### 2.1 Where the Python tests ran, and what schema they ran against

| Thing | Value |
|---|---|
| Container | **`hrlocal-078`** (the engineer's throwaway), image `ghcr.io/surbhigoyal7381-agent/hr-app:dev-3830ed3` |
| Site | `test078`, database **`_078tests`** — its own database, nobody else's |
| Apps mounted | `alvoraa_portal`, `hrms`, `alvoraa_goals` **from this worktree**, bind-mounted |
| **Schema provenance** | A copy of `test_site`'s database, then `bench migrate` **on this branch's code**. I confirmed it directly: `tabAlvoraa Joiner Submission` exists, and `tabAlvoraa Photo Access Log` carries the two new columns `document_type` and `source` (default `Check-in photo`) |
| Frappe in the container | **v16.33.1**, and **already patched** — `ALVORAA PATCH 078` appears 3 times in `file.py`. Every Python result below is therefore **on a patched Frappe** |
| Shared bench | **`hrlocal-bench` was never used.** It bind-mounts the main checkout, so a run there would have tested another session's uncommitted work |
| Concurrency | **One run at a time.** `pgrep -af run-tests` was clear before I started; the two suites ran **serially** in one chained script |

**Nothing shared was touched.** No `bench migrate`, `clear-cache`, `build` or
any deploy command on any shared site. No `docker cp` (it is approval-gated; a
first attempt was refused and I wrote inside the container instead). No git
operation in the shared checkout. No push. No site setting changed anywhere.

### 2.2 The full Python suites — the thing the engineer could not do

This is the thing the engineer's T2 debt named, and it is where the two blocking
defects came from.

```
bench --site test078 run-tests --app alvoraa_portal
bench --site test078 run-tests --app hrms
```

Run **serially**, chained in one script, because two runs against one site clash
on shared fixtures — the trap that cost the engineer two red runs.

**`alvoraa_portal` — and it did not finish. Say that first.**

`bench run-tests` prints **a summary per batch**, and reading only the tail
hides the others. This run had **three** batches, not the two the standing note
warns about:

| Batch | Result |
|---|---|
| 1 | **36 tests, OK** (76 s) |
| 2 | **1082 tests — 4 failures, 4 errors, 19 skipped** (4355 s, 1 h 13 m) |
| 3 | **TERMINATED part-way.** It had reached `test_field_app_m3_133` (about "f" alphabetically) after ~28 minutes, with **3 more tests failed**, when the log recorded a bare `Terminated` and the process died |
| **Total actually observed** | **1118 tests completed in batches 1–2, plus a partial batch 3. 11 tests not passing. 19 skipped** |

**⚠ So the `alvoraa_portal` suite is NOT fully verified against this branch.**
Batches 1 and 2 are a complete, trustworthy result. Batch 3 is a partial one,
and the modules it had not yet reached — roughly `g` to `z` of its own list —
**were not run at all in that batch**. I am not going to call that "mostly
passing".

**Why it died, as far as I can tell, and one disclosure I owe.** The container
records **no OOM kill** (`memory.events: oom_kill 0`, `OOMKilled false`), so it
was a SIGTERM from outside the test code. The host had **310 MB of free memory**
at the time, which makes host-level memory pressure the likeliest cause.

**The disclosure:** during batch 3 I ran a `bench --site test078 execute …`
against **the same site**, to prove the email failure (above). I do not think a
read-only render call sent SIGTERM to another process, and the timing is not
conclusive either way — but the standing rule here is that a result from a
disturbed window proves nothing, and I disturbed the window. **A clean batch 3,
with nothing else touching the site, is the honest re-run** and it belongs in
the human checklist (H-12).

**What batch 3 did tell us before it died:** the slice's own modules re-ran
inside the full suite and passed — `test_faces_078.TestTheChartsCost` 8 of 8,
and `test_employee_documents_078` reached without failure.

**All eleven failures are accounted for. Two are this slice's; nine are not.**

| Test | Assertion | Cause |
|---|---|---|
| `test_invoicing::test_every_billing_doctype_is_named_as_control_plane_only` | `Lists differ: ['Alvoraa Joiner Submission'] != []` | **SLICE 078 — D-1** |
| `test_browser_call_args_045::test_no_endpoint_is_named_but_never_read` | `{'alvoraa_portal.employee_documents_read.open_employee_document': {'portal.js'}} != {}` | **SLICE 078 — D-2** |
| `test_email_brand_174::test_alv174_the_header_shows_alvora_not_frappe` | `AttributeError: 'NoneType' object has no attribute 'get'` | environment |
| `test_email_brand_174::test_alv174_sample_email_saved_for_review` | same | environment |
| `test_email_logo_175::test_alv175_the_header_logo_is_the_absolute_lockup_with_no_account` | same | environment |
| `test_email_logo_175::test_alv175_a_tenants_deliberate_account_logo_still_wins` | same | environment |
| `test_ess_parts_034::test_the_cache_key_moves_with_the_release` | `AssertionError: unexpectedly None` | environment |
| `test_inbox_counts_034::test_the_key_carries_the_build_version` | `AssertionError: unexpectedly None` | environment |
| *batch 3* `test_announcements_076::test_ticked_and_active_queues_escaped_mail_and_logs_no_text` | queues a real email | environment (same cause) |
| *batch 3* `test_announcements_076::test_a_script_is_text_everywhere_the_notice_goes` | renders the notice into mail | environment (same cause) |
| *batch 3* `test_attendance_correction::test_switched_off_refuses_in_plain_words` | — | **NOT ATTRIBUTED** (see below) |

**The six environmental failures share one root cause, and I proved it rather
than assuming it.** This container's sites directory is a fresh bind-mount, and
**`/home/frappe/frappe-bench/sites/assets` does not exist at all** — the site has
never had assets built.

- The email failures are inside **Frappe's own** code:
  `get_formatted_html` → `inline_style_in_html` → `bundled_asset(path)`. I
  reproduced it directly on this site, outside any test:

  ```
  bench --site test078 execute frappe.email.email_body.get_formatted_html \
        --kwargs "{'subject':'t','message':'<p>h</p>'}"

  File "frappe/utils/jinja_globals.py", line 155, in bundled_asset
      path = bundled_assets.get(path) or path
  AttributeError: 'NoneType' object has no attribute 'get'
  ```

  So **every test that renders or queues an email fails on this container,
  whatever the branch.**
- The two cache-key failures are the same gap wearing a different hat.
  `frappe.utils.get_build_version()` returns the **mtime of
  `assets/assets.json`**, and on `OSError` falls back to
  `frappe.utils.random_string(8)`. I called it three times on this site and got
  **`zYAvyy8P`, `ZWcdxBaa`, `5aIDMQOq`** — a different value every time. So the
  test builds its cache key with one version and the code reads with another,
  and the lookup is always `None`. Nothing to do with any branch.

**The one I could not attribute, and will not guess at.**
`test_attendance_correction::test_switched_off_refuses_in_plain_words` asserts
that a manager filing on someone's behalf is refused in plain words when the
switch is off. It is **not** an email test, so the assets explanation does not
cover it. Batch 3 was terminated **before its summary printed**, so there is no
traceback for it in the log.

What I can say: **slice 078 touches `attendance_correction` in none of its 13
commits** (`git log … -- '**/attendance_correction*'` → 0), and this test ran
for the first time in batch 3 — it was not in batch 2, so it is not a
pass-then-fail leak. What I **cannot** say is whether it is a pre-existing
failure, a leak from the failing announcement tests just before it, or
something else. **It is listed as unattributed, not as environmental**, and it
needs the clean re-run in H-12. Note that `origin/dev`'s four most recent
commits are all ALV-199 work on this very test file, including one named *"the
settings test must not commit the site out from under itself"* — so test
isolation in this area has needed attention very recently.

**None of the other nine touches a file this slice changed**, and `test_email_brand_174`,
`test_email_logo_175`, `test_ess_parts_034` and `test_inbox_counts_034` are
**not modified by any of the 13 commits**. The two email templates this slice
*did* add (`birthday_reminder.html`, `anniversary_reminder.html`) are new files
beside an **already-existing** `templates/emails/standard.html` on `origin/dev`,
which is the file those tests render — so the slice does not change what they
resolve.

**`hrms` — it ran ZERO tests, twice. This is the report's biggest gap.**

The hrms suite **cannot be discovered on this site at all.** It never reached a
single test, either time.

| Attempt | Outcome |
|---|---|
| 1, in the chained run | `TestRunnerError: Failed to discover tests for ['hrms']: Year start date or end date is overlapping with Fiscal Year TEST-2025-2026` |
| 2, after I cleared that clash | got **further** — ERPNext's bootstrap built 26 fiscal years — then died on `TestRunnerError: Failed to discover tests for ['hrms']: Could not find Parent Item Group: All Item Groups` |

**Why.** Importing any hrms test module pulls in
`erpnext.tests.utils`, which runs `BootStrapTestData()` **at import time**. That
tries to build ERPNext master data on the site. `test078` is a copy of
`test_site`, which carries **fiscal years that clash** with the ones the
bootstrap wants and is **missing the Item Group root** it needs. The failure is
in ERPNext's own test bootstrap, not in hrms and not in this slice.

**This is a known trap, not a new one** — the same fiscal-year overlap is
recorded in slice 012's test report as *"test-site fiscal-year data, not 012
code"*, and there is a standing note about an hrms test-bootstrap fix.

**⚠ So all four hrms files this slice changed are unverified by their own
app's suite:** `people_fields.py` (188 new lines), `api.py` (+194),
`settings.py` (+259) and `register.py` (+26). That matters more than usual
because `hrms/alvoraa_org_structure/tests/test_company_scope_194.py` — the one
real **multi-company** test over `register.py` and `api.py` — lives there and
**did not run**. It is the test that would have covered part of D-4.

**What does cover them meanwhile:** the slice's own 138 tests in
`alvoraa_portal` call into all four hrms modules, and the hrms-side behaviour
they exercise passed. That is coverage of the behaviour, not of the hrms suite.

**Where this gets closed: CI.** CI builds a **fresh** bench and site
(`ci.yml:430`, `bench init` then installs the apps), so ERPNext's master data is
complete there and the bootstrap has something to work with. **The hrms suite
should be judged on the CI run, not on this container.** That is H-14 — and it
is another reason D-1 and D-2 must be fixed first, since CI is where all of this
gets answered at once.

**What I changed on the throwaway site, and how I put it back.** This is a
site-data change, so it is declared rather than buried:

| Step | What |
|---|---|
| I deleted | the 2 rows `TEST-2025-2026` and `TEST-2026-2027` from `tabFiscal Year`, plus any `tabFiscal Year Company` children of theirs, to clear the clash |
| ERPNext's bootstrap then created | 26 rows, `_Test Fiscal Year 2025` … `2050` (confirmed as today's by their `creation` timestamps, against 2026-09-26 for the pre-existing `_Test Fiscal Year 2024`) |
| I then removed | those 26 rows |
| And restored | both `TEST-*` rows with their original names and dates |
| Verified | the fiscal-year table matches what I found, and **`test_faces_078` re-ran afterwards: 8 tests, OK** — so the site is back in working order |

The one thing I could not restore faithfully is the `tabFiscal Year Company`
children of the two `TEST-*` rows, because I did not record them before
deleting. Every `_Test Fiscal Year%` row on this site has **zero** such
children, so the likelihood is that there were none — but I cannot prove it, and
**`test078` is a throwaway that should be rebuilt rather than trusted on this
point.** Nothing shared was touched at any stage.

### 2.3 The static gates — all re-run by me, independently

Not taken from the engineer's report. I ran each one myself.

| Command | Result |
|---|---|
| `python scripts/check_app_integrity.py` | **OK** |
| `python scripts/check_scope_traps.py` | **OK** |
| `python scripts/check_design_system.py` | **OK** |
| `python scripts/check_brand_spelling.py` | **OK** |
| `python scripts/check_tag_balance.py` | **OK** |
| `python scripts/check_version_pins.py` | **OK** |
| `python scripts/check_api_paths.py --max 0` | **OK** |
| `python scripts/check_portal_assets_gate.py` | **OK** |
| `node scripts/check_undefined_js.js` | **OK** |
| `node scripts/check_positions_tree.js` | **OK — 404 checks** |
| `node scripts/check_wall_chart.js` | **OK — 225 checks** |
| `node scripts/run_dom_tests.js` | **OK — 20 run, 0 not run, 0 failed**; the 078 suite alone **116 passed, 0 failed** |

All twelve green. The engineer's static-gate numbers are confirmed exactly.

### 2.4 The browser work — new, and not in the engineer's report

| What | Result |
|---|---|
| The joiner's public page, Chromium 390×844 and 1280×900, driven through J1→J2→J3→J5→J6 | **46 assertions, 0 failed** (34 + 12). §5.3 |
| `scripts/patch_frappe_binary_file_content.py` against the shipped image's Frappe **v16.33.1** | applied **3 of 3**, idempotent, `--check` correct both ways |
| The same patch against **Frappe v16.35.0**, fetched from the tag CI and the Dockerfile pin | applied **3 of 3**, patched file **compiles** |
| `scripts/browser_check_positions.js` | **NOT RUN.** N-1 |

**Playwright is in fact available on this machine** — `npx playwright --version`
reports 1.64.1 and the Chromium builds are installed under
`~/AppData/Local/ms-playwright`. The module does not resolve from the worktree,
but the scripts accept `PLAYWRIGHT=<path>` and one is in the npx cache. **The
engineer's "no playwright here" was wrong**, and that is worth knowing: T1 and
the browser halves of `check_portal_trays.js` and
`check_positions_connectors.js` are blocked only by the want of a served site
and a login, not by the browser.

---

## 3 · The two defects that make CI red

### 3.1 D-1 · A new DocType nobody has classified — **P1**

**Proved by construction, with no baseline needed.**

`test_invoicing.py::TestBillingNeverWidensTenantAccess::test_every_billing_doctype_is_named_as_control_plane_only`
lists every DocType in module `Alvoraa Portal` whose name is like `Alvoraa %`,
and requires each one to appear in either `subscription.CONTROL_PLANE_DOCTYPES`
or `subscription.TENANT_DOCTYPES`.

| Check | Result |
|---|---|
| `Alvoraa Joiner Submission`, module | `Alvoraa Portal` |
| matches the gate's filter | **yes** |
| on `origin/dev`? | **no** — `git cat-file -e origin/dev:…` fails. New in commit `c1059381` |
| in `CONTROL_PLANE_DOCTYPES`? | **no** |
| in `TENANT_DOCTYPES`? | **no** |

So this slice created the failure. **This is not merely a list to top up.** The
comment above `TENANT_DOCTYPES` says why it exists:

> *"The answer is not to widen the control-plane list, which would quietly
> exclude tenant data from the access derivation."*

The unmade decision is whether a joiner's submission — a **non-employee's**
name, mobile, personal email, home address, emergency contact and uploaded
identity documents — sits inside the tenant access derivation. Every sibling
record of this shape (`Alvoraa App Invite`, `Alvoraa Photo Access Log`,
`Alvoraa Notice Acknowledgement`) was classified **tenant-side**, and the same
reasoning plainly applies here. But it is a privacy and tenancy decision, so it
is `hrms-security-privacy-engineer`'s call, not mine.

**There is a precedent, and it was handled the same way.** Slice 012's own test
report (`docs/slices/012-leadership-view/04-test-report.md`, line 130) records
this exact gate firing on **its** two new doctypes, and classifies it
**"FAIL — Caused by 012 (DEF-1). Message lists exactly the two 012
doctypes."** So this is a known, working gate doing its job for the third time,
and the established response is to classify the new doctype — not to widen the
control-plane list and not to excuse the test.

**Fix:** one line, plus the comment that says why. **Owner:**
`hrms-security-privacy-engineer` to decide, `hrms-fullstack-engineer` to write.

### 3.2 D-2 · An endpoint the arguments gate cannot read — **P1 as a red build, P2 as a risk**

`test_browser_call_args_045.py::test_no_endpoint_is_named_but_never_read` fails.

I reproduced the gate exactly, outside the bench, by stubbing `frappe` and
running the module's own `_js_files`, `_call_sites` and `ENDPOINT_RE`:

```
files read        : 8
call sites read   : 225 (floor is 200)
endpoints called  : 171
ORPHANS           : 1
   alvoraa_portal.employee_documents_read.open_employee_document   in portal.js
```

**The call itself is correct.** `portal.js:10680` posts
`JSON.stringify({ row: row })`, and the server is
`open_employee_document(row=None)`. So the document "View" button works.

What is lost is the **guard**: that gate exists to catch the `action_leave`
bug — a call missing a required argument, a `TypeError` for every user, every
time. It cannot read a raw `fetch(...)`, and this endpoint is deliberately a raw
`fetch` because it streams a binary download. So a new endpoint on the
documents path is now **outside the check**, silently.

**Fix:** add it to `NO_ARG_CALL` with its reason — which the test itself
requires, via `test_no_arg_call_entries_all_give_a_reason`. **Owner:**
`hrms-fullstack-engineer`.

---

## 4 · The other defects

### 4.1 D-3 · A joiner can send an empty form, and cannot get back in — **P2**

Found by pressing the button, not by reading the code.

Driving the real page in Chromium, I tapped Start → Next → Next → Send **without
typing anything**. The page accepted it and reached J6. The payload was:

```json
{"values":"{\"full_name\":\"\",\"mobile\":\"\",\"personal_email\":\"\", … }"}
```

There is **no validation anywhere**:

| Layer | Mandatory fields |
|---|---|
| `www/joiner.html` | none — no `required`, no validation function |
| `joiner_public.submit_invite` | none — it refuses only a non-dict `values` |
| `Alvoraa Joiner Submission` DocType | `reqd` on `status` and `invited_by` only — both system fields |

And the consequence is **irreversible by design**: `submit_invite` sets
`status = "Submitted"`, then calls `_drop_request`, which destroys the row
holding the key. J6 tells them *"This link will not open again."* It does not.
So a joiner who taps through loses their only route, and HR receives a blank
record.

**This is also a spec defect.** No AC requires any field, so no test could have
caught it. **Owner:** `hrms-business-analyst` for the AC, then
`hrms-fullstack-engineer`.

### 4.2 D-4 · Cross-company isolation is untested — **P2, untested control**

The three personas this project tests against are CXO (all companies), HR
Manager (their companies) and Employee (own record). This slice's fixtures build:

| Persona | Built? |
|---|---|
| Employee (own record) | yes — three of them |
| HR Manager, whole company | yes |
| HR Manager, scoped to one **branch** | yes |
| HR Manager with **no** company (fails closed) | yes |
| Guest | yes, throughout the joiner tests |
| **CXO / multi-company leader** | **no — absent from this slice entirely** |
| **A second company** | **no** |

`fixtures_078.py` says the omission is deliberate: building a second company
*"would have made `ensure_company()` hand every other suite a company with no
holiday …"*. That is a fair engineering reason, and it still leaves the control
unproven.

**Two things lower the severity, and they are worth being precise about.**

**First, the new code reuses the shared helpers** rather than reimplementing
scope: `positions_profile.py` references `may_view`/`employee_in_scope` 9
times, `employee_documents_read.py` twice, and there is **no home-rolled
company filter anywhere** in the new code.

**Second — and I did not expect this — the chart and register path *is*
company-scope tested, on the hrms side.**
`hrms/alvoraa_org_structure/tests/test_company_scope_194.py` runs a real
multi-company case against `register.py` and `api.py`, which are **exactly the
two hrms files this slice changed** (+26 and +194 lines). So the faces work —
the batched thumbnail read and `_card` — runs through a genuine cross-company
test, provided the hrms suite is green (§2.2).

**What is left uncovered is narrower than "cross-company isolation", and that
is the honest statement:** the **two new `alvoraa_portal` read endpoints** —
`positions_profile.get_profile` (the mini profile) and
`employee_documents_read` (the documents) — are exercised against **one
company** only. Those are the two surfaces that hand a reader another person's
details and documents, so they are the ones where a company leak would matter
most, and they are the ones with no company test.

**It is still an untested control for these six new endpoints**, in the one
slice whose purpose is to show more personal detail to more people. Say so in
the release note rather than letting it look covered.

### 4.3 D-5 · Four prototype-parity gaps — **P2**

Parity matters more than usual here: the standing rule is that every feature in
the approved prototype is built exactly as drawn, and any difference needs
Surbhi's yes first. These four were not raised.

**(a) The seat tray never opens the mini profile.** The design (`01b` §6.3)
makes the tray *"the only surface that can hold a 25-person seat, so it is the
complete list"*. `data-pos-who` — the attribute that opens the drawer — is
emitted at exactly two places in `portal.js`, and I checked which functions
they sit in:

| Line | Function | Surface |
|---|---|---|
| 950 | `posCells` | the Positions **table** |
| 2004 | `posPaintPeople` | the **seat page**'s "Who is in it" |
| — | `posSeatSheet` (line 4109) | the **tray** — `posPlanMark(p).pre + posEsc(p.name) + c + line`, **plain text, no control, no face** |

**The code's own comment says it should be three.** The handler at
`portal.js:10834` is introduced as *"The Positions table **and the seat tray**:
a name opens the one mini profile."* The tray is named in the comment and is
not wired up — which is good evidence this is an oversight rather than a
decision, and nobody noticed because no test and no AC covers the tray as an
entry point.

The consequence is concrete: a 25-person seat shows three names and *"+22 more
in this seat"*, and **the tray is where the other 22 live** — but in the tray
their names are not controls, so there is no way to open the profile of anyone
beyond the first three.

**(b) The joiner's J4 photo screen does not exist.** The design draws six
screens; `joiner.html` has `j1`, `j2`, `j3`, `j5`, `j6` — **there is no `j4`**,
confirmed both by grep and in the browser. The spec's own flow (`02` line 355)
still lists *"J4 Your photo: optional, skippable"*, and J1 promises *"a
photograph if you want one"*. **No AC covers J4**, so no test could have failed.

**(c) My Profile has three cards, not four.** `01b` S1-G says the documents card
is *"the existing `my-docs-card`, unchanged, **moved into this panel's
order**"*. It was not moved: `my-docs-card` is still at
`templates/includes/ess/parts/home.html:130`, inside `#panel-home`, while
`#panel-my-profile` (line 183) holds only `myp-pic`, `myp-det`, `myp-pw`.

I checked it is not relocated at runtime either — `portal.js` touches the card
in exactly two places (`loadMyDocuments` at 4962, `myDocsShown` at 4999) and
both only **show, hide or fill** it. Nothing moves it.

**This reads as a considered choice rather than an oversight**, and that is
worth saying: `myDocsShown` is new in this slice and adds Decision 3(b)'s *"HR
has chosen 3 of these to show"* line **to the card where it already lives**. So
the slice extended the Home card in place instead of moving it. That may well be
the better answer. It is still a difference from the approved prototype that was
never put to Surbhi, and it has a concrete consequence: **AC-20 is worded as
"an employee opens My profile → the documents card is absent"**, which cannot be
checked as written, because the card is not on that page at all.

**(d) The enlarged picture does not close when the pointer leaves it.** `01b`
§6.3.1 line 441 is explicit for a mouse: it opens on *"Pointer over the photo"*
and closes when *"Pointer leaves both the photo and the enlargement. A click
**pins** it."*

Built: `portal.js:10802-10806` opens it on `mouseover`. **There is no
`mouseleave` or `mouseout` anywhere in `portal.js`** — I grepped the whole
file. And the click handler at `portal.js:10788` is
`MPF.big ? mpfCloseBig() : mpfBig()`, so a click after a hover **closes** it
rather than pinning it — the opposite of what was drawn.

The effect with a mouse: brush the photo, and a colleague's face fills the
drawer body (`.mpf-big{position:absolute;inset:0;z-index:5}`) and **stays
there** until you press Escape or click the photo again. The design's own
"counterweight, said out loud" is about exactly this picture being sensitive,
and the *"Hide before I share my screen"* link sits inches away. A face that
will not go away when you move the mouse works against both. **P3, and closer
to P2 than it looks.**

Touch users are fine: the avatar lives in the drawer's fixed head, above the
enlargement, so a second tap still reaches it.

### 4.4 D-6 · The picker's footer order is reversed on a laptop — **P3**

`01b` line 604: *"Laptop: Preview on the left, then Cancel, then **OK**."*

Built: DOM order is **OK, Preview, Cancel** (`portal.js:7317-7321`) inside
`.ocs-ft-b{display:flex; … justify-content:flex-end}` (`panels.css:2910`). In a
row, that renders **OK · Preview · Cancel** left to right — so the primary,
saving action sits furthest left and Cancel sits where OK was drawn.

The phone layout is correct: `flex-direction:column` puts OK first, as designed.

### 4.5 D-7 · Dead work on the most-attacked page in the product — **P3**

`www/joiner.py:44-52` computes `context.joiner_on` — including a call to
`form_is_on()`, which reads a setting — and comments that it is *"Used only to
draw the 'this link has run out' screen without a round trip"*. **The template
never reads it.** `grep joiner_on` finds no hit in `joiner.html` or anywhere
else. So every anonymous hit on the public page pays for a settings read that
changes nothing. Delete it, or wire it up.

### 4.6 D-8 · The spec and the notes disagree with themselves — **P3, spec defect**

- **`AC-72a` does not exist.** `grep -c "AC-72a" 02-functional-spec.md` → **0**.
  The implementation notes use it in §3.2 for *"the spec's p95 ≤ 50 KB"*, which
  is actually part of **AC-3**. So AC-3 is listed as satisfied in §3.1 and
  partly abandoned in §3.2 under an id that was never issued.
- The spec's highest id is **AC-143**, not AC-151. There is **no `AC-131` row**
  (only a/b/c/d), and no AC-144…151. The "151 criteria" count is 143 base ids
  plus 9 suffixed ones minus the missing AC-131.
- **AC-101, AC-112 and AC-125 are wrong as worded.** See §6.

---

## 5 · What I proved that was previously unproven

### 5.1 The GPS-carrying PNG is real, and the test uses it honestly

This was worth checking, because it is the only proof the metadata strip ever
gets, and a fixture that never carried GPS would make the test a comfort.

`fixtures_078.py:60` builds the PNG in code with a real GPS IFD —
`exif[0x8825] = {1: "N", 2: (28.0, 36.0, 0.0), 3: "E", 4: (77.0, 12.0, 0.0)}`
(a Delhi coordinate) plus a camera-name tag. It is used in two places:
`test_my_photo_078.py:119` (AC-5) and `test_joiner_078.py:584` (AC-115).

And the test asserts the source **before** asserting the outcome:

```python
source = fx.png_with_gps(size=(1600, 1200))
# The GPS really is in the source - otherwise this test passes on a
# fixture that never carried anything.
self.assertIn(0x8825, fx.exif_of(source))
```

then checks the stored file reads back as `bytes`, is a `JPEG`, has longest edge
512, and `exif_of(blob) == {}`. **That is a real proof.** AC-5, OPS-7, OPS-8 and
SEC-6's strip clause are genuinely met.

### 5.2 SEC-13's "one byte-identical answer" — verified byte for byte, as asked

`test_joiner_078.py:139`, `test_missing_unknown_expired_and_cancelled_are_one_answer`:

```python
for bad in ("", "   ", "no-such-key", "a" * 64, key, self._key(cancelled["link"])):
    with self.assertRaises(frappe.PermissionError) as caught:
        joiner_public.open_invite(web_form_request_key=bad)
    said.add(str(caught.exception))
self.assertEqual(len(said), 1, …)
```

**Six inputs** — empty, whitespace, unknown, 64 junk characters, expired,
cancelled. Every one must raise the **same exception class**
(`frappe.PermissionError`, so the same 403), and every message string goes into
a `set` whose length must be **1**. One distinct string from six inputs is
byte-identical by construction. A sibling test adds a **seventh** case, a *used*
key, with a direct `assertEqual(str(used.exception), str(junk.exception))`.

**The engineer's claim stands.** 078-SEC-13 is satisfied more strongly than it
asks. One blemish: the assertion message still says *"four cases"* — stale
wording from an earlier version. **P4.**

### 5.3 The joiner's public page — rendered, and walked, in a real browser

This was the engineer's **D2**, *"the single biggest untested surface in the
slice"*. It is now largely closed.

I substituted the template's two Jinja variables (it has no control-flow blocks
at all), served it from `file://`, stubbed the three endpoints to the **real**
server contract read out of `joiner_public.py`, and drove Chromium through the
whole journey at phone and laptop width.

**46 assertions, 0 failures.** What is now proved by a render rather than by
reading:

| Area | Proved |
|---|---|
| Hardening | `noindex` meta and `no-referrer` meta are in the rendered head; **the page loads nothing from any host** (zero `src`/`href` after boot), which is OPS-44 and SEC-15's asset clause |
| The token | **removed from the address bar** after boot; **never in a request URL**; POSTed in the body as `web_form_request_key` (AC-102, OPS-39); **never written to localStorage** |
| PRIV-8 | the retention notice **precedes the first input in the DOM** — the clause the engineer could not assert; and a real contact renders |
| AC-106 | J1 renders the **configured** 7 / 180 / 90, never a literal |
| PRIV-9 | J2 draws **exactly the seven** allow-listed fields; the submit payload carries those seven and nothing else |
| OPS-29 | typed answers are kept so a dropped connection loses nothing, and **no document bytes and no token** reach localStorage |
| a11y | every J2 input has its own `label`; every control ≥ 44 px; text ≥ 16 px (no iOS zoom) |
| AC-113 | three buttons per document type, **equal width, on one row** on a laptop, stacked on a phone |
| AC-109 / AC-110 | J5 warns the answers cannot be changed and shows them back; J6 names who they hear from, carries **"Bring on your first day: …"** with the deferred types, and says the link will not open again |
| AC-125 / J6 | the joiner **is** told at the time |
| SEC-13 | a visit with **no token at all** lands on the one generic screen |
| Reliability | **no uncaught JavaScript error and no console error** anywhere in the journey |

**An honest note on my own method.** My first run reported three failures. All
three were **my harness, not the product**: I had not filled the fields, and my
stub returned a response shape the real server does not return (it omits
`bringing`, which J6 reads). I read `joiner_public.submit_invite`'s actual
return — `{"sent", "contact", "bringing"}` — corrected the stub, and all three
passed. **They are not reported as defects**, because they were not.

**What this still does not prove** (N-7): the real HTTP response headers.
`joiner.py` sets `X-Robots-Tag`, `Cache-Control: no-store` and
`Referrer-Policy: no-referrer` — inside a bare `try: … except Exception: pass`.
If `frappe.local.response_headers` is ever absent, **all three security headers
vanish silently**. The meta tags survive; the headers do not. Worth one line in
the security review.

### 5.4 The Frappe fork patch — D1 and T5, both much smaller now

The engineer's **D1** said *"nobody should be told HR can add a photograph in
Desk until an image built from this commit has been seen to work"*, because the
patch had only ever run in a throwaway container.

I could not build an image (N-2). I did the next best thing, which turns out to
settle most of it.

**First, the version question.** The engineer believed we ship **v16.35.0** and
could only read **v16.33.1**. Both halves matter:

- `ci.yml:361` sets `FRAPPE_TAG: v16.35.0`; `deploy/Dockerfile:50` sets
  `ARG FRAPPE_TAG=v16.35.0`. So **v16.35.0 is what is built.**
- The **local image is v16.33.1**. So every Python result in this report — the
  engineer's and mine — ran against a Frappe **two tags behind what ships**.
  That is a real caveat and it belongs in the release note.

**Then the patch, against the version that actually ships.** I fetched
`frappe/core/doctype/file/file.py` at tag `v16.35.0` (1181 lines, against the
local 1046 — the file **has** moved) and ran the real script against it:

| Step | Result |
|---|---|
| `--check` on pristine v16.33.1 | `NOT fully applied (0 of 3)`, exit 1 — correct |
| apply on v16.33.1 | `applied 3 edit(s)`, exit 0 |
| re-apply (idempotency) | `already applied (3 of 3)`, exit 0 |
| **apply on v16.35.0** | **`applied 3 edit(s)`, exit 0** |
| **`--check` on patched v16.35.0** | **`already applied (3 of 3)`, exit 0** |
| `python -m py_compile` on the patched v16.35.0 file | **compiles** |
| the bug is still present in v16.35.0 | **yes** — `strip_exif_data(self._content, …)` at line 837, with the decode path above it |

**And both build steps are correctly wired**, apply-then-check so a drift fails
the build loudly rather than quietly:

- `deploy/Dockerfile:164-167` — copy, apply, `--check`, remove.
- `.github/workflows/ci.yml:442-445` — apply, `--check`; and the script is in
  the bench cache key at line 394, so changing it rebuilds the bench.

**So D1's "the line has moved" risk is gone**, for the exact tag that ships.
What remains unproven is only that `docker build` and the CI job themselves
succeed end to end — which is N-2, a release-stage check.

**T5 / OPS-41 is settled too.** On v16.35.0:

```python
def get_web_form_request(
    self, key: str | None, *, docname=None, for_update=False, allow_used=False
)
```

Exactly the signature the build relies on, keyword-only arguments included. The
engineer's reading on v16.33.1 holds on v16.35.0. **T5 can be closed.**

---

## 6 · The three acceptance criteria that are wrong as worded

I tested **what the code does**, and I say separately whether the behaviour is
right and whether the wording is. The engineer did not quietly re-point them,
and neither have I.

| AC | As worded | What is built | Is the behaviour right? | Is the wording right? |
|---|---|---|---|---|
| **AC-101** | *"No field equals the token in plain text."* | **No field of ours holds it in any form** — our DocType's 25 fields include no token field; the only related one, `web_form_request`, is a `Link` holding a **row name** (the row is `autoname: hash`, so the name is not the key), and it is nulled when the row dies. **Frappe's own `Web Form Request.key` is a plain `Data` field and does hold it in clear** — and that row is destroyed the moment the key stops being usable, on submit, on cancel and by the daily job, all through one `_drop_request` | **Yes.** A clear-text key exists only while the link still works, never after. That is a real narrowing and it is the strongest thing available without reimplementing Frappe's token machinery | **No.** It should read: *"No field of ours holds the token in any form, and Frappe's own request row — which does hold it in clear — is deleted the moment the link stops working."* |
| **AC-112** | a used link *"may say already used"* | It **cannot**. The purge deletes the row holding the key on use, so afterwards a used key is simply an unknown key | **Yes, and stronger than asked.** Verified in §5.2: seven wrong inputs, one byte-identical answer, one exception class | **No.** It should read: *"A used link gives the same answer as an unknown one, because the row holding its key has been destroyed."* |
| **AC-125** | *"This link will not open again"* on a second visit | A second visit gets the **generic** answer, which still says *"nothing you sent is lost"*. **J6 does say it at the time** — I confirmed that in the browser (§5.3) | **Yes.** The joiner is told, at the moment it matters | **No.** Same rewording as AC-112 |

**One gap in the SEC-9 story worth naming.** The test that proves our row holds
no token,
`test_our_own_row_never_holds_the_key`, checks that no field's **`fieldname`
contains `token`, `key` or `secret`**. `web_form_request` passes that check
because of what it is *called*. A future field named, say, `invite_ref` holding
a key would pass it too. The other half of the test — that the key string does
not appear anywhere in `doc.as_dict()` — is the one doing the real work. **P4**,
worth a comment.

**One untested path on SEC-9.** `_drop_request` has **four** callers, not three:
submit (`joiner_public.py:298`), cancel (`joiner_invite.py:207`), the daily job
(`joiner_housekeeping.py:204`) and **`purge_submission`
(`joiner_invite.py:286`)** — counsel's own erasure button. The first three each
have a test. **The purge path does not.** **P2 — untested control**, and it is
the one counsel asked for.

---

## 7 · Every SEC and PRIV requirement, by name

`078-SEC-1` … `078-SEC-16` and `078-PRIV-1` … `078-PRIV-9`. **Met or not, each
named.** Beware: slices 010 and 012 use bare `SEC-n`/`PRIV-n` ids; only the
`078-` form is this slice's.

### 7.1 Security

| ID | Requirement | State | Evidence |
|---|---|---|---|
| SEC-1 | Closed server-side allow-list of Positions profile fields; off-list refused on write, ignored on read | **Met** | `test_the_ten_positions_fields_are_exactly_these`, `test_pay_bank_identity_and_date_of_birth_are_denied`, `test_the_reader_intersects_again_so_a_direct_write_produces_nothing`; DOM test line 382. Built as **ten** fields, not eleven — spec ⚠ DECISION 6 |
| SEC-2 | `may_view()` **and** `employee_in_scope()`; an unseeable field **absent**, not blank | **Met** | `test_somebody_who_cannot_open_positions_is_refused`, `test_a_reader_scoped_to_one_branch_is_refused_for_another`, `test_a_caller_with_no_companies_is_refused`, `test_the_values_of_denied_fields_never_reach_the_response`. **Cross-branch only — not cross-company (D-4)** |
| SEC-3 | Documents gated on HR roles independently of Positions | **NOT ADOPTED, by decision** | Declined by Surbhi, Decision 4, 31 Oct 2026. R1 is the recorded accepted residual risk; the exchange is the amber line naming the real roles, which **is** tested (`test_it_counts_people_and_names_the_roles`). Not a test gap |
| SEC-4 | Five ordered checks; the browser never gets a `/private/files/` URL | **Met** | `test_the_scope_check_runs_before_the_ticked_check` (AC-79), `test_a_non_ticked_type_is_refused`, `test_a_row_id_cannot_be_walked_onto_another_person`, `test_the_list_never_carries_a_file_address` |
| SEC-5 | Settings are access-granting: System Manager only, refusal logged, one `Version` per real change | **Met, one clause short** | `test_they_are_all_in_the_access_granting_set`, `test_an_hr_manager_is_refused_on_every_one_of_them`, `test_a_system_manager_change_writes_exactly_one_version_row`, `test_employee_document_type_has_no_show_in_positions_field`. **Gap:** the requirement asks to *"assert zero `Version` rows after cancelling"*; the DOM test proves Cancel changes nothing on screen, but **nothing counts `Version` rows after a cancel**. P3 |
| SEC-6 | Own record, length-before-decode, magic bytes, re-encode JPEG 512/82, private `File`, 48 px in the same call | **Met, with a widening** | `TestTheStoredPicture.*` (8), `TestThe48pxCopy.*` (5). §5.1. **The build also accepts WEBP** (`employee_photo.py:99-119`, per OPS-14) which SEC-6 did not name, and **no test uploads a WEBP**. P3 |
| SEC-7 | My Profile write list is a six-field constant ∩ permlevel-0 write | **Met** | `test_the_six_my_profile_fields_are_exactly_these`, `test_an_off_list_field_is_refused_not_quietly_dropped`, `test_a_ticked_but_off_list_field_is_still_not_writable` |
| SEC-8 | Every new "who am I" lookup resolves `status = "Active"` | **Met** | `test_a_leaver_with_a_live_session_is_refused` (AC-24), `test_a_login_with_no_employee_gets_the_designed_state_not_a_failure` |
| SEC-9 | `token_urlsafe(32)`, **only the SHA-256 hash stored**, retired hash in a second field, single use, 7-day expiry, fragment, limiter keyed on the hash | **PARTLY MET — a recorded, decided deviation** | §6. The fragment, body, parameter name, lifetime and single use are all tested. **The hash-only store is not what was built** (Frappe stores the key in clear); the purge replaces it, with 4 tests. The *"retired hash in a second field"* clause is gone with it. **`purge_submission`, the fourth path, is untested.** Surbhi's decision, 31 Oct 2026 |
| SEC-10 | Rate limits on every public endpoint, readable off the function, **plus one functional over-limit test carrying a retry time** | **PARTLY MET** | The table test exists (`test_the_limits_are_readable_off_each_endpoint`: `open_invite` 20, `submit_invite` 3, `upload_invite_file` 12) and `test_the_limit_is_sixty_an_hour_and_readable_off_the_function` for documents. **No test exceeds a limit**, and `retry_after` appears nowhere in `joiner_public.py`. AC-121 is uncovered. **P2** |
| SEC-11 | Joiner uploads: magic bytes, per-file and per-submission ceilings, images re-encoded, PDFs private and attachment-only, never attached to `Employee` | **PARTLY MET** | Covered: `test_an_exe_renamed_as_a_pdf_is_refused_on_its_bytes`, `test_a_type_nobody_asked_for_is_refused`, `test_an_image_is_re_encoded_so_its_metadata_is_gone`, `test_an_oversized_payload_is_refused_before_anything_is_decoded`, `test_submitting_creates_no_employee…`. **Not covered:** nothing asserts the stored joiner `File` is `is_private = 1` or attached to the new doctype; and **`MAX_FILES_PER_TOKEN = 6` and `MAX_BYTES_PER_TOKEN = 20 MB` (`joiner_public.py:78-81`) are never exercised.** **P2** |
| SEC-12 | A submission never becomes an Employee by itself; no joining date | **Met** | `test_submitting_creates_no_employee_and_does_not_move_the_series`, `test_no_joining_date_is_anywhere_on_the_row`, `test_linking_the_employee_is_what_moves_it_on`. The joining-date absence matters — the back-dated-joining absence backfill is a logged DTC fault, not a theory |
| SEC-13 | One identical answer to every wrong input | **Met, and over-satisfied** | §5.2 — verified byte for byte, seven inputs, one answer, one exception class |
| SEC-14 | No Guest permission row; no Web Form onto `Employee`; no enumeration; no new roles | **Met** | `test_guest_cannot_read_or_list_the_doctype`, and I confirmed the DocType JSON directly: permissions are System Manager, HR Manager, HR User — **no Guest row** |
| SEC-15 | Public page hardened like `enrol.html`: `no_cache`, `X-Robots-Tag` header **and** meta, `no-store`, `no-referrer`, nothing from another host, token out of the address bar | **PARTLY MET — now partly proved by me** | **No Python test fetches the page**, and slice 013's equivalent (`test_field_app_step3_013.py`) was not copied. I proved the **meta tags, the zero external assets and the token leaving the address bar** in a real browser (§5.3). **The three HTTP headers remain unobserved** (N-7) and are set inside a silent `except Exception: pass`. **P2** |
| SEC-16 | No new `ignore_permissions` beyond the `File` and `Version` inserts; no new CI gate | **Met by the gate, above the described number** | `test_portal_security_010.py:857-884` carries a ceiling per new file: `employee_photo` 3, `my_profile` 1, `positions_profile` 0, `employee_documents_read` 1, `people_settings` 0 — five, each argued in the comment, not two. No new gate in `ci.yml` |

### 7.2 Privacy

| ID | Requirement | State | Evidence |
|---|---|---|---|
| PRIV-1 | The notice names **every** surface, Hindi at parity, rendered **before** the control | **PARTLY MET** | DOM test lines 121-146: `compareDocumentPosition` proves the notice precedes the camera, and the staff directory, organisation chart, team pages and **appraisals** are each named separately; the conditional birthday-email sentence is asserted **both ways**, which is right — claiming mail when there is none is also wrong. `TestPhotographsInEmails` (8 tests) covers counsel's tick. **The Hindi half is untested and untestable here (N-3)** |
| PRIV-2 | The employee can remove their own photo; field cleared, both files' **bytes** deleted; every surface falls back to initials | **Met** | `test_removing_clears_the_field_and_deletes_both_files`, `test_ten_replace_cycles_leave_exactly_two_files` (two, not twenty-one), `test_removing_the_picture_clears_the_login_too`, `test_a_person_with_no_photograph_carries_neither` |
| PRIV-3 | Purpose limitation as a refusal: no matching, scoring, emotion analysis, no reuse between check-in and profile photos, no photo into a prompt, no chart-as-image | **Met** | `TestAPhotoNeverReachesAModel` — a **static test over the real source tree**, four methods including `test_the_two_photo_stores_are_never_joined` and `test_no_matching_scoring_or_emotion_wording_exists_about_a_face`. The last greps for the **intention**, not for a library, which is the right shape |
| PRIV-4 | Minimisation: the mini profile is its own call; no personal field joins `position_table`; the 48 px copy only; query count flat 20 → 400 | **Met** | `test_the_thumbnail_read_is_one_statement_whatever_the_headcount`, `test_the_cards_of_a_whole_subtree_cost_two_statements_not_one_each`, `test_a_second_ask_for_the_same_person_costs_nothing`, `test_one_call_answers_the_whole_drawer` |
| PRIV-5 | The access record holds who / whose / which type / when and **nothing from the document**; not for your own; one row per viewer per document per day | **Met** | `test_opening_a_document_writes_one_row_with_the_right_columns`, `test_the_row_holds_nothing_from_the_document_itself`, `test_twice_in_one_day_is_one_row`, `test_a_person_opening_their_own_writes_nothing`, `test_an_ordinary_employee_cannot_read_the_record` |
| PRIV-6 | Retention is a setting read by a daily erase job; legal hold wins; a count is reported; **no "keep for ever"** | **Met, and thoroughly** | `TestRetention` — 13 methods, including `test_no_setting_can_mean_keep_for_ever`, `test_legal_hold_wins_however_old`, `test_the_erase_takes_the_files_with_it`, `test_the_erase_is_real_deletion_not_a_flag`, `test_the_warning_must_come_before_the_deletion`. The not-hired clock runs from `closed_on`, not `modified` — a test caught that, and it was a real bug |
| PRIV-7 | Form ships off; switching it on needs a deliberately-set retention period | **PARTLY MET — the precondition was removed by decision** | `test_it_ships_off`, `test_nothing_works_while_it_is_off`, `test_a_guest_cannot_tell_whether_it_is_off_or_their_link_is_wrong` all pass. The `Version`-row precondition was dropped after counsel answered on 29 Oct 2026; the test that used to enforce it says so in its own docstring. **A decision, not an oversight** |
| PRIV-8 | The joiner's notice before the first question, the **configured** period, who sees it, a real contact, Hindi at parity | **MET except Hindi — and I proved the DOM-order clause** | `test_the_joiners_screen_states_the_configured_numbers`, `test_the_welcome_screen_refuses_to_render_with_no_contact`. The *"before the first input in the DOM"* clause had **no test**; I proved it in a browser with `compareDocumentPosition` (§5.3). **Hindi: N-3** |
| PRIV-9 | A closed seven-field server allow-list; no bank, salary or statutory field | **Met** | `JOINER_FIELDS` is exactly `full_name, mobile, personal_email, current_address, emergency_contact_name, emergency_relation, emergency_phone`. `test_only_the_closed_allow_list_is_stored` posts `bank_ac_no`, `ctc` and `date_of_birth` through the guest endpoint and asserts none of the three **values** reaches the saved row; `test_the_allow_list_has_no_bank_salary_or_statutory_field` pins the list. I confirmed the same seven in the browser payload (§5.3) |

### 7.3 The structural claims, checked against the diff rather than the prose

Four claims that matter for the security review, each verified against
`git diff a378af03~1..30660e28` rather than taken from the notes:

| Claim | Verified |
|---|---|
| Three new `allow_guest` endpoints and no more | **Yes — exactly three**, and every one is `methods=["POST"]`. There is no guest `GET` anywhere in the slice |
| One new scheduled job | **Yes — one**, `alvoraa_portal.joiner_housekeeping.daily`. No queue, no worker |
| The access log's permissions are unchanged | **Yes.** The only additions to that JSON are two `"read_only": 1` **field** properties on the two new columns. **No role row, no `read`/`write`/`create`/`report`/`export` flag changed** |
| No `has_permission` hook, no `permission_query_conditions` | **Yes — none added.** Which matters, because `has_permission` on a child table is always False, and `Employee Document` is a child table (ALV-256). The guard is on the parent, as it must be |
| The joiner's page does not trip the "website pages post to `/`" trap | **Yes, it is clear.** `joiner.html:165` sets `var API = "/api/method/alvoraa_portal.joiner_public."` — a real API path, not a website-page POST to `/` carrying `cmd`. A path-based gate can see these calls. Worth recording, because that trap has bitten this product before |

**One gap this confirms (AC-126).** `test_endpoint_guards_045.py` asserts that
**slice 045's** endpoints are *not* `allow_guest`. It is a deny-list for that
slice, so it does **not** enumerate the new ones. **Nothing anywhere asserts
that the three new `allow_guest` endpoints are the only three**, which is what
AC-126 asked for. A future fourth would be added in silence. **P2 — and it is a
cheap test to write.**

### 7.4 Personal data in logs — checked by reading every line

I read **every** `logger` call in the eleven new modules. They carry: record
ids, the actor (`frappe.session.user`), byte counts, document **type** names and
timestamps. **No joiner's name, no field value, no file URL, no token, no
statutory number.** The engineer's claim holds.

One nuance for the record: `frappe.session.user` is an email address. That is
the **actor** identifier and is the established pattern across this product and
what PRIV-5's "who" requires — not a finding, but say it out loud rather than
claiming "no personal data at all".

---

## 8 · The OPS items

53 items. They are not all in §3 of `07-devops-inputs.md` — §1/§6 holds OPS-1…11,
§3 holds OPS-12…38, §4 holds OPS-39…53.

**Assertable and covered (22):** OPS-2, 4, 6, 7, 8, 12, 13, 15, 18, 19, 20, 21,
22, 23, 25, 26, 28, 39, 40, 42, 43, 45.

Highlights I checked myself: **OPS-21** — `POS_OPEN_DEPTH === 1` and
`POS_NAMES_SHOWN === 3` asserted literally and the first paint capped at 60
faces (`check_positions_tree.js:1557-1576`); **OPS-19** — a face is emitted with
`data-src` and is **never** `loading="lazy"`; **OPS-45** —
`run_dom_tests.js:120` registers the new suite and line 129 raises
`EXPECTED_BROWSER_TESTS` to 20, in the same commit, and I confirmed 20 run.

**Partly covered (4):**

| ID | What is missing |
|---|---|
| OPS-14 | WEBP is accepted by the code and **never tested** |
| OPS-30 | The per-file ceiling is covered; the **per-token file count and byte ceiling are not** |
| OPS-33 | The invariant half is covered; the files-tree reading is release-time |
| OPS-44 | `joiner.html` genuinely has no external asset — **I proved it in a render** — but **nothing asserts it**, and `check_portal_assets_gate.py`'s `PAGES` still lists only `hrms-employee.html`. One `<script src=…>` added later would pass CI silently. **P2** |

**Not adopted by decision (4):** OPS-1 (faces are on the cards, Decision 2),
OPS-3 (DevOps' own advice, superseded by OPS-17), OPS-5 (078-SEC-5 won — the
`Employee Document Type` tick would have given HR Manager `write`), OPS-9
(superseded by OPS-36).

**Out of this slice by their own wording (2):** OPS-48, OPS-50.

**Settled by me this run (1):** **OPS-41** — the `get_web_form_request`
signature on v16.35.0, §5.4.

**One that could be tested and is not (1):** **OPS-29** — "nothing stored before
the token is validated; no document bytes in `localStorage`". The rule is
written at `joiner_public.py:36-37` and nothing asserted it. **I proved the
localStorage half in a browser** (§5.3): typed answers are kept, document bytes
and the token are not. The "nothing stored before validation" half is still
unasserted.

**Release, deploy, config or monitoring — no test can prove these (18):**
OPS-10, 16, 17, 24, 27, 31, 32, 34, 35, 36, 37, 38, 46, 47, 49, 51, 52, 53.
They belong in the release checklist, §12. **OPS-24 / OPS-52** (`max_file_size =
5` in System Settings) and **OPS-38** (count faces on dev) are the two that must
not be forgotten — AC-72 depends on the first.

---

## 9 · Non-functional results

**Every number in this section is the engineer's, re-reported as theirs.** I did
not re-measure at volume (N-5). What I can confirm is that the **assertions**
behind them are real tests and that they pass:

| Thing | Number (engineer's) | Is it asserted? |
|---|---|---|
| `position_table` | **3 statements** for 403 people | yes — the third is the batched thumbnail read |
| A chart subtree's cards | **2 statements**, memoised per request | yes — `test_the_cards_of_a_whole_subtree_cost_two_statements_not_one_each` |
| The thumbnail read | **1 statement** for 20 ids **and** for 400 | yes — `test_the_thumbnail_read_is_one_statement_whatever_the_headcount`. **This is the gate, and it is the right shape**: it asserts flatness, not a wall-clock figure |
| First paint | 16 boxes, 16 faces, **~10 KB** | the ≤ 60 face cap is asserted; the KB figure is recorded, not asserted |
| Stored photograph | 512 px q82; worst case measured **82 KB**; build ceiling **120 KB** | yes — `test_the_stored_size_is_inside_the_build_ceiling`. **The spec's p95 ≤ 50 KB is deliberately not asserted** (OPS-42), and I agree: 50 KB would fail a build on one employee's busy photograph |
| The 48 px copy | **0.4–0.7 KB**, ~4 ms in-request | size asserted indirectly; the ms figure is recorded |
| Making the stored copy | **~240 ms** of CPU in the uploader's own request | **not asserted.** It is the slice's one real cost and the honest number to carry into the release note — an import of 403 photographs is ~1 min 40 s |
| New indexes / background jobs / queues / workers / caches / containers | **none**, bar the one daily erase job | confirmed by reading `hooks.py` |

**Resilience** is genuinely good and genuinely tested: the thumbnail handler can
never fail an Employee save (`test_a_picture_pillow_cannot_read_does_not_fail_the_save`),
`ocFaces` is guarded, the erase catches per row so one bad file cannot stop the
job, the daily job is safe to run twice, and a failed upload never discards what
was typed. I confirmed the last of these in a browser.

**Accessibility:** no a11y tooling exists in this repo. What I could check
mechanically, I did — on the joiner page every input has its own label, every
control is ≥ 44 px and text is ≥ 16 px. **The portal side is not swept.**

On the drawer's focus trap I have a correction to make against my own first
reading. **It does exist** — `portal.js:10821-10832`, bound on `document`,
gated on `#emp-drawer.open`, wrapping first-to-last with `shiftKey` handled
properly. The picker has its own at `portal.js:7467`. What is missing is only
the **assertion**: the DOM test proves the drawer is a named modal dialog
(AC-59), that the first Escape closes the enlargement only and the second
closes the drawer, and that focus returns to the name that opened it (AC-60,
AC-62) — but **nothing exercises Tab**. So this is test debt, **P4**, not a
missing control. Dark theme (AC-133) is unswept. A human pass is still needed —
§12.

---

## 10 · Acceptance criteria — coverage

**The spec defines 151 criteria across ids AC-1 … AC-143** (143 base numbers,
plus `AC-17a/b`, `AC-25a/b`, `AC-37a`, `AC-131a/b/c/d`, less a bare `AC-131`
which has no row). There is **no AC-144…151**, and **no AC-72a** (§4.6).

Roughly **103 criteria have a test that names them or plainly exercises the
behaviour**, about **18 are covered only in part**, and **30 have no test**.
Rather than reprint 151 rows, here is **every AC with no test**, which is what a
reader needs:

| AC | What it wanted | Why there is no test | Now? |
|---|---|---|---|
| AC-17a, AC-17b | The password card's wording; landing back on the portal | not written | gap |
| **AC-20** | Documents card absent when the plan is off | **the card is not on My Profile at all** — D-5(c) | **blocked by a parity gap** |
| AC-34 | Count faces by hand on dev | release-stage, on dev | N-4 |
| AC-37 | The Organisation page's ⚠ DECISION D choice | it is a decision row, not behaviour | n/a |
| **AC-38, AC-40** | `@media print` strips faces and the drawer | **CSS rules with no assertion.** The notes list these as satisfied; they are not proved | gap |
| AC-39 | The wall-chart "Include photographs" tick | **not built** — ⚠ DECISION C's second half | not built |
| AC-43, AC-49 | The POS-PROFILE failure at 10 s; the full picture failing | built, untested | gap |
| **AC-72** | `max_file_size = 5` in System Settings | a per-site setting, left for release | N-4 |
| AC-81 | R1 recorded with her name and date | documentary | n/a |
| AC-83, AC-85, AC-86 | Three settings-card "at rest" sentences | built, untested | gap |
| **AC-107, AC-109, AC-110, AC-113** | The joiner's screens | the page had never been rendered | **all four I have now proved in a browser** (§5.3) |
| AC-117 | The J-E2 wording on a failed upload | built (`joiner.html:355`), untested | still a gap — my stub never failed an upload |
| AC-118, AC-119 | The retention precondition | **superseded** — PRIV-7's gate was removed by decision | n/a |
| **AC-121** | A limit refusal carries a retry time | `retry_after` does not exist in the code | **real gap, SEC-10** |
| AC-126 | A registry test enumerating the new `allow_guest` endpoints | `test_endpoint_guards_045.py` covers only the 045 set; the three new guest endpoints are unenumerated | gap |
| **AC-132** | The public page's headers and meta | no test fetched the page | **meta tags and asset isolation now proved** (§5.3); **the HTTP headers are still unobserved** (N-7) |
| AC-133 | Dark-theme sweep | no tooling | N-6 |
| AC-135, AC-139 | Files-tree size per release; a pre-onboarding tenant | release / environment | N-4 |
| **AC-140** | **This report must say whether the fixtures existed** | — | **§11, done** |
| AC-141, AC-142, AC-143 | Hindi | **impossible in this repository** | N-3 |

**Claims in the implementation notes I checked and found overstated.** §3.1
lists whole AC ranges as satisfied that contain untested members. The concrete
ones: **AC-20, AC-38, AC-40, AC-43, AC-49, AC-81, AC-83, AC-85, AC-86**, plus
the 44/48 px and 150 ms figures under AC-1, AC-14 and AC-28, which are CSS with
no assertion, and AC-6's 15-second wording, which the DOM test says in its own
comment it does not exercise. None of this is dishonest — it is a block-range
summary hiding its members — but a reader should not take §3.1 as a per-AC
claim.

---

## 11 · AC-140 · Did the fixtures exist when each result was produced?

AC-140 requires this report to say so plainly. **Yes — for every Python result
in this report, and they are real.**

`alvoraa_portal/alvoraa_portal/tests/fixtures_078.py` builds its data **inside
each test class's `setUpClass`/`setUp`**, on `test078`, so no 078 result was
ever produced against an empty database. I verified the three that matter:

| Fixture | Real? |
|---|---|
| **The GPS-carrying PNG** (AC-137) | **Yes, and the only proof the metadata strip gets.** Built in code with a true GPS IFD, and the test asserts the GPS is in the **source** before asserting it is gone from the stored file. §5.1 |
| **Employee documents** (AC-136) | **Yes.** `give_documents` creates a **genuine one-page PDF** built by Pillow — after a hand-written `b"%PDF-1.4…"` string was found not to be a PDF at all (Frappe *parses* what it is given) — stored as a real **private** `File`, with a real `Employee Document` child row across the ticked/unticked boundary, for two document types in different categories |
| **Two HR users, one branch-scoped** (AC-138) | **Yes.** `hr_wide_user` and `hr_store_user`, the latter given a real Branch `User Permission` |

**All of it is synthetic and invented** — `S078WithPhoto`, `S078Gps`,
`s078hrstore@…`, a blank grey PDF, a flat-colour PNG. **No real employee data
was used anywhere**, no production or dev data was read, and nothing in this
report contains a real person's details.

**Two caveats, both mine to raise:**

1. **The fixture sets a child field with `db.set_value`** —
   `frappe.db.set_value("Employee Document", row.name, "attachment", f.file_url)`.
   That is not how the app writes it, and the standing lesson is to build
   fixtures the way real data is built. A controller hook on that child row
   would be bypassed. **P4**, but it is the shape that has produced phantom bugs
   before.
2. **Dev has no photographs, no `Employee Document` rows and no document
   types.** That is still true and I did not change it — it is why these
   fixtures had to exist. It also means **AC-34 and OPS-38 cannot be done until
   somebody puts data on dev.**

---

## 12 · What is deliberately not automated — the human checklist

| # | Check | Who | When |
|---|---|---|---|
| H-1 | **Build an image from this commit** and confirm the Frappe patch step succeeds, then add one photograph in Desk and see the 48 px copy appear. This is the last of D1 | DevOps | before anyone is told AC-25b works |
| H-2 | **Run `browser_check_positions.js`** against a site **that actually has seats** — `test078` has none, so this cannot be done on it. The chart, the seat tray and the chart card have never been seen in a real browser (N-1). Playwright and Chromium **are** installed on this machine; pass `PLAYWRIGHT=<path to the npx-cached module>` | Test / DevOps | before release |
| H-3 | **Count `<img class="av">` on a first paint of Positions on dev** — AC-34, OPS-38 | DevOps | on dev, before release |
| H-4 | **Set `max_file_size = 5`** in System Settings on dev, then production — AC-72, OPS-24, OPS-52. A site setting, Surbhi's word | Surbhi | at release |
| H-5 | **Dark-theme sweep** of every new screen and state — AC-133 | UX | before release |
| H-6 | **Keyboard-only pass** over the drawer, the enlargement and the picker. Both focus traps are built; **neither is asserted by any test**, so a regression in them would be silent | UX / Test | before release |
| H-7 | **Hindi** — there is no Hindi file in this repository and the joiner's page is not wrapped in `drT()`. AC-141/142/143 cannot be met here (N-3) | Product | decide: defer, or do the site-level import |
| H-8 | **Read the joiner's page as a joiner would**, on a real phone, on a poor connection | UX | before any tenant switches it on |
| H-9 | **Confirm the three security headers** really reach the browser on a served site — they are set inside a silent `except` (N-7) | Security | before release |
| H-10 | **Decide D-1**: is a joiner's submission tenant-side or control-plane? | Security / Privacy | **blocks** |
| H-11 | **Restore drill** with `--with-files` on dev — OPS-46 | DevOps | before release |
| **H-12** | **Re-run the `alvoraa_portal` suite cleanly to the end.** Batch 3 was terminated part-way and I had a `bench execute` running against the same site at the time. Give the container room (the host had 310 MB free) and touch nothing else while it runs. It must also settle `test_attendance_correction::test_switched_off_refuses_in_plain_words` | Test | **before release** |
| **H-14** | **Judge the `hrms` suite on CI, not locally.** It ran zero tests here because ERPNext's bootstrap cannot build master data on `test078`. CI builds a fresh bench, so it can. **`test_company_scope_194.py` is the one that matters** — it is the multi-company test over the two hrms files this slice changed | DevOps / Test | **before release** |
| **H-13** | **Build the site's assets** (`bench build`, with approval) before judging any email test on a throwaway site, or accept that 8 of the 11 failures seen here are noise. `sites/assets` does not exist on `hrlocal-078` | DevOps | whenever that container is reused |

---

## 13 · Verdict

**Fail.**

Two defects introduced by this slice make the existing suite red (D-1, D-2), and
a red build is a blocked release. Both are small, and neither is a security
hole — but **D-1 needs a decision, not just a line of code**: whether a
non-employee's personal data sits inside the tenant access derivation is exactly
the kind of question the gate was written to force somebody to answer.

Beyond those, the slice is in better shape than its own notes suggest in some
places and worse in others. **Better:** the Frappe patch now applies cleanly to
the version that actually ships, the joiner's page works in a real browser
through all four steps with no console error, SEC-13 is stronger than it was
asked to be, and the GPS fixture is an honest proof rather than a comfort.
**Worse:** three things in the approved prototype were not built and were not
raised (D-5), a joiner can lose their link by tapping through an empty form
(D-3), and cross-company isolation — the thing that finds the worst bugs in an
HRMS — has no test at all in this slice (D-4).

**What I would require before release:** D-1 and D-2 fixed and **a complete,
green CI run** — which is also the only place the `hrms` suite and a real image
build can be judged (H-12, H-14, H-1);
D-3 either fixed or accepted in writing by Surbhi, because it is irreversible
for the joiner it happens to; and D-5's four parity gaps put in front of her as
a decision rather than discovered later, per the standing prototype-parity rule.

**What I would accept as known defects, in writing:** D-4 (with the release note
saying cross-company isolation rests on a helper tested elsewhere), D-6, D-7,
SEC-10's missing over-limit test, SEC-11's missing storage assertions, SEC-15's
unobserved headers, and the Hindi gap, which no commit in this repository can
close.

**Nothing in this report authorises a deploy.** No push was made, no deploy
command was run, and no setting was changed on any shared site.

---

## 14 · Labelling what I leave behind

| Label | Items |
|---|---|
| **Dangerous debt — escalate** | **D-1** — an unclassified DocType means an unmade tenancy decision about a non-employee's personal data. **D-3** — irreversible for the person it happens to |
| **Temporary debt — what removes it** | **N-1** one browser run against a served chart · **N-2** one real image build · **SEC-10/SEC-11** four small tests · **SEC-9's purge path** one test · **AC-126** one registry test |
| **Intentional trade-off** | The clear-text token window (Surbhi's, 31 Oct) · a used link indistinguishable from an unknown one · `position_table` at 3 statements not 2 · **`thumbnails_for`'s `ignore_permissions` — I checked this one and it is sound** (see below) · the shared `#emp-drawer` |

**On that `ignore_permissions`**, because it is the one a security reviewer
should look hardest at: `people_fields.thumbnails_for` reads `File` with
`ignore_permissions=True`, because Frappe's own `File` query condition narrows a
Website User to `owner = me`, which would hide every colleague's thumbnail and
strip the faces from the one chart a frontline employee can open.

Three things make it safe, and I verified each:

1. **It selects two columns and returns two.** `fields=["attached_to_name",
   "file_url"]`, returning `{employee: url}`. No name, no status, nothing else.
2. **The URL is to a private file.** `employee_photo._store` is the single
   helper that creates **both** the 512 px and the 48 px rows, and it hardcodes
   `"is_private": 1` (line 239). So the URL alone is not the face.
3. **Fetching the bytes still asks permission** on the parent Employee.

**One small test gap:** `test_the_stored_file_is_private` asserts privacy on the
**512 px** file. Nothing asserts it for the **48 px** copy. Both come from one
`_store`, so the risk is slight — but the thumbnail is the one whose URL is
handed to every chart reader, so it is the one worth pinning. **P4.**
| **Acceptable simplification** | `?seat=` instead of a route · the Organisation page capping at three names with no tray · HR's joiner screen being the Desk form · the erase leaving a shell with no personal data |
| **Test debt (P4)** | SEC-13's stale *"four cases"* message · `test_our_own_row_never_holds_the_key` keying partly on field **names** · the document fixture setting a child field with `db.set_value` rather than the way the app writes it |

**No hollow tests found.** I went looking for tests that pass whatever the code
does — the usual shapes are a `frappe.get_all` standing in for `get_list`, a
string test matching its own comment, and an assertion with no teeth. The
engineer had already found and fixed all three of those in their own suite and
said so. The tests I read assert real behaviour, and several of them caught real
bugs during the build.

---

## 15 · Subtract pass

Read back once, asking only: **what can I delete and still meet the
requirement?**

**Removed:**

1. **A 151-row AC table.** It would have been three pages restating the
   subagent's inventory. §10 keeps only the ACs with **no** test, which is the
   only part a reader acts on, plus the count.
2. **A second baseline test run** against `origin/dev` to attribute the
   remaining failures. D-1 and D-2 are **proved by construction** — the DocType
   is new and classified nowhere; the orphan endpoint is new and unreadable — so
   a baseline would have cost an hour and proved nothing more. The other nine
   were attributed by **reproducing their root cause directly** instead, which
   was cheaper and stronger.
3. **Chasing ERPNext's test bootstrap any further.** After the fiscal-year
   clash came a missing Item Group root, and behind that would have been more.
   Rebuilding ERPNext master data on a throwaway would have been me reshaping
   the site rather than testing the branch — and CI already builds the fresh
   site that makes it work. I stopped, restored what I had changed, and wrote
   it down.
4. **Three "failures" from my first browser run.** They were my harness, not the
   product. I fixed the harness and report the corrected result, rather than
   listing them as defects with a footnote.
5. **A per-OPS 53-row table.** §8 groups them by what a reader does about them.
6. **My own re-measurement of the NFR numbers.** The gate that matters asserts
   *flatness* (20 ids cost the same as 400), and it passes; re-timing a wall
   clock on a laptop would have been a worse number than the engineer's, not a
   better one.

**Not removed, and why:** §5's four subsections look like a lot of space for
things that *passed*. They stay because each one converts a **"could not
check"** in the engineer's notes into a checked result — which is the whole
point of this report, and the reader cannot tell the difference without the
evidence.

**Tests I wrote:** none that live in the repository. My browser work is a
harness in the scratchpad, not committed — deliberately, because
`browser_check_positions.js` and the DOM suite are where this repo keeps browser
checks, and adding a third pattern would be a cost. **If the team wants the
joiner page covered in CI** — and SEC-15, OPS-44 and AC-132 say it should be —
the right home is a `joiner_078_test.js` in the existing DOM suite, which would
need `EXPECTED_BROWSER_TESTS` raised to 21 in the same commit, per OPS-45. That
is a recommendation, not a thing I did.
