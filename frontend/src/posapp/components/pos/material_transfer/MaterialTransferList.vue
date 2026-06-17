<template>
	<div class="pa-0 h-100 invoice-shell">
		<v-row class="h-100 ma-0">
			<v-col cols="12" class="pa-3">
				<v-card flat class="invoice-section-card pos-themed-card">
					<div class="invoice-section-heading invoice-section-heading--toolbar">
						<h3 class="invoice-section-heading__title">{{ __("Material Transfers") }}</h3>
						<div class="invoice-section-heading__actions">
							<v-switch
								v-model="mineOnly"
								density="compact"
								hide-details
								color="primary"
								:label="__('My Transfers')"
								class="mr-2"
								@update:model-value="loadTransfers"
							/>
							<v-btn
								variant="text"
								size="small"
								color="primary"
								prepend-icon="mdi-sync"
								:loading="listLoading"
								@click="loadTransfers"
							>{{ __("Sync") }}</v-btn>
						</div>
					</div>
					<v-data-table
						:headers="listHeaders"
						:items="transferList"
						:loading="listLoading"
						density="compact"
						hide-default-footer
						:items-per-page="-1"
						class="material-transfer-list-table"
						@click:row="(_, row) => openTransferDetail(row.item)"
					>
						<template #item.transfer_status="{ item }">
							<v-chip size="small" variant="tonal" :color="statusColor(item.transfer_status)">
								{{ item.transfer_status }}
							</v-chip>
						</template>
						<template #item.actions="{ item }">
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
import ConfirmReceiptDialog from '../requisition/ConfirmReceiptDialog.vue';

export default {
	name: 'MaterialTransferList',
	mixins: [format],
	components: {
		ConfirmReceiptDialog,
	},
	setup() {
		const toastStore = useToastStore();
		const transferList = ref([]);
		const listLoading = ref(false);
		const mineOnly = ref(false);
		const confirmDialog = ref(false);
		const confirmItems = ref([]);
		const confirmLoading = ref(false);
		const confirmTransferName = ref('');

		const listHeaders = [
			{ title: __('Transfer'), key: 'name', sortable: true },
			{ title: __('Date'), key: 'transaction_date', sortable: true },
			{ title: __('From'), key: 'from_warehouse', sortable: true },
			{ title: __('To'), key: 'to_warehouse', sortable: true },
			{ title: __('Status'), key: 'transfer_status', sortable: true },
			{ title: __('Actions'), key: 'actions', sortable: false, align: 'end' },
		];

		const loadTransfers = async () => {
			listLoading.value = true;
			try {
				const { message } = await frappe.call({
					method: 'posawesome.posawesome.api.material_transfers.get_material_transfers_list',
					args: { page_start: 0, page_length: 50, mine_only: mineOnly.value ? 1 : 0 },
				});
				transferList.value = message?.transfers || [];
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

		const statusColor = (status) => {
			const map = {
				'In Transit': 'blue',
				'Partially Received': 'yellow',
				'Fully Received': 'green',
			};
			return map[status] || 'grey';
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

		const openTransferDetail = (item) => {
			frappe.set_route('Form', 'Material Transfer', item.name);
		};

		onMounted(() => {
			loadTransfers();
		});

		return {
			transferList,
			listLoading,
			mineOnly,
			listHeaders,
			loadTransfers,
			statusColor,
			openConfirmReceipt,
			confirmDialog,
			confirmItems,
			confirmLoading,
			handleConfirmReceipt,
			openTransferDetail,
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

.material-transfer-list-table :deep(tbody tr) {
	cursor: pointer;
}
</style>
