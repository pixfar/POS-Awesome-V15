<template>
	<DocumentDetailView
		:eyebrow="__('Stock Movement')"
		:title="name"
		:subtitle="__('Material Transfer')"
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

	<ConfirmReceiptDialog
		v-model="confirmDialog"
		:items="confirmItems"
		:loading="confirmLoading"
		@confirm="handleConfirmReceipt"
	/>

	<v-dialog v-model="rejectDialog" max-width="420">
		<v-card class="pos-themed-card">
			<v-card-title class="d-flex align-center gap-2">
				<v-icon color="error">mdi-close-circle-outline</v-icon>
				<span>{{ __("Reject Transfer") }}</span>
			</v-card-title>
			<v-card-text>
				{{
					__(
						"Rejecting will cancel this transfer and reverse the stock movement. This cannot be undone. Continue?"
					)
				}}
			</v-card-text>
			<v-card-actions>
				<v-spacer />
				<v-btn variant="text" @click="rejectDialog = false">{{ __("Cancel") }}</v-btn>
				<v-btn color="error" variant="flat" :loading="rejectLoading" @click="handleRejectTransfer">
					{{ __("Reject") }}
				</v-btn>
			</v-card-actions>
		</v-card>
	</v-dialog>

	<v-dialog v-model="printFormatDialog" max-width="380">
		<v-card class="pos-themed-card">
			<v-card-title class="d-flex align-center gap-2">
				<v-icon color="primary">mdi-printer-outline</v-icon>
				<span>{{ __("Select Print Format") }}</span>
			</v-card-title>
			<v-card-text>
				<v-select
					v-model="selectedPrintFormat"
					:items="printFormatOptions"
					:label="__('Print Format')"
					variant="outlined"
					density="comfortable"
					hide-details
				/>
			</v-card-text>
			<v-card-actions>
				<v-spacer />
				<v-btn variant="text" @click="printFormatDialog = false">{{ __("Cancel") }}</v-btn>
				<v-btn color="primary" variant="flat" :loading="printLoading" @click="confirmPrint">
					{{ __("Print") }}
				</v-btn>
			</v-card-actions>
		</v-card>
	</v-dialog>
</template>

<script>
import { ref, computed, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useToastStore } from '../../../stores/toastStore';
import { openDocumentPdfPrint } from '../../../utils/openDocumentPdfPrint';
import { openDocumentPrintView } from '../../../utils/openDocumentPrintView';
import DocumentDetailView from '../shared/DocumentDetailView.vue';
import ConfirmReceiptDialog from '../requisition/ConfirmReceiptDialog.vue';

