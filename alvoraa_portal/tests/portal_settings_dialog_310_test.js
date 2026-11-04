/* The one settings dialog, overhauled: ALV-310 (the table), ALV-305 (the raw
   database column names) and ALV-304 (the settings that could not be set).
   Driven in jsdom against the real page, the real portal.js and the real
   panels.css. The server is a stub, and every save is checked by WHAT IT SENDS
   rather than by what it draws.

   Pin tests, so a bad merge that drops one fails here by name:

     - **the plain words, and the VISIBLE text, not the hidden attribute.**
       ALV-305 shipped because the only test read `data-ocs-v`, which
       legitimately is `cell_number`, so it passed while the screen was wrong
     - **the preview too.** `ocsPreview()` had the same bug separately: it fell
       back to the Positions word map, which holds none of the six joiner
       fields, so fixing the rows did not fix the preview
     - **the keyboard focus survives a tick.** This is ALV-310's real defect:
       the second tick existed only on a ticked row, so every tick rewrote the
       whole list and the focus landed on `<body>` (WCAG 2.2 AA 3.2.2)
     - **one decision, one column, with a sticky heading**, on all four lists -
       two columns on the two that have a second decision, one on the other two
     - every box's accessible name carries the row AND the column
     - **one word per idea.** HR reads "Must fill in", the joiner reads
       "Needed", and the word "compulsory" appears on no screen
     - the footer stacks in DOM order on a phone: `order:-1` is gone
     - **the four values HR could never set can now be set**, through the
       endpoint that already existed, and only the ones that changed are sent
     - **the card never prints a retention period nobody chose.** The invite
       gate reads the value raw on purpose; printing our own default as though
       it were the employer's decision is the screen contradicting the gate

   Run: node alvoraa_portal/tests/portal_settings_dialog_310_test.js \
          alvoraa_portal/alvoraa_portal/www/hrms-employee.html */
const { JSDOM } = require("jsdom");
const { readPortalSource } = require("../../scripts/lib/portal_source");

const html = readPortalSource(process.argv[2]);
let pass = 0, fail = 0;
const ok = m => { pass++; console.log("  PASS  " + m); };
const bad = m => { fail++; console.log("  FAIL  " + m); };
const yes = (cond, m, detail) => (cond ? ok(m) : bad(m + (detail ? ": " + detail : "")));
const no = (cond, m, detail) => yes(!cond, m, detail);
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
        const body = { exc_type: "ValidationError",
          _server_messages: JSON.stringify([JSON.stringify({ message: h.refuse })]) };
        return Promise.resolve({ ok: false, status: 417, json: () => Promise.resolve(body) });
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
const change = el => el.dispatchEvent(new window.Event("change", { bubbles: true }));
const callsTo = n => CALLS.filter(c => c.name === n);
const text = el => (el ? el.textContent.replace(/\s+/g, " ").trim() : "");

/* THE SIX, as the server sends them: database column names, which is correct -
   they are what gets saved. The screen must never show one. */
const SIX = ["cell_number", "personal_email", "current_address",
             "person_to_be_contacted", "relation", "emergency_phone_number"];

/* A FUNCTION, not an object: the screen holds on to what the server handed it. */
const SETTINGS = (over) => Object.assign({
  profile_fields: ["designation"],
  profile_choices: ["designation", "department", "branch"],
  my_profile_fields: ["cell_number"], my_profile_choices: SIX.slice(),
  my_profile_required_fields: ["cell_number"],
  document_types: [], sensitive: [], audience_count: 7,
  audience_roles: ["HR Manager", "System Manager"],
  link_days: 7, not_hired_days: 180, backstop_days: 90, warn_days: 75,
  document_days: 30, joiner_form_on: true, photo_in_emails: false,
  joiner_fields: ["cell_number", "current_address"],
  joiner_required_fields: ["cell_number"],
  joiner_choices: SIX.slice(),
  joiner_required_documents: [], notice_text: "Our own words.",
  hr_contact_phone: "+91 98100 00079", hr_contact_email: "",
  joiner_not_ready: [], joiner_not_ready_keys: [],
  last_changed: { by: "Kiran Sandhu", on: "2026-11-01 10:00:00" },
}, over || {});

const DOC_TYPES = {
  types: [
    { name: "Aadhaar card", category: "Identity", collect_from: "HR", given: 41,
      mandatory: true, sensitive: true },
    { name: "PAN card", category: "Identity", collect_from: "HR", given: 38,
      mandatory: true, sensitive: true },
    { name: "Highest education certificate", category: "Education",
      collect_from: "HR", given: 3, mandatory: false, sensitive: false },
  ],
  sensitive_categories: ["Identity", "Statutory", "Verification", "Employment", "Address"],
};

