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

**To update a vendored file:** bump the version in `package.json`, run
`npm install`, copy the new `node_modules/<pkg>/dist/...` file over the
vendored one, update the SHA-256 in `check_app.mjs`, and say why in the commit
message - the same review a new dependency would get, because this is one.
