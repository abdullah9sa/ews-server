frappe.pages["ews-dashboard"].on_page_load = function (wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("EWS Dashboard"),
		single_column: true,
	});

	// attach our controller
	page.dashboard = new EWSDashboard(page);
};

class EWSDashboard {
	constructor(page) {
		this.page = page;
		this.filters = {};
		this.data = {};

		// All Reports table state
		this.all_reports_page = 1;
		this.all_reports_page_size = 20;
		this.all_reports_filters = {};
		this.all_reports_data = null;

		this.setup_css();
		this.make_filters();
		this.make_layout();
		this.refresh();
	}

	/* ═══════════════════════════════════════════
	   CSS
	   ═══════════════════════════════════════════ */
	setup_css() {
		if (document.getElementById("ews-dashboard-style")) return;

		const style = document.createElement("style");
		style.id = "ews-dashboard-style";
		style.textContent = `
		/* ── Variables ─────────────────────────────── */
		:root {
			--ews-bg:          #f4f7fa;
			--ews-card:        #ffffff;
			--ews-border:      #e2e8f0;
			--ews-text:        #1a202c;
			--ews-text-muted:  #718096;
			--ews-primary:     #3b82f6;
			--ews-success:     #10b981;
			--ews-warning:     #f59e0b;
			--ews-danger:      #ef4444;
			--ews-info:        #6366f1;
			--ews-purple:      #8b5cf6;
			--ews-radius:      12px;
			--ews-radius-sm:   8px;
			--ews-shadow:      0 1px 3px rgba(0,0,0,.06), 0 1px 2px rgba(0,0,0,.04);
			--ews-shadow-lg:   0 4px 14px rgba(0,0,0,.08);
			--ews-transition:  .22s cubic-bezier(.4,0,.2,1);
		}

		.ews-dashboard-container {
			padding: 0 8px 32px;
			max-width: 1440px;
			margin: 0 auto;
		}

		/* ── Stat cards row ────────────────────────── */
		.ews-stats-row {
			display: grid;
			grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
			gap: 16px;
			margin-bottom: 24px;
		}
		.ews-stat-card {
			background: var(--ews-card);
			border-radius: var(--ews-radius);
			padding: 20px 22px;
			box-shadow: var(--ews-shadow);
			border: 1px solid var(--ews-border);
			display: flex;
			flex-direction: column;
			gap: 6px;
			transition: transform var(--ews-transition), box-shadow var(--ews-transition);
			position: relative;
			overflow: hidden;
		}
		.ews-stat-card:hover {
			transform: translateY(-2px);
			box-shadow: var(--ews-shadow-lg);
		}
		.ews-stat-card::before {
			content: '';
			position: absolute;
			top: 0; left: 0; right: 0;
			height: 4px;
			border-radius: var(--ews-radius) var(--ews-radius) 0 0;
		}
		.ews-stat-card.blue::before   { background: var(--ews-primary); }
		.ews-stat-card.green::before  { background: var(--ews-success); }
		.ews-stat-card.orange::before { background: var(--ews-warning); }
		.ews-stat-card.red::before    { background: var(--ews-danger); }
		.ews-stat-card.purple::before { background: var(--ews-purple); }
		.ews-stat-card.indigo::before { background: var(--ews-info); }

		.ews-stat-icon {
			width: 40px;
			height: 40px;
			border-radius: 10px;
			display: flex;
			align-items: center;
			justify-content: center;
			font-size: 18px;
			margin-bottom: 4px;
		}
		.ews-stat-icon.blue   { background: #dbeafe; color: var(--ews-primary); }
		.ews-stat-icon.green  { background: #d1fae5; color: var(--ews-success); }
		.ews-stat-icon.orange { background: #fef3c7; color: var(--ews-warning); }
		.ews-stat-icon.red    { background: #fee2e2; color: var(--ews-danger); }
		.ews-stat-icon.purple { background: #ede9fe; color: var(--ews-purple); }
		.ews-stat-icon.indigo { background: #e0e7ff; color: var(--ews-info); }

		.ews-stat-value {
			font-size: 28px;
			font-weight: 700;
			color: var(--ews-text);
			line-height: 1.1;
		}
		.ews-stat-label {
			font-size: 12.5px;
			color: var(--ews-text-muted);
			text-transform: uppercase;
			letter-spacing: .4px;
			font-weight: 600;
		}

		/* ── Grid layout for panels ───────────────── */
		.ews-grid {
			display: grid;
			gap: 20px;
			margin-bottom: 20px;
		}
		.ews-grid-2 { grid-template-columns: repeat(2, 1fr); }
		.ews-grid-3 { grid-template-columns: repeat(3, 1fr); }

		@media (max-width: 1024px) {
			.ews-grid-3 { grid-template-columns: 1fr 1fr; }
		}
		@media (max-width: 768px) {
			.ews-grid-2,
			.ews-grid-3 { grid-template-columns: 1fr; }
			.ews-stats-row { grid-template-columns: repeat(2, 1fr); }
		}

		/* ── Panel card ───────────────────────────── */
		.ews-panel {
			background: var(--ews-card);
			border-radius: var(--ews-radius);
			box-shadow: var(--ews-shadow);
			border: 1px solid var(--ews-border);
			overflow: hidden;
		}
		.ews-panel-header {
			padding: 16px 20px 12px;
			border-bottom: 1px solid var(--ews-border);
			display: flex;
			align-items: center;
			justify-content: space-between;
		}
		.ews-panel-title {
			font-size: 15px;
			font-weight: 700;
			color: var(--ews-text);
			display: flex;
			align-items: center;
			gap: 8px;
		}
		.ews-panel-title .indicator {
			width: 8px;
			height: 8px;
			border-radius: 50%;
			display: inline-block;
		}
		.ews-panel-body {
			padding: 16px 20px 20px;
		}

		/* ── Bar chart (pure CSS) ─────────────────── */
		.ews-bar-chart {
			display: flex;
			flex-direction: column;
			gap: 10px;
		}
		.ews-bar-row {
			display: flex;
			align-items: center;
			gap: 10px;
		}
		.ews-bar-label {
			min-width: 120px;
			font-size: 13px;
			color: var(--ews-text);
			font-weight: 500;
			white-space: nowrap;
			overflow: hidden;
			text-overflow: ellipsis;
		}
		.ews-bar-track {
			flex: 1;
			height: 26px;
			background: #f1f5f9;
			border-radius: 6px;
			overflow: hidden;
			position: relative;
		}
		.ews-bar-fill {
			height: 100%;
			border-radius: 6px;
			transition: width .6s cubic-bezier(.4,0,.2,1);
			min-width: 2px;
			display: flex;
			align-items: center;
			padding-left: 8px;
		}
		.ews-bar-fill span {
			font-size: 11px;
			font-weight: 700;
			color: #fff;
			text-shadow: 0 1px 2px rgba(0,0,0,.15);
		}
		.ews-bar-count {
			min-width: 36px;
			text-align: right;
			font-size: 13px;
			font-weight: 700;
			color: var(--ews-text);
		}

		/* ── Donut / ring (SVG based) ─────────────── */
		.ews-donut-container {
			display: flex;
			align-items: center;
			gap: 24px;
			flex-wrap: wrap;
		}
		.ews-donut-svg {
			width: 160px;
			height: 160px;
			flex-shrink: 0;
		}
		.ews-donut-legend {
			display: flex;
			flex-direction: column;
			gap: 8px;
		}
		.ews-legend-item {
			display: flex;
			align-items: center;
			gap: 8px;
			font-size: 13px;
			color: var(--ews-text);
		}
		.ews-legend-dot {
			width: 12px;
			height: 12px;
			border-radius: 3px;
			flex-shrink: 0;
		}
		.ews-legend-count {
			font-weight: 700;
			margin-left: auto;
			padding-left: 12px;
		}

		/* ── Table ────────────────────────────────── */
		.ews-table-wrap {
			overflow-x: auto;
		}
		.ews-table {
			width: 100%;
			border-collapse: separate;
			border-spacing: 0;
			font-size: 13px;
		}
		.ews-table th {
			background: #f8fafc;
			padding: 10px 14px;
			text-align: left;
			font-weight: 700;
			color: var(--ews-text-muted);
			text-transform: uppercase;
			font-size: 11px;
			letter-spacing: .5px;
			border-bottom: 2px solid var(--ews-border);
			position: sticky;
			top: 0;
			z-index: 1;
			white-space: nowrap;
		}
		.ews-table td {
			padding: 10px 14px;
			border-bottom: 1px solid #f1f5f9;
			color: var(--ews-text);
			vertical-align: middle;
		}
		.ews-table tr:hover td {
			background: #f8fafc;
		}
		.ews-table tr:last-child td {
			border-bottom: none;
		}

		/* ── Badges ───────────────────────────────── */
		.ews-badge {
			display: inline-flex;
			align-items: center;
			gap: 4px;
			padding: 3px 10px;
			border-radius: 99px;
			font-size: 11px;
			font-weight: 700;
			text-transform: uppercase;
			letter-spacing: .3px;
			white-space: nowrap;
		}
		.ews-badge.critical { background: #fee2e2; color: #991b1b; }
		.ews-badge.high     { background: #ffedd5; color: #9a3412; }
		.ews-badge.moderate { background: #fef3c7; color: #92400e; }
		.ews-badge.low      { background: #d1fae5; color: #065f46; }
		.ews-badge.climate  { background: #dbeafe; color: #1e40af; }
		.ews-badge.conflict { background: #fce7f3; color: #9d174d; }

		/* ── Timeline sparkline (CSS bar chart) ───── */
		.ews-timeline {
			display: flex;
			align-items: flex-end;
			gap: 2px;
			height: 120px;
			padding: 4px 0;
		}
		.ews-timeline-bar {
			flex: 1;
			background: var(--ews-primary);
			border-radius: 3px 3px 0 0;
			min-height: 2px;
			transition: height .5s cubic-bezier(.4,0,.2,1);
			position: relative;
			cursor: pointer;
			opacity: .75;
		}
		.ews-timeline-bar:hover {
			opacity: 1;
		}
		.ews-timeline-bar:hover::after {
			content: attr(data-tooltip);
			position: absolute;
			bottom: calc(100% + 6px);
			left: 50%;
			transform: translateX(-50%);
			background: #1e293b;
			color: #fff;
			padding: 4px 8px;
			border-radius: 6px;
			font-size: 11px;
			white-space: nowrap;
			z-index: 10;
			pointer-events: none;
		}

		/* ── Trend indicator ──────────────────────── */
		.ews-trend {
			display: inline-flex;
			align-items: center;
			gap: 3px;
			font-size: 12px;
			font-weight: 600;
		}
		.ews-trend.up   { color: var(--ews-danger); }
		.ews-trend.down { color: var(--ews-success); }

		/* ── Reporter list ────────────────────────── */
		.ews-reporter-list {
			display: flex;
			flex-direction: column;
			gap: 10px;
		}
		.ews-reporter-row {
			display: flex;
			align-items: center;
			gap: 12px;
		}
		.ews-reporter-rank {
			width: 26px;
			height: 26px;
			border-radius: 50%;
			background: #f1f5f9;
			display: flex;
			align-items: center;
			justify-content: center;
			font-size: 12px;
			font-weight: 700;
			color: var(--ews-text-muted);
			flex-shrink: 0;
		}
		.ews-reporter-rank.top { background: #fef3c7; color: #92400e; }
		.ews-reporter-info {
			flex: 1;
			min-width: 0;
		}
		.ews-reporter-name {
			font-weight: 600;
			font-size: 13px;
			color: var(--ews-text);
			white-space: nowrap;
			overflow: hidden;
			text-overflow: ellipsis;
		}
		.ews-reporter-email {
			font-size: 11px;
			color: var(--ews-text-muted);
			white-space: nowrap;
			overflow: hidden;
			text-overflow: ellipsis;
		}
		.ews-reporter-count {
			font-size: 18px;
			font-weight: 700;
			color: var(--ews-primary);
		}

		/* ── Loading skeleton ─────────────────────── */
		.ews-skeleton {
			background: linear-gradient(90deg, #f1f5f9 25%, #e2e8f0 50%, #f1f5f9 75%);
			background-size: 200% 100%;
			animation: ews-shimmer 1.5s infinite;
			border-radius: var(--ews-radius-sm);
		}
		@keyframes ews-shimmer {
			0%   { background-position: 200% 0; }
			100% { background-position: -200% 0; }
		}

		/* ── Empty state ──────────────────────────── */
		.ews-empty {
			padding: 32px;
			text-align: center;
			color: var(--ews-text-muted);
			font-size: 13px;
		}
		.ews-empty-icon {
			font-size: 36px;
			margin-bottom: 8px;
			opacity: .4;
		}

		/* ── Location table ───────────────────────── */
		.ews-location-row {
			display: flex;
			align-items: center;
			gap: 10px;
			padding: 8px 0;
			border-bottom: 1px solid #f1f5f9;
		}
		.ews-location-row:last-child { border-bottom: none; }
		.ews-location-info {
			flex: 1;
			min-width: 0;
		}
		.ews-location-site {
			font-weight: 600;
			font-size: 13px;
			color: var(--ews-text);
		}
		.ews-location-district {
			font-size: 11px;
			color: var(--ews-text-muted);
		}
		.ews-location-count {
			font-weight: 700;
			color: var(--ews-info);
			font-size: 15px;
		}

		/* ── Province severity mini-heatmap ────────── */
		.ews-heatmap-grid {
			display: grid;
			gap: 3px;
		}
		.ews-heatmap-cell {
			border-radius: 4px;
			display: flex;
			align-items: center;
			justify-content: center;
			font-size: 11px;
			font-weight: 700;
			color: #fff;
			min-height: 32px;
			transition: transform var(--ews-transition);
		}
		.ews-heatmap-cell:hover { transform: scale(1.08); }
		.ews-heatmap-cell.empty { background: #f1f5f9; color: var(--ews-text-muted); }
		.ews-heatmap-header {
			font-size: 11px;
			font-weight: 700;
			color: var(--ews-text-muted);
			text-align: center;
			padding: 4px 0;
			text-transform: uppercase;
		}
		.ews-heatmap-prov {
			font-size: 12px;
			font-weight: 600;
			color: var(--ews-text);
			display: flex;
			align-items: center;
			padding-right: 8px;
			white-space: nowrap;
			overflow: hidden;
			text-overflow: ellipsis;
		}

		/* ── Page-level link ──────────────────────── */
		.ews-link {
			color: var(--ews-primary);
			text-decoration: none;
			font-weight: 500;
			cursor: pointer;
		}
		.ews-link:hover {
			text-decoration: underline;
		}

		/* ═══════════════════════════════════════════════
		   ALL REPORTS SECTION
		   ═══════════════════════════════════════════════ */
		.ews-allreports-section {
			margin-top: 8px;
		}
		.ews-allreports-header {
			display: flex;
			align-items: center;
			justify-content: space-between;
			margin-bottom: 16px;
			flex-wrap: wrap;
			gap: 10px;
		}
		.ews-allreports-title {
			font-size: 20px;
			font-weight: 800;
			color: var(--ews-text);
			display: flex;
			align-items: center;
			gap: 8px;
		}
		.ews-allreports-count {
			background: var(--ews-primary);
			color: #fff;
			padding: 2px 10px;
			border-radius: 99px;
			font-size: 13px;
			font-weight: 700;
		}

		/* Filter bar */
		.ews-filter-bar {
			background: var(--ews-card);
			border: 1px solid var(--ews-border);
			border-radius: var(--ews-radius);
			padding: 16px 20px;
			margin-bottom: 16px;
			box-shadow: var(--ews-shadow);
		}
		.ews-filter-grid {
			display: grid;
			grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
			gap: 12px;
			align-items: end;
		}
		.ews-filter-group {
			display: flex;
			flex-direction: column;
			gap: 4px;
		}
		.ews-filter-group label {
			font-size: 11px;
			font-weight: 700;
			color: var(--ews-text-muted);
			text-transform: uppercase;
			letter-spacing: .4px;
		}
		.ews-filter-group select,
		.ews-filter-group input {
			padding: 7px 10px;
			border: 1px solid var(--ews-border);
			border-radius: var(--ews-radius-sm);
			font-size: 13px;
			color: var(--ews-text);
			background: #fff;
			transition: border-color var(--ews-transition);
			width: 100%;
			box-sizing: border-box;
		}
		.ews-filter-group select:focus,
		.ews-filter-group input:focus {
			outline: none;
			border-color: var(--ews-primary);
			box-shadow: 0 0 0 3px rgba(59,130,246,.12);
		}
		.ews-filter-actions {
			display: flex;
			gap: 8px;
			margin-top: 12px;
		}
		.ews-btn {
			padding: 8px 18px;
			border: none;
			border-radius: var(--ews-radius-sm);
			font-size: 13px;
			font-weight: 600;
			cursor: pointer;
			transition: all var(--ews-transition);
		}
		.ews-btn-primary {
			background: var(--ews-primary);
			color: #fff;
		}
		.ews-btn-primary:hover { background: #2563eb; }
		.ews-btn-secondary {
			background: #f1f5f9;
			color: var(--ews-text);
		}
		.ews-btn-secondary:hover { background: #e2e8f0; }

		/* Clickable table rows */
		.ews-table.clickable-rows tbody tr {
			cursor: pointer;
			transition: background var(--ews-transition);
		}
		.ews-table.clickable-rows tbody tr:hover td {
			background: #eef2ff;
		}

		/* Pagination */
		.ews-pagination {
			display: flex;
			align-items: center;
			justify-content: space-between;
			padding: 14px 20px;
			border-top: 1px solid var(--ews-border);
			background: #f8fafc;
			border-radius: 0 0 var(--ews-radius) var(--ews-radius);
			flex-wrap: wrap;
			gap: 8px;
		}
		.ews-pagination-info {
			font-size: 13px;
			color: var(--ews-text-muted);
		}
		.ews-pagination-buttons {
			display: flex;
			align-items: center;
			gap: 4px;
		}
		.ews-page-btn {
			padding: 6px 12px;
			border: 1px solid var(--ews-border);
			background: #fff;
			border-radius: 6px;
			font-size: 13px;
			font-weight: 600;
			color: var(--ews-text);
			cursor: pointer;
			transition: all var(--ews-transition);
		}
		.ews-page-btn:hover:not(:disabled) {
			background: var(--ews-primary);
			color: #fff;
			border-color: var(--ews-primary);
		}
		.ews-page-btn.active {
			background: var(--ews-primary);
			color: #fff;
			border-color: var(--ews-primary);
		}
		.ews-page-btn:disabled {
			opacity: .4;
			cursor: not-allowed;
		}

		/* ═══════════════════════════════════════════════
		   DETAIL MODAL
		   ═══════════════════════════════════════════════ */
		.ews-modal-overlay {
			position: fixed;
			top: 0; left: 0; right: 0; bottom: 0;
			background: rgba(0,0,0,.45);
			z-index: 1050;
			display: flex;
			align-items: center;
			justify-content: center;
			padding: 24px;
			animation: ews-fade-in .2s ease;
		}
		@keyframes ews-fade-in {
			from { opacity: 0; }
			to   { opacity: 1; }
		}
		.ews-modal {
			background: var(--ews-card);
			border-radius: 16px;
			box-shadow: 0 20px 60px rgba(0,0,0,.2);
			max-width: 720px;
			width: 100%;
			max-height: 85vh;
			overflow: hidden;
			display: flex;
			flex-direction: column;
			animation: ews-slide-up .25s ease;
		}
		@keyframes ews-slide-up {
			from { opacity: 0; transform: translateY(20px); }
			to   { opacity: 1; transform: translateY(0); }
		}
		.ews-modal-header {
			padding: 20px 24px 16px;
			border-bottom: 1px solid var(--ews-border);
			display: flex;
			align-items: center;
			justify-content: space-between;
		}
		.ews-modal-title {
			font-size: 18px;
			font-weight: 800;
			color: var(--ews-text);
		}
		.ews-modal-close {
			width: 36px;
			height: 36px;
			border: none;
			background: #f1f5f9;
			border-radius: 50%;
			font-size: 18px;
			cursor: pointer;
			display: flex;
			align-items: center;
			justify-content: center;
			color: var(--ews-text-muted);
			transition: all var(--ews-transition);
		}
		.ews-modal-close:hover {
			background: #fee2e2;
			color: var(--ews-danger);
		}
		.ews-modal-body {
			padding: 20px 24px 24px;
			overflow-y: auto;
		}
		.ews-modal-loading {
			padding: 48px;
			text-align: center;
			color: var(--ews-text-muted);
			font-size: 14px;
		}

		/* Detail grid */
		.ews-detail-grid {
			display: grid;
			grid-template-columns: 1fr 1fr;
			gap: 0;
		}
		@media (max-width: 560px) {
			.ews-detail-grid { grid-template-columns: 1fr; }
		}
		.ews-detail-item {
			padding: 10px 0;
			border-bottom: 1px solid #f1f5f9;
		}
		.ews-detail-label {
			font-size: 11px;
			font-weight: 700;
			text-transform: uppercase;
			letter-spacing: .4px;
			color: var(--ews-text-muted);
			margin-bottom: 3px;
		}
		.ews-detail-value {
			font-size: 14px;
			color: var(--ews-text);
			font-weight: 500;
			word-break: break-word;
		}
		.ews-detail-section-title {
			grid-column: 1 / -1;
			font-size: 14px;
			font-weight: 800;
			color: var(--ews-text);
			padding: 16px 0 6px;
			border-bottom: 2px solid var(--ews-border);
			display: flex;
			align-items: center;
			gap: 6px;
		}
		.ews-detail-full {
			grid-column: 1 / -1;
		}
		.ews-detail-actions {
			grid-column: 1 / -1;
			padding-top: 16px;
			display: flex;
			gap: 10px;
		}
		.ews-detail-img {
			max-width: 100%;
			max-height: 200px;
			border-radius: var(--ews-radius-sm);
			object-fit: cover;
			border: 1px solid var(--ews-border);
		}
		`;
		document.head.appendChild(style);
	}

