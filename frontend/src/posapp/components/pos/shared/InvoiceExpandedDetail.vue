<template>
	<div class="invoice-expanded" @click.stop>
		<div v-if="loading" class="invoice-expanded__loading">
			<v-progress-circular indeterminate size="22" color="primary" />
			<span class="ml-2">{{ __("Loading details...") }}</span>
		</div>
		<div v-else-if="!detail" class="invoice-expanded__empty">
			{{ __("No details available.") }}
		</div>
		<div v-else>
			<div class="invoice-expanded__meta">
				<span v-for="bit in metaBits" :key="bit.label">
					<strong>{{ bit.label }}:</strong> {{ bit.value }}
				</span>
			</div>
			<v-table density="compact" class="invoice-expanded__table">
				<thead>
					<tr>
						<th
							v-for="column in columns"
							:key="column.key"
							:class="column.align === 'right' ? 'text-right' : undefined"
						>
							{{ column.label }}
						</th>
					</tr>
				</thead>
				<tbody>
					<tr v-for="(row, idx) in lines" :key="idx">
						<td
							v-for="column in columns"
							:key="column.key"
							:class="cellClass(column)"
						>
							{{ cellText(column, row) }}
						</td>
					</tr>
					<tr v-if="!lines.length">
						<td :colspan="columns.length" class="text-center text-medium-emphasis">
							{{ __("No items") }}
						</td>
					</tr>
				</tbody>
			</v-table>
			<div v-if="totalBits.length" class="invoice-expanded__totals">
				<span v-for="bit in totalBits" :key="bit.label">
					<strong>{{ bit.label }}:</strong> {{ bit.value }}
				</span>
			</div>
			<div v-if="imageAttachments.length" class="invoice-expanded__images">
				<a
					v-for="file in imageAttachments"
					:key="file.file_url"
					:href="file.file_url"
					target="_blank"
					rel="noopener noreferrer"
					@click.stop
				>
					<img :src="file.file_url" :alt="file.file_name || ''" />
				</a>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed } from "vue";

const __ = window.__;

const props = defineProps({
	detail: { type: Object, default: null },
	loading: { type: Boolean, default: false },
	currencySymbol: { type: String, default: "" },
	formatCurrency: { type: Function, default: (v) => Number(v || 0).toFixed(2) },
	variant: { type: String, default: "invoice" },
});

const formatNumber = (v) => {
	const n = Number(v || 0);
	return Number.isInteger(n) ? String(n) : n.toFixed(2);
};

const text = (row, ...keys) => {
	for (const key of keys) {
		const value = row?.[key];
		if (value !== null && value !== undefined && value !== "") return value;
	}
	return "";
};

const column = (key, label, options = {}) => ({ key, label: __(label), ...options });

// Current stock in the source/target warehouse. The detail API only sends
// the sides this user may see (both for System Manager / BSP Admin / BSP
// Viewer, otherwise just the user's own warehouse).
const stockColumns = (d) => [
	...(d.show_source_stock ? [column("source_stock_qty", "Source Stock", { align: "right", kind: "qty" })] : []),
	...(d.show_target_stock ? [column("target_stock_qty", "Target Stock", { align: "right", kind: "qty" })] : []),
];