async function card(over) {
  ROUTES = Object.assign({}, BASE, {
    get_people_settings: { ok: SETTINGS(over) },
    get_document_type_choices: { ok: DOC_TYPES },
  });
  CALLS.length = 0;
  window.ocsLoad();
  await settle(140);
}

async function picker(which, over) {
  /* One dialog at a time, as a person would have it: the modal covers the card,
     so there is no way to open a second from a keyboard or a mouse. */
  const open = doc.querySelector('.ocs-dlg [data-ocs="cancel"]');
  if (open) { click(open); await settle(30); }
  await card(over);
  click($("ocs-body").querySelector('[data-ocs="' + which + '"]'));
  await settle(120);
}

const headings = () => [...doc.querySelectorAll("#ocs-dlg-bd thead th")]
  .map(th => text(th));
const rowNames = () => [...doc.querySelectorAll("#ocs-dlg-bd tbody tr")]
  .filter(r => r.querySelector("[data-ocs-v]"))
  /* The first text node: the name itself, without the hint line under it. */
  .map(r => String(r.querySelector(".oc2-nm").firstChild.textContent).trim());
const dlgText = () => text(doc.querySelector(".ocs-dlg"));

(async () => {
  await settle(400);
  for (const fn of ["ocsLoad", "ocsPick", "ocsRows", "ocsSave", "ocsPreview",
                    "ocsTold", "ocsToldSave"]) {
    if (typeof window[fn] !== "function") {
      bad(fn + " is not reachable on the page"); process.exit(1);
    }
  }

  // ── 1 · ALV-305, in the rows and in the VISIBLE text ──────────────────
  await picker("pick-joiner");
  const names = rowNames();
  eq(names.slice(0, 2), ["Mobile number", "Personal email"],
     "ALV-305: the joiner picker shows the plain words");
  for (const raw of SIX) {
    no(dlgText().indexOf(raw) >= 0,
       "ALV-305: and never the database column " + raw + " anywhere a person "
       + "can read it", dlgText().slice(0, 160));
  }
  /* The attribute still carries the column name - that is what gets saved, and
     it is why the old test passed while the screen was wrong. */
  eq([...doc.querySelectorAll("#ocs-dlg-bd [data-ocs-v]")]
       .map(i => i.getAttribute("data-ocs-v")), SIX,
     "and the hidden value is still the column name, because that is what is saved");
  yes(/The joiner reads/.test(dlgText())
      && /Your mobile number/.test(dlgText()),
      "and each joiner row says what the JOINER will actually read", dlgText().slice(0, 200));

  // ── 2 · ALV-310, the table ────────────────────────────────────────────
  eq(headings(), ["Detail", "Asked for", "Must fill in"],
     "ALV-310: one decision per column, each with its own heading");
  const stuck = /\.oc2-tbl thead th\{[^}]*position:sticky/.test(html);
  yes(stuck, "ALV-310 / OCS9: and the heading row sticks, so at 18 rows the "
           + "columns do not lose their meaning half way down");
  const labels = [...doc.querySelectorAll("#ocs-dlg-bd input")]
    .map(i => i.getAttribute("aria-label"));
  yes(labels.every(l => l && / — /.test(l)),
      "ALV-310: every box's accessible name carries the row and the column - a "
      + "column heading alone is not a reliable name on a checkbox", String(labels[0]));
  yes(labels.indexOf("Mobile number — Must fill in") >= 0,
      "for example the mobile number's compulsory box", String(labels.slice(0, 3)));

  /* THE DEFECT. Focus a box, change it, and the focus must still be on it.
     Before the change `ocsRows()` rewrote the whole list on every tick, which
     detached the focused element and threw the focus to <body>. */
  const box = doc.querySelector('#ocs-dlg-bd [data-ocs-v="personal_email"]');
  box.focus();
  box.checked = true;
  change(box);
  await settle(40);
  yes(doc.activeElement === box,
      "ALV-310 / WCAG 2.2 AA 3.2.2: the keyboard focus stays on the box that "
      + "was just pressed - it used to land on <body> after every single tick",
      doc.activeElement && doc.activeElement.tagName);
  yes(box.closest("tr").className === "",
      "and the row it is in stops being the empty-cell row, in place");

  /* Nothing appears or disappears, which is what makes the above true. */
  eq([...doc.querySelectorAll("#ocs-dlg-bd [data-ocs-need]")].length, 6,
     "ALV-310: the second decision's cell is in every row, always");

  // ── 3 · one word per idea ─────────────────────────────────────────────
  no(/compulsory/i.test(dlgText()),
     "ALV-310 / OCS6: the word “compulsory” is on no screen");
  yes(/Must fill in/.test(dlgText()),
      "HR reads “Must fill in”");
  yes(/Needed/.test(dlgText()),
      "and the tie line is the one place the joiner's word appears beside it");
  yes(/must be filled in/.test(text($("ocs-ok"))),
      "ALV-310: and the save button repeats the column words",
      text($("ocs-ok")));
  yes(/^Save/.test(text($("ocs-ok"))),
      "it says Save, not OK", text($("ocs-ok")));

  // ── 4 · the footer, in DOM order ──────────────────────────────────────
  eq([...doc.querySelectorAll(".ocs-ft-b [data-ocs]")].map(b => b.getAttribute("data-ocs")),
     ["preview", "cancel", "ok"],
     "ALV-310 / OCS7: the footer is Preview, Cancel, Save in DOM order");
  /* The rule itself, not a comment that mentions it. */
  no(/^\s*\.ocs-ft-b \[data-ocs="ok"\]\s*\{/m.test(html),
     "ALV-310 / WCAG 1.3.2: and the rule that lifted OK above them on a phone "
     + "is gone, so the visual order is the tab order");
  yes(/Show me the form a joiner fills in/.test(text(doc.querySelector('[data-ocs="preview"]'))),
      "ALV-310 / OCS5: the preview button names the screen it opens - nobody "
      + "“reads” a joining form",
      text(doc.querySelector('[data-ocs="preview"]')));

  // ── 5 · ALV-305's second half: the preview ────────────────────────────
  click(doc.querySelector('[data-ocs="preview"]'));
  await settle(60);
  const sheet = text($("hm-ov"));
  yes(/Your mobile number/.test(sheet),
      "ALV-305: the joiner's preview is in the JOINER's own words", sheet.slice(0, 160));
  for (const raw of SIX) {
    no(sheet.indexOf(raw) >= 0,
       "ALV-305: and the preview shows no database column either (" + raw + ") "
       + "- fixing the rows did not fix this, it was a second fall-through",
       sheet.slice(0, 160));
  }
  yes(/Needed/.test(sheet),
      "and a compulsory question carries the word the joiner will see");
  window.hmCloseSheet(true);

  // ── 6 · the other three lists get the same table ──────────────────────
  await picker("pick-my");
  eq(headings(), ["Detail", "They may change it", "Keep asking"],
     "ALV-310: My Profile's two decisions are columns too, in its own words");
  yes(/never refuses a save/.test(dlgText()),
      "and its lead sentence tells its own truth: keep asking never blocks");
  click(doc.querySelector('[data-ocs="cancel"]'));
  await settle(30);

  await picker("pick-profile");
  eq(headings(), ["Detail", "Shown"],
     "ALV-310: and a one-decision list simply gains a heading on its one column");
  eq([...doc.querySelectorAll("#ocs-dlg-bd [data-ocs-need]")].length, 0,
     "with no second column at all, because nobody fills anything in there");
  click(doc.querySelector('[data-ocs="cancel"]'));
  await settle(30);

  await picker("pick-docs");
  eq(headings(), ["Detail", "Shown"],
     "ALV-310: the document types too");
  eq([...doc.querySelectorAll("#ocs-dlg-bd .oc2-grp td")].map(td => text(td)),
     ["Identity", "Education"],
     "079 / 078: still grouped by category, with the group name above the block");
  yes([...doc.querySelectorAll("#ocs-dlg-bd tbody tr .ocs-cat")].length === 3,
      "and the real category still on every row, so a sensitive type cannot be "
      + "read as an ordinary one because of what it sits next to");
  click(doc.querySelector('[data-ocs="cancel"]'));
  await settle(30);

  // ── 7 · ALV-304: the card stops printing a number nobody chose ─────────
  await card({ joiner_not_ready: ["how long you keep the details of somebody who does not join",
                                  "how long you keep a photograph of an identity card",
                                  "what you tell a joiner before the first question",
                                  "a phone number or email a joiner can reach you on"],
               joiner_not_ready_keys: ["alvoraa_joiner_not_hired_days",
                                       "alvoraa_joiner_document_days",
                                       "alvoraa_joiner_notice_text",
                                       "alvoraa_hr_contact_phone"],
               notice_text: "", hr_contact_phone: "", hr_contact_email: "" });
  const blank = text($("ocs-body"));
  no(/180 days/.test(blank),
     "ALV-304: the card does not print 180 days when nobody has chosen 180 - "
     + "the invite gate reads the value raw on purpose, because a default we "
     + "picked is not a decision the employer made", blank.slice(0, 200));
  no(/30 days/.test(blank),
     "and not 30 days either");
  yes(/is not set yet/.test(blank),
      "it says so instead, as a statement of fact");
  yes(/cannot invite anybody yet/i.test(blank),
      "079 AC-11: and the standing block still names what is missing");

  // ── 8 · ALV-304: the four values can finally be set ───────────────────
  const btn = $("ocs-body").querySelector('[data-ocs="told"]');
  yes(!!btn, "ALV-304: there is a button, inside the block that states the problem");
  yes(/Set what a joiner is told/.test(text(btn)), "named for what it does", text(btn));
  click(btn);
  await settle(60);
  for (const id of ["ocs-told-notice", "ocs-told-nothired", "ocs-told-docdays",
                    "ocs-told-phone", "ocs-told-email"]) {
    yes(!!$(id), "ALV-304: and a field for " + id.replace("ocs-told-", ""));
  }
  /* Every input has a real label tied to it. On a settings screen nobody opens
     twice a year, a placeholder standing in for a label is how a field comes to
     mean whatever the reader guesses. */
  for (const id of ["ocs-told-notice", "ocs-told-nothired", "ocs-told-docdays",
                    "ocs-told-phone", "ocs-told-email"]) {
    const lab = doc.querySelector('label[for="' + id + '"]');
    yes(!!lab && text(lab).length > 10,
        "ALV-304: " + id.replace("ocs-told-", "") + " has a real label, tied to "
        + "it by `for`", lab && text(lab));
  }
  eq([$("ocs-told-nothired").value, $("ocs-told-docdays").value], ["", ""],
     "ALV-304: the two clocks open BLANK when nobody has chosen one - "
     + "prefilling our own default would turn a suggestion into a decision");
  eq([$("ocs-told-nothired").getAttribute("min"), $("ocs-told-nothired").getAttribute("max")],
     ["180", "365"],
     "with counsel's range on the input, so the browser helps - the server still decides");

  $("ocs-told-notice").value = "We ask so we can put you on the payroll.";
  $("ocs-told-nothired").value = "200";
  $("ocs-told-docdays").value = "45";
  $("ocs-told-phone").value = "+91 98100 00304";
  CALLS.length = 0;
  ROUTES.set_people_setting = { ok: { ok: true } };
  click($("ocs-told-ok"));
  await settle(200);
  const sent = callsTo("set_people_setting");
  eq(sent.map(c => c.args.key),
     ["alvoraa_joiner_notice_text", "alvoraa_joiner_not_hired_days",
      "alvoraa_joiner_document_days", "alvoraa_hr_contact_phone"],
     "ALV-304: it SENDS the four values, through the endpoint that already "
     + "existed - and not the email, which nobody typed");
  eq(sent.map(c => c.args.value),
     ["We ask so we can put you on the payroll.", "200", "45", "+91 98100 00304"],
     "and it sends what was typed");
  yes(callsTo("get_people_settings").length === 1,
      "ALV-304: afterwards the card is repainted FROM THE SERVER, never from "
      + "what was typed - the block must not say ready because a browser thinks so");
  no(!!doc.querySelector(".ocs-dlg"), "and the dialog closes on success");

  // ── 9 · ALV-304: the server's refusal reaches the person ──────────────
  await card({ joiner_not_ready: ["how long you keep a photograph of an identity card"],
               joiner_not_ready_keys: ["alvoraa_joiner_document_days"] });
  click($("ocs-body").querySelector('[data-ocs="told"]'));
  await settle(60);
  $("ocs-told-docdays").value = "4000";
  CALLS.length = 0;
  ROUTES.set_people_setting = { refuse: "Give a number of days between 30 and 60." };
  click($("ocs-told-ok"));
  await settle(200);
  yes(!!doc.querySelector(".ocs-dlg"),
      "ALV-304: a refused value leaves the dialog open with what was typed still in it");
  eq($("ocs-told-docdays").value, "4000", "nothing is thrown away");
  yes(/between 30 and 60/.test(text($("ocs-told-sum"))),
      "and the SERVER's own sentence is what the person reads - never “check "
      + "your connection”", text($("ocs-told-sum")));
  yes(doc.activeElement === $("ocs-told-docdays"),
      "with the focus put on the field the server refused");
  yes($("ocs-told-ok").disabled === false,
      "and the save button works again, so it can be corrected and sent");

  console.log(`\n### ALV-310 / 305 / 304 settings dialog DOM test: ${pass} passed, ${fail} failed`);
  process.exit(fail ? 1 : 0);
})();
