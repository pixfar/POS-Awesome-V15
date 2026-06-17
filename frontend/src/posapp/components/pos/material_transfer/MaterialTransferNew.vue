<template>
	<div class="pa-0 h-100 invoice-shell">
		<v-row class="h-100 ma-0">
			<v-col cols="12" md="7" class="h-100 pa-0">
				<v-card class="h-100 d-flex flex-column pos-themed-card purchase-invoice-card" flat>
					<v-card-text class="flex-grow-1 overflow-y-auto pa-3">
						<div class="invoice-sections">
							<div class="invoice-top-grid purchase-top-grid">
								<v-card flat class="invoice-section-card pos-themed-card">
									<div class="invoice-section-heading">
										<h3 class="invoice-section-heading__title">
											{{ __("Warehouse Details") }}
										</h3>
									</div>
									<div class="sale-options-body">
										<v-autocomplete
											v-if="canChangePosWarehouse && fromWarehouseOptions.length"
											v-model="fromWarehouse"
											:items="fromWarehouseOptions"
											item-title="warehouse_name"
											item-value="name"
											:label="__('From Warehouse')"
											density="compact"
											variant="outlined"
											color="primary"
											hide-details
											:loading="warehouseLoading"
											class="pos-themed-input mb-2"
										/>
										<v-text-field
											v-else-if="fromWarehouse"
											:model-value="fromWarehouseLabel || fromWarehouse"
											:label="__('From Warehouse')"
											density="compact"
											variant="outlined"
											color="primary"
											hide-details
											readonly
											prepend-inner-icon="mdi-warehouse"
											class="pos-themed-input mb-2"
										/>
										<v-autocomplete
											v-model="toWarehouse"
											:items="toWarehouseOptions"
											item-title="warehouse_name"
											item-value="name"
											:label="__('To Warehouse')"
											density="compact"
											variant="outlined"
											color="primary"
											hide-details
											class="pos-themed-input"
										/>
									</div>
								</v-card>

								<v-card flat class="invoice-section-card pos-themed-card outstanding-panel">
									<div class="outstanding-panel__inner">
										<div class="outstanding-panel__label">{{ __("Total Qty") }}</div>
										<div class="outstanding-panel__amount outstanding-panel__amount--clear">
											{{ totalQty }}
										</div>
										<div class="text-caption text-medium-emphasis">
											{{ transferItems.length }}
											{{ requisitionItems.length === 1 ? __("item") : __("items") }}
										</div>
									</div>
								</v-card>

								<v-card flat class="invoice-section-card pos-themed-card sale-options-card">
									<div class="sale-options-body">
										<VueDatePicker
											v-model="transactionDateDisplay"
											model-type="format"
											format="dd-MM-yyyy"
											auto-apply
											teleport
											:placeholder="__('Required Date')"
											class="sleek-field pos-themed-input"
										/>
									</div>
								</v-card>
							</div>

							<v-card flat class="invoice-section-card invoice-items-card pos-themed-card">
								<div class="invoice-section-heading">
									<h3 class="invoice-section-heading__title">{{ __("Transfer Items") }}</h3>
								</div>
								<div class="purchase-search-toolbar">
									<v-autocomplete
										v-model:search="itemSearchQuery"
										:model-value="selectedSearchItemCode"
										:items="itemSearchResults"
										:loading="itemSearchLoading"
										item-title="item_name"
										item-value="item_code"
										:label="__('Search, scan or browse item')"
										:custom-filter="() => true"
										prepend-inner-icon="mdi-magnify"
										variant="solo"
										density="compact"
										color="primary"
										hide-details
										clearable
										class="pos-themed-input purchase-item-search"
										@update:search="handleItemSearchUpdate"
										@update:model-value="handleSearchItemPicked"
									/>
								</div>
								<RequisitionItemsTable
									:items="transferItems"
									@update-qty="({ item, value }) => updateItemQty(item, value)"
									@remove-item="removeItem"
								/>
							</v-card>

							<v-textarea
								v-model="notes"
								:label="__('Notes')"
								variant="outlined"
								density="compact"
								hide-details
								rows="2"
								class="pos-themed-input mt-2"
							/>

							<v-alert v-if="errorMessage" type="error" density="compact" class="mt-2">
								{{ errorMessage }}
							</v-alert>
						</div>
					</v-card-text>

					<div class="purchase-bottom-bar">
						<div class="purchase-bottom-bar__summary">
							<span class="purchase-bottom-bar__label">{{ __("Items") }}</span>
							<strong class="purchase-bottom-bar__amount">{{ totalQty }}</strong>
						</div>
						<v-btn
							:loading="submitLoading"
							:disabled="submitLoading || !transferItems.length"
							size="large"
							color="primary"
							class="text-none purchase-pay-btn"
							prepend-icon="mdi-send"
							@click="submitTransfer"
						>
							{{ __("Submit Transfer") }}
						</v-btn>
					</div>
				</v-card>
			</v-col>

			<v-col cols="12" md="5" class="h-100 pa-0 border-s">
				<ItemsSelector context="material_transfer" @add-item="onAddItem" />
			</v-col>
		</v-row>
	</div>
