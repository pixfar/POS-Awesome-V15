<template>
	<div class="pa-0 h-100 invoice-shell pos-list-page">
		<v-card flat class="invoice-section-card pos-themed-card pos-list-card">
			<div class="pos-list-header">
				<div class="pos-list-header__main">
					<p class="pos-list-header__eyebrow">{{ __("Molding") }}</p>
					<h3 class="pos-list-header__title">{{ __("Daily Production") }}</h3>
					<p class="pos-list-header__subtitle">
						{{ __("Daily molding work (KG) and the wage split between present workers") }}
					</p>
				</div>
				<div v-if="canManage" class="pos-list-header__actions">
					<v-btn color="primary" variant="flat" class="text-none" prepend-icon="mdi-plus" @click="goToNew">
						{{ __("New Production") }}
					</v-btn>
				</div>
			</div>

			<div class="pos-list-stats">
				<div class="pos-list-stat pos-list-stat--primary">
					<span class="pos-list-stat__label">{{ __("Total") }}</span>
					<strong class="pos-list-stat__value">{{ total }}</strong>
				</div>
				<div class="pos-list-stat pos-list-stat--warning">
					<span class="pos-list-stat__label">{{ __("Total Work (KG)") }}</span>
					<strong class="pos-list-stat__value">{{ formatFloat(totalWorkKg) }}</strong>
				</div>
				<div class="pos-list-stat pos-list-stat--success">
					<span class="pos-list-stat__label">{{ __("Total Wage") }}</span>
					<strong class="pos-list-stat__value">{{ formatCurrency(totalWage) }}</strong>
				</div>
			</div>

			<div class="pos-list-toolbar">
				<v-text-field
					v-model="searchQuery"
					:label="__('Search production ID')"
					density="compact"
					variant="solo"
					hide-details
					clearable
					prepend-inner-icon="mdi-magnify"
					class="pos-themed-input pos-list-search"
					@update:model-value="handleSearchUpdate"
				/>
				<div class="pos-list-toolbar__filters">
					<v-btn
						variant="tonal"
						size="small"
						color="primary"
						prepend-icon="mdi-sync"
						:loading="listLoading"
						class="text-none"
						@click="loadRecords"
					>
						{{ __("Sync") }}
					</v-btn>
				</div>
			</div>

			<div class="pos-list-filters">
				<DateFilterField
					v-model="fromDate"
					:label="__('From Date')"
					field-class="pos-themed-input pos-list-filter-field"
					:max="toDate"
					@update:model-value="loadRecords"
				/>
				<DateFilterField
					v-model="toDate"
					:label="__('To Date')"
					field-class="pos-themed-input pos-list-filter-field"
					:min="fromDate"
					@update:model-value="loadRecords"
				/>
				<v-btn variant="text" size="small" class="text-none" @click="clearFilters">
					{{ __("Clear Filters") }}
				</v-btn>
			</div>

			<div v-if="records.length" class="pos-list-table-wrap">
				<v-data-table
					:headers="listHeaders"
					:items="records"
					:loading="listLoading"
					density="comfortable"
					hide-default-footer
					:items-per-page="-1"
					class="pos-list-table"
					@click:row="(_, row) => openDetail(row.item)"
				>
					<template #item.name="{ item }">
						<span class="pos-list-cell-primary">{{ item.name }}</span>
					</template>
					<template #item.date="{ item }">
						<span class="pos-list-cell-muted">{{ formatDisplayDate(item.date) }}</span>
					</template>
					<template #item.total_work_kg="{ item }">{{ formatFloat(item.total_work_kg) }}</template>
					<template #item.rate_per_kg="{ item }">{{ formatCurrency(item.rate_per_kg) }}</template>
					<template #item.total_wage="{ item }">{{ formatCurrency(item.total_wage) }}</template>
					<template #item.status="{ item }">
						<v-chip size="small" variant="tonal" :color="statusColor(item.status)">
							{{ __(item.status) }}
						</v-chip>
					</template>
					<template #item.actions="{ item }">
						<div class="d-flex justify-end">
							<RowActionsMenu
								:actions="rowActions(item)"
								:loading="actionLoadingName === item.name"
								@action="(key) => handleRowAction(key, item)"
							/>
						</div>
					</template>
				</v-data-table>
			</div>

			<div v-else-if="!listLoading" class="pos-list-empty">
				<v-icon size="48" color="primary" class="pos-list-empty__icon">mdi-factory</v-icon>
				<h4 class="pos-list-empty__title">{{ __("No production records found") }}</h4>
				<p class="pos-list-empty__subtitle">
					{{ hasActiveFilters
						? __("Try different filters or clear them.")
						: __("Record a day's molding production to see it listed here.") }}
				</p>
			</div>

			<div v-else class="pos-list-empty">
				<v-progress-circular indeterminate color="primary" />
			</div>
		</v-card>

		<ConfirmActionDialog
			v-model="confirmDialog"
			:title="__('Cancel Molding Daily Production')"
			:message="confirmMessage"
			:confirm-label="__('Cancel Production')"
			confirm-color="error"
			:loading="Boolean(actionLoadingName)"
			@confirm="runCancel"
		/>
	</div>
</template>

