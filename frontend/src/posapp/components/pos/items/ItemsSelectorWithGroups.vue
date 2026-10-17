<template>
	<div class="selector-with-groups">
		<ItemGroupSidebar
			class="selector-group-col"
			:model-value="itemsStore.itemGroup"
			:items-group="itemsStore.itemGroups"
			@update:model-value="itemsStore.filterByGroup($event)"
		/>
		<ItemsSelector class="selector-with-groups__main" v-bind="$attrs" />
	</div>
</template>

<script setup>
import { useItemsStore } from "../../../stores/itemsStore";
import ItemGroupSidebar from "./ItemGroupSidebar.vue";
import ItemsSelector from "./ItemsSelector.vue";

defineOptions({ inheritAttrs: false });

const itemsStore = useItemsStore();
</script>

<style scoped>
.selector-with-groups {
	display: flex;
	flex-direction: row;
	gap: var(--dynamic-sm, 8px);
	align-items: stretch;
	height: 100%;
	min-height: 0;
	width: 100%;
	overflow: hidden;
}

.selector-group-col {
	flex: 0 0 200px;
	width: 200px;
	max-width: 42%;
	min-height: 0;
	height: 100%;
	overflow: hidden;
	border-radius: 12px;
	border: 1px solid rgba(17, 24, 39, 0.1);
	background: #ffffff;
}

.selector-with-groups__main {
	flex: 1 1 auto;
	min-width: 0;
	min-height: 0;
	height: 100%;
	overflow: hidden;
}

@media (max-width: 600px) {
	.selector-group-col {
		flex-basis: 132px;
		width: 132px;
	}
}
</style>
