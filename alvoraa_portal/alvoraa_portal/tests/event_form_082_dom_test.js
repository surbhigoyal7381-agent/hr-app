/**
 * Slice 082: the event form page's own script, driven in jsdom.
 *
 * Uses the two pages rendered by the server and kept in tests/fixtures/
 * (event_form_082_guest.html, event_form_082_manager.html). The Python test
 * `test_082_the_dom_fixtures_carry_todays_script` fails if the template's
 * script changes and the fixtures were not rendered again.
 *
 * What it proves (AC-7, AC-12 - AC-17, AC-31/32, the "test what it sends" rule):
 * a missing answer sends nothing and names the fields; Send posts exactly the
 * form's own answers in the body; a double tap sends once; every failure keeps
 * the answers and shows its own words; the organiser's QR dialog opens and
 * closes with the keyboard.
 */
const { JSDOM } = require("jsdom");
const fs = require("fs");
const path = require("path");
const FIX = path.join(__dirname, "fixtures");
let fails = 0;
const ok = (c, m) => { console.log((c ? "  ok   " : "  FAIL ") + m); if (!c) fails++; };
const tick = () => new Promise(r => setTimeout(r, 20));

async function page(file, answer) {
  const html = fs.readFileSync(path.join(FIX, file), "utf8");
  const sent = [];
  const dom = new JSDOM(html, { runScripts: "dangerously", url: "http://localhost/event-form/s082-pune-dealer-meet",
    beforeParse(w) {
      w.fetch = (url, opt) => { sent.push({ url, opt }); return answer(sent.length); };
      w.HTMLCanvasElement.prototype.getContext = () => new Proxy({}, { get: (t, k) => k === "measureText" ? () => ({ width: 10 }) : () => {} , set: () => true });
      w.HTMLCanvasElement.prototype.toBlob = cb => cb(new w.Blob(["x"]));
      w.URL.createObjectURL = () => "blob:x"; w.URL.revokeObjectURL = () => {};
    } });
  return { w: dom.window, d: dom.window.document, sent };
}
const reply = (status, body) => () => Promise.resolve({ status, json: () => Promise.resolve(body) });
function fill(d) {
  d.querySelector("#i-first_name").value = "Rakesh Kulkarni";
  d.querySelector("#i-mobile_no").value = "9822041012";
  d.querySelector('input[name="custom_event_rating"][value^="2"]').checked = true;
  d.querySelector("#i-custom_event_comment").value = "Could not hear the speaker";
  d.querySelector("#i-custom_consent_event").checked = true;
}
const submit = (w, d) => d.querySelector("#wf").dispatchEvent(new w.Event("submit", { cancelable: true }));

(async () => {
  let p = await page("event_form_082_guest.html", reply(200, { message: { saved: 1 } }));
  ok(!p.d.querySelector("#orgbar") && !p.d.querySelector("#qrm"), "guest page has no organiser box or QR dialog");
  ok(!/<input[^>]*checked/.test(p.d.documentElement.outerHTML), "no tick box starts ticked");
  submit(p.w, p.d); await tick();
  ok(p.sent.length === 0, "missing answers send nothing");
  const msg = p.d.querySelector("#ferr").textContent;
  ok(msg.includes("Please fill these in: Your name, Mobile number, I agree.") && msg.includes("कृपया ये भरें"), "missing message names the fields: " + msg);
  ok(p.d.querySelector("#i-first_name").getAttribute("aria-invalid") === "true", "missing field is aria-invalid");
  ok(p.d.activeElement === p.d.querySelector("#ferr"), "the message takes the focus");
  fill(p.d); submit(p.w, p.d); submit(p.w, p.d); await tick();
  ok(p.sent.length === 1, "a double tap sends one request");
  const s = p.sent[0];
  ok(s.url === "/api/method/alvoraa_portal.event_form.save" && s.opt.method === "POST", "POST to the save");
  const b = new URLSearchParams(s.opt.body), v = JSON.parse(b.get("values"));
  ok(b.get("route") === "s082-pune-dealer-meet", "route in the body");
  ok(v.first_name === "Rakesh Kulkarni" && v.custom_consent_event === 1 && v.custom_consent_news === 0 && v.custom_event_rating.startsWith("2 · Poor"), "values are what was typed");
  ok(!("lead_owner" in v) && Object.keys(v).length === 7, "only the form's seven fields: " + Object.keys(v).join(","));
  ok(!s.url.includes("Rakesh"), "nothing personal in the address");
  const card = p.d.querySelector("#card").textContent;
  ok(card.includes("Thank you. Your details are saved for Pune Dealer Meet, 14 Nov.") && card.includes("You can close this page."), "thank you names the event");
  ok(!card.includes("Rakesh") && !card.includes("9822041012"), "thank you echoes nothing typed");

  const cases = [
    [reply(429, { code: "TOO_MANY_TRIES" }), "Many people are sending at the same moment.", "429"],
    [reply(503, {}), "Many people are sending at the same moment.", "nginx 503"],
    [reply(500, { code: "SERVER_ERROR" }), "Not sent.", "500"],
    [() => Promise.reject(new Error("offline")), "Not sent.", "no signal"],
    [reply(422, { code: "FIELD_INVALID", _server_messages: JSON.stringify([JSON.stringify({ message: "Please check “Email (optional)”, then press Send again." })]) }), "Please check “Email (optional)”", "422 server sentence"],
    [reply(404, { code: "FORM_CLOSED" }), "This form has stopped taking answers,", "closed meanwhile"],
  ];
  for (const [ans, want, label] of cases) {
    p = await page("event_form_082_guest.html", ans); fill(p.d); submit(p.w, p.d); await tick();
    const t = p.d.querySelector("#ferr").textContent;
    ok(t.includes(want), label + " -> " + t.slice(0, 70));
    ok(p.d.querySelector("#i-first_name").value === "Rakesh Kulkarni", label + ": answers kept");
    if (label === "closed meanwhile") ok(p.d.querySelector("#send").hidden, "closed meanwhile hides Send");
    else ok(!p.d.querySelector("#send").disabled, label + ": Send usable again");
  }
  p = await page("event_form_082_guest.html", reply(429, {})); fill(p.d); submit(p.w, p.d); await new Promise(r => setTimeout(r, 300));
  ok(p.sent.length === 1, "too many: nothing is resent by itself");

  p = await page("event_form_082_manager.html", reply(200, {}));
  ok(!!p.d.querySelector("#orgbar") && p.d.querySelector("#orgbar").textContent.includes("Extra questions: 0."), "manager sees the box");
  p.d.querySelector("#openqr").click();
  ok(!p.d.querySelector("#qrm").hidden && p.d.activeElement === p.d.querySelector("#qrclose"), "QR dialog opens with focus on Close");
  p.d.dispatchEvent(new p.w.KeyboardEvent("keydown", { key: "Escape" }));
  ok(p.d.querySelector("#qrm").hidden && p.d.activeElement === p.d.querySelector("#openqr"), "Escape closes it and returns focus");
  console.log(fails ? `FAILED ${fails}` : "ALL OK"); process.exit(fails ? 1 : 0);
})();
