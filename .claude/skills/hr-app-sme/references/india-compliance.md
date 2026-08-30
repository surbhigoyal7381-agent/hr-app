# India Compliance — subject matter reference

Source of truth: the full documentation at
<https://docs.indiacompliance.app/docs/getting-started/introduction>
(every page of that site is distilled below) and the app source at
`resilient-tech/india-compliance`.

India Compliance is a **separate Frappe app** by Resilient Tech that installs on
ERPNext. It is not part of ERPNext and not part of Frappe HR. From v14 onwards
all India GST features were **removed from ERPNext** and moved here.

Modules: `GST India`, `Income Tax India`, `VAT India`, `Audit Trail`.

Main doctypes (`india_compliance/gst_india/doctype`): Bill of Entry ·
Bill of Entry Item · Company Print Options · e-Invoice Applicable Company ·
e-Invoice Log · e-Waybill Log · GST Account · GST Credential · GST HSN Code ·
GST Invoice Management System · GST Inward Supply · GST Inward Supply Item ·
GST Return Log · GST Settings · GST UOM Map · GSTIN · GSTR-1 · GSTR-3B Report ·
GSTR Action · GSTR Import Log · India Compliance Taxes and Charges · PAN ·
Purchase Reconciliation Tool · State Wise e-Waybill Threshold.

---

## 1. Where this matters for an HR product

Be precise about scope. Two different things get called "India compliance":

| Kind | Owned by | Examples |
|---|---|---|
| **Payroll statutory** | Frappe HR `regional/india` | PF, ESI, Professional Tax, Gratuity, TDS on salary (s.192), HRA exemption, Form 16 inputs |
| **Indirect tax / GST** | India Compliance app | GST on invoices, e-Invoice, e-Waybill, GSTR-1/3B, ITC, TDS on vendor payments (s.194) |

**An HR feature almost always needs the first, not the second.** See
`frappe-hr.md` §7 for the payroll-statutory side.

India Compliance becomes relevant to this product when:

- A **vendor/contractor** is paid rather than an employee — TDS under s.194x
  via Tax Withholding Category, and a Lower Deduction Certificate if the vendor
  has one.
- The **vendor portal / delivery module** (`alvoraa_portal`) produces goods
  movement — e-Waybill applies to Delivery Note, Purchase Receipt, Stock Entry
  and Asset Movement.
- **Audit Trail** is switched on — this changes what the whole site can delete
  (§8) and affects every accounting-adjacent HR document.
- An **Expense Claim** carries GST that the company wants ITC on.

---

## 2. Getting started

**Installation** — `bench get-app https://github.com/resilient-tech/india-compliance.git`
then `bench --site <site> install-app india_compliance`. On Frappe Cloud, select
it at site creation. For Docker, add it to `APPS_JSON` and build a custom image.

**India Compliance Account** — required for any API feature (e-Invoice,
e-Waybill, GSTIN autofill, GST returns). Sign up from the GST India workspace
with email + GSTIN, verify the email. Credits: 1 credit = 1 API request. Free
trial 500 credits / 3 months. Purchases are non-refundable, valid one year, and
buying again extends unused credits. Balance updates roughly every 10 minutes.
The same account works across multiple sites; for a multi-client setup put the
API secret in global config (`bench set-config -g ic_api_secret <secret>`) and
disable the per-site account page.

**Sandbox** — enable `Use API in Sandbox Mode?` in GST Settings; sandbox calls
are not billed. Limits: distance is not auto-populated (pass 1–4000 km), use
`05AAACG2140A1ZL` as the test transporter GSTIN, e-Waybill print/attach and
transporter/vehicle updates are unavailable, public APIs unsupported. The old
`ic_api_sandbox_mode` site config is deprecated.

---

## 3. GST setup

- **HSN codes** — 12,000+ ship pre-installed as `GST HSN Code`.
- **Tax accounts and templates** — default GST accounts, Sales/Purchase tax
  templates and Item Tax Templates are auto-created per company.
