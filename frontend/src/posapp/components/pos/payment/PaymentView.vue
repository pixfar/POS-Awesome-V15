<template>
	<div class="pa-0 h-100 payment-shell">
		<v-row class="h-100 ma-0">

			<!-- ═══════════════════════════════════════════════════════
			     LEFT: Party selector · Outstanding invoices · History
			     ═══════════════════════════════════════════════════════ -->
			<v-col cols="12" md="7" class="h-100 pa-0">
				<v-card class="h-100 d-flex flex-column pos-themed-card" flat>
					<v-card-text class="flex-grow-1 overflow-y-auto pa-3">
						<div class="invoice-sections">

							<!-- 3-column top grid -->
							<div class="invoice-top-grid payment-top-grid">

								<!-- Party selector -->
								<v-card flat class="invoice-section-card pos-themed-card">
									<div class="invoice-section-heading">
										<h3 class="invoice-section-heading__title">
											{{ partyType === "Customer" ? __("Customer") : __("Supplier") }}
										</h3>
									</div>
									<Customer v-if="partyType === 'Customer'" />
									<v-autocomplete
										v-else
										v-model="partyName"
										v-model:search="partySearchText"
										:items="partyOptions"
										:loading="partyLoading"
										item-title="supplier_name"
										item-value="name"
										:label="__('Search Supplier')"
										density="compact"
										variant="outlined"
										color="primary"
										hide-details
										clearable
										no-filter
										class="pos-themed-input"
										@update:search="onPartySearch"
									/>
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

								<!-- Date + auto-allocate -->
								<v-card flat class="invoice-section-card pos-themed-card">
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
									</div>
								</v-card>
							</div>

							<!-- Outstanding invoices table -->
							<v-card flat class="invoice-section-card pos-themed-card mt-2">
								<div class="invoice-section-heading">
									<h3 class="invoice-section-heading__title">
										{{ __("Outstanding Invoices") }}
									</h3>
									<div class="invoice-section-heading__actions">
										<span v-if="selected_invoices.length" class="text-caption text-primary mr-2">
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
									</div>
								</div>
								<v-data-table
									:headers="invoiceHeaders"
									:items="outstanding_invoices"
									:loading="invoices_loading"
									density="compact"
									fixed-header
									:height="230"
									hide-default-footer
									:items-per-page="-1"
									:no-data-text="__('No outstanding invoices')"
									:row-props="({ item }) => ({
										class: isInvoiceSelected(item) ? 'selected-invoice-row' : '',
										style: 'cursor:pointer',
									})"
									@click:row="(_, row) => handleInvoiceClick(row.item)"
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
							</v-card>

							<!-- Payment entry history -->
							<v-card flat class="invoice-section-card pos-themed-card mt-2">
								<div class="invoice-section-heading">
									<h3 class="invoice-section-heading__title">{{ __("Payment History") }}</h3>
								</div>
								<v-data-table
									:headers="historyHeaders"
									:items="paymentHistory"
									:loading="historyLoading"
									density="compact"
									fixed-header
									:height="190"
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
									<template #item.unallocated_amount="{ item }">
										<span :class="Number(item.unallocated_amount) > 0 ? 'text-warning' : 'text-success'">
											{{ currencySymbol() }}{{ formatAmt(item.unallocated_amount) }}
										</span>
									</template>
									<template #item.name="{ item }">
										<span class="text-caption text-primary">{{ item.name }}</span>
									</template>
								</v-data-table>
							</v-card>

						</div>
					</v-card-text>

					<!-- Bottom action bar -->
					<div class="payment-bottom-bar">
						<div class="payment-bottom-bar__summary">
							<span class="payment-bottom-bar__label">{{ __("Selected") }}</span>
							<strong class="payment-bottom-bar__amount">
								{{ currencySymbol() }}{{ formatAmt(total_selected_invoices) }}
							</strong>
							<span v-if="selected_invoices.length" class="payment-bottom-bar__meta">
								{{ selected_invoices.length }}
								{{ selected_invoices.length === 1 ? __("invoice") : __("invoices") }}
							</span>
						</div>
						<v-btn
							:loading="isSubmitting"
							:disabled="isSubmitting || !canSubmit"
							size="large"
							class="text-none payment-pay-btn"
							prepend-icon="mdi-cash-check"
							color="primary"
							@click="handleSubmit(false)"
						>
							{{ __("PAY") }}
						</v-btn>
					</div>
				</v-card>
			</v-col>

			<!-- ═══════════════════════════════════════════════════════
			     RIGHT: Summary · Payment methods · Reference · Submit
			     ═══════════════════════════════════════════════════════ -->
			<v-col cols="12" md="5" class="h-100 pa-0 border-s">
				<v-card class="h-100 d-flex flex-column pos-themed-card" flat>
					<v-card-text class="flex-grow-1 overflow-y-auto pa-3">

						<!-- Summary -->
						<v-card flat class="invoice-section-card pos-themed-card mb-2">
							<div class="invoice-section-heading">
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
								<v-divider class="my-1" />
								<div
									class="payment-summary-row"
									:class="paymentDiff === 0
										? 'text-success'
										: paymentDiff > 0 ? 'text-warning' : 'text-error'"
								>
									<span class="payment-summary-row__label">
										{{ paymentDiff >= 0 ? __("Excess") : __("Shortfall") }}
									</span>
									<strong class="payment-summary-row__val">
										{{ currencySymbol() }}{{ formatAmt(Math.abs(paymentDiff)) }}
									</strong>
								</div>
							</div>
						</v-card>

						<!-- Payment methods -->
						<v-card flat class="invoice-section-card pos-themed-card mb-2">
							<div class="invoice-section-heading">
								<h3 class="invoice-section-heading__title">{{ __("Payment Methods") }}</h3>
							</div>
							<div v-if="!payment_methods.length" class="text-caption text-medium-emphasis pa-2">
								{{ __("Enable payment methods in POS Profile settings") }}
							</div>
							<div class="payment-methods-list">
								<div
									v-for="method in payment_methods"
									:key="method.mode_of_payment"
									class="payment-method-entry"
								>
									<v-text-field
										v-model.number="method.amount"
										:label="__(method.mode_of_payment)"
										type="number"
										density="compact"
										variant="outlined"
										hide-details
										min="0"
										class="pos-themed-input"
										:prepend-inner-icon="paymentMethodIcon(method.mode_of_payment)"
									/>
								</div>
							</div>
						</v-card>

						<!-- Reference -->
						<v-card flat class="invoice-section-card pos-themed-card mb-2">
							<div class="invoice-section-heading">
								<h3 class="invoice-section-heading__title">{{ __("Reference") }}</h3>
							</div>
							<v-text-field
								v-model="referenceNo"
								:label="__('Reference No')"
								density="compact"
								variant="outlined"
								hide-details
								class="pos-themed-input mb-2"
								prepend-inner-icon="mdi-identifier"
							/>
							<VueDatePicker
								v-model="referenceDateDisplay"
								model-type="format"
								format="dd-MM-yyyy"
								auto-apply
								teleport
								:placeholder="__('Reference Date')"
								class="sleek-field pos-themed-input"
							/>
						</v-card>

					</v-card-text>

					<!-- Submit panel -->
					<div class="payment-submit-panel pa-3">
						<v-btn
							block
							size="large"
							color="primary"
							:loading="isSubmitting"
							:disabled="isSubmitting || !canSubmit"
							class="mb-2 text-none"
							prepend-icon="mdi-check-circle"
							@click="handleSubmit(false)"
						>
							{{ __("Submit Payment") }}
						</v-btn>
						<v-btn
							block
							size="large"
							color="success"
							variant="tonal"
							:loading="isSubmitting"
							:disabled="isSubmitting || !canSubmit"
							class="text-none"
							prepend-icon="mdi-printer"
							@click="handleSubmit(true)"
						>
							{{ __("Submit & Print") }}
						</v-btn>
					</div>
				</v-card>
			</v-col>
		</v-row>
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
	components: { Customer, VueDatePicker },

	props: {
		partyType: {
			type: String,
			default: "Customer",
			validator: (v) => ["Customer", "Supplier"].includes(v),
		},
	},

	setup(props) {
		const { proxy } = getCurrentInstance();
		const uiStore = useUIStore();
		const customersStore = useCustomersStore();
		const { selectedCustomer } = storeToRefs(customersStore);

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
		const referenceNo = ref("");
		const referenceDate = ref("");
		const paymentHistory = ref([]);
		const historyLoading = ref(false);

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
		const referenceDateDisplay = computed({
			get: () => fmtDisplayDate(referenceDate.value),
			set: (v) => { referenceDate.value = normalizeDateForBackend(v) || ""; },
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
		const isSubmitting = ref(false);

		const resolvedCompany = () =>
			company.value ||
			(typeof frappe !== "undefined" && frappe.defaults?.get_default?.("company")) ||
			"";

		const fetchOutstandingInvoices = async () => {
			invoices_loading.value = true;
			try {
				if (!partyName.value) {
					// No party selected — show ALL outstanding invoices for the company
					const result = await frappe.call({
						method: "posawesome.posawesome.api.payment_entry.get_all_outstanding_invoices",
						args: {
							company: resolvedCompany() || null,
							party_type: props.partyType,
							page_length: 200,
						},
					});
					outstanding_invoices.value = Array.isArray(result.message)
						? result.message
						: [];
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
							page_start: 0,
							page_length: 300,
						},
					}),
					frappe.call({
						method: "posawesome.posawesome.api.customer.get_customer_outstanding",
						args: { customer: partyName.value },
					}),
				]);
				outstanding_invoices.value = Array.isArray(invResult.message)
					? invResult.message
					: [];
				partyOutstanding.value = outResult?.message?.outstanding || 0;
			} catch (e) {
				console.error("Failed to fetch outstanding invoices", e);
				outstanding_invoices.value = [];
			} finally {
				invoices_loading.value = false;
			}
		};

		const get_pos_profiles = async () => {};

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

		const canSubmit = computed(
			() =>
				!!partyName.value &&
				(total_payment_methods.value > 0 || total_selected_invoices.value > 0),
		);

		// ── Invoice click ────────────────────────────────────────────
		const handleInvoiceClick = (item) => {
			if (!partyName.value && item.party) {
				// Clicking from "all invoices" view — auto-select the party
				if (props.partyType === "Customer") {
					customersStore.setSelectedCustomer(item.party);
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
		const onPartySearch = async (text = "") => {
			if (props.partyType !== "Supplier") return;
			partyLoading.value = true;
			try {
				const r = await frappe.call({
					method: "posawesome.posawesome.api.purchase_invoices.search_suppliers",
					args: { search_text: text || "", limit: 20 },
				});
				partyOptions.value = Array.isArray(r.message) ? r.message : [];
			} catch {
				partyOptions.value = [];
			} finally {
				partyLoading.value = false;
			}
		};

		// ── Payment history ──────────────────────────────────────────
		const fetchPaymentHistory = async () => {
			if (!partyName.value) {
				paymentHistory.value = [];
				return;
			}
			historyLoading.value = true;
			try {
				const filters = [
					["party_type", "=", props.partyType],
					["party", "=", partyName.value],
					["docstatus", "=", 1],
				];
				if (company.value) filters.push(["company", "=", company.value]);
				const r = await frappe.call({
					method: "frappe.client.get_list",
					args: {
						doctype: "Payment Entry",
						filters,
						fields: [
							"name",
							"posting_date",
							"mode_of_payment",
							"paid_amount",
							"unallocated_amount",
							"payment_type",
						],
						limit_page_length: 30,
						order_by: "posting_date desc, creation desc",
					},
				});
				paymentHistory.value = Array.isArray(r.message) ? r.message : [];
			} catch (e) {
				console.error("Failed to fetch payment history", e);
				paymentHistory.value = [];
			} finally {
				historyLoading.value = false;
			}
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
			await initPromise;
			await checkDbHealth();
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
					fetchOutstandingInvoices();
					if (partyName.value) fetchPaymentHistory();
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

		const handleSubmit = async (printAfter = false) => {
			if (isSubmitting.value) return;

			if (!partyName.value) {
				frappe.throw(__("Please select a customer or supplier"));
				return;
			}
			const activeMethods = payment_methods.value.filter((m) => (m.amount || 0) > 0);
			if (activeMethods.length === 0 && selected_invoices.value.length === 0) {
				frappe.throw(__("Please enter a payment amount"));
				return;
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
						posting_date: postingDate.value || null,
						reference_no: referenceNo.value || null,
						reference_date: referenceDate.value || null,
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
					referenceNo.value = "";
					referenceDate.value = "";
					if (printAfter) loadPrintPage(result.message.name);
					await Promise.all([fetchOutstandingInvoices(), fetchPaymentHistory()]);
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
		watch(selectedCustomer, (val) => {
			if (props.partyType !== "Customer") return;
			partyName.value = val || "";
		}, { immediate: true });

		watch(partyName, async (val, old) => {
			if (val === old) return;
			clearSelections();
			partyOutstanding.value = 0;
			paymentHistory.value = [];
			await Promise.all([
				fetchOutstandingInvoices(),
				val ? fetchPaymentHistory() : Promise.resolve(),
			]);
		});

		// ── Lifecycle ────────────────────────────────────────────────
		onMounted(() => {
			if (props.partyType === "Supplier") onPartySearch("");
			if (proxy?.eventBus) {
				proxy.eventBus.on("network-online", syncPending);
				proxy.eventBus.on("server-online", syncPending);
			}
			// Always fetch invoices on mount — shows all when no party, filtered when party set
			fetchOutstandingInvoices();
			if (partyName.value) fetchPaymentHistory();
			// Refresh opening entry in background for latest profile / payment methods
			nextTick(checkOpeningEntry);
		});

		onBeforeUnmount(() => {
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
				cols.push({ title: __("Party"), key: "party_name", sortable: true });
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
			{ title: __("Mode"), key: "mode_of_payment", sortable: true },
			{ title: __("Amount"), key: "paid_amount", sortable: true, align: "end" },
			{ title: __("Unallocated"), key: "unallocated_amount", sortable: true, align: "end" },
		];

		return {
			partyName,
			partySearchText,
			partyOptions,
			partyLoading,
			postingDateDisplay,
			referenceDateDisplay,
			autoAllocate,
			referenceNo,
			referenceDate,
			outstanding_invoices,
			invoices_loading,
			selected_invoices,
			total_selected_invoices,
			payment_methods,
			total_payment_methods,
			paymentHistory,
			historyLoading,
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
			onPartySearch,
			handleSubmit,
			paymentMethodIcon,
		};
	},
};
</script>

<style scoped>
.payment-shell { overflow: hidden; }

/* 3-col top grid */
.payment-top-grid {
	display: grid;
	grid-template-columns: 1fr 1fr 1fr;
	gap: 8px;
	margin-bottom: 8px;
}
@media (max-width: 900px) { .payment-top-grid { grid-template-columns: 1fr 1fr; } }
@media (max-width: 600px) { .payment-top-grid { grid-template-columns: 1fr; } }

/* Selected invoice row highlight */
.payment-invoices-table :deep(tr.selected-invoice-row) {
	background: rgba(37, 99, 235, 0.08) !important;
}
.payment-invoices-table :deep(tr.selected-invoice-row td) {
	border-left: 3px solid #2563eb;
}

/* Bottom action bar */
.payment-bottom-bar {
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding: 10px 16px;
	border-top: 1px solid rgba(0, 0, 0, 0.08);
	background: #fff;
	flex-shrink: 0;
	gap: 12px;
}
.payment-bottom-bar__summary {
	display: flex;
	align-items: baseline;
	gap: 8px;
	flex-wrap: wrap;
}
.payment-bottom-bar__label { font-size: 0.8rem; color: #6b7280; }
.payment-bottom-bar__amount { font-size: 1.25rem; font-weight: 700; color: #1d4ed8; }
.payment-bottom-bar__meta { font-size: 0.75rem; color: #9ca3af; }
.payment-pay-btn { min-width: 120px; font-weight: 700; letter-spacing: 0.04em; }

/* Right panel summary */
.payment-summary-list { display: flex; flex-direction: column; gap: 4px; padding: 4px 8px 8px; }
.payment-summary-row { display: flex; justify-content: space-between; align-items: center; font-size: 0.85rem; }
.payment-summary-row__label { color: #6b7280; }
.payment-summary-row__val { font-weight: 600; }

/* Payment methods */
.payment-methods-list { display: flex; flex-direction: column; gap: 8px; padding: 4px 8px 8px; }

/* Submit panel */
.payment-submit-panel {
	border-top: 1px solid rgba(0, 0, 0, 0.08);
	flex-shrink: 0;
	background: #fff;
}

/* Child drawer items indentation */
:deep(.drawer-item--child .v-list-item__content) { padding-left: 12px; }
</style>
