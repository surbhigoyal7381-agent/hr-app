# ALV-469: the portal names the person's own organisation

Built 26 Nov 2026 on branch `fix/alv469-org-label` (worktree `.claude/worktrees/alv469-org-label`),
off origin/dev e82bb3f0. Local only. Nothing pushed, nothing deployed.

## What a person sees now

The name at the top of the sidebar, in the first-letter badge and in the phone top bar now follows
the person, first match wins:

| Person | Name shown |
|---|---|
| No Employee record | the site's tenant name |
| Employment type Gig Worker or Freelancer | their own name |
| Contract, agency set | the agency |
| Contract, no agency | their own name |
| Anyone else | their Employee's company |

Any error shows the tenant name, so a bad record never breaks the page.
Page titles, the PWA name, sign-in, the field app and `data-tenant-name` still use the tenant name.
The email footer is now only "Powered by AllAboutHR".

## Files

- `org_label.py` (new): `org_label(user)`, the two fields, the two Employment Types. The agency is read through the one constant `AGENCY_FIELD`.
- `www/hrms_employee.py`, `www/hrms_employee_next.py`: set `brand_label`.
- `templates/includes/ess/frame.html` (badge, sidebar name, phone bar), `.../next/frame.html` (badge, name). `public/css/ess/frame.css`: sidebar name is one line with an ellipsis; each name has a `title` tooltip. The phone bar and the next frame already had the ellipsis.
- `hooks.py`: `org_label.after_migrate` in both `after_migrate` and `after_install`.
- `patches/v1_0/alv469_org_fields_from_dtc.py`, `alv469_email_footer_no_tenant_name.py`, both in `patches.txt`.
- `email_brand.py`: `_footer_text()` is now just the Powered by line.
- `tests/test_org_label_469.py` (new, 20 tests); `test_email_brand_174.py` (one test renamed and tightened).

## Decisions and why

- **Fields are made once, never updated.** `employment_agency` and `employee_category` (Select, HR only) are created only if missing. `create_custom_fields` was rejected: it re-applies the choices on every migrate and would undo what HR edits in Customize Form. At creation the choices are copied from `dtc_agency` / `dtc_employee_category` where those exist; elsewhere they start empty.
- **HR only (level 2)** comes from the existing `lock_new_custom_field` hook the moment the field is inserted. No change to `employee_field_rights.py` was needed. A test proves an Employee cannot write either field.
- **Employment Types are made in `after_migrate`, not a patch**, because a patch never runs on a new site. Side effect: if HR deletes "Gig Worker" it comes back on the next migrate.
- **The copy patch** runs the field creation first (patches run before the after_migrate hook), copies each old value into the new field only where the new one is empty, then hides the old field with a Property Setter. Old fields and data stay. It prints rows copied per field. Safe to run twice.
- **The email patch** reuses the earlier brand patch. `email_brand` rewrites a footer whose last line is ours and leaves any other footer alone.
- Grace's agency "GI Staffing" is NOT in code. After release HR adds it in Customize Form on the Grace site: Employee > Employment Agency > Options. DTC's choices arrive by the copy.

## Pay on DTC (read before using the new types)

On DTC, `employment_type` is the pay category field (the rule set's `category_field`). A type with no
row in the rule set takes the defaults and **earns marks and leave credit**. Surbhi chose option A
(26 Nov): Gig Worker and Freelancer earn neither. No pay code changed; it is two data rows, see below.

## After-release steps (each on Surbhi's word)

1. Release to the site. `bench migrate` runs `alv469_org_fields_from_dtc` and `alv469_email_footer_no_tenant_name` once, then `after_migrate` makes any missing field and the two Employment Types.
2. **On dtc.alvoraa.co, and any site that copies DTC's rule set (e.g. ppj.dev):** Desk > Alvoraa Payroll Rule Set > Categories. Re-read the live "Contract" row first, then add two rows, "Gig Worker" and "Freelancer", copying it. From the DTC export (`hrlocal-data/dtc-ops/dtc_ruleset.json`) the Contract row is: grace_minutes 15, earns_marks 0, earns_leave_credits 0, doubles_deduction 0, late_quarter_after_minutes 0, break_allowance_minutes 0.
3. Until step 2 is done, nobody on DTC may be given Gig Worker or Freelancer.
4. On the Grace site: add the option "GI Staffing" to Employment Agency in Customize Form.
5. Check the printed counts from step 1 look right (rows copied per field).

## Risks and gaps

- Not checked: DTC's real `dtc_agency` / `dtc_employee_category` field types (the code handles Select, and for anything else uses the values people already hold).
- The footer rule treats any footer ending with the Powered by line as ours, as before.
- Not looked at in a browser: the 360 px ellipsis (CSS read only; the phone bar already had it).
