"""Copy existing reviews onto their review records (slice 010 group D, commit 12).

Reviews that existed before group D have no copies of their Objectives and
KPIs. This gives them copies, as 00d-impact-analysis-group-d.md section 10
designs it:

  Completed            copies of the Objectives and KPIs tagged to that cycle
                       and employee, numbers and ratings as they were stored,
                       frozen, marked backfilled. This is history: nothing is
                       recounted and nothing is written back.
  Employee Review,     the same, with each rating stamped on the stored
  Manager Review,      numbers (so nothing is flagged by the copy itself), the
  Employee Final       freeze point and removal setting in force, frozen only if
  Review, HR Review    the review is already past its freeze point, and the
                       self-review draft re-keyed from live record names to the
                       copies' row names.
  Not Started          nothing: copies are taken when the review is first opened.
  Cancelled appraisal  nothing.

The first time an open review is opened afterwards, its numbers are recounted
from approved facts dated in its period. Where that moves a number a rating
was given on, the rating is flagged (R7). report() counts those in advance.

Functions, all run by a person on the user's word:

  report()                         read-only dry run; changes nothing
  run()                            the copy itself (the patch calls it)
  undo_backfill(dry_run=1)         remove copies the backfill made, from reviews
                                   nobody has changed since
  copy_ratings_back_for_rollback(dry_run=1)
                                   before a code rollback: put ratings given on
                                   open reviews' copies back on the live KPIs

    bench --site <site> execute alvoraa_goals.review_backfill.report

Safe to run twice: a review that already has copies is skipped. Completed
reviews' copies can never be changed through the review record (VIS-10); the
backfill does not go through it, and does not weaken that rule: it writes rows
straight into the table, once, for reviews that have none.

Logs and errors carry document names only (PRIV-15).
"""

import json
from collections import Counter

import frappe
from frappe.utils import cint, cstr, flt, getdate, now_datetime

import alvoraa_goals.review_items as review_items

EXTENSION = "Alvoraa Appraisal Extension"
ITEM = "Alvoraa Review Item"
COMMIT_EVERY = 50
CHUNK = 500

OPEN_STAGES = ("Employee Review", "Manager Review", "Employee Final Review", "HR Review")

_EXT_FIELDS = ["name", "appraisal", "employee", "appraisal_cycle", "review_status", "items_taken_on",
               "overall_rating", "page_data", "modified"]
_KPI_RATINGS = ("self_rating", "self_comment", "manager_rating", "manager_comment",
                "potential_rating", "potential_comment")


# ── Working out what would be copied (shared by report and run) ─────────────


def _chunks(values, size=CHUNK):
    values = list(values)
    for i in range(0, len(values), size):
        yield values[i:i + size]


def _get_all_in(doctype, field, values, filters=None, **kwargs):
    """frappe.get_all for `field in values`, 500 values per query."""
    rows = []
    for part in _chunks(sorted(set(values))):
        rows += frappe.get_all(doctype, filters=dict(filters or {}, **{field: ["in", part]}), **kwargs)
    return rows


