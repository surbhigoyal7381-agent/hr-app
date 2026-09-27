/*
 * Small building blocks the Material 3 screens share (ALV-133): icons, the
 * notice's six parts, the look of each problem screen, list rows, the
 * welcome screen, and the dialog, bottom sheet and snackbar.
 *
 * The same rule as every other file: text from the server goes in with
 * textContent, never as HTML (SEC-17). Icons are built as SVG elements, not
 * from an HTML string. The pure parts (the maps, initials, formatWhen) are
 * exported for the Node tests.
 */
(function (root) {
  "use strict";

  // Material Symbols shapes, 24 px (the prototype's set, 01d §6).
  var ICONS = {
    back: "M20 11H7.83l5.59-5.59L12 4l-8 8 8 8 1.41-1.41L7.83 13H20v-2z",
    close: "M19 6.41 17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z",
    check: "M9 16.17 4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z",
    checkCircle: "M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z",
    settings: "M19.14 12.94c.04-.3.06-.61.06-.94 0-.32-.02-.64-.07-.94l2.03-1.58a.49.49 0 0 0 .12-.61l-1.92-3.32a.488.488 0 0 0-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94l-.36-2.54a.484.484 0 0 0-.48-.41h-3.84c-.24 0-.43.17-.47.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96c-.22-.08-.47 0-.59.22L2.74 8.87c-.12.21-.08.47.12.61l2.03 1.58c-.05.3-.09.63-.09.94s.02.64.07.94l-2.03 1.58a.49.49 0 0 0-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.12-.22.07-.47-.12-.61l-2.01-1.58zM12 15.6c-1.98 0-3.6-1.62-3.6-3.6s1.62-3.6 3.6-3.6 3.6 1.62 3.6 3.6-1.62 3.6-3.6 3.6z",
    pin: "M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z",
    camera: "M12 15.2a3.2 3.2 0 1 0 0-6.4 3.2 3.2 0 0 0 0 6.4zM9 2 7.17 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2h-3.17L15 2H9zm3 15c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5z",
    clock: "M11.99 2C6.47 2 2 6.48 2 12s4.47 10 9.99 10C17.52 22 22 17.52 22 12S17.52 2 11.99 2zM12 20c-4.42 0-8-3.58-8-8s3.58-8 8-8 8 3.58 8 8-3.58 8-8 8zm.5-13H11v6l5.25 3.15.75-1.23-4.5-2.67z",
    eyeOff: "M12 7c2.76 0 5 2.24 5 5 0 .65-.13 1.26-.36 1.83l2.92 2.92c1.51-1.26 2.7-2.89 3.43-4.75-1.73-4.39-6-7.5-11-7.5-1.4 0-2.74.25-3.98.7l2.16 2.16C10.74 7.13 11.35 7 12 7zM2 4.27l2.28 2.28.46.46C3.08 8.3 1.78 10.02 1 12c1.73 4.39 6 7.5 11 7.5 1.55 0 3.03-.3 4.38-.84l.42.42L19.73 22 21 20.73 3.27 3 2 4.27zM7.53 9.8l1.55 1.55c-.05.21-.08.43-.08.65 0 1.66 1.34 3 3 3 .22 0 .44-.03.65-.08l1.55 1.55c-.67.33-1.41.53-2.2.53-2.76 0-5-2.24-5-5 0-.79.2-1.53.53-2.2zm4.31-.78 3.15 3.15.02-.16c0-1.66-1.34-3-3-3l-.17.01z",
    eye: "M12 4.5C7 4.5 2.73 7.61 1 12c1.73 4.39 6 7.5 11 7.5s9.27-3.11 11-7.5c-1.73-4.39-6-7.5-11-7.5zM12 17c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5zm0-8c-1.66 0-3 1.34-3 3s1.34 3 3 3 3-1.34 3-3-1.34-3-3-3z",
    help: "M11 18h2v-2h-2v2zm1-16C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm0-14c-2.21 0-4 1.79-4 4h2c0-1.1.9-2 2-2s2 .9 2 2c0 2-3 1.75-3 5h2c0-2.25 3-2.5 3-5 0-2.21-1.79-4-4-4z",
    group: "M16 11c1.66 0 2.99-1.34 2.99-3S17.66 5 16 5c-1.66 0-3 1.34-3 3s1.34 3 3 3zm-8 0c1.66 0 2.99-1.34 2.99-3S9.66 5 8 5C6.34 5 5 6.34 5 8s1.34 3 3 3zm0 2c-2.33 0-7 1.17-7 3.5V19h14v-2.5c0-2.33-4.67-3.5-7-3.5zm8 0c-.29 0-.62.02-.97.05 1.16.84 1.97 1.97 1.97 3.45V19h6v-2.5c0-2.33-4.67-3.5-7-3.5z",
    hourglass: "M6 2v6h.01L6 8.01 10 12l-4 4 .01.01H6V22h12v-5.99h-.01L18 16l-4-4 4-3.99-.01-.01H18V2H6zm10 14.5V20H8v-3.5l4-4 4 4zm-4-5-4-4V4h8v3.5l-4 4z",
    shield: "M12 1 3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4zm-2 16-4-4 1.41-1.41L10 14.17l6.59-6.59L18 9l-8 8z",
    login: "M11 7 9.6 8.4l2.6 2.6H2v2h10.2l-2.6 2.6L11 17l5-5-5-5zm9 12h-8v2h8c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2h-8v2h8v14z",
    logout: "M17 7l-1.41 1.41L18.17 11H8v2h10.17l-2.58 2.58L17 17l5-5zM4 5h8V3H4c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h8v-2H4V5z",
    wifiOff: "M23.64 7c-.45-.34-4.93-4-11.64-4-1.5 0-2.89.19-4.15.48L18.18 13.8 23.64 7zm-6.6 8.22L3.27 1.44 2 2.72l2.05 2.06C1.91 5.76.59 6.82.36 7l11.63 14.49.01.01.01-.01 3.9-4.86 3.32 3.32 1.27-1.27-3.46-3.46z",
    gps: "M20.94 11c-.46-4.17-3.77-7.48-7.94-7.94V1h-2v2.06C6.83 3.52 3.52 6.83 3.06 11H1v2h2.06c.46 4.17 3.77 7.48 7.94 7.94V23h2v-2.06c4.17-.46 7.48-3.77 7.94-7.94H23v-2h-2.06zM12 19c-3.87 0-7-3.13-7-7s3.13-7 7-7 7 3.13 7 7-3.13 7-7 7z",
    block: "M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zM4 12c0-4.42 3.58-8 8-8 1.85 0 3.55.63 4.9 1.69L5.69 16.9C4.63 15.55 4 13.85 4 12zm8 8c-1.85 0-3.55-.63-4.9-1.69L18.31 7.1C19.37 8.45 20 10.15 20 12c0 4.42-3.58 8-8 8z",
    phone: "M17 1.01 7 1c-1.1 0-2 .9-2 2v18c0 1.1.9 2 2 2h10c1.1 0 2-.9 2-2V3c0-1.1-.9-1.99-2-1.99zM17 19H7V5h10v14z",
    update: "M17 1.01 7 1c-1.1 0-1.99.9-1.99 2v18c0 1.1.89 2 1.99 2h10c1.1 0 2-.9 2-2V3c0-1.1-.9-1.99-2-1.99zM17 19H7V5h10v14zm-1-6h-3V8h-2v5H8l4 4 4-4z",
    error: "M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z",
    lock: "M18 8h-1V6c0-2.76-2.24-5-5-5S7 3.24 7 6v2H6c-1.1 0-2 .9-2 2v10c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V10c0-1.1-.9-2-2-2zm-6 9c-1.1 0-2-.9-2-2s.9-2 2-2 2 .9 2 2-.9 2-2 2zm3.1-9H8.9V6c0-1.71 1.39-3.1 3.1-3.1 1.71 0 3.1 1.39 3.1 3.1v2z",
    info: "M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z",
    image: "M21 19V5c0-1.1-.9-2-2-2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2zM8.5 13.5l2.5 3.01L14.5 12l4.5 6H5l3.5-4.5z",
    qr: "M9.5 6.5v3h-3v-3h3M11 5H5v6h6V5zm-1.5 9.5v3h-3v-3h3M11 13H5v6h6v-6zm6.5-6.5v3h-3v-3h3M19 5h-6v6h6V5zm-6 8h1.5v1.5H13V13zm1.5 1.5H16V16h-1.5v-1.5zM16 13h1.5v1.5H16V13zm-3 3h1.5v1.5H13V16zm1.5 1.5H16V19h-1.5v-1.5zM16 16h1.5v1.5H16V16zm1.5-1.5H19V16h-1.5v-1.5zm0 3H19V19h-1.5v-1.5zM22 7h-2V4h-3V2h5v5zm0 15v-5h-2v3h-3v2h5zM2 22h5v-2H4v-3H2v5zM2 2v5h2V4h3V2H2z",
    chevron: "M10 6 8.59 7.41 13.17 12l-4.58 4.59L10 18l6-6z",
    store: "M12 7V3H2v18h20V7H12zM6 19H4v-2h2v2zm0-4H4v-2h2v2zm0-4H4V9h2v2zm0-4H4V5h2v2zm4 12H8v-2h2v2zm0-4H8v-2h2v2zm0-4H8V9h2v2zm0-4H8V5h2v2zm10 12h-8v-2h2v-2h-2v-2h2v-2h-2V9h8v10zm-2-8h-2v2h2v-2zm0 4h-2v2h2v-2z",
    person: "M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z",
    refresh: "M17.65 6.35A7.958 7.958 0 0 0 12 4c-4.42 0-7.99 3.58-7.99 8s3.57 8 7.99 8c3.73 0 6.84-2.55 7.73-6h-2.08A5.99 5.99 0 0 1 12 18c-3.31 0-6-2.69-6-6s2.69-6 6-6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35z",
    del: "M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z",
    doc: "M14 2H6c-1.1 0-1.99.9-1.99 2L4 20c0 1.1.89 2 1.99 2H18c1.1 0 2-.9 2-2V8l-6-6zm2 16H8v-2h8v2zm0-4H8v-2h8v2zm-3-5V3.5L18.5 9H13z",
    globe: "M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z",
    key: "M12.65 10A5.99 5.99 0 0 0 7 6c-3.31 0-6 2.69-6 6s2.69 6 6 6a5.99 5.99 0 0 0 5.65-4H17v4h4v-4h2v-4H12.65zM7 14c-1.1 0-2-.9-2-2s.9-2 2-2 2 .9 2 2-.9 2-2 2z",
    undo: "M12.5 8c-2.65 0-5.05.99-6.9 2.6L2 7v9h9l-3.62-3.62c1.39-1.16 3.16-1.88 5.12-1.88 3.54 0 6.55 2.31 7.6 5.5l2.37-.78C21.08 11.03 17.15 8 12.5 8z",
  };

  // The six notice parts, by the server's stable key (E-4). If a server sends
  // no key (an older build), the part's place in the list decides.
  var NOTICE_ICONS = {
    record: "camera", not_record: "eyeOff", why: "help",
    who: "group", how_long: "hourglass", rights: "shield",
  };
  var NOTICE_ORDER = ["record", "not_record", "why", "who", "how_long", "rights"];

  function noticeIcon(row, index) {
    var key = row && row.key;
    if (key && NOTICE_ICONS[key]) return NOTICE_ICONS[key];
    return NOTICE_ICONS[NOTICE_ORDER[index]] || "info";
  }

  // The picture and tone of each problem screen (01d §7.7): colour, icon AND
  // words, never colour alone. Keyed by the `screen` id that join-screens.js
  // and checkin-screens.js already return.
  var PROBLEM_LOOK = {
    // joining
    qrExpired: ["qr", "warning"], qrUsed: ["qr", "warning"], qrCancelled: ["qr", "warning"],
    notAlvoraa: ["qr", "warning"], pickNoQr: ["image", "warning"], codeJoinOff: ["qr", "neutral"],
    camDenied: ["camera", "warning"], noSignalJoin: ["wifiOff", "neutral"],
    // either flow
    appOff: ["info", "neutral"], notField: ["person", "neutral"], featureOff: ["info", "neutral"],
    update: ["update", "primary"], serverError: ["error", "error"], tooMany: ["clock", "warning"],
    unknownCode: ["update", "primary"],
    // daily use
    blocked: ["block", "error"], replaced: ["phone", "neutral"], left: ["person", "neutral"],
    locOff: ["gps", "warning"], locDenied: ["pin", "warning"], gpsVague: ["gps", "warning"],
    outside: ["pin", "warning"], noSignal: ["wifiOff", "neutral"], duplicate: ["checkCircle", "success"],
  };

  function problemLook(screen) {
    var look = PROBLEM_LOOK[screen] || ["error", "error"];
    return { icon: look[0], tone: look[1] };
  }

  // "PP Jewellers" -> "PJ"; "Sargam" -> "SA"; "" -> "A" (Alvoraa).
  function initials(name) {
    var words = String(name || "").trim().split(/\s+/).filter(Boolean);
    if (!words.length) return "A";
    if (words.length === 1) return words[0].slice(0, 2).toUpperCase();
    return (words[0][0] + words[1][0]).toUpperCase();
  }

  var WEEKDAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
  var MONTHS = ["January", "February", "March", "April", "May", "June", "July",
    "August", "September", "October", "November", "December"];

  function clock(d) {
    var h = d.getHours();
    var m = d.getMinutes();
    return (h % 12 || 12) + ":" + (m < 10 ? "0" + m : m) + " " + (h < 12 ? "am" : "pm");
  }

  function dayDate(d) {
    return WEEKDAYS[d.getDay()] + " " + d.getDate() + " " + MONTHS[d.getMonth()];
  }

  // The notice cache's "agreed at" is the phone's clock in UTC with no mark
  // ("2026-09-22 03:31:00", from toISOString). Shown in the phone's own time.
  function formatWhen(value) {
    if (!value) return "";
    var d = new Date(String(value).replace(" ", "T") + (/[zZ+]/.test(String(value).slice(10)) ? "" : "Z"));
    if (isNaN(d.getTime())) return String(value);
    return dayDate(d) + " at " + clock(d);
  }

  // ── the DOM part ──────────────────────────────────────────────────────

  // The SVG namespace. It is a name, never fetched; it is built in parts only so
  // check_app.mjs's no-outside-URL rule (OPS-22) keeps meaning what it says.
  var SVG_NS = ["http:", "", "www.w3.org", "2000", "svg"].join("/");

  function icon(name, className) {
    var doc = root.document;
    var svg = doc.createElementNS(SVG_NS, "svg");
    svg.setAttribute("class", "ic" + (className ? " " + className : ""));
    svg.setAttribute("viewBox", "0 0 24 24");
    svg.setAttribute("aria-hidden", "true");
    svg.setAttribute("focusable", "false");
    var path = doc.createElementNS(SVG_NS, "path");
    path.setAttribute("d", ICONS[name] || ICONS.info);
    svg.appendChild(path);
    return svg;
  }

  function clear(node) {
    while (node.firstChild) node.removeChild(node.firstChild);
  }

  function text(tag, value, className) {
    var node = root.document.createElement(tag);
    node.textContent = value;
    if (className) node.className = className;
    return node;
  }

  function bubble(iconName, tone, small) {
    var b = root.document.createElement("div");
    b.className = "bubble " + (small ? "sm " : "") + "tone-" + tone;
    b.appendChild(icon(iconName));
    return b;
  }

  // Fill an element that already exists in index.html with a new icon.
  function setIcon(node, name, className) {
    if (!node) return;
    clear(node);
    node.appendChild(icon(name, className));
  }

  // The same bubble element, repainted: one icon and one tone.
  function setBubble(node, iconName, tone) {
    if (!node) return;
    node.className = "bubble tone-" + tone;
    setIcon(node, iconName);
  }

  /*
   * One list row. o = { lead: iconName | Node, hl, sup, trail: text | Node,
   * danger, action } - `action` makes it a button with that data-action.
   */
  function listItem(o) {
    var doc = root.document;
    var li = doc.createElement("li");
    var row = doc.createElement(o.action ? "button" : "div");
    if (o.action) {
      row.type = "button";
      row.setAttribute("data-action", o.action);
    }
    row.className = "list-item" + (o.sup ? " two" : "") + (o.action ? " link" : "")
      + (o.danger ? " danger" : "");
    if (o.lead) {
      var lead = doc.createElement("span");
      lead.className = "lead";
      lead.appendChild(typeof o.lead === "string" ? icon(o.lead) : o.lead);
      row.appendChild(lead);
    }
    var txt = doc.createElement("span");
    txt.className = "txt";
    txt.appendChild(text("span", o.hl || "", "hl"));
    if (o.sup) txt.appendChild(text("span", o.sup, "sup"));
    row.appendChild(txt);
    if (o.trail) {
      var trail = doc.createElement("span");
      trail.className = "trail";
      trail.appendChild(typeof o.trail === "string" ? text("span", o.trail) : o.trail);
      row.appendChild(trail);
    }
    li.appendChild(row);
    return li;
  }

  function divider() {
    var li = root.document.createElement("li");
    li.className = "divider";
    li.setAttribute("aria-hidden", "true");
    return li;
  }

  // A list with dividers between the rows.
  function fillList(list, items) {
    clear(list);
    items.forEach(function (item, i) {
      if (i) list.appendChild(divider());
      list.appendChild(listItem(item));
    });
  }

  // The six notice parts, each with its picture. The words are the server's,
  // exactly as sent - the layout is the only thing this decides.
  function renderNoticeRows(container, rows) {
    clear(container);
    (rows || []).forEach(function (row, i) {
      var part = root.document.createElement("div");
      part.className = "notice-row";
      part.appendChild(bubble(noticeIcon(row, i), "secondary", true));
      var words = root.document.createElement("div");
      words.appendChild(text("h3", row.heading));
      words.appendChild(text("p", row.body, "t-body-l muted"));
      part.appendChild(words);
      container.appendChild(part);
    });
  }

  // The company tile in the top bar: its initials on the brand colour.
  function setBrandBar(markEl, titleEl, subEl, company, sub) {
    if (markEl) markEl.textContent = initials(company);
    if (titleEl) titleEl.textContent = company || "";
    if (subEl) {
      subEl.textContent = sub || "";
      subEl.hidden = !sub;
    }
  }

  /*
   * Welcome (join.js after a code, signin.js after a password). `whereShort`
   * is checkin-screens.js's "Within 200 m" / "From anywhere", so a radius of
   * 0 is never "within 0 m".
   */
  function renderWelcome(data, whereShort) {
    var t = root.AlvoraaStrings.t;
    var doc = root.document;
    doc.getElementById("welcome-heading").textContent = t("welcomeHeading", { name: data.first_name || "" });
    setBrandBar(doc.getElementById("welcome-mark"), doc.getElementById("welcome-company-bar"), null,
      data.company || "");
    var items = [{ lead: "store", hl: data.company || "", sup: t("labelCompany") }];
    if (data.workplace && data.workplace.name) {
      items.push({ lead: "pin", hl: data.workplace.name, sup: t("labelWorkplace") });
    }
    items.push({ lead: "gps", hl: whereShort, sup: t("labelWhere") });
    fillList(doc.getElementById("welcome-card"), items);
  }

  // index.html writes <span data-icon="name"> where an icon goes; this draws
  // each one once, on start. data-icon-class adds a size class ("s20").
  function hydrateIcons(scope) {
    var nodes = (scope || root.document).querySelectorAll("[data-icon]");
    for (var i = 0; i < nodes.length; i++) {
      var node = nodes[i];
      if (node.firstChild) continue;
      node.appendChild(icon(node.getAttribute("data-icon"), node.getAttribute("data-icon-class")));
    }
  }

  // ── dialog, bottom sheet, snackbar ─────────────────────────────────────

  var FOCUSABLE = "button:not([disabled]), [href], input:not([disabled]), [tabindex]:not([tabindex='-1'])";
  var openers = {};

  function openOverlay(id) {
    var scrim = root.document.getElementById(id);
    if (!scrim) return;
    openers[id] = root.document.activeElement;
    scrim.hidden = false;
    var first = scrim.querySelector(FOCUSABLE);
    if (first) first.focus();
  }

  function closeOverlay(id) {
    var scrim = root.document.getElementById(id);
    if (!scrim || scrim.hidden) return;
    scrim.hidden = true;
    var back = openers[id];
    openers[id] = null;
    if (back && back.focus && root.document.contains(back)) back.focus();
  }

  function closeAllOverlays() {
    var open = root.document.querySelectorAll(".scrim:not([hidden])");
    for (var i = 0; i < open.length; i++) open[i].hidden = true;
  }

  function wireOverlays() {
    var doc = root.document;
    doc.addEventListener("keydown", function (event) {
      var open = doc.querySelector(".scrim:not([hidden])");
      if (!open) return;
      if (event.key === "Escape") {
        event.preventDefault();
        var cancel = open.querySelector("[data-overlay-cancel]");
        if (cancel) cancel.click(); else closeOverlay(open.id);
        return;
      }
      if (event.key !== "Tab") return;
      // Keep the keyboard inside the dialog while it is open.
      var items = open.querySelectorAll(FOCUSABLE);
      if (!items.length) return;
      var first = items[0];
      var last = items[items.length - 1];
      if (event.shiftKey && doc.activeElement === first) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && doc.activeElement === last) { event.preventDefault(); first.focus(); }
    });
    // A tap on the dimmed area outside a sheet or dialog is "cancel".
    doc.addEventListener("click", function (event) {
      var target = event.target;
      if (target && target.classList && target.classList.contains("scrim")) {
        var cancel = target.querySelector("[data-overlay-cancel]");
        if (cancel) cancel.click(); else closeOverlay(target.id);
      }
    });
  }

  var snackTimer = null;
  function snackbar(message, ms) {
    var bar = root.document.getElementById("snackbar");
    if (!bar) return;
    bar.textContent = message;
    bar.hidden = false;
    if (snackTimer) clearTimeout(snackTimer);
    snackTimer = setTimeout(function () { bar.hidden = true; }, ms || 6000);
  }

  var api = {
    ICONS: ICONS,
    NOTICE_ICONS: NOTICE_ICONS,
    PROBLEM_LOOK: PROBLEM_LOOK,
    noticeIcon: noticeIcon,
    problemLook: problemLook,
    initials: initials,
    formatWhen: formatWhen,
    clock: clock,
    dayDate: dayDate,
    icon: icon,
    setIcon: setIcon,
    setBubble: setBubble,
    bubble: bubble,
    text: text,
    clear: clear,
    listItem: listItem,
    fillList: fillList,
    renderNoticeRows: renderNoticeRows,
    setBrandBar: setBrandBar,
    renderWelcome: renderWelcome,
    openOverlay: openOverlay,
    closeOverlay: closeOverlay,
    closeAllOverlays: closeAllOverlays,
    wireOverlays: wireOverlays,
    hydrateIcons: hydrateIcons,
    snackbar: snackbar,
  };

  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  } else {
    root.AlvoraaUi = api;
    if (root.document && root.document.getElementById("app")) {
      hydrateIcons();
      wireOverlays();
    }
  }
})(typeof window !== "undefined" ? window : this);
