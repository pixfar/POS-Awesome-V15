<template>
	<div class="pa-0 h-100 invoice-shell pos-list-page">
		<v-card flat class="invoice-section-card pos-themed-card pos-list-card">
			<div class="pos-list-header">
				<div class="pos-list-header__main">
					<p class="pos-list-header__eyebrow">{{ __("BSP Daily Deposit") }}</p>
					<h3 class="pos-list-header__title">{{ __("Daily Deposits") }}</h3>
					<p class="pos-list-header__subtitle">
						{{ __("Track the daily deposits you have submitted") }}
					</p>
				</div>
				<div class="pos-list-header__actions">
					<v-btn
						color="primary"
						variant="flat"
						class="text-none"
						prepend-icon="mdi-plus"
						@click="goToNew"
					>
						{{ __("New Deposit") }}
					</v-btn>
				</div>
			</div>

			<div class="pos-list-stats">
				<div class="pos-list-stat pos-list-stat--primary">
					<span class="pos-list-stat__label">{{ __("Total") }}</span>
					<strong class="pos-list-stat__value">{{ total }}</strong>
				</div>
				<div class="pos-list-stat pos-list-stat--success">
					<span class="pos-list-stat__label">{{ __("Total Deposited") }}</span>
					<strong class="pos-list-stat__value">{{ formatCurrency(totalDeposited) }}</strong>
				</div>
			</div>

			<div class="pos-list-toolbar">
				<v-text-field
					v-model="searchQuery"
					:label="__('Search deposit or bank')"
					density="compact"
					variant="solo"
					hide-details
					clearable
					prepend-inner-icon="mdi-magnify"
					class="pos-themed-input pos-list-search"
					@update:model-value="handleSearchUpdate"
				/>
				<div class="pos-list-toolbar__filters">
					<v-btn
						variant="tonal"
						size="small"
						color="primary"
						prepend-icon="mdi-sync"
						:loading="listLoading"
						class="text-none"
						@click="loadDeposits"
					>
						{{ __("Sync") }}
					</v-btn>
				</div>
			</div>

			<div class="pos-list-filters">
				<DateFilterField
					v-model="fromDate"
					:label="__('From Date')"
					field-class="pos-themed-input pos-list-filter-field"
					:max="toDate"
					@update:model-value="resetAndLoad"
				/>
				<DateFilterField
					v-model="toDate"
					:label="__('To Date')"
					field-class="pos-themed-input pos-list-filter-field"
					:min="fromDate"
					@update:model-value="resetAndLoad"
				/>
				<v-btn variant="text" size="small" class="text-none" @click="clearFilters">
					{{ __("Clear Filters") }}
				</v-btn>
			</div>

			<div v-if="depositList.length" class="pos-list-table-wrap">
				<v-data-table
					:headers="listHeaders"
					:items="depositList"
					:loading="listLoading"
					density="comfortable"
					hide-default-footer
					:items-per-page="-1"
					class="pos-list-table"
					@click:row="(_, row) => openDepositDetail(row.item)"
				>
					<template #item.name="{ item }">
						<span class="pos-list-cell-primary">{{ item.name }}</span>
					</template>
					<template #item.posting_date="{ item }">
						<span class="pos-list-cell-muted">{{ formatDisplayDate(item.posting_date) }}</span>
					</template>
					<template #item.amount="{ item }">
						{{ formatCurrency(item.amount) }}
					</template>
					<template #item.docstatus="{ item }">
						<v-chip size="small" variant="tonal" :color="statusColor(item.docstatus)">
							{{ statusLabel(item.docstatus) }}
						</v-chip>
					</template>
				</v-data-table>
			</div>

			<div v-else-if="!listLoading" class="pos-list-empty">
				<v-icon size="48" color="primary" class="pos-list-empty__icon">mdi-bank-outline</v-icon>
				<h4 class="pos-list-empty__title">{{ __("No deposits found") }}</h4>
				<p class="pos-list-empty__subtitle">
					{{ hasActiveFilters
						? __("Try different filters or clear them.")
						: __("Submit a new daily deposit to see it listed here.") }}
				</p>
				<v-btn
					v-if="!hasActiveFilters"
					color="primary"
					variant="flat"
					class="text-none mt-2"
					prepend-icon="mdi-plus"
					@click="goToNew"
				>
					{{ __("New Deposit") }}
				</v-btn>
			</div>

			<div v-else class="pos-list-empty">
				<v-progress-circular indeterminate color="primary" />
			</div>
		</v-card>
	</div>
