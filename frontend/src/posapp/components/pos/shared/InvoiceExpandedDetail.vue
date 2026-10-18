<template>
	<div class="invoice-expanded">
		<div v-if="loading" class="invoice-expanded__loading">
			<v-progress-circular indeterminate size="22" color="primary" />
			<span class="ml-2">{{ __("Loading details...") }}</span>
		</div>
		<div v-else-if="!detail" class="invoice-expanded__empty">
			{{ __("No details available.") }}
		</div>
		<div v-else>
			<div class="invoice-expanded__meta">
				<span v-if="detail.customer_name || detail.supplier_name || detail.party_name">
					<strong>{{ __("Party") }}:</strong>
					{{ detail.customer_name || detail.supplier_name || detail.party_name }}
				</span>
				<span v-if="detail.posting_date">
					<strong>{{ __("Date") }}:</strong> {{ detail.posting_date }}
				</span>
				<span v-if="detail.owner_name || detail.owner">
					<strong>{{ __("Created By") }}:</strong> {{ detail.owner_name || detail.owner }}
				</span>
				<span v-if="detail.remarks || detail.notes">
					<strong>{{ __("Remarks") }}:</strong> {{ detail.remarks || detail.notes }}
				</span>
			</div>
			<v-table density="compact" class="invoice-expanded__table">
				<thead>
					<tr>
						<th>{{ __("Item") }}</th>
						<th>{{ __("Code") }}</th>
						<th class="text-right">{{ __("Qty") }}</th>
						<th>{{ __("UOM") }}</th>
						<th class="text-right">{{ __("Rate") }}</th>
						<th class="text-right">{{ __("Amount") }}</th>
					</tr>
				</thead>
				<tbody>
					<tr v-for="(row, idx) in detail.items || []" :key="idx">
						<td>{{ row.item_name }}</td>
						<td class="text-medium-emphasis">{{ row.item_code }}</td>
						<td class="text-right">{{ formatNumber(row.qty) }}</td>
						<td>{{ row.uom }}</td>
						<td class="text-right">{{ currencySymbol }}{{ formatCurrency(row.rate) }}</td>
						<td class="text-right">{{ currencySymbol }}{{ formatCurrency(row.amount) }}</td>
					</tr>
					<tr v-if="!(detail.items || []).length">
						<td colspan="6" class="text-center text-medium-emphasis">{{ __("No items") }}</td>
					</tr>
				</tbody>
			</v-table>
			<div class="invoice-expanded__totals">
				<span v-if="detail.grand_total != null">
					<strong>{{ __("Grand Total") }}:</strong>
					{{ currencySymbol }}{{ formatCurrency(detail.grand_total) }}
				</span>
				<span v-if="detail.discount_amount != null">
					<strong>{{ __("Discount") }}:</strong>
					{{ currencySymbol }}{{ formatCurrency(detail.discount_amount) }}
				</span>
				<span v-if="detail.paid_amount != null">
					<strong>{{ __("Paid") }}:</strong>
					{{ currencySymbol }}{{ formatCurrency(detail.paid_amount) }}
				</span>
				<span v-if="detail.outstanding_amount != null">
					<strong>{{ __("Outstanding") }}:</strong>
					{{ currencySymbol }}{{ formatCurrency(detail.outstanding_amount) }}
				</span>
			</div>
		</div>
	</div>
</template>

<script setup>
const __ = window.__;

defineProps({
	detail: { type: Object, default: null },
	loading: { type: Boolean, default: false },
	currencySymbol: { type: String, default: "" },
	formatCurrency: { type: Function, default: (v) => Number(v || 0).toFixed(2) },
});

const formatNumber = (v) => {
	const n = Number(v || 0);
	return Number.isInteger(n) ? String(n) : n.toFixed(2);
};
</script>

<style scoped>
.invoice-expanded {
	padding: 12px 16px;
	background: color-mix(in srgb, var(--pos-primary, #0f766e) 3%, #fff);
}

.invoice-expanded__loading,
.invoice-expanded__empty {
	display: flex;
	align-items: center;
	padding: 8px 0;
	color: var(--pos-text-secondary, #6b7280);
}

.invoice-expanded__meta {
	display: flex;
	flex-wrap: wrap;
	gap: 6px 18px;
	margin-bottom: 8px;
	font-size: 0.82rem;
	color: var(--pos-text-primary, #1f2937);
}

.invoice-expanded__table {
	border: 1px solid rgba(17, 24, 39, 0.1);
	border-radius: 8px;
	overflow: hidden;
}

.invoice-expanded__totals {
	display: flex;
	flex-wrap: wrap;
	gap: 6px 18px;
	margin-top: 8px;
	font-size: 0.85rem;
	justify-content: flex-end;
}
</style>
