<template>
	<DocumentDetailView
		:eyebrow="__('Manufacturing')"
		:title="name"
		:share="{ doctype: 'Production Requirement', name }"
		:subtitle="__('Production Requirement')"
		:loading="loading"
		:not-found="notFound"
		:status="detail.status ? __(detail.status) : ''"
		:status-color="statusColor(detail.status)"
		:meta-fields="metaFields"
		:item-columns="itemColumns"
		:items="itemRows"
		:totals="totals"
		:actions="actions"
		@back="goBack"
	/>
	<ConfirmActionDialog
		v-model="deleteDialog"
		:title="__('Delete Production Requirement')"
		:message="__('Permanently delete {0}? This cannot be undone.', [name])"
		:confirm-label="__('Delete')"
		confirm-color="error"
		:loading="deleteLoading"
		@confirm="runDelete"
	/>
</template>

<script>
import { ref, computed, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useToastStore } from "../../../stores/toastStore";
import { openDocumentPrintView } from "../../../utils/openDocumentPrintView";
import DocumentDetailView from "../shared/DocumentDetailView.vue";
import ConfirmActionDialog from "../shared/ConfirmActionDialog.vue";
import { formatDisplayDate, formatDisplayDateTime } from "../shared/docStatusUtils";
import {
	formatQty,
	PRODUCTION_REQUIREMENT_STATUSES,
	productionRequirementStatusColor,
} from "./productionRequirementUtils";

const API = "posawesome.posawesome.api.production_requirements";
const DOCTYPE = "Production Requirement";

export default {
	name: "ProductionRequirementDetail",
	components: { DocumentDetailView, ConfirmActionDialog },
	setup() {
		const route = useRoute();
		const router = useRouter();
		const toastStore = useToastStore();
		const name = route.params.name;

		const loading = ref(true);
		const notFound = ref(false);
		const detail = ref({});
		const deleteDialog = ref(false);
		const deleteLoading = ref(false);

		const metaFields = computed(() => [
			{ label: __("Production Date"), value: formatDisplayDate(detail.value.production_date) },
			{ label: __("Posting Date"), value: formatDisplayDate(detail.value.posting_date) },
			{ label: __("Warehouse"), value: detail.value.warehouse_name },
			{ label: __("Production By"), value: detail.value.production_by_name },
			{ label: __("Created By"), value: detail.value.created_by },
			{ label: __("Last Updated"), value: formatDisplayDateTime(detail.value.modified) },
			...(detail.value.remarks ? [{ label: __("Remarks"), value: detail.value.remarks }] : []),
		]);

		const itemColumns = [
			{ key: "idx", label: __("No.") },
			{ key: "item_code", label: __("Item Code") },
			{ key: "item_name", label: __("Item Name") },
			{ key: "item_group", label: __("Item Group") },
			{ key: "uom", label: __("UOM") },
			{ key: "shortage_qty", label: __("Shortage Qty"), align: "end" },
			{ key: "plan_qty", label: __("Plan Qty"), align: "end" },
		];

		const itemRows = computed(() =>
			(detail.value.items || []).map((row, index) => ({
				...row,
				idx: index + 1,
				shortage_qty: formatQty(row.shortage_qty),
				plan_qty: formatQty(row.plan_qty),
			})),
		);

		const totals = computed(() => [
			{ label: __("Total Shortage Qty"), value: formatQty(detail.value.total_shortage_qty) },
			{ label: __("Total Plan Qty"), value: formatQty(detail.value.total_plan_qty) },
		]);

		const actions = computed(() => [
			...(detail.value.can_edit
				? [
						{
							label: __("Change Status"),
							color: "primary",
							loading: statusLoading.value,
							menuItems: PRODUCTION_REQUIREMENT_STATUSES.filter(
								(s) => s !== detail.value.status,
							).map((s) => ({
								label: __(s),
								onClick: () => changeStatus(s),
							})),
						},
					]
				: []),
			...(detail.value.can_edit
				? [
						{
							label: __("Edit"),
							color: "primary",
							onClick: () =>
								router.push(`/production-requirements/${encodeURIComponent(name)}/edit`),
						},
					]
				: []),
			{ label: __("Print"), color: "primary", onClick: () => openDocumentPrintView(DOCTYPE, name) },
			...(detail.value.can_delete
				? [{ label: __("Delete"), color: "error", onClick: () => (deleteDialog.value = true) }]
				: []),
		]);

		const loadDetail = async () => {
			loading.value = true;
			notFound.value = false;
			try {
				const { message } = await frappe.call({
					method: `${API}.get_production_requirement_detail`,
					args: { name },
				});
				if (message) detail.value = message;
				else notFound.value = true;
			} catch (_e) {
				notFound.value = true;
			} finally {
				loading.value = false;
			}
		};

		const statusLoading = ref(false);
		const changeStatus = async (status) => {
			statusLoading.value = true;
			try {
				await frappe.call({
					method: `${API}.set_production_requirement_status`,
					args: { name, status },
				});
				toastStore.show({ title: __("{0} marked {1}", [name, __(status)]), color: "success" });
				await loadDetail();
			} catch (e) {
				toastStore.show({ title: e?.message || __("Failed to update status"), color: "error" });
			} finally {
				statusLoading.value = false;
			}
		};

		const runDelete = async () => {
			deleteLoading.value = true;
			try {
				await frappe.call({ method: `${API}.delete_production_requirement`, args: { name } });
				toastStore.show({ title: __("{0} deleted", [name]), color: "success" });
				deleteDialog.value = false;
				await router.push("/production-requirements/list");
			} catch (e) {
				toastStore.show({ title: e?.message || __("Failed to delete"), color: "error" });
			} finally {
				deleteLoading.value = false;
			}
		};

		const goBack = () => router.push("/production-requirements/list");

		onMounted(loadDetail);

		return {
			name,
			loading,
			notFound,
			detail,
			metaFields,
			itemColumns,
			itemRows,
			totals,
			actions,
			statusColor: productionRequirementStatusColor,
			deleteDialog,
			deleteLoading,
			runDelete,
			goBack,
		};
	},
};
</script>
