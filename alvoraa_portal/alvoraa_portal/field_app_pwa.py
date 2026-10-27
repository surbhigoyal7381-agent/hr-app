"""What makes the web check-in page an installed app, not just a page.

Moved out of `field_checkin.py` unchanged. The three endpoints keep being
called at `alvoraa_portal.field_checkin.app_icon`, `...manifest` and
`...service_worker` - the same function objects are imported back into
`field_checkin`, so the browser's URLs do not move.

These three are served from endpoints rather than as files because Frappe
refuses to serve .js and .json out of www/, and because all three have to
carry the TENANT's name and colour - a static file could only ever be one
customer's. The icon is drawn per request for the same reason.
"""

import os
import re
from functools import lru_cache

import frappe
from frappe.utils import cint


def _brand():
	"""Tenant name and a contrast-safe brand colour, for the icon and manifest."""
	from alvoraa_portal.tenant_context import DEFAULTS, get_branding
	b = get_branding()
	colour = b.get("primary_color") or DEFAULTS["primary_color"]
	if not (isinstance(colour, str) and colour.startswith("#") and len(colour) in (4, 7)):
		colour = DEFAULTS["primary_color"]
	if len(colour) == 4:
		colour = "#" + "".join(c * 2 for c in colour[1:])
	return (b.get("tenant_name") or "Attendance"), colour


_HEX_COLOUR = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")


def brand_colour():
	"""The tenant's brand colour for the phone app (ALV-133, E-1): always a
	"#rrggbb" string. The app builds its whole palette from it, so anything in
	site config that is not a plain hex colour gives the default instead of
	reaching the phone. Read from `frappe.conf`, which is already in memory -
	no query."""
	from alvoraa_portal.tenant_context import DEFAULTS, get_branding
	colour = get_branding().get("primary_color")
	if not (isinstance(colour, str) and _HEX_COLOUR.match(colour.strip())):
		colour = DEFAULTS["primary_color"]
	colour = colour.strip().lower()
	if len(colour) == 4:
		colour = "#" + "".join(c * 2 for c in colour[1:])
	return colour


def _darker(hex_colour, factor=0.72):
	"""A deeper shade for the icon ground, dark enough for a white tick on it.

	A fixed multiplier is not enough on its own. A tenant whose brand is white or
	a pale yellow would get 0.72 of a very light colour, which is still light,
	and the white tick would vanish. So it darkens further until white actually
	passes WCAG AA against it - the same rule brand_color.html applies on screen,
	applied here because this icon is drawn on the server.
	"""
	h = hex_colour.lstrip("#")
	rgb = [max(0, min(255, int(int(h[i:i + 2], 16) * factor))) for i in (0, 2, 4)]

	def contrast_with_white(c):
		def ch(v):
			v /= 255
			return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
		lum = 0.2126 * ch(c[0]) + 0.7152 * ch(c[1]) + 0.0722 * ch(c[2])
		return 1.05 / (lum + 0.05)

	for _ in range(30):
		if contrast_with_white(rgb) >= 4.5:
			break
		rgb = [max(0, int(v * 0.88)) for v in rgb]

	return tuple(rgb)


@frappe.whitelist(allow_guest=True, methods=["GET"])
def app_icon(size=192):
	"""The home-screen icon, drawn in the tenant's own colour.

	A PNG rather than an SVG: Chrome is fussy about which formats it will accept
	for installation, and a PNG at 192 and 512 is the combination it documents.
	"""
	from io import BytesIO

	from PIL import Image, ImageDraw

	# `cint` swallows its own errors and returns 0, so `or 192` is the fallback.
	size = max(48, min(1024, cint(size) or 192))

	_, colour = _brand()
	ground = _darker(colour)

	img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
	d = ImageDraw.Draw(img)
	r = int(size * 0.19)
	d.rounded_rectangle([0, 0, size - 1, size - 1], radius=r, fill=ground + (255,))
	# A tick, drawn rather than shipped, so it scales to any requested size.
	w = max(2, int(size * 0.085))
	d.line([(size * 0.30, size * 0.52), (size * 0.44, size * 0.66),
	        (size * 0.71, size * 0.36)],
	       fill=(255, 255, 255, 255), width=w, joint="curve")

	buf = BytesIO()
	img.save(buf, format="PNG", optimize=True)

	frappe.local.response.filename = f"icon-{size}.png"
	frappe.local.response.filecontent = buf.getvalue()
	frappe.local.response.type = "download"
	frappe.local.response.display_content_as = "inline"


