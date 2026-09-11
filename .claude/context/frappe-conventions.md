# How we build on Frappe here

Conventions, not a tutorial. **`CLAUDE.md` §4 in this repo is the authority for the code
approach; this file expands it.** Where they disagree, `CLAUDE.md` wins.

The framework's own docs and — more importantly — the source in the app folders are the
authority on APIs. **Where this file and the installed source disagree, the source wins
and this file gets corrected.**

---

## Rule zero: verify against the installed source

Frappe's APIs change between versions. No agent may call a function, use a hook, or
describe a field it has not seen in the code.

    ls -d */                                        # which apps are here
    grep -rn "def <name>" hrms/ alvoraa_goals/      # does this API exist?
    find . -path "*doctype*" -name "*.json"         # what DocTypes exist

If it is not in the source, it does not exist. Say so and find the real one.

**The apps in this repo are `alvoraa_goals`, `alvoraa_portal`, `alvox_compensation` and
`hrms`,** alongside `frappe` and `erpnext` in the bench.

> ⚠ `CLAUDE.md` §2 names `grace_compensation` in its cross-module list. **No such folder
> exists — the app is `alvox_compensation`.** Leftover from the rebrand. Agents should
> read the intent (the compensation app is in scope) and use the real name. Worth fixing
> in `CLAUDE.md` so nobody greps for a folder that isn't there.

---

## Frappe-first — use the framework, do not work around it

- **Use the ORM.** `frappe.get_doc`, `doc.insert`, `doc.submit`, `frappe.get_all`,
  `frappe.whitelist`, child-table patterns, `frappe.throw`. **Never bypass the ORM with
  raw SQL when an ORM equivalent exists.** Where raw SQL is genuinely the only option,
  it is parameterised — string-built SQL is a defect, not a style choice.
- **Reuse Frappe HR and ERPNext doctypes.** Before creating any custom field or doctype,
  check whether one already exists. Start with: `Employee`, `Leave Application`,
  `Leave Allocation`, `Leave Type`, `Attendance`, `Shift Type`, `Salary Slip`,
  `Expense Claim`, `Expense Claim Detail`, `Expense Claim Type`. **Do not invent
  parallel structures.**
- **Organisation-level configuration** belongs in Frappe Global Defaults or HR Settings.
  Not in hardcoded logic.
- Before proposing any change, ask two questions out loud: *does Frappe HR or ERPNext
  already handle this?* and *what is the cross-module impact?*

## Choose the cheapest mechanism

| Need | First choice | Avoid |
|---|---|---|
| Extra data on a standard document | Custom Field / Property Setter, exported as a fixture | Editing the standard DocType |
| Behaviour on validate/save/submit | `doc_events` in `hooks.py` | Editing upstream controllers |
| Replace standard logic wholesale | `override_doctype_class` | Import-time monkey-patching |
| Read-only aggregation | Query Report / Script Report | A new DocType duplicating data |
| Scheduled work | `scheduler_events` | A cron script outside the app |
| Work longer than ~2 seconds | `frappe.enqueue` | Blocking the web request |
| A concept the business names and owns | New DocType | A JSON blob in a Text field |

## No over-engineering — and here that has a specific meaning

- **No backwards-compatibility shims.**
- **No feature flags.**
- **No abstractions beyond what the task requires.** No abstraction until the third real
  use.
- No new dependency without a stated reason and a stated cost.

> ⚠ **One tension to settle, not to fudge.** The non-functional budget asks for a
> per-feature kill switch on AI paths and feature-flagged rollback. `CLAUDE.md` says no
> feature flags. These are arguably different things — a speculative flag kept "for
> flexibility" is the thing being banned; a switch that turns off a live AI feature is a
> safety control. **The founder should decide and write the answer here.** Until then,
> agents propose the kill switch explicitly in the strategy step rather than building
> one quietly.

## Think in three personas, always

Every change is evaluated from all three. State what changes for each:

