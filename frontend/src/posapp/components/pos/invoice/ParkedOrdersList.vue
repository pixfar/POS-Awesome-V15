<template>
	<section class="drafts-list">
		<div class="drafts-list__header">
			<div>
				<p class="drafts-list__eyebrow">{{ eyebrow || __("Ready to resume") }}</p>
				<h4 class="drafts-list__title">{{ title || __("Drafts") }}</h4>
				<p v-if="subtitle" class="drafts-list__subtitle">{{ subtitle }}</p>
			</div>
			<div class="drafts-list__actions">
				<span class="drafts-list__count">{{ parkedOrders.length }}</span>
				<v-btn
					v-if="showManageAll"
					size="small"
					variant="text"
					color="primary"
					data-test="drafts-manage-all"
					@click="$emit('manage-all')"
				>
					{{ __("Manage all") }}
				</v-btn>
			</div>
		</div>

		<div v-if="parkedOrders.length" class="drafts-list__cards">
			<div
				v-for="draft in parkedOrders"
				:key="draft.name"
				role="button"
				tabindex="0"
				class="drafts-list__card"
				:data-test="`draft-list-card-${draft.name}`"
				@click="$emit('resume', draft)"
				@keydown.enter="$emit('resume', draft)"
				@keydown.space.prevent="$emit('resume', draft)"
			>
				<div class="drafts-list__card-top">
					<strong>{{ draft.customer_name || __("Walk-in Customer") }}</strong>
					<span class="drafts-list__amount">
						{{ currencySymbol(draft.currency) }}{{ formatCurrency(draft.grand_total) }}
					</span>
				</div>
				<div class="drafts-list__meta">
					<span>{{ draft.name }}</span>
					<span>{{ draft.posting_date }}</span>
					<span>{{ draft.posting_time?.split(".")[0] || "" }}</span>
				</div>
				<div class="drafts-list__card-actions">
					<!-- Delete is hidden from the UI -- users are no longer allowed to
					     delete draft invoices from POS Awesome. -->
					<v-btn
						v-if="false"
						icon
						size="x-small"
						variant="text"
						color="error"
						:aria-label="__('Delete')"
						:title="__('Delete')"
						@click.stop="openDeleteConfirm(draft)"
					>
						<v-icon size="18">mdi-delete-outline</v-icon>
					</v-btn>
				</div>
			</div>
		</div>
		<div v-else class="drafts-list__empty">
			<strong>{{ emptyTitle || __("No records found") }}</strong>
			<span>{{ emptySubtitle || __("Try another source or refresh the list.") }}</span>
		</div>

		<ConfirmActionDialog
			v-model="deleteDialog"
			:title="__('Delete Draft')"
			:message="__('This will permanently delete draft {0}. This cannot be undone. Continue?', [deleteTarget?.name])"
			:confirm-label="__('Delete')"
			confirm-color="error"
			:loading="deleteLoading"
			@confirm="confirmDelete"
		/>
	</section>
</template>

<script setup>
import { ref } from "vue";
import ConfirmActionDialog from "../shared/ConfirmActionDialog.vue";
import { useToastStore } from "../../../stores/toastStore";

const toastStore = useToastStore();

defineProps({
	parkedOrders: {
		type: Array,
		default: () => [],
	},
	formatCurrency: {
		type: Function,
		required: true,
	},
	currencySymbol: {
		type: Function,
		required: true,
	},
	showManageAll: {
		type: Boolean,
		default: false,
	},
	title: {
		type: String,
		default: "",
	},
	eyebrow: {
		type: String,
		default: "",
	},
	subtitle: {
		type: String,
		default: "",
	},
	emptyTitle: {
		type: String,
		default: "",
	},
	emptySubtitle: {
		type: String,
		default: "",
	},
});

const emit = defineEmits(["resume", "manage-all", "deleted"]);

const __ = window.__;

