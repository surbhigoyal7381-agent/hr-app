# hr-app SME agent — how to use it

A standing subject matter expert for **hr-app (Alvoraa)** that knows Frappe HR,
ERPNext and the India Compliance app, and knows how this fork differs from all
three. It helps the product and development teams write feature specifications
and implementation strategies.

## Two ways to call it

**As a slash command** — in Claude Code, type:

```
/hr-app-sme spec out carry-forward leave expiry for multi-company tenants
```

The skill loads into the current conversation, so you can keep talking to it.

**As a subagent** — ask Claude to use the `hr-app-sme` agent. It runs in its own
context, reads the repo, and reports back. Better for a long research question
where you only want the conclusion.

## What it produces

| Ask | You get |
|---|---|
| "Spec this out" | A feature specification: what, why, reuse-vs-build, scope, per-persona behaviour, data model, edge cases, permissions, compliance, success measures, open questions |
| "How should we build it" | An implementation strategy: impact analysis (functional + all seven NFR dimensions), design, risks, files to change, test plan, rollout |
| "Does Frappe already do this?" | A verdict — reuse / extend / build new — checked against Frappe HR, then ERPNext, then India Compliance, then this repo |
| A domain question | A plain-English answer grounded in the vendored source, not from memory |

## What it will not do

It proposes; it does not implement. It stops at the approval gate defined in
`CLAUDE.md` §2 — no code, no commits, no `bench` or `docker` commands until you
say go.

## Files

```
.claude/agents/hr-app-sme.md              the subagent definition
.claude/skills/hr-app-sme/SKILL.md        the slash command
.claude/skills/hr-app-sme/references/
    frappe-hr.md          Frappe HR: 211 doctypes, leave ledger, payroll chain,
                          auto attendance, HR Settings, India payroll statutory
    erpnext.md            ERPNext modules, the HR/ERPNext ownership boundary,
                          accounting integration points
    india-compliance.md   Every page of docs.indiacompliance.app, distilled:
                          GST setup, e-Invoice, e-Waybill, GSTR-1/3B, IMS,
                          purchase reconciliation, TDS, audit trail
    hr-app-product.md     This product: apps, personas, runtime, working rules
    spec-templates.md     The two output formats
```

## Keeping it current

The references are grounded in sources, not memory:

- **India Compliance** — distilled from all 27 pages of
  `resilient-tech/india-compliance-docs`, plus the app's doctype list.
- **Frappe HR** — generated from the `hrms/` source vendored in this repo, and
  diffed against upstream `frappe/hrms`.
- **ERPNext** — generated from the ERPNext source at the pinned version.

When the fork changes materially — new doctypes, a module reorganisation, an
upstream merge — regenerate the inventories in `frappe-hr.md` §3 and re-check
the duplicate-doctype list in `erpnext.md` §2.
