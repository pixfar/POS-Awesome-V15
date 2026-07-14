import { computed } from 'vue';
import { useRouter } from 'vue-router';

const __ = window.__ || ((text) => text);

// Reports listing a "roles" array are only shown to users holding at least
// one of those roles (e.g. financial statements are System Manager only) --
// everyone else never sees the card, and a group left with no visible
// reports is hidden entirely rather than showing an empty section.
function userHasAnyRole(roles) {
	if (!roles || !roles.length) return true;
	const userRoles = frappe?.boot?.user?.roles || [];
	return roles.some((role) => userRoles.includes(role));
}

const reportGroups = [
	{
		title: 'Financial Statements & Cash Management',
		icon: 'mdi-chart-tree',
		reports: [
			{
				title: 'Profit and Loss Statement',
				name: 'Profit and Loss Statement',
				icon: 'mdi-chart-areaspline',
				// Income/Expense breakdown -- restricted since it exposes
				// company-wide financial results. Rendered in-app (tree view)
				// instead of redirecting to the ERPNext desk report.
				roles: ['System Manager'],
				route: '/reports/profit-and-loss',
			},
			{
				title: 'Daily Cash Summary Report',
				name: 'Daily Cash Summary Report',
				icon: 'mdi-file-pdf-box',
				// No role restriction -- the backend scopes it to the user's own
				// permitted warehouse(s), same as the Deposit/Expense lists.
				route: '/reports/daily-cash-summary',
			},
		],
	},
	{
		title: 'Sales',
		icon: 'mdi-point-of-sale',
		reports: [
			{
				title: 'Sales Register',
				name: 'Sales Register',
				icon: 'mdi-file-document-outline',
			},
			{
				title: 'Sales Return Register',
				name: 'Sales Return Register',
				icon: 'mdi-file-undo-outline',
			},
			{
				title: 'Item-Wise Sales Register',
				name: 'Item-wise Sales Register',
				icon: 'mdi-package-variant',
			},
		],
	},
	{
		title: 'Purchase',
		icon: 'mdi-cart-outline',
		reports: [
			{
				title: 'Purchase Register',
				name: 'Purchase Register',
				icon: 'mdi-file-document-outline',
			},
			{
				title: 'Item-Wise Purchase Register',
				name: 'Item-wise Purchase Register',
				icon: 'mdi-package-variant-closed',
			},
		],
	},
	{
		title: 'Stock',
		icon: 'mdi-warehouse',
		reports: [
			{
				title: 'Stock Balance',
				name: 'Stock Balance',
				icon: 'mdi-scale-balance',
			},
			{
				title: 'Stock Ledger',
				name: 'Stock Ledger',
				icon: 'mdi-book-open-outline',
			},
			{
				title: 'Stock Ageing Summary',
				name: 'Stock Ageing Summary',
				icon: 'mdi-timer-sand',
			},
			{
				title: 'Low Stock Alert Report',
				name: 'Low Stock Alert Report',
				icon: 'mdi-alert-outline',
			},
			{
				title: 'Warehouse Wise Item Stock Balance',
				name: 'Warehouse Wise Item Stock Balance',
				icon: 'mdi-table-large',
			},
		],
	},
	{
		title: 'Accounts',
		icon: 'mdi-finance',
		reports: [
			{
				title: 'Customer Ledger Summary',
				name: 'Customer Ledger Summary',
				icon: 'mdi-account-cash-outline',
			},
			{
				title: 'Accounts Receivable Summary',
				name: 'Accounts Receivable Summary',
				icon: 'mdi-cash-plus',
			},
			{
				title: 'Accounts Payable Summary',
				name: 'Accounts Payable Summary',
				icon: 'mdi-cash-minus',
			},
		],
	},
	{
		title: 'Product',
		icon: 'mdi-cube-outline',
		reports: [
			{
				title: 'Product Weight Report Summary',
				name: 'Product Weight Report Summary',
				icon: 'mdi-weight-kilogram',
			},
		],
	},
];

// Shared by ErpNextReports.vue (the standalone /reports page) and
// DashboardOverview.vue (which shows the same grid by default) so the report
// list and its role-gating logic live in exactly one place.
export function useErpReports() {
	const router = useRouter();

	const visibleReportGroups = computed(() =>
		reportGroups
			.map((group) => ({
				...group,
				reports: group.reports.filter((report) => userHasAnyRole(report.roles)),
			}))
			.filter((group) => group.reports.length > 0)
	);

	function openReport(report) {
		if (report.route) {
			router.push(report.route);
			return;
		}
		const url = `/app/query-report/${encodeURIComponent(report.name)}`;
		window.open(url, '_blank', 'noopener,noreferrer');
	}

	return { __, visibleReportGroups, openReport };
}