def _plan(names=None):
    """Every review record (or only these), what would happen to it, and the copies it would get."""
    settings = review_items.review_settings()
    extensions = frappe.get_all(EXTENSION, filters={"name": ["in", list(names) or [""]]} if names is not None else None,
                                fields=_EXT_FIELDS, order_by="name asc")
    appraisals = {a.name: a for a in _get_all_in(
        "Appraisal", "name", [e.appraisal for e in extensions if e.appraisal],
        fields=["name", "employee", "appraisal_cycle", "start_date", "end_date", "docstatus"])}
    with_rows = set(_get_all_in(ITEM, "parent", [e.name for e in extensions], filters={"parenttype": EXTENSION},
                                pluck="parent", distinct=True))

    cycles = {c.name: c for c in frappe.get_all("Appraisal Cycle", fields=["name", "start_date", "end_date"])}
    wanted_cycles = sorted({(appraisals.get(e.appraisal) or e).get("appraisal_cycle") or e.appraisal_cycle
                            for e in extensions} - {None, ""})
    kpis, goals = {}, {}
    for k in _get_all_in("KPI", "appraisal_cycle", wanted_cycles,
                         filters={"status": ["!=", "Cancelled"]},
                         fields=review_items._KPI_FIELDS + ["employee", "appraisal_cycle", "actual_value",
                                                            "attainment_pct", *_KPI_RATINGS],
                         order_by="creation asc"):
        kpis.setdefault((k.employee, k.appraisal_cycle), []).append(k)
    for g in _get_all_in("Individual Goal", "appraisal_cycle", wanted_cycles,
                         filters={"docstatus": ["!=", 2], "status": ["!=", "Cancelled"], "is_future_plan": ["!=", 1]},
                         fields=review_items._GOAL_FIELDS + ["employee", "appraisal_cycle", "actual_progress",
                                                             "progress_pct"],
                         order_by="creation asc"):
        goals.setdefault((g.employee, g.appraisal_cycle), []).append(g)

    plans = []
    for ext in extensions:
        ap = appraisals.get(ext.appraisal)
        status = ext.review_status or "Not Started"
        plan = frappe._dict(ext=ext, appraisal=ap, status=status, action="copy", reason="", goals=[], kpis=[])
        plans.append(plan)
        if ext.name in with_rows or ext.items_taken_on:
            plan.action, plan.reason = "skip", "already has copies"
            continue
        if status == "Not Started":
            plan.action, plan.reason = "skip", "not started: copied when first opened"
            continue
        if not ap or cint(ap.docstatus) == 2:
            plan.action, plan.reason = "skip", "appraisal missing or cancelled"
            continue
        if status not in OPEN_STAGES + ("Completed",):
            plan.action, plan.reason = "skip", "unknown stage"
            continue
        employee = ap.employee or ext.employee
        cycle = ap.appraisal_cycle or ext.appraisal_cycle
        if not (employee and cycle):
            plan.action, plan.reason = "skip", "no employee or cycle"
            continue
        c = cycles.get(cycle) or frappe._dict()
        plan.employee, plan.cycle = employee, cycle
        plan.start = ap.start_date or c.get("start_date")
        plan.end = ap.end_date or c.get("end_date")
        plan.goals = goals.get((employee, cycle), [])
        plan.kpis = kpis.get((employee, cycle), [])
        plan.freeze_point = settings["freeze_point"]
        plan.removal_mode = settings["removal_mode"]
        plan.lock_release_days = settings["lock_release_days"]
        plan.frozen = status == "Completed" or review_items.is_past_freeze_point(status, settings["freeze_point"])
        if not (plan.goals or plan.kpis):
            plan.action, plan.reason = "empty", "nothing tagged to this cycle and employee"
    return plans


def _rows_for(plan, now):
    """The copies one review gets, as field dicts, Objectives first."""
    rows, goal_rows = [], {}
    for goal in plan.goals:
        values = review_items._goal_copy(goal)
        values.update(name=frappe.generate_hash(length=10), actual_value=flt(goal.actual_progress, 6),
                      attainment_pct=flt(goal.progress_pct, 2))
        goal_rows[goal.name] = values["name"]
        rows.append(values)
    for kpi in plan.kpis:
        values = review_items._kpi_copy(kpi)
        values.update(name=frappe.generate_hash(length=10), parent_item=goal_rows.get(kpi.individual_goal) or "",
                      actual_value=flt(kpi.actual_value, 6), attainment_pct=flt(kpi.attainment_pct, 2))
        for field in _KPI_RATINGS:
            values[field] = kpi.get(field) or (0 if field.endswith("_rating") else "")
        rows.append(values)

    for values in rows:
        values.update(backfilled=1, facts_as_of=now)
        # A rating is stamped on the numbers it was stored with, so the copy
        # itself raises no question. Who gave it was never recorded.
        for kind in ("self", "manager"):
            if flt(values.get(f"{kind}_rating")) > 0:
                for part, source in review_items._BASIS:
                    values[f"{kind}_basis_{part}"] = review_items._rounded(values.get(source))
                values[f"{kind}_rated_on"] = now
    return rows


