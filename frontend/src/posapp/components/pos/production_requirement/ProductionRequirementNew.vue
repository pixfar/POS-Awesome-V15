<template>
	<div class="pa-0 h-100 invoice-shell txn-shell" :style="responsiveStyles">
		<v-row class="h-100 ma-0">
			<v-col
				v-show="showInvoicePanel"
				cols="12"
				:md="isCompact ? 12 : 6"
				class="h-100 pa-0 txn-col txn-col--invoice"
			>
				<v-card class="h-100 d-flex flex-column pos-themed-card purchase-invoice-card" flat>
					<v-card-text class="flex-grow-1 overflow-y-auto pa-3 pa-md-4">
						<div v-if="editLoading" class="d-flex justify-center py-8">
							<v-progress-circular indeterminate color="primary" />
						</div>
						<div v-else class="invoice-sections">
							<v-card flat class="invoice-section-card pos-themed-card">
								<div class="invoice-section-heading">
									<h3 class="invoice-section-heading__title">
										{{ __("Production Requirement") }}
										<v-chip
											v-if="editName"
											size="small"
											color="warning"
											variant="tonal"
											class="ml-2"
										>
											{{ __("Editing") }} {{ editName }}
										</v-chip>
									</h3>
								</div>
								<div class="sale-options-body prq-header-grid">
									<div class="prq-field">
										<span class="prq-field__label">{{ __("Production Date") }}</span>
										<VueDatePicker
											v-model="productionDateDisplay"
											model-type="format"
											format="dd-MM-yyyy"
											auto-apply
											teleport
											:clearable="false"
											class="sleek-field pos-themed-input"
										/>
									</div>
									<div class="prq-field">
										<span class="prq-field__label">{{ __("Posting Date") }}</span>
										<VueDatePicker
											v-model="postingDateDisplay"
											model-type="format"
											format="dd-MM-yyyy"
											auto-apply
											teleport
											:clearable="false"
											class="sleek-field pos-themed-input"
										/>
									</div>
									<v-autocomplete
										v-if="context.can_change_production_by"
										v-model="productionBy"
										v-model:search="userSearchQuery"
										:items="userOptions"
										:item-title="(u) => u.full_name || u.name"
										item-value="name"
										:label="__('Production By')"
										:loading="userSearchLoading"
										:custom-filter="() => true"
										density="compact"
										variant="outlined"
										color="primary"
										hide-details
										prepend-inner-icon="mdi-account-hard-hat-outline"
										class="pos-themed-input"
										@update:search="handleUserSearch"
									/>
									<v-text-field
										v-else
										:model-value="productionByName"
										:label="__('Production By')"
										density="compact"
										variant="outlined"
										hide-details
										readonly
										prepend-inner-icon="mdi-account-hard-hat-outline"
										class="pos-themed-input"
									/>
									<v-autocomplete
										v-if="context.can_change_warehouse"
										v-model="warehouse"
										:items="warehouseOptions"
										:item-title="(w) => w.warehouse_name || w.name"
										item-value="name"
										:label="__('Warehouse')"
										density="compact"
										variant="outlined"
										color="primary"
										hide-details
										prepend-inner-icon="mdi-warehouse"
										class="pos-themed-input"
									/>
									<v-text-field
										v-else
										:model-value="warehouseName || warehouse"
										:label="__('Warehouse')"
										density="compact"
										variant="outlined"
										hide-details
										readonly
										prepend-inner-icon="mdi-warehouse"
										class="pos-themed-input"
									/>
									<v-select
										v-model="status"
										:items="statusOptions"
										:label="__('Status')"
										density="compact"
										variant="outlined"
										hide-details
										prepend-inner-icon="mdi-flag-outline"
										class="pos-themed-input"
									>
										<template #selection="{ item }">
											<v-chip
												size="small"
												variant="tonal"
												:color="statusColor(item.value)"
											>
												{{ item.title }}
											</v-chip>
										</template>
									</v-select>
								</div>
							</v-card>

							<v-card flat class="invoice-section-card invoice-items-card pos-themed-card">
								<div
									class="invoice-section-heading d-flex align-center justify-space-between flex-wrap ga-2"
								>
									<h3 class="invoice-section-heading__title">{{ __("Items") }}</h3>
									<span class="text-caption text-medium-emphasis">
										{{ __("Tap an item on the right to add it") }}
									</span>
								</div>
								<v-table
									v-if="planItems.length"
									density="compact"
									class="pos-themed-table prq-items-table"
								>
									<thead>
										<tr>
											<th>{{ __("Item") }}</th>
											<th
												v-for="label in catalogWarehouses"
												:key="label"
												class="text-center prq-wh-col"
												:title="label"
											>
												{{ label }}
											</th>
											<th class="text-center prq-wh-col">{{ __("Shortage Qty") }}</th>
											<th class="text-center prq-qty-col">{{ __("Plan Qty") }}</th>
											<th class="text-center" style="width: 40px"></th>
										</tr>
									</thead>
									<tbody>
										<tr v-for="row in planItems" :key="row.item_code">
											<td>
												<div class="font-weight-medium prq-item-name">
													{{ row.item_name || row.item_code }}
												</div>
												<div class="text-caption text-medium-emphasis">
													{{ row.item_code
													}}<span v-if="row.uom"> · {{ row.uom }}</span>
												</div>
											</td>
											<td
												v-for="(label, idx) in catalogWarehouses"
												:key="label"
												class="text-center prq-num-cell"
											>
												<span :title="__('Stock / Shortage')">
													{{ formatQty(whCell(row, idx).stock) }}
													<span class="text-medium-emphasis">/</span>
													<span
														:class="
															whShortage(row, idx) > 0
																? 'text-error font-weight-bold'
																: 'text-medium-emphasis'
														"
													>
														{{ formatQty(whShortage(row, idx)) }}
													</span>
												</span>
											</td>
											<td class="text-center prq-num-cell">
												<span
													class="font-weight-bold"
													:class="
														shortageQty(row) > 0 ? 'text-error' : 'text-success'
													"
												>
													{{ formatQty(shortageQty(row)) }}
												</span>
											</td>
											<td>
												<v-text-field
													:model-value="row.plan_qty"
													type="number"
													min="0"
													density="compact"
													variant="outlined"
													hide-details
													class="pos-themed-input prq-qty-input"
													@update:model-value="(v) => setQty(row, 'plan_qty', v)"
												/>
											</td>
											<td class="text-center">
												<v-btn
													icon="mdi-delete-outline"
													size="small"
													variant="text"
													color="error"
													:title="__('Remove')"
													@click="removeItem(row)"
												/>
											</td>
										</tr>
									</tbody>
								</v-table>
								<div v-else class="pos-list-empty py-6">
									<v-icon size="40" color="primary" class="pos-list-empty__icon"
										>mdi-clipboard-text-outline</v-icon
									>
									<p class="pos-list-empty__subtitle">{{ __("No items added yet") }}</p>
								</div>
							</v-card>

							<v-card flat class="invoice-section-card pos-themed-card">
								<div class="sale-options-body">
									<v-textarea
										v-model="remarks"
										:label="__('Remarks')"
										variant="outlined"
										density="compact"
										hide-details
										rows="2"
										auto-grow
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
							<span class="purchase-bottom-bar__label">{{ __("Total Plan Qty") }}</span>
							<strong class="purchase-bottom-bar__amount">
								{{ formatQty(totalPlanQty) }}
							</strong>
							<span class="purchase-bottom-bar__meta">
								{{ planItems.length }} {{ planItems.length === 1 ? __("item") : __("items") }}
							</span>
						</div>
						<v-btn
							:loading="submitLoading"
							:disabled="submitLoading || !planItems.length || !context.can_create"
							size="large"
							color="primary"
							class="text-none purchase-pay-btn"
							prepend-icon="mdi-content-save-outline"
							@click="save"
						>
							{{ editName ? __("Save Changes") : __("Save Requirement") }}
						</v-btn>
					</div>
				</v-card>
			</v-col>

			<v-col
				v-show="showSelectorPanel"
				cols="12"
				:md="isCompact ? 12 : 6"
				class="h-100 pa-0 border-s txn-col txn-col--selector"
			>
				<v-card flat class="h-100 d-flex flex-column pos-themed-card prq-catalog">
					<div class="prq-catalog__search">
						<v-text-field
							v-model="catalogSearch"
							:placeholder="__('Search item code or name')"
							prepend-inner-icon="mdi-magnify"
							variant="solo"
							density="compact"
							hide-details
							clearable
							class="pos-themed-input"
						/>
						<span class="prq-catalog__count text-caption text-medium-emphasis">
							{{ __("{0} items", [filteredCatalog.length]) }}
						</span>
						<v-btn
							icon="mdi-refresh"
							variant="text"
							size="small"
							:loading="catalogLoading"
							:title="__('Reload')"
							@click="loadCatalog"
						/>
					</div>

					<div ref="gridRef" class="prq-catalog__grid-wrap">
						<div
							v-if="catalogLoading && !catalogItems.length"
							class="d-flex justify-center py-10"
						>
							<v-progress-circular indeterminate color="primary" />
						</div>
						<div v-else-if="!filteredCatalog.length" class="pos-list-empty py-10">
							<v-icon size="40" color="primary" class="pos-list-empty__icon"
								>mdi-package-variant</v-icon
							>
							<p class="pos-list-empty__subtitle">{{ __("No items match these filters") }}</p>
						</div>
						<div v-else class="prq-catalog__grid">
							<button
								v-for="item in visibleCatalog"
								:key="item.item_code"
								type="button"
								class="prq-card"
								:class="{
									'prq-card--low': item.is_low,
									'prq-card--added': addedCodes.has(item.item_code),
								}"
								@click="addItem(item)"
							>
								<div class="prq-card__top">
									<span class="prq-card__code">{{ item.item_code }}</span>
									<v-icon v-if="addedCodes.has(item.item_code)" size="18" color="primary"
										>mdi-check-circle</v-icon
									>
									<v-chip
										v-else-if="item.is_low"
										size="x-small"
										color="error"
										variant="tonal"
										>{{ __("Low") }}</v-chip
									>
								</div>
								<div class="prq-card__name">{{ item.item_name }}</div>
								<div class="prq-card__stats">
									<div>
										<span class="prq-card__stat-label">{{ __("Stock") }}</span>
										<strong :class="item.is_low ? 'text-error' : ''">{{
											formatQty(item.total_stock)
										}}</strong>
									</div>
									<div>
										<span class="prq-card__stat-label">{{ __("Low Qty") }}</span>
										<strong>{{ formatQty(item.total_low_qty) }}</strong>
									</div>
									<div>
										<span class="prq-card__stat-label">{{ __("Need") }}</span>
										<strong :class="item.shortage > 0 ? 'text-error' : 'text-success'">{{
											formatQty(item.shortage)
										}}</strong>
									</div>
								</div>
								<div class="prq-card__wh">
									<div
										v-for="wh in item.warehouses"
										:key="wh.label"
										class="prq-card__wh-row"
									>
										<span class="prq-card__wh-label" :title="wh.label">{{
											wh.label
										}}</span>
										<span
											class="prq-card__wh-value"
											:class="wh.stock < wh.low_qty ? 'text-error' : ''"
										>
											{{ formatQty(wh.stock)
											}}<span class="text-medium-emphasis">
												/ {{ formatQty(wh.low_qty) }}</span
											>
										</span>
									</div>
								</div>
								<div class="prq-card__footer">
									<span class="text-truncate">{{ item.item_group }}</span>
									<span>{{ item.stock_uom }}</span>
								</div>
							</button>
						</div>
					</div>

					<div v-if="catalogPageCount > 1" class="prq-catalog__pagination">
						<span class="text-caption text-medium-emphasis">
							{{
								__("{0}-{1} of {2}", [
									catalogRangeStart,
									catalogRangeEnd,
									filteredCatalog.length,
								])
							}}
						</span>
						<v-pagination
							v-model="catalogPage"
							:length="catalogPageCount"
							:total-visible="5"
							density="compact"
							size="small"
							rounded="circle"
							active-color="primary"
						/>
					</div>

					<div class="prq-catalog__filters">
						<v-autocomplete
							v-model="itemGroupFilter"
							:items="filterOptions.item_groups"
							:label="__('Item Group')"
							density="compact"
							variant="outlined"
							hide-details
							clearable
							class="pos-themed-input"
							@update:model-value="loadCatalog"
						/>
						<v-select
							v-model="stockStatusFilter"
							:items="stockStatusOptions"
							:label="__('Stock Status')"
							density="compact"
							variant="outlined"
							hide-details
							clearable
							class="pos-themed-input"
							@update:model-value="loadCatalog"
						/>
						<v-autocomplete
							v-model="productionGroupFilter"
							:items="filterOptions.production_groups"
							:label="__('Production Group')"
							density="compact"
							variant="outlined"
							hide-details
							clearable
							class="pos-themed-input"
							@update:model-value="loadCatalog"
						/>
					</div>
				</v-card>
			</v-col>
		</v-row>

		<div v-if="isCompact" class="mobile-pos-stack txn-bottom-dock">
			<div class="mobile-sale-dock">
				<div class="mobile-sale-dock__copy">
					<span class="mobile-sale-dock__eyebrow">{{ __("Total Plan Qty") }}</span>
					<strong class="mobile-sale-dock__amount">
						{{ formatQty(totalPlanQty) }}
					</strong>
					<span class="mobile-sale-dock__meta">
						{{ planItems.length }} {{ planItems.length === 1 ? __("item") : __("items") }}
					</span>
				</div>
				<v-btn
					:loading="submitLoading"
					:disabled="submitLoading || !planItems.length || !context.can_create"
					color="primary"
					variant="flat"
					class="text-none txn-dock-pay-btn"
					prepend-icon="mdi-content-save-outline"
					@click="save"
				>
					{{ __("Save") }}
				</v-btn>
			</div>
			<div class="mobile-pos-dock">
				<button
					type="button"
					class="mobile-pos-dock__item"
					:class="{ 'mobile-pos-dock__item--active': compactPanel === 'selector' }"
					@click="setPanel('selector')"
				>
					<v-icon icon="mdi-view-grid-outline" size="20" />
					<span>{{ __("Items") }}</span>
				</button>
				<button
					type="button"
					class="mobile-pos-dock__item"
					:class="{ 'mobile-pos-dock__item--active': compactPanel === 'invoice' }"
					@click="setPanel('invoice')"
				>
					<span v-if="planItems.length" class="mobile-pos-dock__pill">{{ planItems.length }}</span>
					<v-icon icon="mdi-clipboard-list-outline" size="22" />
					<span>{{ __("Plan") }}</span>
				</button>
			</div>
		</div>
	</div>
