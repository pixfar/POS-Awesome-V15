<template>
	<div class="pa-0 h-100 invoice-shell pos-list-page">
		<v-card flat class="invoice-section-card pos-themed-card pos-list-card">
			<div class="pos-list-header">
				<div class="pos-list-header__main">
					<p class="pos-list-header__eyebrow">{{ __("Stock Movement") }}</p>
					<h3 class="pos-list-header__title">{{ __("Material Transfers") }}</h3>
					<p class="pos-list-header__subtitle">
						{{ __("Track inter-warehouse transfers and confirm received stock") }}
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
						{{ __("New Transfer") }}
					</v-btn>
				</div>
			</div>

			<div class="pos-list-stats">
				<div class="pos-list-stat pos-list-stat--primary">
					<span class="pos-list-stat__label">{{ __("Total") }}</span>
					<strong class="pos-list-stat__value">{{ total }}</strong>
				</div>
				<div class="pos-list-stat">
					<span class="pos-list-stat__label">{{ __("In Transit") }}</span>
					<strong class="pos-list-stat__value">{{ statusCounts["In Transit"] || 0 }}</strong>
				</div>
				<div class="pos-list-stat pos-list-stat--warning">
					<span class="pos-list-stat__label">{{ __("Partial") }}</span>
					<strong class="pos-list-stat__value">{{ statusCounts["Partially Received"] || 0 }}</strong>
				</div>
				<div class="pos-list-stat pos-list-stat--success">
					<span class="pos-list-stat__label">{{ __("Received") }}</span>
					<strong class="pos-list-stat__value">{{ statusCounts["Fully Received"] || 0 }}</strong>
				</div>
				<div class="pos-list-stat pos-list-stat--danger">
					<span class="pos-list-stat__label">{{ __("Rejected") }}</span>
					<strong class="pos-list-stat__value">{{ statusCounts["Rejected"] || 0 }}</strong>
				</div>
			</div>

			<div class="pos-list-toolbar">
				<v-text-field
					v-model="searchQuery"
					:label="__('Search transfer or warehouse')"
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
						:label="__('My Transfers')"
						@update:model-value="resetAndLoad"
					/>
					<v-btn
						variant="tonal"
						size="small"
						color="primary"
						prepend-icon="mdi-sync"
						:loading="listLoading"
						class="text-none"
						@click="loadTransfers"
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

			<div v-if="transferList.length" class="pos-list-table-wrap">
				<v-data-table
					:headers="listHeaders"
					:items="transferList"
					:loading="listLoading"
					density="comfortable"
					hide-default-footer
					:items-per-page="-1"
					class="pos-list-table material-transfer-list-table"
					@click:row="(_, row) => openTransferDetail(row.item)"
				>
					<template #item.name="{ item }">
						<span class="pos-list-cell-primary">{{ item.name }}</span>
					</template>
					<template #item.transaction_date="{ item }">
						<span class="pos-list-cell-muted">{{ formatDisplayDate(item.transaction_date) }}</span>
					</template>
					<template #item.from_warehouse="{ item }">
						<span class="pos-list-cell-truncate" :title="item.from_warehouse">
							{{ item.from_warehouse }}
						</span>
					</template>
					<template #item.to_warehouse="{ item }">
						<span class="pos-list-cell-truncate" :title="item.to_warehouse">
							{{ item.to_warehouse }}
						</span>
					</template>
					<template #item.transfer_status="{ item }">
						<v-chip
							size="small"
							variant="tonal"
							:color="statusColor(item.transfer_status)"
							:class="statusChipClass(item.transfer_status)"
						>
							{{ item.transfer_status }}
						</v-chip>
					</template>
					<template #item.actions="{ item }">
						<div class="d-flex justify-end ga-1">
							<v-btn
								v-if="item.can_confirm"
								size="small"
								variant="flat"
								color="primary"
								class="text-none"
								@click.stop="openConfirmReceipt(item.name)"
							>
								{{ __("Received") }}
							</v-btn>
							<v-btn
								v-if="item.can_confirm"
								size="small"
								variant="tonal"
								color="error"
								class="text-none"
								@click.stop="openRejectDialog(item.name)"
							>
								{{ __("Rejected") }}
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
				<v-icon size="48" color="primary" class="pos-list-empty__icon">mdi-truck-delivery-outline</v-icon>
				<h4 class="pos-list-empty__title">{{ __("No material transfers found") }}</h4>
				<p class="pos-list-empty__subtitle">
					{{ hasActiveFilters
						? __("Try different filters or clear them.")
						: __("Create a new transfer to move stock between warehouses.") }}
				</p>
				<v-btn
					v-if="!hasActiveFilters"
					color="primary"
					variant="flat"
					class="text-none mt-2"
					prepend-icon="mdi-plus"
					@click="goToNew"
				>
					{{ __("New Transfer") }}
				</v-btn>
			</div>

			<div v-else class="pos-list-empty">
				<v-progress-circular indeterminate color="primary" />
			</div>
		</v-card>

		<ConfirmReceiptDialog
			v-model="confirmDialog"
			:items="confirmItems"
			:loading="confirmLoading"
			@confirm="handleConfirmReceipt"
		/>

		<v-dialog v-model="rejectDialog" max-width="420">
			<v-card class="pos-themed-card">
				<v-card-title class="d-flex align-center gap-2">
					<v-icon color="error">mdi-close-circle-outline</v-icon>
					<span>{{ __("Reject Transfer") }}</span>
				</v-card-title>
				<v-card-text>
					{{
						__(
							"Rejecting will cancel this transfer and reverse the stock movement. This cannot be undone. Continue?"
						)
					}}
				</v-card-text>
				<v-card-actions>
					<v-spacer />
					<v-btn variant="text" @click="rejectDialog = false">{{ __("Cancel") }}</v-btn>
					<v-btn color="error" variant="flat" :loading="rejectLoading" @click="handleRejectTransfer">
						{{ __("Reject") }}
					</v-btn>
				</v-card-actions>
			</v-card>
		</v-dialog>
	</div>
