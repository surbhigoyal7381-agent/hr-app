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
      /* ALV-287: a route that answers with a FILE rather than JSON, the way
         `open_employee_document` does - a Content-Disposition name and a blob
         whose type Frappe's `as_raw` has already guessed from the file name. */
      if (h.file) {
        return Promise.resolve({
          ok: true, status: 200,
          headers: { get: () => 'attachment; filename="' + h.file.name + '"' },
          blob: () => Promise.resolve(new w.Blob([h.file.body || "bytes"],
                                                 { type: h.file.type })),
        });
      }
      const v = typeof h.ok === "function" ? h.ok(CALLS[CALLS.length - 1].args) : h.ok;
      return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({ message: v }) });
    };
    /* jsdom has no object urls at all. A COUNTING stub is the right thing here
       rather than a faithful one: ALV-287's rule is that every url handed out
       is handed back when the thing showing it goes away, and this is what
       makes that observable instead of a promise in a comment. */
    w.URLS = { made: [], live: new Set() };
    w.URL.createObjectURL = (b) => {
      const u = "blob:test/" + (w.URLS.made.length + 1);
      w.URLS.made.push({ url: u, type: (b && b.type) || "" });
      w.URLS.live.add(u);
      return u;
    };
    w.URL.revokeObjectURL = (u) => { w.URLS.live.delete(u); };
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
  yes(/Nobody uses it to check who you are or when you arrived/.test(said),
      "078 PRIV-1: and it still makes the two promises it always made");
  /* EMAILS, and the sentence must say what the ORGANISATION CHOSE rather than
     a fixed claim (counsel, 29 Oct 2026). The fixture above sends no
     `photo_in_emails`, so the notice must say it is NOT in the mail. */
  yes(/not put into the birthday or work anniversary emails/i.test(said),
      "078 PRIV-1: with the setting off, the notice says the picture is NOT in "
      + "those emails", said);
  yes(!/has also chosen to put it into/i.test(said),
      "078 PRIV-1: and does not claim it is");

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
  /* Eleven since slice 080, by Surbhi's decision of 2 November 2026. The pin
     moved with the list rather than being loosened to "at least ten". */
  yes(Array.isArray(window.MPF_FIELDS) && window.MPF_FIELDS.length === 11,
      "078 AC-58 / 080: there is ONE mini-profile field list, with eleven details",
      String(window.MPF_FIELDS && window.MPF_FIELDS.length));
  const words = window.MPF_FIELDS.reduce((o, f) => (o[f[0]] = f[1], o), {});
  yes(words.date_of_joining === "In the company since",
      '078 AC-42: the joining date is worded "In the company since", not "Date of joining"');
  yes(words.company_email === "Work email",
      '078 AC-42: company_email is worded "Work email"');
  /* HER label, word for word - she rejected "Work phone" - which is why this
     one is not reworded the way the two above are. */
  yes(words.alvoraa_alternative_number === "Alternative number",
      '080: the new field is labelled "Alternative number", her words');
  yes(!("work_phone" in words) && !("cell_number" in words) && !("date_of_birth" in words),
      "078 AC-51 / 080: the number is the company's one, never the personal mobile, "
      + "and no date of birth");

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
    /* Slice 079 replaced this card's joiner block - which was facts only,
       because the Web Form owned the joiner's field list - with the fourth
       picker. `retention_days` is gone and these are what it reads now. The
       079 DOM test drives that block; this fixture only has to stop the card
       rendering "undefined days" in the middle of a test about something
       else. */
    joiner_fields: [], joiner_required_fields: [], joiner_choices: [],
    joiner_required_documents: [], joiner_not_ready: [],
    not_hired_days: 180, document_days: 30, notice_text: "Their own words.",
    last_changed: { by: "Surbhi", on: "2026-10-31 09:00:00" },
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
  yes(/2 of these 3 are identity, statutory, verification, employment or address/.test(body),
      "078 AC-84: and says how many of them are sensitive");
  /* The count of people and the ROLES are two clauses now, not one. The old
     sentence read "The 7 people who can open the Positions page - HR Manager,
     System Manager - can open the file", which a reader takes as a list of
     seven followed by two names. Both numbers were right; the sentence was
     not. Surbhi found it on dev's PPJ tenant, 1 Nov 2026. */
  yes(/Today that is 7 people, holding these roles: HR Manager, System Manager/.test(body),
      "078 AC-84: the count of people and the roles read as two plain facts", body);

  /* Counsel's email tick, on the card, and it SENDS only the key and the
     value - the thing the screen draws is not the thing being tested. */
  const mail = $("ocs-mail");
  yes(!!mail && mail.type === "checkbox" && !mail.checked,
      "078 (counsel): the email tick is on the card and starts OFF");
  CALLS.length = 0;
  ROUTES.set_people_setting = { ok: { ok: true } };
  mail.checked = true;
  mail.dispatchEvent(new window.Event("change", { bubbles: true }));
  await settle(120);
  const sent2 = callsTo("set_people_setting")[0];
  yes(!!sent2, "078 (counsel): ticking it saves");
  if (sent2) {
    eq([sent2.args.key, sent2.args.value], ["alvoraa_photo_in_emails", "1"],
       "078 (counsel): sending exactly the key and the value, nothing else");
  }

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
  yes(offered.length === 11, "078 SEC-1 / 080: the picker offers exactly the eleven "
      + "allow-listed details", String(offered.length));
  yes(offered.includes("alvoraa_alternative_number"),
      "080: the alternative number is one of them - tickable, and off until it is ticked");
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
      "078 AC-63 / ALV-287: the LIST itself still has no thumbnail and no "
      + "download-all - the picture opens in .mpf-dv when View is pressed");

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

  // ── 15. AC-47: the enlarged picture is held for the life of the page ────
  /* "Cached for the rest of the session" is built as a JAVASCRIPT hold, not as
     an HTTP cache - private files go out `Cache-Control: no-cache`, so the
     browser would revalidate every single time and no product copy claims
     otherwise. What is pinned here is that a second enlargement of the SAME
     person makes no second request. */
  ROUTES.get_positions_profile = { ok: WHO };
  ROUTES.get_employee_documents = { ok: { documents: [] } };
  /* Count every request the page makes for the 512 px picture. jsdom does not
     fetch an <img> at all, so the observable is the `src` assignment itself. */
  let fullLoads = 0;
  const imgProto = window.HTMLImageElement.prototype;
  const srcDesc = Object.getOwnPropertyDescriptor(imgProto, "src")
    || Object.getOwnPropertyDescriptor(window.Element.prototype, "src");
  Object.defineProperty(imgProto, "src", {
    configurable: true,
    get() { return this.getAttribute("src") || ""; },
    set(v) {
      if (String(v) === WHO.image) fullLoads++;
      this.setAttribute("src", String(v));
      /* jsdom never fires load for a fake url, so stand in for the browser:
         the element is now "complete" as far as the page is concerned. */
      const ev = new window.Event("load");
      setTimeout(() => this.dispatchEvent(ev), 0);
    },
  });

  window.mpfOpen("HR-EMP-9", opener);
  await settle(200);
  click($("emp-drawer").querySelector('#ed-av [data-mpf="big"]'));
  await settle(60);
  yes(fullLoads === 1, "078 AC-47: enlarging asks for the 512 px picture ONCE",
      String(fullLoads));

  /* Close the enlargement and open it again - same person, same page. */
  key("Escape");
  await settle(20);
  click($("emp-drawer").querySelector('#ed-av [data-mpf="big"]'));
  await settle(60);
  yes(fullLoads === 1,
      "078 AC-47: a SECOND enlargement of the same person makes NO second "
      + "request - the loaded element is held for the life of the page",
      String(fullLoads));
  yes(!!$("emp-drawer").querySelector(".mpf-big .mpf-big-f"),
      "078 AC-47: and the full picture is shown, not the blurred copy");

  key("Escape"); await settle(20);
  key("Escape"); await settle(20);
  if (srcDesc) Object.defineProperty(imgProto, "src", srcDesc);

  // ── 16. PRIV-1's notice follows the email setting ───────────────────────
  /* The one failure a privacy notice cannot have is overstating the audience.
     So the email sentence is conditional on what the tenant configured - and
     both halves are asserted, because a notice that is wrong in the OTHER
     direction (claiming mail when there is none) is also wrong. */
  await openMyProfile({ get_my_profile: { ok: Object.assign(PROFILE(), { photo_in_emails: true }) },
    birthdays_this_month: { ok: { on: 0 } } });
  const onSaid = text($("myp-pic").querySelector(".myp-notice"));
  yes(/has also chosen to put it into the birthday and work anniversary emails/i.test(onSaid),
      "078 PRIV-1: with the setting ON, the notice says so plainly", onSaid);
  yes(!/not put into the birthday/i.test(onSaid),
      "078 PRIV-1: and does not also say the opposite");
  /* Everything else in the notice is unconditional - the surfaces that are
     always true stay named whichever way the setting goes. */
  for (const must of ["staff directory", "organisation chart", "team pages", "appraisals"]) {
    yes(onSaid.toLowerCase().includes(must),
        "078 PRIV-1: and still names " + must);
  }

  // ── 17. the four prototype-parity fixes (D-5(c), D-5(d), D-6) ───────────
  /* These four were found by the test report and fixed afterwards, and NONE of
     them had a test of its own - the fix commits changed no DOM test at all.
     A parity fix with no assertion is a parity gap again after the next
     refactor, so each one is pinned here. */

  /* D-5(c). The documents card BELONGS on My profile, not on Home - and this
     is also what makes AC-20 checkable at all, because AC-20 asks for the card
     to be ABSENT when the plan is off, on that page. Asserted by where the
     element sits in the document, not by a class, because the card itself is
     unchanged: only its place moved. */
  {
    const card = $("my-docs-card");
    yes(!!card, "078 D-5(c): the My Documents card is still in the page");
    yes(!!card && !!card.closest("#panel-my-profile"),
        "078 AC-20 / D-5(c): and it now lives on MY PROFILE");
    yes(!!card && !card.closest("#panel-home"),
        "078 D-5(c): and no longer on Home");
    /* The design draws the picture, the details, the documents, the password.
       Compared by document order so a card moved out of sequence fails. */
    const order = ["myp-pic", "myp-det", "my-docs-card", "myp-pw"]
      .map(id => $(id)).filter(Boolean);
    yes(order.length === 4, "078 D-5(c): all four cards are present",
        String(order.length));
    let inOrder = true;
    for (let i = 1; i < order.length; i++) {
      if (!(order[i - 1].compareDocumentPosition(order[i])
            & window.Node.DOCUMENT_POSITION_FOLLOWING)) inOrder = false;
    }
    yes(inOrder,
        "078 D-5(c): in the order 01b 6.1 draws them - picture, details, "
        + "documents, password");
    /* AC-20's own clause, which the report listed as BLOCKED by the parity
       gap: with the plan off nothing fills the card, so it must not be on the
       page as an empty heading. It ships hidden and `loadMyDocuments()` is
       what reveals it - and nothing in this run answered that call. */
    yes(card && (card.style.display === "none"
                 || window.getComputedStyle(card).display === "none"),
        "078 AC-20: and with nothing filling it the card is HIDDEN, not an "
        + "empty heading on My profile", card && card.style.display);
  }

  /* D-6. The laptop footer is Preview, Cancel, OK, so the primary action is on
     the right where it is expected and Cancel is not where OK was drawn. The
     phone lifts OK to the top with one `order` rule rather than a second copy
     of the markup - which is why the DOM order is the laptop's. */
  {
    doc.querySelectorAll(".ocs-dlg").forEach(d => d.remove());
    window.ocsLoad();
    await settle(60);
    const picker = doc.querySelector('[data-ocs="pick-profile"]');
    yes(!!picker, "078 D-6: the picker can be opened");
    if (picker) {
      click(picker);
      await settle(40);
      const row = doc.querySelector(".ocs-ft-b");
      const got = row ? [...row.children].map(b => b.getAttribute("data-ocs")) : [];
      eq(got, ["preview", "cancel", "ok"],
         "078 D-6: the footer's DOM order is Preview, Cancel, OK - the "
         + "primary action is not where Cancel is expected");
      click(doc.querySelector('[data-ocs="cancel"]'));
      await settle(20);
    }
  }

  /* D-5(d). The pointer leaving BOTH the photograph and the enlargement closes
     it; a click PINS it. Before this, brushing past a colleague's photograph
     left their face filling the drawer until somebody pressed Escape - on the
     one screen that also carries "Hide before I share my screen".

     The 260 ms grace period is the engineer's own number and was unmeasured.
     It is MEASURED here: still open well inside it, closed well outside it,
     and cancelled the instant the pointer comes back. The reason it has to
     exist is geometry - `.emp-drawer-head` has 18 px of bottom padding
     between the photo and the enlargement, belonging to neither - so the
     "comes back" case is the one that matters. */
  {
    ROUTES.get_positions_profile = { ok: WHO };
    ROUTES.get_employee_documents = { ok: { documents: [] } };
    const over = (el, from) => el.dispatchEvent(new window.MouseEvent(
      "mouseover", { bubbles: true, relatedTarget: from || null }));
    const out = (el, to) => el.dispatchEvent(new window.MouseEvent(
      "mouseout", { bubbles: true, relatedTarget: to || null }));
    const big = () => $("emp-drawer").querySelector(".mpf-big");

    window.mpfOpen("HR-EMP-9", opener);
    await settle(200);
    const face2 = $("emp-drawer").querySelector('#ed-av [data-mpf="big"]');

    /* a) hovering opens it, and it was already doing that. */
    over(face2);
    await settle(30);
    yes(!!big(), "078 D-5(d): hovering the photograph still enlarges it");

    /* b) the pointer leaving for somewhere else closes it - after the grace,
          not before. Both halves, because a close that is instant is the bug
          the grace period exists to prevent. */
    out(face2, doc.body);
    await settle(120);
    yes(!!big(),
        "078 D-5(d): it is still open 120 ms after the pointer left - the "
        + "grace period is real, so the 18 px of head padding between the "
        + "photo and the picture cannot close it");
    await settle(260);
    yes(!big(),
        "078 D-5(d): and it IS closed ~380 ms after the pointer left, so a "
        + "colleague's face does not stay on screen");
    yes($("emp-drawer").classList.contains("open"),
        "078 D-5(d): the drawer itself stays open - only the picture closed");
    yes(doc.activeElement !== face2,
        "078 AC-60: and a pointer leaving does NOT move focus - a focus ring "
        + "appearing because somebody brushed past is not a choice they made");

    /* c) coming back cancels it. This is the case the geometry demands. */
    over(face2);
    await settle(30);
    yes(!!big(), "the picture is open again");
    out(face2, doc.body);
    await settle(100);
    over(big() || face2);
    await settle(300);
    yes(!!big(),
        "078 D-5(d): the pointer arriving ON THE PICTURE inside the grace "
        + "period cancels the close - reaching for it does not dismiss it");

    /* d) a click pins it, and then the pointer leaving does nothing. */
    click(face2);
    await settle(30);
    yes(!!big(), "078 D-5(d): a click on an open picture PINS it, not closes it");
    out(face2, doc.body);
    await settle(400);
    yes(!!big(),
        "078 D-5(d): and a pinned picture survives the pointer leaving");
    click(face2);
    await settle(30);
    yes(!big(),
        "078 D-5(d): a second click on a PINNED picture closes it - so touch "
        + "is unchanged: one tap opens, a second tap closes");

    key("Escape"); await settle(20);
    key("Escape"); await settle(20);
  }

  // ── 20. ALV-286: the seat tray gets out of the way, and comes back ───────
  /* Her words, testing 080 on dev: "if I click on employee name, the dialog of
     employee profile opens below this dialog. I would expect it to be closed."
     The tray is fixed at z-index 1150 and the drawer is 1101, so the profile
     really did open underneath it. Her decision was not "close and forget" but
     "come back to the list where I left it", which is what the scroll half of
     this case is for. */
  ROUTES.get_positions_profile = { ok: WHO };
  ROUTES.get_employee_documents = { ok: { documents: [] } };
  /* The chart was repainted since section 13, which reloads POS from the
     server stub and empties it, so the seat is put back before the tray is
     asked for one. */
  window.POS.rows = [{ id: "P-CASH", title: "Cashier", branch: "Noida Sector 18",
    department: "Retail", designation: "Cashier", grade: "", company: "DTC",
    status: "Active", key: false, seats: 3, filled: 2, open: 1, opening: null,
    reports_to: "", reports_to_title: "Retail Head", leaving_on: null,
    people: [{ assignment: "A1", employee: "HR-EMP-9", name: "Kiran Sandhu",
               weight: 100, type: "Permanent", covering: false, leaving: null },
             { assignment: "A2", employee: "HR-EMP-10", name: "Ravi Kumar",
               weight: 100, type: "Permanent", covering: false, leaving: null }] }];
  window.posSeatSheet("P-CASH");
  await settle(40);
  const tray = doc.querySelector("#pos-layer .pos-sheet");
  yes(!!tray, "ALV-286: the seat tray opens");
  if (!tray) { console.log("\n### 078: the tray never opened"); process.exit(1); }
  const trayBody = doc.querySelector("#pos-layer .sh-b");
  trayBody.scrollTop = 140;                 /* the reader has scrolled down it */
  const inTray = doc.querySelector('#pos-layer [data-pos-who="HR-EMP-10"]');
  yes(!!inTray, "ALV-286: and the second person in the seat is a name to click",
      String(doc.querySelectorAll("#pos-layer [data-pos-who]").length));

  click(inTray);
  await settle(150);
  yes(!doc.querySelector("#pos-layer .pos-sheet"),
      "ALV-286: clicking a name in the tray CLOSES the tray - the profile is "
      + "not left underneath it");
  yes($("emp-drawer").classList.contains("open"),
      "ALV-286: and the profile is open");

  key("Escape");
  await settle(60);
  const backTray = doc.querySelector("#pos-layer .pos-sheet");
  yes(!!backTray, "ALV-286: closing the profile brings the tray BACK - not "
      + "close and forget");
  yes(window.POS.sheet && window.POS.sheet.id === "P-CASH",
      "ALV-286: the same seat", JSON.stringify(window.POS.sheet));
  eq(doc.querySelector("#pos-layer .sh-b").scrollTop, 140,
     "ALV-286: scrolled where she left it");
  yes(doc.activeElement
      && doc.activeElement.getAttribute
      && doc.activeElement.getAttribute("data-pos-who") === "HR-EMP-10",
      "ALV-286 / AC-60: and focus is on the SAME NAME in the redrawn list, not "
      + "at the top of the page",
      doc.activeElement && doc.activeElement.tagName);

  /* ── 20b. The way back is VISIBLE, and the documents say they are coming ──
     Her words, 3 Nov: "add the loading indicator and a link to go back to the
     previous tray." ALV-286 already put the tray back when the drawer closed,
     but nothing on screen said so, so the only way back was to guess that
     closing would do it. The link is a second, named door onto that same
     close path - it must not grow a restore path of its own. */
  const reopen = doc.querySelector('#pos-layer [data-pos-who="HR-EMP-10"]');
  doc.querySelector("#pos-layer .sh-b").scrollTop = 90;
  click(reopen);
  await settle(150);
  const backEl = $("ed-back");
  yes(backEl && !backEl.hidden, "the way back is shown when the profile was "
      + "opened from a seat tray");
  yes(backEl && /Cashier/.test(backEl.textContent),
      "and it NAMES the seat it goes to, rather than saying just 'Back'",
      backEl && backEl.textContent.trim());

  click(backEl.querySelector('[data-mpf="back"]'));
  await settle(80);
  yes(!!doc.querySelector("#pos-layer .pos-sheet"),
      "clicking it brings the tray back");
  eq(doc.querySelector("#pos-layer .sh-b").scrollTop, 90,
     "and it uses the SAME close path, so the scroll is still restored - no "
     + "second way back to keep in step");
  yes($("ed-back").hidden,
      "the way back goes with the drawer; it is not left behind for the next one");
  window.posCloseSheet(true);
  await settle(20);

  /* The other half of the same hook: the Positions table and the seat page
     have no tray, and must be untouched by any of this. */
  window.mpfOpen("HR-EMP-9", opener);
  await settle(150);
  yes($("emp-drawer").classList.contains("open") && !window.POS.sheet,
      "ALV-286: a name clicked where there is NO tray still just opens the "
      + "profile - the same handler serves the table and the seat page");
  yes($("ed-back").hidden,
      "and there is NO way back offered when there was no tray to go back to");
  /* The hazard the placeholder creates: this person's document list came back
     EMPTY (ROUTES above), which draws no section at all - so the grey bar has
     to be taken away on that path too, or a person with no documents is left
     with a bar that never resolves. */
  yes(!doc.querySelector(".mpf-docs-wait"),
      "the documents placeholder is gone once the answer is in, even when the "
      + "answer is 'none' and no section is drawn");
  /* And that it was ever there. The document list is a SECOND call made after
     the profile has painted, so without this the reader sees nothing at all
     and then a whole section drops in. Checked synchronously, before the
     stubbed answer can land. */
  window.mpfDocsLoad(window.MPF.emp);
  const waiting = doc.querySelector(".mpf-docs-wait");
  yes(!!waiting, "while the documents are coming, the section says so");
  yes(waiting && !!waiting.querySelector(".hm-skel"),
      "with the same grey bar the profile itself waits with, not a new kind "
      + "of spinner");
  await settle(120);
  yes(!doc.querySelector(".mpf-docs-wait"), "and it clears itself afterwards");
  key("Escape");
  await settle(20);

  // ── 21. ALV-287: a document is shown, not saved ─────────────────────────
  /* Her words: "on clicking the documents view button it downloads at present.
     Instead check the feasibility of showing documents in readonly." Then,
     after the trade-offs: "agree, do both image and PDF together in a generous
     size popup."

     THE PDF FRAME HAS NO SANDBOX, AND THAT IS PINNED BELOW ON PURPOSE. A
     first build sandboxed it and shipped pictures only, because Chrome will
     not run its PDF viewer in a sandboxed iframe at ANY value - measured on
     Chrome 157 with `sandbox=""`, `allow-scripts` and
     `allow-scripts allow-same-origin`, all broken, unsandboxed fine, and a
     plain http url behaving identically so it is the sandbox and not the
     blob. Surbhi decided to show it anyway: the sandbox was added on top of
     her decision rather than part of it, Chrome's PDF engine already runs in
     its own locked-down OS process, and the download it replaces leaves an
     Aadhaar card in a Downloads folder, opened in Acrobat, outside the access
     log, outside retention and outside any erasure. The assertion below is
     what stops somebody "tidying up" a missing sandbox attribute and quietly
     turning every PDF back into a download. */
  const downloads = [];
  const realClick = window.HTMLAnchorElement.prototype.click;
  window.HTMLAnchorElement.prototype.click = function () {
    downloads.push({ href: this.href, download: this.getAttribute("download") });
  };

  ROUTES.get_employee_documents = { ok: { documents: [
    { document_type: "Aadhaar card", category: "Identity", status: "Verified",
      expiry_date: "", collect_from: "HR", row: "ED-1" },
  ] } };
  ROUTES.open_employee_document = { file: { name: "aadhaar.jpg", type: "image/jpeg" } };
  window.mpfOpen("HR-EMP-9", opener);
  await settle(200);
  const viewBtn = $("emp-drawer").querySelector('[data-mpf="doc"]');
  yes(!!viewBtn, "ALV-287: the View button is there");
  click(viewBtn);
  await settle(200);

  const dv = doc.querySelector(".mpf-dv");
  yes(!!dv, "ALV-287: a picture document opens a viewer instead of downloading");
  yes(!downloads.length,
      "ALV-287: and NOTHING was saved to the reader's machine",
      JSON.stringify(downloads));
  yes(dv && dv.parentNode === doc.body,
      "ALV-287: the viewer is appended to <body>, not inside the 480 px drawer "
      + "- a scanned page does not fit a drawer, which is why it is not built "
      + "like .mpf-big");
  yes(dv && dv.getAttribute("role") === "dialog"
      && dv.getAttribute("aria-modal") === "true"
      && !!dv.getAttribute("aria-label"),
      "ALV-287: and it is a named modal dialog");
  const shot = dv && dv.querySelector("img");
  yes(!!shot && /^blob:/.test(shot.getAttribute("src") || ""),
      "ALV-287: showing the blob the POST already fetched",
      shot && shot.getAttribute("src"));
  yes(!!shot && !!shot.getAttribute("alt"),
      "ALV-287: with alt text, because an unlabelled image is nothing to a "
      + "screen reader");
  yes(!dv.querySelector("iframe"),
      "ALV-287: a picture is an <img>, not a frame");
  yes(!/\/private\/files/.test(dv.innerHTML),
      "078 AC-66 still holds: no /private/files address reaches the browser");
  const dvText = text(dv);
  /* The wording may promise FRICTION, never protection. A reader can
     screenshot this or right-click the picture, so nothing here may read as a
     guarantee - the same discipline as AC-65's sentence about un-ticked types,
     and the same three words. */
  yes(!/hidden|protected|secure|read.?only/i.test(dvText),
      "ALV-287: the viewer does not say or imply the document is hidden, "
      + "protected, secure or read-only", dvText);
  yes(/Opening it is recorded/.test(dvText) && /can see your screen/.test(dvText),
      "ALV-287: it says what IS true - the opening is recorded, and anyone "
      + "looking at the screen can read it", dvText);
  eq(window.URLS.live.size, 1, "ALV-287: exactly one object url is alive");

  key("Escape");
  await settle(30);
  yes(!doc.querySelector(".mpf-dv"),
      "ALV-287: the FIRST Escape closes the viewer only");
  yes($("emp-drawer").classList.contains("open"),
      "ALV-287: and the profile is still open underneath it");
  eq(window.URLS.live.size, 0,
     "ALV-287: the object url is given back when the viewer closes - no timer, "
     + "because a timer would blank a document somebody was still reading");

  /* And a viewer left open when the profile closes goes with it. */
  click($("emp-drawer").querySelector('[data-mpf="doc"]'));
  await settle(200);
  yes(!!doc.querySelector(".mpf-dv"), "ALV-287: open it again");
  key("Escape"); await settle(30);     /* viewer */
  key("Escape"); await settle(30);     /* drawer */
  yes(!doc.querySelector(".mpf-dv") && !$("emp-drawer").classList.contains("open")
      && window.URLS.live.size === 0,
      "ALV-287: nothing is left on screen and no object url is left behind");

  /* The PDF: the SAME viewer, in a frame with no sandbox. */
  ROUTES.open_employee_document = { file: { name: "contract.pdf", type: "application/pdf" } };
  window.mpfOpen("HR-EMP-9", opener);
  await settle(200);
  downloads.length = 0;
  click($("emp-drawer").querySelector('[data-mpf="doc"]'));
  await settle(200);
  const pdv = doc.querySelector(".mpf-dv");
  yes(!!pdv, "ALV-287: a PDF opens in the viewer too - one viewer for both");
  yes(!downloads.length,
      "ALV-287: and a PDF is no longer saved to the reader's Downloads folder, "
      + "which was the copy outside the access log, outside retention and "
      + "outside any erasure", JSON.stringify(downloads));
  const frame = pdv && pdv.querySelector("iframe");
  yes(!!frame && /^blob:/.test(frame.getAttribute("src") || ""),
      "ALV-287: in an iframe holding the blob the POST already fetched",
      frame && frame.getAttribute("src"));
  yes(!!frame && !frame.hasAttribute("sandbox"),
      "ALV-287: with NO sandbox attribute - her decision, because Chrome runs "
      + "no PDF viewer in a sandboxed frame at any value and the download it "
      + "replaces was the worse exposure. Read mpfShowDoc before changing "
      + "this; it is decided, not forgotten",
      frame && frame.getAttribute("sandbox"));
  yes(!!frame && !!frame.getAttribute("title"),
      "ALV-287: an iframe and not an embed, so the frame has an accessible "
      + "name");
  yes(!!frame && frame.getAttribute("referrerpolicy") === "no-referrer",
      "ALV-287: and it still sends no referrer");
  yes(!/\/private\/files/.test(pdv.innerHTML),
      "078 AC-66 still holds for a PDF: no /private/files address reaches the "
      + "browser");
  const pdvText = text(pdv);
  yes(!/hidden|protected|secure|read.?only/i.test(pdvText),
      "ALV-287: and the PDF gets the SAME wording - friction, never a promise "
      + "of protection", pdvText);
  yes(/Opening it is recorded/.test(pdvText) && /can see your screen/.test(pdvText),
      "ALV-287: the true half is said for a PDF as well", pdvText);
  eq(window.URLS.live.size, 1, "ALV-287: one object url for the PDF too");
  /* The frame has to be REACHABLE from a keyboard. With only the Close button
     in the focus trap's list, a keyboard user could see page one of a contract
     and reach nothing else in it. */
  const able = [...pdv.querySelectorAll(
    'a[href], button:not([disabled]), input:not([disabled]), select, textarea,'
    + ' iframe, [tabindex="0"]')];
  yes(able.indexOf(frame) >= 0,
      "ALV-287: the PDF frame is in the viewer's tab order, so the document "
      + "itself can be reached and scrolled from a keyboard",
      String(able.length));
  key("Escape"); await settle(30);
  eq(window.URLS.live.size, 0, "ALV-287: given back when the PDF viewer closes");
  key("Escape"); await settle(30);

  /* And the types nobody listed: still saved, exactly as before. */
  ROUTES.open_employee_document = { file: { name: "scan.tiff", type: "application/octet-stream" } };
  window.mpfOpen("HR-EMP-9", opener);
  await settle(200);
  downloads.length = 0;
  click($("emp-drawer").querySelector('[data-mpf="doc"]'));
  await settle(200);
  eq(downloads.map(d => d.download), ["scan.tiff"],
     "ALV-287: and a type the browser cannot draw falls through to the save it "
     + "always had, rather than a broken square");
  key("Escape"); await settle(30);
  window.HTMLAnchorElement.prototype.click = realClick;

  console.log(`\n### 078 faces and profile DOM test: ${pass} passed, ${fail} failed`);
  process.exit(fail ? 1 : 0);
})();
