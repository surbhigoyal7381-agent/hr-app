/* ALV-297: does the check-in page take its iPhone photo through Apple's camera,
 * and what does it send? Not part of CI: it needs a browser and a bench.
 *
 * WHAT THIS PROVES AND WHAT IT DOES NOT. The page is the real one, rendered by a
 * real bench and run by a real browser. The check-in server answers are faked
 * here so each POST body can be read. THE BROWSER IS CHROMIUM PRETENDING TO BE AN
 * IPHONE. So this tests our JavaScript only. It says nothing about whether
 * Apple's camera opens, whether the photo comes out upright, or any other thing
 * an iPhone does. docs/slices/alv-297-iphone-camera/iphone-test-sheet.md is for that.
 *
 * HOW TO RUN (a bench serving a site with alvoraa_portal, on a secure address such
 * as 127.0.0.1, because the camera and location are refused elsewhere):
 *   BASE=http://127.0.0.1:8297 CHROME="C:/Program Files/Google/Chrome/Application/chrome.exe" \
 *   PLAYWRIGHT=<folder>/node_modules/playwright-core node scripts/browser_check_checkin_iphone_297.js
 *
 * PROVE=1 runs every test again against the page with its fix taken out (the
 * "without" pairs below, applied as the page is served, no file touched). Each of
 * those runs must FAIL. SHOTS=<folder> saves pictures of the screens.
 */
const fs = require("fs");
const path = require("path");
const { chromium } = require(process.env.PLAYWRIGHT || "playwright-core");

const BASE = process.env.BASE || "http://127.0.0.1:8297";
const PAGE = BASE + "/field-checkin";
const IPHONE = "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1";
const ANDROID = "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Mobile Safari/537.36";
const MAC = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Safari/605.1.15";
const LIMIT = 400 * 1024; // field_app_photos.py refuses anything bigger, silently
const TOO_FAR = "You are about 140 m from Sample Branch. You need to be within 100 m to check in.";

function check(ok, what) { if (!ok) throw new Error(what); }
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

let browser, bigPhoto, smallPhoto;

/* A noisy JPEG the size a phone makes, with a marked Exif block, so a raw file
   reaching the server can be seen by its size and by the marker. */
async function makePhoto(w, h) {
  const ctx = await browser.newContext();
  const page = await ctx.newPage();
  const b64 = await page.evaluate(async ([w, h]) => {
    const c = document.createElement("canvas"); c.width = w; c.height = h;
    const x = c.getContext("2d"), im = x.createImageData(w, h);
    for (let i = 0; i < im.data.length; i += 4) {
      im.data[i] = Math.random() * 255; im.data[i + 1] = Math.random() * 255;
      im.data[i + 2] = Math.random() * 255; im.data[i + 3] = 255;
    }
    x.putImageData(im, 0, 0);
    return c.toDataURL("image/jpeg", 0.9).split(",")[1];
  }, [w, h]);
  await ctx.close();
  const jpeg = Buffer.from(b64, "base64");
  const body = Buffer.from("Exif\0\0SECRET-GPS-MARKER");
  const app1 = Buffer.concat([Buffer.from([0xff, 0xe1, (body.length + 2) >> 8, (body.length + 2) & 255]), body]);
  return { name: "photo.jpg", mimeType: "image/jpeg", buffer: Buffer.concat([jpeg.subarray(0, 2), app1, jpeg.subarray(2)]) };
}
const NOT_AN_IMAGE = { name: "photo.jpg", mimeType: "image/jpeg", buffer: Buffer.from("this is not a picture") };

/* One fresh phone: its own storage, the page served (perhaps with a fix removed),
   and every check-in call answered here and written down. */