</template>

<script>
import { ref, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import format from '../../../format';
import { useToastStore } from '../../../stores/toastStore';
import ConfirmReceiptDialog from '../requisition/ConfirmReceiptDialog.vue';
import DateFilterField from '../shared/DateFilterField.vue';

export default {
	name: 'MaterialTransferList',
	mixins: [format],
	components: {
		ConfirmReceiptDialog,
		DateFilterField,
	},
	setup() {
		const router = useRouter();
		const toastStore = useToastStore();
		const transferList = ref([]);
		const listLoading = ref(false);
		const mineOnly = ref(false);
		const searchQuery = ref('');
		let searchTimeout = null;
		const confirmDialog = ref(false);
		const confirmItems = ref([]);
		const confirmLoading = ref(false);
		const confirmTransferName = ref('');
		const rejectDialog = ref(false);
		const rejectLoading = ref(false);
		const rejectTransferName = ref('');

		const page = ref(1);
		const pageSize = ref(20);
		const total = ref(0);
		const totalPages = computed(() => Math.max(1, Math.ceil(total.value / (pageSize.value || 1))));
		const hasMore = ref(false);
		const statusCounts = ref({});

		const statusOptions = ['In Transit', 'Partially Received', 'Fully Received', 'Rejected'];
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
			{ title: __('Transfer'), key: 'name', sortable: true },
			{ title: __('Date'), key: 'transaction_date', sortable: true },
			{ title: __('From'), key: 'from_warehouse', sortable: true },
			{ title: __('To'), key: 'to_warehouse', sortable: true },
			{ title: __('Status'), key: 'transfer_status', sortable: true },
			{ title: __('Actions'), key: 'actions', sortable: false, align: 'end', width: '220px' },
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

		const loadTransfers = async () => {
			listLoading.value = true;
			try {
				const { message } = await frappe.call({
					method: 'posawesome.posawesome.api.material_transfers.get_material_transfers_list',
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
				transferList.value = message?.transfers || [];
				total.value = message?.total || 0;
				hasMore.value = Boolean(message?.has_more);
				statusCounts.value = message?.status_counts || {};
			} catch (e) {
				console.error('Failed to load material transfers', e);
				transferList.value = [];
				toastStore.show({
					title: e?.message || __('Failed to load material transfers'),
					color: 'error',
				});
			} finally {
				listLoading.value = false;
			}
		};

		const resetAndLoad = () => {
			page.value = 1;
			loadTransfers();
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
						method: 'posawesome.posawesome.api.material_transfers.search_items',
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
			loadTransfers();
		};

		const statusColor = (status) => {
			const map = {
				'In Transit': 'blue',
				'Partially Received': 'orange',
				'Fully Received': 'green',
				'Rejected': 'red',
			};
			return map[status] || 'grey';
		};

		const statusChipClass = (status) => {
			if (status === 'Partially Received') {
				return 'pos-status-chip--partial';
			}
			return '';
		};

		const goToNew = () => {
			router.push('/material-transfers/new');
		};

		const openConfirmReceipt = async (transfer) => {
			confirmTransferName.value = transfer;
			try {
				const { message } = await frappe.call({
					method: 'posawesome.posawesome.doctype.material_transfer.material_transfer.get_stock_entry_items',
					args: { transfer },
				});
				confirmItems.value = message?.items || [];
				confirmDialog.value = true;
			} catch (e) {
				toastStore.show({ title: e?.message || __('Nothing to confirm'), color: 'warning' });
			}
		};

		const handleConfirmReceipt = async (receivedMap) => {
			confirmLoading.value = true;
			try {
				await frappe.call({
					method: 'posawesome.posawesome.doctype.material_transfer.material_transfer.confirm_receipt',
					args: {
						transfer: confirmTransferName.value,
						received_quantities: JSON.stringify(receivedMap),
					},
					freeze: true,
					freeze_message: __('Confirming receipt...'),
				});
				toastStore.show({ title: __('Receipt confirmed'), color: 'success' });
				confirmDialog.value = false;
				await loadTransfers();
			} catch (e) {
				toastStore.show({ title: e?.message || __('Confirm failed'), color: 'error' });
			} finally {
				confirmLoading.value = false;
			}
		};

		const openRejectDialog = (transfer) => {
			rejectTransferName.value = transfer;
			rejectDialog.value = true;
		};

		const handleRejectTransfer = async () => {
			rejectLoading.value = true;
			try {
				await frappe.call({
					method: 'posawesome.posawesome.doctype.material_transfer.material_transfer.reject_transfer',
					args: { transfer: rejectTransferName.value },
					freeze: true,
					freeze_message: __('Rejecting transfer...'),
				});
				toastStore.show({ title: __('Transfer rejected'), color: 'success' });
				rejectDialog.value = false;
				await loadTransfers();
			} catch (e) {
				toastStore.show({ title: e?.message || __('Reject failed'), color: 'error' });
			} finally {
				rejectLoading.value = false;
			}
		};

		const openTransferDetail = (item) => {
			router.push(`/material-transfers/${item.name}`);
		};

		onMounted(() => {
			loadItemGroups();
			loadWarehouses();
			loadTransfers();
		});

		return {
			transferList,
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
			loadTransfers,
			resetAndLoad,
			handleSearchUpdate,
			handleItemSearchUpdate,
			clearFilters,
			goToPage,
			formatDisplayDate,
			statusColor,
			statusChipClass,
			goToNew,
			openConfirmReceipt,
			confirmDialog,
			confirmItems,
			confirmLoading,
			handleConfirmReceipt,
			openRejectDialog,
			rejectDialog,
			rejectLoading,
			handleRejectTransfer,
			openTransferDetail,
		};
	},
};
</script>

<style scoped>
@import '../invoice-shared-styles.css';
</style>
