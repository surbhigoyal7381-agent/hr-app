"""ALV-480: every DocType we built is reachable from a Desk tile.

Surbhi, 26 Nov 2026: "all the custom modules created by us ... should directly be
visible on desk". Frappe v16 Desk shows an app only through a Desktop Icon that opens
a Workspace Sidebar; neither app had one. Each sidebar link is shown only to people
who can read it, so listing a DocType here grants nobody anything.

This reads the shipped files only, so it needs no database and passes on an empty
site (ALV-470). A new DocType that is not added to a sidebar fails it.
"""

import glob
import json
import os
import unittest

APPS = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SIDEBARS = {"alvoraa_portal": "alvora.json", "alvoraa_goals": "goals_&_performance.json"}


def _load(path):
	with open(path) as f:
		return json.load(f)


def _our_doctypes():
	"""Name -> is it a child table, for every DocType in both apps."""
	out = {}
	for app in SIDEBARS:
		for path in glob.glob(os.path.join(APPS, app, app, "*", "doctype", "*", "*.json")):
			d = _load(path)
			if d.get("doctype") == "DocType":
				out[d["name"]] = bool(d.get("istable"))
	return out


def _sidebar(app):
	return _load(os.path.join(APPS, app, app, "workspace_sidebar", SIDEBARS[app]))


def _icon(app):
	return _load(os.path.join(APPS, app, app, "desktop_icon", SIDEBARS[app]))


class DeskTiles(unittest.TestCase):
	def test_alv480_each_app_has_a_tile_that_opens_its_sidebar(self):
		for app in SIDEBARS:
			icon, sidebar = _icon(app), _sidebar(app)
			self.assertEqual(icon["app"], app)
			self.assertEqual(sidebar["app"], app)
			self.assertEqual(icon["link_type"], "Workspace Sidebar")
			self.assertEqual(icon["link_to"], sidebar["title"], f"{app}: the tile opens no sidebar")
			self.assertEqual(icon["roles"], [], "a role list on the tile would hide it from HR; "
			                                    "the links' own read permission already decides")

	def test_alv480_every_doctype_we_built_is_on_desk(self):
		linked = {i.get("link_to") for app in SIDEBARS for i in _sidebar(app)["items"]
		          if i.get("type") == "Link" and i.get("link_type") == "DocType"}
		missing = sorted(n for n, child in _our_doctypes().items() if not child and n not in linked)
		self.assertEqual(missing, [], "add these to a sidebar in */workspace_sidebar/ (ALV-480)")

	def test_alv480_no_link_points_at_a_doctype_that_does_not_exist(self):
		ours = _our_doctypes()
		for app in SIDEBARS:
			for i in _sidebar(app)["items"]:
				if i.get("type") == "Link" and i.get("link_type") == "DocType":
					self.assertIn(i["link_to"], ours, f"{app}: {i['label']}")
					self.assertFalse(ours[i["link_to"]], f"{i['link_to']} is a child table; it has no list to open")
