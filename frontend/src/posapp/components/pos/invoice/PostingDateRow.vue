<template>
	<div class="posting-date-row">
		<VueDatePicker
			ref="postingDatePicker"
			v-model="internal_posting_date_display"
			model-type="format"
			format="dd-MM-yyyy"
			auto-apply
			teleport
			:disabled="disabled"
			:placeholder="placeholderText"
			class="sleek-field posting-date-input pos-themed-input mb-2"
			@update:model-value="onUpdate"
		/>
		<v-select
			v-if="pos_profile.posa_enable_price_list_dropdown"
			density="comfortable"
			variant="solo"
			color="primary"
			:items="priceLists"
			:label="priceListLabel"
			v-model="internal_price_list"
			hide-details
			class="sleek-field mb-2"
			@update:model-value="onPriceListUpdate"
		/>
	</div>
</template>

<script setup lang="ts">
import { ref, watch, computed } from "vue";
import type { POSProfile } from "../../../types/models";

interface Props {
	pos_profile: POSProfile | any; // Loose typing for now to avoid breaking changes
	posting_date_display?: string;
	customer_balance?: number;
	formatCurrency: (_val: number | undefined) => string;
	priceList?: string;
	priceLists?: string[];
	disabled?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
	disabled: false,
});

const __ = (str: string) => (window.__ ? window.__(str) : str);

const emit = defineEmits<{
	"update:posting_date_display": [val: string];
	"update:priceList": [val: string];
}>();

const internal_posting_date_display = ref(props.posting_date_display);
const internal_price_list = ref(props.priceList);
const postingDatePicker = ref<any>(null);

const placeholderText = computed(() => frappe._("Sales Date"));
const priceListLabel = computed(() => frappe._("Price List"));

watch(
	() => props.posting_date_display,
	(val) => {
		internal_posting_date_display.value = val;
	},
);

watch(
	() => props.priceList,
	(val) => {
		internal_price_list.value = val;
	},
);

const onUpdate = (val: any) => {
	emit("update:posting_date_display", val);
};

const onPriceListUpdate = (val: any) => {
	emit("update:priceList", val);
};

const focusPostingDate = () => {
	// Use optional chaining carefully with the ref
	const el = postingDatePicker.value?.$el || postingDatePicker.value;
	const input = el?.querySelector("input");
	if (input) {
		input.focus();
		input.select?.();
	}
};

// Expose methods for template refs
defineExpose({
	focusPostingDate,
});
</script>

<style scoped>
/* Theme-aware input styling */
.posting-date-input :deep(.v-field__input),
.posting-date-input :deep(input),
.posting-date-input :deep(.v-label) {
	color: var(--pos-text-primary) !important;
}

.posting-date-input :deep(.v-field__overlay) {
	background-color: var(--pos-input-bg) !important;
}

/* Theme-aware date picker elements */
:deep(.dp__input) {
	background-color: var(--pos-input-bg) !important;
	color: var(--pos-text-primary) !important;
}

:deep(.dp__menu) {
	background-color: var(--pos-card-bg) !important;
	color: var(--pos-text-primary) !important;
	z-index: 4000 !important;
}

/* Ensure calendar numbers remain visible across themes */
.posting-date-input :deep(.dp__calendar_header_item),
.posting-date-input :deep(.dp__cell_inner) {
	color: var(--pos-text-primary) !important;
}

/* Sleek design for VueDatePicker */
:deep(.sleek-field) .dp__input_wrap {
	width: 100%;
	box-sizing: border-box;
}

:deep(.sleek-field) .dp__input {
	width: 100%;
	border-radius: 12px;
	box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
	transition: box-shadow 0.3s ease;
	background-color: var(--field-bg);
	color: var(--text-primary);
	padding: 10px 12px;
}

:deep(.sleek-field:hover) .dp__input {
	box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
}

/* Align calendar icon to the right, before the clear icon */
.posting-date-input :deep(.dp__input_icon) {
	inset-inline-start: auto;
	inset-inline-end: 30px;
}

/* Remove extra left padding added for left icon placement */
.posting-date-input :deep(.dp__input_icon_pad) {
	padding-inline-start: 12px;
}

/* Increase right padding to accommodate both icons */
.posting-date-input :deep(.dp__input) {
	padding-right: calc(30px + var(--dp-input-icon-padding));
}
</style>
