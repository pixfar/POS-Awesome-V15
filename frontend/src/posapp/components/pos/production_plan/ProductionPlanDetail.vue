<template>
	<div class="h-100">
		<DocumentDetailView
			:eyebrow="__('Manufacturing')"
			:title="name"
			:subtitle="__('Production Plan')"
			:loading="loading"
			:not-found="notFound"
			:status="detail.workflow_state"
			:status-color="statusColor(detail.workflow_state)"
			:meta-fields="metaFields"
			:item-columns="itemColumns"
			:items="itemRows"
			:totals="totals"
			:actions="actions"
			@back="goBack"
		>
			<div v-if="rawMaterials.items.length" class="pos-list-table-wrap pos-detail-table-wrap mt-4">
				<div class="d-flex align-center px-3 pt-2">
					<h4 class="text-subtitle-1 font-weight-medium">{{ __("Raw Materials") }}</h4>
					<v-chip v-if="rawMaterials.edited" size="x-small" color="warning" variant="tonal" class="ml-2">
						{{ __("Edited from BOM") }}
					</v-chip>
				</div>
				<v-table density="comfortable" class="pos-themed-table pos-detail-items-table">
					<thead>
						<tr>
							<th class="text-left">{{ __("Item Code") }}</th>
							<th class="text-left">{{ __("Raw Material") }}</th>
							<th class="text-right">{{ __("BOM Qty") }}</th>
							<th class="text-right">{{ __("Qty") }}</th>
							<th class="text-left">{{ __("UOM") }}</th>
						</tr>
					</thead>
					<tbody>
						<tr v-for="rm in rawMaterials.items" :key="rm.item_code">
							<td>{{ rm.item_code }}</td>
							<td>
								{{ rm.item_name }}
								<v-chip v-if="rm.bom_qty === null" size="x-small" color="success" variant="tonal" class="ml-1">
									{{ __("Added") }}
								</v-chip>
							</td>
							<td class="text-right">{{ rm.bom_qty === null ? "—" : formatFloat(rm.bom_qty) }}</td>
							<td class="text-right" :class="{ 'text-warning font-weight-bold': rm.bom_qty !== rm.qty }">
								{{ formatFloat(rm.qty) }}
							</td>
							<td>{{ rm.uom }}</td>
						</tr>
						<tr v-for="rm in rawMaterials.removed" :key="`removed-${rm.item_code}`" class="text-medium-emphasis">
							<td><s>{{ rm.item_code }}</s></td>
							<td>
								<s>{{ rm.item_name }}</s>
								<v-chip size="x-small" color="error" variant="tonal" class="ml-1">{{ __("Removed") }}</v-chip>
							</td>
							<td class="text-right">{{ formatFloat(rm.bom_qty) }}</td>
							<td class="text-right">0</td>
							<td></td>
						</tr>
					</tbody>
				</v-table>
			</div>
		</DocumentDetailView>

		<ConfirmActionDialog
			v-model="confirmDialogOpen"
			:title="confirmDialogTitle"
			:message="confirmDialogMessage"
			:confirm-label="__(pendingAction || 'Confirm')"
			:confirm-color="actionColor(pendingAction)"
			:loading="actionLoading"
			@confirm="performAdvanceStatus"
		/>
	</div>
</template>

<script>
import { ref, computed, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useToastStore } from '../../../stores/toastStore';
import { openDocumentPrintView } from '../../../utils/openDocumentPrintView';
import DocumentDetailView from '../shared/DocumentDetailView.vue';
import ConfirmActionDialog from '../shared/ConfirmActionDialog.vue';
import { useFormat } from '../../../format';

const ACTION_CONFIRM_MESSAGES = {
	'Start Production': __('Start production for this plan? This will submit it and lock in the planned quantities.'),
	'Mark Production Complete': __('Mark this plan as Production Complete? This finalizes it.'),
	Cancel: __(
		'Cancel this production plan? This will also cancel any linked Work Orders, Stock Entries and Job Cards, and reverse stock already consumed or produced.',
	),
	Delete: __(
		'Permanently delete this production plan and its linked Work Order? This cannot be undone.',
	),
};

