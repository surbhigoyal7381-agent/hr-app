/*
 * What to do with a refusal `field_status`/`field_checkin`/`remove_my_phone`/
 * `acknowledge_notice` send at "on open" time - US-41's gate, US-42's
 * changed notice, and the M2 fix from 05-review-daily-use.md. Pure branching
 * on `code` alone, DOM-free, so `checkin.js` only has to read the plan this
 * returns and act on it - it should never itself decide what a code means,
 * the same rule `checkin-screens.js` and `join-screens.js` already keep.
 *
 * Extracted for the same reason `problem-card.js` was extracted for M1: the
 * decision is worth proving with a test that needs no DOM, not just trusted
 * inside a bigger, untestable file.
 *
 * M2, stated plainly: `_device_from_token` refuses `CONSENT_REQUIRED` for a
 * phone parked in "Consent not given" (`field_checkin.py`'s
 * `_REFUSAL_FOR_STATUS`). Before this file existed, `checkin.js` had no
 * branch for it and fell through to the generic `unknownCode` screen -
 * looping forever on "check for an update" for a phone that is not actually
 * out of date. HR's own desk screen already promises "the app asks again
 * each time it opens" for this exact status
 * (`employee_field_app.js:214`), and `acknowledge_notice` (E9)'s own
 * docstring confirms reading the notice again, with no new code, is exactly
 * how such a phone becomes Active again. So `CONSENT_REQUIRED` gets the SAME
 * recovery `NOTICE_CHANGED` already has - it just has to be fetched first,
 * because `CONSENT_REQUIRED`'s own `values` carry only `version`, never the
 * six rows (checked against `field_app_errors.CODES`).
 */
(function (root) {
  "use strict";

  /*
   * planForGateRefusal(code, values) -> one of:
   *   { action: "forgetAndFirst" }                  - NOT_SET_UP, DEVICE_PENDING, DEVICE_REMOVED
   *   { action: "noticeAgain", values }              - NOTICE_CHANGED
   *   { action: "probeConsentRequired" }             - CONSENT_REQUIRED (see below)
   *   { action: "problem", code, values }            - everything else
   */
  function planForGateRefusal(code, values) {
    if (code === "NOT_SET_UP" || code === "DEVICE_PENDING" || code === "DEVICE_REMOVED") {
      return { action: "forgetAndFirst" };
    }
    if (code === "NOTICE_CHANGED") {
      return { action: "noticeAgain", values: values };
    }
    if (code === "CONSENT_REQUIRED") {
      return { action: "probeConsentRequired" };
    }
    return { action: "problem", code: code, values: values };
  }

  /*
   * planForConsentRequiredProbe(result) -> what to do with the answer from
   * deliberately calling acknowledge_notice with a version it cannot
   * possibly match, which is how the full six rows are fetched for a
   * CONSENT_REQUIRED phone (no new server endpoint needed):
   *   { action: "noticeAgain", values }   - the expected path: the server
   *                                         refused with NOTICE_CHANGED and
   *                                         the full rows attached
   *   { action: "reloadStatus" }          - only if the mismatch call somehow
   *                                         succeeded outright (never happens
   *                                         with a real server, kept as a
   *                                         safe fallback rather than a crash)
   *   { action: "problem", code, values } - any OTHER refusal (the employee
   *                                         left, the app is off, etc.) is as
   *                                         real here as anywhere else
   */
  function planForConsentRequiredProbe(result) {
    if (!result.ok && result.code === "NOTICE_CHANGED") {
      return { action: "noticeAgain", values: result.values };
    }
    if (result.ok) {
      return { action: "reloadStatus" };
    }
    return { action: "problem", code: result.code, values: result.values };
  }

  var api = {
    planForGateRefusal: planForGateRefusal,
    planForConsentRequiredProbe: planForConsentRequiredProbe,
  };

  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  } else {
    root.AlvoraaGateRefusal = api;
  }
})(typeof window !== "undefined" ? window : this);
