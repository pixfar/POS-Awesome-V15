<template>
	<div class="pa-0 h-100 invoice-shell pos-list-page">
		<v-card flat class="invoice-section-card pos-themed-card pos-list-card">
			<div class="pos-list-header">
				<div class="pos-list-header__main">
					<p class="pos-list-header__eyebrow">{{ __("Stock Movement") }}</p>
					<h3 class="pos-list-header__title">{{ __("Requisitions") }}</h3>
					<p class="pos-list-header__subtitle">
						{{ __("Track warehouse requisitions and their approval status") }}
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
						{{ __("New Requisition") }}
					</v-btn>
				</div>
			</div>

			<div class="pos-list-stats">
				<div class="pos-list-stat pos-list-stat--primary">
					<span class="pos-list-stat__label">{{ __("Total") }}</span>
					<strong class="pos-list-stat__value">{{ total }}</strong>
				</div>
				<div class="pos-list-stat pos-list-stat--warning">
					<span class="pos-list-stat__label">{{ __("Sent") }}</span>
					<strong class="pos-list-stat__value">{{ statusCounts.Sent || 0 }}</strong>
				</div>
				<div class="pos-list-stat pos-list-stat--success">
					<span class="pos-list-stat__label">{{ __("Received") }}</span>
					<strong class="pos-list-stat__value">{{ statusCounts.Received || 0 }}</strong>
				</div>
				<div class="pos-list-stat">
					<span class="pos-list-stat__label">{{ __("Rejected") }}</span>
					<strong class="pos-list-stat__value">{{ statusCounts.Rejected || 0 }}</strong>
				</div>
			</div>

			<div class="pos-list-toolbar">
				<v-text-field
					v-model="searchQuery"
					:label="__('Search requisition or warehouse')"
					density="compact"
					variant="solo"
					hide-details
					clearable
					prepend-inner-icon="mdi-magnify"
					class="pos-themed-input pos-list-search"
					@update:model-value="handleSearchUpdate"
				/>
				<div class="pos-list-toolbar__filters">
					<v-switch
						v-model="mineOnly"
						density="compact"
						hide-details
						color="primary"
						:label="__('My Requisitions')"
						@update:model-value="resetAndLoad"
					/>
					<v-btn
						variant="tonal"
						size="small"
						color="primary"
						prepend-icon="mdi-sync"
						:loading="listLoading"
						class="text-none"
						@click="loadRequisitions"
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

			<div v-if="requisitionList.length" class="pos-list-table-wrap">
				<v-data-table
					:headers="listHeaders"
					:items="requisitionList"
					:loading="listLoading"
					density="comfortable"
					hide-default-footer
					:items-per-page="-1"
					class="pos-list-table requisition-list-table"
					@click:row="(_, row) => openRequisitionDetail(row.item)"
				>
					<template #item.name="{ item }">
						<span class="pos-list-cell-primary">{{ item.name }}</span>
					</template>
					<template #item.transaction_date="{ item }">
						<span class="pos-list-cell-muted">{{ formatDisplayDate(item.transaction_date) }}</span>
					</template>
					<template #item.source_warehouse="{ item }">
						<span class="pos-list-cell-truncate" :title="item.source_warehouse">
							{{ item.source_warehouse }}
						</span>
					</template>
					<template #item.target_warehouse="{ item }">
						<span class="pos-list-cell-truncate" :title="item.target_warehouse">
							{{ item.target_warehouse }}
						</span>
					</template>
					<template #item.transfer_status="{ item }">
						<v-chip size="small" variant="tonal" :color="statusColor(displayStatus(item))">
							{{ displayStatus(item) }}
						</v-chip>
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
				<v-icon size="48" color="primary" class="pos-list-empty__icon">mdi-clipboard-text-outline</v-icon>
				<h4 class="pos-list-empty__title">{{ __("No requisitions found") }}</h4>
				<p class="pos-list-empty__subtitle">
					{{ hasActiveFilters
						? __("Try different filters or clear them.")
						: __("Create a new requisition to request stock from another warehouse.") }}
				</p>
				<v-btn
					v-if="!hasActiveFilters"
					color="primary"
					variant="flat"
					class="text-none mt-2"
					prepend-icon="mdi-plus"
					@click="goToNew"
				>
					{{ __("New Requisition") }}
				</v-btn>
			</div>

			<div v-else class="pos-list-empty">
				<v-progress-circular indeterminate color="primary" />
			</div>
		</v-card>

		<ConfirmActionDialog
			v-model="confirmDialogOpen"
			:title="confirmDialogTitle"
			:message="confirmDialogMessage"
			:confirm-label="__(pendingAction?.status || 'Confirm')"
			:confirm-color="pendingAction?.status === 'Received' ? 'success' : 'error'"
			:loading="confirmLoading"
			@confirm="performUpdateStatus"
		/>
	</div>
