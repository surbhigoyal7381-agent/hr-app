import frappe

from alvoraa_goals.tests.utils import ensure_employee_prerequisites
import unittest
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, today


def _setup_cascade_with_goals(suffix, company_target, goal_targets):
    company = ensure_employee_prerequisites()
    cascade = frappe.get_doc({
        "doctype": "Goal Cascade",
        "cascade_name": f"Alignment Test {suffix}",
        "company": company,
        "unit": "Orders",
        "period_start": add_days(today(), -30),
        "period_end": add_days(today(), 60),
        "company_target": company_target,
        "status": "Active",
    })
    cascade.insert(ignore_permissions=True)

    emp_name = f"Cascade {suffix} Employee"
    existing_emp = frappe.get_value("Employee", {"employee_name": emp_name}, "name")
    if existing_emp:
        employee = existing_emp
    else:
        emp = frappe.get_doc({
            "doctype": "Employee",
            "first_name": f"Cascade {suffix}",
            "last_name": "Employee",
            "company": company,
            "date_of_joining": today(),
            "gender": "Male",
            "status": "Active",
        })
        emp.insert(ignore_permissions=True)
        employee = emp.name

    goals = []
    for i, tv in enumerate(goal_targets):
        g = frappe.get_doc({
            "doctype": "Individual Goal",
            "employee": employee,
            "goal_name": f"Cascade Goal {suffix}-{i}",
            "goal_cascade": cascade.name,
            "target_value": tv,
            "start_date": add_days(today(), -10),
            "end_date": add_days(today(), 50),
            "status": "Active",
        })
        g.insert(ignore_permissions=True)
        g.submit()
        goals.append(g)

    return cascade, goals


class TestCascade(FrappeTestCase):

    def tearDown(self):
        frappe.db.rollback()

    def test_cascade_alignment_aligned(self):
        from alvoraa_goals.controllers.cascade import run_alignment_check
        # company_target=1000, goals sum=980 => variance=2% => Aligned
        cascade, _ = _setup_cascade_with_goals("Aligned", 1000, [490, 490])
        report = run_alignment_check(cascade.name)
        self.assertEqual(report.status, "Aligned")
        self.assertLess(report.variance_pct, 5)

    def test_cascade_alignment_misaligned(self):
        from alvoraa_goals.controllers.cascade import run_alignment_check
        # company_target=1000, goals sum=500 => variance=50% => Misaligned
        cascade, _ = _setup_cascade_with_goals("Misaligned", 1000, [250, 250])
        report = run_alignment_check(cascade.name)
        self.assertEqual(report.status, "Misaligned")
        self.assertGreaterEqual(report.variance_pct, 5)

    def test_cascade_tree_structure(self):
        from alvoraa_goals.controllers.cascade import get_cascade_tree
        company = ensure_employee_prerequisites()
        cascade = frappe.get_doc({
            "doctype": "Goal Cascade",
            "cascade_name": "Tree Test Cascade",
            "company": company,
            "unit": "Orders",
            "period_start": add_days(today(), -30),
            "period_end": add_days(today(), 60),
            "company_target": 1000,
            "status": "Active",
        })
        cascade.insert(ignore_permissions=True)

        tree_emp_name = "Tree Test Employee"
        existing_emp = frappe.get_value("Employee", {"employee_name": tree_emp_name}, "name")
        if existing_emp:
            employee = existing_emp
        else:
            emp = frappe.get_doc({
                "doctype": "Employee",
                "first_name": "Tree Test",
                "last_name": "Employee",
                "company": company,
                "date_of_joining": today(),
                "gender": "Male",
                "status": "Active",
            })
            emp.insert(ignore_permissions=True)
            employee = emp.name

        parent_goal = frappe.get_doc({
            "doctype": "Individual Goal",
            "employee": employee,
            "goal_name": "Parent Goal",
            "goal_cascade": cascade.name,
            "target_value": 500,
            "start_date": add_days(today(), -10),
            "end_date": add_days(today(), 50),
        })
        parent_goal.insert(ignore_permissions=True)
        parent_goal.submit()

        child_goal = frappe.get_doc({
            "doctype": "Individual Goal",
            "employee": employee,
            "goal_name": "Child Goal",
            "goal_cascade": cascade.name,
            "parent_goal": parent_goal.name,
            "target_value": 200,
            "start_date": add_days(today(), -10),
            "end_date": add_days(today(), 50),
        })
        child_goal.insert(ignore_permissions=True)
        child_goal.submit()

        tree = get_cascade_tree(cascade.name)
        self.assertIn("goals", tree)
        self.assertIn("cascade", tree)
        roots = tree["goals"]
        self.assertEqual(len(roots), 1)
        self.assertEqual(roots[0]["goal_name"], "Parent Goal")
        self.assertEqual(len(roots[0]["children"]), 1)
        self.assertEqual(roots[0]["children"][0]["goal_name"], "Child Goal")
