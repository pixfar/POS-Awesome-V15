<template>
	<div class="pa-0 h-100 payment-shell invoice-shell txn-shell" :style="responsiveStyles">
		<v-row class="h-100 ma-0">

			<!-- LEFT: Party selector · Outstanding invoices · History -->
			<v-col
				v-show="showInvoicePanel"
				cols="12"
				:md="invoiceCols"
				class="h-100 pa-0 txn-col txn-col--invoice"
			>
				<v-card class="h-100 d-flex flex-column pos-themed-card payment-invoice-card" flat>
					<v-card-text class="flex-grow-1 d-flex flex-column pa-3 pa-md-4 payment-main-body">
						<div class="payment-content">

							<div class="invoice-top-grid payment-top-grid">

								<!-- Party selector -->
								<v-card flat class="invoice-section-card pos-themed-card">
									<div class="invoice-section-heading">
										<h3 class="invoice-section-heading__title">
											{{ partyType === "Customer"
												? __("Customer Details")
												: __("Supplier Details") }}
										</h3>
									</div>
									<div class="payment-party-body">
										<Customer v-if="partyType === 'Customer'" />
										<v-autocomplete
											v-else
											v-model="partyName"
											v-model:search="partySearchText"
											:items="partyOptions"
											:loading="partyLoading"
											item-title="supplier_name"
											item-value="name"
											:label="__('Supplier')"
											density="comfortable"
											variant="solo"
											color="primary"
											hide-details
											clearable
											no-filter
											:custom-filter="() => true"
											class="sleek-field pos-themed-input"
											@update:search="onPartySearch"
											@update:model-value="onSupplierSelected"
										/>
									</div>
								</v-card>

								<!-- Outstanding badge -->
								<v-card flat class="invoice-section-card pos-themed-card outstanding-panel">
									<div class="outstanding-panel__inner">
										<div class="outstanding-panel__label">{{ __("Outstanding") }}</div>
										<div
											class="outstanding-panel__amount"
											:class="partyName && totalOutstanding > 0
												? 'outstanding-panel__amount--due'
												: 'outstanding-panel__amount--clear'"
										>
											{{ partyName ? `${currencySymbol()}${formatAmt(totalOutstanding)}` : "—" }}
										</div>
										<v-icon
											v-if="partyName"
											:color="totalOutstanding > 0 ? 'error' : 'success'"
											size="22"
											class="outstanding-panel__icon"
										>
											{{ totalOutstanding > 0 ? "mdi-alert-circle" : "mdi-check-circle" }}
										</v-icon>
									</div>
								</v-card>

								<!-- Date + auto-allocate + accounts override -->
								<v-card flat class="invoice-section-card pos-themed-card sale-options-card">
									<div v-if="canEditPaymentAccount" class="invoice-section-heading">
										<h3 class="invoice-section-heading__title">{{ __("Date & Accounts") }}</h3>
									</div>
									<div class="sale-options-body">
										<VueDatePicker
											v-model="postingDateDisplay"
											model-type="format"
											format="dd-MM-yyyy"
											auto-apply
											teleport
											:placeholder="__('Posting Date')"
											class="sleek-field posting-date-input pos-themed-input mb-2"
										/>
										<v-switch
											v-model="autoAllocate"
											density="compact"
											hide-details
											color="primary"
											:label="__('Auto Allocate')"
											class="sale-opt-switch"
										/>
										<v-autocomplete
											v-if="canEditPaymentAccount"
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
											class="pos-themed-input mt-2"
										/>
									</div>
								</v-card>
							</div>

							<div class="payment-tables-stack">

							<!-- Outstanding invoices table -->
							<v-card flat class="invoice-section-card pos-themed-card payment-table-card payment-table-card--split">
								<div class="invoice-section-heading invoice-section-heading--toolbar">
									<h3 class="invoice-section-heading__title">
										{{ __("Outstanding Invoices") }}
									</h3>
									<div class="invoice-section-heading__actions">
										<span
											v-if="invoicesTotal"
											class="text-caption text-medium-emphasis mr-2"
										>
											{{ invoicesTotal }} {{ __("Outstanding Invoices") }}
										</span>
										<span
											v-if="selected_invoices.length"
											class="text-caption text-primary mr-2"
										>
											{{ selected_invoices.length }} {{ __("selected") }}
											· {{ currencySymbol() }}{{ formatAmt(total_selected_invoices) }}
										</span>
										<v-btn
											v-if="selected_invoices.length"
											variant="text"
											size="small"
											color="error"
											@click="clearSelections"
										>{{ __("Clear") }}</v-btn>
										<v-btn
											variant="text"
											size="small"
											color="primary"
											:loading="invoices_loading"
											prepend-icon="mdi-sync"
											@click="syncData"
										>{{ __("Sync") }}</v-btn>
									</div>
								</div>
								<div
									ref="invoicesScrollRef"
									class="payment-table-scroll payment-table-body"
									@scroll="onInvoicesScroll"
								>
								<v-data-table
									:headers="invoiceHeaders"
									:items="outstanding_invoices"
									:loading="invoices_loading"
									density="compact"
									fixed-header
									hide-default-footer
									:items-per-page="-1"
									:no-data-text="__('No outstanding invoices')"
									:row-props="({ item }) => ({
										class: invoiceRowClass(item),
										style: 'cursor:pointer',
									})"
									@click:row="(_, row) => handleInvoiceClick(row.item)"
									item-value="_row_key"
									class="payment-invoices-table"
								>
									<template #item.sel="{ item }">
										<v-icon
											:color="isInvoiceSelected(item) ? 'primary' : 'grey-lighten-2'"
											size="18"
										>
											{{ isInvoiceSelected(item)
												? "mdi-checkbox-marked-circle"
												: "mdi-checkbox-blank-circle-outline" }}
										</v-icon>
									</template>
									<template #item.voucher_no="{ item }">
										<span class="text-caption font-weight-medium">{{ item.voucher_no }}</span>
									</template>
									<template #item.party_name="{ item }">
										<span class="text-caption">{{ item.party_name || item.party }}</span>
									</template>
									<template #item.posting_date="{ item }">
										<span class="text-caption">{{ item.posting_date }}</span>
									</template>
									<template #item.outstanding_amount="{ item }">
										<strong class="text-error">
											{{ currencySymbol(item.currency) }}{{ formatAmt(item.outstanding_amount) }}
										</strong>
									</template>
								</v-data-table>
								<div v-if="invoicesLoadingMore" class="text-center py-2 text-caption">
									<v-progress-circular indeterminate size="16" width="2" />
								</div>
								<div ref="invoicesSentinel" class="payment-scroll-sentinel" />
								</div>
							</v-card>

							<!-- Payment entry history -->
							<v-card flat class="invoice-section-card pos-themed-card payment-table-card payment-table-card--split">
								<div class="invoice-section-heading invoice-section-heading--toolbar">
									<h3 class="invoice-section-heading__title">{{ __("Payment History") }}</h3>
									<div class="invoice-section-heading__actions">
										<v-btn
											variant="text"
											size="small"
											color="primary"
											:loading="historyLoading"
											prepend-icon="mdi-sync"
											@click="syncData"
										>{{ __("Sync") }}</v-btn>
									</div>
								</div>
								<div
									ref="historyScrollRef"
									class="payment-table-scroll payment-table-body"
									@scroll="onHistoryScroll"
								>
								<v-data-table
									:headers="historyHeaders"
									:items="paymentHistory"
									:loading="historyLoading"
									density="compact"
									fixed-header
									hide-default-footer
									:items-per-page="-1"
									:no-data-text="partyName
										? __('No payment history')
										: __('Select a party to see payment history')"
									class="payment-history-table"
								>
									<template #item.posting_date="{ item }">
										<span class="text-caption">{{ item.posting_date }}</span>
									</template>
									<template #item.paid_amount="{ item }">
										<strong>{{ currencySymbol() }}{{ formatAmt(item.paid_amount) }}</strong>
									</template>
									<template #item.allocated_amount="{ item }">
										<span class="text-caption">
											{{ currencySymbol() }}{{ formatAmt(item.allocated_amount) }}
										</span>
									</template>
									<template #item.payment_type="{ item }">
										<span class="text-caption">{{ item.payment_type }}</span>
									</template>
									<template #item.reference_no="{ item }">
										<span class="text-caption text-truncate payment-ref-no">
											{{ item.reference_no || "—" }}
										</span>
									</template>
									<template #item.name="{ item }">
										<span class="text-caption text-primary">{{ item.name }}</span>
									</template>
								</v-data-table>
								<div v-if="historyLoadingMore" class="text-center py-2 text-caption">
									<v-progress-circular indeterminate size="16" width="2" />
								</div>
								<div ref="historySentinel" class="payment-scroll-sentinel" />
								</div>
							</v-card>

							</div>

						</div>
					</v-card-text>

					<!-- Bottom action bar -->
					<div v-if="!isCompact" class="purchase-bottom-bar">
						<div class="purchase-bottom-bar__summary">
							<span class="purchase-bottom-bar__label">{{ __("Selected Total") }}</span>
							<strong class="purchase-bottom-bar__amount">
								{{ currencySymbol() }}{{ formatAmt(total_selected_invoices) }}
							</strong>
							<span class="purchase-bottom-bar__meta">
								<template v-if="selected_invoices.length">
									{{ selected_invoices.length }}
									{{ selected_invoices.length === 1 ? __("invoice") : __("invoices") }}
								</template>
								<template v-else>{{ __("No invoices selected") }}</template>
							</span>
						</div>
						<v-btn
							:loading="isSubmitting"
							:disabled="isSubmitting || !canSubmit"
							size="large"
							class="text-none purchase-pay-btn"
							prepend-icon="mdi-cash-check"
							@click="handleSubmit(false)"
						>
							{{ __("PAY") }}
						</v-btn>
					</div>
				</v-card>
			</v-col>

			<!-- RIGHT: clicked invoice · payment form -->
			<v-col
				v-show="showSelectorPanel"
				cols="12"
				:md="selectorCols"
				class="h-100 pa-0 border-s txn-col txn-col--selector"
			>
				<v-card class="h-100 d-flex flex-column pos-themed-card payment-side-card" flat>
					<div class="payment-side-body">
						<section
							class="payment-invoice-preview"
							:class="{ 'payment-invoice-preview--empty': !previewInvoice }"
						>
							<template v-if="previewInvoice">
								<div class="invoice-section-heading">
									<h3 class="invoice-section-heading__title">{{ previewInvoice.voucher_no }}</h3>
									<span class="text-caption text-medium-emphasis">
										{{ previewInvoice.party_name || previewInvoice.party }}
									</span>
								</div>
								<div v-if="previewLoading" class="payment-preview-status">
									<v-progress-circular indeterminate size="22" color="primary" />
									<span>{{ __("Loading invoice...") }}</span>
								</div>
								<div v-else-if="previewError" class="payment-preview-status text-error">
									{{ previewError }}
								</div>
								<InvoiceExpandedDetail
									v-else-if="previewDetail"
									:detail="previewDetail"
									variant="invoice"
									:currency-symbol="currencySymbol(previewDetail.currency)"
									:format-currency="formatAmt"
								/>
								<div v-else class="payment-preview-fallback">
									<div>
										<strong>{{ __("Date") }}:</strong>
										{{ previewInvoice.posting_date || "—" }}
									</div>
									<div>
										<strong>{{ __("Due Date") }}:</strong>
										{{ previewInvoice.due_date || "—" }}
									</div>
									<div>
										<strong>{{ __("Outstanding") }}:</strong>
										{{ currencySymbol(previewInvoice.currency) }}{{ formatAmt(previewInvoice.outstanding_amount) }}
									</div>
								</div>
							</template>
							<span v-else>{{ __("Click an invoice to see its details") }}</span>
						</section>

						<v-card flat class="invoice-section-card pos-themed-card payment-form-card">
							<div class="payment-form-scroll">
							<div class="payment-form-top">
							<div>
							<div class="invoice-section-heading payment-form-heading">
								<h3 class="invoice-section-heading__title">{{ __("Summary") }}</h3>
							</div>
							<div class="payment-summary-list">
								<div class="payment-summary-row">
									<span class="payment-summary-row__label">{{ __("Total Outstanding") }}</span>
									<strong class="payment-summary-row__val text-error">
										{{ currencySymbol() }}{{ formatAmt(totalOutstanding) }}
									</strong>
								</div>
								<div class="payment-summary-row">
									<span class="payment-summary-row__label">{{ __("Selected Invoices") }}</span>
									<strong class="payment-summary-row__val text-primary">
										{{ currencySymbol() }}{{ formatAmt(total_selected_invoices) }}
									</strong>
								</div>
								<div class="payment-summary-row">
									<span class="payment-summary-row__label">{{ __("Entered Amount") }}</span>
									<strong class="payment-summary-row__val">
										{{ currencySymbol() }}{{ formatAmt(total_payment_methods) }}
									</strong>
								</div>
								<div
									class="payment-summary-row"
									:class="paymentDiff === 0
										? 'text-success'
										: paymentDiff > 0 ? 'text-warning' : 'text-error'"
								>
									<span class="payment-summary-row__label">
										{{ paymentDiff >= 0 ? __("Change") : __("Shortfall") }}
									</span>
									<strong class="payment-summary-row__val">
										{{ currencySymbol() }}{{ formatAmt(Math.abs(paymentDiff)) }}
									</strong>
								</div>
							</div>
							</div>

							<div class="payment-form-methods">
								<h3 class="payment-form-section__title">{{ __("Payment Methods") }}</h3>
								<div v-if="!payment_methods.length" class="text-caption text-medium-emphasis">
									{{ __("Enable payment methods in POS Profile settings") }}
								</div>
								<div v-else class="payment-methods-list">
									<div
										v-for="method in payment_methods"
										:key="method.mode_of_payment"
										class="payment-method-entry"
									>
										<span class="payment-method-entry__name">
											<v-icon size="16">{{ paymentMethodIcon(method.mode_of_payment) }}</v-icon>
											{{ __(method.mode_of_payment) }}
										</span>
										<v-text-field
											v-model.number="method.amount"
											type="number"
											density="compact"
											variant="outlined"
											hide-details
											min="0"
											placeholder="0"
											class="pos-themed-input"
										/>
									</div>
								</div>
							</div>
							</div>

							<div v-if="partyType === 'Supplier'" class="payment-form-section">
								<h3 class="payment-form-section__title">{{ __("Bank / Cheque Details") }}</h3>
								<div class="cheque-details-grid">
									<v-autocomplete
										v-model="cheque.bank_name"
										:items="bankOptions"
										item-title="name"
										item-value="name"
										:label="__('Bank')"
										:loading="bankLoading"
										density="compact"
										variant="outlined"
										hide-details
										clearable
										prepend-inner-icon="mdi-bank-outline"
										class="pos-themed-input"
									/>
									<v-text-field
										v-model="cheque.cheque_no"
										:label="__('Check Number')"
										density="compact"
										variant="outlined"
										hide-details
										clearable
										prepend-inner-icon="mdi-checkbook"
										class="pos-themed-input"
									/>
									<v-autocomplete
										v-model="cheque.payee"
										:items="payeeOptions"
										item-title="full_name"
										item-value="name"
										:label="__('Payee')"
										:loading="payeeLoading"
										no-filter
										density="compact"
										variant="outlined"
										hide-details
										clearable
										prepend-inner-icon="mdi-account-outline"
										class="pos-themed-input"
										@update:search="onPayeeSearch"
									>
										<template #item="{ props: itemProps, item }">
											<v-list-item v-bind="itemProps" :subtitle="item.raw.name" />
										</template>
									</v-autocomplete>
									<v-file-input
										v-model="chequeFile"
										:label="__('Upload Check (Optional)')"
										accept="image/*,.pdf"
										density="compact"
										variant="outlined"
										hide-details
										prepend-icon=""
										prepend-inner-icon="mdi-paperclip"
										:loading="chequeUploading"
										class="pos-themed-input"
										@update:model-value="onChequeFileSelected"
									/>
								</div>
								<p v-if="cheque.cheque_image" class="text-caption text-success mt-2 mb-0">
									<v-icon size="16" color="success">mdi-check-circle-outline</v-icon>
									{{ __("Check image uploaded") }}
								</p>
							</div>

							</div>
							<div class="payment-form-section payment-form-footer">
								<div class="payment-submit-panel__summary">
									<div class="payment-submit-panel__row">
										<span>{{ __("Entered Amount") }}</span>
										<strong>{{ currencySymbol() }}{{ formatAmt(total_payment_methods) }}</strong>
									</div>
									<div
										class="payment-submit-panel__row"
										:class="paymentDiff === 0
											? 'payment-submit-panel__row--clear'
											: paymentDiff > 0
												? 'payment-submit-panel__row--excess'
												: 'payment-submit-panel__row--short'"
									>
										<span>{{ paymentDiff >= 0 ? __("Change") : __("Shortfall") }}</span>
										<strong>{{ currencySymbol() }}{{ formatAmt(Math.abs(paymentDiff)) }}</strong>
									</div>
								</div>
								<div class="payment-submit-actions">
									<v-btn
										size="large"
										color="primary"
										:loading="isSubmitting"
										:disabled="isSubmitting || !canSubmit"
										class="text-none payment-submit-panel__btn"
										prepend-icon="mdi-check-circle"
										@click="handleSubmit(false)"
									>
										{{ __("Submit Payment") }}
									</v-btn>
									<v-btn
										size="large"
										color="success"
										variant="tonal"
										:loading="isSubmitting"
										:disabled="isSubmitting || !canSubmit"
										class="text-none payment-submit-panel__btn"
										prepend-icon="mdi-printer"
										@click="handleSubmit(true)"
									>
										{{ __("Submit & Print") }}
									</v-btn>
								</div>
							</div>
						</v-card>
					</div>
				</v-card>
			</v-col>
		</v-row>

		<div v-if="isCompact" class="mobile-pos-stack txn-bottom-dock">
			<div class="mobile-sale-dock">
				<div class="mobile-sale-dock__copy">
					<span class="mobile-sale-dock__eyebrow">{{ __("Selected Total") }}</span>
					<strong class="mobile-sale-dock__amount">
						{{ currencySymbol() }}{{ formatAmt(total_selected_invoices) }}
					</strong>
					<span class="mobile-sale-dock__meta">
						<template v-if="selected_invoices.length">
							{{ selected_invoices.length }}
							{{ selected_invoices.length === 1 ? __("invoice") : __("invoices") }}
						</template>
						<template v-else>{{ __("No invoices selected") }}</template>
					</span>
				</div>
				<v-btn
					:loading="isSubmitting"
					:disabled="isSubmitting || !canSubmit"
					color="primary"
					variant="flat"
					class="text-none txn-dock-pay-btn"
					prepend-icon="mdi-cash-check"
					@click="handleSubmit(false)"
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
					<span
						v-if="selected_invoices.length"
						class="mobile-pos-dock__pill"
					>{{ selected_invoices.length }}</span>
					<v-icon icon="mdi-cart-outline" size="22" />
					<span>{{ __("Cart") }}</span>
				</button>
				<button
					type="button"
					class="mobile-pos-dock__item mobile-pos-dock__item--pay"
					@click="handleSubmit(false)"
				>
					<v-icon icon="mdi-cash-check" size="20" />
					<span>{{ __("Pay") }}</span>
				</button>
			</div>
		</div>
	</div>
