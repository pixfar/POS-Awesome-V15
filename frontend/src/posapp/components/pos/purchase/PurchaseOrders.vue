<template>
	<div
		class="pa-0 h-100 invoice-shell txn-shell"
		:style="responsiveStyles"
	>
		<v-row class="h-100 ma-0">
			<!-- Left Column: Purchase Invoice (Sales-style layout) -->
			<v-col
				v-show="showInvoicePanel"
				cols="12"
				:md="invoiceCols"
				class="h-100 pa-0 txn-col txn-col--invoice"
			>
				<v-card class="h-100 d-flex flex-column pos-themed-card purchase-invoice-card" flat>
					<v-card-text class="flex-grow-1 overflow-y-auto pa-3">
						<div class="invoice-sections">
							<div class="invoice-top-grid purchase-top-grid">
								<!-- Col 1: Supplier Details -->
								<v-card flat class="invoice-section-card pos-themed-card">
									<div class="invoice-section-heading">
										<h3 class="invoice-section-heading__title">
											{{ __("Supplier Details") }}
										</h3>
									</div>
									<PurchaseHeader
										v-model:supplier="supplier"
										:supplierOptions="supplierOptions"
										:supplierLoading="supplierLoading"
										@search-supplier="handleSupplierSearch"
										@create-supplier="supplierDialog = true"
									/>
								</v-card>

								<!-- Col 2: Supplier Outstanding -->
								<v-card flat class="invoice-section-card pos-themed-card outstanding-panel">
									<div class="outstanding-panel__inner">
										<div class="outstanding-panel__label">
											{{ __("Supplier Outstanding") }}
										</div>
										<div
											class="outstanding-panel__amount"
											:class="
												supplier && supplierOutstanding > 0
													? 'outstanding-panel__amount--due'
													: 'outstanding-panel__amount--clear'
											"
										>
											{{
												supplier
													? formatCurrency(supplierOutstanding)
													: "—"
											}}
										</div>
										<v-icon
											v-if="supplier"
											:color="supplierOutstanding > 0 ? 'error' : 'success'"
											size="22"
											class="outstanding-panel__icon"
										>
											{{
												supplierOutstanding > 0
													? "mdi-alert-circle"
													: "mdi-check-circle"
											}}
										</v-icon>
									</div>
								</v-card>

								<!-- Col 3: Purchase Options (Warehouse, Date, Toggles) -->
								<v-card flat class="invoice-section-card pos-themed-card sale-options-card">
									<div class="sale-options-body">
										<VueDatePicker
											v-model="postingDateTime"
											model-type="format"
											format="dd-MM-yyyy HH:mm"
											enable-time-picker
											auto-apply
											teleport
											:disabled="!canEditPostingDate"
											:placeholder="frappe._('Purchase Date')"
											class="sleek-field pos-themed-input mb-2"
										/>
										<div class="sale-options-toggles">
											<v-switch
												v-model="updateStock"
												density="compact"
												hide-details
												color="primary"
												:label="__('Update Stock')"
												class="sale-opt-switch"
											/>
											<v-switch
												v-model="customIsPaid"
												density="compact"
												hide-details
												color="primary"
												:label="__('Is Paid')"
												class="sale-opt-switch"
											/>
										</div>
										<v-autocomplete
											v-if="canChangePosWarehouse && warehouseOptions.length"
											v-model="warehouse"
											:items="warehouseOptions"
											item-title="name"
											item-value="name"
											:label="frappe._('Warehouse')"
											density="compact"
											variant="outlined"
											color="primary"
											hide-details
											:loading="warehouseLoading"
											class="pos-themed-input mt-2"
										/>
										<v-text-field
											v-else-if="warehouse"
											:model-value="warehouse || warehouseLabel"
											:label="frappe._('Warehouse')"
											density="compact"
											variant="outlined"
											color="primary"
											hide-details
											readonly
											prepend-inner-icon="mdi-warehouse"
											class="pos-themed-input mt-2"
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
										v-model="doNumber"
										:label="__('DO Number')"
										density="compact"
										variant="outlined"
										hide-details
										class="pos-themed-input"
									/>
								</div>
							</v-card>

							<v-card
								v-if="canEditPaymentAccount"
								flat
								class="invoice-section-card pos-themed-card"
							>
								<div class="invoice-section-heading">
									<h3 class="invoice-section-heading__title">{{ __("Accounts") }}</h3>
								</div>
								<div class="pa-3">
									<v-autocomplete
										v-model="paymentAccountOverride"
										:items="cashAccountOptions"
										item-title="name"
										item-value="name"
										:label="__('Accounts')"
										density="compact"
										variant="outlined"
										hide-details
										clearable
										:loading="cashAccountsLoading"
										class="pos-themed-input"
									/>
								</div>
							</v-card>

							<v-card flat class="invoice-section-card invoice-items-card pos-themed-card">
								<div class="invoice-section-heading">
									<h3 class="invoice-section-heading__title">
										{{ __("Purchase Items") }}
									</h3>
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
										:placeholder="__('Scan barcode or type item name / code')"
										:custom-filter="() => true"
										prepend-inner-icon="mdi-magnify"
										variant="solo"
										density="compact"
										color="primary"
										hide-details
										clearable
										class="pos-themed-input purchase-item-search"
										:no-data-text="
											itemSearchQuery && itemSearchQuery.length < 2
												? __('Type at least 2 characters')
												: __('No items found')
										"
										@update:search="handleItemSearchUpdate"
										@update:model-value="handleSearchItemPicked"
									>
										<template #item="{ props: itemProps, item }">
											<v-list-item v-bind="itemProps" :title="undefined">
												<v-list-item-title class="purchase-item-option__title">
													{{ item.raw.item_name }}
												</v-list-item-title>
												<v-list-item-subtitle class="purchase-item-option__meta">
													<span class="purchase-item-option__code">{{ item.raw.item_code }}</span>
													<span class="purchase-item-option__stock">
														{{ __("Stock") }}: {{ formatNumber(item.raw.actual_qty || 0) }} {{ item.raw.stock_uom || "" }}
													</span>
												</v-list-item-subtitle>
											</v-list-item>
										</template>
									</v-autocomplete>
								</div>
								<PurchaseItemsTable
									:headers="itemHeaders"
									:items="purchaseItems"
									:currencySymbol="currencySymbol(priceListCurrency || supplierCurrency)"
									:totalAmount="totalAmount"
									:receiveNow="false"
									:formatCurrency="formatCurrency"
									:formatNumber="formatNumber"
									@update-uom="({ item, value }) => updateItemUom(item, value)"
									@update-qty="({ item, value }) => updateItemQty(item, value)"
									@update-rate="({ item, value }) => updateItemRate(item, value)"
									@remove-item="removeItem"
								/>
							</v-card>

							<v-alert
								v-if="errorMessage"
								type="error"
								density="compact"
								class="mt-2"
							>
								{{ errorMessage }}
							</v-alert>
						</div>
					</v-card-text>

					<div v-if="!isCompact" class="purchase-bottom-bar">
						<div class="purchase-bottom-bar__summary">
							<span class="purchase-bottom-bar__label">{{ __("Purchase Total") }}</span>
							<strong class="purchase-bottom-bar__amount">
								{{ currencySymbol(supplierCurrency || pos_profile.currency) }}{{ formatCurrency(totalAmount) }}
							</strong>
							<span class="purchase-bottom-bar__meta">
								{{ purchaseItems.length }} {{ purchaseItems.length === 1 ? __("item") : __("items") }}
							</span>
						</div>
						<v-btn
							:loading="submitLoading"
							:disabled="submitLoading"
							@click="openPaymentDialog"
							size="large"
							class="text-none purchase-pay-btn"
							prepend-icon="mdi-credit-card"
						>
							{{ __("PAY") }}
						</v-btn>
					</div>
				</v-card>
			</v-col>

			<!-- Right Column: Item Selector -->
			<v-col
				v-show="showSelectorPanel"
				cols="12"
				:md="selectorCols"
				class="h-100 pa-0 border-s txn-col txn-col--selector"
			>
				<ItemsSelector context="purchase" @add-item="onAddItem" />
			</v-col>
		</v-row>

		<div v-if="isCompact" class="mobile-pos-stack txn-bottom-dock">
			<div class="mobile-sale-dock">
				<div class="mobile-sale-dock__copy">
					<span class="mobile-sale-dock__eyebrow">{{ __("Purchase Total") }}</span>
					<strong class="mobile-sale-dock__amount">
						{{ currencySymbol(supplierCurrency || pos_profile.currency) }}{{ formatCurrency(totalAmount) }}
					</strong>
					<span class="mobile-sale-dock__meta">
						{{ purchaseItems.length }} {{ purchaseItems.length === 1 ? __("item") : __("items") }}
					</span>
				</div>
				<v-btn
					:loading="submitLoading"
					:disabled="submitLoading"
					color="primary"
					variant="flat"
					class="text-none txn-dock-pay-btn"
					prepend-icon="mdi-credit-card"
					@click="openPaymentDialog"
				>
					{{ __("PAY") }}
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
					<span v-if="purchaseItems.length" class="mobile-pos-dock__pill">{{ purchaseItems.length }}</span>
					<v-icon icon="mdi-cart-outline" size="22" />
					<span>{{ __("Cart") }}</span>
				</button>
				<button
					type="button"
					class="mobile-pos-dock__item mobile-pos-dock__item--pay"
					@click="openPaymentDialog"
				>
					<v-icon icon="mdi-credit-card-outline" size="20" />
					<span>{{ __("Pay") }}</span>
				</button>
			</div>
		</div>

		<!-- Payment Dialog -->
		<PurchasePaymentDialog
			v-model="paymentDialog"
			:total-amount="totalAmount"
			:currency="supplierCurrency"
			:pos-profile="pos_profile"
			:is-paid="customIsPaid"
			@submit="handlePaymentSubmit"
		/>

		<!-- Supplier Dialog -->
		<SupplierDialog
			v-model="supplierDialog"
			:groups="supplierGroups"
			:posProfile="pos_profile"
			@created="handleSupplierCreated"
			@error="(msg) => toastStore.show({ title: msg, color: 'error' })"
		/>

		<!-- Validation Dialog -->
		<v-dialog v-model="validationDialog" max-width="380" persistent>
			<v-card class="pos-themed-card pa-2" style="border-radius: 12px;">
				<v-card-title class="d-flex align-center gap-2 pb-1">
					<v-icon color="warning" size="24">mdi-alert-circle-outline</v-icon>
					<span style="font-size: 1rem; font-weight: 700;">{{ __("Cannot Proceed") }}</span>
				</v-card-title>
				<v-card-text class="pt-1 pb-2" style="font-size: 0.92rem; color: var(--pos-text-secondary);">
					{{ validationMessage }}
				</v-card-text>
				<v-card-actions class="pt-0">
					<v-spacer />
					<v-btn
						color="primary"
						variant="flat"
						style="border-radius: 8px; text-transform: none; font-weight: 600;"
						@click="validationDialog = false"
					>
						{{ __("OK") }}
					</v-btn>
				</v-card-actions>
			</v-card>
		</v-dialog>
	</div>
