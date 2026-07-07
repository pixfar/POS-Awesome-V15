<template>
	<v-menu
		v-model="menuOpen"
		:disabled="disabled"
		:close-on-content-click="false"
		location="bottom start"
		transition="scale-transition"
	>
		<template #activator="{ props: menuProps }">
			<v-text-field
				v-bind="menuProps"
				:model-value="displayValue"
				:label="label"
				:density="density"
				:variant="variant"
				:hide-details="hideDetails"
				:clearable="clearable"
				:disabled="disabled"
				readonly
				prepend-inner-icon="mdi-calendar-month-outline"
				:class="fieldClass"
				@click:clear.stop="handleClear"
			/>
		</template>
		<v-date-picker
			:model-value="pickerValue"
			:max="maxDateObj"
			:min="minDateObj"
			hide-header
			show-adjacent-months
			color="primary"
			@update:model-value="handleSelect"
		/>
	</v-menu>
</template>

<script setup>
import { ref, computed } from "vue";

const props = defineProps({
	modelValue: { type: String, default: "" },
	label: { type: String, default: "" },
	density: { type: String, default: "compact" },
	variant: { type: String, default: "outlined" },
	hideDetails: { type: [Boolean, String], default: true },
	clearable: { type: Boolean, default: true },
	fieldClass: { type: [String, Array, Object], default: "pos-themed-input" },
	max: { type: String, default: "" },
	min: { type: String, default: "" },
	disabled: { type: Boolean, default: false },
});

const emit = defineEmits(["update:modelValue"]);

const menuOpen = ref(false);

// The rest of the app works with plain "YYYY-MM-DD" strings (query filters,
// API args, backend comparisons) — v-date-picker works with Date objects, so
// this component is the single place that converts between the two.
const parseDateString = (value) => {
	if (!value) return null;
	const parts = String(value).split("-").map(Number);
	if (parts.length !== 3 || parts.some((n) => Number.isNaN(n))) return null;
	const [year, month, day] = parts;
	return new Date(year, month - 1, day);
};

const formatDateString = (date) => {
	if (!(date instanceof Date) || Number.isNaN(date.getTime())) return "";
	const year = date.getFullYear();
	const month = String(date.getMonth() + 1).padStart(2, "0");
	const day = String(date.getDate()).padStart(2, "0");
	return `${year}-${month}-${day}`;
};

const pickerValue = computed(() => parseDateString(props.modelValue));
const maxDateObj = computed(() => parseDateString(props.max));
const minDateObj = computed(() => parseDateString(props.min));

const displayValue = computed(() => {
	if (!props.modelValue) return "";
	const [year, month, day] = props.modelValue.split("-");
	return year && month && day ? `${day}-${month}-${year}` : props.modelValue;
});

const handleSelect = (value) => {
	emit("update:modelValue", formatDateString(value));
	menuOpen.value = false;
};

const handleClear = () => {
	emit("update:modelValue", "");
};
</script>