def _rekey_page_data(page_data, rows):
    """The self-review draft keyed by copy row names. Returns (json or None, keys dropped)."""
    try:
        data = json.loads(page_data or "{}")
    except ValueError:
        return None, 0
    past = data.get("past-objectives") if isinstance(data, dict) else None
    if not isinstance(past, dict):
        return None, 0
    by_source = {(r["source_doctype"], r["source_name"]): r["name"] for r in rows}
    dropped = 0
    for key, doctype in (("kpis", "KPI"), ("objectives", "Individual Goal")):
        entries = past.get(key)
        if not isinstance(entries, dict):
            continue
        new = {}
        for source, value in entries.items():
            row = by_source.get((doctype, source))
            if row:
                new[row] = value
            else:
                dropped += 1
        past[key] = new
    return json.dumps(data), dropped


# ── The dry run ─────────────────────────────────────────────────────────────


def _approved_facts(kpi_names, goal_names):
    """Every approved fact of these live records, grouped by record, in the shape
    review_items._numbers_for reads. Three queries (more only past 500 records)."""
    readings, evidence, updates = {}, {}, {}
    for f in _get_all_in("KPI Progress Log", "parent", kpi_names,
                         filters={"parenttype": "KPI", "approval_status": "Approved"},
                         fields=["parent", "value", "log_date", "approved_on", "creation"]):
        readings.setdefault(f.parent, []).append(f)
    for f in _get_all_in("Goal Evidence", "parent", goal_names,
                         filters={"parenttype": "Individual Goal", "validation_status": "Approved"},
                         fields=["parent", "value", "extracted_date", "upload_date", "approved_on", "creation"]):
        evidence.setdefault(f.parent, []).append(f)
    for f in _get_all_in("Goal Progress Update", "parent", goal_names,
                         filters={"parenttype": "Individual Goal", "approval_status": "Approved"},
                         fields=["parent", "value", "log_date", "approved_on", "creation"]):
        updates.setdefault(f.parent, []).append(f)
    return readings, evidence, updates


