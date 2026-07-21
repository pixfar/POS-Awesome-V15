<template>
	<v-dialog v-model="dialog" width="96vw" max-width="1480" persistent>
		<v-card class="pos-themed-card payment-shell--dialog">
			<v-progress-linear :active="loading" :indeterminate="loading" absolute location="top" color="info" />
			<div class="overflow-y-auto payment-scroll">
				<div class="payment-sections payment-sections--purchase">
					<section class="payment-section payment-section--summary">
						<div class="payment-section__header">
							<h3 class="payment-section__title">{{ __("Payment Summary") }}</h3>
						</div>
						<v-row v-if="totalAmount > 0" class="payment-summary-grid" dense>
							<v-col cols="12" sm="6">
								<v-text-field
									variant="solo"
									color="primary"
									:label="frappe._('Paid Amount')"
									class="sleek-field pos-themed-input"
									hide-details
									:model-value="formatCurrency(paidAmount, currency)"
									readonly
									:prefix="currencySymbol(currency)"
									density="compact"
								></v-text-field>
							</v-col>
							<v-col cols="12" sm="6">
								<v-text-field
									variant="solo"
									color="primary"
									:label="outstandingLabel"
									class="sleek-field pos-themed-input"
									hide-details
									:model-value="formatCurrency(Math.abs(remainingAmount), currency)"
									:prefix="currencySymbol(currency)"
									density="compact"
									readonly
									:class="remainingAmount > 0 ? 'text-error' : 'text-success'"
								></v-text-field>
							</v-col>
						</v-row>
						<v-alert
							v-if="allowPartialPayment && totalAmount > 0"
							type="info"
							density="compact"
							variant="tonal"
						>
							{{ __("Enter any payment amount. Outstanding balance can remain on the invoice.") }}
						</v-alert>
					</section>

					<section class="payment-section payment-section--methods">
						<div class="payment-section__header">
							<h3 class="payment-section__title">{{ __("Payment Methods") }}</h3>
						</div>
						<PaymentMethods
							:payments="paymentLines"
							:currency="currency"
							:isReturn="false"
							:requestPaymentField="false"
							:currencySymbol="currencySymbol"
							:formatCurrency="(v) => formatCurrency(v, currency)"
							:isNumber="isNumber"
							:getVisibleDenominations="getVisibleDenominations"
							:isCashLikePayment="isCashLikePayment"
							:isMpesaC2bPayment="() => false"
							@update-amount="handlePaymentAmountChange"
							@set-full-amount="set_full_amount"
							@set-denomination="setPaymentToDenomination"
							@set-rest-amount="set_rest_amount"
						/>
					</section>

					<section class="payment-section payment-section--totals">
						<div class="payment-section__header">
							<h3 class="payment-section__title">{{ __("Invoice Totals") }}</h3>
						</div>
						<v-row class="invoice-totals-grid" dense>
							<v-col cols="12" sm="6">
								<v-text-field
									density="compact"
									variant="solo"
									color="primary"
									:label="frappe._('Net Total')"
									class="sleek-field pos-themed-input"
									:model-value="formatCurrency(totalAmount, currency)"
									readonly
									:prefix="currencySymbol(currency)"
									hide-details
								></v-text-field>
							</v-col>
							<v-col cols="12" sm="6">
								<v-text-field
									density="compact"
									variant="solo"
									color="primary"
									:label="frappe._('Additional Discount')"
									class="sleek-field pos-themed-input"
									hide-details
									:model-value="formatCurrency(additionalDiscount, currency)"
									@change="handleDiscountChange"
									:prefix="currencySymbol(currency)"
									inputmode="decimal"
								></v-text-field>
							</v-col>
							<v-col cols="12" sm="6">
								<v-text-field
									density="compact"
									variant="solo"
									color="primary"
									:label="frappe._('Total Amount')"
									class="sleek-field pos-themed-input"
									hide-details
									:model-value="formatCurrency(payableAmount, currency)"
									readonly
									:prefix="currencySymbol(currency)"
								></v-text-field>
							</v-col>
						</v-row>

						<div class="payment-section__subsection">
							<h3 class="payment-section__title payment-section__title--subsection">
								{{ __("Print") }}
							</h3>
						</div>
						<v-select
							v-model="selectedPrintFormat"
							:items="printFormats"
							:label="__('Print Format (Purchase Invoice)')"
							density="compact"
							variant="solo"
							color="primary"
							hide-details
							class="sleek-field pos-themed-input"
							clearable
						></v-select>
					</section>
				</div>
			</div>

			<div class="payment-footer payment-footer--dialog">
				<PaymentActionButtons
					:loading="loading"
					:validatePayment="!isPaid ? false : !isPaymentValid"
					compact
					@submit="submit(false)"
					@submit-and-print="submit(true)"
					@cancel="close"
				/>
			</div>
		</v-card>
	</v-dialog>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import { formatUtils } from "../../../format";
