/**
 * Read hrms-employee.html the way the server does: with its includes expanded.
 *
 * Slice 034 US-10 (AC-37, OPS-6). The page used to be one 18,000-line file that
 * every check opened directly. It is now a short page that pulls in a dozen or so
 * Jinja include files. A check that kept calling fs.readFileSync on the page alone
 * would still pass - while reading a 30-line shell and checking almost nothing.
 * That is worse than no check, so every Node check now comes through here.
 *
 * Two guards make silence impossible:
 *   - at least one include tag must be expanded, and
 *   - every file under templates/includes/ess/ must be reached by the expansion.
 *
 * The matching Python helper is alvoraa_portal/alvoraa_portal/tests/portal_source.py.
 */
const fs = require("fs");
const path = require("path");

const APP_ROOT = path.join(__dirname, "..", "..", "alvoraa_portal", "alvoraa_portal");
const WWW = path.join(APP_ROOT, "www");
const PORTAL_PAGE = path.join(WWW, "hrms-employee.html");
const ESS_DIR = path.join(APP_ROOT, "templates", "includes", "ess");

// Only our own include files. design_system.html and brand_color.html are shared
// with five other pages and were never part of this page's source.
const INCLUDE_RE = /\{%\s*include\s+"(templates\/includes\/ess\/[^"]+)"\s*%\}\r?\n?/g;
const MAX_DEPTH = 5;

function essFilesOnDisk(dir = ESS_DIR) {
  const out = [];
  if (!fs.existsSync(dir)) return out;
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) out.push(...essFilesOnDisk(full));
    else out.push(path.relative(APP_ROOT, full).split(path.sep).join("/"));
  }
  return out;
}

function expand(text, used, depth = 0) {
  if (depth > MAX_DEPTH) throw new Error("include files are nested more than " + MAX_DEPTH + " deep");
  return text.replace(INCLUDE_RE, (_m, rel) => {
    const file = path.join(APP_ROOT, ...rel.split("/"));
    if (!fs.existsSync(file)) throw new Error("the page includes " + rel + ", which does not exist");
    used.add(rel);
    return expand(fs.readFileSync(file, "utf8"), used, depth + 1);
  });
}

/**
 * The page's full source, includes expanded, BOM removed and newlines normalised -
 * exactly what the old `fs.readFileSync(page, "utf8")` calls used to hand back.
 */
function readPortalSource(file = PORTAL_PAGE) {
  const raw = fs.readFileSync(file, "utf8").replace(/^﻿/, "");
  const used = new Set();
  const out = expand(raw, used);

  if (path.resolve(file) === path.resolve(PORTAL_PAGE)) {
    if (used.size === 0) {
      throw new Error(
        "hrms-employee.html has no ess include tags. Either the page was flattened " +
        "or this helper is reading the wrong file - either way every check calling " +
        "it would now be checking a shell."
      );
    }
    const orphans = essFilesOnDisk().filter((f) => !used.has(f));
    if (orphans.length) {
      throw new Error(
        "these include files exist but nothing includes them, so their contents " +
        "are checked by nobody: " + orphans.sort().join(", ")
      );
    }
  }
  return out.split("\r\n").join("\n");
}

module.exports = { readPortalSource, essFilesOnDisk, PORTAL_PAGE, WWW, APP_ROOT };
