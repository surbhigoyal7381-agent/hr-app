/*
 * Which of the three build types (US-32) this bundle is running as -
 * host-check.js needs it to decide whether a *.dev.alvoraa.co host is allowed
 * (pilot and debug only, never release - AC-172).
 *
 * This file is the DEFAULT, copied into every build by `npx cap copy`
 * (web/ -> android/app/src/main/assets/public/). It says "release" - the
 * most restrictive answer - so a build that forgot to override it fails
 * SAFE (refuses a dev host) rather than fails open.
 *
 * The real per-build-type value comes from Android's own source-set asset
 * merging, the same mechanism android/app/src/debug/res/xml/
 * network_security_config.xml already uses for the debug-only cleartext
 * allow-list:
 *
 *   android/app/src/debug/assets/public/js/build-type.js   -> "debug"
 *   android/app/src/pilot/assets/public/js/build-type.js   -> "pilot"
 *   (release has no override - it keeps this file, "release")
 *
 * Gradle merges a build-type source set's assets over main's for the same
 * path, so exactly one of these three files ends up in the built app - never
 * a runtime guess, and `cap sync`/`cap copy` never touch the debug/pilot
 * copies (they only write to src/main/assets).
 */
(function (root) {
  "use strict";

  var BUILD_TYPE = "release";

  var api = { BUILD_TYPE: BUILD_TYPE };

  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  } else {
    root.AlvoraaBuildType = api;
  }
})(typeof window !== "undefined" ? window : this);
