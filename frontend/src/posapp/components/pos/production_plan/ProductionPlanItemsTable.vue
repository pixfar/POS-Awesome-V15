<template>
	<div class="production-items-table">
		<v-table density="compact" class="pos-themed-table">
			<thead>
				<tr>
					<th>{{ __("Item") }}</th>
					<th>{{ __("BOM") }}</th>
					<th class="text-center">{{ __("UOM") }}</th>
					<th class="text-center">{{ __("Qty") }}</th>
					<th class="text-center">{{ __("Weight") }}</th>
					<th class="text-center" style="width: 48px;"></th>
				</tr>
			</thead>
			<tbody>
				<tr v-if="!items.length">
					<td colspan="6" class="text-center text-medium-emphasis py-4">
						{{ __("Add items from the selector or search above") }}
					</td>
				</tr>
				<tr v-for="item in items" :key="item.line_id" class="production-item-row">
					<td>
						<div class="font-weight-medium">{{ item.item_name }}</div>
						<div class="text-caption text-medium-emphasis">{{ item.item_code }}</div>
					</td>
					<td>
						<v-chip
							v-if="item.bom_no"
							size="x-small"
							variant="tonal"
							color="primary"
							class="production-bom-chip"
						>
							{{ item.bom_no }}
						</v-chip>
						<span v-else class="text-caption text-medium-emphasis">{{ __("No BOM") }}</span>
					</td>
					<td class="text-center text-caption">{{ item.uom }}</td>
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
					<td class="text-center text-caption">
						{{ (Number(item.qty || 0) * Number(item.custom_default_weigt_of_measure || 0)).toFixed(2) }}
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
	},
	emits: ['update-qty', 'remove-item'],
};
</script>

<style scoped>
.qty-field :deep(input) {
	text-align: center;
}

.production-bom-chip {
	font-variant-numeric: tabular-nums;
	font-weight: 600;
}
</style>
