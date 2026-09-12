export function isPosWarehouseSwitcher(): boolean {
	// Mirrors bsp_engineering.utils.pos_warehouse.can_change_pos_warehouse --
	// System Manager and BSP Admin already get unrestricted warehouse access
	// everywhere else (see posawesome's is_privileged_invoice_viewer), and
	// BSP Viewer is the deliberately read-only role handed to management for
	// full cross-showroom oversight (see is_read_only_viewer). All three
	// need the warehouse switcher itself enabled, not just the backend data
	// behind it -- this only used to check System Manager, so BSP Admin and
	// BSP Viewer users saw a switcher locked to their own POS Profile
	// warehouse even though the backend (once fixed the same way) would
	// have let them see every warehouse anyway.
	const roles = frappe?.boot?.user?.roles || [];
	return (
		roles.includes('System Manager') ||
		roles.includes('BSP Admin') ||
		roles.includes('BSP Viewer')
	);
}

export function isFundTransferManager(): boolean {
	const roles = frappe?.boot?.user?.roles || [];
	return roles.includes('BSP Admin') || roles.includes('System Manager');
}

export function resolveTransactionWarehouse(
	selected: string | null | undefined,
	profileWarehouse: string | null | undefined,
): string | null {
	const trimmed =
		typeof selected === 'string' && selected.trim().length > 0
			? selected.trim()
			: null;
	if (isPosWarehouseSwitcher()) {
		return trimmed || profileWarehouse || null;
	}
	return trimmed || profileWarehouse || null;
}
