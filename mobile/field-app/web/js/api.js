/*
 * Calling the join endpoints on a tenant's Alvoraa site. Slice 013, US-35/36/38:
 * E1 check_code, E2 refuse_code, E3 join_with_code.
 *
 * The contract (02-functional-spec.md §6/§7, and field_app_errors.py on
 * origin/dev, which is the real, already-shipped version of it):
 *
 *   - POST /api/method/<dotted.function.path>, JSON body, guest, no cookies.
 *   - Every call carries X-Alvoraa-App-Version.
 *   - On success, Frappe wraps the function's return value as
 *     {"message": <value>}.
 *   - On a refusal Frappe already knows how to answer (status < 500), the
 *     wrapper (_private_request in field_checkin.py) sets `code` and `values`
 *     at the TOP LEVEL of the JSON body, beside Frappe's own `exc_type`. The
 *     function itself returns nothing in that case - there is no `message`
 *     key to read.
 *   - The app picks its screen from `code` alone (MA-30) - it never matches
 *     on the English sentence Frappe also queues for its own logs and for the
 *     web page.
 *
 * Every call times out at 30 s and is retried only when the person taps Try
 * again (AC-203) - nothing here retries on its own.
 *
 * On the phone these calls leave through Capacitor's native HTTP
 * (plugins.CapacitorHttp.enabled in capacitor.config.json, slice 038), which
 * replaces the global `fetch` before this file runs. That is what lets a
 * bundled page POST to https://<tenant>.alvoraa.co at all: from the WebView it
 * is a cross-origin request, and the server sends no CORS headers on purpose
 * (OPS-1, OPS-2, OPS-47). `fetchImpl` defaults to whatever `fetch` is at call
 * time, so nothing here needs to know which one it got.
 */
