# ALV-318 and ALV-319 — impact analysis and strategy

Two faults that locked a real person out of a real tenant (amata.dev, 5 Nov 2026).
Surbhi approved the fix the same day. No spec folder exists for these: they are a
defect pair against slice 079, so this file stands in for `02-functional-spec.md`
and names its own acceptance criteria.

## What is actually wrong

| | ALV-318 | ALV-319 |
|---|---|---|
| Fault | `Alvoraa Joiner` can be granted by a Role Profile, which applies to many people and re-applies on every save | `auth._is_a_joiner` caches the answer per user and never drops it, so taking the role away does not release the account |
| Blast radius | Everybody on that profile. Fifty staff on one profile, one edit, fifty lockouts | One person, invisibly: the role is gone from the screen and the lock stays |
| Shipped state | 079 is on dev; the joiner form itself ships OFF at every tenant | same |

## Acceptance criteria I am building to

- **AC-1** A `Role Profile` cannot be saved with `Alvoraa Joiner` among its roles.
  The refusal names the role and says why, in plain words.
- **AC-2** A `User` cannot *gain* `Alvoraa Joiner` except through
  `joiner_invite.make_sign_in`. Holds for Desk, the REST API and a Data Import.
- **AC-3** `make_sign_in` still works, proved by a test.
- **AC-4** The `Role` record says what the role is for.
- **AC-5** A user's roles changing drops the gate's cached answer for that user.
- **AC-6** The false comment in `auth.py` is gone and replaced with what happened.

## Rung of the ladder

**Rung 4, new code — two `doc_events` validate handlers and one `on_update`
handler**, plus **rung 3, one Custom Field** for AC-4.

Cheaper rungs rejected, by name:

- **Already there (rung 1).** Frappe has no "this role may not be granted"
  switch. `Role.disabled` would stop the invite path working too
  (`User.remove_disabled_roles` strips a disabled role from every user on save,
  so every joiner would lose the role at their next save). Role Profile has no
  exclusion list. Checked in `frappe/core/doctype/role/role.json` and
  `role_profile.py` on v16.33.1.
- **Configuration (rung 2).** A permission row cannot express this; worse, the
  079 design requires this role to appear in **no** doctype's permission rows at
  all, because Frappe grants desk access to a role the first time it meets it in
  a permission JSON. A static test already pins that.
- **Customisation (rung 3)** for the refusal: a Server Script on validate would
  work, but it lives in each site's database, is invisible to CI and to this
  repository, and would have to be installed per tenant. Rejected for the
  refusal; **accepted for AC-4**, where a Custom Field is the only way to put
  words on the `Role` record (`Role` ships no description field — field list
  read on v16.33.1: `role_name, disabled, desk_access, two_factor_auth,
  restrict_to_domain, home_page, column_break_4, is_custom`).
- **Rung 5, a new DocType / rung 6, a new app.** Not considered seriously.

Nothing is added that the two tickets did not ask for: no feature flag, no
registry of "protected roles", no generic role-guard engine. One role, named.

## Mechanism, and why

**The refusal lives on `validate`, in `joiner_invite.py`, as two `doc_events`
handlers.**

`validate` is the one place every door passes through. Verified in the installed
source, v16.33.1:

| Door | Path | Runs `User.validate`? |
|---|---|---|
| Desk user form | `frappe.client.save` → `doc.save()` | yes |
| REST `PUT /api/resource/User/<name>` | `api/v1.update_doc` → `doc.save()` | yes |
| REST child write `/api/resource/Has Role/<name>` | `api/v1.update_doc` → then `frappe.get_doc(parenttype, parent).save()` | yes |
| `frappe.client.insert` of a `Has Role` row | `client.insert_doc` → `parent.append(...); parent.save()` | yes |
| `frappe.client.set_value` on a `Has Role` row | `client.set_value` → parent `doc.save()` | yes |
| Data Import | `doc.save()` | yes |
| `user.add_roles(...)` from code | `append_roles` → `self.save()` | yes |
| Role Profile edited | `RoleProfile.on_update` → `update_all_users` → `user.save()` per user | yes — and this is the lockout |

