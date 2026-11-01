"""Frappe's `File` must not DECODE the file it read. Three lines, one fault.

Slice 078. Surbhi's decision, 31 October 2026: fix it in our own image and
report it upstream, so we can drop this patch rather than carry it for ever.

    python scripts/patch_frappe_binary_file_content.py <bench path>
    python scripts/patch_frappe_binary_file_content.py --check <bench path>

## The fault

`File.get_content()` with no argument tries to DECODE what it read, looping
over `FILE_ENCODING_OPTIONS` until one of them does not raise
(`frappe/core/doctype/file/file.py`, in `get_content`). For a JPEG, a PNG or a
PDF one of those encodings succeeds **lossily** and returns a `str` with bytes
changed or dropped - measured: a stored JPEG came back with its first four
bytes altered, so Pillow could not identify it at all.

Three callers in that same file then hand the result somewhere that needs
bytes:

| line | caller | what breaks |
|---|---|---|
| `before_insert` | `self.save_file(content=self.get_content())` | **the one that bites.** `save_file` puts that `str` in `_content` and `strip_exif_data` raises `TypeError: a bytes-like object is required, not 'str'` |
| `save_file` | `self.flags.original_content = self.get_content()` | a rollback writes `original_content` back to disk, choosing `"w+"` for a str - so it would write a CORRUPTED image over a good one |
| `optimize_file` | `original_content = self.get_content()` | `optimize_image(content=...)` is handed a `str` |

## Why it matters to us

ERPNext's `Employee.update_user()` inserts a `File` carrying only a `file_url`
whenever `image` changes, or whenever the linked User's `user_image` is empty.
That is the `before_insert` path above. So **HR adding an employee photograph
in Desk raises** - and because every failed attempt leaves `user_image` empty,
it then raises on **every later save of that employee**. The state is sticky,
and slice 078 is the first feature that puts photographs on employees at all.

## The fix

`encodings=[]` at all three. The decode loop's body then never runs and the raw
bytes come back untouched. It is strictly better at each site.

## Why a guarded replacement rather than a .patch file

A unified diff carries context lines, and we raise `FRAPPE_TAG` deliberately
from time to time. A diff whose context has drifted fails with "patch does not
apply", which tells you nothing about whether the bug is still there. This
asserts on the **exact lines it changes**, says which one it could not find,
and is idempotent - so a cached CI bench that is already patched succeeds
rather than failing on a second run.

**If this fails the build, do not delete it.** Either a line moved (read
`file.py` and update `EDITS` here) or upstream has fixed it - and then delete
this script, its step in `deploy/Dockerfile`, its step in
`.github/workflows/ci.yml`, that file's cache key entry, and the environment
check in `test_my_photo_078.test_a_desk_save_for_an_employee_with_a_login`.
"""

import io
import os
import sys

REL = os.path.join("apps", "frappe", "frappe", "core", "doctype", "file", "file.py")
MARK = "ALVORAA PATCH 078"


def _note(why):
	return (f"\t# {MARK}: `encodings=[]`. Without it this DECODES the file it\n"
	        f"\t# read - lossily, for anything binary - and {why}\n"
	        f"\t# Reported upstream; delete this patch when the report lands.\n"
	        f"\t# scripts/patch_frappe_binary_file_content.py\n")


# (old line, replacement, what the comment says). Indentation is part of the
# match on purpose: it pins the line to its own block.
EDITS = (
	(
		"\t\t\tself.save_file(content=self.get_content())\n",
		"strip_exif_data below then raises TypeError on every jpeg. This is the\n"
		"\t# line ERPNext's Employee.update_user() hits, which is what made HR\n"
		"\t# adding a photograph in Desk fail permanently, per employee.",
		"\t\t\tself.save_file(content=self.get_content(encodings=[]))\n",
	),
	(
		"\t\t\tself.flags.original_content = self.get_content()\n",
		"a rollback would write a CORRUPTED image back over a good one: it\n"
		"\t# picks \"w+\" for a str and \"wb+\" for bytes.",
		"\t\t\tself.flags.original_content = self.get_content(encodings=[])\n",
	),
	(
		"\t\toriginal_content = self.get_content()\n",
		"optimize_image() is handed a str it cannot use.",
		"\t\toriginal_content = self.get_content(encodings=[])\n",
	),
)


def main(argv):
	check_only = "--check" in argv
	rest = [a for a in argv if not a.startswith("--")]
	bench = rest[0] if rest else "/home/frappe/frappe-bench"
	path = os.path.join(bench, REL)

	if not os.path.isfile(path):
		print(f"patch_frappe: {path} does not exist", file=sys.stderr)
		return 2

	text = io.open(path, encoding="utf-8").read()
	applied = text.count(MARK)

	if applied == len(EDITS):
		print(f"patch_frappe: already applied ({applied} of {len(EDITS)})")
		return 0
	if check_only:
		print(f"patch_frappe: NOT fully applied ({applied} of {len(EDITS)})",
		      file=sys.stderr)
		return 1
	if applied:
		print(f"patch_frappe: {applied} of {len(EDITS)} already there, which "
		      f"means a previous run stopped half way. Reinstall the app and "
		      f"run this again.", file=sys.stderr)
		return 1

	for old, why, new in EDITS:
		found = text.count(old)
		if found != 1:
			print(f"patch_frappe: expected exactly one occurrence of\n"
			      f"  {old.strip()}\n"
			      f"in {path}, found {found}.\n"
			      f"Frappe has changed that line. Read file.py and either update "
			      f"EDITS in this script, or - if upstream has fixed it - remove "
			      f"this patch and its build steps (see the module docstring).",
			      file=sys.stderr)
			return 1
		text = text.replace(old, _note(why) + new)

	io.open(path, "w", encoding="utf-8", newline="").write(text)
	print(f"patch_frappe: applied {len(EDITS)} edit(s) to {path}")
	return 0


if __name__ == "__main__":
	sys.exit(main(sys.argv[1:]))
