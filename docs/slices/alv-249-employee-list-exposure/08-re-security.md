# ALV-249 · Security re-check after round 2

Re-checked 31 Oct 2026 by the security and privacy engineer, on branch
`slice/alv-249-employee-list-exposure` (`git diff origin/dev...HEAD`, 6 commits, head
`eafd6375`). I wrote the first review (07-security.md). I did not write or specify any of
the code.

**How I tested.** In the engineer's container `hrlocal-249`, site `test249`. I built real
web requests in code (query string, form POST, multipart, JSON body), ran Frappe's own
request parser and our new guard on them, then sent them through Frappe's real router
(`/api/method`, `/api/v1`, `/api/v2`, `/api/resource`, and `cmd` to "/"). The caller was
the staff login `plain@l063.test` (roles Employee, Desk User; has its own-record row;
191 employees on the site). Every call was rolled back. **No socket was opened**: there is
no web server in that container, and logging in would write a session. So the steps
before the router (nginx, login, cookie) were not exercised. I changed no source and
touched nothing on dev or production.

---

## Bad news first

1. **Production is still open today.** Doors 1 and 2 from 07 (the extra word
   `ignore_user_permissions`) work on every tenant until this branch is deployed. Nothing
   below changes that. Deploy is the fix.
2. **New, P2 Major, not caused by this branch: any login can see which days a colleague
   has no attendance record.** Frappe HR's `get_unmarked_days`
   (`hrms/hr/doctype/attendance/attendance.py:429-467`, whitelisted) reads with
   `frappe.get_all`, which skips all permission checks. *Verified by running it:* the staff
   login asked for HR-EMP-00003, 1 Sep to 31 Oct 2026, and got 4 dates back. It also gives
   away the colleague's joining or leaving date (the list is cut to those dates, `:432-437`).
   The guard cannot help: there is no word to drop. Small fix (rung 4): one
   `override_whitelisted_methods` entry in our `hooks.py` that checks
   `frappe.has_permission("Employee", doc=employee)` and then calls the original. Own
   ticket.
3. **Managers now see their whole tree, including Salary Slips with bank account, gross
   and net pay** (06, D-2). Surbhi accepted this on 31 Oct 2026, in 06. That is
   recorded. I still flag it because pay and bank details are the most sensitive data in
   the product, and counsel question C4 (purpose limitation) is open.
4. **A manager who also holds Employee Self Service can change a team member's phone,
   address or passport number.** *Verified by running it* (rolled back): I gave manager
   HR-EMP-00145 the ESS role inside the transaction; `frappe.client.set_value` on a direct
   report's `cell_number` saved. Without ESS: refused. On someone outside the tree:
   refused. `reports_to` (level 2): silently not changed. Only 1 login on `test249` holds
   ESS. **I do not know how many hold it at DTC.** Still P2 until that count is done.

---

## The guard: I could not break it

`request_guard.py` removes `ignore_user_permissions` and `ignore_permissions` from the
request's arguments before Frappe routes it. A control run with the guard switched off
returned **191 of 191** employees, so the test harness does reproduce the hole.

