/* Slice 076, Part B: "Send a notice" - the Notices card for a holder, Compose,
   the confirm above 25, the 5-a-day screen, the field errors, the result line,
   "Notices I sent" with Cancel, and the holders list in Organisation settings.
   jsdom against the real page and the real portal.js; the server is a stub.

   Pin tests (a bad merge that drops the feature fails by name):
     - "Send a notice" is there for a holder and absent for everyone else
     - above 25 people the page asks first
     - a lost answer says "It may have gone through. Check Notices I sent."
     - a scheduled notice can be cancelled
     - nothing a person wrote becomes an element

   Run: node alvoraa_portal/tests/portal_notices_send_076_test.js alvoraa_portal/alvoraa_portal/www/hrms-employee.html */
const { JSDOM } = require("jsdom");
const { readPortalSource } = require("../../scripts/lib/portal_source");

const html = readPortalSource(process.argv[2]);
let pass = 0, fail = 0;
const ok = m => { pass++; console.log("  PASS  " + m); };
const bad = m => { fail++; console.log("  FAIL  " + m); };
const eq = (got, want, m) => (JSON.stringify(got) === JSON.stringify(want) ? ok(m) : bad(m + ": got <" + JSON.stringify(got) + "> want <" + JSON.stringify(want) + ">"));
const yes = (cond, m) => (cond ? ok(m) : bad(m));

const method = s => String(s).split(".").pop();
const BASE_ROUTES = {get_checkin_status: {ok: {no_employee: 1}}, get_portal_context: {ok: {}},
  get_employee_dashboard: {ok: {no_employee: true}}, get_inbox: {ok: {total: 0, parts: []}}};
let ROUTES = Object.assign({}, BASE_ROUTES);
const CALLS = [];
const HOSTILE = "<img src=x onerror=alert(1)>";

const dom = new JSDOM(html, {
  runScripts: "dangerously", pretendToBeVisual: true,
  url: "http://grace.localhost/hrms-employee",
  beforeParse(w) {
    w.fetch = (url, opts) => {
      const name = method(url);
      CALLS.push({name, args: opts && opts.body ? JSON.parse(opts.body) : {}});
      const h = ROUTES[name] === undefined ? {ok: {}} : ROUTES[name];
      if (h === "drop") return Promise.reject(new TypeError("Failed to fetch"));
      if (h.refuse) {
        return Promise.resolve({ok: false, status: 417, json: () => Promise.resolve({exc_type: "ValidationError",
          _server_messages: JSON.stringify([JSON.stringify({message: h.refuse})])})});
      }
      const v = typeof h.ok === "function" ? h.ok(CALLS[CALLS.length - 1].args) : h.ok;
      return Promise.resolve({ok: true, status: 200, json: () => Promise.resolve({message: v})});
    };
    const call = (o) => {
      CALLS.push({name: method(o.method), args: o.args || {}});
      const h = ROUTES[method(o.method)] === undefined ? {ok: {}} : ROUTES[method(o.method)];
      setTimeout(() => { o.callback && o.callback({message: h.ok}); o.always && o.always({}); }, 0);
      return {status: 200};
    };
    w.frappe = {call, csrf_token: "x", boot: {}, ui: {}, _messages: {}, utils: {escape_html: s => s}, msgprint: () => {}};
  },
});
const {window} = dom, doc = window.document;
const settle = ms => new Promise(r => setTimeout(r, ms));
const $ = id => doc.getElementById(id);
const click = el => el.dispatchEvent(new window.MouseEvent("click", {bubbles: true}));
const callsTo = n => CALLS.filter(c => c.name === n);
const lastCall = n => callsTo(n).pop();
window.alert = () => {};

function setValue(el, v, ev) {
  el.value = v;
  el.dispatchEvent(new window.Event(ev || "input", {bubbles: true}));
}
function choose(name, value) {
  const r = doc.querySelector('input[name="' + name + '"][value="' + value + '"]');
  r.checked = true;
  r.dispatchEvent(new window.Event("change", {bubbles: true}));
}
const btnText = () => $("nc-send").textContent;
const sheet = () => doc.querySelector("#hm-ov [role=dialog]");