import { getSmartTenderSuggestions } from "../../../../utils/smartTender";
import PaymentActionButtons from "../payments/PaymentActionButtons.vue";
import PaymentMethods from "../payments/PaymentMethods.vue";

defineOptions({
	name: "PurchasePaymentDialog",
});

const __ = window.__ || ((text) => text);

const props = defineProps({
	modelValue: Boolean,
	totalAmount: {
		type: Number,
		required: true,
	},
	currency: {
		type: String,
		default: "",
	},
	posProfile: {
		type: Object,
		required: true,
	},
	isPaid: {
		type: Boolean,
		default: true,
	},
});

const emit = defineEmits(["update:modelValue", "submit"]);
const currency_precision = ref(2);

const paymentLines = ref([]);
const printFormats = ref([]);
const selectedPrintFormat = ref(null);
const loading = ref(false);
const additionalDiscount = ref(0);

const dialog = computed({
	get() {
		return props.modelValue;
	},
	set(val) {
		emit("update:modelValue", val);
	},
});

const paidAmount = computed(() =>
	paymentLines.value.reduce((sum, p) => sum + (parseFloat(p.amount) || 0), 0),
);

const payableAmount = computed(() =>
	Math.max(props.totalAmount - (parseFloat(additionalDiscount.value) || 0), 0),
);

const remainingAmount = computed(() => payableAmount.value - paidAmount.value);

// Purchase Invoices always allow partial payment from POS.
const allowPartialPayment = computed(() => true);

const outstandingLabel = computed(() => {
	if (remainingAmount.value > 0 && allowPartialPayment.value) {
		return __("Outstanding");
	}
	return remainingAmount.value > 0 ? __("To Be Paid") : __("Change");
});

const isPaymentValid = computed(() => {
	const hasNegativePayment = paymentLines.value.some((p) => (parseFloat(p.amount) || 0) < 0);
	if (hasNegativePayment) return false;

	if (paidAmount.value <= 0) return true;
	if (allowPartialPayment.value) return true;
	return remainingAmount.value <= 0;
});

// PaymentMethods.vue expects a validation-rule function; purchase amounts
// don't need extra validation beyond the negative-payment check above.
function isNumber() {
	return true;
}

watch(
	() => props.modelValue,
	(val) => {
		if (val) {
			initializePayments();
			fetchPrintFormats();
			loading.value = false;
		}
	},
);

watch(
	() => payableAmount.value,
	() => {
		if (!props.modelValue || !props.isPaid) return;
		const hasAnyAmount = paymentLines.value.some(
			(p) => (parseFloat(p.amount) || 0) > 0,
		);
		if (hasAnyAmount) return;

		const defaultMode =
			paymentLines.value.find((p) => p.default) || paymentLines.value[0];
		if (defaultMode) {
			defaultMode.amount = payableAmount.value;
		}
	},
);

const flt = (value, precision, number_format, rounding_method) => {
	if (!precision && precision != 0) {
		precision = currency_precision.value || 2;
	}
	if (!rounding_method) {
		rounding_method = "Banker's Rounding (legacy)";
	}
	return window.flt(value, precision, number_format, rounding_method);
};

function formatCurrency(value, precision) {
	if (value === null || value === undefined) {
		value = 0;
	}
	let number = Number(formatUtils.fromArabicNumerals(String(value)).replace(/,/g, ""));
	if (isNaN(number)) number = 0;
	let prec = precision != null ? Number(precision) : Number(currency_precision.value) || 2;
	if (!Number.isInteger(prec) || prec < 0 || prec > 20) {
		prec = Math.min(Math.max(parseInt(prec) || 2, 0), 20);
	}

	const locale = formatUtils.getNumberLocale();
	let formatted = number.toLocaleString(locale, {
		minimumFractionDigits: prec,
		maximumFractionDigits: prec,
		useGrouping: true,
	});

	formatted = formatUtils.toArabicNumerals(formatted);
	return formatted;
}

