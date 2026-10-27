/**
 * ALV-222: a findable sign-out in the employee portal.
 *
 * This is a gate, not a nicety. Slice 062 puts the portal on a phone's home
 * screen; DTC has 441 staff logins on shared factory handsets. An installed app
 * with no findable sign-out is worse than a browser tab, because a tab can be
 * closed and an icon looks private.
 *
 * Each check below is one of the four properties the design asks for (072 E-6),
 * so a bad merge that drops one fails here by name rather than being found by
 * the next person to pick up the handset:
 *
 *   1. the WORD "Sign out", not a door glyph
 *   2. ALWAYS VISIBLE - on the bar, not inside the account dropdown
 *   3. at least 44px tall
 *   4. on the PORTAL's own bar, so it survives whatever Frappe does to its navbar
 *
 * Plus two it must not break: it ends the session on the server, and it does not
 * remove the account menu's own Log out (Surbhi: add, do not replace).
 *
 * Scripts are not run. Nothing here needs the half-megabyte portal bundle, and
 * the sign-out deliberately needs no JavaScript beyond an attribute - it is an
 * <a> with a real href, which is also why it works from a keyboard with no
 * handler at all.
 */
const { JSDOM } = require("jsdom");
const { readPortalSource } = require("../../scripts/lib/portal_source");

const html = readPortalSource(process.argv[2]);
let pass = 0, fail = 0;
const ok  = m => { pass++; console.log("  PASS  " + m); };
const bad = m => { fail++; console.log("  FAIL  " + m); };

const dom = new JSDOM(html, { runScripts: "outside-only", pretendToBeVisual: true });
const { window } = dom;
const doc = window.document;

const all = doc.querySelectorAll(".mob-signout");
if (all.length !== 1) {
  bad(`expected exactly one .mob-signout on the page, found ${all.length}`);
  console.log(`\n### ALV-222 sign-out: ${pass} passed, ${fail} failed`);
  process.exit(1);
}
const out = all[0];

/* 4. On the portal's OWN bar. Not Frappe's navbar, which panels.css hides
      below 768px anyway, and not some floating layer. */
if (out.parentElement && out.parentElement.classList.contains("mob-header")) {
  ok("the sign-out is a direct child of the portal's own .mob-header");
} else {
  bad("the sign-out is not on .mob-header - it is in <" +
      (out.parentElement ? out.parentElement.tagName.toLowerCase() +
       ' class="' + out.parentElement.className + '"' : "nothing") + ">");
}

/* 2. Always visible: not inside the account dropdown, and not display:none. */
if (!doc.querySelector("#mob-acct-menu .mob-signout")) {
  ok("the sign-out is not inside the #mob-acct-menu dropdown");
} else {
  bad("the sign-out is back inside the dropdown - that is the bug ALV-222 is about");
}
if (!out.closest("[hidden]") && out.getAttribute("hidden") === null) {
  ok("the sign-out carries no hidden attribute");
} else {
  bad("the sign-out is hidden");
}
const display = window.getComputedStyle(out).display;
if (display && display !== "none") {
  ok(`the sign-out's own rule leaves it displayed (display:${display})`);
} else {
  bad(`the sign-out computes to display:${display}`);
}

/* 1. The word, and a translatable one. The source is unrendered Jinja here, so
      the literal `_("Sign out")` call is what proves both at once: there is a
      word, and Hindi and Punjabi can have it. */
const text = out.textContent.trim();
if (/_\(\s*["']Sign out["']\s*\)/.test(text)) {
  ok('the sign-out is labelled with the words _("Sign out")');
} else {
  bad(`the sign-out's label is not _("Sign out") - it is “${text}”`);
}
if (!out.querySelector("svg")) {
  ok("the label is a word, not a glyph (no svg inside it)");
} else {
  bad("the sign-out contains an svg - a door glyph means nothing to someone who has not used many apps");
}

/* 3. At least 44px of thumb. The rule is unconditional on purpose; see the
      comment beside it in frame.css. */
const minH = window.getComputedStyle(out).minHeight;
const px = parseFloat(minH);
if (px >= 44) {
  ok(`the sign-out is at least 44px tall (min-height:${minH})`);
} else {
  bad(`the sign-out is only min-height:${minH} - the design asks for 44px`);
}

/* It ends the session on the server, not just the screen. */
if (out.getAttribute("href") === "/logout") {
  ok("the sign-out points at /logout, which ends the session on the server");
} else {
  bad(`the sign-out points at ${out.getAttribute("href")}, not /logout`);
}

/* And it takes the portal's one piece of browser storage with it. */
const click = out.getAttribute("onclick") || "";
if (/removeItem\(\s*['"]sb-pinned['"]\s*\)/.test(click)) {
  ok("signing out clears localStorage['sb-pinned'], the one thing the portal keeps here");
} else {
  bad("signing out leaves localStorage['sb-pinned'] behind for the next person");
}
if (/\btry\b/.test(click) && /\bcatch\b/.test(click)) {
  ok("the storage clear cannot stop the sign-out (private mode throws)");
} else {
  bad("the storage clear is unguarded - localStorage throws in some private modes, " +
      "and a sign-out must never be the thing that fails");
}

/* Nothing was replaced: ALV-213's account menu still has its own way out. */
const menuOut = doc.querySelector('#mob-acct-menu a[href="/logout"]');
if (menuOut) {
  ok("the account menu still has its own Log out (add, do not replace)");
} else {
  bad("the account menu's Log out has gone - this change was meant to add one, not swap one");
}

console.log(`\n### ALV-222 sign-out: ${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
