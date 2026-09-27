# Slice template

Copy this folder to `docs/slices/NNN-short-kebab-name/` — or just let `/slice-start`
create it for you.

The five artifacts and what each must contain are defined in
`.claude/context/handoff-contract.md`.

    01-product-brief.md          hrms-product-manager
    02-functional-spec.md        hrms-business-analyst
    03-implementation-notes.md   hrms-fullstack-engineer
    04-test-report.md            hrms-test-automation-engineer
    05-review.md                 hrms-technofunctional-reviewer

Header block for every artifact:

    ---
    slice: NNN-short-kebab-name
    artifact: 0N-name
    author: <agent name>
    date: YYYY-MM-DD
    status: draft | ready | superseded
    inputs: [previous artifact]
    ---

Every artifact ends with: **Open questions** · **Assumptions** · **Handoff note**.
