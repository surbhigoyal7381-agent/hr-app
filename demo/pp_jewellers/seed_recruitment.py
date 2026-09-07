"""
PP Jewellers demo - Block 5: the Senior Sales Executive (Noida) hiring run.

Sources, Skills, Offer Terms, Appointment Letter Template, Staffing Plan,
Job Requisition, Job Opening, 8 Job Applicants (screening answers in the
notes/cover letter until build B3 adds the fields), 3 Interview Types with
expected skills and pass marks, 11 Interviews with 2 Interview Feedbacks
each, Job Offer accepted by Ritika Malhotra, Appointment Letter.

Idempotent.
"""
import os
import sys

sys.path.insert(0, os.environ.get("PPJ_SCRIPT_DIR", "/tmp/ppj"))
from ppj_common import *  # noqa: F401,F403

connect()

DESIG = "Senior Sales Executive"
NOIDA = "PPJ Noida Sector 18"


def emp_by(designation, branch=None, first=True):
    filters = {"designation": designation, "status": "Active"}
    if branch:
        filters["branch"] = branch
    rows = frappe.get_all("Employee", filters=filters, fields=["name", "user_id", "employee_name"], order_by="name asc")
    return rows[0] if (rows and first) else rows


OWNER = emp_by("Owner & Managing Director")
HR_HEAD = emp_by("Head - Human Resources")
RECRUITER = emp_by("Recruitment Executive")
HR_EXEC = emp_by("HR Executive")
NOIDA_SIC = emp_by("Store In-charge", NOIDA)
NOIDA_FM_DIAMOND = emp_by("Floor Manager - Diamond", NOIDA)
NOIDA_SSE = emp_by(DESIG, NOIDA)

# ── Masters ─────────────────────────────────────────────────────────────────
log("Recruitment masters")
for s in ["Naukri", "LinkedIn", "Indeed", "Walk-in", "Employee Referral"]:
    ensure("Job Applicant Source", s, {"source_name": s}, quiet=True)
SKILLS = ["Communication & Grooming", "Jewellery Product Knowledge", "Diamond & Certification Knowledge",
          "Selling & Closing", "Customer Handling", "Integrity & Process Discipline", "Team Coaching",
          "Cultural Fit with PP Jewellers", "Target Orientation"]
for s in SKILLS:
    ensure("Skill", s, {"skill_name": s}, quiet=True)
for t in ["Monthly CTC", "Probation Period", "Notice Period", "Incentive Scheme", "Weekly Off", "Joining Date"]:
    ensure("Offer Term", t, {"offer_term": t}, quiet=True)
ensure("Job Offer Term Template", {"title": "PPJ Store Staff Offer"}, {"offer_terms": [
    {"offer_term": "Monthly CTC", "value": "As per offer"}, {"offer_term": "Probation Period", "value": "6 months"},
    {"offer_term": "Notice Period", "value": "30 days"},
    {"offer_term": "Incentive Scheme", "value": "Category incentive scheme as per policy"},
    {"offer_term": "Weekly Off", "value": "Fixed, Monday to Friday, assigned by store"},
    {"offer_term": "Joining Date", "value": "As per offer"}]})
ensure("Appointment Letter Template", "PPJ Standard Appointment Letter", {
    "template_name": "PPJ Standard Appointment Letter",
    "introduction": "We are pleased to appoint you at PP Jewellers Pvt Ltd on the terms below.",
    "closing_notes": "We look forward to welcoming you to the PP Jewellers family.",
    "terms": [
        {"title": "Position and location", "description": "You are appointed as {designation} at our {location} store, reporting to the Floor Manager."},
        {"title": "Compensation", "description": "Your monthly CTC will be as stated in your offer. Category incentives are paid monthly as per the Category Incentive Policy."},
        {"title": "Probation", "description": "You will be on probation for six months from the date of joining."},
        {"title": "Working hours and weekly off", "description": "Store hours are 9:30 to 18:30, seven days a week, with one fixed weekly off assigned by the store."},
        {"title": "Attendance", "description": "Attendance is recorded on the biometric machine. The Attendance and Late Coming Policy applies."},
        {"title": "Verification", "description": "This appointment is subject to satisfactory background and police verification."},
    ]})
