# Copyright (c) 2026, AbdullahSalih and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class EWSReport(Document):
	def _validate_links(self):
		if self.district:
			# Format district name: remove extra spaces
			self.district = " ".join(self.district.split())

			if not frappe.db.exists("District", self.district):
				frappe.get_doc({
					"doctype": "District",
					"administrative_site": self.get("administrative_site"),
					"district_name": self.district
				}).insert(ignore_permissions=True)

		super()._validate_links()


def get_permission_query_conditions(user):
	if not user: user = frappe.session.user
	user_roles = frappe.get_roles(user)
	
	if "Administrator" in user_roles or "System Manager" in user_roles:
		return None
		
	mapped_provinces = frappe.db.get_list(
		"EWS User Province",
		filters={"user": user, "parent": "User Provinces"},
		pluck="province"
	)
	
	if not mapped_provinces:
		return "1=0"
		
	mapped_provinces_quoted = ", ".join(frappe.db.escape(p) for p in mapped_provinces)
	return f"`tabEWS Report`.province in ({mapped_provinces_quoted})"


def has_permission(doc, user=None, ptype="read"):
	if not user: user = frappe.session.user
	user_roles = frappe.get_roles(user)
	
	if "Administrator" in user_roles or "System Manager" in user_roles:
		return True
		
	mapped_provinces = frappe.db.get_list(
		"EWS User Province",
		filters={"user": user, "parent": "User Provinces"},
		pluck="province"
	)
	
	if doc.province in mapped_provinces:
		return True
		
	return False
