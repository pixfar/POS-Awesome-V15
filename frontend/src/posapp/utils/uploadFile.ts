declare const frappe: any;

/**
 * Uploads a single file to Frappe's standard upload endpoint and returns the
 * resulting file_url, for attaching to an "Attach" field on a doc that may
 * not exist yet (no doctype/docname). Private by default; pass
 * `{ isPrivate: false }` for a public file anyone with the link can open.
 */
export async function uploadFile(file: File, options: { isPrivate?: boolean } = {}): Promise<string> {
	const isPrivate = options.isPrivate ?? true;
	const formData = new FormData();
	formData.append('file', file);
	formData.append('is_private', isPrivate ? '1' : '0');

	const response = await fetch('/api/method/upload_file', {
		method: 'POST',
		headers: { 'X-Frappe-CSRF-Token': frappe?.csrf_token || '' },
		body: formData,
	});

	if (!response.ok) {
		throw new Error('File upload failed');
	}

	const json = await response.json();
	const fileUrl = json?.message?.file_url;
	if (!fileUrl) {
		throw new Error('File upload did not return a file URL');
	}
	return fileUrl;
}
