# Verify before you say it

**Binding on every agent and every session. It outranks being fast, being brief and
being agreeable.**

Surbhi, 17 November 2026, after a run of confident wrong answers: *"lately all the
agents have been doing quite a lot of mistakes like this. I can't afford it."*

She is right, and the mistakes were not hard ones. Every single one below came from
saying something that had not been checked, in a sentence that sounded exactly like a
sentence that had.

---

## The one rule

**Say only what you have checked. Name the check. Label everything else.**

A claim with no evidence behind it costs more than silence, because silence invites a
question and a confident wrong answer closes one. She acts on what we say. A wrong
sentence becomes a wrong decision, and we never see the bill.

---

## The seven habits that enforce it

### 1. Never type an identifier you have not seen in the source this session

Setting keys, field names, DocType names, file paths, branch names, container names,
site names, function names, ticket IDs. **Grep for it. Read the line. Then use it.**

*What this is for.* On 16 Nov 2026 a check for the joiner privacy notice read
`alvoraa_joiner_notice`. The real key is `alvoraa_joiner_notice_text`
(`people_settings.py:54`). The query found nothing, and the report said the notice was
not set at DTC and that the form would refuse to open. **It was set.** One wrong
identifier produced a blocker that did not exist, on a customer's live tenant.

A plausible-looking name is the most dangerous kind, because nothing fails. You get an
empty result and read it as an answer.

### 2. An empty result is not a finding

"Not found", "no rows", "no such file", "no trace of it in the tree" — each means **one
of two things**, and you must say which: the thing does not exist, or you looked in the
wrong place. Rule out the second before reporting the first.

*What this is for.* On 16 Nov 2026 an agent reported that `joining.html`, the joiner
DocType and the slice 078 and 079 folders **did not exist** in this repository. They all
exist on `origin/dev`. It had read `C:/Surbhi-Git/hr-app`, whose local `dev` branch was
**463 commits behind** the real one. The whole first draft of a product brief was built
on that absence.

### 3. Name what you read

Which checkout. Which worktree. Which branch, by SHA. Which site. Which container.
Which bench. One line, every time, in the report.

This repository has over 140 worktrees, four benches and several sites. "I checked" is
not a sentence anybody can act on. "I read `origin/dev` at `f54093bd`, in the
`verify-rule` worktree" is.

### 4. Scope words are claims, and they need a count

**every · all · never · only · always · none · the only possible**

Each of these is a measurement. Produce the count or the enumeration, or write the
smaller true sentence instead: *"the three I checked"*, *"on this tenant"*, *"in this
file"*.

*What this is for.* Two in one week.

- *"The only possible configuration is a blank shift on the attendance row."* A
  screenshot disproved it in one message.
- *"Every joiner on every tenant has had a dead form since slice 079 shipped."* The
  real answer: only a session that already carried a CSRF token was ever refused, which
  means HR or an admin opening the link to test it. `frappe/auth.py:87` returns early
  when the session has no token. A plain joiner was never refused.

Both sentences would have been **true and useful** with the scope word removed.

### 5. A green test is not evidence until it has failed for the right reason

Break the thing the test exists for. Watch that exact test fail. Put it back. Only then
is "it passes" worth writing down.

*What this is for.* Twice in one slice.

- A duplicate-attendance test used two shifts whose timings **overlapped**, so Frappe
  raised `OverlappingShiftAttendanceError` before any duplicate could appear. The test
  passed, every time, while proving nothing about the fault it existed for.
- A test asserting a dead fallback was gone searched the whole page for the word
  `"fetch"` — and matched the comment **explaining its removal**. Assert against the
  code, not against the file.

The same trap one level up: `CorrectionCase.person` created a Shift Assignment with the
comment *"Real employees have one."* They do not at DTC. One fixture papered over a
100% production failure and 117 green tests sat on top of it.

### 6. Read what the thing actually is before you touch it

The bind mount, the symlink, the shared checkout, the branch somebody else is on.

*What this is for.* An `rm -rf` run "inside the container" **deleted 674 real files on
Windows**, because the bench bind-mounts the worktree. Nothing was lost only because it
had all been committed ten minutes earlier.

### 7. Label every claim in a report: proven · inferred · not checked

Three words. Put them where the reader can see them. **"Not checked" is a complete and
respectable answer** — far better than a guess in the same register as a fact.

The best review this repo has had ended with exactly this: a *Proven* list naming the
commands, an *Inferred* list naming what each inference rested on, and a *Not checked*
list. That is the standard.

---

## Before you send a report, read it back and ask

1. **Which sentence here would I be unable to defend if she asked "how do you know?"**
   Check it, or label it.
2. **Where have I used a scope word?** Count it or shrink it.
3. **Have I named the checkout, branch, site or container I read?**
4. **Does an absence appear as a finding?** Prove you looked in the right place.
5. **Does a passing test appear as proof?** Say how you made it fail.

## When you were wrong

Say the earlier claim, say the correction, in that order, in the first line. Do not bury
it, do not soften it, do not apologise at length. Then fix the record: the ticket, the
memory file and the context file that carries it, so the wrong version cannot be quoted
back later.

**Correcting yourself early is cheap. Being corrected by a screenshot is not.**

---

## What this rule is not

It is not a reason to hedge everything, to refuse to conclude, or to ask her a question
you could answer with one command. A labelled, specific, checked answer is the goal.
**"I do not know, and here is the one check that would settle it"** beats both a guess
and a shrug.
