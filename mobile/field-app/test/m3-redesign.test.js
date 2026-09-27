// ALV-133: the Material 3 redesign of the field app. Every test names what it
// keeps alive, so a bad merge that drops one of these fails here:
//   - the company palette: grey for black and grey brands (D-M3-5), Material's
//     tonal palette otherwise, and every text colour pair readable (WCAG AA)
//     in light and dark, for black, grey, pale and ordinary brand colours;
//   - the theme follows the phone (D-M3-1) and the greeting the clock (D-M3-7);
//   - "Stop agreeing to the notice" and its screen, and the new words;
//   - the notice's layout rules security set on 27 Sep 2026;
//   - the result's true location, the status card, the distance format.
// Run: npm test
"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const WEB = path.join(__dirname, "..", "web");
const js = (name) => path.join(WEB, "js", name);
const read = (p) => fs.readFileSync(p, "utf8");

const theme = require(js("theme.js"));
const strings = require(js("strings.js"));
const ui = require(js("ui.js"));
const screens = require(js("checkin-screens.js"));
const joinScreens = require(js("join-screens.js"));
const core = require(js("signin-core.js"));
const noticeCache = require(js("notice-cache.js"));
const api = require(js("api.js"));

// The same vendored colour code the phone loads, run as the phone runs it.
function loadMcu() {
  const context = {};
  vm.createContext(context);
  vm.runInContext(read(js("vendor/material-color-utilities.js")) + ";this.AlvoraaMcu = AlvoraaMcu;", context);
  return context.AlvoraaMcu;
}
const mcu = loadMcu();

const html = read(path.join(WEB, "index.html"));
const css = read(path.join(WEB, "css", "app.css"));
const checkin = read(js("checkin.js"));

// ── the company palette (D-M3-3, D-M3-5) ─────────────────────────────────

test("black and grey brand colours get the grey palette, never pink (D-M3-5)", () => {
  for (const seed of ["#000000", "#000", "#808080", "#777777", "#f5f5f5", "#1b1b1b"]) {
    assert.equal(theme.schemeKind(seed, mcu), "monochrome", seed);
    for (const dark of [false, true]) {
      const p = theme.palette(seed, dark, mcu);
      for (const role of ["primary", "primaryContainer", "secondaryContainer", "surface"]) {
        const n = parseInt(p[role].slice(1), 16);
        const [r, g, b] = [(n >> 16) & 255, (n >> 8) & 255, n & 255];
        assert.ok(Math.max(r, g, b) - Math.min(r, g, b) <= 2, `${seed} ${role} ${p[role]} is not grey`);
      }
    }
  }
  // PP Jewellers' black, measured in the design (01d §5.1): black buttons, not #8c4a60.
  assert.equal(theme.palette("#000000", false, mcu).primary, "#000000");
  assert.notEqual(theme.palette("#000000", false, mcu).primary, "#8c4a60");
});

test("a colourful brand keeps Material's tonal palette; Alvoraa's own matches the CSS", () => {
  assert.equal(theme.schemeKind("#1a6fa3", mcu), "tonal");
  assert.equal(theme.palette("#1a6fa3", false, mcu).primary, "#2b638b");   // the prototype's Sargam blue
  const alvoraa = theme.palette(theme.DEFAULT_SEED, false, mcu);
  const alvoraaDark = theme.palette(theme.DEFAULT_SEED, true, mcu);
  // The CSS file's default roles (light, then the dark block) are exactly the
  // generator's for the Alvoraa seed, so the app looks the same before and
  // after it knows the company's colour.
  const darkBlock = css.slice(css.indexOf("@media (prefers-color-scheme: dark)"));
  for (const role of theme.ROLES) {
    const name = "--md-sys-color-" + theme.kebab(role);
    const light = new RegExp(name + ":(#[0-9a-f]{6})").exec(css);
    assert.ok(light, name);
    if (role === "scrim") continue;
    assert.equal(light[1], alvoraa[role], name + " light");
    const dark = new RegExp(name + ":(#[0-9a-f]{6})").exec(darkBlock);
    assert.equal(dark && dark[1], alvoraaDark[role], name + " dark");
  }
});