export default {
	name: 'ProductionPlanDetail',
	components: { DocumentDetailView, ConfirmActionDialog },
	setup() {
		const route = useRoute();
		const router = useRouter();
		const toastStore = useToastStore();
		const name = route.params.name;

		const loading = ref(true);
		const notFound = ref(false);
		const detail = ref({});
		const { formatFloat } = useFormat();
		const rawMaterials = computed(() => detail.value.raw_materials || { items: [], removed: [], edited: false });
		const actionLoading = ref(false);

		const formatDisplayDate = (value) => {
			if (!value) return '—';
			const parts = String(value).split('-');
			return parts.length === 3 ? `${parts[2]}-${parts[1]}-${parts[0]}` : value;
		};

		const formatDisplayDateTime = (value) => {
			if (!value) return '—';
			const [datePart, timePart] = String(value).split(' ');
			const date = formatDisplayDate(datePart);
			return timePart ? `${date} ${timePart.slice(0, 5)}` : date;
		};

		const metaFields = computed(() => {
			const fields = [
				{ label: __('Posting Date'), value: formatDisplayDate(detail.value.posting_date) },
				{ label: __('Company'), value: detail.value.company },
				{ label: __('Source Warehouse'), value: detail.value.for_warehouse },
				{ label: __('Status'), value: detail.value.status },
				{ label: __('Created By'), value: detail.value.created_by },
				{ label: __('Created On'), value: formatDisplayDateTime(detail.value.creation) },
			];
			if (detail.value.customer) {
				fields.push({ label: __('Customer'), value: detail.value.customer });
			}
			if (detail.value.get_items_from) {
				fields.push({ label: __('Items Sourced From'), value: detail.value.get_items_from });
			}
			if (detail.value.amended_from) {
				fields.push({ label: __('Amended From'), value: detail.value.amended_from });
			}
			return fields;
		});

		const itemColumns = [
			{ key: 'item_code', label: __('Item Code') },
			{ key: 'item_name', label: __('Item Name') },
			{ key: 'bom_no', label: __('BOM') },
			{ key: 'planned_qty', label: __('Planned Qty'), align: 'end' },
			{ key: 'produced_qty', label: __('Produced Qty'), align: 'end' },
			{ key: 'pending_qty', label: __('Pending Qty'), align: 'end' },
			{ key: 'weight', label: __('Weight'), align: 'end' },
			{ key: 'stock_uom', label: __('UOM') },
			{ key: 'warehouse', label: __('Target Warehouse') },
			{ key: 'planned_start_date', label: __('Required Date') },
		];

		const itemRows = computed(() =>
			(detail.value.items || []).map((row) => ({
				...row,
				planned_start_date: formatDisplayDate(row.planned_start_date),
			})),
		);

		const totals = computed(() => [
			{ label: __('Item Count'), value: detail.value.item_count || 0 },
			{ label: __('Total Planned Qty'), value: Number(detail.value.total_planned_qty || 0) },
			{ label: __('Total Produced Qty'), value: Number(detail.value.total_produced_qty || 0) },
			{ label: __('Total Weight'), value: Number(detail.value.total_weight || 0).toFixed(2) },
		]);

		const statusColor = (status) => {
			const map = {
				Draft: 'grey',
				'Work In Progress': 'orange',
				'Production Complete': 'green',
				Cancelled: 'red',
			};
			return map[status] || 'grey';
		};

		const actionColor = (action) => {
			const map = {
				'Start Production': 'primary',
				'Mark Production Complete': 'success',
				Cancel: 'error',
				Delete: 'error',
			};
			return map[action] || 'primary';
		};

		const loadDetail = async () => {
			loading.value = true;
			notFound.value = false;
			try {
				const { message } = await frappe.call({
					method: 'posawesome.posawesome.api.production_plans.get_production_plan_detail',
					args: { name },
				});
				if (!message) {
					notFound.value = true;
				} else {
					detail.value = message;
				}
			} catch (e) {
				notFound.value = true;
			} finally {
				loading.value = false;
			}
		};

		const confirmDialogOpen = ref(false);
		const pendingAction = ref(null);

		const confirmDialogTitle = computed(() =>
			pendingAction.value ? __('{0}?', [__(pendingAction.value)]) : '',
		);
		const confirmDialogMessage = computed(() =>
			pendingAction.value
				? ACTION_CONFIRM_MESSAGES[pendingAction.value] || __('Are you sure you want to continue?')
				: '',
		);

		const requestAdvanceStatus = (action) => {
			pendingAction.value = action;
			confirmDialogOpen.value = true;
		};

		const performAdvanceStatus = async () => {
			if (!pendingAction.value) return;
			const action = pendingAction.value;
			actionLoading.value = true;
			try {
				if (action === 'Delete') {
					await frappe.call({
						method: 'posawesome.posawesome.api.production_plans.delete_production_plan',
						args: { name },
						freeze: true,
						freeze_message: __('Deleting...'),
					});
					toastStore.show({
						title: __('Production Plan {0} and its Work Order deleted', [name]),
						color: 'success',
					});
					confirmDialogOpen.value = false;
					pendingAction.value = null;
					router.push('/production-plans/list');
					return;
				}
				await frappe.call({
					method: 'posawesome.posawesome.api.production_plans.advance_production_plan_status',
					args: { name, action },
					freeze: true,
					freeze_message: __('Updating status...'),
				});
				toastStore.show({ title: __('Production Plan {0} updated', [name]), color: 'success' });
				confirmDialogOpen.value = false;
				pendingAction.value = null;
				await loadDetail();
			} catch (e) {
				toastStore.show({ title: e?.message || __('Failed to update status'), color: 'error' });
			} finally {
				actionLoading.value = false;
			}
		};

		const printDocument = () => openDocumentPrintView('Production Plan', name);

		const actions = computed(() => [
			...(detail.value.available_actions || []).map((action) => ({
				label: __(action),
				color: actionColor(action),
				loading: actionLoading.value,
				onClick: () => requestAdvanceStatus(action),
			})),
			{ label: __('Print'), color: 'primary', onClick: printDocument },
		]);

		const goBack = () => {
			router.push('/production-plans/list');
		};

		onMounted(loadDetail);

		return {
			formatFloat,
			rawMaterials,
			name,
			loading,
			notFound,
			detail,
			metaFields,
			itemColumns,
			itemRows,
			totals,
			actions,
			statusColor,
			actionColor,
			confirmDialogOpen,
			pendingAction,
			confirmDialogTitle,
			confirmDialogMessage,
			actionLoading,
			performAdvanceStatus,
			goBack,
		};
	},
};
</script>
