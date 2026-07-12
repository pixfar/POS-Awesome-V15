import { openDocumentPdfPrint } from './openDocumentPdfPrint';

declare const frappe: any;

/**
 * Open a document print using PDF (not HTML printview) so browser chrome
 * (date, title, URL, page numbers) is not stamped on the page.
 */
export async function openDocumentPrintView(
	doctype: string,
	name: string,
	printFormat?: string,
) {
	if (!doctype || !name) {
		return;
	}

	try {
		await openDocumentPdfPrint({
			doctype,
			name,
			printFormat: printFormat || undefined,
			autoPrint: true,
		});
	} catch (error) {
		console.warn('PDF print failed, falling back to printview', error);
		const params = new URLSearchParams({
			doctype,
			name,
			trigger_print: '1',
		});
		if (printFormat) {
			params.set('format', printFormat);
		}
		const baseUrl = frappe?.urllib?.get_base_url
			? frappe.urllib.get_base_url()
			: '';
		window.open(
			`${baseUrl}/printview?${params.toString()}`,
			'_blank',
			'noopener,noreferrer',
		);
	}
}
