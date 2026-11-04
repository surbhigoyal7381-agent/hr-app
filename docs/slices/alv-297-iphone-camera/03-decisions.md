# ALV-297 and ALV-298: decisions before `main`

Recorded 4 November 2026. These are Surbhi's decisions, written down so they are not only in a chat.

## What was decided

| # | Decision | What it means |
|---|---|---|
| 1 | Fix the false "not saved" message, on iPhone and on Android | After a punch saves, a failed status check no longer draws "No internet. Your attendance has not been saved yet." A punch that really did not save still says so. |
| 2 | Accept the 10-minute photo gap for now | On iPhone, after "too far", a retry within 10 minutes resends the same photo. After 10 minutes the camera opens again. After no signal or a location error, the earlier photo is resent at any age. This is not changed. It is logged as its own YouTrack ticket. |
| 3 | Accept, and record, leaving the "never a file" rule on iPhone | See below. |

## What PRIV-7 asks

The repo has several different items called PRIV-7, one per slice. The one that applies here is in
`docs/slices/013-mobile-app/01c-security-privacy-requirements.md`, line 441:

> Photos and QR pictures stay in memory. The photo is taken inside the page (`getUserMedia`), held in memory, sent, dropped. Never a file, the gallery or a cache.

Its test is a device test: after a punch, the app's storage holds no image.

## Why iPhone no longer meets it, and why that is accepted

- The iPhone path opens Apple's own camera from a file input. Apple, not us, decides whether it writes a temporary file while it does that. We cannot see it and we cannot stop it.
- Our page still does its part: it reads the picture once, redraws it as a small JPEG in memory, sends that, and clears the input. It never saves the picture itself.
- Android keeps the live camera and still meets PRIV-7 as written.
- So on iPhone the rule "never a file" is **not met**. It is knowingly accepted by Surbhi on 4 Nov 2026.

## What the test sheet can and cannot show

Test 10 on `iphone-test-sheet.md` checks that the picture is not in the Photos app. That is all it can check. It **cannot** show hidden temporary files that Apple's camera may create. Passing Test 10 must not be read as proof that no file was made.

## Not decided here (left open on purpose)

- Past consent records for web staff who set up since 22 Sep. This is counsel's matter (see the review).
- The "How long" wording difference (P4).
- "Taken" can still be false when the server drops a refused photo. Left out by design.

## Where the other review items stand on `dev`

- The Cancel bug (review "Fix before the dev test", item 1) is already fixed on `dev`: `field-checkin.html` still asks for status after a cancel and ignores a failure.
- The dead second button `b-err-2` (item 3) is already fixed on `dev`: the page has `.btn[hidden]{display:none}`.
