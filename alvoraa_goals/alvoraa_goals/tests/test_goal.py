import frappe

from alvoraa_goals.tests.utils import ensure_employee_prerequisites
import unittest
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, today


def _make_cascade(suffix="Test"):
    company = ensure_employee_prerequisites()
    cascade = frappe.get_doc({
        "doctype": "Goal Cascade",
        "cascade_name": f"Test Cascade {suffix}",
        "company": company,
        "unit": "Orders",
        "period_start": add_days(today(), -30),
        "period_end": add_days(today(), 60),
        "company_target": 1000,
        "status": "Active",
    })
    cascade.insert(ignore_permissions=True)
    return cascade


def _make_employee(name_suffix="GoalTest"):
    employee_name = f"Test {name_suffix} Employee"
    existing = frappe.get_value("Employee", {"employee_name": employee_name}, "name")
    if existing:
        return existing
    company = ensure_employee_prerequisites()
    emp = frappe.get_doc({
        "doctype": "Employee",
        "first_name": f"Test {name_suffix}",
        "last_name": "Employee",
        "company": company,
        "date_of_joining": today(),
        "gender": "Male",
        "status": "Active",
    })
    emp.insert(ignore_permissions=True)
    return emp.name


class TestGoal(FrappeTestCase):

    def setUp(self):
        self.cascade = _make_cascade("GoalTest")
        self.employee = _make_employee("Goal")

    def tearDown(self):
        frappe.db.rollback()

    def _make_goal(self, **kwargs):
        defaults = {
            "doctype": "Individual Goal",
            "employee": self.employee,
            "goal_name": "Test Goal",
            "goal_cascade": self.cascade.name,
            "target_value": 100,
            "start_date": add_days(today(), -10),
            "end_date": add_days(today(), 50),
            "status": "Active",
        }
        defaults.update(kwargs)
        return frappe.get_doc(defaults)

    def test_goal_validation_target_zero(self):
        goal = self._make_goal(target_value=0)
        with self.assertRaises(frappe.ValidationError):
            goal.insert(ignore_permissions=True)

    def test_goal_validation_date_order(self):
        goal = self._make_goal(
            start_date=add_days(today(), 10),
            end_date=add_days(today(), -10)
        )
        with self.assertRaises(frappe.ValidationError):
            goal.insert(ignore_permissions=True)

    def test_trajectory_on_track(self):
        # 40% of time elapsed (40 out of 100 days), 50% progress => On Track
        from alvoraa_goals.controllers.goal import _update_trajectory
        goal = self._make_goal(
            start_date=add_days(today(), -40),
            end_date=add_days(today(), 60),
            target_value=100,
            actual_progress=50,
        )
        goal.insert(ignore_permissions=True)
        _update_trajectory(goal)
        self.assertEqual(goal.trajectory, "On Track")

    def test_trajectory_at_risk(self):
        # 50% elapsed (50 of 100 days), expected 50%, actual 40% => At Risk (40 >= 50*0.75=37.5)
        from alvoraa_goals.controllers.goal import _update_trajectory
        goal = self._make_goal(
            start_date=add_days(today(), -50),
            end_date=add_days(today(), 50),
            target_value=100,
            actual_progress=40,
        )
        goal.insert(ignore_permissions=True)
        _update_trajectory(goal)
        self.assertEqual(goal.trajectory, "At Risk")

    def test_trajectory_off_track(self):
        # 80% elapsed (80 of 100 days), expected 80%, actual 10% => Off Track (10 < 80*0.75=60)
        from alvoraa_goals.controllers.goal import _update_trajectory
        goal = self._make_goal(
            start_date=add_days(today(), -80),
            end_date=add_days(today(), 20),
            target_value=100,
            actual_progress=10,
        )
        goal.insert(ignore_permissions=True)
        _update_trajectory(goal)
        self.assertEqual(goal.trajectory, "Off Track")

    def test_progress_calculation(self):
        from alvoraa_goals.controllers.goal import recalculate_progress
        goal = self._make_goal(target_value=100)
        goal.insert(ignore_permissions=True)
        goal.submit()
        # Insert approved evidence directly via SQL to bypass hooks
        ev_name = f"test-ev-{goal.name}"
        frappe.db.sql("""
            INSERT INTO `tabGoal Evidence`
            (name, parent, parenttype, parentfield, evidence_type, extracted_order_count,
             validation_status, idx, docstatus)
            VALUES (%(name)s, %(parent)s, 'Individual Goal', 'evidence_items',
             'Sales Order', %(count)s, 'Approved', 1, 0)
        """, {"name": ev_name, "parent": goal.name, "count": 42})
        frappe.db.commit()
        recalculate_progress(goal.name)
        refreshed = frappe.get_doc("Individual Goal", goal.name)
        self.assertEqual(refreshed.actual_progress, 42)
