<template>
	<div class="purchase-header">
		<div class="purchase-header__body">
			<v-autocomplete
				:model-value="supplier"
				@update:model-value="$emit('update:supplier', $event)"
				:items="supplierOptions"
				item-title="supplier_name"
				item-value="name"
				:label="frappe._('Supplier')"
				density="comfortable"
				variant="solo"
				color="primary"
				hide-details="auto"
				:loading="supplierLoading"
				@update:search="$emit('search-supplier', $event)"
				:custom-filter="() => true"
				:no-data-text="supplierLoading ? __('Loading suppliers...') : __('Suppliers not found')"
				class="sleek-field pos-themed-input"
				clearable
			>
				<template #append-inner>
					<v-tooltip text="Add new supplier">
						<template #activator="{ props }">
							<v-icon
								v-bind="props"
								class="cursor-pointer"
								@mousedown.prevent.stop
								@click.stop="$emit('create-supplier')"
							>
								mdi-plus
							</v-icon>
						</template>
					</v-tooltip>
				</template>
			</v-autocomplete>
		</div>
	</div>
</template>

<script>
export default {
	props: {
		supplier: String,
		supplierOptions: Array,
		supplierLoading: Boolean,
	},
	emits: ["update:supplier", "search-supplier", "create-supplier"],
};
</script>

<style scoped>
.purchase-header__body {
	padding: 8px 14px 12px;
}
</style>
