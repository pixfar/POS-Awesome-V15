export function resolvePosWarehouse(
	context: { sale_warehouse?: string | null; pos_profile?: { warehouse?: string } },
	itemWarehouse?: string | null,
): string | null {
	const selected = context?.sale_warehouse?.trim?.() || context?.sale_warehouse;
	if (selected) {
		return selected;
	}
	const itemWh = itemWarehouse?.trim?.() || itemWarehouse;
	if (itemWh) {
		return itemWh;
	}
	return context?.pos_profile?.warehouse || null;
}
