<template>
	<!-- Main Invoice Wrapper -->
	<div class="pa-0 invoice-shell">
		<!-- Cancel Sale Confirmation Dialog -->
		<CancelSaleDialog v-model="cancel_dialog" @confirm="cancel_invoice" />

		<!-- Main Invoice Card (contains all invoice content) -->
		<v-card
			ref="invoiceCard"
			:style="invoiceMainCardStyle"
			:class="[
				'cards my-0 py-0 resizable invoice-main-card',
				'pos-themed-card',
				{ 'return-mode': isReturnInvoice },
			]"
			@mouseup="saveInvoiceHeight($refs.invoiceCard)"
			@touchend="saveInvoiceHeight($refs.invoiceCard)"
		>
			<!-- Scrollable invoice body -->
			<div class="dynamic-padding invoice-main-scroll">
				<v-alert
					type="info"
					density="compact"
					class="invoice-status-alert mb-0"
					v-if="pos_profile.create_pos_invoice_instead_of_sales_invoice"
				>
					{{ __("Invoices saved as POS Invoices") }}
				</v-alert>
				<div class="invoice-sections">
					<v-card flat class="invoice-section-card pos-themed-card invoice-sale-header create-header-card">
						<div class="sale-header create-header">
							<div class="create-header__grid">
								<div class="create-header__party">
									<InvoiceCustomerSection
										ref="customerSection"
										:pos_profile="pos_profile"
										:invoiceTypes="invoiceTypes"
										v-model="invoiceType"
									/>
								</div>
								<div
									v-if="!pos_profile.posa_use_delivery_charges"
									class="create-header__metric"
								>
									<v-text-field
										:model-value="customer ? formatCurrency(customer_outstanding) : '—'"
										:label="__('Due')"
										:title="customer ? formatCurrency(customer_outstanding) : ''"
										readonly
										density="compact"
										variant="outlined"
										hide-details
										class="pos-themed-input create-header__metric-field"
										:class="{
											'create-header__metric-field--due': customer && customer_outstanding > 0,
											'create-header__metric-field--clear': customer && customer_outstanding <= 0,
										}"
									>
										<template #append-inner>
											<v-icon
												v-if="customer"
												:color="customer_outstanding > 0 ? 'error' : 'success'"
												size="18"
											>
												{{ customer_outstanding > 0 ? 'mdi-alert-circle' : 'mdi-check-circle' }}
											</v-icon>
										</template>
									</v-text-field>
								</div>
								<div
									v-else
									class="create-header__delivery"
								>
									<DeliveryCharges
										ref="deliveryChargesComponent"
										:pos_profile="pos_profile"
										:delivery_charges="delivery_charges"
										:selected_delivery_charge="selected_delivery_charge"
										:delivery_charges_rate="delivery_charges_rate"
										:deliveryChargesFilter="deliveryChargesFilter"
										:formatCurrency="formatCurrency"
										:currencySymbol="currencySymbol"
										:readonly="readonly"
										@update:selected_delivery_charge="
											(val) => {
												selected_delivery_charge = val;
												update_delivery_charges(conversion_rate, currency_precision);
											}
										"
									/>
								</div>

								<div class="create-header__field">
									<PostingDateRow
										ref="postingDateComponent"
										:pos_profile="pos_profile"
										:posting_date_display="posting_date_display"
										:customer_balance="customer_balance"
										:price-list="selected_price_list"
										:price-lists="price_lists"
										:formatCurrency="formatCurrency"
										:disabled="!canEditPostingDate"
										@update:posting_date_display="
											(val) => {
												posting_date_display = val;
											}
										"
										@update:priceList="
											(val) => {
												selected_price_list = val;
											}
										"
									/>
								</div>
								<div class="create-header__field">
									<v-select
										v-if="canChangePosWarehouse && warehouses.length"
										:model-value="sale_warehouse"
										:items="warehouses"
										item-title="label"
										item-value="value"
										:label="__('Warehouse')"
										variant="outlined"
										density="compact"
										hide-details
										class="pos-themed-input"
										@update:model-value="onSaleWarehouseUpdate"
									/>
									<v-text-field
										v-else-if="sale_warehouse"
										:model-value="sale_warehouse_label || sale_warehouse"
										:label="__('Warehouse')"
										variant="outlined"
										density="compact"
										hide-details
										readonly
										prepend-inner-icon="mdi-warehouse"
										class="pos-themed-input"
									/>
								</div>

								<div class="create-header__toggles">
									<v-switch
										v-model="sale_update_stock"
										:label="__('Update Stock')"
										color="primary"
										density="compact"
										hide-details
										class="sale-opt-switch"
									/>
									<v-switch
										v-model="sale_is_paid"
										:label="__('Is Paid')"
										color="primary"
										density="compact"
										hide-details
										class="sale-opt-switch"
									/>
								</div>

								<div v-if="canEditDoNumber" class="create-header__field">
									<v-text-field
										v-model="custom_do_number"
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
								<div v-if="canEditPaymentAccount" class="create-header__field">
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

								<div
									v-if="pos_profile.posa_allow_multi_currency"
									class="create-header__span-all"
								>
									<MultiCurrencyRow
										:pos_profile="pos_profile"
										:selected_currency="selected_currency"
										:plc_conversion_rate="exchange_rate"
										:conversion_rate="conversion_rate"
										:available_currencies="available_currencies"
										:isNumber="isNumber"
										:price_list_currency="price_list_currency"
										@update:selected_currency="
											(val) => {
												selected_currency = val;
												update_currency(val);
											}
										"
										@update:plc_conversion_rate="
											(val) => {
												exchange_rate = val;
												update_exchange_rate();
											}
										"
										@update:conversion_rate="
											(val) => {
												conversion_rate = val;
												update_conversion_rate();
											}
										"
									/>
								</div>
							</div>
						</div>
					</v-card>

					<v-card flat class="invoice-section-card invoice-items-card pos-themed-card">
						<div class="invoice-section-heading">
							<h3 class="invoice-section-heading__title">{{ __("Invoice Items") }}</h3>
						</div>
						<div class="items-table-wrapper">
							<InvoiceItemsActionToolbar
								ref="actionToolbar"
								:catalog-search="catalogSearchProp"
								:availableColumns="available_columns"
								:selectedColumns="selected_columns"
								@update:selectedColumns="
									(cols) => {
										selected_columns = cols;
										saveColumnPreferences();
									}
								"
							/>

							<ItemsTable
								ref="itemsTableRef"
								:headers="items_headers"
								v-model:expanded="expanded"
								:itemsPerPage="itemsPerPage"
								:pos_profile="pos_profile"
								:invoiceType="invoiceType"
								:stock_settings="stock_settings"
								:displayCurrency="displayCurrency"
								:formatFloat="formatFloat"
								:formatCurrency="formatCurrency"
								:currencySymbol="currencySymbol"
								:isNumber="isNumber"
								:setFormatedQty="setFormatedQty"
								:setFormatedCurrency="setFormatedCurrency"
								:calcPrices="calc_prices"
								:calcUom="calc_uom"
								:setSerialNo="set_serial_no"
								:setBatchQty="set_batch_qty"
								:validateDueDate="validate_due_date"
								:removeItem="remove_item"
								:subtractOne="subtract_one"
								:addOne="add_one"
								:toggleOffer="toggleOffer"
								:changePriceListRate="change_price_list_rate"
								:isNegative="isNegative"
								@update:expanded="handleExpandedUpdate"
								@reorder-items="handleItemReorder"
								@add-item-from-drag="handleItemDrop"
								@show-drop-feedback="
									(isDragging) => showDropFeedback(isDragging, itemsTableRef)
								"
								@item-dropped="showDropFeedback(false, itemsTableRef)"
								@view-packed="openPackedItems"
							/>

							<PackedItemsDialog
								v-model="show_packed_dialog"
								:items="packed_dialog_items"
								:displayCurrency="displayCurrency"
								:formatFloat="formatFloat"
								:formatCurrency="formatCurrency"
								:currencySymbol="currencySymbol"
							/>
						</div>
					</v-card>

					<v-card flat class="invoice-section-card pos-themed-card remarks-section-card">
						<div class="invoice-section-heading">
							<h3 class="invoice-section-heading__title">{{ __("Remarks") }}</h3>
						</div>
						<div class="sale-header__remarks-body">
							<v-text-field
								v-model="remarks"
								:label="__('Remarks')"
								density="compact"
								variant="outlined"
								hide-details
								clearable
								class="pos-themed-input"
							/>
						</div>
					</v-card>
				</div>
			</div>

			<!-- Sale dock pinned to bottom of invoice column (purchase-style) -->
			<div class="invoice-summary-dock">
				<InvoiceSummary
					ref="invoiceSummary"
					:pos_profile="pos_profile"
					:total_qty="total_qty"
					:additional_discount="additional_discount"
					:additional_discount_percentage="additional_discount_percentage"
					:total_items_discount_amount="total_items_discount_amount"
					:subtotal="subtotal"
					:displayCurrency="displayCurrency"
					:formatFloat="formatFloat"
					:formatCurrency="formatCurrency"
					:currencySymbol="currencySymbol"
					:discount_percentage_offer_name="discount_percentage_offer_name"
					:isNumber="isNumber"
					:return_discount_meta="return_discount_meta"
					:sale_update_stock="sale_update_stock"
					:sale_is_paid="sale_is_paid"
					:sale_warehouse="sale_warehouse"
					:warehouses="warehouses"
					@update:additional_discount="(val) => (additional_discount = val)"
					@update:additional_discount_percentage="(val) => (additional_discount_percentage = val)"
					@update_discount_umount="update_discount_umount"
					@update:sale_update_stock="(val) => (sale_update_stock = val)"
					@update:sale_is_paid="(val) => (sale_is_paid = val)"
					@update:sale_warehouse="onSaleWarehouseUpdate"
					@save-and-clear="save_and_clear_invoice"
					@load-drafts="get_draft_invoices"
					@select-order="get_draft_orders"
					@cancel-sale="cancel_dialog = true"
					@open-invoice-management="open_invoice_management"
					@open-returns="open_returns"
					@print-draft="print_draft_invoice"
					@show-payment="handleShowPaymentRequest"
					@open-customer-display="handleOpenCustomerDisplayRequest"
					@resume-parked-order="resume_parked_order"
				/>
			</div>
		</v-card>

		<!-- Payment Confirmation Dialog -->
		<PaymentConfirmationDialog
			ref="paymentConfirmationDialog"
			v-model="confirm_payment_dialog"
			@confirm="resolvePaymentConfirmation(true)"
			@cancel="resolvePaymentConfirmation(false)"
		/>
		<PriceListRateDialog
			v-model="price_list_rate_dialog_open"
			:initial-rate="price_list_rate_dialog_initial_rate"
			:item-label="price_list_rate_dialog_item_label"
			:currency-symbol="currencySymbol(selected_currency || pos_profile?.currency)"
			@submit="handlePriceListRateDialogSubmit"
			@cancel="handlePriceListRateDialogCancel"
		/>
	</div>
