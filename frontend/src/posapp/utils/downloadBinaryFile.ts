declare const frappe: any;

function resolveBaseUrl(): string {
	if (frappe?.urllib?.get_base_url) {
		return frappe.urllib.get_base_url();
	}
	return window.location.origin;
}

/**
 * Fetch a whitelisted method that responds with frappe.response.type = "pdf"
 * (or any binary download) and save it via the browser's download flow,
 * instead of navigating there directly -- keeps the POS app in place and
 * surfaces server errors (frappe.throw) instead of showing a broken tab.
 */
export async function downloadBinaryFile(
	method: string,
	args: Record<string, string | number | undefined> = {},
): Promise<void> {
	const params = new URLSearchParams();
	for (const [key, value] of Object.entries(args)) {
		if (value !== undefined && value !== null && value !== '') {
			params.set(key, String(value));
		}
	}

	const url = `${resolveBaseUrl()}/api/method/${method}?${params.toString()}`;
	const response = await fetch(url, {
		method: 'GET',
		credentials: 'include',
	});

	if (!response.ok) {
		throw new Error(`Failed to generate file (${response.status})`);
	}

	const disposition = response.headers.get('content-disposition') || '';
	const match = disposition.match(/filename="?([^";]+)"?/);
	const filename = match?.[1] ?? 'download.pdf';

	const blob = await response.blob();
	const blobUrl = URL.createObjectURL(blob);

	const link = document.createElement('a');
	link.href = blobUrl;
	link.download = filename;
	document.body.appendChild(link);
	link.click();
	link.remove();
	setTimeout(() => URL.revokeObjectURL(blobUrl), 60_000);
}
