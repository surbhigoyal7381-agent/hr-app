/*
 * Debug-build override of web/js/build-type.js (see that file for why this
 * exists). Android's source-set asset merging puts this in place of the
 * "release" default for debug builds only - never copied here by `cap sync`,
 * kept in step by hand alongside network_security_config.xml.
 */
(function (root) {
  "use strict";
  var api = { BUILD_TYPE: "debug" };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.AlvoraaBuildType = api;
})(typeof window !== "undefined" ? window : this);
