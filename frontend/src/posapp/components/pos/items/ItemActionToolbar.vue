<template>
	<div
		class="item-toolbar"
		:class="{ 'item-toolbar--dock-offset': reserveBottomDockSpace }"
	>
		<div class="item-toolbar__filters">
			<v-autocomplete
				class="item-toolbar__field"
				:items="itemsGroup"
				:label="frappe._('Items Group')"
				:placeholder="__('Search item group')"
				density="compact"
				variant="outlined"
				hide-details
				clearable
				auto-select-first
				:model-value="modelValue"
				@update:model-value="onItemGroupUpdate"
			>
				<template #prepend-inner>
					<v-icon size="18" class="item-toolbar__field-icon">
						mdi-folder-outline
					</v-icon>
				</template>
			</v-autocomplete>

			<v-text-field
				v-if="posProfile.posa_enable_price_list_dropdown !== false"
				class="item-toolbar__field"
				density="compact"
				variant="outlined"
				color="primary"
				:label="frappe._('Price List')"
				hide-details
				:model-value="activePriceList"
				readonly
			>
				<template #prepend-inner>
					<v-icon size="18" class="item-toolbar__field-icon">
						mdi-tag-outline
					</v-icon>
				</template>
			</v-text-field>
		</div>

		<div class="item-toolbar__actions">
			<span class="item-toolbar__view-label">{{ __("View") }}</span>
			<v-btn-toggle
				:model-value="itemsView"
				@update:model-value="$emit('update:itemsView', $event)"
				color="primary"
				group
				density="compact"
				rounded="lg"
				class="item-toolbar__view-toggle"
			>
				<v-btn size="small" value="list">
					<v-icon start size="16">mdi-view-list-outline</v-icon>
					{{ __("List") }}
				</v-btn>
				<v-btn size="small" value="card">
					<v-icon start size="16">mdi-view-grid-outline</v-icon>
					{{ __("Card") }}
				</v-btn>
			</v-btn-toggle>
		</div>
	</div>
</template>

<script setup>
const __ = window.__;
const frappe = window.frappe;

defineProps({
	modelValue: { type: String, default: "ALL" },
	itemsGroup: { type: Array, default: () => [] },
	itemsView: { type: String, default: "card" },
	posProfile: { type: Object, required: true },
	activePriceList: { type: String, default: "" },
	offersCount: { type: Number, default: 0 },
	couponsCount: { type: Number, default: 0 },
	reserveBottomDockSpace: { type: Boolean, default: false },
});

const emit = defineEmits([
	"update:modelValue",
	"update:itemsView",
	"open-offers",
	"open-coupons",
]);

const onItemGroupUpdate = (value) => {
	emit("update:modelValue", value || "ALL");
};
</script>

<style scoped>
.item-toolbar {
	display: flex;
	flex-wrap: wrap;
	align-items: center;
	justify-content: space-between;
	gap: 8px 10px;
	margin-top: auto;
	margin-bottom: 10px;
	padding: 8px 10px;
	border: 1px solid var(--pos-border, rgba(15, 23, 42, 0.08));
	border-radius: var(--pos-radius-md, 14px);
	background: color-mix(
		in srgb,
		var(--pos-primary) 4%,
		var(--pos-card-bg, #fff)
	);
	box-shadow: 0 1px 2px
		color-mix(in srgb, var(--pos-shadow, #000) 6%, transparent);
	position: relative;
	z-index: 7;
	width: 100%;
	max-width: 100%;
	min-width: 0;
	flex: 0 0 auto;
	align-self: stretch;
	box-sizing: border-box;
}

.item-toolbar--dock-offset {
	margin-bottom: calc(var(--bottom-safe-space) + 6px);
}

.item-toolbar__filters {
	display: flex;
	flex: 1 1 220px;
	flex-wrap: nowrap;
	align-items: center;
	gap: 8px;
	min-width: 0;
}

.item-toolbar__field {
	flex: 1 1 0;
	min-width: 0;
}

.item-toolbar__field :deep(.v-field) {
	border-radius: var(--pos-radius-sm, 10px) !important;
	background: var(--pos-card-bg, #fff) !important;
	box-shadow: none !important;
}

.item-toolbar__field :deep(.v-field__outline) {
	--v-field-border-opacity: 0.55;
}

.item-toolbar__field-icon {
	color: var(--pos-primary);
	opacity: 0.85;
}

.item-toolbar__actions {
	display: inline-flex;
	align-items: center;
	gap: 8px;
	flex-shrink: 0;
}

.item-toolbar__view-label {
	font-size: 11px;
	font-weight: 600;
	letter-spacing: 0.04em;
	text-transform: uppercase;
	color: var(--pos-text-secondary, #6b7280);
}

.item-toolbar__view-toggle {
	height: 34px;
	border: 1px solid color-mix(in srgb, var(--pos-primary) 22%, transparent);
	border-radius: 999px !important;
	overflow: hidden;
	background: var(--pos-card-bg, #fff);
}

.item-toolbar__view-toggle :deep(.v-btn) {
	border-radius: 999px !important;
	font-weight: 600 !important;
	font-size: 0.78rem !important;
	text-transform: none !important;
	letter-spacing: 0.01em !important;
	min-width: 68px;
}

.item-toolbar__view-toggle :deep(.v-btn--active) {
	box-shadow: none !important;
}

@media (max-width: 768px) {
	.item-toolbar {
		padding: 8px;
		gap: 8px;
	}

	.item-toolbar__filters {
		flex: 1 1 100%;
		flex-wrap: wrap;
	}

	.item-toolbar__field {
		flex: 1 1 100%;
	}

	.item-toolbar__actions {
		width: 100%;
		justify-content: space-between;
	}

	.item-toolbar__view-toggle {
		flex: 1;
	}

	.item-toolbar__view-toggle :deep(.v-btn) {
		flex: 1;
	}
}

@media (max-width: 480px) {
	.item-toolbar__view-label {
		display: none;
	}
}
</style>
