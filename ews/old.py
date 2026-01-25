
# --------------------------------------------------


# @frappe.whitelist(allow_guest=False)
# def get_subfields_for_indicator(indicator_name: str, indicator_type: str, language: str = "en") -> Dict[str, Any]:
# 	"""
# 	Get subfields for a specific indicator when user selects it.
	
# 	Args:
# 		indicator_name (str): Name of the indicator
# 		indicator_type (str): Type - 'climate' or 'conflict'
# 		language (str): Language code for translations ('ar' for Arabic, 'en' for English, default: 'en')
	
# 	Returns:
# 		dict: Subfields with their details
# 	"""
	
# 	try:
# 		# Validate language parameter
# 		if language not in ["en", "ar"]:
# 			language = "en"
		
# 		if indicator_type == "climate":
# 			subfields = frappe.db.get_list(
# 				"Climate Indicators Subfields",
# 				fields=["name", "standard"],
# 				filters={"climate_indicators": indicator_name},
# 				order_by="standard asc"
# 			)
			
# 			return {
# 				"indicator": indicator_name,
# 				"type": "climate",
# 				"language": language,
# 				"subfields": [
# 					{
# 						"value": sf["name"],
# 						"label": _translate_text(sf.get("standard", sf["name"]), language)
# 					}
# 					for sf in subfields
# 				]
# 			}
		
# 		elif indicator_type == "conflict":
# 			thresholds = frappe.db.get_list(
# 				"Conflict Sub-fields",
# 				fields=["name", "threshold"],
# 				filters={"conflict_indicators": indicator_name},
# 				order_by="threshold asc"
# 			)
			
# 			return {
# 				"indicator": indicator_name,
# 				"type": "conflict",
# 				"language": language,
# 				"thresholds": [
# 					{
# 						"value": th["name"],
# 						"label": _translate_text(th.get("threshold", th["name"]), language)
# 					}
# 					for th in thresholds
# 				]
# 			}
		
# 		else:
# 			frappe.throw(_("Invalid indicator type: {0}").format(indicator_type))
	
# 	except Exception as e:
# 		frappe.log_error(f"Error getting subfields for {indicator_name}: {str(e)}")
# 		frappe.throw(_("Error fetching subfields: {0}").format(str(e)))


# @frappe.whitelist(allow_guest=False)
# def validate_field_dependencies(report_data: Dict[str, Any], language: str = "en") -> Dict[str, Any]:
# 	"""
# 	Validate that selected fields meet their dependency requirements.
	
# 	Args:
# 		report_data (dict): Form data to validate
# 		language (str): Language code for error messages ('ar' for Arabic, 'en' for English, default: 'en')
	
# 	Returns:
# 		dict: Validation result with errors if any
# 	"""
	
# 	try:
# 		# Validate language parameter
# 		if language not in ["en", "ar"]:
# 			language = "en"
		
# 		errors = {}
# 		doctype_meta = frappe.get_meta("EWS Report")
		
# 		for field in doctype_meta.fields:
# 			fieldname = field.fieldname
			
# 			# Check mandatory_depends_on
# 			if field.mandatory_depends_on and fieldname in report_data:
# 				# Evaluate the dependency expression
# 				doc_dict = {"doc": report_data}
# 				try:
# 					if not frappe.safe_eval(field.mandatory_depends_on, doc_dict):
# 						errors[fieldname] = _translate_text("This field is required based on your selections", language)
# 				except:
# 					pass
		
# 		return {
# 			"valid": len(errors) == 0,
# 			"errors": errors,
# 			"language": language
# 		}
	
# 	except Exception as e:
# 		frappe.log_error(f"Error validating dependencies: {str(e)}")
# 		return {
# 			"valid": False,
# 			"errors": {"general": str(e)},
# 			"language": language
# 		}
