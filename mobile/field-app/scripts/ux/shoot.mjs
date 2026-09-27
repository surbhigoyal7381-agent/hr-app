// Screenshots and layout checks of the field app's screens in headless Chrome
// (ALV-133). Not part of `npm test`: it needs Playwright, which is not an app
// dependency. Run from mobile/field-app with a Playwright install on the path:
//
//     NODE_PATH=<dir with playwright> node scripts/ux/shoot.mjs <out-dir>
//
// It serves web/ on 127.0.0.1, fakes the native parts (secure storage, the
// camera, the location, the server's answers) inside the page, walks the real
// app to each screen by pressing its real buttons, and for every screen:
//   - saves a PNG at 360 px wide, light and dark, and 200% text for some;
//   - fails if anything is wider than the screen, if a visible button or
//     link is smaller than 48 x 48 px, or if any text is under 12 px;
//   - on the notice screens (security, 27 Sep 2026): fails if the fixed tick
//     box and Agree bar overlaps the notice, if the last part cannot scroll
//     fully clear of it, or if at 360 x 640 the first part's heading and body
//     are not both above the bar.
// Nothing here talks to a real server: every answer is written below.

import { createServer } from "node:http";
import { readFileSync, existsSync, mkdirSync, writeFileSync } from "node:fs";
import { join, extname } from "node:path";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const { chromium } = require("playwright");

const APP_DIR = fileURLToPath(new URL("../..", import.meta.url));
const WEB = join(APP_DIR, "web");
const OUT = process.argv[2] || join(APP_DIR, "ux-shots");
mkdirSync(OUT, { recursive: true });

const TYPES = { ".html": "text/html", ".js": "text/javascript", ".css": "text/css",
  ".png": "image/png", ".json": "application/json", ".svg": "image/svg+xml" };

const server = createServer((req, res) => {
  const path = decodeURIComponent(new URL(req.url, "http://x").pathname);
  const file = join(WEB, path === "/" ? "index.html" : path);
  if (!file.startsWith(WEB) || !existsSync(file)) { res.writeHead(404); res.end(); return; }
  res.writeHead(200, { "Content-Type": TYPES[extname(file)] || "application/octet-stream" });
  res.end(readFileSync(file));
});
await new Promise((r) => server.listen(0, "127.0.0.1", r));
const BASE = `http://127.0.0.1:${server.address().port}/`;

// ── sample data (invented; PP Jewellers' black is its real local setting) ──

const ORIGIN = "https:" + "//ppj.alvoraa.co";
const TOKEN = "t".repeat(43);
const NOTICE = {
  version: "2026-09-22", retention_days: 90,
  agree: "I have read this and I understand.",
  what_changed: "We now tell you that we record this phone's model name when you set up.",
  rows: [
    { key: "record", heading: "What we record", body: "A photo of you, where you are, and the time — only when you press Check In or Check Out. When you set up: this phone's model name." },
    { key: "not_record", heading: "What we do not record", body: "Nothing between punches. You are not tracked while you work." },
    { key: "why", heading: "Why", body: "To mark your attendance, and to confirm you were at your workplace." },
    { key: "who", heading: "Who can see it", body: "HR and your manager. Not your colleagues." },
    { key: "how_long", heading: "How long", body: "Check-in photos are kept for 90 days, then deleted." },
    { key: "rights", heading: "Your rights", body: "Ask HR to see what was recorded about you, or to correct it." },
  ],
};
const TODAY = new Date().toISOString().slice(0, 10);
const WORKPLACE = { name: "PPJ Head Office Chandigarh", radius_m: 200 };

function status(extra = {}) {
  return {
    employee: "HR-EMP-0001", employee_name: "Arjun Kumar", first_name: "Arjun",
    designation: "Sales Executive", company: "PP Jewellers", checked_in: false,
    todays_checkins: [], server_time: `${TODAY} 09:30:00`, workplace: WORKPLACE,
    check_in_rule: "radius", min_version: "0.1.0", notice_version: NOTICE.version,
    joined_on: `${TODAY} 08:00:00`, brand_colour: "#000000", ...extra,
  };
}
const IN_ROW = { name: "c1", log_type: "IN", time: `${TODAY} 09:12:00`, device_id: "x" };
const OUT_ROW = { name: "c2", log_type: "OUT", time: `${TODAY} 18:14:00`, device_id: "x" };