</template>

<script>
import { ref, reactive, computed, onMounted, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import VueDatePicker from "@vuepic/vue-datepicker";
import { useUIStore } from "../../../stores/uiStore.js";
import { useToastStore } from "../../../stores/toastStore";
import { normalizeDateForBackend } from "../../../format";
import { useCompactTransactionPanel } from "../../../composables/core/useCompactTransactionPanel";
import { useWarehouseFilterOptions } from "../shared/useWarehouseFilterOptions";
import {
	formatQty,
	PRODUCTION_REQUIREMENT_STATUSES,
	productionRequirementStatusColor,
} from "./productionRequirementUtils";

const API = "posawesome.posawesome.api.production_requirements";
const PAGE_SIZE = 24;

const getTodayDate = () => frappe?.datetime?.nowdate?.() || new Date().toISOString().slice(0, 10);

// yyyy-mm-dd <-> dd-mm-yyyy for VueDatePicker, same as the other POS forms.
const displayDate = (dateRef) =>
	computed({
		get: () => {
			const parts = String(dateRef.value || "").split("-");
			return parts.length === 3 ? `${parts[2]}-${parts[1]}-${parts[0]}` : dateRef.value;
		},
		set: (v) => {
			dateRef.value = normalizeDateForBackend(v) || getTodayDate();
		},
	});

export default {
	name: "ProductionRequirementNew",
	components: { VueDatePicker },
	setup() {
		const route = useRoute();
		const router = useRouter();
		const uiStore = useUIStore();
		const toastStore = useToastStore();
		const { responsiveStyles, isCompact, compactPanel, showInvoicePanel, showSelectorPanel, setPanel } =
			useCompactTransactionPanel("invoice");
		const { warehouseOptions, loadWarehouseOptions } = useWarehouseFilterOptions();

		const editName = computed(() => (route.params.name ? String(route.params.name) : null));
		const editLoading = ref(false);

		const context = reactive({
			can_change_warehouse: false,
			can_change_production_by: false,
			can_create: true,
		});
		const productionDate = ref(getTodayDate());
		const postingDate = ref(getTodayDate());
		const productionDateDisplay = displayDate(productionDate);
		const postingDateDisplay = displayDate(postingDate);
		const warehouse = ref(null);
		const warehouseName = ref("");
		const productionBy = ref(null);
		const productionByName = ref("");
		const remarks = ref("");
		const status = ref("Pending");
		const statusOptions = PRODUCTION_REQUIREMENT_STATUSES.map((s) => ({ title: __(s), value: s }));
		const planItems = ref([]);
		const submitLoading = ref(false);
		const errorMessage = ref("");

		const userOptions = ref([]);
		const userSearchQuery = ref("");
		const userSearchLoading = ref(false);
		let userSearchTimeout = null;

		const catalogItems = ref([]);
		const catalogLoading = ref(false);
		const catalogSearch = ref("");
		const itemGroupFilter = ref(null);
		const stockStatusFilter = ref(null);
		const productionGroupFilter = ref(null);
		const filterOptions = reactive({ item_groups: [], production_groups: [] });
		const stockStatusOptions = [
			{ title: __("Low Stock"), value: "Low Stock" },
			{ title: __("Sufficient Stock"), value: "Sufficient Stock" },
		];
		const catalogPage = ref(1);
		const gridRef = ref(null);

		const totalPlanQty = computed(() => planItems.value.reduce((s, r) => s + Number(r.plan_qty || 0), 0));

		// Warehouse-wise stock and Shortage beside Plan Qty are display-only
		// (never saved -- stock keeps changing): read live from the Production
		// Requirement Report rows the catalog loads, cached per item so a
		// planned item keeps its figures even when a filter hides its card.
		const catalogWarehouses = ref([]);
		const reportByItem = ref({});
		const EMPTY_WH = { stock: 0, low_qty: 0 };
		const whCell = (row, idx) => reportByItem.value[row.item_code]?.warehouses?.[idx] || EMPTY_WH;
		const whShortage = (row, idx) => {
			const wh = whCell(row, idx);
			return Math.max(Number(wh.low_qty || 0) - Number(wh.stock || 0), 0);
		};
		// Saved rows show the shortage recorded on the document; rows added in
		// this session show today's figure (what the server will record).
		const shortageQty = (row) =>
			row.shortage_qty !== undefined && row.shortage_qty !== null
				? Number(row.shortage_qty)
				: Number(reportByItem.value[row.item_code]?.shortage || 0);
		const rememberReportRows = (items) => {
			const next = { ...reportByItem.value };
			items.forEach((item) => {
				next[item.item_code] = { warehouses: item.warehouses || [], shortage: item.shortage };
			});
			reportByItem.value = next;
		};
		const addedCodes = computed(() => new Set(planItems.value.map((r) => r.item_code)));

		const filteredCatalog = computed(() => {
			const term = (catalogSearch.value || "").trim().toLowerCase();
			if (!term) return catalogItems.value;
			return catalogItems.value.filter(
				(item) =>
					String(item.item_code).toLowerCase().includes(term) ||
					String(item.item_name || "")
						.toLowerCase()
						.includes(term),
			);
		});
		const catalogPageCount = computed(() =>
			Math.max(1, Math.ceil(filteredCatalog.value.length / PAGE_SIZE)),
		);
		const visibleCatalog = computed(() => {
			const start = (catalogPage.value - 1) * PAGE_SIZE;
			return filteredCatalog.value.slice(start, start + PAGE_SIZE);
		});
		const catalogRangeStart = computed(() =>
			filteredCatalog.value.length ? (catalogPage.value - 1) * PAGE_SIZE + 1 : 0,
		);
		const catalogRangeEnd = computed(() =>
			Math.min(catalogPage.value * PAGE_SIZE, filteredCatalog.value.length),
		);

		const scrollGridTop = () => {
			if (gridRef.value) gridRef.value.scrollTop = 0;
		};
		const resetVisible = () => {
			catalogPage.value = 1;
			scrollGridTop();
		};
		watch(catalogSearch, resetVisible);
		watch(catalogPage, scrollGridTop);

		const loadCatalog = async () => {
			catalogLoading.value = true;
			try {
				const { message } = await frappe.call({
					method: `${API}.get_requirement_catalog`,
					args: {
						item_group: itemGroupFilter.value || undefined,
						production_group: productionGroupFilter.value || undefined,
						stock_status: stockStatusFilter.value || undefined,
					},
				});
				catalogItems.value = message?.items || [];
				catalogWarehouses.value = message?.warehouses || [];
				rememberReportRows(catalogItems.value);
				resetVisible();
			} catch (e) {
				catalogItems.value = [];
				toastStore.show({
					title: e?.message || __("Failed to load production requirement data"),
					color: "error",
				});
			} finally {
				catalogLoading.value = false;
			}
		};

		const loadFilterOptions = async () => {
			try {
				const { message } = await frappe.call({ method: `${API}.get_filter_options` });
				filterOptions.item_groups = message?.item_groups || [];
				filterOptions.production_groups = message?.production_groups || [];
			} catch (e) {
				console.error("Failed to load filter options", e);
			}
		};

		const loadContext = async () => {
			const { message } = await frappe.call({
				method: `${API}.get_form_context`,
				args: { pos_profile: uiStore.posProfile ? JSON.stringify(uiStore.posProfile) : null },
			});
			Object.assign(context, message || {});
			if (!editName.value) {
				warehouse.value = message?.warehouse || null;
				warehouseName.value = message?.warehouse_name || message?.warehouse || "";
				productionBy.value = message?.production_by || null;
				productionByName.value = message?.production_by_name || "";
			}
			if (context.can_change_production_by && productionBy.value) {
				userOptions.value = [{ name: productionBy.value, full_name: productionByName.value }];
			}
		};

		const handleUserSearch = (term) => {
			if (userSearchTimeout) clearTimeout(userSearchTimeout);
			if (!term || term.trim().length < 2) return;
			userSearchTimeout = setTimeout(async () => {
				userSearchLoading.value = true;
				try {
					const { message } = await frappe.call({
						method: `${API}.search_users`,
						args: { search_text: term.trim() },
					});
					userOptions.value = message || [];
				} catch {
					userOptions.value = [];
				} finally {
					userSearchLoading.value = false;
				}
			}, 300);
		};

		const addItem = (item) => {
			const existing = planItems.value.find((row) => row.item_code === item.item_code);
			if (existing) {
				existing.plan_qty = Number(existing.plan_qty || 0) + 1;
				return;
			}
			// Suggest the report's shortage (Low Qty - Stock) as the plan, else 1.
			planItems.value.push({
				item_code: item.item_code,
				item_name: item.item_name,
				uom: item.stock_uom,
				plan_qty: item.shortage > 0 ? Math.ceil(item.shortage) : 1,
			});
		};

		const setQty = (row, field, value) => {
			row[field] = Math.max(0, Number(value) || 0);
		};

		const removeItem = (row) => {
			planItems.value = planItems.value.filter((r) => r.item_code !== row.item_code);
		};

		const loadForEdit = async (name) => {
			editLoading.value = true;
			try {
				const { message } = await frappe.call({
					method: `${API}.get_production_requirement_detail`,
					args: { name },
				});
				if (!message?.can_edit) {
					toastStore.show({ title: __("You cannot edit {0}", [name]), color: "warning" });
					router.replace(`/production-requirements/${encodeURIComponent(name)}`);
					return;
				}
				productionDate.value = message.production_date;
				postingDate.value = message.posting_date;
				warehouse.value = message.warehouse;
				warehouseName.value = message.warehouse_name;
				productionBy.value = message.production_by;
				productionByName.value = message.production_by_name;
				remarks.value = message.remarks || "";
				status.value = message.status || "Pending";
				planItems.value = (message.items || []).map((row) => ({
					item_code: row.item_code,
					item_name: row.item_name,
					uom: row.uom,
					plan_qty: row.plan_qty,
					shortage_qty: row.shortage_qty,
				}));
				userOptions.value = [{ name: message.production_by, full_name: message.production_by_name }];
			} catch (e) {
				toastStore.show({ title: e?.message || __("Failed to load {0}", [name]), color: "error" });
			} finally {
				editLoading.value = false;
			}
		};

		const save = async () => {
			errorMessage.value = "";
			if (!warehouse.value) {
				errorMessage.value = __("Warehouse is required.");
				return;
			}
			if (!planItems.value.length) {
				errorMessage.value = __("Add at least one item.");
				return;
			}
			const invalid = planItems.value.find((row) => !(Number(row.plan_qty) > 0));
			if (invalid) {
				errorMessage.value = __("Plan Qty for {0} must be greater than zero.", [
					invalid.item_name || invalid.item_code,
				]);
				return;
			}

			submitLoading.value = true;
			try {
				const { message } = await frappe.call({
					method: `${API}.save_production_requirement`,
					args: {
						name: editName.value || undefined,
						data: {
							pos_profile: uiStore.posProfile ? JSON.stringify(uiStore.posProfile) : null,
							production_date: productionDate.value,
							posting_date: postingDate.value,
							warehouse: warehouse.value,
							production_by: productionBy.value,
							remarks: remarks.value,
							status: status.value,
							items: planItems.value.map((row) => ({
								item_code: row.item_code,
								item_name: row.item_name,
								uom: row.uom,
								plan_qty: Number(row.plan_qty || 0),
							})),
						},
					},
					freeze: true,
					freeze_message: __("Saving production requirement..."),
				});
				toastStore.show({
					title: editName.value
						? __("{0} updated", [message?.name])
						: __("Production Requirement {0} created", [message?.name]),
					color: "success",
				});
				await router.push(`/production-requirements/${encodeURIComponent(message?.name)}`);
			} catch (e) {
				errorMessage.value = e?.message || __("Failed to save production requirement");
			} finally {
				submitLoading.value = false;
			}
		};

		onMounted(async () => {
			const jobs = [loadCatalog(), loadFilterOptions(), loadContext().catch((e) => console.error(e))];
			if (editName.value) jobs.push(loadForEdit(editName.value));
			await Promise.all(jobs);
			if (context.can_change_warehouse) loadWarehouseOptions();
		});

		return {
			responsiveStyles,
			isCompact,
			compactPanel,
			showInvoicePanel,
			showSelectorPanel,
			setPanel,
			editName,
			editLoading,
			context,
			productionDateDisplay,
			postingDateDisplay,
			warehouse,
			warehouseName,
			warehouseOptions,
			productionBy,
			productionByName,
			userOptions,
			userSearchQuery,
			userSearchLoading,
			handleUserSearch,
			remarks,
			status,
			statusOptions,
			statusColor: productionRequirementStatusColor,
			planItems,
			submitLoading,
			errorMessage,
			totalPlanQty,
			catalogWarehouses,
			whCell,
			whShortage,
			shortageQty,
			addedCodes,
			formatQty,
			setQty,
			addItem,
			removeItem,
			save,
			catalogItems,
			catalogLoading,
			catalogSearch,
			filteredCatalog,
			visibleCatalog,
			catalogPage,
			catalogPageCount,
			catalogRangeStart,
			catalogRangeEnd,
			gridRef,
			loadCatalog,
			itemGroupFilter,
			stockStatusFilter,
			productionGroupFilter,
			filterOptions,
			stockStatusOptions,
		};
	},
};
</script>

<style scoped>
@import "../invoice-shared-styles.css";

.prq-header-grid {
	display: grid;
	grid-template-columns: repeat(2, minmax(0, 1fr));
	gap: 12px;
}

.prq-field {
	display: flex;
	flex-direction: column;
	gap: 2px;
}

.prq-field__label {
	font-size: 0.72rem;
	color: rgba(var(--v-theme-on-surface), 0.6);
}

.prq-items-table th:first-child,
.prq-items-table td:first-child {
	min-width: 170px;
}

.prq-items-table .prq-wh-col {
	font-size: 0.72rem;
	line-height: 1.2;
	white-space: normal;
	min-width: 64px;
	max-width: 90px;
}

.prq-num-cell {
	font-variant-numeric: tabular-nums;
}

.prq-items-table .prq-qty-col {
	width: 110px;
}

.prq-qty-input :deep(input) {
	text-align: center;
}

.prq-item-name {
	line-height: 1.25;
}

.prq-catalog {
	border-radius: 0;
}

.prq-catalog__search {
	display: flex;
	align-items: center;
	gap: 8px;
	padding: 12px 12px 8px;
}

.prq-catalog__grid-wrap {
	flex: 1 1 auto;
	overflow-y: auto;
	padding: 4px 12px 12px;
}

.prq-catalog__grid {
	display: grid;
	grid-template-columns: repeat(auto-fill, minmax(190px, 1fr));
	gap: 10px;
}

.prq-card {
	display: flex;
	flex-direction: column;
	gap: 6px;
	text-align: left;
	padding: 10px 12px;
	border-radius: 12px;
	border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
	background: rgb(var(--v-theme-surface));
	color: rgb(var(--v-theme-on-surface));
	cursor: pointer;
	transition:
		border-color 0.15s ease,
		box-shadow 0.15s ease,
		transform 0.1s ease;
}

.prq-card:hover {
	border-color: rgb(var(--v-theme-primary));
	box-shadow: 0 2px 10px rgba(0, 0, 0, 0.08);
}

.prq-card:active {
	transform: scale(0.98);
}

.prq-card--low {
	border-left: 4px solid rgb(var(--v-theme-error));
}

.prq-card--added {
	border-color: rgb(var(--v-theme-primary));
	background: rgba(var(--v-theme-primary), 0.06);
}

.prq-card__top {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 6px;
}

.prq-card__code {
	font-size: 0.72rem;
	font-weight: 600;
	font-variant-numeric: tabular-nums;
	color: rgba(var(--v-theme-on-surface), 0.6);
}

.prq-card__name {
	font-weight: 600;
	font-size: 0.88rem;
	line-height: 1.25;
	display: -webkit-box;
	-webkit-line-clamp: 2;
	-webkit-box-orient: vertical;
	overflow: hidden;
	min-height: 2.2em;
}

.prq-card__stats {
	display: grid;
	grid-template-columns: repeat(3, 1fr);
	gap: 4px;
	font-variant-numeric: tabular-nums;
}

.prq-card__stats > div {
	display: flex;
	flex-direction: column;
}

.prq-card__stat-label {
	font-size: 0.66rem;
	text-transform: uppercase;
	letter-spacing: 0.02em;
	color: rgba(var(--v-theme-on-surface), 0.55);
}

.prq-card__wh {
	border-top: 1px dashed rgba(var(--v-border-color), var(--v-border-opacity));
	padding-top: 4px;
	font-size: 0.72rem;
	font-variant-numeric: tabular-nums;
}

.prq-card__wh-row {
	display: flex;
	justify-content: space-between;
	gap: 6px;
}

.prq-card__wh-label {
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
	color: rgba(var(--v-theme-on-surface), 0.65);
}

.prq-card__wh-value {
	flex-shrink: 0;
	white-space: nowrap;
}

.prq-catalog__count {
	white-space: nowrap;
}

.prq-card__footer {
	display: flex;
	justify-content: space-between;
	gap: 6px;
	font-size: 0.7rem;
	color: rgba(var(--v-theme-on-surface), 0.55);
}

.prq-catalog__pagination {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 8px;
	/* Right padding keeps the page controls clear of the floating assistant button. */
	padding: 6px 84px 6px 12px;
	border-top: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.prq-catalog__filters {
	display: grid;
	grid-template-columns: repeat(3, minmax(0, 1fr));
	align-items: center;
	gap: 8px;
	padding: 10px 12px;
	border-top: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}

@media (max-width: 700px) {
	.prq-header-grid,
	.prq-catalog__filters {
		grid-template-columns: 1fr;
	}
}
</style>
