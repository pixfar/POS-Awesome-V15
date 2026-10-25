import _ from "lodash";
import { shouldReloadOnSearchClear } from "../../../utils/searchUtils.js";
import { resolveBooleanSetting } from "./selectorSearch/resolveBooleanSetting";

declare const flt: (_value: unknown) => number;

type SearchDeps = {
	getVM?: () => any;
	scannerInput?: any;
	itemSelection?: any;
	getSearchInput?: () => string;
	setSearchInput?: (_value: string) => void;
	isLimitSearchEnabled?: () => boolean;
	runLimitSearch?: (_term: string) => Promise<unknown> | unknown;
	/** Prefer this over vm.searchItems — keeps store searchTerm in sync. */
	runCanonicalSearch?: (_term: string) => Promise<unknown> | unknown;
	/** True while catalogue load / sync would race a typed search. */
	isSearchBusy?: () => boolean;
	getPendingSearch?: () => string | null | undefined;
	setPendingSearch?: (_value: string | null) => void;
	clearHighlightedItem?: () => void;
};

export const useItemsSelectorSearch = ({
	getVM,
	scannerInput,
	itemSelection,
	getSearchInput,
	setSearchInput,
	isLimitSearchEnabled,
	runLimitSearch,
	runCanonicalSearch,
	isSearchBusy,
	getPendingSearch,
	setPendingSearch,
	clearHighlightedItem,
}: SearchDeps) => {
	const getVm = (): any => (typeof getVM === "function" ? getVM() : null);

	const usesLimitSearch = (vm: any): boolean => {
		if (typeof isLimitSearchEnabled === "function") {
			return isLimitSearchEnabled();
		}
		if (!vm) return false;
		if (typeof vm.usesLimitSearch === "boolean") {
			return vm.usesLimitSearch;
		}
		if (vm.usesLimitSearch && typeof vm.usesLimitSearch.value === "boolean") {
			return vm.usesLimitSearch.value;
		}
		return resolveBooleanSetting(
			vm.pos_profile?.posa_use_limit_search ?? vm.pos_profile?.pose_use_limit_search,
		);
	};

	const hasStorageAvailable = (vm: any): boolean => {
		if (!vm) return false;
		if (typeof vm.storageAvailable === "boolean") {
			return vm.storageAvailable;
		}
		if (vm.storageAvailable && typeof vm.storageAvailable.value === "boolean") {
			return vm.storageAvailable.value;
		}
		return false;
	};

	const getSearchExecutor = (vm: any) => {
		if (!vm) return null;
		if (typeof vm.searchItems === "function") {
			return vm.searchItems.bind(vm);
		}
		if (typeof vm.itemsIntegration?.searchItems === "function") {
			return vm.itemsIntegration.searchItems.bind(vm.itemsIntegration);
		}
		return null;
	};

	const getItemsLoader = (vm: any) => {
		if (!vm) return null;
		if (typeof vm.get_items === "function") {
			return vm.get_items.bind(vm);
		}
		if (typeof vm.itemsIntegration?.get_items === "function") {
			return vm.itemsIntegration.get_items.bind(vm.itemsIntegration);
		}
		return null;
	};

	const getVisibleItemsLoader = (vm: any) => {
		if (!vm) return null;
		if (typeof vm.loadVisibleItems === "function") {
			return vm.loadVisibleItems.bind(vm);
		}
		if (typeof vm.itemsLoader?.loadVisibleItems === "function") {
			return vm.itemsLoader.loadVisibleItems.bind(vm.itemsLoader);
		}
		return null;
	};

	const triggerEnterEvent = (vm: any) => {
		if (!vm) return;
		if (typeof vm.enter_event === "function") {
			vm.enter_event();
			return;
		}
		void enter_event();
	};

	const getCurrentSearchInput = (vm: any): string => {
		if (typeof getSearchInput === "function") {
			return String(getSearchInput() || "");
		}
		return typeof vm?.search_input === "string"
			? vm.search_input
			: vm?.first_search || "";
	};

	const syncSearchInput = (vm: any, value: string) => {
		if (typeof setSearchInput === "function") {
			setSearchInput(value);
		}
		if (vm) {
			vm.search_input = value;
		}
	};

	const clearHighlightedSelection = (vm: any) => {
		if (typeof clearHighlightedItem === "function") {
			clearHighlightedItem();
			return;
		}
		if (typeof (itemSelection || vm?.itemSelection)?.clearHighlightedItem === "function") {
			(itemSelection || vm.itemSelection).clearHighlightedItem();
		}
	};

	const getHighlightedIndex = (selection: any): number => {
		const value = selection?.highlightedIndex;
		if (typeof value === "number") {
			return value;
		}
		if (value && typeof value.value === "number") {
			return value.value;
		}
		return -1;
	};

	const get_search = (first_search: string) => {
		if (!first_search) return "";
		const prefix = scannerInput.getScaleBarcodePrefix();
		const prefix_len = prefix.length;
		if (!scannerInput.scaleBarcodeMatches(first_search)) {
			return first_search;
		}
		// Calculate item code length from total barcode length
		const item_code_len = first_search.length - prefix_len - 6;
		return first_search.substr(0, prefix_len + item_code_len);
	};

	const get_item_qty = (first_search: string) => {
		const vm = getVm();
		if (!vm) return 1;
		const qtyVal = vm.qty != null ? vm.qty : 1;
		let scal_qty: number | string = Math.abs(qtyVal);
		const prefix = scannerInput.getScaleBarcodePrefix();
		const prefix_len = prefix.length;

		if (scannerInput.scaleBarcodeMatches(first_search)) {
			// Determine item code length dynamically based on EAN-13 structure:
			// prefix + item_code + 5 qty digits + 1 check digit
			const item_code_len = first_search.length - prefix_len - 6;
			let pesokg1 = first_search.substr(prefix_len + item_code_len, 5);
			let pesokg;
			if (pesokg1.startsWith("0000")) {
				pesokg = "0.00" + pesokg1.substr(4);
			} else if (pesokg1.startsWith("000")) {
				pesokg = "0.0" + pesokg1.substr(3);
			} else if (pesokg1.startsWith("00")) {
				pesokg = "0." + pesokg1.substr(2);
			} else if (pesokg1.startsWith("0")) {
				pesokg =
					pesokg1.substr(1, 1) +
					"." +
					pesokg1.substr(2, pesokg1.length);
			} else if (!pesokg1.startsWith("0")) {
				pesokg =
					pesokg1.substr(0, 2) +
					"." +
					pesokg1.substr(2, pesokg1.length);
			}
			scal_qty = pesokg;
		}
		if (vm.hide_qty_decimals) {
			scal_qty = Math.round(Number(scal_qty));
		}
		return scal_qty;
	};

	const enter_event = async (scannedCode?: string) => {
		const vm = getVm();
		if (!vm) return;

		const searchTerm = scannedCode || vm.first_search;
		await scannerInput.ensureScaleBarcodeSettings();
		if (!vm.displayedItems.length || !searchTerm) {
			return;
		}

		// Derive the searchable code and detect scale barcode
		const search = get_search(searchTerm);
		const isScaleBarcode = scannerInput.scaleBarcodeMatches(searchTerm);
		vm.search = search;

		const qty = Number(get_item_qty(searchTerm));
		const new_item = { ...vm.displayedItems[0] };
		new_item.qty = flt(qty);
		if (isScaleBarcode) {
			new_item._barcode_qty = true;
		}

		let match = false;
		if (Array.isArray(new_item.item_barcode)) {
			new_item.item_barcode.forEach((element) => {
				if (search === element.barcode) {
					new_item.uom = element.uom;
					match = true;
				}
			});
		}
		if (!match && new_item.barcode === search) {
			match = true;
		}
		if (!match && Array.isArray(new_item.barcodes)) {
			match = new_item.barcodes.some((bc) => String(bc) === search);
		}
		if (!match && String(new_item.item_code || "") === search) {
			match = true;
		}

		if (vm.flags && vm.flags.serial_no) {
			new_item.to_set_serial_no = vm.flags.serial_no;
		}
		if (vm.flags && vm.flags.batch_no) {
			new_item.to_set_batch_no = vm.flags.batch_no;
		}

		if (match) {
			const fromScanner = vm.search_from_scanner;
			if (fromScanner) {
				vm.awaitingScanResult = true;
			}

			try {
				await vm.add_item(new_item, { suppressNegativeWarning: true });
				if (fromScanner) {
					scannerInput.playScanTone("success");
					vm.scannerLocked = false;
					vm.pendingScanCode = "";
				}
			} finally {
				if (fromScanner) {
					vm.awaitingScanResult = false;
				}
			}

			if (vm.flags) {
				vm.flags.serial_no = null;
				vm.flags.batch_no = null;
			}
			vm.qty = 1;

			if (fromScanner) {
				vm.search_from_scanner = false;
			}

			if (!vm.scanErrorDialog) {
				// Clear search field after successfully adding an item
				vm.clearSearch();
				vm.focusItemSearch();
			}
		}
	};

	const _performSearch = async () => {
		const vm = getVm();
		if (!vm) return;

		if (
			vm.itemDetailFetcher &&
			typeof vm.itemDetailFetcher.cancelItemDetailsRequest === "function"
		) {
			vm.itemDetailFetcher.cancelItemDetailsRequest();
		} else if (typeof vm.cancelItemDetailsRequest === "function") {
			vm.cancelItemDetailsRequest();
		}

		// Prefer the visible input value so Enter uses the latest typed text.
		const rawQuery = getCurrentSearchInput(vm);
		const trimmedQuery = String(rawQuery || "").trim();

		// Keep both search refs aligned with the value we are about to process.
		vm.first_search = trimmedQuery;
		syncSearchInput(vm, trimmedQuery);

		// If the input is a numeric string 12 characters or longer, treat it as a barcode
		if (/^\d{12,}$/.test(trimmedQuery)) {
			if (typeof vm.onBarcodeScanned === "function") {
				vm.onBarcodeScanned(trimmedQuery);
			} else if (scannerInput.onBarcodeScanned) {
				scannerInput.onBarcodeScanned(trimmedQuery);
			}
			return;
		}

		// Require at least 2 characters before running a search
		if (!trimmedQuery || trimmedQuery.length < 2) {
			vm.search_from_scanner = false;
			if (typeof setPendingSearch === "function") {
				setPendingSearch(null);
			} else {
				vm.pendingItemSearch = null;
			}
			return;
		}

		// Defer while the catalogue is loading/syncing so an in-flight page
		// load cannot overwrite search results (and leave first_search stuck
		// on a term that no longer matches the loaded page).
		const busy =
			(typeof isSearchBusy === "function" && isSearchBusy()) ||
			Boolean(vm.isLoadingOrSyncing) ||
			Boolean(vm.isBackgroundLoading) ||
			Boolean(vm.loading) ||
			Boolean(vm.isLoading);
		if (busy) {
			if (typeof setPendingSearch === "function") {
				setPendingSearch(trimmedQuery);
			} else {
				vm.pendingItemSearch = trimmedQuery;
			}
			return;
		}

		if (typeof setPendingSearch === "function") {
			setPendingSearch(null);
		} else {
			vm.pendingItemSearch = null;
		}

		vm.search = trimmedQuery;

		const fromScanner = vm.search_from_scanner;

		// Always go through searchItems (or limit-search) so itemsStore.searchTerm
		// stays aligned with the UI query. The old storageAvailable →
		// loadVisibleItems path never set searchTerm, so a later item-group
		// click only filtered the current page locally and showed "No items".
		const runSearch =
			(typeof runCanonicalSearch === "function"
				? runCanonicalSearch
				: null) ||
			(usesLimitSearch(vm) && typeof runLimitSearch === "function"
				? runLimitSearch
				: null) ||
			getSearchExecutor(vm);

		if (runSearch) {
			await runSearch(trimmedQuery);
		} else if (usesLimitSearch(vm) && typeof runLimitSearch === "function") {
			await runLimitSearch(trimmedQuery);
		} else if (hasStorageAvailable(vm)) {
			const loadVisibleItems = getVisibleItemsLoader(vm);
			if (loadVisibleItems) {
				await loadVisibleItems(true);
			}
		} else {
			const getItems = getItemsLoader(vm);
			if (getItems) {
				await getItems(true);
			}
		}

		// Scanner / barcode flows auto-add the first match after search.
		if (fromScanner) {
			triggerEnterEvent(vm);
			vm.clearSearch();
			vm.focusItemSearch();
			vm.search_from_scanner = false;
		}
	};

	/** Flush a search that was deferred while the catalogue was busy. */
	const flushPendingSearch = async () => {
		const pending =
			(typeof getPendingSearch === "function"
				? getPendingSearch()
				: getVm()?.pendingItemSearch) || null;
		const term = String(pending || "").trim();
		if (!term || term.length < 2) {
			return;
		}
		if (typeof setPendingSearch === "function") {
			setPendingSearch(null);
		} else {
			const vm = getVm();
			if (vm) vm.pendingItemSearch = null;
		}
		if (typeof runCanonicalSearch === "function") {
			await runCanonicalSearch(term);
			return;
		}
		const vm = getVm();
		if (vm) {
			vm.first_search = term;
			syncSearchInput(vm, term);
		}
		await _performSearch();
	};

	const search_onchange = _.debounce(() => {
		_performSearch();
	}, 300);

	const onEnter = (event?: KeyboardEvent) => {
		const vm = getVm();
		if (!vm) return;

		if (usesLimitSearch(vm)) {
			if (event && typeof event.preventDefault === "function") {
				event.preventDefault();
			}
			clearHighlightedSelection(vm);
			if (search_onchange.cancel) {
				search_onchange.cancel();
			}
			_performSearch();
			return;
		}

		if (getHighlightedIndex(itemSelection || vm.itemSelection) >= 0) {
			if (event && typeof event.preventDefault === "function") {
				event.preventDefault();
			}
			(itemSelection || vm.itemSelection).selectHighlightedItem();
			return;
		}
		if (search_onchange.cancel) {
			search_onchange.cancel();
		}
		_performSearch();
	};

	const clearSearch = () => {
		const vm = getVm();
		if (!vm) return;

		if (scannerInput.resetKeyboardScanDetection) {
			scannerInput.resetKeyboardScanDetection();
		} else if (typeof vm.resetKeyboardScanDetection === "function") {
			vm.resetKeyboardScanDetection();
		}
		if (vm.clearingSearch) {
			return;
		}

		const shouldReload = shouldReloadOnSearchClear({
			currentSearch: vm.first_search,
			previousSearch: vm.search,
			itemsLoaded: vm.itemsLoaded,
			itemsCount: vm.items.length,
		});

		vm.search_backup = vm.first_search;
		vm.clearingSearch = true;
		vm.search_input = "";
		vm.first_search = "";
		vm.search = "";
		if (typeof setPendingSearch === "function") {
			setPendingSearch(null);
		} else {
			vm.pendingItemSearch = null;
		}

		const release = () => {
			vm.$nextTick(() => {
				vm.clearingSearch = false;
			});
		};

		if (usesLimitSearch(vm)) {
			const preservedItems =
				vm.clearLimitSearchResults({ preserveItems: true }) ||
				vm.items ||
				[];
			vm.resetBarcodeIndex();

			if (Array.isArray(preservedItems) && preservedItems.length) {
				vm.eventBus.emit("set_all_items", preservedItems);
			} else if (Array.isArray(vm.items) && vm.items.length) {
				vm.eventBus.emit("set_all_items", vm.items);
			}

			if (shouldReload) {
				vm.eventBus.emit("data-load-progress", {
					name: "items",
					progress: 0,
				});
				const reloadPromise = vm.get_items(true);
				if (
					reloadPromise &&
					typeof reloadPromise.finally === "function"
				) {
					reloadPromise.finally(release);
					return reloadPromise;
				}
			}

			release();
			return;
		}

		// Canonical clear: resets store searchTerm and reloads the active
		// group catalogue (online-only). Avoids a second parallel reload.
		const clearStoreSearch =
			(typeof runCanonicalSearch === "function" ? runCanonicalSearch : null) ||
			getSearchExecutor(vm);
		if (clearStoreSearch) {
			const reloadPromise = clearStoreSearch("");
			if (reloadPromise && typeof reloadPromise.finally === "function") {
				reloadPromise.finally(release);
				return reloadPromise;
			}
			release();
			return;
		}

		if (!shouldReload) {
			release();
			return;
		}

		if (hasStorageAvailable(vm)) {
			const loadVisibleItems = getVisibleItemsLoader(vm);
			if (loadVisibleItems) {
				loadVisibleItems(true);
			}
			if (
				!vm.isBackgroundLoading &&
				typeof vm.verifyServerItemCount === "function"
			) {
				vm.verifyServerItemCount();
			}
			release();
			return;
		}

		if (vm.isBackgroundLoading) {
			if (vm.pendingGetItems) {
				vm.pendingGetItems.force_server =
					vm.pendingGetItems.force_server || false;
			} else {
				vm.pendingGetItems = { force_server: false };
			}
			release();
			return;
		}

		if (!vm.itemsLoaded || !vm.items.length) {
			vm.get_items(true);
		} else {
			vm.eventBus.emit("set_all_items", vm.items);
		}

		release();
	};

	const restoreSearch = () => {
		const vm = getVm();
		if (!vm) return;
		if (vm.first_search === "") {
			vm.first_search = vm.search_backup;
			vm.search = vm.search_backup;
			// No need to reload items when focus is lost
		}
	};

	const handleItemSearchFocus = () => {
		const vm = getVm();
		if (!vm) return;
		vm.search_input = "";
	};

	return {
		enter_event,
		onEnter,
		search_onchange,
		_performSearch,
		flushPendingSearch,
		get_item_qty,
		get_search,
		clearSearch,
		restoreSearch,
		handleItemSearchFocus,
	};
};
