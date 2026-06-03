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
