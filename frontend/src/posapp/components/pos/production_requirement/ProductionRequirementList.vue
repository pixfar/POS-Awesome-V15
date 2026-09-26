<template>
	<div class="pa-0 h-100 invoice-shell pos-list-page">
		<v-card flat class="invoice-section-card pos-themed-card pos-list-card">
			<div class="pos-list-header">
				<div class="pos-list-header__main">
					<p class="pos-list-header__eyebrow">{{ __("Manufacturing") }}</p>
					<h3 class="pos-list-header__title">{{ __("Production Requirements") }}</h3>
					<p class="pos-list-header__subtitle">
						{{ __("Shortage and planned quantity per item") }}
					</p>
				</div>
				<div class="pos-list-header__actions">
					<v-btn
						v-if="canCreate"
						color="primary"
						variant="flat"
						class="text-none"
						prepend-icon="mdi-plus"
						@click="goToNew"
					>
						{{ __("New Requirement") }}
					</v-btn>
				</div>
			</div>

			<div class="pos-list-stats">
				<div class="pos-list-stat pos-list-stat--primary">
					<span class="pos-list-stat__label">{{ __("Total") }}</span>
					<strong class="pos-list-stat__value">{{ total }}</strong>
				</div>
				<div class="pos-list-stat pos-list-stat--danger">
					<span class="pos-list-stat__label">{{ __("Total Shortage Qty") }}</span>
					<strong class="pos-list-stat__value">{{ formatQty(summary.total_shortage_qty) }}</strong>
				</div>
				<div class="pos-list-stat pos-list-stat--success">
					<span class="pos-list-stat__label">{{ __("Total Plan Qty") }}</span>
					<strong class="pos-list-stat__value">{{ formatQty(summary.total_plan_qty) }}</strong>
				</div>
			</div>

			<div class="pos-list-toolbar">
				<v-text-field
					v-model="searchQuery"
					:label="__('Search ID, warehouse or remarks')"
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
						@click="loadList"
					>
						{{ __("Sync") }}
					</v-btn>
				</div>
			</div>

			<div class="pos-list-filters">
				<v-select
					v-model="statusFilter"
					:items="statusFilterOptions"
					:label="__('Status')"
					density="compact"
					variant="outlined"
					hide-details
					clearable
					class="pos-themed-input pos-list-filter-field"
					@update:model-value="resetAndLoad"
				/>
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
				<v-autocomplete
					v-if="canSeeAllWarehouses"
					v-model="warehouseFilter"
					:items="warehouseOptions"
					:item-title="(w) => w.warehouse_name || w.name"
					item-value="name"
					:label="__('Warehouse')"
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
					:item-title="(item) => `${item.item_name} - ${item.item_code}`"
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
				<v-autocomplete
					v-model="itemGroupFilter"
					:items="filterOptions.item_groups"
					:label="__('Item Group')"
					density="compact"
					variant="outlined"
					hide-details
					clearable
					class="pos-themed-input pos-list-filter-field"
					@update:model-value="resetAndLoad"
				/>
				<v-autocomplete
					v-model="productionGroupFilter"
					:items="filterOptions.production_groups"
					:label="__('Production Group')"
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

			<div v-if="rows.length" class="pos-list-table-wrap">
				<v-data-table
					:headers="listHeaders"
					:items="rows"
					:loading="listLoading"
					density="comfortable"
					hide-default-footer
					:items-per-page="-1"
					class="pos-list-table"
					@click:row="(_, row) => openDetail(row.item)"
				>
					<template #item.name="{ item }">
						<span class="pos-list-cell-primary">{{ item.name }}</span>
					</template>
					<template #item.production_date="{ item }">
						<span class="pos-list-cell-muted">{{ formatDisplayDate(item.production_date) }}</span>
					</template>
					<template #item.posting_date="{ item }">
						<span class="pos-list-cell-muted">{{ formatDisplayDate(item.posting_date) }}</span>
					</template>
					<template #item.warehouse="{ item }">
						<span class="pos-list-cell-truncate" :title="item.warehouse">
							{{ item.warehouse_name || item.warehouse }}
						</span>
					</template>
					<template #item.production_by="{ item }">
						<span class="pos-list-cell-truncate">{{
							item.production_by_name || item.production_by
						}}</span>
					</template>
					<template #item.status="{ item }">
						<v-menu v-if="item.can_edit" location="bottom start">
							<template #activator="{ props: menuProps }">
								<v-chip
									v-bind="menuProps"
									size="small"
									variant="tonal"
									:color="statusColor(item.status)"
									append-icon="mdi-chevron-down"
									:title="__('Change status')"
									@click.stop
								>
									{{ __(item.status) }}
								</v-chip>
							</template>
							<v-list density="compact" min-width="170">
								<v-list-item
									v-for="option in statusOptions"
									:key="option"
									:disabled="option === item.status"
									@click="changeStatus(item, option)"
								>
									<template #prepend>
										<v-icon size="12" :color="statusColor(option)">mdi-circle</v-icon>
									</template>
									<v-list-item-title>{{ __(option) }}</v-list-item-title>
								</v-list-item>
							</v-list>
						</v-menu>
						<v-chip v-else size="small" variant="tonal" :color="statusColor(item.status)">
							{{ __(item.status) }}
						</v-chip>
					</template>
					<template #item.total_shortage_qty="{ item }">
						<span
							:class="
								item.total_shortage_qty > 0
									? 'text-error font-weight-bold'
									: 'pos-list-cell-muted'
							"
						>
							{{ formatQty(item.total_shortage_qty) }}
						</span>
					</template>
					<template #item.total_plan_qty="{ item }">
						<span class="font-weight-bold">{{ formatQty(item.total_plan_qty) }}</span>
					</template>
					<template #item.actions="{ item }">
						<div class="d-flex justify-end">
							<RowActionsMenu
								:actions="rowActions(item)"
								@action="(key) => handleRowAction(key, item)"
							/>
						</div>
					</template>
				</v-data-table>

				<div class="pos-list-pagination">
					<div class="pos-list-pagination__info">{{ paginationLabel }}</div>
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
					</div>
				</div>
			</div>

			<div v-else-if="!listLoading" class="pos-list-empty">
				<v-icon size="48" color="primary" class="pos-list-empty__icon"
					>mdi-clipboard-check-outline</v-icon
				>
				<h4 class="pos-list-empty__title">{{ __("No production requirements found") }}</h4>
				<p class="pos-list-empty__subtitle">
					{{
						hasActiveFilters
							? __("Try different filters or clear them.")
							: __("Create a new production requirement to get started.")
					}}
				</p>
				<v-btn
					v-if="!hasActiveFilters && canCreate"
					color="primary"
					variant="flat"
					class="text-none mt-2"
					prepend-icon="mdi-plus"
					@click="goToNew"
				>
					{{ __("New Requirement") }}
				</v-btn>
			</div>

			<div v-else class="pos-list-empty">
				<v-progress-circular indeterminate color="primary" />
			</div>
		</v-card>
	</div>
