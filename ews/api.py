import frappe
from frappe import _
from typing import Dict, List, Any, Optional

# Configuration constants for field visibility and access control
# These can be easily modified to control which fields are read-only or hidden
READONLY_FIELDS = set({"province","longitude","latitude"})  # Fields that should always be read-only (e.g., {"creation", "modified_by"})
HIDDEN_FIELDS = set({"image_2","ai_severity","province","whatsapp_status","accuracy","altitude","observer","creation", "modified_by"})    # Fields that should be hidden from the API (e.g., {"internal_notes"})

# Configuration for response dependencies
# Maps child field names to their dependency configuration
RESPONSE_DEPENDENCIES = {
	"conflict_threshold": {
		"depends_on": "conflict_indicators",
		"filter_field": "conflict_indicators",
		"child_doctype": "Conflict Sub-fields",
		"label_field": "threshold",
		"group_key": "thresholds",
		"type_value": "conflict_indicator"
	},
	"standard": {
		"depends_on": "climate_indicators",
		"filter_field": "climate_indicators",
		"child_doctype": "Climate Indicators Subfields",
		"label_field": "standard",
		"group_key": "subfields",
		"type_value": "climate_indicator"
	},
	"district": {
		"depends_on": "administrative_site",
		"filter_field": "administrative_site",
		"child_doctype": "District",
		"label_field": "name",
		"group_key": "districts",
		"type_value": "district",
		"label_field_ar": "district_name_arabic"
	}
}

def _translate_text(text: str, language: str = "ar") -> str:
	"""
	Translate text using Frappe's translation system.
	
	Args:
		text (str): The text to translate
		language (str): Target language code ('ar' for Arabic, 'en' for English)
	
	Returns:
		str: Translated text or original if no translation found
	"""
	if not text or language == "en":
		return text
	
	try:
		# Use frappe's standard translation system which checks:
		# 1. Translation Doctype (user overrides)
		# 2. Application translation files (CSV)
		return frappe._(text, lang=language)
	except Exception as e:
		frappe.log_error(f"Error translating '{text}' to {language}: {str(e)}")
		return text

def _apply_language_to_dict(data: Any, language: str = "ar", keys_to_translate: List[str] = None) -> Any:
	"""
	Recursively apply language translations to dictionary/list structures.
	Translates ALL label-like fields and option values.
	
	Args:
		data: Dictionary, list, or value to translate
		language (str): Target language code
		keys_to_translate (list): Keys whose values should be translated
	
	Returns:
		Translated data structure
	"""
	if language == "en":
		return data
	
	if keys_to_translate is None:
		keys_to_translate = ["label", "description", "placeholder", "help_text", "title"]
	
	if isinstance(data, dict):
		result = {}
		for key, value in data.items():
			if key in keys_to_translate and isinstance(value, str):
				# Translate label-like keys
				result[key] = _translate_text(value, language)
			elif key == "option_values" and isinstance(value, list):
				# Translate option values (and their nested children like districts, subfields, etc.)
				result[key] = _translate_option_values(value, language, keys_to_translate)
			elif isinstance(value, (dict, list)):
				# Recursively translate nested structures
				result[key] = _apply_language_to_dict(value, language, keys_to_translate)
			else:
				result[key] = value
		return result
	elif isinstance(data, list):
		return [_apply_language_to_dict(item, language, keys_to_translate) for item in data]
	else:
		return data

def _translate_option_values(options: List[Any], language: str = "ar", keys_to_translate: List[str] = None) -> List[Any]:
	"""
	Translate option values in lists.
	Ensures string options are converted to dicts {value: "Select", label: "اختر"} 
	so original values are preserved for logic dependencies.
	"""
	if language == "en" or not options:
		return options
	
	if keys_to_translate is None:
		keys_to_translate = ["label", "description", "placeholder", "help_text", "title"]
	
	result = []
	for option in options:
		if isinstance(option, dict):
			# Translate dict option (has value, label, etc.)
			translated_option = option.copy()
			if "label" in translated_option and isinstance(translated_option["label"], str):
				translated_option["label"] = _translate_text(translated_option["label"], language)
			
			# Recursively translate nested dependency fields: districts, subfields, thresholds, etc.
			dependency_keys = ["districts", "subfields", "thresholds"]
			for dep_key in dependency_keys:
				if dep_key in translated_option and isinstance(translated_option[dep_key], list):
					translated_option[dep_key] = _translate_option_values(
						translated_option[dep_key], language, keys_to_translate
					)
			result.append(translated_option)
		elif isinstance(option, str):
			# FIX: Return dict with original value AND translated label
			result.append({
				"value": option,
				"label": _translate_text(option, language)
			})
		else:
			result.append(option)
	return result

