export function isPosWarehouseSwitcher(): boolean {
	const roles = frappe?.boot?.user?.roles || [];
	return roles.includes('System Manager');
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
