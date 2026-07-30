<template>
	<div class="pa-0 h-100 invoice-shell txn-shell">
		<v-row class="h-100 ma-0 justify-center">
			<v-col cols="12" md="9" lg="7" class="h-100 pa-0">
				<v-card class="h-100 d-flex flex-column pos-themed-card purchase-invoice-card" flat>
					<v-card-text class="flex-grow-1 overflow-y-auto pa-3 pa-md-4">
						<div class="invoice-sections">
							<div class="invoice-top-grid purchase-top-grid">
								<v-card flat class="invoice-section-card pos-themed-card">
									<div class="invoice-section-heading">
										<h3 class="invoice-section-heading__title">{{ __("Account Paid From") }}</h3>
									</div>
									<div class="sale-options-body">
										<v-text-field
											:model-value="paidFrom"
											:label="__('Company Default Cash Account')"
											density="compact"
											variant="outlined"
											color="primary"
											hide-details
											readonly
											:loading="paidFromLoading"
											prepend-inner-icon="mdi-bank-outline"
											class="pos-themed-input"
										/>
									</div>
								</v-card>

								<v-card flat class="invoice-section-card pos-themed-card outstanding-panel">
									<div class="outstanding-panel__inner">
										<div class="outstanding-panel__label">{{ __("Amount") }}</div>
										<div class="outstanding-panel__amount outstanding-panel__amount--clear">
											{{ formatCurrency(amount) }}
										</div>
									</div>
								</v-card>

								<v-card flat class="invoice-section-card pos-themed-card sale-options-card">
									<div class="invoice-section-heading">
										<h3 class="invoice-section-heading__title">{{ __("Date") }}</h3>
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

							<v-card flat class="invoice-section-card pos-themed-card">
								<div class="invoice-section-heading">
									<h3 class="invoice-section-heading__title">{{ __("Transfer Details") }}</h3>
								</div>
								<div class="sale-options-body transfer-details-grid">
									<v-select
										v-model="paidTo"
										:items="paidToOptions"
										item-title="name"
										item-value="name"
										:label="__('Account Paid To')"
										density="compact"
										variant="outlined"
										color="primary"
										hide-details
										:loading="paidToLoading"
										class="pos-themed-input"
									/>
									<v-select
										v-model="modeOfPayment"
										:items="modeOfPaymentOptions"
										item-title="name"
										item-value="name"
										:label="__('Mode of Payment')"
										density="compact"
										variant="outlined"
										color="primary"
										hide-details
										:loading="modeOfPaymentLoading"
										class="pos-themed-input"
									/>
									<v-text-field
										v-model.number="amount"
										type="number"
										min="0"
										:label="__('Amount')"
										density="compact"
										variant="outlined"
										color="primary"
										hide-details
										class="pos-themed-input"
									/>
									<v-text-field
										v-model="remarks"
										:label="__('Remarks')"
										density="compact"
										variant="outlined"
										color="primary"
										hide-details
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
							<span class="purchase-bottom-bar__label">{{ __("Amount") }}</span>
							<strong class="purchase-bottom-bar__amount">{{ formatCurrency(amount) }}</strong>
						</div>
						<v-btn
							:loading="submitLoading"
							:disabled="submitLoading || !amount || !paidTo || !modeOfPayment"
							size="large"
							color="primary"
							class="text-none purchase-pay-btn"
							prepend-icon="mdi-bank-transfer"
							@click="submitTransfer"
						>
							{{ __("Submit Transfer") }}
						</v-btn>
					</div>
				</v-card>
			</v-col>
		</v-row>
	</div>
</template>

<script>
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import format from '../../../format';
import { useUIStore } from '../../../stores/uiStore.js';
import { useToastStore } from '../../../stores/toastStore';
import DateFilterField from '../shared/DateFilterField.vue';

const getTodayDate = () =>
	frappe?.datetime?.nowdate?.() || new Date().toISOString().slice(0, 10);

