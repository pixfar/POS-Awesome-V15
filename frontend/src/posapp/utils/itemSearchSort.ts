type SortableItem = {
	item_code?: string | null;
	item_name?: string | null;
	barcode?: string | null;
	item_barcode?: Array<{ barcode?: string | null }> | null;
	barcodes?: Array<string | number | null> | null;
};

const normalizeText = (value: unknown) => String(value ?? "").trim().toLowerCase();

export const itemCodeNumeric = (value: unknown) => {
	const digits = normalizeText(value).replace(/\D/g, "");
	if (!digits) {
		return Number.MAX_SAFE_INTEGER;
	}
	const parsed = Number.parseInt(digits, 10);
	return Number.isFinite(parsed) ? parsed : Number.MAX_SAFE_INTEGER;
};

const collectBarcodeValues = (item: SortableItem) => {
	const values: string[] = [];
	const pushValue = (value: unknown) => {
		const normalized = normalizeText(value);
		if (normalized) {
			values.push(normalized);
		}
	};

	pushValue(item.barcode);
	if (Array.isArray(item.item_barcode)) {
		item.item_barcode.forEach((row) => pushValue(row?.barcode));
	}
	if (Array.isArray(item.barcodes)) {
		item.barcodes.forEach((row) => pushValue(row));
	}

	return values;
};

export const getItemSearchRank = (item: SortableItem, searchTerm: string) => {
	const term = normalizeText(searchTerm);
	if (!term) {
		return 0;
	}

	const code = normalizeText(item.item_code);
	if (code) {
		if (code === term) {
			return 0;
		}
		if (code.endsWith(term)) {
			return 1;
		}
		if (code.startsWith(term)) {
			return 2;
		}
		const codeIndex = code.indexOf(term);
		if (codeIndex >= 0) {
			return 10 + codeIndex;
		}
	}

	const name = normalizeText(item.item_name);
	if (name) {
		const nameIndex = name.indexOf(term);
		if (nameIndex >= 0) {
			return 100 + nameIndex;
		}
	}

	for (const barcode of collectBarcodeValues(item)) {
		if (barcode === term) {
			return 200;
		}
		if (barcode.endsWith(term)) {
			return 201;
		}
		const barcodeIndex = barcode.indexOf(term);
		if (barcodeIndex >= 0) {
			return 210 + barcodeIndex;
		}
	}

	return 1000;
};

export const compareItemsByCodeAsc = (
	left: SortableItem,
	right: SortableItem,
) => {
	const codeDiff =
		itemCodeNumeric(left?.item_code) - itemCodeNumeric(right?.item_code);
	if (codeDiff !== 0) {
		return codeDiff;
	}
	return normalizeText(left?.item_code).localeCompare(
		normalizeText(right?.item_code),
	);
};

// The item grid sorts the whole catalogue (1,000+ items) by code on every
// recompute, several times per change. The catalogue is normally already in
// code order (the server returns it that way), so check that in one pass
// before sorting, and reuse the result for the same array.
const sortedByCodeCache = new WeakMap<object, SortableItem[]>();

export function sortItemsByCodeAsc<T extends SortableItem>(items: T[] = []) {
	const cached = sortedByCodeCache.get(items);
	if (cached && cached.length === items.length) {
		return cached.slice() as T[];
	}
	let alreadySorted = true;
	for (let i = 1; i < items.length; i++) {
		if (compareItemsByCodeAsc(items[i - 1] as SortableItem, items[i] as SortableItem) > 0) {
			alreadySorted = false;
			break;
		}
	}
	const sorted = alreadySorted ? [...items] : [...items].sort(compareItemsByCodeAsc);
	sortedByCodeCache.set(items, sorted);
	return sorted.slice() as T[];
}

export function sortItemsForSearchTerm<T extends SortableItem>(
	items: T[] = [],
	searchTerm = "",
) {
	const term = normalizeText(searchTerm);
	if (!items.length) {
		return [];
	}
	if (!term) {
		return sortItemsByCodeAsc(items);
	}

	return [...items].sort((left, right) => {
		const rankDiff = getItemSearchRank(left, term) - getItemSearchRank(right, term);
		if (rankDiff !== 0) {
			return rankDiff;
		}
		return compareItemsByCodeAsc(left, right);
	});
}