commit()

# ── Staffing Plan (so vacancies are checked on the offer) ──────────────────
log("Staffing Plan")
sp_name = "FY27 Store Staffing"
if not frappe.db.exists("Staffing Plan", sp_name):
    current = frappe.db.count("Employee", {"designation": DESIG, "company": COMPANY, "status": "Active"})
    sp = frappe.get_doc({"doctype": "Staffing Plan", "__newname": sp_name, "name": sp_name, "company": COMPANY,
                         "from_date": FY_START, "to_date": FY_END,
                         # `vacancies` is the input; Frappe HR derives number_of_positions = vacancies + current_count
                         "staffing_details": [{"designation": DESIG, "vacancies": 1,
                                               "estimated_cost_per_position": 42000 * 12}]})
    sp.flags.ignore_permissions = True
    sp.insert()
    sp.submit()
    log(f"  [created] Staffing Plan {sp.name}: {DESIG} vacancies {sp.staffing_details[0].vacancies}")
commit()

# ── Job Requisition ─────────────────────────────────────────────────────────
log("Job Requisition")
jr_name = frappe.db.get_value("Job Requisition", {"designation": DESIG, "requested_by": NOIDA_SIC.name}, "name")
if not jr_name:
    jr = frappe.get_doc({"doctype": "Job Requisition", "designation": DESIG, "department": dept("Sales"),
                         "no_of_positions": 1, "expected_compensation": 40000, "company": COMPANY,
                         "requested_by": NOIDA_SIC.name, "posting_date": "2026-07-06", "expected_by": "2026-08-15",
                         "status": "Pending",
                         "reason_for_requesting": "Replacement: resignation of a Senior Sales Executive on the Diamond floor, Noida.",
                         "description": "Senior Sales Executive for the Diamond floor at Noida Sector 18."})
    jr.insert(ignore_permissions=True)
    jr_name = jr.name
    log(f"  [created] Job Requisition {jr_name}")
frappe.db.set_value("Job Requisition", jr_name, {"status": "Open & Approved"}, update_modified=False)
commit()

# ── Job Opening ─────────────────────────────────────────────────────────────
log("Job Opening")
JD = """<h3>Senior Sales Executive – Diamond Floor</h3>
<p>PP Jewellers is a 40-year-old family jewellery house with five stores across Chandigarh, Ambala, Noida and Delhi. We are looking for a Senior Sales Executive for the Diamond floor at our Noida Sector 18 store.</p>
<p><b>What you will do</b></p><ul>
<li>Sell diamond, platinum and gemstone jewellery to walk-in and appointment customers; own a monthly sales target.</li>
<li>Explain certification (IGI, GIA), the 4Cs, hallmarking and our exchange and buy-back policies clearly and honestly.</li>
<li>Build repeat relationships: follow up with customers before festivals, weddings and anniversaries with the Customer Relationship team.</li>
<li>Coach two to three junior Sales Executives on the floor.</li>
<li>Follow vault, display and billing procedures without exception.</li></ul>
<p><b>What we need</b></p><ul>
<li>3 or more years selling jewellery in an organised retail store, at least 1 year on diamonds.</li>
<li>Comfortable with a 7-day store roster with one fixed weekly off, and with working on festival days.</li>
<li>Fluent Hindi and working English. Punjabi is a plus.</li>
<li>Clean background; police verification is part of joining.</li></ul>
<p><b>What you get</b></p>
<p>₹32,000 to ₹45,000 per month fixed, plus category incentives paid monthly, PF and ESI as applicable, festival working allowance, and a clear appraisal every quarter.</p>"""
JOB_TITLE = "Senior Sales Executive – Diamond Floor (Noida)"
jo_name = frappe.db.get_value("Job Opening", {"job_title": JOB_TITLE}, "name")
if not jo_name:
    jo = frappe.get_doc({"doctype": "Job Opening", "job_title": JOB_TITLE, "company": COMPANY, "designation": DESIG,
                         "department": dept("Sales"), "status": "Open", "publish": 1, "location": NOIDA,
                         "employment_type": "Full-time", "currency": "INR", "lower_range": 32000, "upper_range": 45000,
                         "salary_per": "Month", "publish_salary_range": 1, "job_requisition": jr_name,
                         "staffing_plan": sp_name, "planned_vacancies": 1, "vacancies": 1,
                         "posted_on": "2026-07-08 10:00:00", "closes_on": "2026-08-08", "description": JD,
                         "job_application_route": "ppj-senior-sales-application",
                         # build B3: screen-out rules from file 06 §4
                         "screening_require_retail_experience": 1, "screening_min_years": 3,
                         "screening_require_product_knowledge": 1, "screening_require_roster_ok": 1,
                         "screening_require_festival_ok": 1, "screening_max_monthly_ctc": 50000})
    jo.insert(ignore_permissions=True)
    jo_name = jo.name
    log(f"  [created] Job Opening {jo_name}")
