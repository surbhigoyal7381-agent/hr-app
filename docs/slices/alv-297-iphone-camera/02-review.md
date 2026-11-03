# Review: ALV-297 (iPhone camera) and ALV-298 (notice words)

**Verdict: SHIP WITH FIXES, for the dev phone test only. One new bug can record the wrong punch type, and it should be fixed first. This is not ready for `main`.** The verdict is advice. You decide.

**Nothing has run on a real iPhone or a real Android phone.** So nobody yet knows if Apple's camera opens from the tap in a Home Screen app, if photos come out upright, or if the page reloads after the camera. The test sheet is the only way to learn this.

**Not run at all:** Frappe's own rendering of the page, the full test suite, the linters. Nothing touched a server.

**What was reviewed:** a1d3b7f3, 400eff11 and 92a1392f on c503a6be. There are no merge commits and nothing new on `origin/dev`.

**Missing from the process:** the slice folder has no impact analysis, brief, spec or security note. Only the test sheet and the design notes in chat exist. So the requirements and compliance checks below cannot be complete. Recording these is what `main` needs; the dev test can go without them.

## What I ran

| Check | Result | Note |
|---|---|---|
| The slice's browser check | 20 of 20 passed | Chrome pretending to be an iPhone, against a copy of the page. A small local server filled in the template values, so Frappe did not render it |
| The same check with each fix removed | 32 of 32 removals made a test fail | Same setup |
| `test_checkin_iphone_297.py` | 8 passed | With a stand-in for Frappe. These only read the page's text |
| Notice words against `field_app_notice.py` | See ALV-298 below | My own word-by-word script |
| My own probes (bugs below) | Each bug reproduced | Same copy of the page |
| `test_013_the_web_page_shows_the_words...` | **Not run** | Needs a bench. I read it |

## Fix before the dev test

### 1. New bug: after a Cancel, the page stops updating and can send the wrong punch (P2)

- **What happens:** the person presses Check Out and cancels the camera. iPhone sends no signal for a cancel, so `waitingForPhoto` stays on. The app is left in the background, not closed. The next morning `field-checkin.html:1339` skips the status check, because that flag is still on.
- **Result:** the screen still says "You are checked in since 9:00 am", with yesterday's punches. The server resets to "not checked in" each day (`field_checkin.py:1064`), but the page never asks. Pressing the button sends **OUT at the start of the day**.
- **Proven:** I reproduced it. The status said not checked in, the button said Check Out, and the post was `log_type: OUT`. The test that passes at this line (`browser_check...js:299`) asserts that no status check runs, so it locks this bug in.
- **Why it matters:** the punch type feeds attendance and pay.
- **Smallest fix:** in that branch, still ask for the status, but ignore any failure: `call("field_status", {token: store.token}).then(function(s){ lastStatus = s; renderHome(s); }).catch(function(){});`. The aim of the skip was to avoid drawing an error, and this keeps that. Change the test to check that no error screen appears.

### 2. Older bug, both phones: "not saved" after a punch that was saved (P2, your call)

- **What happens:** the punch saves and the "Checked in" screen appears. Then the status check right after it fails on weak signal (`field-checkin.html:998`). The screen flips to "No internet. Your attendance has not been saved yet."
- **Proven:** I reproduced it on the iPhone and Android settings, with one post sent each time. Pressing Done has the same route, through `goHome()`. I read that one and did not run it.
- **What ALV-297 fixed:** only the return from the camera. The test title "so it cannot draw an error" claims more than that.
- **Why it matters:** this is the false "not saved" you asked about. A person who believes it may punch again.
- **Smallest fix:** a failed status check must never draw the "not saved" words. Use the same quiet call at line 998, and do not show the attendance wording when nothing is pending.
- **Decision for you:** this also changes Android, which you wanted left alone. I recommend the fix. Say yes or no.

### 3. `b-err-2` is real: a dead button (P3, older bug)

- **What happens:** `.btn` sets `display:flex` (`field-checkin.html:101`), which beats `hidden` (`:446`). So screens with one action still show a second button.
- **Proven:** on "That is already recorded", the button is visible with the text "—" and does nothing. If another error came first, it shows that error's old label and action instead. By reading, the same happens on Not set up, Blocked, Left and Not in plan.
- **Smallest fix:** replace `#b-nophoto[hidden]{display:none}` (`:148`) with `.btn[hidden]{display:none}`. That is one rule covering both. Update the matching removal entry in the browser check (`browser_check...js:232`).

### 4. The test sheet needs these changes (P2, because the test is the whole goal)