</template>

<script>
import {
	ref,
	computed,
	watch,
	onMounted,
	onBeforeUnmount,
	nextTick,
	getCurrentInstance,
} from "vue";
import { storeToRefs } from "pinia";
import VueDatePicker from "@vuepic/vue-datepicker";
import format from "../../../format";
import { normalizeDateForBackend } from "../../../format";
import Customer from "../customer/Customer.vue";
import { useUIStore } from "../../../stores/uiStore.js";
import { useCustomersStore } from "../../../stores/customersStore.js";
import {
	initPromise,
	checkDbHealth,
	setOpeningStorage,
	getOpeningStorage,
	clearOpeningStorage,
	isOffline,
	getPendingOfflinePaymentCount,
	syncOfflinePayments,
} from "../../../../offline/index";
import {
	isDebugPrintEnabled,
	appendDebugPrintParam,
	silentPrint,
	watchPrintWindow,
} from "../../../plugins/print";
import { printDocumentViaQz } from "../../../services/qzTray";
import { refreshRegisterPosProfile } from "../../../../utils/pos_profile";
import { usePosPaySelection } from "../../../composables/pos/payments/usePosPaySelection";
import { useCompactTransactionPanel } from "../../../composables/core/useCompactTransactionPanel";
import { ONLINE_ONLY_MODE } from "../../../config/runtime";
import { useRouter } from "vue-router";
import { isFundTransferManager } from "../../../utils/posWarehouseAccess";
import { uploadFile } from "../../../utils/uploadFile";
import InvoiceExpandedDetail from "../shared/InvoiceExpandedDetail.vue";

