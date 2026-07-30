<template>
	<div
		:class="['card-item-card', { 'item-highlighted': isItemHighlighted }]"
		@click="onClick"
		:draggable="true"
		@dragstart="onDragStart"
		@dragend="onDragEnd"
	>
		<div class="card-item-image-container">
			<div
				class="stock-badge"
				:class="numericStockQty > 10 ? 'stock-badge--ok' : 'stock-badge--low'"
			>
				{{ formattedBadgeStock }} {{ __("In Stock") }}
			</div>
			<div v-if="showRateInfo" class="info-btn-overlay" @click.stop>
				<ItemRateInfoMenu
					:rate-info="rateInfo"
					:currency-symbol="currencySymbol"
					:format-currency="formatCurrency"
					:rate-precision="ratePrecision"
				/>
			</div>
			<v-img
				:src="item.image || placeholderImage"
				class="card-item-image"
				aspect-ratio="1"
				:alt="item.item_name"
			>
				<template #placeholder>
					<div class="image-placeholder">
						<v-icon size="40" color="grey-lighten-2"> mdi-image </v-icon>
					</div>
				</template>
			</v-img>
		</div>
		<div class="card-item-content">
			<div class="card-item-header">
				<h4 class="card-item-name">{{ item.item_name }}</h4>
				<span class="card-item-code">{{ item.item_code }}</span>
			</div>
			<div class="card-item-details">
				<div class="card-item-price">
					<div class="primary-price">
						<span class="currency-symbol">
							{{ currencySymbol(primaryCurrency) }}
						</span>
						<span class="price-amount">
							{{ formatCurrency(primaryRate, primaryCurrency, primaryPrecision) }}
						</span>
					</div>
					<div v-if="showSecondaryPrice" class="secondary-price">
						<span class="currency-symbol">
							{{ currencySymbol(secondaryCurrency) }}
						</span>
						<span class="price-amount">
							{{ formatCurrency(item.rate, secondaryCurrency, primaryPrecision) }}
						</span>
					</div>
				</div>
				<div class="card-item-stock">
					<v-icon size="small" class="stock-icon"> mdi-package-variant </v-icon>
					<span
						class="stock-amount"
						:class="{
							'negative-number': isNegative(item.actual_qty),
						}"
					>
						{{ formattedActualQty }}
					</span>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed } from "vue";
import placeholderImage from "../placeholder-image.png";
import ItemRateInfoMenu from "./ItemRateInfoMenu.vue";
const __ = window.__ || ((text) => text);

const props = defineProps({
	item: { type: Object, required: true },
	posProfile: { type: Object, required: true },
	context: { type: String, default: "pos" },
	selectedCurrency: { type: String, default: "" },
	hideQtyDecimals: { type: Boolean, default: false },
	showRateInfo: { type: Boolean, default: true },
	getItemRateInfo: { type: Function, required: true },
	isItemHighlighted: { type: Boolean, default: false },
	currencySymbol: { type: Function, required: true },
	formatCurrency: { type: Function, required: true },
	formatNumber: { type: Function, required: true },
	ratePrecision: { type: Function, required: true },
	isNegative: { type: Function, default: (val) => val < 0 },
});

const emit = defineEmits(["click", "dragstart", "dragend"]);

const primaryCurrency = computed(() => {
	if (props.context === "purchase") {
		return (
			props.item.original_currency ||
			props.item.currency ||
			props.item.price_list_currency ||
			props.posProfile.currency
		);
	}
	return (
		props.item.original_currency ||
		props.item.currency ||
		props.item.price_list_currency ||
		props.posProfile.currency
	);
});

const primaryRate = computed(() => {
	if (props.context === "purchase") {
		return props.item.original_rate ?? props.item.rate ?? props.item.standard_rate ?? 0;
	}
	return props.item.original_rate ?? props.item.rate ?? 0;
});

const primaryPrecision = computed(() => {
	return props.ratePrecision(primaryRate.value);
});

const rateInfo = computed(() => props.getItemRateInfo(props.item));

const secondaryCurrency = computed(() => props.selectedCurrency);

const showSecondaryPrice = computed(() => {
	return (
		props.context !== "purchase" &&
		props.posProfile.posa_allow_multi_currency &&
		Boolean(props.selectedCurrency) &&
		props.selectedCurrency !== primaryCurrency.value
	);
});

const formattedActualQty = computed(() => {
	const numericQty = Number(props.item.actual_qty ?? 0);
	if (!Number.isFinite(numericQty)) {
		return 0;
	}
	if (props.hideQtyDecimals) {
		return props.formatNumber(Math.round(numericQty), 0);
	}
	return props.formatNumber(numericQty, 4);
});

const numericStockQty = computed(() => {
	const qty = Number(props.item.actual_qty ?? 0);
	return Number.isFinite(qty) ? qty : 0;
});

const formattedBadgeStock = computed(() => {
	if (props.hideQtyDecimals) {
		return Math.round(numericStockQty.value);
	}
	return Number(numericStockQty.value.toFixed(2));
});

const onClick = (event) => {
	emit("click", event, props.item);
};

const onDragStart = (event) => {
	emit("dragstart", event, props.item);
};

const onDragEnd = (event) => {
	emit("dragend", event);
};
</script>

