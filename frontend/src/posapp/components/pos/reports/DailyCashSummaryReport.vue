<template>
	<div class="pa-0 h-100 invoice-shell pos-list-page">
		<v-card flat class="invoice-section-card pos-themed-card pos-list-card">
			<div class="pos-list-header">
				<div class="pos-list-header__main">
					<p class="pos-list-header__eyebrow">{{ __("Accounts") }}</p>
					<h3 class="pos-list-header__title">{{ __("Daily Cash Summary Report") }}</h3>
				</div>
				<div class="pos-list-header__actions">
					<v-btn
						variant="tonal"
						size="small"
						class="text-none"
						prepend-icon="mdi-arrow-left"
						@click="goBack"
					>
						{{ __("Back to Reports") }}
					</v-btn>
				</div>
			</div>

			<div class="pos-list-filters dcs-filters">
				<v-autocomplete
					v-if="canChangeWarehouse && warehouseOptions.length"
					v-model="warehouse"
					:items="warehouseOptions"
					item-title="name"
					item-value="name"
					:label="__('Warehouse')"
					density="compact"
					variant="outlined"
					color="primary"
					hide-details
					:loading="warehouseLoading"
					class="pos-themed-input dcs-filters__warehouse"
				/>
				<v-text-field
					v-else
					:model-value="warehouse || warehouseLabel"
					:label="__('Warehouse')"
					density="compact"
					variant="outlined"
					color="primary"
					hide-details
					readonly
					:loading="warehouseLoading"
					prepend-inner-icon="mdi-warehouse"
					class="pos-themed-input dcs-filters__warehouse"
				/>
				<div class="dcs-filters__date">
					<DateFilterField
						v-model="reportDate"
						:label="__('Report Date')"
						:clearable="false"
						field-class="pos-themed-input"
					/>
				</div>
				<v-btn
					color="primary"
					variant="flat"
					class="text-none dcs-filters__download"
					prepend-icon="mdi-file-pdf-box"
					:loading="downloading"
					:disabled="!warehouse || !reportDate"
					@click="downloadReport"
				>
					{{ __("Download PDF") }}
				</v-btn>
			</div>

			<v-alert v-if="errorMessage" type="error" density="compact" class="ma-4">
				{{ errorMessage }}
			</v-alert>

			<div v-else-if="dataLoading" class="dcs-state">
				<v-progress-circular indeterminate color="primary" />
			</div>

			<template v-else-if="report">
				<div class="pos-list-stats">
					<div class="pos-list-stat pos-list-stat--primary">
						<span class="pos-list-stat__label">{{ __("Opening Balance") }}</span>
						<strong class="pos-list-stat__value">{{ report.opening_balance }}</strong>
					</div>
					<div class="pos-list-stat pos-list-stat--success">
						<span class="pos-list-stat__label">{{ __("Total Collection") }}</span>
						<strong class="pos-list-stat__value">{{ report.sales_total?.received }}</strong>
					</div>
					<div class="pos-list-stat pos-list-stat--success">
						<span class="pos-list-stat__label">{{ __("Fund Transfer") }}</span>
						<strong class="pos-list-stat__value">{{ report.fund_transfer_total }}</strong>
					</div>
					<div class="pos-list-stat pos-list-stat--danger">
						<span class="pos-list-stat__label">{{ __("Total Expense") }}</span>
						<strong class="pos-list-stat__value">{{ report.expense_total }}</strong>
					</div>
					<div class="pos-list-stat">
						<span class="pos-list-stat__label">{{ __("Total Deposited") }}</span>
						<strong class="pos-list-stat__value">{{ report.deposit_total }}</strong>
					</div>
					<div class="pos-list-stat pos-list-stat--primary">
						<span class="pos-list-stat__label">{{ __("Closing Balance") }}</span>
						<strong class="pos-list-stat__value">{{ report.closing_balance }}</strong>
					</div>
				</div>

				<div class="dcs-section">
					<h4 class="dcs-section__title">{{ __("Sales Collection Summary") }}</h4>
					<v-data-table
						:headers="salesHeaders"
						:items="report.sales_rows"
						hide-default-footer
						:items-per-page="-1"
						density="comfortable"
						class="pos-list-table"
						no-data-text="No sales invoices for this date."
					>
						<template #item.invoice_no="{ item }">
							<span>{{ item.invoice_no }}</span>
							<span v-if="item.description" class="dcs-row-note">{{ item.description }}</span>
						</template>
					</v-data-table>
				</div>

				<div class="dcs-section">
					<h4 class="dcs-section__title">{{ __("Fund Transfer") }}</h4>
					<v-data-table
						:headers="fundTransferHeaders"
						:items="report.fund_transfer_rows"
						hide-default-footer
						:items-per-page="-1"
						density="comfortable"
						class="pos-list-table"
						no-data-text="No fund transfers for this date."
					/>
				</div>

				<div class="dcs-section">
					<h4 class="dcs-section__title">{{ __("Cash Out Outflow") }}</h4>
					<v-data-table
						:headers="expenseHeaders"
						:items="report.expense_rows"
						hide-default-footer
						:items-per-page="-1"
						density="comfortable"
						class="pos-list-table"
						no-data-text="No cash outflow for this date."
					/>
				</div>

				<div class="dcs-section">
					<h4 class="dcs-section__title">{{ __("BSP Deposit") }}</h4>
					<v-data-table
						:headers="depositHeaders"
						:items="report.deposit_rows"
						hide-default-footer
						:items-per-page="-1"
						density="comfortable"
						class="pos-list-table"
						no-data-text="No deposits for this date."
					/>
				</div>
			</template>
		</v-card>
	</div>
</template>

