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
from frappe.utils import add_days, cint, cstr, flt, get_datetime, getdate, now_datetime, nowdate

from alvoraa_goals.alvoraa_goals.doctype.alvoraa_appraisal_extension.alvoraa_appraisal_extension import (
    REVIEW_ITEMS_WRITE_FLAG,
)
from alvoraa_goals.controllers.kpi import MAX_RATING, attainment

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

    start, end = _window(ext)
    kpi_names, goal_names = _source_names(rows)
    readings, evidence, updates = _load_facts(rows, start, end)
    cancelled = set()
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


def _window(ext):
    start = getdate(ext.review_window_start) if ext.get("review_window_start") else None
    end = getdate(ext.review_window_end) if ext.get("review_window_end") else None
    return start, end


def _source_names(rows):
    kpis = sorted({r.source_name for r in rows if r.source_doctype == "KPI" and r.source_name})
    goals = sorted({r.source_name for r in rows if r.source_doctype == "Individual Goal" and r.source_name})
    return kpis, goals


def _load_facts(rows, start, end):
    """Approved facts for these copies, dated in the review period. Three queries at most."""
    readings, evidence, updates = {}, {}, {}
    if not (start and end):
        return readings, evidence, updates
    kpi_names, goal_names = _source_names(rows)
    if kpi_names:
        for f in frappe.get_all(
            "KPI Progress Log",
            filters={"parenttype": "KPI", "parent": ["in", kpi_names], "approval_status": "Approved",
                     "log_date": ["between", [start, end]]},
            fields=["parent", "value", "log_date", "approved_on", "creation"],
        ):
            readings.setdefault(f.parent, []).append(f)
    if goal_names:
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
            fields=["parent", "value", "extracted_date", "upload_date", "approved_on", "creation"],
        ):
            evidence.setdefault(f.parent, []).append(f)
        for f in frappe.get_all(
            "Goal Progress Update",
            filters={"parenttype": "Individual Goal", "parent": ["in", goal_names], "approval_status": "Approved",
                     "log_date": ["between", [start, end]]},
            fields=["parent", "value", "log_date", "approved_on", "creation"],
        ):
            updates.setdefault(f.parent, []).append(f)
    return readings, evidence, updates


def _row_window(row, review_start, review_end):
    """The review period narrowed by the copy's own period, or None if they do not meet."""
    if not (review_start and review_end):
        return None
    start = max(review_start, getdate(row.period_start)) if row.period_start else review_start
    end = min(review_end, getdate(row.period_end)) if row.period_end else review_end
    return (start, end) if start <= end else None


def _facts_in_window(row, window, readings, evidence, updates):
    """Every fact counted for this copy, as (fact, dated_by_upload)."""
    start, end = window
    if row.source_doctype == "KPI":
        return [(f, False) for f in readings.get(row.source_name, []) if start <= getdate(f.log_date) <= end]
    out = [(f, False) for f in updates.get(row.source_name, []) if start <= getdate(f.log_date) <= end]
    for f in evidence.get(row.source_name, []):
        on, by_upload = _evidence_date(f)
        if on and start <= on <= end:
            out.append((f, by_upload))
    return out


def _numbers_for(row, review_start, review_end, readings, evidence, updates):
    empty = {"actual_value": 0, "attainment_pct": 0, "facts_count": 0, "facts_dated_by_upload": 0}
    window = _row_window(row, review_start, review_end)
    if not window:
        # No review period means nothing can be placed in it. Fail closed.
        return empty
    start, end = window

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
      Appraisal                    any right for a role that is not HR (decision 26
                                   removed Employee read as well as write)
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
        elif r.parent == "Appraisal" and rights:
            why = "Lets a role that is not HR read appraisal scores outside the portal"
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


# ── What a review screen receives (commit 4: VIS-3, PRIV-1, PRIV-11, PRIV-12, PRIV-13) ─
#
# One place decides which copy fields each viewer gets, so the review screens
# cannot drift apart. A copy is addressed by its row name only: the name of the
# live Objective or KPI it came from never leaves the server (VIS-3).

VIEWER_SUBJECT = "subject"
VIEWER_MANAGER = "manager"
VIEWER_HR = "hr"
VIEWER_REVIEWER = "reviewer"
VIEWERS = (VIEWER_SUBJECT, VIEWER_MANAGER, VIEWER_HR, VIEWER_REVIEWER)

SELF_REVIEW_DRAFT = ("Not Started", "Employee Review")
RATING_RELEASED = ("Employee Final Review", "HR Review", "Completed")

# Definition fields a review may change on its copy (R2 inside the review).
EDITABLE_DEFINITION = ("title", "target_value", "weightage", "period_start", "period_end")

_STAMP_FIELDS = (
    "self_basis_actual", "self_basis_target", "self_basis_weightage", "self_flag",
    "manager_rated_by", "manager_rated_on",
    "manager_basis_actual", "manager_basis_target", "manager_basis_weightage", "manager_flag",
    "manager_flag_answered_by", "manager_flag_answered_on",
)


# A viewer that may see the review's status and counts but no rating at all:
# HR for someone outside their line while the review is still before HR Review
# (SEC-26). Never passed to review_payload; HR cycle screens only.
VIEWER_NONE = "none"

SELF_FIELDS = ("self_rating", "self_comment")
MANAGER_FIELDS = ("manager_rating", "manager_comment")
POTENTIAL_FIELDS = ("potential_rating", "potential_comment")