- **GST Accounts** are the backbone. Exactly **three rows per company**: Input,
  Output, Reverse Charge. Multiple GST accounts per rate or per state are
  explicitly discouraged — one account per type, with breakup derived from
  transactions. Validations, taxable-value calculation and ITC availability all
  key off these settings.
- **Item master** — HSN, Item Tax Template, and `Is Ineligible for ITC` per item.
- **GST is destination-based**, so every Indian customer and supplier needs a
  GST state, including unregistered ones. GST details resolve from the Address
  first, then the Party.
- **Supplier config** — `Reverse Charge Applicable`, GST Transporter ID,
  Tax Withholding Category (TCS category on customers).
- **Company Print Options** — physical signature toggle, logo, bank details,
  MSME/LLPIN/LUT registration details for the generated print format.

General GST Settings switches worth knowing: HSN-wise tax breakup, reverse
charge in sales, SEZ/overseas transactions, round-off GST values, mandatory
supplier invoice number, HSN validation with minimum digits (4 or 6 by
turnover), reverse charge for unregistered suppliers with an invoice-value
threshold.

---

## 4. Transactions

**Sales** — pick customer + item, verify both GSTINs and HSN, choose
`In State GST` or `Out of State GST` tax template, submit. Print with the
`GST Tax Invoice` format and set the `Invoice Copy` field (Customer / Supplier /
Transporter). Item-level tax breakup shows in the **GST Details** section.

**Purchase** — same flow plus optional supplier invoice number/date. Assets:
create Asset Category → item with `Is Fixed Asset` → normal purchase cycle.

**Reverse charge purchase** — add reverse-charge accounts in GST Settings,
enable `Is Reverse Charge` on the Purchase Invoice, set `Eligibility for ITC` to
"ITC on Reverse Charge", add tax with input heads and deduct the same amount
with reverse-charge heads so net payable is zero. Automate it with a Tax
Category on the supplier plus a Purchase Taxes and Charges template.

**ITC ineligibility** (v14.18.0+) — automatic ITC reversal with GL entries.
Needs a GST Expense Account on Company and `Is Ineligible for ITC` on the item.
Reversal cases: CGST Rules 38/42/43 (via Journal Entry, reported in 4B(1)),
s.17(5) (per item, automatic, 4B(1)), other reasons (Journal Entry, 4B(2)), and
Place-of-Supply restriction (automatic, 4D(2), applied regardless of the item
setting). Accounts hit depend on item type — expense account, stock account
(valuation adjusted), or asset account (value adjusted). With a Bill of Entry,
reversal happens at the Bill of Entry and valuation flows through a Landed Cost
Voucher.

**Advances** — GST is payable on customer advances; the advance receipt is
treated as inclusive of GST and reversed automatically against the Payment Entry
on the date of supply. The **GST Advance Detail** report runs period-wise or
as-on-date, detailed or summary.

**Other** — ITC reversal via Journal Entry with Entry Type "Reversal Of ITC" and
a Reversal Type of "As per rules 42 & 43 of CGST Rules" or "Others".

**TDS** — 28 Tax Withholding Categories are pre-defined for India. Each carries
a rate plus single-transaction and cumulative thresholds per fiscal year, and a
company-wise TDS payable account. Assign the category on the Supplier, tick
`Apply Tax Withholding Amount` on the Purchase Invoice. Report: "TDS payable
monthly".

---

## 5. e-Waybill and e-Invoice

**GSP credentials** — create a GSP user on the e-Waybill portal
(Registration → For GSP → OTP → Add New User → GSP name **Adaequare Info
Private Limited**), then add the same username/password under GST Settings →
Credentials. e-Waybill and e-Invoice share credentials. Personal portal
credentials will not work for API access.

**e-Waybill** is supported on: Sales Invoice, Purchase Invoice, Delivery Note,
Purchase Receipt, Stock Entry, Subcontracting Receipt, Asset Movement.

Settings: enable e-Waybill; enable generation from Delivery Note (intended for
goods movement without an invoice — job work, warehouse transfer), from Purchase
Invoice, and for subcontracting; invoice-value threshold (default ₹50,000, may
vary by state); auto-generate on submission; fetch e-Waybill data after
generation; attach the print after generation.