	/* ═══════════════════════════════════════════
	   FILTERS (in frappe page header)
	   ═══════════════════════════════════════════ */
	make_filters() {
		this.page.add_field({
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_months(frappe.datetime.nowdate(), -1),
			change: () => this.refresh(),
		});
		this.page.add_field({
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.nowdate(),
			change: () => this.refresh(),
		});
		this.page.add_field({
			fieldname: "province",
			label: __("Province"),
			fieldtype: "Link",
			options: "Province",
			change: () => this.refresh(),
		});
		this.page.add_field({
			fieldname: "severity",
			label: __("Severity"),
			fieldtype: "Select",
			options: "\nCritical\nHigh\nModerate\nLow",
			change: () => this.refresh(),
		});
		this.page.add_field({
			fieldname: "report_type",
			label: __("Report Type"),
			fieldtype: "Select",
			options: "\nClimate / Water / Environment\nConflict / Social Tension",
			change: () => this.refresh(),
		});

		// Refresh button
		this.page.set_secondary_action(__("Refresh"), () => this.refresh(), "refresh");
	}

	/* ═══════════════════════════════════════════
	   LAYOUT (container)
	   ═══════════════════════════════════════════ */
	make_layout() {
		this.$container = $('<div class="ews-dashboard-container"></div>');
		$(this.page.body).append(this.$container);
	}

