import type { Ref } from 'vue';

export function useListFilterPersistence(
	storageKey: string,
	filterRefs: Record<string, Ref<any>>
) {
	const loadSavedFilters = (): boolean => {
		try {
			const saved = localStorage.getItem(storageKey);
			if (!saved) return false;
			const parsed = JSON.parse(saved);
			let hasAnyRestored = false;
			for (const [key, refVal] of Object.entries(filterRefs)) {
				if (parsed[key] !== undefined && refVal && typeof refVal === 'object' && 'value' in refVal) {
					refVal.value = parsed[key];
					if (
						parsed[key] !== null &&
						parsed[key] !== '' &&
						parsed[key] !== false &&
						(!Array.isArray(parsed[key]) || parsed[key].length > 0)
					) {
						hasAnyRestored = true;
					}
				}
			}
			return hasAnyRestored;
		} catch (e) {
			console.error(`Failed to load filters from storage key "${storageKey}":`, e);
			return false;
		}
	};

	const saveFilters = () => {
		try {
			const data: Record<string, any> = {};
			for (const [key, refVal] of Object.entries(filterRefs)) {
				if (refVal && typeof refVal === 'object' && 'value' in refVal) {
					data[key] = refVal.value;
				}
			}
			localStorage.setItem(storageKey, JSON.stringify(data));
		} catch (e) {
			console.error(`Failed to save filters to storage key "${storageKey}":`, e);
		}
	};

	const clearSavedFilters = () => {
		try {
			localStorage.removeItem(storageKey);
		} catch (e) {
			console.error(`Failed to clear filters for storage key "${storageKey}":`, e);
		}
	};

	return {
		loadSavedFilters,
		saveFilters,
		clearSavedFilters,
	};
}