def rating_fields_for(viewer, status):
    """Which rating and comment fields of a copy this viewer may see at this stage.

    The one rule for every screen that shows copies, so the review screens and
    HR's cycle screens cannot drift apart (PRIV-1, PRIV-2, SEC-26):

      subject   own self fields; manager fields from Employee Final Review;
                never potential
      manager   self fields once sent; manager and potential fields
      hr        the same as the manager
      reviewer  self fields once sent
      none, or anything unknown: nothing
    """
    status = status or "Not Started"
    sent = status not in SELF_REVIEW_DRAFT
    if viewer == VIEWER_SUBJECT:
        return SELF_FIELDS + (MANAGER_FIELDS if status in RATING_RELEASED else ())
    if viewer in (VIEWER_MANAGER, VIEWER_HR):
        return (SELF_FIELDS if sent else ()) + MANAGER_FIELDS + POTENTIAL_FIELDS
    if viewer == VIEWER_REVIEWER:
        return SELF_FIELDS if sent else ()
    return ()


def overall_rating_visible(viewer, status):
    """The review's overall rating: the subject from Employee Final Review
    (decision 3); the manager line and HR always; nobody else."""
    if viewer == VIEWER_SUBJECT:
        return (status or "Not Started") in RATING_RELEASED
    return viewer in (VIEWER_MANAGER, VIEWER_HR)


def late_fact_counts(reviews, rows_by_review):
    """R10 for many reviews at once: how many facts dated in each frozen review's
    period were approved after it froze, per copy. Three queries in all.

    reviews: dicts with name, frozen, frozen_on, review_window_start and
    review_window_end. rows_by_review: review name -> its copies (dicts).
    Returns copy row name -> count, for copies with at least one.
    """
    frozen = [r for r in reviews if cint(r.get("frozen")) and r.get("frozen_on")
              and r.get("review_window_start") and r.get("review_window_end")]
    rows = [row for r in frozen for row in rows_by_review.get(r["name"], []) if not cint(row.get("removed"))]
    if not rows:
        return {}
    start = min(getdate(r["review_window_start"]) for r in frozen)
    end = max(getdate(r["review_window_end"]) for r in frozen)
    readings, evidence, updates = _load_facts(rows, start, end)

    out = {}
    for r in frozen:
        r_start, r_end = getdate(r["review_window_start"]), getdate(r["review_window_end"])
        frozen_on = get_datetime(r["frozen_on"])
        for row in rows_by_review.get(r["name"], []):
            if cint(row.get("removed")):
                continue
            window = _row_window(frappe._dict(row), r_start, r_end)
            if not window:
                continue
            count = sum(
                1 for f, _by_upload in _facts_in_window(frappe._dict(row), window, readings, evidence, updates)
                if get_datetime(f.get("approved_on") or f.get("creation")) > frozen_on
            )
            if count:
                out[row["name"]] = count
    return out


def _date(value):
    return str(getdate(value)) if value else ""


def definition_changes(row):
    """Editable definition fields changed inside the review: field -> value at the start."""
    try:
        start = json.loads(row.definition_at_start or "{}")
    except ValueError:
        return {}
    now = json.loads(_definition_json(row.as_dict()))
    return {f: start.get(f) for f in EDITABLE_DEFINITION if f in start and start.get(f) != now.get(f)}


