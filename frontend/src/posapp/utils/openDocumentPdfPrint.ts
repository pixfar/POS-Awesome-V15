declare const frappe: any;

export type DocumentPdfPrintOptions = {
	doctype: string;
	name: string;
	printFormat?: string | null;
	letterHead?: string | number | null;
	noLetterhead?: string | number | boolean | null;
	/** When true (default), opens a hidden frame and triggers print. */
	autoPrint?: boolean;
};

function resolveBaseUrl(): string {
	if (frappe?.urllib?.get_base_url) {
		return frappe.urllib.get_base_url();
	}
	return window.location.origin;
}

export function buildDocumentPdfUrl(options: DocumentPdfPrintOptions): string {
	const params = new URLSearchParams({
		doctype: options.doctype,
		name: options.name,
	});

	if (options.printFormat) {
		params.set('format', String(options.printFormat));
	}

	const noLetterhead =
		options.noLetterhead === true ||
		options.noLetterhead === 1 ||
		options.noLetterhead === '1'
			? '1'
			: '0';
	params.set('no_letterhead', noLetterhead);

	if (options.letterHead) {
		params.set('letterhead', String(options.letterHead));
	}

	return `${resolveBaseUrl()}/api/method/frappe.utils.print_format.download_pdf?${params.toString()}`;
}

/**
 * Print Sales/Purchase (and other) documents as PDF so the browser does not
 * stamp date, title, URL, or page numbers from the HTML printview chrome.
 */
export async function openDocumentPdfPrint(
	options: DocumentPdfPrintOptions,
): Promise<void> {
	if (!options.doctype || !options.name) {
		return;
	}

	const url = buildDocumentPdfUrl(options);
	const response = await fetch(url, {
		method: 'GET',
		credentials: 'include',
		headers: {
			Accept: 'application/pdf',
		},
	});

	if (!response.ok) {
		throw new Error(`Failed to generate PDF (${response.status})`);
	}

	const blob = await response.blob();
	const blobUrl = URL.createObjectURL(blob);
	const autoPrint = options.autoPrint !== false;

	if (!autoPrint) {
		window.open(blobUrl, '_blank', 'noopener,noreferrer');
		setTimeout(() => URL.revokeObjectURL(blobUrl), 60_000);
		return;
	}

	const iframe = document.createElement('iframe');
	iframe.setAttribute('title', 'Document Print');
	iframe.setAttribute('aria-hidden', 'true');
	// The iframe needs real rendering area for the browser's built-in PDF
	// viewer to actually rasterize the document; a 0x0 iframe loads the
	// blob but never paints anything, so print() fires on empty content.
	// Must be at least as tall as an A4 page (~1123px at 96dpi) or the PDF
	// viewer only paints what's within its box, cropping content near the
	// bottom when printed. Keep it off-screen instead of zero-sized.
	Object.assign(iframe.style, {
		position: 'fixed',
		top: '-10000px',
		left: '-10000px',
		width: '850px',
		height: '1250px',
		border: '0',
		pointerEvents: 'none',
	});

	const cleanup = () => {
		URL.revokeObjectURL(blobUrl);
		iframe.remove();
	};

	iframe.addEventListener(
		'load',
		() => {
			window.setTimeout(() => {
				try {
					iframe.contentWindow?.focus();
					iframe.contentWindow?.print();
				} catch (error) {
					console.warn('PDF print failed, opening PDF tab', error);
					window.open(blobUrl, '_blank', 'noopener,noreferrer');
				} finally {
					window.setTimeout(cleanup, 60_000);
				}
			}, 400);
		},
		{ once: true },
	);

	document.body.appendChild(iframe);
	iframe.src = blobUrl;
}
