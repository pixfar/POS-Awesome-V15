<template>
	<div class="pa-0 h-100 invoice-shell txn-shell">
		<v-row class="h-100 ma-0 justify-center">
			<!-- Full width, same layout as the other screens. -->
			<v-col cols="12" class="h-100 pa-0">
				<v-card class="h-100 d-flex flex-column pos-themed-card purchase-invoice-card" flat>
					<v-card-text class="flex-grow-1 overflow-y-auto pa-3 pa-md-4">
						<div class="invoice-sections">
							<v-card flat class="invoice-section-card pos-themed-card create-header-card">
								<div class="create-header">
									<div class="create-header__grid">
										<div class="create-header__party">
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
												class="pos-themed-input"
												@update:search="handleEmployeeSearchUpdate"
												@update:menu="onEmployeeMenu"
											>
												<template #append-item>
													<div
														v-if="employeeHasMore"
														v-intersect="onEmployeeListIntersect"
														class="pa-2 text-center text-caption text-medium-emphasis"
													>
														{{ __("Loading more...") }}
													</div>
												</template>
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
												class="pos-themed-input"
											/>
										</div>
										<div class="create-header__metric">
											<v-text-field
												:model-value="formatCurrency(totalAmount)"
												:label="__('Total Amount')"
												:title="`${expenseRows.length} ${expenseRows.length === 1 ? __('expense') : __('expenses')}`"
												readonly
												density="compact"
												variant="outlined"
												hide-details
												class="pos-themed-input create-header__metric-field create-header__metric-field--clear"
											/>
										</div>
										<div class="create-header__field">
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
										<div class="create-header__field">
											<DateFilterField
												v-model="expenseDate"
												:label="__('Expense Date')"
												:clearable="false"
												:disabled="!canEditPostingDate"
												field-class="pos-themed-input"
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
									</div>
								</div>
							</v-card>

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
											<th style="width: 48px">{{ __("No.") }}</th>
											<th style="width: 34%; min-width: 180px">{{ __("Expense Claim Type") }}</th>
											<th style="min-width: 200px">{{ __("Description") }}</th>
											<th style="width: 18%; min-width: 150px" class="text-right">{{ __("Amount") }}</th>
											<th style="width: 48px"></th>
										</tr>
									</thead>
									<tbody>
										<tr v-for="(row, index) in expenseRows" :key="row.key">
											<td>{{ index + 1 }}</td>
											<td>
												<v-autocomplete
													v-model="row.expense_type"
													v-model:search="row.typeSearch"
													:items="expenseTypeOptions"
													item-title="name"
													item-value="name"
													:label="__('Expense Claim Type')"
													density="compact"
													variant="outlined"
													hide-details
													clearable
													class="pos-themed-input"
												>
													<template v-if="canCreateExpenseType" #append-item>
														<div v-if="canOfferNewType(row)" class="expense-type-create">
															<v-btn
																block
																color="primary"
																variant="flat"
																size="small"
																prepend-icon="mdi-plus"
																@mousedown.prevent="openCreateType(row)"
															>
																{{ __('Create "{0}"', [row.typeSearch.trim()]) }}
															</v-btn>
														</div>
													</template>
												</v-autocomplete>
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
													class="pos-themed-input expense-amount-input"
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

							<v-card flat class="invoice-section-card pos-themed-card">
								<div class="invoice-section-heading">
									<h3 class="invoice-section-heading__title">{{ __("Attachments") }}</h3>
									<span class="text-caption text-medium-emphasis">
										{{ attachmentItems.length }}/{{ maxExpenseImages }}
									</span>
								</div>
								<div class="sale-options-body">
									<v-file-input
										v-model="attachmentFiles"
										:label="__('Attach Images')"
										density="compact"
										variant="outlined"
										color="primary"
										hide-details
										multiple
										chips
										prepend-icon=""
										prepend-inner-icon="mdi-paperclip"
										accept="image/*"
										:loading="attachmentUploading"
										:disabled="attachmentUploading || attachmentItems.length >= maxExpenseImages"
										class="pos-themed-input"
										@update:model-value="handleAttachmentsSelected"
									/>
									<p class="text-caption text-medium-emphasis mt-2 mb-0">
										{{ __("Upload up to {0} images.", [maxExpenseImages]) }}
									</p>
									<div v-if="attachmentItems.length" class="expense-attachments">
										<div
											v-for="item in attachmentItems"
											:key="item.url"
											class="expense-attachments__item"
										>
											<img :src="item.preview || item.url" :alt="item.name" />
											<v-btn
												icon="mdi-close"
												size="x-small"
												variant="flat"
												color="error"
												class="expense-attachments__remove"
												@click="removeAttachment(item)"
											/>
										</div>
									</div>
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
							:disabled="submitLoading || attachmentUploading || !totalAmount"
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

		<v-dialog v-model="createTypeDialog" max-width="440">
			<v-card class="pos-themed-card">
				<v-card-title>{{ __("New Expense Claim Type") }}</v-card-title>
				<v-card-text>
					<v-text-field
						v-model="newTypeName"
						:label="__('Expense Claim Type')"
						density="compact"
						variant="outlined"
						hide-details
						autofocus
						class="pos-themed-input"
						@keyup.enter="submitNewType"
					/>
					<p class="text-caption mt-3 mb-0">
						{{ __("Default Account") }}: {{ defaultExpenseAccount }}
					</p>
				</v-card-text>
				<v-card-actions>
					<v-spacer />
					<v-btn variant="text" @click="createTypeDialog = false">{{ __("Cancel") }}</v-btn>
					<v-btn
						color="primary"
						variant="flat"
						:loading="createTypeLoading"
						:disabled="!newTypeName.trim()"
						@click="submitNewType"
					>
						{{ __("Create") }}
					</v-btn>
				</v-card-actions>
			</v-card>
		</v-dialog>
	</div>
