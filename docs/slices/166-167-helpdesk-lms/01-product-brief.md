# Product brief — ALV-166 Frappe Helpdesk, ALV-167 Frappe LMS

**Status:** DRAFT for review. **Confirmed** = checked in this repo. `[recall — verify]` = not re-checked today.

## 1 · What each would add

**Helpdesk** — a ticketing desk: agents, SLAs, a customer portal, email-to-ticket.
- CXO: none directly — a support-ops tool, not a performance one.
- HR Manager: **could** become an internal "ask HR" desk (leave/payroll queries with an SLA and a trail) — but that is a *new use*, not what Helpdesk ships for. Frappe HR has no ticketing today. **Confirmed** — no `helpdesk`/`ticket` hits in `hrms/`.
- Employee: only useful if we stand up that internal desk; otherwise nothing changes for them.
- Customers: useful only if we resell it as **their** external customer-support product — unrelated to HR.

**LMS** — courses, lessons, quizzes, certificates, a public course catalogue.
- Employee: a real "learning" tab — courses tied to onboarding or a KRA. Today Frappe HR already has **Training Program, Training Event, Training Result, Skill, Employee Skill Map** (Confirmed, per `new-frappe-app-checklist.md`, itself built from the same repo). LMS overlaps this directly: two ways to say "this person completed this training."
- HR Manager: needs one source of truth for "who completed what" feeding appraisal KRAs — that source today is Training Program/Result, not LMS.
- CXO: none directly.
- No existing portal learning feature beyond Training Event notices (Confirmed — only a training-event email template found).

## 2 · Recommendation

| App | Recommendation | Kano-lite |
|---|---|---|
| **Helpdesk** | **Do not install now.** It solves a support-desk job we have not been asked to sell. If the job is "internal HR query desk," that's a smaller, cheaper build on Frappe HR's own ticketing pattern — no need for a second app with its own portal, roles and email pipeline. | **Indifferent** (proxy) — no customer has asked for it; nothing in `product-context.md` §7 whitespace or §6 refusals names it. |
| **LMS** | **Install, off by default, sell as an opt-in feature** — but scope it narrowly: certificates and course completion feeding the existing Skill/Training Result data, not a second training data model. Needs a Business Analyst pass on "configure vs extend vs drop" per the checklist before any tenant gets it. | **Performance** (proxy) for mid-market buyers comparing "does it have e-learning" — but only if we resolve the Training Program overlap first, or it becomes two competing sources of truth (Risk in `product-context.md` §10 pattern). |

Neither is on `product-context.md` §7 whitespace or named by any customer yet — both are `[ASSUMPTION]` demand, not evidence. **This is the biggest open question: who asked for these, and why now?** (see Open questions.)

## 3 · Pinned versions

- **Helpdesk** — not proceeding now; if revisited, pin a release tag (never `develop`), and confirm Frappe v16 support first — Helpdesk has historically tracked Frappe HEAD more loosely than CRM. `[needs validation]`
- **LMS** — pin a tagged release or a fixed commit, same rule as CRM (`CRM_TAG`) and WhatsApp (`WHATSAPP_COMMIT`) in `deploy/Dockerfile`. Frappe Learning is documented in our own checklist as declaring "Frappe ≥14, ≤17-dev" (Confirmed, 11 Sep 2026 check) — compatible with v16, but that check predates any specific LMS commit choice; DevOps must re-verify against the exact commit and Payments version we'd pin.
- LMS **requires Frappe Payments installed first** (Confirmed, `new-frappe-app-checklist.md`) — one more app in the chain, one more thing to pin and build.

## 4 · Order and size

- **Do not touch the image or `subscription.py` FEATURES registry for Helpdesk.** No slice needed unless the internal-desk idea is chosen instead (smaller: reuse HR ticket pattern, no new app).
- **LMS, if approved:** follow the CRM/WhatsApp precedent exactly — add to `deploy/Dockerfile` (new ARG + pinned tag/commit, plus Payments), add `lms` as `opt_in: True` in `subscription.py` FEATURES, add the install branch in `deploy/provision_tenant.sh` guarded by `has_feature lms`. **No new nginx route needed if LMS serves itself at `/lms` the way CRM does at its own path** — DevOps to confirm the generic proxy path covers it (per groundwork, likely yes, same pattern as CRM).
- **First tenant:** a demo/internal tenant only (e.g. the Sargam demo tenant, not a live customer) — nobody has bought this yet, and a live customer should not get a public course catalogue and public sign-up switched on by accident.
- **Size:** one slice, thin — course + certificate + a portal card linking out, not a rebuild of Training Program.

