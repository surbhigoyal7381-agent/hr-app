# 06 — Recruitment, end to end: Senior Sales Executive, Noida

One complete hiring run, from the Store In-charge asking for a person to the candidate accepting the offer. Everything is standard Frappe HR recruitment except the screening questions, which need one small build (custom fields on Job Applicant and a custom Web Form, build B3 in file 10).

No client material was supplied, so the JD, screening questions and selection parameters below are written for the demo in the client's context.

## 1. The process as PP Jewellers runs it

| Step | Who | Frappe HR object | Transparency it gives |
|---|---|---|---|
| 1. Ask for a hire | Store In-charge, Noida | **Job Requisition** | Owner sees every open ask with cost, status and time to fill |
| 2. Approve | Owner | Job Requisition status → Open & Approved | |
| 3. Publish | HR (Recruitment Executive) | **Job Opening** (published on the careers page) with the JD | Careers page at `/jobs` |
| 4. Apply | Candidate | **Job Applicant** via Web Form with screening questions | Answers are on the record; HR sees why someone is screened out |
| 5. Screen | HR | Job Applicant status Open → Shortlisted / Rejected, applicant rating | Recruitment Analytics |
| 6. Round 1: HR screening call | Recruitment Executive | **Interview** (type "R1 HR Screening") + **Interview Feedback** | Skill ratings per candidate |
| 7. Round 2: Store In-charge interview | Store In-charge, Noida | Interview "R2 Store In-charge" + Feedback | same |
| 8. Round 3: Owner round | Owner | Interview "R3 Owner Round" + Feedback | same |
| 9. Offer | HR | **Job Offer** with Job Offer Terms | Offer acceptance rate |
| 10. Appointment letter | HR | **Appointment Letter** | Print format |
| 11. Onboarding | HR | **Employee Onboarding** (file 07) | |

## 2. Job Requisition

| Field | Value |
|---|---|
| Designation | Senior Sales Executive |
| Department | Sales |
| Requested by | PPJ-0185 (Store In-charge, Noida) |
| Number of positions | 1 |
| Expected compensation | ₹40,000 per month |
| Posting date / Expected by | 2026-07-06 / 2026-08-15 |
| Reason | Replacement: resignation of a Senior Sales Executive on the Diamond floor |
| Status flow for the demo | Pending (6 Jul) → Open & Approved (7 Jul, Owner) → Filled (24 Aug) |

Also create a **Staffing Plan** "FY27 Store Staffing" for the company with one row per store designation (vacancies = current count), so the "Check Vacancies" setting in HR Settings has something to check.

## 3. Job Opening and JD

| Field | Value |
|---|---|
| Job Title | Senior Sales Executive – Diamond Floor (Noida) |
| Designation / Department | Senior Sales Executive / Sales |
| Location (Branch) | PPJ Noida Sector 18 |
| Employment Type | Full-time |
| Status / Publish | Open / 1 |
| Vacancies | 1 |
| Salary range | ₹32,000 to ₹45,000 per month, published |
| Job Requisition | the one above |
| Job Application Route | `ppj-senior-sales-application` (the custom web form, section 5) |
| Posted on / Closes on | 2026-07-08 / 2026-08-08 |

**Job description (goes in the Description field):**

> **Senior Sales Executive – Diamond Floor**
>
> PP Jewellers is a 40-year-old family jewellery house with five stores across Chandigarh, Ambala, Noida and Delhi. We are looking for a Senior Sales Executive for the Diamond floor at our Noida Sector 18 store.
>
> **What you will do**
> - Sell diamond, platinum and gemstone jewellery to walk-in and appointment customers; own a monthly sales target.
> - Explain certification (IGI, GIA), the 4Cs, hallmarking and our exchange and buy-back policies clearly and honestly.
> - Build repeat relationships: follow up with customers before festivals, weddings and anniversaries with the Customer Relationship team.
> - Coach two to three junior Sales Executives on the floor.
> - Follow vault, display and billing procedures without exception.
>
> **What we need**
> - 3 or more years selling jewellery in an organised retail store, at least 1 year on diamonds.
> - Comfortable with a 7-day store roster with one fixed weekly off, and with working on festival days.
> - Fluent Hindi and working English. Punjabi is a plus.
> - Clean background; police verification is part of joining.
>
> **What you get**
> - ₹32,000 to ₹45,000 per month fixed, plus category incentives paid monthly, PF and ESI as applicable, festival working allowance, and a clear appraisal every quarter.