def review_payload(ext, viewer, employee=None, employee_name=""):
    """The review's items, cut to what this viewer may see at this stage.

    viewer is one of VIEWERS and is decided by the endpoint after its own
    checks. An unknown viewer gets nothing (fail closed).

      subject   own self fields always; manager ratings and removals (label,
                date, reason) from Employee Final Review (decisions 10, 11);
                never potential, stamps, flags or late facts
      manager   everything but late facts
      hr        everything, and facts that arrived after the numbers froze
      reviewer  definitions and numbers, plus self fields once sent; nothing
                about manager ratings, potential, stamps, flags or removals
    """
    if viewer not in VIEWERS:
        return {"goals": [], "standalone_kpis": [], "removed_items": []}

    status = ext.review_status or "Not Started"
    deciders = viewer in (VIEWER_MANAGER, VIEWER_HR)
    allowed = rating_fields_for(viewer, status)
    see_self = "self_rating" in allowed
    see_manager = "manager_rating" in allowed
    rows = list(ext.get("review_items") or [])
    live = [r for r in rows if not cint(r.removed)]
    live_names = {r.name for r in live}
    late = late_facts(ext) if viewer == VIEWER_HR and status in ("HR Review", "Completed") else {}

    def item(row):
        out = {
            "name": row.name,
            "item_type": row.item_type,
            "title": row.title or "",
            "description": row.description or "",
            "unit": row.unit or "",
            "direction": row.direction or "",
            "category": row.category or "",
            "progress_mode": row.progress_mode or "",
            "baseline_value": flt(row.baseline_value),
            "target_value": flt(row.target_value),
            "weightage": flt(row.weightage),
            "period_start": _date(row.period_start),
            "period_end": _date(row.period_end),
            "actual_value": flt(row.actual_value),
            "attainment_pct": flt(row.attainment_pct),
            "facts_count": cint(row.facts_count),
            "source_cancelled": cint(row.source_cancelled),
            "added_in_review": cint(row.added_in_review),
            "employee": employee or "",
            "employee_name": employee_name or "",
        }
        if viewer != VIEWER_REVIEWER:
            out["definition_changed"] = definition_changes(row)
        if see_self:
            out["self_rating"] = flt(row.self_rating)
            out["self_comment"] = row.self_comment or ""
        if see_manager:
            out["manager_rating"] = flt(row.manager_rating)
            out["manager_comment"] = row.manager_comment or ""
        if deciders:
            out["potential_rating"] = flt(row.potential_rating)
            out["potential_comment"] = row.potential_comment or ""
            for field in _STAMP_FIELDS:
                value = row.get(field)
                out[field] = str(value) if value not in (None, "") and field.endswith("_on") else (
                    value if value is not None else "")
        if viewer == VIEWER_HR:
            out["facts_dated_by_upload"] = cint(row.facts_dated_by_upload)
            if row.name in late:
                out["late_facts"] = late[row.name]
        return out

    goals, standalone = [], []
    goal_out = {}
    for row in live:
        if row.item_type != "Objective":
            continue
        g = item(row)
        # The keys the review page reads today.
        g.update({
            "goal_name": g["title"], "actual_progress": g["actual_value"], "progress_pct": g["attainment_pct"],
            "start_date": g["period_start"], "end_date": g["period_end"], "parent_goal": "",
            "status": "Cancelled" if g["source_cancelled"] else "Active", "kpis": [],
        })
        goal_out[row.name] = g
        goals.append(g)
    for row in live:
        if row.item_type == "Objective":
            continue
        k = item(row)
        k["kpi_name"] = k["title"]
        k["status"] = "Cancelled" if k["source_cancelled"] else "Active"
        parent = goal_out.get(row.parent_item) if row.parent_item in live_names else None
        (parent["kpis"] if parent else standalone).append(k)

    removed = []
    if viewer != VIEWER_REVIEWER:
        for row in rows:
            if not cint(row.removed):
                continue
            if (viewer == VIEWER_SUBJECT and status not in RATING_RELEASED
                    and (row.removed_at_stage or "") not in SELF_REVIEW_DRAFT):
                # Before Employee Final Review the subject sees only their own removals.
                continue
            entry = {
                "name": row.name, "item_type": row.item_type, "title": row.title or "",
                "removed_on": str(row.removed_on) if row.removed_on else "",
                "removal_reason": row.removal_reason or "",
            }
            if deciders:
                entry.update({"removed_by": row.removed_by or "", "removed_at_stage": row.removed_at_stage or ""})
            removed.append(entry)

    out = {
        "goals": goals,
        "standalone_kpis": standalone,
        "removed_items": removed,
        "numbers_frozen": cint(ext.frozen),
        "frozen_on": str(ext.frozen_on) if ext.frozen_on else "",
    }
    if deciders:
        out["overall_rating_flag"] = cint(ext.overall_rating_flag)
        out["open_blocking_flags"] = open_blocking_flags(ext)
    return out


def late_facts(ext):
    """R10: facts dated inside a frozen review's period that were approved after
    it froze. They never change a copy; HR sees them (PRIV-11). Three queries.

    Returns row name -> {"count": n, "actual_with_late": number}.
    """
    if not cint(ext.get("frozen")) or not ext.get("frozen_on"):
        return {}
    rows = [r for r in (ext.get("review_items") or []) if not cint(r.removed)]
    start, end = _window(ext)
    if not rows or not (start and end):
        return {}
    frozen_on = get_datetime(ext.frozen_on)
    readings, evidence, updates = _load_facts(rows, start, end)

    out = {}
    for row in rows:
        window = _row_window(row, start, end)
        if not window:
            continue
        count = sum(
            1 for f, _by_upload in _facts_in_window(row, window, readings, evidence, updates)
            if get_datetime(f.get("approved_on") or f.get("creation")) > frozen_on
        )
        if count:
            with_late = _numbers_for(row, start, end, readings, evidence, updates)
            out[row.name] = {"count": count, "actual_with_late": with_late["actual_value"]}
    return out


def copied_sources(ext):
    """Names of the live records this review holds copies of. Server side only."""
    return {r.source_name for r in (ext.get("review_items") or []) if r.source_name}


# ── Changes made on the copies (commit 5: SEC-1, R2, R7, R11, R12, VIS-5, VIS-6) ─
#
# These change the review record in memory. The endpoint has already decided who
# the caller is and whether the stage allows it; it saves with save_review_record.
# Nothing here writes a KPI or an Objective (R13).


def live_row(ext, row_name):
    """This review's copy with that row name, or None. Removed copies do not count."""
    if not row_name or not isinstance(row_name, str):
        return None
    for row in ext.get("review_items") or []:
        if row.name == row_name and not cint(row.removed):
            return row
    return None


def is_rated(row):
    return any(flt(row.get(f)) > 0 for f in ("self_rating", "manager_rating", "potential_rating"))


def rating_value(value, what="Rating"):
    """A rating that was really sent, or None when nothing was sent. 0 means nothing."""
    if value in (None, ""):
        return None
    try:
        rating = float(value)
    except (TypeError, ValueError):
        frappe.throw(_("{0} must be a number between 1 and {1}.").format(_(what), int(MAX_RATING)))
    if rating <= 0:
        return None
    if rating > MAX_RATING:
        frappe.throw(_("{0} must be a number between 1 and {1}.").format(_(what), int(MAX_RATING)))
    return rating


def _refuse(message, rule, endpoint, ext):
    from hrms.alvoraa_hr_core.access import refuse

    refuse(message, rule, endpoint, "Alvoraa Appraisal Extension", ext.name)


