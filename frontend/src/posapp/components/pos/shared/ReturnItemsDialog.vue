<template>
	<v-dialog v-model="dialog" max-width="920px" persistent>
		<v-card class="pos-themed-card">
			<v-card-title class="d-flex align-center gap-2">
				<v-icon color="blue">mdi-keyboard-return</v-icon>
				<span>{{ __("Return Items") }} — {{ invoice?.name }}</span>
			</v-card-title>

			<v-card-text>
				<div v-if="loading" class="d-flex justify-center pa-6">
					<v-progress-circular indeterminate color="primary" />
				</div>

				<div v-else-if="errorMessage" class="pa-2">
					<v-alert type="error" variant="tonal" density="compact">{{ errorMessage }}</v-alert>
				</div>

				<div v-else-if="!rows.length" class="pa-2">
					<v-alert type="info" variant="tonal" density="compact">
						{{ __("Nothing left to return on this invoice.") }}
					</v-alert>
				</div>

				<template v-else>
					<div class="d-flex justify-end mb-2">
						<v-btn size="small" variant="tonal" color="primary" @click="selectAll">
							{{ __("Select All") }}
						</v-btn>
						<v-btn size="small" variant="text" class="ml-1" @click="clearAll">
							{{ __("Clear") }}
						</v-btn>
					</div>

					<v-table density="comfortable" class="return-items-table">
						<thead>
							<tr>
								<th style="min-width: 160px">{{ __("Item") }}</th>
								<th class="text-end" style="width: 90px">{{ __("Price") }}</th>
								<th class="text-end" style="width: 100px">{{ __("Remaining Qty") }}</th>
								<th class="text-end" style="width: 110px">{{ __("Return Qty") }}</th>
								<th class="text-end" style="width: 120px">{{ __("Deduction %") }}</th>
								<th class="text-end" style="width: 110px">{{ __("Return Amount") }}</th>
							</tr>
						</thead>
						<tbody>
							<tr v-for="row in rows" :key="row.name">
								<td>
									<div class="font-weight-medium">{{ row.item_name || row.item_code }}</div>
									<div class="text-caption text-medium-emphasis">{{ row.item_code }}</div>
								</td>
								<td class="text-end">{{ formatMoney(row.rate) }}</td>
								<td class="text-end">{{ row.qty }} {{ row.uom }}</td>
								<td class="text-end">
									<v-text-field
										v-model.number="row.returnQty"
										density="compact"
										variant="outlined"
										hide-details
										type="number"
										min="0"
										:max="row.qty"
										style="width: 90px"
										class="pos-themed-input return-items-table__qty-field"
										@change="clampRow(row)"
									/>
								</td>
								<td class="text-end">
									<v-text-field
										v-model.number="row.deductionPercentage"
										density="compact"
										variant="outlined"
										hide-details
										type="number"
										min="0"
										max="100"
										suffix="%"
										style="width: 100px"
										class="pos-themed-input return-items-table__qty-field"
										@change="clampDeduction(row)"
									/>
								</td>
								<td class="text-end">{{ formatMoney(returnAmount(row)) }}</td>
							</tr>
						</tbody>
					</v-table>
				</template>
			</v-card-text>

			<v-card-actions>
				<v-spacer />
				<v-btn variant="text" :disabled="submitting" @click="close">{{ __("Cancel") }}</v-btn>
				<v-btn
					color="blue"
					variant="flat"
					:loading="submitting"
					:disabled="loading || !hasSelection"
					@click="submit"
				>
					{{ __("Create Return") }}
				</v-btn>
			</v-card-actions>
		</v-card>
	</v-dialog>
</template>

<script setup>
import { ref, computed, watch } from "vue";

const __ = window.__ || ((text) => text);
const frappe = window.frappe;

const props = defineProps({
	modelValue: Boolean,
	invoice: {
		type: Object,
		default: null,
	},
	posProfile: {
		type: String,
		default: null,
	},
	// Explicit, not inferred from invoice.doctype: not every list page's row
	// objects carry a doctype field (Purchase Invoice rows don't), so callers
	// must state which doctype this dialog is operating on.
	doctype: {
		type: String,
		default: "Sales Invoice",
	},
	returnMethod: {
		type: String,
		required: true,
	},
});