	/* ═══════════════════════════════════════════
	   FETCH + RENDER
	   ═══════════════════════════════════════════ */
	refresh() {
		const args = {
			from_date: this.page.fields_dict.from_date.get_value(),
			to_date: this.page.fields_dict.to_date.get_value(),
			province: this.page.fields_dict.province.get_value(),
			severity: this.page.fields_dict.severity.get_value(),
			report_type: this.page.fields_dict.report_type.get_value(),
		};

		// Show loading skeleton
		this.show_loading();

		frappe.xcall("ews.ews.page.ews_dashboard.ews_dashboard.get_dashboard_data", args).then(
			(data) => {
				this.data = data;
				this.render(data);
			},
			(err) => {
				this.$container.html(
					`<div class="ews-empty"><div class="ews-empty-icon">⚠️</div>Error loading dashboard</div>`
				);
			}
		);
	}

	show_loading() {
		let skeleton = "";
		// Stat cards skeleton
		skeleton += '<div class="ews-stats-row">';
		for (let i = 0; i < 6; i++) {
			skeleton += `<div class="ews-stat-card"><div class="ews-skeleton" style="height:24px;width:50%"></div><div class="ews-skeleton" style="height:40px;width:70%;margin-top:8px"></div><div class="ews-skeleton" style="height:14px;width:60%;margin-top:6px"></div></div>`;
		}
		skeleton += "</div>";
		// Panels skeleton
		skeleton += '<div class="ews-grid ews-grid-2">';
		for (let i = 0; i < 4; i++) {
			skeleton += `<div class="ews-panel"><div class="ews-panel-header"><div class="ews-skeleton" style="height:16px;width:40%"></div></div><div class="ews-panel-body"><div class="ews-skeleton" style="height:140px;width:100%"></div></div></div>`;
		}
		skeleton += "</div>";
		this.$container.html(skeleton);
	}

