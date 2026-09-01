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
							<div class="invoice-top-grid bom-top-grid">
								<v-card flat class="invoice-section-card pos-themed-card">
									<div class="invoice-section-heading">
										<h3 class="invoice-section-heading__title">
											{{ __("Warehouse") }}
										</h3>
									</div>
									<div class="sale-options-body">
										<v-autocomplete
											:model-value="activeWarehouse"
											:items="warehouseOptions"
											item-title="warehouse_name"
											item-value="name"
											:label="__('Warehouse')"
											density="compact"
											variant="outlined"
											color="primary"
											hide-details
											:loading="warehouseLoading"
											class="pos-themed-input"
											@update:model-value="handleWarehouseChange"
										/>
									</div>
								</v-card>

								<v-card flat class="invoice-section-card pos-themed-card">
									<div class="invoice-section-heading">
										<h3 class="invoice-section-heading__title">
											{{ __("Item to Manufacture") }}
										</h3>
									</div>
									<div class="sale-options-body">
										<v-autocomplete
											v-model:search="manufactureSearchQuery"
											:model-value="selectedManufactureItemCode"
											:items="manufactureSearchResults"
											:loading="manufactureSearchLoading"
											item-title="item_name"
											item-value="item_code"
											:label="__('Search by item code or name')"
											:placeholder="__('Browse below or type to search')"
											:custom-filter="() => true"
											prepend-inner-icon="mdi-magnify"
											variant="outlined"
											density="compact"
											color="primary"
											hide-details
											clearable
											class="pos-themed-input"
											:no-data-text="__('No items found')"
											@update:search="handleManufactureSearchUpdate"
											@update:model-value="handleManufactureItemPicked"
										>
											<template #item="{ props: itemProps, item }">
												<v-list-item v-bind="itemProps" :title="undefined">
													<v-list-item-title class="purchase-item-option__title">
														{{ item.raw.item_name }}
													</v-list-item-title>
													<v-list-item-subtitle class="purchase-item-option__meta">
														<span class="purchase-item-option__code">{{ item.raw.item_code }}</span>
														<span class="purchase-item-option__stock">
															{{ __("UOM") }}: {{ item.raw.stock_uom || "" }}
														</span>
													</v-list-item-subtitle>
												</v-list-item>
											</template>
										</v-autocomplete>

										<div v-if="manufactureItem.item_code" class="bom-selected-item mt-3">
											<div class="font-weight-medium">{{ manufactureItem.item_name }}</div>
											<div class="text-caption text-medium-emphasis">{{ manufactureItem.item_code }}</div>
										</div>
									</div>
								</v-card>

								<v-card flat class="invoice-section-card pos-themed-card outstanding-panel">
									<div class="outstanding-panel__inner">
										<div class="outstanding-panel__label">{{ __("Raw Materials") }}</div>
										<div class="outstanding-panel__amount outstanding-panel__amount--clear">
											{{ rawMaterials.length }}
										</div>
										<div class="text-caption text-medium-emphasis">
											{{ rawMaterials.length === 1 ? __("line") : __("lines") }}
										</div>
									</div>
								</v-card>

								<v-card flat class="invoice-section-card pos-themed-card sale-options-card">
									<div class="invoice-section-heading">
										<h3 class="invoice-section-heading__title">
											{{ __("Produces Qty") }}
										</h3>
									</div>
									<div class="sale-options-body">
										<v-text-field
											v-model="quantity"
											type="number"
											min="0.01"
											:label="__('Quantity')"
											:suffix="manufactureItem.stock_uom || ''"
											density="compact"
											variant="outlined"
											color="primary"
											hide-details
											class="pos-themed-input"
										/>
									</div>
								</v-card>
							</div>

							<v-card flat class="invoice-section-card invoice-items-card pos-themed-card">
								<div class="invoice-section-heading">
									<h3 class="invoice-section-heading__title">{{ __("Raw Materials") }}</h3>
									<p class="text-caption text-medium-emphasis mb-0">
										{{ __("Items consumed to produce the quantity above") }}
									</p>
								</div>
								<div class="purchase-search-toolbar">
									<v-autocomplete
										v-model:search="rawMaterialSearchQuery"
										:model-value="selectedRawMaterialItemCode"
										:items="rawMaterialSearchResults"
										:loading="rawMaterialSearchLoading"
										:disabled="!manufactureItem.item_code"
										item-title="item_name"
										item-value="item_code"
										:label="__('Search by item code or name')"
										:placeholder="
											!manufactureItem.item_code
												? __('Select an item to manufacture first')
												: __('Browse below or type to search')
										"
										:custom-filter="() => true"
										prepend-inner-icon="mdi-magnify"
										variant="solo"
										density="compact"
										color="primary"
										hide-details
										clearable
										class="pos-themed-input purchase-item-search"
										:no-data-text="__('No items found')"
										@update:search="handleRawMaterialSearchUpdate"
										@update:model-value="handleRawMaterialPicked"
									>
										<template #item="{ props: itemProps, item }">
											<v-list-item v-bind="itemProps" :title="undefined">
												<v-list-item-title class="purchase-item-option__title">
													{{ item.raw.item_name }}
												</v-list-item-title>
												<v-list-item-subtitle class="purchase-item-option__meta">
													<span class="purchase-item-option__code">{{ item.raw.item_code }}</span>
													<span class="purchase-item-option__stock">
														{{ __("UOM") }}: {{ item.raw.stock_uom || "" }}
													</span>
												</v-list-item-subtitle>
											</v-list-item>
										</template>
									</v-autocomplete>
								</div>
								<div class="raw-materials-table">
									<v-table density="compact" class="pos-themed-table">
										<thead>
											<tr>
												<th>{{ __("Raw Material") }}</th>
												<th class="text-center">{{ __("UOM") }}</th>
												<th class="text-center">{{ __("Qty") }}</th>
												<th class="text-center">{{ __("Weight") }}</th>
												<th class="text-center" style="width: 48px;"></th>
											</tr>
										</thead>
										<tbody>
											<tr v-if="!rawMaterials.length">
												<td colspan="5" class="text-center text-medium-emphasis py-4">
													{{ __("Add raw materials from the search above") }}
												</td>
											</tr>
											<tr v-for="row in rawMaterials" :key="row.line_id">
												<td>
													<div class="font-weight-medium">{{ row.item_name }}</div>
													<div class="text-caption text-medium-emphasis">{{ row.item_code }}</div>
												</td>
												<td class="text-center text-caption">{{ row.uom }}</td>
												<td class="text-center" style="max-width: 100px;">
													<v-text-field
														:model-value="row.qty"
														type="number"
														density="compact"
														variant="outlined"
														hide-details
														min="0"
														class="pos-themed-input qty-field"
														@update:model-value="(v) => updateRawMaterialQty(row, v)"
													/>
												</td>
												<td class="text-center text-caption">
													{{ (Number(row.qty || 0) * Number(row.custom_default_weigt_of_measure || 0)).toFixed(2) }}
												</td>
												<td class="text-center">
													<v-btn
														icon="mdi-delete-outline"
														variant="text"
														size="small"
														color="error"
														@click="removeRawMaterial(row)"
													/>
												</td>
											</tr>
										</tbody>
									</v-table>
								</div>
							</v-card>

							<v-alert v-if="errorMessage" type="error" density="compact">
								{{ errorMessage }}
							</v-alert>
						</div>
					</v-card-text>

					<div v-if="!isCompact" class="purchase-bottom-bar">
						<div class="purchase-bottom-bar__summary">
							<span class="purchase-bottom-bar__label">{{ __("Raw Materials") }}</span>
							<strong class="purchase-bottom-bar__amount">{{ rawMaterials.length }}</strong>
							<span class="purchase-bottom-bar__meta">
								{{ rawMaterials.length === 1 ? __("line") : __("lines") }}
							</span>
						</div>
						<v-btn
							:loading="submitLoading"
							:disabled="submitLoading || !manufactureItem.item_code || !rawMaterials.length"
							size="large"
							color="primary"
							class="text-none purchase-pay-btn"
							prepend-icon="mdi-send"
							@click="submitBom"
						>
							{{ __("Create BOM") }}
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
				<ItemsSelector context="bom" @add-item="onAddRawMaterial" />
			</v-col>
		</v-row>

		<div v-if="isCompact" class="mobile-pos-stack txn-bottom-dock">
			<div class="mobile-sale-dock">
				<div class="mobile-sale-dock__copy">
					<span class="mobile-sale-dock__eyebrow">{{ __("Raw Materials") }}</span>
					<strong class="mobile-sale-dock__amount">{{ rawMaterials.length }}</strong>
					<span class="mobile-sale-dock__meta">
						{{ rawMaterials.length === 1 ? __("line") : __("lines") }}
					</span>
				</div>
				<v-btn
					:loading="submitLoading"
					:disabled="submitLoading || !manufactureItem.item_code || !rawMaterials.length"
					color="primary"
					variant="flat"
					class="text-none txn-dock-pay-btn"
					prepend-icon="mdi-send"
					@click="submitBom"
				>
					{{ __("Create BOM") }}
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
					<span v-if="rawMaterials.length" class="mobile-pos-dock__pill">{{ rawMaterials.length }}</span>
					<v-icon icon="mdi-cart-outline" size="22" />
					<span>{{ __("Cart") }}</span>
				</button>
				<button
					type="button"
					class="mobile-pos-dock__item mobile-pos-dock__item--pay"
					@click="submitBom"
				>
					<v-icon icon="mdi-send" size="20" />
					<span>{{ __("Submit") }}</span>
				</button>
			</div>
		</div>
	</div>
