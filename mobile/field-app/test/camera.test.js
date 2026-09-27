// Check-in fix of 27 Sep 2026: the camera must be visible. Until 0.2.1 the
// punch grabbed the first frame of a hidden <video>, so the person never saw
// the camera and the result still said "Photo taken".
//
// There is no browser here, so camera.js is driven with a fake getUserMedia,
// a fake <video> and a fake shrink. Every step is exercised - preview, take,
// retake, use, cancel, denied, no camera, the app going to the background -
// and after each way out the fake camera's tracks must all be stopped.
"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const path = require("node:path");
const fs = require("node:fs");

const { createCamera, CONSTRAINTS } = require(
  path.join(__dirname, "..", "web", "js", "camera.js"));

function fakeStream() {
  const tracks = [{ stopped: false, stop() { this.stopped = true; } }];
  return { tracks, getTracks: () => tracks, allStopped: () => tracks.every((t) => t.stopped) };
}

function fakeVideo() {
  return {
    srcObject: null, videoWidth: 0, videoHeight: 0, playing: false,
    play() { this.playing = true; this.videoWidth = 960; this.videoHeight = 720; return Promise.resolve(); },
    pause() { this.playing = false; },
  };
}

function rig(opts) {
  opts = opts || {};
  const streams = [];
  const asked = [];
  const video = fakeVideo();
  const shrinkCalls = [];
  const cam = createCamera({
    getUserMedia: opts.noCamera ? null : (c) => {
      asked.push(c);
      if (opts.fail) return Promise.reject(opts.fail);
      const s = fakeStream();
      streams.push(s);
      return opts.slow ? new Promise((r) => { opts.release = () => r(s); }) : Promise.resolve(s);
    },
    video,
    shrink: (src, w, h) => { shrinkCalls.push([w, h]); return opts.shrinkFails ? null : { dataUrl: "data:image/jpeg;base64,AAAA" }; },
    now: () => new Date(Date.UTC(2026, 8, 27, 8, 35, 0)),
  });
  return { cam, streams, asked, video, shrinkCalls, opts };
}

test("open shows a live front-camera preview, and nothing is taken until the person presses Take photo", async () => {
  const r = rig();
  assert.equal(await r.cam.open(), "live");
  assert.equal(r.asked[0].video.facingMode, "user");
  assert.equal(r.asked[0].audio, false);
  assert.equal(r.video.srcObject, r.streams[0]);
  assert.ok(r.video.playing);
  assert.equal(r.shrinkCalls.length, 0, "no photo is taken on its own");
  assert.equal(r.cam.stillDataUrl(), null);
});

test("Take photo keeps a still, uses photo.js's shrink, and turns the camera off", async () => {
  const r = rig();
  await r.cam.open();
  assert.equal(r.cam.take(), true);
  assert.equal(r.cam.state(), "still");
  assert.deepEqual(r.shrinkCalls, [[960, 720]]);
  assert.equal(r.cam.stillDataUrl(), "data:image/jpeg;base64,AAAA");
  assert.ok(r.streams[0].allStopped(), "stream stopped once the photo exists");
  assert.equal(r.video.srcObject, null);
});

test("Use photo hands over the photo and its time, and closes", async () => {
  const r = rig();
  await r.cam.open();
  r.cam.take();
  const photo = r.cam.use();
  assert.equal(photo.dataUrl, "data:image/jpeg;base64,AAAA");
  assert.equal(photo.takenAt.toISOString(), "2026-09-27T08:35:00.000Z");
  assert.equal(r.cam.state(), "closed");
  assert.equal(r.cam.hasStream(), false);
  assert.ok(r.streams.every((s) => s.allStopped()));
});

test("Retake drops the still and opens a new live preview", async () => {
  const r = rig();
  await r.cam.open();
  r.cam.take();
  assert.equal(await r.cam.retake(), "live");
  assert.equal(r.cam.stillDataUrl(), null);
  assert.equal(r.streams.length, 2);
  assert.ok(r.streams[0].allStopped());
  r.cam.take();
  assert.ok(r.cam.use());
  assert.ok(r.streams.every((s) => s.allStopped()));
});

test("Cancel from the live preview stops the stream and sends nothing", async () => {
  const r = rig();
  await r.cam.open();
  r.cam.cancel();
  assert.equal(r.cam.state(), "closed");
  assert.ok(r.streams[0].allStopped());
  assert.equal(r.cam.use(), null, "nothing to hand over after a cancel");
});

