<template>
	<div class="pa-0 h-100 invoice-shell pos-list-page">
		<v-card flat class="invoice-section-card pos-themed-card dashboard-stats-card">
			<div class="pos-list-header">
				<div class="pos-list-header__main">
					<p class="pos-list-header__eyebrow">{{ __('Overview') }}</p>
					<h3 class="pos-list-header__title">{{ __('Dashboard') }}</h3>
					<p class="pos-list-header__subtitle">{{ scopeSubtitle }}</p>
				</div>
				<div class="pos-list-header__actions">
					<v-btn
						variant="tonal"
						size="small"
						color="primary"
						class="text-none"
						prepend-icon="mdi-refresh"
						:loading="loading"
						@click="loadDashboard"
					>
						{{ __('Refresh') }}
					</v-btn>
				</div>
			</div>

			<div class="dashboard-filters">
				<DateFilterField
					v-model="startDate"
					:label="__('Start Date')"
					field-class="pos-themed-input dashboard-filter-field"
					:max="endDate"
					@update:model-value="onManualDateChange"
				/>
				<DateFilterField
					v-model="endDate"
					:label="__('End Date')"
					field-class="pos-themed-input dashboard-filter-field"
					:min="startDate"
					@update:model-value="onManualDateChange"
				/>
				<v-select
					v-if="isAdmin"
					v-model="warehouseFilter"
					:items="warehouseOptions"
					item-title="warehouse_name"
					item-value="name"
					:label="__('Warehouse')"
					density="compact"
					variant="outlined"
					hide-details
					clearable
					class="pos-themed-input dashboard-filter-field"
					@update:model-value="loadDashboard"
				/>
				<div v-if="isAdmin" class="dashboard-shortcuts">
					<v-btn
						v-for="shortcut in shortcuts"
						:key="shortcut.key"
						size="small"
						:variant="activeShortcut === shortcut.key ? 'flat' : 'tonal'"
						:color="activeShortcut === shortcut.key ? 'primary' : undefined"
						class="text-none"
						@click="applyShortcut(shortcut.key)"
					>
						{{ shortcut.label }}
					</v-btn>
				</div>
			</div>

			<div v-if="loading && !loaded" class="dashboard-state">
				<v-progress-circular indeterminate color="primary" />
			</div>
			<div v-else-if="error" class="dashboard-state">
				<v-alert type="error" variant="tonal" density="comfortable">{{ error }}</v-alert>
			</div>
			<div v-else class="dashboard-sections">
				<section v-for="section in cardSections" :key="section.key" class="erp-reports-group">
					<div class="erp-reports-group__header">
						<v-icon size="18" class="mr-2">{{ section.icon }}</v-icon>
						<h4 class="erp-reports-group__title">{{ section.title }}</h4>
					</div>
					<div class="dashboard-card-grid">
						<v-card
							v-for="card in section.items"
							:key="card.key"
							variant="tonal"
							:color="card.color"
							class="dashboard-stat-card"
							:class="{
								'dashboard-stat-card--status': card.type === 'status',
								'dashboard-stat-card--list': card.type === 'list',
							}"
						>
							<div class="dashboard-stat-card__icon">
								<v-icon size="26">{{ card.icon }}</v-icon>
							</div>
							<div class="dashboard-stat-card__body">
								<p class="dashboard-stat-card__label">{{ card.label }}</p>
								<template v-if="card.type === 'status'">
									<strong class="dashboard-stat-card__value">{{ card.data.total }}</strong>
									<div class="dashboard-stat-card__chips">
										<v-chip
											v-for="(count, status) in card.data.status_counts"
											:key="status"
											size="x-small"
											variant="flat"
											class="dashboard-stat-card__chip"
										>
											{{ status }}: {{ count }}
										</v-chip>
										<span
											v-if="!Object.keys(card.data.status_counts || {}).length"
											class="dashboard-stat-card__chip-empty"
										>
											{{ __('No records') }}
										</span>
									</div>
								</template>
								<template v-else-if="card.type === 'list'">
									<ol v-if="card.rows.length" class="dashboard-stat-card__list">
										<li
											v-for="row in card.rows"
											:key="row.rank"
											class="dashboard-stat-card__list-row"
										>
											<span class="dashboard-stat-card__list-rank">{{ row.rank }}</span>
											<div class="dashboard-stat-card__list-info">
												<span class="dashboard-stat-card__list-title">{{ row.title }}</span>
												<span class="dashboard-stat-card__list-subtitle">{{ row.subtitle }}</span>
											</div>
											<div class="dashboard-stat-card__list-metrics">
												<strong>{{ row.value }}</strong>
												<span>{{ row.hint }}</span>
											</div>
										</li>
									</ol>
									<span v-else class="dashboard-stat-card__chip-empty">{{ card.emptyLabel }}</span>
								</template>
								<template v-else>
									<strong class="dashboard-stat-card__value">{{ card.value }}</strong>
									<p v-if="card.hint" class="dashboard-stat-card__hint">{{ card.hint }}</p>
								</template>
							</div>
						</v-card>
					</div>
				</section>
			</div>
		</v-card>
	</div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue';
