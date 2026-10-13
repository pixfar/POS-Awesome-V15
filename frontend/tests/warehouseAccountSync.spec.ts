import { afterEach, describe, expect, it, vi } from "vitest";
import { nextTick, ref } from "vue";

import { useWarehouseAccountSync } from "../src/posapp/composables/pos/shared/useWarehouseAccountSync";

// Server rule (get_sale_cash_account): keep `current` if it belongs to the
// warehouse, else the warehouse's first account; unchanged if none configured.
const ACCOUNTS: Record<string, string[]> = {
	"Narsingdi Showroom - BSP": ["Narsingdi Showroom - BSP"],
	"Store Room - BSP": ["Store Room - BSP"],
	"Unconfigured - BSP": [],
};

function mockServer(delays: Record<string, number> = {}) {
	const call = vi.fn(async ({ args }: any) => {
		await new Promise((r) => setTimeout(r, delays[args.warehouse] || 0));
		const list = ACCOUNTS[args.warehouse] || [];
		return { message: !list.length || list.includes(args.current) ? args.current : list[0] };
	});
	(globalThis as any).frappe = { call };
	return call;
}

const flush = () => new Promise((r) => setTimeout(r, 30));

describe("useWarehouseAccountSync", () => {
	afterEach(() => {
		delete (globalThis as any).frappe;
	});

	it("selects the new warehouse's account when the warehouse changes", async () => {
		mockServer();
		const warehouse = ref<string | null>("Store Room - BSP");
		const account = ref<string | null>("Store Room - BSP");
		useWarehouseAccountSync({ warehouse, account, enabled: ref(true) });

		warehouse.value = "Narsingdi Showroom - BSP";
		await nextTick();
		await flush();
		expect(account.value).toBe("Narsingdi Showroom - BSP");
	});

	it("leaves the account alone when the warehouse has no accounts configured", async () => {
		mockServer();
		const warehouse = ref<string | null>("Store Room - BSP");
		const account = ref<string | null>("Store Room - BSP");
		useWarehouseAccountSync({ warehouse, account, enabled: ref(true) });

		warehouse.value = "Unconfigured - BSP";
		await nextTick();
		await flush();
		expect(account.value).toBe("Store Room - BSP");
	});

	it("does nothing for users who cannot edit the account", async () => {
		const call = mockServer();
		const warehouse = ref<string | null>("Store Room - BSP");
		const account = ref<string | null>("Store Room - BSP");
		useWarehouseAccountSync({ warehouse, account, enabled: ref(false) });

		warehouse.value = "Narsingdi Showroom - BSP";
		await nextTick();
		await flush();
		expect(call).not.toHaveBeenCalled();
		expect(account.value).toBe("Store Room - BSP");
	});

	it("ignores a slow answer for a warehouse that is no longer selected", async () => {
		mockServer({ "Narsingdi Showroom - BSP": 20 });
		const warehouse = ref<string | null>("Store Room - BSP");
		const account = ref<string | null>("Store Room - BSP");
		useWarehouseAccountSync({ warehouse, account, enabled: ref(true) });

		warehouse.value = "Narsingdi Showroom - BSP"; // slow
		await nextTick();
		warehouse.value = "Store Room - BSP"; // fast, final choice
		await nextTick();
		await flush();
		expect(account.value).toBe("Store Room - BSP");
	});

	it("syncAccountForWarehouse re-checks a default set after the warehouse", async () => {
		mockServer();
		const warehouse = ref<string | null>("Narsingdi Showroom - BSP");
		const account = ref<string | null>(null);
		const { syncAccountForWarehouse } = useWarehouseAccountSync({
			warehouse,
			account,
			enabled: ref(true),
		});

		account.value = "Store Room - BSP"; // e.g. session default applied late
		await syncAccountForWarehouse();
		expect(account.value).toBe("Narsingdi Showroom - BSP");
	});
});
