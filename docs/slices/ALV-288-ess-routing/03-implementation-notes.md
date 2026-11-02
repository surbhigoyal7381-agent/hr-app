# ALV-288 — implementation notes

Built 2 November 2026 on `slice/alv-288-ess-routing`, worktree
`.claude/worktrees/alv-288-routing`, off `origin/dev` at `f0c9e2f9`. Local only;
nothing pushed, no deploy command run.

## What was built, file by file

| File | Change | Mechanism | Why |
|---|---|---|---|
| `alvoraa_portal/alvoraa_portal/public/js/ess/portal.js` | 95 lines: the router above `switchPanel`, the address write inside it, `url.hash` kept in `spAddress`, `routeWhenReady()` in the two context callbacks, the `hashchange` listener in Boot | new code (rung 4) | Nothing cheaper exists: a website page has no router, and `switchPanel` never touched the address |
| `alvoraa_portal/tests/portal_routing_288_test.js` | new, 26 checks | new test | The pin tests, including the one that proves a hash cannot bypass the sidebar |
| `scripts/run_dom_tests.js` | the new test in `RUN`, count 21 → 22 | configuration | A test not in the list does not run |

### How it works, in five lines

1. `switchPanel(name)` — the one door every screen change goes through — sets
   `_panelNow = name` and writes `#<name>` to the address.
2. `hashchange` calls `routeFromAddress()`, so Back and Forward move between screens.
3. `routeFromAddress()` ignores an address that already matches the screen (which is
   what our own write looks like a moment later, and what keeps a detail screen from
   being bounced off).
4. Otherwise it opens the panel if `mayOpenPanel()` says this person is offered it, and
   Home if not — silently, with `location.replace` so Back does not return to the
   refused address.
5. The startup read happens once, when **both** `get_portal_context` and
   `get_available_features` have answered, because until then every gated nav item is
   still `display:none`.

### Re-implemented, not shared

`next-frame.js:505-525` was read first and its two decisions are kept (draw where the
hash is written; a typo is not news). It is **not** shared as code: it belongs to the
frame Surbhi rejected on 26 September 2026, it is an IIFE with no exports, and its
reach test is a server-provided `allowedSet` this page does not have. Twelve lines of
plain code is less to own than an export surface on a dead file plus a second caller.

### How "may reach" is decided

`mayOpenPanel(name)`: `home` and `my-profile` always; otherwise there must be a
`.nav-item[data-panel="<name>"]` whose own `style.display` is not `none`. The sidebar is
the server's answer already drawn — `loadPortalContext` and `applyPlanNav` reveal an
item only after the server's flags say so. The hash is validated against
`^[a-z0-9-]{1,40}$` before it is ever put in a selector.

## Acceptance

| What was asked | How it is met |
|---|---|
| The screen you were on survives a refresh | `#<panel>` in the address, read back once both context calls land |
| `hashchange` honoured; Back and Forward move between panels | the listener in Boot; checks 7 and 9 |
| The address changes on every route into a panel, including code routes | written inside `switchPanel`; grep confirms only `switchPanel` ever adds `.active` to a `.panel`, so there is no bypass to patch; check 2 drives a code route |
| An unknown or malformed hash falls back to Home with no error | checks 6 |
| A hash cannot open a panel the user is not offered | `mayOpenPanel`; checks 4 and 5 |
| `portal.js:2635`'s `replaceState` not broken | it rebuilt the URL as `pathname + search` and **dropped the fragment**; it now appends `url.hash`. Check 8 |
| Deeper state out of scope | nothing stored but the panel name |

## The seven dimensions, against the code as written

| Dimension | Before → after | Note |
|---|---|---|
| Performance | neutral | No call added. One `querySelector` per route. |
| Security | neutral | No server path touched. A typed hash is refused unless the sidebar offers it, and is regex-validated before reaching a selector. The panels were never a data boundary — their data comes from endpoints that check permission server side — and that has not changed. |
| Reliability | improves | A refresh keeps the screen; a malformed address lands on Home; a failed context call falls back to today's behaviour (start on Home). |
| Scalability | neutral | Nothing grows with headcount or months. |
| Maintainability | improves | One place writes the address, one reads it. The reach test asks the sidebar instead of copying ten role-and-plan flags. |
| Data integrity | neutral | No write path, no cache, no stored state. |
| Compliance / privacy | neutral | The address carries a panel name only — never an employee id, never a record. Nothing new is logged. |

