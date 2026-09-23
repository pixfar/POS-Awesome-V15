<template>
	<v-dialog
		:model-value="modelValue"
		max-width="680"
		scrollable
		@update:model-value="$emit('update:modelValue', $event)"
	>
		<v-card class="pos-themed-card purchase-complete">
			<v-card-title class="d-flex align-center purchase-complete__title">
				<v-icon color="success" size="28" class="mr-2">mdi-check-circle</v-icon>
				<div>
					<div class="purchase-complete__heading">{{ __("Purchase Completed") }}</div>
					<div class="purchase-complete__sub">{{ detail.name }}</div>
				</div>
			</v-card-title>

			<v-card-text>
				<div v-if="loading" class="d-flex justify-center py-8">
					<v-progress-circular indeterminate color="primary" />
				</div>

				<template v-else>
					<div class="purchase-complete__meta">
						<div v-for="field in metaFields" :key="field.label" class="purchase-complete__meta-item">
							<span class="purchase-complete__label">{{ field.label }}</span>
							<span class="purchase-complete__value">{{ field.value }}</span>
						</div>
					</div>

					<v-table density="compact" class="purchase-complete__items mt-3">
						<thead>
							<tr>
								<th>{{ __("Item") }}</th>
								<th class="text-end">{{ __("Qty") }}</th>
								<th class="text-end">{{ __("Rate") }}</th>
								<th class="text-end">{{ __("Amount") }}</th>
							</tr>
						</thead>
						<tbody>
							<tr v-for="(row, idx) in detail.items || []" :key="idx">
								<td>
									<div>{{ row.item_name || row.item_code }}</div>
									<div class="purchase-complete__code">{{ row.item_code }}</div>
								</td>
								<td class="text-end">{{ formatFloat(row.qty) }} {{ row.uom }}</td>
								<td class="text-end">{{ money(row.rate) }}</td>
								<td class="text-end">{{ money(row.amount) }}</td>
							</tr>
						</tbody>
					</v-table>

					<div class="purchase-complete__totals mt-3">
						<div v-if="detail.discount_amount" class="purchase-complete__total-row">
							<span>{{ __("Discount") }}</span>
							<span>{{ money(detail.discount_amount) }}</span>
						</div>
						<div class="purchase-complete__total-row purchase-complete__total-row--strong">
							<span>{{ __("Grand Total") }}</span>
							<span>{{ money(detail.grand_total) }}</span>
						</div>
						<div class="purchase-complete__total-row">
							<span>{{ __("Paid") }}</span>
							<span>{{ money(paidAmount) }}</span>
						</div>
						<div class="purchase-complete__total-row">
							<span>{{ __("Due on this Invoice") }}</span>
							<span>{{ money(detail.outstanding_amount) }}</span>
						</div>
					</div>

					<div
						class="purchase-complete__outstanding mt-3"
						:class="supplierOutstanding > 0 ? 'is-due' : 'is-clear'"
					>
						<div>
							<div class="purchase-complete__label">{{ __("Supplier Current Outstanding") }}</div>
							<div class="purchase-complete__sub">{{ detail.supplier_name || detail.supplier }}</div>
						</div>
						<div class="purchase-complete__outstanding-amount">
							{{ supplierOutstanding === null ? "—" : money(supplierOutstanding) }}
						</div>
					</div>
					<div v-if="previousOutstanding !== null" class="purchase-complete__hint">
						{{ __("Before this purchase: {0}", [money(previousOutstanding)]) }}
					</div>
				</template>
			</v-card-text>

			<v-card-actions class="px-4 pb-4">
				<v-btn variant="text" color="primary" :disabled="loading" @click="$emit('view', detail.name)">
					{{ __("View Invoice") }}
				</v-btn>
				<v-spacer />
				<v-btn
					variant="tonal"
					color="primary"
					prepend-icon="mdi-printer"
					:disabled="loading"
					@click="$emit('print', detail.name)"
				>
					{{ __("Print") }}
				</v-btn>
				<v-btn variant="flat" color="primary" @click="$emit('update:modelValue', false)">
					{{ __("New Purchase") }}
				</v-btn>
			</v-card-actions>
		</v-card>
	</v-dialog>
