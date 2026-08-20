/*
 * Find identifiers a portal page USES but never DEFINES.
 *
 * check_portal_handlers.js calls each button handler, but it cannot reach code
 * behind form validation, and a page that wraps work in its own try/catch turns
 * the failure into a banner rather than an error. That is how
 * "selectedPlan is not defined" shipped and blocked every tenant creation.
 * A static check does not need to reach the line.
 *
 * ESLint's no-undef does this. Naively it is unusable here: this codebase
 * publishes functions as `window.foo = ...` and then calls them bare as `foo()`,
 * and no-undef flags every one. So each page's `window.NAME =` assignments are
 * collected first and passed to ESLint as declared globals for that page, which
 * turns a noisy report into a precise one.
 *
 * Usage: node scripts/check_undefined_js.js [file.html ...]
 */
const fs = require("fs");
const os = require("os");
const path = require("path");
const { execFileSync } = require("child_process");

// Pinned, for the same reason ruff is pinned in CI: a different version reports
// a different set, and a check that changes under you gets ignored.
const ESLINT = "eslint@9.39.5";

// Globals the browser and Frappe really do provide. Missing entries show up as
// false positives, so keep this generous - but only add things that exist.
const GLOBALS = [
  "window", "document", "console", "navigator", "location", "history", "screen",
  "setTimeout", "clearTimeout", "setInterval", "clearInterval", "queueMicrotask",
  "requestAnimationFrame", "cancelAnimationFrame", "fetch", "XMLHttpRequest",
  "FormData", "Blob", "File", "FileReader", "URL", "URLSearchParams", "Image",
  "Audio", "Event", "CustomEvent", "MutationObserver", "IntersectionObserver",
  "ResizeObserver", "AbortController", "localStorage", "sessionStorage", "alert",
  "confirm", "prompt", "getComputedStyle", "matchMedia", "atob", "btoa",
  "structuredClone", "TextEncoder", "TextDecoder", "performance", "crypto",
  "Notification", "WebSocket", "Worker", "DOMParser", "Node", "HTMLElement",
  "Element", "NodeList", "Option", "CSS", "scrollTo", "getSelection",
  // Frappe, plus the libraries these pages load
  "frappe", "__", "moment", "L", "Chart", "html2canvas", "io", "$", "jQuery",
];

function extractJs(html) {
  const blocks = [...html.matchAll(/<script([^>]*)>([\s\S]*?)<\/script>/g)]
    .filter((m) => !m[1].includes("src="))
    .map((m) => m[2]);
  return blocks
    .join("\n;\n")
    // Jinja -> valid JS. Expressions already inside quotes are handled first so
    // they do not end up double-quoted.
    .replace(/"\{\{[\s\S]*?\}\}"/g, '"J"')
    .replace(/'\{\{[\s\S]*?\}\}'/g, "'J'")
    .replace(/\{\{[\s\S]*?\}\}/g, '"J"')
    .replace(/\{%[\s\S]*?%\}/g, "");
}

// `window.foo = ...` publishes foo; the page then calls it bare.
function windowGlobals(js) {
  return [...js.matchAll(/window\.([A-Za-z_$][\w$]*)\s*=/g)].map((m) => m[1]);
}

const wwwDir = path.join(__dirname, "..", "alvoraa_portal", "alvoraa_portal", "www");
const files = process.argv.slice(2).length
  ? process.argv.slice(2)
  : fs.readdirSync(wwwDir).filter((f) => f.endsWith(".html")).map((f) => path.join(wwwDir, f));

const work = fs.mkdtempSync(path.join(os.tmpdir(), "undefjs-"));
const configs = [];
const pages = [];

for (const file of files) {
  const html = fs.readFileSync(file, "utf8").replace(/^﻿/, "");
  const js = extractJs(html);
  if (!js.trim()) {
    console.log("skip " + path.basename(file) + " (no inline script)");
    continue;
  }

  const base = path.basename(file, ".html").replace(/[^a-z0-9]/gi, "_");
  fs.writeFileSync(path.join(work, base + ".js"), js);
  pages.push({ base, file });

  // Scoped with `files` so one page's exports cannot mask a real mistake on another.
  const declared = [...new Set([...GLOBALS, ...windowGlobals(js)])];
  const globalsObj = JSON.stringify(Object.fromEntries(declared.map((g) => [g, "readonly"])));
  configs.push(
    "{files:['" + base + ".js'],languageOptions:{ecmaVersion:2022,sourceType:'script',globals:" +
      globalsObj +
      "},rules:{'no-undef':'error'}}"
  );
}

fs.writeFileSync(path.join(work, "eslint.config.mjs"), "export default [" + configs.join(",") + "];\n");

// One ESLint run for all pages. Invoking npx per file costs minutes.
let out = "";
try {
  out = execFileSync(
    "npx",
    ["--yes", ESLINT, "--no-config-lookup", "-c", "eslint.config.mjs", "--format", "json", "."],
    { cwd: work, encoding: "utf8", stdio: ["ignore", "pipe", "pipe"], shell: process.platform === "win32" }
  );
} catch (e) {
  out = (e.stdout || "") + (e.stderr || "");
}

let results;
try {
  results = JSON.parse(out.slice(out.indexOf("[")));
} catch (e) {
  console.log("Could not parse ESLint output. Raw output follows:");
  console.log(out.slice(0, 2000));
  process.exit(2);
}

let failures = 0;
for (const { base, file } of pages) {
  const r = results.find((x) => path.basename(x.filePath) === base + ".js");
  const undef = ((r && r.messages) || []).filter((m) => m.ruleId === "no-undef");
  if (undef.length) {
    failures += undef.length;
    console.log("FAIL " + path.basename(file));
    for (const m of undef) console.log("   line " + m.line + ": " + m.message);
  } else {
    console.log("ok   " + path.basename(file));
  }
}

fs.rmSync(work, { recursive: true, force: true });

if (failures) {
  console.log("undefined identifiers: " + failures + " problem(s)");
  console.log("Each is a value the code reads but nothing ever creates - it throws when reached.");
  process.exit(1);
}
console.log("undefined identifiers: none");