def apply_self_review(ext, past_objectives, endpoint="submit_employee_review", write=True):
    """Write the self-review's ratings and comments onto this review's copies (SEC-1).

    Keys must be row names of this review's live copies. One key that is not
    refuses the whole call: nothing is written. Progress typed on the page is
    never written anywhere; progress comes from dated facts (decision 4).
    With write=False only the keys are checked (a draft page save).
    """
    past = past_objectives if isinstance(past_objectives, dict) else {}
    kpis = past.get("kpis") or {}
    objectives = past.get("objectives") or {}
    if not isinstance(kpis, dict) or not isinstance(objectives, dict):
        _refuse(_("The self-review could not be read. Reload the page and try again."), "SEC-1", endpoint, ext)
    for key in list(kpis) + list(objectives):
        if not live_row(ext, key):
            _refuse(_("The self-review names an item that is not in this review."), "SEC-1", endpoint, ext)
    if not write:
        return

    for key, values in kpis.items():
        values = values if isinstance(values, dict) else {}
        row = live_row(ext, key)
        rating = rating_value(values.get("self_rating"), "Self-rating")
        if rating is not None:
            row.self_rating = rating
        if values.get("self_comment") is not None:
            row.self_comment = cstr(values.get("self_comment"))
        if rating is not None:
            stamp_rating(row, "self")
    for key, values in objectives.items():
        values = values if isinstance(values, dict) else {}
        if values.get("reflection") is not None:
            live_row(ext, key).self_comment = cstr(values.get("reflection"))


def set_item_rating(row, kind, rating=None, comment=None, potential=None, potential_comment=None, user=None):
    """A self or manager rating on one copy, stamped with the copy's numbers now (R7)."""
    rating = rating_value(rating)
    if rating is not None:
        row.set(f"{kind}_rating", rating)
    if comment is not None:
        row.set(f"{kind}_comment", cstr(comment))
    if kind == "manager":
        potential = rating_value(potential, "Potential rating")
        if potential is not None:
            row.potential_rating = potential
        if potential_comment is not None:
            row.potential_comment = cstr(potential_comment)
    if rating is not None:
        stamp_rating(row, kind, user)


def remove_item(ext, row, reason, stage, user=None):
    """Take a copy out of the review (R12). Returns "kept" or "discarded".

    Discarded only when the review's stamped setting says so AND nothing on the
    copy is rated: a rated copy is always kept, marked Removed (decision 9). An
    unknown setting keeps it (fail closed). The live record, its facts and its
    evidence are untouched.
    """
    user = user or frappe.session.user
    keep = ext.get("removal_mode") != REMOVAL_DISCARD or is_rated(row)
    if keep:
        row.removed = 1
        row.removed_by = user
        row.removed_on = now_datetime()
        row.removal_reason = cstr(reason)
        row.removed_at_stage = stage
    else:
        for other in ext.get("review_items") or []:
            if other.parent_item == row.name:
                other.parent_item = ""
        ext.remove(row)
    raise_rating_flags(ext)
    return "kept" if keep else "discarded"


def add_items(ext, employee, goal_names=(), kpi_names=(), user=None):
    """Add copies of the subject's own live Objectives and KPIs (VIS-5).

    Each must belong to the subject, not be cancelled or a future plan, and meet
    the review period. An Objective brings its KPIs with it. Anything else
    refuses the whole call. Returns the number of copies added.
    """
    user = user or frappe.session.user
    goal_names, kpi_names = sorted(set(goal_names)), sorted(set(kpi_names))
    start, end = _window(ext)
    if not (start and end):
        frappe.throw(_("This review has no period, so nothing can be added to it. Ask HR to set the cycle dates."))
    live = {r.source_name for r in (ext.get("review_items") or []) if not cint(r.removed)}

    goals = frappe.get_all(
        "Individual Goal",
        filters={"name": ["in", goal_names or [""]], "employee": employee, "docstatus": ["!=", 2],
                 "status": ["!=", "Cancelled"], "is_future_plan": ["!=", 1],
                 "start_date": ["<=", end], "end_date": [">=", start]},
        fields=_GOAL_FIELDS,
    ) if goal_names else []
    kpis = frappe.get_all(
        "KPI",
        filters={"name": ["in", kpi_names or [""]], "employee": employee, "status": ["!=", "Cancelled"]},
        fields=_KPI_FIELDS,
    ) if kpi_names else []
    kpis = [k for k in kpis if (not k.period_start or getdate(k.period_start) <= end)
            and (not k.period_end or getdate(k.period_end) >= start)]
    if len(goals) != len(goal_names) or len(kpis) != len(kpi_names):
        _refuse(_("Only your own current Objectives and KPIs for this review period can be added."),
                "VIS-5", "set_review_selection", ext)

    if goals:
        kpis += frappe.get_all(
            "KPI",
            filters={"individual_goal": ["in", [g.name for g in goals]], "employee": employee,
                     "status": ["!=", "Cancelled"], "name": ["not in", [k.name for k in kpis] or [""]]},
            fields=_KPI_FIELDS,
        )

    goal_rows = {r.source_name: r.name for r in (ext.get("review_items") or [])
                 if not cint(r.removed) and r.source_doctype == "Individual Goal"}
    added = 0
    arrived = {"added_in_review": 1, "added_by": user, "added_on": now_datetime()}
    for goal in goals:
        if goal.name in live:
            continue
        row = ext.append("review_items", dict(_goal_copy(goal), **arrived))
        row.name = frappe.generate_hash(length=10)
        goal_rows[goal.name] = row.name
        added += 1
    for kpi in kpis:
        if kpi.name in live:
            continue
        values = dict(_kpi_copy(kpi), **arrived)
        values["parent_item"] = goal_rows.get(kpi.individual_goal) or ""
        row = ext.append("review_items", values)
        row.name = frappe.generate_hash(length=10)
        added += 1
    if added:
        _recount(ext)
        raise_rating_flags(ext)
    return added


