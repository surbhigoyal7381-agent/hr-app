# **SYSTEM CONTEXT**

You are an expert Frappe Framework and ERPNext/Frappe HR Technofunctional Developer. Your task is to build and configure a complete end-to-end HR and Fleet Operations scenario for an FMCG distribution business called "Demo Group".

You will use standard Frappe HR Doctypes, standard ERPNext Fleet Management Doctypes, Frappe Customization tools (Custom Doctypes), and Frappe Workspaces to build this out. Generate the necessary Python server-side scripts, JavaScript client scripts, and JSON fixtures/Doctype schemas to fulfill the following requirements.

# **PHASE 1: Core Organizational & Master Data Setup**

Write the setup scripts or data import configurations to populate the following base data structure using the standard Employee, Designation, and Department Doctypes. Ensure the Reports To field is accurately set to establish the hierarchy.

**1\. C-Suite (Department: Management, No Reports To)**

* Mr. D. K. Malhotra (Designation: Promoter & Director \- Strategy)  
* Mr. Mukesh Mittal (Designation: Promoter & Director \- Finance)  
* Mr. Chaitanya Malhotra (Designation: Promoter & Director \- Digital)

**2\. Key Account Managers (Department: Sales, Reports to: Respective Directors)**

* Arjun Sandhu (Designation: KAM \- Dairy. Handles: Amul, Verka)  
* Neha Sharma (Designation: KAM \- Snacks. Handles: Lay's, Kurkure)  
* Rohit Verma (Designation: KAM \- Processed Foods)  
* Priya Singh (Designation: KAM \- Hardware)

**3\. Warehouse Supervisors (Department: Supply Chain, Reports to: Mukesh Mittal)**

* Vikramjeet Singh (Designation: Cold Storage Supervisor, Location: Chandigarh)  
* Amit Patel (Designation: Warehouse Supervisor, Location: Panchkula)  
* Sandeep Kaur (Designation: Cold Storage Supervisor)

**4\. Fleet Operators (Department: Logistics, Reports to: Logistics Manager)**

* Gurpreet Singh (Designation: Logistics Manager)  
* Harpreet Babbar (Designation: Delivery Executive)  
* Rajinder Kumar (Designation: Delivery Executive)

# **PHASE 2: Fleet Management Setup**

Utilize the standard Vehicle and Vehicle Log Doctypes.

1. Create a setup script to generate dummy fleet assets (e.g., License Plates: PB-65-XXXX).  
2. Assign these vehicles to the Delivery Executives (Harpreet and Rajinder) via Vehicle Log or asset assignment to link the Employee to their tool of trade.

# **PHASE 3: Geo-Fenced Mobile Attendance**

Configure the Frappe HR Attendance engine for mobile-first, geo-fenced check-ins.

1. **Workspaces (Locations)**: Create two physical locations in the Workspace Doctype (or customize Location):  
   * Chandigarh Warehouse: Radius 100m.  
   * Panchkula Warehouse: Radius 100m.  
2. **Shift Types**: Create the following in Shift Type:  
   * "Q-Comm Morning Shift" (Start: 05:30 AM). Enable Auto Attendance. Link to Chandigarh/Panchkula locations.  
   * "GT Day Shift" (Start: 08:00 AM). Enable Auto Attendance. Link to Chandigarh/Panchkula locations.  
3. **Settings**: Ensure HR Settings have "Allow Geolocation Tracking" enabled.

# **PHASE 4: Custom Doctype Development**

Create a Custom Doctype named Daily Route Log. This will be used by drivers on the Frappe Mobile App.

**Doctype Name:** Daily Route Log

**Module:** Logistics / HR (Custom)

**Naming Series:** RTL-.YYYY.-.\#\#\#\#

**Is Submittable:** Yes

**Fields:**

1. employee (Type: Link, Options: Employee, Default: User's linked employee)  
2. date (Type: Date, Default: Today)  
3. vehicle (Type: Link, Options: Vehicle)  
4. route\_category (Type: Select, Options: "Q-Comm\\nGT\\nHORECA\\nInstitution")  
5. completed\_drops (Type: Int)  
6. rto\_count (Type: Int, Label: "Return to Origin Count")  
7. penalty\_logged (Type: Check, Label: "SLA Delay / Penalty Logged")  
8. remarks (Type: Small Text)

**Permissions:**

* Role Employee: Create, Read, Write (Only their own docs).  
* Role Logistics Manager: Read, Write, Submit.

# **PHASE 5: Performance Management & Appraisals**

Automate the Goal and Appraisal configurations via scripting or fixture generation.

**1\. Goals (Set Period: Jan 2026\)**

Write a script to insert Goal documents matching this matrix:

* D.K. Malhotra \-\> Goal: "Accelerate Group Growth" (Turnover \> 180cr).  
* Neha Sharma \-\> Goal: "Q-Comm Snack Dominance" (\< 2% penalty rate).  
* Vikramjeet \-\> Goal: "Zero Perishable Spoilage" (Reduce wastage by 20%).  
* Harpreet Babbar \-\> Goal: "Q-Comm SLA Protection" (Zero delivery penalties).  
* Rajinder Kumar \-\> Goal: "Route Efficiency" (\< 5% RTO rate).

**2\. Appraisal Template & Cycle**

* Create an Appraisal Template named "Delivery Executive Review".  
* Add KRAs: "Attendance Reliability" (Weight: 40%), "Route Efficiency" (Weight: 60%).

**3\. Integration Script (Python/Server-Side)**

Write a Python Server Script hooked to the Appraisal Doctype (before\_save or a custom button "Fetch Metrics").

* Logic: When an Appraisal is opened for a Delivery Executive, automatically query their Attendance records for the cycle to calculate the "Attendance Reliability" score.  
* Logic: Query the custom Daily Route Log for the employee to sum completed\_drops, rto\_count, and check for penalty\_logged flags, injecting this data into the Appraisal remarks/metrics.

# **PHASE 6: Executive Dashboard (Promoter Command Center)**

Create a Workspace named Promoter Command Center. Restrict access to a new role Promoter.

**1\. Number Cards**

* Fleet Readiness: Count of Attendance today where Shift is Q-Comm Morning or GT Day Shift.  
* Q-Comm SLA Breaches: Count of Daily Route Log this month where penalty\_logged is 1 and route\_category is "Q-Comm".  
* Open Appraisals: Count of Appraisal where status is Draft or Pending.

**2\. Dashboard Charts**

* Efficiency vs RTO: Line chart using Daily Route Log, X-Axis: Date (Weekly), Y-Axis: Sum of completed\_drops vs Sum of rto\_count.  
* Performance Distribution: Bar chart using Appraisal, X-Axis: Final Score.

# **PHASE 7: Agentic Automation**

Write a setup script to create an Auto Email Report.

* **Based On:** Daily Route Log  
* **Filters:** penalty\_logged \= 1 OR rto\_count \> 5\.  
* **Schedule:** Daily at 09:00 AM.  
* **Recipients:** Chaitanya Malhotra and Mukesh Mittal's emails.

Please provide the necessary JSON files for Custom Doctypes, Workspaces, and the Python .py hooks and setup scripts to build this application.