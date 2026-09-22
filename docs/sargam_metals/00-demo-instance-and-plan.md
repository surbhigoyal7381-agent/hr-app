# 00 — Demo instance and plan: Sargam Metals

Written 2026-09-22, in the same session as the Sargam Metals proposal doc
(shared with the user as a Claude Docs artifact). This file says how the demo
tenant is created and what it needs, the same way `docs/pp_jewellers/00-demo-instance-and-plan.md`
does for that use case — read that file first if anything here is unclear, it
carries lessons this one reuses.

**This file, and everything under `demo/sargam_metals/`, was written from a
Claude Code session with no server, docker or bench access — the same
starting condition `demo/pp_jewellers/provision_ppj.sh` documents for its own
first run. Nothing here has been executed against any site.** It is ready to
run, not run.

## 0. Open question this file cannot resolve on its own

The user named `demo.alvoraa.co` as the demo target, twice, in the proposal
review. PP Jewellers' precedent is different: a **dedicated subdomain**,
`ppj.dev.alvoraa.co`, created per prospective client. Two different things
could be meant by `demo.alvoraa.co`:

1. A **general-purpose, reusable demo tenant** that already exists and gets
   reseeded per prospect (Sargam's data would need to be reset before the
   next company is demoed on it, and vice versa) — or
2. **Shorthand** for "a demo tenant on the Alvoraa instance," with the actual
   site meant to be `sargam.dev.alvoraa.co`, dedicated to Sargam like `ppj.`
   was to PP Jewellers.

The scripts below default to option 2 (`sargam.dev.alvoraa.co`), because a
shared, reused demo tenant risks one prospect's data bleeding into another's
demo — the exact class of mistake `CLAUDE.md` §1 warns about with parallel
sessions. **Confirm which one is meant before running `provision_sargam.sh`**;
the site name is one flag (`--site`), not a rewrite.

## 1. What this first pass covers, and what it deliberately leaves out

A thin, working slice — Alvoraa's own standard, not a partial build of
everything in the proposal:

| In this pass | Not in this pass yet |
| --- | --- |
| Two Companies: Sargam Metals India, Cuproban Systems Singapore | Multi-company consolidated reporting |
| Item master: raw ingots (aluminium, zinc, magnesium) and a representative anode + ICCP item, standard vs. custom split by Item Group | The full product catalogue |
| Reorder levels on the raw ingots | The automatic-reminder rules from proposal §6 (Notification/Assignment Rule doctypes — configuration work, not seed data, do once the tenant exists) |
| One BOM, one Purchase → Production → Quality → Export-Sales loop | Tender tracking (Opportunity + tender fields) and CRM lead capture — **blocked on a real decision, see §3** |
| Suppliers (ingot suppliers) and Customers (one domestic, one export) | Full supplier/customer list |

This matches the proposal's own Phase 0–1 scope (§7 of the proposal doc),
plus the ingot reorder levels from §6, since those are cheap to add alongside
the item master and make the "minimum stock" story demoable.

## 2. How the tenant gets created

Same mechanism as PP Jewellers — nobody runs `bench new-site` by hand; the
control plane's `alvoraa_portal.tenant_api.create_tenant` does it. See
`demo/sargam_metals/provision_sargam.sh`, which mirrors
`demo/pp_jewellers/provision_ppj.sh` line for line except for the tenant
details and the module list below.

## 3. Which modules this tenant needs — and the one thing it can't have yet

Per `alvoraa_portal/alvoraa_portal/subscription.py`: Alvoraa HR features are
**not** needed here (the 2026-09-22 decision was that Sargam doesn't need
Alvoraa HR). ERPNext modules are opt-in per tenant and only available on the
**Custom** plan — ticking any one of them is what makes a tenant "custom"
automatically, there is no separate ERPNext-only flow.

| Feature key | Covers | Needed for this pass |
| --- | --- | --- |
| `erp_stock` | Inventory, warehouses, stock movements, reorder levels | Yes |
| `erp_buying` | Suppliers, purchase orders, receipts | Yes |
| `erp_manufacturing` | BOMs, work orders, production planning | Yes |
| `erp_quality_management` | Inspections, non-conformance, procedures | Yes |
| `erp_selling` | Customers, quotations, sales orders | Yes |
| `erp_accounts` | Ledgers, invoices, payments, multi-currency | Yes |
| `erp_crm` | ERPNext's *built-in* Lead/Opportunity module | **Not used** — see below |
| Required Alvoraa HR features (`portal`, `leaves`, `attendance`, `expenses`, `hr_setup`) | Cannot be switched off on any plan | Present regardless, unused in the demo |

**`erp_crm` is deliberately left off.** `subscription.py`'s `ERPNEXT_SELLABLE`
list includes a `CRM` module (`erp_crm`) — but that is ERPNext's older,
Desk-based Lead/Opportunity module. What the proposal's §5 actually describes
— and what the 2026-09-22 comment-thread decision asked for — is the
**separate Frappe CRM app** (`frappe/crm`, the modern UI, the one with the
AI-agent email features), installed as a product feature inside Alvoraa HR
itself. That app is not in this bench's dependency chain (`hrms`'s
`apps.json` lists `erpnext`, `payments`, `hrms` — not `crm`), so adding it is
a real "new Frappe app" decision, not a tenant feature-tick. It needs the pass
this team already has for exactly that situation:
`.claude/context/new-frappe-app-checklist.md`. **That checklist has not been
run yet.** Until it has, this demo tenant shows the ERPNext operational loop
only — no lead capture, no tender tracking — and the proposal doc should say
so plainly if it's presented before that work is done.

## 4. Verification, once this actually runs somewhere

Same discipline as `demo/README.md` requires for every seed here: the shape
seeded must match the shape the app reads, checked on the real screen, not
assumed from the doctype name. Concretely, before this is shown to Sargam:

- `bench --site <site> list-apps` shows `erpnext` (already does, it's a base
  dependency) and the tenant's Desk sidebar shows Stock, Buying, Manufacturing,
  Quality, Selling, Accounts — not CRM.
- Open the seeded BOM, Work Order, Quality Inspection and Sales Invoice on
  screen — not just query them from `bench console` — the same "open the
  screen that reads it" step `demo/README.md` had to learn the hard way.
- Confirm the export Sales Invoice actually shows in Cuproban Systems
  Singapore's currency, not just that the field was set.
