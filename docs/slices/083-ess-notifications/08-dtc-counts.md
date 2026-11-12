# 083 — the DTC counts, 6 November 2026

Authorised by Surbhi on 6 Nov 2026. **Read-only.** Seven `SELECT` statements against
`dtc.alvoraa.co` on the production bench (`compose-mariadb-1`, site db `_3e6ff33d82d52e8e`).
Nothing was written, no site setting changed, no cache cleared, no container restarted.

This closes kill criterion **R6 / OPS-3** and the brief's "count the rows before the design
step" item. It was the last unverified assumption in the slice.

---

## 1. The bell's own kinds are empty at DTC

`tabNotification Log` holds **no rows at all** of the three types the notices feed reads —
no `Grooming Mark`, no `Grooming Review`, no `Announcement`. Every grouping query for those
three types returned an empty set.

**What this settles.** The designer's and the product manager's worry — that the heaviest
user might carry hundreds of unread notices, making "Unread notices" the main view rather
than a filter — **does not hold at DTC.** Nobody is near the 100-row cap for these kinds,
because nobody has one row. The design's five-rows-per-group shape is safe, and the
`capped` line will not be seen at DTC on day one.

**What it does not settle.** It means the opposite problem is the real one: **the notices
half of the bell will be visibly empty at DTC after release.** The number on the bell will
come entirely from work owed. That is a product fact worth stating to DTC rather than
letting them discover an empty half of a new page.

| Kind | Rows | Unread | People |
|---|---|---|---|
| `Grooming Mark` | 0 | 0 | 0 |
| `Grooming Review` | 0 | 0 | 0 |
| `Announcement` | 0 | 0 | 0 |

## 2. What DTC's notification table actually holds

| `document_type` | Rows | Unread |
|---|---|---|
| `Employee` | 902 | **902** |
| `Alvoraa App Invite` | 23 | 23 |
| `Report` | 22 | 17 |
| `Interview` | 1 | 1 |

**902 unread `Employee` rows, none of them read by anyone.** These never appear in our
portal bell — `Employee` is not in `NOTICE_DOCTYPES` — but they do appear in Frappe's own
Desk bell for the people who hold Desk access.

**This sharpens SEC-2 from a precaution into a measured risk.** The security engineer
predicted this hazard from PPJ, where the heaviest user carries 406 such rows. DTC carries
**902**. Frappe's own `mark_all_as_read` filters on `for_user` alone, so if the bulk
mark-as-read were written that way, one tap of "Mark all as read" by an HR user would
silently mark their share of those 902 rows read, with nothing logged and nobody likely to
report it. The three-assertion test in SEC-2 is now backed by a real number, and the second
assertion — *the caller's own `Employee` rows stay unread* — is the one that matters most.

## 3. The heaviest people, across every kind

| User | Rows | Unread |
|---|---|---|
| `ritika.arora@dtc.alvoraa.co` | 169 | 167 |
| `admin@dtc.alvoraa.co` | 166 | 166 |
| `vaneet.garg@dtc.alvoraa.co` | 166 | 166 |
| `rama.pandey@dtc.avoraa.co` | 96 | 96 |
| `vikas.garg@dtc.alvoraa.co` | 84 | 84 |

Three people are already over 100 unread rows across all kinds. Not a problem for this
slice, because the bell reads only three types and holds none — but it is the measurement to
quote if the feed is ever widened, because at that point the capped-count bug this slice
fixes would become visible immediately.

## 4. A data fault found while counting, unrelated to this slice

**`rama.pandey@dtc.avoraa.co` is a misspelling** — `avoraa`, missing the `l`. 96 unread
notification rows are addressed to a user id on a domain that does not exist. Any mail to
that address cannot be delivered, and the person cannot be reached by email at all.

Not caused by this slice and not fixed by it. Needs its own ticket, and a check for whether
other accounts carry the same typo.

## 5. Scale, for the record

| Role | Users |
|---|---|
| `Employee Self Service` | 483 |
| `Employee` | 482 |
| `HR User` | 9 |
| `HR Manager` | 5 |
| `System Manager` | 2 |

`tabUser Permission`: **694 `Employee` rows across 464 users**, plus 42 `Branch` rows over
5 users, 3 `Company` rows and 1 `Page` row. This matches the deliberate narrow per-doctype
pattern recorded for DTC — the rows restrict rather than grant, and none of the link fields
they use would open the shared-document door on `Notification Log`.

So the bell's two calls run for **483 portal logins**, which is the figure the DevOps
estimates in `07-devops-inputs.md` §1 were built on.

---

## What is still unverified after this

- **Chrome Android bfcache on a `no-store` page** (risk R5). Needs one real handset, ten
  minutes, with the Chrome version recorded. Unchanged by these counts.
- **The `Cache-Control` header on the signed-in page.** Seen on the Guest redirect only;
  confirming it signed-in would have written a session row to a shared bench.