</template>

<script>
import { ref, reactive, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useUIStore } from '../../../stores/uiStore.js';
import { useToastStore } from '../../../stores/toastStore';
import { useItemsStore } from '../../../stores/itemsStore';
import ItemsSelector from '../items/ItemsSelector.vue';
import { useCompactTransactionPanel } from '../../../composables/core/useCompactTransactionPanel';

export default {
	name: 'BomNew',
	components: {
		ItemsSelector,
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

		const manufactureItem = reactive({ item_code: null, item_name: '', stock_uom: '' });
		const selectedManufactureItemCode = ref(null);
		const manufactureSearchQuery = ref('');
		const manufactureSearchResults = ref([]);
		const manufactureSearchLoading = ref(false);
		const manufactureDefaultResults = ref([]);
		let manufactureSearchTimeout = null;

		const quantity = ref(1);

		const warehouseOptions = ref([]);
		const warehouseLoading = ref(false);
		const activeWarehouse = ref(null);

		const rawMaterials = ref([]);
		const selectedRawMaterialItemCode = ref(null);
		const rawMaterialSearchQuery = ref('');
		const rawMaterialSearchResults = ref([]);
		const rawMaterialSearchLoading = ref(false);
		const rawMaterialDefaultResults = ref([]);
		let rawMaterialSearchTimeout = null;

		const submitLoading = ref(false);
		const errorMessage = ref('');

		const loadDefaultManufactureItems = async () => {
			try {
				const { message } = await frappe.call({
					method: 'posawesome.posawesome.api.boms.search_bom_items',
					args: { limit: 20 },
				});
				manufactureDefaultResults.value = message || [];
				if (!manufactureSearchQuery.value || manufactureSearchQuery.value.trim().length < 2) {
					manufactureSearchResults.value = manufactureDefaultResults.value;
				}
			} catch (e) {
				console.error('Failed to load default items', e);
			}
		};

		const handleManufactureSearchUpdate = (term) => {
			if (manufactureSearchTimeout) clearTimeout(manufactureSearchTimeout);
			if (!term || term.trim().length < 2) {
				manufactureSearchResults.value = manufactureDefaultResults.value;
				return;
			}
			manufactureSearchTimeout = setTimeout(async () => {
				manufactureSearchLoading.value = true;
				try {
					const { message } = await frappe.call({
						method: 'posawesome.posawesome.api.boms.search_bom_items',
						args: { search_text: term.trim(), limit: 20 },
					});
					manufactureSearchResults.value = message || [];
				} catch {
					manufactureSearchResults.value = [];
				} finally {
					manufactureSearchLoading.value = false;
				}
			}, 300);
		};

		const loadDefaultRawMaterialItems = async () => {
			try {
				const { message } = await frappe.call({
					method: 'posawesome.posawesome.api.boms.search_bom_items',
					args: {
						limit: 20,
						stock_items_only: 1,
						exclude_item_code: manufactureItem.item_code || undefined,
					},
				});
				rawMaterialDefaultResults.value = message || [];
				if (!rawMaterialSearchQuery.value || rawMaterialSearchQuery.value.trim().length < 2) {
					rawMaterialSearchResults.value = rawMaterialDefaultResults.value;
				}
			} catch (e) {
				console.error('Failed to load default raw materials', e);
			}
		};

		const handleRawMaterialSearchUpdate = (term) => {
			if (rawMaterialSearchTimeout) clearTimeout(rawMaterialSearchTimeout);
			if (!term || term.trim().length < 2) {
				rawMaterialSearchResults.value = rawMaterialDefaultResults.value;
				return;
			}
			rawMaterialSearchTimeout = setTimeout(async () => {
				rawMaterialSearchLoading.value = true;
				try {
					const { message } = await frappe.call({
						method: 'posawesome.posawesome.api.boms.search_bom_items',
						args: {
							search_text: term.trim(),
							limit: 20,
							stock_items_only: 1,
							exclude_item_code: manufactureItem.item_code || undefined,
						},
					});
					rawMaterialSearchResults.value = message || [];
				} catch {
					rawMaterialSearchResults.value = [];
				} finally {
					rawMaterialSearchLoading.value = false;
				}
			}, 300);
		};

		const handleManufactureItemPicked = (itemCode) => {
			selectedManufactureItemCode.value = null;
			if (!itemCode) {
				manufactureItem.item_code = null;
				manufactureItem.item_name = '';
				manufactureItem.stock_uom = '';
				return;
			}
			const item = manufactureSearchResults.value.find((row) => row.item_code === itemCode);
			if (!item) return;
			manufactureItem.item_code = item.item_code;
			manufactureItem.item_name = item.item_name;
			manufactureItem.stock_uom = item.stock_uom;
			manufactureSearchQuery.value = '';
			manufactureSearchResults.value = manufactureDefaultResults.value;

			// Manufactured item can't also be its own raw material.
			rawMaterials.value = rawMaterials.value.filter((row) => row.item_code !== itemCode);
			loadDefaultRawMaterialItems();
		};

		const onAddRawMaterial = (item) => {
			if (!item?.item_code) return;
			if (manufactureItem.item_code && item.item_code === manufactureItem.item_code) {
				toastStore.show({
					title: __('The item being manufactured cannot also be a raw material.'),
					color: 'warning',
				});
				return;
			}
			const existing = rawMaterials.value.find((row) => row.item_code === item.item_code);
			if (existing) {
				existing.qty += 1;
				return;
			}
			rawMaterials.value.unshift({
				line_id: `bomrm_${Date.now()}_${Math.floor(Math.random() * 10000)}`,
				item_code: item.item_code,
				item_name: item.item_name,
				uom: item.stock_uom,
				qty: 1,
				custom_default_weigt_of_measure: item.custom_default_weigt_of_measure || 0,
			});
		};

		const handleRawMaterialPicked = (itemCode) => {
			if (!itemCode) return;
			const item = rawMaterialSearchResults.value.find((row) => row.item_code === itemCode);
			if (item) onAddRawMaterial(item);
			selectedRawMaterialItemCode.value = null;
			rawMaterialSearchQuery.value = '';
			rawMaterialSearchResults.value = rawMaterialDefaultResults.value;
		};

		const updateRawMaterialQty = (row, value) => {
			row.qty = Math.max(0, Number(value) || 0);
		};

		const removeRawMaterial = (row) => {
			rawMaterials.value = rawMaterials.value.filter((r) => r.line_id !== row.line_id);
		};

		const submitBom = async () => {
			errorMessage.value = '';
			if (!manufactureItem.item_code) {
				errorMessage.value = __('Select an item to manufacture.');
				return;
			}
			if (!Number(quantity.value) || Number(quantity.value) <= 0) {
				errorMessage.value = __('Produces Qty must be greater than 0.');
				return;
			}
			if (!rawMaterials.value.length) {
				errorMessage.value = __('Add at least one raw material.');
				return;
			}

			submitLoading.value = true;
			try {
				const { message } = await frappe.call({
					method: 'posawesome.posawesome.api.boms.create_bom',
					args: {
						data: {
							pos_profile: pos_profile.value?.name,
							item_code: manufactureItem.item_code,
							quantity: quantity.value,
							items: rawMaterials.value.map((row) => ({
								item_code: row.item_code,
								qty: row.qty,
							})),
						},
					},
					freeze: true,
					freeze_message: __('Creating BOM...'),
				});
				toastStore.show({
					title: __('BOM {0} created', [message?.name || '']),
					color: 'success',
				});
				rawMaterials.value = [];
				await router.push('/boms/list');
			} catch (e) {
				errorMessage.value = e?.message || __('Failed to create BOM');
			} finally {
				submitLoading.value = false;
			}
		};

		const loadWarehouses = async () => {
			warehouseLoading.value = true;
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
			} finally {
				warehouseLoading.value = false;
			}
		};

		const handleWarehouseChange = async (value) => {
			activeWarehouse.value = value;
			if (!value) return;
			itemsStore.setActiveSaleWarehouse(value);
			if (typeof itemsStore.refreshItems === 'function') {
				await itemsStore.refreshItems({ warehouse: value, forceServer: true });
			}
		};

		// This page is for back-office BOM management, not cashier sales, so its item
		// catalog (the raw material browser on the right) shouldn't depend on a POS
		// register/shift being open. If one already is, reuse it and just steer its
		// stock context to the WIP warehouse; otherwise seed a fallback profile with
		// the WIP warehouse baked in so the catalog initializes correctly from the start.
		const ensureCatalogReady = async () => {
			let wipWarehouse = null;
			try {
				const { message } = await frappe.call({
					method: 'posawesome.posawesome.api.boms.get_default_wip_warehouse',
				});
				wipWarehouse = message?.name || null;
			} catch (e) {
				console.error('Failed to load default Work In Progress Warehouse', e);
			}

			if (uiStore.posProfile?.name) {
				pos_profile.value = uiStore.posProfile;
				activeWarehouse.value = wipWarehouse || uiStore.posProfile.warehouse || null;
				if (wipWarehouse) {
					itemsStore.setActiveSaleWarehouse(wipWarehouse);
					if (typeof itemsStore.refreshItems === 'function') {
						await itemsStore.refreshItems({ warehouse: wipWarehouse, forceServer: true });
					}
				}
				return;
			}

			try {
				const { message: profile } = await frappe.call({
					method: 'posawesome.posawesome.api.boms.get_default_pos_profile',
				});
				if (profile?.name) {
					if (wipWarehouse) profile.warehouse = wipWarehouse;
					uiStore.setPosProfile(profile);
					pos_profile.value = profile;
					activeWarehouse.value = profile.warehouse || null;
				}
			} catch (e) {
				console.error('Failed to load a default POS Profile', e);
			}
		};

		onMounted(async () => {
			await Promise.all([
				loadDefaultManufactureItems(),
				loadDefaultRawMaterialItems(),
				loadWarehouses(),
				ensureCatalogReady(),
			]);
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
			manufactureItem,
			selectedManufactureItemCode,
			manufactureSearchQuery,
			manufactureSearchResults,
			manufactureSearchLoading,
			handleManufactureSearchUpdate,
			handleManufactureItemPicked,
			quantity,
			warehouseOptions,
			warehouseLoading,
			activeWarehouse,
			handleWarehouseChange,
			rawMaterials,
			selectedRawMaterialItemCode,
			rawMaterialSearchQuery,
			rawMaterialSearchResults,
			rawMaterialSearchLoading,
			handleRawMaterialSearchUpdate,
			handleRawMaterialPicked,
			onAddRawMaterial,
			updateRawMaterialQty,
			removeRawMaterial,
			submitLoading,
			errorMessage,
			submitBom,
		};
	},
};
</script>

<style scoped>
@import '../invoice-shared-styles.css';

.bom-top-grid {
	grid-template-columns: 1fr 1.7fr 1fr 1fr !important;
}

@media (max-width: 900px) {
	.bom-top-grid {
		grid-template-columns: 1fr !important;
	}
}

.bom-selected-item {
	padding: 8px 12px;
	border-radius: 8px;
	background: var(--pos-surface-subtle, color-mix(in srgb, var(--pos-primary) 6%, transparent));
}

.qty-field :deep(input) {
	text-align: center;
}

.purchase-item-option__title {
	font-weight: 600;
	line-height: 1.3;
	white-space: normal;
}

.purchase-item-option__meta {
	display: flex;
	flex-wrap: wrap;
	gap: 8px;
	margin-top: 2px;
}

.purchase-item-option__code {
	font-variant-numeric: tabular-nums;
	font-weight: 600;
}

.purchase-item-option__stock {
	font-variant-numeric: tabular-nums;
	opacity: 0.85;
}
</style>