def report(names=None):
    """Read-only. What run() would do on this site, in counts and document names.

    Writes nothing. Run it on a site after the code is deployed and before its
    migrate, on the user's word:
        bench --site <site> execute alvoraa_goals.review_backfill.report
    `names` limits it to those review records (tests use this).
    """
    plans = _plan(names)
    now = now_datetime()
    to_copy = [p for p in plans if p.action == "copy"]

    by_cycle_stage = {}
    for p in plans:
        cycle = (p.appraisal or p.ext).get("appraisal_cycle") or p.ext.appraisal_cycle or "(no cycle)"
        stages = by_cycle_stage.setdefault(cycle, {})
        stages[p.status] = stages.get(p.status, 0) + 1

    items_per_review = [len(p.goals) + len(p.kpis) for p in to_copy]
    readings, evidence, updates = _approved_facts(
        [k.name for p in to_copy for k in p.kpis], [g.name for p in to_copy for g in p.goals])

    outside = Counter()
    numbers_change, rating_questions, rated_items, no_period, keys_dropped = 0, 0, 0, 0, 0
    for p in to_copy:
        start = getdate(p.start) if p.start else None
        end = getdate(p.end) if p.end else None
        if not (start and end):
            no_period += 1
        rows = [frappe._dict(r) for r in _rows_for(p, now)]
        rated_items += sum(1 for r in rows if any(flt(r.get(f)) > 0 for f in ("self_rating", "manager_rating",
                                                                             "potential_rating")))
        for r in rows:
            window = review_items._row_window(r, start, end)
            if r.source_doctype == "KPI":
                outside["KPI readings"] += sum(1 for f in readings.get(r.source_name, [])
                                               if not window or not window[0] <= getdate(f.log_date) <= window[1])
            else:
                outside["goal updates"] += sum(1 for f in updates.get(r.source_name, [])
                                               if not window or not window[0] <= getdate(f.log_date) <= window[1])
                for f in evidence.get(r.source_name, []):
                    on, _by_upload = review_items._evidence_date(f)
                    if not window or not on or not window[0] <= on <= window[1]:
                        outside["evidence"] += 1
        if p.status in OPEN_STAGES and not p.frozen:
            moved = []
            for r in rows:
                counted = review_items._numbers_for(r, start, end, readings, evidence, updates)
                if (review_items._rounded(counted["actual_value"]) != review_items._rounded(r.actual_value)
                        or review_items._rounded(counted["attainment_pct"]) != review_items._rounded(r.attainment_pct)):
                    moved.append(r)
            numbers_change += len(moved)
            rating_questions += sum(1 for r in moved if flt(r.self_rating) > 0 or flt(r.manager_rating) > 0)
            if moved and flt(p.ext.overall_rating) > 0:
                rating_questions += 1
        _json, dropped = _rekey_page_data(p.ext.page_data, [dict(r) for r in rows])
        keys_dropped += dropped

    running_totals = frappe.db.sql(
        """SELECT COUNT(*) FROM `tabKPI` k
           WHERE k.progress_mode = 'Cumulative'
             AND (SELECT COUNT(*) FROM `tabKPI Progress Log` l
                  WHERE l.parent = k.name AND l.parenttype = 'KPI' AND l.approval_status = 'Approved') > 1
             AND ABS(IFNULL(k.actual_value, 0) - (SELECT IFNULL(SUM(l.value), 0) FROM `tabKPI Progress Log` l
                  WHERE l.parent = k.name AND l.parenttype = 'KPI' AND l.approval_status = 'Approved')) > 0.001"""
    )[0][0]

    return {
        "reviews": len(plans),
        "by_cycle_and_stage": by_cycle_stage,
        "will_copy": {"reviews": len(to_copy), "items": sum(items_per_review),
                      "completed": sum(1 for p in to_copy if p.status == "Completed"),
                      "open": sum(1 for p in to_copy if p.status in OPEN_STAGES),
                      "open_already_frozen": sum(1 for p in to_copy if p.status in OPEN_STAGES and p.frozen)},
        "items_per_review": {"average": flt(sum(items_per_review) / len(items_per_review), 1) if items_per_review else 0,
                             "most": max(items_per_review) if items_per_review else 0},
        "skipped": dict(Counter(p.reason for p in plans if p.action == "skip")),
        "cannot_copy_nothing_tagged": {
            "completed": [p.ext.name for p in plans if p.action == "empty" and p.status == "Completed"],
            "open": [p.ext.name for p in plans if p.action == "empty" and p.status != "Completed"],
        },
        "reviews_with_no_period": no_period,
        "rated_items_copied": rated_items,
        "approved_facts_dated_outside_the_review_period": dict(outside),
        "open_items_whose_number_changes_on_first_open": numbers_change,
        "rating_questions_expected_on_first_open": rating_questions,
        "draft_keys_dropped": keys_dropped,
        "cumulative_kpis_whose_readings_look_like_running_totals": running_totals,
        "extensions_missing_employee_or_cycle": sum(1 for p in plans if not (p.ext.employee and p.ext.appraisal_cycle)),
        "kpi_additional_reviewer_rows": frappe.db.count("KPI Additional Reviewer"),
        "custom_docperm_rows_to_look_at": review_items.custom_docperm_report(),
    }


# ── The copy ────────────────────────────────────────────────────────────────


