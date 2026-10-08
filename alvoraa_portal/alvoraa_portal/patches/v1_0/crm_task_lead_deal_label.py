"""Slice 057, 4 Oct: the "Lead / Deal" column on CRM Task, filled in on tasks that
already exist. Runs before after_migrate, so it adds the column itself first.
A no-op on a site without CRM. Safe to run twice: rows already right are not written.
"""
import alvoraa_portal.crm_steps as crm_steps


def execute():
	if crm_steps.ensure_task_label_field():
		crm_steps.backfill_task_labels()