| Problem | Why a tester gets stuck or misled | Change |
|---|---|---|
| Setup order: Safari first, then Home Screen | The Home Screen app starts empty, as the design notes say. Each setup needs its own approval (`field_checkin.py:521`), so every tester waits twice | Add to Home Screen first, set up inside it, and name who approves on dev. "HR" means nobody on dev. Set up Safari separately for test 23 |
| "Press Check In" when the button says Check Out | Test 3 ends checked in, so test 4 cannot be followed as written. Tests 5, 6 and 17 can hit the same thing | Add one line: "Press the big button, whatever it says" |
| Test 19 and 20 cannot work on a "check in anywhere" login | That login is never too far, so the tester writes Failed | Name a login whose workplace is far from the tester |
| Test 21: Airplane Mode with the camera open, expects "No internet" | Hard to do. GPS may fail first, so a location message may show (not checked) | Turn it on before pressing, and accept either message |
| Test 1 looks only at the phone's own screen | The "Taken" screen draws what the phone sent, not what the server kept (`:1014`) | In test 12, Surbhi also opens the HR record, and checks that the photo is there, upright and which way it is mirrored |
| Missing tests | Bug 1 above, iPad, and Request Desktop Website | Add: cancel, leave overnight, reopen. Add one iPad row and one Desktop Website row |
| Android | The sheet has none, and Android has only run on a fake camera | Add one real Android punch on dev |
| About 30 punches | The limit is 30 an hour per phone (`field_checkin.py:627`). Going over shows "Something went wrong" | Add a note saying this is the limit and not a fault |

Tests 2 to 18 otherwise read clearly. I could not check Apple's menu names on a phone.

## Fix before `main`

- **The HR description is real (P3).** `field_checkin.py:1134` says "Taken by the field app at the moment of the punch." That is untrue on a retry. A photo can be up to 10 minutes old after "too far", and any age after no signal or a location error. HR reads this field as evidence. Suggested wording: "Taken on the phone for this punch. A retry can resend the earlier photo." [Inferred: the existing migrate step updates the description. Not run.]
- **The 10-minute limit is easy to get round (P3, decision for you).** Take the photo at home in Airplane Mode, travel to work, then press Try again. It sends the old photo with the workplace location. The browser check confirms the photo is kept after no signal, and that is on purpose. Location errors behave the same by reading. Nothing on the record shows the gap. Android has the same hole today. Write this down as accepted, or decide otherwise.
- **PRIV-7 and the design decisions are not recorded (P2).** The notes list four decisions for you, including leaving the "never a file" rule and whether the UX agent sees the new home screen. Nothing in the repo records the answers. Test 10 can only check the Photos app, not hidden temporary files.
- **Location help is written for Android (P3, older).** The steps say "press the lock icon next to the address" and "Press Location" (`:1052`, `:1062`). A Home Screen iPhone has no address bar, so someone who refused location may be stuck, and the punch needs location. Test 11 should ask if the steps made sense.
- **"Taken" can still be false (P3, older, left out by design).** The server drops a refused photo and tells the phone nothing. Test 12 will show if this matters.

## ALV-298: notice words

- **Match:** title, all six headings, the five fixed row bodies and the agree line match `field_app_notice.py` exactly, in both copies on the page. **Proven** by script.
- **One difference:** the "How long" line has its own words on the page ("Photos are deleted after {0} days...") and in the store ("Check-in photos are kept for {0} days, then deleted."). The meaning is the same and the file treats this line as unversioned, so it is outside the version pin. It is still not word for word. (P4)
- **Test gap (P3):** the renamed test looks for the words anywhere in the page. The page holds two copies, and the second one (in `T`) is what people see. If that copy drifted, the test would still pass. Fix: check that the changed row appears twice.
- **Past records are not fixed (P2, needs counsel).** Web staff who set up since 22 Sep saw the old words, yet their history row says they read 2026-09-22, and web phones are never asked again (`field_checkin.py:753`). This change only helps new setups. I could not count those people without tenant access. Decide this with counsel. Do not let this commit be read as closing it.
- **Hindi:** the page's own note says all Hindi is a machine draft that needs a native speaker before a customer sees it (`:488`). There is no Hindi copy in the store to match against, so the new notice sentence is the only copy.

## Hindi drafts

My reading: the 8 new strings and the one added notice sentence say what the English says. One is awkward: "काम में नहीं ली जा सकी" in `res.photo.why.failed`. "इस्तेमाल नहीं हो सकी" is simpler. I am not a native reviewer, so this does not replace that review. Test 22 helps but a tester is not a language check.

