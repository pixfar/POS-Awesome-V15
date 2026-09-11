type ItemLike = {
	item_code?: unknown;
};

type BuildItemDetailsRequestIdentityArgs = {
	posProfileName?: string | null;
	activePriceList?: string | null;
	priceListOverride?: string | null;
	warehouse?: string | null;
	items: Array<ItemLike | null | undefined>;
};

export type ItemDetailsRequestIdentity = {
	effectivePriceList: string;
	key: string;
};

export function buildItemDetailsRequestIdentity({
	posProfileName,
	activePriceList,
	priceListOverride = null,
	warehouse = null,
	items,
}: BuildItemDetailsRequestIdentityArgs): ItemDetailsRequestIdentity {
	const effectivePriceList =
		typeof priceListOverride === "string" &&
		priceListOverride.trim().length
			? priceListOverride.trim()
			: activePriceList || "";
	const itemCodes = Array.from(
		new Set(
			items
				.map((item) =>
					item?.item_code !== undefined && item?.item_code !== null
						? String(item.item_code).trim()
						: undefined,
				)
				.filter(
					(code) =>
						code !== undefined && code !== "",
				),
		),
	)
		.sort();

	return {
		effectivePriceList,
		// warehouse is part of the identity so two requests for the same
		// items under different warehouses are never treated as the same
		// in-flight request (see fetchItemDetails's request-dedup cache) --
		// otherwise a request kicked off just before a warehouse switch could
		// have its result handed back to a *later* caller asking for the new
		// warehouse, without ever going back out to the server.
		key: [
			posProfileName || "",
			effectivePriceList,
			warehouse || "",
			itemCodes.join(","),
		].join(":"),
	};
}
