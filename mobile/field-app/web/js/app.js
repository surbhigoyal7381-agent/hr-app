/*
 * First phone test (slice 013). No server call, no storage, no QR scanning yet.
 *
 * It exercises the two things a cheap Android phone has to get right before any
 * of the attendance screens are worth building: the camera inside the web view,
 * and a position good enough to check in with (accuracy at or under 100 m, the
 * server's rule in field_checkin.py).
 *
 * Every piece of text on the screen is set with textContent, never as HTML
 * (SEC-17), which also keeps scripts/check_app.mjs green.
 */
(function () {
  "use strict";

  var MAX_ACCURACY_METRES = 100;   // the server's rule, shown here for the test
  var LOCATION_TIMEOUT_MS = 20000; // 01b: no fix within 20 seconds is "slow"

  var el = function (id) { return document.getElementById(id); };
  var stream = null;

  function say(id, text) { el(id).textContent = text; }

  function buildLine() {
    // No version call anywhere: the build number arrives with the real screens.
    say("build-line", "Debug build - for testing on a phone, not for workers.");
  }

  function startCamera() {
    say("cam-state", "Asking for the camera...");
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      say("cam-state", "This phone's browser gives the app no camera.");
      return;
    }
    navigator.mediaDevices.getUserMedia({
      video: { facingMode: "environment", width: { ideal: 1280 }, height: { ideal: 960 } },
      audio: false
    }).then(function (s) {
      stream = s;
      var view = el("cam-view");
      view.srcObject = s;
      view.hidden = false;
      view.play();
      el("b-shot").hidden = false;
      say("cam-state", "The camera is on. Point it at something and take the photo.");
    }).catch(function (err) {
      say("cam-state", "The camera did not start: " + (err && err.name ? err.name : "unknown")
        + ". If the phone asked and you said no, allow the camera in Android settings.");
    });
  }

  function takePhoto() {
    var view = el("cam-view");
    var shrunk = window.AlvoraaPhoto.shrinkToJpeg(view, view.videoWidth, view.videoHeight);
    if (!shrunk) {
      say("cam-state", "The camera has not given a picture yet. Try again in a second.");
      return;
    }
    var shot = el("cam-shot");
    shot.src = shrunk.dataUrl;
    shot.hidden = false;
    view.hidden = true;
    if (stream) { stream.getTracks().forEach(function (t) { t.stop(); }); stream = null; }
    el("b-shot").hidden = true;
    el("b-cam").textContent = "Turn the camera on again";
    say("cam-state", "Photo taken. It is only in this app's memory.");
    say("cam-facts", shrunk.width + " by " + shrunk.height + " pixels, "
      + Math.round(shrunk.bytes / 1024) + " KB, quality " + shrunk.quality
      + (shrunk.tooBig ? " - TOO BIG, over 150 KB" : " - within the 150 KB limit"));
  }

  function findLocation() {
    say("loc-state", "Looking for your position...");
    say("loc-facts", "");
    if (!navigator.geolocation) {
      say("loc-state", "This phone's browser gives the app no location.");
      return;
    }
    var started = Date.now();
    navigator.geolocation.getCurrentPosition(function (pos) {
      var seconds = ((Date.now() - started) / 1000).toFixed(1);
      var accuracy = Math.round(pos.coords.accuracy);
      say("loc-state", accuracy <= MAX_ACCURACY_METRES
        ? "Good enough to check in with."
        : "Too vague to check in with. Step outside and try again.");
      // Deliberately no latitude or longitude on screen: this test is about
      // whether the phone can place itself, not about where anybody is.
      say("loc-facts", "Accurate to about " + accuracy + " m (the limit is "
        + MAX_ACCURACY_METRES + " m), found in " + seconds + " seconds.");
    }, function (err) {
      say("loc-state", err && err.code === 1
        ? "You said no to location. Allow it in Android settings, then try again."
        : "No position yet. Location may be switched off, or the sky may be blocked.");
    }, { enableHighAccuracy: true, timeout: LOCATION_TIMEOUT_MS, maximumAge: 0 });
  }

  document.addEventListener("DOMContentLoaded", function () {
    buildLine();
    el("b-cam").addEventListener("click", startCamera);
    el("b-shot").addEventListener("click", takePhoto);
    el("b-loc").addEventListener("click", findLocation);
  });
})();
