/* Slice 069: the fixtures the wall chart checks run on, shaped exactly as
 * `position_table` returns its rows (register.py). INVENTED DATA ONLY: the
 * names and seats are prototype-v1's, on DTC's shape - one top, 22 seats
 * under it, 5 leads with 14 / 10 / 13 / 19 / 11 seats under them, 90 seats,
 * 363 people.
 *
 * Used by scripts/check_wall_chart.js (CI, jsdom) and
 * scripts/check_wall_chart_browser.js (Playwright, not CI).
 *
 *   dtc90({ sentinel })  F-DTC90; with sentinel, every key PRIV-1 must keep
 *                        off paper is filled (AC-27a / AC-27b)
 *   owner()              F-OWNER: the 8 Pitampura seats, managers outside
 *   group()              F-GROUP: identical Cashier seats (D-6)
 *   noLeave()            F-NOLEAVE: may_see_leaving false, leaving null
 *   manager()            sent leaving dates for their reports, but not HR
 *   scaled(n)            F-DTC90 repeated n times under one top (10x check)
 */
const FIRST = ["Aarav", "Priya", "Rohit", "Neha", "Vikram", "Ananya", "Karan", "Sneha", "Arjun", "Pooja", "Rahul", "Kavya", "Sanjay", "Meera", "Aditya", "Divya", "Manish", "Ritu", "Nikhil", "Simran", "Deepak", "Isha", "Amit", "Nisha", "Varun", "Tanvi", "Suresh", "Anjali", "Gaurav", "Shreya", "Harish", "Payal", "Mohit", "Jyoti", "Rakesh", "Komal", "Vivek", "Swati", "Ajay", "Bhavna"];
const LAST = ["Sharma", "Verma", "Gupta", "Malhotra", "Kapoor", "Mehta", "Arora", "Bansal", "Chopra", "Saxena", "Joshi", "Khanna", "Sethi", "Bhatia", "Agarwal", "Tandon", "Goel", "Mittal", "Sood", "Grover", "Ahuja", "Bedi", "Kohli", "Nanda", "Puri", "Rana", "Sahni", "Taneja", "Walia", "Dhawan"];

const LEADS = {
  "Admin Head": ["Head Office", "Administration", [["Admin Executive", 4], ["Office Assistant", 5], ["Housekeeping", 9], ["Receptionist", 2], ["Driver", 2], ["Security Guard", 16], ["Electrician", 2], ["Plumber", 1], ["Pantry", 3], ["Courier", 1], ["Gardener", 2], ["Liaison Officer", 1], ["Store Keeper", 2], ["Admin Assistant", 2]]],
  "Back Office Manager": ["Head Office", "Accounts", [["Back Office", 36], ["Accounts Executive", 6], ["Billing", 5], ["Data Entry", 8], ["MIS Executive", 3], ["Inventory Clerk", 4], ["GST Executive", 3], ["Payroll Clerk", 2], ["Dispatch Clerk", 4], ["Audit Assistant", 0]]],
  "Facility Manager": ["Head Office", "Operations", [["Floor Manager Noida", 3], ["Floor Manager Delhi", 3], ["Floor Manager Pitampura", 3, "Pitampura"], ["Cashier Noida", 5], ["Cashier Delhi", 4], ["Cashier Pitampura", 4, "Pitampura"], ["Packing", 11], ["Alteration Tailor", 3], ["Stock Assistant", 6], ["Customer Desk", 3], ["Trial Room Attendant", 4], ["Billing Counter", 4], ["Gift Wrap", 2]]],
  "Manager Delhi": ["Delhi", "Sales", [["Sales - Sarees", 8], ["Sales - Lehenga", 7], ["Sales - Menswear", 6], ["Sales - Kids", 4], ["Sales - Jewellery", 9], ["Sales - Footwear", 5], ["Sales - Accessories", 3], ["Sales - Fabrics", 5], ["Sales - Bridal", 6], ["Sales - Western", 3], ["RSO Pitampura - Sarees", 6, "Pitampura"], ["RSO Pitampura - Lehenga", 5, "Pitampura"], ["RSO Pitampura - Menswear", 4, "Pitampura"], ["RSO Pitampura - Kids", 4, "Pitampura"], ["RSO Pitampura - Jewellery", 5, "Pitampura"], ["RSO Pitampura - Footwear", 3, "Pitampura"], ["Display", 2], ["Stock Room", 4], ["Night Guard", 0]]],
  "S-RE Manager": ["Noida", "Sales", [["RSO Noida", 31], ["Senior RSO Noida", 6], ["RSO Ambala", 8, "Ambala"], ["RSO Gurgaon", 6, "Gurgaon"], ["Sales Trainee", 3], ["Telecaller", 4], ["Online Orders", 5], ["Home Delivery", 4], ["Corporate Sales", 3], ["Event Sales", 0], ["Returns Desk", 5]]],
};
const UNDER_TOP = ["Chief Financial Officer", "Company Secretary", "Head of Purchase", "IT Head", "Marketing Head", "HR Head", "Legal Counsel", "Design Head", "Quality Head", "Logistics Head", "Customer Care Head", "Internal Auditor", "Executive Assistant", "Business Analyst", "Visual Merchandiser", "Security Head", "Training Head"];

