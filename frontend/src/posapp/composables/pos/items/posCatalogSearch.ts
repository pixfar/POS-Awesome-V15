import type { ComputedRef, InjectionKey, Ref } from "vue";

export type CatalogSearchItem = {
	item_code?: string;
	item_name?: string;
	actual_qty?: number | string;
	stock_uom?: string;
	[key: string]: unknown;
};

export type PosCatalogSearchApi = {
	/** Cart (invoice items) search only — independent from the right-panel catalog search. */
	searchInput: Ref<string>;
	qtyInput: Ref<string | number>;
	posProfile: Ref<Record<string, unknown>>;
	displayedItems: ComputedRef<CatalogSearchItem[]>;
	/** Matches for the cart search dropdown (does not filter the item cards). */
	catalogMatches?: ComputedRef<CatalogSearchItem[]> | Ref<CatalogSearchItem[]>;
	isLoading: ComputedRef<boolean> | Ref<boolean>;
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
