<template>
	<div class="column-selector-container invoice-catalog-search">
		<div class="invoice-catalog-search__field">
			<InvoiceCatalogSearchField
				v-if="resolvedCatalogSearch"
				ref="catalogSearchFieldRef"
				:catalog-search="resolvedCatalogSearch"
			/>
			<v-skeleton-loader
				v-else
				type="text"
				class="invoice-catalog-search__loader"
			/>
		</div>
		<v-btn
			density="compact"
			variant="text"
			color="primary"
			prepend-icon="mdi-cog-outline"
			@click="toggleColumnSelection"
			class="column-selector-btn"
		>
			{{ __("Columns") }}
		</v-btn>
		<v-dialog v-model="showColumnSelector" max-width="500px" transition="dialog-bottom-transition">
			<v-card class="pos-themed-card">
				<v-card-title class="text-h6 pa-4 d-flex align-center">
					<span>{{ __("Select Columns to Display") }}</span>
					<v-spacer></v-spacer>
					<v-btn
						icon="mdi-close"
						variant="text"
						density="compact"
						:aria-label="__('Close column selector')"
						@click="showColumnSelector = false"
					></v-btn>
				</v-card-title>
				<v-divider></v-divider>
				<v-card-text class="pa-4">
					<v-row dense>
						<v-col
							cols="12"
							v-for="column in availableColumns.filter((col) => !col.required)"
							:key="column.key"
						>
							<v-switch
								v-model="tempSelectedColumns"
								:label="column.title"
								:value="column.key"
								hide-details
								density="compact"
								color="primary"
								class="column-switch mb-1"
								:disabled="column.required"
							></v-switch>
						</v-col>
					</v-row>
					<div class="text-caption mt-2">
						{{ __("Required columns cannot be hidden") }}
					</div>
				</v-card-text>
				<v-card-actions class="pa-4 pt-0">
					<v-btn color="error" variant="text" @click="cancelColumnSelection">{{
						__("Cancel")
					}}</v-btn>
					<v-spacer></v-spacer>
					<v-btn color="primary" variant="tonal" @click="updateSelectedColumns">{{
						__("Apply")
					}}</v-btn>
				</v-card-actions>
			</v-card>
		</v-dialog>
	</div>
</template>

<script setup>
import { computed, inject, ref, unref } from "vue";
import InvoiceCatalogSearchField from "./InvoiceCatalogSearchField.vue";
import { posCatalogSearchKey } from "../../../composables/pos/items/posCatalogSearch";

const props = defineProps({
	catalogSearch: {
		type: Object,
		default: null,
	},
	availableColumns: {
		type: Array,
		default: () => [],
	},
	selectedColumns: {
		type: Array,
		default: () => [],
	},
});

const emit = defineEmits(["update:selectedColumns"]);

const injectedCatalogSearch = inject(posCatalogSearchKey, null);
const resolvedCatalogSearch = computed(
	() => props.catalogSearch || unref(injectedCatalogSearch) || null,
);

const showColumnSelector = ref(false);
const tempSelectedColumns = ref([]);
const catalogSearchFieldRef = ref(null);

const toggleColumnSelection = () => {
	tempSelectedColumns.value = [...props.selectedColumns];
	showColumnSelector.value = true;
};

const cancelColumnSelection = () => {
	showColumnSelector.value = false;
};

const updateSelectedColumns = () => {
	emit("update:selectedColumns", tempSelectedColumns.value);
	showColumnSelector.value = false;
};

const focusSearch = () => {
	catalogSearchFieldRef.value?.focusSearch?.();
};

defineExpose({
	focusSearch,
});
</script>

<style scoped>
.invoice-catalog-search {
	display: flex;
	align-items: flex-start;
	gap: 8px;
}

.invoice-catalog-search__field {
	flex: 1;
	min-width: 0;
}

.invoice-catalog-search__loader {
	border-radius: 16px;
}

.column-selector-btn {
	flex-shrink: 0;
	margin-top: 2px;
}
</style>
