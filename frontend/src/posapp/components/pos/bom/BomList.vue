<template>
	<div class="pa-0 h-100 invoice-shell pos-list-page">
		<v-card flat class="invoice-section-card pos-themed-card pos-list-card">
			<div class="pos-list-header">
				<div class="pos-list-header__main">
					<p class="pos-list-header__eyebrow">{{ __("Manufacturing") }}</p>
					<h3 class="pos-list-header__title">{{ __("Bill of Materials") }}</h3>
					<p class="pos-list-header__subtitle">
						{{ __("Browse BOMs and the raw materials they consume") }}
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
						{{ __("Create BOM") }}
					</v-btn>
				</div>
			</div>

			<div class="pos-list-stats">
				<div class="pos-list-stat pos-list-stat--primary">
					<span class="pos-list-stat__label">{{ __("Total") }}</span>
					<strong class="pos-list-stat__value">{{ total }}</strong>
				</div>
				<div class="pos-list-stat pos-list-stat--success">
					<span class="pos-list-stat__label">{{ __("Active") }}</span>
					<strong class="pos-list-stat__value">{{ activeCount }}</strong>
				</div>
				<div class="pos-list-stat pos-list-stat--warning">
					<span class="pos-list-stat__label">{{ __("Default") }}</span>
					<strong class="pos-list-stat__value">{{ defaultCount }}</strong>
				</div>
			</div>

			<div class="pos-list-toolbar">
				<v-text-field
					v-model="searchQuery"
					:label="__('Search BOM or item')"
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
						@click="loadBoms"
					>
						{{ __("Sync") }}
					</v-btn>
				</div>
			</div>

			<div class="pos-list-filters">
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
					v-model="isActiveFilter"
					:items="yesNoOptions"
					item-title="label"
					item-value="value"
					:label="__('Active')"
					density="compact"
					variant="outlined"
					hide-details
					clearable
					class="pos-themed-input pos-list-filter-field"
					@update:model-value="resetAndLoad"
				/>
				<v-select
					v-model="isDefaultFilter"
					:items="yesNoOptions"
					item-title="label"
					item-value="value"
					:label="__('Default')"
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

			<div v-if="bomList.length" class="pos-list-table-wrap">
				<v-data-table
					:headers="listHeaders"
					:items="bomList"
					:loading="listLoading"
					density="comfortable"
					hide-default-footer
					:items-per-page="-1"
					class="pos-list-table"
					@click:row="(_, row) => openBomDetail(row.item)"
				>
					<template #item.name="{ item }">
						<span class="pos-list-cell-primary">{{ item.name }}</span>
					</template>
					<template #item.item="{ item }">
						<div>
							<div>{{ item.item_name }}</div>
							<div class="text-caption text-medium-emphasis">{{ item.item }}</div>
						</div>
					</template>
					<template #item.quantity="{ item }">
						<span class="pos-list-cell-muted">{{ formatQty(item.quantity) }} {{ item.uom }}</span>
					</template>
					<template #item.total_weight="{ item }">
						<span class="pos-list-cell-muted">{{ Number(item.total_weight || 0).toFixed(2) }}</span>
					</template>
					<template #item.is_active="{ item }">
						<v-chip size="small" variant="tonal" :color="item.is_active ? 'green' : 'grey'">
							{{ item.is_active ? __("Yes") : __("No") }}
						</v-chip>
					</template>
					<template #item.is_default="{ item }">
						<v-chip size="small" variant="tonal" :color="item.is_default ? 'primary' : 'grey'">
							{{ item.is_default ? __("Yes") : __("No") }}
						</v-chip>
					</template>
					<template #item.status="{ item }">
						<v-chip size="small" variant="tonal" :color="statusColor(item.status)">
							{{ item.status }}
						</v-chip>
					</template>
					<template #item.actions="{ item }">
						<div class="d-flex justify-end">
							<RowActionsMenu
								:actions="rowActions(item)"
								:loading="actionLoadingName === item.name"
								@action="(key) => handleRowAction(key, item)"
							/>
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
				<v-icon size="48" color="primary" class="pos-list-empty__icon">mdi-clipboard-list-outline</v-icon>
				<h4 class="pos-list-empty__title">{{ __("No BOMs found") }}</h4>
				<p class="pos-list-empty__subtitle">
					{{ hasActiveFilters
						? __("Try different filters or clear them.")
						: __("Create a new BOM to get started.") }}
				</p>
				<v-btn
					v-if="!hasActiveFilters"
					color="primary"
					variant="flat"
					class="text-none mt-2"
					prepend-icon="mdi-plus"
					@click="goToNew"
				>
					{{ __("Create BOM") }}
				</v-btn>
			</div>

			<div v-else class="pos-list-empty">
				<v-progress-circular indeterminate color="primary" />
			</div>
		</v-card>

		<ConfirmActionDialog
			v-model="confirmDialog"
			:title="confirmDialogTitle"
			:message="confirmDialogMessage"
			:confirm-label="confirmDialogActionLabel"
			:confirm-color="confirmDialogColor"
			:loading="actionLoadingName === confirmDialogItem?.name"
			@confirm="runConfirmedAction"
		/>
	</div>
