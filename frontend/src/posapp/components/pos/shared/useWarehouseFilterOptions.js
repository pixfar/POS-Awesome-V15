import { ref } from 'vue';

// Warehouse options for a list page's "Warehouse" filter, in BSP's official
// warehouse order (Warehouse.custom_sort_order); unranked ones last, A-Z.
export function useWarehouseFilterOptions() {
	const warehouseOptions = ref([]);

	const loadWarehouseOptions = async () => {
		try {
			const { message } = await frappe.call({
				method: 'frappe.client.get_list',
				args: {
					doctype: 'Warehouse',
					fields: ['name', 'warehouse_name', 'custom_sort_order'],
					filters: { is_group: 0, disabled: 0 },
					limit_page_length: 200,
				},
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
