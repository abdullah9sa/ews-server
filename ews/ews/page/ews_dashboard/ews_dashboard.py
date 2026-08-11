import frappe
from frappe import _
from frappe.utils import nowdate, add_days, getdate, get_first_day, get_last_day, add_months


@frappe.whitelist()
def get_dashboard_data(
    from_date=None,
    to_date=None,
    province=None,
    severity=None,
    report_type=None,
):
    """
    Main dashboard endpoint. Returns all stats needed for the EWS Dashboard page.

    Filters:
        from_date / to_date – restrict by EWS Report.timestamp (or creation fallback)
        province            – restrict by EWS Report.province
        severity            – restrict by EWS Report.severity
        report_type         – restrict by EWS Report.report_type
    """
    filters = _build_filters(from_date, to_date, province, severity, report_type)

    today = nowdate()
    week_ago = add_days(today, -7)
    month_ago = add_months(today, -1)

    # ── 1. Headline counts ──────────────────────────────────────────────
    total_reports = frappe.db.count("EWS Report", filters)

    today_filters = _merge(filters, {"creation": [">=", today]})
    reports_today = frappe.db.count("EWS Report", today_filters)

    week_filters = _merge(filters, {"creation": [">=", week_ago]})
    reports_this_week = frappe.db.count("EWS Report", week_filters)

    month_filters = _merge(filters, {"creation": [">=", month_ago]})
    reports_this_month = frappe.db.count("EWS Report", month_filters)

    critical_filters = _merge(filters, {"severity": "Critical"})
    critical_count = frappe.db.count("EWS Report", critical_filters)

    high_filters = _merge(filters, {"severity": "High"})
    high_count = frappe.db.count("EWS Report", high_filters)

    # ── 2. Breakdowns (GROUP BY queries) ────────────────────────────────
    where, values = _filters_to_sql(filters)

    severity_breakdown = frappe.db.sql(
        f"""
        SELECT severity, COUNT(*) as count
        FROM `tabEWS Report`
        {where}
        GROUP BY severity
        ORDER BY FIELD(severity, 'Critical', 'High', 'Moderate', 'Low')
        """,
        values,
        as_dict=True,
    )

    report_type_breakdown = frappe.db.sql(
        f"""
        SELECT report_type, COUNT(*) as count
        FROM `tabEWS Report`
        {where}
        GROUP BY report_type
        ORDER BY count DESC
        """,
        values,
        as_dict=True,
    )

    province_breakdown = frappe.db.sql(
        f"""
        SELECT IFNULL(province, 'Unknown') as province, COUNT(*) as count
        FROM `tabEWS Report`
        {where}
        GROUP BY province
        ORDER BY count DESC
        """,
        values,
        as_dict=True,
    )

    frequency_breakdown = frappe.db.sql(
        f"""
        SELECT frequency, COUNT(*) as count
        FROM `tabEWS Report`
        {where}
        GROUP BY frequency
        ORDER BY count DESC
        """,
        values,
        as_dict=True,
    )

    timing_breakdown = frappe.db.sql(
        f"""
        SELECT report_timing, COUNT(*) as count
        FROM `tabEWS Report`
        {where}
        GROUP BY report_timing
        ORDER BY count DESC
        """,
        values,
        as_dict=True,
    )

    # ── 3. Top climate & conflict indicators ────────────────────────────
    climate_indicators = frappe.db.sql(
        f"""
        SELECT climate_indicators as indicator, COUNT(*) as count
        FROM `tabEWS Report`
        {where} {"AND" if where else "WHERE"} climate_indicators IS NOT NULL
            AND climate_indicators != ''
        GROUP BY climate_indicators
        ORDER BY count DESC
        LIMIT 10
        """,
        values,
        as_dict=True,
    )

    conflict_indicators = frappe.db.sql(
        f"""
        SELECT conflict_indicators as indicator, COUNT(*) as count
        FROM `tabEWS Report`
        {where} {"AND" if where else "WHERE"} conflict_indicators IS NOT NULL
            AND conflict_indicators != ''
        GROUP BY conflict_indicators
        ORDER BY count DESC
        LIMIT 10
        """,
        values,
        as_dict=True,
    )

    # ── 4. Top reporters ────────────────────────────────────────────────
    top_reporters = frappe.db.sql(
        f"""
        SELECT
            observer,
            COUNT(*) as report_count,
            MAX(creation) as last_report
        FROM `tabEWS Report`
        {where}
        GROUP BY observer
        ORDER BY report_count DESC
        LIMIT 10
        """,
        values,
        as_dict=True,
    )
    # Resolve full names
    for r in top_reporters:
        r["full_name"] = frappe.db.get_value("User", r["observer"], "full_name") or r["observer"]

    # ── 5. Location breakdown (admin site + district) ───────────────────
    location_breakdown = frappe.db.sql(
        f"""
        SELECT
            IFNULL(administrative_site, 'Unknown') as administrative_site,
            IFNULL(district, 'Unknown') as district,
            COUNT(*) as count
        FROM `tabEWS Report`
        {where}
        GROUP BY administrative_site, district
        ORDER BY count DESC
        LIMIT 20
        """,
        values,
        as_dict=True,
    )

    # ── 6. Timeline – reports per day (last 30 days) ────────────────────
    timeline_start = add_days(today, -30)
    timeline = frappe.db.sql(
        f"""
        SELECT DATE(creation) as date, COUNT(*) as count
        FROM `tabEWS Report`
        {where} {"AND" if where else "WHERE"} creation >= %(tl_start)s
        GROUP BY DATE(creation)
        ORDER BY date ASC
        """,
        {**values, "tl_start": timeline_start},
        as_dict=True,
    )

    # ── 7. Recent reports ───────────────────────────────────────────────
    recent_reports = frappe.db.sql(
        f"""
        SELECT
            name, observer, province, administrative_site, district,
            severity, report_type, report_timing, frequency,
            climate_indicators, conflict_indicators,
            creation, timestamp
        FROM `tabEWS Report`
        {where}
        ORDER BY creation DESC
        LIMIT 20
        """,
        values,
        as_dict=True,
    )
    # Resolve observer names
    for r in recent_reports:
        r["observer_name"] = frappe.db.get_value("User", r["observer"], "full_name") or r["observer"]

    # ── 8. Severity over time (last 4 weeks, grouped by week) ──────────
    four_weeks_ago = add_days(today, -28)
    severity_trend = frappe.db.sql(
        f"""
        SELECT
            YEARWEEK(creation, 1) as yw,
            MIN(DATE(creation)) as week_start,
            severity,
            COUNT(*) as count
        FROM `tabEWS Report`
        {where} {"AND" if where else "WHERE"} creation >= %(sw_start)s
        GROUP BY yw, severity
        ORDER BY yw ASC
        """,
        {**values, "sw_start": four_weeks_ago},
        as_dict=True,
    )

    # ── 9. Province x Severity heatmap data ─────────────────────────────
    province_severity = frappe.db.sql(
        f"""
        SELECT
            IFNULL(province, 'Unknown') as province,
            severity,
            COUNT(*) as count
        FROM `tabEWS Report`
        {where}
        GROUP BY province, severity
        ORDER BY province, FIELD(severity, 'Critical', 'High', 'Moderate', 'Low')
        """,
        values,
        as_dict=True,
    )

    # ── 10. Filter options (for filter dropdowns) ───────────────────────
    provinces_list = frappe.db.get_list("Province", pluck="name", order_by="name asc")
    severity_options = ["Critical", "High", "Moderate", "Low"]
    report_type_options = [
        "Climate / Water / Environment",
        "Conflict / Social Tension",
    ]

    # ── 11. Unique observers count ──────────────────────────────────────
    unique_observers = frappe.db.sql(
        f"""
        SELECT COUNT(DISTINCT observer) as cnt
        FROM `tabEWS Report`
        {where}
        """,
        values,
        as_dict=True,
    )[0].cnt or 0

    return {
        # headline stats
        "total_reports": total_reports,
        "reports_today": reports_today,
        "reports_this_week": reports_this_week,
        "reports_this_month": reports_this_month,
        "critical_count": critical_count,
        "high_count": high_count,
        "unique_observers": unique_observers,
        # breakdowns
        "severity_breakdown": severity_breakdown,
        "report_type_breakdown": report_type_breakdown,
        "province_breakdown": province_breakdown,
        "frequency_breakdown": frequency_breakdown,
        "timing_breakdown": timing_breakdown,
        "climate_indicators": climate_indicators,
        "conflict_indicators": conflict_indicators,
        # people & places
        "top_reporters": top_reporters,
        "location_breakdown": location_breakdown,
        # time series
        "timeline": timeline,
        "severity_trend": severity_trend,
        # cross-tab
        "province_severity": province_severity,
        # table
        "recent_reports": recent_reports,
        # filter options
        "provinces_list": provinces_list,
        "severity_options": severity_options,
        "report_type_options": report_type_options,
    }


