/*
 * The check-in photo: small enough to send on a weak connection, big enough for
 * a supervisor to recognise a face. Slice 013: OPS-21, OPS-63, AC-201.
 *
 * Rules (AC-201): long edge at most 640, short edge at most 480, JPEG quality
 * 0.6, saved again at 0.45 if the first try is over 120 KB, and never over
 * 150 KB. The server refuses anything over 400 KB.
 *
 * The photo lives in memory only. It is never written as a file, so the app
 * needs no storage or media permission (PRIV-7).
 *
 * The size arithmetic is here as plain functions so it can be tested in Node,
 * where there is no canvas.
 */
(function (root) {
  "use strict";

  var MAX_LONG_EDGE = 640;
  var MAX_SHORT_EDGE = 480;
  var FIRST_QUALITY = 0.6;
  var SECOND_QUALITY = 0.45;
  var SECOND_TRY_OVER_BYTES = 120 * 1024;
  var NEVER_OVER_BYTES = 150 * 1024;

  // What the picture is scaled down to, keeping its shape.
  function fitSize(width, height) {
    if (!(width > 0) || !(height > 0)) return null;
    var longEdge = Math.max(width, height);
    var shortEdge = Math.min(width, height);
    var scale = Math.min(1, MAX_LONG_EDGE / longEdge, MAX_SHORT_EDGE / shortEdge);
    return {
      width: Math.max(1, Math.round(width * scale)),
      height: Math.max(1, Math.round(height * scale)),
      scale: scale
    };
  }

  function needsSecondTry(bytes) {
    return bytes > SECOND_TRY_OVER_BYTES;
  }

  function isTooBig(bytes) {
    return bytes > NEVER_OVER_BYTES;
  }

  // Bytes behind a data: URL, without copying the picture again.
  function dataUrlBytes(dataUrl) {
    if (typeof dataUrl !== "string") return 0;
    var comma = dataUrl.indexOf(",");
    if (comma === -1) return 0;
    var body = dataUrl.slice(comma + 1);
    var padding = body.endsWith("==") ? 2 : body.endsWith("=") ? 1 : 0;
    return Math.floor(body.length * 3 / 4) - padding;
  }

  /*
   * Draw a video frame or an image into a canvas at the allowed size and return
   * { dataUrl, bytes, width, height, quality, tooBig }. Browser only.
   */
  function shrinkToJpeg(source, width, height, makeCanvas) {
    var size = fitSize(width, height);
    if (!size) return null;
    var canvas = (makeCanvas || function () { return document.createElement("canvas"); })();
    canvas.width = size.width;
    canvas.height = size.height;
    canvas.getContext("2d").drawImage(source, 0, 0, size.width, size.height);

    var quality = FIRST_QUALITY;
    var dataUrl = canvas.toDataURL("image/jpeg", quality);
    var bytes = dataUrlBytes(dataUrl);
    if (needsSecondTry(bytes)) {
      quality = SECOND_QUALITY;
      dataUrl = canvas.toDataURL("image/jpeg", quality);
      bytes = dataUrlBytes(dataUrl);
    }
    return {
      dataUrl: dataUrl,
      bytes: bytes,
      width: size.width,
      height: size.height,
      quality: quality,
      tooBig: isTooBig(bytes)
    };
  }

  var api = {
    fitSize: fitSize,
    needsSecondTry: needsSecondTry,
    isTooBig: isTooBig,
    dataUrlBytes: dataUrlBytes,
    shrinkToJpeg: shrinkToJpeg,
    MAX_LONG_EDGE: MAX_LONG_EDGE,
    MAX_SHORT_EDGE: MAX_SHORT_EDGE,
    NEVER_OVER_BYTES: NEVER_OVER_BYTES
  };

  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  } else {
    root.AlvoraaPhoto = api;
  }
})(typeof window !== "undefined" ? window : this);