const specs = {
	invoice: {
		lines: (d) => d.items || [],
		columns: () => [
			column("item_name", "Item"),
			column("item_code", "Code", { muted: true }),
			column("qty", "Qty", { align: "right", kind: "qty" }),
			column("uom", "UOM"),
			column("rate", "Rate", { align: "right", kind: "money" }),
			column("amount", "Amount", { align: "right", kind: "money" }),
		],
		totals: (d) => [
			["Grand Total", d.grand_total, "money"],
			["Discount", d.discount_amount, "money"],
			["Paid", d.paid_amount, "money"],
			["Outstanding", d.outstanding_amount, "money"],
		],
	},
	requisition: {
		lines: (d) => d.items || [],
		columns: (d) => [
			column("item_name", "Item"),
			column("item_code", "Code", { muted: true }),
			column("required_qty", "Qty", { align: "right", kind: "qty" }),
			...stockColumns(d),
			column("uom", "UOM"),
		],
		totals: (d) => [
			["Total Qty", d.total_required_qty, "qty"],
			["Weight", d.total_weight, "qty"],
		],
	},
	material_transfer: {
		lines: (d) => d.items || [],
		columns: (d) => [
			column("item_name", "Item"),
			column("item_code", "Code", { muted: true }),
			column("qty", "Qty", { align: "right", kind: "qty" }),
			column("received_qty", "Received", { align: "right", kind: "qty" }),
			...stockColumns(d),
			column("uom", "UOM"),
		],
		totals: (d) => [
			["Total Qty", d.total_qty, "qty"],
			["Received", d.total_received_qty, "qty"],
			["Weight", d.total_weight, "qty"],
		],
	},
	stock_entry: {
		lines: (d) => d.items || [],
		columns: () => [
			column("item_name", "Item"),
			column("item_code", "Code", { muted: true }),
			column("qty", "Qty", { align: "right", kind: "qty" }),
			column("uom", "UOM"),
			column("basic_rate", "Rate", { align: "right", kind: "money" }),
			column("amount", "Amount", { align: "right", kind: "money" }),
		],
		totals: (d) => [
			["Total Qty", d.total_qty, "qty"],
			["Value", d.total_value, "money"],
		],
	},
	bom: {
		lines: (d) => d.items || [],
		columns: () => [
			column("item_name", "Item"),
			column("item_code", "Code", { muted: true }),
			column("qty", "Qty", { align: "right", kind: "qty" }),
			column("uom", "UOM"),
			column("rate", "Rate", { align: "right", kind: "money" }),
			column("amount", "Amount", { align: "right", kind: "money" }),
		],
		totals: (d) => [
			["Total Cost", d.total_cost, "money"],
			["Weight", d.total_weight, "qty"],
		],
	},
	requirement: {
		lines: (d) => d.items || [],
		columns: () => [
			column("item_name", "Item"),
			column("item_code", "Code", { muted: true }),
			column("shortage_qty", "Shortage", { align: "right", kind: "qty" }),
			column("plan_qty", "Plan Qty", { align: "right", kind: "qty" }),
			column("uom", "UOM"),
		],
		totals: (d) => [
			["Shortage Qty", d.total_shortage_qty, "qty"],
			["Plan Qty", d.total_plan_qty, "qty"],
		],
	},
	production_plan: {
		lines: (d) => d.items || [],
		columns: () => [
			column("item_name", "Item"),
			column("item_code", "Code", { muted: true }),
			column("planned_qty", "Qty", { align: "right", kind: "qty" }),
			column("stock_uom", "UOM"),
			column("warehouse", "Warehouse"),
		],
		totals: (d) => [
			["Planned Qty", d.total_planned_qty, "qty"],
			["Weight", d.total_weight, "qty"],
		],
	},
	payment: {
		lines: (d) => d.items || [],
		columns: () => [
			column("reference_name", "Reference"),
			column("reference_doctype", "Type", { muted: true }),
			column("total_amount", "Total", { align: "right", kind: "money" }),
			column("outstanding_amount", "Outstanding", { align: "right", kind: "money" }),
			column("allocated_amount", "Allocated", { align: "right", kind: "money" }),
		],
		totals: (d) => [
			["Paid", d.paid_amount, "money"],
			["Allocated", d.total_allocated_amount, "money"],
			["Unallocated", d.unallocated_amount, "money"],
		],
	},
	expense: {
		lines: (d) => d.expenses || [],
		columns: () => [
			column("expense_date", "Date"),
			column("expense_type", "Type"),
			column("description", "Description"),
			column("amount", "Amount", { align: "right", kind: "money" }),
			column("sanctioned_amount", "Sanctioned", { align: "right", kind: "money" }),
		],
		totals: (d) => [
			["Claimed", d.total_claimed_amount, "money"],
			["Sanctioned", d.total_sanctioned_amount, "money"],
			["Grand Total", d.grand_total, "money"],
		],
	},
	production: {
		lines: (d) => d.present_employees || [],
		columns: () => [
			column("employee_name", "Employee"),
			column("employee", "Code", { muted: true }),
			column("point", "Point", { align: "right", kind: "qty" }),
			column("daily_salary", "Daily Salary", { align: "right", kind: "money" }),
		],
		totals: (d) => [
			["Work (KG)", d.total_work_kg, "qty"],
			["Total Wage", d.total_wage, "money"],
			["Points", d.total_points, "qty"],
		],
	},
	wastage: {
		lines: (d) => d.deductions || [],
		columns: () => [
			column("employee_name", "Employee"),
			column("employee", "Code", { muted: true }),
			column("amount", "Amount", { align: "right", kind: "money" }),
			column("payroll_date", "Payroll Date"),
		],
		totals: (d) => [
			["Excess (KG)", d.excess_wastage_kg, "qty"],
			["Penalty", d.penalty_amount, "money"],
		],
	},
	deposit: {
		lines: (d) => [
			{
				deposit_type: d.deposit_type,
				bank_name: d.bank_name,
				amount: d.amount,
				payment_entry: d.payment_entry,
			},
		],
		columns: () => [
			column("deposit_type", "Deposit Type"),
			column("bank_name", "Bank"),
			column("amount", "Amount", { align: "right", kind: "money" }),
			column("payment_entry", "Payment Entry", { muted: true }),
		],
		totals: (d) => [["Amount", d.amount, "money"]],
	},
	fund_transfer: {
		lines: (d) => [
			{
				paid_from: d.paid_from,
				paid_to: d.paid_to,
				mode_of_payment: d.mode_of_payment,
				amount: d.amount,
			},
		],
		columns: () => [
			column("paid_from", "Paid From"),
			column("paid_to", "Paid To"),
			column("mode_of_payment", "Mode"),
			column("amount", "Amount", { align: "right", kind: "money" }),
		],
		totals: (d) => [
			["Amount", d.amount, "money"],
			["Previous Balance", d.previous_balance, "money"],
			["Current Balance", d.current_balance, "money"],
		],
	},
};