@frappe.whitelist(allow_guest=False)
def get_ews_report_form(exclude_fields: Optional[str] = None, language: str = "ar", 
                        readonly_fields: Optional[str] = None, hidden_fields: Optional[str] = None) -> Dict[str, Any]:
	"""
	Get EWS Report form structure with all fields, options, and dependencies.
	
	This endpoint returns:
	- Form field structure including tabs, sections, and column breaks
	- Field options for Link and Select fields
	- Dependent fields with their relationships
	- Climate Indicators with their subfields
	- Conflict Indicators with their thresholds
	
	Args:
		exclude_fields (str): Comma-separated fieldnames to exclude from response
		language (str): Language code for translations ('ar' for Arabic, 'en' for English, default: 'en')
		readonly_fields (str): Comma-separated fieldnames to force as read-only (in addition to code configuration)
		hidden_fields (str): Comma-separated fieldnames to hide from response (in addition to code configuration)
	
	Returns:
		dict: Mobile-friendly form structure with nested options and dependencies
	"""
	
	try:
		# Validate language parameter
		if language not in ["en", "ar"]:
			language = "en"
		
		# Parse exclude_fields
		excluded = set()
		if exclude_fields:
			excluded = set(f.strip() for f in exclude_fields.split(',') if f.strip())
			
		# Explicitly exclude province field as requested
		excluded.add("province")
		
		# Parse readonly_fields - combine code config with runtime parameter
		readonly = READONLY_FIELDS.copy()
		if readonly_fields:
			readonly.update(f.strip() for f in readonly_fields.split(',') if f.strip())
		
		# Parse hidden_fields - combine code config with runtime parameter
		hidden = HIDDEN_FIELDS.copy()
		if hidden_fields:
			hidden.update(f.strip() for f in hidden_fields.split(',') if f.strip())
			
		# Automatically exclude dependent child fields from top-level schema
		# Their values will be embedded in parent fields
		excluded.update(RESPONSE_DEPENDENCIES.keys())
		
		# Get EWS Report doctype metadata
		doctype_meta = frappe.get_meta("EWS Report")
		
		# Build response structure
		response = {
			"doctype": "EWS Report",
			"label": _translate_text(doctype_meta.name, language),
			"language": language,
			"tabs": []
		}
		
		# Process fields
		current_section = None
		# Process fields - organize by tabs, sections, columns, fields
		current_tab = None
		current_section = None
		current_column = 0
		fields_in_column = []
		
		for field in doctype_meta.fields:
			fieldname = field.fieldname
			
			# Skip excluded fields
			if fieldname in excluded:
				continue
			
			# Handle Tab Breaks
			if field.fieldtype == "Tab Break":
				# Save previous section and tab
				if current_section is not None:
					if fields_in_column:
						current_section["columns"].append({
							"column_index": current_column,
							"fields": fields_in_column
						})
					current_tab["sections"].append(current_section)
				
				if current_tab is not None:
					response["tabs"].append(current_tab)
				
				# Start new tab
				current_tab = {
					"fieldname": fieldname,
					"label": _translate_text(field.label or fieldname, language),
					"type": "tab",
					"sections": []
				}
				current_section = None
				current_column = 0
				fields_in_column = []
			
			# Handle Section Breaks
			elif field.fieldtype == "Section Break":
				# Ensure we have a tab
				if current_tab is None:
					current_tab = {
						"fieldname": "default_tab",
						"label": _translate_text("Details", language),
						"type": "tab",
						"sections": []
					}
				
				# Save previous section if exists
				if current_section is not None:
					if fields_in_column:
						current_section["columns"].append({
							"column_index": current_column,
							"fields": fields_in_column
						})
					current_tab["sections"].append(current_section)
				
				# Start new section
				current_section = {
					"fieldname": fieldname,
					"label": _translate_text(field.label or fieldname, language),
					"type": "section",
					"columns": []
				}
				current_column = 0
				fields_in_column = []
			
			# Handle Column Breaks
			elif field.fieldtype == "Column Break":
				pass
				# # Ensure we have a tab and section
				# if current_tab is None:
				# 	current_tab = {
				# 		"fieldname": "default_tab",
				# 		"label": _translate_text("Details", language),
				# 		"type": "tab",
				# 		"sections": []
				# 	}
				
				# if current_section is None:
				# 	current_section = {
				# 		"fieldname": "default_section",
				# 		"label": _translate_text("Information", language),
				# 		"type": "section",
				# 		"columns": []
				# 	}
				
				# # Save current column if it has fields
				# if fields_in_column:
				# 	current_section["columns"].append({
				# 		"column_index": current_column,
				# 		"fields": fields_in_column
				# 	})
				# current_column += 1
				# fields_in_column = []
			
			# Handle regular fields
			else:
				# Ensure we have a tab and section
				if current_tab is None:
					current_tab = {
						"fieldname": "default_tab",
						"label": _translate_text("Details", language),
						"type": "tab",
						"sections": []
					}
				
				if current_section is None:
					current_section = {
						"fieldname": "default_section",
						"label": _translate_text("Information", language),
						"type": "section",
						"columns": []
					}
				
				field_data = _build_field_data(field, excluded, language, readonly, hidden)
				if field_data:
					fields_in_column.append(field_data)
		
		# Add last section and tab
		if current_section is not None:
			if fields_in_column:
				current_section["columns"].append({
					"column_index": current_column,
					"fields": fields_in_column
				})
			current_tab["sections"].append(current_section)
		
		if current_tab is not None:
			response["tabs"].append(current_tab)
		
		# Add metadata
		response["metadata"] = {
			"total_tabs": len(response["tabs"]),
			"is_mobile_friendly": True,
			"dynamic_rendering": True,
			"language": language
		}
		
		# Apply language translations to entire response
		response = _apply_language_to_dict(response, language)
		
		return response
		
	except Exception as e:
		frappe.log_error(f"Error in get_ews_report_form: {str(e)}")
		frappe.throw(_("Error fetching EWS Report form: {0}").format(str(e)))


