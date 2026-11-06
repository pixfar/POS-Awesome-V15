interface PaymentPrintFormatRule {
	customer_group?: string | null;
	print_format?: string | null;
}

interface ResolvePaymentPrintFormatOptions {
	profile?: Record<string, any> | null;
	customerInfo?: Record<string, any> | null;
	availableFormats?: string[] | null;
}

function normalizeFormatName(value: unknown) {
	return typeof value === "string" && value.trim() ? value.trim() : "";
}

function isAvailableFormat(value: string, availableFormats: string[]) {
	return !availableFormats.length || availableFormats.includes(value);
}

export function resolvePaymentPrintFormat({
	profile,
	customerInfo,
	availableFormats = [],
}: ResolvePaymentPrintFormatOptions) {
	const formats = Array.isArray(availableFormats)
		? availableFormats.map(normalizeFormatName).filter(Boolean)
		: [];

	const rules = Array.isArray(profile?.posa_print_format_rules)
		? (profile?.posa_print_format_rules as PaymentPrintFormatRule[])
		: [];
	const customerGroup = normalizeFormatName(customerInfo?.customer_group);

	if (customerGroup) {
		const matchedRule = rules.find(
			(rule) =>
				normalizeFormatName(rule?.customer_group) === customerGroup &&
				isAvailableFormat(normalizeFormatName(rule?.print_format), formats),
		);
		const ruleFormat = normalizeFormatName(matchedRule?.print_format);
		if (ruleFormat) {
			return ruleFormat;
		}
	}

	const preferredDefaults = [
		normalizeFormatName(profile?.print_format_for_online),
		normalizeFormatName(profile?.print_format),
	];

	for (const format of preferredDefaults) {
		if (format && isAvailableFormat(format, formats)) {
			return preferBanglaSalesFormat(format, formats);
		}
	}

	return preferBanglaSalesFormat(formats[0] || "", formats);
}

const LEGACY_SALES_PRINT_FORMATS = new Set(["", "Standard", "BSP Sales Invoice"]);

export const BSP_SALES_INVOICE_BANGLA = "BSP Sales Invoice Bangla";

function preferBanglaSalesFormat(format: string, formats: string[]) {
	if (
		LEGACY_SALES_PRINT_FORMATS.has(format) &&
		formats.includes(BSP_SALES_INVOICE_BANGLA)
	) {
		return BSP_SALES_INVOICE_BANGLA;
	}
	return format;
}

/** Sales Invoice prints default to the Bangla format unless a specific format is chosen. */
export function resolveSalesInvoicePrintFormat(format?: string | null) {
	const name = normalizeFormatName(format);
	if (LEGACY_SALES_PRINT_FORMATS.has(name)) {
		return BSP_SALES_INVOICE_BANGLA;
	}
	return name;
}
