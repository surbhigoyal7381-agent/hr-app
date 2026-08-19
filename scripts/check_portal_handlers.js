/*
 * Clicking a portal button runs an inline on*= handler, which resolves ONLY against
 * global scope. hrms-employee.html wraps most of its code in an IIFE, so a helper
 * declared inside it is invisible to code outside. The click throws ReferenceError
 * and NOTHING happens - no error banner, no console message the user would see.
 *
 * That is how "+ Apply Leave" and "+ New Claim" died: both call pfClearErr(), which
 * was declared inside the IIFE. Static linting cannot see it, so this check loads the
 * page's scripts in a VM with stubbed DOM/Frappe and actually CALLS every handler,
 * reporting only ReferenceError - the signal that an identifier is out of scope.
 *
 * Usage: node scripts/check_portal_handlers.js [file.html ...]
 */
const fs = require("fs"), path = require("path"), vm = require("vm");

const EVENTS = ["onclick=", "onchange=", "oninput=", "onsubmit=", "onkeyup=",
  "onkeydown=", "onfocus=", "onblur="];
const NOT_FUNCS = new Set(["if", "for", "while", "return", "function", "typeof", "new",
  "var", "JSON", "Math", "Number", "String", "Array", "Object", "Boolean", "parseInt",
  "parseFloat", "isNaN", "encodeURIComponent", "decodeURIComponent", "alert", "confirm",
  "prompt", "setTimeout", "setInterval", "rgba", "rgb", "url", "translate", "rotate",
  "scale"]);
const BSQ = String.fromCharCode(92) + '"';
const IDENT = /(?<![.\w$])([A-Za-z_$][\w$]*)\s*\(/g;
const CONCAT = /'[^']*?[+][^+]*?[+][^']*?'/gs;

function handlerNames(html) {
  const out = new Set();
  for (const ev of EVENTS) {
    let i = 0;
    while ((i = html.indexOf(ev, i)) >= 0) {
      const rest = html.slice(i + ev.length);
      let seg = "";
      if (rest.startsWith(BSQ)) {
        const e = rest.indexOf(BSQ, BSQ.length);
        seg = e > 0 ? rest.slice(BSQ.length, e) : "";
      } else if (rest[0] === '"' || rest[0] === "'") {
        const e = rest.indexOf(rest[0], 1);
        seg = e > 0 ? rest.slice(1, e) : "";
      }
      seg = seg.replace(CONCAT, "");
      let m;
      IDENT.lastIndex = 0;
      while ((m = IDENT.exec(seg))) if (!NOT_FUNCS.has(m[1])) out.add(m[1]);
      i += ev.length;
    }
  }
  return [...out];
}

function stub(name) {
  return new Proxy(function () {}, {
    get: (t, p) => (p === Symbol.toPrimitive || p === "toString") ? () => "" :
                   (p === "length" ? 0 : stub(name + "." + String(p))),
    apply: () => stub(name + "()"),
    construct: () => stub("new " + name),
    set: () => true,
  });
}

function check(file) {
  let html = fs.readFileSync(file, "utf8").replace(/^﻿/, "");
  const blocks = [...html.matchAll(/<script([^>]*)>([\s\S]*?)<\/script>/g)]
    .filter((m) => !m[1].includes("src=")).map((m) => m[2]);
  if (!blocks.length) return [];

  const ctx = { console: { log() {}, warn() {}, error() {} } };
  ctx.window = ctx; ctx.globalThis = ctx; ctx.self = ctx; ctx.top = ctx;
  for (const g of ["document", "frappe", "localStorage", "sessionStorage", "navigator",
                   "location", "history", "L", "Chart", "html2canvas", "moment"])
    ctx[g] = stub(g);
  ctx.addEventListener = () => {}; ctx.removeEventListener = () => {};
  ctx.matchMedia = () => ({ matches: false, addEventListener() {}, addListener() {} });
  ctx.getComputedStyle = () => stub("cs");
  ctx.requestAnimationFrame = () => 0;
  ctx.setTimeout = () => 0; ctx.setInterval = () => 0;
  ctx.clearTimeout = () => {}; ctx.clearInterval = () => {};
  ctx.confirm = () => true; ctx.alert = () => {}; ctx.prompt = () => "";
  // A resolving promise would run .then() callbacks as microtasks AFTER this
  // check finishes, throwing outside any try/catch. Never resolve.
  ctx.fetch = () => new Promise(() => {});
  vm.createContext(ctx);

  const problems = [];
  blocks.forEach((body, n) => {
    // Jinja -> valid JS. Expressions already sitting inside quotes must not gain
    // a second pair, so those are substituted first.
    const src = body
      .replace(/"\{\{[\s\S]*?\}\}"/g, '"J"')
      .replace(/'\{\{[\s\S]*?\}\}'/g, "'J'")
      .replace(/\{\{[\s\S]*?\}\}/g, '"J"')
      .replace(/\{%[\s\S]*?%\}/g, "");
    try {
      vm.runInContext(src, ctx, { filename: path.basename(file) + ":script" + n });
    } catch (e) {
      problems.push("script block " + n + " threw at LOAD: " + e.message +
        " - everything assigned after this point never gets defined");
    }
  });

  for (const name of handlerNames(html)) {
    if (typeof ctx[name] !== "function") {
      problems.push(name + "() is not reachable from global scope");
      continue;
    }
    try { ctx[name](); }
    catch (e) {
      // The error is constructed inside the VM realm, so `instanceof` from out here
      // does not match. Compare the name instead.
      if (e && e.constructor && e.constructor.name === "ReferenceError")
        problems.push(name + "() throws " + e.message + " - the click does nothing");
    }
  }
  return problems;
}

const files = process.argv.slice(2).length ? process.argv.slice(2)
  : fs.readdirSync(path.join(__dirname, "..", "alvoraa_portal", "alvoraa_portal", "www"))
      .filter((f) => f.endsWith(".html"))
      .map((f) => path.join(__dirname, "..", "alvoraa_portal", "alvoraa_portal", "www", f));

let bad = 0;
for (const f of files) {
  const problems = check(f);
  if (problems.length) {
    bad += problems.length;
    console.log("FAIL " + path.basename(f));
    problems.forEach((p) => console.log("   " + p));
  } else {
    console.log("ok   " + path.basename(f));
  }
}
if (bad) { console.log("portal handlers: " + bad + " problem(s)"); process.exit(1); }
console.log("portal handlers: all reachable and callable");
// exit now, so any timer/microtask the page queued cannot fire after the verdict
process.exit(0);