@frappe.whitelist(allow_guest=True, methods=["GET"])
def manifest():
	"""The web app manifest. Without a real one the page cannot install.

	It was previously built in the browser as a blob: URL, which looks right in
	the code and never installs: Chrome will not accept a blob manifest.
	"""
	name, colour = _brand()
	deep = "#%02x%02x%02x" % _darker(colour)
	base = "/api/method/alvoraa_portal.field_checkin.app_icon?size="

	frappe.local.response.type = "json"
	frappe.local.response.http_status_code = 200
	return {
		"name": name,
		"short_name": name[:12],
		"description": "Mark your attendance with a photo and your location.",
		"start_url": "/checkin",
		"scope": "/checkin",
		"display": "standalone",
		"orientation": "portrait",
		"background_color": "#F8F6F3",
		"theme_color": deep,
		"icons": [
			{"src": base + "192", "sizes": "192x192", "type": "image/png", "purpose": "any"},
			{"src": base + "512", "sizes": "512x512", "type": "image/png", "purpose": "any"},
			{"src": base + "512", "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
		],
	}


# Deliberately tiny. Its only job today is to exist with a fetch handler, which
# is what lets Chrome offer to install the page. The offline queue (brief P11)
# would live here later; it is NOT implemented, and this must not pretend to
# cache anything, because a stale cached app is worse than no app.
_SERVICE_WORKER = """
self.addEventListener('install', function (e) { self.skipWaiting(); });
self.addEventListener('activate', function (e) { e.waitUntil(self.clients.claim()); });
self.addEventListener('fetch', function (e) { return; });
"""


@frappe.whitelist(allow_guest=True, methods=["GET"])
def service_worker():
	"""Served from here so it can carry Service-Worker-Allowed.

	A worker's scope cannot be wider than the folder it is served from unless
	that header says so - and this one is served from /api/method/, which would
	otherwise be able to control nothing that matters.
	"""
	# A werkzeug Response, returned directly, because Frappe's own response types
	# cannot express what a service worker needs. `binary` hardcodes
	# application/octet-stream, and a browser REFUSES to register a worker that
	# is not served as JavaScript - so the first version of this registered
	# nothing at all and failed silently. Frappe's handler passes a Response
	# through untouched, which is the supported way to set both headers.
	from werkzeug.wrappers import Response

	return Response(
		_SERVICE_WORKER,
		mimetype="application/javascript",
		headers={
			# Without this the worker's scope could only be /api/method/, which
			# controls nothing worth controlling.
			"Service-Worker-Allowed": "/",
			# Never cache the worker itself. nginx serves /assets/ as immutable
			# for 30 days, and a worker frozen for a month is a bug that cannot
			# be shipped a fix.
			"Cache-Control": "no-cache, no-store, must-revalidate",
		},
	)


# ---------------------------------------------------------------------------
# Slice 062: the same three things for the employee portal at /hrms-employee.
#
# Separate endpoints rather than parameters on the three above, because every
# value differs: the name, the start_url, the scope and the header. Sharing
# them would mean a branch in each of the three, which is more code than this.
# The check-in app's endpoints are untouched, so a phone that already has it
# installed keeps working.
# ---------------------------------------------------------------------------

# Decision 4 (27 Oct): the home-screen icon is ALWAYS the Alvora mark, drawn on
# the tenant's own brand colour. It does NOT follow `brand_mark_url`, so a
# tenant with its own logo still gets the Alvora mark here. That is deliberate:
# the icon says which product this is, the colour says whose instance it is.
# Do not "fix" this to read the tenant logo.
PORTAL_APP_NAME = "Alvora"

_PORTAL_SCOPE = "/hrms-employee"

# Built from __file__ and not from frappe.get_app_source_path(), which scrubs
# its arguments and so turns "alvoraa-logo-master.jpg" into
# "alvoraa_logo_master.jpg" - a file that does not exist. The same trap is
# written up in tests/test_brand_logo_025.py.
_MARK_SOURCE = os.path.join(
	os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
	"brand", "alvoraa-logo-master.jpg",
)


@lru_cache(maxsize=8)
def _mark_mask(box):
	"""The Alvora mark as a silhouette, centred in a `box` by `box` square.

	An "L" image, used as a paste mask, so the caller picks the colour. The mark
	is painted white: `_darker()` already guarantees white passes WCAG AA on the
	tenant's ground whatever colour they chose, and the mark's own purple and
	teal would have no such guarantee against a colour it was never drawn for.

	The master artwork is the full lockup - the monogram above the word ALVORA.
	Only the monogram is kept, because a wordmark at 48 points on a home screen
	is an unreadable smudge. The two parts are separated by a band of blank
	rows, so the cut is made at the first blank row after the ink starts. That
	is the same rule `scripts/make_brand_assets.py` uses, for the same reason:
	new artwork with different margins still works, with nothing to re-measure.

	Cached because the answer depends only on the box size and on a file that
	changes with a release, which restarts the process.
	"""
	from PIL import Image, ImageOps

	src = Image.open(_MARK_SOURCE).convert("L")
	# Ink becomes white, paper becomes black. The threshold clears the grey halo
	# a JPEG leaves around every edge - the same 40-of-255 reasoning as
	# make_brand_assets.py's EDGE, which is below any real brand colour and above
	# JPEG ringing.
	ink = ImageOps.invert(src).point(lambda v: 255 if v > 40 else 0)

	# One pixel per row, averaged in Pillow's C code rather than by a Python loop
	# over 2.5 million pixels. A row is inked if its average is above zero.
	rows = ink.resize((1, ink.height), Image.BOX).load()
	cut, seen_ink = ink.height, False
	for y in range(ink.height):
		if rows[0, y]:
			seen_ink = True
		elif seen_ink:
			cut = y
			break

	mark = ink.crop((0, 0, ink.width, cut))
	mark = mark.crop(mark.getbbox())

	# Android promises not to crop inside a circle of 80 % of a maskable icon's
	# width. A shape fits inside that circle when its own DIAGONAL fits, so the
	# mark is scaled by its diagonal and not by its width. It is about two and a
	# half times wider than it is tall, so scaling by width would have left it a
	# third of the size it can safely be.
	diagonal = (mark.width ** 2 + mark.height ** 2) ** 0.5
	scale = box * 0.80 / diagonal
	mark = mark.resize((max(1, round(mark.width * scale)), max(1, round(mark.height * scale))),
	                   Image.LANCZOS)

	out = Image.new("L", (box, box), 0)
	out.paste(mark, ((box - mark.width) // 2, (box - mark.height) // 2))
	return out


@frappe.whitelist(allow_guest=True, methods=["GET"])
def portal_app_icon(size=192):
	"""The portal's home-screen icon: the Alvora mark on the tenant's colour.

	One drawing serves both `any` and `maskable`. That means a square filled
	edge to edge - no rounded corners, no transparency - because Android crops a
	maskable icon to whatever shape the launcher uses, and a transparent corner
	would show as a notch. `_mark_mask` keeps the mark inside the circle Android
	promises not to crop.
	"""
	# No try/except around the clamp: `cint` swallows its own errors and returns
	# 0 for anything it cannot read, so `or 192` is already the whole fallback.
	size = max(48, min(1024, cint(size) or 192))

	frappe.local.response.filename = f"alvora-{size}.png"
	frappe.local.response.filecontent = _portal_icon_png(size, _darker(brand_colour()))
	frappe.local.response.type = "download"
	frappe.local.response.display_content_as = "inline"


@lru_cache(maxsize=16)
def _portal_icon_png(size, ground):
	"""The finished PNG bytes. Cached, because nothing here varies per request.

	The drawing depends only on the box size and the tenant's ground colour, and
	the encode is the expensive half: `optimize=True` tries several filter and
	zlib strategies, which is worth paying once and not on every fetch. The colour
	is part of the key, so this stays correct even if one process ever serves more
	than one site.
	"""
	from io import BytesIO

	from PIL import Image

	img = Image.new("RGB", (size, size), ground)
	img.paste(Image.new("RGB", (size, size), (255, 255, 255)), (0, 0), _mark_mask(size))

	buf = BytesIO()
	img.save(buf, format="PNG", optimize=True)
	return buf.getvalue()


@frappe.whitelist(allow_guest=True, methods=["GET"])
def portal_manifest():
	"""The portal's web app manifest. Without one, no phone offers to install.

	Decision 5 (27 Oct): the name under the icon is always "Alvora", never the
	tenant's. So the only per-tenant value here is the colour.

	Returned as a werkzeug Response and not with `frappe.local.response.type =
	"json"`, which is what the check-in manifest above does. That route wraps
	the value Frappe's own way - `{"type": "json", "message": {...}}` - and a
	browser reading a manifest does not unwrap anything. It would see an object
	with no name, no start_url and no icons, and quietly decline to offer the
	install. Measured over HTTP, not reasoned about: the wrapper is really there.
	"""
	import json

	deep = "#%02x%02x%02x" % _darker(brand_colour())
	base = "/api/method/alvoraa_portal.field_app_pwa.portal_app_icon?size="

	payload = {
		"name": PORTAL_APP_NAME,
		"short_name": PORTAL_APP_NAME,
		"description": "Your payslips, leave, attendance and team, on your phone.",
		"start_url": _PORTAL_SCOPE,
		"scope": _PORTAL_SCOPE,
		"display": "standalone",
		# No "orientation". The check-in app pins portrait because it is a camera
		# page held upright. The portal is a responsive site people also use on a
		# tablet, and pinning it would be a behaviour change nobody asked for.
		"background_color": "#F8F6F3",
		"theme_color": deep,
		"icons": [
			{"src": base + "192", "sizes": "192x192", "type": "image/png", "purpose": "any"},
			{"src": base + "512", "sizes": "512x512", "type": "image/png", "purpose": "any"},
			{"src": base + "512", "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
		],
	}

	from werkzeug.wrappers import Response

	# Chrome re-fetches the manifest on in-scope navigations to decide whether the
	# page is installable. Nothing in it changes between two opens, so a day of
	# browser cache removes one guest request per open per phone. A day stale is
	# harmless: the only per-tenant value is the colour.
	return Response(
		json.dumps(payload),
		mimetype="application/manifest+json",
		headers={"Cache-Control": "public, max-age=86400"},
	)


# Decision 2 (25 Oct): THIS WORKER CACHES NOTHING, and must not start to.
# The portal page carries the signed-in user and the CSRF token, so it must
# never enter a shared store; /assets/ is already kept 30 days by the browser;
# caching would save about 32 KB an open. A caching worker is a bug you cannot
# deploy a fix for - the stale worker serves the stale fix.
#
# Before anyone adds caching here, two things must exist first: the build
# version inside this worker's body, so a release replaces it, and a kill
# switch - a worker that unregisters itself behind a site-config flag.
_PORTAL_SERVICE_WORKER = """
self.addEventListener('install', function (e) { self.skipWaiting(); });
self.addEventListener('activate', function (e) { e.waitUntil(self.clients.claim()); });
self.addEventListener('fetch', function (e) { return; });
"""


@frappe.whitelist(allow_guest=True, methods=["GET"])
def portal_service_worker():
	"""Served from here so it can carry Service-Worker-Allowed.

	The header says `/hrms-employee`, NOT `/`. The check-in worker is allowed
	`/` only because it does nothing at all; copying that here would hand this
	worker /checkin, the login page and the whole desk.
	"""
	from werkzeug.wrappers import Response

	return Response(
		_PORTAL_SERVICE_WORKER,
		mimetype="application/javascript",
		headers={
			"Service-Worker-Allowed": _PORTAL_SCOPE,
			"Cache-Control": "no-cache, no-store, must-revalidate",
		},
	)