## NFR notes

- **Queries:** none added. No endpoint, no Python, no DocType.
- **Permission enforcement points:** unchanged on the server. The router's refusal is a
  UI check on top of them, and is written down as such.
- **Sensitive fields touched:** none. `?seat=` already carried a position id; it is now
  cleared when you leave the seat page, which is slightly less in the address than
  before.
- **Fallbacks:** no hash → Home as today. Unknown hash → Home. Context call fails →
  no restore, Home.
- **Data doors (`.claude/context/data-doors.md`):** no bypass added — `ignore_permissions`
  count unchanged at zero for this change, no raw SQL, no `frappe.db.set_value`, no new
  endpoint. The door list was **not** re-run, because this change adds no read path: it
  only chooses which already-pasted panel shell is visible. What the panels fetch, and
  the permission layer behind it, is untouched.

## What else moved while I worked

`origin/dev` stayed at `f0c9e2f9` throughout; nothing came in, no rebase, no conflicts.
The ALV-286 / ALV-287 worktree (`fix/alv-286-287`) sits on the same base with nothing
pushed. Their three regions — `mpfOpenDoc` and documents (10840-10935),
`[data-pos-who]` (11117-11124), `mpfOpen` / `MPF` (10664-10760) — were not opened; my
four edit sites are at 2634, 4667, 4752, 10430, 10510 and 22825.

## Commands run, and what they said

| Command | Result |
|---|---|
| `node --check …/portal.js` | clean |
| `node alvoraa_portal/tests/portal_routing_288_test.js <page>` | `26 passed, 0 failed` |
| `node scripts/run_dom_tests.js` | `DOM tests: 22 run, 0 not run, 0 failed` |
| `python scripts/check_app_integrity.py` | `app integrity: 898 checks — OK - all consistent` |
| `python scripts/check_design_system.py` | `OK - the visual system holds` |
| `python scripts/check_brand_spelling.py` | `OK - every screen says Alvora` |

**Two existing suites caught a real bug**, which is the argument for them:
`portal_faces_078_test.js` (3 failures) and `portal_notices_send_076_test.js` (1) went
red on the first full run. The address write for a panel with no nav item fired a
`hashchange`, the router did not recognise the panel, and it bounced the seat page and
the Compose screen straight back to Home. The fix is the "address already matches the
screen" early return, and check 9 pins it.

## Known gaps and shortcuts

- **The Python suites were not executed — acceptable simplification, declared.** The
  tests that own the portal's page source need a bench, and the two I may not use are
  the shared `hrlocal-bench` and `hrlocal-078` (which mounts another worktree). Instead
  I read every Python test that slices the page near my edits
  (`test_data_review_page_012`, `test_review_page_010d`, `test_nav_consolidation_060`,
  `test_waves_5_6`, `test_portal_split_034`, `test_field_app_step3_013`,
  `test_joiner_078`, `test_joiner_079`) and confirmed each marker and slice boundary
  they rely on is untouched: the `replaceState` exclusions are about `joining.html`, not
  this file, and no `applyPlanNav()` call count changed. **Somebody should run
  `bench run-tests --app alvoraa_portal` before this goes to dev.**
- **Not tested in a real browser** — jsdom only. The phone case (Android's own Back, and
  the installed PWA) follows the same hash history, but I did not hold a handset.
- **Intentional trade-off:** a detail screen (a seat, a scorecard, a review, Compose) is
  addressed but not restorable, so reloading one lands on Home. Holding its record is
  deeper state, which Surbhi put out of scope. Back from one works, which is the part
  that was missing entirely before.
- **Intentional trade-off:** Back now walks back through screens instead of leaving the
  portal. From Home it still leaves. This is the approved behaviour; it is worth saying
  out loud to the DTC staff who use the installed icon.
- **Temporary debt, small:** if `get_portal_context` or `get_available_features` fails,
  the screen is not restored. Removing it would mean a third "the nav is settled" signal
  that nothing else needs.

## Subtract pass

Removed: the duplicate `want !== _panelNow` guard in the allowed branch (folded into one
early return at the top). Considered and not built: a shared router module, a panel
allow-list constant beside the 23 panels, a `data-route` attribute on the nav, a
"you do not have access" message, and any memory of filters, months or scroll position.
