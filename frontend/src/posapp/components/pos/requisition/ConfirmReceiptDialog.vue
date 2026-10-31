<template>
	<v-dialog :model-value="modelValue" max-width="720" persistent @update:model-value="$emit('update:modelValue', $event)">
		<v-card class="pos-themed-card">
			<v-card-title class="d-flex align-center gap-2">
				<v-icon :color="confirmColor">{{ icon }}</v-icon>
				<span>{{ titleText }}</span>
			</v-card-title>
			<v-card-text>
				<p class="text-caption text-medium-emphasis mb-3">
					{{ descriptionText }}
				</p>
				<v-table density="compact" class="pos-themed-table">
					<thead>
						<tr>
							<th>{{ __("Item Code") }}</th>
							<th>{{ __("Item Name") }}</th>
							<th class="text-right">{{ outstandingLabelText }}</th>
							<th>{{ qtyLabelText }}</th>
						</tr>
					</thead>
					<tbody>
						<tr v-for="item in items" :key="item.name">
							<td class="text-caption">{{ item.item_code }}</td>
							<td class="text-caption">{{ item.item_name }}</td>
							<td class="text-right text-caption">
								{{ formatQty(item.qty) }} {{ item.uom }}
							</td>
							<td style="max-width: 120px;">
								<v-text-field
									v-model.number="qtyMap[item.name]"
									type="number"
									density="compact"
									variant="outlined"
									hide-details
									min="0"
									:max="item.qty"
									class="pos-themed-input"
								/>
							</td>
						</tr>
					</tbody>
				</v-table>
			</v-card-text>
			<v-card-actions>
				<v-spacer />
				<v-btn variant="text" @click="$emit('update:modelValue', false)">
					{{ __("Cancel") }}
				</v-btn>
				<v-btn
					:color="confirmColor"
					variant="flat"
					:loading="loading"
					@click="$emit('confirm', qtyMap)"
				>
					{{ confirmLabelText }}
				</v-btn>
			</v-card-actions>
		</v-card>
	</v-dialog>
</template>

<script>
import { reactive, computed, watch } from 'vue';

export default {
	props: {
		modelValue: Boolean,
		items: { type: Array, default: () => [] },
		loading: Boolean,
		mode: { type: String, default: 'receive' }, // receive | return
		title: { type: String, default: '' },
		description: { type: String, default: '' },
		confirmLabel: { type: String, default: '' },
		qtyLabel: { type: String, default: '' },
		outstandingLabel: { type: String, default: '' },
		confirmColor: { type: String, default: 'primary' },
		icon: { type: String, default: 'mdi-package-variant-closed-check' },
	},
	emits: ['update:modelValue', 'confirm'],
	setup(props) {
		const qtyMap = reactive({});

		const isReturn = computed(() => props.mode === 'return');

		const titleText = computed(
			() => props.title || (isReturn.value ? __('Return to Source') : __('Confirm Receipt')),
		);
		const descriptionText = computed(
			() =>
				props.description ||
				(isReturn.value
					? __('Enter how much to return to the source warehouse. Remaining qty stays in transit.')
					: __('Confirm the quantity actually received. Adjust if some units were damaged or missing.')),
		);
		const confirmLabelText = computed(
			() => props.confirmLabel || (isReturn.value ? __('Confirm Return') : __('Confirm Receipt')),
		);
		const qtyLabelText = computed(
			() => props.qtyLabel || (isReturn.value ? __('Return Qty') : __('Received Qty')),
		);
		const outstandingLabelText = computed(
			() => props.outstandingLabel || __('Outstanding Qty'),
		);

		watch(
			() => [props.modelValue, props.items],
			() => {
				if (!props.modelValue) return;
				Object.keys(qtyMap).forEach((key) => delete qtyMap[key]);
				(props.items || []).forEach((item) => {
					// Default receive to full outstanding; default return to 0 so
					// admins deliberately choose how many to send back.
					qtyMap[item.name] = isReturn.value ? 0 : Number(item.qty) || 0;
				});
			},
			{ deep: true, immediate: true },
		);

		const formatQty = (val) => Number(val || 0);

		return {
			qtyMap,
			titleText,
			descriptionText,
			confirmLabelText,
			qtyLabelText,
			outstandingLabelText,
			formatQty,
		};
	},
};
</script>