## 4. Screening questions (on the application form)

**Status: built and tested 2026-09-07 (file 10, B3).** Module **Alvoraa Screening** (`hrms/hrms/alvoraa_screening`), opt-in feature key `screening_forms`. The fields are generic product fields, not `ppj_*`: the client's wording lives on the Web Form as field labels, and the screen-out rules live on the Job Opening. Mapping: Q1 `screening_retail_experience`, Q2 `screening_years_in_category`, Q3 `screening_product_knowledge`, Q4 `screening_roster_ok`, Q5 `screening_festival_ok`, Q6 `screening_availability`; the three extras are `screening_current_employer`, `screening_category_experience`, `screening_expected_monthly_ctc`. The rules on the PPJ opening: retail experience required, minimum 3 years, product knowledge required, roster and festival availability required, expected monthly CTC at most 50,000. An applicant who fails a rule is saved with `screening_result` = Screened Out, the reasons in `screening_notes`, and status Rejected; the rest are Passed. HR filters the applicant list on Screening Result.

These are the questions the client says they ask before anyone is called. They become custom fields on Job Applicant (build B3) and appear on the web form. HR sees the answers on the applicant record and filters the list on them.

| # | Field on Job Applicant | Question on the form | Type | Screen-out rule |
|---|---|---|---|---|
| Q1 | `ppj_jewellery_retail_experience` | Have you worked in an organised jewellery retail store? | Select Yes / No | No → reject |
| Q2 | `ppj_years_in_jewellery` | How many years have you sold jewellery? | Int | below 3 → reject |
| Q3 | `ppj_gold_diamond_knowledge` | Can you explain hallmarking and diamond certification to a customer? | Select Yes / No | No → reject for Diamond floor |
| Q4 | `ppj_ok_with_7day_roster` | Are you comfortable with a 7-day store roster with one fixed weekly off (not Sunday)? | Select Yes / No | No → reject |
| Q5 | `ppj_ok_with_festival_work` | Are you available to work on festival days (Dhanteras, Diwali, Akshaya Tritiya)? | Select Yes / No | No → reject |
| Q6 | `ppj_availability` | When can you join? Any constraints? | Small Text | information |
| — | `ppj_current_employer`, `ppj_category_experience`, `ppj_expected_monthly_ctc` | Current employer; categories sold (Gold / Diamond / Silver / Platinum, multi-select); expected monthly CTC | Data / Small Text / Currency | CTC above 50,000 → reject (band is 32 to 45) |

## 5. The application web form

The product ships Web Form `screening-application` (route `/screening-application`, doctype Job Applicant, login not required, success URL `/jobs`) with neutral wording. The seed copies it to `ppj-senior-sales-application` with the client's questions as labels (hallmarking and diamond certification, Dhanteras, Diwali, Akshaya Tritiya) and sets that route on the Job Opening's `job_application_route`. Fields: job_title (filled from the careers page link), applicant_name, email_id, phone_number, country, the nine screening fields above, resume_attachment, cover_letter. The standard `job-application` form stays for other openings.

## 6. Applicants

`data/applicants.csv` has 8 applicants with their answers and outcomes. Summary:

| Applicant | Source | Answers | Outcome |
|---|---|---|---|
| Ritika Malhotra | Naukri | 6 yrs, Gold + Diamond, all Yes | **Selected. Offer accepted.** |
| Vikas Tomar | Naukri | 5 yrs, Gold, all Yes | Round 3 runner-up, status Hold |
| Shalini Rawat | Employee referral | 4 yrs, Diamond, festival = No | Round 2 not cleared |
| Amit Chaudhary | LinkedIn | 7 yrs, roster = No | Round 2 not cleared |
| Neha Bisht | Naukri | 3 yrs | Round 1 cleared, withdrew |
| Rohit Sengar | Walk-in | 2 yrs | Screened out (Q2) |
| Preeti Nagar | Indeed | apparel retail, no jewellery | Screened out (Q1) |
| Sunil Dhaka | Naukri | 8 yrs, expects 60,000 | Screened out (CTC) |

Create **Job Applicant Source** records: Naukri, LinkedIn, Indeed, Walk-in, Employee Referral. For Shalini, also create an **Employee Referral** from PPJ-0195 (a Noida Senior Sales Executive) so the referral bonus flow is visible.