elif frappe.get_meta("Job Opening").has_field("screening_min_years") and not frappe.db.get_value("Job Opening", jo_name, "screening_min_years"):
    frappe.db.set_value("Job Opening", jo_name, {"screening_require_retail_experience": 1, "screening_min_years": 3,
                                                 "screening_require_product_knowledge": 1, "screening_require_roster_ok": 1,
                                                 "screening_require_festival_ok": 1, "screening_max_monthly_ctc": 50000},
                        update_modified=False)
    log(f"  [rules] screening rules set on {jo_name}")
commit()

# ── Application web form with the client's wording (build B3) ──────────────
if frappe.db.exists("Web Form", "screening-application") and not frappe.db.exists("Web Form", {"route": "ppj-senior-sales-application"}):
    log("Web Form ppj-senior-sales-application")
    wf = frappe.copy_doc(frappe.get_doc("Web Form", "screening-application"))
    # a Web Form is named from its title, so the title spells the route
    wf.update({"route": "ppj-senior-sales-application", "is_standard": 0,
               "title": "PPJ Senior Sales Application", "module": None,
               "introduction_text": "<p>Thank you for your interest in PP Jewellers. A few quick questions first, "
                                    "so we can call the right people back.</p>"})
    WORDING = {"screening_retail_experience": "Have you worked in an organised jewellery retail store?",
               "screening_years_in_category": "How many years have you sold jewellery?",
               "screening_product_knowledge": "Can you explain hallmarking and diamond certification to a customer?",
               "screening_roster_ok": "Are you comfortable with a 7-day store roster with one fixed weekly off (not Sunday)?",
               "screening_festival_ok": "Are you available to work on festival days (Dhanteras, Diwali, Akshaya Tritiya)?",
               "screening_category_experience": "Which categories have you sold? (Gold / Diamond / Silver / Platinum)"}
    for f in wf.web_form_fields:
        if f.fieldname in WORDING:
            f.label = WORDING[f.fieldname]
    wf.flags.ignore_permissions = True
    wf.insert()
    commit()
    log(f"  [created] Web Form {wf.name} at /{wf.route}")

# ── Applicants ──────────────────────────────────────────────────────────────
log("Job Applicants")
STATUS = {"Ritika Malhotra": "Accepted", "Vikas Tomar": "Hold", "Shalini Rawat": "Rejected", "Amit Chaudhary": "Rejected",
          "Neha Bisht": "Rejected", "Rohit Sengar": "Rejected", "Preeti Nagar": "Rejected", "Sunil Dhaka": "Rejected"}
