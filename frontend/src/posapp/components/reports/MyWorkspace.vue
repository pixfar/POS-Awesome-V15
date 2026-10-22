<template>
	<div class="pa-0 h-100 invoice-shell pos-list-page erp-reports-page">
		<v-card flat class="invoice-section-card pos-themed-card erp-reports-card">
			<div v-if="!canAccess" class="pos-list-empty">
				<v-icon size="48" color="error" class="pos-list-empty__icon">mdi-lock-outline</v-icon>
				<h4 class="pos-list-empty__title">{{ __("Not permitted") }}</h4>
				<p class="pos-list-empty__subtitle">{{ __("My Workspace is available to administrators only.") }}</p>
			</div>
			<div v-else class="erp-reports-groups">
				<section v-for="group in groups" :key="group.title" class="erp-reports-group">
					<div class="erp-reports-group__header">
						<v-icon size="20" class="mr-2">{{ group.icon }}</v-icon>
						<h4 class="erp-reports-group__title">{{ __(group.title) }}</h4>
					</div>
					<div class="erp-reports-grid">
						<button
							v-for="doctype in group.doctypes"
							:key="doctype.name"
							type="button"
							class="erp-report-card"
							@click="openDoctype(doctype)"
						>
							<div class="erp-report-card__icon">
								<v-icon size="22">{{ doctype.icon }}</v-icon>
							</div>
							<div class="erp-report-card__body">
								<p class="erp-report-card__title">{{ __(doctype.name) }}</p>
							</div>
							<v-icon size="18" class="erp-report-card__arrow">mdi-arrow-right</v-icon>
						</button>
					</div>
				</section>
			</div>
		</v-card>
	</div>
</template>

<script setup>
import { isFundTransferManager } from "../../utils/posWarehouseAccess";

const __ = window.__ || ((text) => text);

// Admin-only shortcuts into the ERPNext desk list of each doctype -- same
// full-page hand-off as the Reports page's cards. Access is also enforced by
// the doctypes' own permissions once the desk loads.
const canAccess = isFundTransferManager();

const groups = [
	{
		title: "Users & Permissions",
		icon: "mdi-shield-account-outline",
		doctypes: [
			{ name: "User", icon: "mdi-account-outline" },
			{ name: "User Permission", icon: "mdi-account-key-outline" },
			// Desk page, not a DocType — route is /app/permission-manager.
			{
				name: "Role Permissions Manager",
				icon: "mdi-shield-key-outline",
				route: "/app/permission-manager",
			},
			{ name: "POS Profile", icon: "mdi-cash-register" },
		],
	},
	{
		title: "Masters",
		icon: "mdi-database-outline",
		doctypes: [
			{ name: "Item", icon: "mdi-package-variant" },
			{ name: "Item Group", icon: "mdi-shape-outline" },
			{ name: "Warehouse", icon: "mdi-warehouse" },
			{ name: "Customer", icon: "mdi-account-group-outline" },
			{ name: "Supplier", icon: "mdi-truck-outline" },
		],
	},
	{
		title: "Employees & Attendance",
		icon: "mdi-account-tie-outline",
		doctypes: [
			{ name: "Employee", icon: "mdi-account-tie" },
			{ name: "Employee Checkin", icon: "mdi-fingerprint" },
			{ name: "Employee Advance", icon: "mdi-cash-fast" },
			{ name: "Leave Application", icon: "mdi-calendar-remove-outline" },
			{ name: "Leave Allocation", icon: "mdi-calendar-plus" },
			{ name: "Attendance", icon: "mdi-calendar-check-outline" },
		],
	},
	{
		title: "Payroll",
		icon: "mdi-cash-multiple",
		doctypes: [
			{ name: "Salary Component", icon: "mdi-puzzle-outline" },
			{ name: "Salary Structure", icon: "mdi-sitemap-outline" },
			{ name: "Salary Structure Assignment", icon: "mdi-account-cash-outline" },
			{ name: "Payroll Entry", icon: "mdi-cash-register" },
			{ name: "Salary Slip", icon: "mdi-receipt-text-outline" },
		],
	},
	{
		title: "Tools",
		icon: "mdi-tools",
		doctypes: [{ name: "Data Import", icon: "mdi-database-import-outline" }],
	},
	{
		title: "Accounts",
		icon: "mdi-book-open-variant",
		doctypes: [
			// Tree view of Account, same route as the Chart of Accounts shortcut.
			{
				name: "Chart of Accounts",
				icon: "mdi-file-tree-outline",
				route: "/app/account/view/tree",
			},
			{ name: "Bank", icon: "mdi-bank-outline" },
		],
	},
	{
		title: "Expenses",
		icon: "mdi-cash-minus",
		doctypes: [
			{ name: "Expense Claim", icon: "mdi-receipt-text-outline" },
			{ name: "Expense Claim Type", icon: "mdi-tag-outline" },
		],
	},
];

function openDoctype(doctype) {
	if (doctype.route) {
		window.location.assign(doctype.route);
		return;
	}
	// Desk route slug, same as frappe.router.slug(): lower-case, spaces -> "-".
	const slug = doctype.name.toLowerCase().replace(/ /g, "-");
	window.location.assign(`/app/${slug}`);
}
</script>

<style scoped>
@import "./erp-reports-grid.css";

.erp-reports-page {
	height: 100%;
	overflow-y: auto;
	overflow-x: hidden;
	-webkit-overflow-scrolling: touch;
}
</style>