<script>
import { ref, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import format from '../../../format';
import DateFilterField from '../shared/DateFilterField.vue';
import RowActionsMenu from '../shared/RowActionsMenu.vue';
import ConfirmActionDialog from '../shared/ConfirmActionDialog.vue';
import { useToastStore } from '../../../stores/toastStore';
import { isFundTransferManager } from '../../../utils/posWarehouseAccess';
import { formatDisplayDate, docStatusColor } from '../shared/docStatusUtils';

const API = 'posawesome.posawesome.api.molding';

export default {
	name: 'MoldingProductionList',
	components: { DateFilterField, RowActionsMenu, ConfirmActionDialog },
	mixins: [format],
	setup() {
		const router = useRouter();
		const toastStore = useToastStore();
		// BSP Viewer sees the list but cannot create or cancel -- re-checked server-side.
		const canManage = computed(() => isFundTransferManager());

		const records = ref([]);
		const total = ref(0);
		const listLoading = ref(false);
		const searchQuery = ref('');
		const fromDate = ref('');
		const toDate = ref('');
		let searchTimeout = null;

		const listHeaders = [
			{ title: __('Production'), key: 'name', sortable: true },
			{ title: __('Date'), key: 'date', sortable: true },
			{ title: __('Workers'), key: 'employee_count', sortable: true, align: 'end' },
			{ title: __('Work (KG)'), key: 'total_work_kg', sortable: true, align: 'end' },
			{ title: __('Rate / KG'), key: 'rate_per_kg', sortable: true, align: 'end' },
			{ title: __('Total Wage'), key: 'total_wage', sortable: true, align: 'end' },
			{ title: __('Status'), key: 'status', sortable: true },
			{ title: __('Actions'), key: 'actions', sortable: false, align: 'end', width: '100px' },
		];

		const hasActiveFilters = computed(() => Boolean(searchQuery.value || fromDate.value || toDate.value));
		const activeRecords = computed(() => records.value.filter((row) => row.docstatus === 1));
		const totalWorkKg = computed(() =>
			activeRecords.value.reduce((sum, row) => sum + (Number(row.total_work_kg) || 0), 0),
		);
		const totalWage = computed(() =>
			activeRecords.value.reduce((sum, row) => sum + (Number(row.total_wage) || 0), 0),
		);

		const loadRecords = async () => {
			listLoading.value = true;
			try {
				const { message } = await frappe.call({
					method: `${API}.get_daily_production_list`,
					args: {
						from_date: fromDate.value || undefined,
						to_date: toDate.value || undefined,
						search: searchQuery.value || undefined,
					},
				});
				records.value = message?.records || [];
				total.value = message?.total || 0;
			} catch (e) {
				console.error('Failed to load molding daily production', e);
				records.value = [];
			} finally {
				listLoading.value = false;
			}
		};

		const handleSearchUpdate = () => {
			if (searchTimeout) clearTimeout(searchTimeout);
			searchTimeout = setTimeout(loadRecords, 300);
		};

		const clearFilters = () => {
			searchQuery.value = '';
			fromDate.value = '';
			toDate.value = '';
			loadRecords();
		};

		const goToNew = () => router.push('/molding-production/new');
		const openDetail = (item) => router.push(`/molding-production/${item.name}`);

		const actionLoadingName = ref(null);
		const confirmDialog = ref(false);
		const confirmItem = ref(null);
		const confirmMessage = computed(() =>
			__('This will cancel {0} and its Additional Salary wage entries. Continue?', [
				confirmItem.value?.name || '',
			]),
		);

		const rowActions = (item) => [
			{ key: 'view', label: __('View'), icon: 'mdi-eye-outline' },
			{
				key: 'cancel',
				label: __('Cancel'),
				icon: 'mdi-cancel',
				color: 'error',
				show: canManage.value && item.docstatus === 1,
			},
		];

		const handleRowAction = (key, item) => {
			if (key === 'view') {
				openDetail(item);
			} else if (key === 'cancel') {
				confirmItem.value = item;
				confirmDialog.value = true;
			}
		};

		const runCancel = async () => {
			const item = confirmItem.value;
			if (!item) return;
			actionLoadingName.value = item.name;
			try {
				await frappe.call({ method: `${API}.cancel_daily_production`, args: { name: item.name } });
				toastStore.show({ title: __('{0} cancelled', [item.name]), color: 'success' });
				confirmDialog.value = false;
				await loadRecords();
			} catch (e) {
				toastStore.show({ title: e?.message || __('Action failed'), color: 'error' });
			} finally {
				actionLoadingName.value = null;
			}
		};

		onMounted(loadRecords);

		return {
			canManage,
			records,
			total,
			listLoading,
			searchQuery,
			fromDate,
			toDate,
			listHeaders,
			hasActiveFilters,
			totalWorkKg,
			totalWage,
			loadRecords,
			handleSearchUpdate,
			clearFilters,
			goToNew,
			openDetail,
			formatDisplayDate,
			statusColor: docStatusColor,
			actionLoadingName,
			confirmDialog,
			confirmMessage,
			rowActions,
			handleRowAction,
			runCancel,
		};
	},
};
</script>

<style scoped>
@import '../invoice-shared-styles.css';
</style>
