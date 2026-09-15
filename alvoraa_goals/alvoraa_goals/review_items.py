"""Review copies: each review's own record of the Objectives and KPIs it rates.

Slice 010, group D. The decisions are in
docs/slices/010-portal-security-fixes/00c-review-copies-decisions.md (R1-R16)
and 00e-group-d-approved-decisions.md, which wins where they differ.

This module owns:

  review_settings()        the three organisation settings, read safely
  after_migrate()          installs those settings on HR Settings (migrate and install)
  open_review(ext)         take the copies the first time a review is opened,
                           otherwise bring their numbers up to date
  ensure_review_items()    take the copies, once (decision 4, VIS-4)
  refresh_review_items()   count approved facts dated in the review period (R3, R4)
  stamp_rating(),          remember the numbers a rating was given on, and flag
  stamp_overall_rating(),  the rating when they change (R7)
  raise_rating_flags()

A review's copies are rows of Alvoraa Review Item on its Alvoraa Appraisal
Extension. The Extension refuses any change to them unless it comes through
save_review_record() here.

Log lines and errors from here carry document and row names only. Never a
title, a number, a rating, a comment or a reason (PRIV-15).
"""

import json
from datetime import datetime

import frappe
from frappe import _
from frappe.utils import cint, cstr, flt, get_datetime, getdate, now_datetime

from alvoraa_goals.alvoraa_goals.doctype.alvoraa_appraisal_extension.alvoraa_appraisal_extension import (
    REVIEW_ITEMS_WRITE_FLAG,
)
from alvoraa_goals.controllers.kpi import attainment

# ── Organisation settings (R6, R9, R12) ─────────────────────────────────────
#
# Custom fields on HR Settings: organisation-level, typed, and HR Settings keeps
# a Version row for every change, so "who moved the freeze point" has an answer.
# Not Global Defaults: hr_api.set_org_setting lets HR write any key there with
# no history (SEC-28).

FREEZE_SELF_SENT = "Self-review sent"
FREEZE_MANAGER_SENT = "Manager review sent"
FREEZE_HR_SENT = "HR sent"
FREEZE_POINTS = (FREEZE_HR_SENT, FREEZE_MANAGER_SENT, FREEZE_SELF_SENT)

REMOVAL_DISCARD = "Discard the copy"
REMOVAL_KEEP = "Keep the copy with a reason"
REMOVAL_MODES = (REMOVAL_DISCARD, REMOVAL_KEEP)

DEFAULT_LOCK_RELEASE_DAYS = 30

SETTING_FIELDS = {
    "freeze_point": "alvoraa_review_freeze_point",
    "lock_release_days": "alvoraa_review_lock_release_days",
    "removal_mode": "alvoraa_review_removal",
}

DEFAULTS = {
    "freeze_point": FREEZE_HR_SENT,
    "lock_release_days": DEFAULT_LOCK_RELEASE_DAYS,
    "removal_mode": REMOVAL_DISCARD,
}


def review_settings():
    """The three settings, never throwing.

    An empty or unknown value falls back to the default. A lock release below
    zero is treated as 0, which means the lock is never released (fail closed,
    SEC-22).
    """
    out = dict(DEFAULTS)
    for key, fieldname in SETTING_FIELDS.items():
        try:
            value = frappe.db.get_single_value("HR Settings", fieldname)
        except Exception:
            # Field not installed yet on this site: keep the default.
            continue
        if key == "freeze_point" and value in FREEZE_POINTS:
            out[key] = value
        elif key == "removal_mode" and value in REMOVAL_MODES:
            out[key] = value
        elif key == "lock_release_days" and value is not None:
            out[key] = max(cint(value), 0)
    return out


