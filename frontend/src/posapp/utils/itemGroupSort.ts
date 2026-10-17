// Order Item Group options with Bengali (Bangla) names first, then English,
// each alphabetical within its bucket. Mirrors the item-group sidebar ordering
// so every list filter reads the same way.

const BANGLA_RE = /[ঀ-৿]/;

type GroupLike = string | Record<string, any>;

export function sortItemGroupsBanglaFirst(
	groups: GroupLike[],
	nameKey = "name",
): GroupLike[] {
	if (!Array.isArray(groups)) return [];
	const nameOf = (g: GroupLike): string =>
		typeof g === "string" ? g : String(g?.[nameKey] ?? "");

	const bangla: GroupLike[] = [];
	const english: GroupLike[] = [];
	for (const g of groups) {
		(BANGLA_RE.test(nameOf(g)) ? bangla : english).push(g);
	}
	const byName = (a: GroupLike, b: GroupLike) =>
		nameOf(a).localeCompare(nameOf(b), undefined, { sensitivity: "base" });
	bangla.sort(byName);
	english.sort(byName);
	return [...bangla, ...english];
}
