<template>
	<div class="requisition-items-table">
		<v-table density="compact" class="pos-themed-table">
			<thead>
				<tr>
					<th>{{ __("Item") }}</th>
					<th class="text-center">{{ __("UOM") }}</th>
					<th v-if="showRequisitionQty" class="text-center">{{ __("Requisition Qty") }}</th>
					<th v-if="showStockQty" class="text-center">{{ __("Stock Qty") }}</th>
					<th class="text-center">{{ transferQtyLabel }}</th>
					<th class="text-center">{{ __("Weight") }}</th>
					<th class="text-center" style="width: 48px;"></th>
				</tr>
			</thead>
			<tbody>
				<tr v-if="!items.length">
					<td :colspan="emptyColspan" class="text-center text-medium-emphasis py-4">
						{{ __("Add items from the selector or search above") }}
					</td>
				</tr>
				<tr v-for="item in items" :key="item.line_id">
					<td>
						<div class="font-weight-medium">{{ item.item_name }}</div>
						<div class="text-caption text-medium-emphasis">{{ item.item_code }}</div>
					</td>
					<td class="text-center text-caption">{{ item.uom }}</td>
					<td v-if="showRequisitionQty" class="text-center text-caption font-weight-medium">
						{{ formatQty(item.requisition_qty) }}
					</td>
					<td
						v-if="showStockQty"
						class="text-center text-caption"
						:class="{ 'text-error': showRequisitionQty && stockShort(item) }"
					>
						{{ stockColumnValue(item) }}
					</td>
					<td class="text-center" style="max-width: 100px;">
						<v-text-field
							:model-value="item.qty"
							type="number"
							density="compact"
							variant="outlined"
							hide-details
							min="0"
							:max="showStockQty ? Math.max(0, Number(item.stock_qty || 0)) : undefined"
							class="pos-themed-input qty-field"
							@update:model-value="(v) => $emit('update-qty', { item, value: v })"
						/>
					</td>
					<td class="text-center text-caption">{{ lineWeight(item) }}</td>
					<td class="text-center">
						<v-btn
							icon="mdi-delete-outline"
							variant="text"
							size="small"
							color="error"
							@click="$emit('remove-item', item)"
						/>
					</td>
				</tr>
			</tbody>
		</v-table>
	</div>
</template>

<script>
export default {
	props: {
		items: { type: Array, default: () => [] },
		// Opt-in so Requisition (which has no concept of a single source
		// warehouse's current stock) keeps its existing table unchanged --
		// only Material Transfer passes this in.
		showStockQty: { type: Boolean, default: false },
		// When loading from a Requisition, show requested qty separately so
		// Stock Qty / transfer Qty stay easy to compare.
		showRequisitionQty: { type: Boolean, default: false },
	},
	emits: ['update-qty', 'remove-item'],
	computed: {
		emptyColspan() {
			return 5 + (this.showStockQty ? 1 : 0) + (this.showRequisitionQty ? 1 : 0);
		},
		transferQtyLabel() {
			return this.showRequisitionQty ? __('Transfer Qty') : __('Qty');
		},
	},
	methods: {
		formatQty(value) {
			const n = Number(value || 0);
			return Number.isInteger(n) ? n : n.toFixed(2);
		},
		// From-requisition flow: show true on-hand so the cashier compares
		// against Requisition Qty. Normal transfer: show remaining after this
		// cart line (same live preview Sales uses).
		stockColumnValue(item) {
			if (this.showRequisitionQty) {
				return this.formatQty(item.stock_qty);
			}
			return this.formatQty(Math.max(0, Number(item.stock_qty || 0) - Number(item.qty || 0)));
		},
		stockShort(item) {
			return Number(item.stock_qty || 0) < Number(item.qty || 0);
		},
		lineWeight(item) {
			const weight = Number(item.qty || 0) * Number(item.custom_default_weigt_of_measure || 0);
			return weight ? weight.toFixed(2) : 0;
		},
	},
};
</script>

<style scoped>
.qty-field :deep(input) {
	text-align: center;
}
</style>
