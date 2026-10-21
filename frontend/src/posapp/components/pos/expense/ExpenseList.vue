<template>
	<div class="pa-0 h-100 invoice-shell pos-list-page">
		<v-card flat class="invoice-section-card pos-themed-card pos-list-card">
			<div class="pos-list-header">
				<div class="pos-list-header__main">
					<p class="pos-list-header__eyebrow">{{ __("Expenses & Advances") }}</p>
					<h3 class="pos-list-header__title">{{ __("Expenses") }}</h3>
					<p class="pos-list-header__subtitle">
						{{ __("Track the expense claims you have submitted") }}
					</p>
				</div>
				<div class="pos-list-header__actions">
					<v-btn
						color="primary"
						variant="flat"
						class="text-none"
						prepend-icon="mdi-plus"
						@click="goToNew"
					>
						{{ __("New Expense") }}
					</v-btn>
				</div>
			</div>

			<div class="pos-list-stats">
				<div class="pos-list-stat pos-list-stat--primary">
					<span class="pos-list-stat__label">{{ __("Total") }}</span>
					<strong class="pos-list-stat__value">{{ total }}</strong>
				</div>
				<div class="pos-list-stat pos-list-stat--success">
					<span class="pos-list-stat__label">{{ __("Total Claimed") }}</span>
					<strong class="pos-list-stat__value">{{ formatCurrency(totalClaimed) }}</strong>
				</div>
			</div>

			<div class="pos-list-toolbar">
				<v-text-field
					v-model="searchQuery"
					:label="__('Search expense claim or remark')"
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
						@click="loadExpenseClaims"
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
					@update:model-value="resetAndLoad"
				/>
				<DateFilterField
					v-model="toDate"
					:label="__('To Date')"
					field-class="pos-themed-input pos-list-filter-field"
					:min="fromDate"
					@update:model-value="resetAndLoad"
				/>
				<v-autocomplete
					v-model="warehouseFilter"
					:items="warehouseOptions"
					item-title="warehouse_name"
					item-value="name"
					:label="__('Warehouse')"
					density="compact"
					variant="outlined"
					hide-details
					clearable
					class="pos-themed-input pos-list-filter-field"
					@update:model-value="resetAndLoad"
				/>
				<v-autocomplete
					v-model="expenseTypeFilter"
					:items="expenseTypeOptions"
					item-title="name"
					item-value="name"
					:label="__('Expense Type')"
					density="compact"
					variant="outlined"
					hide-details
					clearable
					class="pos-themed-input pos-list-filter-field"
					@update:model-value="resetAndLoad"
				/>
				<v-btn variant="text" size="small" class="text-none" @click="clearFilters">
					{{ __("Clear Filters") }}
				</v-btn>
			</div>

			<div v-if="expenseList.length" class="pos-list-table-wrap">
				<v-data-table
					:headers="listHeaders"
					:items="expenseList"
					:loading="listLoading"
					density="comfortable"
					hide-default-footer
					:items-per-page="-1"
					class="pos-list-table pos-list-table--wrap"
					show-expand
					:expand-on-click="false"
					item-value="name"
					v-model:expanded="expandedRows"
					@click:row="(_, row) => openExpenseDetail(row.item)"
				>
					<template #item.data-table-expand="{ internalItem, isExpanded, toggleExpand }">
						<v-btn
							:icon="isExpanded(internalItem) ? 'mdi-chevron-up' : 'mdi-chevron-down'"
							size="small"
							variant="text"
							density="comfortable"
							:aria-label="__('Toggle details')"
							@click.stop="toggleExpand(internalItem)"
						/>
					</template>
					<template #expanded-row="{ columns, item }">
						<tr class="pos-list-expanded-row">
							<td :colspan="columns.length">
								<InvoiceExpandedDetail
									variant="expense"
									:detail="detailCache[item.name]"
									:loading="!!detailLoading[item.name]"
									:format-currency="formatCurrency"
								/>
							</td>
						</tr>
					</template>
					<template #item.name="{ item }">
						<span class="pos-list-cell-primary">{{ item.name }}</span>
					</template>
					<template #item.posting_date="{ item }">
						<span class="pos-list-cell-muted">{{ formatDisplayDate(item.posting_date) }}</span>
					</template>
					<template #item.creation_ampm="{ item }">
						<span class="pos-list-cell-muted">{{ $posTimeAmPm(item.creation) }}</span>
					</template>
					<template #item.remark="{ item }">
						<!-- Remarks can be long: one line with "…", full text on hover. -->
						<v-tooltip v-if="item.remark" :text="item.remark" location="top" max-width="420">
							<template #activator="{ props: tipProps }">
								<span v-bind="tipProps" class="pos-list-cell-remarks">{{ item.remark }}</span>
							</template>
						</v-tooltip>
						<span v-else>—</span>
					</template>
					<template #item.expense_types="{ item }">
						<span class="pos-list-cell-truncate" :title="item.expense_types">{{ item.expense_types || "—" }}</span>
					</template>
					<template #item.grand_total="{ item }">
						{{ formatCurrency(item.grand_total) }}
					</template>
					<template #item.status="{ item }">
						<v-chip size="small" variant="tonal" :color="statusColor(item.status)">
							{{ item.status }}
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

				<ListPagination
					v-model:page="page"
					v-model:page-size="pageSize"
					:total="total"
					:loading="listLoading"
					@update:page="loadExpenseClaims"
					@update:page-size="resetAndLoad"
				/>
			</div>

			<div v-else-if="!listLoading" class="pos-list-empty">
				<v-icon size="48" color="primary" class="pos-list-empty__icon">mdi-receipt-text-edit-outline</v-icon>
				<h4 class="pos-list-empty__title">{{ __("No expenses found") }}</h4>
				<p class="pos-list-empty__subtitle">
					{{ hasActiveFilters
						? __("Try different filters or clear them.")
						: __("Submit a new expense claim to see it listed here.") }}
				</p>
				<v-btn
					v-if="!hasActiveFilters"
					color="primary"
					variant="flat"
					class="text-none mt-2"
					prepend-icon="mdi-plus"
					@click="goToNew"
				>
					{{ __("New Expense") }}
				</v-btn>
			</div>

			<div v-else class="pos-list-empty">
				<v-progress-circular indeterminate color="primary" />
			</div>
		</v-card>

		<ConfirmActionDialog
			v-model="confirmDialog"
			:title="confirmDialogTitle"
			:message="confirmDialogMessage"
			:confirm-label="confirmDialogActionLabel"
			:confirm-color="confirmDialogColor"
			:loading="actionLoadingName === confirmDialogItem?.name"
			@confirm="runConfirmedAction"
		/>
	</div>
