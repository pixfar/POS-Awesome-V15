<template>
	<div class="pa-0 h-100 invoice-shell">
		<v-row class="h-100 ma-0 justify-center">
			<v-col cols="12" md="9" lg="7" class="h-100 pa-0">
				<v-card class="h-100 d-flex flex-column pos-themed-card purchase-invoice-card" flat>
					<v-card-text class="flex-grow-1 overflow-y-auto pa-3 pa-md-4">
						<div class="invoice-sections">
							<div class="invoice-top-grid purchase-top-grid">
								<v-card flat class="invoice-section-card pos-themed-card">
									<div class="invoice-section-heading">
										<h3 class="invoice-section-heading__title">{{ __("From Employee") }}</h3>
									</div>
									<div class="sale-options-body">
										<v-text-field
											:model-value="employeeDisplay"
											:label="__('Employee')"
											density="compact"
											variant="outlined"
											color="primary"
											hide-details
											readonly
											:loading="employeeLoading"
											prepend-inner-icon="mdi-account-outline"
											class="pos-themed-input"
										/>
									</div>
								</v-card>

								<v-card flat class="invoice-section-card pos-themed-card outstanding-panel">
									<div class="outstanding-panel__inner">
										<div class="outstanding-panel__label">{{ __("Total Amount") }}</div>
										<div class="outstanding-panel__amount outstanding-panel__amount--clear">
											{{ formatCurrency(totalAmount) }}
										</div>
										<div class="text-caption text-medium-emphasis">
											{{ expenseRows.length }}
											{{ expenseRows.length === 1 ? __("expense") : __("expenses") }}
										</div>
									</div>
								</v-card>

								<v-card flat class="invoice-section-card pos-themed-card sale-options-card">
									<div class="invoice-section-heading">
										<h3 class="invoice-section-heading__title">{{ __("Date") }}</h3>
									</div>
									<div class="sale-options-body">
										<DateFilterField
											v-model="expenseDate"
											:label="__('Expense Date')"
											:clearable="false"
											field-class="pos-themed-input"
										/>
									</div>
								</v-card>
							</div>

							<v-card flat class="invoice-section-card invoice-items-card pos-themed-card">
								<div class="invoice-section-heading d-flex align-center justify-space-between">
									<h3 class="invoice-section-heading__title">{{ __("Expenses") }}</h3>
									<v-btn
										size="small"
										variant="tonal"
										color="primary"
										prepend-icon="mdi-plus"
										class="text-none"
										@click="addRow"
									>
										{{ __("Add Row") }}
									</v-btn>
								</div>

								<v-table density="comfortable" class="expense-rows-table">
									<thead>
										<tr>
											<th style="width: 40px">{{ __("No.") }}</th>
											<th style="min-width: 180px">{{ __("Expense Claim Type") }}</th>
											<th style="min-width: 200px">{{ __("Description") }}</th>
											<th style="width: 140px">{{ __("Amount") }}</th>
											<th style="width: 160px">{{ __("Sanctioned Amount") }}</th>
											<th style="width: 48px"></th>
										</tr>
									</thead>
									<tbody>
										<tr v-for="(row, index) in expenseRows" :key="row.key">
											<td>{{ index + 1 }}</td>
											<td>
												<v-select
													v-model="row.expense_type"
													:items="expenseTypeOptions"
													item-title="name"
													item-value="name"
													density="compact"
													variant="outlined"
													hide-details
													class="pos-themed-input"
												/>
											</td>
											<td>
												<v-text-field
													v-model="row.description"
													density="compact"
													variant="outlined"
													hide-details
													class="pos-themed-input"
												/>
											</td>
											<td>
												<v-text-field
													v-model.number="row.amount"
													type="number"
													min="0"
													density="compact"
													variant="outlined"
													hide-details
													class="pos-themed-input"
													@update:model-value="syncSanctionedAmount(row)"
												/>
											</td>
											<td>
												<v-text-field
													v-model.number="row.sanctioned_amount"
													type="number"
													min="0"
													density="compact"
													variant="outlined"
													hide-details
													class="pos-themed-input"
												/>
											</td>
											<td>
												<v-btn
													icon="mdi-delete-outline"
													size="small"
													variant="text"
													color="error"
													:disabled="expenseRows.length === 1"
													@click="removeRow(index)"
												/>
											</td>
										</tr>
									</tbody>
								</v-table>
							</v-card>

							<v-card flat class="invoice-section-card pos-themed-card notes-section-card">
								<div class="invoice-section-heading">
									<h3 class="invoice-section-heading__title">{{ __("Remark") }}</h3>
								</div>
								<div class="sale-options-body">
									<v-textarea
										v-model="remark"
										:label="__('Remark')"
										variant="outlined"
										density="compact"
										hide-details
										rows="2"
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
							<span class="purchase-bottom-bar__label">{{ __("Total Amount") }}</span>
							<strong class="purchase-bottom-bar__amount">{{ formatCurrency(totalAmount) }}</strong>
							<span class="purchase-bottom-bar__meta">
								{{ expenseRows.length }}
								{{ expenseRows.length === 1 ? __("expense") : __("expenses") }}
							</span>
						</div>
						<v-btn
							:loading="submitLoading"
							:disabled="submitLoading || !totalAmount"
							size="large"
							color="primary"
							class="text-none purchase-pay-btn"
							prepend-icon="mdi-send"
							@click="submitExpenseClaim"
						>
							{{ __("Submit Expense Claim") }}
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
import { useToastStore } from '../../../stores/toastStore';
import DateFilterField from '../shared/DateFilterField.vue';

