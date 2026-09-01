<template>
	<div class="pa-0 h-100 invoice-shell pos-list-page">
		<v-card flat class="invoice-section-card pos-themed-card pos-list-card">
			<div class="pos-list-header">
				<div class="pos-list-header__main">
					<p class="pos-list-header__eyebrow">{{ __("Payment") }}</p>
					<h3 class="pos-list-header__title">{{ __("Payments") }}</h3>
					<p class="pos-list-header__subtitle">
						{{ __("Track submitted payment entries to customers and suppliers") }}
					</p>
				</div>
				<div class="pos-list-header__actions">
					<v-btn
						color="primary"
						variant="flat"
						class="text-none"
						prepend-icon="mdi-account"
						@click="goToNew('Customer')"
					>
						{{ __("Customer Payment") }}
					</v-btn>
					<v-btn
						v-if="canMakeSupplierPayment"
						color="primary"
						variant="tonal"
						class="text-none"
						prepend-icon="mdi-truck-delivery"
						@click="goToNew('Supplier')"
					>
						{{ __("Supplier Payment") }}
					</v-btn>
				</div>
			</div>

			<div class="pos-list-stats">
				<div class="pos-list-stat pos-list-stat--primary">
					<span class="pos-list-stat__label">{{ __("Total") }}</span>
					<strong class="pos-list-stat__value">{{ total }}</strong>
				</div>
				<div class="pos-list-stat pos-list-stat--success">
					<span class="pos-list-stat__label">{{ __("Received") }}</span>
					<strong class="pos-list-stat__value">{{ typeCounts.Receive || 0 }}</strong>
				</div>
				<div class="pos-list-stat pos-list-stat--warning">
					<span class="pos-list-stat__label">{{ __("Paid") }}</span>
					<strong class="pos-list-stat__value">{{ typeCounts.Pay || 0 }}</strong>
				</div>
				<div class="pos-list-stat">
					<span class="pos-list-stat__label">{{ __("Total Amount") }}</span>
					<strong class="pos-list-stat__value">{{ formatCurrency(totalAmount) }}</strong>
				</div>
			</div>

			<div class="pos-list-toolbar">
				<v-text-field
					v-model="searchQuery"
					:label="__('Search payment or party')"
					density="compact"
					variant="solo"
					hide-details
					clearable
					prepend-inner-icon="mdi-magnify"
					class="pos-themed-input pos-list-search"
					@update:model-value="handleSearchUpdate"
				/>
				<div class="pos-list-toolbar__filters">
					<v-switch
						v-model="mineOnly"
						density="compact"
						hide-details
						color="primary"
						:label="__('My Payments')"
						@update:model-value="resetAndLoad"
					/>
					<v-btn
						variant="tonal"
						size="small"
						color="primary"
						prepend-icon="mdi-sync"
						:loading="listLoading"
						class="text-none"
						@click="loadPayments"
					>
						{{ __("Sync") }}
					</v-btn>
				</div>
			</div>

			<div class="pos-list-filters">
				<v-autocomplete
					v-model="customerFilter"
					v-model:search="customerSearchQuery"
					:items="customerSearchResults"
					:loading="customerSearchLoading"
					item-title="customer_name"
					item-value="name"
					:label="__('Customer')"
					density="compact"
					variant="outlined"
					hide-details
					clearable
					:custom-filter="() => true"
					class="pos-themed-input pos-list-filter-field"
					@update:search="handleCustomerSearchUpdate"
					@update:model-value="handleCustomerSelected"
				/>
				<v-autocomplete
					v-model="supplierFilter"
					v-model:search="supplierSearchQuery"
					:items="supplierSearchResults"
					:loading="supplierSearchLoading"
					item-title="supplier_name"
					item-value="name"
					:label="__('Supplier')"
					density="compact"
					variant="outlined"
					hide-details
					clearable
					:custom-filter="() => true"
					class="pos-themed-input pos-list-filter-field"
					@update:search="handleSupplierSearchUpdate"
					@update:model-value="handleSupplierSelected"
				/>
				<v-select
					v-model="paymentTypeFilter"
					:items="paymentTypeOptions"
					:label="__('Payment Type')"
					density="compact"
					variant="outlined"
					hide-details
					clearable
					class="pos-themed-input pos-list-filter-field"
					@update:model-value="resetAndLoad"
				/>
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
				<v-select
					v-model="modeOfPaymentFilter"
					:items="modeOfPaymentOptions"
					item-title="name"
					item-value="name"
					:label="__('Mode of Payment')"
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

			<div v-if="paymentList.length" class="pos-list-table-wrap">
				<v-data-table
					:headers="listHeaders"
					:items="paymentList"
					:loading="listLoading"
					density="comfortable"
					hide-default-footer
					:items-per-page="-1"
					class="pos-list-table payment-list-table"
					@click:row="(_, row) => openPaymentDetail(row.item)"
				>
					<template #item.name="{ item }">
						<span class="pos-list-cell-primary">{{ item.name }}</span>
					</template>
					<template #item.posting_date="{ item }">
						<span class="pos-list-cell-muted">{{ formatDisplayDate(item.posting_date) }}</span>
					</template>
					<template #item.party_name="{ item }">
						<span class="pos-list-cell-truncate" :title="item.party_name || item.party">
							{{ item.party_name || item.party }}
						</span>
					</template>
					<template #item.payment_type="{ item }">
						<v-chip size="small" variant="tonal" :color="paymentTypeColor(item.payment_type)">
							{{ item.payment_type }}
						</v-chip>
					</template>
					<template #item.amount="{ item }">
						<span class="pos-list-cell-primary">
							{{ formatCurrency(item.amount) }}
						</span>
					</template>
					<template #item.docstatus="{ item }">
						<v-chip size="small" variant="tonal" :color="item.docstatus === 2 ? 'red' : 'green'">
							{{ item.docstatus === 2 ? __("Cancelled") : __("Submitted") }}
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

				<div class="pos-list-pagination">
					<div class="pos-list-pagination__info">
						{{ paginationLabel }}
					</div>
					<div class="pos-list-pagination__controls">
						<v-select
							v-model="pageSize"
							:items="[10, 20, 50]"
							density="compact"
							variant="outlined"
							hide-details
							class="pos-themed-input pos-list-pagination__page-size"
							@update:model-value="resetAndLoad"
						/>
						<v-btn
							icon="mdi-page-first"
							size="small"
							variant="text"
							:disabled="page <= 1 || listLoading"
							@click="goToPage(1)"
						/>
						<v-btn
							icon="mdi-chevron-left"
							size="small"
							variant="text"
							:disabled="page <= 1 || listLoading"
							@click="goToPage(page - 1)"
						/>
						<v-btn
							v-for="pageNumber in pageNumbers"
							:key="pageNumber"
							size="small"
							:variant="pageNumber === page ? 'flat' : 'text'"
							:color="pageNumber === page ? 'primary' : undefined"
							class="pos-list-pagination__page-btn"
							:disabled="listLoading"
							@click="goToPage(pageNumber)"
						>
							{{ pageNumber }}
						</v-btn>
						<v-btn
							icon="mdi-chevron-right"
							size="small"
							variant="text"
							:disabled="!hasMore || listLoading"
							@click="goToPage(page + 1)"
						/>
						<v-btn
							icon="mdi-page-last"
							size="small"
							variant="text"
							:disabled="!hasMore || listLoading"
							@click="goToPage(totalPages)"
						/>
					</div>
				</div>
			</div>

			<div v-else-if="!listLoading" class="pos-list-empty">
				<v-icon size="48" color="primary" class="pos-list-empty__icon">mdi-cash-multiple</v-icon>
				<h4 class="pos-list-empty__title">{{ __("No payments found") }}</h4>
				<p class="pos-list-empty__subtitle">
					{{ hasActiveFilters
						? __("Try different filters or clear them.")
						: __("Record a customer or supplier payment to see it listed here.") }}
				</p>
				<v-btn
					v-if="!hasActiveFilters"
					color="primary"
					variant="flat"
					class="text-none mt-2"
					prepend-icon="mdi-account"
					@click="goToNew('Customer')"
				>
					{{ __("Customer Payment") }}
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
import { useUIStore } from '../../../stores/uiStore.js';
import { ensurePosProfile } from '../../../../utils/pos_profile';
import DateFilterField from '../shared/DateFilterField.vue';
import RowActionsMenu from '../shared/RowActionsMenu.vue';
import ConfirmActionDialog from '../shared/ConfirmActionDialog.vue';
import { useToastStore } from '../../../stores/toastStore';
import { isFundTransferManager } from '../../../utils/posWarehouseAccess';