const ok = (message) => ({ status: 200, body: { message } });
const refuse = (status, code, values = {}) => ({ status, body: { code, values, exc_type: "ValidationError" } });

// ── the fakes, run inside the page before any app script ──────────────────

function fakes(config) {
  const store = new Map(Object.entries(config.secure || {}));
  const plugin = {
    get: ({ key }) => store.has(key) ? Promise.resolve({ value: store.get(key) }) : Promise.reject(new Error("no key")),
    set: ({ key, value }) => { store.set(key, value); return Promise.resolve({ value: true }); },
    remove: ({ key }) => { store.delete(key); return Promise.resolve({ value: true }); },
  };
  // A fresh object on every read: capacitor-core.js writes its own
  // isNativePlatform onto whatever window.Capacitor it finds.
  const makeCap = () => ({ isNativePlatform: () => true, getPlatform: () => "android",
    Plugins: { SecureStoragePlugin: plugin }, registerPlugin: () => plugin });
  Object.defineProperty(window, "Capacitor", { get: makeCap, set: () => {}, configurable: false });
  for (const [k, v] of Object.entries(config.local || {})) localStorage.setItem(k, v);

  window.__FAKE__ = config;
  window.fetch = (url, opts) => {
    const method = String(url).split("/api/method/")[1] || "";
    const name = method.split(".").pop();
    const queue = (config.routes || {})[name];
    const answer = Array.isArray(queue) ? (queue.length > 1 ? queue.shift() : queue[0]) : queue;
    if (answer === "never" || !answer) return new Promise(() => {});
    if (answer === "offline") return Promise.reject(new TypeError("Failed to fetch"));
    return Promise.resolve(new Response(JSON.stringify(answer.body), {
      status: answer.status, headers: { "Content-Type": "application/json" } }));
  };

  Object.defineProperty(window, "jsQR", { get: () => () => (config.qr ? { data: config.qr } : null),
    set: () => {}, configurable: false });

  const md = navigator.mediaDevices || {};
  Object.defineProperty(navigator, "mediaDevices", { value: md, configurable: true });
  md.getUserMedia = () => {
    if (config.camera === "denied") {
      const e = new Error("denied"); e.name = "NotAllowedError"; return Promise.reject(e);
    }
    const c = document.createElement("canvas");
    c.width = 640; c.height = 480;
    const g = c.getContext("2d");
    const draw = () => {
      const grad = g.createRadialGradient(320, 190, 10, 320, 240, 420);
      grad.addColorStop(0, "#6b5d52"); grad.addColorStop(.5, "#3a322c"); grad.addColorStop(1, "#141110");
      g.fillStyle = grad; g.fillRect(0, 0, 640, 480);
      g.fillStyle = "#d9c7b8";
      g.beginPath(); g.arc(320, 200, 80, 0, Math.PI * 2); g.fill();
      g.beginPath(); g.ellipse(320, 470, 180, 150, 0, Math.PI, 0); g.fill();
    };
    draw(); setInterval(draw, 100);
    return Promise.resolve(c.captureStream(10));
  };
  const geo = { getCurrentPosition: (ok) => setTimeout(() => ok({ coords: { latitude: 30.7, longitude: 76.8, accuracy: 14 } }), 50) };
  Object.defineProperty(navigator, "geolocation", { value: geo, configurable: true });
}

// ── the screens: how to get to each one ───────────────────────────────────

const JOINED = { secure: { alvoraa_device_secret: TOKEN, alvoraa_tenant_origin: ORIGIN },
  local: { alvoraa_location_explained: "1", alvoraa_company_code: "ppj",
    alvoraa_company_name: "PP Jewellers", alvoraa_brand_colour: "#000000",
    alvoraa_notice_agreed: JSON.stringify({ ...NOTICE, agreedAt: `${TODAY} 03:31:00` }) } };
const joined = (routes, extra = {}) => ({ ...JOINED, ...extra, routes,
  local: { ...JOINED.local, ...(extra.local || {}) } });

const CODE_LINK = ORIGIN + "/enrol#t=" + "c".repeat(43);
const CHECK = ok({ first_name: "Arjun", surname_initial: "K", designation: "Sales Executive",
  company: "PP Jewellers", brand_colour: "#000000", notice: NOTICE, min_version: "0.1.0" });
const JOIN_ANSWER = ok({ token: TOKEN, status: "active", first_name: "Arjun", company: "PP Jewellers",
  workplace: WORKPLACE, todays_checkins: [], brand_colour: "#000000" });