</template>

<script>
import format, { formatUtils } from "../../../format";
import { useUIStore } from "../../../stores/uiStore.js";
import { getOpeningStorage } from "../../../../offline/index";
import { useItemsStore } from "../../../stores/itemsStore";
import { useToastStore } from "../../../stores/toastStore";
import { usePurchaseOrder } from "../../../composables/pos/payments/usePurchaseOrder";
import ItemsSelector from "../items/ItemsSelector.vue";
import PurchasePaymentDialog from "./PurchasePaymentDialog.vue";
import SupplierDialog from "../dialogs/purchase/SupplierDialog.vue";
import PurchaseHeader from "./PurchaseHeader.vue";
import PurchaseItemsTable from "./PurchaseItemsTable.vue";
import { ref, watch, onMounted, onBeforeUnmount, inject, computed } from "vue";
import { isPosWarehouseSwitcher, isFundTransferManager } from "../../../utils/posWarehouseAccess";
import { openDocumentPdfPrint } from "../../../utils/openDocumentPdfPrint";
import { useCompactTransactionPanel } from "../../../composables/core/useCompactTransactionPanel";

export default {
	mixins: [format],
	components: {
		ItemsSelector,
		PurchasePaymentDialog,
		SupplierDialog,
		PurchaseHeader,
		PurchaseItemsTable,
	},
	setup() {
		const uiStore = useUIStore();
		const toastStore = useToastStore();
		const itemsStore = useItemsStore();
		const eventBus = inject("eventBus");
		const {
			responsiveStyles,
			isCompact,
			compactPanel,
			showInvoicePanel,
			showSelectorPanel,
			invoiceCols,
			selectorCols,
			setPanel,
		} = useCompactTransactionPanel("invoice");

		const pos_profile = ref({});
		const receiveNow = ref(false);

		const {
			purchaseItems,
			supplier,
			warehouse,
			postingDateTime,
			updateStock,
			customIsPaid,
			doNumber,
			supplierCurrency,
			supplierPriceList,
			priceListCurrency,
			supplierOutstanding,
			totalAmount,
			submitLoading,
			errorMessage,
			onAddItem,
			fetchSupplierInfo,
			updateItemUom,
			updateItemQty,
			updateItemRate,
			updateItemReceivedQty,
			removeItem,
			resetForm,
			syncPurchaseItemsWarehouse,
		} = usePurchaseOrder({
			posProfile: pos_profile,
			receiveNow: receiveNow,
			formatFloat: (val, prec) => format.methods.formatFloat.call({ currency_precision: 2 }, val, prec),
			eventBus,
		});

		const supplierOptions = ref([]);
		const supplierLoading = ref(false);
		const supplierDialog = ref(false);
		const paymentDialog = ref(false);
		const validationDialog = ref(false);
		const validationMessage = ref("");
		const supplierGroups = ref([]);
		const warehouseOptions = ref([]);
		const warehouseLoading = ref(false);
		const warehouseLabel = ref(null);
		const canChangePosWarehouse = computed(() => isPosWarehouseSwitcher());
		const canEditDoNumber = computed(() => isFundTransferManager());
		const canEditPostingDate = computed(() => isFundTransferManager());
		// "Accounts" override -- System Manager / BSP Admin only. Defaults to
		// the active POS Profile's own account_for_change_amount (same account
		// every other payment already uses), but an admin can pick a different
		// showroom's cash account instead; re-verified server-side, this flag
		// is UX-only.
		const canEditPaymentAccount = computed(() => isFundTransferManager());
		const cashAccountOptions = ref([]);
		const cashAccountsLoading = ref(false);
		const paymentAccountOverride = ref(null);
		const payments = ref([]);
		const discountAmount = ref(0);
		const itemSearchQuery = ref("");
		const selectedSearchItemCode = ref(null);
		const itemSearchResults = ref([]);
		const itemSearchLoading = ref(false);

		const supplierSearchTimeout = ref(null);
		const itemSearchTimeout = ref(null);

		const handleSupplierSearch = (term) => {
			if (supplierSearchTimeout.value) clearTimeout(supplierSearchTimeout.value);
			supplierSearchTimeout.value = setTimeout(() => searchSuppliers(term), 300);
		};

		const searchSuppliers = async (searchText = "") => {
			supplierLoading.value = true;
			try {
				const { message } = await frappe.call({
					method: "posawesome.posawesome.api.purchase_invoices.search_suppliers",
					args: { search_text: searchText, limit: 20 },
				});
				supplierOptions.value = Array.isArray(message) ? message : [];
				if (supplier.value) {
					const s = supplierOptions.value.find((s) => s.name === supplier.value);
					supplierCurrency.value = s?.default_currency || pos_profile.value.currency;
				}
			} catch (error) {
				console.error("Failed to fetch suppliers:", error);
			} finally {
				supplierLoading.value = false;
			}
		};

		const loadSupplierGroups = async () => {
			try {
				const { message } = await frappe.call({
					method: "frappe.client.get_list",
					args: {
						doctype: "Supplier Group",
						fields: ["name"],
						filters: { is_group: 0 },
						limit_page_length: 500,
					},
				});
				supplierGroups.value = (message || []).map((row) => row.name);
			} catch (error) {
				console.error("Failed to load groups:", error);
			}
		};

		const refreshCatalogForWarehouse = async (wh) => {
			if (!wh) {
				return;
			}
			itemsStore.setActiveSaleWarehouse(wh);
			if (pos_profile.value) {
				pos_profile.value = {
					...pos_profile.value,
					warehouse: wh,
				};
			}
			if (typeof itemsStore.refreshItems === "function") {
				await itemsStore.refreshItems({
					warehouse: wh,
					forceServer: true,
				});
			}
		};

		const loadActiveWarehouseLabel = async () => {
			try {
				const { message } = await frappe.call({
					method: "bsp_engineering.api.pos_warehouse.get_pos_active_warehouse",
					args: {
						company: pos_profile.value?.company,
						pos_profile: pos_profile.value
							? JSON.stringify(pos_profile.value)
							: null,
					},
				});
				const row = message || {};
				if (row.name) {
					warehouse.value = row.name;
					warehouseLabel.value = row.warehouse_name || row.name;
					syncPurchaseItemsWarehouse(row.name);
					await refreshCatalogForWarehouse(row.name);
				}
			} catch (error) {
				console.error("Failed to load active warehouse:", error);
				const profileWh = pos_profile.value?.warehouse || null;
				if (profileWh) {
					warehouse.value = profileWh;
					warehouseLabel.value = profileWh;
					syncPurchaseItemsWarehouse(profileWh);
					await refreshCatalogForWarehouse(profileWh);
				}
			}
		};

		const loadWarehouses = async () => {
			warehouseLoading.value = true;
			const profileWh = pos_profile.value?.warehouse || null;
			if (!canChangePosWarehouse.value) {
				warehouseOptions.value = [];
				await loadActiveWarehouseLabel();
				warehouseLoading.value = false;
				return;
			}
			try {
				const { message } = await frappe.call({
					method: "bsp_engineering.api.pos_warehouse.get_pos_warehouses",
					args: {
						company: pos_profile.value?.company,
						pos_profile: pos_profile.value
							? JSON.stringify(pos_profile.value)
							: null,
					},
				});
				const msg = message || {};
				const warehouseList = Array.isArray(msg) ? msg : (msg.warehouses || []);
				const suggestedDefault = Array.isArray(msg) ? null : (msg.default_warehouse || null);
				warehouseOptions.value = warehouseList;
				const permitted = warehouseList.map((row) => row.name);
				let defaultWh = suggestedDefault || pos_profile.value?.warehouse || null;
				if (
					defaultWh &&
					permitted.length &&
					!permitted.includes(defaultWh)
				) {
					defaultWh = permitted[0];
				}
				if (!defaultWh && warehouseOptions.value.length) {
					defaultWh = warehouseOptions.value[0].name;
				}
				if (defaultWh) {
					warehouse.value = defaultWh;
					await refreshCatalogForWarehouse(defaultWh);
				}
			} catch (error) {
				console.error("Failed to load warehouses:", error);
				warehouseOptions.value = [];
			}
			if (!warehouseOptions.value.length && pos_profile.value?.warehouse) {
				const profileWh = pos_profile.value.warehouse;
				warehouseOptions.value = [
					{ name: profileWh, warehouse_name: profileWh },
				];
				warehouse.value = profileWh;
				await refreshCatalogForWarehouse(profileWh);
			}
			warehouseLoading.value = false;
		};

		const handleSupplierCreated = (message) => {
			supplierOptions.value.unshift(message);
			supplier.value = message.name;
			supplierDialog.value = false;
		};

		const searchItems = async (searchText = "") => {
			itemSearchLoading.value = true;
			try {
				const { message } = await frappe.call({
					method: "posawesome.posawesome.api.purchase_invoices.search_items",
					args: {
						search_text: searchText,
						limit: 20,
						warehouse: warehouse.value,
					},
				});
				itemSearchResults.value = Array.isArray(message) ? message : [];
			} catch (error) {
				console.error("Failed to fetch purchase items:", error);
				itemSearchResults.value = [];
			} finally {
				itemSearchLoading.value = false;
			}
		};

		const handleItemSearchUpdate = (term) => {
			itemSearchQuery.value = term || "";
			if (itemSearchTimeout.value) clearTimeout(itemSearchTimeout.value);
			if (!itemSearchQuery.value || itemSearchQuery.value.trim().length < 2) {
				itemSearchResults.value = [];
				return;
			}
			itemSearchTimeout.value = setTimeout(
				() => searchItems(itemSearchQuery.value.trim()),
				250,
			);
		};

		watch(warehouse, async (nextWarehouse) => {
			if (!nextWarehouse) {
				return;
			}
			if (canChangePosWarehouse.value) {
				syncPurchaseItemsWarehouse(nextWarehouse);
			}
			await refreshCatalogForWarehouse(nextWarehouse);
			itemSearchResults.value = [];
			const term = itemSearchQuery.value?.trim();
			if (term && term.length >= 2) {
				searchItems(term);
			}
		});

		const handleSearchItemPicked = async (itemCode) => {
			if (!itemCode) return;
			const found = itemSearchResults.value.find(
				(item) => String(item.item_code) === String(itemCode),
			);
			selectedSearchItemCode.value = null;
			if (!found) return;
			await onAddItem(found);
			itemSearchQuery.value = "";
			itemSearchResults.value = [];
		};

		const openPaymentDialog = () => {
			if (!supplier.value && !purchaseItems.value.length) {
				validationMessage.value = __("Please select a supplier and add at least one item before proceeding.");
				validationDialog.value = true;
				return;
			}
			if (!supplier.value) {
				validationMessage.value = __("Please select a supplier before proceeding to payment.");
				validationDialog.value = true;
				return;
			}
			if (!purchaseItems.value.length) {
				validationMessage.value = __("Please add at least one item before proceeding to payment.");
				validationDialog.value = true;
				return;
			}
			errorMessage.value = "";
			paymentDialog.value = true;
		};

		const handlePaymentSubmit = ({ payments: p, print, print_format, print_invoice, discount_amount }) => {
			payments.value = p;
			discountAmount.value = discount_amount || 0;
			paymentDialog.value = false;
			submitPurchaseInvoice(print, print_format);
		};

		const extractServerError = (error) => {
			const parseServerMessages = (raw) => {
				if (!raw) return "";
				try {
					const parsed = JSON.parse(raw);
					if (Array.isArray(parsed) && parsed.length) {
						const first = parsed[0];
						if (typeof first === "string") {
							return first.replace(/<[^>]*>/g, "").trim();
						}
					}
				} catch {
					return String(raw);
				}
				return "";
			};

			return (
				parseServerMessages(error?._server_messages) ||
				parseServerMessages(error?.responseJSON?._server_messages) ||
				error?.message ||
				error?.responseJSON?.message ||
				__("Unable to create purchase invoice")
			);
		};

		const splitPostingDateTime = (dateTimeValue) => {
			if (!dateTimeValue) {
				return {
					posting_date: frappe.datetime.nowdate(),
					posting_time: frappe.datetime.now_time(),
				};
			}

			const western = formatUtils.fromArabicNumerals(String(dateTimeValue).trim());
			const match = western.match(
				/^(\d{2})-(\d{2})-(\d{4})(?:\s+(\d{1,2}):(\d{2}))?$/,
			);
			if (match) {
				const hours = match[4] ? String(match[4]).padStart(2, "0") : "00";
				const minutes = match[5] || "00";
				return {
					posting_date: `${match[3]}-${match[2]}-${match[1]}`,
					posting_time: `${hours}:${minutes}:00`,
				};
			}

			if (/^\d{4}-\d{2}-\d{2}$/.test(western)) {
				return {
					posting_date: western,
					posting_time: frappe.datetime.now_time(),
				};
			}

			const parsed = new Date(western);
			if (!isNaN(parsed.getTime())) {
				const pad = (value) => String(value).padStart(2, "0");
				return {
					posting_date: `${parsed.getFullYear()}-${pad(parsed.getMonth() + 1)}-${pad(parsed.getDate())}`,
					posting_time: `${pad(parsed.getHours())}:${pad(parsed.getMinutes())}:00`,
				};
			}

			return {
				posting_date: frappe.datetime.nowdate(),
				posting_time: frappe.datetime.now_time(),
			};
		};

		const submitPurchaseInvoice = async (print = false, printFormat = null) => {
			if (!supplier.value || !postingDateTime.value) {
				errorMessage.value = __("Supplier and date are required.");
				return;
			}
			submitLoading.value = true;
			try {
				const { posting_date, posting_time } = splitPostingDateTime(
					postingDateTime.value,
				);

				const resolvedSupplier =
					typeof supplier.value === "object" && supplier.value !== null
						? supplier.value.name || supplier.value.supplier_name || ""
						: supplier.value;

				const txnWarehouse =
					canChangePosWarehouse.value
						? warehouse.value
						: pos_profile.value?.warehouse;

				const payload = {
					supplier: resolvedSupplier,
					company: pos_profile.value.company,
					warehouse: txnWarehouse,
					currency: supplierCurrency.value,
					posting_date,
					posting_time,
					transaction_date: posting_date,
					schedule_date: posting_date,
					receive: 0,
					update_stock: updateStock.value ? 1 : 0,
					custom_is_paid: customIsPaid.value ? 1 : 0,
					custom_do_number: doNumber.value || null,
					// Server re-verifies System Manager / BSP Admin before honoring
					// this -- see purchase_orders._create_purchase_invoice_from_pos.
					payment_account: canEditPaymentAccount.value ? (paymentAccountOverride.value || null) : null,
					pos_profile: pos_profile.value,
					payments: payments.value,
					discount_amount: discountAmount.value,
					items: purchaseItems.value.map((item) => ({
						item_code: item.item_code,
						item_name: item.item_name,
						stock_uom: item.stock_uom,
						uom: item.uom,
						conversion_factor: item.conversion_factor,
						qty: item.qty,
						rate: item.rate,
						warehouse:
							txnWarehouse ||
							pos_profile.value?.warehouse,
					})),
				};
				const { message } = await frappe.call({
					method: "posawesome.posawesome.api.purchase_invoices.create_purchase_invoice",
					args: { data: payload },
				});
				const invoiceName = message?.purchase_invoice || message?.purchase_order;
				if (invoiceName) {
					toastStore.show({ title: __("Purchase Invoice created"), color: "success" });
					if (print) {
						const doctype = "Purchase Invoice";
						const docname = invoiceName;
						const formatName =
							printFormat ||
							pos_profile.value.print_format_for_purchase ||
							"BSP Purchase Invoice";
						try {
							await openDocumentPdfPrint({
								doctype,
								name: docname,
								printFormat: formatName,
								autoPrint: true,
							});
						} catch (printError) {
							console.warn("PDF print failed, opening printview", printError);
							const printUrl = frappe.urllib.get_full_url(
								`/printview?doctype=${doctype}&name=${docname}&format=${encodeURIComponent(formatName)}&trigger_print=1`,
							);
							window.open(printUrl, "_blank")?.focus();
						}
					}
					resetForm();
				}
			} catch (error) {
				errorMessage.value = extractServerError(error);
				toastStore.show({ title: errorMessage.value, color: "error" });
			} finally {
				submitLoading.value = false;
			}
		};

		const loadCashInHandAccounts = async (company) => {
			if (!canEditPaymentAccount.value || !company) return;
			cashAccountsLoading.value = true;
			try {
				const { message } = await frappe.call({
					method: "posawesome.posawesome.api.payment_processing.utils.get_cash_in_hand_accounts",
					args: { company },
				});
				cashAccountOptions.value = message || [];
			} catch (e) {
				console.error("Failed to load Cash In Hand accounts", e);
				cashAccountOptions.value = [];
			} finally {
				cashAccountsLoading.value = false;
			}
		};

		onMounted(async () => {
			const cachedData = getOpeningStorage();
			if (cachedData?.pos_profile) pos_profile.value = cachedData.pos_profile;

			watch(
				() => uiStore.posProfile,
				(p) => {
					if (p) pos_profile.value = p;
				},
				{ immediate: true },
			);
			watch(
				() => pos_profile.value?.company,
				(company) => {
					// Default to this POS Profile's own change account -- the
					// user can still pick a different one from the dropdown.
					paymentAccountOverride.value = pos_profile.value?.account_for_change_amount || null;
					loadCashInHandAccounts(company);
				},
				{ immediate: true },
			);
			watch(supplier, async (val) => {
				if (val) {
					const info = await fetchSupplierInfo(val);
					if (info?.buying_price_list) {
						await itemsStore.updatePriceList(info.buying_price_list, { skipReload: true });
					}
					eventBus?.emit?.("update_buying_price_list", {
						supplier: val,
					});
				} else {
					supplierCurrency.value = pos_profile.value.currency;
					eventBus?.emit?.("update_buying_price_list", null);
				}
			});

			try {
				const { message } = await frappe.call({
					method: "posawesome.posawesome.api.purchase_invoices.get_buying_price_list",
				});
				if (message) await itemsStore.updatePriceList(message);
			} catch (e) {
				console.error("Failed price list load", e);
			}

			resetForm();
			await Promise.all([searchSuppliers(""), loadSupplierGroups(), loadWarehouses()]);
		});

		onBeforeUnmount(() => {
			eventBus?.emit?.("update_buying_price_list", null);
			if (supplierSearchTimeout.value) clearTimeout(supplierSearchTimeout.value);
			if (itemSearchTimeout.value) clearTimeout(itemSearchTimeout.value);
			if (pos_profile.value?.selling_price_list)
				itemsStore.updatePriceList(pos_profile.value.selling_price_list);
		});

		return {
			pos_profile,
			receiveNow,
			canChangePosWarehouse,
			canEditDoNumber,
			canEditPostingDate,
			canEditPaymentAccount,
			cashAccountOptions,
			cashAccountsLoading,
			paymentAccountOverride,
			doNumber,
			responsiveStyles,
			isCompact,
			compactPanel,
			showInvoicePanel,
			showSelectorPanel,
			invoiceCols,
			selectorCols,
			setPanel,
			purchaseItems,
			supplier,
			warehouse,
			warehouseLabel,
			postingDateTime,
			updateStock,
			customIsPaid,
			supplierCurrency,
			supplierPriceList,
			priceListCurrency,
			supplierOutstanding,
			totalAmount,
			submitLoading,
			errorMessage,
			onAddItem,
			fetchSupplierInfo,
			updateItemUom,
			updateItemQty,
			updateItemRate,
			updateItemReceivedQty,
			removeItem,
			resetForm,
			supplierOptions,
			supplierLoading,
			supplierDialog,
			paymentDialog,
			validationDialog,
			validationMessage,
			supplierGroups,
			warehouseOptions,
			warehouseLoading,
			handleSupplierSearch,
			handleSupplierCreated,
			itemSearchQuery,
			selectedSearchItemCode,
			itemSearchResults,
			itemSearchLoading,
			handleItemSearchUpdate,
			handleSearchItemPicked,
			openPaymentDialog,
			handlePaymentSubmit,
			toastStore,
		};
	},
	computed: {
		itemHeaders() {
			return [
				{ title: __("Item"), key: "item_name", align: "start", width: "28%" },
				{ title: __("Item Code"), key: "item_code", align: "start", width: "14%" },
				{ title: __("UOM"), key: "uom", align: "center", width: "13%" },
				{ title: __("QTY"), key: "qty", align: "center", width: "13%" },
				{ title: __("Rate"), key: "rate", align: "center", width: "14%" },
				{ title: __("Amount"), key: "amount", align: "end", width: "10%" },
				{ title: __("Actions"), key: "actions", align: "center", width: "50px" },
			];
		},
	},
	methods: {
		formatNumber(v) {
			return this.formatFloat(v, 2);
		},
		currencySymbol(c) {
			return get_currency_symbol(c || this.pos_profile.currency);
		},
	},
};
</script>

