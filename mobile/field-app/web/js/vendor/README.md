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