def change_definition(ext, row, values, user=None):
    """Change a copy's title, target, weight or period inside the review (R2).

    Returns the fields that changed. The copy remembers who changed it and when;
    what it started from stays in definition_at_start, which is what completion
    compares with before writing anything back (R15).
    """
    user = user or frappe.session.user
    new = {}
    if values.get("title") is not None:
        title = cstr(values["title"]).strip()
        if not title or len(title) > 140:
            frappe.throw(_("Give the item a name of up to 140 characters."))
        new["title"] = title
    if values.get("target_value") not in (None, ""):
        target = flt(values["target_value"])
        if not target:
            frappe.throw(_("The target cannot be 0. Progress is measured against it."))
        new["target_value"] = target
    if values.get("weightage") not in (None, ""):
        weight = flt(values["weightage"])
        if weight < 0 or weight > 100:
            frappe.throw(_("The weight must be between 0 and 100."))
        new["weightage"] = weight
    for field in ("period_start", "period_end"):
        if values.get(field) not in (None, ""):
            try:
                new[field] = getdate(values[field])
            except Exception:
                frappe.throw(_("Enter the period dates as dates."))
    start = new.get("period_start") or (getdate(row.period_start) if row.period_start else None)
    end = new.get("period_end") or (getdate(row.period_end) if row.period_end else None)
    if start and end and start > end:
        frappe.throw(_("The period must start on or before the day it ends."))

    changed = [f for f, v in new.items() if _rounded_or_same(row.get(f)) != _rounded_or_same(v)]
    if not changed:
        return []
    if "weightage" in changed:
        total = sum(flt(r.weightage) for r in (ext.get("review_items") or [])
                    if not cint(r.removed) and r.name != row.name) + new["weightage"]
        if flt(total, 2) > 100:
            frappe.throw(_("The weights in this review would add up to {0}%. They cannot pass 100%.").format(flt(total, 2)))
    for field in changed:
        row.set(field, new[field])
    row.definition_changed_by = user
    row.definition_changed_on = now_datetime()

    if not cint(ext.get("frozen")):
        _recount(ext)
    elif "target_value" in changed:
        # Frozen numbers take no new facts, but attainment follows the target.
        if row.source_doctype == "KPI":
            row.attainment_pct = attainment(row.actual_value, row.target_value, row.direction)
        else:
            row.attainment_pct = flt(min(flt(row.actual_value) / flt(row.target_value) * 100, 100), 2)
    raise_rating_flags(ext)
    return changed


def _rounded_or_same(value):
    if isinstance(value, (int, float)):
        return flt(value, 6)
    if hasattr(value, "year"):
        return str(getdate(value))
    return cstr(value)


def answer_flag(ext, target, keep, rating=None, user=None):
    """Keep or change a flagged manager or overall rating (R7, decision 12).

    Keeping re-stamps the rating on today's numbers; changing sets the new
    rating and stamps it. The answerer is recorded. Returns True when the
    rating itself changed.
    """
    user = user or frappe.session.user
    if target == "overall":
        if not cint(ext.get("overall_rating_flag")):
            frappe.throw(_("This rating has no open question."))
        before, rated_by = flt(ext.overall_rating), ext.overall_rated_by
        if not keep:
            ext.overall_rating = rating
        stamp_overall_rating(ext, user=rated_by if keep and rated_by else user)
        ext.overall_flag_answered_by = user
        ext.overall_flag_answered_on = now_datetime()
        return before != flt(ext.overall_rating)

    row = live_row(ext, target)
    if not row or not cint(row.manager_flag):
        frappe.throw(_("This rating has no open question."))
    before, rated_by = flt(row.manager_rating), row.manager_rated_by
    if not keep:
        row.manager_rating = rating
    stamp_rating(row, "manager", user=rated_by if keep and rated_by else user)
    row.manager_flag_answered_by = user
    row.manager_flag_answered_on = now_datetime()
    return before != flt(row.manager_rating)


# ── Freezing, completion and write-back (commit 6: R6, R15, SEC-25, VIS-10) ──

# Set on a live KPI or Objective by write_back() only. The definition lock lets
# that one save through; nothing else can set a document flag from outside.
WRITE_BACK_FLAG = "alvoraa_review_write_back"

# A copy's editable definition fields, and the live record's field for each.
LIVE_FIELD = {
    "KPI": {"title": "kpi_name", "target_value": "target_value", "weightage": "weightage",
            "period_start": "period_start", "period_end": "period_end"},
    "Individual Goal": {"title": "goal_name", "target_value": "target_value", "weightage": "weightage",
                        "period_start": "start_date", "period_end": "end_date"},
}