async function phone(without, { ua = IPHONE, touch = false, lang = "en", checkedIn = false } = {}) {
  const ctx = await browser.newContext({
    userAgent: ua, hasTouch: touch, viewport: { width: 390, height: 844 },
    geolocation: { latitude: 28.57, longitude: 77.32, accuracy: 14 }, permissions: ["geolocation"],
    serviceWorkers: "block",
  });
  const page = await ctx.newPage();
  page.setDefaultTimeout(6000);
  const p = { page, ctx, posts: [], statusCalls: 0, errors: [], answer: null, statusAnswer: null };
  page.on("pageerror", (e) => p.errors.push(String(e)));

  await page.addInitScript(({ lang, touch }) => {
    localStorage.setItem("alvoraa.field.v1", JSON.stringify({ token: "t".repeat(43), employee_name: "Test Person", lang }));
    window.__gum = 0; window.__busy = [];
    if (touch) Object.defineProperty(navigator, "maxTouchPoints", { get: () => 5 }); // what a real iPad reports
    const md = navigator.mediaDevices;
    if (md) { const real = md.getUserMedia.bind(md); md.getUserMedia = (c) => { window.__gum++; return real(c); }; }
    document.addEventListener("DOMContentLoaded", () => {
      const m = document.getElementById("busy-msg");
      new MutationObserver(() => window.__busy.push(m.textContent)).observe(m, { childList: true, characterData: true, subtree: true });
    });
  }, { lang, touch });

  await page.route("**/field-checkin", async (route) => {
    const res = await route.fetch();
    let html = await res.text();
    for (const [from, to] of without || []) {
      check(html.split(from).length === 2, "the 'without' text is not in the page exactly once: " + from);
      html = html.replace(from, () => to);
    }
    await route.fulfill({ response: res, body: html });
  });
  await page.route("**/api/method/alvoraa_portal.field_checkin.*", async (route) => {
    const name = route.request().url().split(".").pop();
    if (name === "field_status") {
      p.statusCalls++;
      if (p.statusAnswer) return p.statusAnswer(route);
      return route.fulfill({ json: { message: { employee_name: "Test Person", checked_in: checkedIn, todays_checkins: [], server_time: "2026-11-03 09:00:00" } } });
    }
    if (name === "field_checkin") {
      const body = route.request().postDataJSON();
      p.posts.push(body);
      if (p.answer) return p.answer(route, body);
      return route.fulfill({ json: { message: { status: "ok", log_type: body.log_type, time: "2026-11-03 09:01:00", employee_name: "Test Person" } } });
    }
    return route.abort();
  });
  await page.goto(PAGE);
  await page.waitForSelector("#s-home.on");
  await page.waitForFunction(() => document.getElementById("b-punch").getAttribute("data-type"));
  return p;
}

const on = (p, screen) => p.page.waitForSelector("#" + screen + ".on");
const text = (p, id) => p.page.locator("#" + id).innerText();
const visible = (p, id) => p.page.locator("#" + id).isVisible();
const gum = (p) => p.page.evaluate(() => window.__gum);
const busyOn = (p) => p.page.evaluate(() => document.getElementById("busy").classList.contains("on"));

/* Press Check In and return the camera it opened. */
async function tap(p) {
  const waiting = p.page.waitForEvent("filechooser", { timeout: 4000 });
  await p.page.click("#b-punch");
  return waiting;
}
async function photoSize(p, data) {
  return p.page.evaluate((d) => new Promise((ok, no) => {
    const i = new Image(); i.onload = () => ok([i.naturalWidth, i.naturalHeight]); i.onerror = () => no(new Error("the posted photo does not load")); i.src = d;
  }), data);
}
function assertGoodJpeg(photo) {
  check(photo && photo.startsWith("data:image/jpeg;base64,"), "the posted photo is not a JPEG data string");
  const bytes = Buffer.from(photo.split(",")[1], "base64");
  check(bytes[0] === 0xff && bytes[1] === 0xd8, "the posted bytes are not a JPEG");
  check(bytes.length < LIMIT, "the posted photo is " + bytes.length + " bytes, over the 400 KB limit");
  check(!bytes.includes("SECRET-GPS-MARKER") && !bytes.includes("Exif"), "the file's own Exif block was sent");
  return bytes.length;
}
async function refusedTooFar(route) {
  return route.fulfill({ status: 417, json: { _server_messages: JSON.stringify([JSON.stringify({ message: TOO_FAR })]) } });
}
async function alreadyRecorded(route) {
  return route.fulfill({ status: 417, json: { _server_messages: JSON.stringify([JSON.stringify({ message: "This punch is already recorded." })]) } });
}
/* A photo taken at home, refused as too far, and the clock moved on. */
async function refusedThenLater(p, minutes) {
  p.answer = refusedTooFar;
  (await tap(p)).setFiles(bigPhoto);
  await on(p, "s-err");
  p.answer = null;
  await p.page.evaluate((m) => { const n = Date.now; Date.now = () => n() + m * 60000; }, minutes);
}