async function fillSignIn(page) {
  await page.fill("#signin-company", "ppj");
  await page.fill("#signin-email", "arjun.k@example.in");
  await page.fill("#signin-password", "not-a-real-password");
  await page.click('#signin-form button[type="submit"]');
}
async function signInWith(page, code) { await fillSignIn(page); await page.waitForSelector("#signin-error-card:not([hidden])"); }
async function toConfirm(page) {
  await page.click('[data-action="signin-use-code"]');
  await page.setInputFiles("#photo-picker", { name: "qr.png", mimeType: "image/png",
    buffer: readFileSync(join(WEB, "img", "alvoraa-mark.png")) });
  await page.waitForSelector('[data-screen="confirm"]:not([hidden])');
}
const on = (name) => `[data-screen="${name}"]:not([hidden])`;
async function punchFromHome(page) { await page.click("#home-punch-button"); }

const SCREENS = [
  // before the company is known: Alvoraa's own colours and mark
  { id: "signin", config: { routes: {} }, go: async (p) => p.waitForSelector(on("signin")), big: true },
  { id: "signinRemembered", config: { routes: {}, local: { alvoraa_company_code: "ppj" } }, go: async (p) => p.waitForSelector(on("signin")) },
  { id: "signinWrong", config: { routes: { sign_in_with_password: refuse(401, "SIGN_IN_FAILED") } }, go: (p) => signInWith(p), big: true },
  { id: "signinLocked", config: { routes: { sign_in_with_password: refuse(403, "ACCOUNT_LOCKED", { retry_after_s: 300 }) } }, go: (p) => signInWith(p) },
  { id: "signinNetLock", config: { routes: { sign_in_with_password: refuse(403, "NETWORK_LOCKED") } }, go: (p) => signInWith(p) },
  { id: "signinPwOff", config: { routes: { sign_in_with_password: refuse(403, "PASSWORD_SIGNIN_OFF") } }, go: (p) => signInWith(p) },
  { id: "signingIn", config: { routes: { sign_in_with_password: "never" } }, go: async (p) => { await fillSignIn(p); await p.waitForSelector(on("signingIn")); } },
  { id: "otp", config: { routes: { sign_in_with_password: ok({ status: "otp_required", tmp_id: "abc", method: "Email", prompt: "We sent a code to a•••@example.in" }) } },
    go: async (p) => { await fillSignIn(p); await p.waitForSelector(on("signinOtp")); } },
  { id: "otpWrong", config: { routes: { sign_in_with_password: ok({ status: "otp_required", tmp_id: "abc", prompt: "We sent a code to a•••@example.in" }), confirm_sign_in_code: refuse(401, "OTP_WRONG") } },
    go: async (p) => { await fillSignIn(p); await p.waitForSelector(on("signinOtp")); await p.fill("#signin-otp", "482917"); await p.click('#signin-otp-form button[type="submit"]'); await p.waitForSelector("#signin-otp-error:not([hidden])"); } },
  { id: "pwChanged", config: joined({ field_status: refuse(403, "PASSWORD_CHANGED_SIGN_IN_AGAIN") }), go: (p) => p.waitForSelector("#signin-error-card:not([hidden])") },
  { id: "signinNotice", config: { routes: { sign_in_with_password: ok({ token: TOKEN, status: "not_agreed", first_name: "Arjun", company: "PP Jewellers", workplace: WORKPLACE, todays_checkins: [], brand_colour: "#000000", notice: NOTICE }) } },
    go: async (p) => { await fillSignIn(p); await p.waitForSelector(on("signinNotice")); }, notice: true },
  { id: "joinFirst", config: { routes: {} }, go: async (p) => { await p.click('[data-action="signin-use-code"]'); await p.waitForSelector(on("first")); } },
  { id: "camExplain", config: { routes: {} }, go: async (p) => { await p.click('[data-action="signin-use-code"]'); await p.click('[data-action="scan-pressed"]'); await p.waitForSelector(on("camExplain")); } },
  { id: "scan", config: { routes: {} }, go: async (p) => { await p.click('[data-action="signin-use-code"]'); await p.click('[data-action="scan-pressed"]'); await p.click('[data-action="open-scanner"]'); await p.waitForSelector(on("scan")); await p.waitForTimeout(400); } },
  { id: "checking", config: { routes: { check_code: "never" }, qr: CODE_LINK },
    go: async (p) => { await p.click('[data-action="signin-use-code"]'); await p.setInputFiles("#photo-picker", { name: "qr.png", mimeType: "image/png", buffer: readFileSync(join(WEB, "img", "alvoraa-mark.png")) }); await p.waitForSelector(on("checking")); } },
  { id: "notAlvoraa", config: { routes: {}, qr: "upi://pay?pa=shop@bank" },
    go: async (p) => { await p.click('[data-action="signin-use-code"]'); await p.setInputFiles("#photo-picker", { name: "qr.png", mimeType: "image/png", buffer: readFileSync(join(WEB, "img", "alvoraa-mark.png")) }); await p.waitForSelector(on("problem")); } },
  { id: "codeExpired", config: { routes: { check_code: refuse(410, "QR_EXPIRED", { expired_at: `${TODAY} 08:00:00` }) }, qr: CODE_LINK }, go: async (p) => { await toConfirmOrProblem(p); } },
  // the company is known from here: its colour (black -> greys) and its mark
  { id: "confirm", config: { routes: { check_code: CHECK }, qr: CODE_LINK }, go: toConfirm },
  { id: "notMe", config: { routes: { check_code: CHECK }, qr: CODE_LINK }, go: async (p) => { await toConfirm(p); await p.click('[data-action="confirm-not-me"]'); await p.waitForSelector("#dialog-not-me:not([hidden])"); } },
  { id: "notMeDone", config: { routes: { check_code: CHECK, refuse_code: ok({}) }, qr: CODE_LINK }, go: async (p) => { await toConfirm(p); await p.click('[data-action="confirm-not-me"]'); await p.click('[data-action="cancel-code"]'); await p.waitForSelector(on("notMeDone")); } },
  { id: "notice", config: { routes: { check_code: CHECK }, qr: CODE_LINK }, go: async (p) => { await toConfirm(p); await p.click('[data-action="confirm-yes"]'); await p.waitForSelector(on("notice")); }, notice: true, big: true },
  { id: "noticeUnticked", config: { routes: { check_code: CHECK }, qr: CODE_LINK }, go: async (p) => { await toConfirm(p); await p.click('[data-action="confirm-yes"]'); await p.click('[data-action="agree-and-finish"]'); await p.waitForSelector("#notice-tick-error:not([hidden])"); }, notice: true },
  { id: "joining", config: { routes: { check_code: CHECK, join_with_code: "never" }, qr: CODE_LINK }, go: async (p) => { await toConfirm(p); await p.click('[data-action="confirm-yes"]'); await p.check("#notice-tick"); await p.click('[data-action="agree-and-finish"]'); await p.waitForSelector(on("joining")); } },
  { id: "welcome", config: { routes: { check_code: CHECK, join_with_code: JOIN_ANSWER }, qr: CODE_LINK }, go: async (p) => { await toConfirm(p); await p.click('[data-action="confirm-yes"]'); await p.check("#notice-tick"); await p.click('[data-action="agree-and-finish"]'); await p.waitForSelector(on("welcome")); } },
  // daily use
  { id: "homeLoading", config: joined({ field_status: "never" }), go: (p) => p.waitForSelector(on("homeLoading")) },
  { id: "homeIdle", config: joined({ field_status: ok(status()) }), go: (p) => p.waitForSelector(on("home")), big: true },
  { id: "homeIn", config: joined({ field_status: ok(status({ checked_in: true, todays_checkins: [IN_ROW] })) }), go: (p) => p.waitForSelector(on("home")), big: true },
  { id: "homeOut", config: joined({ field_status: ok(status({ todays_checkins: [IN_ROW, OUT_ROW] })) }), go: (p) => p.waitForSelector(on("home")) },
  { id: "homeAnywhere", config: joined({ field_status: ok(status({ check_in_rule: "anywhere", workplace: { name: "PPJ Head Office Chandigarh", radius_m: 0 } })) }), go: (p) => p.waitForSelector(on("home")) },
  { id: "homeSargam", config: joined({ field_status: ok(status({ company: "Sargam Metals", employee_name: "Ravi Singh", first_name: "Ravi", brand_colour: "#1a6fa3" })) }), go: (p) => p.waitForSelector(on("home")) },
  { id: "homePaleBrand", config: joined({ field_status: ok(status({ brand_colour: "#fff59d", checked_in: true, todays_checkins: [IN_ROW] })) }), go: (p) => p.waitForSelector(on("home")) },
  { id: "locExplain", config: joined({ field_status: ok(status()) }, { local: { alvoraa_location_explained: "" } }), go: async (p) => { await p.waitForSelector(on("home")); await punchFromHome(p); await p.waitForSelector(on("locExplain")); } },
  { id: "camera", config: joined({ field_status: ok(status()) }), go: async (p) => { await p.waitForSelector(on("home")); await punchFromHome(p); await p.waitForSelector("#camera-take:not([disabled])"); await p.waitForTimeout(300); } },
  { id: "cameraReview", config: joined({ field_status: ok(status()) }), go: async (p) => { await p.waitForSelector(on("home")); await punchFromHome(p); await p.waitForSelector("#camera-take:not([disabled])"); await p.click("#camera-take"); await p.waitForSelector("#camera-use:not([hidden])"); } },
  { id: "cameraDenied", config: joined({ field_status: ok(status()) }, { camera: "denied" }), go: async (p) => { await p.waitForSelector(on("home")); await punchFromHome(p); await p.waitForSelector("#camera-no-photo:not([hidden])"); } },
  { id: "punching", config: joined({ field_status: ok(status()), field_checkin: "never" }), go: async (p) => { await p.waitForSelector(on("home")); await punchFromHome(p); await p.waitForSelector("#camera-take:not([disabled])"); await p.click("#camera-take"); await p.click("#camera-use"); await p.waitForSelector("#punch-step-save.now"); } },
  { id: "resultIn", config: joined({ field_status: ok(status()), field_checkin: ok({ status: "ok", time: `${TODAY} 09:12:00`, location: { workplace: WORKPLACE.name, radius_m: 200, distance_m: 42, within: true, accuracy_m: 14 } }) }), go: toResult, big: true },
  { id: "resultAnywhere", config: joined({ field_status: ok(status({ check_in_rule: "anywhere" })), field_checkin: ok({ status: "ok", time: `${TODAY} 09:12:00`, location: { workplace: WORKPLACE.name, radius_m: 0, distance_m: 13216, within: null, accuracy_m: 14 } }) }), go: toResult },
  { id: "resultNoPhoto", config: joined({ field_status: ok(status()), field_checkin: ok({ status: "ok", time: `${TODAY} 09:12:00`, location: { workplace: null, radius_m: null, distance_m: null, within: null, accuracy_m: 14 } }) }, { camera: "denied" }),
    go: async (p) => { await p.waitForSelector(on("home")); await punchFromHome(p); await p.click("#camera-no-photo"); await p.waitForSelector(on("result")); } },
  { id: "homeCamOff", config: joined({ field_status: ok(status()), field_checkin: ok({ status: "ok", time: `${TODAY} 09:12:00`, location: {} }) }, { camera: "denied" }),
    go: async (p) => { await p.waitForSelector(on("home")); await punchFromHome(p); await p.click("#camera-no-photo"); await p.waitForSelector(on("result")); await p.click('[data-action="checkin-result-done"]'); await p.waitForSelector("#home-camera-off:not([hidden])"); } },
  { id: "refusedFar", config: joined({ field_status: ok(status()), field_checkin: refuse(422, "OUTSIDE_WORKPLACE", { site: WORKPLACE.name, distance_m: 13216, radius_m: 200 }) }), go: toProblem },
  { id: "gps", config: joined({ field_status: ok(status()), field_checkin: refuse(422, "GPS_NOT_EXACT", { accuracy_m: 86, limit_m: 50 }) }), go: toProblem },
  { id: "noNet", config: joined({ field_status: ok(status()), field_checkin: "offline" }), go: toProblem },
  { id: "serverError", config: joined({ field_status: ok(status()), field_checkin: refuse(500, "SERVER_ERROR") }), go: toProblem },
  { id: "blocked", config: joined({ field_status: refuse(403, "DEVICE_BLOCKED") }), go: (p) => p.waitForSelector(on("problem")), big: true },
  { id: "removeSheetLocal", config: joined({ field_status: refuse(403, "DEVICE_BLOCKED") }), go: async (p) => { await p.waitForSelector(on("problem")); await p.click('[data-action="checkin-local-remove"]'); await p.waitForSelector("#sheet-remove:not([hidden])"); } },
  { id: "replaced", config: joined({ field_status: refuse(403, "DEVICE_REPLACED", { replaced_at: `${TODAY} 08:40:00` }) }), go: (p) => p.waitForSelector(on("problem")) },
  { id: "update", config: joined({ field_status: refuse(426, "APP_TOO_OLD", { min_version: "0.4.0" }) }), go: (p) => p.waitForSelector(on("problem")) },
  { id: "noticeChanged", config: joined({ field_status: refuse(409, "NOTICE_CHANGED", NOTICE) }), go: (p) => p.waitForSelector(on("noticeAgain")), notice: true },
  { id: "settings", config: joined({ field_status: ok(status({ checked_in: true, todays_checkins: [IN_ROW] })) }), go: toSettings, big: true },
  { id: "records", config: joined({ field_status: ok(status({ checked_in: true, todays_checkins: [IN_ROW] })) }), go: async (p) => { await toSettings(p); await p.click('[data-action="checkin-open-records"]'); await p.waitForSelector(on("records")); } },
  { id: "withdrawDialog", config: joined({ field_status: ok(status()) }), go: async (p) => { await toSettings(p); await p.click('[data-action="checkin-open-withdraw"]'); await p.waitForSelector("#dialog-withdraw:not([hidden])"); } },
  { id: "withdrawn", config: joined({ field_status: ok(status()), withdraw_agreement: ok({}), acknowledge_notice: refuse(409, "NOTICE_CHANGED", NOTICE) }),
    go: async (p) => { await toSettings(p); await p.click('[data-action="checkin-open-withdraw"]'); await p.click('[data-action="checkin-withdraw-confirm"]'); await p.waitForSelector(on("noticeAgain")); await p.waitForSelector("#snackbar:not([hidden])"); }, notice: true, big: true },
  { id: "removeSheet", config: joined({ field_status: ok(status()) }), go: async (p) => { await toSettings(p); await p.click('[data-action="checkin-open-leave-confirm"]'); await p.waitForSelector("#sheet-remove:not([hidden])"); } },
];