def apply_stage(ext):
    """Freeze or unfreeze the numbers after the review's stage has changed.

    Numbers freeze when the review reaches the freeze point stamped on it (R6),
    after one last count. Sending the review back before that point unfreezes
    them, and facts that arrived meanwhile flow in (decision 18). A review whose
    copies have not been taken yet is left alone: taking them stamps the right
    state. Returns True when something changed.
    """
    if not ext.get("items_taken_on"):
        return False
    past = is_past_freeze_point(ext.review_status, ext.freeze_point)
    if past and not cint(ext.get("frozen")):
        _recount(ext)
        raise_rating_flags(ext)
        ext.frozen = 1
        ext.frozen_on = now_datetime()
        audit(ext, f"Review numbers frozen at {ext.review_status} (freeze point: {ext.freeze_point}).")
        return True
    if not past and cint(ext.get("frozen")) and ext.review_status != "Completed":
        ext.frozen = 0
        ext.frozen_on = None
        _recount(ext)
        raise_rating_flags(ext)
        audit(ext, f"Review numbers unfrozen: the review went back to {ext.review_status}.")
        return True
    return False


def _live_value(field, value):
    """A live record's value in the same form definition_at_start stores it."""
    if field in ("target_value", "weightage", "baseline_value"):
        return flt(value, 6)
    if field in ("period_start", "period_end"):
        return str(getdate(value)) if value else ""
    return cstr(value)


def write_back(ext):
    """Hand agreed definition changes back to the live records, once (R15, SEC-25).

    Called at completion. For each copy whose name, target, weight or period
    was changed inside the review: a field is written only if the live record
    still holds the value the review started from. Someone else's later change
    is never overwritten; it is recorded instead. The save goes through the
    document, so the live record's own rules and change history apply; a
    refused save does not stop completion and is recorded on the copy. Ratings
    are never written back (R13). Returns the number of copies with a note.
    """
    noted = 0
    for row in ext.get("review_items") or []:
        if cint(row.removed) or row.get("written_back_on"):
            continue
        changes = definition_changes(row)
        if not changes:
            continue
        row.written_back_on = now_datetime()
        noted += 1
        mapping = LIVE_FIELD.get(row.source_doctype)
        if not mapping or not frappe.db.exists(row.source_doctype, row.source_name):
            row.write_back_note = _("Not written back: the live record no longer exists.")
            continue

        doc = frappe.get_doc(row.source_doctype, row.source_name)
        written, kept = [], []
        for field, started in changes.items():
            live_field = mapping[field]
            if _live_value(field, doc.get(live_field)) != started:
                kept.append(live_field)
                continue
            written.append((live_field, doc.get(live_field), row.get(field)))
            doc.set(live_field, row.get(field))

        notes = []
        if written:
            savepoint = f"review_write_back_{row.name}"
            frappe.db.savepoint(savepoint)
            doc.flags[WRITE_BACK_FLAG] = True
            try:
                doc.save(ignore_permissions=True)
                doc.add_comment("Info", _("Changed in review {0}: {1}. Agreed in the review when the manager sent it.").format(
                    ext.name, "; ".join(f"{f} {cstr(old)} to {cstr(new)}" for f, old, new in written)))
                notes.append(_("Written back: {0}.").format(", ".join(f for f, _o, _n in written)))
            except Exception as e:
                frappe.db.rollback(save_point=savepoint)
                notes.append(_("Not written back: {0}").format(_plain(e)))
                frappe.log_error(title="Review write-back refused",
                                 message=f"{ext.name} {row.name} {row.source_doctype} {row.source_name}")
            finally:
                doc.flags[WRITE_BACK_FLAG] = False
        if kept:
            notes.append(_("Not written back, because the live record was changed after the review started: {0}.").format(
                ", ".join(kept)))
        row.write_back_note = " ".join(notes)
    return noted


# ── The definition lock on live records (commit 7: R2, R9, R11, SEC-19, SEC-22) ─
#
# Hung on the documents themselves (before_validate, before_update_after_submit,
# on_trash), so the portal, the desk, REST and Data Import all meet it.
# before_validate, not validate: set_goal_progress and others save with
# flags.ignore_validate, which skips validate but not before_validate.

LOCKED_FIELDS = {
    "KPI": ("kpi_name", "target_value", "weightage", "period_start", "period_end", "appraisal_cycle",
            "employee", "progress_mode", "direction", "baseline_value", "unit", "individual_goal"),
    "Individual Goal": ("goal_name", "target_value", "weightage", "start_date", "end_date", "appraisal_cycle",
                        "employee", "progress_mode", "unit", "parent_goal"),
}
_WHAT = {"KPI": "KPI", "Individual Goal": "Objective"}


def holds(doctype, names):
    """Which of these live records an open review holds. One query.

    Held: a live (not removed) copy sits in a review that is not Completed,
    whose appraisal is not cancelled, and whose lock has not been released.
    The lock is released a number of days after the cycle ends, counted on the
    server's date (R9, SEC-22); 0 days means never, and so does a cycle with no
    end date. Returns name -> release date, or None when it is never released.
    """
    out = {}
    for r in _holding_reviews(doctype, names):
        release = r.release
        if r.source_name in out and (out[r.source_name] is None or (release and out[r.source_name] >= release)):
            continue
        out[r.source_name] = release
    return out


