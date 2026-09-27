/*
 * The words the Material 3 redesign added (ALV-133), in one place, so a
 * later translation has one object to fill in. English only for now: Hindi is
 * not in scope (the prototype's Hindi toggle was a draft).
 *
 * Older words still live beside their own logic (join-screens.js,
 * checkin-screens.js, signin-core.js, index.html); those files are pinned by
 * tests and are moved here only when they are translated.
 *
 * t(key, vars) fills "{name}" holes. Whole sentences only - never glue two
 * strings into one sentence, because word order changes between languages.
 */
(function (root) {
  "use strict";

  var EN = {
    // greeting (D-M3-7): morning before 12, afternoon before 5 pm, evening after
    greetingMorning: "Good morning, {name}",
    greetingAfternoon: "Good afternoon, {name}",
    greetingEvening: "Good evening, {name}",

    // Home: the status card
    statusToday: "Today",
    statusNotYet: "Not checked in yet",
    statusIn: "Checked in",
    statusInSince: "since {time}",
    statusOut: "Checked out",
    statusOutAt: "at {time}",
    ruleWithin: "Check in within {radius} m of {workplace}",
    ruleAnywhere: "Check in from anywhere",
    ruleAnywhereNote: "Your location is still saved with each check-in.",
    todayHeading: "Today",
    noPunchesYet: "No check-ins yet today.",
    punchIn: "Checked in",
    punchOut: "Checked out",
    photoDisclosure: "A photo and your location are taken when you press the button.",
    checkIn: "Check In",
    checkOut: "Check Out",
    settings: "Settings",
    loadingToday: "Loading today",

    // Welcome
    welcomeHeading: "Welcome, {name}",
    welcomeBody: "This phone is set up. You can mark attendance now. You do not need to wait for HR.",
    labelCompany: "Company",
    labelWorkplace: "Your workplace",
    labelWhere: "Where you can check in",
    whereWithin: "Within {radius} m",
    whereAnywhere: "From anywhere",

    // the check-in progress
    checkingIn: "Checking you in",
    checkingOut: "Checking you out",
    stepPhoto: "Photo taken",
    stepNoPhoto: "No photo",
    stepWhere: "Finding where you are",
    stepSave: "Saving your attendance",
    keepOpen: "Keep the app open. This can take up to 20 seconds on a slow connection.",
    stillWorking: "Still working. Your photo is kept.",
    stillWorkingNoPhoto: "Still working.",

    // the result (01d §7.6)
    resultAt: "At {workplace}",
    resultWithinDetail: "Within {radius} m · accuracy {accuracy} m",
    resultAbout: "About {distance} from {workplace}",
    resultAnywhereDetail: "You may check in from anywhere · accuracy {accuracy} m",
    resultAnywhereNoAccuracy: "You may check in from anywhere",
    resultSaved: "Location saved",
    resultAccuracy: "Accuracy {accuracy} m",
    resultPhotoTaken: "Photo taken",
    resultPhotoNotTaken: "Photo not taken",
    resultNoPhotoNote: "The camera was not on. Your attendance still counts.",
    resultInRecord: "Saved in your HR record",
    yourPhoto: "Your photo",

    // Settings
    sectionWorkplace: "Your workplace",
    sectionPrivacy: "Privacy",
    sectionPhone: "This phone",
    sectionAbout: "About",
    rulePlainWithin: "Check in within {radius} m",
    rulePlainAnywhere: "You may check in from anywhere",
    noWorkplace: "No workplace set",
    whatRecords: "What this app records",
    agreedOn: "You agreed on {when}",
    stopAgreeing: "Stop agreeing to the notice",
    stopAgreeingSub: "Attendance on this phone pauses until you agree again",
    removePhone: "Remove this phone from {company}",
    removePhoneSub: "Attendance on this phone stops",
    appVersion: "App version {version}",
    connectedTo: "Connected to {host}",
    poweredBy: "Powered by Alvora",

    // What this app records
    agreedCard: "You agreed on {when}. Notice version {version}.",
    recordedToday: "Recorded today on this phone",
    recordedTodayLine: "Your location and the time, and a photo if one was taken",
    olderRecords: "To see older records, or to correct one, ask HR.",
    nothingToday: "Nothing recorded on this phone today.",
    noticeVersion: "Notice version {version}",

    // Stop agreeing (NEW, 01d §7.8)
    withdrawTitle: "Stop agreeing to the notice?",
    withdrawLine1: "This phone stops marking attendance for you until you agree again.",
    withdrawLine2: "Nothing is deleted. Attendance you already marked stays in your HR record.",
    withdrawLine3: "HR will see that you stopped agreeing.",
    withdrawKeep: "Keep agreeing",
    withdrawConfirm: "Stop agreeing",
    withdrawnHeading: "You stopped agreeing",
    withdrawnIntro: "To mark attendance with this phone again, read the notice and agree.",
    withdrawnSnackbar: "You stopped agreeing. Attendance on this phone is paused.",

    // the notice
    whatIsNew: "What is new",

    // Remove this phone (bottom sheet)
    removeTitle: "Remove this phone from {company}?",

    // sign in
    showPassword: "Show password",
    hidePassword: "Hide password",
    typePasswordAgain: "Type your password again.",
    change: "Change",
    companyCode: "Company code",
    codeForHr: "Code for HR: {code}",
    signingInSlow: "This can take a few seconds on a slow connection.",
    passwordChangedNote: "Use your new password. Attendance you already marked is safe.",

    // camera
    cameraHint: "Hold the phone in front of your face",
    cameraWhoSees: "Only HR and your manager can see this photo.",
    cancel: "Cancel",
    close: "Close",
    back: "Back",
  };

  function t(key, vars) {
    var out = Object.prototype.hasOwnProperty.call(EN, key) ? EN[key] : key;
    if (vars) {
      Object.keys(vars).forEach(function (name) {
        out = out.split("{" + name + "}").join(String(vars[name]));
      });
    }
    return out;
  }

  var api = { t: t, EN: EN };

  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  } else {
    root.AlvoraaStrings = api;
  }
})(typeof window !== "undefined" ? window : this);
