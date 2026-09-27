---
slice: 013-mobile-app
artifact: 04-test-report
author: hrms-technofunctional-reviewer
date: 2026-09-22
covers: mobile/field-app app-client, commits a473e22 (stage 1), debe06b (stage-2 spike),
  b6021ad (US-35–38, the real join screens)
---

# 013 — app-client test report

This covers only the phone-app code in `mobile/field-app/`. The server side (steps
1–5) has its own test report already on `dev` and is not repeated here.

## 1. What was actually run, today, in this review

All commands run inside a fresh worktree of `origin/dev` (commit `1c4e84c`), on Node
22 (the repo pins Node 24 in `.nvmrc`/`package.json` `engines`; this sandbox does not
have Node 24, so this is a real gap between the pinned tool and what checked this —
noted so nobody assumes CI ran on the same interpreter this review did).

| Command | Result |
|---|---|
| `npm ci --ignore-scripts` | 100 packages installed, engine warning for Node 24 (expected — see above) |
| `npm test` (`node --test "test/*.test.js"`) | **63 tests, 63 pass, 0 fail** |
| `npm run check` (`check_app.mjs` + `check_versions.mjs`) | Both **OK**. Bundle, config, dependency and vendored-file checks pass; version rule passes (`versionName 0.1.0`, `versionCode 10002`) |
| `python3 scripts/check_tracked_keys.py` | OK, 2,650 tracked files, nothing key-shaped |
| `sha256sum` on all three vendored files, compared by hand to `VENDORED_FILES` in `check_app.mjs` | All three match exactly (jsQR, Capacitor core, the secure-storage plugin) |

## 2. What the 63 tests actually prove (read, not just counted)

- **`api.js` (7 tests, `api.test.js`)** — a refusal is read from the top-level `code`/
  `values`, never from Frappe's `message` envelope; a success answer IS read from
  `message`; every call carries the version header and a JSON body; nginx's own
  429/502/413 pages map to the right client code with no server JSON at all; a 200
  page that is not JSON (a captive Wi-Fi login page) reads as `NO_INTERNET`; a
  rejected `fetch` (timeout or real network failure) resolves to `NO_INTERNET`
  rather than throwing; `checkCode`/`refuseCode`/`joinWithCode` hit the three real
  dotted paths and `joinWithCode` always sends `agreed: 1`. Checked by hand against
  the server's real `field_app_errors.py` and `field_checkin.py::_private_request` —
  the wire shape they assert against is the shape the server actually sends.
- **`join-screens.js` (9 tests, `join-screens.test.js`)** — every code this build's
  three endpoints (E1/E2/E3) can realistically return lands on a named screen with
  real words, the two date-shaped sentences render both branches (today / an earlier
  date), and a code the table has never heard of still gets a real screen
  (`unknownCode`), never a blank one.
- **`device-secret.js` (7 tests, `device-secret.test.js`)** — round-trips through a
  fake native plugin; a fresh phone reads `null`, not a rejection; `clear()` reports
  whether there was anything to clear; **the safety property itself**: a fake
  Capacitor object shaped exactly like the plugin's own (unencrypted) web fallback —
  `isNativePlatform: () => false` — is refused for save/load/clear, and nothing is
  read from or written to that fallback's store; with no Capacitor global at all,
  every call fails closed.
- **`build-type.js` (4 tests, `build-type.test.js`)** — the default file says
  `"release"` (the safe default) and the two real per-build-type override files
  under `android/app/src/{debug,pilot}/assets/public/js/` say what they claim.
- **`qr-decode.js` (6 tests, carried from the stage-2 spike)** — a genuine 33×33 QR
  matrix built with the `qrcode` npm package, rendered to a raw RGBA buffer, decodes
  back byte-for-byte through the real vendored `jsqr.js`, and that decoded text
  passes `host-check.js`'s own rule end-to-end; a blank frame finds nothing; a
  malformed frame returns `null`; a missing decoder throws (fails closed).
- **`host-check.js` and `photo.js`** (carried from stage 1, untouched this round) —
  26 hostile QR links × 3 build types refused with zero network calls; the photo
  shrink rules.

## 3. What this proves, in plain terms

The parts of the app that can be tested without a phone — reading the server's
answers correctly, picking the right screen for every code, refusing to trust
anything but real phone storage, and reading a real QR code back correctly — are
proven, and proven against the server's own real files, not against a guess at
what the server does.

## 4. What is NOT proven, and cannot be proven without a real phone

This is not a gap in this test report — it is the honest limit of what a text
editor and Node can check. It is already written down in full, with the exact
symptom to look for if each one is wrong, in
`docs/slices/013-mobile-app/03-implementation-notes.md` §8.3. In short, in the
order the implementation notes themselves rank it:

1. **The Capacitor JS bridge wiring** — `capacitor-core.js` must load before
   `secure-storage-plugin.js` on a real page. If this is wrong, the visible symptom
   is a console error (`capacitorExports is not defined`) and every screen after
   `welcome` fails to save the secret.
2. **The real Android Keystore round trip** — encrypt, store, restart the app,
   decrypt — on a real device, and specifically on a low-end 32-bit phone.
3. **The camera scan loop reading a real, moving QR code** fast enough to feel like
   one scan (the decode logic is proven; the camera-frame timing is not).
4. **Permission-prompt timing** and the **"Open phone settings" button**, both
   deliberately simplified this increment (documented, not forgotten).
5. **Everything downstream of a real device build** — this test report was run
   without an Android SDK, the same limit the implementation notes record for the
   whole slice.

This review does not re-derive any of the above; it is stated once, honestly, in
the implementation notes, and this report points at it rather than repeating it
with less detail.

## 5. Gaps in the automated proof this review found while reading the tests

- No test asserts the **exact copy** of the `FEATURE_OFF` and `TOO_MANY_TRIES`
  screens against the source of truth each is meant to match (the 008 web
  check-in page, and the server's real `retry_after_s` value). See
  `05-review.md` findings 2 and 1. A test that had pinned that copy would have
  caught both before this review did.
- No automated check compares `field_app_errors.py`'s `CODES` table against
  `join-screens.js`'s `SCREENS` table (a "does every code this build can receive
  have its own row, not just the fallback" drift check). The `unknownCode`
  fallback means this is not a blank-screen risk today, but it is a silent-drift
  risk the same way the server's own `CODES`-table test guards the server side.
