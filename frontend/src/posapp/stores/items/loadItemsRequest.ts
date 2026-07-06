import type { POSProfile } from "../../types/models";
import type { GetItemsArgs } from "../../services/itemService";

export interface LoadItemsOptions {
	forceServer?: boolean;
	searchValue?: string;
	groupFilter?: string;
	priceList?: string | null;
	limit?: number | null;
	warehouse?: string | null;
}

export interface BuildLoadItemsRequestInput {
	options?: LoadItemsOptions;
	posProfile: POSProfile | null;
	activePriceList: string;
	customer: string | null;
	itemCount: number;
	totalItemCount: number;
	limitSearchEnabled: boolean;
	resolvePageSize: () => number;
	resolveInitialBootstrapPageSize: () => number;
	resolveLimitSearchSize: () => number | null;
}

function clonePosProfileForRequest(
	profile: POSProfile,
	options: { warehouse?: string | null; forceServer?: boolean } = {},
): string {
	try {
		const clone = JSON.parse(JSON.stringify(profile)) as Record<string, unknown>;
		if (options.warehouse) {
			clone.warehouse = options.warehouse;
		}
		if (options.forceServer) {
			clone.posa_use_server_cache = 0;
			clone.posa_force_reload_items = 1;
		}
		return JSON.stringify(clone);
	} catch {
		const clone: Record<string, unknown> = { ...profile };
		if (options.warehouse) {
			clone.warehouse = options.warehouse;
		}
		if (options.forceServer) {
			clone.posa_use_server_cache = 0;
			clone.posa_force_reload_items = 1;
		}
		return JSON.stringify(clone);
	}
}

export interface BuiltLoadItemsRequest {
	forceServer: boolean;
	searchValue: string;
	normalizedGroup: string;
	priceList: string | null;
	effectivePriceList: string;
	isInitialBootstrapRequest: boolean;
	resolvedLimit: number | null;
	args: GetItemsArgs | null;
}

export const buildLoadItemsRequest = ({
	options = {},
	posProfile,
	activePriceList,
	customer,
	itemCount,
	totalItemCount,
	limitSearchEnabled,
	resolvePageSize,
	resolveInitialBootstrapPageSize,
	resolveLimitSearchSize,
}: BuildLoadItemsRequestInput): BuiltLoadItemsRequest => {
	const {
		forceServer = false,
		searchValue: rawSearchValue = "",
		groupFilter = "ALL",
		priceList = null,
		limit = null,
		warehouse = null,
	} = options;

	const searchValue =
		typeof rawSearchValue === "string" ? rawSearchValue.trim() : "";
	const normalizedGroup =
		typeof groupFilter === "string" && groupFilter.trim().length > 0
			? groupFilter.trim()
			: "ALL";

	const isInitialBootstrapRequest =
		!forceServer &&
		!limitSearchEnabled &&
		!searchValue &&
		normalizedGroup === "ALL" &&
		itemCount === 0 &&
		totalItemCount === 0;

	const resolvedLimit =
		Number.isFinite(limit) && limit! > 0
			? limit!
			: isInitialBootstrapRequest
				? resolveInitialBootstrapPageSize()
				: limitSearchEnabled
					? resolveLimitSearchSize()
					: null;

	if (!posProfile) {
		return {
			forceServer,
			searchValue,
			normalizedGroup,
			priceList,
			effectivePriceList: priceList || activePriceList,
			isInitialBootstrapRequest,
			resolvedLimit,
			args: null,
		};
	}

	const effectivePriceList = priceList || activePriceList;
	const activeWarehouse =
		typeof warehouse === "string" && warehouse.trim().length > 0
			? warehouse.trim()
			: null;
	const requestProfile = clonePosProfileForRequest(posProfile, {
		warehouse: activeWarehouse,
		forceServer,
	});

	const args: GetItemsArgs = {
		pos_profile: requestProfile,
		price_list: effectivePriceList,
		item_group: normalizedGroup !== "ALL" ? normalizedGroup.toLowerCase() : "",
		search_value: searchValue || "",
		customer,
		include_image: 1,
		item_groups: posProfile?.item_groups?.map((g: any) => g.item_group) || [],
	};

	if (typeof resolvedLimit === "number" && resolvedLimit > 0) {
		args.limit = resolvedLimit;
	}
	if (activeWarehouse) {
		args.warehouse = activeWarehouse;
	}
	// Plain catalog browsing (no search term) is paginated/displayed in
	// ascending item code order — keep the server cursor consistent with that.
	if (!searchValue) {
		args.sort_by = "item_code";
	}

	return {
		forceServer,
		searchValue,
		normalizedGroup,
		priceList,
		effectivePriceList,
		isInitialBootstrapRequest,
		resolvedLimit,
		args,
	};
};
