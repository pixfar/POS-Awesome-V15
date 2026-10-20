<template>
	<div class="pa-0 h-100 invoice-shell txn-shell">
		<v-row class="h-100 ma-0">
			<v-col cols="12" md="6" class="h-100 pa-0 txn-col txn-col--form">
				<v-card class="h-100 d-flex flex-column pos-themed-card purchase-invoice-card" flat>
					<v-card-text class="flex-grow-1 overflow-y-auto pa-3 pa-md-4">
						<div class="invoice-sections">
							<div class="invoice-top-grid purchase-top-grid">
								<v-card flat class="invoice-section-card pos-themed-card">
									<div class="invoice-section-heading">
										<h3 class="invoice-section-heading__title">{{ __("Warehouse") }}</h3>
									</div>
									<div class="sale-options-body">
										<v-autocomplete
											v-model="warehouse"
											:items="warehouseOptions"
											item-title="warehouse_name"
											item-value="name"
											:label="isIssue ? __('Issue From Warehouse') : __('Receive Into Warehouse')"
											density="compact"
											variant="outlined"
											color="primary"
											hide-details
											prepend-inner-icon="mdi-warehouse"
											class="pos-themed-input"
											@update:model-value="onWarehouseChange"
										/>
									</div>
								</v-card>

								<v-card flat class="invoice-section-card pos-themed-card outstanding-panel">
									<div class="outstanding-panel__inner">
										<div class="outstanding-panel__label">{{ __("Total Qty") }}</div>
										<div class="outstanding-panel__amount outstanding-panel__amount--clear">
											{{ formatFloat(totalQty) }}
										</div>
										<div class="text-caption text-medium-emphasis">
											{{ rows.length }} {{ rows.length === 1 ? __("item") : __("items") }}
										</div>
									</div>
								</v-card>

								<v-card flat class="invoice-section-card pos-themed-card sale-options-card">
									<div class="invoice-section-heading">
										<h3 class="invoice-section-heading__title">{{ __("Posting Date") }}</h3>
									</div>
									<div class="sale-options-body">
										<DateFilterField
											v-model="postingDate"
											:label="__('Posting Date')"
											:clearable="false"
											field-class="pos-themed-input"
										/>
									</div>
								</v-card>
							</div>

							<v-card flat class="invoice-section-card invoice-items-card pos-themed-card">
								<div class="invoice-section-heading">
									<h3 class="invoice-section-heading__title">{{ __("Items") }}</h3>
								</div>
								<div class="purchase-search-toolbar">
									<v-autocomplete
										v-model:search="itemSearchQuery"
										:model-value="null"
										:items="itemSearchResults"
										:loading="itemSearchLoading"
										item-title="item_name"
										item-value="item_code"
										return-object
										:label="__('Search item by name or code')"
										:custom-filter="() => true"
										:no-data-text="itemSearchLoading ? __('Searching...') : __('No items found')"
										prepend-inner-icon="mdi-magnify"
										variant="solo"
										density="compact"
										hide-details
										class="pos-themed-input"
										@update:search="handleItemSearch"
										@update:menu="browseItemsOnOpen"
										@update:model-value="addItem"
									>
										<template #item="{ props: itemProps, item }">
											<v-list-item v-bind="itemProps" :title="undefined">
												<v-list-item-title>{{ item.raw.item_name }}</v-list-item-title>
												<v-list-item-subtitle>
													{{ item.raw.item_code }} · {{ __("Stock") }}: {{ formatFloat(item.raw.actual_qty || 0) }}
												</v-list-item-subtitle>
											</v-list-item>
										</template>
										<template #append-item>
											<div
												v-if="itemSearchHasMore"
												v-intersect="onItemSearchIntersect"
												class="pa-2 text-center text-caption text-medium-emphasis"
											>
												{{ __("Loading more...") }}
											</div>
										</template>
									</v-autocomplete>
								</div>

								<v-table density="comfortable" class="stock-entry-rows-table">
									<thead>
										<tr>
											<th style="width: 40px">{{ __("No.") }}</th>
											<th>{{ __("Item") }}</th>
											<th class="text-right" style="width: 110px">{{ __("In Stock") }}</th>
											<th style="width: 130px">{{ __("Qty") }}</th>
											<th style="width: 80px">{{ __("UOM") }}</th>
											<th v-if="!isIssue" style="width: 140px">{{ __("Rate") }}</th>
											<th style="width: 48px"></th>
										</tr>
									</thead>
									<tbody>
										<tr v-for="(row, index) in rows" :key="row.item_code">
											<td>{{ index + 1 }}</td>
											<td>
												<div>{{ row.item_name }}</div>
												<div class="text-caption text-medium-emphasis">{{ row.item_code }}</div>
											</td>
											<td class="text-right">
												<span :class="{ 'text-error': isIssue && row.qty > (stockQty[row.item_code] || 0) }">
													{{ formatFloat(stockQty[row.item_code] || 0) }}
												</span>
											</td>
											<td>
												<v-text-field
													v-model.number="row.qty"
													type="number"
													min="0"
													density="compact"
													variant="outlined"
													hide-details
													class="pos-themed-input"
												/>
											</td>
											<td>{{ row.uom }}</td>
											<td v-if="!isIssue">
												<v-text-field
													v-model.number="row.basic_rate"
													type="number"
													min="0"
													:placeholder="__('Auto')"
													density="compact"
													variant="outlined"
													hide-details
													class="pos-themed-input"
												/>
											</td>
											<td>
												<v-btn
													icon="mdi-delete-outline"
													size="small"
													variant="text"
													color="error"
													@click="rows.splice(index, 1)"
												/>
											</td>
										</tr>
										<tr v-if="!rows.length">
											<td :colspan="isIssue ? 6 : 7" class="text-center text-medium-emphasis py-4">
												{{ __("Search and add items") }}
											</td>
										</tr>
									</tbody>
								</v-table>
								<div v-if="!isIssue" class="text-caption text-medium-emphasis px-3 pb-2">
									{{ __("Leave Rate empty to use the item's current valuation rate.") }}
								</div>
							</v-card>

							<v-card flat class="invoice-section-card pos-themed-card notes-section-card">
								<div class="invoice-section-heading">
									<h3 class="invoice-section-heading__title">{{ __("Remarks") }}</h3>
								</div>
								<div class="sale-options-body">
									<v-textarea
										v-model="remarks"
										:label="__('Remarks')"
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
							<strong class="purchase-bottom-bar__amount">{{ formatFloat(totalQty) }}</strong>
							<span class="purchase-bottom-bar__meta">
								{{ rows.length }} {{ rows.length === 1 ? __("item") : __("items") }}
							</span>
						</div>
						<v-btn
							:loading="submitLoading"
							:disabled="submitLoading || !canSubmit"
							size="large"
							color="primary"
							class="text-none purchase-pay-btn"
							prepend-icon="mdi-send"
							@click="submit"
						>
							{{ isIssue ? __("Submit Issue") : __("Submit Receipt") }}
						</v-btn>
					</div>
				</v-card>
			</v-col>

			<v-col
				cols="12"
				md="6"
				class="h-100 pa-0 border-s txn-col txn-col--selector"
			>
				<ItemsSelectorWithGroups
					:context="isIssue ? 'material_transfer' : 'purchase'"
					@add-item="addItem"
				/>
			</v-col>
		</v-row>
	</div>
