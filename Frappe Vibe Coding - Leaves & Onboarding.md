# **SYSTEM CONTEXT**

You are extending the Frappe HR implementation for "Demo Group" (FMCG distribution).

Build upon the existing organizational structure, fleet operations, and performance management scenario by implementing two new modules: **Employee Onboarding** and **Leave Management**.

Your instructions must generate the necessary Python hooks, JSON fixtures, and setup scripts to automate these processes, specifically linking HR processes to operational continuity (e.g., reassigning delivery vehicles when a driver goes on leave).

# **PHASE 8: Employee Onboarding Setupa**

Utilize Frappe HR's standard Employee Onboarding and Project/Task modules to create structured onboarding pipelines for different roles within Demo Group.

**1\. Create Standard Onboarding Tasks**

Write a setup script to create the following standard Task documents:

* Task 1: "Verify Commercial Driving License & Background Check" (Department: HR)  
* Task 2: "Allocate Vehicle in Fleet Management" (Department: Logistics)  
* Task 3: "Q-Comm SLA & Cold Storage Safety Briefing" (Department: Supply Chain)  
* Task 4: "Create Corporate Email & Frappe ERP Access" (Department: IT)  
* Task 5: "FMCG Brand Training (Amul/Lays/McCain)" (Department: Sales)

**2\. Create Employee Onboarding Templates**

Write a script to generate two Employee Onboarding Template records:

* **Template A: "Delivery Executive Onboarding"**  
  * Include Tasks: 1, 2, and 3\.  
  * Designation: Delivery Executive.  
* **Template B: "Key Account Manager (KAM) Onboarding"**  
  * Include Tasks: 4 and 5\.  
  * Designation: KAM.

**3\. Integration Logic**

Ensure that when an Employee Onboarding document is submitted, Frappe automatically spins up the associated Tasks and assigns them to the respective Department Heads (e.g., Task 2 automatically assigns to Gurpreet Singh, Logistics Manager).

# **PHASE 9: Leave Management & Fleet Operations Integration**

Configure standard Leave mechanisms and build a custom hook to ensure operational continuity for fleet management when field workers take leave. For Demo Group, leave structures are heavily dependent on industry standards for FMCG and Q-Comm logistics.

**1\. Base Leave Configuration & Types**

Write a setup script to create the following standard records:

* **Leave Period**: "2026 Operations Year" (Jan 1, 2026 \- Dec 31, 2026).  
* **Leave Types**:  
  * Casual Leave (Is Carry Forward: No)  
  * Sick Leave (Is Carry Forward: No)  
  * Privilege Leave (Is Carry Forward: Yes, Earned leave based on days worked)  
  * Compensatory Off (Is Carry Forward: No. Highly critical for FMCG drivers/warehouse staff working during peak festival weekends to meet Q-Comm SLAs).

**2\. Leave Policies (Templates based on Industry Standards)**

Create the following distinct Leave Policy templates to reflect the operational realities of the different divisions:

* **Template A: "Field & Logistics Leave Policy"** (Targeted at Delivery Drivers & Warehouse Staff)  
  * Casual Leave: 10 Days  
  * Sick Leave: 10 Days  
  * Privilege Leave: 12 Days  
  * Compensatory Off: Enabled. (Allows these workers to claim leaves if they work on scheduled week-offs/holidays during peak demand spikes like Diwali/New Year).  
* **Template B: "Corporate & KAM Leave Policy"** (Targeted at Directors & Key Account Managers)  
  * Casual Leave: 12 Days  
  * Sick Leave: 12 Days  
  * Privilege Leave: 15 Days  
  * Compensatory Off: Disabled/Not Allocated.

**3\. Leave Policy Assignment**

Assign these templates programmatically via Leave Policy Assignment:

* **Field Policy**: Assign to Harpreet Babbar, Rajinder Kumar (Drivers), Vikramjeet Singh, Amit Patel (Warehouse).  
* **Corporate Policy**: Assign to Arjun Sandhu, Neha Sharma (KAMs) and the C-Suite.

**4\. Leave Approver Hierarchy**

Update the Employee records to ensure the Leave Approver field is correctly populated:

* Drivers (Harpreet, Rajinder) \-\> Leave Approver: Gurpreet Singh (Logistics Manager).  
* KAMs \-\> Leave Approver: Respective Director (Mukesh Mittal / Chaitanya Malhotra).

**5\. Custom Python Server Script: The "Fleet Reallocation Warning"**

This is the critical operational link. Create a Server Script (Hook on Leave Application, Event: on\_submit).

* **Logic:**  
  1. Check if the Employee taking leave belongs to the Logistics department (i.e., they are a driver).  
  2. If Yes, check the Vehicle Log to see if they have an active vehicle assignment for the leave dates.  
  3. **Action:** If they have a vehicle, use frappe.publish\_realtime and standard Notification doctype to send an urgent alert to the Logistics Manager (Gurpreet Singh).  
  4. **Notification Text:** "URGENT: \[Employee Name\] is on approved leave from \[Start Date\] to \[End Date\]. Please reallocate Vehicle \[Vehicle No\] immediately to prevent Q-Comm SLA breaches."

# **OUTPUT REQUIREMENTS**

1. Generate the Python setup script (setup\_onboarding\_leaves.py) containing the frappe.get\_doc().insert() calls for Tasks, Templates, Leave Types, Leave Policies (Templates A & B), and Policy Assignments.  
2. Provide the Python server script code for the Leave Application submit hook to trigger the Fleet Reallocation Warning.  
3. Provide instructions on how to wire the doc\_events in hooks.py for this custom logic.