const TEXT_PAIRS = [
  ["onPrimary", "primary"], ["onPrimaryContainer", "primaryContainer"],
  ["onSecondaryContainer", "secondaryContainer"], ["onTertiaryContainer", "tertiaryContainer"],
  ["onErrorContainer", "errorContainer"], ["onError", "error"],
  ["onSurface", "surface"], ["onSurfaceVariant", "surface"],
  ["onSurface", "surfaceContainerHigh"], ["onSurfaceVariant", "surfaceContainerHighest"],
  ["onSurface", "surfaceContainerLow"], ["inverseOnSurface", "inverseSurface"],
  ["primary", "surface"],            // text buttons, section headings, links
  ["error", "surface"],              // "Remove this phone" row, error lines
  ["primary", "surfaceContainer"],   // text buttons on the notice's bar
];

test("every text colour pair is readable (WCAG AA 4.5:1) in light and dark, for any brand", () => {
  const seeds = ["#000000", "#808080", "#ffffff", "#5b4b8a", "#1a6fa3", "#1a7f5a",
                 "#fff59d", "#ffeb3b", "#e0f7fa", "#ff0000", "#f59e0b"];
  for (const seed of seeds) {
    for (const dark of [false, true]) {
      const p = theme.palette(seed, dark, mcu);
      for (const [fg, bg] of TEXT_PAIRS) {
        const ratio = theme.contrast(p[fg], p[bg]);
        assert.ok(ratio >= 4.5, `${seed} ${dark ? "dark" : "light"}: ${fg} on ${bg} is ${ratio.toFixed(2)}:1`);
      }
      // field borders and dividers that carry meaning: 3:1 (WCAG 1.4.11)
      assert.ok(theme.contrast(p.outline, p.surface) >= 3, `${seed} outline`);
    }
  }
});

test("green 'done' and amber 'fix this' never follow the company, and stay readable", () => {
  for (const block of [css.slice(0, css.indexOf("@media")), css.slice(css.indexOf("@media (prefers-color-scheme: dark)"))]) {
    const get = (name) => new RegExp("--" + name + ":(#[0-9a-f]{6})").exec(block)[1];
    assert.ok(theme.contrast(get("alv-on-success-container"), get("alv-success-container")) >= 4.5);
    assert.ok(theme.contrast(get("alv-on-warning-container"), get("alv-warning-container")) >= 4.5);
  }
  assert.ok(!theme.ROLES.some((r) => /success|warning/i.test(r)), "a fixed colour became a company role");
});

test("only a plain hex colour is ever used as the seed", () => {
  assert.equal(theme.normaliseHex("#ABC"), "#aabbcc");
  assert.equal(theme.normaliseHex(" #1A6FA3 "), "#1a6fa3");
  for (const bad of ["red", "#12345g", "#1234", "url(x)", "", null, undefined, 42, "#fff;color:red"]) {
    assert.equal(theme.normaliseHex(bad), null, String(bad));
  }
});

// ── theme (D-M3-1) and greeting (D-M3-7) ───────────────────────────────────

test("the theme follows the phone: both colour schemes declared, a dark block, no pinned light", () => {
  assert.match(html, /<meta name="color-scheme" content="light dark">/);
  assert.doesNotMatch(html, /content="light">/);
  assert.match(css, /@media \(prefers-color-scheme: dark\)/);
  assert.match(read(js("theme.js")), /matchMedia\("\(prefers-color-scheme: dark\)"\)/);
});