	/* ═══════════════════════════════════════════
	   RENDER ALL
	   ═══════════════════════════════════════════ */
	render(d) {
		let html = "";

		// 1. Headline stat cards
		html += this.render_stat_cards(d);

		// 2. Timeline + Severity donut
		html += '<div class="ews-grid ews-grid-2">';
		html += this.render_panel("📈 Reports Timeline (Last 30 Days)", this.render_timeline(d.timeline), "blue");
		html += this.render_panel("🎯 Severity Distribution", this.render_severity_donut(d.severity_breakdown, d.total_reports), "red");
		html += "</div>";

		// 3. Report type + Frequency
		html += '<div class="ews-grid ews-grid-2">';
		html += this.render_panel("📊 Report Type Breakdown", this.render_bar_chart(d.report_type_breakdown, "report_type", this.get_report_type_colors()), "indigo");
		html += this.render_panel("🔄 Frequency Distribution", this.render_bar_chart(d.frequency_breakdown, "frequency", this.get_frequency_colors()), "purple");
		html += "</div>";

		// 4. Province breakdown + Timing
		html += '<div class="ews-grid ews-grid-2">';
		html += this.render_panel("🏛️ Reports by Province", this.render_bar_chart(d.province_breakdown, "province", this.get_province_colors()), "green");
		html += this.render_panel("⏱️ Report Timing", this.render_bar_chart(d.timing_breakdown, "report_timing", this.get_timing_colors()), "orange");
		html += "</div>";

		// 5. Climate + Conflict indicators
		html += '<div class="ews-grid ews-grid-2">';
		html += this.render_panel("🌤️ Climate Indicators", this.render_bar_chart(d.climate_indicators, "indicator", this.get_climate_colors()), "blue");
		html += this.render_panel("⚔️ Conflict Indicators", this.render_bar_chart(d.conflict_indicators, "indicator", this.get_conflict_colors()), "red");
		html += "</div>";

		// 6. Top reporters + Locations
		html += '<div class="ews-grid ews-grid-2">';
		html += this.render_panel("👤 Top Reporters", this.render_reporters(d.top_reporters), "purple");
		html += this.render_panel("📍 Top Locations", this.render_locations(d.location_breakdown), "green");
		html += "</div>";

		// 7. Province x Severity heatmap
		html += '<div class="ews-grid">';
		html += this.render_panel("🗺️ Province × Severity Heatmap", this.render_heatmap(d.province_severity, d.province_breakdown), "indigo");
		html += "</div>";

		// 8. All Reports section placeholder
		html += '<div id="ews-all-reports-section" class="ews-allreports-section"></div>';

		this.$container.html(html);

		// Load the all-reports table independently
		this.load_all_reports();
	}

	/* ═══════════════════════════════════════════
	   STAT CARDS
	   ═══════════════════════════════════════════ */
	render_stat_cards(d) {
		const cards = [
			{ icon: "📊", label: __("Total Reports"), value: d.total_reports, color: "blue" },
			{ icon: "📅", label: __("Today"), value: d.reports_today, color: "green" },
			{ icon: "📆", label: __("This Week"), value: d.reports_this_week, color: "indigo" },
			{ icon: "🗓️", label: __("This Month"), value: d.reports_this_month, color: "purple" },
			{ icon: "🔴", label: __("Critical"), value: d.critical_count, color: "red" },
			{ icon: "🟠", label: __("High"), value: d.high_count, color: "orange" },
			{ icon: "👁️", label: __("Unique Reporters"), value: d.unique_observers, color: "indigo" },
		];

		let html = '<div class="ews-stats-row">';
		for (const c of cards) {
			html += `
			<div class="ews-stat-card ${c.color}">
				<div class="ews-stat-icon ${c.color}">${c.icon}</div>
				<div class="ews-stat-value">${this.format_number(c.value)}</div>
				<div class="ews-stat-label">${c.label}</div>
			</div>`;
		}
		html += "</div>";
		return html;
	}