const emit = defineEmits(["update:modelValue", "returned", "error"]);

const dialog = computed({
	get: () => props.modelValue,
	set: (val) => emit("update:modelValue", val),
});

const loading = ref(false);
const submitting = ref(false);
const errorMessage = ref("");
const rows = ref([]);

const hasSelection = computed(() => rows.value.some((row) => (parseFloat(row.returnQty) || 0) > 0));

function clampRow(row) {
	let qty = parseFloat(row.returnQty);
	if (!Number.isFinite(qty) || qty < 0) qty = 0;
	if (qty > row.qty) qty = row.qty;
	row.returnQty = qty;
}

function clampDeduction(row) {
	let pct = parseFloat(row.deductionPercentage);
	if (!Number.isFinite(pct) || pct < 0) pct = 0;
	if (pct > 100) pct = 100;
	row.deductionPercentage = pct;
}

// Preview only -- the actual return rate is computed server-side off the
// same base (_apply_return_deduction there mirrors this), so this shows the
// cashier what they're about to create before submitting.
function returnAmount(row) {
	const baseRate = parseFloat(row.rate) || 0;
	const pct = parseFloat(row.deductionPercentage) || 0;
	const rate = baseRate - (baseRate * pct) / 100;
	const qty = parseFloat(row.returnQty) || 0;
	return qty * rate;
}

function formatMoney(value) {
	const amount = Number(value) || 0;
	try {
		return format_currency(amount, props.invoice?.currency);
	} catch (e) {
		return amount.toFixed(2);
	}
}

function selectAll() {
	rows.value.forEach((row) => {
		row.returnQty = row.qty;
	});
}

function clearAll() {
	rows.value.forEach((row) => {
		row.returnQty = 0;
	});
}

async function loadItems() {
	if (!props.invoice?.name) return;
	loading.value = true;
	errorMessage.value = "";
	rows.value = [];
	try {
		const { message } = await frappe.call({
			method: "posawesome.posawesome.api.invoice_processing.returns.get_invoice_for_return",
			args: {
				invoice_name: props.invoice.name,
				pos_profile: props.posProfile,
				doctype: props.doctype,
			},
		});
		rows.value = (message?.items || []).map((item) => ({
			...item,
			returnQty: 0,
			deductionPercentage: 0,
		}));
	} catch (e) {
		errorMessage.value = e?.message || __("Unable to load invoice items.");
	} finally {
		loading.value = false;
	}
}

async function submit() {
	const items = rows.value
		.filter((row) => (parseFloat(row.returnQty) || 0) > 0)
		.map((row) => ({
			row_name: row.name,
			qty: row.returnQty,
			deduction_percentage: parseFloat(row.deductionPercentage) || 0,
		}));

	if (!items.length) return;

	submitting.value = true;
	try {
		const { message } = await frappe.call({
			method: props.returnMethod,
			args: {
				invoice: props.invoice.name,
				doctype: props.doctype,
				items,
			},
		});
		emit("returned", message);
		dialog.value = false;
	} catch (e) {
		emit("error", e?.message || __("Unable to create return."));
	} finally {
		submitting.value = false;
	}
}

function close() {
	dialog.value = false;
}

watch(
	() => props.modelValue,
	(val) => {
		if (val) {
			loadItems();
		}
	},
);
</script>

<style scoped>
/* Explicit widths on each <th> in the template (not CSS class selectors) are
   what actually pin the columns -- an earlier attempt used
   table-layout:fixed with :deep(th:nth-child(n)) class rules instead, which
   silently failed to reach Vuetify's actual header cells (nth-child count
   didn't line up with its real markup) and left every column but Item
   collapsed to ~32px. table-layout stays auto here since the inline widths
   on <th> already give auto layout everything it needs, and auto tolerates
   a mismatch between declared width and actual content better than fixed
   does. */
.return-items-table {
	width: 100%;
}

.return-items-table__qty-field {
	margin-left: auto;
}

.return-items-table__qty-cell {
	display: flex;
	justify-content: flex-end;
}
</style>
