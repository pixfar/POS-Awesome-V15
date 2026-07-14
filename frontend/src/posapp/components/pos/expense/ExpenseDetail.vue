<template>
	<DocumentDetailView
		:eyebrow="__('Expenses & Advances')"
		:title="name"
		:subtitle="__('Expense Claim')"
		:loading="loading"
		:not-found="notFound"
		:status="detail.status"
		:status-color="statusColor(detail.status)"
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
	name: 'ExpenseDetail',
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
			{ label: __('Employee'), value: detail.value.employee_name || detail.value.employee },
			{ label: __('Warehouse'), value: detail.value.warehouse },
			{ label: __('Approval Status'), value: detail.value.approval_status },
			{ label: __('Mode of Payment'), value: detail.value.mode_of_payment },
			{ label: __('Payable Account'), value: detail.value.payable_account },
			{ label: __('Remark'), value: detail.value.remark },
		]);

		const itemColumns = [
			{ key: 'expense_date', label: __('Date') },
			{ key: 'expense_type', label: __('Expense Claim Type') },
			{ key: 'description', label: __('Description') },
			{ key: 'amount', label: __('Amount'), align: 'end' },
			{ key: 'sanctioned_amount', label: __('Sanctioned Amount'), align: 'end' },
		];

		const itemRows = computed(() =>
			(detail.value.expenses || []).map((row) => ({
				...row,
				expense_date: formatDisplayDate(row.expense_date),
				amount: formatCurrency(row.amount),
				sanctioned_amount: formatCurrency(row.sanctioned_amount),
			})),
		);

		const totals = computed(() => [
			{ label: __('Total Claimed'), value: formatCurrency(detail.value.total_claimed_amount) },
			{ label: __('Total Sanctioned'), value: formatCurrency(detail.value.total_sanctioned_amount) },
			{ label: __('Grand Total'), value: formatCurrency(detail.value.grand_total) },
		]);

		const statusColor = (status) => {
			const map = {
				Paid: 'green',
				Unpaid: 'orange',
				Rejected: 'red',
				Submitted: 'blue',
				Draft: 'grey',
			};
			return map[status] || 'grey';
		};

		const printDocument = () => openDocumentPrintView('Expense Claim', name);

		const actions = computed(() => [{ label: __('Print'), color: 'primary', onClick: printDocument }]);

		const loadDetail = async () => {
			loading.value = true;
			notFound.value = false;
			try {
				const { message } = await frappe.call({
					method: 'posawesome.posawesome.api.expense_claims.get_expense_claim_detail',
					args: { expense_claim: name },
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
			router.push('/expenses/list');
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