</template>

<script>
import { ref, reactive, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import { useToastStore } from "../../../stores/toastStore";
import DateFilterField from "../shared/DateFilterField.vue";
import RowActionsMenu from "../shared/RowActionsMenu.vue";
import { useWarehouseFilterOptions } from "../shared/useWarehouseFilterOptions";
import { formatDisplayDate } from "../shared/docStatusUtils";
import { normalizeBengaliNumbers } from "../../../composables/pos/items/useItemSearch";
import { useListFilterPersistence } from "../../../composables/useListFilterPersistence";
import { isPosWarehouseSwitcher } from "../../../utils/posWarehouseAccess";
import {
	formatQty,
	PRODUCTION_REQUIREMENT_STATUSES,
	productionRequirementStatusColor,
} from "./productionRequirementUtils";

const API = "posawesome.posawesome.api.production_requirements";

export default {
	name: "ProductionRequirementList",
	components: { DateFilterField, RowActionsMenu },
	setup() {
		const router = useRouter();
		const toastStore = useToastStore();
		const { warehouseOptions, loadWarehouseOptions } = useWarehouseFilterOptions();
		const canSeeAllWarehouses = isPosWarehouseSwitcher();

		const rows = ref([]);
		const listLoading = ref(false);
		const canCreate = ref(true);
		const summary = reactive({ total_shortage_qty: 0, total_plan_qty: 0 });
		const searchQuery = ref("");
		let searchTimeout = null;

		const page = ref(1);
		const pageSize = ref(20);
		const total = ref(0);
		const hasMore = ref(false);
		const totalPages = computed(() => Math.max(1, Math.ceil(total.value / (pageSize.value || 1))));

		const statusFilter = ref(null);
		const statusCounts = ref({});
		// "Pending (4)" etc. -- counts come from the server and ignore the status filter itself.
		const statusFilterOptions = computed(() =>
			PRODUCTION_REQUIREMENT_STATUSES.map((s) => ({
				title: `${__(s)} (${statusCounts.value[s] || 0})`,
				value: s,
			})),
		);
		const fromDate = ref("");
		const toDate = ref("");
		const warehouseFilter = ref(null);
		const itemCodeFilter = ref(null);
		const itemGroupFilter = ref(null);
		const productionGroupFilter = ref(null);
		const filterOptions = reactive({ item_groups: [], production_groups: [] });

		const itemSearchQuery = ref("");
		const itemSearchResults = ref([]);
		const itemSearchLoading = ref(false);
		let itemSearchTimeout = null;

		const { loadSavedFilters, saveFilters, clearSavedFilters } = useListFilterPersistence(
			"posa_filter_production_requirement",
			{
				searchQuery,
				statusFilter,
				fromDate,
				toDate,
				warehouseFilter,
				itemCodeFilter,
				itemSearchResults,
				itemGroupFilter,
				productionGroupFilter,
				page,
			},
		);

		const listHeaders = [
			{ title: __("ID"), key: "name", sortable: true },
			{ title: __("Production Date"), key: "production_date", sortable: true },
			{ title: __("Posting Date"), key: "posting_date", sortable: true },
			{ title: __("Warehouse"), key: "warehouse", sortable: true },
			{ title: __("Production By"), key: "production_by", sortable: true },
			{ title: __("Items"), key: "item_count", sortable: true, align: "end" },
			{ title: __("Status"), key: "status", sortable: true },
			{ title: __("Shortage Qty"), key: "total_shortage_qty", sortable: true, align: "end" },
			{ title: __("Plan Qty"), key: "total_plan_qty", sortable: true, align: "end" },
			{ title: "", key: "actions", sortable: false, align: "end" },
		];

		const hasActiveFilters = computed(() =>
			Boolean(
				searchQuery.value ||
					statusFilter.value ||
					fromDate.value ||
					toDate.value ||
					warehouseFilter.value ||
					itemCodeFilter.value ||
					itemGroupFilter.value ||
					productionGroupFilter.value,
			),
		);

		const paginationLabel = computed(() =>
			total.value ? __("Page {0} of {1}", [page.value, totalPages.value]) : __("No results"),
		);

		const pageNumbers = computed(() => {
			const windowSize = 5;
			let start = Math.max(1, page.value - Math.floor(windowSize / 2));
			const end = Math.min(totalPages.value, start + windowSize - 1);
			start = Math.max(1, end - windowSize + 1);
			const pages = [];
			for (let p = start; p <= end; p++) pages.push(p);
			return pages;
		});

		const loadList = async () => {
			listLoading.value = true;
			try {
				const { message } = await frappe.call({
					method: `${API}.get_production_requirements_list`,
					args: {
						page_start: (page.value - 1) * pageSize.value,
						page_length: pageSize.value,
						status: statusFilter.value || undefined,
						from_date: fromDate.value || undefined,
						to_date: toDate.value || undefined,
						warehouse: warehouseFilter.value || undefined,
						item_code: itemCodeFilter.value || undefined,
						item_group: itemGroupFilter.value || undefined,
						production_group: productionGroupFilter.value || undefined,
						search: searchQuery.value || undefined,
					},
				});
				rows.value = message?.rows || [];
				total.value = message?.total || 0;
				hasMore.value = Boolean(message?.has_more);
				canCreate.value = message?.can_create !== false;
				statusCounts.value = message?.status_counts || {};
				summary.total_shortage_qty = message?.total_shortage_qty || 0;
				summary.total_plan_qty = message?.total_plan_qty || 0;
				saveFilters();
			} catch (e) {
				rows.value = [];
				toastStore.show({
					title: e?.message || __("Failed to load production requirements"),
					color: "error",
				});
			} finally {
				listLoading.value = false;
			}
		};

		const resetAndLoad = () => {
			page.value = 1;
			loadList();
		};

		const handleSearchUpdate = () => {
			if (searchTimeout) clearTimeout(searchTimeout);
			searchTimeout = setTimeout(resetAndLoad, 300);
		};

		const handleItemSearchUpdate = (term) => {
			if (itemSearchTimeout) clearTimeout(itemSearchTimeout);
			if (!term || term.trim().length < 2) return;
			itemSearchTimeout = setTimeout(async () => {
				itemSearchLoading.value = true;
				try {
					const { message } = await frappe.call({
						method: "posawesome.posawesome.api.material_transfers.search_items",
						args: { search_text: normalizeBengaliNumbers(term.trim()), limit: 20 },
					});
					itemSearchResults.value = message || [];
				} catch {
					itemSearchResults.value = [];
				} finally {
					itemSearchLoading.value = false;
				}
			}, 300);
		};

		const loadFilterOptions = async () => {
			try {
				const { message } = await frappe.call({ method: `${API}.get_filter_options` });
				filterOptions.item_groups = message?.item_groups || [];
				filterOptions.production_groups = message?.production_groups || [];
			} catch (e) {
				console.error("Failed to load filter options", e);
			}
		};

		const clearFilters = () => {
			searchQuery.value = "";
			statusFilter.value = null;
			fromDate.value = "";
			toDate.value = "";
			warehouseFilter.value = null;
			itemCodeFilter.value = null;
			itemGroupFilter.value = null;
			productionGroupFilter.value = null;
			itemSearchResults.value = [];
			clearSavedFilters();
			resetAndLoad();
		};

		const goToPage = (nextPage) => {
			if (nextPage < 1 || nextPage > totalPages.value) return;
			page.value = nextPage;
			loadList();
		};

		const goToNew = () => router.push("/production-requirements/new");
		const openDetail = (item) => router.push(`/production-requirements/${encodeURIComponent(item.name)}`);

		const rowActions = (item) => [
			{ key: "view", label: __("View"), icon: "mdi-eye-outline" },
			...(item.can_edit
				? [{ key: "edit", label: __("Edit"), icon: "mdi-pencil-outline", color: "primary" }]
				: []),
		];

		const handleRowAction = (key, item) => {
			if (key === "view") openDetail(item);
			else if (key === "edit")
				router.push(`/production-requirements/${encodeURIComponent(item.name)}/edit`);
		};

		const changeStatus = async (item, status) => {
			try {
				await frappe.call({
					method: `${API}.set_production_requirement_status`,
					args: { name: item.name, status },
				});
				toastStore.show({ title: __("{0} marked {1}", [item.name, __(status)]), color: "success" });
				await loadList();
			} catch (e) {
				toastStore.show({ title: e?.message || __("Failed to update status"), color: "error" });
			}
		};

		onMounted(() => {
			loadSavedFilters();
			loadFilterOptions();
			if (canSeeAllWarehouses) loadWarehouseOptions();
			loadList();
		});

		return {
			rows,
			listLoading,
			canCreate,
			summary,
			searchQuery,
			listHeaders,
			page,
			pageSize,
			total,
			hasMore,
			pageNumbers,
			paginationLabel,
			fromDate,
			toDate,
			canSeeAllWarehouses,
			warehouseFilter,
			warehouseOptions,
			itemCodeFilter,
			itemSearchQuery,
			itemSearchResults,
			itemSearchLoading,
			itemGroupFilter,
			productionGroupFilter,
			filterOptions,
			hasActiveFilters,
			loadList,
			resetAndLoad,
			handleSearchUpdate,
			handleItemSearchUpdate,
			clearFilters,
			goToPage,
			goToNew,
			openDetail,
			rowActions,
			handleRowAction,
			formatDisplayDate,
			formatQty,
			statusFilter,
			statusFilterOptions,
			statusOptions: PRODUCTION_REQUIREMENT_STATUSES,
			statusColor: productionRequirementStatusColor,
			changeStatus,
		};
	},
};
</script>

<style scoped>
@import "../invoice-shared-styles.css";
</style>