import { storeToRefs } from 'pinia';
import { useUIStore } from '@/posapp/stores/uiStore';
import { ensurePosProfile } from '@/utils/pos_profile';
import DateFilterField from '../pos/shared/DateFilterField.vue';

const __ = window.__ || ((text) => text);

const uiStore = useUIStore();
const { posProfile } = storeToRefs(uiStore);

const isAdmin = computed(() => {
	const roles = frappe?.boot?.user?.roles || [];
	return roles.includes('BSP Admin') || roles.includes('System Manager');
});

const shortcuts = [
	{ key: 'daily', label: __('Daily') },
	{ key: 'weekly', label: __('Weekly') },
	{ key: 'monthly', label: __('Monthly') },
	{ key: 'yearly', label: __('Yearly') },
];

const loading = ref(false);
const loaded = ref(false);
const error = ref(null);

const startDate = ref('');
const endDate = ref('');
const warehouseFilter = ref(null);
const warehouseOptions = ref([]);
const activeShortcut = ref('daily');

const dashboard = reactive({
	scope: 'own',
	currency: '',
	sales: { total: 0, collection: 0, due: 0, count: 0 },
	purchase: { total: 0, collection: 0, due: 0, count: 0 },
	sales_return: { total: 0, count: 0 },
	purchase_return: { total: 0, count: 0 },
	sales_weight: 0,
	purchase_weight: 0,
	stock_qty: 0,
	material_transfers: { status_counts: {}, total: 0 },
	requisitions: { status_counts: {}, total: 0 },
	production_plans: null,
	expenses: { total: 0, count: 0 },
	deposits: { total: 0, count: 0 },
	fund_transfers: { total: 0, count: 0 },
	top_items: [],
	top_warehouses: [],
});

function formatDateString(date) {
	const year = date.getFullYear();
	const month = String(date.getMonth() + 1).padStart(2, '0');
	const day = String(date.getDate()).padStart(2, '0');
	return `${year}-${month}-${day}`;
}

function formatDisplayDate(value) {
	if (!value) return '—';
	const parts = String(value).split('-');
	return parts.length === 3 ? `${parts[2]}-${parts[1]}-${parts[0]}` : value;
}

function startOfWeek(date) {
	const d = new Date(date);
	// Business week starts Saturday (day 6), not the ISO Monday -- getDay()
	// returns 0=Sun..6=Sat, so days-since-last-Saturday is (day + 1) % 7.
	const day = d.getDay();
	const diff = -((day + 1) % 7);
	d.setDate(d.getDate() + diff);
	return d;
}

function startOfMonth(date) {
	return new Date(date.getFullYear(), date.getMonth(), 1);
}

function startOfYear(date) {
	return new Date(date.getFullYear(), 0, 1);
}

function formatAmount(value) {
	try {
		return format_currency(value || 0, dashboard.currency);
	} catch (e) {
		return String(value || 0);
	}
}

function formatNumber(value) {
	return (Number(value) || 0).toLocaleString();
}

function formatWeight(value) {
	return (Number(value) || 0).toLocaleString(undefined, {
		minimumFractionDigits: 0,
		maximumFractionDigits: 2,
	});
}

const scopeSubtitle = computed(() => {
	const rangeLabel =
		startDate.value === endDate.value
			? formatDisplayDate(startDate.value)
			: `${formatDisplayDate(startDate.value)} – ${formatDisplayDate(endDate.value)}`;
	return dashboard.scope === 'all'
		? __('Company-wide overview · {0}', [rangeLabel])
		: __('Your data · {0}', [rangeLabel]);
});

