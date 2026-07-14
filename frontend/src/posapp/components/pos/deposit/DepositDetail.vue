<template>
	<DocumentDetailView
		:eyebrow="__('BSP Daily Deposit')"
		:title="name"
		:subtitle="__('Daily Deposit')"
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

export default {
	name: 'DepositDetail',
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
			{ label: __('User'), value: detail.value.user_name || detail.value.user },
		]);

		const itemColumns = [
			{ key: 'warehouse', label: __('Warehouse') },
			{ key: 'deposit_type', label: __('Deposit Type') },
			{ key: 'bank_name', label: __('Bank Name') },
			{ key: 'amount', label: __('Amount'), align: 'end' },
		];

		const itemRows = computed(() => {
			if (!detail.value.name) return [];
			return [
				{
					warehouse: detail.value.warehouse,
					deposit_type: detail.value.deposit_type,
					bank_name: detail.value.bank_name,
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

		const viewReceipt = () => {
			if (detail.value.acknowledgment_receipt) {
				window.open(detail.value.acknowledgment_receipt, '_blank', 'noopener,noreferrer');
			}
		};

		const actions = computed(() =>
			detail.value.acknowledgment_receipt
				? [{ label: __('View Receipt'), color: 'primary', onClick: viewReceipt }]
				: [],
		);

		const loadDetail = async () => {
			loading.value = true;
			notFound.value = false;
			try {
				const { message } = await frappe.call({
					method: 'posawesome.posawesome.api.bsp_daily_deposit.get_daily_deposit_detail',
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
			router.push('/deposits/list');
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
