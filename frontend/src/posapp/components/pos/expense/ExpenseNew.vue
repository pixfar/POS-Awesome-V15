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
										<h3 class="invoice-section-heading__title">{{ __("From Employee") }}</h3>
									</div>
									<div class="sale-options-body">
										<v-autocomplete
											v-if="canSelectEmployee"
											v-model="selectedEmployee"
											v-model:search="employeeSearchQuery"
											:items="employeeOptions"
											item-title="employee_name"
											item-value="name"
											:label="__('Employee')"
											density="compact"
											variant="outlined"
											color="primary"
											hide-details
											:loading="employeeLoading || employeeSearchLoading"
											:no-data-text="
												employeeSearchQuery && employeeSearchQuery.length < 2
													? __('Type at least 2 characters')
													: __('No employees found')
											"
											prepend-inner-icon="mdi-account-outline"
											class="pos-themed-input mb-2"
											@update:search="handleEmployeeSearchUpdate"
										>
											<template #item="{ props: itemProps, item }">
												<v-list-item v-bind="itemProps" :title="undefined">
													<v-list-item-title>{{ item.raw.employee_name }}</v-list-item-title>
													<v-list-item-subtitle>{{ item.raw.name }}</v-list-item-subtitle>
												</v-list-item>
											</template>
										</v-autocomplete>
										<v-text-field
											v-else
											:model-value="employeeDisplay"
											:label="__('Employee')"
											density="compact"
											variant="outlined"
											color="primary"
											hide-details
											readonly
											:loading="employeeLoading"
											prepend-inner-icon="mdi-account-outline"
											class="pos-themed-input mb-2"
										/>
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
										<h3 class="invoice-section-heading__title">
											{{ canEditPaymentAccount ? __("Date & Accounts") : __("Date") }}
										</h3>
									</div>
									<div class="sale-options-body">
										<DateFilterField
											v-model="expenseDate"
											:label="__('Expense Date')"
											:clearable="false"
											:disabled="!canEditPostingDate"
											field-class="pos-themed-input"
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
import { ref, computed, watch, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import format from '../../../format';
import { useUIStore } from '../../../stores/uiStore.js';
import { useToastStore } from '../../../stores/toastStore';
import { isPosWarehouseSwitcher, isFundTransferManager } from '../../../utils/posWarehouseAccess';
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
		const uiStore = useUIStore();
		const toastStore = useToastStore();
		const pos_profile = ref(uiStore.posProfile || {});

		const employee = ref(null);
		const employeeLoading = ref(false);
		// "From Employee" override -- System Manager / BSP Admin only, so an
		// admin can create this expense on behalf of a different employee
		// instead of only their own; re-verified server-side, this flag is
		// UX-only. Defaults to the admin's own employee (if they have one).
		const canSelectEmployee = computed(() => isFundTransferManager());
		const selectedEmployee = ref(null);
		const employeeOptions = ref([]);
		const employeeSearchQuery = ref('');
		const employeeSearchLoading = ref(false);
		let employeeSearchTimeout = null;

		// Warehouse follows the same rule used across Sales/Purchase/Material
		// Transfer/Requisition/Deposit: only System Manager can pick a
		// different warehouse -- everyone else is locked to their POS
		// profile's default.
		const canChangeWarehouse = computed(() => isPosWarehouseSwitcher());
		// Same gate as the DO Number card on Sales/Purchase/Material Transfer --
		// only BSP Admin/System Manager can back- or post-date an expense.
		const canEditPostingDate = computed(() => isFundTransferManager());
		// "Accounts" override -- System Manager / BSP Admin only, same feature
		// as the Purchase Invoice screen's "Accounts" card. Defaults to the
		// active POS Profile's own account_for_change_amount, but an admin can
		// route this expense's payout through a different showroom's cash
		// account instead; re-verified server-side, this flag is UX-only.
		const canEditPaymentAccount = computed(() => isFundTransferManager());
		const cashAccountOptions = ref([]);
		const cashAccountsLoading = ref(false);
		const paymentAccountOverride = ref(null);
		const warehouseOptions = ref([]);
		const warehouseLabel = ref('');
		const warehouseLoading = ref(false);
		const warehouse = ref(null);

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
				if (canSelectEmployee.value && employee.value) {
					// Default the picker to the admin's own employee -- they can
					// still search and pick someone else.
					selectedEmployee.value = employee.value.name;
					employeeOptions.value = [employee.value];
				}
			} catch (e) {
				// An admin with no Employee record of their own can still create
				// an expense for someone else via the picker below -- only treat
				// this as a page error for a regular POS user, who has no such
				// fallback.
				if (!canSelectEmployee.value) {
					errorMessage.value = e?.message || __('Failed to load your Employee record');
				}
			} finally {
				employeeLoading.value = false;
			}
		};

		const handleEmployeeSearchUpdate = (term) => {
			if (employeeSearchTimeout) clearTimeout(employeeSearchTimeout);
			if (!term || term.trim().length < 2) return;
			employeeSearchTimeout = setTimeout(async () => {
				employeeSearchLoading.value = true;
				try {
					const { message } = await frappe.call({
						method: 'posawesome.posawesome.api.expense_claims.search_employees',
						args: { search_text: term.trim(), limit: 20 },
					});
					employeeOptions.value = message || [];
				} catch (e) {
					console.error('Failed to search employees', e);
				} finally {
					employeeSearchLoading.value = false;
				}
			}, 300);
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

		const loadWarehouse = async () => {
			warehouseLoading.value = true;
			if (canChangeWarehouse.value) {
				await loadPermittedWarehouses();
			} else {
				await loadActiveWarehouse();
			}
			warehouseLoading.value = false;
		};

		const loadCashInHandAccounts = async () => {
			const company = pos_profile.value?.company;
			if (!canEditPaymentAccount.value || !company) return;
			cashAccountsLoading.value = true;
			try {
				const { message } = await frappe.call({
					method: 'posawesome.posawesome.api.payment_processing.utils.get_cash_in_hand_accounts',
					args: { company },
				});
				cashAccountOptions.value = message || [];
			} catch (e) {
				console.error('Failed to load Cash In Hand accounts', e);
				cashAccountOptions.value = [];
			} finally {
				cashAccountsLoading.value = false;
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
			if (canSelectEmployee.value && !selectedEmployee.value) {
				errorMessage.value = __('Select an Employee.');
				return;
			}

			submitLoading.value = true;
			try {
				const { message } = await frappe.call({
					method: 'posawesome.posawesome.api.expense_claims.create_expense_claim',
					args: {
						data: {
							expense_date: expenseDate.value,
							warehouse: warehouse.value,
							remark: remark.value,
							// Both overrides are re-verified server-side (System Manager /
							// BSP Admin) -- see expense_claims.create_expense_claim.
							employee: canSelectEmployee.value ? (selectedEmployee.value || null) : null,
							payment_account: canEditPaymentAccount.value
								? (paymentAccountOverride.value || null)
								: null,
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
			// pos_profile started as a one-time snapshot of uiStore.posProfile,
			// which can still be empty at that exact moment (e.g. a fresh page
			// load lands here before the store finishes hydrating) -- without
			// this, pos_profile.value.company silently stays blank forever and
			// the Accounts dropdown below has nothing to fetch. Same pattern
			// Purchase Invoice's own "Accounts" card uses.
			watch(
				() => uiStore.posProfile,
				(p) => {
					if (p) pos_profile.value = p;
				},
				{ immediate: true },
			);
			watch(
				() => pos_profile.value?.company,
				() => {
					// Default to this POS Profile's own change account -- the
					// user can still pick a different one from the dropdown.
					paymentAccountOverride.value = pos_profile.value?.account_for_change_amount || null;
					loadCashInHandAccounts();
				},
				{ immediate: true },
			);
			await Promise.all([loadEmployee(), loadExpenseTypes(), loadWarehouse()]);
		});

		return {
			employee,
			employeeLoading,
			employeeDisplay,
			canSelectEmployee,
			selectedEmployee,
			employeeOptions,
			employeeSearchQuery,
			employeeSearchLoading,
			handleEmployeeSearchUpdate,
			canChangeWarehouse,
			canEditPostingDate,
			canEditPaymentAccount,
			cashAccountOptions,
			cashAccountsLoading,
			paymentAccountOverride,
			warehouseOptions,
			warehouseLabel,
			warehouseLoading,
			warehouse,
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
