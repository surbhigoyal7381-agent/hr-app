---
slice: 013-mobile-app
artifact: 09-install-the-test-app
author: hrms-fullstack-engineer
date: 2026-09-18
status: for Surbhi — a debug build to try on a phone. Local only; nothing pushed.
---

# Try the app on your phone

This is a **test build**. It is not the attendance app yet. It checks the two
things a cheap Android phone has to get right first: the **camera** and the
**position**. It talks to **no server**, so nothing is sent or saved anywhere.

## Where the file is

```
C:\Surbhi-Git\hrlocal-data\mobile-builds\alvoraa-attendance-0.1.0-debug.apk
```

The same file, where the build put it:

```
C:\Surbhi-Git\hr-app\.claude\worktrees\013-mobile-app\mobile\field-app\android\app\build\outputs\apk\debug\app-debug.apk
```

About 4 MB. Signed with Android's own debug key — **we have no signing key yet,
and none was made.**

## Getting it onto the phone — two ways

**Easiest: copy the file.**

1. Plug the phone into the PC with a USB cable.
2. On the phone, pull down the notification about the USB connection and choose
   **File transfer** (some phones call it MTP).
3. On the PC the phone appears in File Explorer. Copy the `.apk` file into the
   phone's **Download** folder.
4. On the phone open **Files** → **Downloads** → tap the file.
5. Android will say something like *"For your security, your phone is not
   allowed to install unknown apps from this source"*. Tap **Settings**, turn on
   **Allow from this source**, then press Back and tap **Install** again.
6. If Play Protect says *"Unsafe app blocked"* or offers to scan it, choose
   **Install anyway** / **More details → Install anyway**. That warning is
   normal for any app that did not come from the Play Store.

**Or by cable, if you prefer the command line.** On the phone: Settings → About
phone → tap **Build number** seven times → back → System → **Developer options**
→ turn on **USB debugging**. Then on the PC:

```
C:\Users\Dell\AppData\Local\Android\Sdk\platform-tools\adb.exe devices
C:\Users\Dell\AppData\Local\Android\Sdk\platform-tools\adb.exe install -r "C:\Surbhi-Git\hrlocal-data\mobile-builds\alvoraa-attendance-0.1.0-debug.apk"
```

The first command shows a prompt on the phone asking you to allow this computer —
tick "always allow" and accept.

## What you should see

The app is called **Alvoraa Attendance** on the home screen. It opens on one page:

1. An orange line: this build is not connected to any server.
2. **Camera** — tap **Turn the camera on**. Android asks for the camera; allow it.
   The picture appears. Tap **Take the photo**. You should see the photo and a
   line like "640 by 480 pixels, 38 KB, quality 0.6 — within the 150 KB limit".
   That is exactly the size a real check-in photo will be.
3. **Location** — tap **Find where I am**. Android asks for location; choose
   **While using the app** and **Precise**. You should get a line like "Accurate
   to about 12 m (the limit is 100 m), found in 3.4 seconds". Indoors it is often
   worse than 100 m, which is the point of the test — step outside and try again.
4. A short list of what is not built yet.

**Please tell me:** the phone's maker and model, whether the camera and location
worked, the photo size it showed, and the accuracy and seconds outdoors. That is
the first real data for the pilot budget.

## What will not work yet

- No QR scanning, no joining, no Check In, no Check Out.
- Nothing reaches your Alvoraa site. The server side waits for slice 014 to land.
- No Hindi. No dark mode (light is pinned on purpose).
- The photo is never saved on the phone and is gone when you leave the screen.

## Two safety notes

- This build's app ID ends in `.debug`, so it can never replace the real app later.
- Please **do not send this file to anyone else**. Test builds for other people go
  through Firebase, with named testers, later in the slice.

## To remove it

Long-press the icon → **Uninstall** (or Settings → Apps → Alvoraa Attendance →
Uninstall). Nothing is left behind: the app stores nothing.