function initializePayments() {
	additionalDiscount.value = 0;

	const modes = props.posProfile.payments || [];
	paymentLines.value = modes.map((m) => ({
		name: m.mode_of_payment,
		mode_of_payment: m.mode_of_payment,
		amount: 0,
		default: m.default,
		type: m.type,
	}));

	// Only pre-fill the default payment when Is Paid is ON
	if (props.isPaid) {
		const defaultMode = paymentLines.value.find((p) => p.default) || paymentLines.value[0];
		if (defaultMode) {
			defaultMode.amount = payableAmount.value;
		}
	}
}

function handleDiscountChange(event) {
	additionalDiscount.value = Math.max(parsePaymentInput(event), 0);
}

function set_full_amount(payment) {
	// Reset all other payments
	paymentLines.value.forEach((p) => {
		if (p !== payment) {
			p.amount = 0;
		}
	});
	// Set this payment to total amount
	payment.amount = payableAmount.value;
}

function set_rest_amount(payment) {
	// If payment is 0 and there's remaining amount, auto-fill
	if (payment.amount === 0 && remainingAmount.value > 0) {
		payment.amount = remainingAmount.value;
	}
}

function parsePaymentInput(value) {
	const raw = value?.target?.value ?? value ?? "";
	const normalized = formatUtils.fromArabicNumerals(String(raw)).replace(/,/g, "");
	const parsed = parseFloat(normalized);
	return Number.isFinite(parsed) ? parsed : 0;
}

function handlePaymentAmountChange(payment, event) {
	payment.amount = parsePaymentInput(event);

	if (remainingAmount.value < 0) {
		autoBalancePayments(payment);
	}
}

function setPaymentToDenomination(payment, amount) {
	payment.amount = amount;
	// Auto-balance other payments if needed
	if (remainingAmount.value < 0) {
		autoBalancePayments(payment);
	}
}

function autoBalancePayments(excludePayment) {
	const excess = Math.abs(remainingAmount.value);
	if (excess <= 0) return;

	// Find other payments with amount > 0 to reduce
	const otherPayments = paymentLines.value.filter((p) => p !== excludePayment && parseFloat(p.amount) > 0);

	// Sort by amount descending to reduce larger chunks first
	otherPayments.sort((a, b) => parseFloat(b.amount) - parseFloat(a.amount));

	let remainingExcess = excess;

	for (const other of otherPayments) {
		if (remainingExcess <= 0) break;

		const otherAmount = parseFloat(other.amount) || 0;
		const reduction = Math.min(otherAmount, remainingExcess);

		other.amount = flt(otherAmount - reduction, currency_precision.value);
		remainingExcess = flt(remainingExcess - reduction, currency_precision.value);
	}
}

function isCashLikePayment(payment) {
	if (!payment) return false;

	// Check if it's the configured cash MOP or contains "cash" in name
	const configuredCashMOP = String(props.posProfile?.posa_cash_mode_of_payment || "").toLowerCase();
	const mode = String(payment.mode_of_payment || "").toLowerCase();
	const type = String(payment.type || "").toLowerCase();

	if (type === "cash") return true;
	if (configuredCashMOP && mode === configuredCashMOP) return true;
	return mode.includes("cash");
}

function getVisibleDenominations(payment) {
	if (!isCashLikePayment(payment)) return [];

	const currentTotalPaid = paidAmount.value;
	const currentPaymentAmount = parseFloat(payment.amount) || 0;
	const otherPayments = currentTotalPaid - currentPaymentAmount;
	const amountToPay = payableAmount.value - otherPayments;

	if (amountToPay <= 0) return [];

	return getSmartTenderSuggestions(amountToPay, props.currency);
}

function currencySymbol(curr) {
	return curr || "";
}

function close() {
	dialog.value = false;
}

function submit(doPrint) {
	loading.value = true;
	const payments = paymentLines.value
		.filter((p) => p.amount > 0)
		.map((p) => ({
			mode_of_payment: p.mode_of_payment,
			amount: p.amount,
		}));

	emit("submit", {
		payments,
		print: doPrint,
		print_format: selectedPrintFormat.value,
		print_invoice: true,
		discount_amount: parseFloat(additionalDiscount.value) || 0,
	});
}

async function fetchPrintFormats() {
	try {
		const doctype = "Purchase Invoice";
		const { message } = await frappe.call({
			method: "posawesome.posawesome.api.print_formats.get_print_formats",
			args: {
				doctype: doctype,
			},
		});
		printFormats.value = message || [];
		selectedPrintFormat.value = null;

		if (printFormats.value.length) {
			if (props.posProfile.print_format && printFormats.value.includes(props.posProfile.print_format)) {
				selectedPrintFormat.value = props.posProfile.print_format;
			} else {
				selectedPrintFormat.value = printFormats.value[0];
			}
		}
	} catch (e) {
		console.error("Failed to fetch print formats", e);
	}
}
</script>