def validate_hr_settings(doc, method=None):
    """doc_events HR Settings validate: refuse a value outside the choices (SEC-28)."""
    freeze = doc.get(SETTING_FIELDS["freeze_point"])
    if freeze and freeze not in FREEZE_POINTS:
        frappe.throw(_("Choose when review numbers freeze from the list."))
    removal = doc.get(SETTING_FIELDS["removal_mode"])
    if removal and removal not in REMOVAL_MODES:
        frappe.throw(_("Choose what happens to a removed review item from the list."))
    days = doc.get(SETTING_FIELDS["lock_release_days"])
    if days not in (None, "") and cint(days) < 0:
        frappe.throw(
            _("The number of days before the review lock is released cannot be below 0. Use 0 for never.")
        )


def after_migrate():
    """Add the three settings to HR Settings, on migrate AND on install.

    Both, because a site built with `bench install-app` never runs a migrate
    (see alvoraa_portal/hooks.py). Safe to run again: fields are updated in
    place, and a setting that already has a value keeps it.
    """
    from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

    create_custom_fields(
        {
            "HR Settings": [
                {
                    "fieldname": "alvoraa_review_tab",
                    "fieldtype": "Tab Break",
                    "label": "Performance Reviews",
                    "insert_after": "hiring_sender_email",
                },
                {
                    "fieldname": SETTING_FIELDS["freeze_point"],
                    "fieldtype": "Select",
                    "label": "Freeze review numbers when",
                    "options": "\n".join(FREEZE_POINTS),
                    "default": FREEZE_HR_SENT,
                    "insert_after": "alvoraa_review_tab",
                    "description": "Until then, approved updates dated inside the review period still reach the review. "
                    "A review keeps the choice that was in force when it was first opened.",
                },
                {
                    "fieldname": SETTING_FIELDS["lock_release_days"],
                    "fieldtype": "Int",
                    "label": "Release the Objective and KPI lock this many days after the cycle ends",
                    "default": str(DEFAULT_LOCK_RELEASE_DAYS),
                    "non_negative": 1,
                    "insert_after": SETTING_FIELDS["freeze_point"],
                    "description": "0 means never. The lock always ends when the review is completed.",
                },
                {
                    "fieldname": SETTING_FIELDS["removal_mode"],
                    "fieldtype": "Select",
                    "label": "When an item is removed from a review",
                    "options": "\n".join(REMOVAL_MODES),
                    "default": REMOVAL_DISCARD,
                    "insert_after": SETTING_FIELDS["lock_release_days"],
                    "description": "An item that already has a rating is always kept, marked Removed.",
                },
            ]
        },
        update=True,
    )

    # A custom field's default does not fill a Single that already exists, and an
    # Int with no stored value reads as 0 - which would mean "never release".
    for key, fieldname in SETTING_FIELDS.items():
        stored = frappe.qb.get_query(
            table="Singles",
            filters={"doctype": "HR Settings", "field": fieldname},
            fields="value",
        ).run()
        if not stored:
            frappe.db.set_single_value("HR Settings", fieldname, DEFAULTS[key])


# ── Stages and the freeze point (R6) ────────────────────────────────────────

# How far a review has gone. The freeze point says at which step the numbers stop
# taking new facts: "Self-review sent" is the move into Manager Review, "Manager
# review sent" the move into Employee Final Review, "HR sent" the move to Completed.
STAGE_STEP = {
    "Not Started": 0,
    "Employee Review": 0,
    "Manager Review": 1,
    "Employee Final Review": 2,
    "HR Review": 3,
    "Completed": 4,
}
FREEZE_STEP = {FREEZE_SELF_SENT: 1, FREEZE_MANAGER_SENT: 2, FREEZE_HR_SENT: 4}


def is_past_freeze_point(review_status, freeze_point):
    """Has this review reached the step where its numbers freeze?

    An unknown stage or freeze point counts as frozen: no new fact reaches the
    copies until someone looks (SEC-21 fails closed).
    """
    step = STAGE_STEP.get(review_status or "Not Started")
    freeze_at = FREEZE_STEP.get(freeze_point)
    if step is None or freeze_at is None:
        return True
    return step >= freeze_at


# ── Taking the copies (R1, decision 4, R16) ─────────────────────────────────

DEFINITION_FIELDS = (
    "title", "description", "unit", "direction", "category", "progress_mode",
    "baseline_value", "target_value", "weightage", "period_start", "period_end",
)