const TESTS = [
  { name: "iPhone: never calls the live camera, and posts a JPEG under 400 KB", run: async (p) => {
      check(await gum(p) === 0, "the live camera was asked for on load");
      const chooser = await tap(p);
      await chooser.setFiles(bigPhoto);
      await on(p, "s-result");
      check(await gum(p) === 0, "the live camera was asked for during the punch");
      check(p.posts.length === 1, "expected one punch, got " + p.posts.length);
      const size = assertGoodJpeg(p.posts[0].photo);
      const [w, h] = await photoSize(p, p.posts[0].photo);
      check(w === 480 && h === 640, "expected 480 x 640, got " + w + " x " + h);
      check(!("captured_at" in p.posts[0]), "captured_at would mark the punch Recorded Offline");
      check(await text(p, "res-photo") === "Taken", "result should say Taken");
      const seen = await p.page.evaluate(() => window.__busy);
      check(seen.includes("Getting your photo ready"), "busy words after the shutter: " + seen);
      check(!seen.includes("Taking your photo"), "said Taking your photo after the shutter");
      console.log("      posted " + size + " bytes from a " + bigPhoto.buffer.length + " byte file");
    },
    without: [
      [["  if (PICKER) {", "  if (false) {"]],
      [["var w = 480, h", "var w = img.naturalWidth, h"]],
      [["shrink(file, function(photo){", "(function(f,d){var r=new FileReader();r.onload=function(){d(r.result)};r.readAsDataURL(f)})(file, function(photo){"]],
      [['busy(true, "busy.ready");', 'busy(true, "busy.photo");']],
    ] },
  { name: "iPhone: home shows the words, no video, no Turn on the camera button", run: async (p) => {
      check(await visible(p, "cam-picker"), "the camera message is not showing");
      const words = await text(p, "cam-picker");
      check(/camera opens/.test(words), "home tag missing: " + words);
      check(/close and reopen the app, or check in without a photo/.test(words), "the help line is missing: " + words);
      for (const id of ["video", "cam-tag", "cam-off", "b-cam-retry"]) check(!(await visible(p, id)), id + " should be hidden");
    },
    without: [
      [['$("video").hidden = true; $("cam-tag").hidden = true; $("cam-off").hidden = true;', ""]],
      [['$("cam-picker").hidden = false; $("cam").classList.add("picker");', ""]],
    ] },
  { name: "iPhone: the input is capture=user, image only, and not display:none", run: async (p) => {
      const a = await p.page.evaluate(() => {
        const i = document.getElementById("i-photo");
        return { capture: i.getAttribute("capture"), accept: i.accept, type: i.type, display: getComputedStyle(i).display };
      });
      check(a.capture === "user" && a.accept === "image/*" && a.type === "file", "wrong input: " + JSON.stringify(a));
      check(a.display !== "none", "the input is display:none");
    },
    without: [[['capture="user"', ""]], [['class="sronly" accept', 'style="display:none" accept']]] },
  { name: "iPhone: the tap opens the camera at once, before any busy screen or GPS", run: async (p) => {
      await p.page.evaluate(() => {
        window.__gps = 0; const g = navigator.geolocation.getCurrentPosition.bind(navigator.geolocation);
        navigator.geolocation.getCurrentPosition = (...a) => { window.__gps++; return g(...a); };
      });
      await tap(p);
      check(!(await busyOn(p)), "busy screen showed before the photo");
      check(await p.page.evaluate(() => window.__gps) === 0, "GPS started before the photo");
      check(p.posts.length === 0, "a punch went before the photo");
    },
    without: [[["if (PICKER) return openPicker(type);", "if (PICKER) { busy(true, \"busy.photo\"); return setTimeout(function(){ openPicker(type); }, 5500); }"]]] },
  { name: "iPhone: cancelling the camera does nothing, and it can be opened again", run: async (p) => {
      await tap(p);
      await p.page.evaluate(() => document.getElementById("i-photo").dispatchEvent(new Event("change")));
      await sleep(300);
      check(!(await busyOn(p)), "busy screen stuck after a cancel");
      check(p.posts.length === 0, "a punch went after a cancel");
      check(p.errors.length === 0, "script error: " + p.errors);
      await tap(p);
    },
    without: [[["if (!file || !waitingForPhoto) return;", "if (!waitingForPhoto) return;"]]] },
  { name: "iPhone: the no-photo link appears only after Check In, and posts no photo", run: async (p) => {
      check(!(await visible(p, "b-nophoto")), "the link shows before Check In was pressed");
      await tap(p);
      check(await visible(p, "b-nophoto"), "the link did not appear");
      await p.page.click("#b-nophoto");
      await on(p, "s-result");
      check(p.posts.length === 1 && p.posts[0].photo === null, "expected one punch with no photo");
      check(await text(p, "res-photo") === "Not taken", "result should say Not taken");
      const why = await text(p, "res-photo-why-text");
      check(!/camera was not on/.test(why) && /attendance still counts/.test(why), "untrue reason: " + why);
      await p.page.click("#b-res-done");
      await on(p, "s-home");
      check(!(await visible(p, "b-nophoto")), "the link should go away again until the next tap");
    },
    without: [
      [[".btn[hidden]{display:none}", ""]],
      [['$("b-nophoto").hidden = false;', ""]],
      [["pending = { log_type: pickerType, photo: null };", 'pending = { log_type: pickerType, photo: "x" };']],
      [["  $(\"b-nophoto\").hidden = true;", ""]],
      [['t(photoFailed ? "res.photo.why.failed" : "res.photo.why")', '"The camera was not on. Your attendance still counts."']],
    ] },
  { name: "iPhone: a photo arriving after the no-photo link sends no second punch", run: async (p) => {
      const chooser = await tap(p);
      await p.page.click("#b-nophoto");
      await on(p, "s-result");
      await chooser.setFiles(bigPhoto);
      await sleep(1500);
      check(p.posts.length === 1, "expected one punch, got " + p.posts.length);
    },
    without: [[["if (!file || !waitingForPhoto) return;", "if (!file) return;"]]] },
  { name: "iPhone: a file that will not load sends no photo and says so", run: async (p) => {
      (await tap(p)).setFiles(NOT_AN_IMAGE);
      await on(p, "s-result");
      check(p.posts.length === 1 && p.posts[0].photo === null, "the bad file was sent as a photo");
      check(await text(p, "res-photo") === "Not saved", "result should say Not saved");
      check(/could not use your photo/.test(await text(p, "res-photo-why-text")), "result does not say the photo failed");
    },
    without: [
      [["img.onerror = function(){ finish(null); };", 'img.onerror = function(){ finish("data:,"); };']],
      [['photoFailed ? "res.photo.failed" : "res.photo.no"', '"res.photo.no"']],
      [['t(photoFailed ? "res.photo.why.failed" : "res.photo.why")', 't("res.photo.why")']],
    ] },
  { name: "iPhone: a canvas that gives back junk sends no photo and says so", run: async (p) => {
      await p.page.evaluate(() => { HTMLCanvasElement.prototype.toDataURL = () => "data:,"; });
      (await tap(p)).setFiles(bigPhoto);
      await on(p, "s-result");
      check(p.posts.length === 1 && p.posts[0].photo === null, "junk was sent as a photo");
      check(await text(p, "res-photo") === "Not saved", "result should say Not saved");
    },
    without: [[['if (out.indexOf("data:image/jpeg") === 0) photo = out;', "photo = out;"]]] },
  { name: "iPhone: too far, and Try again inside 10 minutes resends the same photo", run: async (p) => {
      await refusedThenLater(p, 5);
      await p.page.click("#b-err-1");
      await on(p, "s-result");
      check(p.posts.length === 2 && p.posts[1].photo === p.posts[0].photo, "the photo was not resent");
    },
    without: [[["Date.now() - pending.takenAt > PHOTO_TOO_OLD", "true"]]] },
  { name: "iPhone: too far, and Try again after 10 minutes reopens the camera", run: async (p) => {
      await refusedThenLater(p, 11);
      const waiting = p.page.waitForEvent("filechooser", { timeout: 4000 });
      await p.page.click("#b-err-1");
      const chooser = await waiting;
      check(p.posts.length === 1, "the old photo was resent");
      await chooser.setFiles(smallPhoto);
      await on(p, "s-result");
      check(p.posts.length === 2, "expected a second punch with the new photo");
      const [, h] = await photoSize(p, p.posts[1].photo);
      check(h === 360, "the new photo was not the one sent");
      check(!("captured_at" in p.posts[1]), "captured_at would mark the punch Recorded Offline");
    },
    without: [[["pending && PICKER && pending.tooFar && ", "false && "]]] },
  { name: "iPhone: no signal, even after 10 minutes, keeps the photo and resends it", run: async (p) => {
      p.answer = (route) => route.abort();
      (await tap(p)).setFiles(bigPhoto);
      await on(p, "s-err");
      p.answer = null;
      await p.page.evaluate(() => { const n = Date.now; Date.now = () => n() + 660000; });
      await p.page.click("#b-err-1");
      await on(p, "s-result");
      check(p.posts.length === 2 && p.posts[1].photo === p.posts[0].photo, "the photo was not resent");
    },
    without: [[['if (kind === "OUTSIDE" && pending) pending.tooFar = true;', "if (pending) pending.tooFar = true;"]]] },
  { name: "iPhone: coming back with the camera shut still asks for status, and a failed answer draws no error", run: async (p) => {
      await tap(p);
      const before = p.statusCalls;
      p.statusAnswer = (route) => route.abort();
      await p.page.evaluate(() => document.dispatchEvent(new Event("visibilitychange")));
      await sleep(400);
      check(p.statusCalls === before + 1, "status was not asked for on return");
      check(await p.page.locator("#s-home.on").count() === 1, "the error screen was drawn");
    },
    without: [
      [["else if (PICKER && waitingForPhoto) {", "else if (PICKER && waitingForPhoto) { return;"]],
      [["}).catch(function(){});", "}).catch(function(e){ handle(e); });"]],
    ] },
  { name: "iPhone: Cancel at night, app left open: in the morning the button and the punch say Check In", opts: { checkedIn: true }, run: async (p) => {
      await tap(p);                                 // Check Out, then Cancel: iPhone tells us nothing
      check(await p.page.locator("#b-punch").getAttribute("data-type") === "OUT", "should start checked in");
      p.statusAnswer = (route) => route.fulfill({ json: { message: { employee_name: "Test Person", checked_in: false, todays_checkins: [], server_time: "2026-11-04 09:00:00" } } });
      await p.page.evaluate(() => document.dispatchEvent(new Event("visibilitychange")));
      await p.page.waitForFunction(() => document.getElementById("b-punch").getAttribute("data-type") === "IN");
      check(await text(p, "b-nophoto") === "Check in without a photo", "the link still says " + await text(p, "b-nophoto"));
      await p.page.click("#b-nophoto");             // the link, without pressing the button again
      await on(p, "s-result");
      check(p.posts[0].log_type === "IN", "posted " + p.posts[0].log_type + " at the start of the day");
    },
    without: [
      [["else if (PICKER && waitingForPhoto) {", "else if (PICKER && waitingForPhoto) { return;"]],
      [['pickerType = $("b-punch").getAttribute("data-type") || pickerType;', ""]],
    ] },
  { name: "iPhone: Cancel at night, app left open: the big button also sends Check In", opts: { checkedIn: true }, run: async (p) => {
      await tap(p);
      p.statusAnswer = (route) => route.fulfill({ json: { message: { employee_name: "Test Person", checked_in: false, todays_checkins: [], server_time: "2026-11-04 09:00:00" } } });
      await p.page.evaluate(() => document.dispatchEvent(new Event("visibilitychange")));
      await p.page.waitForFunction(() => document.getElementById("b-punch").getAttribute("data-type") === "IN");
      (await tap(p)).setFiles(smallPhoto);
      await on(p, "s-result");
      check(p.posts[0].log_type === "IN", "posted " + p.posts[0].log_type);
    },
    without: [[["else if (PICKER && waitingForPhoto) {", "else if (PICKER && waitingForPhoto) { return;"]]] },
  { name: "iPhone: a one-action error screen shows no dead second button", run: async (p) => {
      p.answer = alreadyRecorded;
      (await tap(p)).setFiles(smallPhoto);
      await on(p, "s-err");
      check(await visible(p, "b-err-1"), "the one real button is missing");
      check(!(await visible(p, "b-err-2")), "a dead button shows: " + await text(p, "b-err-2"));
    },
    without: [[[".btn[hidden]{display:none}", ""]]] },
  { name: "Android: a one-action error screen shows no dead second button", opts: { ua: ANDROID }, run: async (p) => {
      await p.page.waitForFunction(() => document.getElementById("video").readyState >= 2);
      p.answer = alreadyRecorded;
      await p.page.click("#b-punch");
      await on(p, "s-err");
      check(!(await visible(p, "b-err-2")), "a dead button shows: " + await text(p, "b-err-2"));
    },
    without: [[[".btn[hidden]{display:none}", ""]]] },
  { name: "iPhone: coming back while the punch is being sent does not refresh either", run: async (p) => {
      let release;
      p.answer = async (route, body) => { await new Promise((r) => { release = r; });
        return route.fulfill({ json: { message: { status: "ok", log_type: body.log_type, time: "2026-11-03 09:01:00" } } }); };
      (await tap(p)).setFiles(bigPhoto);
      await p.page.waitForFunction(() => document.getElementById("busy-msg").textContent === "Saving your attendance");
      const before = p.statusCalls;
      p.statusAnswer = (route) => route.abort();
      await p.page.evaluate(() => document.dispatchEvent(new Event("visibilitychange")));
      await sleep(400);
      check(p.statusCalls === before, "a refresh ran while the punch was being sent");
      p.statusAnswer = null;
      release();
      await on(p, "s-result");
    },
    without: [[['else if (PICKER && $("busy").classList.contains("on")) { return; }', ""]]] },
  { name: "iPhone: when already checked in, the link says Check out and posts OUT", opts: { checkedIn: true }, run: async (p) => {
      await tap(p);
      check(await text(p, "b-nophoto") === "Check out without a photo", "wrong words: " + await text(p, "b-nophoto"));
      await p.page.click("#b-nophoto");
      await on(p, "s-result");
      check(p.posts[0].log_type === "OUT", "posted " + p.posts[0].log_type);
    },
    without: [[['t(inNow ? "home.nophoto.out" : "home.nophoto.in")', 't("home.nophoto.in")']]] },
  { name: "iPhone, Hindi: the home words, the link, and the result line are in Hindi", opts: { lang: "hi" }, run: async (p) => {
      check(/कैमरा खुल जाएगा/.test(await text(p, "cam-picker")), "home words not in Hindi");
      await tap(p);
      check(await text(p, "b-nophoto") === "बिना फ़ोटो के चेक इन करें", "link not in Hindi");
      await p.page.click("#b-nophoto");
      await on(p, "s-result");
      check(/सेव नहीं हुई/.test(await text(p, "res-photo-why-text")), "result line not in Hindi");
    },
    without: [
      [["इस हाज़िरी के साथ कोई फ़ोटो सेव नहीं हुई। आपकी हाज़िरी फिर भी गिनी जाएगी।", "No photo was saved with this punch."]],
      [["नीचे का बटन दबाएँ, कैमरा खुल जाएगा।", "Press the button."]],
    ] },
  { name: "Android: still calls the live camera, opens no picker, posts its frame", opts: { ua: ANDROID }, run: async (p) => {
      await p.page.waitForFunction(() => window.__gum > 0);
      await p.page.waitForFunction(() => document.getElementById("video").readyState >= 2);
      let choosers = 0;
      p.page.on("filechooser", () => choosers++);
      check(!(await visible(p, "cam-picker")), "Android shows the iPhone words");
      check(!(await visible(p, "b-nophoto")), "Android shows the no-photo link");
      await p.page.click("#b-punch");
      await on(p, "s-result");
      check(choosers === 0, "Android opened the file picker");
      assertGoodJpeg(p.posts[0].photo);
    },
    without: [[["var PICKER = !SAMPLE && (", "var PICKER = !SAMPLE && (true || "]]] },
  { name: "Android: too far, after 10 minutes, Try again resends as it did before", opts: { ua: ANDROID }, run: async (p) => {
      await p.page.waitForFunction(() => document.getElementById("video").readyState >= 2);
      p.answer = refusedTooFar;
      await p.page.click("#b-punch");
      await on(p, "s-err");
      p.answer = null;
      await p.page.evaluate(() => { const n = Date.now; Date.now = () => n() + 660000; });
      await p.page.click("#b-err-1");
      await on(p, "s-result");
      check(p.posts.length === 2 && p.posts[1].photo === p.posts[0].photo, "Android retry changed");
    },
    without: [[["var PICKER = !SAMPLE && (", "var PICKER = !SAMPLE && (true || "]]] },
  { name: "iPad saying Macintosh, with touch: treated as iPhone", opts: { ua: MAC, touch: true }, run: async (p) => {
      check(await gum(p) === 0, "the live camera was asked for");
      await tap(p);
    },
    without: [[["(/Macintosh/.test(navigator.userAgent) && navigator.maxTouchPoints > 1)", "false"]]] },
  { name: "A real Mac, no touch: stays on the live camera", opts: { ua: MAC }, run: async (p) => {
      await p.page.waitForFunction(() => window.__gum > 0);
      check(!(await visible(p, "cam-picker")), "a Mac shows the iPhone words");
    },
    without: [[["navigator.maxTouchPoints > 1", "true"]]] },
];