applicants = {}
for r in read_csv("applicants.csv"):
    name = frappe.db.get_value("Job Applicant", {"email_id": r["email_id"], "job_title": jo_name}, "name")
    source = "Employee Referral" if r["source"].startswith("Employee referral") else r["source"]
    # build B3: the answers go into the screening fields; the opening's rules judge them on insert
    screening = {"screening_retail_experience": r["q1_jewellery_retail_experience"],
                 "screening_years_in_category": cint(r["q2_years_in_jewellery"]),
                 "screening_product_knowledge": r["q3_gold_diamond_knowledge"],
                 "screening_roster_ok": r["q4_ok_with_7day_roster"],
                 "screening_festival_ok": r["q5_ok_with_festival_work"],
                 "screening_availability": r["q6_availability"],
                 "screening_current_employer": r["current_employer"],
                 "screening_category_experience": r["category_experience"],
                 "screening_expected_monthly_ctc": flt(r["expected_monthly_ctc"])}
    if not name:
        ja = frappe.get_doc({"doctype": "Job Applicant", "applicant_name": r["applicant_name"], "email_id": r["email_id"],
                             "phone_number": r["phone_number"], "country": "India", "status": "Open",
                             "job_title": jo_name, "designation": DESIG, "source": source,
                             "cover_letter": f"{r['total_experience_years']} years in jewellery retail, "
                                             f"categories: {r['category_experience']}.",
                             "notes": r["outcome"][:140], "currency": "INR", "lower_range": flt(r["expected_monthly_ctc"]),
                             "upper_range": flt(r["expected_monthly_ctc"]), **screening})
        ja.insert(ignore_permissions=True)
        name = ja.name
        log(f"  [created] Job Applicant {name}: {r['applicant_name']} -> {ja.get('screening_result') or 'not screened'}")
    elif not frappe.db.get_value("Job Applicant", name, "screening_result"):
        ja = frappe.get_doc("Job Applicant", name)      # created before build B3: fill the answers and screen
        ja.update(screening)
        ja.save(ignore_permissions=True)
        log(f"  [screened] Job Applicant {name}: {r['applicant_name']} -> {ja.get('screening_result') or 'not screened'}")
    applicants[r["applicant_name"]] = name
commit()

# Employee referral for Shalini
ref_name = frappe.db.get_value("Employee Referral", {"email": "shalini.rawat@example.demo"}, "name")
if not ref_name:
    ref = frappe.get_doc({"doctype": "Employee Referral", "first_name": "Shalini", "last_name": "Rawat",
                          "email": "shalini.rawat@example.demo", "contact_no": "9811000103", "date": "2026-07-10",
                          "current_employer": "PC Jeweller, Noida", "current_job_title": "Sales Executive",
                          "for_designation": DESIG, "referrer": NOIDA_SSE.name, "is_applicable_for_referral_bonus": 1,
                          "qualification_reason": "Worked with her at a previous store; strong on diamond counters."})
    ref.insert(ignore_permissions=True)
    ref.submit()
    ref_name = ref.name
    frappe.db.set_value("Job Applicant", applicants["Shalini Rawat"],
                        {"employee_referral": ref_name, "source_name": NOIDA_SSE.name}, update_modified=False)
    log(f"  [created] Employee Referral {ref_name}")
commit()

# ── Interview Types (rounds) ────────────────────────────────────────────────
log("Interview Types")
ROUNDS = {
    "R1 HR Screening": (["Communication & Grooming", "Jewellery Product Knowledge", "Target Orientation"], 3.0,
                        [RECRUITER.user_id, HR_EXEC.user_id]),
    "R2 Store In-charge": (["Diamond & Certification Knowledge", "Selling & Closing", "Customer Handling",
                            "Integrity & Process Discipline", "Team Coaching"], 3.5,
                           [NOIDA_SIC.user_id, NOIDA_FM_DIAMOND.user_id]),
    "R3 Owner Round": (["Cultural Fit with PP Jewellers", "Integrity & Process Discipline", "Target Orientation"], 4.0,
                       [OWNER.user_id, HR_HEAD.user_id]),
}
for rname, (skills, pass_mark, users) in ROUNDS.items():
    ensure("Interview Type", rname, {"interview_type_name": rname, "designation": DESIG,
                                     "expected_average_rating": pass_mark / 5.0,
                                     "expected_skill_set": [{"skill": s, "description": s} for s in skills],
                                     "interviewers": [{"user": u} for u in users],
                                     "description": f"Pass mark {pass_mark}/5"})
commit()

