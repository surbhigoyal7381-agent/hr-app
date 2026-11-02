"""Reading an employee's documents from the Positions page.

Slice 078, step 5. US-22 to US-25, and the step that carries the slice's one
named residual risk.

**Why this endpoint exists at all.** `Employee Document` is a CHILD TABLE
(`istable: 1`) and its `attachment` is an `Attach` field, so the file belongs to
the parent `Employee`. A permission rule written at the row therefore never
reaches the file, and - the trap ALV-256 was two days before this was written -
`frappe.has_permission` on a child table returns **False for everybody**, so
asking it would refuse the feature to its own audience. The guard is on the
PARENT, and the file is served by this endpoint rather than by a URL.

**Five checks, in this order, and the order is load-bearing.**

  1. `register.may_view()` - can this person open the Positions page at all.
  2. `employee_in_scope(employee)` - are they inside their own companies and
     branches. **Before** the ticked-type check, so a refusal never reveals
     whether a type was ticked.
  3. the row's `parent` IS that employee - so a row id cannot be walked onto
     somebody else's record.
  4. the row's `document_type` is in the ticked list - intersected here, not
     only where it was set.
  5. the plan includes `employee_documents`.

**The honest half, and no product copy may contradict it.** A reader who
already holds a `/private/files/...` URL can still fetch it directly, because
Frappe's private-file gate falls back to the parent Employee's read permission
and **no `has_permission` hook fires on that path** - traced through
`frappe/app.py:163` -> `utils/response.py:294` -> `file/utils.py:452` ->
`file.py:896` -> `file.py:989`, where the decision is Administrator, then not
private, then `owner == user`, then a DocShare row, then the parent's own read.
`frappe/permissions.py:483` is the only place Frappe reads the `has_permission`
hook and that path never enters it. So the ticked list is **defence in depth**:
it decides what this product shows and streams, not what the framework will
serve to somebody who already has a URL. The browser is never handed one, which
is what makes that matter less; it is not the same as it not mattering.

So: nothing anywhere says or implies that an un-ticked document type is
"hidden", "protected" or "secure", and `test_employee_documents_078` asserts
those three words do not appear about them.
"""

import frappe
from frappe import _
from frappe.utils import cstr, now, today

from alvoraa_portal.field_app_limits import SELF_KEY, _limited
from alvoraa_portal.positions_profile import _guard

DOC = "Employee Document"
DOC_TYPE = "Employee Document Type"
ACCESS_LOG = "Alvoraa Photo Access Log"
DOCS_KEY = "alvoraa_positions_document_types"
RULE = "078-SEC-4"
ENDPOINT = "employee_documents_read.open_employee_document"
FEATURE = "employee_documents"


def ticked_types():
	"""The document types this organisation chose to show on the profile.

	Read from the setting and intersected with the types that actually exist, so
	a type deleted after being ticked is skipped silently in the list (E17) and
	refused by the endpoint - rather than crashing either.
	"""
	raw = frappe.db.get_default(DOCS_KEY) or ""
	wanted = [v.strip() for v in str(raw).split(",") if v.strip()]
	if not wanted:
		return []
	return frappe.get_all(DOC_TYPE, filters={"name": ("in", wanted)}, pluck="name",
	                      limit_page_length=0)


def _plan_on():
	from alvoraa_portal.subscription import has_feature

	return bool(has_feature(FEATURE))


def _refuse(name=None):
	from hrms.alvoraa_hr_core.access import refuse

	# The refusal carries NO document type name and NO employee name: a message
	# is a disclosure too.
	refuse(_("You cannot open that document."), RULE, ENDPOINT, DOC, name)


@frappe.whitelist()
def get_employee_documents(employee=None):
	"""The rows the drawer lists. Only the ticked types, and only with the plan.

	Returns an EMPTY LIST when the plan is off or nothing is ticked, and the
	drawer then draws no section at all - not an empty heading, not a greyed
	tab, not a count of zero (AC-45).
	"""
	employee = _guard(employee)
	types = ticked_types()
	if not types or not _plan_on():
		return {"documents": []}

	meta = {t.name: t for t in frappe.get_all(
		DOC_TYPE, filters={"name": ("in", types)},
		fields=["name", "category", "collect_from"], limit_page_length=0)}
	rows = {r.document_type: r for r in frappe.get_all(
		DOC, filters={"parent": employee, "parenttype": "Employee",
		              "document_type": ("in", types)},
		fields=["name", "document_type", "status", "attachment", "expiry_date"],
		order_by="idx", limit_page_length=0)}

	out = []
	for name in types:
		row = rows.get(name)
		t = meta.get(name) or frappe._dict()
		out.append({
			"document_type": name,
			"category": t.get("category") or "",
			# A row with no file says WHO COLLECTS IT, so a dead row becomes an
			# action rather than a shrug (AC-64).
			"collect_from": t.get("collect_from") or "",
			"status": (row.status if row else "") or "",
			"expiry_date": cstr(row.expiry_date) if (row and row.expiry_date) else "",
			# The ROW's name, which is what the endpoint takes. **Never the file
			# url**: the browser is not handed a `/private/files/...` address for
			# a document anywhere in this product.
			"row": row.name if (row and row.attachment) else None,
		})
	return {"documents": out}


