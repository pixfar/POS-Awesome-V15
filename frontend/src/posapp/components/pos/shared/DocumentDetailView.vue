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
					<v-chip
						v-for="chip in extraStatusChips"
						:key="chip.label"
						size="default"
						variant="tonal"
						:color="chip.color || 'warning'"
						class="ms-1"
					>
						{{ chip.label }}
					</v-chip>
					<div v-if="actions.length || share" class="pos-detail-actions">
						<template v-for="action in actions" :key="action.label">
							<v-menu v-if="action.menuItems && action.menuItems.length" :close-on-content-click="true">
								<template #activator="{ props: menuProps }">
									<v-btn
										v-bind="menuProps"
										size="small"
										variant="tonal"
										:color="action.color || 'primary'"
										:loading="action.loading"
										append-icon="mdi-chevron-down"
										class="text-none"
									>
										{{ action.label }}
									</v-btn>
								</template>
								<v-list density="compact" min-width="220">
									<v-list-item
										v-for="menuItem in action.menuItems"
										:key="menuItem.label"
										@click="menuItem.onClick"
									>
										<v-list-item-title>{{ menuItem.label }}</v-list-item-title>
									</v-list-item>
								</v-list>
							</v-menu>
							<v-btn
								v-else
								size="small"
								variant="tonal"
								:color="action.color || 'primary'"
								:loading="action.loading"
								class="text-none"
								@click="action.onClick"
							>
								{{ action.label }}
							</v-btn>
						</template>
						<v-btn
							v-if="share"
							size="small"
							variant="tonal"
							color="success"
							prepend-icon="mdi-share-variant"
							class="text-none"
							@click="shareOpen = true"
						>
							{{ __("Share") }}
						</v-btn>
					</div>
				</div>

				<!-- Totals as figure tiles, each with its own accent and icon. -->
				<div v-if="totals.length" class="pos-detail-kpis">
					<div
						v-for="t in totalTiles"
						:key="t.label"
						class="pos-detail-kpi"
						:class="`pos-accent--${t.accent}`"
					>
						<span class="pos-detail-kpi__icon">
							<v-icon size="20">{{ t.icon }}</v-icon>
						</span>
						<div class="pos-detail-kpi__copy">
							<span class="pos-detail-kpi__label">{{ t.label }}</span>
							<strong class="pos-detail-kpi__value">{{ t.value }}</strong>
						</div>
					</div>
				</div>

				<section class="pos-detail-section">
					<header class="pos-detail-section__head">
						<span class="pos-detail-section__icon pos-accent--teal">
							<v-icon size="18">mdi-file-document-outline</v-icon>
						</span>
						<h4 class="pos-detail-section__title">{{ __("Document Information") }}</h4>
					</header>
					<div class="pos-detail-meta-grid">
						<div v-for="field in metaTiles" :key="field.label" class="pos-detail-meta-field">
							<span class="pos-detail-meta-field__icon" :class="`pos-accent--${field.accent}`">
								<v-icon size="16">{{ field.icon }}</v-icon>
							</span>
							<div class="pos-detail-meta-field__copy">
								<span class="pos-detail-meta-field__label">{{ field.label }}</span>
								<!-- Optional `href`: shown as a link opening in a new tab (e.g. an attachment). -->
								<a
									v-if="field.href"
									:href="field.href"
									target="_blank"
									rel="noopener noreferrer"
									class="pos-detail-meta-field__value pos-detail-meta-field__link"
								>
									{{ field.value || field.href }}
								</a>
								<v-tooltip v-else-if="isTruncated(field.value)" :text="String(field.value)" location="bottom">
									<template #activator="{ props: tooltipProps }">
										<span v-bind="tooltipProps" class="pos-detail-meta-field__value">
											{{ truncateValue(field.value) }}
										</span>
									</template>
								</v-tooltip>
								<span v-else class="pos-detail-meta-field__value">{{ field.value || "—" }}</span>
							</div>
						</div>
					</div>
				</section>

				<section class="pos-detail-section">
					<header class="pos-detail-section__head">
						<span class="pos-detail-section__icon pos-accent--violet">
							<v-icon size="18">mdi-format-list-bulleted</v-icon>
						</span>
						<h4 class="pos-detail-section__title">{{ __("Items") }}</h4>
						<span class="pos-detail-section__badge">{{ items.length }}</span>
					</header>
					<div class="pos-detail-table-wrap">
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
										:class="[
											col.align === 'end' ? 'text-right' : 'text-left',
											{ 'pos-detail-cell--code': isCodeColumn(col) },
										]"
									>
										<v-chip
											v-if="col.chipWhenPositive && Number(row[col.key] || 0) > 0"
											size="small"
											variant="tonal"
											:color="col.chipColor || 'warning'"
										>
											{{ cellText(row, col) }}
										</v-chip>
										<template v-else>
											{{ cellText(row, col) }}
										</template>
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
				</section>

				<!-- Optional extra section below the items (e.g. Production Plan's raw materials). -->
				<slot />
			</template>
		</v-card>

		<ShareDocumentDialog v-if="share" v-model="shareOpen" :target="share" :text="shareText" />
	</div>
</template>

<script>
import ShareDocumentDialog from "./ShareDocumentDialog.vue";
import { fieldIcon, totalIcon, isCodeColumn } from "./detailIcons";

// Item columns holding money or measures always show two decimals.
const DECIMAL_COLUMN = /weight|rate|amount|price|total|value|cost|discount|tax|balance/i;
// A numeric string with float noise, e.g. "7.199999999999999".
const NOISY_NUMBER = /^-?\d+\.\d{3,}$/;
import { buildShareText } from "../../../utils/documentShare";

export default {
	name: "DocumentDetailView",
	components: { ShareDocumentDialog },
	props: {
		eyebrow: { type: String, default: "" },
		title: { type: String, default: "" },
		subtitle: { type: String, default: "" },
		loading: { type: Boolean, default: false },
		notFound: { type: Boolean, default: false },
		status: { type: String, default: "" },
		statusColor: { type: String, default: "grey" },
		// Extra chips next to the main status (e.g. Returned qty on Material Transfer).
		extraStatusChips: { type: Array, default: () => [] },
		metaFields: { type: Array, default: () => [] },
		itemColumns: { type: Array, default: () => [] },
		items: { type: Array, default: () => [] },
		totals: { type: Array, default: () => [] },
		actions: { type: Array, default: () => [] },
		// { doctype, name, printFormat } -- shows a "Share" button that sends
		// this document's PDF (WhatsApp, email, ...). Omit to hide it.
		share: { type: Object, default: null },
	},
	emits: ["back"],
	data() {
		return { shareOpen: false };
	},
	computed: {
		metaTiles() {
			return this.metaFields.map((field) => ({ ...field, ...fieldIcon(field) }));
		},
		totalTiles() {
			return this.totals.map((total, index) => ({ ...total, ...totalIcon(total, index) }));
		},
		shareText() {
			return buildShareText({
				title: this.title,
				subtitle: this.subtitle,
				status: this.status,
				metaFields: this.metaFields,
				totals: this.totals,
			});
		},
	},
	methods: {
		isCodeColumn,
		// Raw numbers from the server (weights, quantities) arrive unformatted,
		// so 12 x 0.6 kg shows as 7.199999999999999. Money/measure columns get
		// two decimals ("7.20", "1,116.00"); other fractional numbers too;
		// whole quantities stay as they are. Pre-formatted text passes through.
		cellText(row, col) {
			let value = row[col.key];
			if (typeof value === "string" && NOISY_NUMBER.test(value)) {
				value = Number(value);
			}
			if (typeof value !== "number" || !Number.isFinite(value)) return value;
			if (DECIMAL_COLUMN.test(col.key) || !Number.isInteger(value)) {
				return value.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
			}
			return value;
		},
		// Truncation threshold for meta field values (e.g. Requisition's long
		// free-text Notes) -- anything longer than 50 characters gets cut
		// with "..." and the full text moved into a hover tooltip instead
		// of stretching the meta grid.
		isTruncated(value) {
			return typeof value === "string" && value.length > 50;
		},
		truncateValue(value) {
			return `${String(value).slice(0, 50)}...`;
		},
	},
};
</script>

<style scoped>
@import "../invoice-shared-styles.css";
</style>
