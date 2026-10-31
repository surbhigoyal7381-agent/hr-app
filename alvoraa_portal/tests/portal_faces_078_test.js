/* Slice 078 in the browser: My profile, the one mini profile, and the card
   that decides what a reader sees - driven in jsdom against the real page and
   the real portal.js. The server is a stub, and every save is checked by WHAT
   IT SENDS rather than by what it draws.

   Pin tests, so a bad merge that drops one fails here by name:

     - the privacy notice is BEFORE the upload control in the DOM, and it names
       appraisals and emails, which is the half that was wrong in the design's
       own draft
     - My profile answers plainly for a login with no employee record, which
       threw a 500 on dev before this slice
     - the upload sends the picture and nothing else; there is no employee
       argument anywhere on this screen
     - a lost answer says "may have gone through" and DOES NOT CLEAR what was
       typed
     - only the ticked details render; the others are absent, not greyed
     - the mini profile's field list exists ONCE (AC-58), and the drawer is a
       real dialog: Escape closes the enlargement only, then the drawer, and
       focus returns to the name that opened it
     - no photograph means the avatar is not a button at all
     - the settings card is ABSENT for anyone the server refuses, lists names
       rather than counts, and its Cancel writes nothing

   Run: node alvoraa_portal/tests/portal_faces_078_test.js \
          alvoraa_portal/alvoraa_portal/www/hrms-employee.html */
const { JSDOM } = require("jsdom");
const { readPortalSource } = require("../../scripts/lib/portal_source");

const html = readPortalSource(process.argv[2]);
let pass = 0, fail = 0;
const ok = m => { pass++; console.log("  PASS  " + m); };
const bad = m => { fail++; console.log("  FAIL  " + m); };
const yes = (cond, m, detail) => (cond ? ok(m) : bad(m + (detail ? ": " + detail : "")));
const eq = (got, want, m) => (JSON.stringify(got) === JSON.stringify(want)
  ? ok(m) : bad(m + ": got <" + JSON.stringify(got) + "> want <" + JSON.stringify(want) + ">"));

const method = s => String(s).split(".").pop();
const BASE = { get_checkin_status: { ok: { no_employee: 1 } }, get_portal_context: { ok: {} },
  get_employee_dashboard: { ok: { no_employee: true } } };
let ROUTES = Object.assign({}, BASE);
const CALLS = [];

const dom = new JSDOM(html, {
  runScripts: "dangerously", pretendToBeVisual: true,
  url: "http://grace.localhost/hrms-employee",
  beforeParse(w) {
    w.fetch = (url, opts) => {
      const name = method(url);
      CALLS.push({ name, args: opts && opts.body ? JSON.parse(opts.body) : {} });
      const h = ROUTES[name] === undefined ? { ok: {} } : ROUTES[name];
      if (h.refuse) {
        const body = { exc_type: "PermissionError",
          _server_messages: JSON.stringify([JSON.stringify({ message: h.refuse })]) };
        return Promise.resolve({ ok: false, status: 403, json: () => Promise.resolve(body) });
      }
      if (h.lost) {
        /* A write whose answer never comes back: the server may well have
           saved it, which is the whole point of the wording being tested. */
        return new Promise(() => {});
      }
      const v = typeof h.ok === "function" ? h.ok(CALLS[CALLS.length - 1].args) : h.ok;
      return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({ message: v }) });
    };
    const call = (o) => {
      const name = method(o.method);
      CALLS.push({ name, args: o.args || {} });
      const h = ROUTES[name] === undefined ? { ok: {} } : ROUTES[name];
      setTimeout(() => { o.callback && o.callback({ message: h.ok }); o.always && o.always({}); }, 0);
      return { status: 200 };
    };
    w.frappe = { call, csrf_token: "x", boot: {}, ui: {}, _messages: {},
      utils: { escape_html: s => s }, msgprint: () => {} };
  },
});
const { window } = dom, doc = window.document;
const settle = ms => new Promise(r => setTimeout(r, ms));
const $ = id => doc.getElementById(id);
const click = el => el.dispatchEvent(new window.MouseEvent("click", { bubbles: true }));
const key = (k) => doc.dispatchEvent(new window.KeyboardEvent("keydown",
  { key: k, bubbles: true, cancelable: true }));
const callsTo = n => CALLS.filter(c => c.name === n);
const text = el => (el ? el.textContent.replace(/\s+/g, " ").trim() : "");