## 5 · Risks

- **Build time and image size (ALV-164).** CRM alone needed a "free disk on the runner" step (Confirmed, `.github/workflows/build-image.yml` line ~144, runner has ~14 GB free). A second Vue front end (LMS) built at image time adds more disk pressure and more build minutes on every push, whether or not any tenant uses it. **Must measure before committing to "always in the image."**
- **Public pages, by default.** LMS ships public course pages and public sign-up (Confirmed intent per groundwork and the Learning checklist's "brings its own website" finding). Per `security-compliance-baseline.md` and refusal-style thinking in `product-context.md` §6, any public sign-up must be off per tenant unless explicitly turned on — same discipline as CRM's opt-in gate.
- **Helpdesk's email-to-ticket** is an inbound mail pipeline — the product explicitly avoids requiring inbound firewall rules of customers (§6 item 9); email-to-ticket is a different mechanism but still needs a security read before ever being considered.
- **Two sources of truth for training.** If LMS ships without resolving the Training Program/Result overlap, HR Managers get two conflicting "did this person complete training" answers feeding appraisal KRAs — the exact failure mode `product-context.md` §10 already warns about ("wrong numbers before new numbers").
- **Tenant isolation.** Both apps are new attack surface for a security-conscious buyer base (product-context §2, §9 — security review is a real sales gate). Neither should reach any tenant without the Security & Privacy engineer's sign-off per the checklist.

## 6 · Acceptance criteria (if LMS proceeds; Helpdesk has none — not proceeding)

- LMS is invisible on every tenant until a named tenant has `lms: true` in its feature list.
- Public course catalogue and public sign-up are off by default per tenant; on only where explicitly enabled.
- Course completion writes to (or reads from) the existing Training Result / Skill data — no second "did they train" answer for the same person.
- Image build time and size increase are measured and reported before the feature registry entry ships.
- A negative-permission test proves an Employee-role user from Tenant A cannot see Tenant B's course or certificate data.

## 7 · Decisions for Surbhi

1. **Recommend: do not install Helpdesk now.** Who is asking for it, and for what — an internal HR desk, or a resellable customer-support product? These are different products with different personas. *Your call: proceed with Helpdesk anyway, or park it until a real use is named?*
2. **Recommend: install LMS, but scoped to close the Training Program overlap, not duplicate it, and off by default.** *Your call: approve that scope, or do you want LMS's own data model to be the source of truth instead (bigger, touches appraisal KRA scoring)?*
3. **Recommend: first install goes to a demo tenant only (Sargam or similar), never a live customer**, since go-live is dated Oct 2026 and nobody has bought either app yet. *Your call: confirm, or name a specific tenant?*
4. **Pinned versions and the Payments dependency need a DevOps pass** before any Dockerfile change — *do you want that scheduled now, or only once you approve proceeding with LMS?*

## Open questions

| Question | Owner | Blocks |
|---|---|---|
| Who actually asked for Helpdesk and LMS, and why now? | Surbhi | Whether either is worth building at all — no demand evidence found in this repo or `product-context.md` |
| Is the "internal HR helpdesk" idea real, or should Helpdesk stay parked? | Surbhi | Whether any Helpdesk slice starts |
| Should LMS reuse Training Program/Result as its source of truth, or replace it? | Surbhi / Business Analyst | Scope of the LMS slice, appraisal KRA integration |
| Exact LMS commit/tag and its Frappe-v16 + Payments compatibility | DevOps | Dockerfile change |

## Assumptions

- `[ASSUMPTION]` Neither app has a named paying customer waiting; this is speculative capability-building, not a sold commitment. If wrong, say who bought it and revise urgency.
- `[ASSUMPTION]` "Install" means available-but-off, per the CRM/WhatsApp precedent, not on-for-everyone.
- `[ASSUMPTION]` LMS's Payments dependency does not conflict with any existing Payments configuration in this bench — unverified, DevOps to check.

## Kill criteria

- If DevOps reports the image build cannot absorb a second Vue front end within acceptable CI time/cost, drop LMS from the image and revisit as a separately-hosted app or drop entirely.
- If Business Analyst finds no clean way to avoid two competing training-completion records, stop before writing the functional spec.
