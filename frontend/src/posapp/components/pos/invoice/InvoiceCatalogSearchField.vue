<template>
	<div class="invoice-catalog-search-field">
		<v-row class="items" dense>
			<v-col
				class="pb-0"
				:cols="showQtyInput ? 8 : 12"
				:sm="showQtyInput ? 9 : 12"
			>
				<v-autocomplete
					ref="searchFieldRef"
					v-model:search="searchQuery"
					:model-value="pickedItemCode"
					:items="catalogItems"
					:loading="isLoading"
					item-value="item_code"
					item-title="item_name"
					:custom-filter="() => true"
					density="compact"
					variant="solo"
					color="primary"
					class="pos-themed-input invoice-item-autocomplete"
					:label="__('Search, scan or browse item')"
					:placeholder="__('Scan barcode or type item name / code')"
					hide-details
					clearable
					autocomplete="off"
					:menu-props="{ maxHeight: 360, closeOnContentClick: true }"
					:no-data-text="noDataText"
					@update:search="onSearchUpdate"
					@update:model-value="onItemPicked"
					@keydown.enter="onEnterKey"
					@keydown="onSearchKeydown"
					@paste="onSearchPaste"
					@focus="onSearchFocus"
					@blur="onSearchBlur"
					@click:clear="onClearSearch"
					prepend-inner-icon="mdi-magnify"
				>
					<template #append-inner>
						<v-btn
							v-if="posProfile.posa_enable_camera_scanning"
							icon="mdi-camera"
							size="small"
							color="primary"
							variant="text"
							:disabled="scannerLocked"
							@click.stop="catalogSearch.startCameraScanning()"
						/>
					</template>
					<template #item="{ props: itemProps, item }">
						<v-list-item v-bind="itemProps" :title="undefined">
							<v-list-item-title class="invoice-item-option__title">
								{{ item.raw.item_name }}
							</v-list-item-title>
							<v-list-item-subtitle class="invoice-item-option__meta">
								<span class="invoice-item-option__code">
									{{ item.raw.item_code }}
								</span>
								<span class="invoice-item-option__stock">
									{{ __("Stock") }}:
									{{ formatStockQty(item.raw.actual_qty) }}
									{{ item.raw.stock_uom || "" }}
								</span>
							</v-list-item-subtitle>
						</v-list-item>
					</template>
				</v-autocomplete>
			</v-col>
			<v-col v-if="showQtyInput" cols="4" sm="3" class="pb-0">
				<v-text-field
					density="compact"
					variant="solo"
					color="primary"
					class="pos-themed-input"
					:label="__('QTY')"
					hide-details
					:model-value="qtyInputModel"
					@update:model-value="onQtyUpdate"
					type="text"
					inputmode="decimal"
					@keydown.enter="onEnterKey"
					@focus="catalogSearch.clearQty()"
					@blur="catalogSearch.onQtyBlur()"
				/>
			</v-col>
		</v-row>
	</div>
</template>

<script setup>
import _ from "lodash";
import { computed, ref, unref, watch } from "vue";

const props = defineProps({
	catalogSearch: {
		type: Object,
		required: true,
	},
});

const catalogSearch = computed(() => props.catalogSearch);

const searchFieldRef = ref(null);
const searchQuery = ref("");
const pickedItemCode = ref(null);

const readRef = (value) => unref(value);

const posProfile = computed(
	() => readRef(catalogSearch.value?.posProfile) || {},
);
const showQtyInput = computed(() => !!posProfile.value?.posa_input_qty);
const catalogItems = computed(() => {
	const term = String(searchQuery.value || "").trim();
	if (term.length < 2) {
		return [];
	}
	return readRef(catalogSearch.value?.displayedItems) || [];
});
const isLoading = computed(() => !!readRef(catalogSearch.value?.isLoading));
const scannerLocked = computed(
	() => !!readRef(catalogSearch.value?.scannerLocked),
);
const hideQtyDecimals = computed(
	() => !!readRef(catalogSearch.value?.hideQtyDecimals),
);

const qtyInputModel = computed({
	get: () => readRef(catalogSearch.value?.qtyInput) ?? 1,
	set: (value) => {
		if (catalogSearch.value?.qtyInput) {
			catalogSearch.value.qtyInput.value = value;
		}
	},
});

const noDataText = computed(() => {
	const term = String(searchQuery.value || "").trim();
	if (!term) {
		return __("Type to search items");
	}
	if (term.length < 2) {
		return __("Type at least 2 characters");
	}
	return __("No items found");
});

watch(
	() => readRef(catalogSearch.value?.searchInput),
	(value) => {
		const next = String(value || "");
		if (next !== searchQuery.value) {
			searchQuery.value = next;
		}
	},
	{ immediate: true },
);

const debouncedCatalogSearch = _.debounce(() => {
	void catalogSearch.value?.runCatalogSearch?.();
}, 300);

const formatStockQty = (value) => {
	const numeric = Number(value || 0);
	if (!Number.isFinite(numeric)) {
		return "0";
	}
	if (hideQtyDecimals.value) {
		return String(Math.round(numeric));
	}
	const precision = Number(posProfile.value?.float_precision) || 2;
	return numeric.toFixed(precision);
};

const onSearchUpdate = (value) => {
	const normalized = String(value ?? "");
	searchQuery.value = normalized;
	catalogSearch.value?.handleSearchInput?.(normalized);
	if (normalized.trim().length >= 2) {
		debouncedCatalogSearch();
	}
};

const onItemPicked = async (itemCode) => {
	if (!itemCode) {
		return;
	}
	const match = catalogItems.value.find(
		(item) => String(item?.item_code || "") === String(itemCode),
	);
	pickedItemCode.value = null;
	if (match) {
		await catalogSearch.value?.addItemFromCatalog?.(match);
	}
};

const onEnterKey = (event) => {
	void catalogSearch.value?.searchAndAddItem?.(event);
};

const onSearchKeydown = (event) => {
	catalogSearch.value?.handleSearchKeydown?.(event);
};

const onSearchPaste = (event) => {
	catalogSearch.value?.handleSearchPaste?.(event);
};

const onSearchFocus = () => {
	catalogSearch.value?.handleSearchFocus?.();
};

const onSearchBlur = () => {
	catalogSearch.value?.bindDefaultSearchInputHandlers?.();
};

const onClearSearch = () => {
	pickedItemCode.value = null;
	searchQuery.value = "";
	catalogSearch.value?.clearSearch?.();
};

const onQtyUpdate = (value) => {
	qtyInputModel.value = value;
};

const focusSearch = () => {
	const field = searchFieldRef.value;
	const nestedInput = field?.$el?.querySelector?.("input");
	(nestedInput || field)?.focus?.();
};

defineExpose({
	focusSearch,
});
</script>

<style scoped>
.invoice-catalog-search-field {
	width: 100%;
}

.invoice-item-option__title {
	font-weight: 600;
	line-height: 1.3;
	white-space: normal;
}

.invoice-item-option__meta {
	display: flex;
	flex-wrap: wrap;
	gap: 8px;
	margin-top: 2px;
}

.invoice-item-option__code {
	font-variant-numeric: tabular-nums;
	font-weight: 600;
}

.invoice-item-option__stock {
	font-variant-numeric: tabular-nums;
	opacity: 0.85;
}

:deep(.invoice-item-autocomplete .v-field) {
	border-radius: 16px;
}
</style>