def _build_field_data(field, excluded: set, language: str = "ar", readonly: set = None, hidden: set = None) -> Optional[Dict[str, Any]]:
	"""Build field data structure for a single field."""
	
	if readonly is None:
		readonly = set()
	if hidden is None:
		hidden = set()
	
	fieldname = field.fieldname
	
	if fieldname in excluded:
		return None
	
	field_data = {
		"fieldname": fieldname,
		"label": _translate_text(field.label or fieldname, language),
		"fieldtype": field.fieldtype,
		"reqd": 1 if field.reqd else 0,
		"read_only": 1 if (field.read_only or fieldname in readonly) else 0,
		"hidden": 1 if fieldname in hidden else 0
	}
	
	# Add optional properties based on field configuration
	if field.description:
		field_data["description"] = _translate_text(field.description, language)
	
	if field.placeholder:
		field_data["placeholder"] = _translate_text(field.placeholder, language)
	
	if field.depends_on:
		field_data["depends_on"] = field.depends_on
	
	if field.mandatory_depends_on:
		field_data["mandatory_depends_on"] = field.mandatory_depends_on
	
	# Set default value for province field based on user's role
	if fieldname == "province":
		user_province = _get_user_province()
		if user_province:
			field_data["default"] = user_province
	
	# Add field-specific properties
	if field.fieldtype == "Link":
		field_data["options"] = field.options
		
		# 1. Get base options (handles Role checks for Province, etc.)
		options = _get_link_options(field.options, excluded, language)
		
		# 2. Enrich with children recursively if this field has dependents
		mapped_child = _attach_recursive_dependencies(field.fieldname, options, language)
		
		field_data["option_values"] = options
		if mapped_child:
			field_data["mapped_child_field"] = mapped_child
	
	elif field.fieldtype == "Select":
		if field.options:
			options = [o.strip() for o in field.options.split('\n') if o.strip()]
			field_data["option_values"] = _translate_option_values(options, language)
	
	elif field.fieldtype in ["Attach", "Attach Image"]:
		field_data["file_type"] = "attachment"
	
	elif field.fieldtype == "Geolocation":
		field_data["mobile_specific"] = True
	
	# Validation rules
	if hasattr(field, 'validate_depends_on') and field.validate_depends_on:
		field_data["validate_depends_on"] = field.validate_depends_on
	
	return field_data


