<template>
	<DocumentDetailView
		:eyebrow="__('Fund Transfer')"
		:title="name"
		:subtitle="__('Internal Transfer')"
		:loading="loading"
		:not-found="notFound"
		:status="statusLabel(detail.docstatus)"
		:status-color="statusColor(detail.docstatus)"
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
import { useFormat } from '../../../format';
import DocumentDetailView from '../shared/DocumentDetailView.vue';
import { openDocumentPdfPrint } from '../../../utils/openDocumentPdfPrint';
import { openDocumentPrintView } from '../../../utils/openDocumentPrintView';

export default {
	name: 'FundTransferDetail',
	components: { DocumentDetailView },
	setup() {
		const route = useRoute();
		const router = useRouter();
		const name = route.params.name;
		const { formatCurrency } = useFormat();

		const loading = ref(true);
		const notFound = ref(false);
		const detail = ref({});

		const formatDisplayDate = (value) => {
			if (!value) return '—';
			const parts = String(value).split('-');
			return parts.length === 3 ? `${parts[2]}-${parts[1]}-${parts[0]}` : value;
		};

		const metaFields = computed(() => [
			{ label: __('Date'), value: formatDisplayDate(detail.value.posting_date) },
			{ label: __('Mode of Payment'), value: detail.value.mode_of_payment },
			{ label: __('Remarks'), value: detail.value.remarks },
		]);

		const itemColumns = [
			{ key: 'paid_from', label: __('Account Paid From') },
			{ key: 'paid_to', label: __('Account Paid To') },
			{ key: 'amount', label: __('Amount'), align: 'end' },
		];

		const itemRows = computed(() => {
			if (!detail.value.name) return [];
			return [
				{
					paid_from: detail.value.paid_from,
					paid_to: detail.value.paid_to,
					amount: formatCurrency(detail.value.amount),
				},
			];
		});

		const totals = computed(() => [
			{ label: __('Amount'), value: formatCurrency(detail.value.amount) },
		]);

		const statusLabel = (docstatus) => {
			const map = { 0: __('Draft'), 1: __('Submitted'), 2: __('Cancelled') };
			return map[docstatus] || __('Draft');
		};

		const statusColor = (docstatus) => {
			const map = { 0: 'grey', 1: 'green', 2: 'red' };
			return map[docstatus] || 'grey';
		};

		const printLoading = ref(false);
		const printDocument = async () => {
			printLoading.value = true;
			try {
				// Prints the actual generated PDF (same pipeline as the
				// Download button), matching Material Transfer's own Print
				// button -- not a live HTML re-render, which is a different
				// rendering engine with its own layout quirks.
				await openDocumentPdfPrint({
					doctype: 'Payment Entry',
					name,
					printFormat: 'BSP Fundtransfer',
					noLetterhead: true,
				});
			} catch (error) {
				console.warn('PDF print failed, falling back to printview', error);
				openDocumentPrintView('Payment Entry', name, 'BSP Fundtransfer');
			} finally {
				printLoading.value = false;
			}
		};
		const actions = computed(() => [
			{ label: __('Print'), color: 'primary', loading: printLoading.value, onClick: printDocument },
		]);

		const loadDetail = async () => {
			loading.value = true;
			notFound.value = false;
			try {
				const { message } = await frappe.call({
					method: 'posawesome.posawesome.api.fund_transfer.get_fund_transfer_detail',
					args: { name },
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
			router.push('/fund-transfer/list');
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
			statusLabel,
			statusColor,
			goBack,
		};
	},
};
</script>