</template>

<script>
import { ref, computed, onMounted, watch } from 'vue';
import { useRouter } from 'vue-router';
import VueDatePicker from '@vuepic/vue-datepicker';
import format from '../../../format';
import { useUIStore } from '../../../stores/uiStore.js';
import { useToastStore } from '../../../stores/toastStore';
import { useMaterialTransfer } from '../../../composables/pos/material_transfer/useMaterialTransfer';
import { isPosWarehouseSwitcher } from '../../../utils/posWarehouseAccess';
import ItemsSelector from '../items/ItemsSelector.vue';
import RequisitionItemsTable from '../requisition/RequisitionItemsTable.vue';
import { getOpeningStorage } from '../../../../offline/index';
import { normalizeDateForBackend } from '../../../format';

const getTodayDate = () =>
	frappe?.datetime?.nowdate?.() || new Date().toISOString().slice(0, 10);

export default {
	name: 'MaterialTransferNew',
	mixins: [format],
	components: {
		ItemsSelector,
		RequisitionItemsTable,
		VueDatePicker,
	},
	setup() {
		const router = useRouter();
		const uiStore = useUIStore();
		const toastStore = useToastStore();
		const pos_profile = ref(uiStore.posProfile || {});
		const transactionDate = ref(getTodayDate());
		const warehouseOptions = ref([]);
		const fromWarehouseOptions = ref([]);
		const fromWarehouseLabel = ref('');
		const warehouseLoading = ref(false);
		const itemSearchQuery = ref('');
		const selectedSearchItemCode = ref(null);
		const itemSearchResults = ref([]);
		const itemSearchLoading = ref(false);
		let itemSearchTimeout = null;

		const canChangePosWarehouse = computed(() => isPosWarehouseSwitcher());

		const {
			transferItems,
			fromWarehouse,
			toWarehouse,
			notes,
			submitLoading,
			errorMessage,
			totalQty,
			onAddItem,
			updateItemQty,
			removeItem,
			resetForm,
			initWarehousesFromProfile,
		} = useMaterialTransfer({ posProfile: pos_profile });

		const toWarehouseOptions = computed(() => {
			if (!fromWarehouse.value) {
				return warehouseOptions.value;
			}
			return warehouseOptions.value.filter(
				(row) => row.name !== fromWarehouse.value,
			);
		});

		const transactionDateDisplay = computed({
			get: () => {
				const parts = String(transactionDate.value || '').split('-');
				return parts.length === 3
					? `${parts[2]}-${parts[1]}-${parts[0]}`
					: transactionDate.value;
			},
			set: (v) => {
				transactionDate.value = normalizeDateForBackend(v) || getTodayDate();
			},
		});

		const loadAllWarehouses = async () => {
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

		const loadActiveFromWarehouse = async () => {
			try {
				const { message } = await frappe.call({
					method: 'bsp_engineering.api.pos_warehouse.get_pos_active_warehouse',
					args: {
						company: pos_profile.value?.company,
						pos_profile: pos_profile.value
							? JSON.stringify(pos_profile.value)
							: null,
					},
				});
				const row = message || {};
				if (row.name) {
					fromWarehouse.value = row.name;
					fromWarehouseLabel.value = row.warehouse_name || row.name;
					return;
				}
			} catch (error) {
				console.error('Failed to load active warehouse:', error);
			}
			const profileWh = pos_profile.value?.warehouse || null;
			if (profileWh) {
				fromWarehouse.value = profileWh;
				fromWarehouseLabel.value = profileWh;
			}
		};

		const loadFromWarehouses = async () => {
			warehouseLoading.value = true;
			try {
				const { message } = await frappe.call({
					method: 'bsp_engineering.api.pos_warehouse.get_pos_warehouses',
					args: {
						company: pos_profile.value?.company,
						pos_profile: pos_profile.value
							? JSON.stringify(pos_profile.value)
							: null,
					},
				});
				const msg = message || {};
				const warehouseList = Array.isArray(msg) ? msg : (msg.warehouses || []);
				const suggestedDefault = Array.isArray(msg)
					? null
					: (msg.default_warehouse || null);
				fromWarehouseOptions.value = warehouseList;
				const permitted = warehouseList.map((row) => row.name);
				let defaultWh = suggestedDefault || pos_profile.value?.warehouse || null;
				if (defaultWh && permitted.length && !permitted.includes(defaultWh)) {
					defaultWh = permitted[0];
				}
				if (!defaultWh && fromWarehouseOptions.value.length) {
					defaultWh = fromWarehouseOptions.value[0].name;
				}
				if (defaultWh) {
					fromWarehouse.value = defaultWh;
				}
			} catch (error) {
				console.error('Failed to load from warehouses:', error);
				fromWarehouseOptions.value = [];
			}
			if (!fromWarehouseOptions.value.length && pos_profile.value?.warehouse) {
				const profileWh = pos_profile.value.warehouse;
				fromWarehouseOptions.value = [
					{ name: profileWh, warehouse_name: profileWh },
				];
				fromWarehouse.value = profileWh;
			}
			warehouseLoading.value = false;
		};

		const loadWarehouses = async () => {
			await loadAllWarehouses();
			if (canChangePosWarehouse.value) {
				await loadFromWarehouses();
			} else {
				await loadActiveFromWarehouse();
			}
		};

		const handleItemSearchUpdate = (term) => {
			if (itemSearchTimeout) clearTimeout(itemSearchTimeout);
			itemSearchTimeout = setTimeout(() => searchItems(term), 300);
		};

		const searchItems = async (searchText = '') => {
			if (!searchText || searchText.length < 2) {
				itemSearchResults.value = [];
				return;
			}
			itemSearchLoading.value = true;
			try {
				const { message } = await frappe.call({
					method: 'posawesome.posawesome.api.material_transfers.search_items',
					args: { search_text: searchText, limit: 20 },
				});
				itemSearchResults.value = message || [];
			} catch {
				itemSearchResults.value = [];
			} finally {
				itemSearchLoading.value = false;
			}
		};

		const handleSearchItemPicked = async (itemCode) => {
			if (!itemCode) return;
			const item = itemSearchResults.value.find((row) => row.item_code === itemCode);
			if (item) await onAddItem(item);
			selectedSearchItemCode.value = null;
			itemSearchQuery.value = '';
		};

		const resolveFromWarehouse = () =>
			canChangePosWarehouse.value
				? fromWarehouse.value
				: pos_profile.value?.warehouse || fromWarehouse.value;

		const submitTransfer = async () => {
			errorMessage.value = '';
			const resolvedFrom = resolveFromWarehouse();
			if (!resolvedFrom) {
				errorMessage.value = __('From Warehouse is required.');
				return;
			}
			if (!toWarehouse.value) {
				errorMessage.value = __('To Warehouse is required.');
				return;
			}
			if (resolvedFrom === toWarehouse.value) {
				errorMessage.value = __(
					'From Warehouse and To Warehouse cannot be the same.',
				);
				return;
			}
			if (!transferItems.value.length) {
				errorMessage.value = __('Add at least one item.');
				return;
			}

			submitLoading.value = true;
			try {
				const { message } = await frappe.call({
					method: 'posawesome.posawesome.api.material_transfers.create_material_transfer',
					args: {
						data: {
							transaction_date: transactionDate.value,
							from_warehouse: resolvedFrom,
							to_warehouse: toWarehouse.value,
							notes: notes.value,
							items: transferItems.value.map((row) => ({
								item_code: row.item_code,
								item_name: row.item_name,
								item_group: row.item_group,
								qty: row.qty,
								uom: row.uom,
								schedule_date: transactionDate.value,
							})),
						},
					},
					freeze: true,
					freeze_message: __('Submitting material transfer...'),
				});
				toastStore.show({
					title: __('Material Transfer {0} submitted', [message?.name || '']),
					color: 'success',
				});
				resetForm();
				await router.push('/material-transfers/list');
			} catch (e) {
				errorMessage.value = e?.message || __('Failed to submit material transfer');
			} finally {
				submitLoading.value = false;
			}
		};

		watch(fromWarehouse, (nextFrom) => {
			if (nextFrom && toWarehouse.value === nextFrom) {
				toWarehouse.value = null;
			}
		});

		onMounted(async () => {
			const opening = getOpeningStorage();
			if (opening?.pos_profile) {
				pos_profile.value = opening.pos_profile;
			} else if (uiStore.posProfile?.name) {
				pos_profile.value = uiStore.posProfile;
			}
			initWarehousesFromProfile();
			await loadWarehouses();
		});

		return {
			canChangePosWarehouse,
			fromWarehouse,
			fromWarehouseLabel,
			fromWarehouseOptions,
			toWarehouse,
			toWarehouseOptions,
			warehouseLoading,
			transactionDateDisplay,
			transferItems,
			notes,
			totalQty,
			submitLoading,
			errorMessage,
			itemSearchQuery,
			selectedSearchItemCode,
			itemSearchResults,
			itemSearchLoading,
			onAddItem,
			updateItemQty,
			removeItem,
			handleItemSearchUpdate,
			handleSearchItemPicked,
			submitTransfer,
		};
	},
};
</script>

<style scoped>
@import '../invoice-shared-styles.css';

.purchase-top-grid {
	grid-template-columns: 2.5fr 1fr 2fr !important;
	align-items: stretch;
	gap: 12px !important;
}

.purchase-top-grid > .invoice-section-card {
	height: 100%;
	display: flex;
	flex-direction: column;
}

.sale-options-body {
	padding: 8px 14px 12px;
}

@media (max-width: 768px) {
	.purchase-top-grid {
		grid-template-columns: 1fr !important;
	}
}
</style>
