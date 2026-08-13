<template>
	<div class="requisition-items-table">
		<v-table density="compact" class="pos-themed-table">
			<thead>
				<tr>
					<th>{{ __("Item") }}</th>
					<th class="text-center">{{ __("UOM") }}</th>
					<th v-if="showStockQty" class="text-center">{{ __("Stock Qty") }}</th>
					<th class="text-center">{{ __("Qty") }}</th>
					<th class="text-center" style="width: 48px;"></th>
				</tr>
			</thead>
			<tbody>
				<tr v-if="!items.length">
					<td :colspan="showStockQty ? 5 : 4" class="text-center text-medium-emphasis py-4">
						{{ __("Add items from the selector or search above") }}
					</td>
				</tr>
				<tr v-for="item in items" :key="item.line_id">
					<td>
						<div class="font-weight-medium">{{ item.item_name }}</div>
						<div class="text-caption text-medium-emphasis">{{ item.item_code }}</div>
					</td>
					<td class="text-center text-caption">{{ item.uom }}</td>
					<td v-if="showStockQty" class="text-center text-caption">{{ remainingStockQty(item) }}</td>
					<td class="text-center" style="max-width: 100px;">
						<v-text-field
							:model-value="item.qty"
							type="number"
							density="compact"
							variant="outlined"
							hide-details
							min="0"
							class="pos-themed-input qty-field"
							@update:model-value="(v) => $emit('update-qty', { item, value: v })"
						/>
					</td>
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
	},
	emits: ['update-qty', 'remove-item'],
	methods: {
		// item.stock_qty stays the true, independently-fetched on-hand qty
		// (re-fetched whenever the From Warehouse changes) -- what's shown
		// here is a live preview of what would remain after this transfer,
		// same as Sales showing stock count down as items go into the cart,
		// recomputed from that fixed base every time so repeatedly editing
		// qty (4, then 2, then 6...) never compounds.
		remainingStockQty(item) {
			return Math.max(0, Number(item.stock_qty || 0) - Number(item.qty || 0));
		},
	},
};
</script>

<style scoped>
.qty-field :deep(input) {
	text-align: center;
}
</style>
