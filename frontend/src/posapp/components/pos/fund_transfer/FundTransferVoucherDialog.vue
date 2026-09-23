<template>
	<v-dialog
		:model-value="modelValue"
		max-width="720"
		scrollable
		@update:model-value="$emit('update:modelValue', $event)"
	>
		<v-card class="pos-themed-card ft-voucher">
			<v-card-title class="d-flex align-center ft-voucher__title">
				<v-icon color="success" size="28" class="mr-2">mdi-check-circle</v-icon>
				<div>
					<div class="ft-voucher__heading">{{ __("Fund Transfer Submitted") }}</div>
					<div class="ft-voucher__sub">{{ __("Fund Receive Voucher") }}</div>
				</div>
			</v-card-title>

			<v-card-text>
				<div v-if="loading" class="d-flex justify-center py-8">
					<v-progress-circular indeterminate color="primary" />
				</div>

				<template v-else>
					<!-- Same layout as the "BSP Fundtransfer" print format. -->
					<table class="ft-voucher__table">
						<tbody>
							<tr>
								<td><b>{{ __("Voucher No.") }}</b> : {{ detail.name }}</td>
								<td>
									<b>{{ __("Date") }}</b> : {{ longDate(detail.posting_date) }}
									<span class="ml-4"><b>{{ __("Time") }}</b> : {{ timeOf(detail.creation) }}</span>
								</td>
							</tr>
							<tr>
								<td><b>{{ __("Received Warehouse") }}</b> : {{ detail.paid_to || "—" }}</td>
								<td><b>{{ __("Received From") }}</b> : {{ detail.received_from || "—" }}</td>
							</tr>
							<tr>
								<td><b>{{ __("Payment Method") }}</b> : {{ detail.mode_of_payment || "—" }}</td>
								<td><b>{{ __("Reference No.") }}</b> : {{ detail.reference_no || "—" }}</td>
							</tr>
							<tr>
								<td colspan="2" class="ft-voucher__description">
									<b>{{ __("Description") }}</b> : {{ detail.description || "—" }}
								</td>
							</tr>
							<tr>
								<td><b>{{ __("Amount") }}</b> : {{ money(detail.amount) }}</td>
								<td><b>{{ __("Amount in Word") }}</b> : {{ detail.amount_in_words || "—" }}</td>
							</tr>
						</tbody>
					</table>

					<table class="ft-voucher__table ft-voucher__balances mt-4">
						<thead>
							<tr>
								<th>{{ __("Previous Balance") }}</th>
								<th>{{ __("Received Amount") }}</th>
								<th>{{ __("Current Balance") }}</th>
							</tr>
						</thead>
						<tbody>
							<tr>
								<td>{{ money(detail.previous_balance) }}</td>
								<td>{{ money(detail.amount) }}</td>
								<td>{{ money(detail.current_balance) }}</td>
							</tr>
						</tbody>
					</table>
				</template>
			</v-card-text>

			<v-card-actions class="px-4 pb-4">
				<v-btn variant="text" color="primary" :disabled="loading" @click="$emit('view', detail.name)">
					{{ __("View Details") }}
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
					{{ __("New Transfer") }}
				</v-btn>
			</v-card-actions>
		</v-card>
	</v-dialog>
</template>

<script>
import format from "../../../format";

// Shown right after a Fund Transfer is submitted: the same "Fund Receive
// Voucher" the BSP Fundtransfer print shows. `detail` comes from
// fund_transfer.get_fund_transfer_detail.
export default {
	name: "FundTransferVoucherDialog",
	mixins: [format],
	props: {
		modelValue: { type: Boolean, default: false },
		loading: { type: Boolean, default: false },
		detail: { type: Object, default: () => ({}) },
	},
	emits: ["update:modelValue", "print", "view"],
	methods: {
		money(value) {
			if (value === null || value === undefined) return "—";
			return `${this.currencySymbol(this.detail.currency)}${this.formatCurrency(value)}`;
		},
		longDate(value) {
			if (!value) return "—";
			const [y, m, d] = String(value).split("-").map(Number);
			const date = new Date(y, m - 1, d);
			const month = date.toLocaleString("en-US", { month: "long" });
			return `${String(d).padStart(2, "0")}-${month}-${y}`;
		},
		timeOf(value) {
			if (!value) return "—";
			const timePart = String(value).split(" ")[1] || "";
			const [h, min] = timePart.split(":").map(Number);
			if (Number.isNaN(h)) return "—";
			const suffix = h >= 12 ? "PM" : "AM";
			const hour12 = h % 12 || 12;
			return `${String(hour12).padStart(2, "0")}:${String(min).padStart(2, "0")} ${suffix}`;
		},
	},
};
</script>

<style scoped>
.ft-voucher__title {
	gap: 4px;
	padding-top: 16px;
}
.ft-voucher__heading {
	font-size: 1.1rem;
	font-weight: 700;
}
.ft-voucher__sub {
	font-size: 0.85rem;
	color: var(--pos-text-secondary);
}
.ft-voucher__table {
	width: 100%;
	border-collapse: collapse;
	font-size: 0.9rem;
}
.ft-voucher__table td,
.ft-voucher__table th {
	border: 1px solid rgba(128, 128, 128, 0.35);
	padding: 6px 10px;
	vertical-align: top;
	width: 50%;
}
.ft-voucher__description {
	white-space: pre-line;
}
.ft-voucher__balances {
	width: 70%;
}
.ft-voucher__balances th,
.ft-voucher__balances td {
	width: auto;
	text-align: center;
}
.ft-voucher__balances th {
	font-weight: 500;
	color: var(--pos-text-secondary);
}
@media (max-width: 600px) {
	.ft-voucher__balances {
		width: 100%;
	}
}
</style>