async function runOne(t, without) {
  const p = await phone(without, t.opts);
  try {
    await t.run(p);
    check(p.errors.length === 0, "script error: " + p.errors);
  } finally {
    await p.ctx.close();
  }
}

async function shots(dir) {
  fs.mkdirSync(dir, { recursive: true });
  const snap = (p, n) => p.page.screenshot({ path: path.join(dir, n + ".png") });
  let p = await phone(null);
  await snap(p, "iphone-home");
  const c = await tap(p);
  await snap(p, "iphone-home-after-tap");
  await c.setFiles(bigPhoto); await on(p, "s-result"); await snap(p, "iphone-result-photo"); await p.ctx.close();
  p = await phone(null); await tap(p); await p.page.click("#b-nophoto"); await on(p, "s-result"); await snap(p, "iphone-result-no-photo"); await p.ctx.close();
  p = await phone(null, { lang: "hi" }); await snap(p, "iphone-home-hindi"); await p.ctx.close();
  p = await phone(null, { ua: ANDROID }); await p.page.waitForFunction(() => document.getElementById("video").readyState >= 2); await snap(p, "android-home"); await p.ctx.close();
}

(async () => {
  browser = await chromium.launch({
    executablePath: process.env.CHROME || undefined,
    args: ["--use-fake-device-for-media-stream", "--use-fake-ui-for-media-stream"],
  });
  bigPhoto = await makePhoto(3024, 4032);
  smallPhoto = await makePhoto(2000, 1500);
  let failed = 0;
  for (const t of TESTS) {
    try { await runOne(t, null); console.log("ok    " + t.name); }
    catch (e) { failed++; console.log("FAIL  " + t.name + "\n      " + String(e.message).split("\n")[0]); }
  }
  console.log((TESTS.length - failed) + " of " + TESTS.length + " passed");

  if (process.env.PROVE) {
    let runs = 0, wrong = 0;
    for (const t of TESTS) {
      for (const without of t.without) {
        runs++;
        try {
          await runOne(t, without);
          wrong++;
          console.log("STILL PASSES with the fix removed: " + t.name + "\n      " + without[0][0]);
        } catch (e) {
          if (/not in the page exactly once/.test(e.message)) { wrong++; console.log("BAD PROOF: " + e.message); }
          else console.log("proved  " + t.name + "  <-  " + String(e.message).split("\n")[0].slice(0, 90));
        }
      }
    }
    console.log(runs - wrong + " of " + runs + " removals made a test fail");
    failed += wrong;
  }
  if (process.env.SHOTS) await shots(process.env.SHOTS);
  await browser.close();
  process.exit(failed ? 1 : 0);
})();