<script>
import { ref, computed, watch, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useUIStore } from '../../../stores/uiStore.js';
import { isPosWarehouseSwitcher } from '../../../utils/posWarehouseAccess';
import { downloadBinaryFile } from '../../../utils/downloadBinaryFile';
import DateFilterField from '../shared/DateFilterField.vue';

const getTodayDate = () =>
	frappe?.datetime?.nowdate?.() || new Date().toISOString().slice(0, 10);

export default {
	name: 'DailyCashSummaryReport',
	components: { DateFilterField },
	setup() {
		const router = useRouter();
		const uiStore = useUIStore();
		const pos_profile = ref(uiStore.posProfile || {});

		const canChangeWarehouse = computed(() => isPosWarehouseSwitcher());
		const warehouseOptions = ref([]);
		const warehouseLabel = ref('');
		const warehouseLoading = ref(false);
		const warehouse = ref(null);

		const reportDate = ref(getTodayDate());
		const downloading = ref(false);
		const dataLoading = ref(false);
		const errorMessage = ref('');
		const report = ref(null);

		const salesHeaders = [
			{ title: __('S.L'), key: 'sl', sortable: false, width: 60 },
			{ title: __('Invoice No.'), key: 'invoice_no', sortable: false },
			{ title: __('Selling'), key: 'selling', sortable: false, align: 'end' },
			{ title: __('Discount'), key: 'discount', sortable: false, align: 'end' },
			{ title: __('Due'), key: 'due', sortable: false, align: 'end' },
			{ title: __('Received'), key: 'received', sortable: false, align: 'end' },
		];

		const fundTransferHeaders = [
			{ title: __('S.L'), key: 'sl', sortable: false, width: 60 },
			{ title: __('Particulars'), key: 'particulars', sortable: false },
			{ title: __('Description'), key: 'description', sortable: false },
			{ title: __('Reference No.'), key: 'reference_no', sortable: false },
			{ title: __('Amount'), key: 'amount', sortable: false, align: 'end' },
		];

		const expenseHeaders = [
			{ title: __('S.L'), key: 'sl', sortable: false, width: 60 },
			{ title: __('Cash out Type'), key: 'cash_out_type', sortable: false },
			{ title: __('Description'), key: 'description', sortable: false },
			{ title: __('Reference No.'), key: 'reference_no', sortable: false },
			{ title: __('Amount'), key: 'amount', sortable: false, align: 'end' },
		];

		const depositHeaders = [
			{ title: __('S.L'), key: 'sl', sortable: false, width: 60 },
			{ title: __('Deposit Type'), key: 'deposit_type', sortable: false },
			{ title: __('Bank Name'), key: 'bank_name', sortable: false },
			{ title: __('Reference No.'), key: 'reference_no', sortable: false },
			{ title: __('Amount'), key: 'amount', sortable: false, align: 'end' },
		];

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

		const loadReportData = async () => {
			if (!warehouse.value || !reportDate.value) return;
			dataLoading.value = true;
			errorMessage.value = '';
			try {
				const { message } = await frappe.call({
					method: 'posawesome.posawesome.api.daily_cash_summary_pdf.get_report_data',
					args: { warehouse: warehouse.value, date: reportDate.value },
				});
				report.value = message || null;
			} catch (e) {
				errorMessage.value = e?.message || __('Failed to load the report.');
				report.value = null;
			} finally {
				dataLoading.value = false;
			}
		};

		const downloadReport = async () => {
			if (!warehouse.value || !reportDate.value) return;
			downloading.value = true;
			errorMessage.value = '';
			try {
				await downloadBinaryFile(
					'posawesome.posawesome.api.daily_cash_summary_pdf.download_pdf',
					{ warehouse: warehouse.value, date: reportDate.value },
				);
			} catch (e) {
				errorMessage.value = e?.message || __('Failed to generate the PDF.');
			} finally {
				downloading.value = false;
			}
		};

		const goBack = () => {
			router.push('/reports');
		};

		watch([warehouse, reportDate], loadReportData);

		onMounted(async () => {
			await loadWarehouses();
			loadReportData();
		});

		return {
			canChangeWarehouse,
			warehouseOptions,
			warehouseLabel,
			warehouseLoading,
			warehouse,
			reportDate,
			downloading,
			dataLoading,
			errorMessage,
			report,
			salesHeaders,
			fundTransferHeaders,
			expenseHeaders,
			depositHeaders,
			downloadReport,
			goBack,
		};
	},
};
</script>

<style scoped>
@import '../invoice-shared-styles.css';

.pos-list-header {
	margin-bottom: 16px;
}

.dcs-filters {
	align-items: center;
	flex-wrap: nowrap;
}

.dcs-filters__warehouse {
	flex: 1 1 260px;
	max-width: 320px;
}

.dcs-filters__date {
	flex: 1 1 180px;
	max-width: 200px;
}

.dcs-filters__date :deep(.v-input) {
	width: 100%;
}

.dcs-filters__download {
	flex: 1 1 180px;
	max-width: 200px;
}

@media (max-width: 720px) {
	.dcs-filters {
		flex-wrap: wrap;
	}

	.dcs-filters__warehouse,
	.dcs-filters__date,
	.dcs-filters__download {
		max-width: none;
	}
}

.dcs-state {
	padding: 32px;
	display: flex;
	justify-content: center;
}

.dcs-section {
	margin: 0 18px 18px;
}

.dcs-section__title {
	font-size: 0.85rem;
	font-weight: 700;
	text-transform: uppercase;
	letter-spacing: 0.02em;
	color: var(--pos-text-secondary, #666);
	margin-bottom: 6px;
}

.dcs-row-note {
	display: block;
	font-size: 0.72rem;
	font-style: italic;
	color: var(--pos-text-secondary, #888);
	margin-top: 2px;
}
</style>
