# Never over-engineer

This file is binding on every agent in `.claude/agents/`. It expands `CLAUDE.md` §4.
Where it conflicts with your own instinct to build something thorough, this file wins.

The rule in one line: **build the smallest thing that fully meets the approved
requirement, and nothing else.**

Over-engineering is not a style question here. It costs real money to run, it is read by
one small team, and every extra piece has to be maintained, tested, secured and upgraded
through every Frappe release. A clever extra is a permanent bill.

---

## 1. The ladder — always climb from the bottom

In order, cheapest first:

1. **Already there** — standard Frappe, Frappe HR or ERPNext does it. Use it.
2. **Configuration** — a setting, a Leave Type, a Salary Component, a Role, a Print
   Format, a Report Builder view, Global Defaults, HR Settings.
3. **Customisation** — a Custom Field, a Client Script, a Server Script, a Property
   Setter, a Notification, a Workflow.
4. **New code** — a controller method, a whitelisted endpoint, a hook, a page.
5. **A new DocType.**
6. **A new app.**

**State which rung you are on and why every rung below it was rejected.** "It felt
cleaner" is not a reason. If you cannot name what breaks on the cheaper rung, use the
cheaper rung.

## 2. Banned unless the requirement fails without it

Do not propose, specify, design, build, test for, or ask for any of these unless the
approved requirement cannot be met without it — and then say so out loud:

- A new app, a new module, a new workspace, a new settings page, a new dashboard.
- A new DocType where a Custom Field on an existing one would do.
- An abstraction layer, a base class, a registry, a plugin system, a generic "engine",
  a rules engine, a strategy pattern, a wrapper around Frappe.
- A feature flag, a toggle, a config switch, a mode.
- A backwards-compatibility shim, a migration path for data that does not exist, a
  deprecation period, a dual-write, a v1/v2 split.
- A cache, a queue, a background job, a denormalised field, an index — until a measured
  number says the simple version misses the NFR budget.
- A microservice, a separate database, an external service, a new third-party
  dependency, a new npm or pip package.
- A bespoke UI component where a standard Frappe/Frappe UI one exists.
- AI or an LLM where a rule, a default, a sort order, a filter or a well-placed field
  would do the job.
- A hook on a shared doctype where the change belongs in one place.
- "Future-proofing" of any kind. There is no future requirement. There is this one.

## 3. Things that are never a plan

- **"Phase 2 will fix it."** If the slice needs a phase 2 to be right, the slice is
  wrong now. Shrink it instead.
- **"We will need it later."** We do not know that, and later is cheaper than now.
- **"It is only a few more lines."** Those lines are read, tested, reviewed and
  maintained for years.
- **"It is more extensible this way."** Extensible for a requirement nobody has asked
  for is just more surface.
- **"Best practice says."** Say whose, for what size of team, and why it applies to a
  single-tenant-per-site Frappe app with one small team.

## 4. The subtract pass — mandatory before you hand anything off

Before you call your work done, read it once more with one question only: **what can I
delete and still meet the requirement?**

Delete it. Then say, in your output, what you removed on this pass. If you removed
nothing, say that too, so the user can judge.

## 5. When the simple version really is not enough

Say so in one plain sentence, with the number or the failure that proves it:

> "The simple version runs 1 query per employee — 400 queries on the HR list. The NFR
> budget is 50. So this needs one grouped query."

Evidence, then the extra. Never the extra, then a justification.

## 6. Scope creep is over-engineering too

Build what was approved. Not the adjacent thing you noticed. Not the bug you spotted
three files away. Not the refactor that would make it nicer. **Write those down as a
separate line for the user to decide on, and leave them alone.**

If you genuinely believe the approved requirement is the wrong shape, stop and say so
in one sentence. Do not quietly build the better version you have in mind.

## 7. What "no" sounds like

You are allowed — expected — to say no to work, including work another agent or the
user asked for:

> "We can do this with a Custom Field and a Notification. A new DocType would also
> work, but it adds a permission surface, a migration and a report to maintain, and I
> cannot name anything it buys us here. I recommend the Custom Field."

Short. Names the cheaper option. Names what the expensive one costs. Recommends. The
user decides.
