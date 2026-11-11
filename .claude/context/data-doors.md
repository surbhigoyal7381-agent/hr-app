# Data doors: the portal is not the security

Every agent reads this before it touches anything that shows, edits or exports a person's data.
Born from ALV-249 (31 Oct 2026): for weeks, any DTC staff login could read all 597 colleagues'
personal data, because our portal limited what it *showed* but Frappe's own doors stayed open.
Counsel's view: it counts as a breach even if nobody is shown to have read it.

## The one rule

**A rule that lives only in our portal code is not a rule.** The record limit must live in the
permission layer Frappe itself enforces (User Permission, `permission_query_conditions`,
`has_permission`, field levels). The portal then adds convenience on top. Never the reverse.

## Never bypass

- No `ignore_permissions=True`, `frappe.db.set_value`, raw SQL, or `frappe.get_all` inside a
  function a user can call, unless the slice's security note lists it, counts it (the CI
  ceiling in `test_portal_security_010`) and says why no ORM path works.
- A bypass on one record type is never a reason to loosen another.
- Never ask a user to enter, and never accept from a request, a flag that skips a permission
  (`ignore_user_permissions`, `ignore_permissions`). `request_guard.py` removes them; do not
  work around the guard.
- "The portal never shows it" is not an argument. Someone can call the API without a screen.

## The doors to test for every slice that touches personal data

Test each as a **plain staff login** (Employee role only), a **manager**, an **HR Manager**:

1. `/api/resource/<DocType>` list, get, put, post, delete
2. `frappe.desk.reportview.get` and `get_list` / `get_count`, with `reference_doctype` and the
   extra-word variants
3. `frappe.client.*`: get, get_list, get_value, set_value, save, insert, attach_file, rename
4. Link search (`search_link`, `search_widget`, `validate_link_and_fetch`) with `filter_fields`
5. Report view, export to CSV, print views, and every standard report that reads the doctype
   (Frappe HR ships reports with no permission check, for example Employee Birthday)
6. Share, assign, comment, tag and like on a record (sharing opens a record to anyone)
7. Whitelisted methods in `hrms` and `erpnext` that take an employee argument
8. Child tables read or written on their own
9. The role's write rights (Employee Self Service can write Employee, rename, and share)
10. Background and bulk paths: Data Import, bulk edit, patches, scheduled jobs, account scripts

## What every slice must prove

- **Before the build:** the spec names who may read and who may write each new field and record
  type, per persona (staff, manager, HR, CXO), and which Frappe door enforces it.
- **In the tests:** a test per door that FAILS without the fix. A check that cannot fail proves
  nothing. Run the new tests and the budget tests on a **freshly created site** too: a copied
  site hides failures (ALV-249 broke two tests that passed on the copy).
- **Before release:** a read-only count on the real tenant (what a plain staff login can list,
  how many logins would be affected, which roles act on other people's records). Counts only.
- **After release:** the same count again, printed as PASS or FAIL.

## Strategy by role

- **Product manager:** owns the **Access expectations** table in every brief: for each kind
  of data and each persona, what they may see, change and share, the purpose behind it (their
  job to be done), and what they must not have. It comes from HR domain competence, the
  nature of the product and what each persona expects, and it answers the five questions
  below in plain words. Sensitive data (health, passport, bank, pay, grievance, performance)
  is an exception to justify, not a default. The PM flags where a persona's expectation
  conflicts with least privilege, and asks the user.
- **BA:** turns the PM's table into rules per field and per record type, and names the Frappe
  door that enforces each. If a story shows a colleague's data, say which rule limits it.
- **UX designer:** if a screen shows another person's data, flag it. A hidden field in the
  design is not a protection.
- **Security engineer:** threat-model the Frappe doors above, not only our endpoints. Check
  roles that read the doctype and what each can do. Read the real tenant's roles first.
- **Engineer:** put the limit in the permission layer first. Count every bypass. Run the door
  list. Say what you did not test.
- **Test engineer:** a door test per row of the list, as three personas, on a fresh site.
- **Reviewer:** reproduce one door yourself. Do not accept "the portal does not show it".
- **DevOps:** list roles and permission rows per tenant before a deploy that changes who can see
  what. Keep nginx logs and tell the user how far back they go.

## For Surbhi: what to ask at every gate

1. Who can read this, and which Frappe door stops everyone else?
2. Was it tested as a plain staff login through the API, not only through the portal?
3. Does it work on a fresh site, and what does the real tenant look like (read-only counts)?
4. How many bypasses were added, and where are they listed?
5. What would a manager, with a self-service role, be able to change or share?

## If an exposure is found

Stop and tell Surbhi first, in plain words. Open a ticket at once. Make read-only counts, never
changes. Do not say "no misuse". The system keeps no log of list reads, so say that. Counsel's
timeline (DPDP, CERT-In 6 hours) starts on confirmation: ask Surbhi to bring counsel in the same
day. Production fixes and notices are hers.
