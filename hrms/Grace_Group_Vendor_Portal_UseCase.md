# GRACE GROUP VENDOR DELIVERY PORTAL

## Comprehensive Use Case & Implementation Strategy

**An Increment to the Frappe HR System**

---

## EXECUTIVE SUMMARY

Grace Group manages 40 delivery vehicles across three locations (Chandigarh, Panchkula, Mohali) distributing FMCG products to Modern Trade, General Trade, and HORECA customers within 250km radius. The company currently lacks visibility into delivery execution, customer satisfaction feedback, and vehicle performance metrics.

**Objective:** Create a Vendor/Partner Portal that enables:

- ✅ Delivery partners (vendors/contractors) to manage assigned orders  
- ✅ Real-time GPS tracking of 40 delivery vehicles  
- ✅ Customer delivery rating system (5+ factors)  
- ✅ Automated performance assessments of delivery team  
- ✅ Vendor accountability and compliance tracking  
- ✅ Integration with existing Grace Group HR system

**Scope:**

- Phase 6 of existing Frappe implementation (Post go-live)  
- Builds on logistics infrastructure already in place  
- Integrates delivery metrics into driver/logistics staff performance appraisals  
- Separate portal for vendors (guest access) vs internal users (full access)

**Timeline:** 3-4 months (after core HR system stabilized)  
**Investment:** Incremental (builds on existing infrastructure)

---

## PART 1: CURRENT STATE & OPPORTUNITY

### 1.1 Current Delivery Operations

Grace Group Fleet: 40 Delivery Vehicles

├── Chandigarh Hub (22 vehicles)

│   └── Service Area: Chandigarh, Mohali, Zirakpur

├── Panchkula Hub (12 vehicles)

│   └── Service Area: Panchkula, Yamunanagar, Ambala

└── Himachal Hub (6 vehicles)

    └── Service Area: Shimla, Solan, Parwanoo

Delivery Partners: Mix of

├── Company Employees (50% \- Directly managed)

│   └── Drivers, Helpers, Logistics Coordinators

├── Contractual Partners (30% \- Third-party logistics)

│   └── Hired for seasonal peaks

└── Franchisee Partners (20% \- Independent vendors)

    └── Own vehicles, use Grace branding

Current Challenges:

1\. ❌ NO visibility into delivery status (customer/order level)

2\. ❌ NO customer feedback on delivery quality

3\. ❌ NO GPS tracking (vehicles operating blind)

4\. ❌ NO objective basis for delivery team performance assessment

5\. ❌ NO mechanism to identify underperforming partners

6\. ❌ NO digital handshake or proof-of-delivery

7\. ❌ Manual order assignment and tracking

8\. ❌ Customer complaints not systematically collected

### 1.2 The Opportunity

BEFORE:

Customer calls to complain → Escalates to Logistics Manager

                          → Manual investigation

                          → Difficult to assign accountability

                          → No data on driver performance

AFTER (WITH VENDOR PORTAL):

Delivery Assigned → Driver Gets Notification → Accepts/Starts Journey

                          ↓

                   Real-time GPS Tracking (Map view)

                          ↓

                   Delivery Completed (Photo \+ signature)

                          ↓

                   Customer Rates Delivery (5-star \+ factors)

                          ↓

                   Data Auto-syncs to HR System

                          ↓

                   Driver's Monthly Appraisal Includes:

                   \- On-time delivery %

                   \- Customer rating (avg 4.5/5)

                   \- Vehicle compliance %

                   \- Safety incidents

                          ↓

                   Impact: Salary, Bonus, Promotion decisions

---

## PART 2: VENDOR PORTAL ARCHITECTURE

### 2.1 System Components

┌─────────────────────────────────────────────────────────────┐

│          GRACE GROUP LOGISTICS ECOSYSTEM                     │

└─────────────────────────────────────────────────────────────┘

1\. VENDOR PORTAL (Web & Mobile)

   ├─ Delivery Partner Login

   ├─ Order Dashboard

   ├─ Real-time GPS Map

   ├─ Delivery Instructions

   ├─ Customer Feedback

   └─ Performance Dashboard (Own metrics)

2\. CUSTOMER FEEDBACK MODULE

   ├─ QR Code at delivery (optional)

   ├─ SMS link for feedback

   ├─ Rating form (5+ factors)

   └─ Complaint registration

3\. GPS & VEHICLE TRACKING

   ├─ Real-time location (every 30 sec)

   ├─ Route optimization

   ├─ Geofencing alerts

   ├─ Vehicle health monitoring

   └─ Driver behavior (harsh braking, speeding)

4\. DELIVERY MANAGEMENT

   ├─ Order assignment

   ├─ Route planning

   ├─ Proof of delivery (POD)

   ├─ Exception handling

   └─ Audit trail

5\. HR INTEGRATION

   ├─ Delivery metrics → Driver appraisal

   ├─ Customer ratings → Performance score

   ├─ Safety incidents → Conduct assessment

   └─ Bonus calculation (delivery performance)

6\. ANALYTICS & REPORTING

   ├─ Vendor dashboard

   ├─ Customer satisfaction metrics

   ├─ Fleet efficiency reports

   └─ Driver performance scorecards

---

## PART 3: NEW DOCTYPES FOR VENDOR PORTAL

### 3.1 Vendor/Partner Master

DocType: Delivery Partner \[NEW\]

Name: DP-\[CODE\]

Example: DP-CHANDIGARH-001

IDENTIFICATION:

\- partner\_id: Unique ID (auto-generated)

\- partner\_type: Select (Employee/Contractual/Franchisee)

\- partner\_name: Text (Company or individual name)

\- partner\_code: Text (e.g., DP-CDG-001)

\- primary\_contact: Link \[Contact\]

\- primary\_phone: Phone

\- primary\_email: Email

EMPLOYMENT DETAILS:

\- company: Link \[Company\] (Grace Drinks / Grace Sales / Grace Enterprises)

\- department: Link \[Department\] (Logistics / Delivery)

\- linked\_employee: Link \[Employee\] (If partner is employee)

  └─ Auto-links driver's appraisal data

\- reporting\_manager: Link \[Employee\] (Logistics Manager)

VEHICLE DETAILS:

\- vehicle\_id: Text (Unique identifier)

\- vehicle\_registration: Text (Number plate)

\- vehicle\_type: Select (Truck/Van/3-Wheeler/2-Wheeler)

\- vehicle\_capacity: Float (Weight in kg)

\- vehicle\_age: Integer (years)

\- vehicle\_brand: Text

\- vehicle\_model: Text

\- last\_maintenance\_date: Date

\- next\_maintenance\_due: Date

\- insurance\_expiry: Date

OPERATIONAL DETAILS:

\- hub\_assigned: Link \[Delivery Hub\] (Chandigarh/Panchkula/Himachal)

\- service\_area: Text (Area of operation)

\- operational\_status: Select (Active/Inactive/Suspended)

\- daily\_delivery\_capacity: Integer (Orders per day)

\- average\_orders\_per\_day: Integer (Performance)

PERFORMANCE METRICS:

\- total\_deliveries: Integer (Lifetime)

\- on\_time\_delivery\_percentage: Percent (This month)

\- customer\_satisfaction\_rating: Decimal (1-5, auto-calculated)

\- safety\_incidents: Integer (Lifetime)

\- cancellations: Integer (This month)

\- returns\_initiated: Integer (This month)

FINANCIAL:

\- partner\_contract\_type: Select (Fixed/Per-Order/Hourly)

\- daily\_rate: Currency (If fixed)

\- per\_order\_rate: Currency (If per-order)

\- outstanding\_payments: Currency

\- payment\_status: Select (Current/Overdue/Suspended)

\- upi\_id: Text (For payments)

COMPLIANCE:

\- license\_number: Text (DL number for drivers)

\- license\_expiry: Date

\- vehicle\_fitness\_cert\_expiry: Date

\- pan: Text

\- aadhaar: Text (Encrypted)

\- background\_check\_done: Yes/No

\- background\_check\_date: Date

\- certifications: Text Area (Defensive driving, etc.)

ENGAGEMENT:

\- date\_started: Date

\- date\_contract\_expiry: Date (Optional)

\- is\_active: Yes/No

\- deactivation\_reason: Text (If inactive)

\- status: Select (Active/On Leave/Suspended/Terminated)

PORTAL ACCESS:

\- can\_access\_portal: Yes/No

\- portal\_username: Text

\- last\_portal\_login: DateTime

\- portal\_access\_level: Select (View-Only/Full-Access)

CHILD TABLE: vehicle\_history

\- change\_date: Date

\- old\_vehicle\_id: Text

\- new\_vehicle\_id: Text

\- reason: Text

CHILD TABLE: performance\_ratings

\- rating\_date: Date (Monthly snapshot)

\- month: Text

\- on\_time\_delivery: Percent

