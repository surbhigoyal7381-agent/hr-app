// Rebuilds web/js/vendor/material-color-utilities.js from the pinned package
// (D-M3-3). Run from mobile/field-app after `npm ci`:
//
//     node scripts/vendor/build_mcu.mjs
//
// Why a build and not a byte-for-byte copy like the other vendored files: the
// package ships only ES modules split over ~40 files, and the app loads plain
// <script> tags with no bundler. esbuild (pinned in devDependencies) joins the
// five pieces mcu-entry.mjs names into one file that sets window.AlvoraaMcu.
// The output is still pinned by SHA-256 in check_app.mjs, so any change to
// it - a new package version, a new esbuild, a hand edit - fails the check
// until someone updates the pin on purpose.

import { build } from "esbuild";
import { fileURLToPath } from "node:url";
import { join } from "node:path";

const APP_DIR = fileURLToPath(new URL("../..", import.meta.url));

await build({
  entryPoints: [join(APP_DIR, "scripts", "vendor", "mcu-entry.mjs")],
  outfile: join(APP_DIR, "web", "js", "vendor", "material-color-utilities.js"),
  bundle: true,
  format: "iife",
  globalName: "AlvoraaMcu",
  minify: true,
  target: "es2017",
  // Keep Google's licence header in the file; the full text sits beside it.
  legalComments: "inline",
  charset: "utf8",
  logLevel: "info",
});
