<template>
	<DocumentDetailView
		:eyebrow="__('Purchase')"
		:title="name"
		:subtitle="__('Purchase Invoice')"
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
import { ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import format from '../../../format';
import { openDocumentPdfPrint } from '../../../utils/openDocumentPdfPrint';
import { openDocumentPrintView } from '../../../utils/openDocumentPrintView';

import DocumentDetailView from '../shared/DocumentDetailView.vue';

export default {
	name: 'PurchaseInvoiceDetail',
	components: { DocumentDetailView },
	mixins: [format],
	setup() {
		const route = useRoute();
		const router = useRouter();
		const name = route.params.name;

		const loading = ref(true);
		const notFound = ref(false);
		const detail = ref({});

		return { name, loading, notFound, detail, router };
	},
	computed: {
		metaFields() {
			const fields = [
				{
					label: this.__('Date'),
					value: `${this.formatDisplayDate(this.detail.posting_date)} ${this.detail.posting_time || ''}`.trim(),
				},
				{ label: this.__('Supplier'), value: this.detail.supplier_name || this.detail.supplier },
				{ label: this.__('Currency'), value: this.detail.currency },
				{ label: this.__('Due Date'), value: this.formatDisplayDate(this.detail.due_date) },
				{ label: this.__('Warehouse'), value: this.detail.warehouse },
				{ label: this.__('Territory'), value: this.detail.territory },
				{
					label: this.__('Update Stock'),
					value: this.detail.update_stock ? this.__('Yes') : this.__('No'),
				},
				{ label: this.__('Created By'), value: this.detail.owner },
			];
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
			const rows = [{ label: this.__('Net Total'), value: money(this.detail.net_total) }];
			if (this.detail.discount_amount) {
				rows.push({ label: this.__('Discount'), value: money(this.detail.discount_amount) });
			}
			rows.push(
				{ label: this.__('Grand Total'), value: money(this.detail.grand_total) },
				{ label: this.__('Paid Amount'), value: money(this.detail.paid_amount) },
				{ label: this.__('Outstanding'), value: money(this.detail.outstanding_amount) },
			);
			(this.detail.taxes || []).forEach((tax) => {
				rows.push({ label: tax.description, value: money(tax.tax_amount) });
			});
			return rows;
		},
		actions() {
			return [{ label: this.__('Print'), color: 'primary', onClick: () => this.printDocument() }];
		},
	},
	mounted() {
		this.loadDetail();
	},
	methods: {
		formatDisplayDate(value) {
			if (!value) return '—';
			const parts = String(value).split('-');
			return parts.length === 3 ? `${parts[2]}-${parts[1]}-${parts[0]}` : value;
		},
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
				'Debit Note Issued': 'blue',
				Cancelled: 'red',
			};
			return map[status] || 'grey';
		},
		async loadDetail() {
			this.loading = true;
			this.notFound = false;
			try {
				const { message } = await frappe.call({
					method: 'posawesome.posawesome.api.purchase_invoices.get_purchase_invoice_detail',
					args: { name: this.name },
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
			this.router.push('/purchase-invoices/list');
		},
		async printDocument() {
			try {
				await openDocumentPdfPrint({
					doctype: 'Purchase Invoice',
					name: this.name,
					noLetterhead: 1,
					autoPrint: false,
				});
			} catch (error) {
				console.warn('PDF print failed, falling back to printview', error);
				openDocumentPrintView('Purchase Invoice', this.name);
			}
		},
	},
};
</script>
