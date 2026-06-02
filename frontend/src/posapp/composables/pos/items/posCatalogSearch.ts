import type { ComputedRef, InjectionKey, Ref } from "vue";

export type CatalogSearchItem = {
	item_code?: string;
	item_name?: string;
	actual_qty?: number | string;
	stock_uom?: string;
	[key: string]: unknown;
};

export type PosCatalogSearchApi = {
	searchInput: Ref<string>;
	qtyInput: Ref<string | number>;
	posProfile: Ref<Record<string, unknown>>;
	displayedItems: ComputedRef<CatalogSearchItem[]>;
	isLoading: ComputedRef<boolean>;
	scannerLocked: Ref<boolean>;
	enableBackgroundSync: Ref<boolean>;
	lastSyncTime: Ref<string>;
	syncStatus: Ref<string>;
	showSyncProgress: Ref<boolean>;
	syncProgress: Ref<number>;
	syncItemsCount: Ref<number>;
	hideQtyDecimals: Ref<boolean>;
	handleSearchInput: (_value: unknown) => void;
	onEnter: (_event?: KeyboardEvent) => Promise<void> | void;
	handleSearchKeydown: (_event: KeyboardEvent) => void;
	handleSearchPaste: (_event: ClipboardEvent) => void;
	handleSearchFocus: () => void;
	clearSearch: () => void;
	clearQty: () => void;
	onQtyBlur: () => void;
	startCameraScanning: () => void;
	toggleItemSettings: () => void;
	forceReloadItems: () => void;
	runCatalogSearch: () => Promise<void>;
	addItemFromCatalog: (_item: CatalogSearchItem) => Promise<void>;
	searchAndAddItem: (_event?: KeyboardEvent) => Promise<void>;
	focusSearch: () => void;
	bindDefaultSearchInputHandlers?: () => void;
};

export const posCatalogSearchKey: InjectionKey<PosCatalogSearchApi | null> =
	Symbol("posCatalogSearch");
