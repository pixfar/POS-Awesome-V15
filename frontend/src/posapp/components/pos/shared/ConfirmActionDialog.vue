<template>
	<v-dialog
		:model-value="modelValue"
		max-width="420"
		transition="dialog-bottom-transition"
		@update:model-value="$emit('update:modelValue', $event)"
	>
		<v-card class="pos-themed-card">
			<v-card-title class="text-h6">
				{{ title }}
			</v-card-title>
			<v-card-text>
				{{ message }}
			</v-card-text>
			<v-card-actions>
				<v-spacer />
				<v-btn variant="text" :disabled="loading" @click="$emit('update:modelValue', false)">
					{{ cancelLabel }}
				</v-btn>
				<v-btn
					ref="confirmBtn"
					:color="confirmColor"
					variant="flat"
					autofocus
					:loading="loading"
					@click="$emit('confirm')"
				>
					{{ confirmLabel }}
				</v-btn>
			</v-card-actions>
		</v-card>
	</v-dialog>
</template>

<script setup>
import { nextTick, ref, watch } from 'vue';

defineOptions({
	name: 'ConfirmActionDialog',
});

const props = defineProps({
	modelValue: Boolean,
	title: { type: String, default: 'Are you sure?' },
	message: { type: String, default: '' },
	confirmLabel: { type: String, default: 'Confirm' },
	cancelLabel: { type: String, default: 'Back' },
	confirmColor: { type: String, default: 'primary' },
	loading: { type: Boolean, default: false },
});

defineEmits(['update:modelValue', 'confirm']);

const confirmBtn = ref(null);

watch(
	() => props.modelValue,
	(val) => {
		if (val) {
			nextTick(() => {
				setTimeout(() => {
					confirmBtn.value?.$el?.focus();
				}, 100);
			});
		}
	},
);
</script>