async function toConfirmOrProblem(p) {
  await p.click('[data-action="signin-use-code"]');
  await p.setInputFiles("#photo-picker", { name: "qr.png", mimeType: "image/png", buffer: readFileSync(join(WEB, "img", "alvoraa-mark.png")) });
  await p.waitForSelector(on("problem"));
}
async function toCameraUse(p) {
  await p.waitForSelector(on("home")); await punchFromHome(p);
  await p.waitForSelector("#camera-take:not([disabled])"); await p.click("#camera-take"); await p.click("#camera-use");
}
async function toResult(p) { await toCameraUse(p); await p.waitForSelector(on("result")); }
async function toProblem(p) { await toCameraUse(p); await p.waitForSelector(on("problem")); }
async function toSettings(p) { await p.waitForSelector(on("home")); await p.click('[data-action="checkin-open-settings"]'); await p.waitForSelector(on("settings")); }

// ── the checks, run in the page on the screen as shown ─────────────────────

function measure(noticeCheck) {
  const problems = [];
  const vw = document.documentElement.clientWidth;
  if (document.documentElement.scrollWidth > vw + 1) problems.push(`page is ${document.documentElement.scrollWidth}px wide on a ${vw}px screen`);
  const visible = (el) => { const r = el.getBoundingClientRect(); const s = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && s.visibility !== "hidden" && s.display !== "none" && !el.closest("[hidden]"); };
  document.querySelectorAll(".screen:not([hidden]) *, .scrim:not([hidden]) *").forEach((el) => {
    if (!visible(el)) return;
    const r = el.getBoundingClientRect();
    if (r.right > vw + 1 && !el.closest(".cam") && getComputedStyle(el).position !== "fixed") {
      if (!el.closest(".content") || el.closest(".content").scrollWidth > el.closest(".content").clientWidth + 1) {
        problems.push(`<${el.tagName.toLowerCase()} ${el.id ? "#" + el.id : el.className}> sticks out (${Math.round(r.right)}px)`);
      }
    }
    const interactive = el.matches("button, a[href], input:not([type=hidden]), label.check-row");
    if (interactive && !el.closest(".box") && (r.width < 47.5 || r.height < 47.5)) {
      problems.push(`target <${el.tagName.toLowerCase()} ${el.id || el.getAttribute("data-action") || el.className}> is ${Math.round(r.width)}x${Math.round(r.height)}`);
    }
    for (const node of el.childNodes) {
      if (node.nodeType === 3 && node.textContent.trim()) {
        const size = parseFloat(getComputedStyle(el).fontSize);
        if (size < 12) problems.push(`text "${node.textContent.trim().slice(0, 30)}" is ${size}px`);
        break;
      }
    }
  });
  const out = { problems };
  if (noticeCheck) {
    const screen = document.querySelector(".screen:not([hidden])");
    const content = screen.querySelector(".content");
    const bar = screen.querySelector(".actions");
    const barTop = bar.getBoundingClientRect().top;
    const contentBox = content.getBoundingClientRect();
    if (contentBox.bottom > barTop + 0.5) problems.push(`notice: the scroll area (bottom ${contentBox.bottom}) runs under the bar (top ${barTop})`);
    const rows = content.querySelectorAll(".notice-row");
    const first = rows[0];
    const h = first.querySelector("h3").getBoundingClientRect();
    const b = first.querySelector("p").getBoundingClientRect();
    out.firstAboveBar = h.bottom <= barTop && b.bottom <= barTop;
    content.scrollTop = content.scrollHeight;
    const last = rows[rows.length - 1].getBoundingClientRect();
    out.lastClearOfBar = last.bottom <= barTop - 8;
    if (!out.lastClearOfBar) problems.push(`notice: the last part (bottom ${last.bottom}) cannot scroll clear of the bar (top ${barTop})`);
    content.scrollTop = 0;
  }
  return out;
}

