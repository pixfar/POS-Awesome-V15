<template>
	<div class="purchase-header">
		<v-row dense class="px-3 pb-2">
			<v-col cols="12" sm="6">
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
						<v-tooltip v-if="allowCreateSupplier" text="Add new supplier">
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
			</v-col>
			<v-col cols="12" sm="6">
				<v-autocomplete
					:model-value="warehouse"
					@update:model-value="$emit('update:warehouse', $event)"
					:items="warehouseOptions"
					item-title="warehouse_name"
					item-value="name"
					:label="frappe._('Warehouse')"
					density="comfortable"
					variant="solo"
					color="primary"
					hide-details="auto"
					clearable
					:loading="warehouseLoading"
					class="sleek-field pos-themed-input"
				/>
			</v-col>
		</v-row>

		<v-row dense class="px-3 pb-3 align-center">
			<v-col cols="12" sm="6">
				<VueDatePicker
					:model-value="postingDateTime"
					@update:model-value="$emit('update:postingDateTime', $event)"
					model-type="format"
					format="dd-MM-yyyy HH:mm"
					:enable-time-picker="true"
					auto-apply
					teleport
					:placeholder="frappe._('Date')"
					class="sleek-field pos-themed-input posting-date-input"
				/>
			</v-col>
			<v-col cols="12" sm="6" class="d-flex flex-wrap gap-3 align-center">
				<v-switch
					:model-value="updateStock"
					@update:model-value="$emit('update:updateStock', $event)"
					density="compact"
					hide-details
					color="primary"
					:label="__('Update Stock')"
					class="ma-0"
				></v-switch>
				<v-switch
					:model-value="customIsPaid"
					@update:model-value="$emit('update:customIsPaid', $event)"
					density="compact"
					hide-details
					color="info"
					:label="__('Is Paid')"
					class="ma-0"
				></v-switch>
			</v-col>
		</v-row>
	</div>
</template>

<script>
export default {
	props: {
		supplier: String,
		supplierOptions: Array,
		supplierLoading: Boolean,
		allowCreateSupplier: Boolean,
		warehouse: String,
		warehouseOptions: Array,
		warehouseLoading: Boolean,
		postingDateTime: String,
		updateStock: Boolean,
		customIsPaid: Boolean,
	},
	emits: [
		"update:supplier",
		"update:warehouse",
		"update:postingDateTime",
		"update:updateStock",
		"update:customIsPaid",
		"search-supplier",
		"create-supplier",
	],
};
</script>

<style scoped>
.purchase-header :deep(.posting-date-input) {
	width: 100%;
}
</style>