# ── helpers ─────────────────────────────────────────────────────────────

def _build_filters(from_date, to_date, province, severity, report_type):
    """Build a frappe-style filter dict from dashboard controls."""
    filters = {}
    if from_date:
        filters["creation"] = [">=", from_date]
    if to_date:
        # to_date is inclusive; add a day so that <= end-of-day works
        filters["creation"] = ["<=", add_days(getdate(to_date), 1)]
    if from_date and to_date:
        filters["creation"] = [
            "between",
            [from_date, add_days(getdate(to_date), 1)],
        ]
    if province:
        filters["province"] = province
    if severity:
        filters["severity"] = severity
    if report_type:
        filters["report_type"] = report_type
    return filters


def _merge(base, extra):
    """Return a new dict = base + extra, without mutating base."""
    merged = dict(base)
    merged.update(extra)
    return merged


def _filters_to_sql(filters):
    """Convert a frappe-style filters dict to a WHERE clause + values dict."""
    clauses = []
    values = {}
    idx = 0
    for field, condition in filters.items():
        if isinstance(condition, list):
            op = condition[0]
            if op.lower() == "between":
                clauses.append(f"`tabEWS Report`.`{field}` BETWEEN %(_v{idx}a)s AND %(_v{idx}b)s")
                values[f"_v{idx}a"] = condition[1][0]
                values[f"_v{idx}b"] = condition[1][1]
            else:
                clauses.append(f"`tabEWS Report`.`{field}` {op} %(_v{idx})s")
                values[f"_v{idx}"] = condition[1]
        else:
            clauses.append(f"`tabEWS Report`.`{field}` = %(_v{idx})s")
            values[f"_v{idx}"] = condition
        idx += 1

    where = "WHERE " + " AND ".join(clauses) if clauses else ""
    return where, values