| What I tried (staff login, Employee list with date of birth and mobile) | Result with the guard |
|---|---|
| `?ignore_user_permissions=1`, `=true` | 1 (own) |
| POST form, POST multipart, POST JSON body | 1 |
| JSON body plus the word in the query string; form plus query string | 1 |
| Word sent twice; key URL-encoded (`ignore%5Fuser%5Fpermissions`) | 1 |
| Other spellings: `Ignore_User_Permissions`, upper case, `ignore_user_permissions[]`, trailing space, `ignoreUserPermissions` | Error: Frappe rejects the unknown argument. No data |
| The word inside `filters` | Error: "Field not permitted in query". No data |
| JSON array as the body | Error. No data |
| `cmd` to "/" (POST and GET) | 1 |
| `/api/method`, `/api/v1/method`, `/api/v2/method` (GET and POST JSON) | 1 |
| `/api/resource/Employee`, `/api/v2/document/Employee` | 1 |
| `reportview.get`, `get_list`, `get_count`; `frappe.client.get_list`, `get_count` | 1 |
| `frappe.client.get_value` on a colleague | Empty |
| `frappe.client.get`, `form.load.getdoc`, `linked_with.get`, `get_linked_docs` on a colleague | Refused |
| Expense Claim, Attendance, Salary Structure Assignment with the word | Own only (0 for this login) |
| `search_widget` and `search_link`, with `reference_doctype` Serial No, Employee, Employee Grievance, the word and `filter_fields` | 1 |
| `search_widget` with `query=employee_query`; `employee_query` called directly, with the word | 1 |
| `validate_link_and_fetch` on a colleague, with the word and fields to fetch | Empty |
| Tree view `get_children`, `get_all_nodes` (including `tree_method` pointed at `reportview.get_list` with the word) | 1, or error |
| `get_group_by_count`, `get_next`, dashboard chart, number card | Own only |
| `www.list.get_list_data` with the word | 1 |
| Child tables through `parent_doctype` (Expense Claim Detail: 27 rows; Salary Detail: 8 rows) | 0 |
| `parent_doctype` trick on Employee | SQL error. No data |
| Export (`export_query`) with the word | Refused (staff have no export right) |
| `make_salary_slip` for a colleague, with `ignore_permissions=1`, preview and print | Refused |

**Why the nested routes do not get round it.** The only ways to slip arguments past the
guard are `run_doc_method`'s `args` (v1) and `kwargs` (v2), which are JSON inside one
parameter. I listed all 2,053 whitelisted functions on the site. **No document method
takes `ignore_permissions` or `ignore_user_permissions`.** The functions that take
`**kwargs` either pass them to a search the guard already cleaned
(`validate_link_and_fetch`) or have nothing to do with people (manufacturing, OAuth, the
recorder). *Verified by running an inventory script; inference that no future method will.*

**One weak spot in the CI test (P3).** The new test lists every whitelisted argument
named like `ignore_*permission*` and fails if it is not in the drop list. Good. But if a
future **document method** takes such an argument, adding it to the drop list will not
protect it, because it arrives inside `run_doc_method`'s JSON. Today there are none. Fix
when it happens: the test should fail for class methods with a message saying "the
guard cannot protect this; refuse it in code". The test also misses names like
`skip_permission` or `ignore_perms`. None exist today.

---

## Other people's data through other methods

I called every whitelisted Frappe HR, ERPNext and Alvoraa method that takes an employee
argument and has no obvious permission check, with a colleague's ID.

| Method | Result | Rating |
|---|---|---|
| `get_unmarked_days` | **4 days returned for a colleague** | **P2 Major** (bad news 2) |
| `get_leave_allocation_for_posting_date` | Returns the colleague's Leave Allocation ID, so shows they have that leave type. No balance | P4 |
| `alvoraa_portal.kra_api.get_my_kras(employee=…)` | Returns the colleague's appraisal template and its KRA list. Job-level, not their scores. Empty on this site | P4. Should ignore the argument for non-managers |
| `get_leave_balance_on`, `get_leave_details`, `get_holidays`, `get_number_of_leave_days`, `get_leave_approver(_and_mandatory)`, `hrms.api.get_leave_types`, `get_employee_field_property` (both), `get_contact_details`, `get_employee_shift` | Refused | Closed |
| `hrms.api.get_leave_applications`, `get_expense_claims`, `get_attendance_requests`, `get_holidays_for_employee` | Empty | Closed |
| Our own: manager detail, scorecard, notes, goals, cycle items, KPIs, suggest ratings, time, attendance person/month, field rights, org structure views | Refused, or own data only | Closed |
| Guest-open methods in our apps (34 listed) | None returns another person's data. `register_device` answers the same for real and fake IDs (read in code, `field_checkin.py:513-545`) | Closed |
| Org chart `get_children` | 131 active employees: name, designation, photo, manager | P3, unchanged, by design (slice 045 D-10) |