def run(names=None):
    """Give every existing review its copies (or only these). Called by the patch.

    One review at a time inside a savepoint: a failure is logged by review name
    and the rest carry on. Commits every 50 reviews. Returns counts.
    """
    plans = [p for p in _plan(names) if p.action == "copy"]
    done, rows_made, failed = 0, 0, []
    for index, plan in enumerate(plans, start=1):
        savepoint = f"review_backfill_{index}"
        frappe.db.savepoint(savepoint)
        try:
            rows_made += _copy_one(plan)
            done += 1
        except Exception:
            frappe.db.rollback(save_point=savepoint)
            failed.append(plan.ext.name)
            frappe.log_error(title="Review copy backfill failed", message=plan.ext.name)
        if index % COMMIT_EVERY == 0:
            frappe.db.commit()
    frappe.db.commit()
    return {"reviews_copied": done, "copies_made": rows_made, "failed": failed}


def _copy_one(plan):
    now = now_datetime()
    ext = plan.ext
    rows = _rows_for(plan, now)
    for idx, values in enumerate(rows, start=1):
        doc = frappe.get_doc(dict(values, doctype=ITEM, parent=ext.name, parenttype=EXTENSION,
                                  parentfield="review_items", idx=idx))
        doc.db_insert()

    update = {
        "employee": ext.employee or plan.employee,
        "appraisal_cycle": ext.appraisal_cycle or plan.cycle,
        "items_taken_on": now,
        "review_window_start": plan.start,
        "review_window_end": plan.end,
        "freeze_point": plan.freeze_point,
        "removal_mode": plan.removal_mode,
        "lock_release_days": plan.lock_release_days,
        "frozen": cint(plan.frozen),
        "frozen_on": now if plan.frozen else None,
    }
    if plan.status == "Completed":
        update["completed_on"] = ext.modified
    if flt(ext.overall_rating) > 0:
        update["overall_rating_basis"] = json.dumps(
            {r["name"]: [review_items._rounded(r.get("actual_value")), review_items._rounded(r.get("target_value")),
                         review_items._rounded(r.get("weightage")), 0] for r in rows},
            sort_keys=True)
        update["overall_rated_on"] = now
    if plan.status in OPEN_STAGES:
        rekeyed, _dropped = _rekey_page_data(ext.page_data, rows)
        if rekeyed is not None:
            update["page_data"] = rekeyed
    frappe.db.set_value(EXTENSION, ext.name, update, update_modified=False)
    return len(rows)


# ── Rollback helpers ────────────────────────────────────────────────────────


def undo_backfill(dry_run=1, names=None):
    """Remove the copies run() made, from reviews nobody has changed since.

    Only reviews whose every copy is marked backfilled and where nothing has
    happened after the copy: no rating given or answered, no definition change,
    no removal, not frozen or completed later. Other reviews are listed and left
    alone. With dry_run (the default) nothing is written. The self-review draft
    is keyed back to the live record names. `names` limits it to those review
    records (tests use this).
    """
    dry_run = cint(dry_run)
    item_fields = ["name", "parent", "backfilled", "source_doctype", "source_name", "removed", "added_in_review",
                   "definition_changed_on", "self_rated_on", "manager_rated_on", "manager_flag_answered_on"]
    rows_by_parent = {}
    item_filters = {"parenttype": EXTENSION}
    if names is not None:
        item_filters["parent"] = ["in", list(names) or [""]]
    for r in frappe.get_all(ITEM, filters=item_filters, fields=item_fields):
        rows_by_parent.setdefault(r.parent, []).append(r)
    extensions = {e.name: e for e in _get_all_in(
        EXTENSION, "name", list(rows_by_parent),
        fields=["name", "items_taken_on", "frozen_on", "completed_on", "overall_rated_on",
                "overall_flag_answered_on", "page_data"])}

    undo, kept = [], []
    for parent, rows in rows_by_parent.items():
        ext = extensions.get(parent)
        if not ext or not all(cint(r.backfilled) for r in rows):
            continue
        taken = ext.items_taken_on

        def later(value):
            return bool(value and taken and value > taken)

        changed = (
            any(cint(r.removed) or cint(r.added_in_review) or r.definition_changed_on or later(r.self_rated_on)
                or later(r.manager_rated_on) or r.manager_flag_answered_on for r in rows)
            or later(ext.frozen_on) or later(ext.completed_on) or later(ext.overall_rated_on)
            or ext.overall_flag_answered_on
        )
        (kept if changed else undo).append(parent)

    if not dry_run:
        for parent in undo:
            rows = rows_by_parent[parent]
            back = {r.name: r.source_name for r in rows}
            update = {"items_taken_on": None, "review_window_start": None, "review_window_end": None,
                      "freeze_point": None, "removal_mode": None, "lock_release_days": 0,
                      "frozen": 0, "frozen_on": None,
                      "completed_on": None, "overall_rating_basis": None, "overall_rated_on": None}
            try:
                data = json.loads(extensions[parent].page_data or "{}")
                past = data.get("past-objectives") if isinstance(data, dict) else None
                if isinstance(past, dict):
                    for key in ("kpis", "objectives"):
                        if isinstance(past.get(key), dict):
                            past[key] = {back.get(k, k): v for k, v in past[key].items()}
                    update["page_data"] = json.dumps(data)
            except ValueError:
                pass
            frappe.db.delete(ITEM, {"parent": parent, "parenttype": EXTENSION})
            frappe.db.set_value(EXTENSION, parent, update, update_modified=False)
        frappe.db.commit()
    return {"dry_run": dry_run, "undone": len(undo), "kept_because_changed_since": kept}


