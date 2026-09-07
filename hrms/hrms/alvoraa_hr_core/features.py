"""Is an opt-in feature switched on for this site?

The Alvoraa features that live on stock doctypes (custom fields on Employee,
Appraisal Cycle, Appraisal) cannot be hidden by the module gate alone, so
their hooks ask the subscription registry before doing anything. On a bench
without the portal app the answer is yes: there is nothing to gate against.
"""


def feature_enabled(key):
	try:
		from alvoraa_portal.subscription import has_feature
	except ImportError:
		return True
	try:
		return bool(has_feature(key))
	except Exception:
		return True
