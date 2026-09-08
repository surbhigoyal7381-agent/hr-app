# Billing console — the gap, and the plan to close it

Parked 2026-09-08. Written down so it survives the PP Jewellers demo push.

## Where it stands

Three screens are built, tested and live on `dev` (commit `c90cdff`). Nothing on
`main`, nothing in production.

| Screen | Does |
|---|---|
| Billing (sidebar) | Every tenant, what they would be charged, what blocks the ones that cannot be. Preview and Create drafts. |
| Tenant page (Open on a card) | Health, usage, plan, cost, invoices, features — one page per customer. |
| New Tenant | Priced plans with bands and fees, Bill-to customer, subscription created with the tenant. |

## The gap

**The Edit screen does not know billing exists.** Zero references to plans,
customers or subscriptions. It ticks feature boxes and calls `update_tenant`.

So a customer can be put on a plan when created and never moved afterwards —
from the console. Which is the common case: customers change bands as they grow,
add payroll six months in, buy a pack.

None of this is reachable from the console today:

- Move a tenant to a different plan when they outgrow their band
- Change who is billed, or add a customer to a tenant created without one
- Add or remove an add-on and agree a rate
- Add an operations pack, or change named-user counts
- Set a setup fee, switch monthly to annual
- Mark a tenant internal, suspended or cancelled

All of it works. It is only reachable through the Frappe desk, by opening the
Alvoraa Subscription record directly.

Two smaller gaps: prices and plans are desk-only, and the monthly usage count
cannot be triggered by hand.

## The plan, in order

### 1. Make the subscription editable  *(the big one)*

Extend the Edit screen the way the create screen was extended: plan, bill-to
customer, add-ons with agreed rates, packs with user counts, status, billing
frequency, setup fee.

Backend gets a **separate `update_subscription`**, not more parameters on
`update_tenant`. Deliberately separate, because they are different actions.
Ticking payroll installs an app and re-syncs access — that is provisioning.
Adding payroll to the bill is a commercial decision. One form, two buttons.

The agreed-rate field is the important one. It is where per-customer pricing
lives: sell payroll at ₹25 generally and ₹18 to one client, and their
subscription keeps ₹18 whatever the price list does later.

Unblocks everything else.

### 2. Show where billing and reality have drifted

Once both sides can change, they can disagree, and both directions cost money:

- Module enabled, not on the subscription → they use it free
- Module on the subscription, not enabled → they pay for a blank screen

Show it on the tenant page and as one list across all tenants.
**Flag it, never auto-fix.** Silently switching on a module because somebody
added a line to an invoice is the subscription system performing a subscription
bypass — the same reasoning as the dependency guard in `unmet_requirements()`.

Small to build. This is the one that finds money.

### 3. Run the usage count on demand

A button on the tenant page. Today it waits for the monthly job or a bench
command, which makes testing the whole chain awkward. Half a day.

### 4. A pricing screen

Edit plans, module prices, packs and the cap without opening the desk. Useful
once somebody other than the founder changes prices. Until then the desk works.

Lowest priority. Leave it until a real customer forces the question.

## Recommendation

Do **1 and 2 together, then stop and look**. They are the pair that makes the
console self-sufficient — after them the desk is never needed for a
subscription. Three and four are conveniences.

All on `dev`. Nothing near `main` without a named release.
