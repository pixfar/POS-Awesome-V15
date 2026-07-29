<template>
	<div class="pa-0 h-100 invoice-shell pos-list-page">
		<v-card flat class="invoice-section-card pos-themed-card pos-list-card">
			<div class="pos-list-header">
				<div class="pos-list-header__main">
					<p class="pos-list-header__eyebrow">{{ __("Fund Transfer") }}</p>
					<h3 class="pos-list-header__title">{{ __("Fund Transfers") }}</h3>
					<p class="pos-list-header__subtitle">
						{{ isFundTransferManager
							? __("Track fund transfers sent to showroom cash accounts")
							: __("Fund transfers sent to your showroom's cash account") }}
					</p>
				</div>
				<div v-if="isFundTransferManager" class="pos-list-header__actions">
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
				<div class="pos-list-stat pos-list-stat--success">
					<span class="pos-list-stat__label">{{ __("Total Transferred") }}</span>
					<strong class="pos-list-stat__value">{{ formatCurrency(totalTransferred) }}</strong>
				</div>
			</div>

			<div class="pos-list-toolbar">
				<v-text-field
					v-model="searchQuery"
					:label="__('Search transfer or account')"
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
						@click="loadTransfers"
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

			<div v-if="transferList.length" class="pos-list-table-wrap">
				<v-data-table
					:headers="listHeaders"
					:items="transferList"
					:loading="listLoading"
					density="comfortable"
					hide-default-footer
					:items-per-page="-1"
					class="pos-list-table"
					@click:row="(_, row) => openTransferDetail(row.item)"
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
				<v-icon size="48" color="primary" class="pos-list-empty__icon">mdi-bank-transfer</v-icon>
				<h4 class="pos-list-empty__title">{{ __("No fund transfers found") }}</h4>
				<p class="pos-list-empty__subtitle">
					{{ hasActiveFilters
						? __("Try different filters or clear them.")
						: __("Submit a new fund transfer to see it listed here.") }}
				</p>
				<v-btn
					v-if="!hasActiveFilters && isFundTransferManager"
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
import format from '../../../format';
import DateFilterField from '../shared/DateFilterField.vue';
import RowActionsMenu from '../shared/RowActionsMenu.vue';
import ConfirmActionDialog from '../shared/ConfirmActionDialog.vue';
import { useToastStore } from '../../../stores/toastStore';
import { isFundTransferManager } from '../../../utils/posWarehouseAccess';

export default {
	name: 'FundTransferList',
	components: { DateFilterField, RowActionsMenu, ConfirmActionDialog },
	mixins: [format],
	setup() {
		const router = useRouter();
		const toastStore = useToastStore();

		const canManage = computed(() => isFundTransferManager());

		const actionLoadingName = ref(null);
		const confirmDialog = ref(false);
		const confirmDialogItem = ref(null);
		const confirmDialogAction = ref(null);
		const confirmDialogTitle = ref('');
		const confirmDialogMessage = ref('');
		const confirmDialogActionLabel = ref('');
		const confirmDialogColor = ref('error');

		const canCancel = (item) => canManage.value && item.docstatus === 1;

		const rowActions = (item) => [
			{ key: 'view', label: __('View'), icon: 'mdi-eye-outline' },
			{
				key: 'cancel',
				label: __('Cancel'),
				icon: 'mdi-cancel',
				color: 'error',
				show: canCancel(item),
			},
		];

		const handleRowAction = (key, item) => {
			if (key === 'view') {
				openTransferDetail(item);
			} else if (key === 'cancel') {
				openCancelConfirm(item);
			}
		};

		const openCancelConfirm = (item) => {
			confirmDialogItem.value = item;
			confirmDialogAction.value = 'cancel';
			confirmDialogTitle.value = __('Cancel Fund Transfer');
			confirmDialogMessage.value = __(
				'This will cancel {0}. This cannot be undone. Continue?',
				[item.name],
			);
			confirmDialogActionLabel.value = __('Cancel Transfer');
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
						method: 'posawesome.posawesome.api.fund_transfer.cancel_fund_transfer',
						args: { name: item.name },
					});
					toastStore.show({ title: __('{0} cancelled', [item.name]), color: 'success' });
				}
				confirmDialog.value = false;
				await loadTransfers();
			} catch (e) {
				toastStore.show({ title: e?.message || __('Action failed'), color: 'error' });
			} finally {
				actionLoadingName.value = null;
			}
		};

		const transferList = ref([]);
		const listLoading = ref(false);
		const searchQuery = ref('');
		let searchTimeout = null;

		const PAGE_LENGTH = 100;
		const total = ref(0);

		const fromDate = ref('');
		const toDate = ref('');

		const listHeaders = [
			{ title: __('Transfer'), key: 'name', sortable: true },
			{ title: __('Date'), key: 'posting_date', sortable: true },
			{ title: __('Paid From'), key: 'paid_from', sortable: true },
			{ title: __('Paid To'), key: 'paid_to', sortable: true },
			{ title: __('Mode of Payment'), key: 'mode_of_payment', sortable: true },
			{ title: __('Amount'), key: 'amount', sortable: true, align: 'end' },
			{ title: __('Status'), key: 'docstatus', sortable: true },
			{ title: __('Actions'), key: 'actions', sortable: false, align: 'end', width: '120px' },
		];

		const hasActiveFilters = computed(() =>
			Boolean(searchQuery.value || fromDate.value || toDate.value),
		);

		const totalTransferred = computed(() =>
			transferList.value.reduce((sum, row) => sum + (Number(row.amount) || 0), 0),
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

		const loadTransfers = async () => {
			listLoading.value = true;
			try {
				const { message } = await frappe.call({
					method: 'posawesome.posawesome.api.fund_transfer.get_fund_transfers_list',
					args: {
						page_start: 0,
						page_length: PAGE_LENGTH,
						from_date: fromDate.value || undefined,
						to_date: toDate.value || undefined,
						search: searchQuery.value || undefined,
					},
				});
				transferList.value = message?.transfers || [];
				total.value = message?.total || 0;
			} catch (e) {
				console.error('Failed to load fund transfers', e);
				transferList.value = [];
			} finally {
				listLoading.value = false;
			}
		};

		const resetAndLoad = () => {
			loadTransfers();
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
			router.push('/fund-transfer/new');
		};

		const openTransferDetail = (item) => {
			router.push(`/fund-transfer/${item.name}`);
		};

		onMounted(() => {
			loadTransfers();
		});

		return {
			transferList,
			listLoading,
			searchQuery,
			listHeaders,
			total,
			fromDate,
			toDate,
			hasActiveFilters,
			totalTransferred,
			loadTransfers,
			resetAndLoad,
			handleSearchUpdate,
			clearFilters,
			formatDisplayDate,
			statusLabel,
			statusColor,
			goToNew,
			openTransferDetail,
			isFundTransferManager: canManage,
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