// Each section groups the cards that belong together so it's obvious at a
// glance which figure applies to which area of the business, mirroring the
// grouped layout the Reports grid below already uses.
const cardSections = computed(() => {
	const operationsItems = [
		{
			key: 'material_transfers',
			type: 'status',
			label: __('Material Transfers'),
			icon: 'mdi-truck-fast-outline',
			color: 'info',
			data: dashboard.material_transfers,
		},
		{
			key: 'requisitions',
			type: 'status',
			label: __('Requisitions'),
			icon: 'mdi-clipboard-list-outline',
			color: 'purple',
			data: dashboard.requisitions,
		},
	];
	if (dashboard.production_plans) {
		operationsItems.push({
			key: 'production_plans',
			type: 'status',
			label: __('Production Plans'),
			icon: 'mdi-factory',
			color: 'orange',
			data: dashboard.production_plans,
		});
	}

	return [
		{
			key: 'sales',
			title: __('Sales'),
			icon: 'mdi-cash-register',
			items: [
				{
					key: 'sales_total',
					label: __('Total Sales'),
					value: formatAmount(dashboard.sales.total),
					hint: __('{0} invoices', [dashboard.sales.count]),
					icon: 'mdi-cash-register',
					color: 'primary',
				},
				{
					key: 'sales_collection',
					label: __('Sales Collection'),
					value: formatAmount(dashboard.sales.collection),
					icon: 'mdi-cash-check',
					color: 'success',
				},
				{
					key: 'sales_due',
					label: __('Sales Due'),
					value: formatAmount(dashboard.sales.due),
					icon: 'mdi-cash-remove',
					color: 'warning',
				},
				{
					key: 'sales_return',
					label: __('Sales Return'),
					value: formatAmount(dashboard.sales_return.total),
					hint: __('{0} invoices', [dashboard.sales_return.count]),
					icon: 'mdi-keyboard-return',
					color: 'red',
				},
				{
					key: 'sales_weight',
					label: __('Sales Weight'),
					value: formatWeight(dashboard.sales_weight),
					hint: __('Qty × Default Weight of Measure'),
					icon: 'mdi-weight-kilogram',
					color: 'brown',
				},
			],
		},
		{
			key: 'purchase',
			title: __('Purchase'),
			icon: 'mdi-cart',
			items: [
				{
					key: 'purchase_total',
					label: __('Total Purchase'),
					value: formatAmount(dashboard.purchase.total),
					hint: __('{0} invoices', [dashboard.purchase.count]),
					icon: 'mdi-cart',
					color: 'indigo',
				},
				{
					key: 'purchase_collection',
					label: __('Purchase Payment'),
					value: formatAmount(dashboard.purchase.collection),
					icon: 'mdi-cash-fast',
					color: 'teal',
				},
				{
					key: 'purchase_due',
					label: __('Purchase Due'),
					value: formatAmount(dashboard.purchase.due),
					icon: 'mdi-cash-clock',
					color: 'deep-orange',
				},
				{
					key: 'purchase_return',
					label: __('Purchase Return'),
					value: formatAmount(dashboard.purchase_return.total),
					hint: __('{0} invoices', [dashboard.purchase_return.count]),
					icon: 'mdi-keyboard-return',
					color: 'red',
				},
				{
					key: 'purchase_weight',
					label: __('Purchase Weight'),
					value: formatWeight(dashboard.purchase_weight),
					hint: __('Qty × Default Weight of Measure'),
					icon: 'mdi-weight-kilogram',
					color: 'brown',
				},
			],
		},
		{
			key: 'inventory',
			title: __('Inventory'),
			icon: 'mdi-package-variant-closed',
			items: [
				{
					key: 'stock_qty',
					label: __('Total Stock Item Qty'),
					value: formatNumber(dashboard.stock_qty),
					hint: __('Current on-hand quantity'),
					icon: 'mdi-package-variant-closed',
					color: 'blue-grey',
				},
			],
		},
		{
			key: 'operations',
			title: __('Operations'),
			icon: 'mdi-truck-fast-outline',
			items: operationsItems,
		},
		{
			key: 'finance',
			title: __('Finance & Cash'),
			icon: 'mdi-bank-outline',
			items: [
				{
					key: 'expenses',
					label: __('Total Expenses'),
					value: formatAmount(dashboard.expenses.total),
					hint: __('{0} claims', [dashboard.expenses.count]),
					icon: 'mdi-receipt-text-edit-outline',
					color: 'error',
				},
				{
					key: 'deposits',
					label: __('Total Deposits'),
					value: formatAmount(dashboard.deposits.total),
					hint: __('{0} deposits', [dashboard.deposits.count]),
					icon: 'mdi-bank-outline',
					color: 'success',
				},
				{
					key: 'fund_transfers',
					label: __('Total Fund Transfers'),
					value: formatAmount(dashboard.fund_transfers.total),
					hint: __('{0} transfers', [dashboard.fund_transfers.count]),
					icon: 'mdi-bank-transfer',
					color: 'primary',
				},
			],
		},
		{
			key: 'insights',
			title: __('Insights'),
			icon: 'mdi-star-circle-outline',
			items: [
				{
					key: 'top_items',
					type: 'list',
					label: __('Top 5 Best Selling Items'),
					icon: 'mdi-star-circle-outline',
					color: 'pink',
					emptyLabel: __('No sales in this range'),
					rows: dashboard.top_items.map((row, index) => ({
						rank: index + 1,
						title: row.item_name || row.item_code,
						subtitle: row.item_code,
						value: formatAmount(row.amount),
						hint: __('{0} qty sold', [formatNumber(row.qty)]),
					})),
				},
				{
					key: 'top_warehouses',
					type: 'list',
					label: __('Best Selling Warehouses'),
					icon: 'mdi-warehouse',
					color: 'cyan',
					emptyLabel: __('No sales in this range'),
					rows: dashboard.top_warehouses.map((row, index) => ({
						rank: index + 1,
						title: row.warehouse_name || row.warehouse,
						subtitle: row.warehouse,
						value: formatAmount(row.amount),
						hint: __('{0} invoices', [row.count]),
					})),
				},
			],
		},
	];
});