_KPI_FIELDS = [
    "name", "kpi_name", "description", "unit", "direction", "category", "progress_mode",
    "baseline_value", "target_value", "weightage", "period_start", "period_end",
    "individual_goal", "status",
]
_GOAL_FIELDS = [
    "name", "goal_name", "unit", "goal_type", "progress_mode", "target_value", "weightage",
    "start_date", "end_date", "status", "docstatus",
]


def open_review(ext):
    """Called by a review screen once the caller has been allowed in.

    The first open takes the copies; later opens bring their numbers up to date
    (the safety net for any path that changed a fact without saving its parent).
    Returns True when the record was written, so the caller can commit.
    """
    if ensure_review_items(ext):
        return True
    return refresh_review_items(ext)


def ensure_review_items(ext):
    """Take this review's copies, once. A second call changes nothing (VIS-4).

    Copied: the employee's Objectives and KPIs tagged to the review's cycle that
    are not cancelled and not future plans (VIS-14, VIS-15), plus any item still
    held by another open review whose period overlaps this one (R16). The review
    period, freeze point and removal setting in force now are stamped on the
    Extension, so a later settings change does not touch this review (SEC-21).

    Not taken for a Completed review (the migration copies history as it was
    stored) or when the appraisal is cancelled.
    """
    if ext.is_new() or ext.get("items_taken_on"):
        return False
    if (ext.review_status or "Not Started") == "Completed":
        return False

    ap = frappe.db.get_value(
        "Appraisal", ext.appraisal,
        ["employee", "appraisal_cycle", "start_date", "end_date", "docstatus"], as_dict=True,
    )
    if not ap or ap.docstatus == 2:
        return False

    start, end = ap.start_date, ap.end_date
    if not (start and end) and ap.appraisal_cycle:
        cycle = frappe.db.get_value(
            "Appraisal Cycle", ap.appraisal_cycle, ["start_date", "end_date"], as_dict=True
        ) or {}
        start = start or cycle.get("start_date")
        end = end or cycle.get("end_date")

    settings = review_settings()
    ext.employee = ext.employee or ap.employee
    ext.appraisal_cycle = ext.appraisal_cycle or ap.appraisal_cycle
    ext.review_window_start = start
    ext.review_window_end = end
    ext.freeze_point = settings["freeze_point"]
    ext.removal_mode = settings["removal_mode"]
    ext.items_taken_on = now_datetime()

    goals, kpis = _items_for_review(ext, ap, start, end)

    # Objectives first, so a KPI can point at its Objective's row. Row names are
    # set here: the Extension already exists, and Frappe keeps a child row's name
    # when the parent is updated (Document.set_name_in_children).
    goal_rows = {}
    for goal in goals:
        row = ext.append("review_items", _goal_copy(goal))
        row.name = frappe.generate_hash(length=10)
        goal_rows[goal.name] = row.name
    for kpi in kpis:
        values = _kpi_copy(kpi)
        values["parent_item"] = goal_rows.get(kpi.individual_goal) or ""
        row = ext.append("review_items", values)
        row.name = frappe.generate_hash(length=10)

    _recount(ext)
    if is_past_freeze_point(ext.review_status, ext.freeze_point):
        ext.frozen = 1
        ext.frozen_on = now_datetime()
    raise_rating_flags(ext)
    save_review_record(ext)
    return True