</template>

<script>
import format from "../../format";
import InvoiceCustomerSection from "./invoice/InvoiceCustomerSection.vue";
import DeliveryCharges from "./invoice/DeliveryCharges.vue";
import PostingDateRow from "./invoice/PostingDateRow.vue";
import MultiCurrencyRow from "./invoice/MultiCurrencyRow.vue";
import CancelSaleDialog from "./invoice/CancelSaleDialog.vue";
import InvoiceSummary from "./invoice/InvoiceSummary.vue";
import ItemsTable from "./invoice/ItemsTable.vue";
import InvoiceItemsActionToolbar from "./invoice/InvoiceItemsActionToolbar.vue";
import PackedItemsDialog from "./invoice/PackedItemsDialog.vue";
import PaymentConfirmationDialog from "./payments/PaymentConfirmationDialog.vue";
import PriceListRateDialog from "./invoice/PriceListRateDialog.vue";
import invoiceItemMethods from "./invoice/invoiceItemMethods";
import invoiceComputed from "./invoice/invoiceComputed";
import invoiceWatchers from "./invoice/invoiceWatchers";
import shortcutMethods from "./invoice/invoiceShortcuts";
import { useInvoiceStore } from "../../stores/invoiceStore.js";
import { useCustomersStore } from "../../stores/customersStore.js";
import { useToastStore } from "../../stores/toastStore.js";
import { useUIStore } from "../../stores/uiStore.js";
import { useItemsStore } from "../../stores/itemsStore.js";
import { storeToRefs } from "pinia";
import stockCoordinator from "../../utils/stockCoordinator";
import { getCurrentInstance, ref, computed } from "vue";
import { save_and_clear_invoice as saveAndClearInvoiceAction } from "./invoice_utils/actions";
import { applyWarehouseToDocItems } from "./invoice_utils/warehouse";
import { isPosWarehouseSwitcher } from "../../utils/posWarehouseAccess";
import { fetchDraftInvoices } from "../../utils/draftInvoices";

// Composables
import { useOnlineStatus } from "../../composables/core/useOnlineStatus";
import { useInvoiceCurrency } from "../../composables/pos/invoice/useInvoiceCurrency";
import { useInvoiceItems } from "../../composables/pos/invoice/useInvoiceItems";
import { useInvoiceOffers } from "../../composables/pos/invoice/useInvoiceOffers";
import { useInvoiceUI } from "../../composables/pos/invoice/useInvoiceUI";
import { useInvoicePrinting } from "../../composables/pos/invoice/useInvoicePrinting";
import { useInvoiceStock } from "../../composables/pos/invoice/useInvoiceStock";
import { usePaymentPrinting } from "../../composables/pos/payments/usePaymentPrinting";
import { loadSaleDefaults, saveSaleDefaults } from "../../utils/saleDefaultsCache";
import {
	createInvoiceShortcutListeners,
	registerInvoiceShortcutListener,
	unregisterInvoiceShortcutListener,
} from "../../utils/invoiceShortcutListener";

