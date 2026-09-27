/*
 * The company's colours and the light or dark theme (ALV-133).
 *
 *   D-M3-1  the theme follows the phone's own light or dark setting;
 *   D-M3-3  the palette is made on the phone from the company's brand colour,
 *           with Google's material-color-utilities (web/js/vendor/);
 *   D-M3-5  a brand colour with almost no colour in it (PP Jewellers' black,
 *           any grey) gets Material's grey "monochrome" palette - the usual
 *           recipe turns black into pink;
 *   D-M3-7  the greeting follows the phone's clock.
 *
 * Before the app knows the company (sign-in, joining) the CSS file's own
 * Alvoraa palette is used; nothing here runs. Green for "done" and amber for
 * "fix this" are fixed in the CSS and never follow the company.
 *
 * The pure parts (normaliseHex, schemeKind, palette, contrast, greetingKey)
 * take the colour library as an argument, so the Node tests run them on the
 * same vendored file the phone loads.
 */
(function (root) {
  "use strict";

  var DEFAULT_SEED = "#5b4b8a";   // the portal's --primary, 01d §5.1
  var MONOCHROME_BELOW = 8;       // chroma under this is "almost no colour" (D-M3-5)
  var STORE_KEY = "alvoraa_brand_colour";

  // The Material colour roles the CSS reads, as --md-sys-color-<kebab-name>.
  var ROLES = [
    "primary", "onPrimary", "primaryContainer", "onPrimaryContainer",
    "secondary", "onSecondary", "secondaryContainer", "onSecondaryContainer",
    "tertiary", "onTertiary", "tertiaryContainer", "onTertiaryContainer",
    "error", "onError", "errorContainer", "onErrorContainer",
    "surface", "onSurface", "onSurfaceVariant",
    "surfaceContainerLowest", "surfaceContainerLow", "surfaceContainer",
    "surfaceContainerHigh", "surfaceContainerHighest",
    "outline", "outlineVariant",
    "inverseSurface", "inverseOnSurface", "inversePrimary", "scrim",
  ];

  function kebab(name) {
    return name.replace(/[A-Z]/g, function (c) { return "-" + c.toLowerCase(); });
  }

  // "#000" -> "#000000"; anything that is not a plain hex colour -> null. The
  // server already sends "#rrggbb" (E-1); this is the phone's own guard, since
  // the whole palette is built from this one value.
  function normaliseHex(value) {
    if (typeof value !== "string") return null;
    var s = value.trim().toLowerCase();
    if (/^#[0-9a-f]{6}$/.test(s)) return s;
    if (/^#[0-9a-f]{3}$/.test(s)) return "#" + s[1] + s[1] + s[2] + s[2] + s[3] + s[3];
    return null;
  }

  function schemeKind(hex, mcu) {
    var seed = normaliseHex(hex) || DEFAULT_SEED;
    var hct = mcu.Hct.fromInt(mcu.argbFromHex(seed));
    return hct.chroma < MONOCHROME_BELOW ? "monochrome" : "tonal";
  }

  // role name -> "#rrggbb" for one theme.
  function palette(hex, dark, mcu) {
    var seed = normaliseHex(hex) || DEFAULT_SEED;
    var hct = mcu.Hct.fromInt(mcu.argbFromHex(seed));
    var Scheme = hct.chroma < MONOCHROME_BELOW ? mcu.SchemeMonochrome : mcu.SchemeTonalSpot;
    var scheme = new Scheme(hct, !!dark, 0);
    var out = {};
    ROLES.forEach(function (role) {
      out[role] = mcu.hexFromArgb(mcu.MaterialDynamicColors[role].getArgb(scheme));
    });
    return out;
  }

  // WCAG 2.2 contrast ratio of two "#rrggbb" colours.
  function luminance(hex) {
    var n = parseInt(hex.slice(1), 16);
    return [(n >> 16) & 255, (n >> 8) & 255, n & 255].map(function (v) {
      v /= 255;
      return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
    }).reduce(function (sum, v, i) { return sum + v * [0.2126, 0.7152, 0.0722][i]; }, 0);
  }

  function contrast(a, b) {
    var la = luminance(a), lb = luminance(b);
    return (Math.max(la, lb) + 0.05) / (Math.min(la, lb) + 0.05);
  }

  // D-M3-7: the phone's own clock. Morning before 12, afternoon before 5 pm.
  function greetingKey(date) {
    var h = date.getHours();
    if (h < 12) return "greetingMorning";
    if (h < 17) return "greetingAfternoon";
    return "greetingEvening";
  }

  // ── on the phone ───────────────────────────────────────────────────────

  var current = { seed: null, light: null, dark: null };
  var media = null;

  function prefersDark() {
    try {
      return !!(root.matchMedia && root.matchMedia("(prefers-color-scheme: dark)").matches);
    } catch (e) {
      return false;
    }
  }

  function paint() {
    var style = root.document && root.document.documentElement && root.document.documentElement.style;
    if (!style) return;
    var roles = prefersDark() ? current.dark : current.light;
    ROLES.forEach(function (role) {
      if (roles) style.setProperty("--md-sys-color-" + kebab(role), roles[role]);
      else style.removeProperty("--md-sys-color-" + kebab(role));
    });
  }

  function watchTheme() {
    if (media || !root.matchMedia) return;
    try {
      media = root.matchMedia("(prefers-color-scheme: dark)");
      var onChange = function () { if (current.seed) paint(); };
      if (media.addEventListener) media.addEventListener("change", onChange);
      else if (media.addListener) media.addListener(onChange);
    } catch (e) { media = null; }
  }

  function remember(seed) {
    try { root.localStorage.setItem(STORE_KEY, seed); } catch (e) { /* only a convenience */ }
  }

  /*
   * Wear the company's colour. Fail soft: no colour library, or a value that
   * is not a colour, leaves the Alvoraa palette on - never a broken screen.
   */
  function applyBrand(value) {
    var seed = normaliseHex(value);
    var mcu = root.AlvoraaMcu;
    if (!seed || !mcu) return false;
    if (seed !== current.seed) {
      try {
        current = { seed: seed, light: palette(seed, false, mcu), dark: palette(seed, true, mcu) };
      } catch (e) {
        return false;
      }
    }
    watchTheme();
    paint();
    remember(seed);
    return true;
  }

  // Back to Alvoraa's own colours: the phone no longer belongs to a company.
  function reset() {
    current = { seed: null, light: null, dark: null };
    paint();
    try { root.localStorage.removeItem(STORE_KEY); } catch (e) { /* nothing kept */ }
  }

  // On open, before the server answers: the colour this phone last wore, so
  // the loading screen is already the company's.
  function applyRemembered() {
    var saved = null;
    try { saved = root.localStorage.getItem(STORE_KEY); } catch (e) { saved = null; }
    return saved ? applyBrand(saved) : false;
  }

  // Large text for the screenshots and a future font-scale bridge (01d §9.4):
  // at 150% and above the top bar's Settings keeps only its icon.
  function setTextScale(scale) {
    var el = root.document && root.document.documentElement;
    if (!el) return;
    var s = Number(scale) || 1;
    el.style.setProperty("--s", String(s));
    if (s >= 1.5) el.setAttribute("data-large-text", "");
    else el.removeAttribute("data-large-text");
  }

  var api = {
    DEFAULT_SEED: DEFAULT_SEED,
    MONOCHROME_BELOW: MONOCHROME_BELOW,
    ROLES: ROLES,
    kebab: kebab,
    normaliseHex: normaliseHex,
    schemeKind: schemeKind,
    palette: palette,
    contrast: contrast,
    greetingKey: greetingKey,
    applyBrand: applyBrand,
    applyRemembered: applyRemembered,
    reset: reset,
    setTextScale: setTextScale,
  };

  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  } else {
    root.AlvoraaTheme = api;
  }
})(typeof window !== "undefined" ? window : this);
