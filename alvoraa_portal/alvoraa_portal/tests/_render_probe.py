"""Does the joining page actually render? Nothing else asks."""
import frappe
from frappe.utils.jinja import get_jenv

for path, ctx in (
	("alvoraa_portal/www/joining.html",
	 {"tenant_name": "PP Jewellers", "brand_colour": "#1f6feb",
	  "lang": "en", "one_page": False}),
	("alvoraa_portal/www/joining.html",
	 {"tenant_name": "PP Jewellers", "brand_colour": "#1f6feb",
	  "lang": "en", "one_page": True}),
):
	body = open(frappe.get_app_path("alvoraa_portal", "www", "joining.html"),
	            encoding="utf-8").read()
	out = get_jenv().from_string(body).render(**ctx)
	print(path, "one_page=%s" % ctx["one_page"], "->", len(out), "chars")
	for must in ("Before your first day", "joiner_public.", "Needed"):
		print("   contains %r:" % must, must in out)
	print("   JOIN-ONEPAGE drawn:", "JOIN-ONEPAGE" in out)
	print("   no raw jinja left:", "{{" not in out and "{%" not in out)
	# The notice must come before the first input IN THE DOM.
	notice = out.find('id="j0-notice"')
	first_input = min([i for i in (out.find("<input"), out.find("<textarea"))
	                   if i > 0] or [10 ** 9])
	print("   notice before the first input:", 0 < notice < first_input,
	      "(notice at %d, first input at %d)" % (notice, first_input))
	print("   no localStorage anywhere:", "localStorage" not in out)
	print("   no token parameter anywhere:", "web_form_request_key" not in out)
