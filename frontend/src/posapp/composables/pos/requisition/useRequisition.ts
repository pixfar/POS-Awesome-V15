import { ref, computed, type Ref } from 'vue';
import { useItemsStore } from '../../../stores/itemsStore';

declare const frappe: any;
declare const __: (_str: string, _args?: any[]) => string;

export interface RequisitionItem {
	line_id: string;
	item_code: string;
	item_name: string;
	stock_uom: string;
	item_group: string;
	uom: string;
	qty: number;
}

export function useRequisition(options: { posProfile: Ref<any> }) {
	const itemsStore = useItemsStore();
	const requisitionItems = ref<RequisitionItem[]>([]);
	const sourceWarehouse = ref<string | null>(null);
	const targetWarehouse = ref<string | null>(null);
	const notes = ref('');
	const submitLoading = ref(false);
	const errorMessage = ref('');

	const totalQty = computed(() =>
		requisitionItems.value.reduce((sum, row) => sum + Number(row.qty || 0), 0),
	);

	const generateLineId = () =>
		`req_${Date.now()}_${Math.floor(Math.random() * 10000)}`;

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

		const existing = requisitionItems.value.find(
			(row) => row.item_code === item.item_code,
		);
		if (existing) {
			existing.qty += 1;
			return;
		}

		requisitionItems.value.unshift({
			line_id: generateLineId(),
			item_code: item.item_code,
			item_name: item.item_name,
			stock_uom: item.stock_uom,
			item_group: item.item_group,
			uom: item.stock_uom,
			qty: 1,
		});
	};

	const updateItemQty = (item: RequisitionItem, value: number) => {
		if (!item) return;
		item.qty = Math.max(0, Number(value) || 0);
	};

	const removeItem = (item: RequisitionItem) => {
		requisitionItems.value = requisitionItems.value.filter(
			(row) => row.line_id !== item.line_id,
		);
	};

	const resetForm = () => {
		requisitionItems.value = [];
		notes.value = '';
		errorMessage.value = '';
	};

	const initWarehousesFromProfile = () => {
		const profile = options.posProfile.value || {};
		if (!sourceWarehouse.value) {
			sourceWarehouse.value = profile.warehouse || null;
		}
	};

	return {
		requisitionItems,
		sourceWarehouse,
		targetWarehouse,
		notes,
		submitLoading,
		errorMessage,
		totalQty,
		onAddItem,
		updateItemQty,
		removeItem,
		resetForm,
		initWarehousesFromProfile,
	};
}