| Persona | Sees |
|---|---|
| **CXO** | All companies |
| **HR Manager** | Single or multiple companies, per their scope |
| **Employee** | Their own company only, and mostly their own record |

## Server-side truth

Permissions, validation and calculation are enforced on the server. Client-side checks
are a courtesy to the user, never a control. Hiding a button is not a permission.

## Whitelisted endpoints

Every `@frappe.whitelist()` function is a public entry point. Treat it as hostile input:
validate and type-check every argument, check the caller's rights on the **specific**
document, and never let a client-supplied string choose a doctype, field, file path or
code path.

## Queries

Bounded, always. No query inside a loop — batch with a single `in` filter. Index what
you filter and join on. Paginate every list. Never load a full child table to count it.

## Naming and structure

Follow the surrounding code. Read a neighbouring standard implementation and copy its
shape — module layout, controller structure, fixture style, test base class. A change
that looks like it belongs is a change the next person can maintain.

## Migrations

Schema and data changes go through the framework's patch mechanism as this repo already
uses it. Every patch is safe to run twice. Every patch states its rollback, or states
honestly that there isn't one.

## Tests

Use the runner this repo already uses. For Python: `bench run-tests --app <app>` for
every changed module. For JavaScript and HTML: trace every affected UI flow by hand.
Do not introduce a second test framework.

## Fixtures and data

Synthetic and anonymised. Never a copy of production. This is a privacy rule.

## Translations

Every user-facing string is wrapped for translation, in Python and in JavaScript. No
concatenated sentences — they cannot be translated correctly. No hardcoded date, number
or currency formats.

---

## Branch discipline

*From `CLAUDE.md` §1.*

- **Always work on the `dev` branch** unless told otherwise, and **confirm the branch
  before any git operation.**
- On another branch: stash, switch to `dev`, reapply.
- **Never commit to `main` without an explicit instruction.** `main` is for deliberate
  production releases only.
- Committing is part of the deployment pipeline — the change-process checklist runs
  **before** `git commit`, not after.

## The `demo/` folder is deliberately isolated

*From `CLAUDE.md` §5.*

- All demo and seed scripts live in `demo/`, which carries a `merge=ours` driver in
  `demo/.gitattributes`.
- **`demo/` must never land in `main` during a merge.** If a new demo script is added on
  `dev`, add a matching empty stub to `main` in the same session.
- Register the driver locally before merging: `git config merge.ours.driver true`.

---

## 🚫 Production is off limits

*From `CLAUDE.md` §3. This is the hardest rule in the repo. Read it as a wall, not a
guideline.*

- **Never modify or delete anything inside `/var/www/html/hr-app` on the server.**
- **Never interrupt, change, or take down the production application.**
- Production server details live in `deploy/server.env`, which is git-ignored.
  **Never commit that file, and never print its contents.**
- Deploy commands require explicit approval every time — see
  `.claude/context/change-process.md`.

If a task appears to require touching production, **stop and say so.** There is no
version of "it was a small change" that makes this acceptable.

---

## The repo already knows things — read before asking

These live at the repo root and are more current than any agent's assumptions. Read the
relevant one before starting, and **tell the user when your work contradicts one**:

| Document | Use it for |
|---|---|
| `ARCHITECTURE.md` | How the system is actually put together |
| `KNOWN_ISSUES.md` | **Check before reporting a bug** — it may already be known |
| `DEPLOYMENT_RUNBOOK.md` | Anything touching deploy |
| `Design_Theme_Guide.md` | UI work — the design system already exists |
| `OBJECTIVES_AND_KPI_SRS.md` | The requirements authority for goals and KPIs |
| `MODULE_ACCESS_STRATEGY.md` | Entitlement and plan gating |
| `KPI_BACKLOG_DECISION_RECORD.md` | Why the KPI backlog is shaped as it is |
| `backlog/` | Current stories — but see the warning in `product-context.md` about the superseded `KPI_AUTOMATION_BACKLOG.md` |