	/* ═══════════════════════════════════════════
	   TIMELINE (bar sparkline)
	   ═══════════════════════════════════════════ */
	render_timeline(timeline) {
		if (!timeline || !timeline.length) return this.empty_state("No timeline data");

		const maxVal = Math.max(...timeline.map((t) => t.count), 1);
		let html = '<div class="ews-timeline">';
		for (const t of timeline) {
			const pct = (t.count / maxVal) * 100;
			const dateStr = frappe.datetime.str_to_user(t.date);
			html += `<div class="ews-timeline-bar"
				style="height:${Math.max(pct, 3)}%"
				data-tooltip="${dateStr}: ${t.count} reports"></div>`;
		}
		html += "</div>";
		// labels: first & last date
		html += `<div style="display:flex;justify-content:space-between;font-size:11px;color:var(--ews-text-muted);margin-top:4px">
			<span>${frappe.datetime.str_to_user(timeline[0].date)}</span>
			<span>${frappe.datetime.str_to_user(timeline[timeline.length - 1].date)}</span>
		</div>`;
		return html;
	}

	/* ═══════════════════════════════════════════
	   SEVERITY DONUT (SVG)
	   ═══════════════════════════════════════════ */
	render_severity_donut(breakdown, total) {
		if (!breakdown || !breakdown.length) return this.empty_state("No data");

		const colors = {
			Critical: "#ef4444",
			High: "#f97316",
			Moderate: "#f59e0b",
			Low: "#10b981",
		};

		// Build SVG donut
		const cx = 80, cy = 80, r = 60;
		const circumference = 2 * Math.PI * r;
		let offset = 0;
		let arcs = "";
		let legend = "";

		for (const item of breakdown) {
			const pct = total > 0 ? item.count / total : 0;
			const dash = pct * circumference;
			const color = colors[item.severity] || "#94a3b8";
			arcs += `<circle cx="${cx}" cy="${cy}" r="${r}"
				fill="none" stroke="${color}" stroke-width="22"
				stroke-dasharray="${dash} ${circumference - dash}"
				stroke-dashoffset="${-offset}"
				transform="rotate(-90 ${cx} ${cy})"
				style="transition: stroke-dasharray .6s ease" />`;
			offset += dash;

			legend += `
			<div class="ews-legend-item">
				<span class="ews-legend-dot" style="background:${color}"></span>
				<span>${item.severity || "Unknown"}</span>
				<span class="ews-legend-count">${item.count} <span style="font-weight:400;color:var(--ews-text-muted)">(${(pct * 100).toFixed(1)}%)</span></span>
			</div>`;
		}

		return `
		<div class="ews-donut-container">
			<svg class="ews-donut-svg" viewBox="0 0 160 160">
				<circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="#f1f5f9" stroke-width="22"/>
				${arcs}
				<text x="${cx}" y="${cy - 6}" text-anchor="middle" font-size="22" font-weight="700" fill="var(--ews-text)">${this.format_number(total)}</text>
				<text x="${cx}" y="${cy + 12}" text-anchor="middle" font-size="10" fill="var(--ews-text-muted)">Total</text>
			</svg>
			<div class="ews-donut-legend">${legend}</div>
		</div>`;
	}

	/* ═══════════════════════════════════════════
	   BAR CHART (horizontal)
	   ═══════════════════════════════════════════ */
	render_bar_chart(data, labelKey, colorMap) {
		if (!data || !data.length) return this.empty_state("No data");

		const maxVal = Math.max(...data.map((d) => d.count), 1);
		let html = '<div class="ews-bar-chart">';
		for (let i = 0; i < data.length; i++) {
			const item = data[i];
			const label = item[labelKey] || "Unknown";
			const pct = (item.count / maxVal) * 100;
			const color = colorMap[i % colorMap.length];
			html += `
			<div class="ews-bar-row">
				<div class="ews-bar-label" title="${frappe.utils.escape_html(label)}">${frappe.utils.escape_html(label)}</div>
				<div class="ews-bar-track">
					<div class="ews-bar-fill" style="width:${Math.max(pct, 4)}%;background:${color}">
						${pct > 18 ? `<span>${item.count}</span>` : ""}
					</div>
				</div>
				<div class="ews-bar-count">${item.count}</div>
			</div>`;
		}
		html += "</div>";
		return html;
	}

	/* ═══════════════════════════════════════════
	   TOP REPORTERS
	   ═══════════════════════════════════════════ */
	render_reporters(reporters) {
		if (!reporters || !reporters.length) return this.empty_state("No reporters");

		let html = '<div class="ews-reporter-list">';
		reporters.forEach((r, i) => {
			html += `
			<div class="ews-reporter-row">
				<div class="ews-reporter-rank ${i < 3 ? "top" : ""}">${i + 1}</div>
				<div class="ews-reporter-info">
					<div class="ews-reporter-name">${frappe.utils.escape_html(r.full_name)}</div>
					<div class="ews-reporter-email">${frappe.utils.escape_html(r.observer)}</div>
				</div>
				<div class="ews-reporter-count">${r.report_count}</div>
			</div>`;
		});
		html += "</div>";
		return html;
	}

	/* ═══════════════════════════════════════════
	   LOCATIONS
	   ═══════════════════════════════════════════ */
	render_locations(locations) {
		if (!locations || !locations.length) return this.empty_state("No location data");

		let html = '<div>';
		locations.slice(0, 10).forEach((loc) => {
			html += `
			<div class="ews-location-row">
				<div class="ews-location-info">
					<div class="ews-location-site">${frappe.utils.escape_html(loc.administrative_site)}</div>
					<div class="ews-location-district">${frappe.utils.escape_html(loc.district)}</div>
				</div>
				<div class="ews-location-count">${loc.count}</div>
			</div>`;
		});
		html += "</div>";
		return html;
	}

	/* ═══════════════════════════════════════════
	   PROVINCE x SEVERITY HEATMAP
	   ═══════════════════════════════════════════ */
	render_heatmap(data, provinces) {
		if (!data || !data.length) return this.empty_state("No data for heatmap");

		const severities = ["Critical", "High", "Moderate", "Low"];
		const sevColors = {
			Critical: { bg: "#ef4444", scale: [0.2, 0.5, 0.8, 1] },
			High: { bg: "#f97316", scale: [0.2, 0.5, 0.8, 1] },
			Moderate: { bg: "#f59e0b", scale: [0.2, 0.5, 0.8, 1] },
			Low: { bg: "#10b981", scale: [0.2, 0.5, 0.8, 1] },
		};

		// Build lookup: province → severity → count
		const lookup = {};
		const provList = [];
		for (const row of data) {
			if (!lookup[row.province]) {
				lookup[row.province] = {};
				provList.push(row.province);
			}
			lookup[row.province][row.severity] = row.count;
		}

		const maxCount = Math.max(...data.map((r) => r.count), 1);

		let cols = severities.length + 1; // +1 for province label column
		let html = `<div class="ews-heatmap-grid" style="grid-template-columns: 140px repeat(${severities.length}, 1fr)">`;

		// Header row
		html += `<div class="ews-heatmap-header"></div>`;
		for (const sev of severities) {
			html += `<div class="ews-heatmap-header">${sev}</div>`;
		}

		// Data rows
		for (const prov of provList) {
			html += `<div class="ews-heatmap-prov" title="${frappe.utils.escape_html(prov)}">${frappe.utils.escape_html(prov)}</div>`;
			for (const sev of severities) {
				const count = (lookup[prov] && lookup[prov][sev]) || 0;
				if (count > 0) {
					const intensity = Math.min(0.3 + (count / maxCount) * 0.7, 1);
					const color = sevColors[sev]?.bg || "#94a3b8";
					html += `<div class="ews-heatmap-cell" style="background:${color};opacity:${intensity}" title="${prov} - ${sev}: ${count}">${count}</div>`;
				} else {
					html += `<div class="ews-heatmap-cell empty">–</div>`;
				}
			}
		}
		html += "</div>";
		return html;
	}