test("Cancel from the still drops the photo", async () => {
  const r = rig();
  await r.cam.open();
  r.cam.take();
  r.cam.cancel();
  assert.equal(r.cam.stillDataUrl(), null);
  assert.equal(r.cam.use(), null);
});

test("Cancel while the phone is still asking: the late stream is stopped at once", async () => {
  const r = rig({ slow: true });
  const opening = r.cam.open();
  assert.equal(r.cam.state(), "opening");
  r.cam.cancel();
  r.opts.release();
  assert.equal(await opening, "closed");
  assert.ok(r.streams[0].allStopped());
  assert.equal(r.video.srcObject, null);
});

test("Take photo before the first frame does nothing (the button waits)", async () => {
  const r = rig();
  await r.cam.open();
  r.video.videoWidth = 0;
  assert.equal(r.cam.ready(), false);
  assert.equal(r.cam.take(), false);
  assert.equal(r.cam.state(), "live");
});

test("a failed shrink keeps the preview and takes nothing", async () => {
  const r = rig({ shrinkFails: true });
  await r.cam.open();
  assert.equal(r.cam.take(), false);
  assert.equal(r.cam.state(), "live");
});

test("permission denied: its own state, so the app can say so and offer Try again", async () => {
  const err = new Error("no"); err.name = "NotAllowedError";
  const r = rig({ fail: err });
  assert.equal(await r.cam.open(), "denied");
  assert.equal(r.cam.hasStream(), false);
});

test("another camera error, or no camera API at all: unavailable", async () => {
  const err = new Error("busy"); err.name = "NotReadableError";
  assert.equal(await rig({ fail: err }).cam.open(), "unavailable");
  assert.equal(await rig({ noCamera: true }).cam.open(), "unavailable");
});

test("Try again after a denial opens the camera again", async () => {
  const err = new Error("no"); err.name = "NotAllowedError";
  const r = rig({ fail: err });
  assert.equal(await r.cam.open(), "denied");
  r.opts.fail = null;
  assert.equal(await r.cam.open(), "live");
});

test("the app going to the background stops a live preview and asks to reopen it", async () => {
  const r = rig();
  await r.cam.open();
  assert.equal(r.cam.pause(), true);
  assert.ok(r.streams[0].allStopped());
  assert.equal(r.cam.state(), "idle");
  assert.equal(await r.cam.open(), "live");
});

test("the app going to the background with a still: nothing to stop, the photo is kept", async () => {
  const r = rig();
  await r.cam.open();
  r.cam.take();
  assert.equal(r.cam.pause(), false);
  assert.equal(r.cam.state(), "still");
  assert.ok(r.cam.use());
});

test("the constraints ask for the front camera at the old size, no sound", () => {
  assert.deepEqual(CONSTRAINTS, {
    video: { facingMode: "user", width: { ideal: 960 }, height: { ideal: 720 } },
    audio: false,
  });
});

test("checkin.js has no hidden-video capture left, and the camera screen has its buttons", () => {
  const web = path.join(__dirname, "..", "web");
  const src = fs.readFileSync(path.join(web, "js", "checkin.js"), "utf8");
  assert.doesNotMatch(src, /document\.createElement\("video"\)/);
  assert.doesNotMatch(src, /capturePunchPhoto/);
  const html = fs.readFileSync(path.join(web, "index.html"), "utf8");
  for (const action of ["checkin-camera-take", "checkin-camera-use", "checkin-camera-retake",
                        "checkin-camera-cancel", "checkin-camera-try-again", "checkin-camera-no-photo"]) {
    assert.match(html, new RegExp(`data-action="${action}"`), action);
    assert.match(src, new RegExp(`"${action}":`), action);
  }
  assert.match(html, /data-screen="camera"/);
  assert.match(html, /<script src="js\/camera\.js"><\/script>/);
});

test("join.js's QR scanner shows its preview on screen (it never captured silently)", () => {
  const src = fs.readFileSync(path.join(__dirname, "..", "web", "js", "join.js"), "utf8");
  assert.match(src, /el\("scan-video"\)/);
  assert.doesNotMatch(src, /document\.createElement\("video"\)/);
});
