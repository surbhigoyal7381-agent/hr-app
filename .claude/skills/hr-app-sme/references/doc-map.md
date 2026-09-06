# Documentation map — where to look, and what it is worth

How to find a page on each of the three documentation sites, and how much to
trust it against this codebase.

> **Honest provenance.** `docs.frappe.io` is not reachable from every
> environment (some sandboxes block it). Every URL below was confirmed to exist
> through search results, but the *content* summaries in the other reference
> files were generated from source code, not scraped prose. When a claim
> matters, verify it in `hrms/`, `alvoraa_*/` or the ERPNext source — that is
> the version you actually run.

---

## 1. Frappe HR — `docs.frappe.io/hr`

**Slug rule:** the doctype name, lower-cased, spaces to hyphens. So any doctype
in `frappe-hr.md` §3 gives you its page directly.

`leave-type` · `leave-allocation` · `leave-application` · `leave-encashment` ·
`leave-policy-assignment` · `compensatory-leave-request` · `attendance` ·
`shift-type` · `employee` · `employee-onboarding` · `employee-promotion` ·
`employee-transfer` · `employee-separation` · `exit-interview` ·
`expense-claim` · `travel-request` · `employee-tax-exemption-declaration` ·
`salary-component` · `salary-structure` · `salary-structure-assignment` ·
`salary-structure-assignment-tool` · `income-tax-slab` · `appraisal` ·
`appraisal-cycle` · `appraisal-template` · `goal` · `job-requisition` ·
`interview-feedback` · `interview-type` · `employee-performance-feedback` ·
`employee-attendance-tool` · `hr-settings`

**Guide pages** (same rule, applied to the title):

`introduction` · `human-resource-setup` · `payroll-setup` ·
`how-to-process-payroll-in-frappehr` · `income-tax-calculation-in-frappehr` ·
`income-tax-calculation-in-erpnext` ·
`how-to-encash-unused-leaves-using-salary-slips` ·
`leave-allocation-after-compensatory-leave-request` · `auto-attendance` ·
`using-auto-attendance` · `roster` ·
`integrating-frappe-hr-with-biometric-attendance-devices` ·
`interview-management` · `appraisal-overview-report` ·
`human-resources-reports` · `mobile-app-installation`

### 🔎 Some HR features are only documented in the old ERPNext manual

There is no `docs.frappe.io/hr` page for several live features. Their only
documentation is the versioned ERPNext manual:

| Feature | Where the docs actually are |
|---|---|
| Employee Advance | `/erpnext/v14/user/manual/en/human-resources/employee-advance` |
| Employee Benefit Claim | `/erpnext/v12/user/manual/en/human-resources/employee-benefit-claim` |
| Employee Other Income | `/erpnext/v12/user/manual/en/human-resources/employee-other-income` |
| Employee Tax Exemption Proof Submission | `/erpnext/v12/user/manual/en/human-resources/employee-tax-exemption-proof-submission` |
| Gratuity | `/erpnext/v12/user/manual/en/human-resources/gratuity` |
| Employee Checkin | `/erpnext/v14/user/manual/en/human-resources/employee_checkin` |
| Shift Management | `/erpnext/v12/user/manual/en/human-resources/shift-management` |

Prefix all of these with `https://docs.frappe.io`.

**Treat v12/v13/v14 manual pages as historical.** They predate the split of HR
out of ERPNext, so field names, module paths and defaults have moved. Use them
for *intent*, then confirm behaviour in `hrms/`.

### Full and Final Statement

Appears in the navigation but the search index returns no content page. If you
need its behaviour, read
`hrms/hrms/hr/doctype/full_and_final_statement/` — it is the only reliable
source.

---

## 2. ERPNext — `docs.frappe.io/erpnext`

Three URL shapes coexist:

| Shape | Example | Status |
|---|---|---|
| `/erpnext/<slug>` | `/erpnext/introduction`, `/erpnext/selling`, `/erpnext/accounting-introduction`, `/erpnext/accounting-of-inventory-stock` | Current |
| `/erpnext/<module>/<page>` | `/erpnext/accounting/introduction` | Current |
| `/erpnext/user/manual/en/<page>` | `/erpnext/user/manual/en/CRM`, `/erpnext/user/manual/en/manufacturing-reports` | Current, unversioned manual |
| `/erpnext/v12\|v13\|v14/user/manual/en/<module>/<page>` | `/erpnext/v13/user/manual/en/manufacturing/production-plan` | Historical |

Because the shapes are inconsistent, **search rather than guess** an ERPNext
URL. For a doctype's actual behaviour the source at the pinned version beats
all four.

Modules to search within: Accounts · CRM · Buying · Projects · Selling · Setup ·
Manufacturing · Stock · Support · Utilities · Assets · Portal · Maintenance ·
Regional · ERPNext Integrations · Quality Management · Communication ·
Telephony · Bulk Transaction · Subcontracting · EDI.

---

## 3. India Compliance — `docs.indiacompliance.app`

The only one of the three with a complete, stable, open-source page list. All
27 documentation pages are distilled in `india-compliance.md`; the blog
material is in its §10.

Prefix: `https://docs.indiacompliance.app/docs/`

| Section | Pages |
|---|---|
| Getting Started | `getting-started/introduction` · `getting-started/installation` · `getting-started/india_compliance_account` |
| Configuration | `configuration/gst_setup` · `configuration/sales_transaction` · `configuration/purchase_transaction` · `configuration/tds_configuration` · `configuration/other_transaction` |
| e-Waybill & e-Invoice | `ewaybill-and-einvoice/gst_settings` · `ewaybill-and-einvoice/generating_e_waybill` · `ewaybill-and-einvoice/generating_e_invoice` · `ewaybill-and-einvoice/faqs` |
| GST Reports | `gst-reports/gstr1` · `gst-reports/gstr3b` · `gst-reports/gst_ims` · `gst-reports/miscellaneous_reports` |
| Purchase Reconciliation | `purchase-reconciliation/purchase_reconciliation_setup` · `purchase-reconciliation/reconciling_purchase` · `purchase-reconciliation/auto_reconcile` |
| Miscellaneous | `miscellaneous/audit_trail` · `miscellaneous/gstin_verification` · `miscellaneous/transaction_validations` · `miscellaneous/lower_deduction_certificate` |
| Developer Guide | `developer-guide/multi-site-setup` · `developer-guide/migrating-from-v13` · `developer-guide/migration-guide` · `developer-guide/sandbox` · `developer-guide/e_invoice_qr` |

Blog (prefix `https://docs.indiacompliance.app/blog/posts/`):
`gst-accounting-after-gstr3b` · `gst-refund-accounting` ·
`update-taxes-for-items` · `post3` (GST treatments) · `post4` (e-commerce in
GSTR-1) · `post5` (subcontracting workflow) · `post1` (v13 migration) ·
`post2` (India Compliance account).

**To refresh:** the site is built from
`github.com/resilient-tech/india-compliance-docs` (branch `main`, content under
`pages/`). Clone it and re-read — that is how this reference was produced.

---

## 4. Order of trust

1. **The source in this repo** — `hrms/`, `alvoraa_goals/`, `alvoraa_portal/`.
   This is a fork; it is what runs.
2. **Upstream app source** at the pinned version — `frappe/hrms`,
   `frappe/erpnext`, `resilient-tech/india-compliance`.
3. **Current documentation pages.**
4. **Versioned v12–v14 manual pages** — intent only, not behaviour.

Never assert a field name, doctype name or API signature from documentation
alone. Grep for it first.
