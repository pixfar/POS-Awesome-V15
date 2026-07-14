declare const frappe: any;

/**
 * Uploads a single file to Frappe's standard upload endpoint and returns the
 * resulting file_url, for attaching to an "Attach" field on a doc that may
 * not exist yet (uploaded as a private file with no doctype/docname).
 */
export async function uploadFile(file: File): Promise<string> {
	const formData = new FormData();
	formData.append('file', file);
	formData.append('is_private', '1');

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