def _items_for_review(ext, ap, start, end):
    """The originals this review copies. At most five bounded queries."""
    if not ap.appraisal_cycle:
        return [], []
    goals = frappe.get_all(
        "Individual Goal",
        filters={
            "employee": ap.employee,
            "appraisal_cycle": ap.appraisal_cycle,
            "docstatus": ["!=", 2],
            "status": ["!=", "Cancelled"],
            "is_future_plan": ["!=", 1],
        },
        fields=_GOAL_FIELDS,
        order_by="creation asc",
    )
    kpis = frappe.get_all(
        "KPI",
        filters={"employee": ap.employee, "appraisal_cycle": ap.appraisal_cycle, "status": ["!=", "Cancelled"]},
        fields=_KPI_FIELDS,
        order_by="creation asc",
    )
    if not (start and end):
        return goals, kpis

    held_goals, held_kpis = _held_by_other_open_reviews(ap.employee, ext.name)
    held_goals -= {g.name for g in goals}
    held_kpis -= {k.name for k in kpis}
    if held_goals:
        goals += frappe.get_all(
            "Individual Goal",
            filters={
                "name": ["in", sorted(held_goals)],
                "docstatus": ["!=", 2],
                "status": ["!=", "Cancelled"],
                "is_future_plan": ["!=", 1],
                "start_date": ["<=", end],
                "end_date": [">=", start],
            },
            fields=_GOAL_FIELDS,
            order_by="creation asc",
        )
    if held_kpis:
        kpis += frappe.get_all(
            "KPI",
            filters={
                "name": ["in", sorted(held_kpis)],
                "status": ["!=", "Cancelled"],
                "period_start": ["<=", end],
                "period_end": [">=", start],
            },
            fields=_KPI_FIELDS,
            order_by="creation asc",
        )
    return goals, kpis


def _held_by_other_open_reviews(employee, ext_name):
    """Originals with a live copy in another of this employee's open reviews (R16)."""
    item = frappe.qb.DocType("Alvoraa Review Item")
    other = frappe.qb.DocType("Alvoraa Appraisal Extension")
    appraisal = frappe.qb.DocType("Appraisal")
    rows = (
        frappe.qb.from_(item)
        .join(other).on(item.parent == other.name)
        .join(appraisal).on(appraisal.name == other.appraisal)
        .select(item.source_doctype, item.source_name)
        .where(item.parenttype == "Alvoraa Appraisal Extension")
        .where(other.employee == employee)
        .where(other.name != ext_name)
        .where(other.review_status != "Completed")
        .where(appraisal.docstatus != 2)
        .where(item.removed == 0)
    ).run(as_dict=True)
    goals = {r.source_name for r in rows if r.source_doctype == "Individual Goal"}
    kpis = {r.source_name for r in rows if r.source_doctype == "KPI"}
    return goals, kpis


def _kpi_copy(kpi):
    values = {
        "item_type": "KPI",
        "source_doctype": "KPI",
        "source_name": kpi.name,
        "title": kpi.kpi_name,
        "description": kpi.description,
        "unit": kpi.unit,
        "direction": kpi.direction or "Higher is Better",
        "category": kpi.category,
        "progress_mode": kpi.progress_mode or "Cumulative",
        "baseline_value": flt(kpi.baseline_value),
        "target_value": flt(kpi.target_value),
        "weightage": flt(kpi.weightage),
        "period_start": kpi.period_start,
        "period_end": kpi.period_end,
    }
    values["definition_at_start"] = _definition_json(values)
    return values


def _goal_copy(goal):
    values = {
        "item_type": "Objective",
        "source_doctype": "Individual Goal",
        "source_name": goal.name,
        "title": goal.goal_name,
        "description": "",
        "unit": goal.unit,
        "direction": "",
        "category": goal.goal_type,
        "progress_mode": goal.progress_mode or "Cumulative",
        "baseline_value": 0,
        "target_value": flt(goal.target_value),
        "weightage": flt(goal.weightage),
        "period_start": goal.start_date,
        "period_end": goal.end_date,
    }
    values["definition_at_start"] = _definition_json(values)
    return values


def _definition_json(values):
    out = {}
    for field in DEFINITION_FIELDS:
        value = values.get(field)
        if field in ("baseline_value", "target_value", "weightage"):
            value = flt(value, 6)
        elif field in ("period_start", "period_end"):
            value = str(getdate(value)) if value else ""
        else:
            value = cstr(value)
        out[field] = value
    return json.dumps(out, sort_keys=True)


