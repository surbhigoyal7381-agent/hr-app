import frappe
from frappe.model.document import Document
from frappe.utils.nestedset import NestedSet


class Department(NestedSet):
    nsm_parent_field = "parent_department"

    def autoname(self):
        root = self.get_root()
        if self.is_group and not self.parent_department:
            self.name = self.department_name
        else:
            self.name = get_abbreviated_name(self.department_name, self.company)

    def get_root(self):
        try:
            return frappe.db.get_value("Department", {"is_group": 1, "parent_department": ""}, "name")
        except Exception:
            return None

    def on_update(self):
        super().on_update()


def get_abbreviated_name(name, company):
    abbr = frappe.db.get_value("Company", company, "abbr") or ""
    return f"{name} - {abbr}" if abbr else name