\- customer\_rating: Decimal

\- incidents: Integer

\- score: Decimal (Composite score)

### 3.2 Delivery Order

DocType: Delivery Order \[CUSTOM or extend Sales Order\]

Name: DO-\[DATE\]-\[SEQUENCE\]

Example: DO-20260630-0045

ORDER HEADER:

\- delivery\_order\_id: Text (auto-generated)

\- source\_order\_type: Select (Sales Order / Direct / Subscription)

\- source\_order\_link: Link \[Sales Order\] (From Logic ERP)

\- customer: Link \[Customer\] (From Logic ERP)

\- customer\_name: Text (Auto-populated)

\- customer\_phone: Phone

\- customer\_email: Email

\- delivery\_date: Date (Scheduled)

\- delivery\_time\_slot: Select (8-12/12-3/3-6/6-9)

DELIVERY DETAILS:

\- delivery\_address: Text Area

\- delivery\_city: Text

\- delivery\_state: Select

\- delivery\_pin: Text

\- delivery\_coordinates: Geolocation (Lat/Long for mapping)

\- special\_instructions: Text Area

\- is\_fragile: Yes/No (Special handling)

\- requires\_signature: Yes/No

\- requires\_photo: Yes/No

ORDER CONTENTS:

CHILD TABLE: order\_items

\- item\_code: Link \[Item\]

\- item\_name: Text

\- quantity: Float

\- uom: Text

\- unit\_price: Currency

\- total: Currency (qty \* price)

ORDER VALUES:

\- subtotal: Currency (Sum of items)

\- delivery\_charges: Currency

\- discount: Currency

\- tax: Currency

\- grand\_total: Currency (Sync to Logic ERP)

ASSIGNMENT:

\- assigned\_to\_partner: Link \[Delivery Partner\] (Who will deliver)

\- assigned\_date: DateTime

\- assignment\_status: Select (Not-Assigned/Assigned/In-Transit/Delivered/Failed)

TRACKING:

\- current\_status: Select

  ├─ Pending

  ├─ Assigned

  ├─ Picked Up

  ├─ In Transit

  ├─ Nearby (Within 1km)

  ├─ At Location

  ├─ Delivered

  ├─ Failed (Delivery attempt failed)

  ├─ Returned

  └─ Cancelled

\- status\_updated\_at: DateTime

\- status\_updated\_by: Link \[User\]

DELIVERY PROOF:

\- delivery\_photo: Attachment (Proof photo)

\- delivery\_signature: Image (Customer signature)

\- delivery\_timestamp: DateTime

\- delivery\_actual\_time: DateTime (When actually delivered)

\- on\_time\_status: Select (On-Time/Late/Early)

  └─ Auto-calculated vs scheduled delivery\_time\_slot

CUSTOMER FEEDBACK:

\- customer\_available: Yes/No (At delivery)

\- feedback\_provided: Yes/No

\- feedback\_rating: Decimal (1-5)

\- feedback\_details\_link: Link \[Delivery Feedback\] (See next DocType)

EXCEPTIONS:

\- exception\_type: Select (None/Customer Not Home/Address Not Found/Item Damaged/Quantity Mismatch/etc.)

\- exception\_notes: Text Area

\- exception\_photo: Attachment

\- exception\_resolution: Text Area

FINANCIAL IMPACT:

\- partner\_commission: Currency (Based on delivery)

\- bonus\_earned: Currency (If on-time \+ good rating)

\- amount\_collected: Currency (If COD)

\- amount\_to\_be\_paid: Currency (To partner)

AUDIT:

\- created\_date: DateTime

\- created\_by: Link \[User\]

\- last\_updated: DateTime

\- document\_changes: (Auto-tracked)

CHILD TABLE: status\_history

\- status: Select (Current status)

\- timestamp: DateTime (When changed)

\- updated\_by: Link \[User\]

\- gps\_location: Geolocation (Location when status changed)

\- notes: Text

### 3.3 Delivery Feedback (Customer Rating)

DocType: Delivery Feedback \[NEW\]

Name: DF-\[DELIVERY\_ID\]-\[DATE\]

Example: DF-DO-20260630-0045-20260630

HEADER:

\- feedback\_id: Text (auto-generated)

\- delivery\_order: Link \[Delivery Order\] (Which delivery)

\- delivery\_partner: Link \[Delivery Partner\] (Who delivered)

\- customer: Link \[Customer\]

\- customer\_name: Text (Auto-populated)

\- feedback\_date: DateTime (When feedback given)

\- feedback\_method: Select (QR Code / SMS / Web Portal / In-Person)

RATING FACTORS (Each 1-5 scale):

1\. TIMELINESS:

   \- on\_time\_rating: Integer (1-5)

   \- was\_on\_time: Yes/No

   \- if\_late\_minutes: Integer

   \- time\_feedback: Text Area

2\. DELIVERY PERSON BEHAVIOR:

   \- behavior\_rating: Integer (1-5)

   \- behavior\_factors:

     ├─ Politeness

     ├─ Professionalism

     ├─ Patience

     └─ Cleanliness (Vehicle/Uniform)

3\. PRODUCT CONDITION:

   \- product\_condition\_rating: Integer (1-5)

   \- any\_damage: Yes/No

   \- damage\_description: Text Area

   \- damage\_photo: Attachment

   \- product\_temperature\_ok: Yes/No (For cold chain)

4\. QUANTITY & ACCURACY:

   \- quantity\_accuracy\_rating: Integer (1-5)

   \- quantity\_matched: Yes/No

   \- items\_missing: Integer

   \- extra\_items: Integer

   \- items\_wrong: Integer

5\. DELIVERY EXPERIENCE:

   \- overall\_experience\_rating: Integer (1-5)

   \- would\_recommend: Yes/No

   \- ease\_of\_contact: Integer (1-5) (Could you reach them?)

   \- problem\_resolution: Integer (1-5) (If issue, was it resolved?)

OVERALL:

\- average\_rating: Decimal (Auto-calc: Average of all 5 factors)

\- overall\_comment: Text Area (Free text feedback)

\- would\_use\_again: Yes/No

ISSUES REPORTED:

\- issue\_reported: Yes/No

\- issue\_type: Select

  ├─ Damaged Product

  ├─ Missing Items

  ├─ Wrong Item Delivered

  ├─ Late Delivery

  ├─ Driver Behavior

  ├─ Vehicle Condition

  └─ Other

\- issue\_severity: Select (Low / Medium / High / Critical)

\- issue\_description: Text Area

\- issue\_photo: Attachment

\- requested\_action: Select

  ├─ Refund

  ├─ Replacement

  ├─ Discount

  ├─ Complaint Only

  └─ No Action Required

RESOLUTION:

\- issue\_resolved: Yes/No

\- resolution\_date: Date

\- resolution\_type: Text

\- resolution\_satisfaction: Integer (1-5, post-resolution rating)

AUDIT:

\- auto\_calculated\_score: Decimal (Before customer modifies)

\- data\_quality\_check: Yes/No (Feedback seems genuine)

\- flagged\_for\_review: Yes/No (Anomalies detected)

\- reviewed\_by: Link \[User\] (QA person)

\- review\_comments: Text Area

USAGE IN APPRAISAL:

