<template>
	<div class="pa-0 h-100 invoice-shell txn-shell">
		<v-row class="h-100 ma-0 justify-center">
			<v-col cols="12" md="10" lg="8" class="h-100 pa-0">
				<v-card class="h-100 d-flex flex-column pos-themed-card purchase-invoice-card" flat>
					<v-card-text class="flex-grow-1 overflow-y-auto pa-3 pa-md-4">
						<div class="invoice-sections">
							<div class="invoice-top-grid purchase-top-grid">
								<v-card flat class="invoice-section-card pos-themed-card">
									<div class="invoice-section-heading">
										<h3 class="invoice-section-heading__title">{{ __("Production") }}</h3>
									</div>
									<div class="sale-options-body">
										<DateFilterField
											v-model="productionDate"
											:label="__('Date')"
											:clearable="false"
											field-class="pos-themed-input mb-2"
										/>
										<v-text-field
											v-model.number="totalWorkKg"
											type="number"
											min="0"
											:label="__('Total Work (KG)')"
											density="compact"
											variant="outlined"
											hide-details
											prepend-inner-icon="mdi-weight-kilogram"
											class="pos-themed-input mb-2"
										/>
										<v-text-field
											v-model.number="ratePerKg"
											type="number"
											min="0"
											:label="__('Rate per KG')"
											density="compact"
											variant="outlined"
											hide-details
											class="pos-themed-input"
										/>
									</div>
								</v-card>

								<v-card flat class="invoice-section-card pos-themed-card outstanding-panel">
									<div class="outstanding-panel__inner">
										<div class="outstanding-panel__label">{{ __("Total Wage") }}</div>
										<div class="outstanding-panel__amount outstanding-panel__amount--clear">
											{{ formatCurrency(totalWage) }}
										</div>
										<div class="text-caption text-medium-emphasis">
											{{ __("Per point") }}: {{ formatCurrency(perPointRate) }}
										</div>
									</div>
								</v-card>

								<v-card flat class="invoice-section-card pos-themed-card sale-options-card">
									<div class="invoice-section-heading">
										<h3 class="invoice-section-heading__title">{{ __("Workers") }}</h3>
									</div>
									<div class="sale-options-body">
										<div class="text-body-2 mb-1">
											{{ __("Present") }}: <strong>{{ employees.length }}</strong>
										</div>
										<div class="text-body-2 mb-2">
											{{ __("Total Points") }}: <strong>{{ formatFloat(totalPoints) }}</strong>
										</div>
										<v-btn
											size="small"
											variant="tonal"
											color="primary"
											prepend-icon="mdi-account-check-outline"
											class="text-none"
											:loading="attendanceLoading"
											@click="fetchAttendance"
										>
											{{ __("Fetch Attendance") }}
										</v-btn>
									</div>
								</v-card>
							</div>

							<v-card flat class="invoice-section-card invoice-items-card pos-themed-card">
								<div class="invoice-section-heading">
									<h3 class="invoice-section-heading__title">{{ __("Present Employees") }}</h3>
								</div>
								<div class="purchase-search-toolbar">
									<v-autocomplete
										v-model:search="employeeSearchQuery"
										:model-value="null"
										:items="employeeOptions"
										:loading="employeeSearchLoading"
										item-title="employee_name"
										item-value="employee"
										return-object
										:label="__('Add employee by name or ID')"
										:custom-filter="() => true"
										:no-data-text="__('Type at least 2 characters')"
										prepend-inner-icon="mdi-account-plus-outline"
										variant="solo"
										density="compact"
										hide-details
										class="pos-themed-input"
										@update:search="handleEmployeeSearch"
										@update:model-value="addEmployee"
									>
										<template #item="{ props: itemProps, item }">
											<v-list-item v-bind="itemProps" :title="undefined">
												<v-list-item-title>{{ item.raw.employee_name }}</v-list-item-title>
												<v-list-item-subtitle>
													{{ item.raw.employee }} · {{ __("Point") }} {{ formatFloat(item.raw.point) }}
												</v-list-item-subtitle>
											</v-list-item>
										</template>
									</v-autocomplete>
								</div>

								<v-table density="comfortable" class="molding-rows-table">
									<thead>
										<tr>
											<th style="width: 40px">{{ __("No.") }}</th>
											<th>{{ __("Employee") }}</th>
											<th class="text-right" style="width: 110px">{{ __("Point") }}</th>
											<th class="text-right" style="width: 150px">{{ __("Daily Salary") }}</th>
											<th style="width: 48px"></th>
										</tr>
									</thead>
									<tbody>
										<tr v-for="(row, index) in employees" :key="row.employee">
											<td>{{ index + 1 }}</td>
											<td>
												<div>{{ row.employee_name }}</div>
												<div class="text-caption text-medium-emphasis">{{ row.employee }}</div>
											</td>
											<td class="text-right">
												<span :class="{ 'text-error': !(Number(row.point) > 0) }">
													{{ formatFloat(row.point) }}
												</span>
											</td>
											<td class="text-right">{{ formatCurrency(dailySalary(row)) }}</td>
											<td>
												<v-btn
													icon="mdi-delete-outline"
													size="small"
													variant="text"
													color="error"
													@click="employees.splice(index, 1)"
												/>
											</td>
										</tr>
										<tr v-if="!employees.length">
											<td colspan="5" class="text-center text-medium-emphasis py-4">
												{{ __("Fetch attendance or add employees") }}
											</td>
										</tr>
									</tbody>
								</v-table>
								<div class="text-caption text-medium-emphasis px-3 pb-2">
									{{ __("Point comes from each Employee's Molding Point. Wage = Total Work (KG) x Rate per KG, split by point.") }}
								</div>
							</v-card>

							<v-alert v-if="zeroPointEmployees.length" type="warning" density="compact" variant="tonal">
								{{ __("These employees have no Molding Point and get no wage: {0}", [zeroPointEmployees.join(", ")]) }}
							</v-alert>
							<v-alert v-if="errorMessage" type="error" density="compact">
								{{ errorMessage }}
							</v-alert>
						</div>
					</v-card-text>

					<div class="purchase-bottom-bar">
						<div class="purchase-bottom-bar__summary">
							<span class="purchase-bottom-bar__label">{{ __("Total Wage") }}</span>
							<strong class="purchase-bottom-bar__amount">{{ formatCurrency(totalWage) }}</strong>
							<span class="purchase-bottom-bar__meta">
								{{ employees.length }} {{ employees.length === 1 ? __("worker") : __("workers") }}
							</span>
						</div>
						<v-btn
							:loading="submitLoading"
							:disabled="submitLoading || !canSubmit"
							size="large"
							color="primary"
							class="text-none purchase-pay-btn"
							prepend-icon="mdi-send"
							@click="submit"
						>
							{{ __("Submit Production") }}
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
import DateFilterField from '../shared/DateFilterField.vue';
import { useToastStore } from '../../../stores/toastStore';
import { isFundTransferManager } from '../../../utils/posWarehouseAccess';