def _get_link_options(link_doctype: str, excluded: set, language: str = "ar") -> List[Dict[str, Any]]:
	"""
	Get all options for a Link field.
	
	Special handling for:
	- User (observer): Return empty - user is automatically set
	- Province: Filter based on user roles
	- Administrative Site: Filter based on accessible provinces
	- Climate Indicators (with subfields)
	- Conflict Indicators (with thresholds)
	"""
	
	try:
		if link_doctype == "User":
			# Observer is automatically set, don't return options
			return []
		
		elif link_doctype == "Province":
			return _get_province_options_for_user(excluded, language)
		
		elif link_doctype in ["Climate Indicators", "Conflict Indicators"]:
			accessible_provinces = _get_accessible_province_names()
			if not accessible_provinces:
				return []
				
			records = frappe.db.get_list(
				link_doctype,
				fields=["name"],
				filters=[["province", "in", accessible_provinces + [""]]],
				limit_page_length=500,
				ignore_permissions=True
			)
			return [{"value": r["name"], "label": _translate_text(r["name"], language)} for r in records]

		elif link_doctype == "Administrative Site":
			# Return expanded admin sites with nested districts
			# Filtered by user's default province
			return _get_administrative_sites_with_districts_for_user(excluded, language)
		
		elif link_doctype == "District":
			# Return only districts related to user's accessible provinces (via admin sites)
			return _get_districts_for_user(excluded, language)
		
		else:
			# Generic link field - get all documents
			records = frappe.db.get_list(
				link_doctype,
				fields=["name"],
				limit_page_length=500,
				ignore_permissions=True
			)
			return [{"value": r["name"], "label": _translate_text(r["name"], language)} for r in records]
	
	except Exception as e:
		frappe.log_error(f"Error getting options for {link_doctype}: {str(e)}")
		return []


def _get_province_options_for_user(excluded: set, language: str = "ar") -> List[Dict[str, Any]]:
	"""
	Get provinces available to current user based on User Provinces mapping.
	"""
	try:
		accessible_provinces = _get_accessible_province_names()
		
		if not accessible_provinces:
			return []
			
		provinces = frappe.db.get_list(
			"Province",
			fields=["name"],
			filters={"name": ["in", accessible_provinces]},
			order_by="name asc"
		)
		
		available_provinces = []
		for province in provinces:
			province_name = province["name"]
			available_provinces.append({
				"value": province_name,
				"label": _translate_text(province_name, language)
			})
		
		return available_provinces
	
	except Exception as e:
		frappe.log_error(f"Error getting province options: {str(e)}")
		return []


def _get_accessible_province_names() -> List[str]:
	"""
	Get list of province names that current user has access to based on User Provinces mapping.
	
	Returns:
		List of province names user can access
	"""
	try:
		current_user = frappe.session.user
		user_roles = frappe.get_roles(current_user)
		
		if "Administrator" in user_roles or "System Manager" in user_roles:
			return frappe.db.get_list("Province", pluck="name")
			
		mapped_provinces = frappe.db.get_list(
			"EWS User Province",
			filters={"user": current_user, "parent": "User Provinces"},
			pluck="province",
			ignore_permissions=True
		)
		
		return list(set(mapped_provinces))
	
	except Exception as e:
		frappe.log_error(f"Error getting accessible provinces: {str(e)}")
		return []


