<template>
	<div class="pa-0 h-100 invoice-shell pos-list-page">
		<v-card flat class="invoice-section-card pos-themed-card pos-list-card">
			<div class="pos-list-header">
				<div class="pos-list-header__main">
					<p class="pos-list-header__eyebrow">{{ __("Stock Movement") }}</p>
					<h3 class="pos-list-header__title">{{ __("Requisitions") }}</h3>
					<p class="pos-list-header__subtitle">
						{{ __("Track warehouse requisitions, transfers, and receipt confirmations") }}
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
					<strong class="pos-list-stat__value">{{ stats.total }}</strong>
				</div>
				<div class="pos-list-stat pos-list-stat--warning">
					<span class="pos-list-stat__label">{{ __("Pending Transfer") }}</span>
					<strong class="pos-list-stat__value">{{ stats.pendingTransfer }}</strong>
				</div>
				<div class="pos-list-stat">
					<span class="pos-list-stat__label">{{ __("In Transit") }}</span>
					<strong class="pos-list-stat__value">{{ stats.inTransit }}</strong>
				</div>
				<div class="pos-list-stat pos-list-stat--success">
					<span class="pos-list-stat__label">{{ __("Completed") }}</span>
					<strong class="pos-list-stat__value">{{ stats.completed }}</strong>
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
				/>
				<div class="pos-list-toolbar__filters">
					<v-switch
						v-model="mineOnly"
						density="compact"
						hide-details
						color="primary"
						:label="__('My Requisitions')"
						@update:model-value="loadRequisitions"
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

			<div v-if="filteredList.length" class="pos-list-table-wrap">
				<v-data-table
					:headers="listHeaders"
					:items="filteredList"
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
						<div class="d-flex justify-end ga-1 flex-wrap">
							<v-btn
								v-if="item.can_transfer"
								size="small"
								variant="tonal"
								color="warning"
								class="text-none"
								@click.stop="transferStock(item.name)"
							>
								{{ __("Transfer") }}
							</v-btn>
							<v-btn
								v-if="item.can_confirm"
								size="small"
								variant="flat"
								color="primary"
								class="text-none"
								@click.stop="openConfirmReceipt(item.name)"
							>
								{{ __("Confirm") }}
							</v-btn>
						</div>
					</template>
				</v-data-table>
			</div>

			<div v-else-if="!listLoading" class="pos-list-empty">
				<v-icon size="48" color="primary" class="pos-list-empty__icon">mdi-clipboard-text-outline</v-icon>
				<h4 class="pos-list-empty__title">{{ __("No requisitions found") }}</h4>
				<p class="pos-list-empty__subtitle">
					{{ searchQuery
						? __("Try a different search term or clear the filter.")
						: __("Create a new requisition to request stock from another warehouse.") }}
				</p>
				<v-btn
					v-if="!searchQuery"
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

		<ConfirmReceiptDialog
			v-model="confirmDialog"
			:items="confirmItems"
			:loading="confirmLoading"
			@confirm="handleConfirmReceipt"
		/>
	</div>
</template>

