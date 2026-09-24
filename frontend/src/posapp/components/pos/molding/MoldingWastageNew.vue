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
										<h3 class="invoice-section-heading__title">{{ __("Period") }}</h3>
									</div>
									<div class="sale-options-body">
										<DateFilterField
											v-model="startDate"
											:label="__('Start Date')"
											:clearable="false"
											:max="endDate"
											field-class="pos-themed-input mb-2"
											@update:model-value="fetchWeeklyData"
										/>
										<DateFilterField
											v-model="endDate"
											:label="__('End Date')"
											:clearable="false"
											:min="startDate"
											field-class="pos-themed-input"
											@update:model-value="fetchWeeklyData"
										/>
									</div>
								</v-card>

								<v-card flat class="invoice-section-card pos-themed-card outstanding-panel">
									<div class="outstanding-panel__inner">
										<div class="outstanding-panel__label">{{ __("Penalty Amount") }}</div>
										<div
											class="outstanding-panel__amount"
											:class="penaltyAmount > 0 ? 'text-error' : 'outstanding-panel__amount--clear'"
										>
											{{ formatCurrency(penaltyAmount) }}
										</div>
										<div class="text-caption text-medium-emphasis">
											{{ __("Excess") }}: {{ formatFloat(excessWastageKg) }} KG × {{ PENALTY_PER_KG }}
										</div>
									</div>
								</v-card>

								<v-card flat class="invoice-section-card pos-themed-card sale-options-card">
									<div class="invoice-section-heading">
										<h3 class="invoice-section-heading__title">{{ __("Wastage") }}</h3>
									</div>
									<div class="sale-options-body">
										<v-text-field
											v-model.number="actualWastageKg"
											type="number"
											min="0"
											:label="__('Actual Wastage (KG)')"
											density="compact"
											variant="outlined"
											hide-details
											prepend-inner-icon="mdi-weight-kilogram"
											class="pos-themed-input"
										/>
									</div>
								</v-card>
							</div>

							<v-card flat class="invoice-section-card pos-themed-card">
								<div class="invoice-section-heading d-flex align-center justify-space-between">
									<h3 class="invoice-section-heading__title">{{ __("Summary") }}</h3>
									<v-btn
										size="small"
										variant="tonal"
										color="primary"
										prepend-icon="mdi-sync"
										class="text-none"
										:loading="weeklyLoading"
										@click="fetchWeeklyData"
									>
										{{ __("Fetch Weekly Data") }}
									</v-btn>
								</div>
								<v-table density="comfortable">
									<tbody>
										<tr>
											<td>{{ __("Total Work (KG)") }}</td>
											<td class="text-right">{{ formatFloat(totalWeeklyWorkKg) }}</td>
										</tr>
										<tr>
											<td>{{ __("Allowed Wastage (KG, 1%)") }}</td>
											<td class="text-right">{{ formatFloat(allowedWastageKg) }}</td>
										</tr>
										<tr>
											<td>{{ __("Actual Wastage (KG)") }}</td>
											<td class="text-right">{{ formatFloat(actualWastageKg) }}</td>
										</tr>
										<tr>
											<td>{{ __("Excess Wastage (KG)") }}</td>
											<td class="text-right">{{ formatFloat(excessWastageKg) }}</td>
										</tr>
										<tr>
											<td><strong>{{ __("Penalty Amount") }}</strong></td>
											<td class="text-right"><strong>{{ formatCurrency(penaltyAmount) }}</strong></td>
										</tr>
									</tbody>
								</v-table>
							</v-card>

							<v-card flat class="invoice-section-card invoice-items-card pos-themed-card">
								<div class="invoice-section-heading">
									<h3 class="invoice-section-heading__title">{{ __("Penalty Split by Points") }}</h3>
								</div>
								<v-table density="comfortable">
									<thead>
										<tr>
											<th>{{ __("Employee") }}</th>
											<th class="text-right">{{ __("Points") }}</th>
											<th class="text-right">{{ __("Deduction") }}</th>
										</tr>
									</thead>
									<tbody>
										<tr v-for="row in employeePoints" :key="row.employee">
											<td>
												<div>{{ row.employee_name || row.employee }}</div>
												<div class="text-caption text-medium-emphasis">{{ row.employee }}</div>
											</td>
											<td class="text-right">{{ formatFloat(row.points) }}</td>
											<td class="text-right">{{ formatCurrency(deduction(row)) }}</td>
										</tr>
										<tr v-if="!employeePoints.length">
											<td colspan="3" class="text-center text-medium-emphasis py-4">
												{{ __("No submitted Daily Production in this period") }}
											</td>
										</tr>
									</tbody>
								</v-table>
							</v-card>

							<v-alert v-if="errorMessage" type="error" density="compact">
								{{ errorMessage }}
							</v-alert>
						</div>
					</v-card-text>

					<div class="purchase-bottom-bar">
						<div class="purchase-bottom-bar__summary">
							<span class="purchase-bottom-bar__label">{{ __("Penalty Amount") }}</span>
							<strong class="purchase-bottom-bar__amount">{{ formatCurrency(penaltyAmount) }}</strong>
							<span class="purchase-bottom-bar__meta">
								{{ employeePoints.length }}
								{{ employeePoints.length === 1 ? __("worker") : __("workers") }}
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
							{{ __("Submit Wastage") }}
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
// Mirrors ALLOWED_WASTAGE_RATE / PENALTY_PER_KG in bsp_engineering's
// molding_weekly_wastage.py -- preview only, the server recomputes on submit.
const ALLOWED_WASTAGE_RATE = 0.01;
const PENALTY_PER_KG = 20;