<style scoped>
/* Remove readonly styling */
.v-text-field--readonly {
	cursor: text;
}

.v-text-field--readonly:hover {
	background-color: transparent;
}

.pos-themed-card {
	border-radius: 12px;
}

/* Sleek field styling for right-aligned text */
.sleek-field :deep(.v-field__input) {
	text-align: right;
}

/* Dialog shell — mirrors Payments.vue's payment-shell--dialog treatment */
.payment-shell--dialog {
	height: calc(100dvh - 48px);
	display: flex;
	flex-direction: column;
	gap: 0;
	background: var(--pos-card-bg);
	border-radius: 16px;
	overflow: hidden;
	box-shadow: 0 25px 60px rgba(15, 23, 42, 0.35);
}

.payment-scroll {
	padding: var(--pos-space-3);
	display: flex;
	flex-direction: column;
	gap: var(--pos-space-3);
	flex: 1 1 auto;
	min-height: 0;
	scrollbar-width: thin;
	scrollbar-color: var(--v-theme-primary) transparent;
}

.payment-scroll::-webkit-scrollbar {
	width: 6px;
}

.payment-scroll::-webkit-scrollbar-track {
	background: transparent;
}

.payment-scroll::-webkit-scrollbar-thumb {
	background-color: rgb(var(--v-theme-primary));
	border-radius: 3px;
}

.payment-sections--purchase {
	display: grid;
	grid-template-columns: minmax(0, 1.05fr) minmax(0, 0.95fr);
	gap: var(--pos-space-2);
	align-items: start;
	grid-template-areas:
		"summary totals"
		"methods totals";
}

.payment-sections--purchase .payment-section--summary {
	grid-area: summary;
}

.payment-sections--purchase .payment-section--methods {
	grid-area: methods;
}

.payment-sections--purchase .payment-section--totals {
	grid-area: totals;
}

.payment-section {
	background: var(--pos-surface-muted);
	border: 1px solid var(--pos-border-light);
	border-radius: var(--pos-radius-md);
	padding: 10px;
	display: flex;
	flex-direction: column;
	gap: 10px;
}

.payment-section--summary {
	background: linear-gradient(180deg, rgba(var(--v-theme-primary), 0.08) 0%, var(--pos-surface-muted) 100%);
}

.payment-section__header {
	display: flex;
	flex-direction: column;
	gap: 0;
}

.payment-section__subsection {
	display: flex;
	flex-direction: column;
	gap: 2px;
	padding-top: var(--pos-space-1);
	border-top: 1px solid var(--pos-border-light);
}

.payment-section__title {
	margin: 0;
	font-size: 1rem;
	font-weight: 700;
	line-height: 1.2;
	color: var(--pos-text-primary);
}

.payment-section__title--subsection {
	font-size: 0.92rem;
}

.payment-summary-grid,
.invoice-totals-grid {
	margin: 0;
	row-gap: var(--pos-space-2);
}

.payment-summary-grid :deep(.v-col),
.invoice-totals-grid :deep(.v-col) {
	padding-top: 2px;
	padding-bottom: 2px;
}

.payment-summary-grid :deep(.v-field),
.invoice-totals-grid :deep(.v-field) {
	border-radius: var(--pos-radius-sm);
	background: var(--pos-surface-raised);
}

.payment-footer {
	flex: 0 0 auto;
	position: sticky;
	bottom: 0;
	z-index: 8;
	background: var(--pos-card-bg);
}

.payment-footer--dialog {
	padding: 0;
	margin-top: 0;
	border-top: 1px solid var(--pos-border-light);
}

:deep(.payment-footer--dialog .cards) {
	margin-top: 0 !important;
}

:deep(.payment-footer--dialog .v-btn) {
	min-height: 42px;
}

@media (max-width: 768px) {
	.payment-shell--dialog {
		height: auto;
	}

	.payment-scroll {
		padding: var(--pos-space-2);
		gap: var(--pos-space-2);
	}

	.payment-sections--purchase {
		display: flex;
		flex-direction: column;
	}

	.payment-section {
		padding: var(--pos-space-2);
		gap: var(--pos-space-2);
	}
}
</style>