# ── Interviews and feedback ─────────────────────────────────────────────────
log("Interviews and Interview Feedback")
# (applicant, round, date, result, {skill: rating}, feedback text)
PLAN = [
    ("Ritika Malhotra", "R1 HR Screening", "2026-07-15", "Cleared", {"Communication & Grooming": 4.5, "Jewellery Product Knowledge": 4, "Target Orientation": 4.5},
     "Clear, warm, confident. Ran a diamond counter at Tanishq. Comfortable with the 7-day roster."),
    ("Ritika Malhotra", "R2 Store In-charge", "2026-07-24", "Cleared", {"Diamond & Certification Knowledge": 4.5, "Selling & Closing": 4.5, "Customer Handling": 4.5, "Integrity & Process Discipline": 4, "Team Coaching": 4},
     "Explained 4Cs and IGI vs GIA clearly. Handled the 'why is your making charge higher' objection well. Ready for the floor."),
    ("Ritika Malhotra", "R3 Owner Round", "2026-08-12", "Cleared", {"Cultural Fit with PP Jewellers": 5, "Integrity & Process Discipline": 4.5, "Target Orientation": 4.5},
     "Talks about customers as families. Wants to build a career here. Offer."),
    ("Vikas Tomar", "R1 HR Screening", "2026-07-15", "Cleared", {"Communication & Grooming": 3.5, "Jewellery Product Knowledge": 4, "Target Orientation": 3.5},
     "Solid gold-floor experience at Kalyan. Less exposure to diamonds."),
    ("Vikas Tomar", "R2 Store In-charge", "2026-07-24", "Cleared", {"Diamond & Certification Knowledge": 3.5, "Selling & Closing": 4, "Customer Handling": 4, "Integrity & Process Discipline": 4, "Team Coaching": 3.5},
     "Good closer. Needs certification training for the diamond floor."),
    ("Vikas Tomar", "R3 Owner Round", "2026-08-12", "Under Review", {"Cultural Fit with PP Jewellers": 3.5, "Integrity & Process Discipline": 4, "Target Orientation": 3.5},
     "Capable but below the bar for this floor. Keep on hold for the next Gold-floor opening."),
    ("Shalini Rawat", "R1 HR Screening", "2026-07-16", "Cleared", {"Communication & Grooming": 3.5, "Jewellery Product Knowledge": 3, "Target Orientation": 3.5},
     "Referred by our Noida team. Not available on festival days - flagged for R2."),
    ("Shalini Rawat", "R2 Store In-charge", "2026-07-25", "Rejected", {"Diamond & Certification Knowledge": 2, "Selling & Closing": 3, "Customer Handling": 3, "Integrity & Process Discipline": 3, "Team Coaching": 2},
     "Could not explain certification grades. Festival-day constraint confirmed. Not for this role."),
    ("Amit Chaudhary", "R1 HR Screening", "2026-07-16", "Cleared", {"Communication & Grooming": 4, "Jewellery Product Knowledge": 3.5, "Target Orientation": 3.5},
     "7 years at Reliance Jewels. Asked for a fixed Sunday off - flagged."),
    ("Amit Chaudhary", "R2 Store In-charge", "2026-07-25", "Rejected", {"Diamond & Certification Knowledge": 3, "Selling & Closing": 3.5, "Customer Handling": 3, "Integrity & Process Discipline": 4, "Team Coaching": 2.5},
     "Honest and process-minded, but insists on Sunday off. Sunday is our biggest day."),
    ("Neha Bisht", "R1 HR Screening", "2026-07-17", "Cleared", {"Communication & Grooming": 3, "Jewellery Product Knowledge": 3, "Target Orientation": 3},
     "Meets the bar. Withdrew before R2 (accepted another offer)."),
]
for applicant, rname, date, result, ratings, text in PLAN:
    ja = applicants[applicant]
    iv_name = frappe.db.get_value("Interview", {"job_applicant": ja, "interview_type": rname, "docstatus": ["!=", 2]}, "name")
    if iv_name:
        continue
    users = ROUNDS[rname][2]
    iv = frappe.get_doc({"doctype": "Interview", "job_applicant": ja, "job_opening": jo_name, "interview_type": rname,
                         "designation": DESIG, "status": "Pending", "scheduled_on": date, "from_time": "11:00:00",
                         "to_time": "11:45:00", "expected_average_rating": ROUNDS[rname][1] / 5.0,
                         "interview_details": [{"interviewer": u} for u in users], "interview_summary": text})
    iv.flags.ignore_permissions = True
    iv.insert()
    for i, u in enumerate(users):
        # second interviewer rates half a point lower on one skill for a little spread
        fb = frappe.get_doc({"doctype": "Interview Feedback", "interview": iv.name, "interviewer": u,
                             "job_applicant": ja, "interview_type": rname, "feedback": text,
                             # Interview Feedback needs a verdict; a split decision leaves the interview Under Review
                             "result": result if result in ("Cleared", "Rejected") else ("Cleared" if i == 0 else "Rejected"),
                             "skill_assessment": [{"skill": s, "rating": max(0.2, (v - (0.5 if (i and j == 0) else 0)) / 5.0)}
                                                  for j, (s, v) in enumerate(ratings.items())]})
        fb.flags.ignore_permissions = True
        fb.insert()
        fb.submit()
    iv.reload()
    iv.status = result
    iv.flags.ignore_permissions = True
    iv.save()
    if result in ("Cleared", "Rejected"):
        iv.submit()
    log(f"  [created] Interview {iv.name}: {applicant} / {rname} -> {result} (avg {round(iv.average_rating * 5, 2)})")