def save_review_record(ext):
    """The only way the review's copies are written.

    The caller has already decided the person may do this. The Extension has no
    role rules for employees or managers any more (SEC-5), so the save does not
    ask Frappe's role table a second time.
    """
    ext.flags[REVIEW_ITEMS_WRITE_FLAG] = True
    try:
        ext.save(ignore_permissions=True)
    finally:
        ext.flags[REVIEW_ITEMS_WRITE_FLAG] = False


# ── Counting facts by date (R3, R4, R16, decision 1, decision 5) ────────────


def refresh_review_items(ext, save=True):
    """Bring an open, unfrozen review's copies up to date with the live facts.

    Writes only when a number or a flag changed. Returns True if something
    changed.
    """
    if ext.is_new() or not ext.get("items_taken_on") or cint(ext.get("frozen")):
        return False
    if (ext.review_status or "") == "Completed":
        return False
    changed = _recount(ext)
    changed = raise_rating_flags(ext) or changed
    if changed and save:
        save_review_record(ext)
    return changed


def _recount(ext):
    """Recompute every live copy from approved facts. Five queries at most.

    Actual, by the copy's own progress mode (R4 and decision 1):
      KPI, Cumulative        sum of approved readings dated in the window
      KPI, Absolute          latest approved reading dated in the window
      Objective, Cumulative  sum of approved evidence dated in the window
      Objective, Absolute    latest approved goal update in the window,
                             or, with none, the latest approved evidence

    The window is the review period narrowed by the copy's own period. Each
    review counts only its own window, so overlapping reviews split facts by
    date (R16). Evidence with no date of its own is dated by its upload
    (decision 5) and counted in facts_dated_by_upload for HR.
    """
    rows = [r for r in (ext.get("review_items") or []) if not cint(r.removed)]
    if not rows:
        return False

    start = getdate(ext.review_window_start) if ext.get("review_window_start") else None
    end = getdate(ext.review_window_end) if ext.get("review_window_end") else None

    kpi_names = sorted({r.source_name for r in rows if r.source_doctype == "KPI" and r.source_name})
    goal_names = sorted({r.source_name for r in rows if r.source_doctype == "Individual Goal" and r.source_name})

    readings, evidence, updates, cancelled = {}, {}, {}, set()
    if start and end and kpi_names:
        for f in frappe.get_all(
            "KPI Progress Log",
            filters={"parenttype": "KPI", "parent": ["in", kpi_names], "approval_status": "Approved",
                     "log_date": ["between", [start, end]]},
            fields=["parent", "value", "log_date", "approved_on", "creation"],
        ):
            readings.setdefault(f.parent, []).append(f)
    if start and end and goal_names:
        # The date rule needs the fallbacks, so the database narrows by any of the
        # three dates and _evidence_date decides.
        for f in frappe.get_all(
            "Goal Evidence",
            filters={"parenttype": "Individual Goal", "parent": ["in", goal_names], "validation_status": "Approved"},
            or_filters=[
                ["extracted_date", "between", [start, end]],
                ["upload_date", "between", [start, end]],
                ["creation", "between", [start, end]],
            ],
            fields=["parent", "value", "extracted_date", "upload_date", "creation"],
        ):
            evidence.setdefault(f.parent, []).append(f)
        for f in frappe.get_all(
            "Goal Progress Update",
            filters={"parenttype": "Individual Goal", "parent": ["in", goal_names], "approval_status": "Approved",
                     "log_date": ["between", [start, end]]},
            fields=["parent", "value", "log_date", "approved_on", "creation"],
        ):
            updates.setdefault(f.parent, []).append(f)
    if kpi_names:
        cancelled |= set(frappe.get_all(
            "KPI", filters={"name": ["in", kpi_names], "status": "Cancelled"}, pluck="name"
        ))
    if goal_names:
        cancelled |= set(frappe.get_all(
            "Individual Goal",
            filters={"name": ["in", goal_names]},
            or_filters=[["status", "=", "Cancelled"], ["docstatus", "=", 2]],
            pluck="name",
        ))

    changed = False
    for row in rows:
        numbers = _numbers_for(row, start, end, readings, evidence, updates)
        numbers["source_cancelled"] = int(row.source_name in cancelled)
        if any(_rounded(row.get(k)) != _rounded(v) for k, v in numbers.items()):
            row.update(numbers)
            row.facts_as_of = now_datetime()
            changed = True
    return changed