def _get_administrative_sites_with_districts_for_user(excluded: set, language: str = "ar") -> List[Dict[str, Any]]:
	"""
	Get Administrative Sites for the user's assigned province, including nested Districts.
	"""
	try:
		# 1. Determine target province(s)
		# Prioritize the user's assigned "Reporter" province. 
		# If none (e.g. Admin), fall back to all accessible provinces.
		target_province = _get_user_province()
		
		filters = {}
		if target_province:
			filters = {"province": target_province}
		else:
			# Fallback: all accessible provinces
			accessible = _get_accessible_province_names()
			if accessible:
				filters = {"province": ["in", accessible]}
			else:
				return [] # No access
		
		# 2. Get Admin Sites
		admin_sites = frappe.db.get_list(
			"Administrative Site",
			fields=["name", "province"],
			filters=filters,
			limit_page_length=1000,
			ignore_permissions=True,
			order_by="name asc"
		)
		
		# 3. Build options list
		options = []
		for site in admin_sites:
			options.append({
				"value": site["name"],
				"label": _translate_text(site["name"], language),
				"province": site["province"],
				"type": "administrative_site"
			})
			
		# 4. Attach recursive dependencies (Districts)
		# This uses the RESPONSE_DEPENDENCIES config to attach districts
		_attach_recursive_dependencies("administrative_site", options, language)
		
		return options
	
	except Exception as e:
		frappe.log_error(f"Error getting admin sites with districts: {str(e)}")
		return []


def _get_districts_for_user(excluded: set, language: str = "ar") -> List[Dict[str, Any]]:
	"""
	Get Districts only for provinces the user has access to.
	
	Filters via Administrative Site.
	"""
	try:
		# Get provinces user has access to
		accessible_provinces = _get_accessible_province_names()
		
		# If user has no accessible provinces, return empty list
		if not accessible_provinces:
			return []
		
		# Get administrative sites for accessible provinces
		admin_sites = frappe.db.get_list(
			"Administrative Site",
			fields=["name"],
			filters={"province": ["in", accessible_provinces]},
			pluck="name", # optimization: get list of names directly
			limit_page_length=2000,
			ignore_permissions=True
		)
		
		if not admin_sites:
			return []
		
		# Get districts for these admin sites
		# Determine fields to fetch
		fields = ["name", "administrative_site"]
		label_field = "name"
		if language == "ar":
			fields.append("district_name_arabic")
			label_field = "district_name_arabic"

		records = frappe.db.get_list(
			"District",
			fields=fields,
			filters={"administrative_site": ["in", admin_sites]},
			limit_page_length=2000,
			ignore_permissions=True
		)
		
		return [
			{
				"value": r["name"],
				"label": _translate_text(r.get(label_field) or r["name"], language),
				"administrative_site_filter": r.get("administrative_site")
			}
			for r in records
		]
	
	except Exception as e:
		frappe.log_error(f"Error getting districts for user: {str(e)}")
		return []


def _attach_recursive_dependencies(parent_fieldname: str, options: List[Dict[str, Any]], language: str = "ar") -> Optional[str]:
	"""
	Recursively find and attach child dependencies to options.
	
	Args:
		parent_fieldname: The field name corresponding to the current options
		options: List of option dictionaries (modified in-place)
		language: Language code
		
	Returns:
		str: The name of the immediate child field attached, or None
	"""
	mapped_child_field = None
	dependency_config = None
	
	# Find if any field depends on this parent_fieldname
	for child_field, config in RESPONSE_DEPENDENCIES.items():
		if config.get("depends_on") == parent_fieldname:
			mapped_child_field = child_field
			dependency_config = config
			break
			
	if not dependency_config or not options:
		return None
		
	# Process one level of dependency (recurse inside)
	try:
		for option in options:
			parent_value = option.get("value")
			if not parent_value:
				continue
				
			# Fetch direct children
			label_field = dependency_config.get("label_field", "name")
			# Use Arabic label if available and requested
			if language == "ar" and dependency_config.get("label_field_ar"):
				label_field = dependency_config.get("label_field_ar")

			children = frappe.db.get_list(
				dependency_config["child_doctype"],
				fields=["name", label_field],
				filters={dependency_config["filter_field"]: parent_value},
				order_by=f"{label_field} asc",
				ignore_permissions=True
			)
			
			child_options = []
			for child in children:
				child_val = child["name"]
				child_label = child.get(label_field) or child_val
				
				child_opt = {
					"value": child_val,
					"label": _translate_text(child_label, language),
					"type": dependency_config.get("type_value", "option")
				}
				child_options.append(child_opt)
				
			# Recurse: Treat this child as a parent for the next level
			_attach_recursive_dependencies(mapped_child_field, child_options, language)
			
			# Attach children to parent option
			option[dependency_config["group_key"]] = child_options
			
		return mapped_child_field

	except Exception as e:
		frappe.log_error(f"Error attaching dependencies for {parent_fieldname}: {str(e)}")
		return None



