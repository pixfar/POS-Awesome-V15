<template>
	<v-dialog v-model="dialog" max-width="720px" persistent>
		<v-card class="pos-themed-card">
			<v-card-title class="d-flex align-center gap-2">
				<v-icon :color="color">{{ icon }}</v-icon>
				<span>{{ title }} — {{ invoice?.name }}</span>
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
						{{ emptyMessage }}
					</v-alert>
				</div>

				<template v-else>
					<div class="d-flex justify-end mb-2">
						<v-btn size="small" variant="tonal" :color="color" @click="selectAll">
							{{ __("Select All") }}
						</v-btn>
						<v-btn size="small" variant="text" class="ml-1" @click="clearAll">
							{{ __("Clear") }}
						</v-btn>
					</div>

					<v-table density="comfortable" class="delivery-receipt-table">
						<thead>
							<tr>
								<th>{{ __("Item") }}</th>
								<th class="text-end">{{ __("Remaining Qty") }}</th>
								<th class="text-end">{{ qtyLabel }}</th>
							</tr>
						</thead>
						<tbody>
							<tr v-for="row in rows" :key="row.name">
								<td>
									<div class="font-weight-medium">{{ row.item_name || row.item_code }}</div>
									<div class="text-caption text-medium-emphasis">{{ row.item_code }}</div>
								</td>
								<td class="text-end">{{ row.qty }} {{ row.uom }}</td>
								<td class="text-end delivery-receipt-table__qty-cell">
									<v-text-field
										v-model.number="row.selectedQty"
										density="compact"
										variant="outlined"
										hide-details
										type="number"
										min="0"
										:max="row.qty"
										class="pos-themed-input delivery-receipt-table__qty-field"
										@change="clampRow(row)"
									/>
								</td>
							</tr>
						</tbody>
					</v-table>
				</template>
			</v-card-text>

			<v-card-actions>
				<v-spacer />
				<v-btn variant="text" :disabled="submitting" @click="close">{{ __("Cancel") }}</v-btn>
				<v-btn
					:color="color"
					variant="flat"
					:loading="submitting"
					:disabled="loading || !hasSelection"
					@click="submit"
				>
					{{ submitLabel }}
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
	doctype: {
		type: String,
		required: true,
	},
	// Whitelisted method path returning { name, items: [{name, item_code, item_name, uom, qty}] }
	// where qty is the remaining (undelivered/unreceived) quantity for that row.
	loadMethod: {
		type: String,
		required: true,
	},
	// Whitelisted method path accepting { invoice, items: [{row_name, qty}] } and
	// returning { name } of the created (and submitted) Delivery Note / Purchase Receipt.
	submitMethod: {
		type: String,
		required: true,
	},
	title: {
		type: String,
		required: true,
	},
	submitLabel: {
		type: String,
		required: true,
	},
	emptyMessage: {
		type: String,
		required: true,
	},
	icon: {
		type: String,
		default: "mdi-truck-delivery-outline",
	},
	color: {
		type: String,
		default: "primary",
	},
});

const emit = defineEmits(["update:modelValue", "created", "error"]);

const dialog = computed({
	get: () => props.modelValue,
	set: (val) => emit("update:modelValue", val),
});

const loading = ref(false);
const submitting = ref(false);
const errorMessage = ref("");
const rows = ref([]);

const hasSelection = computed(() => rows.value.some((row) => (parseFloat(row.selectedQty) || 0) > 0));

function clampRow(row) {
	let qty = parseFloat(row.selectedQty);
	if (!Number.isFinite(qty) || qty < 0) qty = 0;
	if (qty > row.qty) qty = row.qty;
	row.selectedQty = qty;
}

function selectAll() {
	rows.value.forEach((row) => {
		row.selectedQty = row.qty;
	});
}

function clearAll() {
	rows.value.forEach((row) => {
		row.selectedQty = 0;
	});
}

async function loadItems() {
	if (!props.invoice?.name) return;
	loading.value = true;
	errorMessage.value = "";
	rows.value = [];
	try {
		const { message } = await frappe.call({
			method: props.loadMethod,
			args: { invoice_name: props.invoice.name },
		});
		// Every row defaults to its full remaining quantity — the common case is
		// fulfilling everything outstanding, unlike the Return dialog's opt-in default.
		rows.value = (message?.items || []).map((item) => ({
			...item,
			selectedQty: item.qty,
		}));
	} catch (e) {
		errorMessage.value = e?.message || __("Unable to load invoice items.");
	} finally {
		loading.value = false;
	}
}

async function submit() {
	const items = rows.value
		.filter((row) => (parseFloat(row.selectedQty) || 0) > 0)
		.map((row) => ({ row_name: row.name, qty: row.selectedQty }));

	if (!items.length) return;

	submitting.value = true;
	try {
		const { message } = await frappe.call({
			method: props.submitMethod,
			args: {
				invoice: props.invoice.name,
				doctype: props.doctype,
				items,
			},
		});
		emit("created", message);
		dialog.value = false;
	} catch (e) {
		emit("error", e?.message || __("Unable to complete the action."));
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
.delivery-receipt-table__qty-field {
	max-width: 120px;
	margin-left: auto;
}

.delivery-receipt-table__qty-cell {
	display: flex;
	justify-content: flex-end;
}
</style>