</template>

<script>
import { ref, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useToastStore } from '../../../stores/toastStore';
import RowActionsMenu from '../shared/RowActionsMenu.vue';
import ConfirmActionDialog from '../shared/ConfirmActionDialog.vue';

export default {
	name: 'BomList',
	components: { RowActionsMenu, ConfirmActionDialog },
	setup() {
		const router = useRouter();
		const toastStore = useToastStore();

		const isSystemManager = computed(() =>
			(frappe?.boot?.user?.roles || []).includes('System Manager'),
		);

		const actionLoadingName = ref(null);
		const confirmDialog = ref(false);
		const confirmDialogItem = ref(null);
		const confirmDialogAction = ref(null);
		const confirmDialogTitle = ref('');
		const confirmDialogMessage = ref('');
		const confirmDialogActionLabel = ref('');
		const confirmDialogColor = ref('error');

		const canCancel = (item) => isSystemManager.value && item.docstatus === 1;
		// Delete is hidden from the UI -- users are no longer allowed to delete
		// Draft/Cancelled BOMs from POS Awesome.
		const canDelete = () => false;

		const rowActions = (item) => [
			{ key: 'view', label: __('View'), icon: 'mdi-eye-outline' },
			{
				key: 'cancel',
				label: __('Cancel'),
				icon: 'mdi-cancel',
				color: 'error',
				show: canCancel(item),
			},
			{
				key: 'delete',
				label: __('Delete'),
				icon: 'mdi-delete-outline',
				color: 'error',
				show: canDelete(item),
			},
		];

		const handleRowAction = (key, item) => {
			if (key === 'view') {
				openBomDetail(item);
			} else if (key === 'cancel') {
				openCancelConfirm(item);
			} else if (key === 'delete') {
				openDeleteConfirm(item);
			}
		};

		const openCancelConfirm = (item) => {
			confirmDialogItem.value = item;
			confirmDialogAction.value = 'cancel';
			confirmDialogTitle.value = __('Cancel BOM');
			confirmDialogMessage.value = __(
				'This will cancel {0}. This cannot be undone. Continue?',
				[item.name],
			);
			confirmDialogActionLabel.value = __('Cancel BOM');
			confirmDialogColor.value = 'error';
			confirmDialog.value = true;
		};

		const openDeleteConfirm = (item) => {
			confirmDialogItem.value = item;
			confirmDialogAction.value = 'delete';
			confirmDialogTitle.value = __('Delete BOM');
			confirmDialogMessage.value = __(
				'This will permanently delete cancelled BOM {0}. This cannot be undone. Continue?',
				[item.name],
			);
			confirmDialogActionLabel.value = __('Delete');
			confirmDialogColor.value = 'error';
			confirmDialog.value = true;
		};

		const runConfirmedAction = async () => {
			const item = confirmDialogItem.value;
			const action = confirmDialogAction.value;
			if (!item || !action) return;

			actionLoadingName.value = item.name;
			try {
				if (action === 'cancel') {
					await frappe.call({
						method: 'posawesome.posawesome.api.boms.cancel_bom',
						args: { name: item.name },
					});
					toastStore.show({ title: __('{0} cancelled', [item.name]), color: 'success' });
				} else if (action === 'delete') {
					await frappe.call({
						method: 'posawesome.posawesome.api.boms.delete_cancelled_bom',
						args: { name: item.name },
					});
					toastStore.show({ title: __('{0} deleted', [item.name]), color: 'success' });
				}
				confirmDialog.value = false;
				await loadBoms();
			} catch (e) {
				toastStore.show({ title: e?.message || __('Action failed'), color: 'error' });
			} finally {
				actionLoadingName.value = null;
			}
		};

		const bomList = ref([]);
		const listLoading = ref(false);
		const searchQuery = ref('');
		let searchTimeout = null;

		const page = ref(1);
		const pageSize = ref(20);
		const total = ref(0);
		const totalPages = computed(() => Math.max(1, Math.ceil(total.value / (pageSize.value || 1))));
		const hasMore = ref(false);

		const itemCodeFilter = ref(null);
		const isActiveFilter = ref(null);
		const isDefaultFilter = ref(null);
		const yesNoOptions = [
			{ label: __('Yes'), value: 1 },
			{ label: __('No'), value: 0 },
		];

		const itemSearchQuery = ref('');
		const itemSearchResults = ref([]);
		const itemSearchLoading = ref(false);
		let itemSearchTimeout = null;

		const listHeaders = [
			{ title: __('BOM'), key: 'name', sortable: true },
			{ title: __('Item'), key: 'item', sortable: true },
			{ title: __('Qty'), key: 'quantity', sortable: true, align: 'end' },
			{ title: __('Weight'), key: 'total_weight', sortable: true, align: 'end' },
			{ title: __('Active'), key: 'is_active', sortable: true },
			{ title: __('Default'), key: 'is_default', sortable: true },
			{ title: __('Status'), key: 'status', sortable: true },
			{ title: __('Actions'), key: 'actions', sortable: false, align: 'end', width: '120px' },
		];

		const activeCount = computed(() => bomList.value.filter((row) => row.is_active).length);
		const defaultCount = computed(() => bomList.value.filter((row) => row.is_default).length);

		const hasActiveFilters = computed(() =>
			Boolean(
				searchQuery.value ||
					itemCodeFilter.value ||
					isActiveFilter.value !== null ||
					isDefaultFilter.value !== null,
			),
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

		const formatQty = (value) => Number(value || 0);

		const loadBoms = async () => {
			listLoading.value = true;
			try {
				const { message } = await frappe.call({
					method: 'posawesome.posawesome.api.boms.get_boms_list',
					args: {
						page_start: (page.value - 1) * pageSize.value,
						page_length: pageSize.value,
						item_code: itemCodeFilter.value || undefined,
						is_active: isActiveFilter.value === null ? undefined : isActiveFilter.value,
						is_default: isDefaultFilter.value === null ? undefined : isDefaultFilter.value,
						search: searchQuery.value || undefined,
					},
				});
				bomList.value = message?.boms || [];
				total.value = message?.total || 0;
				hasMore.value = Boolean(message?.has_more);
			} catch (e) {
				console.error('Failed to load BOMs', e);
				bomList.value = [];
				toastStore.show({ title: e?.message || __('Failed to load BOMs'), color: 'error' });
			} finally {
				listLoading.value = false;
			}
		};

		const resetAndLoad = () => {
			page.value = 1;
			loadBoms();
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
						method: 'posawesome.posawesome.api.boms.search_bom_items',
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

		const clearFilters = () => {
			searchQuery.value = '';
			itemCodeFilter.value = null;
			isActiveFilter.value = null;
			isDefaultFilter.value = null;
			resetAndLoad();
		};

		const goToPage = (nextPage) => {
			if (nextPage < 1) return;
			page.value = nextPage;
			loadBoms();
		};

		const statusColor = (status) => {
			const map = { Draft: 'grey', Submitted: 'green', Cancelled: 'red' };
			return map[status] || 'grey';
		};

		const goToNew = () => {
			router.push('/boms/new');
		};

		const openBomDetail = (item) => {
			router.push(`/boms/${item.name}`);
		};

		onMounted(() => {
			loadBoms();
		});

		return {
			bomList,
			listLoading,
			searchQuery,
			listHeaders,
			page,
			pageSize,
			total,
			totalPages,
			pageNumbers,
			hasMore,
			activeCount,
			defaultCount,
			itemCodeFilter,
			isActiveFilter,
			isDefaultFilter,
			yesNoOptions,
			itemSearchQuery,
			itemSearchResults,
			itemSearchLoading,
			hasActiveFilters,
			paginationLabel,
			loadBoms,
			resetAndLoad,
			handleSearchUpdate,
			handleItemSearchUpdate,
			clearFilters,
			goToPage,
			formatQty,
			statusColor,
			goToNew,
			openBomDetail,
			isSystemManager,
			actionLoadingName,
			confirmDialog,
			confirmDialogItem,
			confirmDialogTitle,
			confirmDialogMessage,
			confirmDialogActionLabel,
			confirmDialogColor,
			rowActions,
			handleRowAction,
			runConfirmedAction,
		};
	},
};
</script>

<style scoped>
@import '../invoice-shared-styles.css';
</style>
