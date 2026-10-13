import { watch, type Ref } from "vue";

declare const frappe: any;

// Each warehouse lists its own Cash / Bank Accounts (Warehouse
// "Cash / Bank Accounts" table). On any screen with both a Warehouse and an
// "Accounts" picker, picking a warehouse selects that warehouse's account --
// keeping the current one when it already belongs to that warehouse, and
// leaving it untouched when the warehouse has no accounts configured. The
// cashier can still change the account afterwards.
//
// Same rule as the Sales screen (Invoice.vue syncAccountForWarehouse), via the
// same server helper.
export function useWarehouseAccountSync(options: {
	warehouse: Ref<string | null | undefined>;
	account: Ref<string | null | undefined>;
	enabled: Ref<boolean>;
}) {
	const { warehouse, account, enabled } = options;
	let requestId = 0;

	const syncAccountForWarehouse = async (wh = warehouse.value) => {
		if (!enabled.value || !wh) {
			return;
		}
		const current = account.value || null;
		const thisRequest = ++requestId;
		try {
			const { message } = await frappe.call({
				method: "posawesome.posawesome.utils.invoice_warehouse.get_sale_cash_account",
				args: { warehouse: wh, current },
			});
			// Ignore a stale answer if the warehouse changed again meanwhile.
			if (thisRequest !== requestId || wh !== warehouse.value) {
				return;
			}
			if (message && message !== account.value) {
				account.value = message;
			}
		} catch (error) {
			console.error("Failed to resolve the warehouse's cash account", error);
		}
	};

	watch(warehouse, (wh, previous) => {
		if (wh && wh !== previous) {
			syncAccountForWarehouse(wh);
		}
	});

	return { syncAccountForWarehouse };
}
