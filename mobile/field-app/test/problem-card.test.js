// Regression test for 05-review-daily-use.md's M1: a stale #problem-card left
// by one flow (checkin.js) must not still be visible when the other flow
// (join.js) shows its next problem screen. The fix is one shared render()
// that always clears first - this proves that rule directly, with a plain
// fake element, no DOM library needed.
"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const path = require("node:path");

const { render } = require(path.join(__dirname, "..", "web", "js", "problem-card.js"));

function fakeTextEl(tag, text) {
  return { tag, textContent: text };
}

function fakeCardElement() {
  const children = [];
  return {
    hidden: false,
    appendChild(node) { children.push(node); },
    get firstChild() { return children.length ? children[0] : null; },
    removeChild(node) { children.splice(children.indexOf(node), 1); },
    _children: children,
  };
}

test("render() with no card hides the element and empties it - the M1 fix itself", () => {
  const card = fakeCardElement();
  card.appendChild(fakeTextEl("p", "Your photo is kept.")); // stale content from a previous screen
  card.hidden = false;

  render(card, fakeTextEl, undefined);

  assert.equal(card.hidden, true);
  assert.equal(card._children.length, 0);
});

test("the exact M1 scenario: checkin.js shows a card, then join.js's own showProblem (no card) must clear it", () => {
  const card = fakeCardElement();

  // checkin.js hits TOO_MANY_TRIES mid-punch: shows a card.
  render(card, fakeTextEl, { note: "Your photo is kept." });
  assert.equal(card.hidden, false);
  assert.equal(card._children.length, 1);

  // The phone is removed; control returns to join.js. A new scan comes back
  // QR_EXPIRED - join.js's screens never set `card`, so this call passes none.
  render(card, fakeTextEl, undefined);

  assert.equal(card.hidden, true, "the stale card must not still be showing");
  assert.equal(card._children.length, 0, "the stale text must be gone, not just hidden");
});

test("render() with a note card shows exactly one line", () => {
  const card = fakeCardElement();
  render(card, fakeTextEl, { note: "Your photo is kept." });
  assert.equal(card.hidden, false);
  assert.deepEqual(card._children.map((c) => c.textContent), ["Your photo is kept."]);
});

test("render() with the update-screen shape shows both lines, using the caller's own app version", () => {
  const card = fakeCardElement();
  render(card, fakeTextEl, { onThisPhone: null, needed: "1.2.0", appVersion: "0.1.0" });
  assert.deepEqual(card._children.map((c) => c.textContent),
    ["On this phone 0.1.0", "Needed 1.2.0 or newer"]);
});

test("render() with the For-HR shape shows all three lines", () => {
  const card = fakeCardElement();
  render(card, fakeTextEl, { forHr: "SERVER_ERROR", when: "2026-09-22 09:00:00", appVersion: "0.1.0" });
  assert.deepEqual(card._children.map((c) => c.textContent),
    ["For HR · SERVER_ERROR", "When · 2026-09-22 09:00:00", "App · 0.1.0 · Android"]);
});

test("calling render() twice in a row with different cards never leaves the first one behind", () => {
  const card = fakeCardElement();
  render(card, fakeTextEl, { note: "First." });
  render(card, fakeTextEl, { note: "Second." });
  assert.deepEqual(card._children.map((c) => c.textContent), ["Second."]);
});