const getTodayDate = () =>
	frappe?.datetime?.nowdate?.() || new Date().toISOString().slice(0, 10);

let rowKeySeed = 0;
const makeRow = () => ({
	key: `expense-row-${++rowKeySeed}`,
	expense_type: null,
	description: '',
	amount: null,
	sanctioned_amount: null,
});

export default {
	name: 'ExpenseNew',
	mixins: [format],
	components: { DateFilterField },
	setup() {
		const router = useRouter();
		const toastStore = useToastStore();

		const employee = ref(null);
		const employeeLoading = ref(false);
		const expenseTypeOptions = ref([]);
		const expenseDate = ref(getTodayDate());
		const remark = ref('');
		const expenseRows = ref([makeRow()]);
		const submitLoading = ref(false);
		const errorMessage = ref('');

		const employeeDisplay = computed(() => {
			if (!employee.value) return '';
			return `${employee.value.name} - ${employee.value.employee_name || ''}`;
		});

		const totalAmount = computed(() =>
			expenseRows.value.reduce((sum, row) => sum + (Number(row.amount) || 0), 0),
		);

		const addRow = () => {
			expenseRows.value.push(makeRow());
		};

		const removeRow = (index) => {
			if (expenseRows.value.length === 1) return;
			expenseRows.value.splice(index, 1);
		};

		const syncSanctionedAmount = (row) => {
			row.sanctioned_amount = row.amount;
		};

		const loadEmployee = async () => {
			employeeLoading.value = true;
			try {
				const { message } = await frappe.call({
					method: 'posawesome.posawesome.api.expense_claims.get_current_employee',
				});
				employee.value = message || null;
			} catch (e) {
				errorMessage.value = e?.message || __('Failed to load your Employee record');
			} finally {
				employeeLoading.value = false;
			}
		};

		const loadExpenseTypes = async () => {
			try {
				const { message } = await frappe.call({
					method: 'posawesome.posawesome.api.expense_claims.get_expense_claim_types',
				});
				expenseTypeOptions.value = message || [];
			} catch (e) {
				console.error('Failed to load expense claim types', e);
			}
		};

		const resetForm = () => {
			expenseDate.value = getTodayDate();
			remark.value = '';
			expenseRows.value = [makeRow()];
		};

		const submitExpenseClaim = async () => {
			errorMessage.value = '';

			const validRows = expenseRows.value.filter((row) => Number(row.amount) > 0);
			if (!validRows.length) {
				errorMessage.value = __('Add at least one expense with an amount.');
				return;
			}
			if (validRows.some((row) => !row.expense_type)) {
				errorMessage.value = __('Select an Expense Claim Type for every expense row.');
				return;
			}

			submitLoading.value = true;
			try {
				const { message } = await frappe.call({
					method: 'posawesome.posawesome.api.expense_claims.create_expense_claim',
					args: {
						data: {
							expense_date: expenseDate.value,
							remark: remark.value,
							expenses: validRows.map((row) => ({
								expense_type: row.expense_type,
								description: row.description,
								amount: row.amount,
								sanctioned_amount: row.sanctioned_amount,
							})),
						},
					},
					freeze: true,
					freeze_message: __('Submitting expense claim...'),
				});
				toastStore.show({
					title: __('Expense Claim {0} submitted', [message?.name || '']),
					color: 'success',
				});
				resetForm();
				await router.push('/expenses/list');
			} catch (e) {
				errorMessage.value = e?.message || __('Failed to submit expense claim');
			} finally {
				submitLoading.value = false;
			}
		};

		onMounted(async () => {
			await Promise.all([loadEmployee(), loadExpenseTypes()]);
		});

		return {
			employee,
			employeeLoading,
			employeeDisplay,
			expenseTypeOptions,
			expenseDate,
			remark,
			expenseRows,
			totalAmount,
			submitLoading,
			errorMessage,
			addRow,
			removeRow,
			syncSanctionedAmount,
			submitExpenseClaim,
		};
	},
};
</script>

<style scoped>
@import '../invoice-shared-styles.css';

.expense-rows-table :deep(td) {
	vertical-align: middle;
	padding-top: 6px;
	padding-bottom: 6px;
}
</style>
