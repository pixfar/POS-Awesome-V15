<template>
	<div class="pa-0 h-100 invoice-shell pos-list-page">
		<v-card flat class="invoice-section-card pos-themed-card pos-list-card">
			<div class="pos-list-header">
				<div class="pos-list-header__main">
					<p class="pos-list-header__eyebrow">{{ __("Stock") }}</p>
					<h3 class="pos-list-header__title">{{ __(purpose) }}</h3>
					<p class="pos-list-header__subtitle">
						{{ isIssue ? __("Stock taken out of a warehouse") : __("Stock received into a warehouse") }}
					</p>
				</div>
				<div v-if="canManage" class="pos-list-header__actions">
					<v-btn color="primary" variant="flat" class="text-none" prepend-icon="mdi-plus" @click="goToNew">
						{{ isIssue ? __("New Issue") : __("New Receipt") }}
					</v-btn>
				</div>
			</div>

			<div class="pos-list-stats">
				<div class="pos-list-stat pos-list-stat--primary">
					<span class="pos-list-stat__label">{{ __("Total") }}</span>
					<strong class="pos-list-stat__value">{{ total }}</strong>
				</div>
				<div class="pos-list-stat pos-list-stat--warning">
					<span class="pos-list-stat__label">{{ __("Total Qty") }}</span>
					<strong class="pos-list-stat__value">{{ formatFloat(totalQty) }}</strong>
				</div>
				<div class="pos-list-stat pos-list-stat--success">
					<span class="pos-list-stat__label">{{ __("Total Value") }}</span>
					<strong class="pos-list-stat__value">{{ formatCurrency(totalValue) }}</strong>
				</div>
			</div>

			<div class="pos-list-toolbar">
				<v-text-field
					v-model="searchQuery"
					:label="__('Search ID, item, warehouse or remark')"
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
						@click="loadRecords"
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
					@update:model-value="loadRecords"
				/>
				<DateFilterField
					v-model="toDate"
					:label="__('To Date')"
					field-class="pos-themed-input pos-list-filter-field"
					:min="fromDate"
					@update:model-value="loadRecords"
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
					@update:model-value="loadRecords"
				/>
				<v-text-field
					v-model="remarksFilter"
					:label="__('Remarks')"
					density="compact"
					variant="outlined"
					hide-details
					clearable
					prepend-inner-icon="mdi-text-search"
					class="pos-themed-input pos-list-filter-field"
					@update:model-value="handleSearchUpdate"
				/>
				<v-btn variant="text" size="small" class="text-none" @click="clearFilters">
					{{ __("Clear Filters") }}
				</v-btn>
			</div>

			<div v-if="records.length" class="pos-list-table-wrap">
				<v-data-table
					:headers="listHeaders"
					:items="records"
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
					<template #item.posting_date="{ item }">
						<span class="pos-list-cell-muted">{{ formatDisplayDate(item.posting_date) }}</span>
					</template>
					<template #item.remarks="{ item }">
						<span class="pos-list-cell-truncate" :title="item.remarks">{{ item.remarks || "—" }}</span>
					</template>
					<template #item.total_qty="{ item }">{{ formatFloat(item.total_qty) }}</template>
					<template #item.total_value="{ item }">{{ formatCurrency(item.total_value) }}</template>
					<template #item.status="{ item }">
						<v-chip size="small" variant="tonal" :color="statusColor(item.status)">
							{{ __(item.status) }}
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
			</div>

			<div v-else-if="!listLoading" class="pos-list-empty">
				<v-icon size="48" color="primary" class="pos-list-empty__icon">{{ isIssue ? "mdi-package-up" : "mdi-package-down" }}</v-icon>
				<h4 class="pos-list-empty__title">{{ __("No {0} found", [__(purpose)]) }}</h4>
				<p class="pos-list-empty__subtitle">
					{{ hasActiveFilters
						? __("Try different filters or clear them.")
						: __("Submitted entries are listed here.") }}
				</p>
			</div>

			<div v-else class="pos-list-empty">
				<v-progress-circular indeterminate color="primary" />
			</div>
		</v-card>

		<ConfirmActionDialog
			v-model="confirmDialog"
			:title="__('Cancel {0}', [__(purpose)])"
			:message="confirmMessage"
			:confirm-label="__('Cancel Entry')"
			confirm-color="error"
			:loading="Boolean(actionLoadingName)"
			@confirm="runCancel"
		/>
	</div>
</template>