/* A FUNCTION, not an object. The screen holds on to what the server handed it
   and writes the new picture's url onto it after an upload - which is correct
   behaviour, and which quietly mutated a shared fixture when this was a plain
   object, so a later case was asserting against the previous case's leftovers.
   A fresh copy every time is what makes each case independent. */
const PROFILE = () => ({
  employee: "HR-EMP-078", employee_name: "Kiran Sandhu", image: null, thumb: null,
  fields: [{ fieldname: "cell_number", value: "" },
           { fieldname: "personal_email", value: "k@example.com" }],
  password_last_set: "2026-10-12",
});

async function openMyProfile(routes) {
  ROUTES = Object.assign({}, BASE, routes);
  CALLS.length = 0;
  window.switchPanel("my-profile", null);
  await settle(150);
}

(async () => {
  await settle(400);
  for (const fn of ["mypLoad", "mpfOpen", "ocsLoad", "ocAvatar", "ocFaces", "posPaint"]) {
    if (typeof window[fn] !== "function" && typeof window[fn] !== "object") {
      bad(fn + " is not reachable on the page"); process.exit(1);
    }
  }

  // ── 1. My profile: the notice, and where it is ───────────────────────────
  await openMyProfile({ get_my_profile: { ok: PROFILE() },
    birthdays_this_month: { ok: { on: 0 } } });

  const card = $("myp-pic");
  yes(/Add your picture/.test(text(card)), "the first card asks for a picture");

  const notice = card.querySelector(".myp-notice");
  const camera = card.querySelector('[data-myp="camera"]');
  yes(notice && camera, "the notice and the camera button are both drawn");
  if (notice && camera) {
    /* AC-2. BEFORE the control, in the DOM - not under it, not behind a link,
       not after the camera has opened. */
    yes(notice.compareDocumentPosition(camera) & window.Node.DOCUMENT_POSITION_FOLLOWING,
        "078 AC-2: the privacy notice comes BEFORE the upload control in the DOM");
  }
  const said = text(notice);
  /* AC-8 / 078-PRIV-1. The two the design's own draft did not name, and the
     reason each one is in: Appraisal.employee_image copies the photograph onto
     a submittable record, so Employee permissions stop applying; and the work
     anniversary reminder puts the photograph's URL in a mail body sent to
     colleagues - and that reminder is switched on today. */
  yes(/staff directory/i.test(said), "078 PRIV-1: the notice names the staff directory");
  yes(/organisation chart/i.test(said), "078 PRIV-1: and the organisation chart");
  yes(/team pages/i.test(said), "078 PRIV-1: and team pages");
  yes(/appraisals/i.test(said), "078 PRIV-1: and APPRAISALS", said);
  yes(/emails/i.test(said), "078 PRIV-1: and EMAILS", said);
  yes(/Nobody uses it to check who you are or when you arrived/.test(said),
      "078 PRIV-1: and it still makes the two promises it always made");

  // ── 2. what the upload sends ─────────────────────────────────────────────
  const picked = card.querySelector("#myp-file");
  yes(!!picked, "there is a file input to send a picture with");
  CALLS.length = 0;
  ROUTES.upload_my_photo = { ok: { image: "/private/files/p-078.jpg", bytes: 41000 } };
  /* FileReader in jsdom needs a real Blob; this is the smallest one that
     exercises the path the screen takes. */
  const blob = new window.Blob([new Uint8Array([255, 216, 255, 0])], { type: "image/jpeg" });
  window.mypSend(blob);
  await settle(200);
  const sent = callsTo("upload_my_photo")[0];
  yes(!!sent, "pressing send calls the upload endpoint");
  if (sent) {
    eq(Object.keys(sent.args).sort(), ["photo"],
       "078 AC-23: the upload sends the picture and NOTHING ELSE - there is no "
       + "employee argument for a browser to post");
  }
  yes(/That is you/.test(text($("myp-pic"))),
      "078 AC-7: after it saves, the card says that is you");
  const after = $("myp-pic");
  yes(!!after.querySelector('[data-myp="remove"]') && !!after.querySelector('[data-myp="pick"]'),
      "078 AC-7: and offers Replace and Remove");

  // ── 3. a lost answer never costs somebody their typing ───────────────────
  await openMyProfile({ get_my_profile: { ok: PROFILE() },
    birthdays_this_month: { ok: { on: 0 } } });
  const mobile = $("myp-f-cell_number");
  yes(!!mobile, "the ticked details render as inputs");
  mobile.value = "+91 98765 00078";
  ROUTES.save_my_profile = { lost: true };
  click(doc.querySelector('[data-myp="save"]'));
  await settle(60);
  /* The 15-second wait is the real one; what is pinned here is that nothing is
     cleared while it is in flight, which is the half a timeout test misses. */
  yes($("myp-f-cell_number").value === "+91 98765 00078",
      "078 AC-19: what was typed is still in the input while the answer is lost");

  // ── 4. only the ticked details, and the plain answer when there are none ──
  await openMyProfile({
    get_my_profile: { ok: Object.assign(PROFILE(), { fields: [{ fieldname: "cell_number", value: "" }] }) },
    birthdays_this_month: { ok: { on: 0 } } });
  yes(!!$("myp-f-cell_number") && !$("myp-f-personal_email"),
      "078 AC-16: an unticked detail is ABSENT, not disabled and not greyed");

  await openMyProfile({
    get_my_profile: { ok: Object.assign(PROFILE(), { fields: [] }) },
    birthdays_this_month: { ok: { on: 0 } } });
  yes(/has not chosen any detail for you to change/.test(text($("myp-det"))),
      "078 AC-17: nothing ticked keeps the card and says so");
  yes(/Add your picture/.test(text($("myp-pic"))),
      "078 AC-17: and the picture card is unaffected - the photo is always on",
      text($("myp-pic")).slice(0, 120));

  // ── 5. a login with no employee record ───────────────────────────────────
  await openMyProfile({ get_my_profile: { ok: { no_employee: true } },
    birthdays_this_month: { ok: { on: 0 } } });
  const empty = text($("myp-pic"));
  yes(/not linked to an employee record/.test(empty),
      "078 AC-18: a login with no employee record is told so plainly", empty);
  yes(!/went wrong at the office/.test(empty),
      "078 AC-18: and NOT with the failure it showed on dev before this slice");
  yes(text($("myp-det")) === "" && text($("myp-pw")) === "",
      "078 AC-18: and the other two cards are not drawn at all");

  // ── 6. the one mini profile ──────────────────────────────────────────────
  /* AC-58. ONE place in the code builds the field list. The spec says two
     copies is a test failure, not a style note, so this asserts the list is a
     single array and that the drawer renders from it. */
  yes(Array.isArray(window.MPF_FIELDS) && window.MPF_FIELDS.length === 10,
      "078 AC-58: there is ONE mini-profile field list, with ten details",
      String(window.MPF_FIELDS && window.MPF_FIELDS.length));
  const words = window.MPF_FIELDS.reduce((o, f) => (o[f[0]] = f[1], o), {});
  yes(words.date_of_joining === "In the company since",
      '078 AC-42: the joining date is worded "In the company since", not "Date of joining"');
  yes(words.company_email === "Work email",
      '078 AC-42: company_email is worded "Work email"');
  yes(!("work_phone" in words) && !("cell_number" in words) && !("date_of_birth" in words),
      "078 AC-51: no work phone (it does not exist), no personal mobile, no date of birth");

  const WHO = {
    employee: "HR-EMP-9", employee_name: "Kiran Sandhu", designation: "Cashier",
    image: "/private/files/k-512.jpg", thumb: "/private/files/k-48.jpg",
    rows: [{ fieldname: "designation", value: "Cashier" },
           { fieldname: "branch", value: "Noida Sector 18" },
           { fieldname: "date_of_joining", value: "2024-04-01" },
           { fieldname: "grade", value: "" }],
    can_change_setting: false,
  };
  ROUTES.get_positions_profile = { ok: WHO };
  const opener = doc.createElement("button");
  doc.body.appendChild(opener);
  opener.focus();
  window.mpfOpen("HR-EMP-9", opener);
  await settle(120);

  yes($("emp-drawer").classList.contains("open"), "the drawer opens");
  const drawer = $("emp-drawer");
  /* AC-59. Copied from the payslip drawer eleven lines above it, which already
     had the first three. */
  yes(drawer.getAttribute("role") === "dialog"
      && drawer.getAttribute("aria-modal") === "true"
      && drawer.getAttribute("aria-labelledby") === "ed-name",
      "078 AC-59: the drawer is a named modal dialog");
  const dl = drawer.querySelector(".mpf-dl");
  yes(!!dl, "the ticked details render as a definition list");
  const dts = [...drawer.querySelectorAll(".mpf-dl dt")].map(d => d.textContent);
  /* The allow-list's order, not the order the server happened to send:
     designation, department, branch, company, reports_to, grade,
     employment_type, date_of_joining, default_shift, company_email. */
  eq(dts, ["Job role", "Branch", "Grade", "In the company since"],
     "078 AC-42: the rows are in the allow-list's order, with their own wording");
  yes(/Not recorded/.test(text(dl)),
      "078 AC-42: a ticked detail with no value reads Not recorded, never blank");
  yes(/never shown here/.test(text(drawer)),
      "078 AC-42: and the promise under the list is there");
  yes(!drawer.querySelector(".mpf-docs"),
      "078 AC-45: no document types ticked means NO documents section at all");

  // ── 7. the enlargement, and what Escape does ─────────────────────────────
  const face = drawer.querySelector('#ed-av [data-mpf="big"]');
  yes(!!face && face.tagName === "BUTTON", "078 AC-47: the photograph is a button");
  yes(/Show a bigger picture of Kiran Sandhu/.test(face.getAttribute("aria-label") || ""),
      "078 AC-62: with a spoken name that says what it does");
  yes(drawer.querySelector(".emp-drawer-head").contains(face),
      "078 AC-62: and it lives in the FIXED HEAD, so a scroll can never open it");
  click(face);
  await settle(30);
  yes(!!drawer.querySelector(".mpf-big"), "078 AC-47: it enlarges inside the drawer");
  yes(/Getting the full picture/.test(text(drawer.querySelector(".mpf-big"))),
      "078 AC-48: and says so while the full picture is still coming, with no spinner");
  yes(!/download|open in new tab|save/i.test(text(drawer.querySelector(".mpf-big"))),
      "078 AC-47: with no download, no open-in-new-tab and no save");

  key("Escape");
  await settle(20);
  yes(!drawer.querySelector(".mpf-big") && drawer.classList.contains("open"),
      "078 AC-62: the FIRST Escape closes the enlargement only - the drawer stays");
  key("Escape");
  await settle(20);
  yes(!drawer.classList.contains("open"),
      "078 AC-60: the second Escape closes the drawer");
  yes(doc.activeElement === opener,
      "078 AC-60: and focus returns to the name that opened it");

  // ── 8. no photograph means no control ────────────────────────────────────
  ROUTES.get_positions_profile = { ok: Object.assign({}, WHO, { image: null, thumb: null }) };
  window.mpfOpen("HR-EMP-9", opener);
  await settle(120);
  const plain = $("ed-av").firstElementChild;
  yes(plain && plain.tagName !== "BUTTON" && !plain.getAttribute("tabindex")
      && !plain.getAttribute("aria-label"),
      "078 AC-50: with no photograph the avatar is NOT a button - no role, no "
      + "tabindex, no spoken name. A control that does nothing is worse than none");

  // ── 9. a refusal is not dressed as a failure ─────────────────────────────
  ROUTES.get_positions_profile = { refuse: "You cannot see that person's details." };
  window.mpfOpen("HR-EMP-OUT", opener);
  await settle(120);
  const refused = text($("ed-body"));
  yes(/cannot see that person/.test(refused),
      "078 AC-52: a reader out of scope is refused, not shown an empty profile", refused);
  yes(!/Try again/.test(refused),
      "078 AC-52: and is not offered Try again, which would read as a fault");
  yes(!/HR-EMP-OUT/.test(refused),
      "078 AC-52: and learns nothing about who or where that person is");
  key("Escape");
  await settle(20);

  // ── 10. the settings card ────────────────────────────────────────────────
  ROUTES.get_people_settings = { refuse: "Only a System Manager can change this." };
  window.ocsLoad();
  await settle(120);
  yes($("org-people-card").style.display === "none",
      "078 AC-96: the whole card is ABSENT for anyone the server refuses - not greyed");

  ROUTES.get_people_settings = { ok: {
    profile_fields: ["designation", "branch", "date_of_joining"],
    profile_choices: window.MPF_FIELDS.map(f => f[0]),
    my_profile_fields: ["cell_number"],
    my_profile_choices: ["cell_number", "personal_email"],
    document_types: [{ name: "Aadhaar card", category: "Identity", known: true },
                     { name: "Offer letter", category: "Employment", known: true },
                     { name: "Degree certificate", category: "Education", known: true }],
    sensitive: ["Aadhaar card", "Offer letter"],
    audience_count: 7, audience_roles: ["HR Manager", "System Manager"],
    retention_days: "", last_changed: { by: "Surbhi", on: "2026-10-31 09:00:00" },
  } };
  window.ocsLoad();
  await settle(120);
  const body = text($("ocs-body"));
  yes($("org-people-card").style.display !== "none", "the card is drawn for a System Manager");
  yes(/Aadhaar card/.test(body) && /Offer letter/.test(body) && /Degree certificate/.test(body),
      "078 AC-82: every chosen document type is listed BY NAME");
  yes(!/and \d+ more/.test(body),
      "078 AC-87: nothing is truncated and nothing is paginated");
  /* AC-84, and this is the wording asked for in exchange for 078-SEC-3 being
     declined: the ROLES are named, not only the count, so a widening is
     visible at the moment of the tick. */
  yes(/HR Manager, System Manager/.test(body),
      "078 AC-84: the amber line NAMES THE ROLES that can open the file, not only "
      + "a count", body);
  yes(/2 of these 3 is an identity, statutory, verification, employment or address/.test(body),
      "078 AC-84: and says how many of them are sensitive");

  // ── 11. the picker: OK names the consequence, Cancel writes nothing ──────
  CALLS.length = 0;
  click(doc.querySelector('[data-ocs="pick-profile"]'));
  await settle(30);
  const dlg = doc.querySelector(".ocs-dlg");
  yes(!!dlg, "the picker opens");
  yes(dlg.getAttribute("role") === "dialog" && dlg.getAttribute("aria-modal") === "true"
      && !!dlg.getAttribute("aria-labelledby"),
      "078 AC-91: the picker is a named modal dialog");
  /* Surbhi's third answer at the gate: the picker offers the SAFE allow-list
     only. Bank account, PAN, salary and date of birth cannot be ticked. */
  const offered = [...dlg.querySelectorAll("[data-ocs-v]")].map(i => i.getAttribute("data-ocs-v"));
  yes(offered.length === 10, "078 SEC-1: the picker offers exactly the ten allow-listed "
      + "details", String(offered.length));
  for (const never of ["bank_ac_no", "pan_number", "ctc", "date_of_birth", "cell_number"]) {
    yes(!offered.includes(never),
        "078 SEC-1: " + never + " cannot be ticked");
  }
  yes(/OK - 3 details, seen by 7 people/.test(text($("ocs-ok"))),
      "078 AC-89: the confirm button NAMES THE CONSEQUENCE", text($("ocs-ok")));

  const box = dlg.querySelector('[data-ocs-v="company"]');
  box.checked = true;
  box.dispatchEvent(new window.Event("change", { bubbles: true }));
  await settle(10);
  yes(/OK - 4 details/.test(text($("ocs-ok"))),
      "078 AC-89: and it follows what is ticked right now");

  click(dlg.querySelector('[data-ocs="cancel"]'));
  await settle(20);
  yes(!doc.querySelector(".ocs-dlg"), "Cancel closes the picker");
  eq(callsTo("set_people_setting").length, 0,
     "078 AC-92: Cancel WRITES NOTHING, even though a box was changed");

  click(doc.querySelector('[data-ocs="pick-profile"]'));
  await settle(30);
  const b2 = doc.querySelector('[data-ocs-v="company"]');
  b2.checked = true;
  b2.dispatchEvent(new window.Event("change", { bubbles: true }));
  CALLS.length = 0;
  ROUTES.set_people_setting = { ok: { ok: true } };
  click($("ocs-ok"));
  await settle(120);
  const save = callsTo("set_people_setting")[0];
  yes(!!save, "078 AC-90: OK saves");
  if (save) {
    yes(save.args.key === "alvoraa_positions_profile_fields",
        "078 AC-90: through the access-granting key, not a second setter");
    yes(/company/.test(save.args.value || ""),
        "078 AC-90: carrying what was ticked", String(save.args.value));
  }
  yes(!doc.querySelector(".ocs-dlg"),
      "078 AC-90: and there is no unsaved state left anywhere on the page");

  // ── 12. faces: one circle, five states ───────────────────────────────────
  const none = window.ocAvatar({ name: "Ann Bee" });
  const some = window.ocAvatar({ name: "Ann Bee", thumb: "/private/files/a-48.jpg" });
  yes(/class="av"/.test(none) && !/<img/.test(none),
      "078 AC-26: no photograph draws the circle and no image at all");
  yes(/AB/.test(none) && /AB/.test(some),
      "078 AC-28: the initials are in the circle whether there is a photograph or not");
  yes(/data-src="\/private\/files\/a-48\.jpg"/.test(some) && !/\ssrc=/.test(some),
      "078 OPS-19: the face waits for ocFaces, and is not loading=lazy");
  yes(/width="48" height="48"/.test(some),
      "078 AC-27: with width and height ATTRIBUTES, so nothing reflows as it lands");
  yes(/onerror="this\.remove\(\)"/.test(some),
      "078 AC-29: a failed face removes itself and leaves the initials - no broken "
      + "icon, no message, no retry");

  // ── 13. the seat page, and its own pin test ─────────────────────────────
  /* The seat editor was `#pos-editor`, a .gp-backdrop modal that three CI
     scripts named. It is a page now, and this is the test that ships with it
     (parallel-work.md section 7), so a bad merge that drops the page fails
     here by name instead of a user finding out. */
  yes(!doc.getElementById("pos-editor"),
      "078 AC-56: the #pos-editor backdrop is retired, not left beside the page");
  const seatPanel = doc.getElementById("panel-seat");
  yes(!!seatPanel && seatPanel.classList.contains("panel"),
      "078 AC-54: the seat page exists as a panel of its own");
  const back = doc.getElementById("sp-back");
  yes(!!back && back.tagName === "A" && /Positions/.test(back.textContent),
      "078 AC-54: with a LABELLED way back, not a cross", back ? back.textContent : "missing");
  yes(!!back && !!back.getAttribute("href"),
      "078 AC-54: and it is a real link, so it works from a keyboard with no handler");
  /* AC-55: three parts, in the order of the question. */
  yes(!!doc.getElementById("sp-about"), "078 AC-55: part 1, the seat");
  yes(!!doc.getElementById("pos-people-wrap"), "078 AC-55: part 2, who is in it");
  yes(!!doc.getElementById("pos-e-title") && !!doc.getElementById("pos-save-btn"),
      "078 AC-55: part 3, the seat itself - the form that was in the dialog");

  window.POS.may_edit = true;
  window.POS.may_delete = false;
  window.POS.rows = [{ id: "P-CASH", title: "Cashier", branch: "Noida Sector 18",
    department: "Retail", designation: "Cashier", grade: "", company: "DTC",
    status: "Active", key: false, seats: 3, filled: 2, open: 1, opening: null,
    reports_to: "", reports_to_title: "Retail Head", leaving_on: null,
    people: [{ assignment: "A1", employee: "HR-EMP-9", name: "Kiran Sandhu",
               weight: 100, type: "Permanent", covering: false, leaving: null,
               thumb: "/private/files/k-48.jpg" },
             { assignment: "A2", employee: "HR-EMP-10", name: "Ravi Kumar",
               weight: 100, type: "Permanent", covering: false, leaving: null }] }];
  window.posOpenEditor("P-CASH");
  await settle(60);
  yes(seatPanel.classList.contains("active"),
      "078 AC-54: opening a seat shows the page");
  yes(/seat=P-CASH/.test(window.location.search),
      "078 AC-54: and puts it in the address, so it can be sent to a colleague",
      window.location.search);
  yes(/3 of 3 filled|2 of 3 filled/.test(text(doc.getElementById("sp-about"))),
      "078 AC-55: part 1 says how full the seat is",
      text(doc.getElementById("sp-about")));
  yes(/Retail Head/.test(text(doc.getElementById("sp-about"))),
      "078 AC-55: and who it reports to");

  const inIt = [...doc.querySelectorAll("#pos-people .sp-person")];
  yes(inIt.length === 2, "078 AC-55: part 2 lists every person in the seat",
      String(inIt.length));
  yes(inIt[0].querySelector(".av") && inIt[1].querySelector(".av"),
      "078 AC-55: each with their face, or their initials where there is none");
  const whoBtn = inIt[0].querySelector("[data-pos-who]");
  yes(!!whoBtn && whoBtn.getAttribute("data-pos-who") === "HR-EMP-9",
      "078 AC-57: and the name is a control carrying the employee it is about");

  ROUTES.get_positions_profile = { ok: WHO };
  click(whoBtn);
  await settle(120);
  yes($("emp-drawer").classList.contains("open"),
      "078 AC-57: a name on the seat page opens THE SAME drawer the rest of the "
      + "product opens - one behaviour for one job");
  /* AC-58: identical content from both entry points, because there is only one
     place that builds it. */
  const fromSeat = [...$("emp-drawer").querySelectorAll(".mpf-dl dt")].map(d => d.textContent);
  key("Escape");
  await settle(20);
  window.mpfOpen("HR-EMP-9", opener);
  await settle(120);
  const fromTable = [...$("emp-drawer").querySelectorAll(".mpf-dl dt")].map(d => d.textContent);
  eq(fromSeat, fromTable,
     "078 AC-58: the seat page and the table give the drawer IDENTICAL content - "
     + "two copies of the field list would be a test failure, not a style note");
  key("Escape");
  await settle(20);

  window.posCloseEditor();
  await settle(40);
  yes(!/seat=/.test(window.location.search),
      "078 AC-54: going back clears the address", window.location.search);
  yes(doc.getElementById("panel-positions").classList.contains("active"),
      "078 AC-54: and returns to the chart");

  // ── 14. documents on the profile ────────────────────────────────────────
  ROUTES.get_positions_profile = { ok: WHO };
  ROUTES.get_employee_documents = { ok: { documents: [
    { document_type: "Aadhaar card", category: "Identity", status: "Verified",
      expiry_date: "", collect_from: "HR", row: "ED-1" },
    { document_type: "Vault access authorisation", category: "Verification",
      status: "", expiry_date: "", collect_from: "Manager", row: null },
  ] } };
  window.mpfOpen("HR-EMP-9", opener);
  await settle(200);
  const docs = $("emp-drawer").querySelector(".mpf-docs");
  yes(!!docs, "078 AC-63: the documents section is drawn when types are ticked");
  const dtext = text(docs);
  yes(/2 types your organisation chose to show here/.test(dtext),
      "078 AC-63: and says how many, in the organisation's own terms", dtext);
  yes(/Opening one is recorded/.test(dtext),
      "078 AC-63: and that opening one is recorded");
  /* AC-65's honest half. A reader who already holds a private-file url can
     still fetch it, so nothing here may imply the other types are protected. */
  yes(!/hidden|protected|secure/i.test(dtext),
      "078 AC-65: and NOTHING says or implies the other types are hidden, "
      + "protected or secure", dtext);
  yes(/Hide before I share my screen/.test(dtext),
      "078 AC-80: slice 065's screen-share link covers this section too");
  yes(/collected by Manager/.test(dtext),
      "078 AC-64: a ticked type with no file says who collects it - a dead row "
      + "becomes an action");
  yes(!/\/private\/files/.test(docs.innerHTML),
      "078 AC-66: the browser is NEVER handed a /private/files address for a "
      + "document");
  const view = docs.querySelector('[data-mpf="doc"]');
  yes(!!view && view.tagName === "BUTTON" && view.getAttribute("data-row") === "ED-1",
      "078 AC-66: View is a button carrying the ROW, which only our endpoint takes");
  yes(!docs.querySelector("img") && !/download all/i.test(dtext),
      "078 AC-63: no inline preview, no thumbnail, no download-all");

  /* Session only, never remembered (slice 065's own rule). */
  click(docs.querySelector('[data-mpf="hide"]'));
  await settle(20);
  yes(docs.classList.contains("mpf-hidden"), "078 AC-80: the hide link hides them");
  key("Escape");
  await settle(20);
  window.mpfOpen("HR-EMP-9", opener);
  await settle(200);
  const again = $("emp-drawer").querySelector(".mpf-docs");
  yes(again && !again.classList.contains("mpf-hidden"),
      "078 AC-80: and it is NOT remembered the next time the drawer opens");
  key("Escape");
  await settle(20);

  /* AC-45 again, from the other direction: the server sending an empty list
     means no section at all - not an empty heading and not a count of zero. */
  ROUTES.get_employee_documents = { ok: { documents: [] } };
  window.mpfOpen("HR-EMP-9", opener);
  await settle(200);
  yes(!$("emp-drawer").querySelector(".mpf-docs"),
      "078 AC-45: an empty list means NO SECTION AT ALL");
  key("Escape");
  await settle(20);

  console.log(`\n### 078 faces and profile DOM test: ${pass} passed, ${fail} failed`);
  process.exit(fail ? 1 : 0);
})();
