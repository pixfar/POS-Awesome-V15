<template>
	<v-autocomplete
		:model-value="modelValue"
		v-model:search="searchText"
		:items="options"
		:loading="loading"
		item-value="item_code"
		:item-title="optionTitle"
		:label="label"
		density="compact"
		variant="outlined"
		hide-details
		clearable
		:custom-filter="() => true"
		:no-data-text="loading ? __('Searching...') : __('No items found')"
		:menu-props="{ maxHeight: 360 }"
		class="pos-themed-input pos-list-filter-field"
		@update:model-value="onPick"
		@update:search="onSearch"
		@update:menu="onMenu"
	>
		<template #item="{ props: itemProps, item }">
			<v-list-item v-bind="itemProps" :title="undefined">
				<v-list-item-title class="list-item-filter__name">
					{{ item.raw.item_name || item.raw.item_code }}
				</v-list-item-title>
				<v-list-item-subtitle class="list-item-filter__code">
					{{ item.raw.item_code }}
				</v-list-item-subtitle>
			</v-list-item>
		</template>
		<template #append-item>
			<div v-if="hasMore" v-intersect="onEndReached" class="list-item-filter__more">
				<v-progress-circular v-if="loading" indeterminate size="18" width="2" color="primary" />
			</div>
		</template>
	</v-autocomplete>
</template>

<script setup>
// Item filter for list pages. Searches like the item search above the cart:
// through Frappe's Item link search, which on BSP sites is the ranked POS
// search (bsp_engineering/api/item_search.py) -- Bangla digits fold to ASCII,
// every word must match, exact/leading code matches first. Opening the
// dropdown lists items straight away (no typing needed) and scrolling to the
// bottom loads the next page. The v-model is the selected item code.
import { onBeforeUnmount, ref, watch } from "vue";

const __ = window.__;

const props = defineProps({
	modelValue: { type: String, default: null },
	label: { type: String, default: "" },
});

const emit = defineEmits(["update:modelValue"]);

const PAGE_SIZE = 20;
const SEARCH_DELAY_MS = 300;

const options = ref([]);
const loading = ref(false);
const hasMore = ref(false);
const searchText = ref("");

let loadedTerm = null; // term the current options were loaded for
let requestId = 0;
let searchTimer = null;

const optionTitle = (option) =>
	option?.item_name ? `${option.item_name} - ${option.item_code}` : option?.item_code || "";

async function fetchPage(term, start) {
	const id = ++requestId;
	loading.value = true;
	try {
		const { message } = await frappe.call({
			method: "frappe.desk.search.search_link",
			args: { doctype: "Item", txt: term, page_length: PAGE_SIZE, start },
		});
		if (id !== requestId) return; // a newer search replaced this one
		const rows = (message || []).map((row) => ({
			item_code: row.value,
			item_name: row.description || "",
		}));
		const seen = new Set(start ? options.value.map((o) => o.item_code) : []);
		const fresh = rows.filter((row) => !seen.has(row.item_code));
		options.value = start ? options.value.concat(fresh) : keepSelected(rows);
		loadedTerm = term;
		hasMore.value = rows.length === PAGE_SIZE && fresh.length > 0;
	} catch {
		if (id === requestId) hasMore.value = false;
	} finally {
		if (id === requestId) loading.value = false;
	}
}

// Keep the selected item in the options so its name stays shown in the field.
function keepSelected(rows) {
	const selected = options.value.find((o) => o.item_code === props.modelValue);
	if (selected && !rows.some((r) => r.item_code === selected.item_code)) {
		return [selected, ...rows];
	}
	return rows;
}

// While an item is selected the field shows its title; that is not a query.
function currentTerm() {
	const text = String(searchText.value || "").trim();
	const selected = options.value.find((o) => o.item_code === props.modelValue);
	return selected && text === optionTitle(selected) ? "" : text;
}

function onSearch() {
	clearTimeout(searchTimer);
	searchTimer = setTimeout(() => {
		const term = currentTerm();
		if (term !== loadedTerm) fetchPage(term, 0);
	}, SEARCH_DELAY_MS);
}

function onMenu(open) {
	if (open && currentTerm() !== loadedTerm) {
		fetchPage(currentTerm(), 0);
	}
}

function onEndReached(isIntersecting) {
	if (isIntersecting && hasMore.value && !loading.value) {
		fetchPage(loadedTerm ?? "", options.value.length);
	}
}

function onPick(value) {
	emit("update:modelValue", value || null);
}

// A filter restored from storage only has the code: look up its name.
watch(
	() => props.modelValue,
	async (code) => {
		if (!code || options.value.some((o) => o.item_code === code)) return;
		options.value = [{ item_code: code, item_name: "" }, ...options.value];
		try {
			const { message } = await frappe.call({
				method: "frappe.client.get_value",
				args: { doctype: "Item", filters: { name: code }, fieldname: "item_name" },
			});
			const option = options.value.find((o) => o.item_code === code);
			if (option && message?.item_name) option.item_name = message.item_name;
		} catch {
			// Name unavailable: the code alone is shown.
		}
	},
	{ immediate: true },
);

onBeforeUnmount(() => clearTimeout(searchTimer));
</script>

<style scoped>
.list-item-filter__name {
	font-weight: 600;
	white-space: normal;
}

.list-item-filter__code {
	font-family: "Roboto Mono", ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
	font-size: 0.78rem;
}

.list-item-filter__more {
	display: flex;
	justify-content: center;
	min-height: 28px;
	padding: 4px 0;
}
</style>
