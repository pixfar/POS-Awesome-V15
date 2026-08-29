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
										<h3 class="invoice-section-heading__title">{{ __("Deposited By") }}</h3>
									</div>
									<div class="sale-options-body">
										<v-text-field
											:model-value="userDisplay"
											:label="__('User')"
											density="compact"
											variant="outlined"
											color="primary"
											hide-details
											readonly
											:loading="userLoading"
											prepend-inner-icon="mdi-account-outline"
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
											:disabled="!canEditPostingDate"
											field-class="pos-themed-input"
										/>
									</div>
								</v-card>
							</div>

							<v-card flat class="invoice-section-card pos-themed-card">
								<div class="invoice-section-heading">
									<h3 class="invoice-section-heading__title">{{ __("Deposit Details") }}</h3>
								</div>
								<div class="sale-options-body deposit-details-grid">
									<v-autocomplete
										v-if="canChangeWarehouse && warehouseOptions.length"
										v-model="warehouse"
										:items="warehouseOptions"
										item-title="warehouse_name"
										item-value="name"
										:label="__('Warehouse')"
										density="compact"
										variant="outlined"
										color="primary"
										hide-details
										:loading="warehouseLoading"
										class="pos-themed-input"
									/>
									<v-text-field
										v-else
										:model-value="warehouseLabel || warehouse"
										:label="__('Warehouse')"
										density="compact"
										variant="outlined"
										color="primary"
										hide-details
										readonly
										:loading="warehouseLoading"
										prepend-inner-icon="mdi-warehouse"
										class="pos-themed-input"
									/>
									<v-select
										v-model="depositType"
										:items="depositTypeOptions"
										:label="__('Deposit Type')"
										density="compact"
										variant="outlined"
										color="primary"
										hide-details
										class="pos-themed-input"
									/>
									<v-select
										v-model="bankName"
										:items="bankOptions"
										item-title="name"
										item-value="name"
										:label="__('Bank Name')"
										density="compact"
										variant="outlined"
										color="primary"
										hide-details
										:loading="bankLoading"
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
								</div>
							</v-card>

							<v-card flat class="invoice-section-card pos-themed-card">
								<div class="invoice-section-heading">
									<h3 class="invoice-section-heading__title">{{ __("Acknowledgment Receipt") }}</h3>
								</div>
								<div class="sale-options-body">
									<v-file-input
										v-model="receiptFile"
										:label="__('Attach Receipt')"
										density="compact"
										variant="outlined"
										color="primary"
										hide-details
										prepend-icon=""
										prepend-inner-icon="mdi-paperclip"
										accept="image/*,.pdf"
										:loading="receiptUploading"
										class="pos-themed-input"
										@update:model-value="handleReceiptSelected"
									/>
									<p v-if="receiptUrl" class="text-caption text-success mt-2">
										<v-icon size="16" color="success">mdi-check-circle-outline</v-icon>
										{{ __("Receipt uploaded") }}
									</p>
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
							:disabled="submitLoading || !amount"
							size="large"
							color="primary"
							class="text-none purchase-pay-btn"
							prepend-icon="mdi-send"
							@click="submitDeposit"
						>
							{{ __("Submit Deposit") }}
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
import format from '../../../format';
import { useUIStore } from '../../../stores/uiStore.js';
import { useToastStore } from '../../../stores/toastStore';
import { uploadFile } from '../../../utils/uploadFile';
import { isPosWarehouseSwitcher, isFundTransferManager } from '../../../utils/posWarehouseAccess';
import DateFilterField from '../shared/DateFilterField.vue';

const getTodayDate = () =>
	frappe?.datetime?.nowdate?.() || new Date().toISOString().slice(0, 10);

