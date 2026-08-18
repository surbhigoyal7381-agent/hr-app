"""Render the KPI Automation backlog to a review document and a YouTrack import CSV.

Usage:  python backlog/render_stories.py
Outputs: backlog/KPI_AUTOMATION_BACKLOG.md
         backlog/kpi_automation_youtrack.csv
"""

import csv
import io
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "kpi_automation_stories.json")
MD_OUT = os.path.join(HERE, "KPI_AUTOMATION_BACKLOG.md")
CSV_OUT = os.path.join(HERE, "kpi_automation_youtrack.csv")


def load():
    with io.open(DATA, encoding="utf-8") as fh:
        return json.load(fh)


def story_description(story, epic, feature):
    """YouTrack-friendly markdown description."""
    lines = [
        "**As a** %s" % story["persona"],
        "**I want to** %s" % story["want"],
        "**So that** %s" % story["so_that"],
        "",
        "### Acceptance criteria",
    ]
    lines += ["- %s" % a for a in story["ac"]]
    if story.get("notes"):
        lines += ["", "### Notes", story["notes"]]
    lines += [
        "",
        "---",
        "Epic: %s · Phase %s" % (epic["name"], epic["phase"]),
        "Feature: %s" % feature,
        "Source: KPI_AUTOMATION_STRATEGY.md",
    ]
    return "\n".join(lines)


def render_markdown(data):
    out = [
        "# %s — Product Backlog" % data["feature"],
        "",
        "Derived from `%s`. Open decisions resolved as recommended:" % data["source_document"],
        "",
    ]
    for key in sorted(data["decisions_applied"]):
        out.append("- **%s** — %s" % (key, data["decisions_applied"][key]))

    total_points = 0
    counts = []
    for epic in data["epics"]:
        pts = sum(s["points"] for s in epic["stories"])
        total_points += pts
        counts.append((epic, pts))

    out += ["", "## Summary", "", "| Epic | Phase | Stories | Points | Goal |", "|---|---|---|---|---|"]
    for epic, pts in counts:
        out.append("| %s · %s | %s | %d | %d | %s |" % (
            epic["id"], epic["name"], epic["phase"], len(epic["stories"]), pts, epic["goal"]))
    out.append("| **Total** | | **%d** | **%d** | |" % (
        sum(len(e["stories"]) for e in data["epics"]), total_points))

    for epic in data["epics"]:
        out += [
            "",
            "---",
            "",
            "## %s · %s" % (epic["id"], epic["name"]),
            "",
            "**Phase %s** — %s" % (epic["phase"], epic["goal"]),
        ]
        for s in epic["stories"]:
            out += [
                "",
                "### %s — %s" % (s["id"], s["summary"]),
                "",
                "`%s` · %d points" % (s["priority"], s["points"]),
                "",
                "**As a** %s **I want to** %s **so that** %s" % (s["persona"], s["want"], s["so_that"]),
                "",
                "**Acceptance criteria**",
                "",
            ]
            out += ["- %s" % a for a in s["ac"]]
            if s.get("notes"):
                out += ["", "> %s" % s["notes"]]

    with io.open(MD_OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(out) + "\n")
    return total_points


def render_csv(data):
    rows = []
    for epic in data["epics"]:
        for s in epic["stories"]:
            rows.append({
                "Summary": s["summary"],
                "Description": story_description(s, epic, data["feature"]),
                "Type": "User Story",
                "Priority": s["priority"],
                "State": "Open",
                "Subsystem": epic["name"],
                "Epic": "%s %s" % (epic["id"], epic["name"]),
                "Phase": "Phase %s" % epic["phase"],
                "Estimation": s["points"],
                "Tag": "kpi-automation",
                "ExternalId": s["id"],
            })

    with io.open(CSV_OUT, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()), quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


if __name__ == "__main__":
    data = load()
    points = render_markdown(data)
    n = render_csv(data)
    print("epics:  %d" % len(data["epics"]))
    print("stories: %d" % n)
    print("points:  %d" % points)
    print("wrote:  %s" % MD_OUT)
    print("wrote:  %s" % CSV_OUT)
