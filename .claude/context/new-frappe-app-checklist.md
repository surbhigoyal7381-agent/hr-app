# Adding an existing Frappe app — checklist

Built from the Frappe Learning (`frappe/lms`) walkthrough on 11 Sep 2026. Use it whenever
a slice installs an app someone else maintains — Frappe Learning, Frappe Payments,
India Payroll, Helpdesk, CRM.

Each agent owns its section. **Record the answers in the slice artifacts, not here.**
Only change this file to add a lesson learned.

---

## What the Frappe Learning check found

Verified against the repository on 11 Sep 2026. Re-check before relying on it.

| Question | Answer |
|---|---|
| Works with our Frappe v16? | Yes — it declares Frappe ≥ 14 and ≤ 17-dev |
| Needs other apps? | **Yes — Frappe Payments must be installed first** |
| How big? | 70 doctypes |
| Name clashes with our apps? | None found. Not yet re-checked against Frappe and ERPNext |
| Brings its own website? | Yes — its own pages at `/lms`, with its own look |
| Installs data or fields? | Yes — custom fields and categories as fixtures, plus an install hook |
| Overlaps what we already have? | **Yes.** Frappe HR already has Training Program, Training Event, Training Result, Skill and Employee Skill Map |
| Overlaps a sibling product? | **Yes.** Its job board overlaps Alvora Hire |

The lesson that generalises: **an "install an app" request is never just an install.**
It is a decision about duplicate data models, a second look and feel, public pages, and
extra apps to run.

---

## Product manager — `01-product-brief.md`

- [ ] Which parts does Frappe HR or ERPNext already do? Name the doctypes.
- [ ] Which parts overlap a sibling product (Alvora Hire, Alvora Gig)? Drop them from
      the slice.
- [ ] Kano class and market-demand evidence for the parts we keep.
- [ ] Which plans include it — the feature in `alvoraa_portal/subscription.py`.

## UX designer — `01a-ux-opportunities.md`, `01b-ux-design.md`

- [ ] Does the app bring its own portal or look? Decide with the user: link out, restyle,
      or show it inside our portal using the app's data.
- [ ] How each persona reaches it from the employee portal.
- [ ] Frontline use on a low-end phone, and in Hindi.

## Security and privacy — `01c-security-privacy-requirements.md`, `06-security-review.md`

- [ ] Public pages, guest access and self sign-up — per tenant, and off by default.
- [ ] New personal data (scores, certificates, activity) — sensitivity class, purpose,
      retention.
- [ ] Roles the app creates and the permissions it grants by default.

## DevOps — `07-devops-inputs.md`

- [ ] The chain of required apps, and the install order.
- [ ] Supported version range. **Pin a release tag or commit — never a moving branch.**
- [ ] Image size, build time, asset size, and migrate time on a copy of real data.
- [ ] Workers, queues and scheduled jobs the app adds, and whether a worker listens.
- [ ] Downgrade path: hide the module and keep the data. **Never uninstall on a live
      tenant** — it drops tables.

## Business analyst — `02-functional-spec.md`

- [ ] Where two data models describe one thing (the app's skills vs Frappe HR's Skill),
      name the single source of truth.
- [ ] For each of the app's features: configure, extend or drop.

## Full-stack engineer — `00-impact-analysis.md`, `03-implementation-notes.md`

- [ ] Run the doctype-clash check against the new app as well.
- [ ] Check whether the app's fixtures overwrite any of ours.
- [ ] Install it only for the tenants whose plan includes it, in provisioning.

## Test automation — `04-test-report.md`

- [ ] Install on a fresh site, the way CI does.
- [ ] Negative permission tests for every role the app adds.
- [ ] Check that private pages are not reachable without signing in.

## Reviewer — `05-review.md`

- [ ] Every row above answered with evidence, or waived by the user in writing.
