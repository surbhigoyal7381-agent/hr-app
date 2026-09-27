# Vendored third-party code

Files here are copied byte-for-byte from an npm package's published `dist/`
output, never hand-edited. The app has no bundler step (`web/*.js` files are
loaded as plain `<script>` tags, the same way `js/host-check.js` and
`js/photo.js` already are), so a browser-ready file has to be committed rather
than resolved from `node_modules` at build time.

Each file's exact SHA-256 is pinned in `scripts/check_app.mjs`
(`VENDORED_FILES`), the same pattern `ci.yml` already uses for gitleaks: CI
fails if the committed copy ever drifts from that hash, whether by a hand
edit or a bad copy.

| File | From | Version | License |
|---|---|---|---|
| `jsqr.js` | `node_modules/jsqr/dist/jsQR.js` | 1.4.0 (pinned in `package.json`) | Apache-2.0 (`jsqr.LICENSE.txt`) |
| `capacitor-core.js` | `node_modules/@capacitor/core/dist/capacitor.js` | 8.5.2 | MIT (`capacitor-core.LICENSE.txt`) |
| `secure-storage-plugin.js` | `node_modules/capacitor-secure-storage-plugin/dist/plugin.js` | 0.13.0 | MIT (`secure-storage-plugin.LICENSE.txt`) |
| `material-color-utilities.js` | **built**, see below | 0.3.0 | Apache-2.0 (`material-color-utilities.LICENSE.txt`) |

**`material-color-utilities.js` is the one file here that is built, not copied**
(D-M3-3, 01d-ux-redesign-m3.md §9). Google publishes the package only as ES
modules spread over about forty files, and this app has no bundler. So
`node scripts/vendor/build_mcu.mjs` joins the five pieces the app uses
(`scripts/vendor/mcu-entry.mjs`) into one file that sets `window.AlvoraaMcu`,
with the pinned esbuild (devDependencies). Measured on 27 Sep 2026: 64.5 KB,
13.9 KB gzipped. Its SHA-256 is pinned like the others, so a new package
version, a new esbuild or a hand edit all fail `npm run check` until the pin is
changed on purpose. `web/js/theme.js` is its only user.

**Load order matters for the last two.** `capacitor-core.js` defines the global
`capacitorExports` (and `window.Capacitor`) that `secure-storage-plugin.js`
expects to already exist - it must be included first. Both are only needed
because this app has no bundler: the native Android runtime injects its own
low-level bridge automatically (`native-bridge.js`, inside `@capacitor/android`
itself, not vendored here), but the public `Capacitor.registerPlugin` /
`Capacitor.Plugins` API and each plugin's own JS side still have to be loaded
from web assets, the same as any other script this app uses.

**This wiring has not been proven on a real device yet.** It is read from the
package structure and Capacitor's own documented "vanilla JS, no bundler"
pattern, not from a working build - see
`docs/slices/013-mobile-app/03-implementation-notes.md` §7 for exactly what
is and is not verified.

**To update a vendored file:** bump the version in `package.json`, run
`npm install`, copy the new `node_modules/<pkg>/dist/...` file over the
vendored one, update the SHA-256 in `check_app.mjs`, and say why in the commit
message - the same review a new dependency would get, because this is one.
