# ALV-318 and ALV-319 — implementation notes

Built on `slice/alv-318` in `.claude/worktrees/alv-318`, off `origin/dev` at
`bd50f75a`. **Nothing pushed, nothing deployed, no tenant touched.**

## What I built, file by file

| File | What changed | Mechanism | Why that one |
|---|---|---|---|
| `alvoraa_portal/alvoraa_portal/joiner_invite.py` | `keep_the_joiner_role_out_of_profiles` and `keep_the_joiner_role_to_the_invite`; `INVITE_FLAG` set in `make_sign_in`; `ROLE_PURPOSE_FIELD` and `ROLE_PURPOSE` written by `make_role`; the stale cross-reference comment in `end_the_sign_in` rewritten | **extend** (two `validate` handlers) + **configure** (one Custom Field) | The module already owns the role, `make_role` and the invite path. One module, one story |
| `alvoraa_portal/alvoraa_portal/auth.py` | the false `_JOINER_CACHE` comment replaced with what happened; `forget_whether_they_are_a_joiner` added | **extend** (one `on_update` handler) | `auth.py` owns the cache key, so the clear belongs beside it |
| `alvoraa_portal/alvoraa_portal/hooks.py` | `User.validate` becomes a list (the 043 guard kept first) with the new guard; `auth.forget_whether_they_are_a_joiner` appended to `User.on_update`; a new `Role Profile.validate`; `joiner_invite.make_role` appended to `after_migrate` | **configure** | Appended only, never rewriting a block, per the hot-file rule |
| `alvoraa_portal/alvoraa_portal/tests/test_joiner_079.py` | two new classes, 16 tests | — | The tests travel with the code they prove, in the suite that owns the surface |
| `alvoraa_portal/alvoraa_portal/tests/test_portal_security_010.py` | one ceiling row: `auth.py` at **0** | — | Pins "no bypass in the file every request passes through" |
| `alvoraa_portal/alvoraa_portal/tests/test_joiner_to_employee_082.py` | the fixture builds its joiner login with the invite flag set | — | **Another slice's test file, and the only one outside my scope I touched.** The guard refused its fixture, which built a joiner login directly. See `04-test-output.md` |

## The mechanism for the refusal, and why

**Two `doc_events` handlers on `validate`, and nothing else.**

`validate` is the single choke point every door passes through. Verified in the
installed Frappe source, v16.33.1, not from memory:

| Door | How it reaches `User.validate` |
|---|---|
| Desk user form | `frappe.client.save` → `doc.save()` |
| `PUT /api/resource/User/<name>` | `frappe/api/v1.py: update_doc` → `doc.save()` |
| `PUT /api/resource/Has Role/<name>` | `update_doc` then `frappe.get_doc(parenttype, parent).save()` |
| `frappe.client.insert` of a `Has Role` row | `client.insert_doc` → `parent.append(...); parent.save()` |
| `frappe.client.set_value` on a `Has Role` row | `client.set_value` → parent `doc.save()` |
| Data Import | `doc.save()`, and the guard does **not** skip itself on `flags.in_import` |
| `user.add_roles(...)` from code | `append_roles` → `self.save()` |
| **A Role Profile edit — the incident** | `RoleProfile.on_update` → `update_all_users` → `user.save()` per user |

Rungs rejected, in short: Frappe ships no "this role may not be granted" switch;
`Role.disabled` would break the invite path too, because `User.remove_disabled_roles`
strips a disabled role from every user on save; a permission row cannot express
it and 079 requires this role to appear in no permission row at all; a Server
Script would live in each site's database, invisible to CI and to this repository.
The long form is in `00-impact-analysis.md`.

**How `make_sign_in` keeps working.** It sets `user.flags["alvoraa_joiner_invite"]
= True` before `user.insert()`. `"flags"` is in Frappe's `RESERVED_KEYWORDS`
(`frappe/model/base_document.py`), so `BaseDocument.update` skips it and no
request payload can set it; `api/v1.py: update_doc` deletes `"flags"` from the
payload as well. There is a test that posts the flag and is still refused.

**The guard refuses gaining the role, not holding it.** It returns early when the
`Has Role` row already exists. Without that, every ordinary re-save of a live
joiner account — HR disabling the login, Frappe's own Role Profile sync, our
`module_access`, `field_app_device` and `own_record_permission` hooks — would
throw, and we would have replaced one lockout with another. There is a test for
that too.

## The AC list

