/*
 * The one shared `#problem-card` element inside index.html's shared
 * `#problem` section, written to by both `join.js`'s and `checkin.js`'s own
 * `showProblem()`. Pulled out after a real, traced review finding: before
 * this existed, `checkin.js` could leave a stale card visible - "Your photo
 * is kept.", or a stale "For HR · SERVER_ERROR" card - and `join.js`'s own
 * `showProblem()` never touched `#problem-card` at all, so scanning a new,
 * different dead code (e.g. `QR_EXPIRED`) after a check-in problem screen
 * could show the OLD card's text underneath the new heading and body
 * (05-review-daily-use.md, M1).
 *
 * One rule fixes it for good: every call to `render()` clears the card
 * first, and only shows it again if THIS call's own `card` argument says to.
 * join.js's own screens never set `card` at all, so calling this (with no
 * card) is exactly the one-line fix the review asked for, and sharing the
 * function is the "better" version of that fix it also named - one place
 * decides what the card looks like, not two.
 *
 * Pure and DOM-adjacent only - takes the element and a small text-node
 * helper as arguments rather than looking either up itself, so this is
 * trivially testable with a plain fake object, no DOM library needed.
 */
(function (root) {
  "use strict";

  function clearChildren(node) {
    while (node.firstChild) node.removeChild(node.firstChild);
  }

  /*
   * render(cardEl, textEl, card)
   *   cardEl  the element itself: needs .hidden, .appendChild, .firstChild,
   *           .removeChild - exactly what a real DOM element and a plain
   *           fake test object both provide.
   *   textEl  function(tag, text) -> a node to append, so this file does not
   *           need its own copy of the textContent-only helper both callers
   *           already have (SEC-17: never innerHTML).
   *   card    the screen's `card` field, or undefined/null. Shapes:
   *             { note: "..." }
   *             { onThisPhone: null, needed: "1.2.0", appVersion: "0.1.0" }
   *             { forHr: "SERVER_ERROR", when: "...", appVersion: "0.1.0" }
   *           `appVersion`/`when` are passed in by the caller rather than
   *           read from a global clock or `window.AlvoraaVersion` here, so
   *           this function has no hidden dependency and no DOM library is
   *           needed to test it.
   */
  function render(cardEl, textEl, card) {
    clearChildren(cardEl);
    if (!card) {
      cardEl.hidden = true;
      return;
    }
    cardEl.hidden = false;
    if (card.note) cardEl.appendChild(textEl("p", card.note));
    if (card.onThisPhone !== undefined) {
      cardEl.appendChild(textEl("p", "On this phone " + (card.appVersion || "")));
      cardEl.appendChild(textEl("p", "Needed " + card.needed + " or newer"));
    }
    if (card.forHr) {
      cardEl.appendChild(textEl("p", "For HR · " + card.forHr));
      cardEl.appendChild(textEl("p", "When · " + (card.when || "")));
      cardEl.appendChild(textEl("p", "App · " + (card.appVersion || "") + " · Android"));
    }
  }

  var api = { render: render };

  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  } else {
    root.AlvoraaProblemCard = api;
  }
})(typeof window !== "undefined" ? window : this);
