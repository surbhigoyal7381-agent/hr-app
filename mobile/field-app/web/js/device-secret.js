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
 */
(function (root) {
  "use strict";

  // The one key this app ever stores. One phone, one secret, one company at a
  // time (D18: no "switch company" in this increment).
  var KEY = "alvoraa_device_secret";

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
   * clear(cap) -> Promise<boolean>
   * Used by "Remove this phone" (US-43, not built yet) and after a server
   * refusal that means the secret can never work again. Never rejects: a
   * phone with nothing to clear, or no native storage, both count as done.
   */
  function clear(cap) {
    var plugin = nativePlugin(cap);
    if (!plugin) return Promise.resolve(false);
    return plugin.remove({ key: KEY })
      .then(function (result) { return !!(result && result.value); })
      .catch(function () { return false; });
  }

  var api = { KEY: KEY, save: save, load: load, clear: clear, _nativePlugin: nativePlugin };

  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  } else {
    root.AlvoraaDeviceSecret = api;
  }
})(typeof window !== "undefined" ? window : this);