const REACH = (o) => Object.assign({everyone: {label: "Everyone I look after", n: 240},
  targets: [{kind: "branch", value: "Noida unit", label: "Noida unit", n: 240},
            {kind: "branch", value: "Gurugram unit", label: "Gurugram unit", n: 172}],
  email_active: false, sent_today: 2, per_day: 5, confirm_above: 25, max_chars: 300}, o || {});
const SENT = [
  {name: "ANN-1", message: "Tomorrow is a half day for the Noida unit.", audience_label: "Noida unit",
   scheduled_for: "2026-10-26 16:10:00", status: "Sent", reason: "", reached: 238, read: 212, created: "2026-10-26 16:10:00"},
  {name: "ANN-2", message: HOSTILE, audience_label: "Gurugram unit", scheduled_for: "2026-11-03 09:00:00",
   status: "Scheduled", reason: "", reached: 0, read: 0, created: "2026-10-27 09:00:00"},
  {name: "ANN-3", message: "Held one", audience_label: "Everyone I look after", scheduled_for: "2026-10-25 09:00:00",
   status: "Not sent", reason: "The sender no longer has the Notice Sender access.", reached: 0, read: 0, created: "2026-10-24 09:00:00"},
];

async function openCompose(routes) {
  ROUTES = Object.assign({}, BASE_ROUTES, {notice_reach: {ok: REACH()}, my_sent_notices: {ok: SENT},
    search_notice_people: {ok: [{id: "E1", name: "Anita Verma"}, {id: "E2", name: "Bhavna Shah"}]}}, routes || {});
  CALLS.length = 0;
  window.ncOpen();
  await settle(80);
}

