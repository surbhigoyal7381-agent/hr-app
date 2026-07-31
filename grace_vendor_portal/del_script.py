import frappe

def run():
    appraisals = frappe.db.sql("SELECT count(*) as c FROM tabAppraisal")[0][0]
    cycles = frappe.db.sql("SELECT count(*) as c FROM `tabAppraisal Cycle`")[0][0]
    print("Appraisals: " + str(appraisals) + ", Cycles: " + str(cycles))

    frappe.db.sql("DELETE FROM tabAppraisalGoal")
    frappe.db.sql("DELETE FROM tabAppraisalKPIItem")
    frappe.db.sql("DELETE FROM `tabGrace Appraisal Extension`")
    frappe.db.sql("DELETE FROM tabAppraisal")
    frappe.db.sql("DELETE FROM `tabAppraisal Cycle`")
    frappe.db.sql("DELETE FROM `tabGrace Cycle Config`")
    frappe.db.commit()
    print("All deleted.")

run()
