/*
 * The check-in camera: a live preview the person can see, a photo they take
 * themselves, and a still they can use or take again. Slice 013, fix of
 * 27 Sep 2026.
 *
 * Why it exists: until 0.2.1 the punch opened the front camera on a hidden
 * <video> and kept the first frame. The person never saw the camera, yet the
 * result said "Photo taken". Now nothing is taken until the person presses
 * "Take photo", and nothing is sent until they press "Use photo".
 *
 * This file holds the steps and the one rule that matters most - the camera
 * stream is stopped on every way out (use, cancel, a failure, the app going
 * to the background). It does not touch the screen: checkin.js draws the
 * buttons from the state this returns. Everything it needs from the browser
 * (getUserMedia, the <video>, the shrink) is passed in, so the Node tests can
 * run every step with a fake camera.
 *
 * The photo stays in memory only, as before (PRIV-7). Its size rules are
 * photo.js's, unchanged.
 *
 * States:
 *   idle         nothing open yet
 *   opening      asked the phone for the camera, waiting
 *   live         the preview is showing; "Take photo" works
 *   still        a photo was taken and the stream is stopped
 *   denied       the person (or the phone) said no to the camera
 *   unavailable  this phone has no camera the app can use
 *   closed       used or cancelled; the stream is stopped
 */
(function (root) {
  "use strict";

  var CONSTRAINTS = {
    video: { facingMode: "user", width: { ideal: 960 }, height: { ideal: 720 } },
    audio: false,
  };

  function isDenial(err) {
    var name = err && err.name;
    return name === "NotAllowedError" || name === "SecurityError" || name === "PermissionDeniedError";
  }

  /*
   * deps = {
   *   getUserMedia(constraints) -> Promise<MediaStream>   (absent = no camera)
   *   video                     the <video> element for the preview
   *   shrink(video, w, h)       -> { dataUrl } or null    (photo.js's shrinkToJpeg)
   *   now()                     -> Date                   (optional, for tests)
   * }
   */
  function createCamera(deps) {
    var stream = null;
    var state = "idle";
    var photo = null;       // { dataUrl, takenAt }
    var openCount = 0;      // which open() call is the current one

    function stopStream() {
      if (stream) {
        stream.getTracks().forEach(function (t) { t.stop(); });
        stream = null;
      }
      if (deps.video) {
        try { deps.video.pause && deps.video.pause(); } catch (e) { /* nothing to pause */ }
        deps.video.srcObject = null;
      }
    }

    function open() {
      stopStream();
      photo = null;
      if (typeof deps.getUserMedia !== "function") {
        state = "unavailable";
        return Promise.resolve(state);
      }
      state = "opening";
      var mine = ++openCount;
      var asked;
      try {
        asked = Promise.resolve(deps.getUserMedia(CONSTRAINTS));
      } catch (e) {
        asked = Promise.reject(e);
      }
      return asked.then(function (s) {
        if (mine !== openCount || state !== "opening") {
          // Cancelled (or re-opened) while the phone was still asking. The
          // late stream must not stay on with nobody looking at it.
          s.getTracks().forEach(function (t) { t.stop(); });
          return state;
        }
        stream = s;
        deps.video.srcObject = s;
        var played = deps.video.play && deps.video.play();
        if (played && played.catch) played.catch(function () { /* autoplay refusal: the preview still attaches */ });
        state = "live";
        return state;
      }, function (err) {
        if (mine !== openCount || state !== "opening") return state;
        stopStream();
        state = isDenial(err) ? "denied" : "unavailable";
        return state;
      });
    }

    // True once the preview has a real picture to take.
    function ready() {
      return state === "live" && !!(deps.video && deps.video.videoWidth && deps.video.videoHeight);
    }

    function take() {
      if (!ready()) return false;
      var shrunk = deps.shrink(deps.video, deps.video.videoWidth, deps.video.videoHeight);
      if (!shrunk || !shrunk.dataUrl) return false;
      photo = { dataUrl: shrunk.dataUrl, takenAt: deps.now ? deps.now() : new Date() };
      // The camera light goes off the moment the photo exists. Retake opens it again.
      stopStream();
      state = "still";
      return true;
    }

    function retake() {
      return open();
    }

    // Hands the photo over and closes. Null when there is no photo to use.
    function use() {
      var taken = state === "still" ? photo : null;
      stopStream();
      state = "closed";
      photo = null;
      return taken;
    }

    function cancel() {
      openCount++;
      stopStream();
      state = "closed";
      photo = null;
    }

    // The app went to the background. A live preview is stopped; a still is
    // kept (its stream is already off). Returns true when the caller should
    // open the preview again once the app is back.
    function pause() {
      if (state === "live" || state === "opening") {
        openCount++;
        stopStream();
        state = "idle";
        return true;
      }
      return false;
    }

    return {
      open: open,
      take: take,
      retake: retake,
      use: use,
      cancel: cancel,
      pause: pause,
      ready: ready,
      state: function () { return state; },
      stillDataUrl: function () { return photo ? photo.dataUrl : null; },
      hasStream: function () { return !!stream; },
    };
  }

  var api = { createCamera: createCamera, CONSTRAINTS: CONSTRAINTS };

  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  } else {
    root.AlvoraaCamera = api;
  }
})(typeof window !== "undefined" ? window : this);