const deleteDialog = ref(false);
const deleteLoading = ref(false);
const deleteTarget = ref(null);

function openDeleteConfirm(draft) {
	deleteTarget.value = draft;
	deleteDialog.value = true;
}

async function confirmDelete() {
	if (!deleteTarget.value) return;
	deleteLoading.value = true;
	try {
		await frappe.call({
			method: "posawesome.posawesome.api.invoices.delete_invoice",
			args: { invoice: deleteTarget.value.name },
		});
		toastStore.show({ title: __("Draft {0} deleted", [deleteTarget.value.name]), color: "success" });
		deleteDialog.value = false;
		emit("deleted", deleteTarget.value);
	} catch (e) {
		toastStore.show({ title: e?.message || __("Delete failed"), color: "error" });
	} finally {
		deleteLoading.value = false;
	}
}
</script>

<style scoped>
.drafts-list {
	display: flex;
	flex-direction: column;
	gap: 12px;
}

.drafts-list__header {
	display: flex;
	align-items: flex-start;
	justify-content: space-between;
	gap: 12px;
}

.drafts-list__eyebrow {
	margin: 0 0 2px;
	font-size: 0.72rem;
	font-weight: 700;
	letter-spacing: 0.08em;
	text-transform: uppercase;
	color: var(--pos-text-secondary);
}

.drafts-list__title {
	margin: 0;
	font-size: 1rem;
	font-weight: 700;
	color: var(--pos-text-primary);
}

.drafts-list__subtitle {
	margin: 4px 0 0;
	font-size: 0.82rem;
	color: var(--pos-text-secondary);
}

.drafts-list__actions {
	display: flex;
	align-items: center;
	gap: 8px;
}

.drafts-list__count {
	min-width: 28px;
	height: 28px;
	padding: 0 8px;
	border-radius: 999px;
	display: inline-flex;
	align-items: center;
	justify-content: center;
	background: rgba(var(--v-theme-primary), 0.14);
	color: rgb(var(--v-theme-primary));
	font-weight: 700;
}

.drafts-list__cards {
	display: flex;
	flex-direction: column;
	gap: 10px;
	max-height: calc(100vh - 180px);
	overflow: auto;
	padding-right: 2px;
}

.drafts-list__empty {
	display: flex;
	flex-direction: column;
	gap: 6px;
	padding: 18px 16px;
	border-radius: 18px;
	border: 1px dashed rgba(var(--v-theme-primary), 0.24);
	background: rgba(var(--v-theme-surface), 0.72);
	color: var(--pos-text-secondary);
}

.drafts-list__empty strong {
	color: var(--pos-text-primary);
}

.drafts-list__card {
	border: 1px solid rgba(var(--v-theme-primary), 0.14);
	border-radius: 16px;
	background: rgba(var(--v-theme-surface), 0.92);
	padding: 12px;
	text-align: left;
	display: flex;
	flex-direction: column;
	gap: 8px;
	cursor: pointer;
	color: var(--pos-text-primary);
	transition:
		transform 0.18s ease,
		box-shadow 0.18s ease,
		border-color 0.18s ease;
}

.drafts-list__card:hover,
.drafts-list__card:focus-visible {
	transform: translateY(-1px);
	box-shadow: 0 10px 18px rgba(15, 23, 42, 0.12);
	border-color: rgba(var(--v-theme-primary), 0.34);
}

.drafts-list__card-top {
	display: flex;
	align-items: flex-start;
	justify-content: space-between;
	gap: 8px;
}

.drafts-list__amount {
	font-weight: 700;
	white-space: nowrap;
}

.drafts-list__meta {
	display: flex;
	flex-wrap: wrap;
	gap: 6px 10px;
	font-size: 0.8rem;
	color: var(--pos-text-secondary);
}

.drafts-list__card-actions {
	display: flex;
	justify-content: flex-end;
	margin-top: -4px;
}
</style>
