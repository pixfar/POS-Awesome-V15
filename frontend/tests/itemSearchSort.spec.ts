import { describe, expect, it } from "vitest";

import {
	getItemSearchRank,
	sortItemsByCodeAsc,
	sortItemsForSearchTerm,
} from "../src/posapp/utils/itemSearchSort";

describe("itemSearchSort", () => {
	it("sorts item codes numerically in ascending order", () => {
		const items = [
			{ item_code: "00000024" },
			{ item_code: "00000002" },
			{ item_code: "00000044" },
		];

		expect(sortItemsByCodeAsc(items).map((item) => item.item_code)).toEqual([
			"00000002",
			"00000024",
			"00000044",
		]);
	});

	it("ranks exact and suffix item-code matches ahead of other matches", () => {
		expect(getItemSearchRank({ item_code: "00000002" }, "02")).toBe(1);
		expect(getItemSearchRank({ item_code: "00000024" }, "02")).toBeGreaterThan(
			1,
		);
	});

	it("keeps ascending item-code order when search term is empty", () => {
		const items = [
			{ item_code: "00000433" },
			{ item_code: "00000002" },
			{ item_code: "00000024" },
		];

		expect(sortItemsForSearchTerm(items, "").map((item) => item.item_code)).toEqual([
			"00000002",
			"00000024",
			"00000433",
		]);
	});

	it("places 00000002 first when searching for 02", () => {
		const items = [
			{ item_code: "00000044" },
			{ item_code: "00000433" },
			{ item_code: "00000024" },
			{ item_code: "00000002" },
			{ item_code: "0000045" },
		];

		expect(sortItemsForSearchTerm(items, "02").map((item) => item.item_code)).toEqual([
			"00000002",
			"00000024",
			"00000044",
			"0000045",
			"00000433",
		]);
	});
});
