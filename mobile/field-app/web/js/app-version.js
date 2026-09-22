/*
 * The one place the app's own version number is written down. Sent on every
 * server call as X-Alvoraa-App-Version (OPS-8, AC-203), and shown on the
 * About/settings screen once that exists (US-43, not built yet).
 *
 * Must match android/app/build.gradle's versionName exactly - a mismatch
 * would mean the server enforces a minimum version against a number the app
 * never actually sends. scripts/check_app.mjs pins the two together, the same
 * way it pins jsQR's hash, so this can never quietly drift.
 */
(function (root) {
  "use strict";

  var APP_VERSION = "0.1.0";

  var api = { APP_VERSION: APP_VERSION };

  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  } else {
    root.AlvoraaVersion = api;
  }
})(typeof window !== "undefined" ? window : this);
