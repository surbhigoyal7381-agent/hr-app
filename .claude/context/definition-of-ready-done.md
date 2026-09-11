# Definition of Ready / Definition of Done

Two checklists. They are gates, not paperwork: an agent that cannot tick a box says
so out loud rather than passing soft work downstream.

## Definition of Ready — a slice may start build when…

- [ ] One named user gets one complete outcome. Not a fragment of five outcomes.
- [ ] The job to be done is written in the user's own words.
- [ ] The WOW moment is named, specific, and achievable inside this slice.
- [ ] Out of scope is written down explicitly.
- [ ] Gap analysis done: configure / extend / build new / drop, decided per requirement
      against what Frappe HR **actually** ships (verified in source, not recalled).
- [ ] Every requirement has at least one Given/When/Then acceptance criterion with an
      observable oracle.
- [ ] The permission matrix is written, including the negative cases — who must NOT
      see this.
- [ ] Edge cases listed: mid-period joiners/leavers, back-dating, negative balances,
      time zones, multi-company, cancelled/amended documents, concurrency.
- [ ] NFR numbers for this slice are pulled from the budget and made specific.
- [ ] Migration/backfill for existing tenants stated — even if the answer is "none".
- [ ] **Compliance-impact sub-analysis present** — data touched, obligations engaged,
      visibility delta, decision automation, retention and deletion, open questions.
      Mandatory on every spec, even when the honest answer to every row is "no impact".
- [ ] Every ⚠ COMPLIANCE question names a human who must decide and what it blocks.
- [ ] Nothing in the slice requires a prohibited capability (AI-set ratings, emotion or
      voice or facial inference, passive behavioural monitoring, individual-level
      surveillance framed as transparency).
- [ ] Open questions have owners and none of them blocks the first day of work.

If more than two boxes fail, the slice goes back. That is cheaper than building it twice.

## Definition of Done — a slice may ship when…

**Functional**
- [ ] Every AC met, or explicitly waived by a named human with a reason.
- [ ] Unhappy paths work: bad input, missing record, no permission, empty state.
- [ ] The WOW moment exists in the shipped code, not in a follow-up ticket.

**Quality**
- [ ] Automated tests cover every AC and the HR edge cases; each test fails when the
      feature is broken.
- [ ] Permission negative-tests present and passing.
- [ ] Full suite and linters run — real output, real result. No red.

**Process** *(`CLAUDE.md` §2)*
- [ ] Impact analysis written **before** any file was edited, covering cross-module
      reach, every caller grepped, all three personas, and HRMS domain impact.
- [ ] Each of the seven non-functional dimensions carries an explicit
      **improves / degrades / neutral** verdict — first in the proposal, then re-checked
      against the code actually written.
- [ ] Strategy was approved by a human before implementation began.
- [ ] `bench run-tests --app <app>` run for every changed Python app; UI flows traced by
      hand for JavaScript and HTML changes.
- [ ] Findings presented **before** `git commit`, with before-vs-after on each dimension.
- [ ] Work is on `dev`. Nothing committed to `main` without an explicit instruction.
      No demo or seed script is on a path to `main`.
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
- [ ] Security review (`06-security-review.md`) done where the slice touches personal
      data, permissions, integrations or AI — with residual risk named, owned and dated.

**AI (if applicable)**
- [ ] Guardrails structural, not prompt-only.
- [ ] Sensitive data redaction proven by test.
- [ ] Human gate on every irreversible or commitment-bearing action.
- [ ] Fallback and kill switch work.
- [ ] Eval set passes its threshold; must-refuse cases refuse.

**Handover**
- [ ] All five slice artifacts written and consistent with each other.
- [ ] Reviewer verdict is SHIP, or SHIP WITH FIXES and the fixes are done.
- [ ] Rollback plan stated.
- [ ] Anyone supporting this feature can explain it from the artifacts alone.
