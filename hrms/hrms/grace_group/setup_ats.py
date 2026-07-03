"""
Grace Group FMCG Distribution – Recruitment & ATS Setup
Configures the full Applicant Tracking System flow for hiring Delivery Executives.

Sections:
  1. Skills (prerequisites for Interview Types)
  2. Job Requisition & Job Opening
  3. Interview Types (Round masters)
  4. Offer Terms & Job Offer Term Template
  5. Candidate flow: Job Applicant → Interview (×2) → Job Offer

Run: bench execute hrms.grace_group.setup_ats.setup_all
"""

import frappe
from frappe.utils import today, add_days, nowtime


COMPANY = "Grace Group"
COMPANY_ABBR = "GG"
OFFER_TEMPLATE = "Standard Delivery Executive Terms"
JOB_OPENING_TITLE = "Delivery Executive – Q-Comm Expansion"
CANDIDATE_NAME = "Manjit Singh"
CANDIDATE_EMAIL = "manjit.singh@demo.gracegrp.in"


def _exists(doctype, name):
    return bool(frappe.db.exists(doctype, name))


def _dept(name):
    return f"{name} - {COMPANY_ABBR}"


def _get_employee(first_name, last_name):
    return frappe.db.get_value(
        "Employee",
        {"first_name": first_name, "last_name": last_name, "company": COMPANY},
        "name",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Prerequisites: Skills
# ─────────────────────────────────────────────────────────────────────────────

def setup_skills():
    skills = [
        ("Route Knowledge",              "Knowledge of city/town road networks and delivery zones"),
        ("Vehicle Handling",             "Ability to operate LCV and 2-wheeler delivery vehicles safely"),
        ("Defensive Driving",            "Certified defensive driving techniques for urban logistics"),
        ("Commercial Driving License",   "Valid CDL for LMV/Transport vehicles as per RTO norms"),
        ("Cold Chain Handling",          "Basic cold storage and perishable goods handling protocols"),
        ("Q-Comm SLA Awareness",         "Understanding of Quick Commerce SLA windows and escalation SOPs"),
    ]
    created = {}
    for skill_name, desc in skills:
        if not _exists("Skill", skill_name):
            frappe.get_doc({
                "doctype": "Skill",
                "skill_name": skill_name,
                "description": desc,
            }).insert(ignore_permissions=True)
            print(f"  [+] Skill: {skill_name}")
        created[skill_name] = skill_name
    return created


# ─────────────────────────────────────────────────────────────────────────────
# Section 1: Job Requisition & Job Opening
# ─────────────────────────────────────────────────────────────────────────────

def setup_job_requisition():
    # Check for an existing requisition for this designation/company
    existing = frappe.db.get_value(
        "Job Requisition",
        {
            "designation": "Delivery Executive",
            "company": COMPANY,
            "no_of_positions": 5,
        },
        "name",
    )
    if existing:
        print(f"  [=] Job Requisition already exists: {existing}")
        return existing

    requested_by = _get_employee("Gurpreet", "Singh")  # Logistics Manager
    if not requested_by:
        print("  [!] Gurpreet Singh not found — run setup_grace_group.setup_all first")
        return None

    doc = frappe.get_doc({
        "doctype": "Job Requisition",
        "designation": "Delivery Executive",
        "department": _dept("Logistics"),
        "no_of_positions": 5,
        "expected_compensation": 25000,
        "status": "Open & Approved",
        "company": COMPANY,
        "requested_by": requested_by,
        "posting_date": today(),
        "expected_by": add_days(today(), 30),
        "reason_for_requesting": "Scaling Q-Comm operations for Swiggy/Zepto",
        "description": (
            "<p>Grace Group requires 5 additional Delivery Executives to handle the surge in "
            "Quick Commerce (Q-Comm) volume from Swiggy Instamart and Zepto partnerships. "
            "These roles are critical for maintaining SLA compliance during peak demand windows "
            "(Diwali, IPL season, end-of-month spikes). Candidates must hold a valid CDL and "
            "have experience with urban last-mile logistics.</p>"
        ),
    })
    doc.insert(ignore_permissions=True)
    print(f"  [+] Job Requisition: {doc.name} (5 × Delivery Executive)")
    return doc.name


def setup_job_opening(requisition_name):
    existing = frappe.db.get_value(
        "Job Opening", {"job_title": JOB_OPENING_TITLE, "company": COMPANY}, "name"
    )
    if existing:
        print(f"  [=] Job Opening already exists: {existing}")
        return existing

    doc = frappe.get_doc({
        "doctype": "Job Opening",
        "job_title": JOB_OPENING_TITLE,
        "company": COMPANY,
        "designation": "Delivery Executive",
        "department": _dept("Logistics"),
        "status": "Open",
        "publish": 1,
        "vacancies": 5,
        "route": "General Trade & Q-Comm",
        "job_requisition": requisition_name,
        "posted_on": frappe.utils.now(),
        "closes_on": add_days(today(), 45),
        "description": (
            "<p><strong>Role:</strong> Delivery Executive — Q-Comm & General Trade</p>"
            "<p><strong>Key Responsibilities:</strong></p>"
            "<ul>"
            "<li>Execute Q-Comm deliveries for Swiggy Instamart / Zepto within 10-minute SLA windows</li>"
            "<li>Manage General Trade (GT) route drops across Chandigarh/Panchkula territory</li>"
            "<li>Log daily routes and RTOs in the Frappe Daily Route Log system via mobile app</li>"
            "<li>Maintain assigned PB-65 series vehicle and report defects immediately</li>"
            "</ul>"
            "<p><strong>Requirements:</strong> Valid CDL, 2+ years urban delivery experience, "
            "smartphone literacy for Frappe mobile attendance.</p>"
        ),
    })
    doc.insert(ignore_permissions=True)
    print(f"  [+] Job Opening: {doc.name} -- {JOB_OPENING_TITLE}")
    return doc.name


# ─────────────────────────────────────────────────────────────────────────────
# Section 2: Interview Types (Round Masters)
# ─────────────────────────────────────────────────────────────────────────────

def setup_interview_types():
    rounds = [
        {
            "interview_type_name": "Route Knowledge & Background Verification",
            "description": (
                "HR-led in-person round assessing candidate's familiarity with Chandigarh/Panchkula "
                "delivery zones, Q-Comm SLA awareness, and background/CDL verification."
            ),
            "skills": ["Route Knowledge", "Q-Comm SLA Awareness", "Commercial Driving License"],
            "expected_average_rating": 3.0,
        },
        {
            "interview_type_name": "Practical Driving & Vehicle Handling Test",
            "description": (
                "Logistics Manager-evaluated practical test. Candidate drives PB-65 series LCV "
                "on a test route, assessed on vehicle handling, defensive driving, and cold chain "
                "cargo securing."
            ),
            "skills": ["Vehicle Handling", "Defensive Driving", "Cold Chain Handling"],
            "expected_average_rating": 3.5,
        },
    ]

    created_names = []
    for r in rounds:
        name = r["interview_type_name"]
        if _exists("Interview Type", name):
            print(f"  [=] Interview Type already exists: {name}")
            created_names.append(name)
            continue

        skill_rows = [
            {"doctype": "Expected Skill Set", "skill": s}
            for s in r["skills"]
        ]

        frappe.get_doc({
            "doctype": "Interview Type",
            "interview_type_name": name,
            "description": r["description"],
            "expected_average_rating": r["expected_average_rating"],
            "expected_skill_set": skill_rows,
        }).insert(ignore_permissions=True)
        print(f"  [+] Interview Type: {name}")
        created_names.append(name)

    return created_names


# ─────────────────────────────────────────────────────────────────────────────
# Section 3: Offer Terms & Job Offer Term Template
# ─────────────────────────────────────────────────────────────────────────────

_OFFER_TERMS = [
    {
        "name": "Base Compensation",
        "value": (
            "₹25,000/month fixed (₹20,000 basic + ₹5,000 transport allowance). "
            "Reviewed annually based on performance appraisal score."
        ),
    },
    {
        "name": "Q-Comm SLA Bonus",
        "value": (
            "Variable monthly bonus of ₹3,000–₹6,000 based on zero-penalty Q-Comm delivery record. "
            "Forfeited entirely if SLA penalty count exceeds 2 in a calendar month. "
            "Paid out with the following month's salary."
        ),
    },
    {
        "name": "Asset Responsibility",
        "value": (
            "Driver is solely responsible for routine maintenance logging of their assigned "
            "PB-65 series vehicle in the Frappe Fleet Management system. "
            "Failure to log on-time servicing will result in vehicle allowance deduction of ₹500/month. "
            "Major damage due to negligence will be assessed by the Logistics Manager."
        ),
    },
]


def setup_offer_terms():
    created = {}
    for term in _OFFER_TERMS:
        if not _exists("Offer Term", term["name"]):
            frappe.get_doc({
                "doctype": "Offer Term",
                "offer_term": term["name"],
            }).insert(ignore_permissions=True)
            print(f"  [+] Offer Term: {term['name']}")
        created[term["name"]] = term["name"]
    return created


def setup_offer_term_template():
    if _exists("Job Offer Term Template", OFFER_TEMPLATE):
        print(f"  [=] Offer Template already exists: {OFFER_TEMPLATE}")
        return OFFER_TEMPLATE

    term_rows = [
        {
            "doctype": "Job Offer Term",
            "offer_term": t["name"],
            "value": t["value"],
        }
        for t in _OFFER_TERMS
    ]

    frappe.get_doc({
        "doctype": "Job Offer Term Template",
        "title": OFFER_TEMPLATE,
        "offer_terms": term_rows,
    }).insert(ignore_permissions=True)
    print(f"  [+] Job Offer Term Template: {OFFER_TEMPLATE}")
    return OFFER_TEMPLATE


# ─────────────────────────────────────────────────────────────────────────────
# Section 4: Candidate Flow – Manjit Singh
# ─────────────────────────────────────────────────────────────────────────────

def create_job_applicant(job_opening_name):
    existing = frappe.db.get_value(
        "Job Applicant",
        {"applicant_name": CANDIDATE_NAME, "email_id": CANDIDATE_EMAIL},
        "name",
    )
    if existing:
        print(f"  [=] Job Applicant already exists: {existing}")
        return existing

    doc = frappe.get_doc({
        "doctype": "Job Applicant",
        "applicant_name": CANDIDATE_NAME,
        "email_id": CANDIDATE_EMAIL,
        "phone_number": "+91-98760-11223",
        "status": "Shortlisted",
        "job_title": job_opening_name,
        "designation": "Delivery Executive",
        "cover_letter": (
            "I am an experienced commercial vehicle driver with 4 years of last-mile delivery "
            "experience in Chandigarh urban zones, including 2 years specifically on Quick Commerce "
            "routes for Swiggy. I hold a valid LMV transport CDL and am familiar with cold chain "
            "handling protocols. I am seeking to join Grace Group's expanding Q-Comm fleet."
        ),
    })
    doc.insert(ignore_permissions=True)
    print(f"  [+] Job Applicant: {doc.name} — {CANDIDATE_NAME}")
    return doc.name


def create_interviews(applicant_name, job_opening_name, interview_type_names):
    round_1_type = interview_type_names[0] if len(interview_type_names) > 0 else None
    round_2_type = interview_type_names[1] if len(interview_type_names) > 1 else None

    interviews = []

    # Round 1 – HR Background Check (Day +3)
    if round_1_type:
        existing_r1 = frappe.db.get_value(
            "Interview",
            {"job_applicant": applicant_name, "interview_type": round_1_type},
            "name",
        )
        if existing_r1:
            print(f"  [=] Interview Round 1 already exists: {existing_r1}")
            interviews.append(existing_r1)
        else:
            r1 = frappe.get_doc({
                "doctype": "Interview",
                "job_applicant": applicant_name,
                "job_opening": job_opening_name,
                "interview_type": round_1_type,
                "designation": "Delivery Executive",
                "status": "Cleared",
                "scheduled_on": add_days(today(), 3),
                "from_time": "10:00:00",
                "to_time": "11:30:00",
                "interview_summary": (
                    "Candidate demonstrated strong knowledge of Chandigarh Sector 17–35 zone delivery "
                    "routes and Q-Comm 10-minute SLA constraints. Background check cleared — "
                    "CDL verified (LMV Transport, valid until 2029). No criminal record. "
                    "Recommended for Round 2."
                ),
            })
            r1.insert(ignore_permissions=True)
            print(f"  [+] Interview Round 1: {r1.name} (Route Knowledge — Cleared)")
            interviews.append(r1.name)

    # Round 2 – Practical Driving Test (Day +7, evaluated by Logistics Manager)
    if round_2_type:
        existing_r2 = frappe.db.get_value(
            "Interview",
            {"job_applicant": applicant_name, "interview_type": round_2_type},
            "name",
        )
        if existing_r2:
            print(f"  [=] Interview Round 2 already exists: {existing_r2}")
            interviews.append(existing_r2)
        else:
            r2 = frappe.get_doc({
                "doctype": "Interview",
                "job_applicant": applicant_name,
                "job_opening": job_opening_name,
                "interview_type": round_2_type,
                "designation": "Delivery Executive",
                "status": "Cleared",
                "scheduled_on": add_days(today(), 7),
                "from_time": "09:00:00",
                "to_time": "12:00:00",
                "interview_summary": (
                    "Evaluated by Gurpreet Singh (Logistics Manager) on the Chandigarh Warehouse "
                    "test circuit. Candidate completed the PB-65 LCV handling test with zero incidents. "
                    "Cold chain cargo securing assessed — passed. Defensive driving score: 4.2/5. "
                    "Strongly recommended for offer."
                ),
            })
            r2.insert(ignore_permissions=True)
            print(f"  [+] Interview Round 2: {r2.name} (Practical Driving — Cleared)")
            interviews.append(r2.name)

    return interviews


def create_job_offer(applicant_name):
    existing = frappe.db.get_value(
        "Job Offer", {"job_applicant": applicant_name}, "name"
    )
    if existing:
        print(f"  [=] Job Offer already exists: {existing}")
        return existing

    # Build offer terms from the template definition
    term_rows = [
        {
            "doctype": "Job Offer Term",
            "offer_term": t["name"],
            "value": t["value"],
        }
        for t in _OFFER_TERMS
    ]

    doc = frappe.get_doc({
        "doctype": "Job Offer",
        "job_applicant": applicant_name,
        "applicant_name": CANDIDATE_NAME,
        "applicant_email": CANDIDATE_EMAIL,
        "designation": "Delivery Executive",
        "company": COMPANY,
        "offer_date": add_days(today(), 10),
        "status": "Awaiting Response",
        "job_offer_term_template": OFFER_TEMPLATE,
        "offer_terms": term_rows,
    })
    doc.insert(ignore_permissions=True)
    print(f"  [+] Job Offer: {doc.name} → {CANDIDATE_NAME} (Awaiting Response)")
    return doc.name


# ─────────────────────────────────────────────────────────────────────────────
# Main Orchestrator
# ─────────────────────────────────────────────────────────────────────────────

def setup_all():
    frappe.set_user("Administrator")

    print("\n══ Prerequisites: Skills ══")
    setup_skills()
    frappe.db.commit()

    print("\n══ Section 1: Job Requisition & Opening ══")
    requisition_name = setup_job_requisition()
    frappe.db.commit()
    job_opening_name = setup_job_opening(requisition_name)
    frappe.db.commit()

    print("\n══ Section 2: Interview Types (Round Masters) ══")
    interview_type_names = setup_interview_types()
    frappe.db.commit()

    print("\n══ Section 3: Offer Terms & Template ══")
    setup_offer_terms()
    frappe.db.commit()
    setup_offer_term_template()
    frappe.db.commit()

    print("\n══ Section 4: Candidate Flow – Manjit Singh ══")
    applicant_name = create_job_applicant(job_opening_name)
    frappe.db.commit()
    create_interviews(applicant_name, job_opening_name, interview_type_names)
    frappe.db.commit()
    create_job_offer(applicant_name)
    frappe.db.commit()

    print("\n✓ Grace Group ATS setup complete!")
    print(f"  Job Opening  : {job_opening_name}")
    print(f"  Candidate    : {CANDIDATE_NAME} ({CANDIDATE_EMAIL})")
    print(f"  Offer Status : Awaiting Response")
