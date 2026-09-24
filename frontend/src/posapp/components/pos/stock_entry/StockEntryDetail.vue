<template>
	<DocumentDetailView
		:eyebrow="__('Stock')"
		:title="name"
		:subtitle="__(purpose)"
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
		:title="__('Cancel {0}', [__(purpose)])"
		:message="__('This will cancel {0} and reverse its stock and accounting entries. Continue?', [name])"
		:confirm-label="__('Cancel Entry')"
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
import { stockEntryBasePath } from './stockEntryRoutes';

const API = 'posawesome.posawesome.api.stock_entries';

export default {
	name: 'StockEntryDetail',
	components: { DocumentDetailView, ConfirmActionDialog },
	props: {
		purpose: { type: String, required: true },
	},
	setup(props) {
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
			{ label: __('Posting Date'), value: formatDisplayDate(detail.value.posting_date) },
			{ label: __('Posting Time'), value: String(detail.value.posting_time || '').slice(0, 5) },
			{
				label: props.purpose === 'Material Issue' ? __('Issued From') : __('Received Into'),
				value: detail.value.warehouse,
			},
			{ label: __('Company'), value: detail.value.company },
			{ label: __('Created By'), value: detail.value.created_by },
			{ label: __('Created On'), value: formatDisplayDateTime(detail.value.creation) },
			{ label: __('Remarks'), value: detail.value.remarks },
		]);

		const itemColumns = [
			{ key: 'idx', label: __('No.') },
			{ key: 'item_code', label: __('Item Code') },
			{ key: 'item_name', label: __('Item Name') },
			{ key: 'warehouse', label: __('Warehouse') },
			{ key: 'qty', label: __('Qty'), align: 'end' },
			{ key: 'uom', label: __('UOM') },
			{ key: 'basic_rate', label: __('Rate'), align: 'end' },
			{ key: 'amount', label: __('Amount'), align: 'end' },
		];

		const itemRows = computed(() =>
			(detail.value.items || []).map((row, index) => ({
				...row,
				idx: index + 1,
				qty: formatFloat(row.qty),
				basic_rate: formatCurrency(row.basic_rate),
				amount: formatCurrency(row.amount),
			})),
		);

		const totals = computed(() => [
			{ label: __('Total Qty'), value: formatFloat(detail.value.total_qty) },
			{ label: __('Total Value'), value: formatCurrency(detail.value.total_value) },
		]);

		const actions = computed(() => [
			{ label: __('Print'), color: 'primary', onClick: () => openDocumentPrintView('Stock Entry', name) },
			...(isFundTransferManager() && detail.value.docstatus === 1
				? [{ label: __('Cancel'), color: 'error', onClick: () => (confirmDialog.value = true) }]
				: []),
		]);

		const loadDetail = async () => {
			loading.value = true;
			notFound.value = false;
			try {
				const { message } = await frappe.call({ method: `${API}.get_stock_entry_detail`, args: { name } });
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
				await frappe.call({ method: `${API}.cancel_stock_entry`, args: { name } });
				toastStore.show({ title: __('{0} cancelled', [name]), color: 'success' });
				confirmDialog.value = false;
				await loadDetail();
			} catch (e) {
				toastStore.show({ title: e?.message || __('Action failed'), color: 'error' });
			} finally {
				cancelLoading.value = false;
			}
		};

		const goBack = () => router.push(`${stockEntryBasePath(props.purpose)}/list`);

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
