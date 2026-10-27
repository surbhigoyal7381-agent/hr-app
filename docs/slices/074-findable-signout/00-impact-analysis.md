# ALV-222 — a findable sign-out in the employee portal

Impact analysis and strategy. Engineer: `hrms-fullstack-engineer`, 27 Oct 2026.
Worktree `.claude/worktrees/074-signout`, branch `slice/074-signout`, from
`origin/dev` 5f423750.

---

## 0. The first question, answered: is Frappe's sign-out reachable on a phone?

**No. On a phone, Frappe's navbar is not on the page at all.** The ticket's own
starting assumption and mine were both out of date.

The evidence, all in `origin/dev`:

| Where | What it says |
|---|---|
| `public/css/ess/panels.css:371`, inside `@media(max-width:768px)` | `nav.navbar,.page-header-wrapper{display:none}` |
| `public/css/ess/panels.css:368-370` (the comment beside it) | "ALV-213: one top bar on a phone. The portal header carries the account menu, so Frappe's own navbar (42 px) is hidden here" |
| `templates/includes/ess/frame.html:143-147` | the portal's own `#mob-avatar` button and `#mob-acct-menu` dropdown, holding `My Account` (`/me`) and `Log out` (`/logout`) |
| `tests/test_portal_full_width_213.py:29-35` | pins all of that |

So `frame.css:275-280` (the ALV-153 comment the ticket quotes) is still true but
no longer relevant on a phone: `#website-post-login` is Frappe's dropdown, and
Frappe's whole navbar is hidden below 768px. ALV-213 (already on `dev`) replaced
it with the portal's own account menu, which does carry a `Log out`.

**What this means for the job.** It is neither "it already works, just style it"
nor "build one from nothing". It is the third answer:

> A sign-out exists, it is ours, and it is two taps deep behind an unlabelled
> circle with an initial in it. It needs to come out of the dropdown and onto the
> bar.

That is a smaller job than the ticket feared and a slightly different one than it
described. The sign-out to make findable is **our own**, not Frappe's.

**A real phone check is still owed and is not mine.** Nothing here was opened on a
handset. Three things need eyes on glass before this ships: that the new button
fits beside the tenant name on a 320 px screen, that tapping it actually ends the
session and lands on the login page, and that `/logout` behaves the same inside an
installed PWA (slice 062) as in a tab. That last one is the one I would check
first.

**One defect found in passing, not mine to fix.** `public/js/ess/next-frame.js:1002`
falls back to `window.location.href = "/?cmd=web_logout"` if the `logout` call
fails. On the installed Frappe v16.33.1, `web_logout` is
`@frappe.whitelist(allow_guest=True, methods=["POST"])` (`frappe/handler.py:119-125`),
so a GET to that URL is refused. That fallback cannot work. It is on the `next`
frame, which is not the page customers use, so I have left it alone and written it
down.

---

## 1. Which rung of the ladder

**Rung 1 and rung 4, and the cheap rung is doing most of the work.**

- *Already there* — the sign-out itself. `/logout` is Frappe's own page
  (`frappe/www/logout.py` + `logout.html`, verified in `hrlocal-bench`). It is
  already the target of our dropdown row, shipped and pinned by ALV-213. I am not
  writing a sign-out; I am reusing the one that exists.
- *New code* — **one anchor in the phone header and one CSS block.** This is the
  cheapest rung that can meet "always visible, not behind a menu": visibility is
  markup, and no setting, custom field or property setter can put a control on a
  page.

Rejected, with reasons:

| Cheaper or adjacent option | Why not |
|---|---|
| Style the existing dropdown so it is easier to find | It would still be a dropdown. The requirement is "not behind a menu". |
| Keep it as the dropdown and add a confirm | Does not address findability at all. |
| A POST form to `/api/method/logout` instead of the `/logout` link | More robust in theory — the session dies server-side with no JavaScript — but it needs a CSRF token in the template and a new code path. The portal is a half-megabyte JavaScript application: with JS broken, nothing on this page works, so a JS-dependent sign-out is not the weak link. Rejected as unearned. |
| A new `public/js/ess/signout.js` | A new asset file needs a `<script src>` in the page and a line in the orphan guard, to hold one `removeItem` call. |
| A function in `portal.js` | Four other sessions are in that file. A one-line attribute avoids it entirely. |
| Remove the dropdown's `Log out` row now that there is a visible one | Surbhi's instruction is to add, not replace. Noted below as a thing to decide later, not done. |

