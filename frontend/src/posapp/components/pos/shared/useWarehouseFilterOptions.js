import { ref } from 'vue';

// Warehouse options for a list page's "Warehouse" filter, in BSP's official
// warehouse order (Warehouse.custom_sort_order); unranked ones last, A-Z.
// Uses the dashboard warehouse API so Warehouse User Permissions apply even
// for BSP Admin / System Manager (frappe.client.get_list alone is not enough
// when privileged roles bypass or when we need a single shared source).
export function useWarehouseFilterOptions() {
	const warehouseOptions = ref([]);

	const loadWarehouseOptions = async () => {
		try {
			const { message } = await frappe.call({
				method: 'posawesome.posawesome.api.company_dashboard.get_dashboard_warehouses',
			});
			const rank = (w) => (Number(w.custom_sort_order) > 0 ? Number(w.custom_sort_order) : Infinity);
			warehouseOptions.value = (message || []).sort(
				(a, b) =>
					rank(a) - rank(b) ||
					String(a.warehouse_name || a.name).localeCompare(String(b.warehouse_name || b.name)),
			);
		} catch (e) {
			console.error('Failed to load warehouses', e);
			warehouseOptions.value = [];
		}
	};

	return { warehouseOptions, loadWarehouseOptions };
}