**The one door `validate` does not cover**, and I am not closing it:
`POST /api/resource/Has Role` goes to `api/v1.create_doc` →
`frappe.new_doc(...).insert()`, which inserts the child row on its own without
re-saving the parent (there is no `istable` guard in `Document.insert` on this
version). Permission for it is checked against the **parent** doctype
(`document.py:419`), so it needs `write` on `User` — System Manager. The same
person can edit the role list on the user form, where the guard does fire, so
this door is reachable only by a deliberate act of somebody who already holds
full rights, not by the accident ALV-318 describes. A `Has Role` validate hook
would close it, and I am leaving it out under the no-over-engineering rule; it is
listed in the notes as a known gap for Surbhi to overrule if she wants it.
Raw SQL into `tabHas Role` is likewise out of reach of any hook.

**How `make_sign_in` is let through:** it sets `user.flags.alvoraa_joiner_invite
= True` before `user.insert()`. `"flags"` is in Frappe's `RESERVED_KEYWORDS`
(`frappe/model/base_document.py:1598`), so `BaseDocument.update` skips it and a
request payload can never set it; `api/v1.update_doc` deletes `"flags"` from the
payload as well. So the exemption cannot be claimed from outside the server.

**The guard refuses gaining the role, not holding it.** It returns early when the
user already has the row in `tabHas Role`. Without that, every ordinary re-save
of a live joiner account — disabling it, Frappe's own Role Profile sync, our
`module_access` and `field_app_device` hooks — would throw, and we would have
replaced one lockout with another.

**ALV-319:** a `User.on_update` handler in `auth.py` does
`frappe.cache().hdel(_JOINER_CACHE, user)`. `auth.py` owns the key, so the clear
belongs there. `on_update` fires on insert as well as save
(`document.py: run_post_save_methods`, `_action == "save"`).

## Files I will change

| File | Change | Hot file? |
|---|---|---|
| `alvoraa_portal/alvoraa_portal/joiner_invite.py` | two guard functions; the invite flag; the role description in `make_role` | listed as "shared API" style, but no signature changes |
| `alvoraa_portal/alvoraa_portal/auth.py` | the cache-forget handler; the false comment replaced | the joiner gate itself |
| `alvoraa_portal/alvoraa_portal/hooks.py` | three `doc_events` entries, one `after_migrate` entry | **yes** — appending only, never rewriting a block |
| `alvoraa_portal/alvoraa_portal/tests/test_joiner_079.py` | the new tests, with 079's own | shared test file |
| `alvoraa_portal/alvoraa_portal/tests/test_portal_security_010.py` | one ceiling row: `auth.py` at 0 | **yes** |

`hooks.py` needs one careful edit: `"User"` already has `"validate"` as a single
string (`ai_leads.guards.validate_user`). It becomes a two-item list with that
entry kept first. Replacing the key instead of extending it would silently
switch off slice 043's AI mailbox guard.

`after_migrate` gets `joiner_invite.make_role`, because AC-4's description must
reach sites that already ran the 079 patch — a patch never runs twice. `make_role`
is already safe to run twice and already runs from `after_install`.

## Parallel-work check

- `git fetch origin` run. **The shared main checkout is 406 commits behind
  `origin/dev`** and holds another session's uncommitted edits across ~40 files
  (agents, context, payroll, portal CSS, `auth.py` and `hooks.py` among them —
  `auth.py` and `hooks.py` show as `MM`, staged *and* unstaged). I have not
  touched the main checkout and will not stage anything there.
- I branched `slice/alv-318` from `origin/dev` in
  `.claude/worktrees/alv-318`. All editing and committing happens there.
