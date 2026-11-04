# iPhone check-in: test sheet (ALV-297)

**Test first on the iPhone with iOS 18.7.1.** That is the phone we have today.

**What we want to learn:** does check-in work on a real iPhone when the photo is taken with Apple's own camera screen? Nobody has tried this on a phone yet. Your results decide if it goes further.

**Use test logins on `dev` only.** Do not use real employee data.

**If something goes wrong, send a screenshot** with the test number, your iPhone model and its iOS version (Settings > General > About).

## Ask Surbhi for these first

- The check-in address on `dev`.
- **Test employee A:** a login that can check in from where you are testing. Use it for almost everything.
- **Test employee B:** a login whose workplace is far from you, so you get "too far". Use it for tests 19, 20, 23 and 26.
- **Who approves new phones on `dev`:** Surbhi, or the person she names. Tell them when you have set up, and wait for their word.

## Before you start

Do these in this order, so nobody waits for approval twice. Safari and the Home Screen app keep separate setups, and each setup needs its own approval.

1. Open the check-in address in **Safari**. Not Chrome, and not a link inside WhatsApp or Gmail. **Do not set up here yet.**
2. Press Share (the box with an arrow), then **Add to Home Screen**, then **Add**.
3. Open the app from the **Home Screen**. Set it up with test employee A. Ask for it to be approved.
4. Do all the tests from the Home Screen app, unless a test says Safari.
5. Only when you reach test 19: set up **Safari** with test employee B, and ask for that to be approved too.

Your iPhone: ____________ iOS version: ________ Your name: ____________ Date: ________

**Testing on any other iPhone?** Please write its iOS version here, and use a fresh copy of this sheet for it. The version matters: the camera can behave differently from one iOS version to the next. To find it: Settings > General > About.

| Other iPhone model | iOS version | Tester |
|---|---|---|
| | | |
| | | |

## Three things that are not faults

- **The big button may say Check Out.** It changes after each punch. Wherever this sheet says "press the big button", press it whatever it says. The link under it changes too: "Check out without a photo".
- **30 punches an hour is the limit for each phone.** Going over shows "Something went wrong". This is the limit and not a fault. Keep a count: stop for an hour after 25. A good place for the break is after test 12. Cancelling the camera does not add to the count.
- **"That is already recorded"** means the same punch was sent twice within a minute. Wait a minute and carry on.

## The tests

Write **OK** or **Failed** in the Result column. Add anything odd you saw.