**I did not test every one of the 2,053 methods.** I tested the ones that take an
employee, a user or a permission word. Reports were covered in 07.

---

## The 07 findings, re-rated

| # | 07 finding | Now | How I know |
|---|---|---|---|
| 1 | P0: `ignore_user_permissions` on list endpoints | **Closed on this branch.** Open on production until deploy | Verified by running (table above) |
| 2 | P0: same word on link search | **Closed on this branch.** Open on production until deploy | Verified by running |
| 3 | P1: new joiners linked by a database write get no row | **P3.** `on_login` adds the row at first sign-in, before the session is handed back (`own_record_permission.py`, `hooks.py` `on_login`). Gap: a session already open at deploy keeps working without the row until it ends, which `run_once` covers. API-key logins: 0 on `test249`; unknown at DTC. The account script line (`sync_user`) is still not added, because DTC's real script is not in the repo | Verified in code; API-key count by query |
| 4 | P2: role permission changes do not re-run the rule | **P3.** Now caught at the next sign-in, plus a runbook line in 06 | Verified in code |
| 5 | P2: `rollback()` deletes rows it did not add | **Closed.** It now deletes only the names `run_once` saved in `sites/<site>/alv249_rows_added.json`, and refuses if the file is missing (fails safe) | Verified in code |
| 6 | Managers see the whole tree, including pay | **Accepted by Surbhi, 31 Oct 2026** (06, D-2). Now known to include Salary Slips with bank and net pay | 06; counsel C4 still open |
| 8 | Leave Balance report ignores Company permission | P2, unchanged. Own ticket. Harmless at DTC (one company) | From 07 |
| 9 | ERPNext Company row on HR people | P3, unchanged | From 07 |
| 10 | ESS write on the tree | **P2, now verified by running** (bad news 4). Needs the DTC count | Verified by running |
| 11 | Org chart; User list emails | P3, unchanged | Re-run: 131 |

**New things this round added, checked:**

- `on_login` runs our two User Permission writes on every sign-in. They write only the
  exact own-record row. The `ignore_permissions` ceiling test pins the file at 2
  (`test_portal_security_010.py`). If the sync ever raises an error, that login fails.
  This fails closed, but it would lock people out. P4: watch the error log after deploy.
- `request_guard.py`: no personal data logged, no new route. Cost is as 06 says: link
  pickers marked "Ignore User Permissions" show a staff or manager login only its own
  tree. HR and System Managers are unaffected.
- No new public route, export, cache or copy of personal data in the diff.

---

## The nginx log: what it does and does not show

**Fact given to me:** the production container log, since 28 Oct 23:26, has 260 requests
naming `ignore_user_permissions`: 210 with value 0, 50 with another value. All on
`validate_link_and_fetch` and `search_link`. None on `reportview.get`.

**What it shows:**

- **This is what Frappe's own Desk sends.** Every link field sends the word with the
  field's own setting, 0 or 1 (`frappe/public/js/frappe/form/controls/link.js:437`). So
  210 zeros are harmless by definition. The 50 others most likely come from link fields
  marked "Ignore User Permissions", such as `Employee.reports_to`, when someone opens or
  fills a form.
- **It tells us who will notice the guard.** After deploy, the pickers behind those 50
  requests will be narrowed for any login that holds a row. If they were HR people, nothing changes.

**What it does not show:**

- **It cannot show who read colleagues' data.** Before this fix nobody at DTC had a row,
  so a staff login saw everyone **without** the word. A plain request with no word looks
  exactly like normal use. The word was never needed to read the data.
- **"None on reportview.get" proves nothing.** Desk sends `reportview.get` as a POST.
  nginx logs the address, not the body. A POST carrying the word looks the same as any
  other list load.
- **It does not name the person.** nginx logs an IP address, not a login. To link one to
  a person, match the time and IP against Frappe's Activity Log (login records carry the
  IP). Office or mobile IPs may be shared.
