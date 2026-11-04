"""ALV-297: on iPhone the check-in page takes its photo through Apple's camera.

These read the page's source, so a bad merge that drops the iPhone path fails CI.
They do not prove it works: scripts/browser_check_checkin_iphone_297.js drives the
page in a browser and reads what it posts, and only a real iPhone can prove the
camera (docs/slices/alv-297-iphone-camera/iphone-test-sheet.md).
"""

import os
import re

from frappe.tests.utils import FrappeTestCase

PAGE = os.path.join(
	os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "www", "field-checkin.html"
)


class IphoneCameraPinCase(FrappeTestCase):
	def setUp(self):
		with open(PAGE, encoding="utf-8") as f:
			self.page = f.read()

	def _function(self, name: str) -> str:
		start = self.page.index("function %s(" % name)
		return self.page[start : self.page.index("\n}\n", start)]

	def test_297_iphone_and_ipad_are_picked_without_changing_what_registration_stores(self):
		self.assertIn(
			'var PICKER = !SAMPLE && (platform() === "iOS" || '
			"(/Macintosh/.test(navigator.userAgent) && navigator.maxTouchPoints > 1));",
			self.page,
		)
		self.assertNotIn("maxTouchPoints", self._function("platform"))

	def test_297_iphone_returns_before_the_live_camera_call(self):
		start = self._function("startCamera")
		self.assertLess(start.index("if (PICKER)"), start.index("getUserMedia"))

	def test_297_the_input_opens_the_front_camera_and_can_be_clicked(self):
		tag = re.search(r'<input type="file" id="i-photo"[^>]*>', self.page).group(0)
		self.assertIn('capture="user"', tag)
		self.assertIn('accept="image/*"', tag)
		self.assertIn('class="sronly"', tag)

	def test_297_the_tap_opens_the_camera_before_any_busy_screen(self):
		start = self.page.index('$("b-punch").addEventListener')
		handler = self.page[start : self.page.index("sendPunch();", start)]
		self.assertLess(handler.index("openPicker(type)"), handler.index("busy(true"))

	def test_297_a_late_photo_cannot_make_a_second_punch(self):
		self.assertIn("if (!file || !waitingForPhoto) return;", self.page)
		start = self.page.index('$("b-nophoto").addEventListener')
		self.assertIn("waitingForPhoto = false;", self.page[start : start + 120])

	def test_297_the_shrink_checks_its_own_output_and_never_uses_create_image_bitmap(self):
		shrink = self._function("shrink")
		self.assertIn("img.naturalWidth > 0", shrink)
		self.assertIn('out.indexOf("data:image/jpeg") === 0', shrink)
		self.assertNotIn("createImageBitmap(", self.page)

	def test_297_an_old_photo_is_retaken_on_iphone_after_too_far_only(self):
		self.assertIn("pending && PICKER && pending.tooFar && pending.photo", self.page)
		self.assertIn('if (kind === "OUTSIDE" && pending) pending.tooFar = true;', self.page)
		self.assertNotIn("captured_at", self._function("sendPunch"))

	def test_297_the_result_line_is_true_and_has_hindi(self):
		self.assertNotIn("The camera was not on", self.page)
		self.assertIn('"res.photo.why":', self.page)
		self.assertIn('"res.photo.why.failed":', self.page)
		self.assertIn('"busy.ready":', self.page)
		self.assertNotIn("2 MB the server accepts", self.page)

	def test_297_a_hidden_button_is_really_hidden(self):
		""".btn sets display:flex, which beats hidden: the error screen showed a dead button."""
		self.assertIn(".btn[hidden]{display:none}", self.page)

	def test_297_a_cancel_does_not_stop_the_page_asking_for_status(self):
		"""iPhone gives no signal for a cancel. Left overnight, the page must still learn
		the day changed, or the morning punch goes as OUT."""
		start = self.page.index("else if (PICKER && waitingForPhoto) {")
		branch = self.page[start : start + 300]
		self.assertIn('call("field_status"', branch)
		self.assertIn("renderHome(s)", branch)
		self.assertIn('pickerType = $("b-punch").getAttribute("data-type")', branch)
