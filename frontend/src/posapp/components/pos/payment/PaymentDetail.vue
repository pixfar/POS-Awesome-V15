<template>
	<DocumentDetailView
		:eyebrow="__('Payment')"
		:title="name"
		:subtitle="__('Payment Entry')"
		:loading="loading"
		:not-found="notFound"
		:status="detail.payment_type"
		:status-color="statusColor(detail.payment_type)"
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
import { openDocumentPrintView } from '../../../utils/openDocumentPrintView';
import { useFormat } from '../../../format';
import DocumentDetailView from '../shared/DocumentDetailView.vue';

export default {
	name: 'PaymentDetail',
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

		const formatDisplayDateTime = (value) => {
			if (!value) return '—';
			const [datePart, timePart] = String(value).split(' ');
			const date = formatDisplayDate(datePart);
			return timePart ? `${date} ${timePart.slice(0, 5)}` : date;
		};

		const metaFields = computed(() => {
			const fields = [
				{ label: __('Date'), value: formatDisplayDate(detail.value.posting_date) },
				{ label: __('Party Type'), value: detail.value.party_type },
				{ label: __('Party'), value: detail.value.party_name || detail.value.party },
				{ label: __('Mode of Payment'), value: detail.value.mode_of_payment },
				{ label: __('Company'), value: detail.value.company },
				{ label: __('Created By'), value: detail.value.created_by },
				{ label: __('Created On'), value: formatDisplayDateTime(detail.value.creation) },
			];
			if (detail.value.reference_no) {
				fields.push({ label: __('Reference No'), value: detail.value.reference_no });
			}
			if (detail.value.reference_date) {
				fields.push({ label: __('Reference Date'), value: formatDisplayDate(detail.value.reference_date) });
			}
			if (detail.value.amended_from) {
				fields.push({ label: __('Amended From'), value: detail.value.amended_from });
			}
			if (detail.value.remarks) {
				fields.push({ label: __('Remarks'), value: detail.value.remarks });
			}
			return fields;
		});

		const itemColumns = [
			{ key: 'reference_doctype', label: __('Document Type') },
			{ key: 'reference_name', label: __('Document') },
			{ key: 'total_amount', label: __('Total Amount'), align: 'end' },
			{ key: 'outstanding_amount', label: __('Outstanding'), align: 'end' },
			{ key: 'allocated_amount', label: __('Allocated'), align: 'end' },
		];

		const itemRows = computed(() =>
			(detail.value.items || []).map((row) => ({
				...row,
				total_amount: formatCurrency(row.total_amount),
				outstanding_amount: formatCurrency(row.outstanding_amount),
				allocated_amount: formatCurrency(row.allocated_amount),
			})),
		);

		const totals = computed(() => [
			{ label: __('Paid Amount'), value: formatCurrency(detail.value.paid_amount) },
			{ label: __('Received Amount'), value: formatCurrency(detail.value.received_amount) },
			{ label: __('Allocated'), value: formatCurrency(detail.value.total_allocated_amount) },
			{ label: __('Unallocated'), value: formatCurrency(detail.value.unallocated_amount) },
		]);

		const statusColor = (paymentType) => {
			const map = { Receive: 'green', Pay: 'orange', 'Internal Transfer': 'blue' };
			return map[paymentType] || 'grey';
		};

		const printDocument = () => openDocumentPrintView('Payment Entry', name);

		const actions = computed(() => [{ label: __('Print'), color: 'primary', onClick: printDocument }]);

		const loadDetail = async () => {
			loading.value = true;
			notFound.value = false;
			try {
				const { message } = await frappe.call({
					method: 'posawesome.posawesome.api.payment_entry.get_payment_entry_detail',
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
			router.push('/payments/list');
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
