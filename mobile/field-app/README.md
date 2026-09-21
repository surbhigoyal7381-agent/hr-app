# Alvoraa Attendance — field app (slice 013)

The phone app for field workers: join by HR's QR code, check in and out with a
photo and place. A Capacitor shell with a bundled page. Specs:
`docs/slices/013-mobile-app/`.

## Never in this folder

Signing keys, keystores, `keystore.properties`, `google-services.json`, built
`.apk` / `.aab` files. The repo is public. Keys are made **outside every git
folder** and kept in Bitwarden plus one offline copy (OPS-39). Before any push:

    python scripts/check_tracked_keys.py        (from the repo root)

## What works today

    cd mobile/field-app
    npm ci --ignore-scripts
    npm test                        # host allow-list, photo shrink, build-type
                                     # and network-config checks' own tests
    npm run check                   # config, pins, bundle, permissions, build
                                     # types and dependencies
    node scripts/check_versions.mjs [old-build.gradle]   # AC-168, see below

`android/` is generated (`npx cap add android` was already run and its output
committed). It has three build types (OPS-38, AC-165), all built from this one
source tree, never three copies of the code:

- **debug** — app ID `co.alvoraa.app.debug`. Signed with Android's own debug
  key. The only build type that may reach plain HTTP, and only to
  `localhost`/`10.0.2.2` (the developer's own machine via `adb reverse` or the
  emulator) - see `android/app/src/debug/res/xml/network_security_config.xml`.
  Never a tenant host, in debug or any other build type.
- **pilot** — app ID `co.alvoraa.app.pilot`. Not debuggable, not minified
  differently from release. Built only by hand, from a commit on `dev`,
  through the protected `mobile-pilot` GitHub environment (needs a real
  signing key, which does not exist yet - US-31/OPS-38).
- **release** — app ID `co.alvoraa.app` (the store ID, no suffix). Built only
  from a commit on `main`.

All three install side by side on one phone, so a test build can never be
mistaken for, or replace, the real one.

## Still waiting for a real Android SDK

This repo's own CI runner and the sandbox this was authored in can read and
check the Android **source** (manifest, Gradle files, resources) with plain
Node, which is what `npm run check` and `check_versions.mjs` do. Building or
running the app - `./gradlew assembleDebug`, install on a phone or emulator,
and the built-package checks (an unsigned release APK read with
`apkanalyzer`: the *merged* manifest, the debuggable flag, actual network
rules, package size <= 10 MB, before the first pilot build - DevOps `07` §4
gate 5) all need Android Studio 2025.2.1+ with its SDK (compileSdk and
targetSdk 36, minSdk 24) on a machine that has it. Use Android Studio's own
Java 21, not the Java on PATH. Do not accept Studio's offer to upgrade the
Android Gradle Plugin ahead of Capacitor (OPS-77).

## Pins

Node 24 (`.nvmrc`), Capacitor 8.5.2 exactly, lock file committed, `npm ci`.
