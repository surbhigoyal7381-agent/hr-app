import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime


class PMSCycle(Document):
    def validate(self):
        if self.start_date and self.end_date and self.start_date > self.end_date:
            frappe.throw("Start Date must be before End Date.")

    def before_save(self):
        # Snapshot the template at cycle creation so in-flight reviews stay version-locked
        if self.template and not self.template_snapshot:
            tmpl = frappe.get_doc("PMS Review Template", self.template)
            self.template_snapshot = tmpl.as_snapshot()

    def on_update(self):
        if self.status == "Active" and self.auto_create_records:
            self._auto_create_review_records()

    def _auto_create_review_records(self):
        frappe.enqueue(
            "hrms.performance_management.doctype.pms_cycle.pms_cycle.create_review_records_for_cycle",
            cycle=self.name,
            now=False,
            queue="long",
        )


def create_review_records_for_cycle(cycle):
    """Background job: create PMS Review Record for each employee in scope."""
    cycle_doc = frappe.get_doc("PMS Cycle", cycle)
    employees = _get_employees_in_scope(cycle_doc)
    created = 0
    for emp in employees:
        if frappe.db.exists("PMS Review Record", {"employee": emp.name, "cycle": cycle}):
            continue
        rec = frappe.new_doc("PMS Review Record")
        rec.employee = emp.name
        rec.cycle = cycle
        rec.primary_manager = emp.reports_to
        rec.status = "Not Started"
        rec.insert(ignore_permissions=True)
        created += 1
    frappe.db.commit()
    frappe.log_error(f"PMS Cycle {cycle}: created {created} review records.", "PMS Cycle Activation")


def _get_employees_in_scope(cycle_doc):
    filters = {"status": "Active"}
    if not cycle_doc.applicability:
        return frappe.get_all("Employee", filters=filters, fields=["name", "reports_to"])
    # OR across applicability rows
    employees = []
    seen = set()
    for row in cycle_doc.applicability:
        f = dict(filters)
        if row.company:
            f["company"] = row.company
        if row.department:
            f["department"] = row.department
        if row.designation:
            f["designation"] = row.designation
        if row.branch:
            f["branch"] = row.branch
        for emp in frappe.get_all("Employee", filters=f, fields=["name", "reports_to"]):
            if emp.name not in seen:
                seen.add(emp.name)
                employees.append(emp)
    return employees