Operations: generate (Part A / Part B shown separately in the dialog; distance 0
lets the portal suggest it), update transporter, update vehicle info, extend
validity (only from 8 hours before to 8 hours after expiry), print (`e-Waybill`
simplified or `e-Waybill Detailed`), attach, cancel (within validity; cancelling
removes the attachment). History lives in **e-Waybill Log**.

Bulk: either generate an e-Waybill JSON from the list view and upload it on the
portal, or "Enqueue Bulk e-Waybill Generation" from list-view actions.

**e-Invoice** — auto-generated on Sales Invoice submission when applicable;
IRN and QR are written back. Not generated for supplies to unregistered persons
or non-GST supplies. Settings include auto-generate, generate e-Waybill with
e-Invoice, `e-Invoice Applicable From` date, per-company applicability, retry on
gateway timeout, and handling of Nil-rated/Exempted/Non-GST items
(**Do Not Generate** (default) / Generate with Other Charges / Generate with
Taxable Values — the last is not recommended because GSTR-1 auto-populates such
items as Zero-Rated).

**Interaction rules:** if auto e-Invoice is on, auto e-Waybill becomes
mandatory. Generate e-Invoice first, then e-Waybill. To cancel an e-Invoice the
e-Waybill must be cancelled first — the app does both together. An expired
e-Invoice cannot be cancelled; issue a credit or debit note instead.

---

## 6. GST returns and reconciliation

**GSTR-1 Beta** — fetch filed and unfiled data from the portal, compare, export
JSON/Excel, reset, upload, and file with PAN + OTP. Settings: compare with GST
portal, filing frequency (monthly/quarterly), restrict changes to Sales Invoices
after filing, and the role allowed to modify them. Requires portal API access
enabled and credentials for the `Returns` service. The legacy GSTR-1 Report is
deprecated in v16.

**GSTR-3B** — generated per month or quarter from Company + GSTIN + period.
`ITC Claim Period` decides which month ITC is claimed in for Purchase Invoices
and Bills of Entry. Auto-set from the posting period, or the later of posting
period and 2B return period, moved forward to the next unfiled period up to the
s.16(4) deadline; IMS actions override (Rejected/Pending → `Deferred`,
Accepted → the IMS period). Format is `MMYYYY` or `Deferred`; you cannot set a
period whose GSTR-3B is already filed. **Outward RCM liability always follows
posting date; inward RCM ITC follows the ITC Claim Period.**

**Invoice Management System (IMS)** — v15+, live since 14 Oct 2024. Supplier
invoices arrive from GSTR-1/1A/IFF; you Accept (into GSTR-2B), Reject (excluded)
or mark Pending (stays in IMS). No action = deemed accepted. Draft GSTR-2B is
generated on the 14th. Match statuses: Exact Match, Suggested Match, Mismatch,
Manual Match, Missing in PI, Suggested Mark as Pending. You cannot Accept a
"Missing in PI" row. Actions cannot be changed after GSTR-3B is filed for that
month. Inward RCM supplies and items blocked by s.16(4) or PoS rules bypass IMS
and go straight to GSTR-3B.

**Purchase Reconciliation Tool** — downloads GSTR-2A and GSTR-2B (OTP-based
session; enable API access on the GST portal under My Profile → Manage API
Access, keep the session alive 30 days). Creates `GST Inward Supply` per invoice
and `GSTR Import Log` per period. **GSTR-2B is static** (basis for GSTR-3B);
**GSTR-2A is dynamic** and adds live GSTIN status, supplier GSTR-3B filing
status and not-yet-filed uploads — useful for vendor payment decisions. Bulk
actions: Ignore, Pending. Individual: unlink/accept a match, create a missing
purchase, link manually. Reports can be shared with vendors.

