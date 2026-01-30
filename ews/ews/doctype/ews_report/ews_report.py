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
