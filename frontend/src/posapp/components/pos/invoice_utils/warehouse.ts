import {
	isPosWarehouseSwitcher,
	resolveTransactionWarehouse,
} from '../../../utils/posWarehouseAccess';

export function resolvePosWarehouse(
	context: { sale_warehouse?: string | null; pos_profile?: { warehouse?: string } },
	itemWarehouse?: string | null,
): string | null {
	const profileWh = context?.pos_profile?.warehouse || null;
	const selected = context?.sale_warehouse?.trim?.() || context?.sale_warehouse;
	const transactionWh = resolveTransactionWarehouse(selected, profileWh);
	if (transactionWh) {
		return transactionWh;
	}
	if (!isPosWarehouseSwitcher()) {
		return profileWh;
	}
	const itemWh = itemWarehouse?.trim?.() || itemWarehouse;
	if (itemWh) {
		return itemWh;
	}
	return profileWh;
}

// True only when a line is *known* to be a non-stock item (service/labour
// charge). A missing flag means "unknown", not "non-stock": rows reloaded
// from the server never carry is_stock_item (it isn't a Sales Invoice Item
// field), and treating them as non-stock used to leave them on the POS
// Profile's default warehouse.
export function isNonStockFlag(flag: unknown): boolean {
	return flag === 0 || flag === false || flag === "0";
}

// Re-point a cached invoice doc's lines at a newly selected sale warehouse.
// Stock lines (or lines with no flag) get the warehouse; known non-stock
// lines get none. cartItems supplies the flag for rows that came back from
// the server without one. Returns the same row object when nothing changed.
export function applyWarehouseToDocItems<T extends { item_code?: string; is_stock_item?: unknown; warehouse?: string | null }>(
	rows: T[],
	warehouse: string,
	cartItems: Array<{ item_code?: string; is_stock_item?: unknown }> = [],
): T[] {
	const cartStockFlags = new Map(
		(cartItems || [])
			.filter((item) => item && item.item_code)
			.map((item) => [item.item_code, item.is_stock_item]),
	);
	return rows.map((row) => {
		if (!row) {
			return row;
		}
		const flag = row.is_stock_item ?? cartStockFlags.get(row.item_code);
		const target = isNonStockFlag(flag) ? null : warehouse;
		return row.warehouse !== target ? { ...row, warehouse: target } : row;
	});
}