(async () => {
  await settle(400);
  for (const fn of ["ncOpen", "ncHolders", "loadHome"]) {
    if (typeof window[fn] !== "function") { bad(fn + " is not on the page"); process.exit(1); }
  }

  // ── the Notices card: "Send a notice" for holders only (AC-51) ─────────
  const ann = {name: "N1", kind: "announcement", from: "Kavita Rao, HR Manager", text: HOSTILE, link: null,
               when: "2026-10-27 09:12:00", read: 0};
  const alert1 = {name: "N2", kind: "alert", from: null, text: "Grooming mark recorded", link: null, when: "2026-10-27 08:00:00", read: 0};
  ROUTES = Object.assign({}, BASE_ROUTES, {notices_feed: {ok: {unread: 2, any: true, can_send: 1, items: [ann, alert1]}}});
  window.loadHome(); await settle(120);
  let foot = $("home-notices-foot");
  const sendBtn = [...foot.querySelectorAll("button")].find(b => b.textContent === "Send a notice");
  yes(sendBtn, "a holder sees 'Send a notice' on the Notices card");
  yes(foot.firstElementChild === sendBtn, "it sits on the left of the footer, before See all");
  const rows = [...$("home-notices-body").querySelectorAll(".hm-row")];
  yes(/Pinned/.test(rows[0].textContent) && /Kavita Rao ·/.test(rows[0].textContent), "an announcement is Pinned and names its sender");
  yes(!/HR Manager/.test(rows[0].querySelector(".hm-meta").textContent), "the row shows the name only; the sheet shows the full label");
  yes(!/Pinned/.test(rows[1].textContent), "an alert is not pinned");
  yes(!$("home-notices-body").querySelector("img:not([aria-hidden]), script") && rows[0].textContent.includes(HOSTILE),
      "a hostile notice is text on the card");
  click(rows[0]); await settle(30);
  yes(sheet() && /Notice from Kavita Rao/.test(sheet().querySelector("h2").textContent), "the sheet is 'Notice from Kavita Rao'");
  yes(/Kavita Rao, HR Manager ·/.test(sheet().textContent), "the sheet shows the full sender label");
  yes(!sheet().querySelector("img, script") && sheet().textContent.includes(HOSTILE), "a hostile notice is text in the sheet");
  window.hmCloseSheet(true);

  ROUTES.notices_feed = {ok: {unread: 0, any: false, can_send: 0, items: []}};
  window.loadHome(); await settle(120);
  yes(![...$("home-notices-foot").querySelectorAll("button")].some(b => /Send a notice/.test(b.textContent)),
      "a non-holder sees no 'Send a notice' (absent, not greyed)");
  ROUTES.notices_feed = {ok: {unread: 0, any: false, can_send: 1, items: []}};
  window.loadHome(); await settle(120);
  yes([...$("home-notices-foot").querySelectorAll("button")].some(b => b.textContent === "Send a notice"),
      "a holder with no notices still has the way in");

  // ── Compose: what it says (AC-44, AC-45, AC-46, AC-52) ─────────────────
  await openCompose();
  yes($("panel-notice-compose").classList.contains("active"), "Send a notice opens the Compose screen");
  eq([callsTo("notice_reach").length, callsTo("my_sent_notices").length], [1, 1], "it asks for the reach and the sent list");
  eq($("nc-cnt").textContent, "0 of 300", "the counter starts at 0 of 300");
  setValue($("nc-text"), "Safety walk on Monday");
  eq($("nc-cnt").textContent, "21 of 300", "the counter follows the typing");
  yes(/Do not put pay, health or other personal details in it\./.test($("nc-warn").textContent), "the warning is shown");
  yes(/Everyone I look after \(240 people\)/.test($("nc-form").textContent), "Everyone shows its count");
  eq($("nc-reach").textContent, "This reaches 240 people. Everyone has a login, so everyone sees it. People who have left are skipped.",
     "the live reach line, as drawn");
  yes(!$("nc-email"), "no email control while email is not active");
  eq(btnText(), "Send to 240 people", "the button names what happens");
  yes(/You have sent 2 of 5 notices today\./.test($("nc-form").textContent), "the sent-today line");
  yes($("nc-text").labels.length === 1 && doc.querySelectorAll("#nc-form fieldset legend").length === 2,
      "the message has a label and the choices are fieldsets with legends");

  choose("nc-aud", "target");
  yes($("nc-target") && $("nc-target").querySelector('optgroup[label="Branches"]'), "a branch or company list appears, grouped");
  eq([...$("nc-target").options].map(o => o.textContent), ["Choose…", "Noida unit (240 people)", "Gurugram unit (172 people)"],
     "only what the sender may reach, with counts");
  eq($("nc-reach").textContent, "Choose a branch or company to see how many people this reaches.", "before a choice, the line says so");
  setValue($("nc-target"), "branch:Gurugram unit", "change");
  yes(/This reaches 172 people\./.test($("nc-reach").textContent), "the line follows the choice");
  choose("nc-when", "later");
  yes($("nc-date") && $("nc-time") && /It goes out at about this time, up to 4 minutes later\./.test($("nc-form").textContent),
      "Send later shows a date, a time and the 4-minute hint");
  setValue($("nc-date"), "2099-11-03", "change");
  setValue($("nc-time"), "09:00", "change");
  eq(btnText(), "Schedule for 3 Nov, 9:00 am to 172 people", "the button says when and to how many");

  await openCompose({notice_reach: {ok: REACH({email_active: true})}});
  yes($("nc-email") && !$("nc-email").checked, "with email active the tick is there, unticked");

  // ── errors at the field (AC-49) ───────────────────────────────────────
  await openCompose();
  click($("nc-send")); await settle(10);
  const err = $("nc-e-text");
  eq(err && err.textContent, "Write a message first.", "an empty message says so at the field");
  yes(doc.activeElement === $("nc-text"), "focus moves to the field");
  yes(/nc-e-text/.test($("nc-text").getAttribute("aria-describedby")), "the field is described by its error");
  eq(callsTo("create_notice").length, 0, "nothing is sent");
  setValue($("nc-text"), "Hello");
  choose("nc-when", "later");
  click($("nc-send")); await settle(10);
  eq($("nc-e-when") && $("nc-e-when").textContent, "Choose a date and a time.", "a later send needs a date and time");
  setValue($("nc-date"), "2001-01-01", "change"); setValue($("nc-time"), "09:00", "change");
  click($("nc-send")); await settle(10);
  eq($("nc-e-when") && $("nc-e-when").textContent, "Choose a time that has not passed yet.", "a past time is refused");
  choose("nc-when", "now"); choose("nc-aud", "people"); await settle(20);
  click($("nc-send")); await settle(10);
  eq($("nc-e-people") && $("nc-e-people").textContent, "Tick at least one person.", "chosen people needs a tick");

  // ── 25 or fewer: no dialog (AC-47) ───────────────────────────────────
  ROUTES.create_notice = {ok: {name: "ANN-9", status: "Sent", reached: 2, people: 2, later: false, sent_today: 3}};
  const boxes = [...$("nc-plist").querySelectorAll("input[type=checkbox]")];
  eq(boxes.length, 2, "the search shows the people the server found");
  boxes.forEach(b => { b.checked = true; b.dispatchEvent(new window.Event("change", {bubbles: true})); });
  yes(/This reaches 2 people\./.test($("nc-reach").textContent), "ticks count on the reach line");
  click($("nc-send")); await settle(40);
  yes(!sheet(), "2 people: no confirm dialog");
  const sent2 = lastCall("create_notice").args;
  eq([sent2.audience_kind, JSON.parse(sent2.people), sent2.confirmed, sent2.message], ["people", ["E1", "E2"], 0, "Hello"],
     "the request carries the ids, not names");
  eq($("nc-banner").textContent, "Sent to 2 people. They will see it on Home and in the bell.", "the green result line (AC-50)");

  // ── above 25: the dialog (AC-47) ─────────────────────────────────────
  await openCompose({create_notice: {ok: {name: "ANN-10", status: "Sent", reached: 238, people: 238, later: false, sent_today: 3}}});
  setValue($("nc-text"), "Diwali sweets at the gate");
  click($("nc-send")); await settle(10);
  yes(sheet() && sheet().querySelector("h2").textContent === "Send to 240 people?", "above 25 people the page asks first");
  eq(sheet().querySelector(".hm-sh-b").textContent.trim(), "You are about to send this now to 240 people. You cannot take a sent notice back.",
     "the dialog says it cannot be taken back");
  eq([...sheet().querySelectorAll(".hm-sh-f button")].map(b => b.textContent), ["Go back", "Send to 240 people"], "Go back and Send");
  click([...sheet().querySelectorAll(".hm-sh-f button")][0]); await settle(10);
  yes(!sheet() && callsTo("create_notice").length === 0, "Go back sends nothing");
  click($("nc-send")); await settle(10);
  click([...sheet().querySelectorAll(".hm-sh-f button")][1]); await settle(40);
  eq(lastCall("create_notice").args.confirmed, 1, "the confirmed send says so to the server");
  eq($("nc-banner").textContent, "Sent to 238 people. They will see it on Home and in the bell.", "the result line counts who got it");

  // ── over 200 now: "Sending" (decision 1) and scheduled ────────────────
  await openCompose({create_notice: {ok: {name: "ANN-11", status: "Scheduled", reached: 0, people: 240, later: false, sent_today: 3}}});
  setValue($("nc-text"), "Big one");
  click($("nc-send")); await settle(10);
  click([...sheet().querySelectorAll(".hm-sh-f button")][1]); await settle(40);
  eq($("nc-banner").textContent, "Sending to 240 people. It will show under Notices I sent when it is done.", "decision 1's wording");
  await openCompose({create_notice: {ok: {name: "ANN-12", status: "Scheduled", reached: 0, people: 172, later: true, sent_today: 3}}});
  setValue($("nc-text"), "Safety walk");
  choose("nc-aud", "target"); setValue($("nc-target"), "branch:Gurugram unit", "change");
  choose("nc-when", "later"); setValue($("nc-date"), "2099-11-03", "change"); setValue($("nc-time"), "09:00", "change");
  click($("nc-send")); await settle(10);
  eq(sheet().querySelector(".hm-sh-b").textContent.trim(),
     "You are about to schedule this for 3 Nov, 9:00 am to 172 people. You cannot take a sent notice back.", "the later dialog");
  click([...sheet().querySelectorAll(".hm-sh-f button")][1]); await settle(40);
  const a12 = lastCall("create_notice").args;
  eq([a12.audience_kind, a12.branch, a12.when, a12.send_at], ["branch", "Gurugram unit", "later", "2099-11-03 09:00:00"], "a branch, later");
  eq($("nc-banner").textContent, "Scheduled for 3 Nov, 9:00 am. It will reach 172 people.", "the scheduled line");

  // ── a lost answer (decision 10) and a refusal at the field ───────────
  await openCompose({create_notice: "drop"});
  setValue($("nc-text"), "Short one");
  choose("nc-aud", "people"); await settle(20);
  const pb = $("nc-plist").querySelector("input"); pb.checked = true; pb.dispatchEvent(new window.Event("change", {bubbles: true}));
  const sentBefore = callsTo("my_sent_notices").length;
  click($("nc-send")); await settle(40);
  eq($("nc-general") && $("nc-general").textContent, "It may have gone through. Check Notices I sent.", "a lost answer says check the list");
  yes($("nc-send").disabled, "and the button stays off, so it is not sent twice");
  yes(callsTo("my_sent_notices").length > sentBefore, "the list is read again");
  await openCompose({create_notice: {refuse: "Choose a time that has not passed yet."}});
  setValue($("nc-text"), "x"); choose("nc-when", "later");
  setValue($("nc-date"), "2099-11-03", "change"); setValue($("nc-time"), "09:00", "change");
  choose("nc-aud", "people"); await settle(20);
  const pc = $("nc-plist").querySelector("input"); pc.checked = true; pc.dispatchEvent(new window.Event("change", {bubbles: true}));
  click($("nc-send")); await settle(40);
  eq($("nc-e-when") && $("nc-e-when").textContent, "Choose a time that has not passed yet.", "the server's refusal lands at its field");
  yes(!$("nc-send").disabled, "and the person can fix it and send");

  // ── the 5-a-day screen (AC-48) and an empty scope (AC-12) ─────────────
  await openCompose({notice_reach: {ok: REACH({sent_today: 5})}});
  yes(!$("nc-text") && /You have sent 5 notices today\./.test($("nc-form").textContent)
      && /That is the limit for one day\. You can send again tomorrow\./.test($("nc-form").textContent),
      "at 5 the form is replaced by the limit sentence");
  await openCompose({notice_reach: {ok: REACH({everyone: {label: "Everyone I look after", n: 0}, targets: []})}});
  yes(!$("nc-text") && /No one is in your scope\. Ask HR\./.test($("nc-form").textContent), "nobody in scope says so");

  // ── Notices I sent, and Cancel (AC-36, AC-39, AC-63) ──────────────────
  await openCompose();
  const list = $("nc-sent");
  yes(/Reached 238 people · Read by 212 of 238/.test(list.textContent), "a sent notice shows counts, never names");
  yes(/To Noida unit · Sent 26 Oct, 4:10 pm/.test(list.textContent), "who it went to, and when");
  yes(/Not sent yet/.test(list.textContent) && /Scheduled for 3 Nov, 9:00 am/.test(list.textContent), "a scheduled one says not sent yet");
  yes(/Not sent: The sender no longer has the Notice Sender access\./.test(list.textContent), "a held one says why");
  yes(!list.querySelector("img, script") && list.textContent.includes(HOSTILE), "a hostile notice is text in Notices I sent");
  const cancels = list.querySelectorAll("[data-nc=cancel]");
  eq(cancels.length, 1, "only the scheduled one can be cancelled");
  click(cancels[0]); await settle(10);
  eq(sheet().querySelector("h2").textContent, "Cancel this notice?", "Cancel asks first");
  eq([...sheet().querySelectorAll(".hm-sh-f button")].map(b => b.textContent), ["Keep it", "Cancel the notice"], "Keep it, or cancel");
  ROUTES.cancel_notice = {ok: {name: "ANN-2", status: "Cancelled"}};
  const readsBefore = callsTo("my_sent_notices").length;
  click([...sheet().querySelectorAll(".hm-sh-f button")][1]); await settle(40);
  eq(lastCall("cancel_notice").args, {name: "ANN-2"}, "cancel names the notice");
  yes(!sheet() && callsTo("my_sent_notices").length > readsBefore, "the dialog closes and the list is read again");

  // ── back, and the holders list (AC-107) ───────────────────────────────
  click(doc.querySelector("[data-nc=back]"));
  yes($("panel-home").classList.contains("active"), "Back to Home");
  ROUTES.notice_sender_holders = {ok: ["Arjun Mehta", "Kavita Rao"]};
  window.ncHolders(); await settle(30);
  yes($("org-senders-card").style.display !== "none", "HR sees who can send");
  eq([...$("org-senders-list").children].map(c => c.textContent), ["Arjun Mehta", "Kavita Rao"], "names only");
  ROUTES.notice_sender_holders = {refuse: "Only HR can see who may send notices."};
  window.ncHolders(); await settle(30);
  yes($("org-senders-card").style.display === "none", "anyone the server refuses sees no list");

  console.log(`\n### Notices send 076 DOM test: ${pass} passed, ${fail} failed`);
  process.exit(fail ? 1 : 0);
})();