</template>

<script>
import { useMobileErrorToast } from '../../../composables/core/useMobileErrorToast';
import { ref, computed, watch, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import format from '../../../format';
import { useUIStore } from '../../../stores/uiStore.js';
import { ensurePosProfile } from '../../../../utils/pos_profile';
import { useToastStore } from '../../../stores/toastStore';
import { uploadFile } from '../../../utils/uploadFile';
import { isPosWarehouseSwitcher, isFundTransferManager } from '../../../utils/posWarehouseAccess';
import { useWarehouseAccountSync } from '../../../composables/pos/shared/useWarehouseAccountSync';
import DateFilterField from '../shared/DateFilterField.vue';

const getTodayDate = () =>
	frappe?.datetime?.nowdate?.() || new Date().toISOString().slice(0, 10);

let rowKeySeed = 0;
const DEFAULT_EXPENSE_ACCOUNT = 'Operating Expenses - BSP';
const MAX_EXPENSE_IMAGES = 3;

const makeRow = () => ({
	key: `expense-row-${++rowKeySeed}`,
	expense_type: null,
	typeSearch: '',
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
		// Picking a warehouse selects that warehouse's own cash account.
		const { syncAccountForWarehouse } = useWarehouseAccountSync({
			warehouse,
			account: paymentAccountOverride,
			enabled: canEditPaymentAccount,
		});

		const expenseTypeOptions = ref([]);
		const canCreateExpenseType = computed(() => isFundTransferManager());
		const createTypeDialog = ref(false);
		const newTypeName = ref('');
		const createTypeRow = ref(null);
		const createTypeLoading = ref(false);
		const defaultExpenseAccount = DEFAULT_EXPENSE_ACCOUNT;
		const expenseDate = ref(getTodayDate());
		const remark = ref('');
		const maxExpenseImages = MAX_EXPENSE_IMAGES;
		const attachmentFiles = ref(null);
		const attachmentItems = ref([]);
		const attachmentUploading = ref(false);
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
				if (canSelectEmployee.value) {
					loadEmployeeOptions();
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

		// BSP Admin / System Manager: list active employees straight away (not
		// only after typing) -- 10 at a time, the next 10 loading as the list
		// is scrolled to the bottom. Keeps the already-selected one.
		const EMPLOYEE_PAGE = 10;
		const employeeHasMore = ref(false);
		let employeeSearchText = '';
		const loadEmployeeOptions = async (searchText = '', { append = false } = {}) => {
			if (!canSelectEmployee.value) return;
			if (append && (employeeSearchLoading.value || !employeeHasMore.value)) return;
			employeeSearchText = searchText;
			employeeSearchLoading.value = true;
			try {
				const pageStart = append ? employeeOptions.value.filter((e) => !e?._pinned).length : 0;
				const { message } = await frappe.call({
					method: 'posawesome.posawesome.api.expense_claims.search_employees',
					args: { search_text: searchText, limit: EMPLOYEE_PAGE, page_start: pageStart },
				});
				if (searchText !== employeeSearchText) return; // a newer search replaced this one
				const rows = message || [];
				employeeHasMore.value = rows.length === EMPLOYEE_PAGE;
				if (append) {
					const known = new Set(employeeOptions.value.map((e) => e?.name));
					employeeOptions.value = [...employeeOptions.value, ...rows.filter((e) => !known.has(e.name))];
					return;
				}
				const selected = employeeOptions.value.find((e) => e?.name === selectedEmployee.value);
				employeeOptions.value =
					selected && !rows.some((e) => e.name === selected.name)
						? [{ ...selected, _pinned: true }, ...rows]
						: rows;
			} catch (e) {
				console.error('Failed to search employees', e);
			} finally {
				employeeSearchLoading.value = false;
			}
		};
		const onEmployeeListIntersect = (a) => {
			const isIntersecting = typeof a === 'boolean' ? a : Array.isArray(a) && !!a[0]?.isIntersecting;
			if (isIntersecting) loadEmployeeOptions(employeeSearchText, { append: true });
		};

		// Opening the picker always shows the full employee list.
		let employeeListIsFiltered = false;
		const onEmployeeMenu = (open) => {
			if (open && (employeeListIsFiltered || employeeOptions.value.length <= 1)) {
				employeeListIsFiltered = false;
				loadEmployeeOptions();
			}
		};

		const handleEmployeeSearchUpdate = (term) => {
			if (employeeSearchTimeout) clearTimeout(employeeSearchTimeout);
			const text = (term || '').trim();
			// Typing the selected employee's name into the box isn't a new search.
			const selected = employeeOptions.value.find((e) => e?.name === selectedEmployee.value);
			if (selected && (text === selected.employee_name || text === selected.name)) return;
			if (text.length === 1) return;
			employeeListIsFiltered = Boolean(text);
			employeeSearchTimeout = setTimeout(() => loadEmployeeOptions(text), 300);
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

		const canOfferNewType = (row) => {
			const term = (row.typeSearch || '').trim();
			if (!term) return false;
			return !expenseTypeOptions.value.some(
				(option) => String(option.name).toLowerCase() === term.toLowerCase(),
			);
		};

		const openCreateType = (row) => {
			createTypeRow.value = row;
			newTypeName.value = (row.typeSearch || '').trim();
			createTypeDialog.value = true;
		};

		const submitNewType = async () => {
			const name = newTypeName.value.trim();
			if (!name || createTypeLoading.value) return;
			createTypeLoading.value = true;
			try {
				const { message } = await frappe.call({
					method: 'posawesome.posawesome.api.expense_claims.create_expense_claim_type',
					args: { expense_type: name },
				});
				const created = message?.name || name;
				if (!expenseTypeOptions.value.some((option) => option.name === created)) {
					expenseTypeOptions.value = [...expenseTypeOptions.value, { name: created }].sort((a, b) =>
						String(a.name).localeCompare(String(b.name)),
					);
				}
				if (createTypeRow.value) {
					createTypeRow.value.expense_type = created;
					createTypeRow.value.typeSearch = '';
				}
				createTypeDialog.value = false;
				toastStore.show({
					title: __('Expense Claim Type {0} created', [created]),
					color: 'success',
				});
			} catch (e) {
				toastStore.show({
					title: e?.message || __('Could not create Expense Claim Type'),
					color: 'error',
				});
			} finally {
				createTypeLoading.value = false;
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

		const clearAttachmentPreviews = () => {
			for (const item of attachmentItems.value) {
				if (item.preview) URL.revokeObjectURL(item.preview);
			}
			attachmentItems.value = [];
			attachmentFiles.value = null;
		};

		const handleAttachmentsSelected = async (files) => {
			const selected = (Array.isArray(files) ? files : files ? [files] : []).filter(Boolean);
			if (!selected.length) return;
			attachmentFiles.value = null;

			const room = maxExpenseImages - attachmentItems.value.length;
			if (room <= 0) {
				errorMessage.value = __('You can attach at most {0} images.', [maxExpenseImages]);
				return;
			}

			const images = selected.filter((file) => String(file.type || '').startsWith('image/'));
			if (!images.length || images.length !== selected.length) {
				errorMessage.value = __('Only image files can be attached.');
				if (!images.length) return;
			} else {
				errorMessage.value = '';
			}

			const incoming = images.slice(0, room);
			if (images.length > room) {
				errorMessage.value = __('You can attach at most {0} images.', [maxExpenseImages]);
			}

			attachmentUploading.value = true;
			try {
				for (const file of incoming) {
					const url = await uploadFile(file);
					attachmentItems.value.push({
						url,
						name: file.name,
						preview: URL.createObjectURL(file),
					});
				}
			} catch (e) {
				errorMessage.value = e?.message || __('Failed to upload image');
			} finally {
				attachmentUploading.value = false;
			}
		};

		const removeAttachment = (item) => {
			if (item.preview) URL.revokeObjectURL(item.preview);
			attachmentItems.value = attachmentItems.value.filter((row) => row.url !== item.url);
		};

		const resetForm = () => {
			expenseDate.value = getTodayDate();
			remark.value = '';
			expenseRows.value = [makeRow()];
			clearAttachmentPreviews();
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
			if (attachmentUploading.value) {
				errorMessage.value = __('Wait for the images to finish uploading.');
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
							attachments: attachmentItems.value.map((item) => item.url),
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
			// A direct page load can land here before anything has put the
			// active POS Profile in uiStore -- fetch it ourselves so company
			// (and so the Accounts dropdown) is never left blank.
			if (!uiStore.posProfile?.name) {
				try {
					const profile = await ensurePosProfile();
					if (profile?.name) uiStore.setPosProfile(profile);
				} catch (e) {
					console.error('Failed to resolve active POS profile', e);
				}
			}
			watch(
				() => pos_profile.value?.company,
				() => {
					// Default to whatever the cashier already picked elsewhere
					// this session (uiStore.activeSaleAccount, shared with the
					// Sales/Purchase Invoice and standalone Payment screens'
					// own "Accounts" card), falling back to this POS Profile's
					// own change account only when nothing has been picked yet
					// -- the user can still pick a different one from the
					// dropdown.
					paymentAccountOverride.value =
						uiStore.activeSaleAccount || pos_profile.value?.account_for_change_amount || null;
					// ...then make sure it belongs to the selected warehouse.
					syncAccountForWarehouse();
					loadCashInHandAccounts();
				},
				{ immediate: true },
			);
			// Keep every other "Accounts" picker in sync with whatever gets
			// picked here.
			watch(paymentAccountOverride, (val) => {
				uiStore.setActiveSaleAccount(val);
			});
			await Promise.all([loadEmployee(), loadExpenseTypes(), loadWarehouse()]);
		});

		// Errors visible on phones too (the inline alert sits under the bottom bar).
		useMobileErrorToast(errorMessage);

		return {
			employee,
			employeeLoading,
			employeeDisplay,
			canSelectEmployee,
			selectedEmployee,
			employeeOptions,
			onEmployeeMenu,
			employeeHasMore,
			onEmployeeListIntersect,
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
			canCreateExpenseType,
			canOfferNewType,
			openCreateType,
			submitNewType,
			createTypeDialog,
			newTypeName,
			createTypeLoading,
			defaultExpenseAccount,
			expenseDate,
			remark,
			maxExpenseImages,
			attachmentFiles,
			attachmentItems,
			attachmentUploading,
			handleAttachmentsSelected,
			removeAttachment,
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

.expense-type-create {
	padding: 8px 10px 10px;
	background: #e6f4f6;
	border-top: 1px solid rgba(0, 151, 167, 0.18);
}

/* Amount wide enough to read and right-aligned like other money columns. */
.expense-amount-input :deep(input) {
	text-align: right;
	font-variant-numeric: tabular-nums;
}

.expense-attachments {
	display: flex;
	flex-wrap: wrap;
	gap: 10px;
	margin-top: 12px;
}

.expense-attachments__item {
	position: relative;
	width: 88px;
	height: 88px;
	border-radius: 8px;
	overflow: hidden;
	border: 1px solid rgba(0, 151, 167, 0.28);
	background: #f4fbfb;
}

.expense-attachments__item img {
	width: 100%;
	height: 100%;
	object-fit: cover;
	display: block;
}

.expense-attachments__remove {
	position: absolute;
	top: 4px;
	right: 4px;
}
</style>
