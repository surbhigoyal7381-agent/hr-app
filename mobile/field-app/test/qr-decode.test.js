// Slice 013 stage-2 spike: proves the vendored jsQR decoder actually reads a
// real QR code, in plain Node, with no device, emulator or bench (the same
// promise host-check.test.js already keeps for the host allow-list).
//
// The module matrix below is a REAL QR code, computed once with the `qrcode`
// npm package (never added to this project - a QR reader has no business
// depending on a QR writer) for the exact shape of link host-check.js already
// expects: https://ppj.alvoraa.co/enrol#t=<43-char code>. It is baked in as
// plain data so this test needs no image library and no network call to run.
"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const path = require("node:path");

// The vendored file is a UMD bundle - in Node it exports the decoder function
// directly (the same "module.exports = factory()" branch jsQR's own wrapper
// takes), exactly as web/js/vendor/README.md says a browser <script> tag
// would instead put it on window.jsQR.
const jsQR = require(path.join(__dirname, "..", "web", "js", "vendor", "jsqr.js"));
const { decode } = require(path.join(__dirname, "..", "web", "js", "qr-decode.js"));

const ENROL_LINK = "https://ppj.alvoraa.co/enrol#t=" + "A".repeat(43);

// 33x33 modules, error correction M - real output of QRCode.create(ENROL_LINK,
// {errorCorrectionLevel: "M"}), read off once and frozen here as plain rows of
// 0/1 characters, one row per string.
const QR_ROWS = [
  "111111100111011010111001001111111",
  "100000100010001111101110001000001",
  "101110101010110000010100101011101",
  "101110101101001110101000101011101",
  "101110101010000101111010001011101",
  "100000101010001101000111001000001",
  "111111101010101010101010101111111",
  "000000001011000010000100100000000",
  "101111100011110101110010101111100",
  "110110000110001001111011001101100",
  "010011101011010101000100111010111",
  "101100000011010110111011000011110",
  "000110101010000001011101111001001",
  "100100000100110011100101000101011",
  "110001100111001001011010111110110",
  "001011001001000100010101011000100",
  "010110111110010101000011110111001",
  "111110011000010010110101111101110",
  "100110111000010110101010100110110",
  "011000011011110011000111111111110",
  "100011111110111010000001101111000",
  "110000000110011000101010110010001",
  "101010110000010110010010000101110",
  "101111010111000010001111100100011",
  "101100111111010101010010111110111",
  "000000001000011011111110100010101",
  "111111100001110100001101101010100",
  "100000101101011000100001100011110",
  "101110101011111101101010111111011",
  "101110101101011101000100110011110",
  "101110101010010011000000111101000",
  "100000100110101100111101001010100",
  "111111101010101011000011100101010",
];

// Renders the module matrix into an ImageData-shaped RGBA buffer, the way a
// real photo of the code would arrive: white quiet zone border, each module
// scaled up to several real pixels (a raw 1-pixel-per-module image is smaller
// than any real camera frame and some decoders read it less reliably).
function renderToImageData(rows, { scale = 6, quietZoneModules = 4 } = {}) {
  const size = rows.length;
  const withQuiet = size + quietZoneModules * 2;
  const width = withQuiet * scale;
  const height = width;
  const data = new Uint8ClampedArray(width * height * 4).fill(255); // white, opaque

  for (let r = 0; r < size; r++) {
    for (let c = 0; c < size; c++) {
      if (rows[r][c] !== "1") continue;
      const px0 = (c + quietZoneModules) * scale;
      const py0 = (r + quietZoneModules) * scale;
      for (let dy = 0; dy < scale; dy++) {
        for (let dx = 0; dx < scale; dx++) {
          const idx = ((py0 + dy) * width + (px0 + dx)) * 4;
          data[idx] = 0;
          data[idx + 1] = 0;
          data[idx + 2] = 0;
          data[idx + 3] = 255;
        }
      }
    }
  }
  return { data, width, height };
}

test("decode() reads a real QR code back to its exact text", () => {
  const imageData = renderToImageData(QR_ROWS);
  const result = decode(imageData, jsQR);
  assert.ok(result, "expected a QR code to be found");
  assert.equal(result.text, ENROL_LINK);
});

test("decode() also works off the vendored global (window.jsQR shape)", () => {
  const previous = globalThis.jsQR;
  globalThis.jsQR = jsQR;
  try {
    const imageData = renderToImageData(QR_ROWS);
    const result = decode(imageData);
    assert.equal(result.text, ENROL_LINK);
  } finally {
    if (previous === undefined) delete globalThis.jsQR;
    else globalThis.jsQR = previous;
  }
});

test("decode() finds nothing in a blank image - no false positive", () => {
  const blank = { data: new Uint8ClampedArray(200 * 200 * 4).fill(255), width: 200, height: 200 };
  assert.equal(decode(blank, jsQR), null);
});

test("decode() returns null on a malformed frame instead of throwing", () => {
  assert.equal(decode(null, jsQR), null);
  assert.equal(decode({}, jsQR), null);
  assert.equal(decode({ data: new Uint8ClampedArray(4), width: 0, height: 0 }, jsQR), null);
});

test("decode() fails closed (throws) when no decoder is available at all", () => {
  const previous = globalThis.jsQR;
  delete globalThis.jsQR;
  try {
    const imageData = renderToImageData(QR_ROWS);
    assert.throws(() => decode(imageData), /jsQR is not loaded/);
  } finally {
    if (previous !== undefined) globalThis.jsQR = previous;
  }
});

test("the text decode() returns is exactly what host-check.js's rule expects", () => {
  const { checkEnrolLink } = require(path.join(__dirname, "..", "web", "js", "host-check.js"));
  const imageData = renderToImageData(QR_ROWS);
  const result = decode(imageData, jsQR);
  const checked = checkEnrolLink(result.text, "pilot");
  assert.equal(checked.ok, true);
  assert.equal(checked.code, "A".repeat(43));
});