export default {
	name: "POSInvoice",
	props: {
		catalogSearch: {
			type: Object,
			default: null,
		},
	},
	mixins: [format],
	setup(props) {
		const instance = getCurrentInstance();
		const uiStore = useUIStore();
		const itemsStore = useItemsStore();
		const invoiceStore = useInvoiceStore();
		const customersStore = useCustomersStore();
		const toastStore = useToastStore();
		const { isOnline } = useOnlineStatus();

		const { activeView, posProfile: livePosProfile } = storeToRefs(uiStore);
		const { selectedCustomer, refreshToken: customerRefreshToken } = storeToRefs(customersStore);
		const {
			items,
			packedItems: packed_items,
			invoiceDoc: invoice_doc,
			invoiceType,
			flowToLoad,
			flowContext,
		} = storeToRefs(invoiceStore);
		const itemsTableRef = ref(null);
		const currencyState = useInvoiceCurrency({}, {});
		const itemActions = useInvoiceItems(invoiceType);
		const offerLogic = useInvoiceOffers();

		// New composables
		const uiLogic = useInvoiceUI();
		const { loadPrintPage } = usePaymentPrinting({
			invoiceDoc: invoice_doc,
			posProfile: livePosProfile,
			invoiceType,
		});
		const printingLogic = useInvoicePrinting(
			livePosProfile,
			loadPrintPage,
			() => {
				if (!instance?.proxy) {
					return Promise.resolve(null);
				}
				return saveAndClearInvoiceAction(instance.proxy);
			},
			invoice_doc,
		);

		const stockLogic = useInvoiceStock(items, packed_items, uiStore.eventBus, () => {});

		return {
			catalogSearchProp: computed(() => props.catalogSearch),
			uiStore,
			itemsStore,
			activeView,
			isOnline,
			toastStore,
			invoiceStore,
			customersStore,
			selectedCustomer,
			customerRefreshToken,
			invoiceType,
			flowToLoad,
			flowContext,
			itemsTableRef,
			...currencyState,
			...itemActions,
			...offerLogic,
			...uiLogic,
			...printingLogic,
			...stockLogic,
		};
	},
	data() {
		return {
			pos_profile: "",
			pos_opening_shift: "",
			stock_settings: "",
			return_doc: "",
			customer: "",
			customer_info: "",
			customer_balance: 0,
			customer_outstanding: 0,
			total_tax: 0,
			packed_dialog_items: [],
			show_packed_dialog: false,
			invoiceTypes: ["Invoice", "Order", "Quotation"],
			itemsPerPage: 1000,
			expanded: [],
			singleExpand: true,
			cancel_dialog: false,
			available_stock_cache: {},
			item_detail_cache: {},
			item_stock_cache: {},
			brand_cache: {},
			stockUnsubscribe: null,
			invoice_posting_date: false,
			posting_date_display: "",
			_shortcutHandlers: {},
			shortcutSubmitInFlight: false,
			shortcutCycle: {
				qty: 0,
				uom: 0,
				rate: 0,
			},
			return_discount_base_total: 0,
			return_discount_base_amount: 0,
			_busHandlers: {},
			price_list_rate_dialog_open: false,
			price_list_rate_dialog_initial_rate: "",
			price_list_rate_dialog_item_label: "",
			price_list_rate_dialog_resolver: null,
			// Sales flags — shown in the bottom dock so the user can toggle before paying
			sale_update_stock: true,
			sale_is_paid: true,
			sale_warehouse: null,
			sale_warehouse_label: null,
			warehouses: [],
			doNumberLookupLoading: false,
			doNumberDraft: "",
			cashAccountOptions: [],
			cashAccountsLoading: false,
			paymentAccountOverride: null,
			remarks: "",
		};
	},

	components: {
		InvoiceCustomerSection,
		DeliveryCharges,
		PostingDateRow,
		MultiCurrencyRow,
		InvoiceSummary,
		CancelSaleDialog,
		ItemsTable,
		InvoiceItemsActionToolbar,
		PackedItemsDialog,
		PaymentConfirmationDialog,
		PriceListRateDialog,
	},
	computed: {
		invoiceMainCardStyle() {
			const canResize = this.canResizeInvoicePanel?.() === true;
			return {
				flex: "1 1 auto",
				minHeight: 0,
				height: "100%",
				maxHeight: "100%",
				resize: canResize ? "vertical" : "none",
				overflow: "hidden",
			};
		},
		items: {
			get() {
				return this.invoiceStore.items;
			},
			set(value) {
				this.invoiceStore.setItems(value);
			},
		},
		invoice_doc: {
			get() {
				return this.invoiceStore.invoiceDoc;
			},
			set(value) {
				this.invoiceStore.setInvoiceDoc(value);
			},
		},
		packed_items: {
			get() {
				return this.invoiceStore.packedItems;
			},
			set(value) {
				this.invoiceStore.setPackedItems(value);
			},
		},
		paymentVisible() {
			return this.activeView === "payment" || this.uiStore.paymentDialogOpen;
		},
		discount_amount: {
			get() {
				return this.invoiceStore.discountAmount;
			},
			set(val) {
				this.invoiceStore.setDiscountAmount(val);
			},
		},
		additional_discount: {
			get() {
				return this.invoiceStore.additionalDiscount;
			},
			set(val) {
				this.invoiceStore.setAdditionalDiscount(val);
			},
		},
		additional_discount_percentage: {
			get() {
				return this.invoiceStore.additionalDiscountPercentage;
			},
			set(val) {
				this.invoiceStore.setAdditionalDiscountPercentage(val);
			},
		},
		posting_date: {
			get() {
				return this.invoiceStore.postingDate;
			},
			set(val) {
				this.invoiceStore.setPostingDate(val);
			},
		},
		canChangePosWarehouse() {
			return isPosWarehouseSwitcher();
		},
		canEditDoNumber() {
			const roles = frappe?.boot?.user?.roles || [];
			return roles.includes("BSP Admin") || roles.includes("System Manager");
		},
		canEditPostingDate() {
			const roles = frappe?.boot?.user?.roles || [];
			return roles.includes("BSP Admin") || roles.includes("System Manager");
		},
		canEditPaymentAccount() {
			const roles = frappe?.boot?.user?.roles || [];
			return roles.includes("BSP Admin") || roles.includes("System Manager");
		},
		custom_do_number: {
			get() {
				// On a brand new, not-yet-saved invoice invoiceStore.invoiceDoc is
				// still null (it's only created once the first item lands in the
				// cart), so there's nowhere to persist a typed DO Number yet.
				// doNumberDraft is the local echo that covers exactly that gap —
				// see the setter below and handleDoNumberLookup.
				return this.invoiceStore.invoiceDoc?.custom_do_number || this.doNumberDraft || "";
			},
			set(value) {
				this.doNumberDraft = value;
				if (this.invoiceStore.invoiceDoc) {
					this.invoiceStore.invoiceDoc.custom_do_number = value;
				}
			},
		},
		return_discount_meta() {
			if (!this.isReturnInvoice || !this.return_doc || this.pos_profile?.posa_use_percentage_discount) {
				return null;
			}

			const originalDiscount = Math.abs(Number(this.return_discount_base_amount || 0));
			if (!originalDiscount) return null;

			const originalTotal = Math.abs(Number(this.return_discount_base_total || 0));
			if (!originalTotal) return null;

			const returnTotal = Math.abs(Number(this.Total || 0));
			if (!returnTotal) return null;

			const ratio = Math.min(1, returnTotal / originalTotal);
			const prorated = originalDiscount * ratio;

			return {
				ratio,
				original_discount: originalDiscount,
				prorated_discount: prorated,
			};
		},
		...invoiceComputed,
	},

	methods: {
		// Non-switcher: the one warehouse this user works in. Returns
		// { name, label } (or the POS Profile's warehouse when the lookup
		// fails); resolveSaleWarehouse applies it.
		async loadActiveWarehouseLabel() {
			try {
				const result = await frappe.call({
					method: "bsp_engineering.api.pos_warehouse.get_pos_active_warehouse",
					args: {
						company: this.pos_profile?.company,
						pos_profile: this.pos_profile
							? JSON.stringify(this.pos_profile)
							: null,
					},
				});
				const row = result.message || {};
				return row.name ? { name: row.name, label: row.warehouse_name || row.name } : null;
			} catch (e) {
				console.error("Failed to load active warehouse", e);
				const profileWh = this.pos_profile?.warehouse || null;
				return profileWh ? { name: profileWh, label: profileWh } : null;
			}
		},
		async reloadItemsForWarehouse(warehouse) {
			if (!warehouse || typeof this.itemsStore?.refreshItems !== "function") {
				return;
			}
			await this.itemsStore.refreshItems({ warehouse, forceServer: true });
		},
		fetchWarehouses() {
			// mounted() and profile registration both call this at load -- share
			// one in-flight resolution instead of resolving (and reloading the
			// item catalogue) twice.
			const profileName = this.pos_profile?.name || "";
			if (this._fetchWarehousesPromise && this._fetchWarehousesProfile === profileName) {
				return this._fetchWarehousesPromise;
			}
			this._fetchWarehousesProfile = profileName;
			const promise = (async () => {
				try {
					await this.resolveSaleWarehouse();
				} finally {
					if (this._fetchWarehousesPromise === promise) {
						this._fetchWarehousesPromise = null;
					}
					// Release the item catalog even if no warehouse could be
					// resolved -- but not on the mounted() call that runs before
					// the POS Profile is registered, which can't resolve anything.
					if (this.pos_profile?.name) {
						this.itemsStore?.endWarehouseResolution?.();
					}
				}
			})();
			this._fetchWarehousesPromise = promise;
			return promise;
		},
		async resolveSaleWarehouse() {
			// Nothing to resolve before the POS Profile is registered: without
			// it the server answers with just the first permitted warehouse,
			// and when that answer arrived after the real one it replaced the
			// correct warehouse/account (e.g. Asif Engineering / Cash - BSP
			// instead of Store Room).
			const profileName = this.pos_profile?.name;
			if (!profileName) {
				return;
			}
			// Only the newest lookup may apply its result, and never over a
			// warehouse the cashier has already picked by hand.
			const token = (this._warehouseResolveToken || 0) + 1;
			this._warehouseResolveToken = token;
			const isCurrent = () =>
				token === this._warehouseResolveToken && !this._userPickedWarehouse;
			const profileWh = this.pos_profile?.warehouse || null;

			// Last server-resolved default for this user + profile: applied at
			// once so the screen and its catalogue start on the right warehouse
			// and account without waiting for the lookups below, which still
			// run and correct it if the default has changed.
			const cached = this._userPickedWarehouse ? null : loadSaleDefaults(profileName);
			if (cached) {
				this.applySaleWarehouse(cached.warehouse, cached.warehouse_label);
				if (this.canEditPaymentAccount && cached.account) {
					this.paymentAccountOverride = cached.account;
				}
				void this.reloadItemsForWarehouse(cached.warehouse);
			}

			const applyResolved = async (warehouse, label, { syncAccount }) => {
				if (!warehouse || !isCurrent()) return;
				if (warehouse !== cached?.warehouse) {
					this.applySaleWarehouse(warehouse, label);
					if (syncAccount) await this.syncAccountForWarehouse(warehouse);
					if (!isCurrent()) return;
					await this.reloadItemsForWarehouse(warehouse);
				} else if (syncAccount && !cached?.account) {
					await this.syncAccountForWarehouse(warehouse);
				}
				if (!isCurrent()) return;
				saveSaleDefaults(profileName, {
					warehouse,
					warehouse_label: label || warehouse,
					account: this.canEditPaymentAccount ? this.paymentAccountOverride : null,
				});
			};

			if (!this.canChangePosWarehouse) {
				this.warehouses = [];
				const active = await this.loadActiveWarehouseLabel();
				if (active) {
					await applyResolved(active.name, active.label, { syncAccount: false });
				}
				return;
			}
			try {
				const result = await frappe.call({
					method: "bsp_engineering.api.pos_warehouse.get_pos_warehouses",
					args: {
						company: this.pos_profile?.company,
						pos_profile: this.pos_profile
							? JSON.stringify(this.pos_profile)
							: null,
					},
				});
				if (token !== this._warehouseResolveToken) return;
				const msg = result.message || {};
				const warehouseList = Array.isArray(msg) ? msg : (msg.warehouses || []);
				const suggestedDefault = Array.isArray(msg) ? null : (msg.default_warehouse || null);
				this.warehouses = warehouseList.map((w) => ({
					value: w.name,
					label: w.warehouse_name || w.name,
				}));
				const permitted = this.warehouses.map((w) => w.value);
				let defaultWh = suggestedDefault || profileWh;
				if (defaultWh && permitted.length && !permitted.includes(defaultWh)) {
					defaultWh = permitted[0];
				}
				if (!defaultWh && this.warehouses.length) {
					defaultWh = this.warehouses[0].value;
				}
				if (defaultWh) {
					// Also pushes the warehouse into the item catalogue / stock
					// coordinator (setActiveSaleWarehouse) and the cart -- without
					// that, a default differing from pos_profile.warehouse left
					// stock figures primed against the profile's warehouse (false
					// "Insufficient stock" at Pay).
					const label = this.warehouses.find((w) => w.value === defaultWh)?.label;
					await applyResolved(defaultWh, label, { syncAccount: true });
				}
			} catch (e) {
				console.error("Failed to fetch warehouses", e);
				this.warehouses = [];
			}
			if (!this.warehouses.length && profileWh) {
				this.warehouses = [
					{ value: profileWh, label: profileWh },
				];
				await applyResolved(profileWh, profileWh, { syncAccount: false });
			}
		},
		// Scrolls the cart (Invoice Items table) into view. onlyIfHidden: leave
		// the scroll position alone when the table is already on screen.
		scrollCartIntoView({ onlyIfHidden = false } = {}) {
			const table = this.$el?.querySelector?.(".items-table-wrapper");
			if (!table || !table.offsetParent) return; // panel hidden (phone Browse view)
			if (onlyIfHidden) {
				const rect = table.getBoundingClientRect();
				const summary = this.$el.querySelector(".invoice-summary-dock");
				const bottomLimit = summary
					? Math.min(window.innerHeight, summary.getBoundingClientRect().top)
					: window.innerHeight;
				if (rect.top >= 0 && rect.top + 120 <= bottomLimit) return;
			}
			table.scrollIntoView({ block: "start", behavior: "smooth" });
		},
		applySaleWarehouse(warehouse, label) {
			this.sale_warehouse = warehouse;
			this.sale_warehouse_label = label || warehouse;
			if (this.canChangePosWarehouse && !this.warehouses.some((w) => w.value === warehouse)) {
				this.warehouses = [{ value: warehouse, label: label || warehouse }, ...this.warehouses];
			}
			this.itemsStore?.setActiveSaleWarehouse?.(warehouse);
			this.syncCartWarehouse(warehouse);
		},
		onSaleWarehouseUpdate(val) {
			if (!this.canChangePosWarehouse) {
				return;
			}
			if (!val || val === this.sale_warehouse) {
				return;
			}
			// A hand-picked warehouse is never replaced by a default lookup
			// still running in the background.
			this._userPickedWarehouse = true;
			this.sale_warehouse = val;
			this.handleSaleWarehouseChange(val);
		},
		syncCartWarehouse(warehouse) {
			// IMPORTANT: this.pos_profile is the *exact same object reference*
			// as this.uiStore.posProfile (handleRegisterPosProfile does
			// `this.pos_profile = data.pos_profile`, no clone) -- and
			// mounted() has a `{ deep: true }` $watch on uiStore.posProfile
			// that calls handleRegisterPosProfile again on any change to it.
			// Mutating this.pos_profile.warehouse here (an earlier attempt at
			// this fix) therefore re-triggered that deep watcher, which
			// re-ran registration, which called back into this same method,
			// which mutated it again -- an infinite loop that manifested as
			// the whole POS screen re-fetching everything every ~1s with an
			// empty cart. Do NOT reintroduce a write to this.pos_profile
			// here; see the ItemsSelector.vue add_item fix (activeSaleWarehouse)
			// for how new items get the correct warehouse without this.
			if (!warehouse || !Array.isArray(this.items)) {
				return;
			}
			let changed = false;
			this.items.forEach((item) => {
				if (item && item.warehouse !== warehouse) {
					item.warehouse = warehouse;
					changed = true;
				}
			});
			if (changed) {
				this.invoiceStore.setItems([...this.items]);
			}

			// invoiceStore.invoiceDoc is a *separate*, cached snapshot from
			// invoiceStore.items -- it's what actually gets submitted (see
			// usePaymentSubmission's invoiceDoc prop), built once via
			// get_invoice_doc() and otherwise only refreshed by further item
			// edits (see invoice_utils/server.ts's debounced sync). Updating
			// this.items above was never enough on its own: switching
			// warehouse with no further cart edit before hitting PAY left
			// this cached doc's items -- and the stock/GL entries created
			// from them -- pointing at the *previous* warehouse, even though
			// set_warehouse and everything else in the UI already showed the
			// new one. Same class of bug, and same fix, as
			// paymentAccountOverride's watcher below.
			//
			// Rows in this cached doc usually came back from the server
			// (update_invoice / frappe.client.get), where is_stock_item is
			// missing -- it isn't a Sales Invoice Item field. Requiring a
			// truthy is_stock_item here skipped every such row, so stock went
			// out of the previous warehouse. Only a row known to be non-stock
			// (from the row itself or its cart line) is left without a
			// warehouse; everything else follows the switch.
			const doc = this.invoiceStore.invoiceDoc;
			if (doc) {
				const updatedItems = Array.isArray(doc.items)
					? applyWarehouseToDocItems(doc.items, warehouse, this.items)
					: doc.items;
				this.invoiceStore.setInvoiceDoc({
					...doc,
					set_warehouse: warehouse,
					items: updatedItems,
				});
			}
		},
		// Each warehouse lists its own Cash / Bank Accounts; a sale's money
		// must land in the same warehouse its stock leaves from. Switching
		// warehouse selects that warehouse's account (keeping the current one
		// if it already belongs to it). The server enforces the same rule.
		async syncAccountForWarehouse(warehouse) {
			if (!this.canEditPaymentAccount || !warehouse) {
				return;
			}
			try {
				const r = await frappe.call({
					method: "posawesome.posawesome.utils.invoice_warehouse.get_sale_cash_account",
					args: { warehouse, current: this.paymentAccountOverride },
				});
				if (r?.message && r.message !== this.paymentAccountOverride) {
					this.paymentAccountOverride = r.message;
				}
			} catch (error) {
				console.error("Failed to resolve the warehouse's cash account", error);
			}
		},
		async handleSaleWarehouseChange(warehouse) {
			if (!this.canChangePosWarehouse || !warehouse) {
				return;
			}
			// Stock/rates belong to the previous warehouse — drop the cart
			// instead of rewriting item.warehouse and keeping stale qty/stock.
			if (Array.isArray(this.items) && this.items.length) {
				this.invoiceStore.clearItems();
				this.invoiceStore.setPackedItems([]);
				this.expanded = [];
			}
			await this.syncAccountForWarehouse(warehouse);
			const canRefresh = this.canChangePosWarehouse;
			this.itemsStore?.setActiveSaleWarehouse?.(warehouse);
			if (
				canRefresh &&
				typeof this.itemsStore?.refreshItems === "function"
			) {
				await this.itemsStore.refreshItems({ warehouse });
			}
		},
		// setActiveSaleWarehouse/refreshItems above only refetches actual_qty
		// for whatever page the *catalog* is currently showing -- an item
		// already sitting in the cart (scrolled out of the catalog view, or
		// added via DO Number lookup) is never part of that page, so its
		// actual_qty -- and the cart's "Stock Qty" column, which reads it
		// directly -- kept silently showing the *previous* warehouse's number
		// after a switch. Explicitly re-fetch actual_qty for exactly the item
		// codes already in the cart, against the new warehouse.
		async refreshCartStockForWarehouse(warehouse) {
			if (!warehouse || !Array.isArray(this.items) || !this.items.length) {
				return;
			}
			if (typeof this.itemsStore?.refreshActualQtyForItemCodes !== "function") {
				return;
			}
			const qtyMap = await this.itemsStore.refreshActualQtyForItemCodes(
				this.items,
				warehouse,
			);
			if (!qtyMap || !qtyMap.size) {
				return;
			}
			let changed = false;
			this.items.forEach((item) => {
				if (!item || !qtyMap.has(item.item_code)) {
					return;
				}
				const freshQty = qtyMap.get(item.item_code);
				if (item.actual_qty !== freshQty || item._stockWarehouse !== warehouse) {
					item.actual_qty = freshQty;
					item._stockWarehouse = warehouse;
					changed = true;
				}
			});
			if (changed) {
				this.invoiceStore.setItems([...this.items]);
			}
		},
		formatDateForDisplay(date) {
			if (!date) return "";
			const parts = date.split("-");
			if (parts.length === 3) {
				return `${parts[2]}-${parts[1]}-${parts[0]}`;
			}
			return date;
		},
		...shortcutMethods,
		...invoiceItemMethods,
		focusCustomerSearchField() {
			const customerSection = this.$refs.customerSection;
			if (customerSection && typeof customerSection.focusCustomerSearch === "function") {
				customerSection.focusCustomerSearch();
			}
		},

		focusItemSearchField() {
			this.uiStore.triggerItemSearchFocus();
		},

		focusInvoiceCatalogSearchField() {
			this.$refs.actionToolbar?.focusSearch?.();
		},

		focusAdditionalDiscountField() {
			this.eventBus?.emit?.("focus_additional_discount");
			this.$refs.invoiceSummary?.focusAdditionalDiscountField?.();
		},

		handleStockCoordinatorUpdate(event = {}) {
			const codes = Array.isArray(event.codes) ? event.codes : [];
			if (!codes.length) return;
			this.applyStockStateToInvoiceItems(codes);
		},

		// UI methods from composable are available in scope but might need wrapping if they access 'this' context unavailable in setup
		// showDropFeedback is handled by composable

		openPackedItems(bundle_id) {
			this.packed_dialog_items = this.packed_items.filter((it) => it.bundle_id === bundle_id);
			this.show_packed_dialog = true;
		},

		makeid(length) {
			let result = "";
			const characters = "abcdefghijklmnopqrstuvwxyz0123456789";
			const charactersLength = characters.length;
			for (var i = 0; i < length; i++) {
				result += characters.charAt(Math.floor(Math.random() * charactersLength));
			}
			return result;
		},

		handleExpandedUpdate(ids) {
			this.expanded = Array.isArray(ids) ? ids.slice(-1) : [];
		},

		applyReturnDiscountProration(options = {}) {
			const { defer } = options || {};
			if (defer && typeof this.$nextTick === "function") {
				this.$nextTick(() => {
					setTimeout(() => this.applyReturnDiscountProration(), 0);
				});
				return;
			}

			if (
				!this.isReturnInvoice ||
				this.pos_profile?.posa_use_percentage_discount ||
				!this.return_doc ||
				typeof this.return_doc !== "object"
			) {
				return;
			}

			const originalDiscount = Math.abs(Number(this.return_discount_base_amount || 0));
			const originalTotal = Math.abs(Number(this.return_discount_base_total || 0));
			const returnTotal = Math.abs(Number(this.Total || 0));

			if (!originalDiscount || !originalTotal || !returnTotal) {
				return;
			}

			const ratio = Math.min(1, returnTotal / originalTotal);
			const prorated = -Math.abs(originalDiscount * ratio);

			console.log("[POSA][Returns] Event auto-prorate discount", {
				originalDiscount,
				originalTotal,
				returnTotal,
				ratio,
				prorated,
			});

			this.discount_amount = prorated;
			this.additional_discount = prorated;
			this.additional_discount_percentage = 0;
		},

		async set_delivery_charges(options = {}) {
			const { forceReset = false } = options;
			if (!this.pos_profile || !this.customer || !this.pos_profile.posa_use_delivery_charges) {
				this.delivery_charges = [];
				this.base_delivery_charges_rate = 0;
				this.delivery_charges_rate = 0;
				this.selected_delivery_charge = "";
				return;
			}

			if (forceReset) {
				this.base_delivery_charges_rate = 0;
				this.delivery_charges_rate = 0;
				this.selected_delivery_charge = "";
			}
			try {
				const r = await frappe.call({
					method: "posawesome.posawesome.api.offers.get_applicable_delivery_charges",
					args: {
						company: this.pos_profile.company,
						pos_profile: this.pos_profile.name,
						customer: this.customer,
					},
				});
				if (r.message && r.message.length) {
					this.delivery_charges = r.message;
				}
			} catch (error) {
				console.error("Failed to fetch delivery charges", error);
			}
		},
		deliveryChargesFilter(itemText, queryText, itemRow) {
			const item = itemRow.raw;
			const textOne = item.name.toLowerCase();
			const searchText = queryText.toLowerCase();
			return textOne.indexOf(searchText) > -1;
		},
		updatePostingDate(date) {
			if (!date) return;
			this.posting_date = date;
			this.invoiceStore.setPostingDate(date);
			this.$forceUpdate();
		},

		// Entering a DO Number on the Sales screen pulls in whatever items were
		// actually received under that DO on the Purchase side (see
		// purchase_orders.get_items_by_do_number), adding each to the cart at
		// qty 1 — same as clicking its catalog card — so the cashier adjusts
		// quantity the normal way and the existing cart Stock Qty column (which
		// already tracks the current warehouse correctly for any item) is what
		// they check against. Items with no received qty under this DO at all
		// are reported back as unavailable instead of being added.
		onDoNumberFocusChange(focused) {
			// Vuetify's v-text-field @blur listens for a re-emitted "blur" custom
			// event that isn't reliably fired the same way as the native DOM
			// event here; @update:focused is the documented, reliable way to
			// detect a field losing focus, so this is the actual blur trigger.
			if (!focused) {
				this.handleDoNumberLookup();
			}
		},

		async handleDoNumberLookup() {
			const doNumber = (this.custom_do_number || "").trim();
			if (!doNumber) {
				return;
			}
			// Items already sitting in the cart are left completely untouched --
			// add_item would otherwise merge into that existing line and bump its
			// qty by 1, which silently inflates a quantity the cashier already
			// set/reviewed (possibly from a *different* DO Number's lookup) every
			// time a DO Number is looked up. Only genuinely new item codes get
			// added, at qty 1, same as clicking a fresh catalog card.
			this.doNumberLookupLoading = true;
			try {
				const lookup = await frappe.call({
					method: "posawesome.posawesome.api.purchase_invoices.get_items_by_do_number",
					args: {
						do_number: doNumber,
						warehouse: this.sale_warehouse,
						company: this.pos_profile?.company,
					},
				});
				const result = lookup?.message || { items: [], unavailable: [] };
				const foundItems = result.items || [];
				const unavailable = result.unavailable || [];

				let addedCount = 0;
				let skippedExisting = 0;
				for (const row of foundItems) {
					const alreadyInCart = (this.items || []).some(
						(cartRow) => cartRow.item_code === row.item_code,
					);
					if (alreadyInCart) {
						skippedExisting += 1;
						continue;
					}
					try {
						// Go through the exact same search lookup a catalog card
						// click/scan uses (posawesome.posawesome.api.items.get_items)
						// instead of building a cart item by hand from a partial
						// payload — that's what previously produced items with a
						// zero rate and a warehouse that didn't match this sale,
						// since building it manually meant guessing at fields this
						// endpoint already computes correctly on its own.
						const searchRes = await frappe.call({
							method: "posawesome.posawesome.api.items.get_items",
							args: {
								pos_profile: JSON.stringify({
									...this.pos_profile,
									warehouse: this.sale_warehouse || this.pos_profile?.warehouse,
								}),
								price_list: this.selected_price_list,
								search_value: row.item_code,
							},
						});
						const matches = searchRes?.message || [];
						const catalogItem =
							matches.find((m) => m.item_code === row.item_code) || matches[0];
						if (!catalogItem) continue;
						await this.add_item({ ...catalogItem }, { skipNotification: true });
						addedCount += 1;
					} catch (itemError) {
						console.error("Failed to add DO item", row.item_code, itemError);
					}
				}

				if (addedCount) {
					this.toastStore.show({
						title: __("{0} item(s) added from DO {1}", [addedCount, doNumber]),
						color: "success",
					});
				}

				if (skippedExisting) {
					this.toastStore.show({
						title: __("{0} item(s) already in the cart were left unchanged", [skippedExisting]),
						color: "info",
					});
				}

				if (unavailable.length) {
					const names = unavailable
						.map((row) => row.item_name || row.item_code)
						.join(", ");
					this.toastStore.show({
						title: __("Not available in this warehouse"),
						detail: names,
						color: "warning",
					});
				}

				if (!foundItems.length && !unavailable.length) {
					this.toastStore.show({
						title: __("No received items found for DO {0}", [doNumber]),
						color: "warning",
					});
				}
			} catch (error) {
				console.error("Error looking up DO Number:", error);
				this.toastStore.show({
					title: __("Error looking up DO Number"),
					color: "error",
				});
			} finally {
				this.doNumberLookupLoading = false;
			}
		},

		update_exchange_rate() {
			this.sync_exchange_rate();
		},

		update_conversion_rate() {
			this.sync_exchange_rate();
		},

		async update_exchange_rate_on_server() {
			if (this.conversion_rate) {
				if (!this.items.length) {
					this.sync_exchange_rate();
					return;
				}

				const doc = this.get_invoice_doc();
				doc.conversion_rate = this.conversion_rate;
				doc.plc_conversion_rate = this._getPlcConversionRate();
				try {
					const resp = await this.update_invoice(doc);
					if (resp && resp.exchange_rate_date) {
						this.exchange_rate_date = resp.exchange_rate_date;
						const posting_backend = this.formatDateForBackend(this.posting_date_display);
						if (posting_backend !== this.exchange_rate_date) {
							this.toastStore.show({
								title: __(
									"Exchange rate date " +
										this.exchange_rate_date +
										" differs from posting date " +
										posting_backend,
								),
								color: "warning",
							});
						}
					}
					this.sync_exchange_rate();
				} catch (error) {
					console.error("Error updating exchange rate:", error);
					this.toastStore.show({
						title: "Error updating exchange rate",
						color: "error",
					});
				}
			}
		},

		sync_exchange_rate() {
			if (!this.exchange_rate || this.exchange_rate <= 0) {
				this.exchange_rate = 1;
			}
			if (!this.conversion_rate || this.conversion_rate <= 0) {
				this.conversion_rate = 1;
			}

			this.eventBus.emit("update_currency", {
				currency: this.selected_currency || this.pos_profile.currency,
				exchange_rate: this.exchange_rate,
				conversion_rate: this.conversion_rate,
			});

			this.update_item_rates();
			this.update_delivery_charges(this.conversion_rate, this.currency_precision);
		},

		handleRegisterPosProfile(data) {
			// The deep watcher on uiStore.posProfile (mounted) fires on every
			// replacement of the profile object -- cached copy, then server
			// copy, then each shift check -- with the same profile. Re-running
			// the full registration each time re-fetched warehouses, price
			// lists, currencies, drafts, cash accounts and the whole item
			// catalogue 3-4 times per page load, blocking the page (and its
			// menu) for seconds. Same profile + company + opening shift: only
			// refresh the local copies below.
			const registrationKey = [
				data.pos_profile?.name,
				data.pos_profile?.company,
				data.pos_opening_shift?.name,
			].join("|");
			const alreadyRegistered = registrationKey === this._posProfileRegistrationKey;
			this._posProfileRegistrationKey = registrationKey;

			this.pos_profile = data.pos_profile;
			this.company = data.company || null;
			this.pos_opening_shift = data.pos_opening_shift;
			this.stock_settings = data.stock_settings;

			this.invoiceType = this.pos_profile.posa_default_sales_order ? "Order" : "Invoice";

			if (alreadyRegistered) {
				return;
			}
			this.customer = data.pos_profile.customer;

			// Seed warehouse from POS profile if user hasn't picked one yet.
			// Only an already-resolved warehouse goes to the item store here --
			// the profile's static default is just a placeholder until
			// fetchWarehouses() resolves the real one, and handing it over
			// would load the catalog for the wrong warehouse first.
			if (this.sale_warehouse) {
				this.itemsStore?.setActiveSaleWarehouse?.(this.sale_warehouse);
			} else if (data.pos_profile?.warehouse) {
				this.sale_warehouse = data.pos_profile.warehouse;
			}

			this.fetchWarehouses();
			this.fetch_price_lists();
			this.update_price_list();
			this.fetch_available_currencies();
			this.refresh_parked_orders();

			// Admin-only "Accounts" override -- default to whatever the cashier
			// already picked elsewhere this session (uiStore.activeSaleAccount,
			// shared with the standalone Payment screen, Expense Claim, and
			// Purchase Order screens), falling back to this POS Profile's own
			// change account only when nothing has been picked yet. Without the
			// shared value, this screen re-mounting (e.g. after collecting a
			// payment on a different screen) silently reverted the cashier's
			// chosen showroom account back to the profile default (see
			// canEditPaymentAccount / get_invoice_doc's payment_account wiring).
			this.paymentAccountOverride =
				this.uiStore.activeSaleAccount || data.pos_profile?.account_for_change_amount || null;
			this.uiStore.setActiveSaleAccount(this.paymentAccountOverride);
			if (this.canEditPaymentAccount) {
				// this.company (set above from data.company, i.e.
				// uiStore.companyDoc) is a whole Company *document*, not its
				// name -- get_cash_in_hand_accounts expects the company name
				// string, which only the POS Profile itself reliably carries
				// here; passing the document silently matched zero accounts.
				this.loadCashInHandAccounts(data.pos_profile?.company);
			}
		},
		async loadCashInHandAccounts(company) {
			if (!company || !this.canEditPaymentAccount) {
				this.cashAccountOptions = [];
				return;
			}
			this.cashAccountsLoading = true;
			try {
				const accounts = await frappe.call({
					method: "posawesome.posawesome.api.payment_processing.utils.get_cash_in_hand_accounts",
					args: { company },
				});
				this.cashAccountOptions = accounts.message || [];
			} catch (error) {
				console.error("Error loading Cash In Hand accounts:", error);
				this.cashAccountOptions = [];
			} finally {
				this.cashAccountsLoading = false;
			}
		},
		async refresh_parked_orders() {
			if (!this.pos_profile || !this.pos_opening_shift?.name) {
				this.uiStore.setParkedOrders([]);
				return;
			}

			try {
				const drafts = await fetchDraftInvoices({
					posOpeningShift: this.pos_opening_shift,
					posProfile: this.pos_profile,
				});
				this.uiStore.setParkedOrders(drafts);
			} catch (error) {
				console.error("Error refreshing parked orders:", error);
			}
		},
		handleClearInvoice() {
			this.clear_invoice();
			this.remarks = "";
			this.uiStore.triggerItemSearchFocus();
		},
		handleLoadInvoice(data) {
			this.remarks = data?.remarks || "";
			this.load_invoice(data, { preserveStickies: true });
		},
		handleLoadOrder(data) {
			this.new_order(data);
		},
		handleLoadFlow(flow) {
			if (!flow?.prepared_doc) {
				return;
			}

			this.invoiceStore.setFlowContext?.(flow.flow_context || null);
			const action = flow?.action || flow?.flow_context?.prepared_action;
			const targetDoctype = flow?.flow_context?.target_doctype || flow?.prepared_doc?.doctype || "";

			if (targetDoctype === "Quotation" || action === "quote_edit_draft") {
				this.invoiceType = "Quotation";
				this.invoiceTypes = ["Invoice", "Order", "Quotation"];
			} else if (
				targetDoctype === "Sales Order" ||
				action === "order_load" ||
				action === "quote_to_order"
			) {
				this.invoiceType = "Order";
				this.invoiceTypes = ["Invoice", "Order", "Quotation"];
			} else {
				this.invoiceType = "Invoice";
				this.invoiceTypes = ["Invoice", "Order", "Quotation"];
			}

			this.load_invoice(flow.prepared_doc, { preserveStickies: true });
		},

		calcProratedReturnDiscount(returnDoc) {
			if (!returnDoc) return 0;

			const originalDiscount = Math.abs(Number(returnDoc.discount_amount || 0));
			if (!originalDiscount) return 0;

			const originalTotal = Math.abs(
				Number(returnDoc.total ?? returnDoc.net_total ?? returnDoc.grand_total ?? 0),
			);
			if (!originalTotal) return 0;

			const returnTotal = Math.abs(Number(this.Total || 0));
			if (!returnTotal) return 0;

			const ratio = Math.min(1, returnTotal / originalTotal);
			const prorated = originalDiscount * ratio;
			console.log("[POSA][Returns] Prorate discount", {
				originalDiscount,
				originalTotal,
				returnTotal,
				ratio,
				prorated,
			});
			return -Math.abs(prorated);
		},

		handleSetAllItems(data) {
			this.allItems = data;
			this.items.forEach((item) => {
				if (item._detailSynced !== true) {
					this.update_item_detail(item);
				}
			});
			this.primeInvoiceStockState();
		},
		handleLoadReturnInvoice(data) {
			this.load_invoice(data.invoice_doc);
			this.invoiceType = "Return";
			this.invoiceTypes = ["Return"];
			this.invoice_doc.is_return = 1;
			if (Array.isArray(this.invoice_doc.payments)) {
				this.invoice_doc.payments.forEach((payment) => {
					const amount = this.flt(payment.amount || 0, this.currency_precision);
					payment.amount = amount ? -Math.abs(amount) : 0;
					if (payment.base_amount !== undefined) {
						const baseAmount = this.flt(payment.base_amount || 0, this.currency_precision);
						payment.base_amount = baseAmount ? -Math.abs(baseAmount) : 0;
					}
				});
			}
			if (this.items && this.items.length) {
				this.items.forEach((item) => {
					if (item.qty > 0) item.qty = -Math.abs(item.qty);
					if (item.stock_qty > 0) item.stock_qty = -Math.abs(item.stock_qty);
				});
			}
			if (data.return_doc) {
				this.return_doc = data.return_doc;
				this.invoice_doc.return_against = data.return_doc.name;
				this.return_discount_base_amount = Math.abs(Number(data.return_doc.discount_amount || 0));
				this.return_discount_base_total = Math.abs(
					Number(
						data.return_doc.total ??
							data.return_doc.net_total ??
							data.return_doc.grand_total ??
							0,
					),
				);
				console.log("[POSA][Returns] Loaded return doc", {
					return_against: data.return_doc.name,
					is_percentage: !!this.pos_profile?.posa_use_percentage_discount,
					discount_amount: data.return_doc.discount_amount,
					discount_percentage: data.return_doc.additional_discount_percentage,
					original_total:
						data.return_doc.total ?? data.return_doc.net_total ?? data.return_doc.grand_total,
					base_total: this.return_discount_base_total,
					base_discount: this.return_discount_base_amount,
				});

				if (this.pos_profile?.posa_use_percentage_discount) {
					if (data.return_doc.additional_discount_percentage !== undefined) {
						this.additional_discount_percentage = this.flt(
							data.return_doc.additional_discount_percentage || 0,
							this.float_precision,
						);
					}
					this.update_discount_umount();
				} else {
					const prorated = this.calcProratedReturnDiscount(data.return_doc);
					this.discount_amount = prorated;
					this.additional_discount = prorated;
					this.additional_discount_percentage = 0;
				}
			} else {
				this.discount_amount = 0;
				this.additional_discount = 0;
				this.additional_discount_percentage = 0;
			}
		},
		handleSetNewLine(data) {
			this.new_line = data;
		},
		handleShowPaymentRequest() {
			this.show_payment();
		},
		async resume_parked_order(draft) {
			try {
				const message = await this.load_draft_source_record(draft);
				if (message) {
					this.uiStore?.closeDrafts?.();
				}
			} catch (error) {
				console.error("Error loading parked order:", error);
				this.toastStore.show({
					title: __("Unable to load parked order"),
					color: "error",
				});
			}
		},
		handleOpenCustomerDisplayRequest() {
			if (this.eventBus && typeof this.eventBus.emit === "function") {
				this.eventBus.emit("open_customer_display");
			}
		},
		promptPriceListRate(initialRate, item) {
			if (typeof this.price_list_rate_dialog_resolver === "function") {
				this.price_list_rate_dialog_resolver(null);
			}

			this.price_list_rate_dialog_initial_rate = initialRate == null ? "" : String(initialRate);
			this.price_list_rate_dialog_item_label = String(item?.item_name || item?.item_code || "");
			this.price_list_rate_dialog_open = true;

			return new Promise((resolve) => {
				this.price_list_rate_dialog_resolver = resolve;
			});
		},
		handlePriceListRateDialogCancel() {
			if (typeof this.price_list_rate_dialog_resolver === "function") {
				this.price_list_rate_dialog_resolver(null);
			}
			this.price_list_rate_dialog_open = false;
			this.price_list_rate_dialog_initial_rate = "";
			this.price_list_rate_dialog_item_label = "";
			this.price_list_rate_dialog_resolver = null;
		},
		handlePriceListRateDialogSubmit(value) {
			if (typeof this.price_list_rate_dialog_resolver === "function") {
				this.price_list_rate_dialog_resolver(value);
			}
			this.price_list_rate_dialog_open = false;
			this.price_list_rate_dialog_initial_rate = "";
			this.price_list_rate_dialog_item_label = "";
			this.price_list_rate_dialog_resolver = null;
		},
	},

	async mounted() {
		this.setUpdateItemDetail(this.update_item_detail);
		await this.loadColumnPreferences();
		this.loadInvoiceHeight();
		this.fetchWarehouses();

		this.$watch(
			() => this.uiStore.posProfile,
			(profile) => {
				if (profile && profile.name) {
					this.handleRegisterPosProfile({
						pos_profile: profile,
						stock_settings: this.uiStore.stockSettings,
						company: this.uiStore.companyDoc,
						pos_opening_shift: this.uiStore.posOpeningShift,
					});
				}
			},
			{ deep: true, immediate: true },
		);

		this.$watch(
			() => this.uiStore.offers,
			(offers) => {
				if (offers) {
					this.handleSetOffers(offers);
				}
			},
			{ deep: true, immediate: true },
		);

		this.$watch(
			() => this.invoiceStore.invoiceToLoad,
			(doc) => {
				if (doc) {
					this.handleLoadInvoice(doc);
				}
			},
			{ deep: false },
		);

		this.$watch(
			() => this.invoiceStore.orderToLoad,
			(doc) => {
				if (doc) {
					this.handleLoadOrder(doc);
				}
			},
			{ deep: false },
		);

		this.$watch(
			() => this.invoiceStore.flowToLoad,
			(flow) => {
				if (flow?.prepared_doc) {
					this.handleLoadFlow(flow);
				} else if (flow) {
					this.handleLoadFlow({
						action: this.invoiceStore.flowContext?.prepared_action,
						prepared_doc: flow,
						flow_context: this.invoiceStore.flowContext,
					});
				}
			},
			{ deep: false },
		);

		this.$watch(
			() => this.uiStore.draggedItem,
			(item) => {
				this.showDropFeedback(!!item, this.itemsTableRef);
			},
		);

		this.$watch(
			() => this.invoiceStore.postingDate,
			(val) => {
				if (val) this.posting_date = val;
			},
			{ immediate: true },
		);

		this._busHandlers = {
			focus_invoice_catalog_search: this.focusInvoiceCatalogSearchField,
			add_item: this.add_item,
			clear_invoice: this.handleClearInvoice,
			apply_pricing_rules: () => {
				if (typeof this.schedulePricingRuleApplication === "function") {
					this.schedulePricingRuleApplication();
				}
			},
			update_invoice_offers: this.handleUpdateInvoiceOffers,
			update_invoice_coupons: this.handleUpdateInvoiceCoupons,
			set_all_items: this.handleSetAllItems,
			load_return_invoice: this.handleLoadReturnInvoice,
			set_new_line: this.handleSetNewLine,
			calc_uom: this.calc_uom,
			recalculate_return_discount: (payload) => this.applyReturnDiscountProration(payload),
			reset_invoice_type_to_invoice: () => {
				this.invoiceType = "Invoice";
				this.invoiceTypes = ["Invoice", "Order", "Quotation"];
			},
		};

		Object.entries(this._busHandlers).forEach(([eventName, handler]) => {
			this.eventBus.on(eventName, handler);
		});

		this.stockUnsubscribe = stockCoordinator.subscribe(this.handleStockCoordinatorUpdate);

		this.emitCartQuantities();
		this.$nextTick(() => {
			this.primeInvoiceStockState();
		});
	},
	beforeUnmount() {
		if (typeof this.price_list_rate_dialog_resolver === "function") {
			this.price_list_rate_dialog_resolver(null);
			this.price_list_rate_dialog_resolver = null;
		}

		if (typeof this.stockUnsubscribe === "function") {
			this.stockUnsubscribe();
			this.stockUnsubscribe = null;
		}

		Object.entries(this._busHandlers || {}).forEach(([eventName, handler]) => {
			this.eventBus.off(eventName, handler);
		});
		this._busHandlers = {};
		if (typeof this.cancelScheduledOfferRefresh === "function") {
			this.cancelScheduledOfferRefresh();
		}
		if (this._suppressClosePaymentsTimer) {
			clearTimeout(this._suppressClosePaymentsTimer);
			this._suppressClosePaymentsTimer = null;
		}
	},
	created() {
		this.invoiceStore.clear();
		// Hold the item selector's first catalog load until fetchWarehouses()
		// resolves the cashier's real warehouse (see itemsStore). Invoice is
		// created before ItemsSelector in Pos.vue, so this runs first.
		this.itemsStore?.beginWarehouseResolution?.();
		this.$watch(
			() => this.selectedCustomer,
			(newCustomer) => {
				if (newCustomer) {
					if (this.customer !== newCustomer) {
						this.customer = newCustomer;
					}
				} else if (this.customer) {
					this.customer = "";
				}
			},
			{ immediate: true },
		);
		this.$watch(
			() => this.customerRefreshToken,
			() => {
				if (this.customer) {
					this.fetch_customer_details();
				}
			},
		);
		this._shortcutHandlers = this._shortcutHandlers || {};

		this._shortcutHandlers.handleInvoiceShortcut = createInvoiceShortcutListeners(
			this.handleInvoiceShortcut.bind(this),
		);
		registerInvoiceShortcutListener(document, this._shortcutHandlers.handleInvoiceShortcut);
	},
	unmounted() {
		if (!this._shortcutHandlers) {
			return;
		}

		unregisterInvoiceShortcutListener(document, this._shortcutHandlers.handleInvoiceShortcut);

		this._shortcutHandlers = {};
	},
	watch: {
		...invoiceWatchers,
		// A new cart line on a short screen (installed app window, laptop)
		// was added below the fold -- under the customer / DO / accounts
		// cards -- so the cashier couldn't see its qty or change it. Bring
		// the cart into view when the line count grows and it isn't visible.
		"items.length"(count, previous) {
			if (count > (previous || 0)) {
				this.$nextTick(() => this.scrollCartIntoView({ onlyIfHidden: true }));
			}
		},
		sale_update_stock: {
			immediate: true,
			handler(val) {
				// Mirror the toggle into invoiceStore so ItemsSelector/scan can
				// skip stock-availability checks entirely while it's off - this
				// sale won't touch the stock ledger, so there's nothing to block.
				this.invoiceStore.setUpdateStock(val);
			},
		},
		"invoiceStore.invoiceDoc"(doc) {
			// invoiceDoc only comes into existence once the first item lands in
			// the cart (see the custom_do_number getter/setter above) — if a DO
			// Number was already typed before that (through any path, not just
			// handleDoNumberLookup), it only ever reached the local
			// doNumberDraft echo. Carry it over as soon as there's a real doc
			// to put it on, so it isn't silently lost by save time.
			if (doc && this.doNumberDraft && !doc.custom_do_number) {
				doc.custom_do_number = this.doNumberDraft;
			}
		},
		confirm_payment_dialog(val) {
			if (val) {
				this.$nextTick(() => {
					setTimeout(() => {
						this.$refs.paymentConfirmationDialog?.focus?.();
					}, 100);
				});
			}
		},
		// Keep every other "Accounts" picker (standalone Payment screen, Expense
		// Claim, Purchase Order) in sync with whatever a System Manager / BSP
		// Admin picks here -- see handleRegisterPosProfile for the read side.
		paymentAccountOverride(val) {
			this.uiStore.setActiveSaleAccount(val);

			// invoiceStore.invoiceDoc is a *cached* snapshot -- built once via
			// get_invoice_doc() when the cart first gets an item, then only
			// re-synced on further item changes (see invoice_utils/server.ts's
			// debounced sync). It's also what the PAY dialog (Payments.vue,
			// via usePaymentSubmission's invoiceDoc prop) actually submits --
			// not a fresh get_invoice_doc() call. Picking a different Accounts
			// override *after* the cart already has items, with no further
			// item edits before hitting PAY, left that cached snapshot's
			// payment_account pointing at whatever was selected (or nothing)
			// when the doc was last synced -- the dropdown looked right, but
			// the submitted payment still went to the old account. Push the
			// new value into the cached doc directly so it can never lag
			// behind what the dropdown shows.
			if (this.invoiceStore.invoiceDoc) {
				this.invoiceStore.setInvoiceDoc({
					...this.invoiceStore.invoiceDoc,
					payment_account: this.canEditPaymentAccount && val ? val : null,
				});
			}
		},
	},
};
</script>

