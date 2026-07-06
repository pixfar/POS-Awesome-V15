<template>
	<div class="pa-0 h-100 invoice-shell pos-list-page">
		<v-card flat class="invoice-section-card pos-themed-card pos-list-card">
			<div class="pos-list-header">
				<div class="pos-list-header__main">
					<p class="pos-list-header__eyebrow">{{ __("Manufacturing") }}</p>
					<h3 class="pos-list-header__title">{{ __("Production Plans") }}</h3>
					<p class="pos-list-header__subtitle">
						{{ __("Track production plans from draft through completion") }}
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
						{{ __("Create Plan") }}
					</v-btn>
				</div>
			</div>

			<div class="pos-list-stats">
				<div class="pos-list-stat pos-list-stat--primary">
					<span class="pos-list-stat__label">{{ __("Total") }}</span>
					<strong class="pos-list-stat__value">{{ total }}</strong>
				</div>
				<div class="pos-list-stat pos-list-stat--warning">
					<span class="pos-list-stat__label">{{ __("Work In Progress") }}</span>
					<strong class="pos-list-stat__value">{{ statusCounts["Work In Progress"] || 0 }}</strong>
				</div>
				<div class="pos-list-stat pos-list-stat--success">
					<span class="pos-list-stat__label">{{ __("Production Complete") }}</span>
					<strong class="pos-list-stat__value">{{ statusCounts["Production Complete"] || 0 }}</strong>
				</div>
				<div class="pos-list-stat">
					<span class="pos-list-stat__label">{{ __("Cancelled") }}</span>
					<strong class="pos-list-stat__value">{{ statusCounts["Cancelled"] || 0 }}</strong>
				</div>
			</div>

			<div class="pos-list-toolbar">
				<v-text-field
					v-model="searchQuery"
					:label="__('Search plan or warehouse')"
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
						@click="loadPlans"
					>
						{{ __("Sync") }}
					</v-btn>
				</div>
			</div>

			<div class="pos-list-filters">
				<v-select
					v-model="statusFilter"
					:items="statusOptions"
					:label="__('Status')"
					density="compact"
					variant="outlined"
					hide-details
					clearable
					class="pos-themed-input pos-list-filter-field"
					@update:model-value="resetAndLoad"
				/>
				<v-text-field
					v-model="fromDate"
					type="date"
					:label="__('From Date')"
					density="compact"
					variant="outlined"
					hide-details
					clearable
					class="pos-themed-input pos-list-filter-field"
					@update:model-value="resetAndLoad"
				/>
				<v-text-field
					v-model="toDate"
					type="date"
					:label="__('To Date')"
					density="compact"
					variant="outlined"
					hide-details
					clearable
					class="pos-themed-input pos-list-filter-field"
					@update:model-value="resetAndLoad"
				/>
				<v-autocomplete
					v-model="itemCodeFilter"
					v-model:search="itemSearchQuery"
					:items="itemSearchResults"
					:loading="itemSearchLoading"
					item-title="item_name"
					item-value="item_code"
					:label="__('Item')"
					density="compact"
					variant="outlined"
					hide-details
					clearable
					:custom-filter="() => true"
					class="pos-themed-input pos-list-filter-field"
					@update:search="handleItemSearchUpdate"
					@update:model-value="resetAndLoad"
				/>
				<v-select
					v-model="itemGroupFilter"
					:items="itemGroupOptions"
					item-title="name"
					item-value="name"
					:label="__('Item Group')"
					density="compact"
					variant="outlined"
					hide-details
					clearable
					class="pos-themed-input pos-list-filter-field"
					@update:model-value="resetAndLoad"
				/>
				<v-select
					v-model="warehouseFilter"
					:items="warehouseOptions"
					item-title="warehouse_name"
					item-value="name"
					:label="__('Warehouse')"
					density="compact"
					variant="outlined"
					hide-details
					clearable
					class="pos-themed-input pos-list-filter-field"
					@update:model-value="resetAndLoad"
				/>
				<v-btn variant="text" size="small" class="text-none" @click="clearFilters">
					{{ __("Clear Filters") }}
				</v-btn>
			</div>

			<div v-if="planList.length" class="pos-list-table-wrap">
				<v-data-table
					:headers="listHeaders"
					:items="planList"
					:loading="listLoading"
					density="comfortable"
					hide-default-footer
					:items-per-page="-1"
					class="pos-list-table production-plan-list-table"
					@click:row="(_, row) => openPlanDetail(row.item)"
				>
					<template #item.name="{ item }">
						<span class="pos-list-cell-primary">{{ item.name }}</span>
					</template>
					<template #item.posting_date="{ item }">
						<span class="pos-list-cell-muted">{{ formatDisplayDate(item.posting_date) }}</span>
					</template>
					<template #item.for_warehouse="{ item }">
						<span class="pos-list-cell-truncate" :title="item.for_warehouse">
							{{ item.for_warehouse || "—" }}
						</span>
					</template>
					<template #item.total_planned_qty="{ item }">
						<span class="pos-list-cell-muted">{{ formatQty(item.total_planned_qty) }}</span>
					</template>
					<template #item.workflow_state="{ item }">
						<v-chip size="small" variant="tonal" :color="statusColor(item.workflow_state)">
							{{ item.workflow_state }}
						</v-chip>
					</template>
					<template #item.actions="{ item }">
						<div class="d-flex justify-end ga-1 flex-wrap">
							<v-btn
								v-for="action in item.available_actions"
								:key="action"
								size="small"
								variant="tonal"
								:color="actionColor(action)"
								class="text-none"
								@click.stop="advanceStatus(item.name, action)"
							>
								{{ __(action) }}
							</v-btn>
						</div>
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
							icon="mdi-chevron-left"
							size="small"
							variant="text"
							:disabled="page <= 1 || listLoading"
							@click="goToPage(page - 1)"
						/>
						<span class="pos-list-pagination__page">{{ page }}</span>
						<v-btn
							icon="mdi-chevron-right"
							size="small"
							variant="text"
							:disabled="!hasMore || listLoading"
							@click="goToPage(page + 1)"
						/>
					</div>
				</div>
			</div>

			<div v-else-if="!listLoading" class="pos-list-empty">
				<v-icon size="48" color="primary" class="pos-list-empty__icon">mdi-factory</v-icon>
				<h4 class="pos-list-empty__title">{{ __("No production plans found") }}</h4>
				<p class="pos-list-empty__subtitle">
					{{ hasActiveFilters
						? __("Try different filters or clear them.")
						: __("Create a new production plan to get started.") }}
				</p>
				<v-btn
					v-if="!hasActiveFilters"
					color="primary"
					variant="flat"
					class="text-none mt-2"
					prepend-icon="mdi-plus"
					@click="goToNew"
				>
					{{ __("Create Plan") }}
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
import { useToastStore } from '../../../stores/toastStore';

