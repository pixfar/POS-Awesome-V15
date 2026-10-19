<template>
	<div class="pos-list-pagination">
		<div class="pos-list-pagination__info">
			{{ total ? __("Page {0} of {1}", [page, totalPages]) : __("No results") }}
		</div>
		<div class="pos-list-pagination__controls">
			<v-select
				:model-value="pageSize"
				:items="pageSizes"
				density="compact"
				variant="outlined"
				hide-details
				class="pos-themed-input pos-list-pagination__page-size"
				@update:model-value="(size) => emit('update:pageSize', size)"
			/>
			<v-btn
				icon="mdi-page-first"
				size="small"
				variant="text"
				:disabled="page <= 1 || loading"
				@click="go(1)"
			/>
			<v-btn
				icon="mdi-chevron-left"
				size="small"
				variant="text"
				:disabled="page <= 1 || loading"
				@click="go(page - 1)"
			/>
			<v-btn
				v-for="pageNumber in pageNumbers"
				:key="pageNumber"
				size="small"
				:variant="pageNumber === page ? 'flat' : 'text'"
				:color="pageNumber === page ? 'primary' : undefined"
				class="pos-list-pagination__page-btn"
				:disabled="loading"
				@click="go(pageNumber)"
			>
				{{ pageNumber }}
			</v-btn>
			<v-btn
				icon="mdi-chevron-right"
				size="small"
				variant="text"
				:disabled="page >= totalPages || loading"
				@click="go(page + 1)"
			/>
			<v-btn
				icon="mdi-page-last"
				size="small"
				variant="text"
				:disabled="page >= totalPages || loading"
				@click="go(totalPages)"
			/>
		</div>
	</div>
</template>

<script setup>
// Page controls shared by the POS list pages: page-size picker, first/prev,
// a 5-page window, next/last. The parent owns `page`/`pageSize` and reloads
// on update:page / update:pageSize. Styles come from invoice-shared-styles.css
// (imported below, as on every list page, since they are scoped).
import { computed } from 'vue';

const props = defineProps({
	page: { type: Number, required: true },
	pageSize: { type: Number, required: true },
	total: { type: Number, required: true },
	loading: { type: Boolean, default: false },
	pageSizes: { type: Array, default: () => [10, 20, 50] },
});

const emit = defineEmits(['update:page', 'update:pageSize']);

const totalPages = computed(() => Math.max(1, Math.ceil(props.total / (props.pageSize || 1))));

const pageNumbers = computed(() => {
	const windowSize = 5;
	let start = Math.max(1, props.page - Math.floor(windowSize / 2));
	const end = Math.min(totalPages.value, start + windowSize - 1);
	start = Math.max(1, end - windowSize + 1);
	const pages = [];
	for (let p = start; p <= end; p++) pages.push(p);
	return pages;
});

const go = (target) => {
	if (target < 1 || target > totalPages.value || target === props.page) return;
	emit('update:page', target);
};
</script>

<style scoped>
@import '../invoice-shared-styles.css';
</style>
