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

				<div class="pos-list-pagination">
					<div class="pos-list-pagination__info">
						{{ paginationLabel }}
					</div>
					<div class="pos-list-pagination__controls">
						<v-select
							v-model="pageSize"
							:items="[10, 20, 50]"
							density="compact"
							variant="outlined"
							hide-details
							class="pos-themed-input pos-list-pagination__page-size"
							@update:model-value="resetAndLoad"
						/>
						<v-btn
							icon="mdi-page-first"
							size="small"
							variant="text"
							:disabled="page <= 1 || listLoading"
							@click="goToPage(1)"
						/>
						<v-btn
							icon="mdi-chevron-left"
							size="small"
							variant="text"
							:disabled="page <= 1 || listLoading"
							@click="goToPage(page - 1)"
						/>
						<v-btn
							v-for="pageNumber in pageNumbers"
							:key="pageNumber"
							size="small"
							:variant="pageNumber === page ? 'flat' : 'text'"
							:color="pageNumber === page ? 'primary' : undefined"
							class="pos-list-pagination__page-btn"
							:disabled="listLoading"
							@click="goToPage(pageNumber)"
						>
							{{ pageNumber }}
						</v-btn>
						<v-btn
							icon="mdi-chevron-right"
							size="small"
							variant="text"
							:disabled="!hasMore || listLoading"
							@click="goToPage(page + 1)"
						/>
						<v-btn
							icon="mdi-page-last"
							size="small"
							variant="text"
							:disabled="!hasMore || listLoading"
							@click="goToPage(totalPages)"
						/>
					</div>
				</div>
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

		const page = ref(1);
		const pageSize = ref(20);
		const total = ref(0);
		const totalPages = computed(() => Math.max(1, Math.ceil(total.value / (pageSize.value || 1))));
		const hasMore = ref(false);

		const fromDate = ref('');
		const toDate = ref('');

		const listHeaders = [
			{ title: __('Expense Claim'), key: 'name', sortable: true },
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

		const paginationLabel = computed(() => {
			if (!total.value) return __('No results');
			return __('Page {0} of {1}', [page.value, totalPages.value]);
		});

		const pageNumbers = computed(() => {
			const totalCount = totalPages.value;
			const current = page.value;
			const windowSize = 5;
			let start = Math.max(1, current - Math.floor(windowSize / 2));
			let end = Math.min(totalCount, start + windowSize - 1);
			start = Math.max(1, end - windowSize + 1);
			const pages = [];
			for (let p = start; p <= end; p++) pages.push(p);
			return pages;
		});

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
						page_start: (page.value - 1) * pageSize.value,
						page_length: pageSize.value,
						from_date: fromDate.value || undefined,
						to_date: toDate.value || undefined,
						search: searchQuery.value || undefined,
					},
				});
				expenseList.value = message?.expense_claims || [];
				total.value = message?.total || 0;
				hasMore.value = Boolean(message?.has_more);
			} catch (e) {
				console.error('Failed to load expense claims', e);
				expenseList.value = [];
			} finally {
				listLoading.value = false;
			}
		};

		const resetAndLoad = () => {
			page.value = 1;
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

		const goToPage = (nextPage) => {
			if (nextPage < 1) return;
			page.value = nextPage;
			loadExpenseClaims();
		};

		const goToNew = () => {
			router.push('/expenses/new');
		};

		const openExpenseDetail = (item) => {
			window.open(`/app/expense-claim/${item.name}`, '_blank');
		};

		onMounted(() => {
			loadExpenseClaims();
		});

		return {
			expenseList,
			listLoading,
			searchQuery,
			listHeaders,
			page,
			pageSize,
			total,
			totalPages,
			pageNumbers,
			hasMore,
			fromDate,
			toDate,
			hasActiveFilters,
			totalClaimed,
			paginationLabel,
			loadExpenseClaims,
			resetAndLoad,
			handleSearchUpdate,
			clearFilters,
			goToPage,
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
