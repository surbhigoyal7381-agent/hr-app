# India statutory payroll — strategy

**Status:** evaluated 2026-09-08. Not started. Needs one product decision (§2) before any code.
**Scope:** Indian statutory payroll compliance — PF, ESI, Professional Tax, LWF, TDS, Form 16, Form 24Q.
**Trigger:** the question "is India payroll installed in our repos?" — it is not, and what we do have is
much smaller than it looks.

---

## 1. The one-line summary

> **We ship the *names* of Indian salary components. We do not ship the *calculations*.**
>
> Frappe publishes an app that does — `frappe/india-payroll` — but **two of its three integration
> points do not exist in our hrms fork**, so installing it today would look successful and silently
> compute nothing.

---

## 2. The decision that comes first

**Is Indian statutory compliance something Alvoraa sells, or something customers handle outside the
system?**

Everything below assumes the answer is "we sell it". If the answer is "customers use their CA and a
spreadsheet", then this document is a note in the backlog and nothing else. Nobody should start the
work in §6 until this is settled, because it is a real piece of engineering in the most sensitive
file we own.

The commercial case, stated neutrally: Alvoraa targets Indian companies, and a payroll product that
cannot produce a Form 16 or a PF ECR file is not a payroll product to a buyer in India. Against
that, statutory rules change every budget, and owning them is a permanent maintenance commitment.
Adopting Frappe's app moves that commitment to Frappe.

---

## 3. What we actually have today

`hrms/hrms/regional/india/` — present on **both `dev` and `main`**. It is not an app; it is a
regional module inside our hrms fork, and it activates on **company country = India**.

| Piece | What it really does |
|---|---|
| `data/salary_components.json` | 6 components: Professional Tax, Provident Fund, HRA, Basic, Arrear, Leave Encashment. **Names and types only.** No slab or rate logic. |
| `utils.py` | HRA exemption (annual and per-period), marginal relief, `set_esi_applicable` |
| `setup.py` | Creates those components and custom fields for an India company |

Wired through `hooks.py` as three `regional_overrides` on `hrms.hr.utils`, plus one `before_insert`.

**So a customer gets:** correct HRA exemption, correct marginal relief, an ESI-applicable flag, and
component names they fill in by hand.

**A customer does not get:** any statutory computation, return or form.

One branch difference worth noting: `dev` carries
`hrms/hrms/patches/v16_0/add_esi_fields_for_india.py`, which `main` does not. That is part of a
group of four v16 patches `main` is simply behind on — not an India-specific gap.

---

## 4. What `frappe/india-payroll` is

A separate Frappe app (`india_payroll`) installed on top of Frappe HR.

| Capability | Ours | `india_payroll` |
|---|---|---|
| EPF — wage ceiling, **ECR file export** | component name only | full |
| ESI — contribution deduction, thresholds | applicability flag only | full |
| **Professional Tax — state-wise slabs** | component name only | full |
| **Labour Welfare Fund** | ✗ | full |
| Income tax / TDS — both regimes, surcharge | marginal relief only | full |
| **Form 24Q e-filing** | ✗ | full |
| **Form 16 generation** | ✗ | full |
| Tax regime selector for employees | ✗ | full |
| Statutory registers (PF, ESIC, LWF, bank mandate) | ✗ | 4 reports |
| HRA exemption | ✓ | ✓ |

### Health check — measured, not assumed

| | |
|---|---|
| Version | `16.0.1` — matches our v16 bench |
| Python | `requires-python >= 3.14`; we run 3.14.2 |
| `required_apps` | `frappe/hrms` — satisfied |
| Branches | one: `develop` |
| Activity | 188 commits, latest **2026-09-08** |
| Size | 77 Python files, 10 test files, 4 reports |
| **Uninstall** | `uninstall.py` present — matters for plan downgrades |
| New doctypes | 6 (Form 16, TDS Challan, TDS Return + 3 child tables) |

**No doctype clash.** None of its 6 doctypes collide with Frappe, ERPNext, or our apps. Verified
against the full upstream inventory; `check_app_integrity.py` would catch it if that ever changed.

---

## 5. The blocker

`india_payroll` integrates through three `regional_overrides`. Our fork has one of them.

| Hook it overrides | In our fork? | Consequence if missing |
|---|---|---|
| `income_tax_slab.apply_surcharge_with_marginal_relief` | **present and called** | — |
| `salary_slip.apply_regional_deductions` | **MISSING** | **PF, ESI, PT and LWF are never deducted on a salary slip** |
| `salary_structure_assignment.apply_regional_ctc_components` | **MISSING** | **Employer PF/ESI contributions never reach CTC** |

Our `salary_slip.py` and `salary_structure_assignment.py` contain **no reference to `regional` at
all**. Our fork is `17.0.0-dev` and has diverged; upstream v16 hrms added these extension points and
we do not have them.

**Why this matters more than a normal missing feature:** the app would install cleanly, its settings
screens would render, its doctypes would appear, and payroll would run — producing salary slips with
no statutory deductions. A silent wrong answer, not an error. That is the same failure shape as the
shadowed-doctype bug of 2026-08-24, and it is the reason this document exists instead of an
`install-app` command.

