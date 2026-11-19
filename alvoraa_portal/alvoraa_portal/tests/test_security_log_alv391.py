"""ALV-391: a security line must actually reach the file, not just be written.

**Every one of these lines was thrown away until 19 November 2026.** Frappe fixes
a logger's level when it first creates it, from `frappe.log_level or
default_log_level`, and that default is ERROR unless `DEV_SERVER` is set - which
it is not in any of our images. All seven call sites use `.warning` or `.info`.
Measured on the live dev site that day: `logs/security.log` was 0 bytes.

**The existing tests for these controls could never have caught it.** They patch
`log_refusal` and assert the CALL. A call that goes nowhere passes them. So the
tests here assert the FILE, which is the only thing that would have failed.
"""

import logging
import os

import frappe
from frappe.tests.utils import FrappeTestCase

from hrms.alvoraa_hr_core.access import log_refusal, security_logger


def _log_path():
	"""Where the handler is actually writing, asked of the handler itself.

	Not built from a guessed path: `create_handler` joins `..`/`logs` relative to
	the sites directory, and a test that guessed wrong would pass by reading a
	file nobody writes.
	"""
	for h in security_logger().handlers:
		name = getattr(h, "baseFilename", None)
		if name:
			return name
	return None


class TestASecurityLineReachesTheFile(FrappeTestCase):
	def test_the_logger_is_loud_enough_to_write(self):
		"""The whole bug in one assertion: at ERROR, warning and info vanish."""
		logger = security_logger()
		self.assertTrue(logger.isEnabledFor(logging.WARNING),
		                "a refusal is written at warning; the logger must accept it")
		self.assertTrue(logger.isEnabledFor(logging.INFO),
		                "three call sites write at info; the logger must accept those too")

	def test_a_refusal_lands_in_the_file(self):
		"""Not 'log_refusal was called' - that is what the old tests asserted and
		why this went unnoticed for months. This reads the bytes back."""
		path = _log_path()
		self.assertIsNotNone(path, "the security logger has no file handler at all")

		before = os.path.getsize(path) if os.path.exists(path) else 0
		marker = "alv391-probe-" + frappe.generate_hash(length=10)
		log_refusal(rule=marker, endpoint="test_security_log_alv391", doctype="Employee")
		for h in security_logger().handlers:
			h.flush()

		self.assertTrue(os.path.exists(path), "no security log file was created")
		self.assertGreater(os.path.getsize(path), before,
		                   "the refusal wrote nothing: the file did not grow")
		with open(path, encoding="utf-8", errors="replace") as fh:
			self.assertIn(marker, fh.read(),
			              "the file grew but this refusal is not in it")

	def test_the_line_says_who_and_what(self):
		"""A line nobody can read back is not a record."""
		path = _log_path()
		marker = "alv391-shape-" + frappe.generate_hash(length=10)
		log_refusal(rule=marker, endpoint="an_endpoint", doctype="Employee", name="HR-EMP-00001")
		for h in security_logger().handlers:
			h.flush()
		with open(path, encoding="utf-8", errors="replace") as fh:
			line = [l for l in fh.read().splitlines() if marker in l][-1]
		for wanted in ("refused", "an_endpoint", "Employee", "HR-EMP-00001",
		               frappe.session.user):
			self.assertIn(wanted, line, f"the refusal line does not say {wanted}")

	def test_logging_never_stops_the_refusal(self):
		"""`log_refusal` swallows its own errors on purpose. Prove it still does -
		a refusal must happen even when the record of it cannot be written."""
		broken = object()
		real = security_logger().handlers
		try:
			security_logger().handlers = [broken]      # any write will raise
			log_refusal(rule="alv391-broken", endpoint="e")   # must not raise
		finally:
			security_logger().handlers = real
