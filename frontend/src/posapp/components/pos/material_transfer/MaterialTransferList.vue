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
					<strong class="pos-list-stat__value">{{ stats.total }}</strong>
				</div>
				<div class="pos-list-stat">
					<span class="pos-list-stat__label">{{ __("In Transit") }}</span>
					<strong class="pos-list-stat__value">{{ stats.inTransit }}</strong>
				</div>
				<div class="pos-list-stat pos-list-stat--warning">
					<span class="pos-list-stat__label">{{ __("Partial") }}</span>
					<strong class="pos-list-stat__value">{{ stats.partial }}</strong>
				</div>
				<div class="pos-list-stat pos-list-stat--success">
					<span class="pos-list-stat__label">{{ __("Received") }}</span>
					<strong class="pos-list-stat__value">{{ stats.received }}</strong>
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
				/>
				<div class="pos-list-toolbar__filters">
					<v-switch
						v-model="mineOnly"
						density="compact"
						hide-details
						color="primary"
						:label="__('My Transfers')"
						@update:model-value="loadTransfers"
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

			<div v-if="filteredList.length" class="pos-list-table-wrap">
				<v-data-table
					:headers="listHeaders"
					:items="filteredList"
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
						<div class="d-flex justify-end">
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
				<v-icon size="48" color="primary" class="pos-list-empty__icon">mdi-truck-delivery-outline</v-icon>
				<h4 class="pos-list-empty__title">{{ __("No material transfers found") }}</h4>
				<p class="pos-list-empty__subtitle">
					{{ searchQuery
						? __("Try a different search term or clear the filter.")
						: __("Create a new transfer to move stock between warehouses.") }}
				</p>
				<v-btn
					v-if="!searchQuery"
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
	</div>
</template>

<script>
import { ref, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
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
		const router = useRouter();
		const toastStore = useToastStore();
		const transferList = ref([]);
		const listLoading = ref(false);
		const mineOnly = ref(false);
		const searchQuery = ref('');
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
			{ title: __('Actions'), key: 'actions', sortable: false, align: 'end', width: '120px' },
		];

		const filteredList = computed(() => {
			const q = String(searchQuery.value || '').trim().toLowerCase();
			if (!q) return transferList.value;
			return transferList.value.filter((row) => {
				const haystack = [
					row.name,
					row.from_warehouse,
					row.to_warehouse,
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
			const rows = transferList.value;
			return {
				total: rows.length,
				inTransit: rows.filter((row) => row.transfer_status === 'In Transit').length,
				partial: rows.filter((row) => row.transfer_status === 'Partially Received').length,
				received: rows.filter((row) => row.transfer_status === 'Fully Received').length,
			};
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
				'Partially Received': 'orange',
				'Fully Received': 'green',
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

		const openTransferDetail = (item) => {
			frappe.set_route('Form', 'Material Transfer', item.name);
		};

		onMounted(() => {
			loadTransfers();
		});

		return {
			transferList,
			filteredList,
			stats,
			listLoading,
			mineOnly,
			searchQuery,
			listHeaders,
			loadTransfers,
			formatDisplayDate,
			statusColor,
			statusChipClass,
			goToNew,
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
</style>