</template>

<script>
import { ref, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import format from '../../../format';
import DateFilterField from '../shared/DateFilterField.vue';
import { useWarehouseFilterOptions } from '../shared/useWarehouseFilterOptions';
import { useToastStore } from '../../../stores/toastStore';
import { useUIStore } from '../../../stores/uiStore.js';
import { useItemsStore } from '../../../stores/itemsStore';
import { isFundTransferManager } from '../../../utils/posWarehouseAccess';
import { stockEntryBasePath } from './stockEntryRoutes';
import ItemsSelectorWithGroups from '../items/ItemsSelectorWithGroups.vue';

const API = 'posawesome.posawesome.api.stock_entries';
const ITEM_API = 'posawesome.posawesome.api.material_transfers';
const getTodayDate = () => frappe?.datetime?.nowdate?.() || new Date().toISOString().slice(0, 10);

export default {
	name: 'StockEntryNew',
	mixins: [format],
	components: { DateFilterField, ItemsSelectorWithGroups },
	props: {
		purpose: { type: String, required: true },
	},
	setup(props) {
		const router = useRouter();
		const toastStore = useToastStore();
		const uiStore = useUIStore();
		const itemsStore = useItemsStore();
		const isIssue = computed(() => props.purpose === 'Material Issue');
		const basePath = computed(() => stockEntryBasePath(props.purpose));

		const { warehouseOptions, loadWarehouseOptions } = useWarehouseFilterOptions();
		const warehouse = ref(uiStore.posProfile?.warehouse || null);
		const postingDate = ref(getTodayDate());
		const remarks = ref('');
		const rows = ref([]);
		const stockQty = ref({});
		const submitLoading = ref(false);
		const errorMessage = ref('');

		const itemSearchQuery = ref('');
		const itemSearchResults = ref([]);
		const itemSearchLoading = ref(false);
		const itemSearchHasMore = ref(false);
		const ITEM_SEARCH_PAGE = 50;
		let itemSearchTimeout = null;
		let itemSearchTerm = '';

		const totalQty = computed(() => rows.value.reduce((sum, row) => sum + (Number(row.qty) || 0), 0));
		const canSubmit = computed(
			() => Boolean(warehouse.value) && rows.value.some((row) => Number(row.qty) > 0),
		);

		const refreshStockQty = async () => {
			const codes = rows.value.map((row) => row.item_code);
			if (!warehouse.value || !codes.length) {
				stockQty.value = {};
				return;
			}
			try {
				const { message } = await frappe.call({
					method: `${ITEM_API}.get_stock_qty`,
					args: { item_codes: codes, warehouse: warehouse.value },
				});
				stockQty.value = message || {};
			} catch (e) {
				console.error('Failed to load stock qty', e);
			}
		};

		const fetchItemPage = async (pageStart) => {
			const { message } = await frappe.call({
				method: `${ITEM_API}.search_items`,
				args: {
					search_text: itemSearchTerm,
					limit: ITEM_SEARCH_PAGE,
					page_start: pageStart,
					warehouse: warehouse.value || null,
				},
			});
			return Array.isArray(message) ? message : [];
		};

		// Opening the item search lists items straight away (first page of the
		// catalogue) instead of waiting for the user to type.
		const browseItemsOnOpen = (open) => {
			if (open && !itemSearchResults.value.length && !itemSearchLoading.value) {
				handleItemSearch(itemSearchQuery.value || '');
			}
		};

		const handleItemSearch = (term) => {
			if (itemSearchTimeout) clearTimeout(itemSearchTimeout);
			const trimmed = String(term || '').trim();
			// Empty: browse the first page of items. One character is too broad
			// to search, so the current list stays until there are two.
			if (trimmed.length === 1) return;
			itemSearchTimeout = setTimeout(async () => {
				itemSearchTerm = trimmed;
				itemSearchLoading.value = true;
				try {
					const rows = await fetchItemPage(0);
					itemSearchResults.value = rows;
					itemSearchHasMore.value = rows.length >= ITEM_SEARCH_PAGE;
				} catch (e) {
					console.error('Failed to search items', e);
				} finally {
					itemSearchLoading.value = false;
				}
			}, 300);
		};

		const loadMoreItems = async () => {
			if (itemSearchLoading.value || !itemSearchHasMore.value || itemSearchTerm.length === 1) return;
			itemSearchLoading.value = true;
			try {
				const rows = await fetchItemPage(itemSearchResults.value.length);
				itemSearchResults.value = [...itemSearchResults.value, ...rows];
				itemSearchHasMore.value = rows.length >= ITEM_SEARCH_PAGE;
			} catch (e) {
				console.error('Failed to load more items', e);
			} finally {
				itemSearchLoading.value = false;
			}
		};

		const onItemSearchIntersect = (a) => {
			const isIntersecting =
				typeof a === 'boolean' ? a : Array.isArray(a) && !!a[0]?.isIntersecting;
			if (isIntersecting) loadMoreItems();
		};

		// Mirror the other transaction screens: itemsStore.posProfile is only
		// set by itemsStore.initialize() (normally run by the Sales shell).
		// Landing here directly must initialize it too, else the catalog grid
		// never loads.
		const ensureItemsStoreInitialized = async (profile) => {
			if (itemsStore.posProfile?.name) return;
			let resolvedProfile = profile;
			if (!resolvedProfile?.name) {
				try {
					const { message } = await frappe.call({
						method: 'bsp_engineering.posawesome.profile.get_active_pos_profile',
					});
					if (message?.name) resolvedProfile = message;
				} catch (error) {
					console.error('Failed to resolve active POS Profile:', error);
				}
			}
			if (!resolvedProfile?.name) return;
			try {
				await itemsStore.initialize(resolvedProfile);
			} catch (error) {
				console.error('Failed to initialize items store:', error);
			}
		};

		const onWarehouseChange = async () => {
			if (warehouse.value) {
				itemsStore.setActiveSaleWarehouse(warehouse.value);
				if (typeof itemsStore.refreshItems === 'function') {
					try {
						await itemsStore.refreshItems({
							warehouse: warehouse.value,
							forceServer: true,
						});
					} catch (e) {
						console.error('Failed to refresh catalog for warehouse', e);
					}
				}
			}
			await refreshStockQty();
		};

		const addItem = (item) => {
			if (!item) return;
			const existing = rows.value.find((row) => row.item_code === item.item_code);
			if (existing) {
				existing.qty = (Number(existing.qty) || 0) + 1;
			} else {
				rows.value.push({
					item_code: item.item_code,
					item_name: item.item_name,
					uom: item.stock_uom,
					qty: 1,
					basic_rate: null,
				});
			}
			itemSearchQuery.value = '';
			refreshStockQty();
		};

		const submit = async () => {
			errorMessage.value = '';
			if (!canSubmit.value) return;
			submitLoading.value = true;
			try {
				const { message } = await frappe.call({
					method: `${API}.create_stock_entry`,
					args: {
						purpose: props.purpose,
						data: {
							warehouse: warehouse.value,
							posting_date: postingDate.value,
							remarks: remarks.value,
							items: rows.value
								.filter((row) => Number(row.qty) > 0)
								.map((row) => ({
									item_code: row.item_code,
									qty: row.qty,
									uom: row.uom,
									basic_rate: isIssue.value ? undefined : row.basic_rate,
								})),
						},
					},
					freeze: true,
					freeze_message: __('Submitting {0}...', [__(props.purpose)]),
				});
				toastStore.show({ title: __('{0} submitted', [message?.name || '']), color: 'success' });
				await router.push(message?.name ? `${basePath.value}/${message.name}` : `${basePath.value}/list`);
			} catch (e) {
				errorMessage.value = e?.message || __('Failed to submit {0}', [__(props.purpose)]);
			} finally {
				submitLoading.value = false;
			}
		};

		onMounted(async () => {
			if (!isFundTransferManager()) {
				router.replace(`${basePath.value}/list`);
				return;
			}
			loadWarehouseOptions();
			await ensureItemsStoreInitialized(uiStore.posProfile);
			// Landing here directly, the POS Profile (and so its warehouse) may
			// only be known after the store initialized.
			if (!warehouse.value) {
				warehouse.value = itemsStore.posProfile?.warehouse || null;
			}
			// initialize() alone only fetches the 20-item first page; load the
			// warehouse's full catalogue like the other entry screens (and the
			// warehouse picker) do.
			await onWarehouseChange();
		});

		return {
			isIssue,
			warehouseOptions,
			warehouse,
			postingDate,
			remarks,
			rows,
			stockQty,
			submitLoading,
			errorMessage,
			itemSearchQuery,
			itemSearchResults,
			itemSearchLoading,
			itemSearchHasMore,
			onItemSearchIntersect,
			totalQty,
			canSubmit,
			refreshStockQty,
			onWarehouseChange,
			handleItemSearch,
			browseItemsOnOpen,
			addItem,
			submit,
		};
	},
};
</script>

<style scoped>
@import '../invoice-shared-styles.css';

.stock-entry-rows-table :deep(td) {
	vertical-align: middle;
	padding-top: 6px;
	padding-bottom: 6px;
}
</style>