<style scoped>
@import "../invoice-shared-styles.css";

/* 3-column top grid matching Sales layout */
.purchase-top-grid {
	grid-template-columns: 2.5fr 1fr 2fr !important;
	align-items: stretch;
	gap: 12px !important;
	margin-bottom: 12px;
}

/* Force every card in the top grid to fill the row height */
.purchase-top-grid > .invoice-section-card {
	height: 100%;
	display: flex;
	flex-direction: column;
}

/* Outstanding panel fills height and centers its content */
.purchase-top-grid > .outstanding-panel {
	justify-content: center;
}

@media (max-width: 768px) {
	.purchase-top-grid {
		grid-template-columns: 1fr !important;
	}
	.purchase-top-grid > .invoice-section-card {
		height: auto;
	}
}

/* Purchase Options card (col 3) */
.sale-options-card {
	display: flex;
	flex-direction: column;
}

.sale-options-body {
	padding: 8px 14px 12px;
	display: flex;
	flex-direction: column;
	gap: 0;
	flex: 1 1 auto;
}

.sale-options-toggles {
	display: flex;
	flex-direction: row;
	gap: 8px;
	flex-wrap: wrap;
	margin-top: 4px;
}

.sale-opt-switch {
	flex: 0 0 auto;
}

.purchase-date-picker {
	width: 100%;
}