const toIsoDate = (date) => {
	const pad = (n) => String(n).padStart(2, '0');
	return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
};

export default {
	name: 'MoldingWastageNew',
	mixins: [format],
	components: { DateFilterField },
	setup() {
		const router = useRouter();
		const toastStore = useToastStore();

		const today = new Date();
		const weekAgo = new Date(today);
		weekAgo.setDate(today.getDate() - 6);
		const startDate = ref(toIsoDate(weekAgo));
		const endDate = ref(toIsoDate(today));
		const actualWastageKg = ref(null);
		const totalWeeklyWorkKg = ref(0);
		const employeePoints = ref([]);
		const weeklyLoading = ref(false);
		const submitLoading = ref(false);
		const errorMessage = ref('');

		const allowedWastageKg = computed(() => (Number(totalWeeklyWorkKg.value) || 0) * ALLOWED_WASTAGE_RATE);
		const excessWastageKg = computed(() =>
			Math.max(0, (Number(actualWastageKg.value) || 0) - allowedWastageKg.value),
		);
		const penaltyAmount = computed(() => excessWastageKg.value * PENALTY_PER_KG);
		const totalPoints = computed(() =>
			employeePoints.value.reduce((sum, row) => sum + (Number(row.points) || 0), 0),
		);
		const deduction = (row) =>
			totalPoints.value > 0 ? penaltyAmount.value * ((Number(row.points) || 0) / totalPoints.value) : 0;
		const canSubmit = computed(
			() =>
				Boolean(startDate.value && endDate.value) &&
				actualWastageKg.value !== null &&
				actualWastageKg.value !== '' &&
				Number(actualWastageKg.value) >= 0,
		);

		const fetchWeeklyData = async () => {
			if (!startDate.value || !endDate.value) return;
			errorMessage.value = '';
			weeklyLoading.value = true;
			try {
				const { message } = await frappe.call({
					method: `${API}.fetch_weekly_data`,
					args: { start_date: startDate.value, end_date: endDate.value },
				});
				totalWeeklyWorkKg.value = Number(message?.total_weekly_work_kg) || 0;
				employeePoints.value = message?.employee_points || [];
			} catch (e) {
				errorMessage.value = e?.message || __('Failed to fetch weekly data');
			} finally {
				weeklyLoading.value = false;
			}
		};

		const submit = async () => {
			errorMessage.value = '';
			if (!canSubmit.value) return;
			submitLoading.value = true;
			try {
				const { message } = await frappe.call({
					method: `${API}.create_weekly_wastage`,
					args: {
						data: {
							start_date: startDate.value,
							end_date: endDate.value,
							actual_wastage_kg: actualWastageKg.value,
						},
					},
					freeze: true,
					freeze_message: __('Submitting wastage...'),
				});
				toastStore.show({ title: __('{0} submitted', [message?.name || '']), color: 'success' });
				await router.push(message?.name ? `/molding-wastage/${message.name}` : '/molding-wastage/list');
			} catch (e) {
				errorMessage.value = e?.message || __('Failed to submit wastage');
			} finally {
				submitLoading.value = false;
			}
		};

		onMounted(() => {
			if (!isFundTransferManager()) {
				router.replace('/molding-wastage/list');
				return;
			}
			fetchWeeklyData();
		});

		return {
			PENALTY_PER_KG,
			startDate,
			endDate,
			actualWastageKg,
			totalWeeklyWorkKg,
			employeePoints,
			weeklyLoading,
			submitLoading,
			errorMessage,
			allowedWastageKg,
			excessWastageKg,
			penaltyAmount,
			deduction,
			canSubmit,
			fetchWeeklyData,
			submit,
		};
	},
};
</script>

<style scoped>
@import '../invoice-shared-styles.css';
</style>