def _numbers_for(row, review_start, review_end, readings, evidence, updates):
    empty = {"actual_value": 0, "attainment_pct": 0, "facts_count": 0, "facts_dated_by_upload": 0}
    if not (review_start and review_end):
        # No review period means nothing can be placed in it. Fail closed.
        return empty
    start = max(review_start, getdate(row.period_start)) if row.period_start else review_start
    end = min(review_end, getdate(row.period_end)) if row.period_end else review_end
    if start > end:
        return empty

    absolute = (row.progress_mode or "Cumulative") == "Absolute"
    target = flt(row.target_value)

    if row.source_doctype == "KPI":
        facts = [f for f in readings.get(row.source_name, []) if start <= getdate(f.log_date) <= end]
        if not facts:
            return empty
        if absolute:
            actual = flt(max(facts, key=_reading_order).value)
        else:
            actual = sum(flt(f.value) for f in facts)
        return {
            "actual_value": flt(actual, 6),
            "attainment_pct": attainment(actual, target, row.direction),
            "facts_count": len(facts),
            "facts_dated_by_upload": 0,
        }

    dated = []
    for f in evidence.get(row.source_name, []):
        on, by_upload = _evidence_date(f)
        if on and start <= on <= end:
            dated.append((on, by_upload, f))
    goal_updates = [f for f in updates.get(row.source_name, []) if start <= getdate(f.log_date) <= end]

    if absolute and goal_updates:
        actual = flt(max(goal_updates, key=_reading_order).value)
        count, by_upload_count = len(goal_updates), 0
    elif absolute and dated:
        latest = max(dated, key=lambda d: (d[0], get_datetime(d[2].creation)))
        actual = flt(latest[2].value)
        count, by_upload_count = len(dated), sum(1 for d in dated if d[1])
    elif not absolute and dated:
        actual = sum(flt(d[2].value) for d in dated)
        count, by_upload_count = len(dated), sum(1 for d in dated if d[1])
    else:
        return empty

    # The same formula as controllers.goal.recalculate_progress.
    progress = min(actual / target * 100, 100) if target else 0
    return {
        "actual_value": flt(actual, 6),
        "attainment_pct": flt(progress, 2),
        "facts_count": count,
        "facts_dated_by_upload": by_upload_count,
    }


def _reading_order(fact):
    """Latest reading last: its date, then when it was approved, then created."""
    approved = get_datetime(fact.approved_on) if fact.get("approved_on") else datetime.min
    return (getdate(fact.log_date), approved, get_datetime(fact.creation))


def _evidence_date(fact):
    """(date, dated_by_upload): the evidence's own date, else its upload, else creation."""
    if fact.get("extracted_date"):
        return getdate(fact.extracted_date), False
    if fact.get("upload_date"):
        return getdate(fact.upload_date), True
    if fact.get("creation"):
        return getdate(fact.creation), True
    return None, True


def _rounded(value):
    return flt(value, 2)


# ── Rating stamps and flags (R7) ────────────────────────────────────────────
#
# Every rating remembers the numbers it was given on. When those numbers change
# the rating is flagged, so the rater can keep or change it. Flags are only
# raised here; answering one is what clears it. Stamps and flags are written by
# the server, never taken from a client (SEC-23).

_BASIS = (("actual", "actual_value"), ("target", "target_value"), ("weightage", "weightage"))


def stamp_rating(row, kind, user=None):
    """Stamp a self or manager rating on a copy with that copy's numbers now."""
    if kind not in ("self", "manager"):
        raise ValueError(kind)
    for part, source in _BASIS:
        row.set(f"{kind}_basis_{part}", _rounded(row.get(source)))
    row.set(f"{kind}_flag", 0)
    if kind == "self":
        row.self_rated_on = now_datetime()
    else:
        row.manager_rated_by = user or frappe.session.user
        row.manager_rated_on = now_datetime()