<style scoped>
.card-item-card {
	background: #ffffff;
	border-radius: 12px;
	border: 1px solid rgba(17, 24, 39, 0.12);
	overflow: hidden;
	transition:
		transform 0.2s cubic-bezier(0.4, 0, 0.2, 1),
		box-shadow 0.2s ease,
		border-color 0.2s ease,
		background-color 0.2s ease;
	cursor: pointer;
	display: flex;
	flex-direction: column;
	height: 100%;
	width: 100%;
	box-shadow: none;
	will-change: transform;
	backface-visibility: hidden;
	transform: translate3d(0, 0, 0);
	position: relative;
	/* Enable CSS container queries so child elements can adapt to card width */
	container-type: inline-size;
	container-name: item-card;
}

.card-item-card:hover {
	transform: none;
	box-shadow: none;
	border-color: color-mix(in srgb, var(--pos-primary) 35%, transparent);
}

.card-item-card.item-highlighted {
	border-color: var(--pos-primary);
	box-shadow: 0 0 0 2px color-mix(in srgb, var(--pos-primary) 15%, transparent);
	transform: none;
	background: #ffffff;
}

.card-item-image-container {
	position: relative;
	height: 100px;
	flex-shrink: 0;
	overflow: hidden;
	background: #f9fafb;
}

/* "i" info button pinned to top-left of the image */
.info-btn-overlay {
	position: absolute;
	top: 4px;
	left: 6px;
	z-index: 3;
	line-height: 0;
}

.stock-badge {
	position: absolute;
	top: 8px;
	right: 8px;
	z-index: 2;
	font-size: 13px;
	font-weight: 700;
	padding: 3px 8px;
	border-radius: 6px;
	border: 1px solid transparent;
}

.stock-badge--ok {
	background: #ecfdf3;
	color: #15803d;
	border-color: #bbf7d0;
}

.stock-badge--low {
	background: #fef2f2;
	color: #b91c1c;
	border-color: #fecaca;
}

.card-item-image {
	width: 100%;
	height: 100%;
	object-fit: contain; /* Changed to contain to ensure full image visibility */
	background-color: rgb(var(--v-theme-surface-bright));
}

/* Image Placeholder Style */
.image-placeholder {
	display: flex;
	align-items: center;
	justify-content: center;
	width: 100%;
	height: 100%;
	background-color: rgb(var(--v-theme-surface-variant));
}

.card-item-content {
	padding: 7px 10px;
	display: flex;
	flex-direction: column;
	flex-grow: 1;
	justify-content: flex-start;
	gap: 4px;
}

.card-item-header {
	display: flex;
	flex-direction: column;
	gap: var(--pos-space-1);
}

.card-item-name {
	font-size: 0.92rem;
	font-weight: 700;
	margin: 0;
	line-height: 1.35;
	color: var(--pos-text-primary);
	overflow: hidden;
	display: -webkit-box;
	-webkit-line-clamp: 2;
	line-clamp: 2;
	-webkit-box-orient: vertical;
}

.card-item-code {
	font-size: 0.7rem;
	color: #9ca3af;
	display: block;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
	letter-spacing: 0.02em;
}

.card-item-details {
	display: flex;
	justify-content: space-between;
	align-items: flex-start;
	gap: var(--pos-space-2);
}

.card-item-price {
	display: flex;
	flex-direction: column;
	gap: var(--pos-space-1);
	min-width: 0;
}

.primary-price {
	display: flex;
	align-items: baseline;
	flex-wrap: wrap;
	gap: var(--pos-space-1);
	font-weight: 700;
	color: var(--pos-primary-variant);
	font-size: 1.25rem;
}

.secondary-price {
	font-size: 0.8rem;
	color: var(--pos-text-secondary);
}

.card-item-stock {
	text-align: right;
	font-size: 0.75rem;
	color: #6b7280;
	display: flex;
	flex-direction: row;
	align-items: flex-end;
	gap: 6px;
	padding: 4px 6px;
	border-radius: 6px;
	background: #f9fafb;
	white-space: nowrap;
}

.stock-amount {
	font-weight: 600;
}

.stock-amount.negative-number {
	color: rgb(var(--v-theme-error));
}

.stock-uom {
	font-size: 0.7rem;
	text-transform: uppercase;
}

/* ── Medium card (160 px – 220 px wide, e.g. 4-column layout) ── */
@container item-card (max-width: 220px) {
	.card-item-image-container {
		height: 80px;
	}

	.card-item-content {
		padding: 8px 10px;
		gap: 4px;
	}

	.card-item-name {
		font-size: 0.8rem;
		-webkit-line-clamp: 2;
		line-clamp: 2;
	}

	.card-item-code {
		font-size: 0.65rem;
	}

	.primary-price {
		font-size: 1rem;
	}

	.card-item-stock {
		font-size: 0.65rem;
		padding: 3px 5px;
		gap: 4px;
	}

	.stock-badge {
		font-size: 11px;
		padding: 2px 6px;
	}
}

/* ── Compact card (≤ 160 px wide, e.g. 5-column layout) ── */
@container item-card (max-width: 160px) {
	.card-item-image-container {
		height: 64px;
	}

	.card-item-content {
		padding: 6px 8px;
		gap: 3px;
	}

	.card-item-name {
		font-size: 0.72rem;
		-webkit-line-clamp: 1;
		line-clamp: 1;
	}

	.card-item-code {
		font-size: 0.6rem;
	}

	.card-item-details {
		flex-direction: column;
		align-items: flex-start;
		gap: 3px;
	}

	.primary-price {
		font-size: 0.88rem;
		gap: 2px;
	}

	.card-item-stock {
		font-size: 0.6rem;
		padding: 2px 4px;
		gap: 3px;
	}

	.stock-badge {
		font-size: 10px;
		padding: 2px 5px;
		top: 5px;
		right: 5px;
	}
}
</style>
