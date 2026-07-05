<template>
	<div class="pa-0 h-100 invoice-shell">
		<v-row class="h-100 ma-0">
			<v-col cols="12" class="h-100 pa-0">
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
											v-model="sourceWarehouse"
											:items="warehouseOptions"
											item-title="warehouse_name"
											item-value="name"
											:label="__('Source Warehouse (optional)')"
											density="compact"
											variant="outlined"
											color="primary"
											hide-details
											clearable
											:loading="warehouseLoading"
											class="pos-themed-input mb-2"
										/>
										<v-autocomplete
											v-model="targetWarehouse"
											:items="warehouseOptions"
											item-title="warehouse_name"
											item-value="name"
											:label="__('Target Warehouse')"
											density="compact"
											variant="outlined"
											color="primary"
											hide-details
											:loading="warehouseLoading"
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
											{{ planItems.length }}
											{{ planItems.length === 1 ? __("item") : __("items") }}
										</div>
									</div>
								</v-card>

								<v-card flat class="invoice-section-card pos-themed-card sale-options-card">
									<div class="invoice-section-heading">
										<h3 class="invoice-section-heading__title">
											{{ __("Items Required Date") }}
										</h3>
									</div>
									<div class="sale-options-body">
										<VueDatePicker
											v-model="requiredDateDisplay"
											model-type="format"
											format="dd-MM-yyyy"
											auto-apply
											teleport
											:placeholder="__('Items Required Date')"
											class="sleek-field pos-themed-input"
										/>
									</div>
								</v-card>
							</div>

							<v-card flat class="invoice-section-card invoice-items-card pos-themed-card">
								<div class="invoice-section-heading">
									<h3 class="invoice-section-heading__title">{{ __("Production Items") }}</h3>
									<p class="text-caption text-medium-emphasis mb-0">
										{{ __("Only items with an active default BOM can be planned for production") }}
									</p>
								</div>
								<div class="purchase-search-toolbar">
									<v-autocomplete
										v-model:search="itemSearchQuery"
										:model-value="selectedSearchItemCode"
										:items="itemSearchResults"
										:loading="itemSearchLoading"
										item-title="item_name"
										item-value="item_code"
										:label="__('Search manufacturable item')"
										:placeholder="__('Type at least 2 characters')"
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
									:items="planItems"
									@update-qty="({ item, value }) => updateItemQty(item, value)"
									@remove-item="removeItem"
								/>
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
								{{ planItems.length }}
								{{ planItems.length === 1 ? __("item") : __("items") }}
							</span>
						</div>
						<v-btn
							:loading="submitLoading"
							:disabled="submitLoading || !planItems.length"
							size="large"
							color="primary"
							class="text-none purchase-pay-btn"
							prepend-icon="mdi-send"
							@click="submitPlan"
						>
							{{ __("Create Plan") }}
						</v-btn>
					</div>
				</v-card>
			</v-col>
		</v-row>
	</div>
</template>

