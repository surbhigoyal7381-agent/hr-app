/*
 * Reading a QR code from a camera frame or a chosen picture. Slice 013 stage-2
 * spike: US-35, AC-183, AC-184.
 *
 * Deliberately a pure-JS decoder (jsQR), not a native barcode-scanning plugin
 * (ML Kit or similar), for three reasons written up in
 * docs/slices/013-mobile-app/00-impact-analysis-app-client.md §5 and agreed by
 * Surbhi on 2026-09-21:
 *
 *   1. No new Android permission: it reads pixels the app already has through
 *      the CAMERA permission it holds for the punch photo. A native scanner
 *      plugin would add its own permission surface to re-audit.
 *   2. Provable in a plain Node test, the same way host-check.js already is -
 *      no emulator, no device, no bench.
 *   3. Some pilot phones may have no Google Play services (the pilot phone
 *      table, AC-231, tracks this per phone) - an ML-Kit-backed plugin would
 *      not run there; this will.
 *
 * This file does the decoding only - reading a frame, finding a QR code,
 * returning its text. It does not touch the camera, does not decide what a
 * decoded string MEANS (that is host-check.js's job, matched against the
 * decoded text), and does not know about screens. It never uploads or stores
 * the image it is given (PRIV-7): the pixel data lives only for the length of
 * this call.
 *
 * jsQR is vendored, not resolved from node_modules at build time (there is no
 * bundler step) - see web/js/vendor/README.md and jsqr.js's pinned SHA-256 in
 * scripts/check_app.mjs.
 */
(function (root) {
  "use strict";

  /*
   * imageData  { data: Uint8ClampedArray, width: number, height: number } -
   *            exactly the shape both a canvas 2D context's getImageData()
   *            and jsQR itself expect, so the caller (a camera-frame loop,
   *            or a photo picker's decoded picture) needs no adapter.
   *
   * jsQRFn     the decoder function itself, defaulting to the vendored
   *            global (window.jsQR in the app, set by the <script> tag for
   *            web/js/vendor/jsqr.js). Accepting it as an argument, rather
   *            than always reaching for the global, is what lets a Node test
   *            call this with no browser and no DOM at all - the same reason
   *            photo.js takes `makeCanvas` as a parameter instead of always
   *            calling document.createElement itself.
   *
   * Returns { text: string } on a QR code found and read, or null. Throws
   * nothing on a frame with no code: a corrupt or unreadable frame is just
   * "not found this time", the same way a camera scan misses a frame and
   * tries the next one. It DOES throw if the decoder itself is missing -
   * failing closed, never silently treating "not loaded" as "no code here".
   */
  function decode(imageData, jsQRFn) {
    if (!imageData || !imageData.data || !imageData.width || !imageData.height) {
      return null;
    }
    var jsQR = jsQRFn || (typeof globalThis !== "undefined" ? globalThis.jsQR : undefined);
    if (typeof jsQR !== "function") {
      throw new Error("jsQR is not loaded (web/js/vendor/jsqr.js).");
    }
    var result = jsQR(imageData.data, imageData.width, imageData.height, {
      // "attemptBoth" also tries the image inverted (light-on-dark), which
      // costs almost nothing and helps on a screen showing a QR code, not
      // only a printed sheet - relevant for MA-5, "pick from photos" sent on
      // WhatsApp, since a photo of a screen is common there.
      inversionAttempts: "attemptBoth",
    });
    if (!result || !result.data) return null;
    return { text: result.data };
  }

  var api = { decode: decode };

  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  } else {
    root.AlvoraaQr = api;
  }
})(typeof window !== "undefined" ? window : this);
