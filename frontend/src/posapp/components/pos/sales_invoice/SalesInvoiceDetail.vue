<template>
	<DocumentDetailView
		:eyebrow="__('Sales')"
		:title="name"
		:subtitle="__('Sales Invoice')"
		:loading="loading"
		:not-found="notFound"
		:status="detail.status"
		:status-color="statusColor(detail.status)"
		:meta-fields="metaFields"
		:item-columns="itemColumns"
		:items="itemRows"
		:totals="totals"
		:actions="actions"
		@back="goBack"
	/>
</template>

<script>
import { ref, computed, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import format from '../../../format';
import { openDocumentPdfPrint } from '../../../utils/openDocumentPdfPrint';
import { openDocumentPrintView } from '../../../utils/openDocumentPrintView';

import DocumentDetailView from '../shared/DocumentDetailView.vue';

// "BSP Sales Invoice" is the default (listed first); "BSP Sales Invoice For
// Agent" is the only other format staff pick from when printing/reprinting
// a Sales Invoice from this detail page.
const SALES_PRINT_FORMATS = ['BSP Sales Invoice', 'BSP Sales Invoice For Agent'];

export default {
	name: 'SalesInvoiceDetail',
	components: { DocumentDetailView },
	mixins: [format],
	setup() {
		const route = useRoute();
		const router = useRouter();
		const name = route.params.name;
		const doctype = route.query.doctype || 'Sales Invoice';

		const loading = ref(true);
		const notFound = ref(false);
		const detail = ref({});

		const formatDisplayDate = (value) => {
			if (!value) return '—';
			const parts = String(value).split('-');
			return parts.length === 3 ? `${parts[2]}-${parts[1]}-${parts[0]}` : value;
		};

		return {
			name,
			doctype,
			loading,
			notFound,
			detail,
			formatDisplayDate,
			route,
			router,
		};
	},
	computed: {
		metaFields() {
			const fields = [
				{
					label: this.__('Date'),
					value: `${this.formatDisplayDate(this.detail.posting_date)} ${this.detail.posting_time || ''}`.trim(),
				},
				{ label: this.__('Customer'), value: this.detail.customer_name || this.detail.customer },
				{ label: this.__('Currency'), value: this.detail.currency },
				{
					label: this.__('Return'),
					value: this.detail.is_return ? this.__('Yes') : this.__('No'),
				},
				{ label: this.__('POS Profile'), value: this.detail.pos_profile },
				{ label: this.__('Cashier'), value: this.detail.owner },
				{ label: this.__('Warehouse'), value: this.detail.warehouse },
				{ label: this.__('Territory'), value: this.detail.territory },
			];
			if (this.detail.is_return && this.detail.return_against) {
				fields.push({ label: this.__('Return Against'), value: this.detail.return_against });
			}
			if (this.detail.custom_do_number) {
				fields.push({ label: this.__('DO Number'), value: this.detail.custom_do_number });
			}
			if (this.detail.remarks) {
				fields.push({ label: this.__('Remarks'), value: this.detail.remarks });
			}
			return fields;
		},
		itemColumns() {
			return [
				{ key: 'item_code', label: this.__('Item Code') },
				{ key: 'item_name', label: this.__('Item Name') },
				{ key: 'warehouse', label: this.__('Warehouse') },
				{ key: 'qty', label: this.__('Qty'), align: 'end' },
				{ key: 'weight', label: this.__('Weight'), align: 'end' },
				{ key: 'uom', label: this.__('UOM') },
				{ key: 'rate', label: this.__('Rate'), align: 'end' },
				{ key: 'amount', label: this.__('Amount'), align: 'end' },
			];
		},
		itemRows() {
			const symbol = this.currencySymbol(this.detail.currency);
			return (this.detail.items || []).map((row) => ({
				...row,
				rate: `${symbol}${this.formatCurrency(row.rate)}`,
				amount: `${symbol}${this.formatCurrency(row.amount)}`,
			}));
		},
		totals() {
			const symbol = this.currencySymbol(this.detail.currency);
			const money = (val) => `${symbol}${this.formatCurrency(val)}`;
			const rows = [
				{ label: this.__('Net Total'), value: money(this.detail.net_total) },
				{ label: this.__('Total Weight'), value: Number(this.detail.total_weight || 0).toFixed(2) },
			];
			if (this.detail.discount_amount) {
				rows.push({ label: this.__('Discount'), value: money(this.detail.discount_amount) });
			}
			rows.push(
				{ label: this.__('Grand Total'), value: money(this.detail.grand_total) },
				{ label: this.__('Paid Amount'), value: money(this.detail.paid_amount) },
				{ label: this.__('Outstanding'), value: money(this.detail.outstanding_amount) },
			);
			if (this.detail.change_amount) {
				rows.push({ label: this.__('Change'), value: money(this.detail.change_amount) });
			}
			(this.detail.payments || []).forEach((payment) => {
				rows.push({
					label: this.__('Paid via {0}', [payment.mode_of_payment]),
					value: money(payment.amount),
				});
			});
			(this.detail.taxes || []).forEach((tax) => {
				rows.push({ label: tax.description, value: money(tax.tax_amount) });
			});
			return rows;
		},
		actions() {
			return [
				{
					label: this.__('Print'),
					color: 'primary',
					menuItems: SALES_PRINT_FORMATS.map((printFormat) => ({
						label: printFormat,
						onClick: () => this.printDocument(printFormat),
					})),
				},
			];
		},
	},
	mounted() {
		this.loadDetail();
	},
	methods: {
		statusColor(status) {
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
		},
		async loadDetail() {
			this.loading = true;
			this.notFound = false;
			try {
				const { message } = await frappe.call({
					method: 'posawesome.posawesome.api.invoices.get_sales_invoice_detail',
					args: { name: this.name, doctype: this.doctype },
				});
				if (!message) {
					this.notFound = true;
				} else {
					this.detail = message;
				}
			} catch (e) {
				this.notFound = true;
			} finally {
				this.loading = false;
			}
		},
		goBack() {
			this.router.push('/sales-invoices/list');
		},
		async printDocument(printFormat) {
			try {
				await openDocumentPdfPrint({
					doctype: this.doctype,
					name: this.name,
					printFormat,
					noLetterhead: 1,
					autoPrint: false,
				});
			} catch (error) {
				console.warn('PDF print failed, falling back to printview', error);
				openDocumentPrintView(this.doctype, this.name, printFormat);
			}
		},
	},
};
</script>