<script>
import { ref, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import format from '../../../format';
import DateFilterField from '../shared/DateFilterField.vue';
import RowActionsMenu from '../shared/RowActionsMenu.vue';
import ConfirmActionDialog from '../shared/ConfirmActionDialog.vue';
import { useToastStore } from '../../../stores/toastStore';
import { isFundTransferManager } from '../../../utils/posWarehouseAccess';
import { formatDisplayDate, docStatusColor } from '../shared/docStatusUtils';
import { useWarehouseFilterOptions } from '../shared/useWarehouseFilterOptions';
import { stockEntryBasePath } from './stockEntryRoutes';

const API = 'posawesome.posawesome.api.stock_entries';

export default {
	name: 'StockEntryList',
	components: { DateFilterField, RowActionsMenu, ConfirmActionDialog },
	mixins: [format],
	props: {
		purpose: { type: String, required: true },
	},
	setup(props) {
		const router = useRouter();
		const toastStore = useToastStore();
		// BSP Viewer sees the list but cannot create or cancel -- re-checked server-side.
		const canManage = computed(() => isFundTransferManager());

		const records = ref([]);
		const total = ref(0);
		const listLoading = ref(false);
		const searchQuery = ref('');
		const fromDate = ref('');
		const toDate = ref('');
		const warehouseFilter = ref(null);
		const remarksFilter = ref('');
		const { warehouseOptions, loadWarehouseOptions } = useWarehouseFilterOptions();
		const isIssue = computed(() => props.purpose === 'Material Issue');
		const basePath = computed(() => stockEntryBasePath(props.purpose));
		let searchTimeout = null;

		const listHeaders = [
			{ title: __('Stock Entry'), key: 'name', sortable: true },
			{ title: __('Date'), key: 'posting_date', sortable: true },
			{ title: __('Warehouse'), key: 'warehouse', sortable: true },
			{ title: __('Items'), key: 'item_count', sortable: true, align: 'end' },
			{ title: __('Qty'), key: 'total_qty', sortable: true, align: 'end' },
			{ title: __('Value'), key: 'total_value', sortable: true, align: 'end' },
			{ title: __('Remarks'), key: 'remarks', sortable: false },
			{ title: __('Created By'), key: 'created_by', sortable: true },
			{ title: __('Status'), key: 'status', sortable: true },
			{ title: __('Actions'), key: 'actions', sortable: false, align: 'end', width: '100px' },
		];

		const hasActiveFilters = computed(() => Boolean(searchQuery.value || fromDate.value || toDate.value || warehouseFilter.value || remarksFilter.value));
		const activeRecords = computed(() => records.value.filter((row) => row.docstatus === 1));
		const totalQty = computed(() =>
			activeRecords.value.reduce((sum, row) => sum + (Number(row.total_qty) || 0), 0),
		);
		const totalValue = computed(() =>
			activeRecords.value.reduce((sum, row) => sum + (Number(row.total_value) || 0), 0),
		);

		const loadRecords = async () => {
			listLoading.value = true;
			try {
				const { message } = await frappe.call({
					method: `${API}.get_stock_entries_list`,
					args: {
						purpose: props.purpose,
						warehouse: warehouseFilter.value || undefined,
						remarks: remarksFilter.value || undefined,
						from_date: fromDate.value || undefined,
						to_date: toDate.value || undefined,
						search: searchQuery.value || undefined,
					},
				});
				records.value = message?.records || [];
				total.value = message?.total || 0;
			} catch (e) {
				console.error('Failed to load stock entries', e);
				records.value = [];
			} finally {
				listLoading.value = false;
			}
		};

		const handleSearchUpdate = () => {
			if (searchTimeout) clearTimeout(searchTimeout);
			searchTimeout = setTimeout(loadRecords, 300);
		};

		const clearFilters = () => {
			searchQuery.value = '';
			fromDate.value = '';
			toDate.value = '';
			warehouseFilter.value = null;
			remarksFilter.value = '';
			loadRecords();
		};

		const goToNew = () => router.push(`${basePath.value}/new`);
		const openDetail = (item) => router.push(`${basePath.value}/${item.name}`);

		const actionLoadingName = ref(null);
		const confirmDialog = ref(false);
		const confirmItem = ref(null);
		const confirmMessage = computed(() =>
			__('This will cancel {0} and reverse its stock and accounting entries. Continue?', [
				confirmItem.value?.name || '',
			]),
		);

		const rowActions = (item) => [
			{ key: 'view', label: __('View'), icon: 'mdi-eye-outline' },
			{
				key: 'cancel',
				label: __('Cancel'),
				icon: 'mdi-cancel',
				color: 'error',
				show: canManage.value && item.docstatus === 1,
			},
		];

		const handleRowAction = (key, item) => {
			if (key === 'view') {
				openDetail(item);
			} else if (key === 'cancel') {
				confirmItem.value = item;
				confirmDialog.value = true;
			}
		};

		const runCancel = async () => {
			const item = confirmItem.value;
			if (!item) return;
			actionLoadingName.value = item.name;
			try {
				await frappe.call({ method: `${API}.cancel_stock_entry`, args: { name: item.name } });
				toastStore.show({ title: __('{0} cancelled', [item.name]), color: 'success' });
				confirmDialog.value = false;
				await loadRecords();
			} catch (e) {
				toastStore.show({ title: e?.message || __('Action failed'), color: 'error' });
			} finally {
				actionLoadingName.value = null;
			}
		};

		onMounted(() => {
			loadWarehouseOptions();
			loadRecords();
		});

		return {
			canManage,
			records,
			total,
			listLoading,
			searchQuery,
			fromDate,
			toDate,
			warehouseFilter,
			remarksFilter,
			warehouseOptions,
			isIssue,
			listHeaders,
			hasActiveFilters,
			totalQty,
			totalValue,
			loadRecords,
			handleSearchUpdate,
			clearFilters,
			goToNew,
			openDetail,
			formatDisplayDate,
			statusColor: docStatusColor,
			actionLoadingName,
			confirmDialog,
			confirmMessage,
			rowActions,
			handleRowAction,
			runCancel,
		};
	},
};
</script>

<style scoped>
@import '../invoice-shared-styles.css';
</style>