<script>
import { ref, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import VueDatePicker from '@vuepic/vue-datepicker';
import format from '../../../format';
import { useUIStore } from '../../../stores/uiStore.js';
import { useToastStore } from '../../../stores/toastStore';
import RequisitionItemsTable from '../requisition/RequisitionItemsTable.vue';
import { normalizeDateForBackend } from '../../../format';

const getTodayDate = () =>
	frappe?.datetime?.nowdate?.() || new Date().toISOString().slice(0, 10);

export default {
	name: 'ProductionPlanNew',
	mixins: [format],
	components: {
		RequisitionItemsTable,
		VueDatePicker,
	},
	setup() {
		const router = useRouter();
		const uiStore = useUIStore();
		const toastStore = useToastStore();
		const pos_profile = ref(uiStore.posProfile || {});
		const requiredDate = ref(getTodayDate());
		const warehouseOptions = ref([]);
		const warehouseLoading = ref(false);
		const sourceWarehouse = ref(null);
		const targetWarehouse = ref(null);
		const planItems = ref([]);
		const submitLoading = ref(false);
		const errorMessage = ref('');

		const itemSearchQuery = ref('');
		const selectedSearchItemCode = ref(null);
		const itemSearchResults = ref([]);
		const itemSearchLoading = ref(false);
		let itemSearchTimeout = null;

		const totalQty = computed(() =>
			planItems.value.reduce((sum, row) => sum + Number(row.qty || 0), 0),
		);

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

		const handleItemSearchUpdate = (term) => {
			if (itemSearchTimeout) clearTimeout(itemSearchTimeout);
			if (!term || term.trim().length < 2) {
				itemSearchResults.value = [];
				return;
			}
			itemSearchTimeout = setTimeout(async () => {
				itemSearchLoading.value = true;
				try {
					const { message } = await frappe.call({
						method: 'posawesome.posawesome.api.production_plans.search_manufacturable_items',
						args: { search_text: term.trim(), limit: 20 },
					});
					itemSearchResults.value = message || [];
				} catch {
					itemSearchResults.value = [];
				} finally {
					itemSearchLoading.value = false;
				}
			}, 300);
		};

		const onAddItem = (item) => {
			if (!item?.item_code) return;
			const existing = planItems.value.find((row) => row.item_code === item.item_code);
			if (existing) {
				existing.qty += 1;
				return;
			}
			planItems.value.unshift({
				line_id: `pp_${Date.now()}_${Math.floor(Math.random() * 10000)}`,
				item_code: item.item_code,
				item_name: item.item_name,
				item_group: item.item_group,
				bom_no: item.bom_no,
				uom: item.stock_uom,
				qty: 1,
			});
		};

		const handleSearchItemPicked = (itemCode) => {
			if (!itemCode) return;
			const item = itemSearchResults.value.find((row) => row.item_code === itemCode);
			if (item) onAddItem(item);
			selectedSearchItemCode.value = null;
			itemSearchQuery.value = '';
		};

		const updateItemQty = (item, value) => {
			if (!item) return;
			item.qty = Math.max(0, Number(value) || 0);
		};

		const removeItem = (item) => {
			planItems.value = planItems.value.filter((row) => row.line_id !== item.line_id);
		};

		const submitPlan = async () => {
			errorMessage.value = '';
			if (!targetWarehouse.value) {
				errorMessage.value = __('Target Warehouse is required.');
				return;
			}
			if (!planItems.value.length) {
				errorMessage.value = __('Add at least one item.');
				return;
			}

			submitLoading.value = true;
			try {
				const { message } = await frappe.call({
					method: 'posawesome.posawesome.api.production_plans.create_production_plan',
					args: {
						data: {
							pos_profile: pos_profile.value?.name,
							posting_date: getTodayDate(),
							source_warehouse: sourceWarehouse.value,
							target_warehouse: targetWarehouse.value,
							items: planItems.value.map((row) => ({
								item_code: row.item_code,
								bom_no: row.bom_no,
								qty: row.qty,
								uom: row.uom,
								planned_start_date: requiredDate.value,
							})),
						},
					},
					freeze: true,
					freeze_message: __('Creating production plan...'),
				});
				toastStore.show({
					title: __('Production Plan {0} created', [message?.name || '']),
					color: 'success',
				});
				planItems.value = [];
				await router.push('/production-plans/list');
			} catch (e) {
				errorMessage.value = e?.message || __('Failed to create production plan');
			} finally {
				submitLoading.value = false;
			}
		};

		onMounted(async () => {
			if (uiStore.posProfile?.name) {
				pos_profile.value = uiStore.posProfile;
			}
			if (pos_profile.value?.warehouse) {
				sourceWarehouse.value = pos_profile.value.warehouse;
			}
			await loadWarehouses();
		});

		return {
			sourceWarehouse,
			targetWarehouse,
			warehouseOptions,
			warehouseLoading,
			requiredDateDisplay,
			planItems,
			totalQty,
			submitLoading,
			errorMessage,
			itemSearchQuery,
			selectedSearchItemCode,
			itemSearchResults,
			itemSearchLoading,
			handleItemSearchUpdate,
			handleSearchItemPicked,
			updateItemQty,
			removeItem,
			submitPlan,
		};
	},
};
</script>

<style scoped>
@import '../invoice-shared-styles.css';
</style>