---

## 2. What I will change

| File | Change | Hot? |
|---|---|---|
| `alvoraa_portal/alvoraa_portal/templates/includes/ess/frame.html` | one `<a class="mob-signout" href="/logout">` inside `.mob-header`, after the avatar | yes — 2 commits in `origin/dev` this week, both already under me |
| `alvoraa_portal/alvoraa_portal/public/css/ess/frame.css` | one appended `ALV-222` block: `.mob-signout`, its focus ring, and one line letting `.mob-brand` truncate | yes — 4 commits, all already under me |
| `alvoraa_portal/tests/portal_signout_222_test.js` | new jsdom test | new file |
| `scripts/run_dom_tests.js` | one `RUN` entry, `EXPECTED_BROWSER_TESTS` 15 → 16 | low |

**`portal.js` is not touched.** The ticket asked for that and it turned out to be
free: the only behaviour needed beyond following a link is clearing one
`localStorage` key, which is an attribute on the anchor.

The `.mob-brand` truncation line is not decoration. The phone header is a flex row
and the tenant name has no truncation today, so a long name ("Dev Tex Clothing
Private Limited") would push the new button off the right edge of a 320 px screen
— which fails "always visible" outright. One line, same rule set, stated here so
it is not a surprise in the diff.

---

## 3. Functional impact

**Cross-module.** None. No Python, no DocType, no API, no hook, no permission, no
query. `alvoraa_goals`, `alvox_compensation`, `hrms` and `erpnext` are untouched.
`/logout` is Frappe's. No function signature changes, so there are no callers to
grep; the two existing callers of the `/logout` URL (`frame.html:146` and
`test_portal_full_width_213.py:34`) keep working unchanged.

**HRMS domain.** None. Leaves, attendance, payroll, appraisals and org structure
are untouched.

**Personas.**

| Persona | What changes |
|---|---|
| **Employee** (the one this is for) | On a phone, a named `Sign out` on the bar. One tap instead of two, and the word instead of an initial in a circle. On a desktop, nothing changes — the phone header is `display:none` above 768px and Frappe's navbar with its own menu is still there. |
| **HR Manager** | Same as Employee. The sign-out is personal; it carries no company or row scope. |
| **CXO** | Same again. Signing out is not a multi-company action. |

**Multi-tenancy.** Nothing read, nothing listed, nothing aggregated. The one Jinja
value in the header (`tenant_name`) was already there.

---

## 4. The seven non-functional dimensions — proposal

| Dimension | Verdict | Why |
|---|---|---|
| **Performance** | neutral | One anchor and ~10 lines of CSS on a page that already ships half a megabyte of script. No query, no request, no render path changed. |
| **Scalability** | neutral | Static markup. Identical at 11 logins and at 441. |
| **Security / permissions** | **improves** | The control that ends a session becomes reachable in one tap on a shared handset. Nothing is granted: `/logout` is `allow_guest` by design and ends only the caller's own session (`frappe/auth.py:367-378` deletes the caller's own `sid` and re-cookies them as Guest). No new endpoint, no `ignore_permissions`, no new input. |
| **Reliability** | neutral | The same mechanism the dropdown already uses, so it cannot be less reliable than today's only sign-out. The `localStorage` clear is wrapped so a private-mode throw cannot stop the navigation. |
| **Maintainability** | **improves slightly** | Two sign-outs to one page is duplication, but both point at the same URL, and the visible one removes the ALV-213 comment's open question. No abstraction, no helper, no new file of code. |
| **Data integrity** | neutral | Nothing is written. `sb-pinned` is a sidebar display preference, not data. |
| **Compliance / privacy** | **improves** | This is the mechanism behind the gate. 441 staff on shared handsets, about to get an installable icon: ending a session is the control that stops the next person reading the last person's payslip. No personal data is added to the page, no log line is written, nothing is widened — no field, list, export, notification or API response changes. |

