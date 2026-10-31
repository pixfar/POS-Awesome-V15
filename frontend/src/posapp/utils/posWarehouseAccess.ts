export function isPosWarehouseSwitcher(): boolean {
	// Prefer the server flag from bsp_engineering.boot.boot_session so users
	// with multiple Warehouse User Permissions (and no privileged role) can
	// still swap showrooms. Falls back to the role check for older boots.
	if (frappe?.boot && "can_switch_pos_warehouse" in frappe.boot) {
		return Boolean(frappe.boot.can_switch_pos_warehouse);
	}
	// Mirrors bsp_engineering.utils.pos_warehouse.POS_WAREHOUSE_UNRESTRICTED_ROLES
	const roles = frappe?.boot?.user?.roles || [];
	return (
		roles.includes("System Manager") ||
		roles.includes("BSP Admin") ||
		roles.includes("BSP Viewer")
	);
}

export function isFundTransferManager(): boolean {
	const roles = frappe?.boot?.user?.roles || [];
	return roles.includes("BSP Admin") || roles.includes("System Manager");
}

export function resolveTransactionWarehouse(
	selected: string | null | undefined,
	profileWarehouse: string | null | undefined,
): string | null {
	const trimmed =
		typeof selected === "string" && selected.trim().length > 0
			? selected.trim()
			: null;
	if (isPosWarehouseSwitcher()) {
		return trimmed || profileWarehouse || null;
	}
	return trimmed || profileWarehouse || null;
}