| AC | How it is satisfied | Test |
|---|---|---|
| AC-1 A Role Profile cannot save with the role | `Role Profile.validate` guard; the message names the role and says a profile hands it to everybody at once | `test_a_role_profile_cannot_carry_it`, `test_it_cannot_be_added_to_a_profile_that_already_exists`, `test_an_ordinary_role_profile_still_saves` |
| AC-2 A User cannot gain it except through the invite | `User.validate` guard, proved at the user form, through `frappe.client`, and under `flags.in_import` | `test_a_member_of_staff_cannot_be_given_it_on_their_user_record`, `test_the_rest_api_child_write_door_is_refused`, `test_a_data_import_cannot_slip_it_in`, `test_the_invite_exemption_cannot_be_claimed_from_outside` |
| AC-3 `make_sign_in` still works | the document flag | `test_hr_can_still_make_a_sign_in`, `test_a_live_joiner_account_can_still_be_saved`, and the whole existing 079 suite, which invites a joiner in almost every test |
| AC-4 The Role record says what it is for | Custom Field `alvoraa_role_purpose` on `Role`, written by `make_role`, which now also runs on `after_migrate` | `test_the_role_says_what_it_is_for`, `test_the_guards_are_registered_and_the_043_one_survived` |
| AC-5 A role change drops the cached answer | `User.on_update` → `frappe.cache().hdel` | `test_the_cached_yes_goes_when_the_roles_change`, `test_the_gate_then_lets_them_through`, `test_a_name_with_no_cached_answer_is_harmless` |
| AC-6 The false comment is gone | the comment block is replaced with the incident | `test_the_comment_that_was_wrong_is_gone` (a static read of the module source) |

Nothing on the AC list is unsatisfied.

## The seven dimensions, against the code I actually wrote

| Dimension | Before | After | Verdict |
|---|---|---|---|
| Performance | the gate: one cache read per request | unchanged for everybody; **one** `frappe.db.exists` on `tabHas Role` (indexed on `parent`) only on a `User` save that actually carries the role; zero extra queries otherwise; zero on a `Role Profile` save that does not carry it | **neutral** |
| Security | the one-page role could be handed to a crowd; removing it did not release the account | both closed; no new `ignore_permissions` (counted: `auth.py` 0, `joiner_invite.py` still 3, pinned in `test_portal_security_010`) | **improves** |
| Reliability | a silent lockout with nothing on screen | a `frappe.throw` naming the role, the reason and the next step, in the right order; the cache clear is wrapped so Redis failing costs the invalidation and not the save | **improves** |
| Scalability | the fault scaled with headcount — fifty on a profile was fifty lockouts | gone at the profile | **improves** |
| Maintainability | a comment that was known to be false | replaced with the incident and the ticket; the guards sit in the module that owns the role; the hot-file edits are additive | **improves** |
| Data integrity | removing a permission did not take effect | it does | **improves** |
| Compliance / privacy | — | no personal data read, written, logged or exposed; the refusals name the role, never the person; no log line gains a name, id or contact | **neutral** |

## NFR notes

- **Query counts.** Role Profile guard: 0 queries in the common case; the refusal
  itself is 0. User guard: 0 queries unless the role is in the submitted roles
  table, then 1 `exists` on `Has Role`. The cache clear is one Redis `HDEL`.
- **Indexes added:** none. `tabHas Role.parent` is already indexed by Frappe.
- **Background jobs:** none added.
- **Permission enforcement points:** `Role Profile.validate` and `User.validate`,
  both server side, reached by every save whatever the client.
- **`ignore_permissions` declared:** **none added.** `auth.py` is 0 and now pinned
  at 0; `joiner_invite.py` stays at 3, the three 079 already argued. Verified with
  the same AST method `test_portal_security_010` uses.
- **Sensitive fields touched:** none.
- **Fallbacks:** the cache clear swallows a Redis failure into
  `frappe.log_error` with no user detail; the gate then reads the roles from the
  database, which is correct, only slower.

## The door list, run

Per `.claude/context/data-doors.md`. This change does not widen what anybody can
read; it narrows who can be granted one role. The doors that matter here are the
write doors on `User` and `Role Profile`:

| Door | Result |
|---|---|
| `/api/resource/User` PUT | refused (test) |
| `/api/resource/Has Role` PUT, and `frappe.client.insert` / `set_value` on a child row | refused (test) |
| `/api/resource/Has Role` **POST** | **not closed.** See below |
| Desk user form | refused (test) |
| Data Import | refused (test) |
| `user.add_roles()` from code | refused (same `validate`) |
| Role Profile, Desk or API | refused (test) |
| Raw SQL into `tabHas Role` | out of reach of any hook |

**What I did not test.** I could not test as a plain staff login or an HR Manager
through real HTTP: granting any role needs `write` on `User`, which neither holds,
so there is no path for them to test. Every test runs as Administrator — the one
persona that can actually reach these doors. No browser run: nothing on a screen
changed except two refusal messages.

## Known gaps and shortcuts

1. **`POST /api/resource/Has Role` is still open** — *intentional trade-off.*
   `frappe/api/v1.py: create_doc` does `frappe.new_doc(doctype, **data).insert()`,
   and `Document.insert` has no `istable` guard on v16.33.1, so a child row can be
   inserted without re-saving the parent. Permission is checked against the parent
   doctype (`document.py:419`), so it needs `write` on `User` — System Manager. The
   same person is refused at the user form. Closing it would be a third guard, on
   `Has Role.validate`, which fires for every child row of every user save and
   would need its own "already had it" read. **If Surbhi wants it closed, say so
   and it is about ten lines.**