**Security and privacy requirements met.** This change creates no new attack
surface to argue about: no endpoint, no input, no query, no SQL, no permission
decision. The one thing worth saying out loud is that `/logout` is a GET, so it is
cross-site-forgeable — but the worst a forged sign-out can do is sign someone out,
Frappe ships the link that way itself, and we already shipped it in ALV-213.

**Accessibility.** The word, not a glyph, which is the point. 44 px minimum
height. `:focus-visible` ring matching `.mob-avatar`'s. It is an `<a>` with real
href, so it is keyboard-reachable and works with the Enter key with no handler.
The string goes through `_()`, so Hindi and Punjabi can have it.

---

## 5. Parallel-work check

**What came in.** My worktree is from `origin/dev` 5f423750; local `dev` was 192
commits behind. Five of those commits touch my two files:

| Commit | What it did to my files |
|---|---|
| `6aaf9ffd` ALV-213, the portal uses the whole screen | **The one that matters.** Added `#mob-avatar`, `#mob-acct-menu` with `My Account` and `Log out`, and hid `nav.navbar` below 768px. It is the reason this ticket's premise needed correcting. |
| `82384a20` ESS: one brand mark, the avatar on the page's edge | moved the avatar; touches the same header block |
| `bebbca79`, `92fc3a35` ALV-217, readable on a cheap phone | appended the `.fail` block at the end of `frame.css` |
| `96fefc1a` 066, grooming notices in the bell | added `#gm-bell` inside the notification panel in `frame.html` |

**Who else is in them.**

- The work board claims `frame.css` for `ALV-213-portal-full-width` (worktree
  `agent-ade6cbb51a6e764eb`) and for `ALV-149/152/153`. ALV-213's work is now **in
  `origin/dev`**, so that row is stale rather than live.
- `073-ess-ux-fixes` sits on `82384a20`, the newest `frame.html` commit, and is in
  the same header block.
- Four sessions are in `portal.js`. **I do not touch it.**
- The main checkout holds another session's uncommitted work in `auth.py`,
  `hooks.py`, `module_access.py` and two test files, plus an untracked
  `alvoraa_portal/tests/portal_appraisal_test.js`. **I have not touched, staged or
  reverted any of it.** That stray test file will trip `run_dom_tests.js`'s
  file-list guard in the main checkout; it is not mine and I have left it.

**The plan: split.** I own one new element at the end of the `.mob-header` block
and one appended `ALV-222` block at the end of `frame.css`. I move, rename,
re-indent and reformat nothing, so 073's edits to the brand mark and the avatar
land beside mine rather than on top of them.

**The test that pins it.** `portal_signout_222_test.js` asserts the button exists
on the bar, carries the word, is at least 44 px, is not inside the dropdown, and
that the dropdown's own `Log out` is still there. A merge that drops either fails
by name. `test_portal_full_width_213.py` already pins ALV-213's side.

---

## 6. What I am deliberately not doing

Each of these is a line for Surbhi to decide, not work I have quietly done:

1. **No confirm dialog.** Design E-6 asks for "a confirm only on a shared
   session", but "shared session" is a slice 072 concept that does not exist in
   the code yet. A confirm on every sign-out would make the fast path slower for
   the person whose phone it is. Deferred to 072, where the concept lands.
2. **The dropdown's `Log out` row stays.** Surbhi said add, not replace. Once the
   visible button has been seen working on a handset, removing the row is a
   one-line follow-up.
3. **No desktop change.** Desktop still uses Frappe's navbar menu. The gate is
   about shared phones.
4. **`next-frame.js`'s broken `web_logout` fallback stays broken.** Written up in
   §0; it is on a page customers do not use.
5. **No session idle timeout.** That is 072's Q3 and a different change.

---

## 7. Strategy, in one paragraph

Put one `<a href="/logout">Sign out</a>` on the phone header beside the avatar,
style it to 44 px with the word visible, let the tenant name truncate so it can
never be pushed off a narrow screen, clear the one `localStorage` key on the way
out, and pin all of it with a jsdom test. Reuse Frappe's `/logout`, which already
ends the session and which our own dropdown already points at. Do not touch
`portal.js`, Python, any DocType or any permission. Leave the dropdown alone.
