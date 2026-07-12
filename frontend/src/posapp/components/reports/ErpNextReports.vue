<template>
	<div class="pa-0 h-100 invoice-shell pos-list-page">
		<v-card flat class="invoice-section-card pos-themed-card pos-list-card">
			<div class="erp-reports-groups">
				<section
					v-for="group in reportGroups"
					:key="group.title"
					class="erp-reports-group"
				>
					<div class="erp-reports-group__header">
						<v-icon size="20" class="mr-2">{{ group.icon }}</v-icon>
						<h4 class="erp-reports-group__title">{{ __(group.title) }}</h4>
					</div>
					<div class="erp-reports-grid">
						<button
							v-for="report in group.reports"
							:key="report.name"
							type="button"
							class="erp-report-card"
							@click="openReport(report.name)"
						>
							<div class="erp-report-card__icon">
								<v-icon size="22">{{ report.icon }}</v-icon>
							</div>
							<div class="erp-report-card__body">
								<p class="erp-report-card__title">{{ __(report.title) }}</p>
								<p class="erp-report-card__hint">
									{{ __('Open in ERPNext') }}
								</p>
							</div>
							<v-icon size="18" class="erp-report-card__arrow">
								mdi-open-in-new
							</v-icon>
						</button>
					</div>
				</section>
			</div>
		</v-card>
	</div>
</template>

<script setup>
const __ = window.__ || ((text) => text);

const reportGroups = [
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

function openReport(reportName) {
	const url = `/app/query-report/${encodeURIComponent(reportName)}`;
	window.open(url, '_blank', 'noopener,noreferrer');
}
</script>

<style scoped>
.erp-reports-groups {
	display: flex;
	flex-direction: column;
	gap: 24px;
	padding: 8px 16px 24px;
}

.erp-reports-group__header {
	display: flex;
	align-items: center;
	margin-bottom: 12px;
}

.erp-reports-group__title {
	margin: 0;
	font-size: 0.95rem;
	font-weight: 700;
	color: var(--pos-text-primary, #212121);
}

.erp-reports-grid {
	display: grid;
	grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
	gap: 12px;
}

.erp-report-card {
	display: flex;
	align-items: center;
	gap: 12px;
	width: 100%;
	padding: 14px 16px;
	border: 1px solid var(--pos-border, rgba(0, 0, 0, 0.12));
	border-radius: 12px;
	background: var(--pos-card-bg, #fff);
	text-align: left;
	cursor: pointer;
	transition:
		border-color 0.15s ease,
		box-shadow 0.15s ease,
		background-color 0.15s ease;
}

.erp-report-card:hover {
	border-color: rgba(37, 99, 235, 0.35);
	box-shadow: 0 4px 12px rgba(15, 23, 42, 0.08);
	background: rgba(37, 99, 235, 0.03);
}

.erp-report-card:focus-visible {
	outline: 2px solid rgba(37, 99, 235, 0.5);
	outline-offset: 2px;
}

.erp-report-card__icon {
	display: flex;
	align-items: center;
	justify-content: center;
	width: 40px;
	height: 40px;
	border-radius: 10px;
	background: rgba(37, 99, 235, 0.08);
	color: #2563eb;
	flex-shrink: 0;
}

.erp-report-card__body {
	min-width: 0;
	flex: 1;
}

.erp-report-card__title {
	margin: 0;
	font-size: 0.9rem;
	font-weight: 600;
	color: var(--pos-text-primary, #212121);
}

.erp-report-card__hint {
	margin: 2px 0 0;
	font-size: 0.75rem;
	color: var(--pos-text-secondary, #666);
}

.erp-report-card__arrow {
	color: var(--pos-text-secondary, #666);
	flex-shrink: 0;
}

@media (max-width: 600px) {
	.erp-reports-groups {
		padding: 4px 12px 20px;
	}

	.erp-reports-grid {
		grid-template-columns: 1fr;
	}
}
</style>