(function (root) {
  "use strict";

  var TIMEOUT_MS = 30000;

  function parseJson(text) {
    try {
      return JSON.parse(text);
    } catch (e) {
      return null;
    }
  }

  // A server call answered with a status we understand but no `code` of its
  // own - nginx's own pages (429, 502/503/504/413), or a 200 that is not JSON
  // at all (a Wi-Fi captive-portal login page, §7.3). Never guesses a code
  // the server did not actually send when the server DID send valid JSON.
  function fallbackFor(status, ok) {
    if (status === 429) return { code: "TOO_MANY_TRIES", values: {} };
    if (status === 502 || status === 503 || status === 504 || status === 413) {
      return { code: "SERVER_ERROR", values: {} };
    }
    if (ok) return { code: "NO_INTERNET", values: {} }; // 200 but not JSON
    if (status >= 500) return { code: "SERVER_ERROR", values: {} };
    return { code: "INVALID_REQUEST", values: {} };
  }

  /*
   * origin      "https://<tenant>.alvoraa.co", no trailing slash, from the QR's
   *             own host (host-check.js), never typed or guessed.
   * method      the dotted path, e.g. "alvoraa_portal.field_app_join.check_code"
   * params      plain object, JSON-encoded as the request body
   * opts        { fetchImpl, appVersion, timeoutMs } - all optional; fetchImpl
   *             defaults to the global fetch, so a test can inject a fake one
   *             and this file needs no browser to run under node:test.
   *
   * Resolves to one of:
   *   { ok: true,  data: <the function's return value> }
   *   { ok: false, code: "SOME_CODE", values: {...} }
   * Never rejects - a network failure or timeout is itself just NO_INTERNET,
   * the same as the app's own client-made codes in §7.2 of the spec.
   */
  function callMethod(origin, method, params, opts) {
    opts = opts || {};
    var fetchImpl = opts.fetchImpl || (typeof fetch !== "undefined" ? fetch : undefined);
    var appVersion = opts.appVersion
      || (root.AlvoraaVersion && root.AlvoraaVersion.APP_VERSION)
      || (typeof globalThis !== "undefined" && globalThis.AlvoraaVersion && globalThis.AlvoraaVersion.APP_VERSION);
    var timeoutMs = opts.timeoutMs || TIMEOUT_MS;

    if (typeof fetchImpl !== "function") {
      return Promise.resolve({ code: "NO_INTERNET", values: {} });
    }

    // The timer answers NO_INTERNET by itself, and only additionally aborts a
    // fetch that listens. Since slice 038 the app's calls go through Capacitor's
    // native HTTP, whose replacement `fetch` ignores `signal` and whose Android
    // side sets no timeout of its own (read in @capacitor/android 8.5.2,
    // native-bridge.js and HttpRequestHandler.java) - aborting alone would let
    // a hung call hold a worker at the gate for ever (OPS-79: 30 s in code).
    var controller = (typeof AbortController !== "undefined") ? new AbortController() : null;
    var timer = null;
    var timedOut = new Promise(function (resolve) {
      timer = setTimeout(function () {
        if (controller) controller.abort();
        resolve({ code: "NO_INTERNET", values: {} });
      }, timeoutMs);
    });

    var call = fetchImpl(origin + "/api/method/" + method, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Alvoraa-App-Version": appVersion || "",
      },
      body: JSON.stringify(params || {}),
      signal: controller ? controller.signal : undefined,
    }).then(function (res) {
      return res.text().then(function (text) {
        var body = parseJson(text);
        if (body && typeof body.code === "string" && body.code) {
          return { code: body.code, values: body.values || {} };
        }
        if (res.ok && body && Object.prototype.hasOwnProperty.call(body, "message")) {
          return { ok: true, data: body.message };
        }
        var fallback = fallbackFor(res.status, res.ok);
        return fallback;
      });
    }, function () {
      // fetch rejected: aborted (timeout) or a real network failure. Both are
      // "the phone could not reach the server" from the person's point of
      // view - the app has one screen for that, before joining (noSignalJoin).
      return { code: "NO_INTERNET", values: {} };
    });

    return Promise.race([call, timedOut]).then(function (result) {
      clearTimeout(timer);
      return result;
    });
  }

  function checkCode(origin, code, token, opts) {
    return callMethod(origin, "alvoraa_portal.field_app_join.check_code", { code: code, token: token }, opts);
  }

  function refuseCode(origin, code, opts) {
    return callMethod(origin, "alvoraa_portal.field_app_join.refuse_code", { code: code }, opts);
  }

  function joinWithCode(origin, params, opts) {
    // params: { code, notice_version, device_label, platform, token }
    // agreed is always 1 here (D18/01b: the tick is required before this call
    // is ever made - see join.js). The server also accepts agreed=0 for a
    // later decision the app does not build a path to in this increment.
    return callMethod(origin, "alvoraa_portal.field_app_join.join_with_code",
      Object.assign({}, params, { agreed: 1 }), opts);
  }

  // ── daily use (US-39/43): E4, E5, E6, E9 - all guest POST, device-secret
  //    proven, same {ok,data}/{code,values} contract as the join calls above.

  function fieldStatus(origin, token, opts) {
    return callMethod(origin, "alvoraa_portal.field_checkin.field_status", { token: token }, opts);
  }

  function punch(origin, params, opts) {
    // params: { token, log_type, latitude, longitude, accuracy, photo,
    //           captured_at, mock_location }
    return callMethod(origin, "alvoraa_portal.field_checkin.field_checkin", params, opts);
  }

  function removeMyPhone(origin, token, opts) {
    return callMethod(origin, "alvoraa_portal.field_app_device.remove_my_phone", { token: token }, opts);
  }

  function acknowledgeNotice(origin, token, noticeVersion, opts) {
    return callMethod(origin, "alvoraa_portal.field_app_join.acknowledge_notice",
      { token: token, notice_version: noticeVersion }, opts);
  }

  var api = {
    callMethod: callMethod,
    checkCode: checkCode,
    refuseCode: refuseCode,
    joinWithCode: joinWithCode,
    fieldStatus: fieldStatus,
    punch: punch,
    removeMyPhone: removeMyPhone,
    acknowledgeNotice: acknowledgeNotice,
  };

  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  } else {
    root.AlvoraaApi = api;
  }
})(typeof window !== "undefined" ? window : this);
