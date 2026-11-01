/* Slice 079 in the browser: My profile's "Needed" marks and its two columns,
   and the settings card's fourth picker - driven in jsdom against the real page
   and the real portal.js. The server is a stub, and every save is checked by
   WHAT IT SENDS rather than by what it draws.

   Pin tests, so a bad merge that drops one fails here by name:

     - **a save still goes through with something still missing.** Decision 3,
       and the reason is the whole point: blocking would mean somebody with no
       permanent address could never change anything on that page again - not
       even their own phone number - and their only way out is a call to HR
     - the word is **Needed**, on a chip, with `aria-required` and NOT
       `required` - so neither the server nor the browser refuses the form - and
       there is no red border, because nothing here is invalid
     - the standing amber block names what is missing on EVERY visit, and names
       what is missing NOW rather than what was missing before the save
     - **two columns, in source order**: details, then documents, then password.
       There is no `order:` override, so the reflow order is the DOM order
     - the joiner picker offers the SIX the code allows, not the sixteen the
       prototype drew - the extra ten included bank account and IFSC
     - the "must fill in" tick exists only on a ticked row, and unticking the
       row takes it with it
     - the picker saves ASKED first and REQUIRED second, because a detail
       nobody is asked for cannot be compulsory and the setter refuses it
     - HR is told plainly when the employer has not set its own values yet

   Run: node alvoraa_portal/tests/portal_joiner_079_test.js \
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
const callsTo = n => CALLS.filter(c => c.name === n);
const text = el => (el ? el.textContent.replace(/\s+/g, " ").trim() : "");

/* A FUNCTION, not an object: the screen holds on to what the server handed it
   and writes back onto it after a save, which quietly mutated a shared fixture
   the last time this was a plain object. */
const PROFILE = () => ({
  employee: "HR-EMP-079", employee_name: "Kiran Sandhu", image: null, thumb: null,
  fields: [
    /* HR asks for all three and keeps asking for two of them. The mobile number
       is filled in; the other two are not - so one mark is satisfied and one is
       not, which is the only shape that proves the mark follows the VALUE and
       not the tick. */
    { fieldname: "cell_number", value: "+91 98100 00079", needed: true },
    { fieldname: "current_address", value: "", needed: true },
    { fieldname: "personal_email", value: "", needed: false },
  ],
  password_last_set: "2026-10-12",
});

const SETTINGS = () => ({
  profile_fields: [], profile_choices: ["designation", "department"],
  my_profile_fields: ["cell_number"], my_profile_choices: [
    "cell_number", "personal_email", "current_address",
    "person_to_be_contacted", "relation", "emergency_phone_number"],
  my_profile_required_fields: [],
  document_types: [], sensitive: [], audience_count: 4,
  audience_roles: ["HR Manager", "System Manager"],
  link_days: 7, not_hired_days: 180, backstop_days: 90, warn_days: 75,
  document_days: 30, joiner_form_on: true, photo_in_emails: false,
  joiner_fields: ["cell_number", "current_address"],
  joiner_required_fields: ["cell_number"],
  /* THE SIX. The prototype drew sixteen rows, including bank account number and
     IFSC code, and the drawing was wrong, not the code. */
  joiner_choices: ["cell_number", "personal_email", "current_address",
                   "person_to_be_contacted", "relation", "emergency_phone_number"],
  joiner_required_documents: [], notice_text: "Our own words.",
  hr_contact_phone: "+91 98100 00079", hr_contact_email: "",
  joiner_not_ready: [],
  last_changed: { by: "Kiran Sandhu", on: "2026-11-01 10:00:00" },
});

async function openMyProfile(routes) {
  ROUTES = Object.assign({}, BASE, routes);
  CALLS.length = 0;
  window.switchPanel("my-profile", null);
  await settle(150);
}

