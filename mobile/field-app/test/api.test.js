// Slice 013, US-35/36/38: the network layer picks a `code` at the top level
// of the body, never Frappe's English sentence, and never crashes when the
// server sends something the app was not built to expect.
"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const path = require("node:path");

const { callMethod, checkCode, refuseCode, joinWithCode } = require(
  path.join(__dirname, "..", "web", "js", "api.js"));

function fakeFetch(status, bodyObj, { ok } = {}) {
  const text = JSON.stringify(bodyObj);
  return (url, init) => {
    fakeFetch.lastUrl = url;
    fakeFetch.lastInit = init;
    return Promise.resolve({
      ok: ok !== undefined ? ok : status >= 200 && status < 300,
      status,
      text: () => Promise.resolve(text),
    });
  };
}

test("a success answer is read from Frappe's message envelope", async () => {
  const fetchImpl = fakeFetch(200, { message: { first_name: "Suresh" } });
  const result = await callMethod("https://ppj.alvoraa.co", "alvoraa_portal.field_app_join.check_code",
    { code: "x" }, { fetchImpl, appVersion: "0.1.0" });
  assert.deepEqual(result, { ok: true, data: { first_name: "Suresh" } });
});

test("a refusal is read from the top-level code and values, not the message key", async () => {
  const fetchImpl = fakeFetch(410, { exc_type: "ValidationError", code: "QR_USED", values: { used_at: "2026-09-17 09:01:00" } }, { ok: false });
  const result = await callMethod("https://ppj.alvoraa.co", "x", {}, { fetchImpl });
  assert.deepEqual(result, { code: "QR_USED", values: { used_at: "2026-09-17 09:01:00" } });
});

test("every call carries the version header and a JSON body", async () => {
  const fetchImpl = fakeFetch(200, { message: {} });
  await callMethod("https://ppj.alvoraa.co", "some.method", { a: 1 }, { fetchImpl, appVersion: "1.2.3" });
  assert.equal(fakeFetch.lastUrl, "https://ppj.alvoraa.co/api/method/some.method");
  assert.equal(fakeFetch.lastInit.method, "POST");
  assert.equal(fakeFetch.lastInit.headers["X-Alvoraa-App-Version"], "1.2.3");
  assert.equal(fakeFetch.lastInit.headers["Content-Type"], "application/json");
  assert.deepEqual(JSON.parse(fakeFetch.lastInit.body), { a: 1 });
});

test("nginx's own pages, not JSON, map to the right client code", async () => {
  const tooMany = await callMethod("https://x", "m", {}, { fetchImpl: fakeFetch(429, {}) });
  assert.equal(tooMany.code, "TOO_MANY_TRIES");

  const gateway = await callMethod("https://x", "m", {}, { fetchImpl: fakeFetch(502, {}) });
  assert.equal(gateway.code, "SERVER_ERROR");

  const big = await callMethod("https://x", "m", {}, { fetchImpl: fakeFetch(413, {}) });
  assert.equal(big.code, "SERVER_ERROR");
});

test("a 200 that is not JSON (a captive Wi-Fi login page) reads as no internet", async () => {
  const fetchImpl = (url, init) => Promise.resolve({ ok: true, status: 200, text: () => Promise.resolve("<html>Sign in to Wi-Fi</html>") });
  const result = await callMethod("https://x", "m", {}, { fetchImpl });
  assert.deepEqual(result, { code: "NO_INTERNET", values: {} });
});

test("fetch rejecting (network down, or the timeout firing) reads as no internet, never throws", async () => {
  const fetchImpl = () => Promise.reject(new Error("network unreachable"));
  const result = await callMethod("https://x", "m", {}, { fetchImpl });
  assert.deepEqual(result, { code: "NO_INTERNET", values: {} });
});

test("checkCode, refuseCode and joinWithCode call the right dotted paths", async () => {
  const fetchImpl = fakeFetch(200, { message: { ok: 1 } });
  await checkCode("https://x", "CODE123", null, { fetchImpl });
  assert.equal(fakeFetch.lastUrl, "https://x/api/method/alvoraa_portal.field_app_join.check_code");

  await refuseCode("https://x", "CODE123", { fetchImpl });
  assert.equal(fakeFetch.lastUrl, "https://x/api/method/alvoraa_portal.field_app_join.refuse_code");

  await joinWithCode("https://x", { code: "CODE123", notice_version: "2026-09-13" }, { fetchImpl });
  assert.equal(fakeFetch.lastUrl, "https://x/api/method/alvoraa_portal.field_app_join.join_with_code");
  const sentBody = JSON.parse(fakeFetch.lastInit.body);
  assert.equal(sentBody.agreed, 1); // D18/01b: the tick is required; this call never skips it
  assert.equal(sentBody.code, "CODE123");
});