test("the greeting follows the phone's clock: morning before 12, afternoon before 5 pm", () => {
  const at = (h, m) => ({ getHours: () => h, getMinutes: () => m });
  assert.equal(theme.greetingKey(at(0, 0)), "greetingMorning");
  assert.equal(theme.greetingKey(at(11, 59)), "greetingMorning");
  assert.equal(theme.greetingKey(at(12, 0)), "greetingAfternoon");
  assert.equal(theme.greetingKey(at(16, 59)), "greetingAfternoon");
  assert.equal(theme.greetingKey(at(17, 0)), "greetingEvening");
  assert.equal(strings.t("greetingEvening", { name: "Arjun" }), "Good evening, Arjun");
  assert.match(checkin, /t\(window\.AlvoraaTheme\.greetingKey\(now\)/);
});

// ── words: one strings object, every key the code asks for exists ─────────

test("every t(\"key\") the app uses has English words (nothing shows a raw key)", () => {
  for (const f of ["checkin.js", "signin.js", "join.js", "ui.js", "checkin-screens.js"]) {
    const src = read(js(f));
    for (const m of src.matchAll(/\bt\("([A-Za-z]+)"/g)) {
      assert.ok(Object.prototype.hasOwnProperty.call(strings.EN, m[1]), `${f}: missing words for ${m[1]}`);
    }
  }
});

// ── Stop agreeing to the notice (new in the app) ───────────────────────────

test("Stop agreeing calls withdraw_agreement with the phone's secret", async () => {
  let called = null;
  const fetchImpl = (url, opts) => {
    called = { url, body: JSON.parse(opts.body) };
    return Promise.resolve({ ok: true, status: 200, text: () => Promise.resolve('{"message":{}}') });
  };
  const result = await api.withdrawAgreement("https:" + "//ppj.alvoraa.co", "s".repeat(43), { fetchImpl, appVersion: "0.3.0" });
  assert.deepEqual(result, { ok: true, data: {} });
  assert.match(called.url, /\/api\/method\/alvoraa_portal\.field_app_join\.withdraw_agreement$/);
  assert.deepEqual(called.body, { token: "s".repeat(43) });
});

test("the Settings row, the dialog's words and the way back are all wired", () => {
  assert.match(html, /data-action="checkin-open-withdraw"/);
  for (const words of ["Stop agreeing to the notice?",
    "This phone stops marking attendance for you until you agree again.",
    "Nothing is deleted. Attendance you already marked stays in your HR record.",
    "HR will see that you stopped agreeing.", "Keep agreeing", ">Stop agreeing<"]) {
    assert.ok(html.includes(words), words);
  }
  for (const action of ["checkin-open-withdraw", "checkin-withdraw-keep", "checkin-withdraw-confirm"]) {
    assert.match(checkin, new RegExp(`"${action}":`), action);
  }
  const doWithdraw = checkin.slice(checkin.indexOf("function doWithdraw()"), checkin.indexOf("// ── Settings"));
  assert.match(doWithdraw, /AlvoraaApi\.withdrawAgreement\(state\.origin, state\.secret\)/);
  assert.match(doWithdraw, /AlvoraaNoticeCache\.markWithdrawn\(\)/);
  assert.match(doWithdraw, /probeNotice\("withdrawn"\)/, "the notice opens next, with its own words");
  assert.match(doWithdraw, /snackbar\(t\("withdrawnSnackbar"\)\)/);
  assert.equal(strings.t("withdrawnHeading"), "You stopped agreeing");
  assert.equal(strings.t("withdrawnIntro"), "To mark attendance with this phone again, read the notice and agree.");
  assert.equal(strings.t("withdrawnSnackbar"), "You stopped agreeing. Attendance on this phone is paused.");
});

test("after a withdrawal the notice never says 'first check-in' or 'has changed' (M3-10)", () => {
  const store = new Map();
  const storage = { getItem: (k) => store.get(k) ?? null, setItem: (k, v) => store.set(k, v), removeItem: (k) => store.delete(k) };
  noticeCache.save({ version: "2026-09-22", rows: [{ key: "record", heading: "h", body: "b" }], agreedAt: "2026-09-22 03:31:00" }, storage);
  assert.equal(noticeCache.load(storage).withdrawn, undefined);
  assert.equal(noticeCache.markWithdrawn(storage), true);
  const entry = noticeCache.load(storage);
  assert.equal(entry.withdrawn, true);
  assert.equal(entry.version, "2026-09-22", "the words agreed to are kept");
  // agreeing again writes a fresh entry without the mark
  noticeCache.save({ version: "2026-09-22", rows: [], agreedAt: "2026-09-27 04:00:00" }, storage);
  assert.equal(noticeCache.load(storage).withdrawn, undefined);
  // renderNoticeAgain chooses the words from the mark
  const render = checkin.slice(checkin.indexOf("function renderNoticeAgain("), checkin.indexOf("function agreeToNoticeAgain("));
  assert.match(render, /cached\.withdrawn \? "withdrawn"/);
});

// ── the notice: security's layout rules (27 Sep 2026) ──────────────────────

test("the tick box and Agree sit BELOW the notice's scroll area, never over it", () => {
  for (const screen of ["signinNotice", "notice", "noticeAgain"]) {
    const start = html.indexOf(`data-screen="${screen}"`);
    const section = html.slice(start, html.indexOf("</section>", start));
    const content = section.indexOf('class="content notice-scroll"');
    const bar = section.indexOf('class="actions raised"');
    assert.ok(content > 0 && bar > content, `${screen}: the bar must follow the scroll area`);
    // the bar is a sibling after the content, not inside it: every <div>
    // opened from the scroll area on is closed before the bar starts
    const between = section.slice(content - 5, bar - 5);  // from "<div class=content" to just before "<div class=actions"
    assert.equal((between.match(/<div\b/g) || []).length, (between.match(/<\/div>/g) || []).length, screen);
    // never pre-ticked
    assert.doesNotMatch(section, /type="checkbox"[^>]*checked/, screen);
  }
  const actions = /\.actions \{([^}]*)\}/.exec(css)[1];
  assert.doesNotMatch(actions, /position\s*:\s*(fixed|absolute|sticky)/, "the bar must not float over the notice");
  assert.match(css, /\.content\.notice-scroll \{ padding-bottom:var\(--sp-8\); \}/,
    "the last part must scroll fully clear of the bar");
});

test("the notice's words and tick-box words stay the server's; only the layout changed", () => {
  // The rows are drawn from what the server sent, with textContent.
  const render = read(js("ui.js"));
  const fn = render.slice(render.indexOf("function renderNoticeRows("), render.indexOf("// The company tile"));
  assert.match(fn, /text\("h3", row\.heading\)/);
  assert.match(fn, /text\("p", row\.body/);
  assert.doesNotMatch(fn, /innerHTML/);
  assert.match(html, /Please tick the box to show you have read the notice\./);
  assert.match(checkin, /"I have read this and I understand\."/);
});

test("each notice part gets its picture from the server's key, or its place in the list", () => {
  assert.equal(ui.noticeIcon({ key: "record" }, 5), "camera");
  assert.equal(ui.noticeIcon({ key: "rights" }, 0), "shield");
  assert.equal(ui.noticeIcon({ heading: "Why" }, 2), "help");  // an older server, no key
  assert.equal(ui.noticeIcon({}, 9), "info");
});

// ── sign in ───────────────────────────────────────────────────────────────

test("a locked network gets security's words and a wait, not an error (D-M3-6)", () => {
  assert.equal(core.messageFor("NETWORK_LOCKED").text,
    "Too many wrong sign-in attempts from this network. Try again in a few minutes, or turn off Wi-Fi and use your mobile data.");
  assert.deepEqual(core.lookFor("NETWORK_LOCKED"), { tone: "warning", icon: "lock", markPassword: false });
  assert.deepEqual(core.lookFor("ACCOUNT_LOCKED"), { tone: "warning", icon: "lock", markPassword: false });
  assert.equal(core.lookFor("PASSWORD_CHANGED_SIGN_IN_AGAIN").tone, "info", "not the person's fault: not red");
  assert.equal(core.lookFor("PASSWORD_SIGNIN_OFF").tone, "info");
  assert.deepEqual(core.lookFor("SIGN_IN_FAILED"), { tone: "error", icon: "error", markPassword: true });
});

test("show password changes only the box's type; the password is still never kept", () => {
  const src = read(js("signin.js"));
  const fn = src.slice(src.indexOf("function showPassword("), src.indexOf("// ── step 1"));
  assert.match(fn, /el\("signin-password"\)\.type = on \? "text" : "password"/);
  assert.doesNotMatch(src, /setItem\([^)]*password/i);
  assert.match(src, /passwordBox\.value = "";\n    showPassword\(false\);/);
});

// ── Home, the result, the problems ─────────────────────────────────────────

test("the status card: after a check-out it says 'Checked out', never 'not checked in yet' (FC-1)", () => {
  assert.deepEqual(screens.statusOf([]), { kind: "idle", time: null });
  assert.equal(screens.statusOf([{ log_type: "IN", time: "t1" }]).kind, "in");
  assert.deepEqual(screens.statusOf([{ log_type: "IN", time: "t1" }, { log_type: "OUT", time: "t2" }]),
    { kind: "out", time: "t2" });
});

test("the result's location follows 01d §7.6, from the server's measurement", () => {
  assert.deepEqual(screens.whereLines({ workplace: "PPJ Head Office Chandigarh", radius_m: 200, distance_m: 42, within: true, accuracy_m: 14 }),
    { icon: "pin", headline: "At PPJ Head Office Chandigarh", detail: "Within 200 m · accuracy 14 m" });
  assert.deepEqual(screens.whereLines({ workplace: "PPJ Head Office Chandigarh", radius_m: 0, distance_m: 13216, within: null, accuracy_m: 14 }),
    { icon: "globe", headline: "About 13.2 km from PPJ Head Office Chandigarh", detail: "You may check in from anywhere · accuracy 14 m" });
  assert.deepEqual(screens.whereLines({ workplace: null, radius_m: null, distance_m: null, within: null, accuracy_m: 14 }),
    { icon: "pin", headline: "Location saved", detail: "Accuracy 14 m" });
  // outside a radius the server did not enforce: never "At", never "anywhere"
  const out = screens.whereLines({ workplace: "Okhla Depot", radius_m: 200, distance_m: 380, within: false, accuracy_m: 9 });
  assert.doesNotMatch(out.headline, /^At /);
  assert.doesNotMatch(out.detail, /anywhere/);
});

test("distances: metres under 1 km, one decimal to 99.9 km, whole km from 100 km", () => {
  assert.equal(screens.formatDistance(140), "140 m");
  assert.equal(screens.formatDistance(1400), "1.4 km");
  assert.equal(screens.formatDistance(13216), "13.2 km");
  assert.equal(screens.formatDistance(99949), "99.9 km");
  assert.equal(screens.formatDistance(140400), "140 km");
});

test("one brand colour for both Check In and Check Out (D-M3-2), and one 96 px button", () => {
  assert.doesNotMatch(checkin, /primary-green|primary-purple/);
  assert.equal((html.match(/btn filled block large/g) || []).length, 2, "Check In on welcome and home only");
  assert.match(css, /\.btn\.large \{ min-height:96px;/);
});

test("every problem screen has a picture and a tone, and keeps its Code for HR", () => {
  const ids = new Set();
  for (const src of [read(js("join-screens.js")), read(js("checkin-screens.js"))]) {
    for (const m of src.matchAll(/screen: "([a-zA-Z]+)"/g)) ids.add(m[1]);
  }
  for (const id of ids) {
    assert.ok(ui.PROBLEM_LOOK[id], `no picture for ${id}`);
    assert.ok(["primary", "neutral", "success", "warning", "error"].includes(ui.problemLook(id).tone), id);
  }
  assert.equal(joinScreens.screenFor("QR_EXPIRED", {}).footerCode, "QR_EXPIRED");
  assert.match(checkin, /t\("codeForHr", \{ code: info\.footerCode \}\)/);
  assert.equal(strings.t("codeForHr", { code: "X" }), "Code for HR: X");
});

test("Remove this phone is one bottom sheet: no browser pop-up after it (M3-8)", () => {
  for (const f of ["checkin.js", "join.js", "signin.js"]) {
    assert.doesNotMatch(read(js(f)), /window\.confirm\(/, f);
  }
  assert.match(html, /id="sheet-remove"/);
  assert.match(checkin, /"checkin-local-remove": function \(\) \{ openRemoveSheet\(true\); \}/);
});

test("names and dates on screen", () => {
  assert.equal(ui.initials("PP Jewellers"), "PJ");
  assert.equal(ui.initials("Sargam"), "SA");
  assert.equal(ui.initials(""), "A");
  assert.match(ui.formatWhen("2026-09-22 12:00:00"), /^Tuesday 22 September at \d{1,2}:\d{2} (am|pm)$/);
  assert.equal(ui.formatWhen(""), "");
});

test("older WebViews (minSdk 24): every inset, color-mix and aspect-ratio has a plain fallback first", () => {
  for (const rule of css.split("}")) {
    if (/color-mix\(/.test(rule)) {
      const prop = /([a-z-]+):[^;]*color-mix\(/.exec(rule)[1];
      assert.ok(rule.indexOf(prop + ":") < rule.indexOf("color-mix("), `no ${prop} fallback in: ${rule.trim()}`);
    }
    if (/[\s;{]inset:/.test(rule)) assert.match(rule, /top:[^;]+; right:/, `no inset fallback in: ${rule.trim()}`);
  }
  assert.match(css, /@supports \(aspect-ratio: 1\)/);
  assert.doesNotMatch(css.replace(/@supports \(aspect-ratio: 1\)[^\n]*/, ""), /aspect-ratio/);
});

test("the password box never teaches the keyboard the password, even while shown", () => {
  const input = /<input type="password" id="signin-password"[^>]*>/.exec(html)[0];
  for (const attr of ['spellcheck="false"', 'autocapitalize="none"', 'autocorrect="off"']) {
    assert.ok(input.includes(attr), attr);
  }
});

test("inline styles are refused, because the content policy drops them on the phone", () => {
  assert.doesNotMatch(html, /<[a-z][^>]*\sstyle\s*=/i);
  assert.doesNotMatch(html, /<style\b/i);
});

test("the Alvoraa logo is in the bundle and has a name for screen readers", () => {
  assert.ok(fs.existsSync(path.join(WEB, "img", "alvoraa-logo.png")));
  assert.ok(fs.existsSync(path.join(WEB, "img", "alvoraa-mark.png")));
  for (const m of html.matchAll(/<img[^>]*class="alv-(mark|logo)"[^>]*>/g)) {
    assert.match(m[0], /alt="Alvoraa"/, m[0]);
  }
  assert.match(html, /Powered by Alvoraa/);
});
