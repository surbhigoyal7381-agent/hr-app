/*
 * Remembering the notice this phone's owner actually agreed to, so Settings'
 * "What this app records" (US-43, AC-215) can show it "from saved data, no
 * call." Slice 013, daily use.
 *
 * Why this has to exist at all: the full six rows of the notice are only ever
 * sent to the phone at E1 (check_code) and inside a NOTICE_CHANGED refusal's
 * values. `field_status` (E4) sends only a bare `notice_version` string, never
 * the words. So the only moments the app can capture the text are right after
 * E3 (join_with_code) succeeds, and right after E9 (acknowledge_notice)
 * re-agrees to a changed one - both in `join.js`/`checkin.js`, which call
 * save() at exactly those two points.
 *
 * Backed by `localStorage`, not the Keystore-backed secure storage
 * device-secret.js uses. Deliberately so: this text is not secret - it is the
 * same words HR already showed this person at setup - so it does not need
 * (or deserve) the extra weight of Keystore, and keeping it out of that store
 * keeps the store's own job ("the one thing that authenticates a call")
 * uncluttered. Every call is wrapped so a WebView that blocks or clears
 * `localStorage` degrades to "nothing cached" rather than a crash - Settings
 * then falls back to naming only the version it already knows from the last
 * `field_status` answer (see checkin.js), not the full six rows.
 */
(function (root) {
  "use strict";

  var KEY = "alvoraa_notice_agreed";

  function realStorage() {
    try {
      return (typeof localStorage !== "undefined") ? localStorage : null;
    } catch (e) {
      // Some WebViews throw merely for touching the global in a restricted
      // context (e.g. a file:// preview with storage disabled).
      return null;
    }
  }

  /*
   * save(entry, storage) -> boolean
   * entry: { version, rows: [{heading, body}, ...], agree, retentionDays,
   *          agreedAt } - agreedAt is an ISO string the caller supplies
   *          (server time, not the phone's clock - see checkin.js/join.js).
   * Never throws. Returns false (not saved) rather than raising, because a
   * failure here must never block the join or the notice-changed flow it is
   * called from.
   */
  function save(entry, storage) {
    storage = storage || realStorage();
    if (!storage || !entry || typeof entry !== "object") return false;
    try {
      storage.setItem(KEY, JSON.stringify({
        version: entry.version || "",
        rows: Array.isArray(entry.rows) ? entry.rows : [],
        agree: entry.agree || "",
        retentionDays: entry.retentionDays,
        agreedAt: entry.agreedAt || "",
      }));
      return true;
    } catch (e) {
      return false;
    }
  }

  /*
   * load(storage) -> the saved entry, or null if there is none or it cannot
   * be read. Never throws - a phone that has never joined, or whose storage
   * was cleared, reads as "nothing saved," the same as a fresh install.
   */
  function load(storage) {
    storage = storage || realStorage();
    if (!storage) return null;
    var raw;
    try {
      raw = storage.getItem(KEY);
    } catch (e) {
      return null;
    }
    if (!raw) return null;
    try {
      var parsed = JSON.parse(raw);
      return (parsed && typeof parsed === "object") ? parsed : null;
    } catch (e) {
      return null;
    }
  }

  /*
   * clear(storage) -> void
   * Called wherever the phone forgets the company (Remove this phone; the
   * server telling it the phone is Removed/Blocked/Replaced/not set up).
   */
  function clear(storage) {
    storage = storage || realStorage();
    if (!storage) return;
    try {
      storage.removeItem(KEY);
    } catch (e) {
      // Nothing to do - if it could not be read, there is nothing to worry
      // about leaving behind either.
    }
  }

  var api = { KEY: KEY, save: save, load: load, clear: clear };

  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  } else {
    root.AlvoraaNoticeCache = api;
  }
})(typeof window !== "undefined" ? window : this);