## 7. Selection parameters and interview rounds

Selection parameters are **Skills**, grouped per round on an **Interview Type**, each rated 1 to 5 in **Interview Feedback**. The round's pass mark is the Interview Type's `expected_average_rating`. This is what Frappe HR supports; there is no weighting per skill.

Create these **Skill** records: Communication & Grooming, Jewellery Product Knowledge, Diamond & Certification Knowledge, Selling & Closing, Customer Handling, Integrity & Process Discipline, Team Coaching, Cultural Fit with PP Jewellers, Target Orientation.

| Interview Type | Designation | Expected skills | Pass mark (expected average) | Interviewers |
|---|---|---|---|---|
| R1 HR Screening | Senior Sales Executive | Communication & Grooming; Jewellery Product Knowledge; Target Orientation | 3.0 | Recruitment Executive (PPJ-0013), HR Executive |
| R2 Store In-charge | Senior Sales Executive | Diamond & Certification Knowledge; Selling & Closing; Customer Handling; Integrity & Process Discipline; Team Coaching | 3.5 | Store In-charge Noida (PPJ-0185), Floor Manager - Diamond Noida |
| R3 Owner Round | Senior Sales Executive | Cultural Fit with PP Jewellers; Integrity & Process Discipline; Target Orientation | 4.0 | Owner (PPJ-0001), Head - HR (PPJ-0010) |

Frappe HR blocks two interviews of the same type for one applicant, so each round is its own type. `Interview Type.designation` must equal the applicant's designation.

**Interview and feedback records to create** (dates in July and August 2026):

| Applicant | R1 (avg) | R2 (avg) | R3 (avg) | Applicant status |
|---|---|---|---|---|
| Ritika Malhotra | Cleared 4.3 | Cleared 4.4 | Cleared 4.7 | Accepted |
| Vikas Tomar | Cleared 3.7 | Cleared 3.8 | Under Review 3.7 (below 4.0) | Hold |
| Shalini Rawat | Cleared 3.3 | Rejected 2.6 | — | Rejected |
| Amit Chaudhary | Cleared 3.7 | Rejected 3.0 (Integrity 4, but roster refusal noted) | — | Rejected |
| Neha Bisht | Cleared 3.0 | — (withdrew) | — | Rejected, note "withdrew" |

Each Interview Feedback has one **Skill Assessment** row per expected skill with the rating, a short feedback text, and `result`. Write the feedback in the interviewer's voice, e.g. R2 for Ritika: "Explained 4Cs and IGI vs GIA clearly. Handled the 'why is your making charge higher' objection well. Ran a Diamond counter at Tanishq. Ready for the floor."

HR Settings: turn on interview reminders and feedback reminders so the notifications show.

## 8. Offer and appointment letter

**Offer Terms**: Monthly CTC, Probation Period, Notice Period, Incentive Scheme, Weekly Off, Joining Date. **Job Offer Term Template** "PPJ Store Staff Offer".

**Job Offer** for Ritika Malhotra: offer date 2026-08-18, designation Senior Sales Executive, terms: CTC ₹42,000 per month; Probation 6 months; Notice 30 days; Incentive "Category incentive scheme as per policy"; Weekly Off "Fixed, Monday to Friday, assigned by store"; Joining 2026-09-01. Status Accepted on 2026-08-20.

**Appointment Letter** with template "PPJ Standard Appointment Letter" (introduction, 6 terms, closing note). Print it in the demo.

## 9. What each persona sees

| Persona | Screen |
|---|---|
| Owner | Recruitment dashboard: openings by store, pipeline funnel (8 → 5 → 4 → 2 → 1), offer acceptance rate, time to fill = 49 days. Owner also rates R3. |
| HR | Job Requisition list, Job Opening, applicants with screening answers, interviews calendar, Recruitment Analytics report |
| Store In-charge (Noida) | Their requisition status, R2 interviews assigned to them, feedback form, the offer status |
| Candidate | Careers page, the application form, interview reminder emails |

## 10. Verification

- Recruitment Analytics report: 1 requisition, 1 opening, 8 applicants, 1 offer, 1 accepted.
- Applicant-to-hire percentage number card = 12.5%.
- Ritika's Job Applicant record shows the six screening answers and three interviews with average ratings.
