<template>
	<div class="pa-0 h-100 invoice-shell">
		<v-row class="h-100 ma-0">
			<!-- Left Column: Purchase Invoice (Sales-style layout) -->
			<v-col cols="12" md="7" class="h-100 pa-0">
				<v-card class="h-100 d-flex flex-column pos-themed-card purchase-invoice-card" flat>
					<v-card-text class="flex-grow-1 overflow-y-auto pa-3">
						<div class="invoice-sections">
							<div class="invoice-top-grid">
								<v-card flat class="invoice-section-card pos-themed-card">
									<div class="invoice-section-heading d-flex align-center">
										<h3 class="invoice-section-heading__title">
											{{ __("Supplier Details") }}
										</h3>
										<v-spacer></v-spacer>
										<v-btn
											icon="mdi-delete-outline"
											variant="text"
											size="small"
											color="error"
											@click="resetForm"
											:title="__('Clear All')"
											:aria-label="__('Clear all purchase invoice items')"
										></v-btn>
									</div>
									<PurchaseHeader
										v-model:supplier="supplier"
										v-model:warehouse="warehouse"
										v-model:postingDateTime="postingDateTime"
										v-model:updateStock="updateStock"
										v-model:customIsPaid="customIsPaid"
										:supplierOptions="supplierOptions"
										:supplierLoading="supplierLoading"
										:warehouseOptions="warehouseOptions"
										:warehouseLoading="warehouseLoading"
										:allowCreateSupplier="allowCreateSupplier"
										@search-supplier="handleSupplierSearch"
										@create-supplier="supplierDialog = true"
									/>
								</v-card>

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
											:color="
												supplierOutstanding > 0 ? 'error' : 'success'
											"
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
							</div>

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

					<div class="purchase-bottom-bar">
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
			<v-col cols="12" md="5" class="h-100 pa-0 border-s">
				<ItemsSelector context="purchase" @add-item="onAddItem" />
			</v-col>
		</v-row>

		<!-- Payment Dialog -->
		<PurchasePaymentDialog
			v-model="paymentDialog"
			:total-amount="totalAmount"
			:currency="supplierCurrency"
			:pos-profile="pos_profile"
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
import { ref, watch, onMounted, onBeforeUnmount, inject } from "vue";

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

		const pos_profile = ref({});
		const receiveNow = ref(false);

		const {
			purchaseItems,
			supplier,
			warehouse,
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
		} = usePurchaseOrder({
			posProfile: pos_profile,
			receiveNow: receiveNow,
			formatFloat: (val, prec) => format.methods.formatFloat.call({ currency_precision: 2 }, val, prec),
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
		const payments = ref([]);
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

		const loadWarehouses = async () => {
			warehouseLoading.value = true;
			try {
				const { message } = await frappe.call({
					method: "frappe.client.get_list",
					args: {
						doctype: "Warehouse",
						fields: ["name", "warehouse_name"],
						filters: { company: pos_profile.value.company, is_group: 0, disabled: 0 },
					},
				});
				warehouseOptions.value = message || [];
			} catch (error) {
				console.error("Failed to load warehouses:", error);
			} finally {
				warehouseLoading.value = false;
			}
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
					args: { search_text: searchText, limit: 20 },
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

		const handlePaymentSubmit = ({ payments: p, print, print_format, print_invoice }) => {
			payments.value = p;
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

				const payload = {
					supplier: resolvedSupplier,
					company: pos_profile.value.company,
					warehouse: warehouse.value,
					currency: supplierCurrency.value,
					posting_date,
					posting_time,
					transaction_date: posting_date,
					schedule_date: posting_date,
					receive: 0,
					update_stock: updateStock.value ? 1 : 0,
					custom_is_paid: customIsPaid.value ? 1 : 0,
					pos_profile: pos_profile.value,
					payments: payments.value,
					items: purchaseItems.value.map((item) => ({
						item_code: item.item_code,
						item_name: item.item_name,
						stock_uom: item.stock_uom,
						uom: item.uom,
						conversion_factor: item.conversion_factor,
						qty: item.qty,
						rate: item.rate,
						warehouse: warehouse.value || item.warehouse,
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
						const printUrl = frappe.urllib.get_full_url(
							`/printview?doctype=${doctype}&name=${docname}&print_format=${encodeURIComponent(formatName)}`,
						);
						window.open(printUrl, "_blank")?.focus();
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
			watch(supplier, async (val) => {
				if (val) {
					const info = await fetchSupplierInfo(val);
					if (info?.buying_price_list) {
						await itemsStore.updatePriceList(info.buying_price_list, { skipReload: true });
					}
					eventBus?.emit?.("update_buying_price_list", {
						price_list: info?.buying_price_list || null,
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
			purchaseItems,
			supplier,
			warehouse,
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
		allowCreateSupplier() {
			return !!this.pos_profile?.posa_allow_create_purchase_suppliers;
		},
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
@import "../Invoice.vue.css";

.purchase-invoice-card {
	border-radius: var(--pos-radius-md, 18px);
}

.purchase-bottom-bar {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 16px;
	padding: 12px 16px;
	background: #2563eb;
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
	color: #2563eb !important;
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