const API = 'posawesome.posawesome.api.molding';
const getTodayDate = () => frappe?.datetime?.nowdate?.() || new Date().toISOString().slice(0, 10);

export default {
	name: 'MoldingProductionNew',
	mixins: [format],
	components: { DateFilterField },
	setup() {
		const router = useRouter();
		const toastStore = useToastStore();

		const productionDate = ref(getTodayDate());
		const totalWorkKg = ref(null);
		const ratePerKg = ref(null);
		const employees = ref([]);
		const attendanceLoading = ref(false);
		const submitLoading = ref(false);
		const errorMessage = ref('');

		const employeeSearchQuery = ref('');
		const employeeOptions = ref([]);
		const employeeSearchLoading = ref(false);
		let employeeSearchTimeout = null;

		// Same maths as bsp_engineering's MoldingDailyProduction.validate --
		// shown live here, recomputed server-side on submit.
		const totalWage = computed(() => (Number(totalWorkKg.value) || 0) * (Number(ratePerKg.value) || 0));
		const totalPoints = computed(() =>
			employees.value.reduce((sum, row) => sum + (Number(row.point) || 0), 0),
		);
		const perPointRate = computed(() => (totalPoints.value > 0 ? totalWage.value / totalPoints.value : 0));
		const dailySalary = (row) => (Number(row.point) || 0) * perPointRate.value;
		const zeroPointEmployees = computed(() =>
			employees.value.filter((row) => !(Number(row.point) > 0)).map((row) => row.employee_name || row.employee),
		);
		const canSubmit = computed(
			() => Number(totalWorkKg.value) > 0 && employees.value.length > 0 && totalPoints.value > 0,
		);

		const mergeEmployees = (rows) => {
			const existing = new Set(employees.value.map((row) => row.employee));
			let added = 0;
			for (const row of rows || []) {
				if (!row?.employee || existing.has(row.employee)) continue;
				existing.add(row.employee);
				employees.value.push({
					employee: row.employee,
					employee_name: row.employee_name,
					point: Number(row.point) || 0,
				});
				added += 1;
			}
			return added;
		};

		const fetchAttendance = async () => {
			errorMessage.value = '';
			attendanceLoading.value = true;
			try {
				const { message } = await frappe.call({
					method: `${API}.fetch_attendance`,
					args: { date: productionDate.value },
				});
				const added = mergeEmployees(message);
				toastStore.show({ title: __('{0} employees added', [added]), color: added ? 'success' : 'info' });
			} catch (e) {
				errorMessage.value = e?.message || __('Failed to fetch attendance');
			} finally {
				attendanceLoading.value = false;
			}
		};

		const handleEmployeeSearch = (term) => {
			if (employeeSearchTimeout) clearTimeout(employeeSearchTimeout);
			if (!term || term.trim().length < 2) return;
			employeeSearchTimeout = setTimeout(async () => {
				employeeSearchLoading.value = true;
				try {
					const { message } = await frappe.call({
						method: `${API}.search_employees`,
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

		const addEmployee = (row) => {
			if (!row) return;
			mergeEmployees([row]);
			employeeSearchQuery.value = '';
		};

		const loadDefaultRate = async () => {
			try {
				const { message } = await frappe.call({ method: `${API}.get_default_rate_per_kg` });
				if (ratePerKg.value === null) ratePerKg.value = Number(message) || 0;
			} catch (e) {
				console.error('Failed to load default rate per KG', e);
			}
		};

		const submit = async () => {
			errorMessage.value = '';
			if (!canSubmit.value) return;
			submitLoading.value = true;
			try {
				const { message } = await frappe.call({
					method: `${API}.create_daily_production`,
					args: {
						data: {
							date: productionDate.value,
							total_work_kg: totalWorkKg.value,
							rate_per_kg: ratePerKg.value,
							present_employees: employees.value.map((row) => ({
								employee: row.employee,
								point: row.point,
							})),
						},
					},
					freeze: true,
					freeze_message: __('Submitting production...'),
				});
				toastStore.show({ title: __('{0} submitted', [message?.name || '']), color: 'success' });
				await router.push(message?.name ? `/molding-production/${message.name}` : '/molding-production/list');
			} catch (e) {
				errorMessage.value = e?.message || __('Failed to submit production');
			} finally {
				submitLoading.value = false;
			}
		};

		onMounted(() => {
			if (!isFundTransferManager()) {
				router.replace('/molding-production/list');
				return;
			}
			loadDefaultRate();
		});

		return {
			productionDate,
			totalWorkKg,
			ratePerKg,
			employees,
			attendanceLoading,
			submitLoading,
			errorMessage,
			employeeSearchQuery,
			employeeOptions,
			employeeSearchLoading,
			totalWage,
			totalPoints,
			perPointRate,
			dailySalary,
			zeroPointEmployees,
			canSubmit,
			fetchAttendance,
			handleEmployeeSearch,
			addEmployee,
			submit,
		};
	},
};
</script>

<style scoped>
@import '../invoice-shared-styles.css';

.molding-rows-table :deep(td) {
	vertical-align: middle;
	padding-top: 6px;
	padding-bottom: 6px;
}
</style>