</template>

<script>
import { ref, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import format from '../../../format';
import { useToastStore } from '../../../stores/toastStore';
import DateFilterField from '../shared/DateFilterField.vue';
import ConfirmActionDialog from '../shared/ConfirmActionDialog.vue';
import RowActionsMenu from '../shared/RowActionsMenu.vue';

const STATUS_CONFIRM_MESSAGES = {
	Received: __('Mark this requisition as Received? This confirms the stock transfer is complete.'),
	Rejected: __('Reject this requisition? This cannot be undone.'),
	Cancel: __('Cancel this requisition? This cannot be undone.'),
	Delete: __('Permanently delete this cancelled requisition? This cannot be undone.'),
};

export default {
	name: 'RequisitionList',
	components: { DateFilterField, ConfirmActionDialog, RowActionsMenu },
	mixins: [format],
	setup() {
		const router = useRouter();
		const toastStore = useToastStore();

		const isSystemManager = computed(() =>
			(frappe?.boot?.user?.roles || []).includes('System Manager'),
		);

		const requisitionList = ref([]);
		const listLoading = ref(false);
		const mineOnly = ref(false);
		const searchQuery = ref('');
		let searchTimeout = null;

		const page = ref(1);
		const pageSize = ref(20);
		const total = ref(0);
		const totalPages = computed(() => Math.max(1, Math.ceil(total.value / (pageSize.value || 1))));
		const hasMore = ref(false);
		const statusCounts = ref({});

		const statusOptions = ['Sent', 'Received', 'Rejected'];
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
			{ title: __('Requisition'), key: 'name', sortable: true },
			{ title: __('Date'), key: 'transaction_date', sortable: true },
			{ title: __('From'), key: 'source_warehouse', sortable: true },
			{ title: __('To'), key: 'target_warehouse', sortable: true },
			{ title: __('Status'), key: 'transfer_status', sortable: true },
			{ title: __('Actions'), key: 'actions', sortable: false, align: 'end', width: '180px' },
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

		const loadRequisitions = async () => {
			listLoading.value = true;
			try {
				const { message } = await frappe.call({
					method: 'posawesome.posawesome.api.requisitions.get_requisitions_list',
					args: {
						page_start: (page.value - 1) * pageSize.value,
						page_length: pageSize.value,
						mine_only: mineOnly.value ? 1 : 0,
						status: statusFilter.value || undefined,
						from_date: fromDate.value || undefined,
						to_date: toDate.value || undefined,
						item_code: itemCodeFilter.value || undefined,
						item_group: itemGroupFilter.value || undefined,
						warehouse: warehouseFilter.value || undefined,
						search: searchQuery.value || undefined,
					},
				});
				requisitionList.value = message?.requisitions || [];
				total.value = message?.total || 0;
				hasMore.value = Boolean(message?.has_more);
				statusCounts.value = message?.status_counts || {};
			} catch (e) {
				console.error('Failed to load requisitions', e);
				requisitionList.value = [];
			} finally {
				listLoading.value = false;
			}
		};

		const resetAndLoad = () => {
			page.value = 1;
			loadRequisitions();
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
						method: 'posawesome.posawesome.api.requisitions.search_items',
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
			loadRequisitions();
		};

		const statusColor = (status) => {
			const map = {
				Sent: 'orange',
				Received: 'green',
				Rejected: 'red',
				Cancelled: 'red',
				Draft: 'grey',
			};
			return map[status] || 'grey';
		};

		// A Requisition can be cancelled (docstatus=2) independently of its
		// transfer_status label (Sent/Received/Rejected never changes on
		// cancel) -- show the real docstatus-derived state so a cancelled row
		// doesn't misleadingly still read "Sent" in orange.
		const displayStatus = (item) => {
			if (item.docstatus === 2) return __('Cancelled');
			if (item.docstatus === 0) return __('Draft');
			return item.transfer_status;
		};

		const rowActions = (item) => [
			{ key: 'view', label: __('View'), icon: 'mdi-eye-outline' },
			{
				key: 'received',
				label: __('Received'),
				icon: 'mdi-check-circle-outline',
				color: 'success',
				show: item.can_manage_status,
			},
			{
				key: 'rejected',
				label: __('Rejected'),
				icon: 'mdi-close-circle-outline',
				color: 'error',
				show: item.can_manage_status,
			},
			{
				key: 'cancel',
				label: __('Cancel'),
				icon: 'mdi-cancel',
				color: 'error',
				show: isSystemManager.value && item.docstatus === 1,
			},
			{
				key: 'delete',
				label: __('Delete'),
				icon: 'mdi-delete-outline',
				color: 'error',
				show: item.docstatus === 0 || item.docstatus === 2,
			},
		];

		const handleRowAction = (key, item) => {
			if (key === 'view') {
				openRequisitionDetail(item);
			} else if (key === 'received') {
				requestUpdateStatus(item.name, 'Received');
			} else if (key === 'rejected') {
				requestUpdateStatus(item.name, 'Rejected');
			} else if (key === 'cancel') {
				requestUpdateStatus(item.name, 'Cancel');
			} else if (key === 'delete') {
				requestUpdateStatus(item.name, 'Delete');
			}
		};

		const goToNew = () => {
			router.push('/requisitions/new');
		};

		const confirmDialogOpen = ref(false);
		const confirmLoading = ref(false);
		const pendingAction = ref(null);

		const confirmDialogTitle = computed(() =>
			pendingAction.value ? __('{0}?', [__(pendingAction.value.status)]) : '',
		);
		const confirmDialogMessage = computed(() =>
			pendingAction.value
				? STATUS_CONFIRM_MESSAGES[pendingAction.value.status] || __('Are you sure you want to continue?')
				: '',
		);

		const requestUpdateStatus = (requisition, status) => {
			pendingAction.value = { requisition, status };
			confirmDialogOpen.value = true;
		};

		const performUpdateStatus = async () => {
			if (!pendingAction.value) return;
			const { requisition, status } = pendingAction.value;
			confirmLoading.value = true;
			try {
				if (status === 'Cancel') {
					await frappe.call({
						method: 'posawesome.posawesome.api.requisitions.cancel_requisition',
						args: { requisition },
						freeze: true,
						freeze_message: __('Cancelling...'),
					});
					toastStore.show({ title: __('Requisition {0} cancelled', [requisition]), color: 'success' });
				} else if (status === 'Delete') {
					await frappe.call({
						method: 'posawesome.posawesome.api.requisitions.delete_cancelled_requisition',
						args: { requisition },
						freeze: true,
						freeze_message: __('Deleting...'),
					});
					toastStore.show({ title: __('Requisition {0} deleted', [requisition]), color: 'success' });
				} else {
					await frappe.call({
						method: 'posawesome.posawesome.api.requisitions.set_requisition_status',
						args: { requisition, status },
						freeze: true,
						freeze_message:
							status === 'Received' ? __('Marking as received...') : __('Marking as rejected...'),
					});
					toastStore.show({
						title: __('Requisition {0} marked {1}', [requisition, status]),
						color: status === 'Received' ? 'success' : 'warning',
					});
				}
				confirmDialogOpen.value = false;
				pendingAction.value = null;
				await loadRequisitions();
			} catch (e) {
				toastStore.show({ title: e?.message || __('Failed to update status'), color: 'error' });
			} finally {
				confirmLoading.value = false;
			}
		};

		const openRequisitionDetail = (item) => {
			router.push(`/requisitions/${item.name}`);
		};

		onMounted(() => {
			loadItemGroups();
			loadWarehouses();
			loadRequisitions();
		});

		return {
			requisitionList,
			listLoading,
			mineOnly,
			searchQuery,
			listHeaders,
			page,
			pageSize,
			total,
			totalPages,
			pageNumbers,
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
			loadRequisitions,
			resetAndLoad,
			handleSearchUpdate,
			handleItemSearchUpdate,
			clearFilters,
			goToPage,
			formatDisplayDate,
			statusColor,
			displayStatus,
			rowActions,
			handleRowAction,
			goToNew,
			confirmDialogOpen,
			confirmLoading,
			pendingAction,
			confirmDialogTitle,
			confirmDialogMessage,
			requestUpdateStatus,
			performUpdateStatus,
			openRequisitionDetail,
			isSystemManager,
		};
	},
};
</script>

<style scoped>
@import '../invoice-shared-styles.css';
</style>
