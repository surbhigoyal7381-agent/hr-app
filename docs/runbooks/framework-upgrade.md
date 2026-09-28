# Upgrading Frappe, ERPNext and India Compliance

**Surbhi's standing rule, given 2026-09-27:**

> "We will first upgrade the version on dev, test our applications on it and then
> upgrade the production. It will reduce the risk of breaking the production
> environments."

This page is that rule, written down so it happens the same way every time.

It covers the three apps we pull from upstream. It does **not** cover Frappe HR,
which is copied into this repository and only changes when we change it.

---

## Why this had to be written down

**Before 27 September 2026 this rule could not be followed, even by someone
trying.**

The build fetched whatever the `version-16` branch pointed at that morning. So:

- you upgrade dev and test it
- a week later you deploy production
- **production gets whatever the branch points at that day** — not what you tested

That is not a risk we imagined. It is what happened. On 27 September, production
was running Frappe v16.34.0 and dev was running v16.35.0, from the same branch
name. Nobody chose that. Somebody rebuilt and the branch had moved.

**So the version pin is not an alternative to this rule. It is what makes the
rule possible.** Once the version is a number in a file, "the thing we tested"
and "the thing production gets" are the same thing by construction.

---

## The three rules that sit above the steps

**1 · A framework upgrade is its own deploy. Never combine it with a code
release.**

If the framework moves in the same deploy as our code and something breaks, you
cannot tell which caused it. Two deploys, one variable each.

This applies to the big release (ALV-137) above all.

**2 · Dev takes it first, and lives with it for a working week.**

Not an afternoon. A framework patch shows itself when somebody uses the product
for a few days, not when a test suite passes.

**3 · Test against real data, not only seeded data.**

Dev tenants have tidy data made by a seed script. A framework upgrade breaks on
the awkward records — the half-finished ones, the ones with odd history.
Restore a copy of a real tenant onto dev and migrate **that**. See `REHEARSAL.md`.

---

## The steps

The detail behind each of these — commands, what to read, what to time — is in
`docs/slices/055-pin-framework-versions/07-devops-inputs.md` §4.4.

1. **Look once a month.** Check what the three upstream branches have moved to,
   and read the release notes. A security advisory jumps the queue and does not
   wait for the month.

2. **One pull request raises the pins and nothing else.** Only `deploy/Dockerfile`
   and `ci.yml`. **No application code in the same change** — that is the whole
   point. The description says the tag, the commit, how many commits it moves,
   and whether any of the three apps changed their migration list.

3. **CI proves the build.** The first build after a pin change runs cold and is
   slow. Then the normal test suite.

4. **Read the migrations.** If any of the three apps added a migration, read what
   it does before it runs anywhere. A migration that writes permission rows is
   the one to worry about — see ALV-159 for a live example, and ALV-127 for why
   that table matters.

5. **Dev takes it, on Surbhi's word. Then leave it for a working week.**
   Somebody uses the tenant. This is the only place a framework patch meets our
   code before it meets a customer's data.

6. **Rehearse on a copy of a real tenant** before production — always when a
   migration list changed. Time it, and write down how long it took.

7. **Tell the tenants.** The notice needs a version, a date and a plain sentence
   about what changes. The non-functional budget asks for **at least 72 hours**
   notice for planned maintenance, so this goes out during step 5, not after.
   This is ALV-129, and it is only possible because the pin exists.

8. **Production, on Surbhi's word, in a quiet window.** **Never at month end** —
   payroll and attendance close then.

9. **Write the tag and the commit in the release notes.** Next month starts from
   there.

---

## What this does not protect against

Said plainly, because a rule that oversells itself is worse than no rule.

- **Pinning to something broken.** A pinned bad version is a bad version you
  keep. Step 5 is the protection, not the pin.
- **Getting old.** The pin rots if nobody raises it, and an unpatched framework
  is a security problem. We have swapped *silent change* for *deliberate
  staleness*. That is a better trade, not a free one — which is why step 1 has a
  month on it.
- **The rest of the image.** The base image is still a moving tag, and so are the
  Debian, Python and Node packages inside it. Two builds of the same commit can
  still differ — just not in the framework.
- **The sites volume.** A deploy does not refresh the built assets by itself, so
  what a browser downloads can be older than what the image holds. Separate
  problem, see `DEPLOYMENT_RUNBOOK.md` §5.7.

---

## Before this rule starts: what dev is on now

Dev's current versions arrived by accident, not decision — nobody chose Frappe
v16.35.0 or ERPNext v16.36.0. Two options, and the first is recommended:

- **Bless them.** Treat dev's current set as the first upgrade under this rule,
  and run steps 4 to 8 against it properly.
- **Pin dev back** to what production runs and start clean. **Not recommended:**
  production's image contains no CRM and no WhatsApp at all, so pinning backwards
  would ship a combination nobody has ever booted.

Related: ALV-156 (the pins), ALV-129 (telling tenants), ALV-159 (the ERPNext
v16.36.0 permission migration), ALV-137 (the production release).
