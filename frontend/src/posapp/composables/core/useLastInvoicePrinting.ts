import { useUIStore } from "../../stores/uiStore";
import {
	appendDebugPrintParam,
	isDebugPrintEnabled,
	silentPrint,
	watchPrintWindow,
} from "../../plugins/print";
import { printDocumentViaQz } from "../../services/qzTray";
import { openDocumentPdfPrint } from "../../utils/openDocumentPdfPrint";

declare const frappe: any;

export function useLastInvoicePrinting() {
	const uiStore = useUIStore();

	function parseBooleanSetting(value: unknown) {
		if (value === undefined || value === null) return false;
		if (typeof value === "string") {
			const normalized = value.trim().toLowerCase();
			return ["1", "true", "yes", "on"].includes(normalized);
		}
		if (typeof value === "number") return value === 1;
		return Boolean(value);
	}

	async function printLastInvoice() {
		const lastInvoiceId = uiStore.lastInvoiceId;
		const posProfile = uiStore.posProfile;

		if (!lastInvoiceId) {
			console.warn("No last invoice ID to print");
			return;
		}

		if (!posProfile) {
			console.warn("No POS Profile loaded");
			return;
		}

		const pf =
			posProfile.print_format_for_online || posProfile.print_format;
		const letter_head = posProfile.letter_head || 0;
		const doctype = posProfile.create_pos_invoice_instead_of_sales_invoice
			? "POS Invoice"
			: "Sales Invoice";
		const debugPrint = isDebugPrintEnabled();
		const openInNewTab = parseBooleanSetting(
			posProfile.posa_open_print_in_new_tab,
		);
		const useSilentPrint = parseBooleanSetting(posProfile.posa_silent_print);
		const noLetterhead = letter_head ? "0" : "1";
		const printFormat = pf || "Standard";

		if (useSilentPrint) {
			try {
				await printDocumentViaQz({
					doctype,
					name: lastInvoiceId,
					printFormat,
					letterhead: letter_head || null,
					noLetterhead,
				});
				return;
			} catch (error) {
				console.warn("QZ Tray print failed, falling back to PDF print", error);
			}
		}

		try {
			await openDocumentPdfPrint({
				doctype,
				name: lastInvoiceId,
				printFormat,
				letterHead: letter_head || null,
				noLetterhead,
				autoPrint: !openInNewTab,
			});
			return;
		} catch (error) {
			console.warn("PDF print failed, falling back to printview", error);
		}

		const basePrintUrl = frappe.urllib.get_base_url() + "/printview";
		let url =
			basePrintUrl +
			"?doctype=" +
			encodeURIComponent(doctype) +
			"&name=" +
			encodeURIComponent(lastInvoiceId) +
			"&trigger_print=1" +
			"&format=" +
			encodeURIComponent(printFormat) +
			"&no_letterhead=" +
			noLetterhead;

		if (letter_head) {
			url += "&letterhead=" + encodeURIComponent(letter_head);
		}

		url = appendDebugPrintParam(url, debugPrint);

		const printOptions = {
			triggerPrint: "1",
			debugPrint,
			debugInfo: {
				printFormat,
				templatePath: "online-printview",
			},
		};

		if (openInNewTab) {
			let newTabUrl =
				basePrintUrl +
				"?doctype=" +
				encodeURIComponent(doctype) +
				"&name=" +
				encodeURIComponent(lastInvoiceId) +
				"&trigger_print=0" +
				"&format=" +
				encodeURIComponent(printFormat) +
				"&no_letterhead=" +
				noLetterhead;

			if (letter_head) {
				newTabUrl += "&letterhead=" + encodeURIComponent(letter_head);
			}

			newTabUrl = appendDebugPrintParam(newTabUrl, debugPrint);
			const printWindow = window.open(newTabUrl, "_blank");
			if (printWindow) {
				watchPrintWindow(printWindow, {
					...printOptions,
					triggerPrint: "0",
					shouldPrint: false,
					showSessionMessage: false,
				});
				return;
			}
			silentPrint(url, printOptions);
			return;
		}

		if (useSilentPrint) {
			silentPrint(url, printOptions);
			return;
		}

		const printWindow = window.open(url, "Print");
		if (printWindow) {
			watchPrintWindow(printWindow, printOptions);
		}
	}

	return {
		printLastInvoice,
	};
}
