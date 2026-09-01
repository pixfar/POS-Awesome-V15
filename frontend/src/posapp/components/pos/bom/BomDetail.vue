<template>
	<DocumentDetailView
		:eyebrow="__('Manufacturing')"
		:title="name"
		:subtitle="__('Bill of Materials')"
		:loading="loading"
		:not-found="notFound"
		:status="detail.status"
		:status-color="statusColor(detail.status)"
		:meta-fields="metaFields"
		:item-columns="itemColumns"
		:items="itemRows"
		:totals="totals"
		@back="goBack"
	/>
</template>

<script>
import { ref, computed, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import DocumentDetailView from '../shared/DocumentDetailView.vue';

export default {
	name: 'BomDetail',
	components: { DocumentDetailView },
	setup() {
		const route = useRoute();
		const router = useRouter();
		const name = route.params.name;

		const loading = ref(true);
		const notFound = ref(false);
		const detail = ref({});

		const formatDisplayDateTime = (value) => {
			if (!value) return '—';
			const [datePart, timePart] = String(value).split(' ');
			const parts = String(datePart || '').split('-');
			const date = parts.length === 3 ? `${parts[2]}-${parts[1]}-${parts[0]}` : datePart;
			return timePart ? `${date} ${timePart.slice(0, 5)}` : date;
		};

		const metaFields = computed(() => [
			{ label: __('Item'), value: detail.value.item_name },
			{ label: __('Item Code'), value: detail.value.item },
			{ label: __('Produces Qty'), value: `${Number(detail.value.quantity || 0)} ${detail.value.uom || ''}` },
			{ label: __('Company'), value: detail.value.company },
			{ label: __('Active'), value: detail.value.is_active ? __('Yes') : __('No') },
			{ label: __('Default'), value: detail.value.is_default ? __('Yes') : __('No') },
			{ label: __('Created On'), value: formatDisplayDateTime(detail.value.creation) },
		]);

		const itemColumns = [
			{ key: 'item_code', label: __('Item Code') },
			{ key: 'item_name', label: __('Item Name') },
			{ key: 'qty', label: __('Qty'), align: 'end' },
			{ key: 'weight', label: __('Weight'), align: 'end' },
			{ key: 'uom', label: __('UOM') },
			{ key: 'rate', label: __('Rate'), align: 'end' },
			{ key: 'amount', label: __('Amount'), align: 'end' },
		];

		const itemRows = computed(() => detail.value.items || []);

		const totals = computed(() => [
			{ label: __('Raw Material Lines'), value: (detail.value.items || []).length },
			{ label: __('Total Cost'), value: Number(detail.value.total_cost || 0) },
			{ label: __('Total Weight'), value: Number(detail.value.total_weight || 0).toFixed(2) },
		]);

		const statusColor = (status) => {
			const map = { Draft: 'grey', Submitted: 'green', Cancelled: 'red' };
			return map[status] || 'grey';
		};

		const loadDetail = async () => {
			loading.value = true;
			notFound.value = false;
			try {
				const { message } = await frappe.call({
					method: 'posawesome.posawesome.api.boms.get_bom_detail',
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
			router.push('/boms/list');
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
			statusColor,
			goBack,
		};
	},
};
</script>
