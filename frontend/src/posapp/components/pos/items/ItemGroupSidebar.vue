<template>
	<div class="group-sidebar">
		<div class="group-sidebar__title">{{ __("Item Group") }}</div>
		<form class="group-sidebar__search" autocomplete="posa-off" @submit.prevent>
			<v-text-field
				v-model="search"
				:placeholder="__('Search group')"
				density="compact"
				variant="outlined"
				hide-details
				clearable
				prepend-inner-icon="mdi-folder-outline"
				autocomplete="posa-off"
				name="posa_item_group_search"
				:spellcheck="false"
			/>
		</form>
		<div class="group-sidebar__list">
			<button
				v-for="group in filteredGroups"
				:key="group"
				type="button"
				class="group-sidebar__item"
				:class="{ 'group-sidebar__item--active': group === modelValue }"
				:title="group"
				@click="selectGroup(group)"
			>
				{{ group === "ALL" ? __("All Groups") : group }}
			</button>
			<div v-if="!filteredGroups.length" class="group-sidebar__empty">
				{{ __("No groups") }}
			</div>
		</div>
	</div>
</template>

<script setup>
const __ = window.__;

import { ref, computed } from "vue";

const props = defineProps({
	modelValue: { type: String, default: "ALL" },
	itemsGroup: { type: Array, default: () => [] },
});

const emit = defineEmits(["update:modelValue"]);

const search = ref("");

// Bengali (Bangla) names first, English/Latin names last. "ALL" stays pinned
// at the top. Within each bucket keep alphabetical order.
const BANGLA_RE = /[ঀ-৿]/;
const sortGroups = (groups) => {
	const all = [];
	const bangla = [];
	const english = [];
	for (const g of groups) {
		const name = String(g);
		if (name === "ALL") {
			all.push(g);
		} else if (BANGLA_RE.test(name)) {
			bangla.push(g);
		} else {
			english.push(g);
		}
	}
	const byName = (a, b) =>
		String(a).localeCompare(String(b), undefined, { sensitivity: "base" });
	bangla.sort(byName);
	english.sort(byName);
	return [...all, ...bangla, ...english];
};

const filteredGroups = computed(() => {
	// clearable v-text-field sets model to null on clear — never call .trim() on it.
	const term = String(search.value ?? "").trim().toLowerCase();
	const base =
		!term
			? props.itemsGroup
			: props.itemsGroup.filter((g) =>
					String(g).toLowerCase().includes(term),
				);
	return sortGroups(base);
});


const selectGroup = (group) => {
	emit("update:modelValue", group || "ALL");
};
</script>

<style scoped>
.group-sidebar {
	display: flex;
	flex-direction: column;
	height: 100%;
	min-height: 0;
	gap: 8px;
	padding: 8px;
	border-right: 1px solid var(--pos-border, rgba(15, 23, 42, 0.08));
	background: color-mix(
		in srgb,
		var(--pos-primary) 3%,
		var(--pos-card-bg, #fff)
	);
	box-sizing: border-box;
}

.group-sidebar__title {
	flex: 0 0 auto;
	font-size: 1rem;
	font-weight: 700;
	color: var(--pos-text-primary, #1f2937);
	padding: 2px 4px;
}

.group-sidebar__search {
	flex: 0 0 auto;
}

.group-sidebar__list {
	flex: 1 1 auto;
	min-height: 0;
	overflow-y: auto;
	display: flex;
	flex-direction: column;
	gap: 4px;
	padding-right: 2px;
	scrollbar-width: thin;
}

.group-sidebar__item {
	display: block;
	width: 100%;
	flex: 0 0 auto;
	text-align: left;
	padding: 9px 10px;
	min-height: 36px;
	border-radius: var(--pos-radius-sm, 10px);
	font-size: 0.82rem;
	line-height: 1.3;
	color: var(--pos-text-primary, #1f2937);
	background: color-mix(in srgb, var(--pos-primary) 5%, #fff);
	border: 1px solid var(--pos-border, rgba(15, 23, 42, 0.08));
	cursor: pointer;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
	transition:
		background 0.12s ease,
		color 0.12s ease;
}

.group-sidebar__item:hover {
	background: color-mix(in srgb, var(--pos-primary) 10%, transparent);
}

.group-sidebar__item--active {
	background: var(--pos-primary);
	color: #fff;
	font-weight: 600;
}

.group-sidebar__item--active:hover {
	background: var(--pos-primary);
}

.group-sidebar__empty {
	padding: 10px;
	font-size: 0.8rem;
	color: var(--pos-text-secondary, #6b7280);
	text-align: center;
}
</style>