<style scoped>
/* Card background adjustments */
.cards {
	background-color: var(--pos-surface-muted) !important;
}

.invoice-shell {
	display: flex;
	flex-direction: column;
	gap: 0;
	flex: 1 1 auto;
	min-height: 0;
	height: 100%;
	overflow: hidden;
}

@media (max-width: 1099px) {
	.invoice-shell {
		padding-bottom: calc(var(--bottom-safe-space) + var(--dynamic-xs));
		height: auto;
		overflow: visible;
	}
}

.invoice-main-card {
	display: flex;
	flex-direction: column;
	flex: 1 1 auto;
	overflow: hidden !important;
	min-width: 0;
	min-height: 0;
	margin-top: 0 !important;
}

.invoice-main-scroll {
	flex: 1 1 auto;
	min-height: 0;
	overflow: auto;
}

/* .dynamic-padding (below) also sets "overflow: visible" and has the same
   specificity as .invoice-main-scroll above -- on the element carrying both
   classes, whichever rule is later in the file silently wins the tie, which
   was cancelling out this "auto" and leaving the invoice content area
   permanently non-scrollable at desktop widths. The compound selector here
   outranks both single-class rules regardless of source order. */
.dynamic-padding.invoice-main-scroll {
	overflow: auto;
}

.invoice-summary-dock {
	flex: 0 0 auto;
	width: 100%;
	padding: 0 var(--dynamic-sm) var(--dynamic-sm);
}