.purchase-invoice-card {
	border-radius: var(--pos-radius-md, 18px);
}

.purchase-bottom-bar {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 16px;
	padding: 12px 16px;
	background: var(--pos-primary);
	border-radius: 10px;
	margin: 8px 12px 12px;
}

.purchase-bottom-bar__summary {
	display: flex;
	flex-direction: column;
	gap: 3px;
	min-width: 0;
}

.purchase-bottom-bar__label {
	font-size: 0.7rem;
	font-weight: 700;
	text-transform: uppercase;
	letter-spacing: 0.08em;
	color: rgba(255, 255, 255, 0.72);
}

.purchase-bottom-bar__amount {
	font-size: clamp(1.1rem, 2vw, 1.6rem);
	font-weight: 700;
	color: #ffffff;
	line-height: 1.1;
}

.purchase-bottom-bar__meta {
	font-size: 0.82rem;
	color: rgba(255, 255, 255, 0.82);
}

.outstanding-panel {
	display: flex;
	align-items: center;
	justify-content: center;
}

.outstanding-panel__inner {
	display: flex;
	flex-direction: column;
	align-items: center;
	justify-content: center;
	gap: 4px;
	padding: 12px 16px;
	width: 100%;
	height: 100%;
	text-align: center;
}

.outstanding-panel__label {
	font-size: 0.72rem;
	font-weight: 600;
	text-transform: uppercase;
	letter-spacing: 0.08em;
	color: var(--pos-text-secondary, rgba(0, 0, 0, 0.5));
}

.outstanding-panel__amount {
	font-size: 1.5rem;
	font-weight: 700;
	line-height: 1.1;
}

.outstanding-panel__amount--due {
	color: rgb(var(--v-theme-error));
}

.outstanding-panel__amount--clear {
	color: rgb(var(--v-theme-success));
}

.outstanding-panel__icon {
	margin-top: 2px;
}

.purchase-search-toolbar {
	padding: 8px 16px 12px;
}

.purchase-pay-btn {
	background: #ffffff !important;
	color: var(--pos-primary) !important;
	font-weight: 700;
	letter-spacing: 0.02em;
	border-radius: 8px !important;
	min-width: 140px !important;
	box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15) !important;
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