	/* ═══════════════════════════════════════════
	   RECENT REPORTS TABLE
	   ═══════════════════════════════════════════ */
	render_recent_table(reports) {
		if (!reports || !reports.length) return this.empty_state("No recent reports");

		let html = '<div class="ews-table-wrap"><table class="ews-table"><thead><tr>';
		html += `<th>${__("Report")}</th>`;
		html += `<th>${__("Observer")}</th>`;
		html += `<th>${__("Province")}</th>`;
		html += `<th>${__("Type")}</th>`;
		html += `<th>${__("Severity")}</th>`;
		html += `<th>${__("Timing")}</th>`;
		html += `<th>${__("Date")}</th>`;
		html += "</tr></thead><tbody>";

		for (const r of reports) {
			const sevClass = (r.severity || "").toLowerCase();
			const typeClass = (r.report_type || "").includes("Climate") ? "climate" : "conflict";
			html += `<tr>
				<td><a class="ews-link" href="/app/ews-report/${r.name}">${frappe.utils.escape_html(r.name)}</a></td>
				<td>${frappe.utils.escape_html(r.observer_name || r.observer || "")}</td>
				<td>${frappe.utils.escape_html(r.province || "")}</td>
				<td><span class="ews-badge ${typeClass}">${frappe.utils.escape_html(r.report_type || "N/A")}</span></td>
				<td><span class="ews-badge ${sevClass}">${frappe.utils.escape_html(r.severity || "N/A")}</span></td>
				<td>${frappe.utils.escape_html(r.report_timing || "")}</td>
				<td>${r.creation ? frappe.datetime.str_to_user(r.creation) : ""}</td>
			</tr>`;
		}
		html += "</tbody></table></div>";
		return html;
	}

	/* ═══════════════════════════════════════════
	   HELPERS
	   ═══════════════════════════════════════════ */
	render_panel(title, content, accent) {
		const dotColor = {
			blue: "var(--ews-primary)",
			green: "var(--ews-success)",
			orange: "var(--ews-warning)",
			red: "var(--ews-danger)",
			purple: "var(--ews-purple)",
			indigo: "var(--ews-info)",
		};
		return `
		<div class="ews-panel">
			<div class="ews-panel-header">
				<div class="ews-panel-title">
					<span class="indicator" style="background:${dotColor[accent] || dotColor.blue}"></span>
					${title}
				</div>
			</div>
			<div class="ews-panel-body">${content}</div>
		</div>`;
	}

	empty_state(message) {
		return `<div class="ews-empty"><div class="ews-empty-icon">📭</div>${message}</div>`;
	}

	format_number(n) {
		if (n == null) return "0";
		return Number(n).toLocaleString();
	}

	// ── Color palettes ──────────────────────────
	get_report_type_colors() {
		return ["#3b82f6", "#ec4899", "#8b5cf6", "#10b981", "#f59e0b"];
	}
	get_frequency_colors() {
		return ["#6366f1", "#8b5cf6", "#a78bfa", "#c4b5fd"];
	}
	get_province_colors() {
		return ["#10b981", "#059669", "#34d399", "#6ee7b7", "#a7f3d0", "#d1fae5", "#047857", "#065f46"];
	}
	get_timing_colors() {
		return ["#f97316", "#fb923c", "#fdba74", "#fed7aa"];
	}
	get_climate_colors() {
		return ["#3b82f6", "#60a5fa", "#93c5fd", "#bfdbfe", "#2563eb", "#1d4ed8", "#1e40af"];
	}
	get_conflict_colors() {
		return ["#ef4444", "#f87171", "#fca5a5", "#fecaca", "#dc2626", "#b91c1c"];
	}

	/* ═══════════════════════════════════════════════════════════
	   ALL REPORTS – FULL TABLE WITH FILTERS & PAGINATION
	   ═══════════════════════════════════════════════════════════ */

	load_all_reports() {
		const section = this.$container.find("#ews-all-reports-section");
		section.html(`
			<div class="ews-panel" style="border:none;box-shadow:none;background:transparent">
				<div class="ews-panel-body" style="padding:0">
					<div class="ews-skeleton" style="height:300px;width:100%"></div>
				</div>
			</div>
		`);

		const args = {
			page: this.all_reports_page,
			page_size: this.all_reports_page_size,
			...this.all_reports_filters,
		};

		frappe.xcall("ews.ews.page.ews_dashboard.ews_dashboard.get_all_reports", args).then(
			(data) => {
				this.all_reports_data = data;
				this.render_all_reports_section(data);
			},
			() => {
				section.html(this.empty_state("Error loading reports"));
			}
		);
	}

	render_all_reports_section(d) {
		const section = this.$container.find("#ews-all-reports-section");
		let html = "";

		// Header
		html += `
		<div class="ews-allreports-header">
			<div class="ews-allreports-title">
				📋 ${__("All Reports")}
				<span class="ews-allreports-count">${this.format_number(d.total)}</span>
			</div>
		</div>`;

		// Filter bar
		html += this.render_all_reports_filters(d);

		// Table
		html += '<div class="ews-panel">';
		html += this.render_all_reports_table(d.reports);
		html += this.render_pagination(d);
		html += '</div>';

		section.html(html);

		// Wire events
		this.bind_all_reports_events();
	}

