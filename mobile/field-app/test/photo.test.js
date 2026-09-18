// Slice 013, AC-201 / OPS-21: the photo size rules, tested where there is no canvas.
"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const photo = require("../web/js/photo.js");

test("a big picture is scaled to 640 by 480 at most, keeping its shape", () => {
  const landscape = photo.fitSize(4000, 3000);
  assert.deepEqual(landscape, { width: 640, height: 480, scale: 0.16 });
  assert.ok(landscape.width <= 640 && landscape.height <= 480);

  const portrait = photo.fitSize(3000, 4000);
  assert.equal(portrait.width, 480);
  assert.equal(portrait.height, 640);

  const wide = photo.fitSize(4000, 1000);
  assert.equal(wide.width, 640);
  assert.equal(wide.height, 160);
});

test("a picture that is already small is left alone", () => {
  assert.deepEqual(photo.fitSize(320, 240), { width: 320, height: 240, scale: 1 });
});

test("nonsense sizes give nothing rather than a broken picture", () => {
  assert.equal(photo.fitSize(0, 100), null);
  assert.equal(photo.fitSize(-1, -1), null);
  assert.equal(photo.fitSize(undefined, undefined), null);
});

test("over 120 KB is saved again at lower quality; over 150 KB is too big", () => {
  assert.equal(photo.needsSecondTry(119 * 1024), false);
  assert.equal(photo.needsSecondTry(121 * 1024), true);
  assert.equal(photo.isTooBig(150 * 1024), false);
  assert.equal(photo.isTooBig(151 * 1024), true);
});

test("the size of a data URL is counted without copying it", () => {
  assert.equal(photo.dataUrlBytes("data:image/jpeg;base64,/9j/4AAQ"), 6); // 8 characters -> 6 bytes
  assert.equal(photo.dataUrlBytes("data:image/jpeg;base64,AAAA"), 3);
  assert.equal(photo.dataUrlBytes("data:image/jpeg;base64,AAA="), 2);
  assert.equal(photo.dataUrlBytes("data:image/jpeg;base64,AA=="), 1);
  assert.equal(photo.dataUrlBytes("nonsense"), 0);
});

test("shrinkToJpeg draws once, and saves again only when the first try is too big", () => {
  const calls = [];
  const fakeCanvas = (bytesByQuality) => ({
    width: 0,
    height: 0,
    getContext: () => ({ drawImage: (...a) => calls.push(["draw", a[3], a[4]]) }),
    toDataURL: (type, quality) => {
      calls.push(["save", quality]);
      const body = "A".repeat(Math.ceil(bytesByQuality[quality] * 4 / 3));
      return `data:${type};base64,${body}`;
    },
  });

  const small = photo.shrinkToJpeg({}, 4000, 3000, () => fakeCanvas({ 0.6: 90 * 1024 }));
  assert.deepEqual(calls, [["draw", 640, 480], ["save", 0.6]]);
  assert.equal(small.quality, 0.6);
  assert.equal(small.tooBig, false);

  calls.length = 0;
  const big = photo.shrinkToJpeg({}, 4000, 3000,
    () => fakeCanvas({ 0.6: 130 * 1024, 0.45: 100 * 1024 }));
  assert.deepEqual(calls, [["draw", 640, 480], ["save", 0.6], ["save", 0.45]]);
  assert.equal(big.quality, 0.45);
  assert.equal(big.tooBig, false);

  calls.length = 0;
  const stubborn = photo.shrinkToJpeg({}, 4000, 3000,
    () => fakeCanvas({ 0.6: 200 * 1024, 0.45: 160 * 1024 }));
  assert.equal(stubborn.tooBig, true, "over 150 KB must be reported, not sent quietly");
});
