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

	try:
		size = max(48, min(1024, cint(size) or 192))
	except Exception:
		size = 192

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
