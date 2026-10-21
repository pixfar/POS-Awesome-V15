/**
 * Last server-resolved default warehouse / payment account for the Sales
 * Invoice screen, per user + POS Profile. Applied instantly on load so the
 * screen (and its item catalogue) starts on the right warehouse without
 * waiting for get_pos_warehouses / get_sale_cash_account; the server lookup
 * still runs in the background and corrects it if the default has changed.
 */

declare const frappe: any;

export interface SaleDefaults {
	warehouse: string;
	warehouse_label?: string;
	account?: string | null;
}

const keyFor = (profileName: string) => {
	const user = (typeof frappe !== "undefined" && frappe?.session?.user) || "";
	return `posa_sale_defaults:${user}:${profileName}`;
};

export const loadSaleDefaults = (profileName?: string | null): SaleDefaults | null => {
	if (!profileName) return null;
	try {
		const raw = localStorage.getItem(keyFor(profileName));
		const parsed = raw ? JSON.parse(raw) : null;
		return parsed && typeof parsed.warehouse === "string" && parsed.warehouse ? parsed : null;
	} catch {
		return null;
	}
};

export const saveSaleDefaults = (profileName: string | null | undefined, defaults: SaleDefaults) => {
	if (!profileName || !defaults?.warehouse) return;
	try {
		localStorage.setItem(keyFor(profileName), JSON.stringify(defaults));
	} catch {
		// Storage unavailable (private mode / quota) -- the server lookup still works.
	}
};