export default {
	name: 'ProductionPlanList',
	mixins: [format],
	setup() {
		const router = useRouter();
		const toastStore = useToastStore();
		const planList = ref([]);
		const listLoading = ref(false);
		const searchQuery = ref('');
		let searchTimeout = null;

		const page = ref(1);
		const pageSize = ref(20);
		const total = ref(0);
		const hasMore = ref(false);
		const statusCounts = ref({});

		const statusOptions = ['Draft', 'Work In Progress', 'Production Complete', 'Cancelled'];
		const statusFilter = ref(null);
		const fromDate = ref('');
		const toDate = ref('');
		const itemCodeFilter = ref(null);
		const itemGroupFilter = ref(null);
		const warehouseFilter = ref(null);

		const itemSearchQuery = ref('');
		const itemSearchResults = ref([]);
		const itemSearchLoading = ref(false);
		let itemSearchTimeout = null;

		const itemGroupOptions = ref([]);
		const warehouseOptions = ref([]);

		const listHeaders = [
			{ title: __('Plan'), key: 'name', sortable: true },
			{ title: __('Date'), key: 'posting_date', sortable: true },
			{ title: __('Source Warehouse'), key: 'for_warehouse', sortable: true },
			{ title: __('Planned Qty'), key: 'total_planned_qty', sortable: true, align: 'end' },
			{ title: __('Status'), key: 'workflow_state', sortable: true },
			{ title: __('Actions'), key: 'actions', sortable: false, align: 'end', width: '260px' },
		];

		const hasActiveFilters = computed(() =>
			Boolean(
				searchQuery.value ||
					statusFilter.value ||
					fromDate.value ||
					toDate.value ||
					itemCodeFilter.value ||
					itemGroupFilter.value ||
					warehouseFilter.value,
			),
		);

		const paginationLabel = computed(() => {
			if (!total.value) return __('No results');
			const start = (page.value - 1) * pageSize.value + 1;
			const end = Math.min(page.value * pageSize.value, total.value);
			return __('Showing {0}-{1} of {2}', [start, end, total.value]);
		});

		const formatDisplayDate = (value) => {
			if (!value) return '—';
			const parts = String(value).split('-');
			return parts.length === 3 ? `${parts[2]}-${parts[1]}-${parts[0]}` : value;
		};

		const formatQty = (value) => Number(value || 0);

		const loadPlans = async () => {
			listLoading.value = true;
			try {
				const { message } = await frappe.call({
					method: 'posawesome.posawesome.api.production_plans.get_production_plans_list',
					args: {
						page_start: (page.value - 1) * pageSize.value,
						page_length: pageSize.value,
						status: statusFilter.value || undefined,
						from_date: fromDate.value || undefined,
						to_date: toDate.value || undefined,
						item_code: itemCodeFilter.value || undefined,
						item_group: itemGroupFilter.value || undefined,
						warehouse: warehouseFilter.value || undefined,
						search: searchQuery.value || undefined,
					},
				});
				planList.value = message?.plans || [];
				total.value = message?.total || 0;
				hasMore.value = Boolean(message?.has_more);
				statusCounts.value = message?.status_counts || {};
			} catch (e) {
				console.error('Failed to load production plans', e);
				planList.value = [];
				toastStore.show({
					title: e?.message || __('Failed to load production plans'),
					color: 'error',
				});
			} finally {
				listLoading.value = false;
			}
		};

		const resetAndLoad = () => {
			page.value = 1;
			loadPlans();
		};

		const handleSearchUpdate = () => {
			if (searchTimeout) clearTimeout(searchTimeout);
			searchTimeout = setTimeout(resetAndLoad, 300);
		};

		const handleItemSearchUpdate = (term) => {
			if (itemSearchTimeout) clearTimeout(itemSearchTimeout);
			if (!term || term.trim().length < 2) {
				itemSearchResults.value = [];
				return;
			}
			itemSearchTimeout = setTimeout(async () => {
				itemSearchLoading.value = true;
				try {
					const { message } = await frappe.call({
						method: 'posawesome.posawesome.api.production_plans.search_manufacturable_items',
						args: { search_text: term.trim(), limit: 20 },
					});
					itemSearchResults.value = message || [];
				} catch {
					itemSearchResults.value = [];
				} finally {
					itemSearchLoading.value = false;
				}
			}, 300);
		};

		const loadItemGroups = async () => {
			try {
				const { message } = await frappe.call({
					method: 'frappe.client.get_list',
					args: {
						doctype: 'Item Group',
						fields: ['name'],
						filters: { is_group: 0 },
						limit_page_length: 200,
					},
				});
				itemGroupOptions.value = message || [];
			} catch (e) {
				console.error('Failed to load item groups', e);
			}
		};

		const loadWarehouses = async () => {
			try {
				const { message } = await frappe.call({
					method: 'frappe.client.get_list',
					args: {
						doctype: 'Warehouse',
						fields: ['name', 'warehouse_name'],
						filters: { is_group: 0, disabled: 0 },
						limit_page_length: 200,
					},
				});
				warehouseOptions.value = message || [];
			} catch (e) {
				console.error('Failed to load warehouses', e);
			}
		};

		const clearFilters = () => {
			searchQuery.value = '';
			statusFilter.value = null;
			fromDate.value = '';
			toDate.value = '';
			itemCodeFilter.value = null;
			itemGroupFilter.value = null;
			warehouseFilter.value = null;
			resetAndLoad();
		};

		const goToPage = (nextPage) => {
			if (nextPage < 1) return;
			page.value = nextPage;
			loadPlans();
		};

		const statusColor = (status) => {
			const map = {
				Draft: 'grey',
				'Work In Progress': 'orange',
				'Production Complete': 'green',
				Cancelled: 'red',
			};
			return map[status] || 'grey';
		};

		const actionColor = (action) => {
			const map = {
				'Start Production': 'primary',
				'Mark Production Complete': 'success',
				Cancel: 'error',
			};
			return map[action] || 'primary';
		};

		const goToNew = () => {
			router.push('/production-plans/new');
		};

		const advanceStatus = async (name, action) => {
			try {
				await frappe.call({
					method: 'posawesome.posawesome.api.production_plans.advance_production_plan_status',
					args: { name, action },
					freeze: true,
					freeze_message: __('Updating status...'),
				});
				toastStore.show({
					title: __('Production Plan {0} updated', [name]),
					color: 'success',
				});
				await loadPlans();
			} catch (e) {
				toastStore.show({ title: e?.message || __('Failed to update status'), color: 'error' });
			}
		};

		const openPlanDetail = (item) => {
			router.push(`/production-plans/${item.name}`);
		};

		onMounted(() => {
			loadItemGroups();
			loadWarehouses();
			loadPlans();
		});

		return {
			planList,
			listLoading,
			searchQuery,
			listHeaders,
			page,
			pageSize,
			total,
			hasMore,
			statusCounts,
			statusOptions,
			statusFilter,
			fromDate,
			toDate,
			itemCodeFilter,
			itemGroupFilter,
			itemGroupOptions,
			warehouseFilter,
			warehouseOptions,
			itemSearchQuery,
			itemSearchResults,
			itemSearchLoading,
			hasActiveFilters,
			paginationLabel,
			loadPlans,
			resetAndLoad,
			handleSearchUpdate,
			handleItemSearchUpdate,
			clearFilters,
			goToPage,
			formatDisplayDate,
			formatQty,
			statusColor,
			actionColor,
			goToNew,
			advanceStatus,
			openPlanDetail,
		};
	},
};
</script>

<style scoped>
@import '../invoice-shared-styles.css';
</style>