	render_all_reports_filters(d) {
		const f = this.all_reports_filters;

		const _opts = (list, selected) => {
			let h = '<option value="">All</option>';
			(list || []).forEach((v) => {
				h += `<option value="${frappe.utils.escape_html(v)}" ${v === selected ? 'selected' : ''}>${frappe.utils.escape_html(v)}</option>`;
			});
			return h;
		};

		return `
		<div class="ews-filter-bar">
			<div class="ews-filter-grid">
				<div class="ews-filter-group">
					<label>${__("Search")}</label>
					<input type="text" id="ews-ar-search" placeholder="${__("Search reports...")}" value="${frappe.utils.escape_html(f.search || '')}">
				</div>
				<div class="ews-filter-group">
					<label>${__("Province")}</label>
					<select id="ews-ar-province">${_opts(d.provinces_list, f.province)}</select>
				</div>
				<div class="ews-filter-group">
					<label>${__("Severity")}</label>
					<select id="ews-ar-severity">${_opts(d.severity_options, f.severity)}</select>
				</div>
				<div class="ews-filter-group">
					<label>${__("Report Type")}</label>
					<select id="ews-ar-report_type">${_opts(d.report_type_options, f.report_type)}</select>
				</div>
				<div class="ews-filter-group">
					<label>${__("Timing")}</label>
					<select id="ews-ar-report_timing">${_opts(d.timing_options, f.report_timing)}</select>
				</div>
				<div class="ews-filter-group">
					<label>${__("Frequency")}</label>
					<select id="ews-ar-frequency">${_opts(d.frequency_options, f.frequency)}</select>
				</div>
				<div class="ews-filter-group">
					<label>${__("Observer")}</label>
					<select id="ews-ar-observer">${_opts(d.observers_list, f.observer)}</select>
				</div>
				<div class="ews-filter-group">
					<label>${__("Admin Site")}</label>
					<select id="ews-ar-admin_site">${_opts(d.admin_sites_list, f.administrative_site)}</select>
				</div>
				<div class="ews-filter-group">
					<label>${__("District")}</label>
					<select id="ews-ar-district">${_opts(d.districts_list, f.district)}</select>
				</div>
				<div class="ews-filter-group">
					<label>${__("Climate Indicator")}</label>
					<select id="ews-ar-climate">${_opts(d.climate_list, f.climate_indicators)}</select>
				</div>
				<div class="ews-filter-group">
					<label>${__("Conflict Indicator")}</label>
					<select id="ews-ar-conflict">${_opts(d.conflict_list, f.conflict_indicators)}</select>
				</div>
				<div class="ews-filter-group">
					<label>${__("From Date")}</label>
					<input type="date" id="ews-ar-from_date" value="${f.from_date || ''}">
				</div>
				<div class="ews-filter-group">
					<label>${__("To Date")}</label>
					<input type="date" id="ews-ar-to_date" value="${f.to_date || ''}">
				</div>
			</div>
			<div class="ews-filter-actions">
				<button class="ews-btn ews-btn-primary" id="ews-ar-apply">
					🔍 ${__("Apply Filters")}
				</button>
				<button class="ews-btn ews-btn-secondary" id="ews-ar-clear">
					✕ ${__("Clear")}
				</button>
			</div>
		</div>`;
	}

	render_all_reports_table(reports) {
		if (!reports || !reports.length) {
			return `<div class="ews-panel-body">${this.empty_state("No reports match the current filters")}</div>`;
		}

		let html = '<div class="ews-table-wrap"><table class="ews-table clickable-rows" id="ews-ar-table"><thead><tr>';
		html += `<th>${__("Report")}</th>`;
		html += `<th>${__("Observer")}</th>`;
		html += `<th>${__("Province")}</th>`;
		html += `<th>${__("Admin Site")}</th>`;
		html += `<th>${__("District")}</th>`;
		html += `<th>${__("Type")}</th>`;
		html += `<th>${__("Severity")}</th>`;
		html += `<th>${__("Timing")}</th>`;
		html += `<th>${__("Frequency")}</th>`;
		html += `<th>${__("Date")}</th>`;
		html += "</tr></thead><tbody>";

		for (const r of reports) {
			const sevClass = (r.severity || "").toLowerCase();
			const typeClass = (r.report_type || "").includes("Climate") ? "climate" : "conflict";
			html += `<tr data-report="${frappe.utils.escape_html(r.name)}">
				<td><span class="ews-link">${frappe.utils.escape_html(r.name)}</span></td>
				<td>${frappe.utils.escape_html(r.observer_name || r.observer || "")}</td>
				<td>${frappe.utils.escape_html(r.province || "")}</td>
				<td>${frappe.utils.escape_html(r.administrative_site || "")}</td>
				<td>${frappe.utils.escape_html(r.district || "")}</td>
				<td><span class="ews-badge ${typeClass}">${frappe.utils.escape_html(this._short_type(r.report_type))}</span></td>
				<td><span class="ews-badge ${sevClass}">${frappe.utils.escape_html(r.severity || "N/A")}</span></td>
				<td>${frappe.utils.escape_html(this._short_timing(r.report_timing))}</td>
				<td>${frappe.utils.escape_html(this._short_freq(r.frequency))}</td>
				<td style="white-space:nowrap">${r.creation ? frappe.datetime.str_to_user(r.creation) : ""}</td>
			</tr>`;
		}
		html += "</tbody></table></div>";
		return html;
	}

	_short_type(t) {
		if (!t) return "N/A";
		return t.includes("Climate") ? "Climate" : "Conflict";
	}
	_short_timing(t) {
		if (!t) return "";
		return t.includes("Ongoing") ? "Ongoing" : "Forecasted";
	}
	_short_freq(f) {
		if (!f) return "";
		if (f.includes("Rare")) return "Rare";
		if (f.includes("Occasionally")) return "Occasional";
		return "Constant";
	}

	render_pagination(d) {
		const { page, total_pages, total, page_size } = d;
		const from = ((page - 1) * page_size) + 1;
		const to = Math.min(page * page_size, total);

		let btns = "";
		btns += `<button class="ews-page-btn" data-page="1" ${page === 1 ? 'disabled' : ''}>«</button>`;
		btns += `<button class="ews-page-btn" data-page="${page - 1}" ${page === 1 ? 'disabled' : ''}>‹</button>`;

		// Show up to 5 page numbers around current
		let start = Math.max(1, page - 2);
		let end = Math.min(total_pages, page + 2);
		if (start > 1) btns += `<span style="padding:0 4px;color:var(--ews-text-muted)">…</span>`;
		for (let p = start; p <= end; p++) {
			btns += `<button class="ews-page-btn ${p === page ? 'active' : ''}" data-page="${p}">${p}</button>`;
		}
		if (end < total_pages) btns += `<span style="padding:0 4px;color:var(--ews-text-muted)">…</span>`;

		btns += `<button class="ews-page-btn" data-page="${page + 1}" ${page === total_pages ? 'disabled' : ''}>›</button>`;
		btns += `<button class="ews-page-btn" data-page="${total_pages}" ${page === total_pages ? 'disabled' : ''}>»</button>`;

		return `
		<div class="ews-pagination">
			<div class="ews-pagination-info">
				${__("Showing")} <strong>${from}–${to}</strong> ${__("of")} <strong>${this.format_number(total)}</strong> ${__("reports")}
			</div>
			<div class="ews-pagination-buttons">${btns}</div>
		</div>`;
	}

	bind_all_reports_events() {
		const self = this;

		// Apply filters
		this.$container.find("#ews-ar-apply").on("click", () => {
			self.all_reports_filters = self._collect_ar_filters();
			self.all_reports_page = 1;
			self.load_all_reports();
		});

		// Clear filters
		this.$container.find("#ews-ar-clear").on("click", () => {
			self.all_reports_filters = {};
			self.all_reports_page = 1;
			self.load_all_reports();
		});

		// Search on Enter
		this.$container.find("#ews-ar-search").on("keydown", (e) => {
			if (e.key === "Enter") {
				self.all_reports_filters = self._collect_ar_filters();
				self.all_reports_page = 1;
				self.load_all_reports();
			}
		});

		// Pagination
		this.$container.find(".ews-page-btn").on("click", function () {
			const p = parseInt($(this).data("page"));
			if (p && p !== self.all_reports_page) {
				self.all_reports_page = p;
				self.load_all_reports();
				// Scroll to all-reports section
				self.$container.find("#ews-all-reports-section")[0]?.scrollIntoView({ behavior: 'smooth', block: 'start' });
			}
		});

		// Row click → detail popup
		this.$container.find("#ews-ar-table tbody tr").on("click", function () {
			const reportName = $(this).data("report");
			if (reportName) self.show_report_detail(reportName);
		});
	}

