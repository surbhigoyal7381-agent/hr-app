# Which endpoints check who is asking, and which do not

**Written 9 September 2026. For review — nothing here has been changed.**

## What this document is

Every function marked `@frappe.whitelist()` can be called over the internet by
anybody with a login on that tenant. Not just from our pages — from a browser
console, a script, anything.

I checked all of them and read every one that looked unguarded. This is the
result, in plain language, with what I would do about each.

| | Endpoints | Establish who is asking | Do not |
|---|---|---|---|
| **Our code** | 183 | 133 | **50** |
| Vendored Frappe HR fork | 224 | 84 | 140 |

The 140 in the Frappe HR fork are upstream code. Worth knowing about; not ours
to fix.

## First, the thing that caused the question

`frappe.get_all()` **does not check permissions**. `frappe.get_list()` **does**.

That is Frappe's own design, not a decision anybody here made. From Frappe's
source:

```python
def get_all(doctype, *args, **kwargs):
    """List database query via `frappe.model.db_query`. Will **not** check for permissions."""
```

Two functions, near-identical names, opposite behaviour. Frappe and ERPNext use
`get_all` heavily themselves.

**And `ignore_permissions=True` is not automatically wrong.** It is fine — often
better — when the code does its own explicit scoping instead. This is good code:

```python
mgr = _get_employee()                            # who is asking
team = frappe.get_all("Employee",
    filters={"reports_to": mgr.name},            # the scope, written down
    ignore_permissions=True)
```

The rule is visible, it can be read, and it can be tested. Relying on Frappe's
User Permissions instead would hide the same rule in a settings table where
nobody reviewing the code would see it.

**The real problem is different.** It is an endpoint that takes an **ID from the
caller** and returns or changes that record without checking the caller has any
right to it. Change the ID in the request, get somebody else's data. That is the
pattern to hunt for, and it is what most of the 50 below are.

## How the 50 break down

| Group | Count | What it means | Action |
|---|---|---|---|
| **A. Already safe** | 15 | The check is real, just one layer down | Nothing — but see note |
| **B. Public by nature** | 9 | No personal data. Everyone legitimately needs it | Nothing |
| **C. Leaks internal state** | 4 | Tells an ordinary employee about the system | Restrict to admins |
| **D. Change the ID, get the data** | 22 | Takes an ID, no ownership check | **Fix these** |

---

## Group A — already safe (15)

My first pass flagged these because the check is not in the function itself. It
is in the helper or the document method the function calls. That layered style
is fine, and arguably better: the rule sits next to the data it protects, so it
also applies to any other caller.

**Vendor portal API** — `alvoraa_portal/api/vendor_portal_api.py`

`get_vendor_orders` · `get_order_detail` · `get_delivery_tracking` ·
`get_vendor_dashboard` · `get_vendor_notifications`

Every one calls `_get_vendor_id()` — which resolves the *logged-in user's* own
vendor — and the ones that take an order id also call
`_assert_vendor_owns_order(order_id, vendor_id)`. This is exactly the right
shape. It is the model the rest of the vendor code should copy.

**Goals approvals** — `alvoraa_portal/hr_api.py`

`get_pending_approvals` · `approve_goal_evidence` · `reject_goal_evidence` ·
`approve_kpi_progress` · `reject_kpi_progress`

Three-line wrappers that hand straight over to `alvoraa_goals`. The real
function checks: `approve_evidence()` calls `_assert_can_validate(goal_name)`
before touching anything.

**Policy publishing** — `hr_api.publish_policy`

Looks bare. But `doc.publish()` starts with:

```python
if not can_write(self):
    frappe.throw(_("You cannot publish this policy."), frappe.PermissionError)
```

**One caveat for all fifteen.** The safety depends on a check in another file.
If somebody later "simplifies" `publish()` or `_assert_can_validate()`, the
endpoint silently becomes open and nothing here would show it. A one-line
comment at each endpoint saying *where* its check lives would cost nothing and
would survive the next refactor.

---

## Group B — public by nature (9)

These return no personal data. Every logged-in employee legitimately needs them,
and restricting them would break ordinary use.

| Endpoint | What it returns | Why it is fine |
|---|---|---|
| `auth.get_tenant_config` | Company name, logo, brand colour | The **login page** needs it, before anyone can log in. Guest access is required, not a mistake |
| `hr_api.get_expense_types` | The list of claim types | You need it to file a claim |
| `hr_api.get_shift_types` | Shift names and times | You need it to request a shift change |
| `hr_api.get_switch_target` | Where *you* may switch to | About the caller themselves |
| `hr_api.get_hr_approver` | The fallback HR approver's name | Needed to route a request |
| `goals_api.get_active_cascades` | Company goals available to align to | Published company objectives |
| `goals_api.get_alignment_options` | The same, for a picker | As above |
| `goals_api.get_linkable_objectives` | Objectives you may link a goal to | As above |
| `goals_api.get_appraisal_data` | Appraisal cycle settings | Configuration, not results |

**One mild note.** `get_hr_approver` gives out an HR person's email address to
anybody who asks. Harmless inside a company; worth remembering if the portal is
ever opened wider.

---

## Group C — leaks internal state (4)

No personal data, but these tell an ordinary employee things about the system
that only an administrator should see. Low harm, easy to fix, and the kind of
detail that helps somebody who is probing.