export default {
	name: 'PaymentList',
	components: { DateFilterField, RowActionsMenu, ConfirmActionDialog },
	mixins: [format],
	setup() {
		const router = useRouter();
		const uiStore = useUIStore();
		const toastStore = useToastStore();

		const isSystemManager = computed(() =>
			(frappe?.boot?.user?.roles || []).includes('System Manager'),
		);
		// Same gate as Fund Transfer's "New Transfer" and the Navbar's
		// "Supplier" payment link -- only BSP Admin/System Manager can make a
		// Supplier Payment.
		const canMakeSupplierPayment = computed(() => isFundTransferManager());

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
		// Draft/Cancelled Payment Entries from POS Awesome.
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
				openPaymentDetail(item);
			} else if (key === 'cancel') {
				openCancelConfirm(item);
			} else if (key === 'delete') {
				openDeleteConfirm(item);
			}
		};

		const openCancelConfirm = (item) => {
			confirmDialogItem.value = item;
			confirmDialogAction.value = 'cancel';
			confirmDialogTitle.value = __('Cancel Payment Entry');
			confirmDialogMessage.value = __(
				'This will cancel {0} and reverse its accounting entries. This cannot be undone. Continue?',
				[item.name],
			);
			confirmDialogActionLabel.value = __('Cancel Payment');
			confirmDialogColor.value = 'error';
			confirmDialog.value = true;
		};

		const openDeleteConfirm = (item) => {
			confirmDialogItem.value = item;
			confirmDialogAction.value = 'delete';
			confirmDialogTitle.value = __('Delete Payment Entry');
			confirmDialogMessage.value = __(
				'This will permanently delete cancelled payment {0}. This cannot be undone. Continue?',
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
						method: 'posawesome.posawesome.api.payment_entry.cancel_payment_entry',
						args: { name: item.name },
					});
					toastStore.show({ title: __('{0} cancelled', [item.name]), color: 'success' });
				} else if (action === 'delete') {
					await frappe.call({
						method: 'posawesome.posawesome.api.payment_entry.delete_cancelled_payment_entry',
						args: { name: item.name },
					});
					toastStore.show({ title: __('{0} deleted', [item.name]), color: 'success' });
				}
				confirmDialog.value = false;
				await loadPayments();
			} catch (e) {
				toastStore.show({ title: e?.message || __('Action failed'), color: 'error' });
			} finally {
				actionLoadingName.value = null;
			}
		};

		const paymentList = ref([]);
		const listLoading = ref(false);
		const mineOnly = ref(false);
		const searchQuery = ref('');
		let searchTimeout = null;

		const page = ref(1);
		const pageSize = ref(20);
		const total = ref(0);
		const totalPages = computed(() => Math.max(1, Math.ceil(total.value / (pageSize.value || 1))));
		const hasMore = ref(false);
		const typeCounts = ref({});
		const totalAmount = ref(0);

		const paymentTypeOptions = ['Receive', 'Pay'];
		const paymentTypeFilter = ref(null);
		const fromDate = ref('');
		const toDate = ref('');
		const modeOfPaymentFilter = ref(null);
		const modeOfPaymentOptions = ref([]);

		const customerFilter = ref(null);
		const customerSearchQuery = ref('');
		const customerSearchResults = ref([]);
		const customerSearchLoading = ref(false);
		let customerSearchTimeout = null;

		const supplierFilter = ref(null);
		const supplierSearchQuery = ref('');
		const supplierSearchResults = ref([]);
		const supplierSearchLoading = ref(false);
		let supplierSearchTimeout = null;

		const listHeaders = [
			{ title: __('Payment'), key: 'name', sortable: true },
			{ title: __('Date'), key: 'posting_date', sortable: true },
			{ title: __('Party'), key: 'party_name', sortable: true },
			{ title: __('Type'), key: 'payment_type', sortable: true },
			{ title: __('Mode'), key: 'mode_of_payment', sortable: true },
			{ title: __('Amount'), key: 'amount', sortable: true, align: 'end' },
			{ title: __('Status'), key: 'docstatus', sortable: true },
			{ title: __('Actions'), key: 'actions', sortable: false, align: 'end', width: '120px' },
		];

		const hasActiveFilters = computed(() =>
			Boolean(
				searchQuery.value ||
					customerFilter.value ||
					supplierFilter.value ||
					paymentTypeFilter.value ||
					fromDate.value ||
					toDate.value ||
					modeOfPaymentFilter.value,
			),
		);

		const paginationLabel = computed(() => {
			if (!total.value) return __('No results');
			return __('Page {0} of {1}', [page.value, totalPages.value]);
		});

		const pageNumbers = computed(() => {
			const totalCount = totalPages.value;
			const current = page.value;
			const windowSize = 5;
			let start = Math.max(1, current - Math.floor(windowSize / 2));
			let end = Math.min(totalCount, start + windowSize - 1);
			start = Math.max(1, end - windowSize + 1);
			const pages = [];
			for (let p = start; p <= end; p++) pages.push(p);
			return pages;
		});

		const formatDisplayDate = (value) => {
			if (!value) return '—';
			const parts = String(value).split('-');
			return parts.length === 3 ? `${parts[2]}-${parts[1]}-${parts[0]}` : value;
		};

		const resolvePosProfile = async () => {
			if (uiStore.posProfile?.name) {
				return uiStore.posProfile;
			}
			try {
				const profile = await ensurePosProfile();
				if (profile?.name) {
					uiStore.setPosProfile(profile);
				}
				return profile;
			} catch (e) {
				console.error('Failed to resolve active POS profile', e);
				return null;
			}
		};

		const loadPayments = async () => {
			const posProfile = await resolvePosProfile();
			let partyType;
			let party;
			if (customerFilter.value) {
				partyType = 'Customer';
				party = customerFilter.value;
			} else if (supplierFilter.value) {
				partyType = 'Supplier';
				party = supplierFilter.value;
			}
			listLoading.value = true;
			try {
				const { message } = await frappe.call({
					method: 'posawesome.posawesome.api.payment_entry.get_payment_entries_list',
					args: {
						pos_profile: posProfile?.name || undefined,
						page_start: (page.value - 1) * pageSize.value,
						page_length: pageSize.value,
						mine_only: mineOnly.value ? 1 : 0,
						party_type: partyType,
						party,
						payment_type: paymentTypeFilter.value || undefined,
						from_date: fromDate.value || undefined,
						to_date: toDate.value || undefined,
						mode_of_payment: modeOfPaymentFilter.value || undefined,
						search: searchQuery.value || undefined,
					},
				});
				paymentList.value = message?.payments || [];
				total.value = message?.total || 0;
				hasMore.value = Boolean(message?.has_more);
				typeCounts.value = message?.type_counts || {};
				totalAmount.value = message?.total_amount || 0;
			} catch (e) {
				console.error('Failed to load payments', e);
				paymentList.value = [];
			} finally {
				listLoading.value = false;
			}
		};

		const resetAndLoad = () => {
			page.value = 1;
			loadPayments();
		};

		const handleSearchUpdate = () => {
			if (searchTimeout) clearTimeout(searchTimeout);
			searchTimeout = setTimeout(resetAndLoad, 300);
		};

		// Fetches customers immediately (empty term = default/most-recent list,
		// so the dropdown isn't empty before the user types anything), then
		// refines as they search by name, ID, or mobile number.
		const fetchCustomers = async (term) => {
			const posProfile = await resolvePosProfile();
			if (!posProfile?.name) {
				customerSearchResults.value = [];
				return;
			}
			customerSearchLoading.value = true;
			try {
				const { message } = await frappe.call({
					method: 'posawesome.posawesome.api.customers.search_customers',
					args: { pos_profile: JSON.stringify(posProfile), search_text: term || undefined, limit: 20 },
				});
				customerSearchResults.value = message || [];
			} catch {
				customerSearchResults.value = [];
			} finally {
				customerSearchLoading.value = false;
			}
		};

		const handleCustomerSearchUpdate = (term) => {
			if (customerSearchTimeout) clearTimeout(customerSearchTimeout);
			const trimmed = (term || '').trim();
			if (trimmed.length === 1) return;
			customerSearchTimeout = setTimeout(() => fetchCustomers(trimmed), 300);
		};

		const handleCustomerSelected = (value) => {
			if (value) {
				supplierFilter.value = null;
			}
			resetAndLoad();
		};

		// Same idea as fetchCustomers: an empty term returns a default list.
		const fetchSuppliers = async (term) => {
			supplierSearchLoading.value = true;
			try {
				const { message } = await frappe.call({
					method: 'posawesome.posawesome.api.purchase_invoices.search_suppliers',
					args: { search_text: term || undefined, limit: 20 },
				});
				supplierSearchResults.value = message || [];
			} catch {
				supplierSearchResults.value = [];
			} finally {
				supplierSearchLoading.value = false;
			}
		};

		const handleSupplierSearchUpdate = (term) => {
			if (supplierSearchTimeout) clearTimeout(supplierSearchTimeout);
			const trimmed = (term || '').trim();
			if (trimmed.length === 1) return;
			supplierSearchTimeout = setTimeout(() => fetchSuppliers(trimmed), 300);
		};

		const handleSupplierSelected = (value) => {
			if (value) {
				customerFilter.value = null;
			}
			resetAndLoad();
		};

		const loadModeOfPayments = async () => {
			try {
				const { message } = await frappe.call({
					method: 'frappe.client.get_list',
					args: {
						doctype: 'Mode of Payment',
						fields: ['name'],
						filters: { enabled: 1 },
						limit_page_length: 200,
					},
				});
				modeOfPaymentOptions.value = message || [];
			} catch (e) {
				console.error('Failed to load modes of payment', e);
			}
		};

		const clearFilters = () => {
			searchQuery.value = '';
			customerFilter.value = null;
			supplierFilter.value = null;
			paymentTypeFilter.value = null;
			fromDate.value = '';
			toDate.value = '';
			modeOfPaymentFilter.value = null;
			resetAndLoad();
		};

		const goToPage = (nextPage) => {
			if (nextPage < 1) return;
			page.value = nextPage;
			loadPayments();
		};

		const paymentTypeColor = (type) => {
			const map = { Receive: 'green', Pay: 'orange', 'Internal Transfer': 'blue' };
			return map[type] || 'grey';
		};

		const goToNew = (partyType) => {
			router.push(partyType === 'Supplier' ? '/payments/supplier' : '/payments/customer');
		};

		const openPaymentDetail = (item) => {
			router.push(`/payments/${item.name}`);
		};

		onMounted(() => {
			loadModeOfPayments();
			fetchCustomers('');
			fetchSuppliers('');
			loadPayments();
		});

		return {
			paymentList,
			listLoading,
			mineOnly,
			searchQuery,
			listHeaders,
			page,
			pageSize,
			total,
			totalPages,
			pageNumbers,
			hasMore,
			typeCounts,
			totalAmount,
			paymentTypeOptions,
			paymentTypeFilter,
			fromDate,
			toDate,
			modeOfPaymentFilter,
			modeOfPaymentOptions,
			customerFilter,
			customerSearchQuery,
			customerSearchResults,
			customerSearchLoading,
			supplierFilter,
			supplierSearchQuery,
			supplierSearchResults,
			supplierSearchLoading,
			hasActiveFilters,
			paginationLabel,
			loadPayments,
			resetAndLoad,
			handleSearchUpdate,
			handleCustomerSearchUpdate,
			handleCustomerSelected,
			handleSupplierSearchUpdate,
			handleSupplierSelected,
			clearFilters,
			goToPage,
			formatDisplayDate,
			paymentTypeColor,
			goToNew,
			openPaymentDetail,
			isSystemManager,
			canMakeSupplierPayment,
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