const getTodayDate = () =>
	frappe?.datetime?.nowdate?.() || new Date().toISOString().slice(0, 10);

const fmtDisplayDate = (date) => {
	if (!date) return "";
	const parts = String(date).split("-");
	return parts.length === 3
		? `${parts[2]}-${parts[1]}-${parts[0]}`
		: String(date);
};

export default {
	name: "PaymentView",
	mixins: [format],
	components: { Customer, VueDatePicker, InvoiceExpandedDetail },

	props: {
		partyType: {
			type: String,
			default: "Customer",
			validator: (v) => ["Customer", "Supplier"].includes(v),
		},
	},

	setup(props) {
		const { proxy } = getCurrentInstance();
		const router = useRouter();
		const uiStore = useUIStore();
		const customersStore = useCustomersStore();
		const { selectedCustomer } = storeToRefs(customersStore);
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

		// ── Core refs — seed from uiStore (already populated by POS session) ─
		const pos_profile = ref(
			uiStore.posProfile && uiStore.posProfile.name ? uiStore.posProfile : {},
		);
		const pos_opening_shift = ref(uiStore.posOpeningShift || "");
		const company = ref(uiStore.company || "");
		const partyName = ref(
			props.partyType === "Customer"
				? customersStore.selectedCustomer || ""
				: "",
		);
		const partySearchText = ref("");
		const partyOptions = ref([]);
		const partyLoading = ref(false);
		const postingDate = ref(getTodayDate());
		const autoAllocate = ref(true);
		// "Accounts" override -- System Manager / BSP Admin only, same feature
		// as the Sales/Purchase Invoice and Expense Claim screens' "Accounts"
		// card. Defaults to the active POS Profile's own
		// account_for_change_amount, but an admin can route this payment
		// through a different showroom's cash account instead; re-verified
		// server-side (make_payment_direct), this flag is UX-only.
		const canEditPaymentAccount = computed(() => isFundTransferManager());
		const cashAccountOptions = ref([]);
		const cashAccountsLoading = ref(false);
		const paymentAccountOverride = ref(null);
		const paymentHistory = ref([]);
		const historyLoading = ref(false);
		const PAGE_SIZE = 10;
		const invoicesPageStart = ref(0);
		const invoicesHasMore = ref(true);
		const invoicesLoadingMore = ref(false);
		const historyPageStart = ref(0);
		const historyHasMore = ref(true);
		const historyLoadingMore = ref(false);
		const invoicesScrollRef = ref(null);
		const historyScrollRef = ref(null);
		const invoicesSentinel = ref(null);
		const historySentinel = ref(null);
		const previewInvoice = ref(null);
		const previewDetail = ref(null);
		const previewLoading = ref(false);
		const previewError = ref("");
		const previewCache = new Map();

		// ── Format helpers ───────────────────────────────────────────
		const formatAmt = (val) => {
			let num = parseFloat(String(val || 0).replace(/,/g, ""));
			if (isNaN(num)) num = 0;
			let p = 2;
			if (typeof frappe !== "undefined" && frappe.defaults) {
				const dp = frappe.defaults.get_default("currency_precision");
				if (dp != null) p = Number(dp);
			}
			return num.toLocaleString("en-US", {
				minimumFractionDigits: p,
				maximumFractionDigits: p,
				useGrouping: true,
			});
		};

		const currencySymbol = (currency) =>
			get_currency_symbol(currency || pos_profile.value?.currency || "");

		// ── Date computed (display ↔ ISO) ────────────────────────────
		const postingDateDisplay = computed({
			get: () => fmtDisplayDate(postingDate.value),
			set: (v) => { postingDate.value = normalizeDateForBackend(v) || getTodayDate(); },
		});

		// ── Payment direction derives from party type ────────────────
		const paymentEntryType = computed(() =>
			props.partyType === "Supplier" ? "Pay" : "Receive",
		);
		const partyTypeRef = computed(() => props.partyType);

		// ── Direct outstanding invoices (bypass composable for reliability) ─
		const outstanding_invoices = ref([]);
		const invoices_loading = ref(false);
		const partyOutstanding = ref(0);
		// True total row count (invoices/dues), not just how many the
		// paginated/infinite-scroll list has loaded so far -- see
		// get_party_outstanding's "count" and get_all_outstanding_invoices's
		// "total" on the backend.
		const invoicesTotal = ref(0);
		const isSubmitting = ref(false);

		const resolvedCompany = () =>
			company.value ||
			(typeof frappe !== "undefined" && frappe.defaults?.get_default?.("company")) ||
			"";

		// One Journal Entry often carries a line per customer (opening
		// balances). Those rows share voucher_no and only differ by party,
		// so the key has to include party or "load more" throws the next
		// page away and the list stays stuck on the first screen.
		const invoiceRowKey = (row) =>
			`${row?.voucher_type || ""}::${row?.voucher_no || ""}::${row?.party || ""}`;

		const withRowKey = (row) => ({ ...row, _row_key: invoiceRowKey(row) });

		const mergeInvoiceRows = (existingRows, newRows) => {
			const seen = new Set(existingRows.map(invoiceRowKey));
			const deduped = [];
			for (const row of newRows) {
				const key = invoiceRowKey(row);
				if (seen.has(key)) continue;
				seen.add(key);
				deduped.push(withRowKey(row));
			}
			return [...existingRows, ...deduped];
		};

		// Bumped at the start of every fetchOutstandingInvoices() call, and
		// compared again once each call's network round trip resolves. This
		// screen fires that call from several independent places (onMounted,
		// the async checkOpeningEntry() re-fetch once company resolves, the
		// partyName/partyType watchers, and manual Sync) -- without this
		// guard, an older call's response landing *after* a newer call has
		// already replaced the list re-appends/re-replaces on top of it,
		// which is what was producing the duplicated Outstanding Invoices
		// rows on this screen.
		let outstandingFetchSeq = 0;

		const fetchOutstandingInvoices = async ({ append = false } = {}) => {
			if (append) {
				if (
					!outstanding_invoices.value.length ||
					!invoicesHasMore.value ||
					invoicesLoadingMore.value ||
					invoices_loading.value
				) return;
				invoicesLoadingMore.value = true;
			} else {
				invoices_loading.value = true;
				invoicesPageStart.value = 0;
				invoicesHasMore.value = true;
				outstanding_invoices.value = [];
			}

			const requestToken = ++outstandingFetchSeq;
			const isStale = () => requestToken !== outstandingFetchSeq;

			try {
				const pageStart = append ? outstanding_invoices.value.length : 0;

				if (!partyName.value) {
					const result = await frappe.call({
						method: "posawesome.posawesome.api.payment_entry.get_all_outstanding_invoices",
						args: {
							company: resolvedCompany() || null,
							party_type: props.partyType,
							page_start: pageStart,
							page_length: PAGE_SIZE,
						},
					});
					if (isStale()) return;
					const payload = result.message || {};
					const rows = Array.isArray(payload.invoices) ? payload.invoices : [];
					outstanding_invoices.value = append
						? mergeInvoiceRows(outstanding_invoices.value, rows)
						: rows.map(withRowKey);
					invoicesHasMore.value = Boolean(payload.has_more);
					invoicesTotal.value = Number(payload.total) || 0;
					partyOutstanding.value = 0;
					return;
				}

				const [invResult, outResult] = await Promise.all([
					frappe.call({
						method: "posawesome.posawesome.api.payment_entry.get_outstanding_invoices",
						args: {
							party: partyName.value,
							party_type: props.partyType,
							company: resolvedCompany() || null,
							pos_profile: null,
							include_all_currencies: true,
							page_start: pageStart,
							page_length: PAGE_SIZE,
						},
					}),
					frappe.call({
						method: "posawesome.posawesome.api.payment_entry.get_party_outstanding",
						args: {
							party: partyName.value,
							party_type: props.partyType,
							company: resolvedCompany() || null,
						},
					}),
				]);
				if (isStale()) return;
				const rows = Array.isArray(invResult.message) ? invResult.message : [];
				outstanding_invoices.value = append
					? mergeInvoiceRows(outstanding_invoices.value, rows)
					: rows.map(withRowKey);
				invoicesHasMore.value = rows.length >= PAGE_SIZE;
				partyOutstanding.value = outResult?.message?.outstanding || 0;
				invoicesTotal.value = Number(outResult?.message?.count) || 0;
				if (!append && partyName.value) {
					setDefaultPaymentAmount(partyOutstanding.value);
				}
			} catch (e) {
				console.error("Failed to fetch outstanding invoices", e);
				if (!append && !isStale()) {
					outstanding_invoices.value = [];
					invoicesTotal.value = 0;
				}
			} finally {
				if (!isStale()) {
					invoices_loading.value = false;
					invoicesLoadingMore.value = false;
				}
			}
		};

		const get_pos_profiles = async () => {};

		// Every non-group Cash account under the company's "Cash In Hand"
		// parent group -- backs the Accounts override dropdown above. Same
		// endpoint/gate the Sales/Purchase Invoice and Expense Claim screens
		// use (see get_cash_in_hand_accounts's own docstring).
		const loadCashInHandAccounts = async () => {
			const companyName = resolvedCompany();
			if (!canEditPaymentAccount.value || !companyName) return;
			cashAccountsLoading.value = true;
			try {
				const { message } = await frappe.call({
					method: "posawesome.posawesome.api.payment_processing.utils.get_cash_in_hand_accounts",
					args: { company: companyName },
				});
				cashAccountOptions.value = message || [];
			} catch (e) {
				console.error("Failed to load Cash In Hand accounts", e);
				cashAccountOptions.value = [];
			} finally {
				cashAccountsLoading.value = false;
			}
		};

		// ── Selection composable ─────────────────────────────────────
		const currency_filter = ref("ALL");
		const {
			selected_invoices,
			payment_methods,
			total_selected_invoices,
			total_payment_methods,
			toggleInvoiceSelection,
			isInvoiceSelected,
			clearSelections,
			resetPaymentMethodAmounts,
		} = usePosPaySelection({ posProfile: pos_profile, currency_filter });

		const setDefaultPaymentAmount = (amount) => {
			if (!payment_methods.value.length) return;
			const outstanding = parseFloat(String(amount || 0)) || 0;
			payment_methods.value = payment_methods.value.map((method, index) => ({
				...method,
				amount: index === 0 ? outstanding : 0,
			}));
		};

		// ── Populate payment methods (POS profile first, fallback to system) ──
		const initPaymentMethods = async () => {
			const profilePayments = pos_profile.value?.payments || [];
			if (profilePayments.length > 0) {
				payment_methods.value = profilePayments.map((m) => ({
					mode_of_payment: m.mode_of_payment,
					amount: 0,
					row_id: m.name,
				}));
				return;
			}
			// No POS profile payments configured — fetch all enabled modes
			try {
				const r = await frappe.call({
					method: "frappe.client.get_list",
					args: {
						doctype: "Mode of Payment",
						filters: [["enabled", "=", 1]],
						fields: ["name"],
						limit_page_length: 20,
					},
				});
				payment_methods.value = (r.message || []).map((m) => ({
					mode_of_payment: m.name,
					amount: 0,
				}));
			} catch {
				payment_methods.value = [];
			}
		};
		initPaymentMethods();

		// ── Computed totals ──────────────────────────────────────────
		const totalOutstanding = computed(
			() => partyOutstanding.value,
		);

		const paymentDiff = computed(
			() => total_payment_methods.value - total_selected_invoices.value,
		);

		// Belt-and-suspenders alongside the redirect guard below (onMounted /
		// the partyType watcher) -- even if a Supplier payment view somehow
		// stays mounted for a non-privileged user, the actual submit stays
		// blocked. Only BSP Admin/System Manager can make a Supplier Payment,
		// same gate as Fund Transfer's "New Transfer" and the Navbar's
		// "Supplier" payment link.
		const canSubmit = computed(
			() =>
				!!partyName.value &&
				total_payment_methods.value > 0 &&
				// Payments are invoice-wise only -- no advance / unallocated
				// amount (make_payment_direct enforces the same).
				(selected_invoices.value.length > 0 || autoAllocate.value) &&
				(props.partyType !== "Supplier" || isFundTransferManager()),
		);

		// Redirects away from the Supplier payment view for anyone without
		// permission -- covers direct navigation to /payments/supplier (a
		// bookmark, browser back/forward, etc.) since the Navbar link and
		// PaymentList's "Supplier Payment" button are already hidden for them.
		const redirectIfSupplierNotAllowed = () => {
			if (props.partyType !== "Supplier" || isFundTransferManager()) {
				return false;
			}
			proxy?.eventBus?.emit("show_message", {
				title: __("You do not have permission to make Supplier Payments."),
				color: "error",
			});
			router.replace("/payments/customer");
			return true;
		};

		const autoSelectInvoicesForAmount = () => {
			if (!autoAllocate.value || !partyName.value) return;
			if (total_payment_methods.value <= 0) {
				clearSelections();
				return;
			}

			let budget = total_payment_methods.value;
			const picks = [];
			const sorted = [...outstanding_invoices.value].sort((a, b) => {
				const da = a.due_date || a.posting_date || "";
				const db = b.due_date || b.posting_date || "";
				return String(da).localeCompare(String(db));
			});

			for (const inv of sorted) {
				if (budget <= 0) break;
				const outstanding = parseFloat(inv.outstanding_amount) || 0;
				if (outstanding <= 0) continue;
				picks.push(inv);
				budget -= outstanding;
			}

			selected_invoices.value = picks;
		};

		// ── Invoice click ────────────────────────────────────────────
		const clearInvoicePreview = () => {
			previewInvoice.value = null;
			previewDetail.value = null;
			previewError.value = "";
			previewLoading.value = false;
		};

		const loadInvoicePreview = async (item) => {
			if (!item?.voucher_no) return;
			previewInvoice.value = item;
			previewError.value = "";
			const type = item.voucher_type || (
				props.partyType === "Supplier" ? "Purchase Invoice" : "Sales Invoice"
			);
			if (type === "Journal Entry") {
				previewDetail.value = null;
				previewLoading.value = false;
				return;
			}
			const key = `${type}:${item.voucher_no}`;
			if (previewCache.has(key)) {
				previewDetail.value = previewCache.get(key);
				previewLoading.value = false;
				return;
			}
			previewDetail.value = null;
			previewLoading.value = true;
			try {
				const method = type === "Purchase Invoice"
					? "posawesome.posawesome.api.purchase_invoices.get_purchase_invoice_detail"
					: "posawesome.posawesome.api.invoices.get_sales_invoice_detail";
				const { message } = await frappe.call({
					method,
					args: { name: item.voucher_no },
				});
				previewCache.set(key, message || null);
				if (previewInvoice.value?.voucher_no === item.voucher_no) {
					previewDetail.value = message || null;
				}
			} catch (e) {
				if (previewInvoice.value?.voucher_no === item.voucher_no) {
					previewError.value = e?.message || __("Could not load invoice details");
				}
			} finally {
				if (previewInvoice.value?.voucher_no === item.voucher_no) {
					previewLoading.value = false;
				}
			}
		};

		const invoiceRowClass = (item) => {
			const classes = [];
			if (isInvoiceSelected(item)) classes.push("selected-invoice-row");
			if (
				previewInvoice.value &&
				invoiceRowKey(previewInvoice.value) === invoiceRowKey(item)
			) {
				classes.push("preview-invoice-row");
			}
			return classes.join(" ");
		};

		const handleInvoiceClick = (item) => {
			loadInvoicePreview(item);
			if (!partyName.value && item.party) {
				if (props.partyType === "Customer") {
					customersStore.setSelectedCustomer(item.party);
				} else {
					upsertPartyOption({
						name: item.party,
						supplier_name: item.party_name || item.party,
					});
				}
				partyName.value = item.party;
				return;
			}
			toggleInvoiceSelection(item, partyName, (name) => {
				if (props.partyType === "Customer") {
					customersStore.setSelectedCustomer(name);
				}
				partyName.value = name;
			});
		};

		// ── Supplier search ──────────────────────────────────────────
		const upsertPartyOption = (party) => {
			if (!party?.name) return;
			const index = partyOptions.value.findIndex((row) => row.name === party.name);
			if (index >= 0) {
				const updated = [...partyOptions.value];
				updated[index] = { ...updated[index], ...party };
				partyOptions.value = updated;
				return;
			}
			partyOptions.value = [party, ...partyOptions.value];
		};

		const ensureSupplierResolved = async (supplierId) => {
			if (!supplierId || props.partyType !== "Supplier") return;
			const existing = partyOptions.value.find((row) => row.name === supplierId);
			if (existing?.supplier_name && existing.supplier_name !== supplierId) {
				return;
			}
			try {
				const result = await frappe.call({
					method: "posawesome.posawesome.api.purchase_invoices.get_supplier_info",
					args: { supplier: supplierId },
				});
				const info = result.message || {};
				upsertPartyOption({
					name: info.supplier || supplierId,
					supplier_name: info.supplier_name || supplierId,
				});
			} catch {
				upsertPartyOption({
					name: supplierId,
					supplier_name: supplierId,
				});
			}
		};

		const onSupplierSelected = (supplierId) => {
			if (!supplierId) return;
			const match = partyOptions.value.find((row) => row.name === supplierId);
			if (match) {
				upsertPartyOption(match);
				return;
			}
			void ensureSupplierResolved(supplierId);
		};

		const onPartySearch = async (text = "") => {
			if (props.partyType !== "Supplier") return;
			partyLoading.value = true;
			try {
				const r = await frappe.call({
					method: "posawesome.posawesome.api.purchase_invoices.search_suppliers",
					args: { search_text: text || "", limit: 20 },
				});
				partyOptions.value = Array.isArray(r.message) ? r.message : [];
				if (partyName.value) {
					await ensureSupplierResolved(partyName.value);
				}
			} catch {
				partyOptions.value = [];
			} finally {
				partyLoading.value = false;
			}
		};

		// ── Payment history ──────────────────────────────────────────
		const fetchPaymentHistory = async ({ append = false } = {}) => {
			if (!partyName.value) {
				if (!append) {
					paymentHistory.value = [];
					historyHasMore.value = false;
				}
				return;
			}
			if (append) {
				if (
					!paymentHistory.value.length ||
					!historyHasMore.value ||
					historyLoadingMore.value ||
					historyLoading.value
				) return;
				historyLoadingMore.value = true;
			} else {
				historyLoading.value = true;
				historyPageStart.value = 0;
				historyHasMore.value = true;
				if (!append) paymentHistory.value = [];
			}

			try {
				const pageStart = append ? paymentHistory.value.length : 0;
				const r = await frappe.call({
					method: "posawesome.posawesome.api.payment_entry.get_payment_history",
					args: {
						party: partyName.value,
						party_type: props.partyType,
						company: resolvedCompany() || null,
						page_start: pageStart,
						page_length: PAGE_SIZE,
					},
				});
				const payload = r.message || {};
				const rows = Array.isArray(payload.payments) ? payload.payments : [];
				paymentHistory.value = append
					? [...paymentHistory.value, ...rows]
					: rows;
				historyHasMore.value = Boolean(payload.has_more);
			} catch (e) {
				console.error("Failed to fetch payment history", e);
				if (!append) paymentHistory.value = [];
			} finally {
				historyLoading.value = false;
				historyLoadingMore.value = false;
			}
		};

		const syncData = async () => {
			await Promise.all([
				fetchOutstandingInvoices(),
				partyName.value ? fetchPaymentHistory() : Promise.resolve(),
			]);
			if (autoAllocate.value) autoSelectInvoicesForAmount();
			await nextTick();
			fillInvoicePane();
			fillHistoryPane();
		};

		// Vuetify's table wrapper is overflow:auto. When that node is the one
		// with a scrollbar, scroll events stay on it and never reach the
		// parent div. Use whichever element is actually scrolling.
		const listScroller = (root) => {
			if (!root) return null;
			const wrapper = root.querySelector?.(".v-table__wrapper");
			if (wrapper && wrapper.scrollHeight > wrapper.clientHeight + 4) return wrapper;
			return root;
		};

		const isNearBottom = (el) =>
			!!el && el.scrollHeight - el.scrollTop - el.clientHeight <= 96;

		const isNearListEnd = (root) => {
			const el = listScroller(root);
			if (!el) return false;
			if (el.scrollHeight <= el.clientHeight + 4) return true;
			return isNearBottom(el);
		};

		let fillingInvoices = false;
		let fillingHistory = false;

		const fillInvoicePane = async () => {
			if (fillingInvoices) return;
			fillingInvoices = true;
			try {
				let passes = 0;
				while (
					passes < 6 &&
					invoicesHasMore.value &&
					outstanding_invoices.value.length &&
					!invoices_loading.value &&
					!invoicesLoadingMore.value &&
					isNearListEnd(invoicesScrollRef.value)
				) {
					const before = outstanding_invoices.value.length;
					await fetchOutstandingInvoices({ append: true });
					if (outstanding_invoices.value.length === before) break;
					passes += 1;
					await nextTick();
				}
			} finally {
				fillingInvoices = false;
			}
		};

		const fillHistoryPane = async () => {
			if (fillingHistory || !partyName.value) return;
			fillingHistory = true;
			try {
				let passes = 0;
				while (
					passes < 6 &&
					historyHasMore.value &&
					paymentHistory.value.length &&
					!historyLoading.value &&
					!historyLoadingMore.value &&
					isNearListEnd(historyScrollRef.value)
				) {
					const before = paymentHistory.value.length;
					await fetchPaymentHistory({ append: true });
					if (paymentHistory.value.length === before) break;
					passes += 1;
					await nextTick();
				}
			} finally {
				fillingHistory = false;
			}
		};

		const onInvoicesScroll = (event) => {
			const el = event.target;
			if (!el || el.nodeType !== 1) return;
			if (isNearBottom(el)) {
				fetchOutstandingInvoices({ append: true }).then(() => fillInvoicePane());
			}
		};

		const onHistoryScroll = (event) => {
			const el = event.target;
			if (!el || el.nodeType !== 1) return;
			if (isNearBottom(el)) {
				fetchPaymentHistory({ append: true }).then(() => fillHistoryPane());
			}
		};

		let invoicesObserver = null;
		let historyObserver = null;
		let unbindInvoiceScroll = null;
		let unbindHistoryScroll = null;

		const bindInfiniteScroll = () => {
			invoicesObserver?.disconnect();
			historyObserver?.disconnect();
			unbindInvoiceScroll?.();
			unbindHistoryScroll?.();
			unbindInvoiceScroll = null;
			unbindHistoryScroll = null;

			const listen = (root, handler) => {
				if (!root) return null;
				root.addEventListener("scroll", handler, true);
				return () => root.removeEventListener("scroll", handler, true);
			};
			unbindInvoiceScroll = listen(invoicesScrollRef.value, onInvoicesScroll);
			unbindHistoryScroll = listen(historyScrollRef.value, onHistoryScroll);

			if (typeof IntersectionObserver === "undefined") return;
			// Sentinel sits in the outer pane, so the observer root has to be
			// that pane. The capture scroll listener above covers the case
			// where Vuetify's inner wrapper is the element that scrolls.
			const observe = (sentinel, root, load) => {
				if (!sentinel || !root) return null;
				const observer = new IntersectionObserver(
					(entries) => {
						if (entries.some((entry) => entry.isIntersecting)) load();
					},
					{ root, rootMargin: "80px" },
				);
				observer.observe(sentinel);
				return observer;
			};
			invoicesObserver = observe(invoicesSentinel.value, invoicesScrollRef.value, () => {
				fetchOutstandingInvoices({ append: true }).then(() => fillInvoicePane());
			});
			historyObserver = observe(historySentinel.value, historyScrollRef.value, () => {
				fetchPaymentHistory({ append: true }).then(() => fillHistoryPane());
			});
		};

		// ── Opening shift ────────────────────────────────────────────
		const applyOpeningData = async (data) => {
			if (!data) return null;
			const rd = await refreshRegisterPosProfile(data);
			pos_profile.value = rd.pos_profile;
			pos_opening_shift.value = rd.pos_opening_shift;
			company.value = rd.company?.name || rd.pos_profile?.company || "";
			uiStore.setRegisterData(rd);
			initPaymentMethods();
			return rd;
		};

		const checkOpeningEntry = async () => {
			if (!ONLINE_ONLY_MODE) {
				await initPromise;
				await checkDbHealth();
			}
			const cached = getOpeningStorage();
			if (cached) await applyOpeningData(cached);
			try {
				const r = await frappe.call(
					"posawesome.posawesome.api.shifts.check_opening_shift",
					{ user: frappe.session.user },
				);
				if (r.message) {
					const rd = await applyOpeningData(r.message);
					if (rd) setOpeningStorage(rd);
					get_pos_profiles();
					// Re-fetch invoices now that company is resolved
					fetchOutstandingInvoices().then(() => fillInvoicePane());
					if (partyName.value) fetchPaymentHistory().then(() => fillHistoryPane());
				} else {
					clearOpeningStorage();
				}
			} catch (e) {
				console.error("Error checking opening entry", e);
				if (!isOffline()) clearOpeningStorage();
			}
		};

		// ── Print helper ─────────────────────────────────────────────
		const loadPrintPage = async (name) => {
			if (!name) return;
			const debugPrint = isDebugPrintEnabled();
			let url =
				frappe.urllib.get_base_url() +
				`/printview?doctype=Payment%20Entry&name=${name}&trigger_print=1`;
			url = appendDebugPrintParam(url, debugPrint);
			const opts = { allowOfflineFallback: isOffline(), triggerPrint: "1", debugPrint };
			if (pos_profile.value?.posa_silent_print) {
				try {
					await printDocumentViaQz({ doctype: "Payment Entry", name, printFormat: "Standard", noLetterhead: 1 });
					return;
				} catch {
					/* fall through */
				}
				silentPrint(url, opts);
			} else {
				watchPrintWindow(window.open(url, "_blank"), opts);
			}
		};

		// ── Bank / cheque details (Supplier payment only) ────────────
		const emptyCheque = () => ({
			bank_name: null,
			cheque_no: "",
			payee: frappe.session?.user || null,
			cheque_image: "",
		});
		const cheque = ref(emptyCheque());
		const chequeFile = ref(null);
		const chequeUploading = ref(false);
		const bankOptions = ref([]);
		const bankLoading = ref(false);
		const payeeOptions = ref([]);
		const payeeLoading = ref(false);
		let payeeSearchTimeout = null;

		const resetCheque = () => {
			cheque.value = emptyCheque();
			chequeFile.value = null;
		};

		const loadBanks = async () => {
			if (bankOptions.value.length) return;
			bankLoading.value = true;
			try {
				const { message } = await frappe.call({
					method: "posawesome.posawesome.api.bsp_daily_deposit.get_bank_options",
				});
				bankOptions.value = message || [];
			} catch (e) {
				console.error("Failed to load banks", e);
			} finally {
				bankLoading.value = false;
			}
		};

		const searchPayees = async (txt = "") => {
			payeeLoading.value = true;
			try {
				const { message } = await frappe.call({
					method: "posawesome.posawesome.api.payment_entry.search_payee_users",
					args: { txt },
				});
				const rows = (message || []).map((u) => ({ ...u, full_name: u.full_name || u.name }));
				// Keep the current pick selectable even when the search no longer matches it.
				const current = cheque.value.payee;
				if (current && !rows.some((u) => u.name === current)) {
					const known = payeeOptions.value.find((u) => u.name === current);
					rows.unshift(known || { name: current, full_name: frappe.session?.user_fullname || current });
				}
				payeeOptions.value = rows;
			} catch (e) {
				console.error("Failed to load users", e);
			} finally {
				payeeLoading.value = false;
			}
		};

		const onPayeeSearch = (txt) => {
			clearTimeout(payeeSearchTimeout);
			payeeSearchTimeout = setTimeout(() => searchPayees(txt || ""), 300);
		};

		const onChequeFileSelected = async (file) => {
			const selected = Array.isArray(file) ? file[0] : file;
			if (!selected) {
				cheque.value.cheque_image = "";
				return;
			}
			chequeUploading.value = true;
			try {
				// Public, so the check image opens for anyone viewing the payment.
				cheque.value.cheque_image = await uploadFile(selected, { isPrivate: false });
			} catch (e) {
				cheque.value.cheque_image = "";
				chequeFile.value = null;
				proxy?.eventBus?.emit("show_message", {
					title: e?.message || __("Failed to upload check image"),
					color: "error",
				});
			} finally {
				chequeUploading.value = false;
			}
		};

		const chequeArgs = () => {
			if (props.partyType !== "Supplier") return null;
			const c = cheque.value;
			if (!c.bank_name && !c.cheque_no && !c.cheque_image) return null;
			return { ...c };
		};

		const handleSubmit = async (printAfter = false) => {
			if (isSubmitting.value) return;

			if (!partyName.value) {
				frappe.throw(__("Please select a customer or supplier"));
				return;
			}
			const activeMethods = payment_methods.value.filter((m) => (m.amount || 0) > 0);
			if (activeMethods.length === 0) {
				frappe.throw(__("Please enter a payment amount"));
				return;
			}

			const chequeData = chequeArgs();
			if (chequeData && (!chequeData.bank_name || !chequeData.cheque_no)) {
				frappe.throw(__("Please enter both Bank and Check Number, or clear the cheque details."));
				return;
			}

			if (autoAllocate.value && !selected_invoices.value.length) {
				autoSelectInvoicesForAmount();
			}

			isSubmitting.value = true;
			try {
				const result = await frappe.call({
					method: "posawesome.posawesome.api.payment_entry.make_payment_direct",
					args: {
						party: partyName.value,
						party_type: props.partyType,
						company: resolvedCompany() || null,
						payment_methods: activeMethods,
						selected_invoices: selected_invoices.value,
						auto_allocate: autoAllocate.value ? 1 : 0,
						posting_date: postingDate.value || null,
						// Re-verified server-side (make_payment_direct) -- see
						// canEditPaymentAccount above.
						payment_account: canEditPaymentAccount.value
							? (paymentAccountOverride.value || null)
							: null,
						cheque: chequeData,
					},
					freeze: true,
					freeze_message: __("Processing Payment..."),
				});

				if (result?.message?.name) {
					frappe.utils?.play_sound?.("submit");
					proxy?.eventBus?.emit("show_message", {
						title: __("Payment submitted successfully"),
						color: "success",
					});
					clearSelections();
					resetPaymentMethodAmounts();
					resetCheque();
					if (printAfter) loadPrintPage(result.message.name);
					await syncData();
				}
			} catch (err) {
				console.error("Payment submission failed", err);
			} finally {
				isSubmitting.value = false;
			}
		};

		// ── Offline sync ─────────────────────────────────────────────
		const syncPending = async () => {
			const pending = getPendingOfflinePaymentCount();
			if (pending) proxy?.eventBus?.emit("show_message", { title: `${pending} payment(s) pending`, color: "warning" });
			if (!isOffline()) {
				const result = await syncOfflinePayments();
				if (result?.synced) proxy?.eventBus?.emit("show_message", { title: `${result.synced} payment(s) synced`, color: "success" });
			}
		};

		// ── Watchers ─────────────────────────────────────────────────
		watch(
			() => pos_profile.value?.company,
			() => {
				// Default to whatever the cashier already picked elsewhere this
				// session (uiStore.activeSaleAccount, shared with the Sales/
				// Purchase Invoice and Expense Claim screens' own "Accounts"
				// card), falling back to this POS Profile's own change account
				// only when nothing has been picked yet -- the user can still
				// pick a different one from the dropdown. Without the shared
				// value, this watcher firing again (e.g. this screen remounting)
				// silently reverted the cashier's chosen showroom account back
				// to the profile default.
				paymentAccountOverride.value =
					uiStore.activeSaleAccount || pos_profile.value?.account_for_change_amount || null;
				loadCashInHandAccounts();
			},
			{ immediate: true },
		);

		// Keep every other "Accounts" picker (Sales/Purchase Invoice, Expense
		// Claim) in sync with whatever gets picked here.
		watch(paymentAccountOverride, (val) => {
			uiStore.setActiveSaleAccount(val);
		});

		watch(selectedCustomer, (val) => {
			if (props.partyType !== "Customer") return;
			partyName.value = val || "";
		}, { immediate: true });

		watch(partyName, async (val, old) => {
			if (val === old) return;
			clearSelections();
			if (previewInvoice.value?.party && previewInvoice.value.party !== val) {
				clearInvoicePreview();
			}
			partyOutstanding.value = 0;
			paymentHistory.value = [];
			resetPaymentMethodAmounts();
			if (val && props.partyType === "Supplier") {
				await ensureSupplierResolved(val);
			}
			await Promise.all([
				fetchOutstandingInvoices(),
				val ? fetchPaymentHistory() : Promise.resolve(),
			]);
			if (autoAllocate.value) autoSelectInvoicesForAmount();
			await nextTick();
			fillInvoicePane();
			fillHistoryPane();
		});

		// Customer and Supplier pages share this same component instance --
		// Vue Router doesn't remount it when navigating between them via the
		// menu (only the partyType prop changes), so without this the
		// outstanding invoices list stayed stuck showing whichever party
		// type loaded first until a full page reload.
		watch(
			() => props.partyType,
			async () => {
				if (redirectIfSupplierNotAllowed()) return;
				partyName.value = "";
				partySearchText.value = "";
				partyOptions.value = [];
				clearSelections();
				clearInvoicePreview();
				previewCache.clear();
				partyOutstanding.value = 0;
				paymentHistory.value = [];
				resetPaymentMethodAmounts();
				resetCheque();
				await fetchOutstandingInvoices();
				await nextTick();
				fillInvoicePane();
				if (props.partyType === "Supplier") {
					onPartySearch("");
					loadBanks();
					searchPayees("");
				}
			},
		);

		watch(
			() => payment_methods.value.map((m) => m.amount),
			() => {
				if (autoAllocate.value) autoSelectInvoicesForAmount();
			},
			{ deep: true },
		);

		watch(autoAllocate, (enabled) => {
			if (enabled) autoSelectInvoicesForAmount();
			else clearSelections();
		});

		// ── Lifecycle ────────────────────────────────────────────────
		onMounted(() => {
			if (redirectIfSupplierNotAllowed()) return;
			if (props.partyType === "Supplier") {
				onPartySearch("");
				loadBanks();
				searchPayees("");
			}
			if (proxy?.eventBus) {
				proxy.eventBus.on("network-online", syncPending);
				proxy.eventBus.on("server-online", syncPending);
			}
			fetchOutstandingInvoices().then(() => fillInvoicePane());
			if (partyName.value) fetchPaymentHistory().then(() => fillHistoryPane());
			nextTick(() => {
				bindInfiniteScroll();
				checkOpeningEntry();
			});
		});

		onBeforeUnmount(() => {
			invoicesObserver?.disconnect();
			historyObserver?.disconnect();
			unbindInvoiceScroll?.();
			unbindHistoryScroll?.();
			if (proxy?.eventBus) {
				proxy.eventBus.off("network-online", syncPending);
				proxy.eventBus.off("server-online", syncPending);
			}
		});

		// ── Icon helper ──────────────────────────────────────────────
		const paymentMethodIcon = (mode = "") => {
			const m = mode.toLowerCase();
			if (m.includes("cash")) return "mdi-cash";
			if (m.includes("card") || m.includes("credit") || m.includes("debit")) return "mdi-credit-card";
			if (m.includes("bank") || m.includes("transfer")) return "mdi-bank-transfer";
			if (m.includes("cheque") || m.includes("check")) return "mdi-checkbook";
			return "mdi-wallet";
		};

		// ── Table headers ────────────────────────────────────────────
		const invoiceHeaders = computed(() => {
			const cols = [
				{ title: "", key: "sel", sortable: false, width: "40px" },
				{ title: __("Invoice"), key: "voucher_no", sortable: true },
			];
			if (!partyName.value) {
				cols.push({
					title: props.partyType === "Supplier"
						? __("Supplier")
						: __("Customer"),
					key: "party_name",
					sortable: true,
				});
			}
			cols.push(
				{ title: __("Date"), key: "posting_date", sortable: true },
				{ title: __("Due Date"), key: "due_date", sortable: true },
				{ title: __("Outstanding"), key: "outstanding_amount", sortable: true, align: "end" },
			);
			return cols;
		});
		const historyHeaders = [
			{ title: __("Reference"), key: "name", sortable: true },
			{ title: __("Date"), key: "posting_date", sortable: true },
			{ title: __("Type"), key: "payment_type", sortable: true },
			{ title: __("Mode"), key: "mode_of_payment", sortable: true },
			{ title: __("Amount"), key: "paid_amount", sortable: true, align: "end" },
			{ title: __("Allocated"), key: "allocated_amount", sortable: true, align: "end" },
			{ title: __("Ref No"), key: "reference_no", sortable: true, minWidth: "140px" },
		];

		return {
			responsiveStyles,
			isCompact,
			compactPanel,
			showInvoicePanel,
			showSelectorPanel,
			invoiceCols,
			selectorCols,
			setPanel,
			partyName,
			partySearchText,
			partyOptions,
			partyLoading,
			postingDateDisplay,
			autoAllocate,
			canEditPaymentAccount,
			cashAccountOptions,
			cashAccountsLoading,
			paymentAccountOverride,
			outstanding_invoices,
			invoices_loading,
			invoicesTotal,
			selected_invoices,
			total_selected_invoices,
			payment_methods,
			total_payment_methods,
			paymentHistory,
			historyLoading,
			cheque,
			chequeFile,
			chequeUploading,
			bankOptions,
			bankLoading,
			payeeOptions,
			payeeLoading,
			onPayeeSearch,
			onChequeFileSelected,
			totalOutstanding,
			paymentDiff,
			canSubmit,
			isSubmitting,
			invoiceHeaders,
			historyHeaders,
			currencySymbol,
			formatAmt,
			isInvoiceSelected,
			clearSelections,
			handleInvoiceClick,
			invoiceRowClass,
			previewInvoice,
			previewDetail,
			previewLoading,
			previewError,
			onPartySearch,
			onSupplierSelected,
			handleSubmit,
			paymentMethodIcon,
			syncData,
			onInvoicesScroll,
			onHistoryScroll,
			invoicesLoadingMore,
			historyLoadingMore,
		};
	},
};
</script>

