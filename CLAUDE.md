# Claude Code Instructions — HR App (Alvoraa)

These instructions are mandatory in every session. They override default behavior.

**Write in simple, plain English — see §6. This applies to every message, not just summaries.**

---

## 1. Branch discipline

- Always work on the **`dev` branch** unless explicitly told otherwise.
- Before any git operation, confirm the working branch is `dev`.
- If on another branch, stash changes, switch to `dev`, and reapply — do not commit to `main` without explicit instruction.
- `main` is reserved for deliberate production releases only.

---

## 2. Mandatory change process — in this exact order

Every change follows these steps in order. Do not skip or reorder them.

**Before writing a single line of code:**

1. **Impact analysis** — cover all four dimensions before opening any file:
   - *Functional*: cross-modular impact (alvoraa_goals, grace_compensation, hrms, erpnext), persona impact (CXO / HR Manager / Employee), HRMS domain impact (leaves, attendance, payroll, appraisals, org structure). Grep all callers of every function being changed.
   - *Non-functional*: evaluate the change against each NFR dimension below and state explicitly whether the change improves, degrades, or is neutral for each one:
     - **Performance** — query count, payload size, render time, N+1 risks, cache hit rate
     - **Security** — permission checks, injection surface, data exposure, `ignore_permissions` scope
     - **Reliability** — error handling, edge cases, graceful degradation, hook side-effects
     - **Scalability** — behaviour under high employee count, multi-company, concurrent requests
     - **Maintainability** — readability, coupling, duplication, testability
     - **Data integrity** — stale data risk, cache invalidation correctness, transaction boundaries
     - **Compliance / privacy** — PII exposure, role-based data scoping

2. **Propose strategy** — present the approach, flag risks and trade-offs, suggest the best engineering path. Apply senior developer judgment: anticipate consequences (e.g. cache invalidation strategy, stale data risk, hook side-effects) without being asked. Do not surface half-solutions that require the user to ask the obvious follow-up question.

3. **Wait for explicit approval** — user reviews the strategy and approves, adjusts, or redirects. "Go ahead with all changes" is approval to implement, not to skip steps 4–7.

**After implementation:**

4. **Run tests** — `bench run-tests --app <app>` for any changed Python module; manually trace all affected UI flows for JS/HTML changes.
5. **Senior architect review** — correctness, edge cases, regressions, security, consistency across all touched files. Re-check each NFR dimension against the actual code written, not just the proposal.
6. **Present findings** — summarise test results, review outcome, NFR assessment before vs. after, confirm readiness.
7. **Wait for deploy approval** — explicit "go ahead" required before any server command.

**The checklist runs BEFORE `git commit`. Committing is part of the deployment pipeline.**

**Fixing a bug and deploying it are two separate steps. "Fix this" is not deploy permission.**

**Senior developer standard:** Anticipate issues before being asked. If a change introduces a caching layer, the invalidation strategy must be defined in the same proposal. If a change touches a shared doctype, cross-module impact must be listed. Do not surface half-solutions that require the user to ask the obvious follow-up question.

Deploy commands that require explicit approval before running:
- `docker cp` (copying files into a container)
- `bench clear-cache` / `bench migrate` / `bench build`
- `nginx -s reload`
- Any `git push` to a remote branch
- Any `scp` or file transfer to the production server

---

## 3. Production environment — do not touch

- **Never modify or delete anything inside `/var/www/html/hr-app`** on the server.
- **Never interrupt, change, or take down the production application** at `https://alvoraa.co/`.
- Production server: see `deploy/server.env` (git-ignored — never commit this file)
- Live domains: `alvoraa.co`, `dev.alvoraa.co`, `minda.alvoraa.co`
- Do not cite `alvoraa.co` as a live URL — it was renamed; current domain is `alvoraa.co`.

---

## 4. Code approach — Frappe-first, no over-engineering

- **All changes must follow the Frappe framework** — use `frappe.get_doc`, `doc.insert`, `doc.submit`, `frappe.get_all`, `frappe.whitelist`, child-table patterns, `frappe.throw`, etc. Never bypass the ORM with raw SQL when an ORM equivalent exists.
- **Reuse Frappe HR and ERPNext doctypes** — before creating any custom field or doctype, check whether Frappe HR or ERPNext already provides it. Examples: `Leave Application`, `Expense Claim`, `Expense Claim Detail`, `Leave Allocation`, `Salary Slip`, `Expense Claim Type`, `Leave Type`, `Employee`, `Shift Type`, `Attendance`. Use these; do not invent parallel structures.
- Organisation-level config belongs in Frappe Global Defaults or HR Settings — not hardcoded logic.
- Before proposing any change, ask: does Frappe HR or ERPNext already handle this? What is the cross-module impact?
- Think from three personas: **CXO** (sees all companies), **HR Manager** (single/multi company), **Employee** (own company only).
- No backwards-compatibility shims, no feature flags, no abstractions beyond what the task requires.

---

## 5. Demo scripts — git isolation

- All demo/seed scripts live in the `demo/` folder, which has a `merge=ours` `.gitattributes` driver.
- The `demo/` folder must never land in `main` during a merge. If a new demo script is added on `dev`, add a matching empty stub to `main` in the same session.
- Register the merge driver locally before merging: `git config merge.ours.driver true`.

---

## 6. Write in simple language

Use plain, everyday English. Short sentences. This applies to every reply, every
explanation, and every commit message.

**Do:**

- Say what happened, then what it means, then what to do next.
- Use short sentences. One idea per sentence.
- Explain a technical word the first time it appears, in a few plain words.
  Example: "a ReferenceError — the code asked for something that does not exist".
- Lead with the answer. Put the detail after it.
- Use a small table or a short list when comparing things.
- Say "I do not know" or "I could not check that" when it is true.

**Do not:**

- Do not use jargon when a normal word works. Say "stopped working", not
  "regressed". Say "runs by itself", not "idempotent".
- Do not use long words to sound careful. Say "use", not "utilise".
- Do not write a wall of text. Break it up.
- Do not hide bad news in the middle of a paragraph. Put it first, in bold.
- Do not explain how clever the fix was. Explain what it does.

**A good test before sending:** could a smart person who does not work on this
codebase follow it? If not, rewrite it.

If something really is complex, say so in one plain sentence, then break it into
steps. Complexity is not a reason for complicated language.
