<template>
	<div class="pa-0 h-100 invoice-shell txn-shell" :style="responsiveStyles">
		<v-row class="h-100 ma-0">
			<v-col
				v-show="showInvoicePanel"
				cols="12"
				:md="invoiceCols"
				class="h-100 pa-0 txn-col txn-col--invoice"
			>
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
											{{ transferItems.length === 1 ? __("item") : __("items") }}
										</div>
									</div>
								</v-card>

								<v-card flat class="invoice-section-card pos-themed-card sale-options-card">
									<div class="invoice-section-heading">
										<h3 class="invoice-section-heading__title">
											{{ __("Transfer Date") }}
										</h3>
									</div>
									<div class="sale-options-body">
										<VueDatePicker
											v-model="requiredDateDisplay"
											model-type="format"
											format="dd-MM-yyyy"
											auto-apply
											teleport
											:placeholder="__('Transfer Date')"
											class="sleek-field pos-themed-input"
										/>
									</div>
								</v-card>
							</div>

							<v-card
								v-if="canEditDoNumber"
								flat
								class="invoice-section-card pos-themed-card"
							>
								<div class="invoice-section-heading">
									<h3 class="invoice-section-heading__title">{{ __("DO Number") }}</h3>
								</div>
								<div class="pa-3">
									<v-text-field
										v-model="customDoNumber"
										:label="__('DO Number')"
										density="compact"
										variant="outlined"
										hide-details
										class="pos-themed-input"
										:loading="doNumberLookupLoading"
										@keyup.enter="handleDoNumberLookup"
										@update:focused="onDoNumberFocusChange"
									/>
								</div>
							</v-card>

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

					<div v-if="!isCompact" class="purchase-bottom-bar">
						<div class="purchase-bottom-bar__summary">
							<span class="purchase-bottom-bar__label">{{ __("Total Qty") }}</span>
							<strong class="purchase-bottom-bar__amount">{{ totalQty }}</strong>
							<span class="purchase-bottom-bar__meta">
								{{ transferItems.length }}
								{{ transferItems.length === 1 ? __("item") : __("items") }}
							</span>
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

			<v-col
				v-show="showSelectorPanel"
				cols="12"
				:md="selectorCols"
				class="h-100 pa-0 border-s txn-col txn-col--selector"
			>
				<ItemsSelector context="material_transfer" @add-item="onAddItem" />
			</v-col>
		</v-row>

		<div v-if="isCompact" class="mobile-pos-stack txn-bottom-dock">
			<div class="mobile-sale-dock">
				<div class="mobile-sale-dock__copy">
					<span class="mobile-sale-dock__eyebrow">{{ __("Total Qty") }}</span>
					<strong class="mobile-sale-dock__amount">{{ totalQty }}</strong>
					<span class="mobile-sale-dock__meta">
						{{ transferItems.length }}
						{{ transferItems.length === 1 ? __("item") : __("items") }}
					</span>
				</div>
				<v-btn
					:loading="submitLoading"
					:disabled="submitLoading || !transferItems.length"
					color="primary"
					variant="flat"
					class="text-none txn-dock-pay-btn"
					prepend-icon="mdi-send"
					@click="submitTransfer"
				>
					{{ __("Submit Transfer") }}
				</v-btn>
			</div>
			<div class="mobile-pos-dock">
				<button
					type="button"
					class="mobile-pos-dock__item"
					:class="{ 'mobile-pos-dock__item--active': compactPanel === 'selector' }"
					@click="setPanel('selector')"
				>
					<v-icon icon="mdi-magnify" size="20" />
					<span>{{ __("Browse") }}</span>
				</button>
				<button
					type="button"
					class="mobile-pos-dock__item"
					:class="{ 'mobile-pos-dock__item--active': compactPanel === 'invoice' }"
					@click="setPanel('invoice')"
				>
					<span v-if="transferItems.length" class="mobile-pos-dock__pill">{{ transferItems.length }}</span>
					<v-icon icon="mdi-cart-outline" size="22" />
					<span>{{ __("Cart") }}</span>
				</button>
				<button
					type="button"
					class="mobile-pos-dock__item mobile-pos-dock__item--pay"
					@click="submitTransfer"
				>
					<v-icon icon="mdi-send" size="20" />
					<span>{{ __("Submit") }}</span>
				</button>
			</div>
		</div>
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
import { useItemsStore } from '../../../stores/itemsStore';
import { isPosWarehouseSwitcher } from '../../../utils/posWarehouseAccess';
import ItemsSelector from '../items/ItemsSelector.vue';
import RequisitionItemsTable from '../requisition/RequisitionItemsTable.vue';
import { getOpeningStorage } from '../../../../offline/index';
import { normalizeDateForBackend } from '../../../format';
import { useCompactTransactionPanel } from '../../../composables/core/useCompactTransactionPanel';

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
		const itemsStore = useItemsStore();
		const {
			responsiveStyles,
			isCompact,
			compactPanel,
			showInvoicePanel,
			showSelectorPanel,
			invoiceCols,
			selectorCols,
			setPanel,
		} = useCompactTransactionPanel('invoice');
		const pos_profile = ref(uiStore.posProfile || {});
		const requiredDate = ref(getTodayDate());
		const warehouseOptions = ref([]);
		const fromWarehouseOptions = ref([]);
		const fromWarehouseLabel = ref('');
		const warehouseLoading = ref(false);
		const itemSearchQuery = ref('');
		const selectedSearchItemCode = ref(null);
		const itemSearchResults = ref([]);
		const itemSearchLoading = ref(false);
		let itemSearchTimeout = null;
		const customDoNumber = ref('');
		const doNumberLookupLoading = ref(false);

		const canChangePosWarehouse = computed(() => isPosWarehouseSwitcher());
		// Same gate Invoice.vue uses for its own DO Number card -- keep the two
		// in sync if that role check ever changes.
		const canEditDoNumber = computed(() => {
			const roles = frappe?.boot?.user?.roles || [];
			return roles.includes('BSP Admin') || roles.includes('System Manager');
		});

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

		const requiredDateDisplay = computed({
			get: () => {
				const parts = String(requiredDate.value || '').split('-');
				return parts.length === 3
					? `${parts[2]}-${parts[1]}-${parts[0]}`
					: requiredDate.value;
			},
			set: (v) => {
				requiredDate.value = normalizeDateForBackend(v) || getTodayDate();
			},
		});

		const refreshCatalogForWarehouse = async (wh) => {
			if (!wh) {
				return;
			}
			itemsStore.setActiveSaleWarehouse(wh);
			if (typeof itemsStore.refreshItems === 'function') {
				await itemsStore.refreshItems({
					warehouse: wh,
					forceServer: true,
				});
			}
		};

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
					await refreshCatalogForWarehouse(row.name);
					return;
				}
			} catch (error) {
				console.error('Failed to load active warehouse:', error);
			}
			const profileWh = pos_profile.value?.warehouse || null;
			if (profileWh) {
				fromWarehouse.value = profileWh;
				fromWarehouseLabel.value = profileWh;
				await refreshCatalogForWarehouse(profileWh);
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
					await refreshCatalogForWarehouse(defaultWh);
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
				await refreshCatalogForWarehouse(profileWh);
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

		// Same idea as Invoice.vue's DO Number lookup on the Sales screen: items
		// actually received under this DO (posawesome.posawesome.api.purchase_invoices
		// .get_items_by_do_number, capped by current stock in the From Warehouse)
		// are added to the transfer's item table at qty 1 -- same as clicking a
		// search result -- so the user still confirms/adjusts the quantity being
		// moved rather than a DO number silently pre-filling a large transfer.
		const onDoNumberFocusChange = (focused) => {
			if (!focused) {
				handleDoNumberLookup();
			}
		};

		const handleDoNumberLookup = async () => {
			const doNumber = (customDoNumber.value || '').trim();
			if (!doNumber) return;

			const resolvedFrom = resolveFromWarehouse();
			if (!resolvedFrom) {
				toastStore.show({ title: __('Set the From Warehouse first.'), color: 'warning' });
				return;
			}

			doNumberLookupLoading.value = true;
			try {
				const lookup = await frappe.call({
					method: 'posawesome.posawesome.api.purchase_invoices.get_items_by_do_number',
					args: {
						do_number: doNumber,
						warehouse: resolvedFrom,
						company: pos_profile.value?.company,
					},
				});
				const result = lookup?.message || { items: [], unavailable: [] };
				const foundItems = result.items || [];
				const unavailable = result.unavailable || [];

				let addedCount = 0;
				for (const row of foundItems) {
					try {
						const { message } = await frappe.call({
							method: 'posawesome.posawesome.api.material_transfers.search_items',
							args: { search_text: row.item_code, limit: 20 },
						});
						const matches = message || [];
						const catalogItem =
							matches.find((m) => m.item_code === row.item_code) || matches[0];
						if (!catalogItem) continue;
						await onAddItem({ ...catalogItem });
						addedCount += 1;
					} catch (itemError) {
						console.error('Failed to add DO item', row.item_code, itemError);
					}
				}

				if (addedCount) {
					toastStore.show({
						title: __('{0} item(s) added from DO {1}', [addedCount, doNumber]),
						color: 'success',
					});
				}

				if (unavailable.length) {
					const names = unavailable.map((row) => row.item_name || row.item_code).join(', ');
					toastStore.show({
						title: __('Not available in this warehouse'),
						detail: names,
						color: 'warning',
					});
				}

				if (!foundItems.length && !unavailable.length) {
					toastStore.show({
						title: __('No received items found for DO {0}', [doNumber]),
						color: 'warning',
					});
				}
			} catch (error) {
				console.error('Error looking up DO Number:', error);
				toastStore.show({ title: __('Error looking up DO Number'), color: 'error' });
			} finally {
				doNumberLookupLoading.value = false;
			}
		};

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
							transaction_date: getTodayDate(),
							from_warehouse: resolvedFrom,
							to_warehouse: toWarehouse.value,
							custom_do_number: customDoNumber.value,
							notes: notes.value,
							items: transferItems.value.map((row) => ({
								item_code: row.item_code,
								item_name: row.item_name,
								item_group: row.item_group,
								qty: row.qty,
								uom: row.uom,
								schedule_date: requiredDate.value,
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
				customDoNumber.value = '';
				await router.push('/material-transfers/list');
			} catch (e) {
				errorMessage.value = e?.message || __('Failed to submit material transfer');
			} finally {
				submitLoading.value = false;
			}
		};

		watch(fromWarehouse, async (nextFrom) => {
			if (nextFrom && toWarehouse.value === nextFrom) {
				toWarehouse.value = null;
			}
			await refreshCatalogForWarehouse(nextFrom);
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
			responsiveStyles,
			isCompact,
			compactPanel,
			showInvoicePanel,
			showSelectorPanel,
			invoiceCols,
			selectorCols,
			setPanel,
			canChangePosWarehouse,
			canEditDoNumber,
			customDoNumber,
			doNumberLookupLoading,
			fromWarehouse,
			fromWarehouseLabel,
			fromWarehouseOptions,
			toWarehouse,
			toWarehouseOptions,
			warehouseLoading,
			requiredDateDisplay,
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
			onDoNumberFocusChange,
			handleDoNumberLookup,
			submitTransfer,
		};
	},
};
</script>

<style scoped>
@import '../invoice-shared-styles.css';
</style>