**Auto Reconciliation** — enable in GST Settings → Purchase Reconciliation tab;
set number of months, GST categories (usually B2B and CDNR) and the weekday to
run. Authenticate each GSTIN once by OTP, re-authenticating every 30 days.
GSTR-2A costs one API request per category per month — configuration controls
credit burn.

**Other reports** — GST Job Work Stock Movement (with JSON export), GST Balance,
GST Sales Register Beta, GST Purchase Register Beta.

---

## 7. Validations enforced by the app

- Missing fields for e-Invoice/e-Waybill (mode of transport, transporter name or
  ID, address state code, pincode).
- Pincode validated against the state master; falls back to the first three
  digits mapped to state.
- HSN code validity and minimum digit count.
- e-Waybill validity checked before cancel/update; applicability checked before
  the API call (not required for non-GST items).
- Duplicate IRN — the API updates the existing IRN rather than regenerating.
- Correct routing to the right GST account.
- **Document naming**: alphanumeric, may contain `-` or `/`, must not start with
  a special character or zero, **maximum 16 characters**. If your series suffixes
  amendments (`SINV-222-1`), keep the base to 14 characters. Applies to every
  document reported through e-Waybill / e-Invoice / GSTR-1, so set naming
  conventions for Purchase Invoice, Purchase Receipt and Delivery Note too.

---

## 8. Audit Trail — read before enabling

Required by the Companies Act for Indian companies since 1 April 2023 (MCA
notification). Enabled from Accounts Settings or the Setup Wizard, and
**once enabled it cannot be disabled.**

Consequences: deletion of accounting and stock ledger entries on transaction
delete becomes read-only and disabled; document versioning / track changes is
forced on for all accounting and stock transactions and cannot be overridden.
It records user, timestamp, action type and changed values.

Enforced on: Accounts Settings, Dunning, Invoice Discounting, Journal Entry,
Payment Entry, Period Closing Voucher, Process Deferred Accounting, Purchase
Invoice, Sales Invoice, Asset, Asset Capitalization, Asset Repair, Loan Balance
Adjustment, Loan Disbursement, Loan Interest Accrual, Loan Refund, Loan
Repayment, Loan Write Off, Delivery Note, Landed Cost Voucher, Purchase Receipt,
Stock Entry, Stock Reconciliation, Subcontracting Receipt, POS Invoice, Bill of
Entry.

Custom doctypes can be added via the `audit_trail_doctypes` hook in a custom
app's `hooks.py`, followed by `bench migrate`.

---

## 9. Other features

**GSTIN verification / autofill** — enable `Autofill Party Information based on
GSTIN` in GST Settings; Quick Entry for Customer/Supplier/Address then fills
from the GSTIN.

**Lower Deduction Certificate** — a supplier's certificate for a lower or NIL
TDS rate. Create with certificate number, section code, fiscal year, supplier
(PAN auto-fetched), validity dates, rate and limit. The certificate rate then
overrides the Tax Withholding Category rate on Purchase Invoices.

**Migrating from ERPNext v13** — upgrade to v14 first, then install India
Compliance (India features were removed from ERPNext). Watch: GST Settings fully
revamped; one GST account per type per company (merge rate-wise or state-wise
accounts); GST Category and GSTIN now on both Party and Address, with "URP"/"NA"
no longer accepted (leave blank); e-Invoice refactored — `E Invoice Settings`
moved into GST Settings, `E Invoice Request Log` into Integration Request,
acknowledgement fields moved to `e-Invoice Log`; reports `E-Invoice Summary` and
`Eway Bill` deprecated. Custom print formats using the old QR field must be
rewritten.

**Item Tax Template migration** (v14.21.0 / v15.2.0) — `Is Nil Exempt` and
`Is Non-GST` removed from Item; `GST Treatment` introduced on Item Tax
Templates, splitting Nil-Rated from Exempted. Fix via Update HSN Taxes →
Update taxes for Items.

**e-Invoice QR in print formats** — read `signed_qr_code` and `invoice_data`
from `e-Invoice Log` by `doc.irn` and render with `get_qr_code(...)`; for
standard print formats wrap it in a Web Template component and call
`web_block(...)`.
