import frappe

from alvoraa_goals.tests.utils import ensure_employee, ensure_employee_prerequisites
import unittest
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, today, now_datetime


def _make_cascade_and_goal(suffix="EvidTest"):
    company = ensure_employee_prerequisites()
    cascade = frappe.get_doc({
        "doctype": "Goal Cascade",
        "cascade_name": f"Evid Test Cascade {suffix}",
        "company": company,
        "unit": "Orders",
        "period_start": add_days(today(), -30),
        "period_end": add_days(today(), 60),
        "company_target": 500,
        "status": "Active",
    })
    cascade.insert(ignore_permissions=True)

    employee = ensure_employee(f"Evid {suffix}")

    goal = frappe.get_doc({
        "doctype": "Individual Goal",
        "employee": employee,
        "goal_name": f"Evidence Goal {suffix}",
        "goal_cascade": cascade.name,
        "target_value": 200,
        "start_date": add_days(today(), -10),
        "end_date": add_days(today(), 50),
        "status": "Active",
    })
    goal.insert(ignore_permissions=True)
    goal.submit()
    return goal


class TestEvidence(FrappeTestCase):

    def tearDown(self):
        frappe.db.rollback()

    @unittest.skip(
        "Stale: exercises validate_evidence via hand-built stub objects that no longer match the controller. Evidence validation is being replaced by the KPI automation work (KPI Fact / KPI Metric Definition), so these are parked rather than rewritten twice. See KPI_AUTOMATION_STRATEGY.md and backlog KPIA-6..KPIA-18."
    )
    def test_evidence_approved_on_valid_invoice(self):
        from alvoraa_goals.validators.invoice_validator import validate_invoice
        goal = _make_cascade_and_goal("InvValid")

        class FakeEvidence:
            name = "test-inv-ev"
            extracted_date = today()
            extracted_amount = 5000.0
            extracted_order_count = None

        errors = validate_invoice(FakeEvidence(), goal)
        self.assertEqual(errors, [], f"Expected no errors but got: {errors}")

    @unittest.skip(
        "Stale: exercises validate_evidence via hand-built stub objects that no longer match the controller. Evidence validation is being replaced by the KPI automation work (KPI Fact / KPI Metric Definition), so these are parked rather than rewritten twice. See KPI_AUTOMATION_STRATEGY.md and backlog KPIA-6..KPIA-18."
    )
    def test_evidence_pending_on_manual_entry(self):
        from alvoraa_goals.controllers.evidence import validate_evidence

        goal = _make_cascade_and_goal("ManualPend")

        class FakeManualEvidence:
            parent = goal.name
            upload_date = None
            uploaded_by = None
            evidence_type = "Manual Entry"
            extracted_date = None
            extracted_amount = None
            extracted_order_count = None
            name = "new"
            validation_status = None
            approved_by = None
            approved_on = None

        validate_evidence(FakeManualEvidence(), None)
        self.assertEqual(FakeManualEvidence.validation_status, "Pending")

    def test_duplicate_detection(self):
        from alvoraa_goals.validators.duplicate_detector import _similarity_score

        class Ev1:
            extracted_amount = 10000.0
            extracted_order_count = 5
            extracted_date = today()

        ev2_dict = {
            "extracted_amount": 10000.0,
            "extracted_order_count": 5,
            "extracted_date": today(),
        }
        score = _similarity_score(Ev1(), ev2_dict)
        # amount match=40, count match=30, date match=30 => 100
        self.assertGreaterEqual(score, 80, f"Expected score >= 80, got {score}")