## The other things you asked about

| Question | Finding | Label |
|---|---|---|
| Double punch from a photo after the link | Blocked. The late photo does nothing. Double tap on the link sends one post | Proven in Chrome |
| Double punch from a lost reply, then retry after 60 seconds | Possible, as before. Server blocks repeats only within 60 seconds | Read; not new |
| Android changing | Live camera path unchanged, and 2 tests pass. **Two word changes reach Android:** the new notice sentence and the no-photo reason line. Both look intended | Proven by diff; fake camera only |
| iPad detection | Logic is right: Macintosh plus more than one touch point. iPad setup still shows Android steps and stores "Other", because `platform()` was left alone (P4) | Proven in Chrome; never on an iPad |
| Hidden input opens from the tap | Runs at once inside the tap, on both the Check In and retake routes, before any busy screen | Proven in Chrome; **not proven on an iPhone** |
| Failed shrink | Bad file or junk canvas sends no photo, saves the punch and says "Not saved" | Proven in Chrome |
| What if iPhone's file goes away | The input is cleared before the file is read (`:967`). This works in Chrome. On an iPhone the sign would be "Photo: Not saved" on every punch | Not checked |
| Spinner that never ends | Shrink has no time limit. It relies on the browser always reporting load or error | Read; not seen failing |
| 10-minute retry | Correct for "too far". A cancel then the link still works and posts no photo. See the limit above | Proven in Chrome |
| Jinja | No new line has `{{`, `{%` or `{#` | Proven by search; Frappe did not render it |
| Small screens | Button and link stay on screen at 320x460 in Hindi. There the words in the box are cut off | Proven in Chrome |
| Raw file or location data sent | Never. Only the redrawn JPEG leaves the phone | Proven in Chrome |
| Tests passing for the wrong reason | Overall they are honest and fail when the fix is removed. The problems are the test at bug 1, the test title at bug 2 and the notice test above | Proven |

**Data doors:** this adds no field, endpoint or limit, and the server is unchanged, so there is no new door to test. I did not reproduce one live.

## Requirements and compliance

There are no written acceptance rules to walk. Against your summary:

| Asked for | Status |
|---|---|
| iPhone and iPad stop using the live camera | Met in Chrome |
| Tap opens Apple's camera, 480px JPEG, punch sent | Met in Chrome; camera not proven |
| Android keeps the live camera | Met in Chrome, on a fake camera |
| Link appears after the first tap | Met |
| Team can test on real iPhones | Partly, until the sheet is fixed |

**Compliance: cannot be reviewed.** The slice has no compliance analysis, and I will not write one here. PRIV-7 stands as not discharged until you decide it.

**Seven dimensions:** there is no impact analysis to compare with, so this is only my reading of the code.

| Dimension | My reading |
|---|---|
| Performance | No new server load. A photo is about 54 KB on my noisy test image. Real phone memory not measured |
| Security | Unchanged. A person can now approve a shot and maybe flip the camera, so the photo is weaker evidence |
| Reliability | Better on iPhone if the camera works. Bug 1 makes it worse after a cancel |
| Scalability | Unchanged |
| Maintainability | Slightly worse. Two photo routes on one page |
| Data integrity | Worse until bug 1 is fixed |
| Privacy | Stale photo risk reduced but not closed. Temporary file question open |

## What to delete

- **`browser_check_checkin_iphone_297.js`, 440 lines, not in CI (P4).** Keep it until the phone results are in, because it is the only proof of behaviour. Then decide whether it stays.
- **`res.photo.why.failed` (P4).** One shared reason line would nearly do, but "Not taken" would be false for someone who did take a photo. Leave it unless you want the fewer strings.
- **`#b-nophoto[hidden]`** goes when fix 3 goes in.

## What was done well

- Opening the camera before any busy screen or GPS, because Apple needs a real tap.
- Showing the link only after the camera has been offered.
- Checking the shrink's own output, so a broken picture never reads as "Taken".
- Every test carries its own removal proof. I re-ran all 32.
- The script and commit message both say plainly that Chrome proves only the JavaScript.

## Confidence

- **Proven:** the bugs and Chrome results above, on my copy of the page.
- **Inferred:** the description update on migrate, and how long a page stays alive in the background. Bug 1 needs the page to survive overnight, which an iPhone may not always allow. If it does not, the page reloads and the bug does not appear.
- **Not checked:** everything on a real phone, Frappe's rendering, the full test suite, tenant data.

**Subtract pass:** I removed a guess about Android browsers in desktop mode and a note on an error that is very unlikely. I also cut the repeated design notes.
