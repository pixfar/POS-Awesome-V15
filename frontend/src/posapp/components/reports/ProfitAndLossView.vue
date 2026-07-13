<template>
	<div class="pa-0 h-100 invoice-shell pos-list-page">
		<v-card flat class="invoice-section-card pos-themed-card pos-list-card">
			<div class="pos-list-header">
				<div class="pos-list-header__main">
					<p class="pos-list-header__eyebrow">{{ __('Financial Statements') }}</p>
					<h3 class="pos-list-header__title">{{ __('Profit and Loss Statement') }}</h3>
					<p class="pos-list-header__subtitle">
						{{ companyLabel }}<template v-if="periodLabel"> &middot; {{ periodLabel }}</template>
					</p>
				</div>
				<div class="pos-list-header__actions">
					<v-btn
						variant="tonal"
						size="small"
						class="text-none"
						prepend-icon="mdi-arrow-left"
						@click="goBack"
					>
						{{ __('Back to Reports') }}
					</v-btn>
					<v-btn
						v-if="hasAccess"
						variant="tonal"
						size="small"
						class="text-none"
						:prepend-icon="allCollapsed ? 'mdi-arrow-expand' : 'mdi-arrow-collapse'"
						@click="toggleCollapseAll"
					>
						{{ allCollapsed ? __('Expand All') : __('Collapse All') }}
					</v-btn>
					<v-btn
						v-if="hasAccess"
						variant="tonal"
						size="small"
						color="primary"
						class="text-none"
						prepend-icon="mdi-refresh"
						:loading="loading"
						@click="loadReport"
					>
						{{ __('Refresh') }}
					</v-btn>
				</div>
			</div>

			<div v-if="!hasAccess" class="pl-state">
				<v-alert type="warning" variant="tonal" density="comfortable">
					{{ __('You need the System Manager role to view financial statements.') }}
				</v-alert>
			</div>

			<template v-else>
				<div v-if="loading" class="pl-state">
					<v-progress-circular indeterminate color="primary" />
				</div>

				<div v-else-if="error" class="pl-state">
					<v-alert type="error" variant="tonal" density="comfortable">
						{{ error }}
					</v-alert>
				</div>

				<template v-else>
					<div class="pos-list-stats">
						<div class="pos-list-stat pos-list-stat--success">
							<span class="pos-list-stat__label">{{ __('Total Income') }}</span>
							<strong class="pos-list-stat__value">{{ summary.incomeFormatted }}</strong>
						</div>
						<div class="pos-list-stat pos-list-stat--danger">
							<span class="pos-list-stat__label">{{ __('Total Expense') }}</span>
							<strong class="pos-list-stat__value">{{ summary.expenseFormatted }}</strong>
						</div>
						<div
							class="pos-list-stat"
							:class="summary.profit < 0 ? 'pos-list-stat--danger' : 'pos-list-stat--primary'"
						>
							<span class="pos-list-stat__label">{{ __('Profit / Loss') }}</span>
							<strong class="pos-list-stat__value">{{ summary.profitFormatted }}</strong>
						</div>
					</div>

					<div class="pl-tree">
						<div class="pl-tree__header">
							<span class="pl-tree__header-label">{{ __('Account') }}</span>
							<span class="pl-tree__header-value">{{ periodLabel }}</span>
						</div>
						<div v-if="!tree.length" class="pl-state">
							<v-alert type="info" variant="tonal" density="comfortable">
								{{ __('No data found for this period.') }}
							</v-alert>
						</div>
						<ProfitAndLossRow v-for="node in tree" :key="node.id" :node="node" />
					</div>
				</template>
			</template>
		</v-card>
	</div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import ProfitAndLossRow from './ProfitAndLossRow.vue';

const __ = window.__ || ((text) => text);
const router = useRouter();

const REPORT_NAME = 'Profit and Loss Statement';

const loading = ref(false);
const error = ref(null);
const tree = ref([]);
const periodLabel = ref('');
const companyLabel = ref('');
const allCollapsed = ref(false);

const hasAccess = computed(() => {
	const roles = frappe?.boot?.user?.roles || [];
	return roles.includes('System Manager');
});