def overall_basis(ext):
    """Every copy's numbers, as the overall rating's stamp."""
    return {
        row.name: [_rounded(row.actual_value), _rounded(row.target_value), _rounded(row.weightage), cint(row.removed)]
        for row in (ext.get("review_items") or [])
    }


def stamp_overall_rating(ext, user=None):
    """Stamp the overall rating with every copy's numbers now."""
    ext.overall_rating_basis = json.dumps(overall_basis(ext), sort_keys=True)
    ext.overall_rating_flag = 0
    ext.overall_rated_by = user or frappe.session.user
    ext.overall_rated_on = now_datetime()


def raise_rating_flags(ext):
    """Flag every rating whose numbers moved since it was given. Returns True if
    a flag went up.

    A rating with no stamp at all counts as moved (SEC-23 fails closed): nobody
    can show which numbers it was given on.
    """
    raised = False
    for row in ext.get("review_items") or []:
        if cint(row.removed):
            continue
        for kind in ("self", "manager"):
            if flt(row.get(f"{kind}_rating")) <= 0 or cint(row.get(f"{kind}_flag")):
                continue
            stamped = row.get("self_rated_on" if kind == "self" else "manager_rated_on")
            moved = any(
                _rounded(row.get(f"{kind}_basis_{part}")) != _rounded(row.get(source))
                for part, source in _BASIS
            )
            if not stamped or moved:
                row.set(f"{kind}_flag", 1)
                raised = True

    if flt(ext.get("overall_rating")) > 0 and not cint(ext.get("overall_rating_flag")):
        try:
            basis = json.loads(ext.overall_rating_basis) if ext.get("overall_rating_basis") else None
        except ValueError:
            basis = None
        if basis is None or basis != overall_basis(ext):
            ext.overall_rating_flag = 1
            raised = True
    return raised


def custom_docperm_report():
    """Read-only. Tenant permission rows that would reopen review records (M3).

    A Custom DocPerm replaces a DocType's shipped permissions on that site, so a
    tenant that once re-granted Employee keeps that grant after this slice. This
    lists such rows and changes nothing; removing one is the tenant's decision.

    Run on a site before deploying:
        bench --site <site> execute alvoraa_goals.review_items.custom_docperm_report

    Reported:
      Alvoraa Appraisal Extension  any right for a role that is not HR
      Appraisal                    write, create or delete for a role that is not HR
      KPI                          any right at level 1 or above for a role that is not HR
    """
    hr = {"HR Manager", "HR User", "System Manager", "Administrator"}
    rows = frappe.get_all(
        "Custom DocPerm",
        filters={"parent": ["in", ["Alvoraa Appraisal Extension", "Appraisal", "KPI"]]},
        fields=["parent", "role", "permlevel", "read", "write", "create", "delete"],
        order_by="parent asc, role asc, permlevel asc",
    )
    found = []
    for r in rows:
        if r.role in hr:
            continue
        rights = [p for p in ("read", "write", "create", "delete") if cint(r.get(p))]
        if r.parent == "Alvoraa Appraisal Extension" and rights:
            why = "Opens review records to a role that is not HR"
        elif r.parent == "Appraisal" and set(rights) & {"write", "create", "delete"}:
            why = "Lets a role that is not HR change appraisals"
        elif r.parent == "KPI" and cint(r.permlevel) >= 1 and rights:
            why = "Opens restricted KPI fields to a role that is not HR"
        else:
            continue
        found.append({
            "doctype": r.parent, "role": r.role, "permlevel": cint(r.permlevel),
            "rights": rights, "why": why,
        })
    return found


def open_blocking_flags(ext):
    """Flags that stop HR completing the review: manager ratings and the overall
    rating. Self-rating flags are information only (decision 13)."""
    count = sum(
        1 for row in (ext.get("review_items") or [])
        if not cint(row.removed) and cint(row.manager_flag)
    )
    return count + cint(ext.get("overall_rating_flag"))