/* A designation as DTC writes one: the job, without the store in it
   ("RSO Noida" -> "RSO", "Cashier Pitampura" -> "Cashier"). Otherwise the
   same as the seat title, which the paper then leaves out. */
function designationOf(title) {
  const m = /^(RSO|Senior RSO|Cashier|Floor Manager) /.exec(title);
  if (m) return m[1];
  if (/^Sales - /.test(title)) return "Sales Executive";
  return title;
}

function dtc90(opt) {
  opt = opt || {};
  let pi = 0, rid = 0;
  const rows = [];
  const person = () => {
    const n = FIRST[(pi * 7) % FIRST.length] + " " + LAST[(pi * 11 + Math.floor(pi / 30)) % LAST.length];
    pi++;
    return { employee: opt.sentinel ? "EMP-SNTL" : "HR-EMP-" + pi, assignment: opt.sentinel ? "ASG-SNTL" : "ASG-" + pi,
             name: n, weight: opt.sentinel ? 50 : 100, type: opt.sentinel ? "TYPE-SNTL" : "Permanent",
             covering: !!opt.sentinel, hired_on: opt.sentinel ? "HIRED-SNTL" : null, leaving: null,
             image: opt.sentinel ? "IMG-SNTL" : undefined };
  };
  const seat = (title, branch, dept, parent, count) => {
    const r = { id: "POS-" + String(++rid).padStart(3, "0"), title, reports_to: parent ? parent.id : "",
                reports_to_title: parent ? parent.title : "", branch, department: dept,
                designation: designationOf(title), grade: "", company: "Sample Fashions Pvt Ltd",
                status: "Active", key: false, seats: Math.max(1, count), filled: count,
                open: count ? 0 : 1, opening: null, leaving_on: null, people: [] };
    for (let i = 0; i < count; i++) r.people.push(person());
    rows.push(r);
    return r;
  };
  const top = seat("Owner and Managing Director", "Head Office", "Management", null, 1);
  Object.keys(LEADS).forEach((t) => {
    const [br, dept, list] = LEADS[t];
    const lead = seat(t, br, dept, top, 1);
    list.forEach(([title, n, b]) => seat(title, b || br, dept, lead, n));
  });
  UNDER_TOP.forEach((t) => seat(t, "Head Office", "Management", top, (t === "Legal Counsel" || t === "Training Head") ? 0 : 1));

  const cfo = rows.find((r) => r.title === "Chief Financial Officer");
  const guard = rows.find((r) => r.title === "Security Guard");
  cfo.people[0].leaving = "2026-11-30"; cfo.leaving_on = "2026-11-30";
  rows.find((r) => r.title === "Legal Counsel").opening = opt.sentinel ? "OPEN-SNTL" : "HR-OPN-SNTL";
  if (opt.sentinel) {
    guard.people[0].leaving = "2099-01-01"; guard.leaving_on = "2099-01-01";
    rows.forEach((r) => {
      Object.assign(r, { grade: "GRADE-SNTL", designation: "DESIG-OK", department: "DEPT-OK", key: true,
                         status: "Frozen", image: "IMG-SNTL",
                         plan: { note: "PLAN-SNTL", set_by: "WHO-SNTL", reason: "REASON-SNTL" } });
    });
  }
  return {
    rows, as_at: "2026-10-24", may_see_leaving: true, may_edit: true, may_delete: true,
    unseated: opt.sentinel ? [{ name: "UNSEATED-SNTL", branch: "Noida", no_manager: false }] : Array.from({ length: 82 }, (_, i) => ({ name: "Unseated " + i, branch: "Noida" })),
    active_people: 445,
    plans: opt.sentinel ? { "POS-001": { note: "PLAN-SNTL", set_by: "WHO-SNTL", reason: "REASON-SNTL" } } : undefined,
  };
}