def copy_ratings_back_for_rollback(dry_run=1, names=None):
    """Before a code rollback: put ratings given on open reviews' copies back on
    the live KPIs, which is where the old code reads them (00d section 10.3).

    For each KPI copied into an open review, the ratings on the copy of the
    review with the latest period are written to the KPI where they differ,
    through the document with the repair flag the rating guard honours. With
    dry_run (the default) nothing is written. Returns counts and the KPI names
    that would change (document names only). `names` limits it to those review
    records (tests use this).
    """
    from alvoraa_goals.controllers.kpi import RATING_REPAIR_FLAG

    dry_run = cint(dry_run)
    item = frappe.qb.DocType(ITEM)
    ext = frappe.qb.DocType(EXTENSION)
    copies = (
        frappe.qb.from_(item).join(ext).on(item.parent == ext.name)
        .select(item.source_name, ext.review_window_end, *[item[f] for f in _KPI_RATINGS])
        .where(item.parenttype == EXTENSION)
        .where(item.source_doctype == "KPI")
        .where(item.removed == 0)
        .where(ext.review_status != "Completed")
        .where(ext.name.isin(list(names) or [""]) if names is not None else ext.name.isnotnull())
    ).run(as_dict=True)
    latest = {}
    for c in copies:
        current = latest.get(c.source_name)
        if current is None or cstr(c.review_window_end) > cstr(current.review_window_end):
            latest[c.source_name] = c

    stored = {k.name: k for k in _get_all_in("KPI", "name", list(latest), fields=["name", *_KPI_RATINGS])}
    changes = {}
    for name, c in latest.items():
        k = stored.get(name)
        if not k:
            continue
        diff = {f: c.get(f) for f in _KPI_RATINGS
                if (flt(c.get(f), 6) if f.endswith("_rating") else cstr(c.get(f)))
                != (flt(k.get(f), 6) if f.endswith("_rating") else cstr(k.get(f)))}
        if diff and any(flt(c.get(f)) for f in ("self_rating", "manager_rating", "potential_rating")):
            changes[name] = diff

    failed = []
    if not dry_run:
        for name, diff in changes.items():
            savepoint = f"rating_back_{frappe.generate_hash(length=8)}"
            frappe.db.savepoint(savepoint)
            try:
                doc = frappe.get_doc("KPI", name)
                doc.update(diff)
                doc.flags[RATING_REPAIR_FLAG] = True
                doc.flags.ignore_validate = True
                doc.save()
            except Exception:
                frappe.db.rollback(save_point=savepoint)
                failed.append(name)
                frappe.log_error(title="Rating copy-back failed", message=name)
        frappe.db.commit()
    return {"dry_run": dry_run, "kpis_to_change": len(changes), "kpis": sorted(changes), "failed": failed}
