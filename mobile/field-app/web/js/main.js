/*
 * The one decision the whole page hinges on: has this phone already joined?
 * Slice 013, daily use.
 *
 * Deliberately tiny and DOM-free beyond this one call. Before this file
 * existed, join.js decided this by itself, unconditionally, by always
 * calling show("first") - there was no check at all for a phone that had
 * already joined (see 00-impact-analysis-daily-use.md §0.4/§4.4). Now
 * neither join.js nor checkin.js runs until this says which one should.
 */
(function () {
  "use strict";
  window.AlvoraaDeviceSecret.load().then(function (secret) {
    if (secret) {
      window.AlvoraaCheckin.start();
    } else {
      window.AlvoraaJoin.start();
    }
  });
})();