@frappe.whitelist()
def get_all_reports(
    from_date=None,
    to_date=None,
    province=None,
    severity=None,
    report_type=None,
    report_timing=None,
    frequency=None,
    observer=None,
    administrative_site=None,
    district=None,
    climate_indicators=None,
    conflict_indicators=None,
    search=None,
    page=1,
    page_size=20,
    sort_field="creation",
    sort_order="DESC",
):
    """
    Paginated reports endpoint with specialized filters for the All Reports table.
    Returns reports list + total count + filter option lists.
    """
    page = max(1, int(page))
    page_size = min(100, max(5, int(page_size)))
    offset = (page - 1) * page_size

    # Validate sort
    allowed_sort_fields = {
        "creation", "timestamp", "severity", "province",
        "report_type", "observer", "administrative_site",
    }
    if sort_field not in allowed_sort_fields:
        sort_field = "creation"
    if sort_order.upper() not in ("ASC", "DESC"):
        sort_order = "DESC"

    # Build WHERE clauses
    clauses = []
    values = {}
    idx = 0

    def _add(field, op, val):
        nonlocal idx
        clauses.append(f"`tabEWS Report`.`{field}` {op} %(_f{idx})s")
        values[f"_f{idx}"] = val
        idx += 1

    if from_date and to_date:
        clauses.append(f"`tabEWS Report`.`creation` BETWEEN %(_f{idx}a)s AND %(_f{idx}b)s")
        values[f"_f{idx}a"] = from_date
        values[f"_f{idx}b"] = add_days(getdate(to_date), 1)
        idx += 1
    elif from_date:
        _add("creation", ">=", from_date)
    elif to_date:
        _add("creation", "<=", add_days(getdate(to_date), 1))

    if province:
        _add("province", "=", province)
    if severity:
        _add("severity", "=", severity)
    if report_type:
        _add("report_type", "=", report_type)
    if report_timing:
        _add("report_timing", "=", report_timing)
    if frequency:
        _add("frequency", "=", frequency)
    if observer:
        _add("observer", "=", observer)
    if administrative_site:
        _add("administrative_site", "=", administrative_site)
    if district:
        _add("district", "=", district)
    if climate_indicators:
        _add("climate_indicators", "=", climate_indicators)
    if conflict_indicators:
        _add("conflict_indicators", "=", conflict_indicators)
    if search:
        search_val = f"%{search}%"
        clauses.append(
            f"(`tabEWS Report`.`name` LIKE %(_fs)s "
            f"OR `tabEWS Report`.`observer` LIKE %(_fs)s "
            f"OR `tabEWS Report`.`province` LIKE %(_fs)s "
            f"OR `tabEWS Report`.`district` LIKE %(_fs)s "
            f"OR `tabEWS Report`.`administrative_site` LIKE %(_fs)s "
            f"OR `tabEWS Report`.`extra_details` LIKE %(_fs)s)"
        )
        values["_fs"] = search_val

    where = "WHERE " + " AND ".join(clauses) if clauses else ""

    # Count
    total = frappe.db.sql(
        f"SELECT COUNT(*) as cnt FROM `tabEWS Report` {where}",
        values,
        as_dict=True,
    )[0].cnt or 0

    # Fetch page
    reports = frappe.db.sql(
        f"""
        SELECT
            name, observer, province, administrative_site, district,
            severity, ai_severity, report_type, report_timing, frequency,
            climate_indicators, conflict_indicators,
            standard, conflict_threshold,
            affected_groups, participated_groups, most_affected_groups,
            extra_details, creation, timestamp
        FROM `tabEWS Report`
        {where}
        ORDER BY `tabEWS Report`.`{sort_field}` {sort_order}
        LIMIT %(limit)s OFFSET %(offset)s
        """,
        {**values, "limit": page_size, "offset": offset},
        as_dict=True,
    )

    # Resolve observer names
    for r in reports:
        r["observer_name"] = (
            frappe.db.get_value("User", r["observer"], "full_name") or r["observer"]
        )

    # Filter option lists for the inline filter controls
    observers_list = frappe.db.sql(
        "SELECT DISTINCT observer FROM `tabEWS Report` WHERE observer IS NOT NULL ORDER BY observer",
        as_dict=False,
    )
    observers_list = [row[0] for row in observers_list]

    admin_sites_list = frappe.db.sql(
        "SELECT DISTINCT administrative_site FROM `tabEWS Report` WHERE administrative_site IS NOT NULL AND administrative_site != '' ORDER BY administrative_site",
        as_dict=False,
    )
    admin_sites_list = [row[0] for row in admin_sites_list]

    districts_list = frappe.db.sql(
        "SELECT DISTINCT district FROM `tabEWS Report` WHERE district IS NOT NULL AND district != '' ORDER BY district",
        as_dict=False,
    )
    districts_list = [row[0] for row in districts_list]

    climate_list = frappe.db.sql(
        "SELECT DISTINCT climate_indicators FROM `tabEWS Report` WHERE climate_indicators IS NOT NULL AND climate_indicators != '' ORDER BY climate_indicators",
        as_dict=False,
    )
    climate_list = [row[0] for row in climate_list]

    conflict_list = frappe.db.sql(
        "SELECT DISTINCT conflict_indicators FROM `tabEWS Report` WHERE conflict_indicators IS NOT NULL AND conflict_indicators != '' ORDER BY conflict_indicators",
        as_dict=False,
    )
    conflict_list = [row[0] for row in conflict_list]

    return {
        "reports": reports,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, -(-total // page_size)),  # ceil division
        # filter options
        "provinces_list": frappe.db.get_list("Province", pluck="name", order_by="name asc"),
        "severity_options": ["Critical", "High", "Moderate", "Low"],
        "report_type_options": ["Climate / Water / Environment", "Conflict / Social Tension"],
        "timing_options": ["Ongoing / Current Incident", "Expected / Forecasted"],
        "frequency_options": ["Rare/First Time", "Occasionally Frequent", "Constantly Frequent or Almost Daily"],
        "observers_list": observers_list,
        "admin_sites_list": admin_sites_list,
        "districts_list": districts_list,
        "climate_list": climate_list,
        "conflict_list": conflict_list,
    }


@frappe.whitelist()
def get_report_detail(report_name):
    """
    Get full details of a single EWS Report for the detail popup.
    Resolves all linked field names.
    """
    if not report_name:
        frappe.throw("Report name is required")

    report = frappe.db.sql(
        """
        SELECT *
        FROM `tabEWS Report`
        WHERE name = %(name)s
        LIMIT 1
        """,
        {"name": report_name},
        as_dict=True,
    )

    if not report:
        frappe.throw(f"Report {report_name} not found")

    r = report[0]

    # Resolve names
    r["observer_name"] = frappe.db.get_value("User", r.get("observer"), "full_name") or r.get("observer", "")

    # Resolve subfield display values
    if r.get("standard"):
        r["standard_label"] = frappe.db.get_value(
            "Climate Indicators Subfields", r["standard"], "standard"
        ) or r["standard"]
    if r.get("conflict_threshold"):
        r["conflict_threshold_label"] = frappe.db.get_value(
            "Conflict Sub-fields", r["conflict_threshold"], "threshold"
        ) or r["conflict_threshold"]

    return r
