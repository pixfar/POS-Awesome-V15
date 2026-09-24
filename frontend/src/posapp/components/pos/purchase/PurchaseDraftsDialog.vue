<template>
	<v-dialog :model-value="modelValue" max-width="760" scrollable @update:model-value="$emit('update:modelValue', $event)">
		<v-card class="pos-themed-card">
			<v-card-title class="d-flex align-center ga-2 pt-4">
				<v-icon color="primary">mdi-file-document-edit-outline</v-icon>
				{{ __("Draft Purchase Invoices") }}
				<v-spacer />
				<v-btn icon="mdi-close" variant="text" size="small" @click="$emit('update:modelValue', false)" />
			</v-card-title>
			<div class="px-4 pb-2">
				<v-text-field
					v-model="search"
					:placeholder="__('Search draft or supplier')"
					prepend-inner-icon="mdi-magnify"
					density="compact"
					variant="outlined"
					hide-details
					clearable
					class="pos-themed-input"
					@update:model-value="onSearch"
				/>
			</div>
			<v-card-text class="pt-0" style="max-height: 60vh">
				<div v-if="loading" class="text-center py-8">
					<v-progress-circular indeterminate color="primary" />
				</div>
				<div v-else-if="!drafts.length" class="text-center text-medium-emphasis py-8">
					<v-icon size="40" class="mb-2">mdi-file-check-outline</v-icon>
					<div>{{ __("No draft purchase invoices") }}</div>
				</div>
				<v-list v-else density="comfortable" class="py-0">
					<v-list-item
						v-for="draft in drafts"
						:key="draft.name"
						class="draft-row"
						rounded="lg"
						@click="$emit('load', draft.name)"
					>
						<v-list-item-title class="font-weight-medium">
							{{ draft.supplier_name || draft.supplier }}
						</v-list-item-title>
						<v-list-item-subtitle>
							{{ draft.name }} · {{ formatDate(draft.posting_date) }} · {{ draft.item_count }}
							{{ draft.item_count === 1 ? __("item") : __("items") }}
							<span v-if="draft.set_warehouse"> · {{ draft.set_warehouse }}</span>
							<span> · {{ draft.owner_name }}</span>
						</v-list-item-subtitle>
						<template #append>
							<div class="d-flex align-center ga-3">
								<strong>{{ formatCurrency(draft.grand_total) }}</strong>
								<v-btn size="small" color="primary" variant="tonal" class="text-none" @click.stop="$emit('load', draft.name)">
									{{ __("Load") }}
								</v-btn>
							</div>
						</template>
					</v-list-item>
				</v-list>
			</v-card-text>
		</v-card>
	</v-dialog>
</template>

<script>
export default {
	name: "PurchaseDraftsDialog",
	props: {
		modelValue: { type: Boolean, default: false },
		formatCurrency: { type: Function, required: true },
	},
	emits: ["update:modelValue", "load"],
	data() {
		return { drafts: [], loading: false, search: "", timer: null };
	},
	watch: {
		modelValue(open) {
			if (open) this.fetch();
		},
	},
	methods: {
		formatDate(value) {
			const parts = String(value || "").split("-");
			return parts.length === 3 ? `${parts[2]}-${parts[1]}-${parts[0]}` : value || "";
		},
		onSearch() {
			if (this.timer) clearTimeout(this.timer);
			this.timer = setTimeout(this.fetch, 300);
		},
		async fetch() {
			this.loading = true;
			try {
				const { message } = await frappe.call({
					method: "posawesome.posawesome.api.purchase_invoices.get_purchase_drafts",
					args: { search: this.search || undefined },
				});
				this.drafts = message || [];
			} catch (e) {
				console.error("Failed to load purchase drafts", e);
				this.drafts = [];
			} finally {
				this.loading = false;
			}
		},
	},
};
</script>

<style scoped>
.draft-row {
	border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
	margin-bottom: 8px;
}
</style>
