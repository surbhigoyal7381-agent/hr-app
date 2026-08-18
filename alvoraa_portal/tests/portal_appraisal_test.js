/* Appraisals page: list renders, Open switches to detail, HR-only button is
   gated, and the New Process modal reaches the server. */
const fs = require("fs");
const { JSDOM } = require("jsdom");

const html = fs.readFileSync(process.argv[2], "utf8");
const isHr = process.argv[3] !== "employee";
let pass = 0, fail = 0;
const ok  = m => { pass++; console.log("  PASS  " + m); };
const bad = m => { fail++; console.log("  FAIL  " + m); };

const LIST = {
  is_hr: isHr ? 1 : 0,
  employee_id: "HR-EMP-00005",
  counts: { total: 2, submitted: 1, draft: 1 },
  appraisals: [
    { name: "AP-1", employee: "HR-EMP-00005", employee_name: "Vikram Joshi",
      designation: "Sales Executive", appraisal_cycle: "H2 2026", cycle_status: "In Progress",
      docstatus: 0, status: "Draft", total_score: 3.8, self_score: 0, final_score: 3.8,
      start_date: "2026-07-01", end_date: "2026-12-31", is_own: 1,
      can_review: 0, can_self_assess: 1 },
    { name: "AP-2", employee: "HR-EMP-00004", employee_name: "Priya Mehta",
      designation: "Finance Executive", appraisal_cycle: "H2 2026", cycle_status: "In Progress",
      docstatus: 1, status: "Submitted", total_score: 4.0, self_score: 0, final_score: 4.0,
      start_date: "2026-07-01", end_date: "2026-12-31", is_own: 0,
      can_review: 1, can_self_assess: 0 },
  ],
};
const DETAIL = {
  cycle: { name: "H2 2026", cycle_name: "H2 2026", status: "In Progress",
           start_date: "2026-07-01", end_date: "2026-12-31" },
  appraisal: { name: "AP-2", employee: "HR-EMP-00004", employee_name: "Priya Mehta",
               designation: "Finance Executive", department: "Finance", docstatus: 0,
               total_score: 3.5, self_score: 0, avg_feedback_score: 0, final_score: 3.5,
               reflections: "", goals: [{ kra: "Collection days", per_weightage: 50, score: 3.5, score_earned: 1.75 }],
               kras: [], rate_goals_manually: 1, self_ratings: [],
               is_own: 0, can_review: 1, can_self_assess: 0 },
};

const calls = [];
function reply(url, body) {
  const m = /performance_api\.(\w+)|goals_api\.(\w+)/.exec(url) || [];
  const fn = m[1] || m[2] || "";
  calls.push({ fn, body });
  if (fn === "list_appraisals") return LIST;
  if (fn === "get_appraisal") return DETAIL;
  if (fn === "hr_start_appraisal_process")
    return { cycle: "FY28", message: "Cycle 'FY28' created.", created: [], skipped: [] };
  if (fn === "get_performance_context")
    return { employee_id: "HR-EMP-00005", is_hr: isHr, is_manager: true,
             cycles: [{ name: "H2 2026", cycle_name: "H2 2026", status: "In Progress" }],
             active_cycle: { name: "H2 2026" }, report_count: 1, max_rating: 5 };
  if (fn === "get_performance_tree")
    return { roots: [], unattached_kpis: [], categories: [], employee_id: "HR-EMP-00005",
             is_hr: isHr ? 1 : 0, counts: { objectives: 0, kpis: 0 }, flat_goals: [] };
  return [];
}