# NOTE: register_reporter and get_public_provinces have been moved to ews.auth_api
# Re-exported here to maintain the same API endpoints for the Flutter mobile app
from ews.auth_api import register_reporter, send_otp, verify_otp, login, get_public_provinces



@frappe.whitelist()
def get_dashboard_stats(language: str = "ar") -> Dict[str, Any]:
	"""
	Get dashboard statistics for the current user.
	Args:
		language (str): Language code ('ar' for Arabic, 'en' for English)
	Returns:
		- Number of reports made last week
		- Number of reports made today
		- 5 most recent reports with full data
	"""
	from frappe.utils import add_days, nowdate
	
	try:
		user = frappe.session.user
		today = nowdate()
		last_week = add_days(today, -7)

		stats_filters = {}
		
		# Reports last week (last 7 days)
		last_week_filters = stats_filters.copy()
		last_week_filters["creation"] = [">=", last_week]
		last_week_count = frappe.db.count("EWS Report", last_week_filters)
		
		# Reports today
		today_filters = stats_filters.copy()
		today_filters["creation"] = [">=", today]
		today_count = frappe.db.count("EWS Report", today_filters)
		
		# Recent 5 reports (only user's history)
		history_filters = {"owner": user}
		
		# Using get_list with * fetches all columns in the main table
		recent_reports = frappe.get_list("EWS Report", 
			filters=history_filters,
			fields=["*"],
			order_by="creation desc",
			limit=5
		)
		
		# Translate reports
		recent_reports = _translate_report_list(recent_reports, language)
		
		return {
			"reports_last_week": last_week_count,
			"reports_today": today_count,
			"recent_reports": recent_reports
		}
	except Exception as e:
		frappe.log_error(f"Error fetching dashboard stats: {str(e)}")
		return {
			"reports_last_week": 0,
			"reports_today": 0,
			"recent_reports": []
		}


@frappe.whitelist()
def get_user_report_history(limit: int = 20, language: str = "ar") -> List[Dict[str, Any]]:
	"""
	Get user report history.
	Args:
		limit (int): Number of reports to return (default 20)
		language (str): Language code ('ar' for Arabic, 'en' for English)
	"""
	try:
		filters = {"owner": frappe.session.user}

		reports = frappe.get_list("EWS Report", 
			filters=filters,
			fields=["*"],
			order_by="creation desc",
			limit_page_length=int(limit)
		)
		return _translate_report_list(reports, language)
	except Exception as e:
		frappe.log_error(f"Error fetching report history: {str(e)}")
		return []