\- feedback\_weight\_in\_appraisal: Percent (30% of driver's performance)

\- linked\_appraisal: Link \[Appraisal\] (Driver's appraisal)

### 3.4 GPS Tracking Record

DocType: Vehicle Tracking \[NEW \- Transactional, High Volume\]

Name: VT-\[PARTNER\_ID\]-\[DATETIME\]

Example: VT-DP-CDG-001-20260630143050

PURPOSE: Record vehicle location every 30 seconds during delivery

TRACKING DATA:

\- tracking\_id: Text (auto-generated)

\- delivery\_partner: Link \[Delivery Partner\]

\- vehicle\_id: Text

\- delivery\_order: Link \[Delivery Order\] (Current delivery)

\- recorded\_timestamp: DateTime

\- latitude: Decimal (Precise to 5 decimals)

\- longitude: Decimal

\- accuracy: Integer (Meters \- GPS accuracy)

\- speed: Integer (km/h)

\- heading: Integer (Direction 0-360 degrees)

\- altitude: Integer (Meters, optional)

DEVICE INFO:

\- device\_type: Select (Mobile/GPS Device/Both)

\- device\_id: Text (IMEI)

\- app\_version: Text (If mobile)

\- battery\_level: Percent (If mobile)

\- network\_type: Select (WiFi/4G/3G/2G/Offline)

GEOFENCE DATA:

\- geofence\_name: Text (Which zone/hub)

\- is\_inside\_geofence: Yes/No

\- geofence\_entry\_time: DateTime (When entered hub zone)

\- geofence\_exit\_time: DateTime (When left hub zone)

BEHAVIOR DATA:

\- harsh\_acceleration: Yes/No (Detected)

\- harsh\_braking: Yes/No (Detected)

\- sharp\_turn: Yes/No (Detected)

\- speeding\_alert: Yes/No (Over speed limit)

\- speed\_limit\_for\_area: Integer (km/h)

\- idle\_status: Yes/No (Vehicle stationary)

\- idle\_duration: Integer (Minutes, if idle)

AUDIT:

\- data\_quality: Select (Good/Fair/Poor)

\- signal\_strength: Integer (% of GPS signal)

\- notes: Text (If anomaly detected)

NOTE: This table is TRANSACTIONAL with high volume

\- Not designed for manual querying

\- Data aggregated into summary reports

\- Retention: 90 days raw data, 1 year aggregated

\- Indexed by: delivery\_partner, delivery\_order, recorded\_timestamp

### 3.5 Vehicle Health/Compliance Monitoring

DocType: Vehicle Maintenance & Compliance \[NEW\]

Name: VMC-\[VEHICLE\_ID\]-\[DATE\]

Example: VMC-DL05AZ5500-20260630

VEHICLE REFERENCE:

\- vehicle\_id: Link \[Delivery Partner.vehicle\_id\]

\- vehicle\_registration: Text

\- partner: Link \[Delivery Partner\]

MAINTENANCE TRACKING:

\- maintenance\_type: Select

  ├─ Regular Service

  ├─ Oil Change

  ├─ Tire Rotation

  ├─ Brake Check

  ├─ Battery

  ├─ AC Service

  ├─ Repair

  └─ Other

\- maintenance\_date: Date

\- maintenance\_mileage: Integer (km on odometer)

\- maintenance\_details: Text Area

\- maintenance\_cost: Currency

\- maintenance\_vendor: Text

\- next\_service\_due\_date: Date

\- next\_service\_due\_mileage: Integer

COMPLIANCE TRACKING:

\- compliance\_type: Select

  ├─ Insurance

  ├─ Vehicle Fitness (Pollution \+ Mechanical)

  ├─ License Plate

  ├─ Safety Equipment (Fire extinguisher, first aid)

  ├─ Permits

  └─ Other

\- compliance\_issue: Text

\- compliance\_expiry\_date: Date

\- days\_until\_expiry: Integer (Auto-calculated)

\- is\_expired: Yes/No (Auto-calc: expiry \< today)

\- renewal\_required: Yes/No

\- renewal\_date: Date (When renewed)

\- renewal\_document: Attachment

\- renewal\_cost: Currency

ALERTS:

\- alert\_status: Select

  ├─ Clear (All compliant)

  ├─ Warning (Due within 30 days)

  ├─ Critical (Due within 7 days)

  └─ Overdue (Expired)

\- alert\_notification\_sent: Yes/No

\- alert\_notification\_date: DateTime

\- notification\_recipient: Email/Phone

CHILD TABLE: compliance\_history

\- check\_date: Date

\- status: Pass/Fail

\- details: Text

\- corrective\_action: Text

\- action\_completed: Yes/No

### 3.6 Delivery Hub Master

DocType: Delivery Hub \[NEW\]

Name: DH-\[CITY\]

Example: DH-CHANDIGARH

HUB DETAILS:

\- hub\_name: Text (Chandigarh Hub)

\- hub\_code: Text (CDG)

\- hub\_city: Text

\- hub\_state: Text

\- hub\_location: Geolocation (Central warehouse)

\- hub\_area\_coverage: Integer (Radius in km)

\- operating\_hours: Text (9 AM \- 6 PM)

CAPACITY:

\- max\_deliveries\_per\_day: Integer (100)

\- average\_deliveries\_per\_day: Integer (85)

\- utilization\_percentage: Percent (Auto-calc: avg/max)

\- vehicles\_assigned: Integer (Linked to Delivery Partners)

\- staff\_count: Integer

PERFORMANCE (Aggregated):

\- avg\_on\_time\_delivery: Percent

\- avg\_customer\_rating: Decimal (1-5)

\- total\_complaints\_this\_month: Integer

\- repeat\_customers\_satisfied: Percent

CHILD TABLE: service\_areas

\- area\_name: Text (Chandigarh City)

\- pin\_codes: Text (comma-separated)

\- delivery\_time: Integer (estimated minutes)

\- special\_notes: Text

### 3.7 Driver Performance Scorecard (for HR Integration)

DocType: Delivery Performance Scorecard \[NEW/CUSTOM\]

Name: DPS-\[PARTNER\_ID\]-\[MONTH\]-\[YEAR\]

Example: DPS-DP-CDG-001-06-2026

PURPOSE: Monthly summary for HR appraisal integration

PERIOD:

\- delivery\_partner: Link \[Delivery Partner\]

\- scoring\_period: Select (Month/Quarter/Year)

\- month: Integer (06)

\- year: Integer (2026)

\- reporting\_manager: Link \[Employee\] (Logistics Manager)

VOLUME METRICS:

\- total\_deliveries: Integer (How many orders delivered)

\- on\_time\_deliveries: Integer (Delivered on schedule)

\- on\_time\_percentage: Percent (Auto-calc: on-time / total)

\- late\_deliveries: Integer

\- failed\_deliveries: Integer (Attempt failed, will retry)

\- cancelled\_deliveries: Integer

QUALITY METRICS:

\- avg\_customer\_rating: Decimal (1-5, from Delivery Feedback)

\- total\_customer\_feedbacks: Integer (How many rated)

\- rating\_breakdown:

  ├─ 5-star: Integer

  ├─ 4-star: Integer

  ├─ 3-star: Integer

  ├─ 2-star: Integer

  └─ 1-star: Integer

ISSUES:

\- complaints\_received: Integer

\- complaint\_details: Text Area (Summary)

\- damage\_claims: Integer

\- missing\_item\_claims: Integer

\- customer\_not\_home\_incidents: Integer

\- wrong\_address\_incidents: Integer

SAFETY & COMPLIANCE:

\- safety\_incidents: Integer (Accidents, harsh driving)

\- harsh\_driving\_detected: Integer (Times flagged)

\- speeding\_incidents: Integer

\- vehicle\_maintenance\_overdue: Yes/No

\- compliance\_issues\_open: Integer

BEHAVIOR:

\- punctuality\_to\_hub: Yes/No (Always on time to start shift)

\- attendance\_rate: Percent (Present days / working days)

\- attendance\_notes: Text (Any absences?)

\- professional\_conduct: Yes/No (No customer complaints about behavior)

\- conduct\_notes: Text

FINANCIAL:

\- commission\_earned: Currency

\- bonuses\_earned: Currency (For on-time \+ good ratings)

\- deductions: Currency (If damage, etc.)

\- net\_amount: Currency

COMPOSITE SCORE:

\- on\_time\_score: Percent (On-time % \* 30%)

\- quality\_score: Percent (Avg rating / 5 \* 30%)

\- safety\_score: Percent (100 \- incidents \* 20%)

\- professionalism\_score: Percent (Behavior \+ compliance \* 20%)

\- overall\_delivery\_score: Percent (Composite of above)

PERFORMANCE LEVEL:

\- performance\_level: Select

  ├─ Excellent (90-100) → Bonus eligible

  ├─ Good (75-89) → Regular pay \+ incentive

  ├─ Satisfactory (60-74) → Regular pay, improvement plan

  ├─ Poor (Below 60\) → Warning, retraining required

  └─ Critical (Below 40\) → Termination consideration

MANAGEMENT NOTES:

\- manager\_comments: Text Area

\- training\_recommended: Yes/No

\- training\_type: Text (Defensive driving, customer service, etc.)

\- promotion\_eligible: Yes/No

\- promotion\_reason: Text

\- warning\_issued: Yes/No

\- warning\_type: Select (Verbal / Written / Suspension)

\- suspension\_period: Days (If suspended)

LINKED TO HR:

\- appraisal\_reference: Link \[Appraisal\] (Driver's appraisal)

\- appraisal\_weight: Percent (Delivery metrics weight in appraisal \= 40%)

\- salary\_adjustment\_recommended: Yes/No

\- recommended\_increment: Percent (0-20% based on score)

---

## PART 4: VENDOR PORTAL USER INTERFACE

### 4.1 Vendor Portal \- Driver View

DASHBOARD (After Login)

┌──────────────────────────────────────────────────────────┐

│ Welcome Back, Rajesh\! | Last Login: 30 Jun 14:30        │

├──────────────────────────────────────────────────────────┤

│ TODAY'S ASSIGNMENTS                                      │

│ ┌──────────────────────────────────────────────────────┐ │

│ │ 8 Orders | 2 Completed | 4 In Transit | 2 Pending  │ │

│ │ ✓ ON TRACK (8/8 orders should complete on-time)    │ │

│ └──────────────────────────────────────────────────────┘ │

├──────────────────────────────────────────────────────────┤

│ MY ORDERS TODAY                                          │

│ ┌─────────────────────────────────────────────────────┐  │

│ │ Order 1: CDG-045-001 → Chandigarh City Center      │  │

│ │ Status: IN TRANSIT | Scheduled: 2-3 PM | Now: 2:15│  │

│ │ Customer: ABC Store | Distance: 3.2 km away       │  │

│ │ \[📍 OPEN IN MAP\] \[➜ DIRECTIONS\] \[✓ DELIVERED\]     │  │

│ ├─────────────────────────────────────────────────────┤  │

│ │ Order 2: CDG-045-002 → Chandigarh Market          │  │

│ │ Status: PENDING | Scheduled: 4-5 PM | Now: Upcoming│  │

│ │ Items: 12 units | \[START DELIVERY\]                │  │

│ └─────────────────────────────────────────────────────┘  │

├──────────────────────────────────────────────────────────┤

│ THIS MONTH'S PERFORMANCE                                 │

│ ┌──────────────────────────────────────────────────────┐ │

│ │ Deliveries: 156 | On-Time: 152 (97.4%) ✓          │ │

│ │ Avg Rating: 4.7/5 ⭐⭐⭐⭐⭐ (98 ratings)             │ │

│ │ Bonus Earned: ₹8,500 (Good performance bonus)       │ │

│ └──────────────────────────────────────────────────────┘ │

├──────────────────────────────────────────────────────────┤

│ ALERTS                                                   │

│ ⚠️  Vehicle maintenance due: 15 Jul (Tire rotation)      │

│ ✓ Insurance valid until: 30 Sep 2026                    │

└──────────────────────────────────────────────────────────┘

### 4.2 Delivery Tracking Map

LIVE MAP VIEW (During Delivery)

┌──────────────────────────────────────────────────────────┐

│ Order CDG-045-001 | Customer: ABC Store | 2:45 PM      │

├──────────────────────────────────────────────────────────┤

│  📍                                                       │

│    ╔═════════════════════════════╗                       │

│    ║                             ║                       │

│    ║        GOOGLE MAPS          ║                       │

│    ║                             ║                       │

│    ║   🚐 (Current Location)      ║                       │

│    ║   │                          ║                       │

│    ║   │ 250m away               ║                       │

│    ║   │                          ║                       │

│    ║   ▼                          ║                       │

│    ║  🏪 (Destination)            ║                       │

│    ║                             ║                       │

│    ║  ETA: 5 minutes            ║                       │

│    ╚═════════════════════════════╝                       │

│                                                          │

│ STATUS: IN TRANSIT                                      │

│ Speed: 42 km/h | Direction: North-East                 │

│ Distance Remaining: 250m | Time Remaining: 5 min       │

│                                                          │

│ \[📞 CALL CUSTOMER\] \[💬 SEND MESSAGE\] \[📸 TAKE PHOTO\]   │

└──────────────────────────────────────────────────────────┘

### 4.3 Proof of Delivery

DELIVERY COMPLETION SCREEN

┌──────────────────────────────────────────────────────────┐

│ COMPLETE DELIVERY                                        │

├──────────────────────────────────────────────────────────┤

│ Order: CDG-045-001                                       │

│ Customer: ABC Store                                      │

│ Items Delivered: 12 units                                │

│ Amount Collected: ₹45,600 (If COD)                      │

├──────────────────────────────────────────────────────────┤

│ 1\. TAKE DELIVERY PHOTO                                   │

│    \[📸 Take Photo\] \[or Select from Gallery\]             │

│    Preview: \[Proof photo showing delivery\]              │

├──────────────────────────────────────────────────────────┤

│ 2\. GET CUSTOMER SIGNATURE                                │

│    \[✍️ Capture Signature on Screen\] or \[Skip\]           │

│    Preview: \[Signature image\]                            │

├──────────────────────────────────────────────────────────┤

│ 3\. OPTIONAL: CUSTOMER FEEDBACK                           │

│    "Customer available? Would they like to rate?"        │

│    ○ Yes → \[COLLECT RATING\] (QR Code shown)            │

│    ○ No → \[SKIP\]                                        │

├──────────────────────────────────────────────────────────┤

│ 4\. CONFIRM DELIVERY                                      │

│    \[✓ MARK AS DELIVERED\]                                │

│    (This timestamp is locked and can't be changed)      │

│                                                          │

│    ⏱️ Scheduled Time: 2-3 PM | Actual: 2:28 PM ✓       │

│    Status: ON-TIME DELIVERY ✓                           │

└──────────────────────────────────────────────────────────┘

### 4.4 Customer Rating Interface

CUSTOMER FEEDBACK (QR Code Scan or SMS Link)

┌──────────────────────────────────────────────────────────┐

│ RATE YOUR DELIVERY                                       │

│ Order \#CDG-045-001 | Items: 12 units | ₹45,600        │

├──────────────────────────────────────────────────────────┤

│                                                          │

│ 1\. DELIVERY TIMELINESS                                   │

│    Was your delivery on-time? (2-3 PM scheduled)        │

│    Actual Delivery: 2:28 PM ✓ YES, ON-TIME             │

│    Rating: ⭐⭐⭐⭐⭐ (5/5 \- Excellent)                 │

│                                                          │

│ 2\. DELIVERY PERSON BEHAVIOR                              │

│    Rate the driver's behavior (politeness, professionalism)│

│    Rating: ⭐⭐⭐⭐⭐ (5/5 \- Very Professional)          │

│                                                          │

│ 3\. PRODUCT CONDITION                                     │

│    Were items in good condition? Any damage?            │

│    Rating: ⭐⭐⭐⭐⭐ (5/5 \- Perfect Condition)          │

│                                                          │

│ 4\. QUANTITY ACCURACY                                     │

│    Did you receive all items as ordered (12 units)?    │

│    Rating: ⭐⭐⭐⭐⭐ (5/5 \- All Correct)               │

│                                                          │

│ 5\. OVERALL EXPERIENCE                                    │

│    Overall satisfaction with delivery?                  │

│    Rating: ⭐⭐⭐⭐⭐ (5/5 \- Excellent)                 │

│                                                          │

│ OVERALL SCORE: 5.0 / 5.0 ⭐⭐⭐⭐⭐                      │

│                                                          │

│ Additional Comments (Optional):                          │

│ \[Good service\! Recommended for other deliveries\]       │

│                                                          │

│ Would you recommend this delivery service? ○ Yes ● No  │

│                                                          │

│ \[SUBMIT FEEDBACK\]                                       │

└──────────────────────────────────────────────────────────┘

### 4.5 Driver Performance Dashboard

MY MONTHLY PERFORMANCE

┌──────────────────────────────────────────────────────────┐

│ Rajesh Kumar | Driver ID: DP-CDG-001 | Jun 2026        │

├──────────────────────────────────────────────────────────┤

│ DELIVERY VOLUME                                          │

│ ┌────────────────────────────────────────────────────┐  │

│ │ Total: 156  | On-Time: 152 (97.4%) | Late: 4 (2.6%)│

│ │ Failed: 0   | Cancelled: 0                         │  │

│ └────────────────────────────────────────────────────┘  │

│                                                          │

│ CUSTOMER RATINGS                                         │

│ ┌────────────────────────────────────────────────────┐  │

│ │ Avg Rating: 4.7/5.0 (Based on 98 customer ratings) │  │

│ │ 5-Star: 85 (87%) | 4-Star: 10 (10%) | 3-Star: 3   │  │

│ │ 2-Star: 0        | 1-Star: 0                       │  │

│ └────────────────────────────────────────────────────┘  │

│                                                          │

│ SAFETY & COMPLIANCE                                      │

│ ┌────────────────────────────────────────────────────┐  │

│ │ Harsh Driving Incidents: 1 (One harsh brake)       │  │

│ │ Speeding Incidents: 0                               │  │

│ │ Vehicle Maintenance: ✓ Current (Due 15 Jul)        │  │

│ │ License Status: ✓ Valid until 30 Sep 2027          │  │

│ └────────────────────────────────────────────────────┘  │

│                                                          │

│ FINANCIAL                                                │

│ ┌────────────────────────────────────────────────────┐  │

│ │ Commission Earned: ₹12,480                          │  │

│ │ Performance Bonus: ₹8,500 (97.4% on-time)          │  │

│ │ Deductions: ₹0                                      │  │

│ │ NET EARNED: ₹20,980                                 │  │

│ └────────────────────────────────────────────────────┘  │

│                                                          │

│ PERFORMANCE RATING                                       │

│ ┌────────────────────────────────────────────────────┐  │

│ │ Overall Score: 94/100                               │  │

│ │ Level: ⭐ EXCELLENT (90-100)                        │  │

│ │ Status: ✓ BONUS ELIGIBLE                           │  │

│ └────────────────────────────────────────────────────┘  │

│                                                          │

│ \[Download Performance Report PDF\]                       │

└──────────────────────────────────────────────────────────┘

---

## PART 5: INTEGRATION WITH HR SYSTEM

### 5.1 Delivery Metrics → Appraisal Score

EXISTING HR APPRAISAL WEIGHTAGE (100% total):

Current (Without Delivery Portal):

├─ Goals Achievement: 50%

├─ Competency Assessment: 30%

└─ Behavioral Assessment: 20%

NEW (With Delivery Portal \- For Logistics Staff Only):

├─ Goals Achievement: 35%

│   └─ E.g., "Manage 120 deliveries/month" (Goal)

├─ Competency Assessment: 25%

│   └─ Technical driving, customer service, route planning

├─ Behavioral Assessment: 15%

│   └─ Punctuality, teamwork, following SOPs

└─ DELIVERY PERFORMANCE METRICS: 25% \[NEW\]

    ├─ On-Time Delivery Rate: 10%

    │   └─ 95%+ \= 5 points, 90-95% \= 4 points, etc.

    ├─ Customer Satisfaction Rating: 10%

    │   └─ 4.5-5.0 \= 5 points, 4.0-4.5 \= 4 points, etc.

    ├─ Safety & Compliance: 3%

    │   └─ Zero incidents \= 5 points, 1+ incidents \= deduct

    └─ Vehicle Maintenance & Care: 2%

        └─ No overdue maintenance \= 5 points

### 5.2 Performance Rating Impact on Compensation

DELIVERY PERFORMANCE TIER → SALARY IMPACT

Tier 1: EXCELLENT (Score 90-100)

├─ On-Time Delivery: 95%+

├─ Customer Rating: 4.5-5.0

├─ Safety Incidents: 0

├─ Maintenance: Current

└─ COMPENSATION DECISION:

    ├─ Base Salary Increase: \+12-15%

    ├─ Performance Bonus: 1.5x monthly base

    ├─ Loyalty Bonus: \+₹2,000 quarterly

    └─ Promotion Eligible: Yes

Tier 2: GOOD (Score 75-89)

├─ On-Time Delivery: 85-95%

├─ Customer Rating: 4.0-4.5

├─ Safety Incidents: 0-1

└─ COMPENSATION DECISION:

    ├─ Base Salary Increase: \+8-12%

    ├─ Performance Bonus: 1.0x monthly base

    └─ Promotion Eligible: With improvement plan

Tier 3: SATISFACTORY (Score 60-74)

├─ On-Time Delivery: 75-85%

├─ Customer Rating: 3.5-4.0

├─ Safety Incidents: 1-2

└─ COMPENSATION DECISION:

    ├─ Base Salary Increase: \+3-5%

    ├─ Performance Bonus: 0.5x monthly base

    ├─ Improvement Plan: Required

    └─ Promotion Eligible: No

Tier 4: POOR (Score Below 60\)

├─ On-Time Delivery: \< 75%

├─ Customer Rating: \< 3.5

├─ Safety Incidents: 2+

└─ COMPENSATION DECISION:

    ├─ Base Salary Increase: 0%

    ├─ Performance Bonus: None

    ├─ Improvement Plan: Mandatory, 90-day review

    └─ Warning: Written warning issued

### 5.3 HR Appraisal Integration \- Data Flow

MONTHLY DATA SYNC (Automatic)

┌─────────────────────────────────────────────────────┐

│ 1\. DELIVERY METRICS AGGREGATED                      │

│    \- On-time delivery % for month                   │

│    \- Avg customer rating for month                  │

│    \- Safety incidents count                         │

│    \- Vehicle maintenance status                     │

│    (All from Delivery Performance Scorecard)        │

└─────────────────────────────────────────────────────┘

                    ↓

┌─────────────────────────────────────────────────────┐

│ 2\. DELIVERY SCORECARD CREATED                       │

│    (Delivery Performance Scorecard DocType)         │

│    \- Calculated performance level                   │

│    \- Composite delivery score (out of 25%)          │

│    \- Manager review/comments added                  │

└─────────────────────────────────────────────────────┘

                    ↓

┌─────────────────────────────────────────────────────┐

│ 3\. DATA LINKED TO HR APPRAISAL                      │

│    \- Appraisal.delivery\_performance\_metrics linked  │

│    \- Score auto-populated in appraisal              │

│    \- Weighted 25% of overall rating                 │

└─────────────────────────────────────────────────────┘

                    ↓

┌─────────────────────────────────────────────────────┐

│ 4\. MANAGER REVIEWS APPRAISAL (March)                │

│    \- Reviews delivery metrics as one section        │

│    \- No separate rating needed (already calculated) │

│    \- Makes compensation decisions based on tier     │

└─────────────────────────────────────────────────────┘

                    ↓

┌─────────────────────────────────────────────────────┐

│ 5\. COMPENSATION ADJUSTED (April)                    │

│    \- New salary structure created                   │

│    \- Bonus calculated per tier                      │

│    \- Promotion processed (if eligible)              │

│    \- Synced to Logic ERP GL                         │

└─────────────────────────────────────────────────────┘

---

## PART 6: SECURITY & ACCESS CONTROL

### 6.1 Vendor Portal Access Model

ROLE-BASED ACCESS CONTROL:

1\. DELIVERY PARTNER (Self-Service Portal Access)

   Can:

   ├─ View own assigned orders for the day

   ├─ View delivery locations on map

   ├─ Mark delivery as complete with POD

   ├─ See own monthly performance metrics

   ├─ Receive notifications for new orders

   └─ View own earnings and bonuses

   Cannot:

   ├─ View other partners' orders

   ├─ View customer details beyond delivery address

   ├─ Modify order details

   ├─ Access financial details

   ├─ View strategic information

   └─ Download raw GPS data

2\. LOGISTICS MANAGER (Internal Admin)

   Can:

   ├─ View all partners and their performance

   ├─ View all orders and live tracking

   ├─ Assign orders to partners

   ├─ Create delivery hubs

   ├─ View real-time GPS data

   ├─ Access all delivery reports

   ├─ Manage partner compliance

   └─ Override delivery assignments

   Cannot:

   ├─ Access HR appraisal data (read-only reference)

   ├─ Modify salary/compensation (finance only)

   └─ Delete delivery records

3\. FINANCE MANAGER (Compensation Link)

   Can:

   ├─ View delivery performance scorecard

   ├─ Access performance tier classifications

   ├─ Calculate bonuses based on delivery metrics

   ├─ Approve salary increases

   └─ Generate payroll reports

   Cannot:

   ├─ Modify delivery assignments

   ├─ Access real-time GPS

   └─ Override logistics decisions

4\. HR MANAGER (Appraisal Integration)

   Can:

   ├─ View delivery metrics in appraisal (as data)

   ├─ See performance tier recommendations

   ├─ Review linked appraisal scores

   └─ Generate HR reports with delivery data

   Cannot:

   ├─ Modify delivery metrics

   ├─ Assign orders

   ├─ Access real-time tracking

   └─ Make logistics decisions

5\. CUSTOMER (Customer Portal \- Feedback)

   Can:

   ├─ Rate delivery via link/QR code

   ├─ Report delivery issues

   ├─ View delivery status (if opted in)

   └─ Track real-time location (if opted in)

   Cannot:

   ├─ See partner details

   ├─ Modify ratings

   ├─ Access performance data

   └─ Contact partner directly (through portal)

### 6.2 Data Privacy & Security

SENSITIVE DATA HANDLING:

1\. CUSTOMER DATA

   ├─ Email/Phone: Shown to partner (required for delivery)

   ├─ Address: Full address shown to partner

   ├─ Order Details: Shown to partner

   ├─ Payment Info: NOT shown to partner

   └─ Retention: 1 year after delivery

2\. PARTNER DATA

   ├─ Name/Phone: Visible to logistics manager only

   ├─ License Details: Encrypted, visible to HR/Admin

   ├─ Bank Account: Encrypted, Finance only

   ├─ Performance Ratings: Visible to HR/Finance/Manager

   └─ GPS Location: Real-time to manager, aggregated to partner

3\. GPS DATA

   ├─ Real-time: Manager only during delivery

   ├─ Historical: Aggregated, not real-time after delivery

   ├─ Retention: 90 days raw, 1 year aggregated

   ├─ GDPR Compliance: Anonymized after 90 days

   └─ Cannot be used for: Personal tracking outside work

4\. CUSTOMER FEEDBACK

   ├─ Individual Ratings: Partner can see own feedback

   ├─ Comments: NOT visible to partner (only manager)

   ├─ Complaint Details: Manager only

   └─ Public: Aggregated ratings only (no names)

ENCRYPTION:

└─ In Transit: HTTPS/TLS 1.3

└─ At Rest: AES-256 for sensitive fields

└─ Database: All PII encrypted with separate keys

---

## PART 7: IMPLEMENTATION STRATEGY

### 7.1 Phase 6: Vendor Portal Implementation

**Timeline:** Months 10-13 (Post-HR system go-live)

PHASE 6A: REQUIREMENTS & DESIGN (Weeks 1-4)

Week 1-2: Vendor Portal Design

□ Document vendor user requirements (driver perspective)

□ Design customer feedback interface

□ GPS tracking architecture design

□ Security framework for vendor access

□ Mobile app requirements

Week 3-4: Integration Design

□ API design for HR appraisal integration

□ Data sync frequency and methods

□ Performance scorecard calculation rules

□ Exception handling procedures

□ Testing strategy

Deliverables:

✓ Detailed specifications

✓ Wireframes and mockups

✓ Integration architecture

✓ Risk assessment

### 7.2 Phase 6B: Development

PHASE 6B: DEVELOPMENT & CUSTOMIZATION (Weeks 5-12)

Week 5-6: Backend Development

□ Create new DocTypes (Delivery Partner, Delivery Order, etc.)

□ GPS tracking table and APIs

□ Feedback form and data capture

□ Performance scorecard calculation logic

□ API development for HR integration

Week 7-8: Frontend Development

□ Vendor portal web interface (React/Vue)

□ Mobile app development (Flutter/React Native)

□ Map integration (Google Maps API)

□ Real-time notifications

□ Dashboard creation

Week 9-10: Integration Development

□ Logic ERP API integration (Order sync)

□ HR System API integration (Appraisal data)

□ Automated sync pipelines

□ Data transformation and mapping

□ Error handling and logging

Week 11-12: Internal Portal Features

□ Manager dashboard for tracking

□ Compliance monitoring tools

□ Report generation

□ Alert system setup

□ Admin interface

Deliverables:

✓ Fully functional vendor portal

✓ Mobile app (beta)

✓ Integration pipelines

✓ API endpoints

### 7.3 Phase 6C: Testing & Pilot

PHASE 6C: TESTING & PILOT LAUNCH (Weeks 13-16)

Week 13: Unit & Integration Testing

□ API testing (Logic ERP sync, HR integration)

□ Database performance testing (GPS high volume)

□ GPS accuracy and reliability testing

□ Feedback form validation

□ Performance scorecard calculations

Week 14: UAT with Real Data

□ Test with 5-10 actual delivery partners

□ Real orders and real customers

□ Live GPS tracking

□ Customer feedback collection

□ Performance metrics validation

Week 15: Pilot Refinement

□ Bug fixes from UAT

□ Performance optimization

□ UX/UI improvements

□ Partner feedback incorporation

□ Security hardening

Week 16: Go-Live Preparation

□ Final testing

□ Partner training

□ Customer communication

□ Go-live checklist

□ Support team readiness

Deliverables:

✓ Tested, production-ready system

✓ Partner training materials

✓ Operations manual

✓ Support documentation

### 7.4 Phase 6D: Rollout & Stabilization

PHASE 6D: ROLLOUT & STABILIZATION (Weeks 17-20)

Week 17: Pilot Rollout

□ 10-15 drivers (Chandigarh Hub first)

□ 50-100 orders daily

□ Monitor system performance

□ Collect feedback

□ Address issues immediately

Week 18: Staged Expansion

□ Add Panchkula Hub (10 drivers)

□ Monitor combined system

□ Optimize GPS and notifications

□ Refine performance algorithms

Week 19: Full Rollout

□ Deploy to all 40 drivers across all hubs

□ Full system load testing

□ Monitor all KPIs

□ Customer satisfaction tracking

Week 20: Post-Launch Optimization

□ Performance tuning

□ User feedback incorporation

□ Security audit completion

□ Documentation finalization

□ Training for new hires

Deliverables:

✓ 40 drivers, 1000+ orders/day live

✓ Customer feedback system operational

✓ HR integration tested and stable

✓ All KPIs tracking

### 7.5 Implementation Dependencies

CRITICAL PATH:

├─ HR System Must Be: LIVE & STABLE (Prerequisite)

├─ Logic ERP Must Provide: Sales Order \+ Delivery Order APIs

├─ Logistics Team Must Provide: Current order flow documentation

└─ IT Must Provide: GPS API services, mobile infrastructure

RESOURCE REQUIREMENTS:

├─ Development: 2-3 Full-stack developers

├─ Backend: 1 Database expert (GPS high volume)

├─ Frontend: 2 Mobile \+ Web developers

├─ QA: 2 Test engineers

├─ Business Analyst: 1 (requirements, UAT coordination)

├─ Logistics Trainer: 1 (driver training)

└─ Project Manager: 1 (overall coordination)

INFRASTRUCTURE:

├─ GPS Database: High-capacity (Millions of records/day)

├─ API Gateway: Rate-limited for vendor access

├─ Map API: Google Maps integration (Budget: ₹50K/month)

├─ Mobile Backend: Push notifications service

└─ Security: SSL certificates, VPN for logistics staff

---

## PART 8: VENDOR PORTAL DASHBOARDS

### 8.1 Manager Dashboard \- Live Tracking

LOGISTICS MANAGER DASHBOARD (Real-time)

┌──────────────────────────────────────────────────────────┐

│ CHANDIGARH HUB | 22 Drivers | 88 Orders Today           │

├──────────────────────────────────────────────────────────┤

│                                                          │

│ DELIVERY STATUS                                          │

│ ✓ Completed: 24 (27%) | ⏳ In Transit: 48 (55%)         │

│ ⏱️ Pending: 12 (14%) | ❌ Failed: 4 (5%)                │

│                                                          │

│ ON-TIME DELIVERY TODAY                                   │

│ Expected: 70+ (80% target) | Actual: 68 (77%)          │

│ ⚠️ Slightly behind target \- monitor next 2 hours       │

│                                                          │

│ LIVE MAP (with all vehicle markers)                     │

│ ┌────────────────────────────────────────────────────┐  │

│ │ 🚐 🚐 🚐 (22 vehicles mapped)                       │  │

│ │ ✓ ✓ ✓ (14 completed deliveries marked)            │  │

│ │ ⏱️ ⏱️ (8 vehicles offline \- check)                  │  │

│ └────────────────────────────────────────────────────┘  │

│                                                          │

│ ALERTS                                                   │

│ 🔴 CRITICAL: Driver \#12 harsh braking detected (5x/min) │

│    → Vehicle assigned: CDG-045-012                      │

│    → Action: Contact driver, check safety            │

│                                                          │

│ 🟠 WARNING: Order CDG-045-056 20min behind schedule    │

│    → Customer: XYZ Store, Delivery window: 3-4 PM      │

│    → Current: 3:40 PM                                  │

│    → Action: Notify customer, confirm safe delivery   │

│                                                          │

│ 🟡 INFO: Vehicle \#18 maintenance due 15 Jul            │

│    → Status: On schedule, no action needed            │

│                                                          │

│ PERFORMANCE THIS MONTH (As of today, 30 Jun)          │

│ ┌────────────────────────────────────────────────────┐  │

│ │ Drivers: 22                                         │  │

│ │ Avg Rating: 4.65/5 ⭐⭐⭐⭐⭐                        │  │

│ │ On-time %: 97.2% ✓ (Target: 95%)                  │  │

│ │ Failed Deliveries: 2 (0.8%)                       │  │

│ │ Customer Complaints: 1 (0.03%)                    │  │

│ └────────────────────────────────────────────────────┘  │

│                                                          │

│ \[VIEW DETAILED REPORTS\] \[ASSIGN NEW ORDER\] \[SETTINGS\]  │

└──────────────────────────────────────────────────────────┘

### 8.2 Hub Performance Report

MONTHLY HUB PERFORMANCE (June 2026\)

┌──────────────────────────────────────────────────────────┐

│ CHANDIGARH HUB                                           │

├──────────────────────────────────────────────────────────┤

│ Drivers: 22 | Vehicles: 22 | Orders: 2,064             │

│                                                          │

│ DELIVERY PERFORMANCE                                     │

│ ┌────────────────────────────────────────────────────┐  │

│ │ On-Time Delivery: 2,006 / 2,064 \= 97.2%           │  │

│ │ Late Delivery: 48 / 2,064 \= 2.3%                  │  │

│ │ Failed (Retry): 8 / 2,064 \= 0.4%                  │  │

│ │ Cancelled: 2 / 2,064 \= 0.1%                       │  │

│ │ TARGET: 95% on-time → STATUS: ✓ EXCEEDED          │  │

│ └────────────────────────────────────────────────────┘  │

│                                                          │

│ CUSTOMER SATISFACTION                                    │

│ ┌────────────────────────────────────────────────────┐  │

│ │ Avg Rating: 4.65 / 5.0                             │  │

│ │ Ratings Collected: 1,562 (75.6% feedback rate)    │  │

│ │ 5-Star: 1,285 (82%) | 4-Star: 195 (12%)          │  │

│ │ 3-Star: 65 (4%) | 2-Star: 15 (1%) | 1-Star: 2 (0%)│  │

│ │ TREND: ✓ Improving (June: 4.65 vs May: 4.58)     │  │

│ └────────────────────────────────────────────────────┘  │

│                                                          │

│ ISSUES & COMPLAINTS                                      │

│ ┌────────────────────────────────────────────────────┐  │

│ │ Complaints: 12 (0.58% of orders)                  │  │

│ │ • Damaged Products: 5                             │  │

│ │ • Missing Items: 4                                │  │

│ │ • Rude Behavior: 2                                │  │

│ │ • Late Delivery: 1                                │  │

│ │ Resolution Rate: 100% (All resolved)              │  │

│ │ Avg Resolution Time: 2 days                       │  │

│ │ TREND: ✓ Below 1% complaint rate                 │  │

│ └────────────────────────────────────────────────────┘  │

│                                                          │

│ DRIVER PERFORMANCE (Top 5\)                              │

│ ┌─────────────────────────────────────────────────────┐ │

│ │ 1\. Rajesh Kumar (CDG-001): 156 orders, 4.7/5, 97.4%│ │

│ │ 2\. Amit Singh (CDG-002): 142 orders, 4.6/5, 96.0% │ │

│ │ 3\. Priya Sharma (CDG-003): 148 orders, 4.5/5, 95.2%│ │

│ │ 4\. Vikram Patel (CDG-004): 140 orders, 4.5/5, 94.3%│ │

│ │ 5\. Neha Das (CDG-005): 135 orders, 4.4/5, 93.7%  │ │

│ └─────────────────────────────────────────────────────┘ │

│                                                          │

│ FINANCIAL SUMMARY                                        │

│ ┌────────────────────────────────────────────────────┐  │

│ │ Total Commission Paid: ₹2,30,500                   │  │

│ │ Performance Bonuses: ₹85,000 (40% of drivers)      │  │

│ │ Cost per Delivery: ₹115 (2,064 orders / commission)│  │

│ │ Revenue Impact: ₹40,000+ (Avoided complaints)      │  │

│ └────────────────────────────────────────────────────┘  │

│                                                          │

│ \[DOWNLOAD FULL REPORT\] \[EXPORT TO EXCEL\]               │

└──────────────────────────────────────────────────────────┘

---

## PART 9: VENDOR PORTAL KPIs & METRICS

### 9.1 Key Performance Indicators

DELIVERY PERFORMANCE KPIs:

1\. ON-TIME DELIVERY %

   Definition: (Orders delivered by scheduled time / Total orders) × 100

   Target: 95%+

   Impact: 10% of driver appraisal score

   

   Status: 97.2% ✓ (Exceeding target)

   Bonus: 1.5x monthly (if maintained)

2\. AVERAGE CUSTOMER RATING

   Definition: Sum of all customer ratings / Total ratings collected

   Scale: 1-5 stars

   Target: 4.5+

   Impact: 10% of driver appraisal score

   

   Status: 4.65/5 ✓ (Exceeding target)

   Bonus: Eligible for tier promotion

3\. FAILURE RATE

   Definition: (Failed delivery attempts / Total orders) × 100

   Target: \< 1%

   Impact: Included in appraisal

   

   Status: 0.4% ✓ (Below target)

   Implication: Good route planning, customer contact

4\. CUSTOMER COMPLAINT RATE

   Definition: (Complaints received / Total orders) × 100

   Target: \< 0.5%

   Impact: 3% of appraisal score

   

   Status: 0.58% ⚠️ (Slightly above target, monitoring)

   Action: Focus on quality control

5\. SAFETY INCIDENT RATE

   Definition: Number of safety incidents per month

   Target: 0

   Impact: 3% of appraisal score

   

   Status: 2 harsh braking incidents (June)

   Action: Defensive driving course recommended

6\. VEHICLE MAINTENANCE COMPLIANCE

   Definition: All scheduled maintenance completed on time

   Target: 100%

   Impact: 2% of appraisal score

   

   Status: 100% ✓

   Implication: Good vehicle upkeep

7\. ATTENDANCE & PUNCTUALITY

   Definition: Days worked / Expected working days

   Target: 95%+

   Impact: Tied to appraisal

   

   Status: 98% ✓

8\. FEEDBACK COLLECTION RATE

   Definition: (Customer feedbacks / Total deliveries) × 100

   Target: 70%+

   Impact: Quality of data

   

   Status: 75.6% ✓ (Good feedback coverage)

### 9.2 Performance Tier Calculation

COMPOSITE SCORE FORMULA:

Delivery Score \= (On-Time % × 0.40) \+ 

                 (Avg Rating / 5 × 0.40) \+ 

                 (Safety Score × 0.20)

Where:

\- On-Time %: Actual percentage (97.2% \= 0.972)

\- Avg Rating: Out of 5 (4.65/5 \= 0.93)

\- Safety Score: (5 \- incidents) / 5 (if 2 incidents: 0.6)

Example Calculation (Rajesh Kumar):

\= (97.4% × 0.40) \+ (4.7/5 × 0.40) \+ ((5-0)/5 × 0.20)

\= (0.389) \+ (0.376) \+ (0.200)

\= 0.965 or 96.5%

This 96.5% \= EXCELLENT tier (90-100)

Compensation Impact: \+15% salary increase \+ 1.5x bonus

Promotion: Eligible for Senior Driver / Logistics Supervisor role

---

## PART 10: RISK MITIGATION & CONTINGENCY

### 10.1 Implementation Risks

RISK MATRIX:

HIGH PRIORITY RISKS:

1\. GPS ACCURACY & RELIABILITY

   Risk: GPS signal loss, inaccurate location data

   Impact: Delivery tracking not visible, liability issues

   Mitigation:

   ├─ Test with 10+ devices before rollout

   ├─ Use high-accuracy GPS receivers (not just phone)

   ├─ Implement fallback (last known location \+ time)

   ├─ Alert system if signal lost \> 5 minutes

   └─ Insurance coverage for disputes

2\. DATA PRIVACY / GDPR COMPLIANCE

   Risk: Customer/driver location data misuse, legal action

   Impact: Regulatory fines, reputation damage

   Mitigation:

   ├─ Data encryption (AES-256)

   ├─ Limited access controls

   ├─ Data retention policies (90 days raw)

   ├─ Anonymization after retention period

   ├─ Vendor agreements with privacy clauses

   └─ Regular security audits

3\. VENDOR PORTAL ADOPTION

   Risk: Drivers not using app, data gaps, slow rollout

   Impact: System failure, incomplete metrics

   Mitigation:

   ├─ Incentivize usage (bonus based on platform adoption)

   ├─ Training on platform before rollout

   ├─ 24/7 support hotline for drivers

   ├─ Fallback: Manual order assignment if needed

   ├─ Gamification (leaderboards, performance badges)

   └─ Regular feedback collection

4\. INTEGRATION FAILURES

   Risk: Logic ERP API broken, HR sync fails, data mismatch

   Impact: Wrong order assignments, incorrect appraisals

   Mitigation:

   ├─ Parallel run (manual \+ system) for first 2 weeks

   ├─ Reconciliation reports (automated daily)

   ├─ Fallback: Manual entry if API fails

   ├─ Vendor support on call during rollout

   ├─ Daily monitoring of sync status

   └─ Alert system for failures

MEDIUM PRIORITY RISKS:

5\. Customer Feedback Quality

   Risk: Drivers rate their own deliveries, biased feedback

   Impact: Inaccurate performance assessment

   Mitigation:

   ├─ QR code/SMS link (third-party feedback, not driver)

   ├─ Verify feedback legitimacy (flagged if suspicious)

   ├─ Cross-check with order data (order must exist)

   └─ Manual review of extreme ratings

6\. Cost Overruns

   Risk: GPS, maps, mobile development costs exceed budget

   Impact: ROI delayed, budget pressure

   Mitigation:

   ├─ Phased rollout (start with 10 drivers)

   ├─ Open-source alternatives (OSM instead of Google Maps)

   ├─ In-house development focus

   ├─ Clear scope management, change control

   └─ Monthly budget tracking

7\. Change Management

   Risk: Drivers resisting system, managers not using dashboards

   Impact: Low adoption, system underutilized

   Mitigation:

   ├─ Early engagement (involve drivers in UAT)

   ├─ Incentives for adoption (bonuses, recognition)

   ├─ Training and support

   ├─ Regular communication of benefits

   ├─ Feedback loop and continuous improvement

   └─ Cultural shift narrative (transparency, fairness)

LOW PRIORITY RISKS:

8\. Mobile App Crashes

   Risk: App freezes, poor UX, connectivity issues

   Mitigation: Beta testing, regular updates, support chat

9\. Vehicle GPS Hardware Failure

   Risk: Device breaks, needs replacement

   Mitigation: Insurance, spare devices, supplier agreement

---

## PART 11: SUCCESS METRICS & GO-LIVE CHECKLIST

### 11.1 Success Metrics (6 Months Post Go-Live)

TECHNOLOGY METRICS:

✓ System Uptime: 99.5%+ (Target: 99%)

✓ GPS Accuracy: 95%+ within 50m (Target: 90%)

✓ Data Sync Success: 99%+ (Target: 98%)

✓ API Response Time: \< 500ms (Target: \< 1s)

✓ Mobile App Crash Rate: \< 0.1% (Target: \< 1%)

ADOPTION METRICS:

✓ Driver Portal Usage: 98%+ daily active (Target: 85%)

✓ Customer Feedback Rate: 80%+ (Target: 70%)

✓ Order Assignment via System: 100% (Target: 95%)

✓ Manager Dashboard Usage: 95%+ (Target: 80%)

OPERATIONAL METRICS:

✓ On-Time Delivery: Increased to 97% (Previously: Manual tracking)

✓ Failed Delivery Rate: \< 1% (Previously: Unknown)

✓ Customer Complaint Rate: \< 0.5% (Previously: \~1.5% estimated)

✓ Customer Satisfaction: 4.6+/5 (New metric)

✓ Feedback Collection: 75%+ (Target: 70%)

FINANCIAL METRICS:

✓ Logistics Cost Reduction: 5-10% (Through efficiency)

✓ Revenue Protected: ₹50L+ (Avoided complaints/returns)

✓ Driver Retention: 95%+ (Fair assessment system)

✓ ROI Achievement: Breakeven within 8-10 months

BUSINESS METRICS:

✓ Customer Satisfaction (overall): Increased 10%+

✓ Repeat Orders: Increased 15%+ (Good delivery experience)

✓ HR Appraisal Objectivity: 100% data-driven for logistics staff

✓ Performance-based Compensation: Full transparency achieved

✓ Delivery Partner Engagement: 90%+ satisfaction with system

TARGET (Month 6): 80%+ of all metrics met or exceeded

### 11.2 Go-Live Checklist

PRE-LAUNCH (1 Week Before)

SYSTEM READINESS:

□ All code merged and deployed to production

□ Database backups configured and tested

□ Performance testing completed (load test with 50 users)

□ Security audit completed

□ API endpoints tested with Logic ERP

□ Mobile app signed and published to app stores

□ SMS/Email notification system tested

□ Map integration tested across regions

DATA READINESS:

□ All 40 drivers added to system with credentials

□ Vehicle data complete and verified

□ Customer master synced from Logic ERP

□ Delivery hub coordinates set correctly

□ Geofences created for all hubs

PEOPLE READINESS:

□ 40 drivers trained on app usage

□ 5 logistics managers trained on admin portal

□ HR team trained on performance scorecard

□ Finance team trained on integration

□ Support team briefed and on standby

□ Escalation process documented

CONTINGENCY:

□ Fallback procedure documented (manual order assignment)

□ Rollback plan prepared (if critical issues)

□ Vendor support contact verified

□ 24/7 hotline setup (for drivers, customers)

□ Issue tracking system ready

□ Daily monitoring dashboard created

COMMUNICATION:

□ Driver announcement (launch date, benefits)

□ Customer communication (tracking capability)

□ Manager briefing (system capabilities)

□ Internal team notification (support team ready)

□ Supplier notification (vendor integration live)

GO-LIVE DAY (T-Day):

6 AM:

□ Production system health check

□ API connectivity verified

□ Database integrity confirmed

□ Mobile app deployed and accessible

8 AM:

□ Start with Chandigarh Hub (10 drivers, 50 orders)

□ Monitor system performance

□ Collect real-time logs

□ Verify order assignments

12 PM:

□ Review morning metrics

□ Collect driver feedback

□ Verify customer feedback collection

□ Check for any issues

3 PM:

□ Add Panchkula Hub (10 drivers, 40 orders) if Chandigarh stable

□ Monitor combined system

□ Continue issue monitoring

6 PM:

□ Daily review meeting

□ Document issues found

□ Plan fixes for next day

□ Celebrate successful launch

WEEK 1 (Stabilization):

Daily:

□ Monitor system performance (all KPIs)

□ Review error logs

□ Collect driver feedback

□ Respond to support tickets (\< 2 hour response)

□ Fix critical bugs immediately

□ Deploy hot fixes as needed

Monitor:

□ GPS accuracy and reliability

□ API sync success rate

□ Customer feedback collection

□ Driver app usage and issues

□ Customer communication effectiveness

By End of Week 1:

□ 40+ successful deliveries tracked

□ 100+ customer feedback collected

□ Zero critical issues remaining

□ Driver adoption \> 90%

□ System stable for expansion

POST-LAUNCH:

Week 2-4:

□ Full rollout to all 40 drivers across all hubs

□ Scale monitoring to full capacity

□ Optimize performance based on Week 1 learnings

□ Continue support and training

□ Gather comprehensive feedback

Month 2+:

□ Performance optimization

□ Feature enhancements based on feedback

□ Integration refinement with HR appraisal

□ Vendor onboarding for contractual partners

□ Documentation finalization

---

## CONCLUSION

The Vendor Delivery Portal is a **transformative addition** to Grace Group's Frappe HR system, creating complete visibility into delivery execution while enabling **objective, data-driven performance assessments** of the logistics team.

### Key Benefits:

✅ **For Customers:**

- Real-time delivery tracking  
- Ability to rate delivery quality  
- Better delivery experiences (on-time, professional)

✅ **For Delivery Partners:**

- Clear performance metrics (objective assessment)  
- Fair compensation (tied to actual performance)  
- Career growth opportunities (data-backed promotions)  
- Accountability and transparency

✅ **For Grace Group:**

- Complete logistics visibility  
- Data-driven HR decisions for logistics staff  
- Risk mitigation (customer satisfaction, safety)  
- Cost optimization (5-10% efficiency gains)  
- Competitive advantage (superior delivery experience)

### Strategic Impact:

This portal transforms delivery from a **cost center** (minimize expenses) to a **value center** (enhance customer satisfaction, drive repeat orders). By linking operational metrics to HR appraisals, Grace Group creates a **virtuous cycle:**

Better Delivery → Higher Customer Satisfaction 

         ↓

Customer Repeat Orders → Revenue Growth

         ↓

Performance-Linked Compensation → Driver Motivation

         ↓

Higher Service Quality → Even Better Deliveries

         ↓

\[Cycle Repeats\]

### Timeline to Full Value:

- **Month 1-3:** System built and pilot tested (10 drivers)  
- **Month 4:** Full rollout (40 drivers, 1000+ orders/day)  
- **Month 6:** System optimized, metrics stabilized, ROI positive  
- **Month 12:** Integrated with vendor/franchisee network (60+ partners)

**Estimated Investment:** ₹25-40 Lakhs (Development \+ Infrastructure)  
**Estimated Payback:** 8-10 months (Through efficiency gains \+ retained revenue)  
**5-Year Value:** ₹2-3 Crores (Cumulative efficiency \+ customer retention)

---

**Document Version:** 1.0  
**Date:** July 2026  
**For:** Grace Group Leadership & Implementation Team

*This vendor portal represents Grace Group's next competitive advantage: a transparent, technology-enabled, performance-based logistics operation that delights customers and motivates partners.*

---

## APPENDIX: Mobile App Wireframe Overview

DRIVER APP SCREENS:

1\. LOGIN

   ├─ Driver ID / Email

   └─ Password

2\. HOME DASHBOARD

   ├─ Today's Stats (Orders, Status, Rating)

   ├─ Live Order Map

   └─ Performance Metrics

3\. ORDER LIST

   ├─ Today's Orders (Pending/In Transit/Completed)

   ├─ Order Details (Items, Location, Time)

   └─ Actions (Start, Navigate, Complete)

4\. DELIVERY MAP

   ├─ Real-time Location (GPS)

   ├─ Navigation to Customer

   ├─ ETA and Distance

   └─ Customer Contact

5\. DELIVERY COMPLETION

   ├─ Take Photo (Proof)

   ├─ Collect Signature

   ├─ Mark Delivered

   └─ Confirmation

6\. PERFORMANCE

   ├─ Monthly Metrics (On-time %, Rating, Earnings)

   ├─ Charts and Trends

   └─ Feedback (Recent ratings)

7\. SUPPORT

   ├─ Help Center

   ├─ Contact Manager

   ├─ Report Issue

   └─ Chat Support

---

END OF VENDOR PORTAL USE CASE  