commit()

for applicant, status in STATUS.items():
    frappe.db.set_value("Job Applicant", applicants[applicant], "status", status, update_modified=False)
commit()

# ── Offer and appointment letter ────────────────────────────────────────────
log("Job Offer and Appointment Letter")
ritika = applicants["Ritika Malhotra"]
offer_name = frappe.db.get_value("Job Offer", {"job_applicant": ritika, "docstatus": ["!=", 2]}, "name")
if not offer_name:
    offer = frappe.get_doc({"doctype": "Job Offer", "job_applicant": ritika, "applicant_name": "Ritika Malhotra",
                            "applicant_email": "ritika.malhotra@ppjewellers.demo", "status": "Awaiting Response",
                            "offer_date": "2026-08-18", "designation": DESIG, "company": COMPANY,
                            "job_offer_term_template": frappe.db.get_value("Job Offer Term Template", {"title": "PPJ Store Staff Offer"}, "name"),
                            "offer_terms": [
                                {"offer_term": "Monthly CTC", "value": "₹42,000 per month"},
                                {"offer_term": "Probation Period", "value": "6 months"},
                                {"offer_term": "Notice Period", "value": "30 days"},
                                {"offer_term": "Incentive Scheme", "value": "Category incentive scheme as per policy"},
                                {"offer_term": "Weekly Off", "value": "Fixed, Monday to Friday, assigned by store"},
                                {"offer_term": "Joining Date", "value": "1 September 2026"}]})
    offer.flags.ignore_permissions = True
    offer.insert()
    offer.submit()
    offer_name = offer.name
    log(f"  [created] Job Offer {offer_name}")
frappe.db.set_value("Job Offer", offer_name, "status", "Accepted", update_modified=False)
frappe.db.set_value("Job Applicant", ritika, "status", "Accepted", update_modified=False)
if not frappe.db.exists("Appointment Letter", {"job_applicant": ritika}):
    al = frappe.get_doc({"doctype": "Appointment Letter", "job_applicant": ritika, "applicant_name": "Ritika Malhotra",
                         "appointment_date": "2026-09-01", "company": COMPANY,
                         "appointment_letter_template": "PPJ Standard Appointment Letter"})
    tpl = frappe.get_doc("Appointment Letter Template", "PPJ Standard Appointment Letter")
    al.introduction = tpl.introduction
    al.closing_notes = tpl.closing_notes
    for t in tpl.terms:
        al.append("terms", {"title": t.title, "description": t.description.replace("{designation}", DESIG).replace("{location}", "Noida Sector 18")})
    al.insert(ignore_permissions=True)
    log(f"  [created] Appointment Letter {al.name}")
frappe.db.set_value("Job Requisition", jr_name, {"status": "Filled", "completed_on": "2026-08-24"}, update_modified=False)
frappe.db.set_value("Job Opening", jo_name, {"status": "Closed", "closed_on": "2026-08-24"}, update_modified=False)
commit()

log("Block 5 done")
counts("Job Requisition", "Job Opening", "Job Applicant", "Interview", "Interview Feedback", "Job Offer", "Appointment Letter")
