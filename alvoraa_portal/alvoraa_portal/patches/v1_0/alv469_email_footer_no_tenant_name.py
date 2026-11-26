"""ALV-469: the email footer is only "Powered by AllAboutHR".

Same work as the alvora_email_brand patch, which has already run on every
existing site, so it needs a patch of its own. email_brand.apply() rewrites a
footer this module wrote (last line is ours) and leaves a hand-written one.
"""

from alvoraa_portal.patches.v1_0 import alvora_email_brand


def execute():
	alvora_email_brand.execute()
