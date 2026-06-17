<template>
	<div class="pa-0 h-100 invoice-shell">
		<v-row class="h-100 ma-0">
			<v-col cols="12" class="pa-3">
				<v-card flat class="invoice-section-card pos-themed-card">
					<div class="invoice-section-heading invoice-section-heading--toolbar">
						<h3 class="invoice-section-heading__title">{{ __("Requisitions") }}</h3>
						<div class="invoice-section-heading__actions">
							<v-switch
								v-model="mineOnly"
								density="compact"
								hide-details
								color="primary"
								:label="__('My Requisitions')"
								class="mr-2"
								@update:model-value="loadRequisitions"
							/>
							<v-btn
								variant="text"
								size="small"
								color="primary"
								prepend-icon="mdi-sync"
								:loading="listLoading"
								@click="loadRequisitions"
							>{{ __("Sync") }}</v-btn>
						</div>
					</div>
					<v-data-table
						:headers="listHeaders"
						:items="requisitionList"
						:loading="listLoading"
						density="compact"
						hide-default-footer
						:items-per-page="-1"
						class="requisition-list-table"
						@click:row="(_, row) => openRequisitionDetail(row.item)"
					>
						<template #item.transfer_status="{ item }">
							<v-chip size="small" variant="tonal" :color="statusColor(item.transfer_status)">
								{{ item.transfer_status }}
							</v-chip>
						</template>
						<template #item.actions="{ item }">
							<v-btn
								v-if="item.can_transfer"
								size="small"
								variant="tonal"
								color="warning"
								class="text-none mr-1"
								@click.stop="transferStock(item.name)"
							>{{ __("Transfer") }}</v-btn>
							<v-btn
								v-if="item.can_confirm"
								size="small"
								variant="flat"
								color="primary"
								class="text-none"
								@click.stop="openConfirmReceipt(item.name)"
							>{{ __("Confirm") }}</v-btn>
						</template>
					</v-data-table>
				</v-card>
			</v-col>
		</v-row>

		<ConfirmReceiptDialog
			v-model="confirmDialog"
			:items="confirmItems"
			:loading="confirmLoading"
			@confirm="handleConfirmReceipt"
		/>
	</div>
</template>

<script>
import { ref, onMounted } from 'vue';
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
		const toastStore = useToastStore();
		const requisitionList = ref([]);
		const listLoading = ref(false);
		const mineOnly = ref(false);
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
			{ title: __('Actions'), key: 'actions', sortable: false, align: 'end' },
		];

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
				'Partially Transferred': 'yellow',
				'Fully Transferred': 'green',
				'Over Transferred': 'red',
			};
			return map[status] || 'grey';
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
			listLoading,
			mineOnly,
			listHeaders,
			loadRequisitions,
			statusColor,
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

.invoice-section-heading--toolbar {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 12px;
}

.invoice-section-heading__actions {
	display: flex;
	align-items: center;
	margin-left: auto;
}

.requisition-list-table :deep(tbody tr) {
	cursor: pointer;
}
</style>