const dom = new JSDOM(html, {
  runScripts: "dangerously", pretendToBeVisual: true,
  url: "http://grace.localhost/hrms-employee",
  beforeParse(w) {
    w.fetch = (url, opts) => Promise.resolve({
      ok: true, status: 200,
      json: () => Promise.resolve({ message: reply(String(url), opts && opts.body) }),
      text: () => Promise.resolve(""),
    });
    w.frappe = { csrf_token: "", call: () => Promise.resolve({ message: [] }) };
    w._version_number = "0"; w.confirm = () => true; w.alert = () => {};
  },
});
const { window } = dom, doc = window.document;
const settle = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  await settle(400);
  window.switchPanel("appraisals");
  await settle(300);

  const listBody = doc.getElementById("ap-list-body");
  const rows = listBody.querySelectorAll("tbody tr");
  rows.length === 2 ? ok(`list renders ${rows.length} appraisals`)
                    : bad(`expected 2 rows, got ${rows.length}`);
  listBody.textContent.includes("Vikram Joshi") && listBody.textContent.includes("Priya Mehta")
    ? ok("list shows every appraisal returned") : bad("list is missing employees");
  listBody.textContent.includes("Submitted") && listBody.textContent.includes("Draft")
    ? ok("status badges rendered") : bad("status badges missing");

  const newBtn = doc.getElementById("ap-new-btn");
  if (isHr) {
    newBtn.style.display !== "none" ? ok("HR sees New Appraisal Process")
                                    : bad("HR cannot see the New Process button");
  } else {
    newBtn.style.display === "none" ? ok("non-HR does not see New Appraisal Process")
                                    : bad("non-HR sees the New Process button");
  }

  // Open a specific appraisal
  const openBtn = Array.from(listBody.querySelectorAll("button"))
    .find(b => b.textContent.trim() === "Open");
  openBtn ? ok("each row has an Open action") : bad("no Open button");
  calls.length = 0;
  openBtn.dispatchEvent(new window.MouseEvent("click", { bubbles: true }));
  await settle(300);
  doc.getElementById("ap-detail-view").style.display !== "none" &&
  doc.getElementById("ap-list-view").style.display === "none"
    ? ok("Open switches to the detail view") : bad("detail view did not open");
  const got = calls.find(c => c.fn === "get_appraisal");
  got ? ok("detail fetches that specific appraisal") : bad("get_appraisal not called");
  doc.getElementById("ap-d-title").textContent.includes("Priya")
    ? ok("detail header names the employee") : bad("detail header wrong: " + doc.getElementById("ap-d-title").textContent);
  doc.getElementById("gp-perf-body").textContent.includes("Collection days")
    ? ok("detail renders the KPI rows") : bad("detail missing KPI rows");
  doc.getElementById("gp-self-reflections").disabled
    ? ok("someone else's reflections are read-only") : bad("reflections editable on another's appraisal");
  doc.getElementById("gp-perf-body").textContent.includes("Submit Appraisal")
    ? ok("manager sees Submit on a report's appraisal") : bad("no Submit action for the reviewer");

  window.apBack();
  await settle(300);
  doc.getElementById("ap-list-view").style.display !== "none"
    ? ok("Back returns to the list") : bad("Back did not return to the list");

  // ── Rich text from the desk must not leak markup into the editor ───
  // reflections is a Text Editor field, so desk-written content arrives as
  // Quill HTML. It has to read as prose, not tags.
  {
    const QUILL = '<div class="ql-editor read-mode"><p>I did my best to coordinate ' +
                  'with my team to delivery best result.</p><p>I saved stock wastage by 5%.</p></div>';
    DETAIL.appraisal.reflections = QUILL;
    DETAIL.appraisal.is_own = 1;
    DETAIL.appraisal.can_self_assess = 1;
    window.apOpen("AP-2");
    await settle(300);

    const ta = doc.getElementById("gp-self-reflections");
    if (!ta) { bad("no reflections editor"); }
    else {
      !/<[a-z/][^>]*>/i.test(ta.value)
        ? ok("stored rich text renders as prose, not markup")
        : bad("raw HTML still shown in the editor: " + ta.value.slice(0, 80));
      /ql-editor|read-mode/.test(ta.value)
        ? bad("Quill wrapper classes leaked into the text")
        : ok("Quill wrapper stripped");
      ta.value.includes("I saved stock wastage by 5%.")
        ? ok("the words themselves survive the conversion") : bad("content lost: " + ta.value);
      ta.value.includes("\n")
        ? ok("paragraph breaks become newlines") : bad("paragraphs collapsed into one line");

      // Saving must go back as HTML so the desk renders it too.
      ta.value = "First paragraph.\n\nSecond paragraph.";
      calls.length = 0;
      window.gpSaveReflections("AP-2");
      await settle(250);
      const saved = calls.find(c => c.fn === "save_self_assessment");
      if (!saved) { bad("save_self_assessment not called"); }
      else {
        const sent = JSON.parse(saved.body || "{}");
        /<p>First paragraph\.<\/p>/.test(sent.reflections)
          ? ok("plain text is stored back as HTML paragraphs")
          : bad("stored value not HTML: " + sent.reflections);
        !/<script|onerror=/i.test(sent.reflections)
          ? ok("escaping holds on the way out") : bad("unescaped content in payload");
      }

      // And markup a user types is escaped rather than becoming live HTML.
      ta.value = '<img src=x onerror=alert(1)> plain';
      calls.length = 0;
      window.gpSaveReflections("AP-2");
      await settle(250);
      const s2 = JSON.parse((calls.find(c => c.fn === "save_self_assessment") || {}).body || "{}");
      /&lt;img/.test(s2.reflections || "")
        ? ok("typed markup is escaped, not stored as live HTML")
        : bad("typed markup stored raw: " + (s2.reflections || "").slice(0, 60));
    }
  }

  if (isHr) {
    window.apOpenProcessModal();
    const modal = doc.getElementById("ap-process-modal");
    (modal.classList.contains("open") && window.getComputedStyle(modal).display !== "none")
      ? ok("New Appraisal Process modal opens") : bad("process modal stayed hidden");
    window.apSubmitProcess();
    await settle(100);
    doc.getElementById("ap-process-error").textContent.length
      ? ok("process modal validates required fields") : bad("no validation on empty process form");
    doc.getElementById("ap-p-name").value = "FY28 Review";
    doc.getElementById("ap-p-start").value = "2028-01-01";
    doc.getElementById("ap-p-end").value = "2028-06-30";
    calls.length = 0;
    window.apSubmitProcess();
    await settle(300);
    const started = calls.find(c => c.fn === "hr_start_appraisal_process");
    if (started) {
      const sent = JSON.parse(started.body || "{}");
      (sent.cycle_name === "FY28 Review" && sent.generate === 1)
        ? ok("process creation posts name, dates and generate flag")
        : bad("wrong payload: " + JSON.stringify(sent));
    } else bad("hr_start_appraisal_process not called");
  }

  console.log(`### appraisals DOM test (${isHr ? "HR" : "employee"}): ${pass} passed, ${fail} failed`);
  process.exit(fail ? 1 : 0);
})();
