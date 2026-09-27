// Slice 013, AC-172: host-check.js needs to know which build type it is
// running as. Each of the three copies (the default, and the two per-build
// overrides under android/app/src/<type>/assets/) must say what it claims to.
"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const path = require("node:path");

test("the default (release) build-type file says release - the safe default", () => {
  const { BUILD_TYPE } = require(path.join(__dirname, "..", "web", "js", "build-type.js"));
  assert.equal(BUILD_TYPE, "release");
});

test("the debug override says debug", () => {
  const { BUILD_TYPE } = require(
    path.join(__dirname, "..", "android", "app", "src", "debug", "assets", "public", "js", "build-type.js"));
  assert.equal(BUILD_TYPE, "debug");
});

test("the pilot override says pilot", () => {
  const { BUILD_TYPE } = require(
    path.join(__dirname, "..", "android", "app", "src", "pilot", "assets", "public", "js", "build-type.js"));
  assert.equal(BUILD_TYPE, "pilot");
});

test("all three are one of the build types host-check.js actually accepts", () => {
  const { BUILD_TYPES } = { BUILD_TYPES: ["debug", "pilot", "release"] }; // mirrors host-check.js's own list
  for (const p of ["web/js/build-type.js",
                   "android/app/src/debug/assets/public/js/build-type.js",
                   "android/app/src/pilot/assets/public/js/build-type.js"]) {
    const { BUILD_TYPE } = require(path.join(__dirname, "..", ...p.split("/")));
    assert.ok(BUILD_TYPES.includes(BUILD_TYPE), p);
  }
});
