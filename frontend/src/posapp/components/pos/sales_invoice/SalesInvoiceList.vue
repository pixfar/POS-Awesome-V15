<template>
	<div class="pa-0 h-100 invoice-shell pos-list-page">
		<v-card flat class="invoice-section-card pos-themed-card pos-list-card">
			<div class="pos-list-header">
				<div class="pos-list-header__main">
					<p class="pos-list-header__eyebrow">{{ __("Sales") }}</p>
					<h3 class="pos-list-header__title">{{ __("Sales Invoices") }}</h3>
					<p class="pos-list-header__subtitle">
						{{ __("Track submitted sales invoices, balances, and returns") }}
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
						{{ __("Create Invoice") }}
					</v-btn>
				</div>
			</div>

			<div class="pos-list-stats">
				<div class="pos-list-stat pos-list-stat--primary">
					<span class="pos-list-stat__label">{{ __("Total") }}</span>
					<strong class="pos-list-stat__value">{{ total }}</strong>
				</div>
				<div class="pos-list-stat pos-list-stat--success">
					<span class="pos-list-stat__label">{{ __("Paid") }}</span>
					<strong class="pos-list-stat__value">{{ paidCount }}</strong>
				</div>
				<div class="pos-list-stat pos-list-stat--warning">
					<span class="pos-list-stat__label">{{ __("Unpaid") }}</span>
					<strong class="pos-list-stat__value">{{ unpaidCount }}</strong>
				</div>
				<div class="pos-list-stat">
					<span class="pos-list-stat__label">{{ __("Returns") }}</span>
					<strong class="pos-list-stat__value">{{ returnsCount }}</strong>
				</div>
			</div>

			<div class="pos-list-toolbar">
				<v-text-field
					v-model="searchQuery"
					:label="__('Search invoice or customer')"
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
						:label="__('My Invoices')"
						@update:model-value="resetAndLoad"
					/>
					<v-btn
						variant="tonal"
						size="small"
						color="primary"
						prepend-icon="mdi-sync"
						:loading="listLoading"
						class="text-none"
						@click="loadInvoices"
					>
						{{ __("Sync") }}
					</v-btn>
				</div>
			</div>

			<div class="pos-list-filters">
				<v-select
					v-model="statusFilter"
					:items="statusOptions"
					:label="__('Status')"
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
				<v-autocomplete
					v-model="itemCodeFilter"
					v-model:search="itemSearchQuery"
					:items="itemSearchResults"
					:loading="itemSearchLoading"
					item-title="item_name"
					item-value="item_code"
					:label="__('Item')"
					density="compact"
					variant="outlined"
					hide-details
					clearable
					:custom-filter="() => true"
					class="pos-themed-input pos-list-filter-field"
					@update:search="handleItemSearchUpdate"
					@update:model-value="resetAndLoad"
				/>
				<v-select
					v-model="itemGroupFilter"
					:items="itemGroupOptions"
					item-title="name"
					item-value="name"
					:label="__('Item Group')"
					density="compact"
					variant="outlined"
					hide-details
					clearable
					class="pos-themed-input pos-list-filter-field"
					@update:model-value="resetAndLoad"
				/>
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
					@update:model-value="resetAndLoad"
				/>
				<v-select
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
				<v-text-field
					v-model="doNumberFilter"
					:label="__('DO Number')"
					density="compact"
					variant="outlined"
					hide-details
					clearable
					class="pos-themed-input pos-list-filter-field"
					@update:model-value="handleSearchUpdate"
				/>
				<v-btn variant="text" size="small" class="text-none" @click="clearFilters">
					{{ __("Clear Filters") }}
				</v-btn>
			</div>

			<div v-if="invoiceList.length" class="pos-list-table-wrap">
				<v-data-table
					:headers="listHeaders"
					:items="invoiceList"
					:loading="listLoading"
					density="comfortable"
					hide-default-footer
					:items-per-page="-1"
					class="pos-list-table sales-invoice-list-table"
					@click:row="(_, row) => openInvoiceDetail(row.item)"
				>
					<template #item.name="{ item }">
						<span class="pos-list-cell-primary">{{ item.name }}</span>
					</template>
					<template #item.posting_date="{ item }">
						<span class="pos-list-cell-muted">{{ formatDisplayDate(item.posting_date) }}</span>
					</template>
					<template #item.customer_name="{ item }">
						<span class="pos-list-cell-truncate" :title="item.customer_name || item.customer">
							{{ item.customer_name || item.customer }}
						</span>
					</template>
					<template #item.status="{ item }">
						<v-chip size="small" variant="tonal" :color="statusColor(item.status)">
							{{ item.status }}
						</v-chip>
					</template>
					<template #item.delivery_status="{ item }">
						<v-chip
							v-if="item.delivery_status"
							size="small"
							variant="tonal"
							:color="deliveryStatusColor(item.delivery_status)"
						>
							{{ item.delivery_status }}
						</v-chip>
						<span v-else class="pos-list-cell-muted">—</span>
					</template>
					<template #item.custom_do_number="{ item }">
						<span v-if="item.custom_do_number" class="pos-list-cell-muted">{{ item.custom_do_number }}</span>
						<span v-else class="pos-list-cell-muted">—</span>
					</template>
					<template #item.grand_total="{ item }">
						<span class="pos-list-cell-primary">
							{{ currencySymbol(item.currency) }}{{ formatCurrency(item.grand_total) }}
						</span>
					</template>
					<template #item.outstanding_amount="{ item }">
						<span
							:class="
								item.outstanding_amount > 0
									? 'pos-list-cell-primary text-warning'
									: 'pos-list-cell-muted'
							"
						>
							{{ currencySymbol(item.currency) }}{{ formatCurrency(item.outstanding_amount) }}
						</span>
					</template>
					<template #item.actions="{ item }">
						<div class="d-flex justify-end">
							<v-menu :close-on-content-click="true" location="bottom end">
								<template #activator="{ props }">
									<v-btn
										v-bind="props"
										icon
										size="small"
										variant="text"
										class="pos-list-row-actions-btn"
										:loading="actionLoadingName === item.name"
										:aria-label="__('Actions')"
										:title="__('Actions')"
										@click.stop
									>
										<v-icon>mdi-dots-vertical</v-icon>
									</v-btn>
								</template>
								<v-list density="compact" min-width="190">
									<v-list-item @click="openInvoiceDetail(item)">
										<template #prepend>
											<v-icon size="18">mdi-eye-outline</v-icon>
										</template>
										<v-list-item-title>{{ __("View") }}</v-list-item-title>
									</v-list-item>
									<v-list-item @click="printInvoice(item, 'BSP Sales Invoice')">
										<template #prepend>
											<v-icon size="18">mdi-printer-outline</v-icon>
										</template>
										<v-list-item-title>{{ __("Print") }}</v-list-item-title>
									</v-list-item>
									<v-list-item @click="printInvoice(item, 'BSP Sales Invoice For Agent')">
										<template #prepend>
											<v-icon size="18">mdi-printer-outline</v-icon>
										</template>
										<v-list-item-title>{{ __("Print (For Agent)") }}</v-list-item-title>
									</v-list-item>
									<v-list-item v-if="canReturn(item)" @click="openReturnConfirm(item)">
										<template #prepend>
											<v-icon size="18" color="blue">mdi-keyboard-return</v-icon>
										</template>
										<v-list-item-title>{{ __("Sales Return") }}</v-list-item-title>
									</v-list-item>
									<v-list-item v-if="canDeliver(item)" @click="openDeliveryDialog(item)">
										<template #prepend>
											<v-icon size="18" color="teal">mdi-truck-delivery-outline</v-icon>
										</template>
										<v-list-item-title>{{ __("Create Delivery") }}</v-list-item-title>
									</v-list-item>
									<v-list-item v-if="canCancel(item)" @click="openCancelConfirm(item)">
										<template #prepend>
											<v-icon size="18" color="error">mdi-cancel</v-icon>
										</template>
										<v-list-item-title>{{ __("Cancel") }}</v-list-item-title>
									</v-list-item>
									<v-list-item v-if="canDelete(item)" @click="openDeleteConfirm(item)">
										<template #prepend>
											<v-icon size="18" color="error">mdi-delete-outline</v-icon>
										</template>
										<v-list-item-title>{{ __("Delete") }}</v-list-item-title>
									</v-list-item>
								</v-list>
							</v-menu>
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
				<v-icon size="48" color="primary" class="pos-list-empty__icon">mdi-receipt-text-outline</v-icon>
				<h4 class="pos-list-empty__title">{{ __("No sales invoices found") }}</h4>
				<p class="pos-list-empty__subtitle">
					{{ hasActiveFilters
						? __("Try different filters or clear them.")
						: __("Create a new invoice to see it listed here.") }}
				</p>
				<v-btn
					v-if="!hasActiveFilters"
					color="primary"
					variant="flat"
					class="text-none mt-2"
					prepend-icon="mdi-plus"
					@click="goToNew"
				>
					{{ __("Create Invoice") }}
				</v-btn>
			</div>

			<div v-else class="pos-list-empty">
				<v-progress-circular indeterminate color="primary" />
			</div>
		</v-card>

		<v-dialog v-model="confirmDialog" max-width="420">
			<v-card class="pos-themed-card">
				<v-card-title class="d-flex align-center gap-2">
					<v-icon :color="confirmDialogColor">mdi-alert-circle-outline</v-icon>
					<span>{{ confirmDialogTitle }}</span>
				</v-card-title>
				<v-card-text>{{ confirmDialogMessage }}</v-card-text>
				<v-card-actions>
					<v-spacer />
					<v-btn variant="text" @click="confirmDialog = false">{{ __("Cancel") }}</v-btn>
					<v-btn
						:color="confirmDialogColor"
						variant="flat"
						:loading="actionLoadingName === confirmDialogItem?.name"
						@click="runConfirmedAction"
					>
						{{ confirmDialogActionLabel }}
					</v-btn>
				</v-card-actions>
			</v-card>
		</v-dialog>

		<ReturnItemsDialog
			v-model="returnDialogOpen"
			:invoice="returnDialogItem"
			:doctype="returnDialogItem?.doctype || 'Sales Invoice'"
			:pos-profile="uiStore.posProfile?.name"
			return-method="posawesome.posawesome.api.invoices.create_sales_return"
			@returned="onInvoiceReturned"
			@error="onReturnError"
		/>

		<DeliveryReceiptDialog
			v-model="deliveryDialogOpen"
			:invoice="deliveryDialogItem"
			doctype="Sales Invoice"
			load-method="posawesome.posawesome.api.invoice_processing.fulfillment.get_sales_invoice_for_delivery"
			submit-method="posawesome.posawesome.api.invoices.create_sales_delivery"
			:title="__('Create Delivery')"
			:submit-label="__('Create Delivery Note')"
			:empty-message="__('Nothing left to deliver on this invoice.')"
			icon="mdi-truck-delivery-outline"
			color="teal"
			@created="onInvoiceDelivered"
			@error="onDeliveryError"
		/>
	</div>