def _translate_report_list(reports: List[Dict[str, Any]], language: str = "ar") -> List[Dict[str, Any]]:
	"""
	Translate report values to the target language.
	Translates Select fields and Link fields where applicable.
	"""
	if not reports or language != "ar":
		return reports
		
	# Select fields to translate
	# These are standard strings that should be in translation files
	select_fields = [
		"severity", "report_timing", "report_type", 
		"frequency", "whatsapp_status"
	]
	
	# Link fields relying on frappe translation (translatable=1)
	# Assumes names are translated in the system
	standard_link_fields = [
		"administrative_site", "climate_indicators", "conflict_indicators"
	]

	for report in reports:
		# 1. Translate Select fields
		for field in select_fields:
			if report.get(field):
				report[field] = frappe._(report[field], lang=language)
		
		# 2. Translate Standard Link fields
		for field in standard_link_fields:
			if report.get(field):
				report[field] = frappe._(report[field], lang=language)
		
		# 3. Translate Subfield Links (standard, conflict_threshold)
		# These have autonames with suffixes (e.g. "Text01"), so we must fetch the raw text field
		if report.get("standard"):
			standard_val = frappe.db.get_value("Climate Indicators Subfields", report["standard"], "standard")
			if standard_val:
				report["standard"] = frappe._(standard_val, lang=language)
			else:
				# Fallback if lookup fails (unlikely)
				report["standard"] = frappe._(report["standard"], lang=language)

		if report.get("conflict_threshold"):
			threshold_val = frappe.db.get_value("Conflict Sub-fields", report["conflict_threshold"], "threshold")
			if threshold_val:
				report["conflict_threshold"] = frappe._(threshold_val, lang=language)
			else:
				report["conflict_threshold"] = frappe._(report["conflict_threshold"], lang=language)
				
		# 4. Translate Fields with Special Arabic Columns
		
		# Province -> province_name_arabic
		if report.get("province"):
			ar_province = frappe.db.get_value("Province", report["province"], "province_name_arabic")
			if ar_province:
				report["province"] = ar_province
				
		# District -> district_name_arabic
		if report.get("district"):
			ar_district = frappe.db.get_value("District", report["district"], "district_name_arabic")
			if ar_district:
				report["district"] = ar_district

	return reports


@frappe.whitelist()
def update_account_settings(full_name: Optional[str] = None, password: Optional[str] = None) -> Dict[str, Any]:
	"""
	Update user account settings (name and password).
	"""
	from frappe.utils.password import update_password
	
	try:
		user = frappe.session.user
		
		if full_name:
			frappe.db.set_value("User", user, "first_name", full_name)
		
		if password:
			# update_password handles hashing and saving
			frappe.flags.ignore_password_policy = True
			try:
				update_password(user, password)
			finally:
				frappe.flags.ignore_password_policy = False
			
		return {
			"status": "success",
			"message": _("Account settings updated successfully")
		}
	except Exception as e:
		frappe.log_error(f"Error updating account settings: {str(e)}")
		frappe.throw(_("Error updating account settings: {0}").format(str(e)))


@frappe.whitelist(allow_guest=True)
def get_about_app_text() -> Dict[str, str]:
	"""
	Return text from single settings doctype EWS Settings.
	"""
	try:
		about_text = frappe.db.get_single_value("EWS Settings", "about_app_text")
		return {"about_app_text": about_text}
	except Exception as e:
		frappe.log_error(f"Error fetching about text: {str(e)}")
		return {"about_app_text": ""}


@frappe.whitelist()
def get_current_user_info() -> Dict[str, Any]:
	"""
	Get current user's name and province.
	
	Returns:
		dict: Contains user's first_name and province name
	"""
	try:
		user_email = frappe.session.user
		
		# Get user's full name
		user_doc = frappe.get_doc("User", user_email)
		full_name = user_doc.first_name or ""
		
		# Get user's province from their roles
		province = _get_user_province(user_email)
		
		return {
			"name": full_name,
			"email": user_email,
			"province": province
		}
	
	except Exception as e:
		frappe.log_error(f"Error fetching current user info: {str(e)}")
		frappe.throw(_("Error fetching user information: {0}").format(str(e)))


def _get_user_province(user_email: str = None) -> Optional[str]:
	"""
	Get the primary province associated with the user via User Provinces mapping.
	"""
	try:
		if not user_email:
			user_email = frappe.session.user
			
		mapped_provinces = frappe.db.get_list(
			"EWS User Province",
			filters={"user": user_email, "parent": "User Provinces"},
			pluck="province",
			limit=1,
			ignore_permissions=True
		)
		
		if mapped_provinces:
			return mapped_provinces[0]
				
		return None
	except Exception as e:
		frappe.log_error(f"Error getting user province: {str(e)}")
		return None