	_collect_ar_filters() {
		return {
			search: this.$container.find("#ews-ar-search").val() || "",
			province: this.$container.find("#ews-ar-province").val() || "",
			severity: this.$container.find("#ews-ar-severity").val() || "",
			report_type: this.$container.find("#ews-ar-report_type").val() || "",
			report_timing: this.$container.find("#ews-ar-report_timing").val() || "",
			frequency: this.$container.find("#ews-ar-frequency").val() || "",
			observer: this.$container.find("#ews-ar-observer").val() || "",
			administrative_site: this.$container.find("#ews-ar-admin_site").val() || "",
			district: this.$container.find("#ews-ar-district").val() || "",
			climate_indicators: this.$container.find("#ews-ar-climate").val() || "",
			conflict_indicators: this.$container.find("#ews-ar-conflict").val() || "",
			from_date: this.$container.find("#ews-ar-from_date").val() || "",
			to_date: this.$container.find("#ews-ar-to_date").val() || "",
		};
	}

	/* ═══════════════════════════════════════════════════════════
	   REPORT DETAIL POPUP
	   ═══════════════════════════════════════════════════════════ */

	show_report_detail(reportName) {
		// Create overlay
		const $overlay = $(`
			<div class="ews-modal-overlay" id="ews-detail-modal">
				<div class="ews-modal">
					<div class="ews-modal-header">
						<div class="ews-modal-title">📄 ${frappe.utils.escape_html(reportName)}</div>
						<button class="ews-modal-close" id="ews-modal-close">✕</button>
					</div>
					<div class="ews-modal-body">
						<div class="ews-modal-loading">
							<div class="ews-skeleton" style="height:200px;width:100%"></div>
						</div>
					</div>
				</div>
			</div>
		`);

		$("body").append($overlay);

		// Close handlers
		const close = () => $overlay.remove();
		$overlay.find("#ews-modal-close").on("click", close);
		$overlay.on("click", (e) => {
			if ($(e.target).hasClass("ews-modal-overlay")) close();
		});
		$(document).one("keydown.ews-modal", (e) => {
			if (e.key === "Escape") close();
		});

		// Fetch detail
		frappe.xcall("ews.ews.page.ews_dashboard.ews_dashboard.get_report_detail", {
			report_name: reportName,
		}).then(
			(r) => {
				$overlay.find(".ews-modal-body").html(this.render_report_detail(r));
			},
			() => {
				$overlay.find(".ews-modal-body").html(
					`<div class="ews-empty">Error loading report details</div>`
				);
			}
		);
	}

	render_report_detail(r) {
		const sevClass = (r.severity || "").toLowerCase();
		const typeClass = (r.report_type || "").includes("Climate") ? "climate" : "conflict";

		const _row = (label, value, opts = {}) => {
			if (!value && !opts.showEmpty) return "";
			const cls = opts.full ? "ews-detail-item ews-detail-full" : "ews-detail-item";
			const valHtml = opts.badge
				? `<span class="ews-badge ${opts.badgeClass || ''}">${frappe.utils.escape_html(value || 'N/A')}</span>`
				: `<div class="ews-detail-value">${frappe.utils.escape_html(value || '—')}</div>`;
			return `<div class="${cls}"><div class="ews-detail-label">${label}</div>${valHtml}</div>`;
		};

		const _section = (icon, title) => {
			return `<div class="ews-detail-section-title">${icon} ${title}</div>`;
		};

		let html = '<div class="ews-detail-grid">';

		// ── Location Info ──
		html += _section("📍", __("Location Information"));
		html += _row(__("Observer"), r.observer_name || r.observer);
		html += _row(__("Province"), r.province);
		html += _row(__("Administrative Site"), r.administrative_site);
		html += _row(__("District"), r.district);
		html += _row(__("Latitude"), r.latitude ? String(r.latitude) : null);
		html += _row(__("Longitude"), r.longitude ? String(r.longitude) : null);
		html += _row(__("Altitude"), r.altitude ? String(r.altitude) : null);
		html += _row(__("Accuracy"), r.accuracy ? String(r.accuracy) : null);

		// ── Incident Information ──
		html += _section("⚡", __("Incident Information"));
		html += _row(__("Report Type"), r.report_type, { badge: true, badgeClass: typeClass });
		html += _row(__("Severity"), r.severity, { badge: true, badgeClass: sevClass });
		html += _row(__("AI Severity"), r.ai_severity, { badge: true, badgeClass: (r.ai_severity || "").toLowerCase() });
		html += _row(__("Report Timing"), r.report_timing);
		html += _row(__("Frequency"), r.frequency);

		if (r.report_type && r.report_type.includes("Climate")) {
			html += _row(__("Climate Indicator"), r.climate_indicators);
			html += _row(__("Climate Standard"), r.standard_label || r.standard);
			html += _row(__("Affected Groups"), r.affected_groups);
		} else if (r.report_type && r.report_type.includes("Conflict")) {
			html += _row(__("Conflict Indicator"), r.conflict_indicators);
			html += _row(__("Conflict Threshold"), r.conflict_threshold_label || r.conflict_threshold);
			html += _row(__("Participated Groups"), r.participated_groups);
		}
		html += _row(__("Most Affected Groups"), r.most_affected_groups);

		// ── Extra Details ──
		if (r.extra_details) {
			html += _section("📝", __("Extra Details"));
			html += `<div class="ews-detail-item ews-detail-full">
				<div class="ews-detail-value" style="white-space:pre-wrap;background:#f8fafc;padding:12px;border-radius:8px;font-size:13px">${frappe.utils.escape_html(r.extra_details)}</div>
			</div>`;
		}

		// ── Attachments ──
		if (r.image || r.image_2 || r.audio) {
			html += _section("📎", __("Attachments"));
			if (r.image) {
				html += `<div class="ews-detail-item"><div class="ews-detail-label">${__("Image 1")}</div><img class="ews-detail-img" src="${r.image}" alt="Image 1"></div>`;
			}
			if (r.image_2) {
				html += `<div class="ews-detail-item"><div class="ews-detail-label">${__("Image 2")}</div><img class="ews-detail-img" src="${r.image_2}" alt="Image 2"></div>`;
			}
			if (r.audio) {
				html += `<div class="ews-detail-item ews-detail-full"><div class="ews-detail-label">${__("Audio")}</div><audio controls src="${r.audio}" style="width:100%;margin-top:4px"></audio></div>`;
			}
		}

		// ── Metadata ──
		html += _section("🕐", __("Metadata"));
		html += _row(__("Created"), r.creation ? frappe.datetime.str_to_user(r.creation) : null);
		html += _row(__("Timestamp"), r.timestamp ? frappe.datetime.str_to_user(r.timestamp) : null);
		html += _row(__("Report ID"), r.name);

		// ── Actions ──
		html += `<div class="ews-detail-actions">
			<a class="ews-btn ews-btn-primary" href="/app/ews-report/${r.name}" target="_blank">
				↗ ${__("Open Full Report")}
			</a>
		</div>`;

		html += "</div>";
		return html;
	}
}