@frappe.whitelist()
# Sixty an hour PER USER (AC-71), keyed through `field_app_limits` so the
# limiter's Redis key is a HASH - Frappe writes a limiter's key value into
# Redis in clear, and a document row id is not something to scatter about.
# The limit is readable off the function, so a table test can pin it.
@_limited(SELF_KEY, "user", limit=60)
def open_employee_document(row=None):
	"""Stream ONE document, after the five checks. There is no "all documents".

	The payslip pattern (`hr_api.get_payslip_pdf`): the bytes go into
	`frappe.local.response` with `type = "download"`, which Frappe serves with
	`Content-Disposition: attachment`, and `as_raw` sets the content type from
	the file name.

	**The header is unchanged; what the browser does with the bytes is not.**
	Since ALV-287 (2 Nov 2026) the portal fetches this with `fetch`, holds the
	blob and SHOWS it - a picture in an `<img>`, a PDF in an iframe with no
	sandbox - instead of saving it. The disposition never reaches a navigation,
	so it decides nothing. A PDF is still the one accepted type we do not
	re-encode and therefore cannot strip; Surbhi weighed that against the
	download it replaced - a copy in the reader's Downloads folder, opened in
	Acrobat, outside the access log, outside retention and outside any erasure -
	and chose to show it. Her reasons and the browser measurements behind them
	are at `mpfShowDoc` in portal.js. Nothing here changed to make that
	possible, and nothing here should change to undo it.

	**One file per request.** An "all documents" call would be a single click
	that puts a person's whole identity file through eight worker slots, and
	nothing in the design needs one.
	"""
	if not isinstance(row, str) or not row.strip():
		_refuse(row)
	row = row.strip()

	# The row, read without asking the CHILD TABLE's own permission - which
	# would be False for everybody (ALV-256). The guard is the parent's, below.
	doc = frappe.db.get_value(
		DOC, row, ["name", "parent", "parenttype", "document_type", "attachment"],
		as_dict=True)
	if not doc or doc.parenttype != "Employee" or not doc.attachment:
		_refuse(row)

	# 1 and 2. The page's own permission, then the reader's scope on that
	# employee. `_guard` raises the same refusal for both, so a reader scoped
	# out of a branch learns nothing about the employee OR the branch.
	employee = _guard(doc.parent)

	# 3. The row's parent IS that employee. Belt and braces: `_guard` was asked
	# about `doc.parent`, so this cannot fail - and it is written down because
	# the version of this function that takes an `employee` argument alongside
	# the row is the version with the hole in it.
	if doc.parent != employee:
		_refuse(row)

	# 4. The type is ticked. AFTER the scope check, on purpose.
	if doc.document_type not in ticked_types():
		_refuse(row)

	# 5. The plan.
	if not _plan_on():
		_refuse(row)

	f = frappe.get_doc("File", {"file_url": doc.attachment})
	# `encodings=[]`, because `get_content()` with no argument tries to DECODE
	# what it read and hands back a lossy `str` for anything binary - which for
	# a scanned PDF or a photographed document means serving a corrupted file
	# that opens as nothing. See `employee_photo._raw_bytes` for the trace.
	content = f.get_content(encodings=[])

	log_document_view(employee, doc.document_type)

	frappe.local.response.filename = f.file_name or "document"
	frappe.local.response.filecontent = content
	frappe.local.response.type = "download"
	# The document NAME and the employee id. Never the file, never the url,
	# never a document number, never a name.
	frappe.logger("alvoraa").info(
		f"employee document: {row} on {employee} opened by {frappe.session.user}")


# ── who opened whose document ────────────────────────────────────────────────

def log_document_view(employee, document_type):
	"""One row per viewer per document per day, on the table that already holds
	"who looked at a face".

	**This is the only way an employee who cannot open the Positions page can
	ever ask "who looked at my Aadhaar" and get an answer that is not "we do not
	know".** Nobody asked for it; it stays because of that.

	A SIBLING of `field_app_access.log_photo_view`, not a change to it: changing
	that function would alter check-in logging, which is not this slice's.
	The three narrowing rules are copied from it, because an access log that
	records everything is one nobody reads:

	  * only when there is something to look at;
	  * **never a person looking at their own**;
	  * one row per viewer per document per day, not one per refresh.

	It holds no file, no file url, no document number and no value from the
	document itself (078-PRIV-5).
	"""
	user = frappe.session.user
	if user in ("Guest", "Administrator", ""):
		return
	if not frappe.db.exists("DocType", ACCESS_LOG):
		return
	try:
		mine = frappe.db.get_value("Employee", {"user_id": user, "status": "Active"},
		                           "name")
		if mine and mine == employee:
			# Never a person looking at their own.
			return
		if frappe.db.exists(ACCESS_LOG, {
			"employee": employee, "document_type": document_type,
			"viewed_by": user, "viewed_on_date": today(),
			"source": "Employee document"}):
			return
		frappe.get_doc({
			"doctype": ACCESS_LOG,
			"employee": employee,
			"employee_name": frappe.db.get_value("Employee", employee, "employee_name"),
			"document_type": document_type,
			"source": "Employee document",
			"viewed_by": user,
			"viewed_at": now(),
			"viewed_on_date": today(),
		}).insert(ignore_permissions=True)
		frappe.db.commit()
	except Exception:
		# Never let the record stop somebody doing their job. The same rule the
		# check-in photo log already follows.
		frappe.log_error(f"Could not record the document view on {employee}",
		                 "Employee document access log")


@frappe.whitelist()
def what_is_shown_about_me():
	"""⚠ DECISION O: the employee's own answer to "what of mine is on show".

	One line on their own My-profile documents card, because the person whose
	documents these are **cannot open the Positions page** and otherwise has no
	way at all to find out which of them a reader can open. About an hour of
	work, and it is the difference between a policy and a secret.

	It names the TYPES, which the organisation chose, and nothing about any
	reader or any person.
	"""
	if frappe.session.user in ("Guest", ""):
		frappe.throw(_("Please sign in."), frappe.PermissionError)
	if not _plan_on():
		return {"types": []}
	return {"types": ticked_types()}
