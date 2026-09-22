---
slice: 034-redesign-wave1
artifact: 01c-security-privacy-requirements
author: hrms-fullstack-engineer (written at the coordinator's request; for review by hrms-security-privacy-engineer)
date: 2026-09-22
status: draft
inputs: [00-impact-analysis.md, ../009-ess-portal-redesign/00f-decisions-2026-09-22.md, ../009-ess-portal-redesign/01b-ux-design.md §5 §9, ../009-ess-portal-redesign/appendix-a-frame.md, ../030-store-hr-scoping/00-impact-and-fix.md, .claude/context/security-compliance-baseline.md]
---

# Wave 1 frame — security and privacy requirements

**Kept short on purpose.** It covers the four areas the coordinator named: the preview
page's exposure, store-HR scoping, what search may and may not return, and the profile
menu's desk and admin links. Plus the smaller duties the frame carries (counts, language,
logs). **The security engineer should review it before the spec is called Ready.** I am
the engineer who will build this, so I am not the right person to sign off my own
requirements.

## Threat model in four lines

1. **A logged-in employee** changes the calls the page makes, to find people, counts or
   pages outside their reach. The frame's new endpoints are all whitelisted and callable
   by hand.
2. **A store's HR person** reads another store's people or pending approvals through a
   count, the bell list or search, because those still scope by company.
3. **Anyone who guesses the preview address** on production sees unfinished screens, or
   reaches a path whose checks were only written in the page.
4. **The frame puts data on a bigger stage**: a count, name or link that used to sit
   inside one panel now shows on every page, and on the landing page.

## Data inventory

| Data | Where it appears | Sensitivity | Purpose | Kept |
|---|---|---|---|---|
| Person's own name, job title, photo | Rail, profile menu | Personal, low | Show who is signed in | Not stored by the frame |
| Colleague name, job title, department, photo | Search results | Personal, low | Find a person in your scope | Not stored |
| Colleague phone, email, employee number, branch, manager | **Never** in search or frame | Personal | — | — |
| Counts of pending items, by part | Bell, menu, bottom bar, Inbox page | Aggregate; can reveal that *someone* has a request | Tell a person work is waiting | Not stored; counted live |
| `User.language` | User record | Preference | Language of the portal | As long as the user exists |
| Theme choice | Browser storage on the device | Preference, not personal | Light or dark | On that device only |

## Who must NOT see what

| Who | Must not see |
|---|---|
| Employee | Anyone outside their own reporting line downwards in search (decision Q-c). Any count about other people's requests |
| Manager | People outside their line downwards in search. Counts for items that are not theirs to act on |
| Store HR | **Anyone outside their store** — in search, in counts, in the bell list. An employee with no branch counts as outside the store (slice 030, DEF-6) |
| Company-wide HR | People and items outside their permitted companies |
| A tenant's own System Manager | The Alvoraa control plane (`/alvoraa-admin`) — not offered |
| Anyone not System Manager | The preview page, until the swap |
| Guest | Anything; every new endpoint refuses Guest |

## Obligations engaged (from the baseline)

- **DPDP Act 2023 — minimisation and purpose:** search returns the least data needed to
  pick a person. No phone, email or ID.
- **Access rights on every path (baseline "access rights"):** scope is enforced on the
  server for every new endpoint, not by what the menu shows.
- **Logging duties:** no personal data in logs (names, reasons, counts per person).
- **OWASP ASVS 5.0 L2, access control:** row-level scope on every list and count.

## Abuse cases

| # | Actor and path | What must happen |
|---|---|---|
| A1 | Employee calls `search_people` with a colleague's name from another store | No result |
| A2 | Store HR opens the bell list or reads `get_nav_counts` | Only their store's items |
| A3 | Employee calls `get_nav_counts` and compares totals over time to learn when a colleague applied for leave | Impossible: an employee's count holds only their own requests and items addressed to them |
| A4 | Anyone opens `/hrms-employee-next` on production | Only a System Manager gets the page. Everyone else gets the normal "not permitted" page |
| A5 | Tenant owner edits the page to show the Tenant admin link and clicks it | `/alvoraa-admin` still refuses: it checks `alvoraa_control_plane` itself |
| A6 | Caller sends `set_my_language` with a disabled or made-up language, or with another user's name | Refused; only the caller's own record can be written |
| A7 | Caller sends a search string with SQL or HTML in it | Treated as text. Query is built by the ORM. Results are escaped when shown |
| A8 | A tenant's logo URL holds a script | The URL is escaped in the attribute, as slice 025 does; it can only come from site config |

## Requirements