.invoice-summary-dock :deep(.sticky-summary-card) {
	position: relative;
	bottom: auto;
	margin-bottom: 0;
	box-shadow: 0 -4px 16px var(--pos-shadow-light, rgba(15, 23, 42, 0.08));
}

/* Style for selected checkbox button */
.v-checkbox-btn.v-selected {
	background-color: var(--submit-start) !important;
	color: white;
}

/* Bottom border for elements */
.border_line_bottom {
	border-bottom: 1px solid var(--field-border);
}

/* Disable pointer events for elements */
.disable-events {
	pointer-events: none;
}

/* Style for customer balance field */
:deep(.balance-field) {
	display: flex;
	align-items: center;
	justify-content: flex-end;
	flex-wrap: nowrap;
}

/* Style for balance value text */
:deep(.balance-value) {
	font-size: 1.5rem;
	font-weight: bold;
	color: var(--primary-start);
	margin-left: var(--dynamic-xs);
}

/* Red border and label for return mode card */

/* Red border and label for return mode card */

.return-mode {
	border: 2px solid rgb(var(--v-theme-error)) !important;
	position: relative;
}

/* Label for return mode card */
.return-mode::before {
	content: "RETURN";
	position: absolute;
	top: 0;
	right: 0;
	background-color: rgb(var(--v-theme-error));
	color: white;
	padding: 4px 12px;
	font-weight: bold;
	border-bottom-left-radius: 8px;
	z-index: 1;
}

