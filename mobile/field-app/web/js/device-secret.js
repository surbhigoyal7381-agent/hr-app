/*
 * Storing this phone's device secret - the only thing a server call ever
 * proves itself with, and the only thing this app keeps once it is set up
 * (AC-217, PRIV-1). Slice 013 stage-2 spike, now wired for real (US-36).
 *
 * Backed by capacitor-secure-storage-plugin (Android Keystore, see
 * docs/slices/013-mobile-app/03-implementation-notes.md §7.4 for why this one
 * was chosen and what is and is not proven about it).
 *
 * The safety point the spike found and flagged: that plugin's WEB fallback -
 * used only if this code somehow ran outside the native Android app - is
 * plain localStorage plus base64, no encryption at all. This file must never
 * trust that fallback for a real secret, so every call checks
 * Capacitor.isNativePlatform() first and refuses to read or write through
 * anything else. Fails closed: no native platform, no plugin, no secret.
 *
 * A second key, added in the daily-use build (US-39/43): which tenant this
 * phone talks to. `join.js` only ever learns a QR's host in memory
 * (`state.origin`), so without this, every app open after the process is
 * killed - normal on Android, not exceptional - would have nowhere to call.
 * The origin is not secret, but it decides which company a phone belongs to,
 * so it lives beside the secret in the same already-vetted, fail-closed
 * store rather than in a second storage mechanism with its own lifecycle to
 * keep in sync. Both are written after a join succeeds and both are cleared
 * together by `clear()` - never one without the other (see the docstring
 * there).
 */
(function (root) {
  "use strict";

  // The one secret this app ever authenticates a call with. One phone, one
  // secret, one company at a time (D18: no "switch company" in this
  // increment).
  var KEY = "alvoraa_device_secret";

  // Which tenant that secret belongs to - "https://<tenant>.alvoraa.co" or
  // "https://<tenant>.dev.alvoraa.co" in pilot/debug, exactly the shape
  // host-check.js's checkEnrolLink() returns. Never a secret; kept here only
  // so both pieces of "which phone, which company" state share one lifecycle.
  var ORIGIN_KEY = "alvoraa_tenant_origin";

  /*
   * cap  the Capacitor global, or an injected fake for a test. Defaults to
   *      globalThis.Capacitor, which the native Android runtime provides on
   *      every real page load - never resolved from a global inside a module
   *      wrapper's own `this`, which is a different, empty object (the same
   *      lesson qr-decode.js's `globalThis.jsQR` fix already applied here).
   *
   * Returns the plugin object to call, or null if this is not a real,
   * trustworthy native context.
   */
  function nativePlugin(cap) {
    cap = cap || (typeof globalThis !== "undefined" ? globalThis.Capacitor : undefined);
    if (!cap || typeof cap.isNativePlatform !== "function" || !cap.isNativePlatform()) {
      return null;
    }
    var plugins = cap.Plugins;
    var plugin = plugins && plugins.SecureStoragePlugin;
    return (plugin && typeof plugin.get === "function") ? plugin : null;
  }

  /*
   * save(secret, cap) -> Promise<boolean>
   * Rejects if there is no trustworthy native storage to write to - the
   * caller must treat that as a setup failure, never as "saved anyway".
   */
  function save(secret, cap) {
    var plugin = nativePlugin(cap);
    if (!plugin) {
      return Promise.reject(new Error("Secure storage is not available on this platform."));
    }
    if (typeof secret !== "string" || secret.length < 20) {
      return Promise.reject(new Error("Refusing to store an empty or too-short secret."));
    }
    return plugin.set({ key: KEY, value: secret }).then(function (result) {
      return !!(result && result.value);
    });
  }

  /*
   * load(cap) -> Promise<string|null>
   * Never rejects: "nothing stored yet" and "no native storage at all" both
   * mean the same thing to a caller deciding whether this phone is set up -
   * null. The plugin itself rejects a promise for "no such key", which is
   * business as usual on a fresh install, not an error to surface.
   */
  function load(cap) {
    var plugin = nativePlugin(cap);
    if (!plugin) return Promise.resolve(null);
    return plugin.get({ key: KEY })
      .then(function (result) { return (result && result.value) || null; })
      .catch(function () { return null; });
  }

  /*
   * saveOrigin(origin, cap) -> Promise<boolean>
   * Same shape as save(), but for the tenant origin, not the secret. A light
   * sanity check only (no length floor, no secret-strength check) - the real
   * validation already happened in host-check.js before this is ever called,
   * and duplicating that regex here would just be a second place for the two
   * to drift apart.
   */
  function saveOrigin(origin, cap) {
    var plugin = nativePlugin(cap);
    if (!plugin) {
      return Promise.reject(new Error("Secure storage is not available on this platform."));
    }
    if (typeof origin !== "string" || !/^https:\/\/[a-z0-9.-]+$/i.test(origin)) {
      return Promise.reject(new Error("Refusing to store something that is not a plain https origin."));
    }
    return plugin.set({ key: ORIGIN_KEY, value: origin }).then(function (result) {
      return !!(result && result.value);
    });
  }

  /*
   * loadOrigin(cap) -> Promise<string|null>
   * Never rejects, for the same reason load() does not.
   */
  function loadOrigin(cap) {
    var plugin = nativePlugin(cap);
    if (!plugin) return Promise.resolve(null);
    return plugin.get({ key: ORIGIN_KEY })
      .then(function (result) { return (result && result.value) || null; })
      .catch(function () { return null; });
  }

  /*
   * clear(cap) -> Promise<boolean>
   * Used by "Remove this phone" (US-43) and after a server refusal that means
   * the secret can never work again. Never rejects: a phone with nothing to
   * clear, or no native storage, both count as done.
   *
   * Removes BOTH keys, always. The secret and the origin describe one fact -
   * "this phone belongs to this company" - and leaving one behind after
   * clearing the other is exactly the failure mode this file exists to
   * avoid. The return value still answers only for the SECRET (unchanged
   * from before this key existed, and what every existing caller already
   * reads): whether the origin happened to be there too is not this
   * function's caller's business.
   */
  function clear(cap) {
    var plugin = nativePlugin(cap);
    if (!plugin) return Promise.resolve(false);
    var originDone = plugin.remove({ key: ORIGIN_KEY }).catch(function () { return null; });
    return plugin.remove({ key: KEY })
      .then(function (result) { return originDone.then(function () { return !!(result && result.value); }); })
      .catch(function () { return originDone.then(function () { return false; }); });
  }

  var api = {
    KEY: KEY, ORIGIN_KEY: ORIGIN_KEY,
    save: save, load: load, clear: clear,
    saveOrigin: saveOrigin, loadOrigin: loadOrigin,
    _nativePlugin: nativePlugin,
  };

  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  } else {
    root.AlvoraaDeviceSecret = api;
  }
})(typeof window !== "undefined" ? window : this);