---

## 6. Options

### Option A — port the two missing hook points, then install *(recommended)*

Bring `apply_regional_deductions` and `apply_regional_ctc_components` into our fork from upstream
hrms v16, then install `india_payroll` unchanged.

- **For:** puts us back on the upstream extension contract, which pays off beyond this app. Frappe
  owns the statutory rules and their yearly churn. The app stays a drop-in, upgradeable dependency.
- **Against:** the work lands in `salary_slip.py`, the most consequential file we own.

### Option B — retire our India module and adopt theirs wholesale

- **For:** cleanest end state. One owner for PF/ESI, no duplicate switches.
- **Against:** a data migration. Existing `pf_applicable` / `esi_applicable` values must move to
  their fieldnames, on live tenants.

### Option C — build the statutory pieces ourselves

**Not recommended.** Form 24Q, Form 16 and state-wise professional tax are a large, permanently
moving regulatory surface. Owning them buys nothing a customer can see and costs us every budget.

**Recommendation: A now, B later.** A is reversible and unblocks the product. B is the tidy-up once
the app has proven itself on a real tenant.

---

## 7. Collisions, and what to do about them

Custom fields on the five doctypes both touch:

| Doctype | Ours | Theirs | Colliding fieldnames |
|---|--:|--:|---|
| Employee | 6 | 9 | **`ifsc_code`, `micr_code`** |
| Salary Structure Assignment | 3 | 14 | none by name |
| Payroll Settings | 0 | 24 | none |
| Company | 5 | 7 | none |
| Income Tax Slab | 1 | 1 | none |

**The two name clashes are minor.** `create_custom_fields` updates rather than duplicates; whoever
installs last wins the label and position. Worth a deliberate decision on which app owns them, not
worth blocking on.

**The semantic overlap is the real one.** Both implement PF/ESI applicability on Salary Structure
Assignment under different names — ours `pf_applicable` / `esi_applicable`, theirs `epf_applicable`
and 13 more. Two switches for one concept means the data splits and neither is authoritative.

**Handling:** under Option A, make ours read-only and hidden once `india_payroll` is installed, and
treat theirs as the source of truth. Under Option B, migrate and delete ours. Do **not** leave both
editable — that is how a tenant ends up with PF deducted twice or not at all.

---

## 8. Fitting it into plans and provisioning

It becomes a feature in `alvoraa_portal/subscription.py`, like `alvoraa_goals`:

1. A new feature id (e.g. `india_statutory`) with `app: "india_payroll"`, so `required_apps()`
   installs it only for tenants that bought it.
2. Provisioning installs the app conditionally, the way `alvoraa_goals` already is.
3. Its module (`India Payroll`) is added to `blocked_module_defs()` for plans without it, so the
   desk hides it — remembering that module blocking **hides, it does not deny**. Roles are the real
   gate.
4. Downgrade **hides and keeps the data**, per the decision recorded in `MODULE_ACCESS_STRATEGY.md`
   §7. Never `bench uninstall-app` on a live tenant — it drops tables.

Its `uninstall.py` exists, which makes a clean removal possible on a **new or test** site. That is
not a licence to run it on a customer's.

---

## 9. Risks

| Risk | Severity | Handling |
|---|---|---|
| Ported hook points behave subtly differently from upstream | **high** | Port verbatim from upstream v16, do not reinterpret. Diff our `salary_slip.py` against upstream first and record what already diverges. |
| Silent no-op if a hook is added but never called | **high** | A test that asserts a PF deduction actually appears on a slip — not that the function exists |
| Duplicate PF/ESI switches confuse payroll | medium | §7 — one owner, the other hidden |
| Statutory rules change | medium | This is the argument *for* adopting the app; Frappe tracks them |
| App is on `develop` only, no stable tag | medium | Pin a commit in provisioning. Do not track a moving branch on customer sites. |
| Our fork diverges further and breaks the contract again | medium | Extend `check_app_integrity.py` to assert the hook points still exist and are called |

---

## 10. How we will know it works

Not "the app installed". On a **fresh site with an Indian company**:

1. A salary slip for an EPF-eligible employee shows a **PF deduction of the right amount**.
2. Employer PF/ESI appears in **CTC** on the salary structure assignment.
3. **Professional Tax** differs correctly between two employees in different states.
4. The **PF register, ESIC register and LWF register** reports produce rows.
5. A **Form 16** generates.
6. `bench migrate` reports **no orphaned doctypes** and integrity checks stay green.

Steps 1 and 2 are the ones that prove the blocker in §5 is genuinely fixed. Everything else can pass
while payroll is silently wrong.

---

## 11. Open decisions

| # | Question | Owner |
|---|---|---|
| 1 | Do we sell Indian statutory compliance at all? (§2) | Surbhi |
| 2 | Option A now, or straight to B? | Surbhi |
| 3 | Which plans include it — Business and above, or Enterprise only? | Surbhi |
| 4 | Who owns `ifsc_code` / `micr_code` on Employee? | engineering, once 1–2 are settled |

Nothing starts until 1 and 2 are answered.
