<template>
	<div class="pa-0 h-100 invoice-shell pos-list-page">
		<v-card flat class="invoice-section-card pos-themed-card pos-list-card">
			<div class="pos-list-header">
				<div class="pos-list-header__main">
					<p class="pos-list-header__eyebrow">{{ __('Overview') }}</p>
					<h3 class="pos-list-header__title">{{ __('Dashboard') }}</h3>
					<p class="pos-list-header__subtitle">
						{{ __("Today's status at a glance") }}
						<template v-if="overview.date"> &middot; {{ overview.date }}</template>
					</p>
				</div>
				<div class="pos-list-header__actions">
					<v-btn
						variant="tonal"
						size="small"
						color="primary"
						class="text-none"
						prepend-icon="mdi-refresh"
						:loading="loading"
						@click="loadOverview"
					>
						{{ __('Refresh') }}
					</v-btn>
				</div>
			</div>

			<div v-if="loading && !loaded" class="dashboard-state">
				<v-progress-circular indeterminate color="primary" />
			</div>
			<div v-else-if="error" class="dashboard-state">
				<v-alert type="error" variant="tonal" density="comfortable">{{ error }}</v-alert>
			</div>
			<div v-else class="pos-list-stats dashboard-kpis">
				<div class="pos-list-stat pos-list-stat--success">
					<span class="pos-list-stat__label">{{ __('Daily Sales') }}</span>
					<strong class="pos-list-stat__value">{{ formatAmount(overview.net_sales) }}</strong>
					<span class="pos-list-stat__hint">
						{{ overview.invoice_count || 0 }} {{ __('invoices') }}
					</span>
				</div>
				<div class="pos-list-stat pos-list-stat--primary">
					<span class="pos-list-stat__label">{{ __('Daily Payment Collected') }}</span>
					<strong class="pos-list-stat__value">{{ formatAmount(overview.collections_total) }}</strong>
					<span class="pos-list-stat__hint">
						{{ __('Cash') }} {{ formatAmount(overview.cash_collections) }} &middot;
						{{ __('Card/Online') }} {{ formatAmount(overview.card_online_collections) }}
					</span>
				</div>
				<div class="pos-list-stat pos-list-stat--danger">
					<span class="pos-list-stat__label">{{ __('Daily Expenses') }}</span>
					<strong class="pos-list-stat__value">{{ formatAmount(overview.expense_total) }}</strong>
					<span class="pos-list-stat__hint">
						{{ overview.expense_count || 0 }} {{ __('entries') }}
					</span>
				</div>
			</div>
		</v-card>

		<v-card flat class="invoice-section-card pos-themed-card pos-list-card dashboard-reports-card">
			<div class="dashboard-reports-header">
				<v-icon size="20" class="mr-2">mdi-chart-box-outline</v-icon>
				<h4 class="dashboard-reports-title">{{ __('Reports') }}</h4>
			</div>
			<div class="erp-reports-groups">
				<section
					v-for="group in visibleReportGroups"
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
							@click="openReport(report)"
						>
							<div class="erp-report-card__icon">
								<v-icon size="22">{{ report.icon }}</v-icon>
							</div>
							<div class="erp-report-card__body">
								<p class="erp-report-card__title">{{ __(report.title) }}</p>
							</div>
							<v-icon size="18" class="erp-report-card__arrow">
								{{ report.route ? 'mdi-arrow-right' : 'mdi-open-in-new' }}
							</v-icon>
						</button>
					</div>
				</section>
			</div>
		</v-card>
	</div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue';
import { storeToRefs } from 'pinia';
import { useUIStore } from '@/posapp/stores/uiStore';
import { useErpReports } from './useErpReports';

const { __, visibleReportGroups, openReport } = useErpReports();

const uiStore = useUIStore();
const { posProfile } = storeToRefs(uiStore);

const loading = ref(false);
const loaded = ref(false);
const error = ref(null);
const overview = reactive({
	date: '',
	currency: '',
	invoice_count: 0,
	net_sales: 0,
	collections_total: 0,
	cash_collections: 0,
	card_online_collections: 0,
	other_collections: 0,
	expense_total: 0,
	expense_count: 0,
});

function formatAmount(value) {
	try {
		return format_currency(value || 0, overview.currency);
	} catch (e) {
		return String(value || 0);
	}
}

async function loadOverview() {
	loading.value = true;
	error.value = null;
	try {
		const profileName = posProfile.value?.name || undefined;
		const r = await frappe.call({
			method: 'posawesome.posawesome.api.dashboard.get_daily_overview',
			args: { pos_profile: profileName },
		});
		Object.assign(overview, r.message || {});
		loaded.value = true;
	} catch (e) {
		error.value = e?.message || __('Failed to load the daily overview.');
	} finally {
		loading.value = false;
	}
}

onMounted(loadOverview);
</script>

<style scoped>
@import '../pos/invoice-shared-styles.css';
@import './erp-reports-grid.css';

.dashboard-state {
	padding: 24px;
	display: flex;
	justify-content: center;
}

.dashboard-kpis {
	grid-template-columns: repeat(3, minmax(0, 1fr));
	padding-bottom: 16px;
}

.pos-list-stat__hint {
	font-size: 0.72rem;
	color: var(--pos-text-secondary, rgba(0, 0, 0, 0.55));
}

.dashboard-reports-card {
	flex: 1 1 auto;
	min-height: 0;
	overflow: auto;
}

.dashboard-reports-header {
	display: flex;
	align-items: center;
	padding: 16px 18px 0;
}

.dashboard-reports-title {
	margin: 0;
	font-size: 1rem;
	font-weight: 700;
	color: var(--pos-text-primary, #212121);
}

@media (max-width: 900px) {
	.dashboard-kpis {
		grid-template-columns: 1fr;
	}
}
</style>