export default {
	name: 'DepositNew',
	mixins: [format],
	components: { DateFilterField },
	setup() {
		const router = useRouter();
		const uiStore = useUIStore();
		const toastStore = useToastStore();
		const pos_profile = ref(uiStore.posProfile || {});

		const userName = ref('');
		const userLoading = ref(false);

		// Warehouse follows the same rule used across Sales/Purchase/Material
		// Transfer/Requisition: only System Manager can pick a different
		// warehouse -- everyone else is locked to their POS profile's default.
		const canChangeWarehouse = computed(() => isPosWarehouseSwitcher());
		// Same gate as the DO Number card on Sales/Purchase/Material Transfer --
		// only BSP Admin/System Manager can back- or post-date a deposit.
		const canEditPostingDate = computed(() => isFundTransferManager());
		const warehouseOptions = ref([]);
		const warehouseLabel = ref('');
		const warehouseLoading = ref(false);
		const warehouse = ref(null);

		const depositTypeOptions = ref(['Bank Deposit', 'Cash Deposit']);
		const depositType = ref('Bank Deposit');

		const bankOptions = ref([]);
		const bankLoading = ref(false);
		const bankName = ref(null);

		const postingDate = ref(getTodayDate());
		const amount = ref(null);

		const receiptFile = ref(null);
		const receiptUrl = ref('');
		const receiptUploading = ref(false);

		const submitLoading = ref(false);
		const errorMessage = ref('');

		const userDisplay = ref('');

		const loadUser = async () => {
			userLoading.value = true;
			try {
				const { message } = await frappe.call({
					method: 'posawesome.posawesome.api.bsp_daily_deposit.get_current_user_display',
				});
				userName.value = message?.user_name || '';
				userDisplay.value = message?.user_name || message?.user || '';
			} catch (e) {
				errorMessage.value = e?.message || __('Failed to load your user record');
			} finally {
				userLoading.value = false;
			}
		};

		const loadPermittedWarehouses = async () => {
			try {
				const { message } = await frappe.call({
					method: 'bsp_engineering.api.pos_warehouse.get_pos_warehouses',
					args: {
						company: pos_profile.value?.company,
						pos_profile: pos_profile.value ? JSON.stringify(pos_profile.value) : null,
					},
				});
				const msg = message || {};
				const warehouseList = Array.isArray(msg) ? msg : (msg.warehouses || []);
				const suggestedDefault = Array.isArray(msg) ? null : (msg.default_warehouse || null);
				warehouseOptions.value = warehouseList;
				const permitted = warehouseList.map((row) => row.name);
				let defaultWh = suggestedDefault || pos_profile.value?.warehouse || null;
				if (defaultWh && permitted.length && !permitted.includes(defaultWh)) {
					defaultWh = permitted[0];
				}
				if (!defaultWh && warehouseOptions.value.length) {
					defaultWh = warehouseOptions.value[0].name;
				}
				warehouse.value = defaultWh || null;
			} catch (e) {
				console.error('Failed to load permitted warehouses', e);
				warehouseOptions.value = [];
			}
			if (!warehouseOptions.value.length && pos_profile.value?.warehouse) {
				const profileWh = pos_profile.value.warehouse;
				warehouseOptions.value = [{ name: profileWh, warehouse_name: profileWh }];
				warehouse.value = profileWh;
			}
		};

		const loadActiveWarehouse = async () => {
			try {
				const { message } = await frappe.call({
					method: 'bsp_engineering.api.pos_warehouse.get_pos_active_warehouse',
					args: {
						company: pos_profile.value?.company,
						pos_profile: pos_profile.value ? JSON.stringify(pos_profile.value) : null,
					},
				});
				const row = message || {};
				if (row.name) {
					warehouse.value = row.name;
					warehouseLabel.value = row.warehouse_name || row.name;
					return;
				}
			} catch (e) {
				console.error('Failed to load active warehouse', e);
			}
			const profileWh = pos_profile.value?.warehouse || null;
			if (profileWh) {
				warehouse.value = profileWh;
				warehouseLabel.value = profileWh;
			}
		};

		const loadWarehouses = async () => {
			warehouseLoading.value = true;
			if (canChangeWarehouse.value) {
				await loadPermittedWarehouses();
			} else {
				await loadActiveWarehouse();
			}
			warehouseLoading.value = false;
		};

		const loadDepositTypes = async () => {
			try {
				const { message } = await frappe.call({
					method: 'posawesome.posawesome.api.bsp_daily_deposit.get_deposit_type_options',
				});
				if (message?.length) depositTypeOptions.value = message;
			} catch (e) {
				console.error('Failed to load deposit types', e);
			}
		};

		const loadBanks = async () => {
			bankLoading.value = true;
			try {
				const { message } = await frappe.call({
					method: 'posawesome.posawesome.api.bsp_daily_deposit.get_bank_options',
				});
				bankOptions.value = message || [];
			} catch (e) {
				console.error('Failed to load banks', e);
			} finally {
				bankLoading.value = false;
			}
		};

		const handleReceiptSelected = async (file) => {
			const selected = Array.isArray(file) ? file[0] : file;
			if (!selected) {
				receiptUrl.value = '';
				return;
			}
			receiptUploading.value = true;
			errorMessage.value = '';
			try {
				receiptUrl.value = await uploadFile(selected);
			} catch (e) {
				errorMessage.value = e?.message || __('Failed to upload receipt');
				receiptFile.value = null;
				receiptUrl.value = '';
			} finally {
				receiptUploading.value = false;
			}
		};

		const resetForm = () => {
			postingDate.value = getTodayDate();
			warehouse.value = null;
			depositType.value = 'Bank Deposit';
			bankName.value = null;
			amount.value = null;
			receiptFile.value = null;
			receiptUrl.value = '';
		};

		const submitDeposit = async () => {
			errorMessage.value = '';

			if (!warehouse.value) {
				errorMessage.value = __('Select a Warehouse.');
				return;
			}
			if (!bankName.value) {
				errorMessage.value = __('Select a Bank Name.');
				return;
			}
			if (!Number(amount.value) || Number(amount.value) <= 0) {
				errorMessage.value = __('Enter an Amount greater than zero.');
				return;
			}
			if (!receiptUrl.value) {
				errorMessage.value = __('Attach the Acknowledgment Receipt.');
				return;
			}

			submitLoading.value = true;
			try {
				const { message } = await frappe.call({
					method: 'posawesome.posawesome.api.bsp_daily_deposit.create_daily_deposit',
					args: {
						data: {
							warehouse: warehouse.value,
							posting_date: postingDate.value,
							deposit_type: depositType.value,
							bank_name: bankName.value,
							amount: amount.value,
							acknowledgment_receipt: receiptUrl.value,
						},
					},
					freeze: true,
					freeze_message: __('Submitting deposit...'),
				});
				toastStore.show({
					title: __('Daily Deposit {0} submitted', [message?.name || '']),
					color: 'success',
				});
				resetForm();
				await router.push('/deposits/list');
			} catch (e) {
				errorMessage.value = e?.message || __('Failed to submit deposit');
			} finally {
				submitLoading.value = false;
			}
		};

		onMounted(async () => {
			await Promise.all([loadUser(), loadWarehouses(), loadDepositTypes(), loadBanks()]);
		});

		return {
			userDisplay,
			userLoading,
			canChangeWarehouse,
			canEditPostingDate,
			warehouseOptions,
			warehouseLabel,
			warehouseLoading,
			warehouse,
			depositTypeOptions,
			depositType,
			bankOptions,
			bankLoading,
			bankName,
			postingDate,
			amount,
			receiptFile,
			receiptUrl,
			receiptUploading,
			submitLoading,
			errorMessage,
			handleReceiptSelected,
			submitDeposit,
		};
	},
};
</script>

<style scoped>
@import '../invoice-shared-styles.css';

.deposit-details-grid {
	display: grid;
	grid-template-columns: repeat(2, minmax(0, 1fr));
	gap: 12px;
}

@media (max-width: 600px) {
	.deposit-details-grid {
		grid-template-columns: 1fr;
	}
}
</style>
