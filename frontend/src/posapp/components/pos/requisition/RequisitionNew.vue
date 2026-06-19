<template>
	<div class="pa-0 h-100 invoice-shell">
		<v-row class="h-100 ma-0">
			<v-col cols="12" md="7" class="h-100 pa-0">
				<v-card class="h-100 d-flex flex-column pos-themed-card purchase-invoice-card" flat>
					<v-card-text class="flex-grow-1 overflow-y-auto pa-3 pa-md-4">
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
											v-if="canChangePosWarehouse && sourceWarehouseOptions.length"
											v-model="sourceWarehouse"
											:items="sourceWarehouseOptions"
											item-title="warehouse_name"
											item-value="name"
											:label="__('Source Warehouse')"
											density="compact"
											variant="outlined"
											color="primary"
											hide-details
											:loading="warehouseLoading"
											class="pos-themed-input mb-2"
										/>
										<v-text-field
											v-else-if="sourceWarehouse"
											:model-value="sourceWarehouseLabel || sourceWarehouse"
											:label="__('Source Warehouse')"
											density="compact"
											variant="outlined"
											color="primary"
											hide-details
											readonly
											prepend-inner-icon="mdi-warehouse"
											class="pos-themed-input mb-2"
										/>
										<v-autocomplete
											v-model="targetWarehouse"
											:items="targetWarehouseOptions"
											item-title="warehouse_name"
											item-value="name"
											:label="__('Target Warehouse')"
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
											{{ requisitionItems.length }}
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
									<h3 class="invoice-section-heading__title">{{ __("Requisition Items") }}</h3>
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
									:items="requisitionItems"
									@update-qty="({ item, value }) => updateItemQty(item, value)"
									@remove-item="removeItem"
								/>
							</v-card>

							<v-card flat class="invoice-section-card pos-themed-card notes-section-card">
								<div class="invoice-section-heading">
									<h3 class="invoice-section-heading__title">{{ __("Notes") }}</h3>
								</div>
								<div class="sale-options-body">
									<v-textarea
										v-model="notes"
										:label="__('Notes')"
										variant="outlined"
										density="compact"
										hide-details
										rows="2"
										class="pos-themed-input"
									/>
								</div>
							</v-card>

							<v-alert v-if="errorMessage" type="error" density="compact">
								{{ errorMessage }}
							</v-alert>
						</div>
					</v-card-text>

					<div class="purchase-bottom-bar">
						<div class="purchase-bottom-bar__summary">
							<span class="purchase-bottom-bar__label">{{ __("Total Qty") }}</span>
							<strong class="purchase-bottom-bar__amount">{{ totalQty }}</strong>
							<span class="purchase-bottom-bar__meta">
								{{ requisitionItems.length }}
								{{ requisitionItems.length === 1 ? __("item") : __("items") }}
							</span>
						</div>
						<v-btn
							:loading="submitLoading"
							:disabled="submitLoading || !requisitionItems.length"
							size="large"
							color="primary"
							class="text-none purchase-pay-btn"
							prepend-icon="mdi-send"
							@click="submitRequisition"
						>
							{{ __("Submit Requisition") }}
						</v-btn>
					</div>
				</v-card>
			</v-col>

			<v-col cols="12" md="5" class="h-100 pa-0 border-s">
				<ItemsSelector context="requisition" @add-item="onAddItem" />
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
import { useRequisition } from '../../../composables/pos/requisition/useRequisition';
import { isPosWarehouseSwitcher } from '../../../utils/posWarehouseAccess';
import ItemsSelector from '../items/ItemsSelector.vue';
import RequisitionItemsTable from './RequisitionItemsTable.vue';
import { getOpeningStorage } from '../../../../offline/index';
import { normalizeDateForBackend } from '../../../format';

const getTodayDate = () =>
	frappe?.datetime?.nowdate?.() || new Date().toISOString().slice(0, 10);