- Incoming on `origin/dev` that matters to me: `bd50f75a` / `e730e176`
  (ALV-317, Frappe Learning pinning — build only), and the slice 082 series
  ending `981d8690` (joiner-to-employee, `test_joiner_to_employee_082.py`). The
  last change to `auth.py` / `joiner_invite.py` / `hooks.py` is `a53b333a`
  (ALV-312) and before it `dcf74d58` (ALV-292, "the joiner role must reach a site
  built from scratch"), which is the commit that put `make_role` in
  `after_install`. Nothing in flight edits the lines I will edit.
- `.claude/work-in-progress.md` did not exist on this machine when I started, so
  there was no board to read; I created it and added my row. **Open question for
  Surbhi: is anyone else in `auth.py`, `joiner_invite.py` or `hooks.py` today?**
  The main checkout's uncommitted `auth.py` and `hooks.py` edits say somebody may
  be. **Answered in part while I was testing:** another session added a row for
  "ALV-266 rebase test" on `slice/alv-266-rebased`, which names `hooks.py`. The
  plan is a **split** — they are in the `employee_field_rights` entries, I am in
  `doc_events["User"]`, a new `doc_events["Role Profile"]` key and the end of
  `after_migrate`.
- Pin tests: every one of AC-1 to AC-6 gets a named test in
  `test_joiner_079.py`, so a bad merge that drops the guard fails CI rather than
  locking out a tenant again.
- `hrlocal-bench` runs a background worker against the shared test database
  (ALV-268 phantom `QueryDeadlockError`). I will build my own container and my
  own database and will not run tests against `test_site` in the shared bench.

## Functional impact

**Cross-module.** `alvoraa_goals`, `alvox_compensation`, `hrms`, `erpnext`: none
of them know this role exists. Grep of every caller of what I touch:

- `JOINER_ROLE` — defined twice on purpose (`auth.py`, `joiner_invite.py`), read
  in `joiner_invite._role`, `auth.home_page_for`, `auth._is_a_joiner` and the two
  test files. I change no signature.
- `make_role` — called from `after_install` (hooks.py) and
  `patches/v1_0/joiner_sign_in_replaces_the_link._make_the_role`; asserted by
  `test_joiner_079.TestTheRoleReachesANewSite`. I add a third caller
  (`after_migrate`) and do not change its signature or its two existing branches.
- `make_sign_in` — called from the joiner UI and from `test_joiner_079`,
  `test_joiner_078`, `test_joiner_to_employee_082` and `fixtures_079`. One line
  added inside it.
- `_is_a_joiner` / `_JOINER_CACHE` — read only inside `auth.py`; the comment in
  `joiner_invite.end_the_sign_in` cites the comment I am deleting, so that
  comment is rewritten to stand on its own reason.
- `User.validate` / `User.on_update` hook lists — every existing handler is kept.

**Personas.**

| | Change |
|---|---|
| **Employee** | None, unless somebody tries to give them this role, which now fails with a sentence instead of locking them out. A member of staff who already holds it (there should be none after Surbhi's recovery) keeps it; the guard refuses gaining, not holding. |
| **HR Manager** | `make_sign_in` is unchanged. If HR has been using a Role Profile that contains the role, that profile's next save is refused and tells them to take the role out. |
| **CXO** | None. |
| **System Manager** | Can no longer add the role on the user form or via the API. The `Has Role` direct-insert door above remains theirs. |

**HRMS domain.** Leaves, attendance, payroll, appraisals and org structure are
untouched. No Employee record is involved: a joiner has none by design.

## The three things settled before any code

**Race conditions.**
- *Two saves at once on one user.* The guard reads `tabHas Role` to decide
  "already had it". Two concurrent grants could both see "no" and both refuse, or
  a grant could land between the read and the write. The worst outcome is a role
  granted by somebody who already holds `write` on `User`; no lock is worth
  buying for that, and the profile door — the one that caused the incident — is
  closed before any user save happens.
- *A cache read between the invalidation and the commit.* `on_update` runs before
  commit, so a concurrent request from the same user could read the old roles and
  re-cache "yes" after my `hdel`. One request wide, and any later save of that
  user clears it again. I considered `frappe.db.after_commit.add` (it exists,
  `database.py:130`), and rejected it: it does not run inside a test transaction,
  so the fix would stop being provable, and buying a narrower window with an
  untestable fix is the wrong trade for a one-key hash entry. The window is named
  in the code comment rather than hidden.
- *The scheduler and a person at once.* `joiner_housekeeping.expire_the_dead_sign_ins`
  calls `end_the_sign_in`, which writes with `frappe.db.delete` and fires no
  `on_update`. That is unchanged, and the comment there is rewritten to say why a
  cached "yes" is still the answer we want for a closed account.

**Edge cases.**
- *None:* a `Role Profile` with no rows; a `User` with no roles. Both return early.
- *One:* the first joiner on a site where the role does not exist — `_role()`
  already refuses with words, and the guards never fire on a role nobody holds.
- *Many:* a profile with every role in it; a user on several profiles
  (`populate_role_profile_roles` unions them). The guard looks at the resulting
  `roles` table, so it catches the union.
- *Administrator and Guest.* Frappe strips Guest's roles and clears
  `role_profiles` for standard users. The guard still refuses rather than
  special-casing them; the gate in `auth.py` already skips both.
- *A user renamed.* The cache key is the login id, so a rename leaves an entry
  under a name no user holds. Any user later created with that name fires
  `on_update` on insert and clears it. No handling added.
- *An existing joiner account being disabled, expired, declined or hired.* All go
  through `end_the_sign_in`, which removes the role with `frappe.db.delete` and
  saves no document, so no guard and no hook fires. Unchanged on purpose.
- *A tenant whose profile already holds the role.* Its next save fails. See the
  risk below.

**State transitions.** Neither `Role Profile` nor `User` is submittable; there are
no workflow states to break. The submission's own states (Invited → Sent →
Hired / Declined / Cancelled / Expired) are not touched. The transition 079 forgot
and 318 found is the one that has no state at all: *a user acquiring the role
from somewhere other than the invite*. That is now refused.

## Non-functional verdict

| Dimension | Verdict | Why |
|---|---|---|
| Performance | **neutral / one query on a rare path** | The guards add nothing to a request. On a `User` save that actually carries the role, one `frappe.db.exists` on `tabHas Role` (indexed on `parent`). Zero extra queries on a save that does not carry the role, and zero on a `Role Profile` save. The gate's hot path — a member of staff's every request — is untouched: still one cache read, no database read. |
| Security | **improves** | The role that confines an account to one page can no longer be handed to a crowd, and removing it now actually releases the account. No new `ignore_permissions`; a ceiling row of 0 is added for `auth.py` so a future one has to be argued. |
| Reliability | **improves** | The refusal is a `frappe.throw` with a next step, not a silent lockout. The cache-forget is wrapped so a Redis blip costs the invalidation, not the user's save. |
| Scalability | **improves** | The fault scaled with headcount — a fifty-person profile was a fifty-person lockout. That is gone. |
| Maintainability | **improves** | A comment that was known to be false is replaced by what happened, with the ticket number. The guards sit in the module that owns the role. |
| Data integrity | **improves** | Removing a permission now takes effect, which is the whole of ALV-319. |
| Compliance / privacy | **neutral** | No personal data is read, written, logged or exposed. The refusal names the role and never the person. No log line gains a name, an id or a contact. |

## Risks, and the one that needs Surbhi

1. **A tenant that already has the role on a Role Profile will find that profile
   unsaveable** until somebody takes the role out of it — and the message says
   exactly that. I cannot count which tenants are in that state: dev and
   production are out of bounds for me, and the local bench's sites are not
   tenants. **This needs a read-only count on dev and production before release,
   and it is Surbhi's to run.** The query is one line and is in the notes.
2. **The recovery order matters and the refusal does not teach it.** Taking the
   role off the *user* first does nothing: Frappe re-applies the profile's roles
   on save and hands it straight back. The profile must be cleared first. That
   order is written into the refusal message on the user guard, so the next
   person reads it at the moment it matters, and into the notes as a runbook. No
   script: a script for a two-step manual fix nobody can run unattended is the
   kind of helper the no-over-engineering rule bans.
3. **One custom field on a core Frappe doctype** (`Role`) for AC-4. If Surbhi
   would rather not customise `Role`, AC-4 can be dropped and the rest stands.

## Strategy, in order

1. `joiner_invite.py` — the two guards, the invite flag in `make_sign_in`, the
   description in `make_role`, and the rewritten comment in `end_the_sign_in`.
2. `auth.py` — the cache-forget handler, and the false comment replaced.
3. `hooks.py` — three `doc_events` entries and one `after_migrate` entry,
   appended, never rewriting a block.
4. Tests in `test_joiner_079.py`, one per AC, plus the ceiling row in
   `test_portal_security_010.py`.
5. Build my own container and site, run `test_joiner_078`, `test_joiner_079`,
   `test_joiner_to_employee_082`, `test_portal_security_010` and the whole
   `alvoraa_portal` suite, writing the output to a file and reading **every**
   batch summary from it.
6. Every static gate from `ci.yml`'s Lint job.
7. Commit in the worktree, staging by path. **No push, no deploy.**
