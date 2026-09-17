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
    npm test              # host allow-list and the checks' own tests
    npm run check         # config, pins, bundle and permission checks

## Waiting for Android Studio

`npx cap add android`, debug builds, the Android manifest checks on a real
project, and the built-package checks need Android Studio 2025.2.1+ with its SDK
(compileSdk and targetSdk 36, minSdk 24). Use Android Studio's own Java 21, not
the Java on PATH. Do not accept Studio's offer to upgrade the Android Gradle
Plugin ahead of Capacitor (OPS-77).

## Pins

Node 24 (`.nvmrc`), Capacitor 8.5.2 exactly, lock file committed, `npm ci`.
