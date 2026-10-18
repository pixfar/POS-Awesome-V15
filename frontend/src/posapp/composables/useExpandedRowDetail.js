import { reactive, ref, watch } from "vue";

/**
 * Shared expand-to-detail state for POS list pages.
 * Loads a document once per row and caches it for the session.
 */
export function useExpandedRowDetail(method, argName = "name") {
	const expandedRows = ref([]);
	const detailCache = reactive({});
	const detailLoading = reactive({});

	const loadRowDetail = async (name) => {
		if (!name || Object.prototype.hasOwnProperty.call(detailCache, name) || detailLoading[name]) {
			return;
		}
		detailLoading[name] = true;
		try {
			const { message } = await frappe.call({
				method,
				args: { [argName]: name },
			});
			detailCache[name] = message || {};
		} catch (error) {
			console.error("Failed to load row detail", error);
			detailCache[name] = {};
		} finally {
			detailLoading[name] = false;
		}
	};

	watch(expandedRows, (names) => {
		(names || []).forEach((name) => loadRowDetail(name));
	});

	return { expandedRows, detailCache, detailLoading };
}