<style scoped>
@import "../invoice-shared-styles.css";

.cheque-details-grid {
	display: grid;
	grid-template-columns: repeat(2, minmax(0, 1fr));
	gap: 12px;
}

@media (max-width: 600px) {
	.cheque-details-grid {
		grid-template-columns: 1fr;
	}
}

.payment-shell {
	overflow: hidden;
}

.payment-invoice-card,
.payment-side-card {
	border-radius: var(--pos-radius-md, 18px);
}

.payment-main-body {
	overflow: hidden;
	min-height: 0;
}

.payment-content {
	display: flex;
	flex-direction: column;
	flex: 1 1 auto;
	min-height: 0;
	gap: var(--dynamic-sm);
}

.payment-top-grid {
	grid-template-columns: 2.5fr 1fr 2fr;
	align-items: stretch;
	gap: var(--dynamic-sm);
	flex: 0 0 auto;
}

.payment-top-grid > .invoice-section-card {
	height: 100%;
	display: flex;
	flex-direction: column;
}

.payment-top-grid > .outstanding-panel {
	justify-content: center;
}

.payment-party-body {
	padding: 8px 14px 12px;
}

.payment-tables-stack {
	display: flex;
	flex-direction: column;
	flex: 1 1 auto;
	min-height: 0;
	gap: var(--dynamic-sm);
	overflow: hidden;
}

