import frappe


def prefill_agenda(doc, method=None):
    """Prefill standard agenda when a new check-in is created without items."""
    if doc.agenda_items:
        return
    standard_items = [
        "Progress on business goals",
        "Blockers and support needed",
        "Development and learning",
        "Well-being and engagement",
    ]
    for item in standard_items:
        doc.append("agenda_items", {"agenda_item": item, "status": "Open"})
    doc.save(ignore_permissions=True)