export default {
	name: 'RequisitionNew',
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
		const sourceWarehouseOptions = ref([]);
		const sourceWarehouseLabel = ref('');
		const warehouseLoading = ref(false);
		const itemSearchQuery = ref('');
		const selectedSearchItemCode = ref(null);
		const itemSearchResults = ref([]);
		const itemSearchLoading = ref(false);
		let itemSearchTimeout = null;

		const canChangePosWarehouse = computed(() => isPosWarehouseSwitcher());

		const {
			requisitionItems,
			sourceWarehouse,
			targetWarehouse,
			notes,
			submitLoading,
			errorMessage,
			totalQty,
			onAddItem,
			updateItemQty,
			removeItem,
			resetForm,
			initWarehousesFromProfile,
		} = useRequisition({ posProfile: pos_profile });

		const targetWarehouseOptions = computed(() => {
			if (!sourceWarehouse.value) {
				return warehouseOptions.value;
			}
			return warehouseOptions.value.filter(
				(row) => row.name !== sourceWarehouse.value,
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

		const loadActiveSourceWarehouse = async () => {
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
					sourceWarehouse.value = row.name;
					sourceWarehouseLabel.value = row.warehouse_name || row.name;
					return;
				}
			} catch (error) {
				console.error('Failed to load active warehouse:', error);
			}
			const profileWh = pos_profile.value?.warehouse || null;
			if (profileWh) {
				sourceWarehouse.value = profileWh;
				sourceWarehouseLabel.value = profileWh;
			}
		};

		const loadSourceWarehouses = async () => {
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
				sourceWarehouseOptions.value = warehouseList;
				const permitted = warehouseList.map((row) => row.name);
				let defaultWh = suggestedDefault || pos_profile.value?.warehouse || null;
				if (defaultWh && permitted.length && !permitted.includes(defaultWh)) {
					defaultWh = permitted[0];
				}
				if (!defaultWh && sourceWarehouseOptions.value.length) {
					defaultWh = sourceWarehouseOptions.value[0].name;
				}
				if (defaultWh) {
					sourceWarehouse.value = defaultWh;
				}
			} catch (error) {
				console.error('Failed to load source warehouses:', error);
				sourceWarehouseOptions.value = [];
			}
			if (!sourceWarehouseOptions.value.length && pos_profile.value?.warehouse) {
				const profileWh = pos_profile.value.warehouse;
				sourceWarehouseOptions.value = [
					{ name: profileWh, warehouse_name: profileWh },
				];
				sourceWarehouse.value = profileWh;
			}
			warehouseLoading.value = false;
		};

		const loadWarehouses = async () => {
			await loadAllWarehouses();
			if (canChangePosWarehouse.value) {
				await loadSourceWarehouses();
			} else {
				await loadActiveSourceWarehouse();
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
					method: 'posawesome.posawesome.api.requisitions.search_items',
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

		const resolveSourceWarehouse = () =>
			canChangePosWarehouse.value
				? sourceWarehouse.value
				: pos_profile.value?.warehouse || sourceWarehouse.value;

		const submitRequisition = async () => {
			errorMessage.value = '';
			const resolvedSource = resolveSourceWarehouse();
			if (!resolvedSource) {
				errorMessage.value = __('Source Warehouse is required.');
				return;
			}
			if (!targetWarehouse.value) {
				errorMessage.value = __('Target Warehouse is required.');
				return;
			}
			if (resolvedSource === targetWarehouse.value) {
				errorMessage.value = __(
					'Source Warehouse and Target Warehouse cannot be the same.',
				);
				return;
			}
			if (!requisitionItems.value.length) {
				errorMessage.value = __('Add at least one item.');
				return;
			}

			submitLoading.value = true;
			try {
				const { message } = await frappe.call({
					method: 'posawesome.posawesome.api.requisitions.create_requisition',
					args: {
						data: {
							transaction_date: transactionDate.value,
							source_warehouse: resolvedSource,
							target_warehouse: targetWarehouse.value,
							notes: notes.value,
							items: requisitionItems.value.map((row) => ({
								item_code: row.item_code,
								item_name: row.item_name,
								item_group: row.item_group,
								required_qty: row.qty,
								uom: row.uom,
								schedule_date: transactionDate.value,
							})),
						},
					},
					freeze: true,
					freeze_message: __('Submitting requisition...'),
				});
				toastStore.show({
					title: __('Requisition {0} submitted', [message?.name || '']),
					color: 'success',
				});
				resetForm();
				await router.push('/requisitions/list');
			} catch (e) {
				errorMessage.value = e?.message || __('Failed to submit requisition');
			} finally {
				submitLoading.value = false;
			}
		};

		watch(sourceWarehouse, (nextSource) => {
			if (nextSource && targetWarehouse.value === nextSource) {
				targetWarehouse.value = null;
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
			sourceWarehouse,
			sourceWarehouseLabel,
			sourceWarehouseOptions,
			targetWarehouse,
			targetWarehouseOptions,
			warehouseLoading,
			transactionDateDisplay,
			requisitionItems,
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
			submitRequisition,
		};
	},
};
</script>

<style scoped>
@import '../invoice-shared-styles.css';
</style>
