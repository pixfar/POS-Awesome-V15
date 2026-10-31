// Icons and accent colours for document fields on detail pages and expanded
// list rows, picked from the field's label ("Posting Date" -> calendar,
// "From Warehouse" -> warehouse, ...). Display only: a field can name its
// own `icon` / `accent` to override, and unknown labels get a neutral icon.
// Accents map to the --pos-accent-* tokens in styles/theme.css.

const FIELD_RULES = [
	[/mobile|phone|contact/, "mdi-phone-outline", "green"],
	[/date|created on|modified on|time|period/, "mdi-calendar-blank-outline", "teal"],
	[/warehouse|store room|source|target|location/, "mdi-warehouse", "violet"],
	[/status|approval/, "mdi-check-decagram-outline", "green"],
	[/remark|note|memo|description|reason/, "mdi-note-text-outline", "amber"],
	[/customer|supplier|party|employee|requested by|created by|modified by|cashier|owner|user|approver|received by|dispatched by/, "mdi-account-outline", "teal"],
	[/weight/, "mdi-weight-kilogram", "violet"],
	[/qty|quantity|count|items/, "mdi-counter", "teal"],
	[/currency|amount|total|price|rate|paid|payment|account|outstanding|discount|balance|cost|value/, "mdi-cash", "green"],
	[/return/, "mdi-keyboard-return", "red"],
	[/profile|territory|area|company|branch|showroom|department/, "mdi-store-outline", "violet"],
	[/vehicle|transport|driver|delivery/, "mdi-truck-outline", "amber"],
	[/attachment|file|image/, "mdi-paperclip", "teal"],
	[/entry|reference|invoice|order|bom|plan|no\b|number|id\b/, "mdi-file-document-outline", "teal"],
	[/type|group|category|mode/, "mdi-shape-outline", "amber"],
];

const DEFAULT_FIELD = { icon: "mdi-information-outline", accent: "slate" };

export function fieldIcon(field) {
	const label = String(field?.label || "").toLowerCase();
	const rule = FIELD_RULES.find(([pattern]) => pattern.test(label));
	const fallback = rule ? { icon: rule[1], accent: rule[2] } : DEFAULT_FIELD;
	return {
		icon: field?.icon || fallback.icon,
		accent: field?.accent || fallback.accent,
	};
}

// Totals get the same icons, with accents cycling so a row of figures reads
// as distinct tiles.
const TOTAL_ACCENTS = ["teal", "green", "violet", "amber"];

export function totalIcon(total, index) {
	const label = String(total?.label || "").toLowerCase();
	let icon = "mdi-sigma";
	if (/outstanding|due|balance/.test(label)) icon = "mdi-alert-circle-outline";
	else if (/discount/.test(label)) icon = "mdi-tag-outline";
	else if (/paid|received amount|sanctioned/.test(label)) icon = "mdi-cash-check";
	else if (/weight/.test(label)) icon = "mdi-weight-kilogram";
	else if (/return/.test(label)) icon = "mdi-keyboard-return";
	else if (/qty|quantity|count|items/.test(label)) icon = "mdi-counter";
	else if (/total|amount|claimed|grand|net/.test(label)) icon = "mdi-cash-multiple";
	return {
		icon: total?.icon || icon,
		accent: total?.accent || TOTAL_ACCENTS[index % TOTAL_ACCENTS.length],
	};
}

// Item table columns holding a code (item_code, ...) are shown as codes.
export function isCodeColumn(column) {
	return /(^|_)code$/.test(String(column?.key || ""));
}
