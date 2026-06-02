<template>
	<v-card
		class="cards mb-0 mt-3 dynamic-padding"
		:class="{ 'cards--with-mobile-offset': reserveBottomDockSpace }"
	>
		<v-row no-gutters align="center" justify="center" class="dynamic-spacing-sm">
			<v-col cols="12" class="mb-2">
				<v-select
					:items="itemsGroup"
					:label="frappe._('Items Group')"
					density="compact"
					variant="solo"
					hide-details
					:model-value="modelValue"
					@update:model-value="$emit('update:modelValue', $event)"
				></v-select>
			</v-col>
			<v-col cols="12" class="mb-2" v-if="posProfile.posa_enable_price_list_dropdown !== false">
				<v-text-field
					density="compact"
					variant="solo"
					color="primary"
					:label="frappe._('Price List')"
					hide-details
					:model-value="activePriceList"
					readonly
				></v-text-field>
			</v-col>
			<v-col cols="12" sm="4" class="dynamic-margin-xs">
				<v-btn-toggle
					:model-value="itemsView"
					@update:model-value="$emit('update:itemsView', $event)"
					color="primary"
					group
					density="compact"
					rounded
					class="view-toggle-btn"
				>
					<v-btn size="small" value="list">{{ __("List") }}</v-btn>
					<v-btn size="small" value="card">{{ __("Card") }}</v-btn>
				</v-btn-toggle>
			</v-col>
			<v-col cols="6" sm="4" class="dynamic-margin-xs">
				<v-btn
					size="small"
					block
					color="warning"
					variant="text"
					@click="$emit('open-offers')"
					class="action-btn-consistent"
				>
					{{ offersCount }} {{ __("Offers") }}
				</v-btn>
			</v-col>
			<v-col cols="6" sm="4" class="dynamic-margin-xs">
				<v-btn
					size="small"
					block
					color="primary"
					variant="text"
					@click="$emit('open-coupons')"
					class="action-btn-consistent"
				>
					{{ couponsCount }} {{ __("Coupons") }}
				</v-btn>
			</v-col>
		</v-row>
	</v-card>
</template>

<script setup>
const __ = window.__;
const frappe = window.frappe;

defineProps({
	modelValue: { type: String, default: "ALL" }, // item_group
	itemsGroup: { type: Array, default: () => [] },
	itemsView: { type: String, default: "card" },
	posProfile: { type: Object, required: true },
	activePriceList: { type: String, default: "" },
	offersCount: { type: Number, default: 0 },
	couponsCount: { type: Number, default: 0 },
	reserveBottomDockSpace: { type: Boolean, default: false },
});

defineEmits(["update:modelValue", "update:itemsView", "open-offers", "open-coupons"]);
</script>

<style scoped>
/* ── Offers / Coupons action buttons ─────────────────────── */
.action-btn-consistent {
	height: 38px !important;
	margin-top: var(--dynamic-xs) !important;
	padding: 0 var(--pos-space-4) !important;
	border-radius: 999px !important;
	text-transform: none !important;
	font-weight: 700 !important;
	font-size: 0.82rem !important;
	letter-spacing: 0.02em !important;
	transition: transform 0.15s ease, box-shadow 0.15s ease !important;
}

.action-btn-consistent:hover {
	transform: translateY(-1px) !important;
	box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12) !important;
}

/* ── List / Card view toggle ─────────────────────────────── */
.view-toggle-btn {
	height: 36px;
	border: 1.5px solid var(--pos-border, rgba(15,23,42,0.12));
	border-radius: 999px !important;
	overflow: hidden;
}

.view-toggle-btn :deep(.v-btn) {
	border-radius: 999px !important;
	font-weight: 600 !important;
	font-size: 0.8rem !important;
	text-transform: none !important;
}

/* ── Toolbar card at the bottom ─────────────────────────── */
.dynamic-padding {
	padding: var(--dynamic-sm);
}

.dynamic-spacing-sm {
	padding: var(--dynamic-sm) !important;
}

.cards {
	background: var(--pos-card-bg, #ffffff) !important;
	margin-top: var(--dynamic-sm) !important;
	padding: var(--dynamic-sm) !important;
	border: 1.5px solid var(--pos-border, rgba(15,23,42,0.08)) !important;
	border-radius: var(--pos-radius-md, 16px) !important;
	box-shadow: 0 -2px 12px rgba(15, 23, 42, 0.06) !important;
	position: sticky;
	bottom: 0;
	z-index: 7;
	min-width: 0;
	overflow: visible;
}

.cards--with-mobile-offset {
	margin-bottom: calc(var(--bottom-safe-space) + 6px) !important;
}

@media (max-width: 1099px) {
	.cards {
		position: static;
	}
}

@media (max-width: 768px) {
	.dynamic-padding {
		padding: var(--dynamic-xs);
	}

	.dynamic-spacing-sm {
		padding: var(--dynamic-xs) !important;
	}

	.view-toggle-btn {
		width: 100%;
	}

	.action-btn-consistent {
		min-height: 42px !important;
		font-size: 0.8rem !important;
	}
}

@media (max-width: 480px) {
	.cards {
		padding: var(--dynamic-xs) !important;
		position: static;
	}
}
</style>
