# ALV-288 — the address remembers which screen you are on

Surbhi, 2 November 2026: *"Refresh and forget is the issue in the complete Employee
Self Service portal. If I refresh the page from browser refresh button, it takes us to
home page insted of where we were before refresh."*

Strategy approved by Surbhi on 2 November 2026: screen-level routing in the live ESS
portal, with browser Back moving between screens. There is no `02-functional-spec.md`
for this one; the approved scope is the ticket and her sentence above.

## Rung on the cost ladder

**Rung 4, new code — about 50 lines in one file.** Cheaper rungs rejected:

| Rung | Why not |
|---|---|
| Already there | Frappe's website pages have no router, and `switchPanel` never touched the address. Nothing in the framework does this for a one-page panel switcher. |
| Configuration | There is no setting for "put the panel in the address". |
| Customisation | A Client Script runs in Desk, not on a website page. |

Not taken: a second page, a Vue router, a new dependency, a panel registry, server-side
panel gating, or deep state (which person, which month, which filter). The hard half of
a router already exists — `switchPanel` takes a stable panel name and the nav carries
`data-panel`, so the names are the addresses.

## Shape

- `switchPanel(name)` is the one door every screen change goes through (grepped: 30
  callers, and only line 4673 adds `.active` to a `.panel`). It writes `#<name>`.
- `hashchange` reads the address back, and so Back and Forward move between screens.
- The address is read once at load, when the server's two answers have landed.
- An address nobody recognises, or one this person may not open, lands on Home
  silently.

### Re-implemented, not shared with `next-frame.js`

`public/js/ess/next-frame.js:505-525` has a sound hash router and it was read first —
its synchronous-draw comment is why `switchPanel` draws the panel itself rather than
waiting for `hashchange`, and its "a typo is not a fault worth telling somebody about"
fallback is copied as behaviour.

It is **not shared as code.** It belongs to the frame Surbhi rejected on 26 September
2026, it is an IIFE with no exports, and its reach test (`frame.allowedSet`) is a
server-provided set this page does not have. A shared helper would mean giving a dead
file an export surface and a second caller. Twelve lines of plain code in `portal.js`
is less to own than that.

### How "may this person reach this panel" is decided

**The sidebar is the answer, already drawn.** A nav item is revealed only after
`get_portal_context` and `get_available_features` have said so
(`loadPortalContext` / `applyPlanNav`); until then it carries `display:none`. So the
test is: there is a `.nav-item[data-panel="<name>"]` whose own `style.display` is not
`none`. Re-deriving the ten role-and-plan conditions inside the router would drift from
`applyPlanNav` the first time a flag changes.

Two panels have no sidebar item and are decided by hand:

- `home` — always.
- `my-profile` — always. It is everyone's own profile, reached from the name in the
  sidebar and the account menu, neither of which is gated.

The other seven panels with no nav item (`seat`, `scorecard`, `pms-review`,
`mr-review`, `notice-compose`, `appraisal-setup`, `data-review` has one) mean nothing
without a record, and deeper state is out of scope. They get an address so Back leaves
them for the screen that opened them, but they are **not restorable**: reloading one
lands on Home.

### The leak this must not open

All 23 panels are in the DOM for every user — `ess_parts.py` pastes every part in with
no server-side gating. Today a panel is out of reach only because its nav item is not
shown. A naive router would let anybody type `#org-settings` and see the shell. It is a
UI leak, not a data leak (every panel's data comes from endpoints that check
permission server side, and `ALV-249`'s doors are closed in the permission layer), but
the router refuses it anyway, and silently — a sentence naming what was refused is a map
of what to go after.

**The timing trap:** the two context calls race, so a restore that ran before both
landed would refuse a page the person is allowed **and rewrite the address while doing
it**. The restore therefore happens once, when both answers are in. If one call fails,
no restore happens and the person starts on Home — the behaviour they have today, and
the safe way round.

## Functional impact

- **Cross-module:** none. One JavaScript file in `alvoraa_portal`. No DocType, no
  endpoint, no Python, no permission rule, no `hooks.py`.
- **CXO / HR Manager / Employee:** each gets back the screen they were on, and only
  from the set their own sidebar offers. A CXO's `#org-settings` restores; an
  employee's does not and lands on Home.
- **HRMS domain:** no change to leaves, attendance, payroll, appraisals or org
  structure.
- **`history.replaceState` at `portal.js:2635`** — slice 078's `?seat=` address.
  Read: it keeps a seat page shareable and uses `replaceState` so Back does not walk
  through every seat looked at. It rebuilds the URL as `pathname + search`, which
  **drops the fragment**, so it would have erased the panel from the address. It now
  keeps the hash. And because Back can now leave a seat page, leaving the seat panel
  clears `?seat=` — otherwise the parameter would stay behind and reopen the seat on
  the next reload.

## Non-functional verdict

| Dimension | Verdict | One line |
|---|---|---|
| Performance | neutral | No call added. `querySelector` per route, once per click. |
| Security | neutral | No server path touched; the router refuses a panel the sidebar does not offer, and the hash is validated against `^[a-z0-9-]{1,40}$` before it ever reaches a selector. |
| Reliability | improves | A reload no longer loses the screen. A malformed address lands on Home with no error. A failed context call falls back to today's behaviour. |
| Scalability | neutral | Nothing grows with headcount. |
| Maintainability | improves | One place writes the address and one reads it; panel names stay the single naming scheme. |
| Data integrity | neutral | No write path, no cache. |
| Compliance / privacy | neutral | No personal data in the address — a panel name only, never an employee id. Nothing new is logged. |
| Accessibility | improves | Back works the way a phone user expects; no visual-only signal added. |

## Parallel-work check

| File | Mine | Who else |
|---|---|---|
| `public/js/ess/portal.js` | `switchPanel` (~4665), `spAddress` (~2628), the two context callbacks (~10340, ~10415) | ALV-286 / ALV-287 in `mpfOpenDoc` and documents (10840-10935), `[data-pos-who]` (11117-11124), `mpfOpen` / `MPF` (10664-10760) |
| `alvoraa_portal/tests/portal_routing_288_test.js` | new file | nobody |
| `scripts/run_dom_tests.js` | the RUN list and its count | nobody known |

No overlap: their three regions are 6,000 lines away from all four of mine. Plan: stay
out, rebase onto their commits, read the whole incoming diff before committing.
`origin/dev` is at `f0c9e2f9`; their worktree `alv-288`… `alv-286-287` is on the same
base with nothing pushed yet.

## What is out

Deeper state (which person's mini profile, which month, which filter), scroll position,
server-side panel gating, and any change to what a panel shows.