const summary = computed(() => {
	const roots = tree.value;
	const groupRoots = roots.filter((node) => node.is_group);
	// Structural rather than text-based lookup: the report always emits the
	// Income tree first, then Expenses, then standalone total/profit rows --
	// so the last non-group root is always the Profit/Loss line, regardless
	// of language/translation of its label.
	const totalRoots = roots.filter((node) => !node.is_group);
	const income = groupRoots[0]?.value || 0;
	const expense = groupRoots[1]?.value || 0;
	const profit = totalRoots.length ? totalRoots[totalRoots.length - 1].value : income - expense;
	const currency = groupRoots[0]?.currency;

	return {
		income,
		expense,
		profit,
		incomeFormatted: formatAmount(income, currency),
		expenseFormatted: formatAmount(expense, currency),
		profitFormatted: formatAmount(profit, currency),
	};
});

function goBack() {
	router.push('/reports');
}

function formatAmount(value, currency) {
	try {
		return format_currency(value, currency);
	} catch (e) {
		return String(value);
	}
}

function getValueColumn(columns) {
	return (columns || []).find(
		(col) => col.fieldname !== 'account' && col.fieldname !== 'currency' && col.fieldname !== 'total'
	);
}

function buildTree(rows, columns) {
	const valueColumn = getValueColumn(columns);
	const valueFieldname = valueColumn ? valueColumn.fieldname : null;

	const roots = [];
	const stack = [];
	let counter = 0;

	for (const row of rows || []) {
		if (!row || !row.account) continue;

		const value = Number(valueFieldname ? row[valueFieldname] : 0) || 0;
		const label = String(row.account_name || row.account).replace(/^'+|'+$/g, '');
		const indent = Number(row.indent) || 0;

		const node = reactive({
			id: `pl-node-${counter++}`,
			label,
			value,
			currency: row.currency,
			formattedValue: formatAmount(value, row.currency),
			indent,
			is_group: !!row.is_group,
			isTotal: row.is_group === undefined,
			expanded: true,
			children: [],
		});

		while (stack.length && stack[stack.length - 1].indent >= indent) {
			stack.pop();
		}
		if (stack.length) {
			stack[stack.length - 1].children.push(node);
		} else {
			roots.push(node);
		}
		stack.push(node);
	}

	return roots;
}

function setExpandedRecursive(nodes, expanded) {
	for (const node of nodes) {
		node.expanded = expanded;
		if (node.children.length) setExpandedRecursive(node.children, expanded);
	}
}

function toggleCollapseAll() {
	allCollapsed.value = !allCollapsed.value;
	setExpandedRecursive(tree.value, !allCollapsed.value);
}

async function loadReport() {
	loading.value = true;
	error.value = null;
	try {
		const fiscalYear = frappe?.boot?.current_fiscal_year;
		const [fiscalYearName] = fiscalYear || [];
		const company = frappe?.defaults?.get_user_default?.('Company') || '';
		companyLabel.value = company;

		const r = await frappe.call({
			method: 'frappe.desk.query_report.run',
			args: {
				report_name: REPORT_NAME,
				filters: {
					company,
					filter_based_on: 'Fiscal Year',
					from_fiscal_year: fiscalYearName,
					to_fiscal_year: fiscalYearName,
					periodicity: 'Yearly',
					include_default_book_entries: 1,
					selected_view: 'Report',
				},
			},
		});

		const message = r.message || {};
		const valueColumn = getValueColumn(message.columns);
		periodLabel.value = valueColumn ? valueColumn.label : '';
		tree.value = buildTree(message.result, message.columns);
		allCollapsed.value = false;
	} catch (e) {
		error.value = e?.message || __('Failed to load the report.');
	} finally {
		loading.value = false;
	}
}

onMounted(() => {
	if (hasAccess.value) {
		loadReport();
	}
});
</script>

<style scoped>
@import '../pos/invoice-shared-styles.css';

.pl-state {
	padding: 24px;
	display: flex;
	justify-content: center;
}

.pl-tree {
	margin: 8px 16px 16px;
	border: 1px solid var(--pos-border, rgba(0, 0, 0, 0.08));
	border-radius: 10px;
	overflow: hidden;
}

.pl-tree__header {
	display: flex;
	align-items: center;
	gap: 8px;
	padding: 10px 12px;
	background: var(--pos-hover-bg, rgba(0, 0, 0, 0.03));
	font-weight: 700;
	font-size: 0.8rem;
	text-transform: uppercase;
	letter-spacing: 0.02em;
	color: var(--pos-text-secondary, #666);
}

.pl-tree__header-label {
	flex: 1;
}

.pl-tree__header-value {
	min-width: 130px;
	text-align: right;
}
</style>
