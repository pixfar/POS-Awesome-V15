<template>
	<div class="pl-row-wrap">
		<div
			class="pl-row"
			:class="{ 'pl-row--group': node.is_group, 'pl-row--total': node.isTotal }"
			:style="{ paddingLeft: node.indent * 22 + 12 + 'px' }"
		>
			<button
				v-if="node.children.length"
				type="button"
				class="pl-row__toggle"
				@click="node.expanded = !node.expanded"
			>
				<v-icon size="16">
					{{ node.expanded ? 'mdi-chevron-down' : 'mdi-chevron-right' }}
				</v-icon>
			</button>
			<span v-else class="pl-row__toggle-spacer"></span>

			<span class="pl-row__label">{{ node.label }}</span>

			<span
				class="pl-row__value"
				:class="{ 'pl-row__value--negative': node.value < 0 }"
			>
				{{ node.formattedValue }}
			</span>
		</div>

		<template v-if="node.children.length && node.expanded">
			<ProfitAndLossRow v-for="child in node.children" :key="child.id" :node="child" />
		</template>
	</div>
</template>

<script setup>
defineProps({
	node: {
		type: Object,
		required: true,
	},
});
</script>

<style scoped>
.pl-row {
	display: flex;
	align-items: center;
	gap: 8px;
	padding: 8px 12px 8px 0;
	border-bottom: 1px solid var(--pos-border, rgba(0, 0, 0, 0.06));
}

.pl-row--group .pl-row__label {
	font-weight: 600;
}

.pl-row--total {
	background: var(--pos-hover-bg, rgba(0, 0, 0, 0.02));
}

.pl-row--total .pl-row__label,
.pl-row--total .pl-row__value {
	font-weight: 700;
}

.pl-row__toggle {
	display: flex;
	align-items: center;
	justify-content: center;
	width: 20px;
	height: 20px;
	flex-shrink: 0;
	border: none;
	background: transparent;
	cursor: pointer;
	color: var(--pos-text-secondary, #666);
	padding: 0;
}

.pl-row__toggle-spacer {
	width: 20px;
	flex-shrink: 0;
}

.pl-row__label {
	flex: 1;
	min-width: 0;
	color: var(--pos-text-primary, #212121);
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
}

.pl-row__value {
	flex-shrink: 0;
	min-width: 130px;
	text-align: right;
	color: var(--pos-text-primary, #212121);
	font-variant-numeric: tabular-nums;
}

.pl-row__value--negative {
	color: #dc2626;
}
</style>
