import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../src/offline/index", () => ({
	getTaxTemplate: vi.fn(() => null),
	getTaxInclusiveSetting: vi.fn(() => false),
	isOffline: vi.fn(() => false),
}));

vi.mock("../src/posapp/components/pos/invoice_utils/currency", () => ({
	_getPlcConversionRate: vi.fn(() => 1),
}));

import { get_invoice_doc } from "../src/posapp/components/pos/invoice_utils/document";
import {
	applyWarehouseToDocItems,
	isNonStockFlag,
} from "../src/posapp/components/pos/invoice_utils/warehouse";

const STORE_ROOM = "Store Room - BSP";
const NARSINGDI = "Narsingdi Showroom - BSP";

function cartItem(overrides: Record<string, unknown>) {
	return {
		item_code: "ITEM",
		item_name: "Item",
		qty: 1,
		stock_qty: 1,
		rate: 10,
		price_list_rate: 10,
		amount: 10,
		uom: "Nos",
		stock_uom: "Nos",
		conversion_factor: 1,
		warehouse: STORE_ROOM,
		posa_row_id: "row",
		...overrides,
	};
}

function buildContext(items: any[], saleWarehouse: string | null) {
	return {
		invoiceType: "Invoice",
		pos_profile: {
			company: "BSP Engineering Works",
			name: "BSP Store Room",
			currency: "BDT",
			warehouse: STORE_ROOM,
			payments: [{ mode_of_payment: "Cash", account: "Cash", type: "Cash", default: 1 }],
		},
		sale_warehouse: saleWarehouse,
		selected_currency: "BDT",
		conversion_rate: 1,
		company: { default_currency: "BDT" },
		price_list_currency: "BDT",
		get_price_list: () => "Standard Selling",
		customer_info: { customer: "CUST", customer_name: "Customer" },
		customer: "CUST",
		isReturnInvoice: false,
		items,
		packed_items: [],
		Total: 0,
		subtotal: 0,
		additional_discount: 0,
		additional_discount_percentage: 0,
		roundAmount: (value: number) => value,
		pos_opening_shift: { name: "SHIFT-1" },
		posa_offers: [],
		posa_coupons: [],
		selected_delivery_charge: null,
		delivery_charges_rate: 0,
		posting_date_display: "2026-10-13",
		formatDateForBackend: (value: string) => value,
		invoice_doc: { name: "ACC-SINV-DRAFT", payments: [], taxes: [] },
	};
}

describe("isNonStockFlag", () => {
	it("is true only for an explicit non-stock flag", () => {
		expect(isNonStockFlag(0)).toBe(true);
		expect(isNonStockFlag(false)).toBe(true);
		expect(isNonStockFlag("0")).toBe(true);
		expect(isNonStockFlag(1)).toBe(false);
		expect(isNonStockFlag(true)).toBe(false);
		// Rows reloaded from the server have no flag -- that is "unknown",
		// and must NOT be treated as non-stock.
		expect(isNonStockFlag(undefined)).toBe(false);
		expect(isNonStockFlag(null)).toBe(false);
	});
});

describe("applyWarehouseToDocItems (warehouse switch on the cached invoice doc)", () => {
	it("moves server-reloaded rows without is_stock_item to the new warehouse", () => {
		// Exactly the shape frappe.client.get / update_invoice return.
		const rows = [
			{ item_code: "STOCK-A", warehouse: STORE_ROOM },
			{ item_code: "STOCK-B", warehouse: STORE_ROOM },
		];
		const result = applyWarehouseToDocItems(rows, NARSINGDI);
		expect(result.map((r) => r.warehouse)).toEqual([NARSINGDI, NARSINGDI]);
	});

	it("clears the warehouse of known non-stock rows (flag on row or on cart line)", () => {
		const rows = [
			{ item_code: "STOCK-A", warehouse: STORE_ROOM },
			{ item_code: "SERVICE", warehouse: STORE_ROOM },
			{ item_code: "LABOUR", warehouse: STORE_ROOM, is_stock_item: 0 },
		];
		const cart = [
			{ item_code: "STOCK-A", is_stock_item: 1 },
			{ item_code: "SERVICE", is_stock_item: 0 },
		];
		const result = applyWarehouseToDocItems(rows, NARSINGDI, cart);
		expect(result.map((r) => r.warehouse)).toEqual([NARSINGDI, null, null]);
	});

	it("keeps unchanged rows as the same object", () => {
		const row = { item_code: "STOCK-A", warehouse: NARSINGDI };
		expect(applyWarehouseToDocItems([row], NARSINGDI)[0]).toBe(row);
	});
});

describe("get_invoice_doc warehouse per line", () => {
	beforeEach(() => {
		(globalThis as any).flt = (value: unknown, precision = 2) =>
			Number(Number(value || 0).toFixed(precision));
		(globalThis as any).frappe = { boot: { user: { roles: ["System Manager"] } } };
	});

	it("puts stock lines (even without is_stock_item) on the selected warehouse", () => {
		const context: any = buildContext(
			[
				cartItem({ item_code: "STOCK-FLAGGED", is_stock_item: 1, posa_row_id: "r1" }),
				cartItem({ item_code: "STOCK-UNFLAGGED", posa_row_id: "r2" }),
			],
			NARSINGDI,
		);
		const doc = get_invoice_doc(context);
		expect(doc.set_warehouse).toBe(NARSINGDI);
		expect(doc.items.map((r: any) => r.warehouse)).toEqual([NARSINGDI, NARSINGDI]);
	});

	it("gives non-stock lines no warehouse", () => {
		const context: any = buildContext(
			[
				cartItem({ item_code: "STOCK", is_stock_item: 1, posa_row_id: "r1" }),
				cartItem({ item_code: "SERVICE", is_stock_item: 0, posa_row_id: "r2" }),
			],
			NARSINGDI,
		);
		const doc = get_invoice_doc(context);
		const byCode = Object.fromEntries(doc.items.map((r: any) => [r.item_code, r.warehouse]));
		expect(byCode).toEqual({ STOCK: NARSINGDI, SERVICE: null });
	});

	it("falls back to the POS Profile warehouse when nothing was selected", () => {
		const context: any = buildContext(
			[cartItem({ item_code: "STOCK", is_stock_item: 1, warehouse: NARSINGDI })],
			null,
		);
		const doc = get_invoice_doc(context);
		expect(doc.set_warehouse).toBe(STORE_ROOM);
		expect(doc.items[0].warehouse).toBe(STORE_ROOM);
	});
});