def _holding_reviews(doctype, names):
    """Every open review still holding one of these live records, with its release
    date and period end. One query. Shared by the lock and the badge, so the two
    can never disagree about what "in a review" means."""
    names = sorted({n for n in (names or []) if n})
    if not names:
        return []
    item = frappe.qb.DocType("Alvoraa Review Item")
    ext = frappe.qb.DocType("Alvoraa Appraisal Extension")
    appraisal = frappe.qb.DocType("Appraisal")
    cycle = frappe.qb.DocType("Appraisal Cycle")
    rows = (
        frappe.qb.from_(item)
        .join(ext).on(item.parent == ext.name)
        .join(appraisal).on(appraisal.name == ext.appraisal)
        .left_join(cycle).on(cycle.name == ext.appraisal_cycle)
        .select(item.source_name, cycle.end_date, ext.review_window_end)
        .where(item.parenttype == "Alvoraa Appraisal Extension")
        .where(item.source_doctype == doctype)
        .where(item.source_name.isin(names))
        .where(item.removed == 0)
        .where(ext.review_status != "Completed")
        .where(appraisal.docstatus != 2)
    ).run(as_dict=True)
    if not rows:
        return []

    days = review_settings()["lock_release_days"]
    today = getdate(nowdate())
    held = []
    for r in rows:
        end = r.end_date or r.review_window_end
        r.release = getdate(add_days(end, days)) if (days and end) else None
        if r.release and today >= r.release:
            continue
        held.append(r)
    return held


def review_badges(doctype, names):
    """The "in review" badge for live records outside the review (R5, PRIV-10).

    name -> {"in_review": 1, "updates_after": "YYYY-MM-DD"} for each record an
    open review holds: it is in a review, and updates dated after that day do not
    change the review. Nothing else: no review, stage, rating, reviewer or freeze
    state, because anyone who can see the live record sees the badge. With two
    open reviews (R16) the later period end is given. One query.
    """
    out = {}
    for r in _holding_reviews(doctype, names):
        end = str(getdate(r.review_window_end)) if r.review_window_end else ""
        current = out.get(r.source_name)
        if current is None or (end and end > current["updates_after"]):
            out[r.source_name] = {"in_review": 1, "updates_after": end}
    return out


def _lock_value(meta, field, value):
    """A field's value in a form that compares the same however it arrived
    (a REST call may send "50" for 50.0, or a date as text)."""
    fieldtype = (meta.get_field(field) or frappe._dict()).fieldtype
    if fieldtype in ("Float", "Percent", "Currency", "Int"):
        return flt(value, 6)
    if fieldtype == "Date":
        return str(getdate(value)) if value else ""
    return cstr(value)


def _held_or_refuse(doc, rule, endpoint):
    """holds() for one document; a lookup that fails refuses (SEC-19 fails closed)."""
    from hrms.alvoraa_hr_core.access import refuse

    try:
        return holds(doc.doctype, [doc.name])
    except Exception:
        refuse(_("This change cannot be checked against open reviews right now. Try again shortly."),
               rule, endpoint, doc.doctype, doc.name)


def enforce_definition_lock(doc, method=None):
    """doc_events before_validate / before_update_after_submit on KPI and Individual Goal.

    While an open review holds a live record, its definition cannot change here:
    name, target, weight, period, cycle, person, progress mode, direction,
    baseline, unit and parent link (R2, decision 8). Facts, status and
    cancelling are not locked (decision 20). No role is exempt; only the
    completion write-back passes.
    """
    if doc.is_new() or doc.flags.get(WRITE_BACK_FLAG) or doc.doctype not in LOCKED_FIELDS:
        return
    before = doc.get_doc_before_save() or frappe.get_doc(doc.doctype, doc.name)
    changed = [f for f in LOCKED_FIELDS[doc.doctype]
               if _lock_value(doc.meta, f, before.get(f)) != _lock_value(doc.meta, f, doc.get(f))]
    if not changed:
        return
    held = _held_or_refuse(doc, "R2", f"{doc.doctype} save")
    if doc.name not in held:
        return
    from hrms.alvoraa_hr_core.access import refuse

    release = held[doc.name]
    when = (_("or after {0}").format(frappe.utils.formatdate(release)) if release
            else _("or once the review is completed"))
    refuse(
        _("This {0} is in an open review, so its {1} cannot be changed here. Change it inside the review, {2}.").format(
            _(_WHAT[doc.doctype]), ", ".join(doc.meta.get_label(f) for f in changed), when),
        "R2", f"{doc.doctype} save", doc.doctype, doc.name,
    )


def refuse_delete_while_held(doc, method=None):
    """doc_events on_trash on KPI and Individual Goal (R11).

    A live record an open review holds cannot be deleted by any path. An item
    created inside the review is deleted through the review, which takes its
    copy out first (delete_review_item). Cancelling stays possible.
    """
    held = _held_or_refuse(doc, "R11", f"{doc.doctype} delete")
    if doc.name not in held:
        return
    from hrms.alvoraa_hr_core.access import refuse

    refuse(
        _("This {0} is in an open review, so it cannot be deleted. Remove it from the review instead.").format(
            _(_WHAT[doc.doctype])),
        "R11", f"{doc.doctype} delete", doc.doctype, doc.name,
    )