function applyShortcut(key) {
	activeShortcut.value = key;
	const now = new Date();
	if (key === 'weekly') {
		startDate.value = formatDateString(startOfWeek(now));
	} else if (key === 'monthly') {
		startDate.value = formatDateString(startOfMonth(now));
	} else if (key === 'yearly') {
		startDate.value = formatDateString(startOfYear(now));
	} else {
		startDate.value = formatDateString(now);
	}
	endDate.value = formatDateString(now);
	loadDashboard();
}

function onManualDateChange() {
	activeShortcut.value = null;
	loadDashboard();
}

async function loadWarehouses() {
	if (!isAdmin.value) return;
	try {
		const { message } = await frappe.call({
			method: 'posawesome.posawesome.api.company_dashboard.get_dashboard_warehouses',
			args: { pos_profile: posProfile.value?.name },
		});
		warehouseOptions.value = message || [];
	} catch (e) {
		console.error('Failed to load dashboard warehouses', e);
	}
}

async function loadDashboard() {
	loading.value = true;
	error.value = null;
	try {
		const { message } = await frappe.call({
			method: 'posawesome.posawesome.api.company_dashboard.get_company_dashboard',
			args: {
				pos_profile: posProfile.value?.name || undefined,
				start_date: startDate.value || undefined,
				end_date: endDate.value || undefined,
				warehouse: isAdmin.value ? warehouseFilter.value || undefined : undefined,
			},
		});
		Object.assign(dashboard, message || {});
		loaded.value = true;
	} catch (e) {
		error.value = e?.message || __('Failed to load the dashboard.');
	} finally {
		loading.value = false;
	}
}

onMounted(async () => {
	const today = formatDateString(new Date());
	startDate.value = today;
	endDate.value = today;

	if (!posProfile.value?.name) {
		try {
			const profile = await ensurePosProfile();
			if (profile?.name) {
				uiStore.setPosProfile(profile);
			}
		} catch (e) {
			console.error('Failed to resolve active POS profile', e);
		}
	}

	await loadWarehouses();
	await loadDashboard();
});
</script>

<style scoped>
@import '../pos/invoice-shared-styles.css';
@import './erp-reports-grid.css';

.dashboard-state {
	padding: 24px;
	display: flex;
	justify-content: center;
}

