import { silentPrint } from '../plugins/print';

declare const frappe: any;

/**
 * Print a document via the same HTML printview Frappe already renders
 * correctly (e.g. /printview?doctype=...&no_letterhead=1). A generated PDF
 * embedded in a hidden iframe was tried previously, but a fixed-size iframe
 * can't reliably display/print a PDF that may span multiple pages, so
 * content beyond the iframe's viewport silently never printed. The HTML
 * printview paginates natively under the browser's print engine, and the
 * print formats already set `@page { margin: 0 }` in their print CSS, which
 * suppresses the browser's date/title/URL/page-number chrome.
 */
export async function openDocumentPrintView(
	doctype: string,
	name: string,
	printFormat?: string,
) {
	if (!doctype || !name) {
		return;
	}

	const params = new URLSearchParams({
		doctype,
		name,
		trigger_print: '1',
		no_letterhead: '1',
		letterhead: 'No Letterhead',
	});
	if (printFormat) {
		params.set('format', printFormat);
	}

	const baseUrl = frappe?.urllib?.get_base_url
		? frappe.urllib.get_base_url()
		: '';
	const url = `${baseUrl}/printview?${params.toString()}`;

	silentPrint(url, { triggerPrint: '1' });
}