const spec = computed(() => specs[props.variant] || specs.invoice);
const columns = computed(() => spec.value.columns(props.detail || {}));
const lines = computed(() => (props.detail ? spec.value.lines(props.detail) || [] : []));

const formatKind = (kind, value) => {
	if (kind === "money") return `${props.currencySymbol}${props.formatCurrency(value)}`;
	if (kind === "qty") return formatNumber(value);
	return value;
};

const metaBits = computed(() => {
	const detail = props.detail || {};
	const bits = [];
	const party = text(
		detail,
		"customer_name",
		"supplier_name",
		"party_name",
		"employee_name",
		"user_name",
		"requested_by",
		"received_from",
		"item_name",
	);
	if (party) bits.push({ label: __("Party"), value: party });
	if (detail.start_date && detail.end_date) {
		bits.push({ label: __("Date"), value: `${detail.start_date} – ${detail.end_date}` });
	} else {
		const date = text(detail, "posting_date", "transaction_date", "production_date", "date");
		if (date) bits.push({ label: __("Date"), value: date });
	}
	const created = text(detail, "owner_name", "created_by", "owner");
	if (created) bits.push({ label: __("Created By"), value: created });
	const remarks = text(detail, "remarks", "notes", "remark", "description");
	if (remarks) bits.push({ label: __("Remarks"), value: remarks });
	if (props.variant !== "invoice") {
		const from = text(detail, "from_warehouse", "source_warehouse", "paid_from");
		if (from) bits.push({ label: __("From"), value: from });
		const to = text(detail, "to_warehouse", "target_warehouse", "paid_to");
		if (to) bits.push({ label: __("To"), value: to });
		const warehouse = detail.warehouse_name || detail.warehouse || detail.for_warehouse;
		if (warehouse) bits.push({ label: __("Warehouse"), value: warehouse });
	}
	return bits;
});

const totalBits = computed(() => {
	if (!props.detail) return [];
	return spec.value
		.totals(props.detail)
		.filter(([, value]) => value !== null && value !== undefined && value !== "")
		.map(([label, value, kind]) => ({
			label: __(label),
			value: formatKind(kind, value),
		}));
});

const imageAttachments = computed(() =>
	Array.isArray(props.detail?.attachments) ? props.detail.attachments : [],
);

const cellClass = (col) => ({
	"text-right": col.align === "right",
	"text-medium-emphasis": col.muted,
});

const cellText = (col, row) => {
	const value = row?.[col.key];
	if (value === null || value === undefined || value === "") return "—";
	return formatKind(col.kind, value);
};
</script>

<style scoped>
.invoice-expanded {
	padding: 12px 16px;
	background: color-mix(in srgb, var(--pos-primary, #0f766e) 3%, #fff);
}

.invoice-expanded__loading,
.invoice-expanded__empty {
	display: flex;
	align-items: center;
	padding: 8px 0;
	color: var(--pos-text-secondary, #6b7280);
}

.invoice-expanded__meta {
	display: flex;
	flex-wrap: wrap;
	gap: 6px 18px;
	margin-bottom: 8px;
	font-size: 0.82rem;
	color: var(--pos-text-primary, #1f2937);
}

.invoice-expanded__table {
	border: 1px solid rgba(17, 24, 39, 0.1);
	border-radius: 8px;
	overflow: hidden;
}

.invoice-expanded__totals {
	display: flex;
	flex-wrap: wrap;
	gap: 6px 18px;
	margin-top: 8px;
	font-size: 0.85rem;
	justify-content: flex-end;
}

.invoice-expanded__images {
	display: flex;
	flex-wrap: wrap;
	gap: 8px;
	margin-top: 10px;
}

.invoice-expanded__images img {
	width: 72px;
	height: 72px;
	object-fit: cover;
	border-radius: 6px;
	border: 1px solid rgba(17, 24, 39, 0.12);
	display: block;
}
</style>