| Endpoint | What it gives away | Better way |
|---|---|---|
| `health.check_here` | Error counts, whether the scheduler is running, queue state | `frappe.only_for("System Manager")`. It is a support and monitoring tool |
| `module_access.get_restricted_doctypes` | Which features this tenant is blocked from | Same. This is effectively the tenant's licence state |
| `module_access.get_hidden_workspaces` | Which screens are hidden and why | Same |
| `goal_api.get_cascade_alignment` | A cascade's alignment report, by id | Check the caller can see that cascade |

Each is a one-line fix. Together, about ten minutes.

---

## Group D — change the ID, get the data (22)

**This is the group that matters**, and it is almost entirely the vendor and
delivery portal — the newest module, where the permission work was never done.

Every one follows the same shape:

```python
@frappe.whitelist()
def get_partner_performance_summary(partner_name):     # ← caller supplies the id
    partner = frappe.get_doc("Delivery Partner", partner_name)
    ...                                                # ← no check that it is theirs
```

A driver logged into the portal can change `partner_name` in the request and
read any other driver's earnings, ratings and performance. Nothing stops them.

### The ones that read other people's data (13)

`delivery_order.get_hub_live_summary` · `delivery_order.get_partner_today_orders`
· `delivery_partner.get_partner_performance_summary` ·
`delivery_partner.get_today_orders_for_partner` ·
`delivery_feedback.get_partner_feedback_summary` · `rating.get_driver_ratings` ·
`scorecard.get_hub_performance_report` ·
`vehicle_compliance.get_compliance_dashboard`
— plus five more of the same shape.

What leaks: a named driver's earnings, commission, bonuses, ratings, customer
feedback, today's route, and a hub's live operational picture.

### The ones that change data (5) — the serious ones

| Endpoint | What any logged-in user can do |
|---|---|
| **`delivery_assignment.update_gps_location`** | Write a GPS position into **any** delivery, push it to the live tracking screen, and **cause an email to the vendor** ("arriving in 10 minutes"). Then it saves with `ignore_permissions=True` and commits |
| `delivery_order.mark_proof_of_delivery` | Mark any order delivered, with a photo and signature of their choosing. Sets `ignore_validate` too |
| `delivery_partner.update_partner_stats_from_orders` | Rewrite any driver's performance figures |
| `scorecard.generate_scorecard_for_partner` | Generate or overwrite any driver's monthly scorecard — which drives their commission |
| `vendor_order.assign_delivery` | Assign a delivery to any driver |

`update_gps_location` is the one I would fix first. It writes, it broadcasts, and
it sends mail to an outside party — so it can be used to harass a vendor as well
as to falsify a delivery record.

### How exposed is this really

Honest framing, because the numbers matter:

- **It needs a working login on that tenant.** Nothing here is open to the
  internet.
- **The `vendor` feature is not opt-in.** It is part of the Enterprise plan, so
  it is on by default for those tenants.
- **PP Jewellers has it enabled**, and 403 people have accounts there.

So it is live, not theoretical — but it is a demo tenant, and it needs an
insider.

### The better way

The vendor portal API in Group A already does this correctly. The fix is to copy
that pattern down into the controllers:

```python
@frappe.whitelist()
def get_partner_performance_summary(partner_name):
    _assert_can_see_partner(partner_name)     # the driver themselves, their hub
    ...                                       # manager, or an administrator
```

One helper, used everywhere, that answers: *is this the caller's own record, are
they the manager of that hub, or are they an administrator?* Roughly one day of
work including tests, most of it writing the tests.

**Why a helper and not Frappe's permission system.** These doctypes are new and
have no permission rules configured, so `get_list` would return nothing rather
than the right subset — it would look broken and somebody would "fix" it by
putting `ignore_permissions` back. An explicit helper is visible, testable, and
does not depend on a settings table nobody reads.

---

## The recommendation that outlasts the fixes

Fixing these 22 leaves the same door open for the next module. **Add a check to
CI** that fails the build when a new `@frappe.whitelist()` function has no
guard and is not on a short, deliberate allow-list.

The script that produced this document does most of the work already. There is
a natural home for it: `scripts/check_app_integrity.py`, which CI runs.

Without that, this list grows back. The vendor portal was written after the HR
portal, by which time the pattern in `hr_api.py` was well established — and it
still ended up like this, because nothing enforced it.

---

## Appendix — what I checked and how far to trust it

- Parsed every `.py` in `alvoraa_portal`, `alvoraa_goals` and the `alvoraa_*`
  modules of the `hrms` fork; found every `@frappe.whitelist()` function.
- Flagged any that did not mention establishing the caller or their role.
- **Read all 50 flagged functions**, and followed the ones that delegate into the
  function they call. Groups A to D above are that reading, not the heuristic.
- Confirmed `get_all` behaviour from Frappe's source on the dev server.
- Confirmed the `vendor` feature is live on `ppj.dev.alvoraa.co`.

**Limits, so this is not over-trusted:**

- Only whitelisted functions. A permission bug in a doctype controller,
  a hook or a report would not show up here.
- I did not test any of this by making a request. The reading is static. Before
  fixing, each Group D item should be confirmed with an actual call from a
  low-privileged account — a couple of them may turn out to be unreachable for
  reasons I did not see.
- The 140 in the vendored Frappe HR fork were counted, not read.
