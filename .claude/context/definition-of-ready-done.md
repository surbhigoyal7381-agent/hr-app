# Definition of Ready / Definition of Done

Two checklists. They are gates, not paperwork: an agent that cannot tick a box says
so out loud rather than passing soft work downstream. **Ticking every box does not
approve anything — the user still decides.**

## Definition of Ready — a slice may start build when…

**The brief**
- [ ] One named user gets one complete outcome. Not a fragment of five outcomes.
- [ ] The job to be done is written in the user's own words.
- [ ] A competitive analysis across whole products is present, every claim labelled
      seen / read with date / `[recall — verify]`, including what we will NOT copy.
- [ ] The Kano class is stated and marked **survey** or **proxy**, with the demand
      evidence behind it.
- [ ] Persona enhancements through the employee portal are decided — each idea from the
      UX opportunities scan marked in this slice / later / no, with a reason.
- [ ] The WOW moment is named, specific, and achievable inside this slice.
- [ ] Out of scope is written down explicitly.
- [ ] The user approved the brief.

**The design** *(when the slice changes a screen)*
- [ ] A **clickable prototype** exists and the user reviewed it at the design check.
- [ ] The user's feedback is logged in `.claude/context/ux-learnings.md`.
- [ ] Every state is designed: empty, loading, error, no permission, first-time.

**The requirements**
- [ ] `01c-security-privacy-requirements.md` is written — even when the finding is "no
      personal data touched" — with numbered `SEC` and `PRIV` requirements.
- [ ] `07-devops-inputs.md` §1–3 are written, with numbered `OPS` items.
- [ ] Gap analysis done: configure / extend / build new / drop, decided per requirement
      against what Frappe HR **actually** ships (verified in source, not recalled).
- [ ] The epic and user stories are written — named personas, INVEST-checked, sized,
      linked to prototype screens — including the "must not" stories.
- [ ] Every story has at least one Given/When/Then acceptance criterion with an
      observable oracle.
- [ ] **Traceability is complete:** every brief line, prototype screen, `SEC`, `PRIV` and
      `OPS` item maps to an acceptance criterion, or is marked "not adopted" with the
      user's decision recorded.
- [ ] The permission matrix is written, including the negative cases — who must NOT
      see this.
- [ ] Edge cases listed: mid-period joiners/leavers, back-dating, negative balances,
      time zones, multi-company, cancelled/amended documents, concurrency.
- [ ] NFR numbers for this slice are pulled from the budget and made specific.
- [ ] Migration/backfill for existing tenants stated — even if the answer is "none".
- [ ] **Compliance-impact sub-analysis present** — data touched, obligations engaged,
      visibility delta, decision automation, retention and deletion, open questions.
- [ ] Every ⚠ COMPLIANCE question names a human who must decide and what it blocks.
- [ ] Nothing in the slice requires a prohibited capability (AI-set ratings, emotion or
      voice or facial inference, passive behavioural monitoring, individual-level
      surveillance framed as transparency).
- [ ] When the slice installs an existing Frappe app, every row of
      `new-frappe-app-checklist.md` up to the spec is answered.
- [ ] Open questions have owners and none of them blocks the first day of work.

If more than two boxes fail, the slice goes back. That is cheaper than building it twice.

## Definition of Done — a slice may be presented for deploy when…

**Functional**
- [ ] Every AC met, or explicitly waived by the user with a reason.
- [ ] Unhappy paths work: bad input, missing record, no permission, empty state.
- [ ] The WOW moment exists in the shipped code, not in a follow-up ticket.
- [ ] The built screens match the prototype the user approved, or every difference was
      agreed by the user.

**Quality**
- [ ] Automated tests cover every AC and the HR edge cases; each test fails when the
      feature is broken.
- [ ] Every `SEC`, `PRIV` and `OPS` item has a test, or is listed as an untested control.
- [ ] Permission negative-tests present and passing.
- [ ] Full suite and linters run — real output, real result. No red.
- [ ] When an existing Frappe app was added: installed and tested on a fresh site, the way
      CI builds one.

**Process** *(`CLAUDE.md` §1 and §2)*
- [ ] Impact analysis written **before** any file was edited, covering cross-module
      reach, every caller grepped, all three personas, and HRMS domain impact.
- [ ] Each of the seven non-functional dimensions carries an explicit
      **improves / degrades / neutral** verdict — first in the proposal, then re-checked
      against the code actually written.
- [ ] The DevOps view on the strategy (`07` §4) was shown to the user with the engineer's.
- [ ] Strategy was approved by the user before implementation began.
- [ ] Built and tested on the local instance first.
- [ ] `bench run-tests --app <app>` run for every changed Python app; UI flows traced by
      hand for JavaScript and HTML changes.
- [ ] Findings presented **before** `git commit`, with before-vs-after on each dimension.
- [ ] Work is on `dev`. Nothing pushed to dev, and nothing pushed or merged to `main`,
      without the user's explicit word for that step. No demo or seed script is on a path
      to `main`.
- [ ] Deploy approval requested separately, and not assumed from "fix this".

**Non-functional**
- [ ] Performance measured against the budget at realistic volume, not asserted.
- [ ] Permissions enforced server side on every path.
- [ ] No personal data in logs, errors, exports, notifications, prompts or fixtures.
- [ ] Failure paths defined: timeout, bounded retry, defined end state.
- [ ] Observability in place: someone on call could diagnose this at 2am.
- [ ] Accessibility checks done; what is not automated is written down.
- [ ] Customisation is upgrade-safe — no upstream edits.
- [ ] All user-facing strings translatable.

**Compliance**
- [ ] Every obligation named in the spec is discharged by a **mechanism in the code**,
      and each mechanism is named in the implementation notes.
- [ ] Every mechanism has a **test named after the obligation** — or appears in the test
      report as an untested control. Those are the only two options.
- [ ] No new personal-data field without a sensitivity class, a purpose tag and a
      retention answer.
- [ ] No visibility widened beyond what the spec authorised.
- [ ] Retention and purge respect legal hold.
- [ ] Audit entries carry before and after, not just "changed".
- [ ] Where a decision about a person is automated or influenced: a named accountable
      human, a replayable derivation, and a route to contest it.
- [ ] `06-security-review.md` marks every `SEC` and `PRIV` requirement met / partial / not
      met — with residual risk named, owned and dated.

**Release readiness**
- [ ] `07-devops-inputs.md` §5 is written: rollout from local to dev to main, migration dry
      run on a copy, deploy commands marked for the user's approval, post-deploy checks,
      rollback and monitoring.
- [ ] The repo's known release traps were checked (the DevOps agent's "Lessons already
      paid for").

**AI (if applicable)**
- [ ] Guardrails structural, not prompt-only.
- [ ] Sensitive data redaction proven by test.
- [ ] Human gate on every irreversible or commitment-bearing action.
- [ ] Fallback and kill switch work.
- [ ] Eval set passes its threshold; must-refuse cases refuse.

**Handover**
- [ ] All slice artifacts written and consistent with each other.
- [ ] Reviewer, security and DevOps verdicts are SHIP, or SHIP WITH FIXES and the fixes
      are done.
- [ ] Anyone supporting this feature can explain it from the artifacts alone.