</template>

<script>
import { ref, computed, onMounted, watch } from 'vue';
import { useRouter } from 'vue-router';
import format from '../../../format';
import { useUIStore } from '../../../stores/uiStore.js';
import { useToastStore } from '../../../stores/toastStore';
import { ensurePosProfile } from '../../../../utils/pos_profile';
import DateFilterField from '../shared/DateFilterField.vue';
import ReturnItemsDialog from '../shared/ReturnItemsDialog.vue';
import DeliveryReceiptDialog from '../shared/DeliveryReceiptDialog.vue';
import { openDocumentPdfPrint } from '../../../utils/openDocumentPdfPrint';
import { openDocumentPrintView } from '../../../utils/openDocumentPrintView';

const UNPAID_STATUSES = [
	'Unpaid',
	'Unpaid and Discounted',
	'Partly Paid',
	'Partly Paid and Discounted',
	'Overdue',
	'Overdue and Discounted',
];
const RETURN_STATUSES = ['Return', 'Credit Note Issued'];

export default {
	name: 'SalesInvoiceList',
	components: { DateFilterField, ReturnItemsDialog, DeliveryReceiptDialog },
	mixins: [format],
	setup() {
		const router = useRouter();
		const uiStore = useUIStore();
		const toastStore = useToastStore();

		const isSystemManager = computed(() =>
			(frappe?.boot?.user?.roles || []).includes('System Manager'),
		);

		const NON_CANCELLABLE_STATUSES = ['Draft', 'Cancelled'];
		const canReturn = (item) =>
			!item.is_return && !NON_CANCELLABLE_STATUSES.includes(item.status);
		const canCancel = (item) =>
			isSystemManager.value && !NON_CANCELLABLE_STATUSES.includes(item.status);
		const canDelete = (item) => item.status === 'Cancelled';
		const canDeliver = (item) =>
			item.delivery_status === 'Not Delivered' || item.delivery_status === 'Partly Delivered';

		const deliveryDialogOpen = ref(false);
		const deliveryDialogItem = ref(null);

		const openDeliveryDialog = (item) => {
			deliveryDialogItem.value = item;
			deliveryDialogOpen.value = true;
		};

		const onInvoiceDelivered = async (result) => {
			toastStore.show({
				title: __('Delivery Note {0} created', [result?.name]),
				color: 'success',
			});
			await loadInvoices();
		};

		const onDeliveryError = (message) => {
			toastStore.show({
				title: message || __('Action failed'),
				color: 'error',
			});
		};

		const deliveryStatusColor = (status) => {
			const map = {
				'Not Delivered': 'grey',
				'Partly Delivered': 'orange',
				Delivered: 'green',
			};
			return map[status] || 'grey';
		};

		const actionLoadingName = ref(null);
		const confirmDialog = ref(false);
		const confirmDialogItem = ref(null);
		const confirmDialogAction = ref(null);
		const confirmDialogTitle = ref('');
		const confirmDialogMessage = ref('');
		const confirmDialogActionLabel = ref('');
		const confirmDialogColor = ref('error');

		const returnDialogOpen = ref(false);
		const returnDialogItem = ref(null);

		const openReturnConfirm = (item) => {
			returnDialogItem.value = item;
			returnDialogOpen.value = true;
		};

		const onInvoiceReturned = async (result) => {
			toastStore.show({
				title: __('Return {0} created', [result?.name]),
				color: 'success',
			});
			await loadInvoices();
		};

		const onReturnError = (message) => {
			toastStore.show({
				title: message || __('Action failed'),
				color: 'error',
			});
		};

		const openCancelConfirm = (item) => {
			confirmDialogItem.value = item;
			confirmDialogAction.value = 'cancel';
			confirmDialogTitle.value = __('Cancel Sales Invoice');
			confirmDialogMessage.value = __(
				'This will cancel {0} and reverse its stock, payment, and accounting entries. This cannot be undone. Continue?',
				[item.name],
			);
			confirmDialogActionLabel.value = __('Cancel Invoice');
			confirmDialogColor.value = 'error';
			confirmDialog.value = true;
		};

		const openDeleteConfirm = (item) => {
			confirmDialogItem.value = item;
			confirmDialogAction.value = 'delete';
			confirmDialogTitle.value = __('Delete Sales Invoice');
			confirmDialogMessage.value = __(
				'This will permanently delete cancelled invoice {0}. This cannot be undone. Continue?',
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
						method: 'posawesome.posawesome.api.invoices.cancel_sales_invoice',
						args: { invoice: item.name, doctype: item.doctype || 'Sales Invoice' },
					});
					toastStore.show({ title: __('{0} cancelled', [item.name]), color: 'success' });
				} else if (action === 'delete') {
					await frappe.call({
						method: 'posawesome.posawesome.api.invoices.delete_cancelled_sales_invoice',
						args: { invoice: item.name, doctype: item.doctype || 'Sales Invoice' },
					});
					toastStore.show({ title: __('{0} deleted', [item.name]), color: 'success' });
				}
				confirmDialog.value = false;
				await loadInvoices();
			} catch (e) {
				toastStore.show({
					title: e?.message || __('Action failed'),
					color: 'error',
				});
			} finally {
				actionLoadingName.value = null;
			}
		};
		const invoiceList = ref([]);
		const listLoading = ref(false);
		const mineOnly = ref(false);
		const searchQuery = ref('');
		let searchTimeout = null;

		const page = ref(1);
		const pageSize = ref(20);
		const total = ref(0);
		const totalPages = computed(() => Math.max(1, Math.ceil(total.value / (pageSize.value || 1))));
		const hasMore = ref(false);
		const statusCounts = ref({});

		const statusOptions = [
			'Draft',
			'Unpaid',
			'Unpaid and Discounted',
			'Partly Paid',
			'Partly Paid and Discounted',
			'Overdue',
			'Overdue and Discounted',
			'Paid',
			'Return',
			'Credit Note Issued',
			'Cancelled',
		];
		const statusFilter = ref(null);
		const fromDate = ref('');
		const toDate = ref('');
		const itemCodeFilter = ref(null);
		const itemGroupFilter = ref(null);
		const customerFilter = ref(null);
		const warehouseFilter = ref(null);
		const warehouseOptions = ref([]);
		const doNumberFilter = ref('');

		const itemSearchQuery = ref('');
		const itemSearchResults = ref([]);
		const itemSearchLoading = ref(false);
		let itemSearchTimeout = null;

		const customerSearchQuery = ref('');
		const customerSearchResults = ref([]);
		const customerSearchLoading = ref(false);
		let customerSearchTimeout = null;

		const itemGroupOptions = ref([]);

		const listHeaders = [
			{ title: __('Invoice'), key: 'name', sortable: true },
			{ title: __('Date'), key: 'posting_date', sortable: true },
			{ title: __('Customer'), key: 'customer_name', sortable: true },
			{ title: __('Status'), key: 'status', sortable: true },
			{ title: __('Delivery Status'), key: 'delivery_status', sortable: true },
			{ title: __('DO Number'), key: 'custom_do_number', sortable: true },
			{ title: __('Total'), key: 'grand_total', sortable: true, align: 'end' },
			{ title: __('Outstanding'), key: 'outstanding_amount', sortable: true, align: 'end' },
			{ title: __('Actions'), key: 'actions', sortable: false, align: 'end', width: '120px' },
		];

		const hasActiveFilters = computed(() =>
			Boolean(
				searchQuery.value ||
					statusFilter.value ||
					fromDate.value ||
					toDate.value ||
					itemCodeFilter.value ||
					itemGroupFilter.value ||
					customerFilter.value ||
					warehouseFilter.value ||
					doNumberFilter.value,
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

		const paidCount = computed(() => statusCounts.value['Paid'] || 0);
		const unpaidCount = computed(() =>
			UNPAID_STATUSES.reduce((sum, key) => sum + (statusCounts.value[key] || 0), 0),
		);
		const returnsCount = computed(() =>
			RETURN_STATUSES.reduce((sum, key) => sum + (statusCounts.value[key] || 0), 0),
		);

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

		const loadInvoices = async () => {
			const posProfile = await resolvePosProfile();
			if (!posProfile?.name) {
				invoiceList.value = [];
				return;
			}
			listLoading.value = true;
			try {
				const { message } = await frappe.call({
					method: 'posawesome.posawesome.api.invoices.get_sales_invoices_list',
					args: {
						pos_profile: posProfile.name,
						page_start: (page.value - 1) * pageSize.value,
						page_length: pageSize.value,
						mine_only: mineOnly.value ? 1 : 0,
						status: statusFilter.value || undefined,
						from_date: fromDate.value || undefined,
						to_date: toDate.value || undefined,
						item_code: itemCodeFilter.value || undefined,
						item_group: itemGroupFilter.value || undefined,
						customer: customerFilter.value || undefined,
						warehouse: warehouseFilter.value || undefined,
						do_number: doNumberFilter.value || undefined,
						search: searchQuery.value || undefined,
					},
				});
				invoiceList.value = message?.invoices || [];
				total.value = message?.total || 0;
				hasMore.value = Boolean(message?.has_more);
				statusCounts.value = message?.status_counts || {};
			} catch (e) {
				console.error('Failed to load sales invoices', e);
				invoiceList.value = [];
			} finally {
				listLoading.value = false;
			}
		};

		const resetAndLoad = () => {
			page.value = 1;
			loadInvoices();
		};

		const handleSearchUpdate = () => {
			if (searchTimeout) clearTimeout(searchTimeout);
			searchTimeout = setTimeout(resetAndLoad, 300);
		};

		const handleItemSearchUpdate = (term) => {
			if (itemSearchTimeout) clearTimeout(itemSearchTimeout);
			if (!term || term.trim().length < 2) {
				itemSearchResults.value = [];
				return;
			}
			itemSearchTimeout = setTimeout(async () => {
				itemSearchLoading.value = true;
				try {
					const { message } = await frappe.call({
						method: 'posawesome.posawesome.api.invoices.search_items',
						args: { search_text: term.trim(), limit: 20 },
					});
					itemSearchResults.value = message || [];
				} catch {
					itemSearchResults.value = [];
				} finally {
					itemSearchLoading.value = false;
				}
			}, 300);
		};

		const handleCustomerSearchUpdate = (term) => {
			if (customerSearchTimeout) clearTimeout(customerSearchTimeout);
			const posProfile = uiStore.posProfile;
			if (!term || term.trim().length < 2 || !posProfile?.name) {
				customerSearchResults.value = [];
				return;
			}
			customerSearchTimeout = setTimeout(async () => {
				customerSearchLoading.value = true;
				try {
					const { message } = await frappe.call({
						method: 'posawesome.posawesome.api.customers.search_customers',
						args: { pos_profile: JSON.stringify(posProfile), search_text: term.trim(), limit: 20 },
					});
					customerSearchResults.value = message || [];
				} catch {
					customerSearchResults.value = [];
				} finally {
					customerSearchLoading.value = false;
				}
			}, 300);
		};

		const loadItemGroups = async () => {
			try {
				const { message } = await frappe.call({
					method: 'frappe.client.get_list',
					args: {
						doctype: 'Item Group',
						fields: ['name'],
						filters: { is_group: 0 },
						limit_page_length: 200,
					},
				});
				itemGroupOptions.value = message || [];
			} catch (e) {
				console.error('Failed to load item groups', e);
			}
		};

		const loadWarehouses = async () => {
			try {
				const { message } = await frappe.call({
					method: 'frappe.client.get_list',
					args: {
						doctype: 'Warehouse',
						fields: ['name', 'warehouse_name'],
						filters: { is_group: 0, disabled: 0 },
						limit_page_length: 200,
					},
				});
				warehouseOptions.value = message || [];
			} catch (e) {
				console.error('Failed to load warehouses', e);
			}
		};

		const clearFilters = () => {
			searchQuery.value = '';
			statusFilter.value = null;
			fromDate.value = '';
			toDate.value = '';
			itemCodeFilter.value = null;
			itemGroupFilter.value = null;
			customerFilter.value = null;
			warehouseFilter.value = null;
			doNumberFilter.value = '';
			resetAndLoad();
		};

		const goToPage = (nextPage) => {
			if (nextPage < 1) return;
			page.value = nextPage;
			loadInvoices();
		};

		const statusColor = (status) => {
			const map = {
				Draft: 'grey',
				Unpaid: 'orange',
				'Unpaid and Discounted': 'orange',
				'Partly Paid': 'orange',
				'Partly Paid and Discounted': 'orange',
				Overdue: 'red',
				'Overdue and Discounted': 'red',
				Paid: 'green',
				Return: 'blue',
				'Credit Note Issued': 'blue',
				Cancelled: 'red',
			};
			return map[status] || 'grey';
		};

		const goToNew = () => {
			router.push('/sales-invoices/new');
		};

		const openInvoiceDetail = (item) => {
			router.push({
				path: `/sales-invoices/${item.name}`,
				query: { doctype: item.doctype || 'Sales Invoice' },
			});
		};

		const printInvoice = async (item, printFormat) => {
			const doctype = item.doctype || 'Sales Invoice';
			actionLoadingName.value = item.name;
			try {
				await openDocumentPdfPrint({
					doctype,
					name: item.name,
					printFormat,
					noLetterhead: 1,
					autoPrint: false,
				});
			} catch (e) {
				console.warn('PDF print failed, falling back to printview', e);
				openDocumentPrintView(doctype, item.name, printFormat);
			} finally {
				actionLoadingName.value = null;
			}
		};

		onMounted(() => {
			loadItemGroups();
			loadWarehouses();
			loadInvoices();
		});

		// The POS profile is hydrated asynchronously by the app shell after mount —
		// retry once it becomes available instead of leaving the list stuck empty.
		watch(
			() => uiStore.posProfile?.name,
			(profileName, previousProfileName) => {
				if (profileName && profileName !== previousProfileName) {
					resetAndLoad();
				}
			},
		);

		return {
			invoiceList,
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
			statusOptions,
			statusFilter,
			fromDate,
			toDate,
			itemCodeFilter,
			itemGroupFilter,
			itemGroupOptions,
			customerFilter,
			warehouseFilter,
			warehouseOptions,
			doNumberFilter,
			itemSearchQuery,
			itemSearchResults,
			itemSearchLoading,
			customerSearchQuery,
			customerSearchResults,
			customerSearchLoading,
			hasActiveFilters,
			paginationLabel,
			paidCount,
			unpaidCount,
			returnsCount,
			loadInvoices,
			resetAndLoad,
			handleSearchUpdate,
			handleItemSearchUpdate,
			handleCustomerSearchUpdate,
			clearFilters,
			goToPage,
			formatDisplayDate,
			statusColor,
			goToNew,
			openInvoiceDetail,
			printInvoice,
			isSystemManager,
			canReturn,
			canCancel,
			canDelete,
			canDeliver,
			deliveryStatusColor,
			deliveryDialogOpen,
			deliveryDialogItem,
			openDeliveryDialog,
			onInvoiceDelivered,
			onDeliveryError,
			actionLoadingName,
			confirmDialog,
			confirmDialogItem,
			confirmDialogTitle,
			confirmDialogMessage,
			confirmDialogActionLabel,
			confirmDialogColor,
			openReturnConfirm,
			openCancelConfirm,
			openDeleteConfirm,
			runConfirmedAction,
			returnDialogOpen,
			returnDialogItem,
			onInvoiceReturned,
			onReturnError,
			uiStore,
		};
	},
};
</script>

<style scoped>
@import '../invoice-shared-styles.css';
</style>