</template>

<script>
import format from "../../../format";

// Shown once a Purchase Invoice is submitted from the new-purchase screen:
// what was bought, what was paid, and where the supplier's balance stands
// now. The parent loads `detail` (get_purchase_invoice_detail) and
// `supplierOutstanding` (get_supplier_info) and passes them in.
export default {
	name: "PurchaseCompleteDialog",
	mixins: [format],
	props: {
		modelValue: { type: Boolean, default: false },
		loading: { type: Boolean, default: false },
		detail: { type: Object, default: () => ({}) },
		supplierOutstanding: { type: Number, default: null },
		previousOutstanding: { type: Number, default: null },
	},
	emits: ["update:modelValue", "print", "view"],
	computed: {
		// Paid through the purchase's own Payment Entry lands as a reduced
		// outstanding_amount, not in paid_amount -- so derive it.
		paidAmount() {
			return Math.max(
				0,
				Number(this.detail.grand_total || 0) - Number(this.detail.outstanding_amount || 0),
			);
		},
		metaFields() {
			const d = this.detail;
			const fields = [
				{ label: this.__("Supplier"), value: d.supplier_name || d.supplier || "—" },
				{ label: this.__("Date"), value: this.formatDate(d.posting_date) },
				{ label: this.__("Warehouse"), value: d.warehouse || "—" },
				{ label: this.__("Total Qty"), value: this.formatFloat(d.total_qty) },
			];
			if (d.custom_do_number) {
				fields.push({ label: this.__("DO Number"), value: d.custom_do_number });
			}
			return fields;
		},
	},
	methods: {
		money(value) {
			return `${this.currencySymbol(this.detail.currency)}${this.formatCurrency(value || 0)}`;
		},
		formatDate(value) {
			if (!value) return "—";
			const parts = String(value).split("-");
			return parts.length === 3 ? `${parts[2]}-${parts[1]}-${parts[0]}` : value;
		},
	},
};
</script>

<style scoped>
.purchase-complete__title {
	gap: 4px;
	padding-top: 16px;
}
.purchase-complete__heading {
	font-size: 1.1rem;
	font-weight: 700;
}
.purchase-complete__sub {
	font-size: 0.85rem;
	color: var(--pos-text-secondary);
}
.purchase-complete__meta {
	display: grid;
	grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
	gap: 10px;
}
.purchase-complete__meta-item {
	display: flex;
	flex-direction: column;
}
.purchase-complete__label {
	font-size: 0.75rem;
	text-transform: uppercase;
	letter-spacing: 0.03em;
	color: var(--pos-text-secondary);
}
.purchase-complete__value {
	font-weight: 600;
}
.purchase-complete__code {
	font-size: 0.75rem;
	color: var(--pos-text-secondary);
}
.purchase-complete__totals {
	margin-left: auto;
	max-width: 320px;
}
.purchase-complete__total-row {
	display: flex;
	justify-content: space-between;
	padding: 2px 0;
}
.purchase-complete__total-row--strong {
	font-weight: 700;
	border-top: 1px solid rgba(128, 128, 128, 0.3);
	padding-top: 6px;
}
.purchase-complete__outstanding {
	display: flex;
	justify-content: space-between;
	align-items: center;
	padding: 12px 14px;
	border-radius: 10px;
}
.purchase-complete__outstanding.is-due {
	background: rgba(var(--v-theme-error), 0.1);
}
.purchase-complete__outstanding.is-clear {
	background: rgba(var(--v-theme-success), 0.1);
}
.purchase-complete__outstanding-amount {
	font-size: 1.35rem;
	font-weight: 700;
}
.is-due .purchase-complete__outstanding-amount {
	color: rgb(var(--v-theme-error));
}
.is-clear .purchase-complete__outstanding-amount {
	color: rgb(var(--v-theme-success));
}
.purchase-complete__hint {
	font-size: 0.8rem;
	color: var(--pos-text-secondary);
	margin-top: 4px;
	text-align: right;
}
</style>