</template>

<script>
import { ref, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import format from '../../../format';
import DateFilterField from '../shared/DateFilterField.vue';

export default {
	name: 'DepositList',
	components: { DateFilterField },
	mixins: [format],
	setup() {
		const router = useRouter();
		const depositList = ref([]);
		const listLoading = ref(false);
		const searchQuery = ref('');
		let searchTimeout = null;

		// Single page view: the whole (per-user) list fits comfortably within
		// the backend's max page_length, so it's fetched and shown in one
		// continuous table instead of paginated.
		const PAGE_LENGTH = 100;
		const total = ref(0);

		const fromDate = ref('');
		const toDate = ref('');

		const listHeaders = [
			{ title: __('Deposit'), key: 'name', sortable: true },
			{ title: __('Date'), key: 'posting_date', sortable: true },
			{ title: __('Warehouse'), key: 'warehouse', sortable: true },
			{ title: __('Deposit Type'), key: 'deposit_type', sortable: true },
			{ title: __('Bank Name'), key: 'bank_name', sortable: true },
			{ title: __('Amount'), key: 'amount', sortable: true, align: 'end' },
			{ title: __('Status'), key: 'docstatus', sortable: true },
		];

		const hasActiveFilters = computed(() =>
			Boolean(searchQuery.value || fromDate.value || toDate.value),
		);

		const totalDeposited = computed(() =>
			depositList.value.reduce((sum, row) => sum + (Number(row.amount) || 0), 0),
		);

		const formatDisplayDate = (value) => {
			if (!value) return '—';
			const parts = String(value).split('-');
			return parts.length === 3 ? `${parts[2]}-${parts[1]}-${parts[0]}` : value;
		};

		const statusLabel = (docstatus) => {
			const map = { 0: __('Draft'), 1: __('Submitted'), 2: __('Cancelled') };
			return map[docstatus] || __('Draft');
		};

		const statusColor = (docstatus) => {
			const map = { 0: 'grey', 1: 'green', 2: 'red' };
			return map[docstatus] || 'grey';
		};

		const loadDeposits = async () => {
			listLoading.value = true;
			try {
				const { message } = await frappe.call({
					method: 'posawesome.posawesome.api.bsp_daily_deposit.get_daily_deposits_list',
					args: {
						page_start: 0,
						page_length: PAGE_LENGTH,
						from_date: fromDate.value || undefined,
						to_date: toDate.value || undefined,
						search: searchQuery.value || undefined,
					},
				});
				depositList.value = message?.deposits || [];
				total.value = message?.total || 0;
			} catch (e) {
				console.error('Failed to load daily deposits', e);
				depositList.value = [];
			} finally {
				listLoading.value = false;
			}
		};

		const resetAndLoad = () => {
			loadDeposits();
		};

		const handleSearchUpdate = () => {
			if (searchTimeout) clearTimeout(searchTimeout);
			searchTimeout = setTimeout(resetAndLoad, 300);
		};

		const clearFilters = () => {
			searchQuery.value = '';
			fromDate.value = '';
			toDate.value = '';
			resetAndLoad();
		};

		const goToNew = () => {
			router.push('/deposits/new');
		};

		const openDepositDetail = (item) => {
			router.push(`/deposits/${item.name}`);
		};

		onMounted(() => {
			loadDeposits();
		});

		return {
			depositList,
			listLoading,
			searchQuery,
			listHeaders,
			total,
			fromDate,
			toDate,
			hasActiveFilters,
			totalDeposited,
			loadDeposits,
			resetAndLoad,
			handleSearchUpdate,
			clearFilters,
			formatDisplayDate,
			statusLabel,
			statusColor,
			goToNew,
			openDepositDetail,
		};
	},
};
</script>

<style scoped>
@import '../invoice-shared-styles.css';
</style>