<script>
import { ref, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import format from '../../../format';
import { useToastStore } from '../../../stores/toastStore';
import ConfirmReceiptDialog from './ConfirmReceiptDialog.vue';

export default {
	name: 'RequisitionList',
	mixins: [format],
	components: {
		ConfirmReceiptDialog,
	},
	setup() {
		const router = useRouter();
		const toastStore = useToastStore();
		const requisitionList = ref([]);
		const listLoading = ref(false);
		const mineOnly = ref(false);
		const searchQuery = ref('');
		const confirmDialog = ref(false);
		const confirmItems = ref([]);
		const confirmLoading = ref(false);
		const confirmRequisitionName = ref('');

		const listHeaders = [
			{ title: __('Requisition'), key: 'name', sortable: true },
			{ title: __('Date'), key: 'transaction_date', sortable: true },
			{ title: __('From'), key: 'source_warehouse', sortable: true },
			{ title: __('To'), key: 'target_warehouse', sortable: true },
			{ title: __('Status'), key: 'transfer_status', sortable: true },
			{ title: __('Actions'), key: 'actions', sortable: false, align: 'end', width: '180px' },
		];

		const filteredList = computed(() => {
			const q = String(searchQuery.value || '').trim().toLowerCase();
			if (!q) return requisitionList.value;
			return requisitionList.value.filter((row) => {
				const haystack = [
					row.name,
					row.source_warehouse,
					row.target_warehouse,
					row.transfer_status,
					row.requested_by,
				]
					.filter(Boolean)
					.join(' ')
					.toLowerCase();
				return haystack.includes(q);
			});
		});

		const stats = computed(() => {
			const rows = requisitionList.value;
			return {
				total: rows.length,
				pendingTransfer: rows.filter((row) => row.can_transfer).length,
				inTransit: rows.filter((row) => row.transfer_status === 'In Transit').length,
				completed: rows.filter((row) =>
					['Fully Transferred', 'Over Transferred'].includes(row.transfer_status),
				).length,
			};
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
					args: { page_start: 0, page_length: 50, mine_only: mineOnly.value ? 1 : 0 },
				});
				requisitionList.value = message?.requisitions || [];
			} catch (e) {
				console.error('Failed to load requisitions', e);
				requisitionList.value = [];
			} finally {
				listLoading.value = false;
			}
		};

		const statusColor = (status) => {
			const map = {
				'Not Transferred': 'orange',
				'In Transit': 'blue',
				'Partially Transferred': 'orange',
				'Fully Transferred': 'green',
				'Over Transferred': 'red',
			};
			return map[status] || 'grey';
		};

		const statusChipClass = (status) => {
			if (status === 'Partially Transferred') {
				return 'pos-status-chip--partial';
			}
			return '';
		};

		const goToNew = () => {
			router.push('/requisitions/new');
		};

		const transferStock = async (requisition) => {
			try {
				const { message } = await frappe.call({
					method: 'posawesome.posawesome.api.requisitions.make_stock_entry',
					args: { requisition },
					freeze: true,
					freeze_message: __('Creating Stock Entry...'),
				});
				if (message?.name) {
					frappe.set_route('Form', 'Stock Entry', message.name);
				}
			} catch (e) {
				toastStore.show({ title: e?.message || __('Transfer failed'), color: 'error' });
			}
		};

		const openConfirmReceipt = async (requisition) => {
			confirmRequisitionName.value = requisition;
			try {
				const { message } = await frappe.call({
					method: 'posawesome.posawesome.api.requisitions.get_in_transit_se_items',
					args: { requisition },
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
					method: 'posawesome.posawesome.api.requisitions.confirm_receipt_from_requisition',
					args: {
						requisition: confirmRequisitionName.value,
						received_quantities: JSON.stringify(receivedMap),
					},
					freeze: true,
					freeze_message: __('Confirming receipt...'),
				});
				toastStore.show({ title: __('Receipt confirmed'), color: 'success' });
				confirmDialog.value = false;
				await loadRequisitions();
			} catch (e) {
				toastStore.show({ title: e?.message || __('Confirm failed'), color: 'error' });
			} finally {
				confirmLoading.value = false;
			}
		};

		const openRequisitionDetail = (item) => {
			frappe.set_route('Form', 'Requisition', item.name);
		};

		onMounted(() => {
			loadRequisitions();
		});

		return {
			requisitionList,
			filteredList,
			stats,
			listLoading,
			mineOnly,
			searchQuery,
			listHeaders,
			loadRequisitions,
			formatDisplayDate,
			statusColor,
			statusChipClass,
			goToNew,
			transferStock,
			openConfirmReceipt,
			confirmDialog,
			confirmItems,
			confirmLoading,
			handleConfirmReceipt,
			openRequisitionDetail,
		};
	},
};
</script>

<style scoped>
@import '../invoice-shared-styles.css';
</style>
