<template>
	<div class="h-100">
		<DocumentDetailView
			:eyebrow="__('Stock Movement')"
			:title="name"
			:share="{ doctype: 'Requisition', name }"
			:subtitle="__('Requisition')"
			:loading="loading"
			:not-found="notFound"
			:status="displayStatus"
			:status-color="statusColor(rawStatus)"
			:meta-fields="metaFields"
			:item-columns="itemColumns"
			:items="itemRows"
			:totals="totals"
			:actions="actions"
			@back="goBack"
		/>

		<ConfirmActionDialog
			v-model="confirmDialogOpen"
			:title="confirmDialogTitle"
			:message="confirmDialogMessage"
			:confirm-label="__(pendingAction || 'Confirm')"
			:confirm-color="confirmColorForStatus(pendingAction)"
			:loading="actionLoading"
			@confirm="performUpdateStatus"
		/>
	</div>
</template>

<script>
import { ref, computed, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useToastStore } from '../../../stores/toastStore';
import { openDocumentPrintView } from '../../../utils/openDocumentPrintView';
import DocumentDetailView from '../shared/DocumentDetailView.vue';
import ConfirmActionDialog from '../shared/ConfirmActionDialog.vue';

const STATUS_CONFIRM_MESSAGES = {
	Sent: __('Mark this requisition as Sent? It can no longer be edited after this.'),
	Seen: __('Mark this requisition as Seen? This lets the requester know it is being processed.'),
	Completed: __('Mark this requisition as Completed? This confirms the stock transfer is complete.'),
	Rejected: __('Reject this requisition? This cannot be undone.'),
};

const CONFIRM_COLOR_BY_STATUS = {
	Sent: 'warning',
	Seen: 'primary',
	Completed: 'success',
	Rejected: 'error',
};

export default {
	name: 'RequisitionDetail',
	components: { DocumentDetailView, ConfirmActionDialog },
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
				{ label: __('Posting Date'), value: formatDisplayDate(detail.value.transaction_date) },
				{ label: __('Requested By'), value: detail.value.requested_by },
				{ label: __('Source Warehouse'), value: detail.value.source_warehouse },
				{ label: __('Target Warehouse'), value: detail.value.target_warehouse },
				{ label: __('Created By'), value: detail.value.created_by },
			{ label: __('Last Modified By'), value: detail.value.last_modified_by },
				{ label: __('Created On'), value: formatDisplayDateTime(detail.value.creation) },
			];
			if (detail.value.amended_from) {
				fields.push({ label: __('Amended From'), value: detail.value.amended_from });
			}
			if (detail.value.notes) {
				fields.push({ label: __('Remarks'), value: detail.value.notes });
			}
			return fields;
		});

		// Current stock columns: the server only sends the warehouse sides this
		// user may see (all for System Manager / BSP Admin / BSP Viewer).
		const itemColumns = computed(() => {
			const columns = [
				{ key: 'item_code', label: __('Item Code') },
				{ key: 'item_name', label: __('Item Name') },
				{ key: 'item_group', label: __('Item Group') },
				{ key: 'required_qty', label: __('Required Qty'), align: 'end' },
			];
			if (detail.value.show_source_stock) {
				columns.push({ key: 'source_stock_qty', label: __('Source Stock ({0})', [detail.value.source_warehouse]), align: 'end' });
			}
			if (detail.value.show_target_stock) {
				columns.push({ key: 'target_stock_qty', label: __('Target Stock ({0})', [detail.value.target_warehouse]), align: 'end' });
			}
			columns.push(
				{ key: 'weight', label: __('Weight'), align: 'end' },
				{ key: 'uom', label: __('UOM') },
				{ key: 'schedule_date', label: __('Required Date') },
			);
			return columns;
		});

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
				{ label: __('Total Weight'), value: Number(detail.value.total_weight || 0).toFixed(2) },
			];
		});

		const rawStatus = computed(() => {
			if (detail.value.docstatus === 2) return 'Cancelled';
			return detail.value.transfer_status;
		});

		const displayStatus = computed(() => (rawStatus.value ? __(rawStatus.value) : ''));

		const statusColor = (status) => {
			const map = {
				Draft: 'grey',
				Sent: 'orange',
				Seen: 'blue',
				Completed: 'green',
				Rejected: 'deep-purple',
				Cancelled: 'red',
			};
			return map[status] || 'grey';
		};

		const confirmColorForStatus = (status) => CONFIRM_COLOR_BY_STATUS[status] || 'error';

		const confirmDialogOpen = ref(false);
		const pendingAction = ref(null);

		const confirmDialogTitle = computed(() =>
			pendingAction.value ? __('{0}?', [__(pendingAction.value)]) : '',
		);
		const confirmDialogMessage = computed(() =>
			pendingAction.value
				? STATUS_CONFIRM_MESSAGES[pendingAction.value] || __('Are you sure you want to continue?')
				: '',
		);

		const requestUpdateStatus = (status) => {
			pendingAction.value = status;
			confirmDialogOpen.value = true;
		};

		const performUpdateStatus = async () => {
			if (!pendingAction.value) return;
			const status = pendingAction.value;
			actionLoading.value = true;
			const freezeMessages = {
				Sent: __('Sending...'),
				Seen: __('Marking as seen...'),
				Completed: __('Marking as completed...'),
				Rejected: __('Marking as rejected...'),
			};
			try {
				await frappe.call({
					method: 'posawesome.posawesome.api.requisitions.set_requisition_status',
					args: { requisition: name, status },
					freeze: true,
					freeze_message: freezeMessages[status] || __('Updating status...'),
				});
				toastStore.show({
					title: __('Requisition {0} marked {1}', [name, status]),
					color: status === 'Completed' ? 'success' : status === 'Seen' ? 'primary' : 'warning',
				});
				confirmDialogOpen.value = false;
				pendingAction.value = null;
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
			// Draft stays editable. Sending locks it; Seen and later are
			// handled by a System Manager.
			if (detail.value.can_edit) {
				list.push({
					label: __('Edit'),
					color: 'primary',
					onClick: () => router.push(`/requisitions/${encodeURIComponent(detail.value.name)}/edit`),
				});
				list.push({
					label: __('Send'),
					color: 'warning',
					loading: actionLoading.value,
					onClick: () => requestUpdateStatus('Sent'),
				});
			}
			if (detail.value.can_manage_status) {
				if (detail.value.transfer_status === 'Sent') {
					list.push({
						label: __('Mark as Seen'),
						color: 'primary',
						loading: actionLoading.value,
						onClick: () => requestUpdateStatus('Seen'),
					});
				} else if (detail.value.transfer_status === 'Seen') {
					list.push({
						label: __('Completed'),
						color: 'success',
						loading: actionLoading.value,
						onClick: () => requestUpdateStatus('Completed'),
					});
				}
				list.push({
					label: __('Rejected'),
					color: 'error',
					loading: actionLoading.value,
					onClick: () => requestUpdateStatus('Rejected'),
				});
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
			rawStatus,
			displayStatus,
			statusColor,
			confirmColorForStatus,
			confirmDialogOpen,
			pendingAction,
			confirmDialogTitle,
			confirmDialogMessage,
			actionLoading,
			performUpdateStatus,
			goBack,
		};
	},
};
</script>
