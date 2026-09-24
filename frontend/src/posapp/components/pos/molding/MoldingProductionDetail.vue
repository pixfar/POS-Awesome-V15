<template>
	<DocumentDetailView
		:eyebrow="__('Molding')"
		:title="name"
		:subtitle="__('Molding Daily Production')"
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
		:title="__('Cancel Molding Daily Production')"
		:message="__('This will cancel {0} and its Additional Salary wage entries. Continue?', [name])"
		:confirm-label="__('Cancel Production')"
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
	name: 'MoldingProductionDetail',
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
			{ label: __('Date'), value: formatDisplayDate(detail.value.date) },
			{ label: __('Total Work (KG)'), value: formatFloat(detail.value.total_work_kg) },
			{ label: __('Rate per KG'), value: formatCurrency(detail.value.rate_per_kg) },
			{ label: __('Present Workers'), value: String((detail.value.present_employees || []).length) },
			{ label: __('Created By'), value: detail.value.created_by },
			{ label: __('Created On'), value: formatDisplayDateTime(detail.value.creation) },
			...(detail.value.amended_from ? [{ label: __('Amended From'), value: detail.value.amended_from }] : []),
		]);

		const itemColumns = [
			{ key: 'idx', label: __('No.') },
			{ key: 'employee', label: __('Employee ID') },
			{ key: 'employee_name', label: __('Employee Name') },
			{ key: 'point', label: __('Point'), align: 'end' },
			{ key: 'daily_salary', label: __('Daily Salary'), align: 'end' },
		];

		const itemRows = computed(() =>
			(detail.value.present_employees || []).map((row, index) => ({
				...row,
				idx: index + 1,
				point: formatFloat(row.point),
				daily_salary: formatCurrency(row.daily_salary),
			})),
		);

		const totals = computed(() => [
			{ label: __('Total Points'), value: formatFloat(detail.value.total_points) },
			{ label: __('Per Point Rate'), value: formatCurrency(detail.value.per_point_rate) },
			{ label: __('Total Wage'), value: formatCurrency(detail.value.total_wage) },
		]);

		const actions = computed(() => [
			{ label: __('Print'), color: 'primary', onClick: () => openDocumentPrintView('Molding Daily Production', name) },
			...(isFundTransferManager() && detail.value.docstatus === 1
				? [{ label: __('Cancel'), color: 'error', onClick: () => (confirmDialog.value = true) }]
				: []),
		]);

		const loadDetail = async () => {
			loading.value = true;
			notFound.value = false;
			try {
				const { message } = await frappe.call({
					method: `${API}.get_daily_production_detail`,
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
				await frappe.call({ method: `${API}.cancel_daily_production`, args: { name } });
				toastStore.show({ title: __('{0} cancelled', [name]), color: 'success' });
				confirmDialog.value = false;
				await loadDetail();
			} catch (e) {
				toastStore.show({ title: e?.message || __('Action failed'), color: 'error' });
			} finally {
				cancelLoading.value = false;
			}
		};

		const goBack = () => router.push('/molding-production/list');

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