function owner() {
  const all = dtc90();
  const rows = all.rows.filter((r) => r.branch === "Pitampura");
  return { rows, as_at: all.as_at, may_see_leaving: false, may_edit: false,
           unseated: Array.from({ length: 35 }, (_, i) => ({ name: "Unseated " + i, branch: "Pitampura" })),
           active_people: 69 };
}

function group() {
  const base = { reports_to_title: "Store Manager", designation: "Cashier", grade: "", company: "Sample Fashions Pvt Ltd",
                 status: "Active", key: false, seats: 1, opening: null, leaving_on: null };
  const p = (n) => ({ employee: "E-" + n, name: n, weight: 100, covering: false, leaving: null });
  const rows = [Object.assign({}, base, { id: "G-TOP", title: "Store Manager", reports_to: "", branch: "Noida", department: "Sales", designation: "Store Manager", people: [p("Gita Top")] })];
  [["G-1", [p("Asha One"), p("Babu Two")]], ["G-2", [p("Chand Three")]], ["G-3", []]].forEach(([id, people]) =>
    rows.push(Object.assign({}, base, { id, title: "Cashier", reports_to: "G-TOP", branch: "Noida", department: "Sales", people, filled: people.length, open: people.length ? 0 : 1 })));
  ["G-4", "G-5", "G-6"].forEach((id) =>
    rows.push(Object.assign({}, base, { id, title: "Cashier", reports_to: "G-TOP", branch: "Delhi", department: "Sales", people: [], filled: 0, open: 1 })));
  rows.find((r) => r.id === "G-3").opening = "HR-OPN-1";
  rows.find((r) => r.id === "G-5").opening = "HR-OPN-2";
  rows.find((r) => r.id === "G-6").opening = "HR-OPN-3";
  return { rows, as_at: "2026-10-24", may_see_leaving: true, unseated: [], active_people: 4 };
}

function noLeave(forceLeaving) {
  const d = dtc90();
  d.may_see_leaving = false;
  d.rows.forEach((r) => { r.leaving_on = null; r.people.forEach((p) => { p.leaving = null; }); });
  if (forceLeaving) d.rows.find((r) => r.title === "Security Guard").people[0].leaving = "2099-01-01";
  return d;
}

/* A manager who is sent leaving dates for their own reports (may_see_leaving
   true) but is not HR: the server sends no "in no seat" list (the key is
   absent), which is how the page knows. Surbhi, 25 Oct 2026: the HR copy is
   for HR only, so this reader never gets the tick. */
function manager() {
  const d = dtc90();
  delete d.unseated; delete d.active_people;
  d.may_edit = false; d.may_delete = false;
  return d;
}

/* n copies of DTC's 89 seats under one top: 10x is 891 seats. */
function scaled(n) {
  const one = dtc90();
  const top = one.rows[0], rows = [top];
  for (let k = 0; k < n; k++) {
    one.rows.slice(1).forEach((r) => {
      const c = JSON.parse(JSON.stringify(r));
      c.id = r.id + "-" + k;
      c.title = r.title + (k ? " " + (k + 1) : "");
      c.reports_to = r.reports_to === top.id ? top.id : r.reports_to + "-" + k;
      rows.push(c);
    });
  }
  return Object.assign({}, one, { rows });
}

module.exports = { dtc90, owner, group, noLeave, manager, scaled };
