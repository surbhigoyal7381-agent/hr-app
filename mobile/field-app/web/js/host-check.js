/*
 * Which QR codes this app will act on. Slice 013: SEC-14, OPS-7, OPS-55, AC-172.
 *
 * A QR code is only a link, and anybody can print one. If the app followed any
 * link, a planted code could send a worker's photo and position to someone
 * else's server. So a scanned or picked code must be exactly:
 *
 *     https scheme, host <tenant>.alvoraa.co, path /enrol, fragment #t=<43-character code>
 *
 * and in pilot and debug builds also the host <tenant>.dev.alvoraa.co.
 *
 * Anything else is refused with QR_NOT_ALVORAA, BEFORE any network call. This
 * function is pure: it never fetches, stores or logs anything, and the code in
 * the answer must only ever be kept in memory by the caller (AC-218).
 *
 * Parsed with the standard URL parser (the same one the browser and Node use),
 * never with string tests on the raw text, because a link whose user part is
 * "x.alvoraa.co" and one whose host is "alvoraa.co.evil.com" both CONTAIN
 * ".alvoraa.co" (the hostile cases are in test/host-check.test.js).
 * (No example links in this file: the bundle check refuses any URL but the
 * tenant pattern.)
 *
 * Works as a plain browser script (window.AlvoraaHostCheck) and in Node tests.
 */
(function (root) {
  "use strict";

  var BASE_DOMAIN = "alvoraa.co";

  // secrets.token_urlsafe(32) on the server: 43 URL-safe base64 characters.
  var CODE_PATTERN = /^[A-Za-z0-9_-]{43}$/;

  // One DNS label, lower case after parsing. No punycode ("xn--"): a look-alike
  // name in another alphabet is refused rather than trusted.
  var LABEL_PATTERN = /^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$/;

  var BUILD_TYPES = ["debug", "pilot", "release"];

  function refuse() {
    return { ok: false, code: "QR_NOT_ALVORAA" };
  }

  /*
   * text       what the scanner or the picture decoder returned
   * buildType  "debug", "pilot" or "release" - fixed at build time, never
   *            taken from the server or from the QR code
   *
   * Returns { ok: true, origin: <"https:" + "//" + host>, code: "..." }
   *      or { ok: false, code: "QR_NOT_ALVORAA" }
   */
  function checkEnrolLink(text, buildType) {
    if (BUILD_TYPES.indexOf(buildType) === -1) return refuse();
    // (hostIsAllowed below asks this again; asking first keeps a bad build
    // type from ever reaching the URL parser.)
    if (typeof text !== "string" || text.length === 0 || text.length > 200) return refuse();
    // The code we print never has spaces or line breaks around it.
    if (text !== text.trim()) return refuse();

    var url;
    try {
      url = new URL(text);
    } catch (e) {
      return refuse();
    }

    if (url.protocol !== "https:") return refuse();
    if (url.username !== "" || url.password !== "") return refuse();
    if (url.port !== "") return refuse();
    if (url.pathname !== "/enrol") return refuse();
    // The code travels only in the fragment, never in the query (OPS-13).
    if (url.search !== "") return refuse();

    var host = url.hostname;
    if (!hostIsAllowed(host, buildType)) return refuse();

    var match = /^#t=(.*)$/.exec(url.hash);
    if (!match || !CODE_PATTERN.test(match[1])) return refuse();

    return { ok: true, origin: "https://" + host, code: match[1] };
  }

  /*
   * The one rule for which hosts this app will ever call, shared by the QR
   * link above and the company code below (ALV-128), so the two can never
   * disagree:
   *   <tenant>.alvoraa.co        every build type
   *   <tenant>.dev.alvoraa.co    pilot and debug builds only
   * `host` must already be lower case (the URL parser makes it so).
   */
  function hostIsAllowed(host, buildType) {
    if (BUILD_TYPES.indexOf(buildType) === -1) return false;
    if (typeof host !== "string") return false;
    var suffix = "." + BASE_DOMAIN;
    if (host.length <= suffix.length) return false;
    if (host.slice(-suffix.length) !== suffix) return false;

    var labels = host.slice(0, -suffix.length).split(".");
    for (var i = 0; i < labels.length; i++) {
      if (!LABEL_PATTERN.test(labels[i])) return false;
      if (labels[i].indexOf("xn--") === 0) return false;
    }

    if (labels.length === 1) return true;                       // tenant.alvoraa.co
    if (labels.length === 2 && labels[1] === "dev" && buildType !== "release") {
      return true;                                              // tenant.dev.alvoraa.co
    }
    return false;
  }

  /*
   * ALV-128: the person types their company code once - "sargam" - and the
   * app builds the address from it. Nothing typed is ever used as an address
   * as it stands: the code is cleaned, turned into a host, and that host must
   * pass the same rule a QR link does. A pilot or debug build also accepts
   * "sargam.dev" for the dev site; a release build refuses it.
   *
   * Forgiving about what people paste: spaces, capitals, a leading
   * "https://", a trailing "/" or ".alvoraa.co" are all taken off first.
   *
   * Returns { ok: true, origin, code } - `code` is the cleaned company code,
   * the thing worth remembering for next time - or { ok: false, code:
   * "COMPANY_CODE_INVALID" }. Pure: never fetches, stores or logs.
   */
  function originForCompanyCode(text, buildType) {
    var bad = { ok: false, code: "COMPANY_CODE_INVALID" };
    if (typeof text !== "string") return bad;
    var cleaned = text.trim().toLowerCase();
    if (cleaned.length === 0 || cleaned.length > 100) return bad;
    cleaned = cleaned.replace(/^https?:\/\//, "").replace(/\/+$/, "");
    var suffix = "." + BASE_DOMAIN;
    if (cleaned.slice(-suffix.length) === suffix) cleaned = cleaned.slice(0, -suffix.length);
    if (!/^[a-z0-9.-]+$/.test(cleaned)) return bad;
    var host = cleaned + suffix;
    if (!hostIsAllowed(host, buildType)) return bad;
    return { ok: true, origin: "https://" + host, code: cleaned };
  }

  var api = {
    checkEnrolLink: checkEnrolLink,
    originForCompanyCode: originForCompanyCode,
    hostIsAllowed: hostIsAllowed,
    BASE_DOMAIN: BASE_DOMAIN,
  };

  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  } else {
    root.AlvoraaHostCheck = api;
  }
})(typeof window !== "undefined" ? window : this);
