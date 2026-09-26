import { buildDocumentPdfUrl } from './openDocumentPdfPrint';

declare const frappe: any;
declare const __: (_text: string, _args?: any[]) => string;

export type ShareTarget = {
	doctype: string;
	name: string;
	printFormat?: string | null;
};

type SummaryField = { label?: string; value?: unknown; href?: string };

export type ShareSummary = {
	title?: string;
	subtitle?: string;
	status?: string;
	metaFields?: SummaryField[];
	totals?: SummaryField[];
};

const fileSafeName = (name: string) => String(name).replace(/[\s/\\]+/g, '-');

/** The same PDF the Print button produces, as a File for the native share sheet / download. */
export async function fetchDocumentPdfFile(target: ShareTarget): Promise<File> {
	const url = buildDocumentPdfUrl({
		doctype: target.doctype,
		name: target.name,
		printFormat: target.printFormat,
		noLetterhead: 1,
	});
	const response = await fetch(url, { credentials: 'include', headers: { Accept: 'application/pdf' } });
	if (!response.ok) {
		throw new Error(`Failed to generate PDF (${response.status})`);
	}
	const blob = await response.blob();
	return new File([blob], `${fileSafeName(target.name)}.pdf`, { type: 'application/pdf' });
}

/** Public (share-key) PDF link anyone can open without logging in, until it expires. */
export async function getDocumentShareLink(
	target: ShareTarget,
): Promise<{ url: string; expires_on: string | null }> {
	const { message } = await frappe.call({
		method: 'posawesome.posawesome.api.document_share.get_document_share_link',
		args: { doctype: target.doctype, name: target.name, print_format: target.printFormat || undefined },
	});
	return { url: `${window.location.origin}${message.path}`, expires_on: message.expires_on };
}

const isShown = (value: unknown) => {
	const text = value === null || value === undefined ? '' : String(value).trim();
	return text && text !== '—';
};

/** Plain-text summary of a detail page (heading, status, meta fields, totals) for WhatsApp/email. */
export function buildShareText(summary: ShareSummary): string {
	const company = frappe?.boot?.sysdefaults?.company;
	const lines: string[] = [];
	const heading = [summary.subtitle, summary.title].filter(isShown).join(' ');
	if (heading) lines.push(`*${heading}*`);
	if (company) lines.push(String(company));
	if (isShown(summary.status)) lines.push(`${__('Status')}: ${summary.status}`);

	const fieldLines = (fields?: SummaryField[]) =>
		(fields || [])
			.filter((f) => f?.label && isShown(f.value) && !f.href)
			.map((f) => `${f.label}: ${String(f.value).trim()}`);

	const meta = fieldLines(summary.metaFields);
	if (meta.length) lines.push('', ...meta);
	const totals = fieldLines(summary.totals);
	if (totals.length) lines.push('', ...totals);
	return lines.join('\n');
}
