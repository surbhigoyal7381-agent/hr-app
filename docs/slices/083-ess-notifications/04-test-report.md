# 083 — test report, 12 November 2026

Branch `slice/083-ess-notifications`, rebased on `origin/dev` at `75149184`.

Everything below was run on a **fresh `test_site` built inside throwaway containers**
(`a83-bench`, `a83-db`, `a83-redis`, own network, own Redis) with this worktree bind-mounted
over `apps/alvoraa_portal`, `apps/alvoraa_goals` and `apps/hrms`. **`hrlocal-bench` was never
used** — it mounts the shared main checkout, which is behind `origin/dev` with 289 modified
files belonging to other sessions, so it would have tested somebody else's working tree.

---

## 1. The numbers

| Suite | Result |
|---|---|
| `test_notices_076` | **30 OK** |
| `test_grooming_066` | **65 OK** and **1 OK** (two batches, both read from the log) |
| `test_portal_security_010` | **45 OK** and **5 OK** (two batches) |
| `test_inbox_parts_042` | **32 OK** |
| jsdom, all suites | **24 run, 0 failed** — `portal_notifications_083_test.js` 80 passed, `portal_home_076_test.js` **90** passed (was 78) |
| Static gates | all nine exit 0; `check_design_system.py` sizes **7/7**, radii **3/3**, loose colours **0** — unchanged |
| ruff | no new findings |

`bench run-tests --app` prints **two** batch summaries and the first says `OK`. Every number
above was read from the log file and `^Ran ` was counted per file; only `test_grooming_066`
and `test_portal_security_010` print two.

**What this does not cover.** These four suites are about **175 of roughly 4,360 test methods**
in `alvoraa_portal` — about **4%**. They are the suites that own this surface, but they are not
the app's suite. The full run is CI's Python job, and **CI is not in the deploy chain**: the
image build fires on the push and the deploy fires on the image build, so the first green tick
on a dev push is the deploy's, not the tests'.

---

## 2. What was proved by breaking it

A guard nobody has watched fail is not a guard. Four controls were broken on purpose and the
code put back afterwards.

| Control removed | What failed | Restored |
|---|---|---|
| `for_user` from the unread count | **two** tests, independently — one on the data, one on the source text | yes, 27 green at the time |
| `context.no_cache = 1` on the portal page | `test_the_page_asks_not_to_be_cached` | yes |
| `raise frappe.Redirect` for a Guest | `test_a_guest_is_sent_to_the_login` | yes |
| the CXO branch put back in `hmPaintPending` | `a CXO's chip counts kinds, the same number the bell shows` — *got "29 waiting", want "4 waiting"* | yes, 90 passed |

The first pair is genuinely two tests and not two views of one: one only has its power because
the fixture plants a colleague's unread announcement; the other reads the module's source.

The write's three assertions were **not** mutation-tested, because that means editing product
code inside a container another review was reading. They were traced by hand instead, by two
reviewers independently: drop `document_type` and only AC-31 breaks; drop `for_user` and only
AC-32 breaks; AC-30 survives both and cannot mask either.

---

## 3. The nine problems found, and where they were

**Every one was in the tests. Nothing in the product was changed to make a test pass.**

1. **Five tests counted one notice too many.** The shared `_wipe` cleared grooming notification
   rows and nothing else — correct until this slice, whose tests are the first ever to create an
   `Announcement` row. Each leftover sat in the next test's results.
2. **A test marked Ritika**, who is an HR Manager and does not report to the marker, so grooming
   refused it: *"only Ritika's current manager or HR can mark Ritika."*
3. **The replacement subject, Aman, has no login**, so grooming demanded the told-in-person tick:
   *"tick the box to confirm you told Aman in person."* Deepa satisfies both conditions — reports
   to Ravi **and** has a login — and the comment now says both, because picking a name that met
   only one is what cost the extra round.
4. **The link-search door asserted only absence.** If an upgrade made link search return nothing
   at all for this doctype, it would have passed and proved nothing. It now anchors on the
   caller's own row first.
5. **The export door did not clear `frappe.response`** before exporting, so a stale value could in
   principle have satisfied the positive assertion and hidden a moved key.
6. **A docstring named the wrong assertion** — dropping `for_user` makes the count 2, so the
   *first* assertion fails, not the second.
7. **`frappe.get_all` was used for the first door.** It is `get_list` with the permission check
   switched off, so it "found a leak" that was only the wrong function. That is also why
   `notices.py` reads these rows with `get_list`.
8. **`assertIsNone` on `get_value`** — it returns `{}`, not `None`, when a row is out of reach.
9. **The six-door list had five doors.** The `share` door and the `reference_doctype` count path
   were missing. Both are closed in the product — two reviewers reproduced them — so it was a hole
   in the canary rather than an exposure. Both are now covered.

---

## 4. Two faults the tests could not catch, found by review

Recorded here because "the suite is green" was true while both were live.

- **The desktop badge anchored to the top bar, not the bell.** `.nf-bell-set` was
  `position:static`, so the absolutely-positioned badge hung off `nav.navbar` — the viewport's
  top-right corner, partly clipped, with no number on the bell. jsdom loads the portal page with
  no Frappe navbar, so the code that moves the bell returns early and the rule is never applied:
  the tests only ever saw the `position:fixed` fallback, which is correct. One word, `relative`.
- **For a CXO, Home said "278 waiting" and the bell said 4, on one load.** Two definitions of
  "work owed" for one persona — and **the suite had pinned the bug**, asserting the summed value.
  The fix is a deletion. The assertion now asserts the shared number and that the two surfaces
  agree; put the branch back and it fails by name.

---

## 5. Still unproven, and stated rather than implied

- **No browser has ever shown this page.** Every claim about the badge colour, the Hindi strings,
  200% text and the bell at 1180 px is an argument from a CSS token. Surbhi will check it herself
  once dev is deployed.
- **Chrome Android, Back after sign-out.** A release gate, with the Chrome version to be recorded.
  The fallback if it shows rows is one line (`pagehide`) and was deliberately not written in
  advance.
- **Hindi is a machine draft** awaiting a native reader — any native reader, per Surbhi, but the
  sign-off itself is still required by name and date.
- **The 31st-call rate-limit refusal is not written.** The method is pinned POST twice over —
  `@frappe.whitelist(methods=["POST"])` and `gpSend` sending an args object — so the GET trap that
  would have made it unlimited-while-looking-limited is shut. The limit itself is untested.
- **The version the tests ran on is not the version we ship.** The containers run Frappe
  **16.33.1**; the image pins **16.35.0**. CI builds its own bench on the pin, so CI's Python job
  is what closes this.
- **`get_nav_counts` has never been measured in DTC's configuration**, and this slice makes it run
  on every non-Home page load for 483 logins. The standing backlog-depth assertion is in
  `test_inbox_parts_042`; the one-off measurement was deliberately not taken, because the only
  honest route to it would have rotated away DTC's single backup.
- **Nothing at DTC can demonstrate half of this slice.** It holds **zero** rows of all three
  notice kinds, so the notices group is empty there, "Mark all as read" never appears, and the
  bulk write matches nothing. Production can confirm it did no harm; it can never confirm it
  works. That needs seeded data, and DTC should be told before they find it.

---

## 6. One operational note

My own earlier mistake, recorded so it is not repeated: I started a second test run while the
first was still on its last suite, so two runs were writing to one site, and killing the script
left its children alive. That left a half-written user row which produced a
`TimestampMismatchError` on the next run and looked like a real failure. Any numbers taken during
that overlap were discarded, not reported.
