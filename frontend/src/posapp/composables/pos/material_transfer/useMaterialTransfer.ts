import { ref, computed, type Ref } from 'vue';
import { useItemsStore } from '../../../stores/itemsStore';

export interface MaterialTransferItem {
	line_id: string;
	item_code: string;
	item_name: string;
	stock_uom: string;
	item_group: string;
	uom: string;
	qty: number;
	// On-hand qty in the current From Warehouse -- 0 until refreshStockQty()
	// (or the fetch onAddItem kicks off) fills it in; not the qty being
	// transferred (that's `qty` above).
	stock_qty: number;
}

export function useMaterialTransfer(options: { posProfile: Ref<any> }) {
	const itemsStore = useItemsStore();
	const transferItems = ref<MaterialTransferItem[]>([]);
	const fromWarehouse = ref<string | null>(null);
	const toWarehouse = ref<string | null>(null);
	const notes = ref('');
	const submitLoading = ref(false);
	const errorMessage = ref('');

	const totalQty = computed(() =>
		transferItems.value.reduce((sum, row) => sum + Number(row.qty || 0), 0),
	);

	const generateLineId = () =>
		`mt_${Date.now()}_${Math.floor(Math.random() * 10000)}`;

	// Refreshes Stock Qty (on-hand in `warehouse`) for every item currently
	// in the table -- called whenever From Warehouse changes, since the same
	// item's available qty differs per warehouse. Silently leaves stale
	// values in place on failure rather than blocking the cart.
	const refreshStockQty = async (warehouse: string | null | undefined) => {
		if (!warehouse || !transferItems.value.length) return;
		const itemCodes = transferItems.value.map((row) => row.item_code);
		try {
			const { message } = await frappe.call({
				method: 'posawesome.posawesome.api.material_transfers.get_stock_qty',
				args: { item_codes: JSON.stringify(itemCodes), warehouse },
			});
			const qtyByItem = message || {};
			transferItems.value.forEach((row) => {
				row.stock_qty = Number(qtyByItem[row.item_code] || 0);
			});
		} catch {
			/* ignore */
		}
	};

	const onAddItem = async (item: any) => {
		if (!item?.item_code) return;

		if (!item.item_uoms?.length) {
			try {
				const details = await itemsStore.getItemByCode(item.item_code);
				if (details?.item_uoms) item.item_uoms = details.item_uoms;
			} catch {
				/* ignore */
			}
		}

		const existing = transferItems.value.find(
			(row) => row.item_code === item.item_code,
		);
		if (existing) {
			existing.qty += 1;
			return;
		}

		transferItems.value.unshift({
			line_id: generateLineId(),
			item_code: item.item_code,
			item_name: item.item_name,
			stock_uom: item.stock_uom,
			item_group: item.item_group,
			uom: item.stock_uom,
			qty: 1,
			stock_qty: 0,
		});
		// Newly added row starts at stock_qty 0 -- re-fetch for the whole
		// table (simpler and cheap enough than tracking just the delta).
		refreshStockQty(fromWarehouse.value);
	};

	const updateItemQty = (item: MaterialTransferItem, value: number) => {
		if (!item) return;
		item.qty = Math.max(0, Number(value) || 0);
	};

	const removeItem = (item: MaterialTransferItem) => {
		transferItems.value = transferItems.value.filter(
			(row) => row.line_id !== item.line_id,
		);
	};

	const resetForm = () => {
		transferItems.value = [];
		notes.value = '';
		errorMessage.value = '';
	};

	const initWarehousesFromProfile = () => {
		const profile = options.posProfile.value || {};
		if (!fromWarehouse.value) {
			fromWarehouse.value = profile.warehouse || null;
		}
	};

	return {
		transferItems,
		fromWarehouse,
		toWarehouse,
		notes,
		submitLoading,
		errorMessage,
		totalQty,
		onAddItem,
		updateItemQty,
		removeItem,
		resetForm,
		initWarehousesFromProfile,
		refreshStockQty,
	};
}