export default {
	name: 'MaterialTransferDetail',
	components: { DocumentDetailView, ConfirmReceiptDialog },
	setup() {
		const route = useRoute();
		const router = useRouter();
		const toastStore = useToastStore();
		const name = route.params.name;

		const loading = ref(true);
		const notFound = ref(false);
		const detail = ref({});
		const confirmDialog = ref(false);
		const confirmItems = ref([]);
		const confirmLoading = ref(false);
		const rejectDialog = ref(false);
		const rejectLoading = ref(false);
		const printFormatDialog = ref(false);
		const printLoading = ref(false);
		const printFormatOptions = ['BSP Material Transfer', 'BSP Delivery Note'];
		const selectedPrintFormat = ref(printFormatOptions[0]);

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
				{ label: __('From Warehouse'), value: detail.value.from_warehouse },
				{ label: __('To Warehouse'), value: detail.value.to_warehouse },
				{ label: __('Created By'), value: detail.value.created_by },
				{ label: __('Created On'), value: formatDisplayDateTime(detail.value.creation) },
			];
			if (detail.value.custom_do_number) {
				fields.push({ label: __('DO Number'), value: detail.value.custom_do_number });
			}
			if (detail.value.stock_entry) {
				fields.push({ label: __('Stock Entry'), value: detail.value.stock_entry });
			}
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
			{ key: 'qty', label: __('Qty'), align: 'end' },
			{ key: 'received_qty', label: __('Received Qty'), align: 'end' },
			{ key: 'weight', label: __('Weight'), align: 'end' },
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
			const totalQty = (detail.value.items || []).reduce((sum, row) => sum + Number(row.qty || 0), 0);
			const totalReceived = (detail.value.items || []).reduce(
				(sum, row) => sum + Number(row.received_qty || 0),
				0,
			);
			return [
				{ label: __('Item Count'), value: detail.value.items?.length || 0 },
				{ label: __('Total Qty'), value: totalQty },
				{ label: __('Total Received Qty'), value: totalReceived },
				{ label: __('Total Weight'), value: Number(detail.value.total_weight || 0).toFixed(2) },
			];
		});

		const statusColor = (status) => {
			const map = {
				'In Transit': 'blue',
				'Partially Received': 'orange',
				'Fully Received': 'green',
				'Rejected': 'red',
			};
			return map[status] || 'grey';
		};

		const loadDetail = async () => {
			loading.value = true;
			notFound.value = false;
			try {
				const { message } = await frappe.call({
					method: 'posawesome.posawesome.api.material_transfers.get_material_transfer_detail',
					args: { transfer: name },
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

		const openConfirmReceipt = async () => {
			try {
				const { message } = await frappe.call({
					method: 'posawesome.posawesome.doctype.material_transfer.material_transfer.get_stock_entry_items',
					args: { transfer: name },
				});
				confirmItems.value = message?.items || [];
				confirmDialog.value = true;
			} catch (e) {
				toastStore.show({ title: e?.message || __('Nothing to confirm'), color: 'warning' });
			}
		};

		const handleConfirmReceipt = async (receivedMap) => {
			confirmLoading.value = true;
			try {
				await frappe.call({
					method: 'posawesome.posawesome.doctype.material_transfer.material_transfer.confirm_receipt',
					args: {
						transfer: name,
						received_quantities: JSON.stringify(receivedMap),
					},
					freeze: true,
					freeze_message: __('Confirming receipt...'),
				});
				toastStore.show({ title: __('Receipt confirmed'), color: 'success' });
				confirmDialog.value = false;
				await loadDetail();
			} catch (e) {
				toastStore.show({ title: e?.message || __('Confirm failed'), color: 'error' });
			} finally {
				confirmLoading.value = false;
			}
		};

		const openRejectDialog = () => {
			rejectDialog.value = true;
		};

		const handleRejectTransfer = async () => {
			rejectLoading.value = true;
			try {
				await frappe.call({
					method: 'posawesome.posawesome.doctype.material_transfer.material_transfer.reject_transfer',
					args: { transfer: name },
					freeze: true,
					freeze_message: __('Rejecting transfer...'),
				});
				toastStore.show({ title: __('Transfer rejected'), color: 'success' });
				rejectDialog.value = false;
				await loadDetail();
			} catch (e) {
				toastStore.show({ title: e?.message || __('Reject failed'), color: 'error' });
			} finally {
				rejectLoading.value = false;
			}
		};

		const openPrintFormatDialog = () => {
			printFormatDialog.value = true;
		};

		const confirmPrint = async () => {
			printLoading.value = true;
			try {
				await openDocumentPdfPrint({
					doctype: 'Material Transfer',
					name,
					printFormat: selectedPrintFormat.value,
					noLetterhead: 1,
					autoPrint: false,
				});
				printFormatDialog.value = false;
			} catch (error) {
				console.warn('PDF print failed, falling back to printview', error);
				openDocumentPrintView('Material Transfer', name, selectedPrintFormat.value);
				printFormatDialog.value = false;
			} finally {
				printLoading.value = false;
			}
		};

		const actions = computed(() => {
			const list = [];
			if (detail.value.can_confirm) {
				list.push({ label: __('Received'), color: 'primary', onClick: openConfirmReceipt });
				list.push({ label: __('Rejected'), color: 'error', onClick: openRejectDialog });
			}
			list.push({ label: __('Print'), color: 'primary', onClick: openPrintFormatDialog });
			return list;
		});

		const goBack = () => {
			router.push('/material-transfers/list');
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
			confirmDialog,
			confirmItems,
			confirmLoading,
			handleConfirmReceipt,
			rejectDialog,
			rejectLoading,
			handleRejectTransfer,
			printFormatDialog,
			printLoading,
			printFormatOptions,
			selectedPrintFormat,
			confirmPrint,
			goBack,
		};
	},
};
</script>