/* Dynamic padding for responsive layout */
.dynamic-padding {
	/* Uniform spacing for better alignment */
	padding: var(--dynamic-sm);
	display: flex;
	flex-direction: column;
	gap: var(--dynamic-sm);
	flex: 1 1 auto;
	min-height: 0;
	overflow: visible;
}

.invoice-status-alert {
	border-radius: 14px;
	flex: 0 0 auto;
}

.invoice-sections {
	display: flex;
	flex-direction: column;
	gap: var(--dynamic-sm);
	flex: 1 1 auto;
	min-height: 0;
	overflow: visible;
	align-items: stretch;
}

.invoice-sale-header,
.create-header-card {
	flex: 0 0 auto;
	container-type: inline-size;
	container-name: txn-form;
	min-width: 0;
}

.create-header {
	display: flex;
	flex-direction: column;
	gap: 8px;
	padding: 10px 12px 12px;
	min-width: 0;
}

.create-header__grid {
	display: grid;
	grid-template-columns: minmax(0, 1fr);
	gap: 8px 10px;
	align-items: center;
	min-width: 0;
}

.create-header__party,
.create-header__metric,
.create-header__field,
.create-header__delivery,
.create-header__toggles {
	min-width: 0;
}

.create-header__party :deep(.sale-customer-row),
.create-header__party :deep(.v-col),
.create-header__party :deep(.customer-input-wrapper),
.create-header__party :deep(.customer-field-shell),
.create-header__party :deep(.customer-autocomplete) {
	width: 100%;
	max-width: none;
}