| ID | Requirement | How it is tested |
|---|---|---|
| **SEC-1** | The preview page `/hrms-employee-next` renders only for a user with System Manager. Everyone else, including HR, gets Frappe's not-permitted response. Guest is sent to login. The check is in the page's `get_context`, on the server, and is deleted with the page in the swap commit | Test per role: Guest, Employee, HR, System Manager |
| **SEC-2** | The preview page calls no endpoint whose permission check lives only in the page. Every call it makes goes to a whitelisted function that checks the caller itself | Review of the page's call list against `test_portal_call_paths`; every new endpoint has a Guest-refused and a wrong-role test |
| **SEC-3** | `_pending_approvals_scope` limits HR to `access.permitted_employees()`. The count and the bell list keep sharing it, so they cannot disagree | Store-HR fixture with two stores: count and list show only store A; company-wide HR sees both |
| **SEC-4** | `_search_scope` narrows HR by `access.permitted_branches()` when they hold a Branch permission. An employee with no branch is outside a store | Same two-store fixture, plus a head-office employee with no branch |
| **SEC-5** | Every part of `get_nav_counts` is scoped on the server: personal parts by the caller's own user or employee; HR parts by `permitted_employees()`; policy parts by the policy library's own read rules. No part counts the caller's own requests as approvals | Per-persona tests, including "my own request is not in my approvals" |
| **SEC-6** | New endpoints (`get_frame`, `get_nav_counts`, `set_my_language`) refuse Guest, take no client-chosen doctype, field or method, and add no `ignore_permissions` | Tests; the `ignore_permissions` counter in CI does not rise |
| **SEC-7** | The "Switch to the full desk" item shows only when `get_switch_target` returns a target (admins → `/app`, HR → `/app/hr`, others → none). The label and URL come from the server | Test per role on `get_frame`'s payload |
| **SEC-8** | The "Tenant admin" item shows only when the user is a System Manager **and** the site is the control plane (`alvoraa_control_plane` set) — decision 9. `/alvoraa-admin`'s own check is unchanged | Test on `get_frame`'s payload on a tenant site and on a control-plane site |
| **SEC-9** | `set_my_language` accepts only a Language record that is enabled on this site, writes only the caller's own `User.language`, and never takes a user argument | Tests for disabled, unknown and valid languages |
| **SEC-10** | Everything the frame puts into HTML from data (names, titles, labels, counts, logo URL) is escaped. The rail keeps slice 025's `| e` on the logo URL | `test_brand_logo_025` repointed at the new frame; a test with `<script>` in a job title |
| **SEC-11** | Page search offers only pages from the menu list, after the same visibility rules. A page the person cannot open never appears | Test per persona on the list of searchable pages |
| **PRIV-1** | People search keeps decision Q-c: an employee or manager finds themselves and people below them; HR finds their permitted people; nobody finds anyone else (decision 5) | Tests per persona |
| **PRIV-2** | A search result carries name, job title, department and photo only. The Employee record name travels as a link key and is never displayed. No phone, email, employee number, branch or manager | Test that the returned keys are exactly this set |
| **PRIV-3** | A search needs at least two letters. The frame asks for 12 people. The server never returns more than 50 (the cap `search_people` already has), so nobody pages through a staff list | Tests |
| **PRIV-4** | Counts carry numbers only — never a name or a reason. The Inbox page in Wave 1 shows rows per part ("3 leave requests"), not people | Test the payload shape; review the page |
| **PRIV-5** | Logs from the frame's endpoints carry the endpoint, the user id, the outcome and the time. Never a name, a search term, or a count per person. Refusals use `access.log_refusal` | Log-capture test on a refused call and on a search |
| **PRIV-6** | Theme is stored on the device only and holds no personal data | Review |
| **PRIV-7** | The frame widens no visibility. It shows nothing on the landing page that the person could not already see in a panel today. The wider design search (manager and leadership) is **not** built | Review against today's panels; PRIV-1 tests |

## Questions for the compliance owner

None that block this wave. One to note: search result photos are personal data. They are
already shown in today's org chart and search, so the frame does not widen this.

## Open questions

| # | Question | Owner | Blocks |
|---|---|---|---|
| 1 | Should SEC-1's "not permitted" page for the preview address be a 404 instead, so its existence is not confirmed? | Security engineer | Nothing; either is safe |
| 2 | Review of this document by the security engineer | Security engineer | The spec's Ready check |

## Assumptions

- `[ASSUMPTION]` `access.permitted_employees()` and `permitted_branches()` behave as their
  docstrings and slice 030's tests say. Not re-tested today.
- `[ASSUMPTION]` Frappe's `/me` page (My account) shows only the caller's own record.

## Handoff note

To the security engineer: the risky parts are SEC-3 and SEC-4 (a scope change inside two
shared helpers), and SEC-1 (a page that will exist on production for two or three weeks).
The rest mostly holds existing rules steady while the page around them changes. Please
say where you disagree.
