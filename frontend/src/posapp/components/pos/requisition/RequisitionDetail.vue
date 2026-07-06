<template>
	<DocumentDetailView
		:eyebrow="__('Stock Movement')"
		:title="name"
		:subtitle="__('Requisition')"
		:loading="loading"
		:not-found="notFound"
		:status="detail.transfer_status"
		:status-color="statusColor(detail.transfer_status)"
		:meta-fields="metaFields"
		:item-columns="itemColumns"
		:items="itemRows"
		:totals="totals"
		:actions="actions"
		@back="goBack"
	/>
</template>

<script>
import { ref, computed, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useToastStore } from '../../../stores/toastStore';
import { openDocumentPrintView } from '../../../utils/openDocumentPrintView';
import DocumentDetailView from '../shared/DocumentDetailView.vue';

export default {
	name: 'RequisitionDetail',
	components: { DocumentDetailView },
	setup() {
		const route = useRoute();
		const router = useRouter();
		const toastStore = useToastStore();
		const name = route.params.name;

		const loading = ref(true);
		const notFound = ref(false);
		const detail = ref({});
		const actionLoading = ref(false);

		const formatDisplayDate = (value) => {
			if (!value) return '—';
			const parts = String(value).split('-');
			return parts.length === 3 ? `${parts[2]}-${parts[1]}-${parts[0]}` : value;
		};

		const formatDisplayDateTime = (value) => {
			if (!value) return '—';
			const [datePart, timePart] = String(value).split(' ');
			const date = formatDisplayDate(datePart);
			return timePart ? `${date} ${timePart.slice(0, 5)}` : date;
		};

		const metaFields = computed(() => {
			const fields = [
				{ label: __('Date'), value: formatDisplayDate(detail.value.transaction_date) },
				{ label: __('Requested By'), value: detail.value.requested_by },
				{ label: __('Source Warehouse'), value: detail.value.source_warehouse },
				{ label: __('Target Warehouse'), value: detail.value.target_warehouse },
				{ label: __('Created By'), value: detail.value.created_by },
				{ label: __('Created On'), value: formatDisplayDateTime(detail.value.creation) },
			];
			if (detail.value.amended_from) {
				fields.push({ label: __('Amended From'), value: detail.value.amended_from });
			}
			if (detail.value.notes) {
				fields.push({ label: __('Notes'), value: detail.value.notes });
			}
			return fields;
		});

		const itemColumns = [
			{ key: 'item_code', label: __('Item Code') },
			{ key: 'item_name', label: __('Item Name') },
			{ key: 'item_group', label: __('Item Group') },
			{ key: 'required_qty', label: __('Required Qty'), align: 'end' },
			{ key: 'uom', label: __('UOM') },
			{ key: 'schedule_date', label: __('Required Date') },
		];

		const itemRows = computed(() =>
			(detail.value.items || []).map((row) => ({
				...row,
				schedule_date: formatDisplayDate(row.schedule_date),
			})),
		);

		const totals = computed(() => {
			const totalQty = (detail.value.items || []).reduce(
				(sum, row) => sum + Number(row.required_qty || 0),
				0,
			);
			return [
				{ label: __('Item Count'), value: detail.value.items?.length || 0 },
				{ label: __('Total Qty'), value: totalQty },
			];
		});

		const statusColor = (status) => {
			const map = { Sent: 'orange', Received: 'green', Rejected: 'red' };
			return map[status] || 'grey';
		};

		const updateStatus = async (status) => {
			actionLoading.value = true;
			try {
				await frappe.call({
					method: 'posawesome.posawesome.api.requisitions.set_requisition_status',
					args: { requisition: name, status },
					freeze: true,
					freeze_message:
						status === 'Received' ? __('Marking as received...') : __('Marking as rejected...'),
				});
				toastStore.show({
					title: __('Requisition {0} marked {1}', [name, status]),
					color: status === 'Received' ? 'success' : 'warning',
				});
				await loadDetail();
			} catch (e) {
				toastStore.show({ title: e?.message || __('Failed to update status'), color: 'error' });
			} finally {
				actionLoading.value = false;
			}
		};

		const printDocument = () => openDocumentPrintView('Requisition', name);

		const actions = computed(() => {
			const list = [];
			if (detail.value.can_manage_status) {
				list.push(
					{
						label: __('Received'),
						color: 'success',
						loading: actionLoading.value,
						onClick: () => updateStatus('Received'),
					},
					{
						label: __('Rejected'),
						color: 'error',
						loading: actionLoading.value,
						onClick: () => updateStatus('Rejected'),
					},
				);
			}
			list.push({ label: __('Print'), color: 'primary', onClick: printDocument });
			return list;
		});

		const loadDetail = async () => {
			loading.value = true;
			notFound.value = false;
			try {
				const { message } = await frappe.call({
					method: 'posawesome.posawesome.api.requisitions.get_requisition_detail',
					args: { requisition: name },
				});
				if (!message) {
					notFound.value = true;
				} else {
					detail.value = message;
				}
			} catch (e) {
				notFound.value = true;
			} finally {
				loading.value = false;
			}
		};

		const goBack = () => {
			router.push('/requisitions/list');
		};

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
			statusColor,
			goBack,
		};
	},
};
</script>
