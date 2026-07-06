<template>
	<div class="pa-0 h-100 invoice-shell pos-list-page">
		<v-card flat class="invoice-section-card pos-themed-card pos-list-card pos-detail-card">
			<div class="pos-list-header">
				<div class="pos-list-header__main">
					<p class="pos-list-header__eyebrow">{{ eyebrow }}</p>
					<h3 class="pos-list-header__title">{{ title }}</h3>
					<p v-if="subtitle" class="pos-list-header__subtitle">{{ subtitle }}</p>
				</div>
				<div class="pos-list-header__actions">
					<v-btn
						variant="text"
						class="text-none"
						prepend-icon="mdi-arrow-left"
						@click="$emit('back')"
					>
						{{ __("Back to list") }}
					</v-btn>
				</div>
			</div>

			<div v-if="loading" class="pos-list-empty">
				<v-progress-circular indeterminate color="primary" />
			</div>

			<div v-else-if="notFound" class="pos-list-empty">
				<v-icon size="48" color="error" class="pos-list-empty__icon">mdi-alert-circle-outline</v-icon>
				<h4 class="pos-list-empty__title">{{ __("Document not found") }}</h4>
			</div>

			<template v-else>
				<div class="pos-detail-status-row">
					<v-chip v-if="status" size="default" variant="tonal" :color="statusColor">
						{{ status }}
					</v-chip>
					<div v-if="actions.length" class="pos-detail-actions">
						<v-btn
							v-for="action in actions"
							:key="action.label"
							size="small"
							variant="tonal"
							:color="action.color || 'primary'"
							:loading="action.loading"
							class="text-none"
							@click="action.onClick"
						>
							{{ action.label }}
						</v-btn>
					</div>
				</div>

				<div class="pos-detail-meta-grid">
					<div v-for="field in metaFields" :key="field.label" class="pos-detail-meta-field">
						<span class="pos-detail-meta-field__label">{{ field.label }}</span>
						<span class="pos-detail-meta-field__value">{{ field.value || "—" }}</span>
					</div>
				</div>

				<div class="pos-list-table-wrap pos-detail-table-wrap">
					<v-table density="comfortable" class="pos-themed-table pos-detail-items-table">
						<thead>
							<tr>
								<th
									v-for="col in itemColumns"
									:key="col.key"
									:class="col.align === 'end' ? 'text-right' : 'text-left'"
								>
									{{ col.label }}
								</th>
							</tr>
						</thead>
						<tbody>
							<tr v-for="(row, idx) in items" :key="idx">
								<td
									v-for="col in itemColumns"
									:key="col.key"
									:class="col.align === 'end' ? 'text-right' : 'text-left'"
								>
									{{ row[col.key] }}
								</td>
							</tr>
							<tr v-if="!items.length">
								<td :colspan="itemColumns.length || 1" class="text-center text-medium-emphasis py-4">
									{{ __("No items") }}
								</td>
							</tr>
						</tbody>
					</v-table>
				</div>

				<div v-if="totals.length" class="pos-detail-totals">
					<div v-for="t in totals" :key="t.label" class="pos-detail-totals__row">
						<span class="pos-detail-totals__label">{{ t.label }}</span>
						<strong class="pos-detail-totals__value">{{ t.value }}</strong>
					</div>
				</div>
			</template>
		</v-card>
	</div>
</template>

<script>
export default {
	name: "DocumentDetailView",
	props: {
		eyebrow: { type: String, default: "" },
		title: { type: String, default: "" },
		subtitle: { type: String, default: "" },
		loading: { type: Boolean, default: false },
		notFound: { type: Boolean, default: false },
		status: { type: String, default: "" },
		statusColor: { type: String, default: "grey" },
		metaFields: { type: Array, default: () => [] },
		itemColumns: { type: Array, default: () => [] },
		items: { type: Array, default: () => [] },
		totals: { type: Array, default: () => [] },
		actions: { type: Array, default: () => [] },
	},
	emits: ["back"],
};
</script>

<style scoped>
@import "../invoice-shared-styles.css";
</style>