.payment-tables-stack > .payment-table-card {
	flex: 1 1 0;
	min-height: 0;
	overflow: hidden;
}

.payment-side-body {
	display: flex;
	flex-direction: column;
	gap: 12px;
	height: 100%;
	min-height: 0;
	padding: 12px;
}

.payment-invoice-preview {
	flex: 1 1 auto;
	min-height: 180px;
	overflow: auto;
	border: 1px solid rgba(var(--v-theme-on-surface), 0.08);
	border-radius: 14px;
	background: var(--pos-card-bg, #fff);
}

.payment-invoice-preview--empty {
	display: flex;
	align-items: center;
	justify-content: center;
	color: var(--pos-text-secondary, #6b7280);
	font-size: 0.9rem;
	text-align: center;
	padding: 16px;
}

.payment-preview-status,
.payment-preview-fallback {
	display: flex;
	align-items: center;
	gap: 8px;
	padding: 8px 16px 14px;
	font-size: 0.85rem;
}

.payment-preview-fallback {
	flex-direction: column;
	align-items: flex-start;
	gap: 6px;
}

.payment-form-card {
	flex: 0 0 auto;
	display: flex;
	flex-direction: column;
	min-height: 0;
	overflow: visible;
}

.payment-form-scroll {
	overflow: visible;
	min-height: 0;
}

.payment-form-top {
	display: grid;
	grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
	gap: 8px 12px;
	align-items: start;
}

.payment-form-heading {
	padding: 10px 14px 0;
}

.payment-form-methods {
	padding: 10px 14px 8px 0;
}

.payment-form-section {
	padding: 12px 14px;
	border-top: 1px solid rgba(var(--v-theme-on-surface), 0.08);
}

.payment-form-section__title {
	margin: 0 0 10px;
	font-size: 0.95rem;
	font-weight: 600;
}

.payment-form-footer {
	display: flex;
	flex-direction: column;
	gap: 12px;
	flex-shrink: 0;
	background: var(--pos-card-bg, #fff);
}

.payment-submit-actions {
	display: grid;
	grid-template-columns: 1fr 1fr;
	gap: 10px;
}

.payment-invoices-table :deep(tr.preview-invoice-row:not(.selected-invoice-row)) {
	background: color-mix(in srgb, var(--pos-primary, #0097a7) 6%, transparent);
}

.invoice-section-heading--toolbar {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 12px;
	padding: 16px 18px 8px;
}

.invoice-section-heading__actions {
	display: flex;
	align-items: center;
	justify-content: flex-end;
	gap: 4px;
	margin-left: auto;
	flex-shrink: 0;
}

.payment-table-card {
	display: flex;
	flex-direction: column;
	min-height: 0;
}

.payment-table-card--split {
	flex: 1 1 0;
}

.payment-table-body {
	padding: 0 14px 14px;
	flex: 1 1 auto;
	min-height: 0;
	display: flex;
	flex-direction: column;
}

.payment-table-scroll {
	flex: 1 1 auto;
	min-height: 0;
	overflow-y: auto;
}

.payment-ref-no {
	display: inline-block;
	max-width: 180px;
}

.payment-history-table + .text-center,
.payment-invoices-table + .text-center {
	border-top: 1px solid rgba(var(--v-theme-on-surface), 0.08);
}

.payment-invoices-table :deep(tr.selected-invoice-row) {
	background: color-mix(in srgb, var(--pos-primary) 8%, transparent) !important;
}

.payment-invoices-table :deep(tr.selected-invoice-row td) {
	border-left: 3px solid var(--primary-start, #0097a7);
}

.payment-invoices-table,
.payment-history-table {
	flex: 1 1 auto;
	min-height: 0;
}

/* Deliberately NOT overflow/max-height here -- .payment-table-scroll (the
   ancestor div carrying @scroll="onInvoicesScroll"/"onHistoryScroll") must
   be the *only* scrolling container. Giving the table's own internal
   wrapper its own overflow:auto here made *it* the element that actually
   scrolled once content overflowed, so the ancestor's scroll listener
   (which drives the infinite-scroll fetch-more) never fired -- the list
   silently capped at the first page. */
.payment-invoices-table :deep(.v-table__wrapper),
.payment-history-table :deep(.v-table__wrapper) {
	overflow: visible !important;
	max-height: none !important;
	height: auto !important;
}

.payment-scroll-sentinel {
	height: 1px;
}

.payment-summary-list {
	display: flex;
	flex-direction: column;
	gap: 6px;
	padding: 8px 14px 10px;
}

.payment-summary-row {
	display: flex;
	justify-content: space-between;
	align-items: center;
	gap: 12px;
	font-size: 0.875rem;
}

.payment-summary-row__label {
	color: var(--pos-text-secondary, #6b7280);
}

.payment-summary-row__val {
	font-weight: 600;
	text-align: right;
}

.payment-methods-list {
	display: flex;
	flex-direction: column;
	gap: 6px;
	padding: 0;
}

.payment-method-entry {
	display: grid;
	grid-template-columns: minmax(72px, 38%) minmax(0, 1fr);
	align-items: center;
	gap: 6px;
	width: 100%;
}

.payment-method-entry__name {
	display: flex;
	align-items: center;
	gap: 4px;
	font-size: 0.78rem;
	font-weight: 600;
	line-height: 1.15;
}

.payment-submit-panel {
	display: flex;
	flex-direction: column;
	gap: 12px;
	flex-shrink: 0;
	padding: 16px 18px 18px;
	border-top: 1px solid rgba(var(--v-theme-on-surface), 0.08);
	background: var(--pos-card-bg, #fff);
}

.payment-submit-panel__summary {
	display: flex;
	flex-direction: column;
	gap: 8px;
	padding: 12px 14px;
	border-radius: 12px;
	background: rgba(var(--v-theme-on-surface), 0.04);
}

.payment-submit-panel__row {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 12px;
	font-size: 0.875rem;
	color: var(--pos-text-secondary, #6b7280);
}

.payment-submit-panel__row strong {
	font-size: 1rem;
	color: var(--pos-text-primary, #111827);
}

.payment-submit-panel__row--clear strong {
	color: rgb(var(--v-theme-success));
}

.payment-submit-panel__row--excess strong {
	color: rgb(var(--v-theme-warning));
}

.payment-submit-panel__row--short strong {
	color: rgb(var(--v-theme-error));
}

.payment-submit-panel__btn {
	min-height: 48px !important;
	font-weight: 700;
	border-radius: 10px !important;
}

@media (max-width: 900px) {
	.payment-form-top {
		grid-template-columns: 1fr;
	}

	.payment-form-methods {
		padding: 0 14px 8px;
		border-top: 1px solid rgba(var(--v-theme-on-surface), 0.08);
	}
}

@media (max-width: 768px) {
	.payment-top-grid {
		grid-template-columns: 1fr;
	}

	.payment-top-grid > .invoice-section-card {
		height: auto;
	}

	.payment-tables-stack {
		flex: 1 1 auto;
		min-height: 0;
		overflow: visible;
	}

	.payment-tables-stack > .payment-table-card,
	.payment-table-card--split {
		flex: 1 1 auto;
		min-height: 220px;
		max-height: 420px;
	}
}

:deep(.drawer-item--child .v-list-item__content) {
	padding-left: 12px;
}
</style>
