# ALV-302 review: commit ca987a2c

**Verdict: SHIP WITH FIXES. The code opens no read door for a plain sync account, but HR User must NOT come off DTC's account yet, because the bridge's Shift Type update would then fail with no visible error.**

`SHIP WITH FIXES` means ready to present to Surbhi after the fixes. It is not permission to deploy.

**How this was checked.** I ran the code, over real HTTP with API keys, on the throwaway site `test302` (fresh install, this worktree mounted). I did not touch any server, and no live DTC data was available.

**Process gap.** This slice has no impact analysis, spec or security requirements. I reviewed against the ticket brief only, so walking each AC, `SEC`, `PRIV` and `OPS` item is **unreviewable**.

## Findings

### 1. P1, before the DTC cut-over: taking HR User off stops the bridge moving the shift marker

- **Input:** DTC's account holds only `Biometric Sync`, and the bridge sends its `PUT /api/resource/Shift Type/<name>` with `last_sync_of_checkin`.
- **What happens:** the server answers 403. **Proven** on `test302`. Nothing in this commit grants Shift Type, and `hooks.py` has no Shift Type permission hook.
- **Why it is wrong:** attendance is only worked out for shifts that ended before that marker. If a shift has `auto_update_last_sync = 0`, nothing else moves the marker, so punches keep landing and attendance quietly stops. Nobody would see it until payroll.
- **What applies to DTC:** on 23 Sep DTC's shifts had `auto_update_last_sync = 0` and the bridge was moving the marker (slice 041 notes). A 16 Oct note says the scheduler moves it. I could not check which is true today.

The obvious fix is also unsafe. I added a read and write row on Shift Type for the role, and the same key then did all of this (**Proven**, each returned 200):

| PUT | Result |
|---|---|
| The marker, to a normal time | Saved |
| The marker, to the year 2099 | Saved |
| `working_hours_threshold_for_absent`, to 1.5 | Saved |

That threshold decides Absent, and so decides pay.

**Decision for Surbhi:**

| Option | Cost |
|---|---|
| **A. Recommended:** bring across the fence already built on `slice/041-biometric-sync-user` (`guard_shift_type_change`, `shift_type_has_permission`), then add the row | A little more code, already written and tested on that branch, but it has never landed and will need a rebase |
| B. Tick `auto_update_last_sync` on DTC's shifts | No code, but the marker moves even when a shop's line is down, so staff can be marked Absent before their punches arrive |
| C. Leave HR User on | The key keeps reading all personal data, which is what this ticket set out to end |

**Risk if it waits:** none, as long as HR User stays on. **Owner:** Surbhi for the choice, `hrms-fullstack-engineer` for the fix.

**Check first on DTC, read-only:** each Shift Type's `auto_update_last_sync`, `last_sync_of_checkin` and `modified_by`. Then use the four-step list in slice 041's `04-when-dtc-can-untick-hr-user.md`. Its condition 4 is exactly this.

### 2. P2, Major: anyone who merely also holds the role can file and back-date punches, for anyone

- **Input:** a login with `Employee` + `Biometric Sync`, and its own Employee record, calls `add_log_based_on_employee_field`.
- **What happens (Proven over HTTP):**
  - For a colleague, asking for 5 days ago: 200, stored at that exact time.
  - For themselves, asking for 5 days ago: 200, stored at that exact time.
- **Why it is wrong:** the brief says a sync account holding *only* this role. The code checks `SYNC_ROLE in frappe.get_roles(...)` at `field_app_access.py:41` and `:91`. One wrong tick, or a role profile, lets a member of staff write their own attendance, and so their own pay. Read stays refused for this login (403).
- **Smallest fix:** treat the login as a machine only if its roles minus `All`, `Guest` and `Desk User` are exactly `{Biometric Sync}` and it has no Employee record. Use that check in both places, and add a test for this login. Slice 041 made the same choice for its fence.
- **Check first:** the other roles on DTC's role profile. If it carries any besides this one, the fix would refuse that account. **Not checked.**

