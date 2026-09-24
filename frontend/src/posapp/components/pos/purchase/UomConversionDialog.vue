<template>
	<v-dialog :model-value="modelValue" max-width="460" @update:model-value="$emit('update:modelValue', $event)">
		<v-card class="pos-themed-card">
			<v-card-title class="d-flex align-center ga-2 pt-4">
				<v-icon color="primary">mdi-scale-balance</v-icon>
				{{ __("Purchase in another unit") }}
			</v-card-title>
			<v-card-subtitle class="pb-2">
				{{ item?.item_name }} · {{ __("stock unit") }}: <strong>{{ item?.stock_uom }}</strong>
			</v-card-subtitle>
			<v-card-text>
				<v-autocomplete
					v-model="uom"
					v-model:search="uomSearch"
					:items="uomOptions"
					item-title="name"
					item-value="name"
					:loading="uomLoading"
					:label="__('Purchase unit')"
					:no-data-text="__('No units found')"
					density="compact"
					variant="outlined"
					hide-details
					class="pos-themed-input mb-4"
					@update:search="searchUoms"
					@update:model-value="onUomPicked"
				/>
				<div class="d-flex align-center ga-2">
					<span class="text-no-wrap">1 {{ uom || __("unit") }} =</span>
					<v-text-field
						v-model.number="factor"
						type="number"
						min="0"
						step="any"
						density="compact"
						variant="outlined"
						hide-details
						class="pos-themed-input"
					/>
					<span class="text-no-wrap">{{ item?.stock_uom }}</span>
				</div>
				<p class="text-caption text-medium-emphasis mt-3 mb-0">
					{{ __("Saved on the item, so this unit can be picked on later purchases too. Stock is still kept and sold in {0}.", [item?.stock_uom || ""]) }}
				</p>
				<v-alert v-if="errorMessage" type="error" density="compact" variant="tonal" class="mt-3">
					{{ errorMessage }}
				</v-alert>
			</v-card-text>
			<v-card-actions class="px-4 pb-4">
				<v-spacer />
				<v-btn variant="text" class="text-none" @click="$emit('update:modelValue', false)">{{ __("Cancel") }}</v-btn>
				<v-btn
					color="primary"
					variant="flat"
					class="text-none"
					:loading="saving"
					:disabled="!canSave"
					@click="save"
				>
					{{ __("Save & use") }}
				</v-btn>
			</v-card-actions>
		</v-card>
	</v-dialog>
</template>

<script>
export default {
	name: "UomConversionDialog",
	props: {
		modelValue: { type: Boolean, default: false },
		item: { type: Object, default: null },
	},
	emits: ["update:modelValue", "saved"],
	data() {
		return {
			uom: null,
			factor: null,
			uomSearch: "",
			uomOptions: [],
			uomLoading: false,
			saving: false,
			errorMessage: "",
			searchTimer: null,
		};
	},
	computed: {
		canSave() {
			return Boolean(this.uom) && Number(this.factor) > 0 && this.uom !== this.item?.stock_uom;
		},
	},
	watch: {
		modelValue(open) {
			if (!open) return;
			this.errorMessage = "";
			const current = this.item?.uom !== this.item?.stock_uom ? this.item?.uom : null;
			this.uom = current;
			this.factor = current ? this.factorFor(current) : null;
			this.searchUoms("");
		},
	},
	methods: {
		factorFor(uom) {
			const row = (this.item?.item_uoms || []).find((u) => u.uom === uom);
			return row ? row.conversion_factor : null;
		},
		onUomPicked(uom) {
			// Prefill with the factor already saved on the item, if any.
			const saved = this.factorFor(uom);
			if (saved) this.factor = saved;
		},
		searchUoms(term) {
			if (this.searchTimer) clearTimeout(this.searchTimer);
			this.searchTimer = setTimeout(async () => {
				this.uomLoading = true;
				try {
					const { message } = await frappe.call({
						method: "posawesome.posawesome.api.items.search_uoms",
						args: { search_text: term || "", limit: 30 },
					});
					const stock = this.item?.stock_uom;
					this.uomOptions = (message || []).filter((u) => u.name !== stock);
				} catch (e) {
					console.error("Failed to load units", e);
				} finally {
					this.uomLoading = false;
				}
			}, term ? 250 : 0);
		},
		async save() {
			if (!this.canSave) return;
			this.saving = true;
			this.errorMessage = "";
			try {
				const { message } = await frappe.call({
					method: "posawesome.posawesome.api.items.set_item_uom_conversion",
					args: {
						item_code: this.item.item_code,
						uom: this.uom,
						conversion_factor: this.factor,
					},
				});
				const saved = (message?.item_uoms || []).find(
					(u) => String(u.uom).toLowerCase() === String(this.uom).toLowerCase(),
				);
				this.$emit("saved", {
					item: this.item,
					uom: saved ? saved.uom : this.uom,
					item_uoms: message?.item_uoms || [],
				});
				this.$emit("update:modelValue", false);
			} catch (e) {
				this.errorMessage = e?.message || __("Failed to save the unit");
			} finally {
				this.saving = false;
			}
		},
	},
};
</script>
