import { watchPrintWindow } from "../plugins/print";

declare const frappe: any;

export function openDocumentPrintView(doctype: string, name: string, printFormat?: string) {
	if (!doctype || !name) return;

	const params = new URLSearchParams({ doctype, name, trigger_print: "1" });
	if (printFormat) {
		params.set("format", printFormat);
	}

	const baseUrl = frappe?.urllib?.get_base_url ? frappe.urllib.get_base_url() : "";
	const url = `${baseUrl}/printview?${params.toString()}`;

	const printWindow = window.open(url, "_blank");
	watchPrintWindow(printWindow, { triggerPrint: "1" });
}