2. **A tenant whose Role Profile already holds the role will find that profile
   unsaveable** — *dangerous debt, and it is escalated here rather than noted.*
   The message tells them to take the role out, which is the right fix, but
   nobody has counted which tenants are in that state. **This needs a read-only
   count on dev and production before any release, and only Surbhi can run it:**
   ```
   bench --site <site> execute frappe.client.get_list --kwargs \
     '{"doctype":"Has Role","filters":{"parenttype":"Role Profile","role":"Alvoraa Joiner"},"fields":["parent"],"ignore_permissions":true}'
   ```
   amata.dev was recovered by hand, so it should come back empty. Any other row
   is a tenant that must be cleaned before this ships.
3. **One Custom Field on a core Frappe doctype** (`Role`) — *acceptable
   simplification.* `Role` ships no description field, so there is nowhere else to
   put the sentence AC-4 asks for. If Surbhi would rather not customise `Role`,
   AC-4 can be dropped and everything else stands.
4. **The invalidation runs before commit** — *intentional trade-off.* A request
   from the same person landing between the `hdel` and the commit can re-cache
   "yes". One request wide, cleared by that account's next save.
   `frappe.db.after_commit` would shut it but does not run inside a test
   transaction, so the fix would stop being provable. Written into the function's
   docstring rather than hidden.
5. **`end_the_sign_in` still leaves a cached "yes"** — *intentional, unchanged.*
   That path closes an account: disabled, sessions cleared, password destroyed. A
   cached "yes" there can only refuse an account that must be refused. The comment
   no longer rests on the argument ALV-319 disproved.
6. **No helper and no runbook script for the recovery order** — *deliberate.* The
   order (profile first, then the account) is in the refusal message the person
   reads at the moment it matters, and in `00-impact-analysis.md`. A script for a
   two-step manual fix is the kind of helper the no-over-engineering rule bans.

## The subtract pass

Removed before handing off:

- A third guard on `Has Role.validate`. It only adds the System-Manager-only POST
  door above, at the cost of a hook firing on every child row of every user save.
- `frappe.db.after_commit` for the cache clear — see gap 4.
- A separate patch file for AC-4. One line in `after_migrate` reaches every site,
  and `make_role` was already safe to run twice.
- Clearing the cache inside `end_the_sign_in`, which would have needed a new
  import for no behaviour change.
- A `_the_purpose_field()` helper with one caller. It is three lines inside
  `make_role` instead.

## What else moved while I worked

- The shared main checkout `C:/Surbhi-Git/hr-app` is **406 commits behind
  `origin/dev`** and holds another session's uncommitted edits in roughly forty
  files, including `auth.py` and `hooks.py` (both `MM` — staged and unstaged). I
  did not touch, stage or revert anything there. I branched off `origin/dev`
  instead, so none of that work is in my diff and none of it was lost.
- Incoming on `origin/dev` while I worked: nothing. `origin/dev` was at
  `bd50f75a` when I branched and at `bd50f75a` when I committed.
- No conflicts, so nothing to prove about anyone's lines surviving.
- `.claude/work-in-progress.md` did not exist; I created it (git-ignored) with my
  own row. Other sessions' rows are missing because they were never recorded.
- **While I was testing, another session added a row to the board: "ALV-266
  rebase test", on `slice/alv-266-rebased`, and it names `hooks.py`.** We are both
  in that file. The plan is a **split**: they are in the
  `employee_field_rights` entries, I am in `doc_events["User"]`, a new
  `doc_events["Role Profile"]` key and the end of `after_migrate`. Different
  blocks, so a rebase should not conflict — but `hooks.py` is a hot file and
  whoever lands second must read the other's diff rather than resolve by hand.
  **Worth telling that session, because neither of us has landed yet.**
- `git worktree list` shows **about 150 worktrees**, many from July and August,
  several on branches whose slices shipped long ago. None is mine to delete.
  Worth a clean-up session of its own.

## Commands I ran, and what they said

**My own stack, never the shared bench.** `hrlocal-bench` binds the stale main
checkout and runs a background worker against the shared test database (ALV-268),
so I built `alv318-mariadb` (mariadb:10.8, utf8mb4), `alv318-redis` and
`alv318-bench` from the same image the local bench uses, bound to **my worktree**,
and created my own `test_site` with frappe, erpnext, hrms, alvoraa_portal and
alvoraa_goals. Its own database and its own Redis, so neither the shared hook
cache nor the shared database is touched.

Results are in `04-test-output.md` beside this file, with every batch summary read
from the file rather than from a tail.

## Still needing Surbhi

1. The read-only count in gap 2, on dev and production, before this ships.
2. Whether to close the `Has Role` POST door (gap 1).
3. Whether the Custom Field on `Role` is acceptable (gap 3).
4. Is anyone else working in `auth.py`, `joiner_invite.py` or `hooks.py` today?
   The main checkout's uncommitted edits in two of those files suggest somebody is.