| # | Do this | It should | Result |
|---|---|---|---|
| 1 | Close the app fully (swipe it away). Open it. Press the big button. Take the photo and confirm. **Write down the time and send it to Surbhi.** | No question about the camera. The **front** camera opens. You see "Checked in" with your photo, the right way up. **Surbhi opens the HR record for that time:** the photo is there and the right way up. (The phone's own screen does not prove the server kept it.) | |
| 2 | Hold up your right hand when taking a photo. Look at the result screen. Send Surbhi the time. | Tell us: is your right hand on the right or the left of the picture? Surbhi checks the same on the HR record. | |
| 3 | Do one punch with the phone held sideways, then one held upright. | Both photos are the right way up. | |
| 4 | Press the big button. Press Cancel on the camera. Press the big button again. | The camera opens again. Nothing was saved after the Cancel. | |
| 5 | Press the big button. With the camera open, close the app fully. Open it and press the big button. | The camera opens. | |
| 6 | Press the big button. With the camera open, go to another app, then come back. | The camera still works, and is not black. | |
| 7 | Do five punches in a row (on your oldest iPhone, if you have one). | All five save. The app does not reload itself. Each photo looks right. | |
| 8 | When the camera is open, look for a way to pick an old photo, and for a button that flips the camera. | Tell us: can you pick an old photo? Can you flip to the back camera? | |
| 9 | Settings > Screen Time > Content & Privacy Restrictions > Allowed Apps: turn **Camera** off. Press the big button. | Tell us what opens. Turn Camera back on afterwards. | |
| 9b | Same as test 9. If a menu with Photo Library appears, pick a photo that is at least a week old. | Tell us: did it save the punch with that old photo? | |
| 10 | After some punches, open the Photos app. | No check-in photos should be there. | |
| 11 | Settings > Privacy & Security > Location Services > Safari Websites: choose **Never**. Press the big button and take the photo. Then allow location again and press Try again. | First a message about location. Tell us if its steps made sense. After you allow it, the punch saves, with the photo. | |
| 12 | Tell Surbhi the time of one punch. She checks the size of the saved photo. | Under 400 KB. (Surbhi's team fills this in.) | |

## Coming back to the app

This is how people really use it: check in, then come back hours later.

| # | Do this | It should | Result |
|---|---|---|---|
| 13 | Do a punch. Leave the app (do not close it fully) for **5 seconds**. Come back. Press the big button. | The camera opens and works. | |
| 14 | The same, but leave it for **10 minutes**. | The camera opens and works. | |
| 15 | The same, but leave it for **several hours**. | The camera opens and works. The screen shows the right state. | |
| 24 | **Overnight.** In the evening, while the button says Check Out, press it and **Cancel** the camera. Leave the app in the background (do not close it). Next morning, open it and look before you press anything. | Yesterday's punches are gone and the big button says **Check In**. Press it and take the photo: Surbhi checks the HR record shows a Check In, not a Check Out. Tell us if the app reloaded itself. | |

## When things go wrong

| # | Do this | It should | Result |
|---|---|---|---|
| 16 | Settings > Apps > Safari > Camera (on older iPhones, Settings > Safari > Camera): choose **Deny**. Press the big button. | Tell us what happens. A black camera is possible. If so, Cancel it and press the "without a photo" link. Set Camera back to Allow afterwards. | |
| 17 | Press the big button, Cancel, then press the **"without a photo"** link. | Saved. The screen says Photo: Not taken, and that your attendance still counts. | |
| 18 | After a punch, press Done. Before you press the big button, look for the "without a photo" link. | It should not be there until you have pressed the big button once. | |
| 19 | **Safari, test employee B.** Press the big button and take the photo. You are told you are too far. Wait **more than 10 minutes**, then press Try again. | The camera opens again for a new photo. | |
| 20 | **Safari, test employee B.** The same, but press Try again **within 10 minutes**. | It tries again with the same photo. The camera does not open. You are told you are too far again. | |
| 21 | Turn on Airplane Mode **before** you press the big button. Take the photo. Turn Airplane Mode off and press Try again. | You see "No internet" or a message about location. Either is fine. After Try again, it saves with your photo. | |
| 22 | Switch to Hindi (the button at the top). Look at the words on the home screen and on the result screen. | All in Hindi. Tell us about any wrong or odd wording. These are machine drafts. | |
| 23 | **Safari, test employee B.** Do test 1 up to the "too far" message. | The same camera behaviour as test 1. | |
| 28 | Any time you see a problem screen, look at its buttons. | Every button does something. No empty button with a dash on it. | |

## Other devices

| # | Do this | It should | Result |
|---|---|---|---|
| 25 | **An iPad.** Add to Home Screen, set up, press the big button. Write its iPadOS version here: ________ | Apple's camera opens, as on iPhone. Tell us if the setup steps looked wrong for an iPad. | |
| 26 | **Desktop Website mode, Safari, test employee B.** On the iPhone, press the **aA** button by the address (or the page menu), then **Request Desktop Website**. Press the big button. | Apple's camera opens. No question about the camera. Turn the mode off afterwards. | |
| 27 | **One real Android phone**, in Chrome, on `dev`. Set up with a test login of its own and do one punch. Write its Android version here: ________ | The live camera shows on the screen, as it did before. Pressing the button saves the punch. Surbhi checks the HR record has the photo. There is no "without a photo" link. | |

**Thank you.** Send this sheet and your screenshots to Surbhi.
