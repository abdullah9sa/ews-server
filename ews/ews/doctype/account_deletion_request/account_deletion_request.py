# Copyright (c) 2026, Sustainable Peace Foundation and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class AccountDeletionRequest(Document):
    def before_save(self):
        if self.has_value_changed("status") and self.status == "Processed":
            self.processed_date = frappe.utils.now()