// ── run ───────────────────────────────────────────────────────────────────

const browser = await chromium.launch();
const report = [];
let failures = 0;
const only = process.env.ONLY ? new RegExp(process.env.ONLY) : null;

for (const s of SCREENS) {
  if (only && !only.test(s.id)) continue;
  const variants = [["light", 1, 780], ["dark", 1, 780]];
  if (s.big) variants.push(["light", 2, 780]);
  if (s.notice) variants.push(["light", 1, 640]);
  for (const [scheme, scale, height] of variants) {
    const context = await browser.newContext({ viewport: { width: 360, height }, deviceScaleFactor: 2,
      colorScheme: scheme, reducedMotion: "reduce" });
    const page = await context.newPage();
    const errors = [];
    page.on("pageerror", (e) => errors.push(String(e)));
    page.on("console", (m) => { if (m.type() === "error") errors.push(m.text()); });
    await page.addInitScript(fakes, s.config);
    await page.goto(BASE);
    if (scale !== 1) await page.evaluate((k) => window.AlvoraaTheme.setTextScale(k), scale);
    let label = `${s.id}-${scheme}${scale !== 1 ? "-200" : ""}${height !== 780 ? "-640" : ""}`;
    try {
      await s.go(page);
      await page.waitForTimeout(150);
      const m = await page.evaluate(measure, !!s.notice);
      if (height === 640 && s.notice && !m.firstAboveBar) m.problems.push("notice at 360 x 640: the first part's heading and body are not both above the bar");
      m.problems.push(...errors.filter((e) => !/favicon/.test(e)).map((e) => "script error: " + e));
      await page.screenshot({ path: join(OUT, label + ".png") });
      if (m.problems.length) failures++;
      report.push({ screen: label, ok: m.problems.length === 0, problems: m.problems,
        notice: s.notice ? { firstAboveBar: m.firstAboveBar, lastClearOfBar: m.lastClearOfBar } : undefined });
    } catch (e) {
      if (process.env.DEBUG) console.log(await page.evaluate(() => Promise.all([
        typeof window.Capacitor, window.Capacitor && String(window.Capacitor.isNativePlatform()),
        window.AlvoraaDeviceSecret.load(), window.AlvoraaDeviceSecret.loadOrigin()])));
      failures++;
      await page.screenshot({ path: join(OUT, label + "-FAILED.png") }).catch(() => {});
      report.push({ screen: label, ok: false, problems: ["could not reach the screen: " + String(e).split("\n")[0], ...errors] });
    }
    await context.close();
  }
}
await browser.close();
server.close();
writeFileSync(join(OUT, "report.json"), JSON.stringify(report, null, 2));
for (const r of report) if (!r.ok) console.log(`FAIL ${r.screen}\n  - ${r.problems.join("\n  - ")}`);
console.log(`${report.length} shots, ${report.length - failures} clean, ${failures} with problems. ${OUT}`);
process.exit(failures ? 1 : 0);