</template>

<script>
import { ref, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import format from '../../../format';
import DateFilterField from '../shared/DateFilterField.vue';
import ListPagination from '../shared/ListPagination.vue';
import { useWarehouseFilterOptions } from '../shared/useWarehouseFilterOptions';
import RowActionsMenu from '../shared/RowActionsMenu.vue';
import ConfirmActionDialog from '../shared/ConfirmActionDialog.vue';
import InvoiceExpandedDetail from '../shared/InvoiceExpandedDetail.vue';
import { useExpandedRowDetail } from '../../../composables/useExpandedRowDetail';
import { useToastStore } from '../../../stores/toastStore';

export default {
	name: 'ExpenseList',
	components: { DateFilterField, ListPagination, RowActionsMenu, ConfirmActionDialog, InvoiceExpandedDetail },
	mixins: [format],
	setup() {
		const router = useRouter();
		const toastStore = useToastStore();

		const isSystemManager = computed(() =>
			(frappe?.boot?.user?.roles || []).includes('System Manager'),
		);

		const actionLoadingName = ref(null);
		const confirmDialog = ref(false);
		const confirmDialogItem = ref(null);
		const confirmDialogAction = ref(null);
		const confirmDialogTitle = ref('');
		const confirmDialogMessage = ref('');
		const confirmDialogActionLabel = ref('');
		const confirmDialogColor = ref('error');

		const canCancel = (item) => isSystemManager.value && item.docstatus === 1;
		// Delete is hidden from the UI -- users are no longer allowed to delete
		// Draft/Cancelled Expense Claims from POS Awesome.
		const canDelete = () => false;

		const rowActions = (item) => [
			{ key: 'view', label: __('View'), icon: 'mdi-eye-outline' },
			{
				key: 'cancel',
				label: __('Cancel'),
				icon: 'mdi-cancel',
				color: 'error',
				show: canCancel(item),
			},
			{
				key: 'delete',
				label: __('Delete'),
				icon: 'mdi-delete-outline',
				color: 'error',
				show: canDelete(item),
			},
		];

		const handleRowAction = (key, item) => {
			if (key === 'view') {
				openExpenseDetail(item);
			} else if (key === 'cancel') {
				openCancelConfirm(item);
			} else if (key === 'delete') {
				openDeleteConfirm(item);
			}
		};

		const openCancelConfirm = (item) => {
			confirmDialogItem.value = item;
			confirmDialogAction.value = 'cancel';
			confirmDialogTitle.value = __('Cancel Expense Claim');
			confirmDialogMessage.value = __(
				'This will cancel {0} and reverse its accounting entries. This cannot be undone. Continue?',
				[item.name],
			);
			confirmDialogActionLabel.value = __('Cancel Expense');
			confirmDialogColor.value = 'error';
			confirmDialog.value = true;
		};

		const openDeleteConfirm = (item) => {
			confirmDialogItem.value = item;
			confirmDialogAction.value = 'delete';
			confirmDialogTitle.value = __('Delete Expense Claim');
			confirmDialogMessage.value = __(
				'This will permanently delete cancelled expense claim {0}. This cannot be undone. Continue?',
				[item.name],
			);
			confirmDialogActionLabel.value = __('Delete');
			confirmDialogColor.value = 'error';
			confirmDialog.value = true;
		};

		const runConfirmedAction = async () => {
			const item = confirmDialogItem.value;
			const action = confirmDialogAction.value;
			if (!item || !action) return;

			actionLoadingName.value = item.name;
			try {
				if (action === 'cancel') {
					await frappe.call({
						method: 'posawesome.posawesome.api.expense_claims.cancel_expense_claim',
						args: { expense_claim: item.name },
					});
					toastStore.show({ title: __('{0} cancelled', [item.name]), color: 'success' });
				} else if (action === 'delete') {
					await frappe.call({
						method: 'posawesome.posawesome.api.expense_claims.delete_cancelled_expense_claim',
						args: { expense_claim: item.name },
					});
					toastStore.show({ title: __('{0} deleted', [item.name]), color: 'success' });
				}
				confirmDialog.value = false;
				await loadExpenseClaims();
			} catch (e) {
				toastStore.show({ title: e?.message || __('Action failed'), color: 'error' });
			} finally {
				actionLoadingName.value = null;
			}
		};

		const expenseList = ref([]);
		const listLoading = ref(false);
		const searchQuery = ref('');
		let searchTimeout = null;

		const page = ref(1);
		const pageSize = ref(10);
		// Covers every page, not just the rows on screen -- from the server.
		const totalClaimed = ref(0);
		const total = ref(0);

		const fromDate = ref('');
		const toDate = ref('');
		const warehouseFilter = ref(null);
		const expenseTypeFilter = ref(null);
		const expenseTypeOptions = ref([]);
		const { warehouseOptions, loadWarehouseOptions } = useWarehouseFilterOptions();

		const listHeaders = [
			{ title: __('Expense Claim'), key: 'name', sortable: true },
			{ title: __('Employee'), key: 'employee_name', sortable: true },
			{ title: __('Warehouse'), key: 'warehouse', sortable: true },
			{ title: __('Date'), key: 'posting_date', sortable: true },
			{ title: __('Time'), key: 'creation_ampm', sortable: false },
			{ title: __('Remark'), key: 'remark', sortable: false , headerProps: { class: 'pos-list-col-flex' } },
			{ title: __('Expense Type'), key: 'expense_types', sortable: false },
			{ title: __('Amount'), key: 'grand_total', sortable: true, align: 'end' },
			{ title: __('Status'), key: 'status', sortable: true },
			{ title: __('Actions'), key: 'actions', sortable: false, align: 'end', width: '48px' },
		];

		const hasActiveFilters = computed(() =>
			Boolean(
				searchQuery.value ||
					fromDate.value ||
					toDate.value ||
					warehouseFilter.value ||
					expenseTypeFilter.value,
			),
		);

		const formatDisplayDate = (value) => {
			if (!value) return '—';
			const parts = String(value).split('-');
			return parts.length === 3 ? `${parts[2]}-${parts[1]}-${parts[0]}` : value;
		};

		const statusColor = (status) => {
			const map = {
				Paid: 'green',
				Unpaid: 'orange',
				Rejected: 'red',
				Cancelled: 'red',
				Submitted: 'blue',
				Draft: 'grey',
			};
			return map[status] || 'grey';
		};

		const loadExpenseClaims = async () => {
			listLoading.value = true;
			try {
				const { message } = await frappe.call({
					method: 'posawesome.posawesome.api.expense_claims.get_expense_claims_list',
					args: {
						page_start: (page.value - 1) * pageSize.value,
						page_length: pageSize.value,
						from_date: fromDate.value || undefined,
						to_date: toDate.value || undefined,
						warehouse: warehouseFilter.value || undefined,
						expense_type: expenseTypeFilter.value || undefined,
						search: searchQuery.value || undefined,
					},
				});
				expenseList.value = message?.expense_claims || [];
				total.value = message?.total || 0;
				totalClaimed.value = message?.total_claimed || 0;
			} catch (e) {
				console.error('Failed to load expense claims', e);
				expenseList.value = [];
			} finally {
				listLoading.value = false;
			}
		};

		const resetAndLoad = () => {
			page.value = 1;
			loadExpenseClaims();
		};

		const handleSearchUpdate = () => {
			if (searchTimeout) clearTimeout(searchTimeout);
			searchTimeout = setTimeout(resetAndLoad, 300);
		};

		const loadExpenseTypes = async () => {
			try {
				const { message } = await frappe.call({
					method: 'posawesome.posawesome.api.expense_claims.get_expense_claim_types',
				});
				expenseTypeOptions.value = message || [];
			} catch (e) {
				console.error('Failed to load expense claim types', e);
			}
		};

		const clearFilters = () => {
			searchQuery.value = '';
			fromDate.value = '';
			toDate.value = '';
			warehouseFilter.value = null;
			expenseTypeFilter.value = null;
			resetAndLoad();
		};

		const goToNew = () => {
			router.push('/expenses/new');
		};

		const openExpenseDetail = (item) => {
			router.push(`/expenses/${item.name}`);
		};

		onMounted(() => {
			loadWarehouseOptions();
			loadExpenseTypes();
			loadExpenseClaims();
		});

		const { expandedRows, detailCache, detailLoading } = useExpandedRowDetail(
			'posawesome.posawesome.api.expense_claims.get_expense_claim_detail',
			'expense_claim',
		);

		return {
			expandedRows,
			detailCache,
			detailLoading,
			expenseList,
			listLoading,
			searchQuery,
			listHeaders,
			total,
			page,
			pageSize,
			fromDate,
			toDate,
			warehouseFilter,
			warehouseOptions,
			expenseTypeFilter,
			expenseTypeOptions,
			hasActiveFilters,
			totalClaimed,
			loadExpenseClaims,
			resetAndLoad,
			handleSearchUpdate,
			clearFilters,
			formatDisplayDate,
			statusColor,
			goToNew,
			openExpenseDetail,
			isSystemManager,
			actionLoadingName,
			confirmDialog,
			confirmDialogItem,
			confirmDialogTitle,
			confirmDialogMessage,
			confirmDialogActionLabel,
			confirmDialogColor,
			rowActions,
			handleRowAction,
			runConfirmedAction,
		};
	},
};
</script>

<style scoped>
@import '../invoice-shared-styles.css';
</style>
