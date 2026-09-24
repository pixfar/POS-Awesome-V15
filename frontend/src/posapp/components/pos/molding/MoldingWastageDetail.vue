<template>
	<DocumentDetailView
		:eyebrow="__('Molding')"
		:title="name"
		:subtitle="__('Molding Weekly Wastage')"
		:loading="loading"
		:not-found="notFound"
		:status="detail.status ? __(detail.status) : ''"
		:status-color="statusColor(detail.status)"
		:meta-fields="metaFields"
		:item-columns="itemColumns"
		:items="itemRows"
		:totals="totals"
		:actions="actions"
		@back="goBack"
	/>
	<ConfirmActionDialog
		v-model="confirmDialog"
		:title="__('Cancel Molding Weekly Wastage')"
		:message="__('This will cancel {0} and its Additional Salary penalty deductions. Continue?', [name])"
		:confirm-label="__('Cancel Wastage')"
		confirm-color="error"
		:loading="cancelLoading"
		@confirm="runCancel"
	/>
</template>

<script>
import { ref, computed, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { openDocumentPrintView } from '../../../utils/openDocumentPrintView';
import { useFormat } from '../../../format';
import { useToastStore } from '../../../stores/toastStore';
import { isFundTransferManager } from '../../../utils/posWarehouseAccess';
import DocumentDetailView from '../shared/DocumentDetailView.vue';
import ConfirmActionDialog from '../shared/ConfirmActionDialog.vue';
import { formatDisplayDate, formatDisplayDateTime, docStatusColor } from '../shared/docStatusUtils';

const API = 'posawesome.posawesome.api.molding';

export default {
	name: 'MoldingWastageDetail',
	components: { DocumentDetailView, ConfirmActionDialog },
	setup() {
		const route = useRoute();
		const router = useRouter();
		const toastStore = useToastStore();
		const name = route.params.name;
		const { formatCurrency, formatFloat } = useFormat();

		const loading = ref(true);
		const notFound = ref(false);
		const detail = ref({});
		const confirmDialog = ref(false);
		const cancelLoading = ref(false);

		const metaFields = computed(() => [
			{ label: __('Start Date'), value: formatDisplayDate(detail.value.start_date) },
			{ label: __('End Date'), value: formatDisplayDate(detail.value.end_date) },
			{ label: __('Total Work (KG)'), value: formatFloat(detail.value.total_weekly_work_kg) },
			{ label: __('Allowed Wastage (KG)'), value: formatFloat(detail.value.allowed_wastage_kg) },
			{ label: __('Actual Wastage (KG)'), value: formatFloat(detail.value.actual_wastage_kg) },
			{ label: __('Excess Wastage (KG)'), value: formatFloat(detail.value.excess_wastage_kg) },
			{ label: __('Created By'), value: detail.value.created_by },
			{ label: __('Created On'), value: formatDisplayDateTime(detail.value.creation) },
		]);

		const itemColumns = [
			{ key: 'employee', label: __('Employee ID') },
			{ key: 'employee_name', label: __('Employee Name') },
			{ key: 'payroll_date', label: __('Payroll Date') },
			{ key: 'additional_salary', label: __('Additional Salary') },
			{ key: 'amount', label: __('Deduction'), align: 'end' },
		];

		const itemRows = computed(() =>
			(detail.value.deductions || []).map((row) => ({
				...row,
				payroll_date: formatDisplayDate(row.payroll_date),
				amount: formatCurrency(row.amount),
			})),
		);

		const totals = computed(() => [
			{ label: __('Penalty Amount'), value: formatCurrency(detail.value.penalty_amount) },
		]);

		const actions = computed(() => [
			{ label: __('Print'), color: 'primary', onClick: () => openDocumentPrintView('Molding Weekly Wastage', name) },
			...(isFundTransferManager() && detail.value.docstatus === 1
				? [{ label: __('Cancel'), color: 'error', onClick: () => (confirmDialog.value = true) }]
				: []),
		]);

		const loadDetail = async () => {
			loading.value = true;
			notFound.value = false;
			try {
				const { message } = await frappe.call({
					method: `${API}.get_weekly_wastage_detail`,
					args: { name },
				});
				if (message) detail.value = message;
				else notFound.value = true;
			} catch (_e) {
				notFound.value = true;
			} finally {
				loading.value = false;
			}
		};

		const runCancel = async () => {
			cancelLoading.value = true;
			try {
				await frappe.call({ method: `${API}.cancel_weekly_wastage`, args: { name } });
				toastStore.show({ title: __('{0} cancelled', [name]), color: 'success' });
				confirmDialog.value = false;
				await loadDetail();
			} catch (e) {
				toastStore.show({ title: e?.message || __('Action failed'), color: 'error' });
			} finally {
				cancelLoading.value = false;
			}
		};

		const goBack = () => router.push('/molding-wastage/list');

		onMounted(loadDetail);

		return {
			name,
			loading,
			notFound,
			detail,
			metaFields,
			itemColumns,
			itemRows,
			totals,
			actions,
			statusColor: docStatusColor,
			confirmDialog,
			cancelLoading,
			runCancel,
			goBack,
		};
	},
};
</script>
