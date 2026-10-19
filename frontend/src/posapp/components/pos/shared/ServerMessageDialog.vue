<template>
	<v-dialog :model-value="Boolean(message)" max-width="760" @update:model-value="(open) => !open && emit('close')">
		<v-card v-if="message" class="pos-themed-card">
			<v-card-title class="d-flex align-center ga-2 pt-4">
				<v-icon color="error" size="20">mdi-alert-circle-outline</v-icon>
				<span>{{ message.title }}</span>
			</v-card-title>
			<!-- Server-built HTML (frappe.throw message); the server escapes the
			     data it puts in it. -->
			<v-card-text class="server-message" v-html="message.html" />
			<v-card-actions class="justify-end">
				<v-btn color="primary" variant="flat" class="text-none" @click="emit('close')">
					{{ __("Close") }}
				</v-btn>
			</v-card-actions>
		</v-card>
	</v-dialog>
</template>

<script setup>
// Shows a frappe.throw() message inside the POS app. Use with
// frappe.call({ ..., silent: true }) and parseServerError(): Frappe's own
// msgprint is a Bootstrap modal whose Desk styles are not reliably present
// on this page, so it can render as unstyled page content.
defineProps({
	// { title, html } from parseServerError(), or null when closed.
	message: { type: Object, default: null },
});
const emit = defineEmits(['close']);
</script>

<script>
/** { title, html } from a rejected frappe.call, or null if the server sent
 * no message (e.g. a network error). */
export function parseServerError(error) {
	const raw = error?._server_messages || error?.responseJSON?._server_messages;
	if (!raw) return null;
	try {
		const parts = JSON.parse(raw).map((part) => {
			try {
				return typeof part === 'string' ? JSON.parse(part) : part;
			} catch {
				return { message: String(part) };
			}
		});
		return {
			title: parts.find((part) => part.title)?.title || __('Message'),
			html: parts.map((part) => part.message || '').join('<br>'),
		};
	} catch {
		return { title: __('Message'), html: frappe.utils.escape_html(String(raw)) };
	}
}
</script>

<style scoped>
.server-message :deep(table) {
	width: 100%;
	margin-top: 12px;
	border-collapse: collapse;
}

.server-message :deep(th),
.server-message :deep(td) {
	border: 1px solid rgba(var(--v-theme-on-surface), 0.12);
	padding: 6px 8px;
	vertical-align: top;
}

.server-message :deep(th) {
	font-weight: 600;
	background: rgba(var(--v-theme-on-surface), 0.04);
}

.server-message :deep(.text-right) {
	text-align: right;
}
</style>
