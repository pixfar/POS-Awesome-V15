<template>
	<v-dialog :model-value="modelValue" max-width="720" persistent @update:model-value="$emit('update:modelValue', $event)">
		<v-card class="pos-themed-card">
			<v-card-title class="d-flex align-center gap-2">
				<v-icon color="primary">mdi-package-variant-closed-check</v-icon>
				<span>{{ __("Confirm Receipt") }}</span>
			</v-card-title>
			<v-card-text>
				<p class="text-caption text-medium-emphasis mb-3">
					{{
						__(
							'Confirm the quantity actually received. Adjust if some units were damaged or missing.'
						)
					}}
				</p>
				<v-table density="compact" class="pos-themed-table">
					<thead>
						<tr>
							<th>{{ __("Item Code") }}</th>
							<th>{{ __("Item Name") }}</th>
							<th class="text-right">{{ __("Sent Qty") }}</th>
							<th>{{ __("Received Qty") }}</th>
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
									v-model.number="receivedMap[item.name]"
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
				<v-btn color="primary" variant="flat" :loading="loading" @click="$emit('confirm', receivedMap)">
					{{ __("Confirm Receipt") }}
				</v-btn>
			</v-card-actions>
		</v-card>
	</v-dialog>
</template>

<script>
import { reactive, watch } from 'vue';

export default {
	props: {
		modelValue: Boolean,
		items: { type: Array, default: () => [] },
		loading: Boolean,
	},
	emits: ['update:modelValue', 'confirm'],
	setup(props) {
		const receivedMap = reactive({});

		watch(
			() => [props.modelValue, props.items],
			() => {
				if (!props.modelValue) return;
				Object.keys(receivedMap).forEach((key) => delete receivedMap[key]);
				(props.items || []).forEach((item) => {
					receivedMap[item.name] = Number(item.qty) || 0;
				});
			},
			{ deep: true, immediate: true },
		);

		const formatQty = (val) => Number(val || 0);

		return { receivedMap, formatQty };
	},
};
</script>