.create-header__metric-field :deep(input) {
	font-weight: 700;
	font-variant-numeric: tabular-nums;
	text-align: end;
}

.create-header__metric-field--due :deep(input) {
	color: rgb(var(--v-theme-error)) !important;
}

.create-header__metric-field--clear :deep(input) {
	color: rgb(var(--v-theme-success)) !important;
}

.create-header__toggles {
	display: flex;
	flex-wrap: wrap;
	align-items: center;
	gap: 4px 14px;
	padding: 2px 0;
}

.create-header__toggles :deep(.v-label) {
	white-space: nowrap !important;
}

.create-header__span-all {
	grid-column: 1 / -1;
}

@container txn-form (min-width: 460px) {
	.create-header__grid {
		grid-template-columns: repeat(2, minmax(0, 1fr));
	}

	.create-header__toggles,
	.create-header__span-all {
		grid-column: 1 / -1;
	}
}

.remarks-section-card .sale-header__remarks-body {
	padding: 8px 12px 12px;
}

.create-header :deep(.posting-date-row) {
	margin: 0;
}

.create-header :deep(.posting-date-input),
.create-header :deep(.posting-date-input.mb-2) {
	margin-bottom: 0 !important;
}

.create-header :deep(.sleek-field.mb-2) {
	margin-bottom: 0 !important;
}