def refresh_copies_of(doc, method=None):
    """doc_events on_update on KPI and Individual Goal: bring open reviews' copies
    up to date when a live record's facts change (R3).

    One query when no open, unfrozen review holds the record, which is the usual
    case. A failure never stops the live save: it is logged with document names
    only, and the review catches up the next time it is opened.
    """
    if doc.flags.get(WRITE_BACK_FLAG):
        return
    item = frappe.qb.DocType("Alvoraa Review Item")
    ext_t = frappe.qb.DocType("Alvoraa Appraisal Extension")
    appraisal = frappe.qb.DocType("Appraisal")
    parents = (
        frappe.qb.from_(item)
        .join(ext_t).on(item.parent == ext_t.name)
        .join(appraisal).on(appraisal.name == ext_t.appraisal)
        .select(item.parent).distinct()
        .where(item.parenttype == "Alvoraa Appraisal Extension")
        .where(item.source_doctype == doc.doctype)
        .where(item.source_name == doc.name)
        .where(item.removed == 0)
        .where(ext_t.frozen == 0)
        .where(ext_t.review_status != "Completed")
        .where(appraisal.docstatus != 2)
    ).run(pluck=True)
    for parent in parents:
        savepoint = f"review_refresh_{frappe.generate_hash(length=8)}"
        frappe.db.savepoint(savepoint)
        try:
            refresh_review_items(frappe.get_doc("Alvoraa Appraisal Extension", parent))
        except Exception:
            frappe.db.rollback(save_point=savepoint)
            frappe.log_error(title="Review copy refresh failed", message=f"{parent} {doc.doctype} {doc.name}")


def _plain(error):
    import re

    return re.sub(r"<[^>]+>", "", cstr(getattr(error, "message", None) or error)).strip()[:500]


def audit(ext, text):
    """An Info entry on the review record's timeline: who did what to which row.

    The review record opens only for HR under the stage rule (SEC-27), so a
    reason may be written here. Never a rating or a number.
    """
    ext.add_comment("Info", text)


# ── Reminding HR about items still locked after a cycle (commit 10: R9, SEC-22) ─

REMINDER_FIRST_DAY = 15
REMINDER_EVERY_DAYS = 7


def remind_hr_of_held_items():
    """Daily job: tell HR when open reviews still lock Objectives and KPIs after
    their cycle ended (R9).

    On day 15 after a cycle's end date, then every 7 days while the lock lasts.
    The date decides, so nothing is stored and a missed day is not made up. If
    the lock is released on or before day 15 there is nothing to remind about;
    with 0 (never released) the reminder repeats until the reviews are completed.

    Each enabled HR Manager hears only about reviews of the companies they look
    after. The message holds the cycle name, a count and a date: no person's
    name (PRIV-15). A failed notification is logged with the user id only and
    never stops the others. Returns the number of notifications made.
    """
    from hrms.alvoraa_hr_core.access import permitted_companies

    days = review_settings()["lock_release_days"]
    if days and days <= REMINDER_FIRST_DAY:
        return 0
    today = getdate(nowdate())

    item = frappe.qb.DocType("Alvoraa Review Item")
    ext = frappe.qb.DocType("Alvoraa Appraisal Extension")
    appraisal = frappe.qb.DocType("Appraisal")
    cycle = frappe.qb.DocType("Appraisal Cycle")
    rows = (
        frappe.qb.from_(item)
        .join(ext).on(item.parent == ext.name)
        .join(appraisal).on(appraisal.name == ext.appraisal)
        .join(cycle).on(cycle.name == ext.appraisal_cycle)
        .select(ext.name, cycle.name.as_("cycle"), cycle.cycle_name, cycle.end_date, appraisal.company)
        .distinct()
        .where(item.parenttype == "Alvoraa Appraisal Extension")
        .where(item.removed == 0)
        .where(ext.review_status != "Completed")
        .where(appraisal.docstatus != 2)
        .where(cycle.end_date <= add_days(today, -REMINDER_FIRST_DAY))
    ).run(as_dict=True)

    # cycle -> company -> number of open reviews still holding items
    due = {}
    for r in rows:
        after = (today - getdate(r.end_date)).days
        if (after - REMINDER_FIRST_DAY) % REMINDER_EVERY_DAYS:
            continue
        if days and today >= getdate(add_days(r.end_date, days)):
            continue
        entry = due.setdefault(r.cycle, {"label": r.cycle_name or r.cycle, "end": getdate(r.end_date),
                                         "after": after, "companies": {}})
        entry["companies"][r.company] = entry["companies"].get(r.company, 0) + 1
    if not due:
        return 0

    hr_managers = frappe.get_all(
        "User",
        filters={"enabled": 1, "name": ["in", frappe.get_all(
            "Has Role", filters={"role": "HR Manager", "parenttype": "User"}, pluck="parent") or [""]]},
        pluck="name",
    )
    sent = 0
    for user in hr_managers:
        if user in ("Administrator", "Guest"):
            continue
        companies = set(permitted_companies(user))
        lines = []
        for entry in sorted(due.values(), key=lambda e: e["label"]):
            count = sum(n for company, n in entry["companies"].items() if company in companies)
            if not count:
                continue
            until = (_("until {0}").format(frappe.utils.formatdate(add_days(entry["end"], days))) if days
                     else _("until the reviews are completed"))
            lines.append(_("{0}: {1} review(s) are still open {2} days after the cycle ended. "
                           "The Objectives and KPIs in them stay locked {3}.").format(
                entry["label"], count, entry["after"], until))
        if not lines:
            continue
        savepoint = f"review_reminder_{frappe.generate_hash(length=8)}"
        frappe.db.savepoint(savepoint)
        try:
            frappe.get_doc({
                "doctype": "Notification Log",
                "for_user": user,
                "type": "Alert",
                "subject": _("Objectives and KPIs are still locked in open reviews"),
                "email_content": "<p>" + "</p><p>".join(frappe.utils.escape_html(line) for line in lines) + "</p>",
            }).insert()
            sent += 1
        except Exception:
            frappe.db.rollback(save_point=savepoint)
            frappe.log_error(title="Review lock reminder failed", message=user)
    return sent
