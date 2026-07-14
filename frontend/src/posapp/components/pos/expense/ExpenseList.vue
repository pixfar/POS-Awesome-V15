<template>
	<div class="pa-0 h-100 invoice-shell pos-list-page">
		<v-card flat class="invoice-section-card pos-themed-card pos-list-card">
			<div class="pos-list-header">
				<div class="pos-list-header__main">
					<p class="pos-list-header__eyebrow">{{ __("Expenses & Advances") }}</p>
					<h3 class="pos-list-header__title">{{ __("Expenses") }}</h3>
					<p class="pos-list-header__subtitle">
						{{ __("Track the expense claims you have submitted") }}
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
						{{ __("New Expense") }}
					</v-btn>
				</div>
			</div>

			<div class="pos-list-stats">
				<div class="pos-list-stat pos-list-stat--primary">
					<span class="pos-list-stat__label">{{ __("Total") }}</span>
					<strong class="pos-list-stat__value">{{ total }}</strong>
				</div>
				<div class="pos-list-stat pos-list-stat--success">
					<span class="pos-list-stat__label">{{ __("Total Claimed") }}</span>
					<strong class="pos-list-stat__value">{{ formatCurrency(totalClaimed) }}</strong>
				</div>
			</div>

			<div class="pos-list-toolbar">
				<v-text-field
					v-model="searchQuery"
					:label="__('Search expense claim or remark')"
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
						@click="loadExpenseClaims"
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

			<div v-if="expenseList.length" class="pos-list-table-wrap">
				<v-data-table
					:headers="listHeaders"
					:items="expenseList"
					:loading="listLoading"
					density="comfortable"
					hide-default-footer
					:items-per-page="-1"
					class="pos-list-table"
					@click:row="(_, row) => openExpenseDetail(row.item)"
				>
					<template #item.name="{ item }">
						<span class="pos-list-cell-primary">{{ item.name }}</span>
					</template>
					<template #item.posting_date="{ item }">
						<span class="pos-list-cell-muted">{{ formatDisplayDate(item.posting_date) }}</span>
					</template>
					<template #item.remark="{ item }">
						<span class="pos-list-cell-truncate" :title="item.remark">{{ item.remark || "—" }}</span>
					</template>
					<template #item.grand_total="{ item }">
						{{ formatCurrency(item.grand_total) }}
					</template>
					<template #item.status="{ item }">
						<v-chip size="small" variant="tonal" :color="statusColor(item.status)">
							{{ item.status }}
						</v-chip>
					</template>
				</v-data-table>
			</div>

			<div v-else-if="!listLoading" class="pos-list-empty">
				<v-icon size="48" color="primary" class="pos-list-empty__icon">mdi-receipt-text-edit-outline</v-icon>
				<h4 class="pos-list-empty__title">{{ __("No expenses found") }}</h4>
				<p class="pos-list-empty__subtitle">
					{{ hasActiveFilters
						? __("Try different filters or clear them.")
						: __("Submit a new expense claim to see it listed here.") }}
				</p>
				<v-btn
					v-if="!hasActiveFilters"
					color="primary"
					variant="flat"
					class="text-none mt-2"
					prepend-icon="mdi-plus"
					@click="goToNew"
				>
					{{ __("New Expense") }}
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
	name: 'ExpenseList',
	components: { DateFilterField },
	mixins: [format],
	setup() {
		const router = useRouter();
		const expenseList = ref([]);
		const listLoading = ref(false);
		const searchQuery = ref('');
		let searchTimeout = null;

		// Single page view: the whole (per-employee) list fits comfortably
		// within the backend's max page_length, so it's fetched and shown in
		// one continuous table instead of paginated.
		const PAGE_LENGTH = 100;
		const total = ref(0);

		const fromDate = ref('');
		const toDate = ref('');

		const listHeaders = [
			{ title: __('Expense Claim'), key: 'name', sortable: true },
			{ title: __('Employee'), key: 'employee_name', sortable: true },
			{ title: __('Warehouse'), key: 'warehouse', sortable: true },
			{ title: __('Date'), key: 'posting_date', sortable: true },
			{ title: __('Remark'), key: 'remark', sortable: false },
			{ title: __('Amount'), key: 'grand_total', sortable: true, align: 'end' },
			{ title: __('Status'), key: 'status', sortable: true },
		];

		const hasActiveFilters = computed(() =>
			Boolean(searchQuery.value || fromDate.value || toDate.value),
		);

		const totalClaimed = computed(() =>
			expenseList.value.reduce((sum, row) => sum + (Number(row.grand_total) || 0), 0),
		);

		const formatDisplayDate = (value) => {
			if (!value) return '—';
			const parts = String(value).split('-');
			return parts.length === 3 ? `${parts[2]}-${parts[1]}-${parts[0]}` : value;
		};

		const statusColor = (status) => {
			const map = {
				Paid: 'green',
				Unpaid: 'orange',
				Rejected: 'red',
				Submitted: 'blue',
				Draft: 'grey',
			};
			return map[status] || 'grey';
		};

		const loadExpenseClaims = async () => {
			listLoading.value = true;
			try {
				const { message } = await frappe.call({
					method: 'posawesome.posawesome.api.expense_claims.get_expense_claims_list',
					args: {
						page_start: 0,
						page_length: PAGE_LENGTH,
						from_date: fromDate.value || undefined,
						to_date: toDate.value || undefined,
						search: searchQuery.value || undefined,
					},
				});
				expenseList.value = message?.expense_claims || [];
				total.value = message?.total || 0;
			} catch (e) {
				console.error('Failed to load expense claims', e);
				expenseList.value = [];
			} finally {
				listLoading.value = false;
			}
		};

		const resetAndLoad = () => {
			loadExpenseClaims();
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
			router.push('/expenses/new');
		};

		const openExpenseDetail = (item) => {
			router.push(`/expenses/${item.name}`);
		};

		onMounted(() => {
			loadExpenseClaims();
		});

		return {
			expenseList,
			listLoading,
			searchQuery,
			listHeaders,
			total,
			fromDate,
			toDate,
			hasActiveFilters,
			totalClaimed,
			loadExpenseClaims,
			resetAndLoad,
			handleSearchUpdate,
			clearFilters,
			formatDisplayDate,
			statusColor,
			goToNew,
			openExpenseDetail,
		};
	},
};
</script>

<style scoped>
@import '../invoice-shared-styles.css';
</style>