.invoice-section-card {
	background: var(--pos-card-bg) !important;
	border: 1px solid rgba(var(--v-theme-on-surface), 0.08);
	border-radius: var(--pos-radius-md, 18px);
	box-shadow: 0 10px 30px rgba(15, 23, 42, 0.05);
	overflow: hidden;
	flex: 0 0 auto;
	min-height: fit-content;
}

.invoice-section-heading {
	padding: 12px 14px 0;
}

.invoice-section-heading__title {
	margin: 0;
	font-size: 0.95rem;
	font-weight: 700;
	line-height: 1.25;
	color: var(--pos-text-primary);
}

.invoice-items-card {
	padding-bottom: var(--dynamic-xs);
	display: flex;
	flex-direction: column;
	flex: 0 0 auto;
	min-height: 320px;
	overflow: visible;
}

/* Responsive breakpoints — match Purchase: full fields visible under 1100 */
@media (max-width: 1099px) {
	.invoice-shell {
		gap: var(--dynamic-xs);
		height: auto;
		overflow: visible;
	}

	.invoice-main-card {
		height: auto !important;
		max-height: none !important;
		resize: none !important;
		overflow: visible !important;
		flex: 0 0 auto !important;
	}

	.invoice-main-scroll,
	.dynamic-padding.invoice-main-scroll {
		/* !important: the unconditional .dynamic-padding.invoice-main-scroll
		   compound rule above (higher specificity, no media query) would
		   otherwise win here too and force "auto" back on, undoing the
		   intentional page-scroll behavior this compact breakpoint relies on. */
		overflow: visible !important;
		flex: 0 0 auto;
	}

	.invoice-summary-dock {
		padding: 0 var(--dynamic-xs) var(--dynamic-xs);
	}

	.dynamic-padding {
		padding: var(--dynamic-xs);
		overflow: visible;
	}

	.create-header {
		padding: 8px 10px 10px;
		gap: 8px;
	}

	.invoice-sections {
		overflow: visible;
	}

	.invoice-items-card {
		flex: 0 0 auto;
		min-height: 240px;
		padding-bottom: calc(var(--bottom-safe-space) + 8px);
	}

	.items-table-wrapper {
		margin-left: 0;
		margin-right: 0;
		width: 100%;
		max-width: 100%;
		min-height: 220px;
		padding-bottom: 8px;
	}

	.item-search-field {
		max-width: 100%;
	}

	.invoice-section-heading {
		padding: 10px 12px 0;
	}

	.invoice-section-heading__title {
		font-size: 0.92rem;
	}
}

@media (max-width: 768px) {
	.invoice-shell {
		gap: var(--dynamic-xs);
	}

	.dynamic-padding .v-row {
		margin: 0 -2px;
	}

	.dynamic-padding .v-col {
		padding: 2px 4px;
	}

	.items-table-wrapper {
		min-height: 280px;
	}
}

@media (max-width: 480px) {
	.invoice-main-card {
		margin-top: var(--dynamic-xs) !important;
	}

	.dynamic-padding {
		padding: var(--dynamic-xs);
	}

	.dynamic-padding .v-row {
		margin: 0 -1px;
	}

	.dynamic-padding .v-col {
		padding: 1px 2px;
	}

	.items-table-wrapper {
		margin-left: 0;
		margin-right: 0;
		width: 100%;
		max-width: 100%;
		min-height: 240px;
	}

	.item-search-field {
		flex-basis: 100%;
		max-width: 100%;
		margin-right: 0;
	}
}

.column-selector-container {
	display: flex;
	align-items: center;
	justify-content: flex-end;
	flex-wrap: wrap;
	gap: 8px;
	padding: 8px 16px;
	background-color: var(--pos-card-bg);
	border-radius: 12px 12px 0 0;
	box-sizing: border-box;
	margin-bottom: 8px;
}

.item-search-field {
	width: 100%;
	max-width: 320px;
	flex: 1 1 240px;
	margin-right: auto;
}

.column-selector-btn {
	font-size: 0.875rem;
}

.items-table-wrapper {
	position: relative;
	margin-top: var(--dynamic-sm);
	width: 100%;
	max-width: 100%;
	box-sizing: border-box;
	display: flex;
	flex-direction: column;
	flex: 0 0 auto;
	min-height: 320px;
	min-width: 0;
}

:deep(.items-table-wrapper .column-selector-container) {
	position: sticky;
	top: 0;
	z-index: 3;
	background: var(--pos-card-bg);
}

:deep(.items-table-wrapper .posa-items-table-container) {
	flex: 0 0 auto;
	min-height: 320px;
	height: auto !important;
	max-height: none !important;
	overflow: visible !important;
}

:deep(.items-table-wrapper .posa-cart-table),
:deep(.items-table-wrapper .v-data-table__wrapper),
:deep(.items-table-wrapper .v-table__wrapper) {
	height: auto !important;
	max-height: none !important;
}

/* New styles for improved column switches */
:deep(.column-switch) {
	margin: 0;
	padding: 0;
}

:deep(.column-switch .v-switch__track) {
	opacity: 0.7;
}

:deep(.column-switch .v-switch__thumb) {
	transform: scale(0.8);
}

:deep(.column-switch .v-label) {
	opacity: 0.9;
	font-size: 0.95rem;
}

.sale-opt-switch {
	flex: 0 0 auto;
	min-width: max-content;
}
</style>