(async () => {
  await settle(400);
  for (const fn of ["mypLoad", "mypPaintDetails", "ocsLoad", "ocsPick", "ocsSave"]) {
    if (typeof window[fn] !== "function") {
      bad(fn + " is not reachable on the page"); process.exit(1);
    }
  }

  // ── 1 · the Needed marks ────────────────────────────────────────────────
  await openMyProfile({ get_my_profile: { ok: PROFILE() },
    birthdays_this_month: { ok: { on: 0 } } });

  const det = $("myp-det");
  const chips = det.querySelectorAll(".myp-need");
  eq(chips.length, 2, "079 AC-101: a chip on each detail HR keeps asking for");
  yes([...chips].every(c => /Needed/.test(text(c))),
      "079 AC-37: the word is Needed - never “mandatory” on one screen "
      + "and “required” on the other, because the same person meets "
      + "both inside a week");

  const needed = det.querySelector("#myp-f-current_address");
  const satisfied = det.querySelector("#myp-f-cell_number");
  const not = det.querySelector("#myp-f-personal_email");
  yes(needed && needed.getAttribute("aria-required") === "true",
      "079 AC-37: a needed field carries aria-required");
  yes(needed && !needed.hasAttribute("required"),
      "079 AC-100: and NOT `required` - the browser must not refuse the form "
      + "either, because the save always goes through");
  yes(not && !not.hasAttribute("aria-required"),
      "a detail nobody is chasing carries no mark");
  yes(satisfied && satisfied.getAttribute("aria-required") === "true",
      "a filled-in needed detail keeps its mark, because the tick is HR's and "
      + "does not switch itself off");
  yes(!det.querySelector('[aria-invalid="true"]'),
      "079 AC-102: nothing is marked invalid. It is not wrong - it is simply "
      + "not filled in yet, and the “blocked save” state was deleted "
      + "from the prototype rather than parked beside it");

  const block = det.querySelector(".myp-needed-block");
  yes(!!block, "079 AC-101: a standing amber block, on every visit");
  const said = text(block);
  yes(/still needs/i.test(said) && /Where you live now/i.test(said),
      "it names what is missing, in words a person can act on", said);
  yes(!/mobile/i.test(said.replace(/Mobile number/g, "")) || !/Mobile number/.test(said),
      "and not what is already filled in");
  yes(/your own record, so you can change anything here and save as you go/i.test(said),
      "079 AC-101: with the one positive sentence of reason", said);
  yes(!/joining form|joiner/i.test(said),
      "079 `01b` §8: and it does NOT compare itself to the joiner's form - "
      + "that would ask most readers to remember a form they never saw", said);

  // ── 2 · the save goes through anyway ───────────────────────────────────
  CALLS.length = 0;
  ROUTES.save_my_profile = { ok: { saved: 1, fields: ["cell_number"] } };
  satisfied.value = "+91 98100 11111";
  click(det.querySelector('[data-myp="save"]'));
  await settle(120);
  const sent = callsTo("save_my_profile")[0];
  yes(!!sent, "079 AC-100: pressing Save calls the endpoint even with a needed "
      + "detail still empty");
  if (sent) {
    const values = JSON.parse(sent.args.values);
    eq(values.cell_number, "+91 98100 11111",
       "and it sends the changed number");
    yes("current_address" in values,
        "with the empty one sent as empty rather than withheld - the server "
        + "decides what is missing, and it refuses nothing");
  }
  const after = $("myp-det").querySelector(".myp-needed-block");
  yes(!!after, "079 AC-101: and the block is redrawn after the save, so it says "
      + "what is missing NOW rather than what was missing before");

  // ── 3 · two columns, in source order ──────────────────────────────────
  const grid = doc.querySelector("#panel-my-profile .myp-two-up");
  yes(!!grid, "079 AC-108: My profile draws a two-column grid");
  if (grid) {
    const kids = [...grid.children];
    eq(kids.map(k => k.id || k.className), ["myp-det", "myp-stack"],
       "079 AC-108: Your details on the left, a stack on the right");
    const stack = grid.querySelector(".myp-stack");
    const inStack = [...stack.children].map(k => k.id);
    eq(inStack, ["my-docs-card", "myp-pw"],
       "079 AC-108: documents above the password, inside the one grid cell");
    /* The reflow order IS the DOM order. A CSS `order` that disagreed with the
       DOM would be an accessibility fault waiting to happen, so there must not
       be one. */
    const pic = $("myp-pic");
    yes(pic && (pic.compareDocumentPosition(grid)
                & window.Node.DOCUMENT_POSITION_FOLLOWING),
        "079 AC-109: the picture card stays above the grid - it is a banner, "
        + "not a column of fields");
    const pw = $("myp-pw");
    yes(pw && (grid.querySelector("#my-docs-card")
               .compareDocumentPosition(pw)
               & window.Node.DOCUMENT_POSITION_FOLLOWING),
        "079 AC-109: and the one-column reflow order is details, documents, "
        + "password - in source order, with no `order:` override");
  }

  // ── 4 · the settings card's fourth picker ─────────────────────────────
  ROUTES = Object.assign({}, BASE, { get_people_settings: { ok: SETTINGS() } });
  CALLS.length = 0;
  window.ocsLoad();
  await settle(120);
  const body = $("ocs-body");
  yes(!!body && /new joiner is asked for/i.test(text(body)),
      "079 AC-104: the card has a joiner section");
  const joinerSaid = text(body);
  yes(/180 days/.test(joinerSaid) && /30 days/.test(joinerSaid),
      "079 AC-92: both of counsel's periods, separately - one sentence covering "
      + "both would be wrong about one of them", joinerSaid);

  const open = body.querySelector('[data-ocs="pick-joiner"]');
  yes(!!open, "and a button that opens the picker");
  click(open);
  await settle(80);
  const rows = [...doc.querySelectorAll("#ocs-dlg-bd [data-ocs-v]")]
    .map(i => i.getAttribute("data-ocs-v"));
  eq(rows, ["cell_number", "personal_email", "current_address",
            "person_to_be_contacted", "relation", "emergency_phone_number"],
     "079 AC-104 / decision 6b: the picker offers the SIX the code allows");
  for (const banned of ["bank_ac_no", "ifsc_code", "date_of_birth",
                        "permanent_address"]) {
    yes(rows.indexOf(banned) < 0,
        "and not " + banned + " - the prototype drew it and the drawing was "
        + "wrong: self-service write on a bank account is how payroll fraud "
        + "happens");
  }

  /* The second tick exists only on a ticked row. */
  const needTicks = [...doc.querySelectorAll("#ocs-dlg-bd [data-ocs-need]")]
    .map(i => i.getAttribute("data-ocs-need"));
  eq(needTicks, ["cell_number", "current_address"],
     "079 §17.2: the “must fill in” tick exists only on a ticked "
     + "row");

  /* Unticking the row takes its "must fill in" tick with it - a compulsory
     detail nobody is asked for is a setting that cannot mean anything, and the
     setter refuses it. */
  const row = doc.querySelector('#ocs-dlg-bd [data-ocs-v="cell_number"]');
  row.checked = false;
  row.dispatchEvent(new window.Event("change", { bubbles: true }));
  await settle(40);
  const left = [...doc.querySelectorAll("#ocs-dlg-bd [data-ocs-need]")]
    .map(i => i.getAttribute("data-ocs-need"));
  eq(left, ["current_address"],
     "079 AC-40: unticking a detail takes its compulsory mark with it");

  /* OK sends ASKED first and REQUIRED second, and the order matters: the setter
     refuses a name that is compulsory but not being asked for, so sending them
     the other way round would refuse a legitimate save. */
  /* And tick the survivor's "must fill in" box, so the SECOND key is proved to
     carry a value rather than only to be sent. Without this the fixture's only
     compulsory detail was the one we just unticked, and the assertion below
     would be satisfied by an empty string. */
  const needBox = doc.querySelector('#ocs-dlg-bd [data-ocs-need="current_address"]');
  yes(!!needBox, "the survivor still offers its compulsory tick");
  needBox.checked = true;
  needBox.dispatchEvent(new window.Event("change", { bubbles: true }));
  await settle(40);

  CALLS.length = 0;
  ROUTES.set_people_setting = { ok: { ok: true } };
  click($("ocs-ok"));
  await settle(150);
  const saves = callsTo("set_people_setting").map(c => c.args.key);
  eq(saves, ["alvoraa_joiner_fields", "alvoraa_joiner_required_fields"],
     "079 AC-40: the picker saves what is asked FIRST and what is compulsory "
     + "SECOND");
  const saved = callsTo("set_people_setting");
  if (saved.length === 2) {
    eq(saved[0].args.value, "current_address", "the remaining ticked detail");
    eq(saved[1].args.value, "current_address", "and it is the compulsory one");
  }

  // ── 5 · HR is told when the employer has not set its own values ────────
  const notReady = Object.assign(SETTINGS(), {
    joiner_not_ready: ["how long you keep a photograph of an identity card",
                       "what you tell a joiner before the first question"],
    notice_text: "",
  });
  ROUTES = Object.assign({}, BASE, { get_people_settings: { ok: notReady } });
  window.ocsLoad();
  await settle(120);
  const warned = text($("ocs-body"));
  yes(/cannot invite anybody yet/i.test(warned),
      "079 AC-11: the card says so plainly, on the screen that can fix it");
  yes(/photograph of an identity card/.test(warned)
      && /before the first question/.test(warned),
      "and names which of them are missing", warned);
  yes(/your own words are not set yet/i.test(warned),
      "079 AC-111: no words, no form - said as a fact rather than as an error");

  console.log(`\n### 079 joiner and profile DOM test: ${pass} passed, ${fail} failed`);
  process.exit(fail ? 1 : 0);
})();