.dashboard-filters {
	display: flex;
	flex-wrap: wrap;
	align-items: center;
	gap: 12px;
	padding: 0 18px 16px;
}

.dashboard-filter-field {
	max-width: 200px;
}

.dashboard-shortcuts {
	display: flex;
	gap: 6px;
	margin-left: auto;
}

.dashboard-sections {
	display: flex;
	flex-direction: column;
	gap: 22px;
	padding: 4px 18px 20px;
}

.dashboard-sections .erp-reports-group__title {
	font-size: 0.85rem;
}

.dashboard-card-grid {
	display: grid;
	/* auto-fit (not auto-fill) collapses any track beyond the real card count,
	   so the 1fr share goes entirely to the actual cards -- a 3-card row
	   stretches to fill the width instead of leaving a gap after 900px of
	   fixed-size cards on a wide screen. A lone card in a section (e.g.
	   Inventory) will span the full row -- an accepted, common dashboard
	   pattern for a single highlighted metric. */
	grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
	gap: 14px;
}

.dashboard-stat-card {
	display: flex;
	align-items: flex-start;
	gap: 12px;
	padding: 16px;
	border-radius: 14px;
}

.dashboard-stat-card__icon {
	display: flex;
	align-items: center;
	justify-content: center;
	width: 44px;
	height: 44px;
	border-radius: 12px;
	background: rgba(255, 255, 255, 0.35);
	flex-shrink: 0;
}

.dashboard-stat-card__body {
	min-width: 0;
	flex: 1 1 auto;
}

.dashboard-stat-card__label {
	margin: 0 0 4px;
	font-size: 0.78rem;
	font-weight: 600;
	opacity: 0.85;
}

.dashboard-stat-card__value {
	display: block;
	font-size: 1.35rem;
	font-weight: 700;
	line-height: 1.2;
}

.dashboard-stat-card__hint {
	margin: 4px 0 0;
	font-size: 0.72rem;
	opacity: 0.75;
}

.dashboard-stat-card--status .dashboard-stat-card__chips {
	display: flex;
	flex-wrap: wrap;
	gap: 4px;
	margin-top: 8px;
}

.dashboard-stat-card__chip {
	font-weight: 600;
}

.dashboard-stat-card__chip-empty {
	font-size: 0.72rem;
	opacity: 0.75;
}

.dashboard-stat-card--list {
	align-items: flex-start;
}

.dashboard-stat-card__list {
	list-style: none;
	margin: 8px 0 0;
	padding: 0;
	display: flex;
	flex-direction: column;
	gap: 8px;
}

.dashboard-stat-card__list-row {
	display: flex;
	align-items: center;
	gap: 10px;
}

.dashboard-stat-card__list-rank {
	display: flex;
	align-items: center;
	justify-content: center;
	width: 22px;
	height: 22px;
	flex-shrink: 0;
	border-radius: 50%;
	background: rgba(255, 255, 255, 0.45);
	font-size: 0.72rem;
	font-weight: 700;
}

.dashboard-stat-card__list-info {
	min-width: 0;
	flex: 1 1 auto;
	display: flex;
	flex-direction: column;
}

.dashboard-stat-card__list-title {
	font-size: 0.85rem;
	font-weight: 600;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

.dashboard-stat-card__list-subtitle {
	font-size: 0.7rem;
	opacity: 0.75;
}

.dashboard-stat-card__list-metrics {
	flex-shrink: 0;
	text-align: right;
	display: flex;
	flex-direction: column;
	font-size: 0.78rem;
}

.dashboard-stat-card__list-metrics span {
	font-size: 0.68rem;
	opacity: 0.75;
}

/* Unlike a single full-height table list, this page stacks several cards of
   organically-sized content -- let it size to its content and the outer
   .invoice-shell scroll the whole page, instead of clipping/scrolling within
   a fixed viewport-height share (.pos-list-card's behavior, which is built
   for exactly one full-height table). */
.dashboard-stats-card {
	flex: 0 0 auto;
	overflow: visible;
}

@media (max-width: 900px) {
	.dashboard-card-grid {
		grid-template-columns: 1fr 1fr;
	}
	.dashboard-shortcuts {
		margin-left: 0;
	}
}

@media (max-width: 600px) {
	.dashboard-card-grid {
		grid-template-columns: 1fr;
	}
}
</style>
