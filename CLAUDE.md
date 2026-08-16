# Claude Code Instructions — HR App (Alvoraa)

These instructions are mandatory in every session. They override default behavior.

---

## 1. Branch discipline

- Always work on the **`dev` branch** unless explicitly told otherwise.
- Before any git operation, confirm the working branch is `dev`.
- If on another branch, stash changes, switch to `dev`, and reapply — do not commit to `main` without explicit instruction.
- `main` is reserved for deliberate production releases only.

---

## 2. Mandatory pre-commit / pre-deploy checklist

Every code change must go through all four steps **in order** before anything reaches the server:

1. **Run tests** — `bench run-tests --app <app>` for any changed Python module; manually trace all affected UI flows for JS/HTML changes.
2. **Code review as senior technical architect** — correctness, edge cases, regressions, security, consistency across all touched files.
3. **Impact analysis** — identify every function, hook, API endpoint, and UI path affected by the change, not just the directly edited lines. Grep for all callers of changed functions.
4. **Present findings and wait for explicit user approval** — summarise test results, review findings, and impact before deploying. Do not proceed until the user says "go ahead" or equivalent.

**Fixing a bug and deploying it are two separate steps. "Fix this" is not deploy permission.**

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
- Production server: `root@169.58.108.3`
- Live domains: `alvoraa.co`, `dev.alvoraa.co`, `minda.alvoraa.co`
- Do not cite `alvox.in` as a live URL — it was renamed; current domain is `alvoraa.co`.

---

## 4. Code approach — no over-engineering

- Exhaust existing Frappe mechanisms before writing new code.
- Organisation-level config belongs in Frappe Global Defaults or HR Settings — not hardcoded logic.
- Before proposing any change, ask: does Frappe already handle this? What is the cross-module impact?
- Think from three personas: **CXO** (sees all companies), **HR Manager** (single/multi company), **Employee** (own company only).
- No backwards-compatibility shims, no feature flags, no abstractions beyond what the task requires.

---

## 5. Demo scripts — git isolation

- All demo/seed scripts live in the `demo/` folder, which has a `merge=ours` `.gitattributes` driver.
- The `demo/` folder must never land in `main` during a merge. If a new demo script is added on `dev`, add a matching empty stub to `main` in the same session.
- Register the merge driver locally before merging: `git config merge.ours.driver true`.
