import os

import frappe
from frappe.website.page_renderers.base_renderer import BaseRenderer


class MobileSPARenderer(BaseRenderer):
	"""
	Custom page renderer that serves the Flutter web app as an SPA
	at /mobile and all sub-routes (e.g. /mobile/dashboard, /mobile/settings).

	All Flutter static assets (JS, CSS, icons, etc.) are served from
	/assets/ews/mobile/ by Frappe's built-in static file serving.
	This renderer only handles the HTML shell page.
	"""

	def can_render(self):
		return self.path == "mobile" or self.path.startswith("mobile/")

	def render(self):
		spa_html = self._get_spa_html()
		return self.build_response(
			spa_html,
			http_status_code=self.http_status_code or 200,
			headers={"Content-Type": "text/html; charset=utf-8"},
		)

	def _get_spa_html(self):
		html_path = frappe.get_app_path("ews", "public", "mobile", "index.html")
		if not os.path.exists(html_path):
			frappe.throw(
				"Flutter SPA build not found. Run 'flutter build web' first.",
				frappe.DoesNotExistError,
			)

		with open(html_path) as f:
			return f.read()