export default {
	name: 'FundTransferNew',
	mixins: [format],
	components: { DateFilterField },
	setup() {
		const router = useRouter();
		const uiStore = useUIStore();
		const toastStore = useToastStore();
		const pos_profile = ref(uiStore.posProfile || {});
		const company = pos_profile.value?.company || null;

		const paidFrom = ref('');
		const paidFromLoading = ref(false);

		const paidToOptions = ref([]);
		const paidToLoading = ref(false);
		const paidTo = ref(null);

		const modeOfPaymentOptions = ref([]);
		const modeOfPaymentLoading = ref(false);
		const modeOfPayment = ref(null);

		const postingDate = ref(getTodayDate());
		const amount = ref(null);
		const remarks = ref('');

		const submitLoading = ref(false);
		const errorMessage = ref('');

		const loadPaidFrom = async () => {
			paidFromLoading.value = true;
			try {
				const { message } = await frappe.call({
					method: 'posawesome.posawesome.api.fund_transfer.get_paid_from_account',
					args: { company },
				});
				paidFrom.value = message?.account || '';
			} catch (e) {
				errorMessage.value = e?.message || __('Failed to load the source account');
			} finally {
				paidFromLoading.value = false;
			}
		};

		const loadPaidToOptions = async () => {
			paidToLoading.value = true;
			try {
				const { message } = await frappe.call({
					method: 'posawesome.posawesome.api.fund_transfer.get_paid_to_account_options',
					args: { company },
				});
				paidToOptions.value = message || [];
			} catch (e) {
				errorMessage.value = e?.message || __('Failed to load Cash In Hand accounts');
			} finally {
				paidToLoading.value = false;
			}
		};

		const loadModeOfPaymentOptions = async () => {
			modeOfPaymentLoading.value = true;
			try {
				const { message } = await frappe.call({
					method: 'posawesome.posawesome.api.fund_transfer.get_mode_of_payment_options',
				});
				modeOfPaymentOptions.value = message || [];
			} catch (e) {
				errorMessage.value = e?.message || __('Failed to load Modes of Payment');
			} finally {
				modeOfPaymentLoading.value = false;
			}
		};

		const resetForm = () => {
			postingDate.value = getTodayDate();
			paidTo.value = null;
			modeOfPayment.value = null;
			amount.value = null;
			remarks.value = '';
		};

		const submitTransfer = async () => {
			errorMessage.value = '';

			if (!paidTo.value) {
				errorMessage.value = __('Select an Account Paid To.');
				return;
			}
			if (!modeOfPayment.value) {
				errorMessage.value = __('Select a Mode of Payment.');
				return;
			}
			if (!Number(amount.value) || Number(amount.value) <= 0) {
				errorMessage.value = __('Enter an Amount greater than zero.');
				return;
			}

			submitLoading.value = true;
			try {
				const { message } = await frappe.call({
					method: 'posawesome.posawesome.api.fund_transfer.create_fund_transfer',
					args: {
						data: {
							company,
							posting_date: postingDate.value,
							paid_to: paidTo.value,
							mode_of_payment: modeOfPayment.value,
							amount: amount.value,
							remarks: remarks.value,
						},
					},
					freeze: true,
					freeze_message: __('Submitting transfer...'),
				});
				toastStore.show({
					title: __('Fund Transfer {0} submitted', [message?.name || '']),
					color: 'success',
				});
				resetForm();
				await router.push('/fund-transfer/list');
			} catch (e) {
				errorMessage.value = e?.message || __('Failed to submit transfer');
			} finally {
				submitLoading.value = false;
			}
		};

		onMounted(async () => {
			await Promise.all([loadPaidFrom(), loadPaidToOptions(), loadModeOfPaymentOptions()]);
		});

		return {
			paidFrom,
			paidFromLoading,
			paidToOptions,
			paidToLoading,
			paidTo,
			modeOfPaymentOptions,
			modeOfPaymentLoading,
			modeOfPayment,
			postingDate,
			amount,
			remarks,
			submitLoading,
			errorMessage,
			submitTransfer,
		};
	},
};
</script>

<style scoped>
@import '../invoice-shared-styles.css';

.transfer-details-grid {
	display: grid;
	grid-template-columns: repeat(2, minmax(0, 1fr));
	gap: 12px;
}

@media (max-width: 600px) {
	.transfer-details-grid {
		grid-template-columns: 1fr;
	}
}
</style>