- **It starts at 28 Oct 23:26.** Anything earlier is gone unless a backup has it.
- **`validate_link_and_fetch` with value 1 checks only that a name exists.** Fetching a
  colleague's fields still needs read permission (`frappe/client.py:510-520`). Before the
  fix that read was open anyway.

**What to do with it:**

1. Copy and keep the log now, access-controlled. Its query strings contain employee IDs
   and names, so it is personal data itself.
2. For the 50 non-zero lines, list: time, IP, `doctype`, `reference_doctype`, `txt`,
   `page_length`. Signs worth a closer look: empty `txt` with a large `page_length`, a
   `filter_fields` parameter, or a `reference_doctype` the person would never use (for
   example Serial No). Normal use looks like short typed text, page length 10, on a form
   they work in.
3. Do not tell DTC or counsel "the log shows no misuse". The honest line is: "the log
   cannot show whether anyone read colleagues' data, because no special request was
   needed to do it".

---

## Can ALV-249 and ALV-261 be called closed?

**Yes, once all four of these are done, and not before:**

1. The branch is deployed to production (it shuts doors 1 and 2 there).
2. `run_once` is run on each live tenant: dry run read by a person first, then
   `dry_run=0`, with **every line PASS** and "BEFORE own-record rows" noted.
3. One smoke test over real HTTP on dev, as a staff login: the Employee list, and the
   list with `?ignore_user_permissions=1`, each show one record. My tests ran in code, not
   over a socket.
4. The `sync_user` line is added to DTC's real account script, or Surbhi accepts in
   writing that sign-in (`on_login`) plus `run_once` after each batch is enough.

The ticket's goal, "a staff login sees only its own Employee record and only its own
claims", then holds on every door I could find.

**What stays open after closing, each needing its own ticket or a written acceptance:**

| Item | Rating | Owner |
|---|---|---|
| `get_unmarked_days` shows any colleague's missing-attendance days | P2 | Surbhi to raise; engineer to fix |
| ESS holders who manage people can edit their team's contact and passport fields | P2 | Surbhi: DTC count, then accept or remove ESS write |
| Managers read the tree's pay and bank details | Accepted 31 Oct 2026 (Surbhi) | Follow-up ticket idea in 06; counsel C4 |
| Leave Balance report and multi-company HR | P2 | Own ticket |
| Org chart and user emails visible to all | P3 | Confirm D-10 |
| CI test gap for document methods | P3 | Engineer, when a case appears |
| `get_my_kras`, `get_leave_allocation_for_posting_date` | P4 | Note |
| Report the `ignore_user_permissions` hole to Frappe's security team | Not filed | Surbhi |
| DPDP questions C1-C4 (07) and the nginx log copy | Open | Counsel; Surbhi |

---

## Residual risk

| Risk | Rating | Owner | Accepted |
|---|---|---|---|
| Doors 1 and 2 open on production until deploy | P0 | Surbhi (deploy decision) | Not accepted |
| Colleague attendance gaps via `get_unmarked_days` | P2 | Surbhi | Open |
| ESS write on the tree | P2 | Surbhi | Open until DTC count |
| Managers read tree pay and bank | P2 | Surbhi | Accepted 31 Oct 2026 |
| Sessions open at deploy keep wide access until they end | P3 | Surbhi | Open: `run_once` right after deploy closes it |
| No record of who read what before the fix | Fact | Counsel | For C1-C3 |

## What I could not check

- A real HTTP request through nginx and a login cookie (no web server in the container).
- DTC's numbers: ESS holders, API-key users, Salary Slips, which link fields are marked
  "Ignore User Permissions". Needs a read-only count on production, with Surbhi's
  approval.
- Production's Frappe version matches `test249`'s (16.33.1).
- All 2,053 whitelisted methods. I covered those taking an employee, a user or a
  permission word.

## Subtract pass

Removed from my draft: a second table repeating 07's closed doors, and a proposal for a
general wrapper around every Frappe HR method that takes an employee. Only one such method
leaks today; one override fixes it.
