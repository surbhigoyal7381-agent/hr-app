// The five pieces of Google's material-color-utilities the app uses to make a
// company's colours from its brand colour (01d-ux-redesign-m3.md §5.1, D-M3-3).
//
// Not loaded by the app. scripts/vendor/build_mcu.mjs bundles this file into
// web/js/vendor/material-color-utilities.js, which check_app.mjs pins by hash.
// The package exports only its index; esbuild drops everything these five do
// not reach (the image quantiser, score, blend and the other schemes).
export {
  argbFromHex,
  hexFromArgb,
  Hct,
  SchemeTonalSpot,
  SchemeMonochrome,
  MaterialDynamicColors,
} from "@material/material-color-utilities";