### 3. P2, Major: "reads nothing" is not quite true, the punch endpoint answers with a name

The commit message says the role cannot read. These doors still give something back to the sync key (**Proven**):

| Door | What comes back |
|---|---|
| Reply to `add_log_based_on_employee_field`, or to `POST /api/resource/Employee Checkin` | The whole punch: employee ID, **full name**, shift, times |
| `employee_fieldname=name` with any employee ID | That person's full name, and it files a punch on them |
| `employee_fieldname=personal_email` with an exact address | Which employee owns it. It works for any Employee field, but only on an exact match (a `like` value found nothing) |
| Sending a duplicate punch | The error names the person and links the existing punch, so it confirms a punch exists at that exact second |

- **Failure scenario:** a leaked key, walking IDs or device numbers, can list staff names and test guesses such as a phone number. Each hit also leaves a false punch.
- **How bad:** far less than today, when the key reads everything. It returns names and yes/no answers, not stored personal data. This is upstream `hrms` code and was not made worse here.
- **Decision for Surbhi:** accept in writing, or limit `employee_fieldname` to `attendance_device_id` for this role. I recommend the limit if the fix stays small. The reply itself probably has to stay, since I recall the bridge reading `name` from it **[ASSUMPTION, not read from DTC's copy]**.

Also correct the commit message wording, and the test name `test_cannot_read_a_punch_it_filed_itself`. That test checks `has_permission` only, not the reply.

### 4. P3, Minor: the machine's time has no limits

The key filed punches dated 2001, 2003 and 2099, and all were stored as sent (**Proven**). A 2099 punch landed with no shift. Today's HR User key can do the same, so this is not new, but this role exists only for machines. A limit of "not more than 15 minutes in the future", as in slice 041's fence, would catch a broken clock. Back-dating has to stay, or the backlog fails. Ship and track it. **Owner:** `hrms-fullstack-engineer`.

## Your questions

| Question | Answer | Label |
|---|---|---|
| Guest files a punch? | No, 403 | Proven |
| Employee files for a colleague? | No, 403 | Proven |
| Employee files their own, back-dated? | Files, but stored at Now. Unchanged by this commit | Proven |
| Manager files for a direct report, back-dated? | Files, but stored at Now. Unchanged, this branch was already there | Proven |
| Field-app token? | Its code sets `time: now()` itself and inserts with `ignore_permissions` (`field_checkin.py:670`), so this hook cannot change its time. Not run through a device | Read, not run |
| Reached by a user who also holds the role? | **Yes, finding 2** | Proven |
| Reached on update? | No. `before_insert` runs only inside `insert` (`document.py:480`). PUT on a saved punch, including its own, gives 403 | Proven |
| Can a client set the flag itself? | No. Staff sent `flags` in the POST and still got Now | Proven |
| `__islocal` trick on an existing name? | Makes a new record. The old one is not overwritten or returned | Proven (reply); no overwrite inferred |
| Read doors, plain row | REST by name and list, `frappe.client` get, get_value, get_list and get_count, report view, count, export, form load, print view, PDF, link search, Shift Attendance report, private file URL: all 403. File list: empty | Proven |
| Read doors, if a tenant's row also says read | By name, form load, print and file URL: 403. List, count, link search: empty. `get_value` was 200 over HTTP (I did not print the body); the test proves it comes back empty | Proven |
| Change doors | PUT, DELETE, share, `run_doc_method`, `bulk_fetch_shift`: all 403 | Proven |
| Data Import? | The role's row has no `import`, and Data Import checks that first (`data_import.py:83`). Roles that do have it can already write `time` | Inferred |
| Web-portal check-ins? | No other portal code in this app creates a punch besides `field_checkin.py:670` (grep). Staff punches stay at Now | Inferred, with the test |
| Auto attendance? | Nothing new. The stored punch is the same as under HR User. A late punch on a day that already has attendance gets skipped, as it does today | Inferred |
| `ptype` right for this version? | Yes. Frappe 16.33.1: `frappe.call(method, doc=doc, ptype=ptype, user=user, debug=debug)` at `permissions.py:495`. The hook only ever narrows; the tenant's role row must still grant `create` | Proven |
| Why the time hook works | `document.py:477-483`: check create, then `before_insert`, then the permlevel reset, which honours this flag at `base_document.py:1492` | Proven |
| Three sibling hooks left alone | Safe. None reads the value (`field_app_access.py:163-184`). `slice/041` renames them, so expect a conflict if it lands | Proven |
| Other callers of `checkin_has_permission` | None in Python except Frappe through `hooks.py`, plus the re-export in `field_checkin.py` | Proven |

## Do the tests pass for the right reasons?

**Yes.** 18 of 18 pass on `test302`. I then broke the code in memory, with nothing changed on disk, and re-ran them:

| Break | Tests that failed |
|---|---|
| Old hook, or the parameter misnamed | 4, including filing the punch |
| No `is_new()` | 2, changing a saved punch |
| No role check in the hook | 2, filing for a colleague |
| Role allowed every operation | 6, read, photo and change |
| `before_insert` does nothing | 2, the kept time |
| Time kept for everyone | 2, staff's own time |

One difference from the docstring: "let the role through for every operation" fails the photo test only under the read row, not under both.

**Gaps:** no test for finding 2, nothing on the endpoint's reply (finding 3), nothing on Shift Type (finding 1). The tests call the functions directly rather than over HTTP. My HTTP run covered that once, but it is not repeatable from the repo.

## Seven dimensions

No impact analysis exists to compare against (**unreviewable**). My reading:

| Dimension | Before (HR User on) | After, with HR User off |
|---|---|---|
| Security and privacy | Key reads all personal data | Much better, apart from findings 2 and 3 |
| Reliability | Works | **Worse until finding 1 is settled** |
| Data integrity | Unchanged | A new risk if finding 2 is not fixed |
| Performance | - | One cached role lookup per insert. Not measured |
| Scalability | - | Neutral [reasoned] |
| Maintainability | - | Two sync roles now exist in the code's history: this one and slice 041's `Alvoraa Attendance Sync`. Someone should decide which survives |

## What to delete

**Nothing, if finding 2 is fixed.** Otherwise the time hook is not needed. A tenant permission row for this role, `permlevel 1, write 1, read 0`, kept the machine's time with the hook switched off, and still refused write and read on a punch (**Proven** in a rolled-back transaction, row written directly, not saved through the Role Permissions screen). That is a cheaper rung, but it cannot limit itself to machine-only accounts, so the fix for finding 2 is what makes the hook earn its place. If it stays as it is, the hook costs code on a shared doctype for no gain over the row.

The rest is small and in proportion: no new DocType, no settings, no new `ignore_permissions`.

## What was done well

- The time reset was found and pinned. Letting the role through alone would have filed every late punch at its arrival time, with no error.
- Every test runs under two shapes of the permission row, so the hook is proven to hold even if a tenant's row says read.
- The test file lists how to break the code and what should fail. I tried it, and it is accurate apart from the one note above.

## Not checked

- **DTC itself:** its permission row, role profile, Shift Type settings and bridge copy. The tool's behaviour comes from slice 041's reading of the public repo.
- **A DTC-style plan profile on the account.** The test users have theirs removed. `has_permission` shows no module check, so I expect no effect [inferred].
- **Other test suites.** I ran only this module. The other field-app and security suites were not re-run by me; logs from an earlier run sit on the `hrlocal-302-sites` volume, and I did not read them.
- **A real field-app device, and a real bridge.**
- **Report coverage.** I tried one report door (Shift Attendance), not every report.
- **Rebase.** `origin/dev` moved past this branch's base while I reviewed. Rebase and re-run this module before any push.

## Subtract pass

I removed style notes, a performance remark about `_viewer` (not changed here) and a File-list note (not opened by this commit). Everything left affects a decision.
