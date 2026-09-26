<template>
	<v-dialog :model-value="modelValue" max-width="460" @update:model-value="(v) => $emit('update:modelValue', v)">
		<v-card class="pos-themed-card share-dialog">
			<v-card-title class="d-flex align-center ga-2 pt-4">
				<v-icon color="primary">mdi-share-variant</v-icon>
				<span>{{ __("Share {0}", [target.name]) }}</span>
			</v-card-title>
			<v-card-subtitle class="pb-2">
				{{ __("Send the PDF with all the details of this document.") }}
			</v-card-subtitle>

			<v-card-text>
				<v-alert v-if="errorMessage" type="error" density="compact" class="mb-3">{{ errorMessage }}</v-alert>

				<v-btn
					v-if="canNativeShare"
					block
					size="large"
					color="primary"
					variant="flat"
					class="text-none mb-3"
					prepend-icon="mdi-share-variant"
					:loading="!pdfFile && pdfLoading"
					:disabled="!pdfFile"
					@click="nativeShare"
				>
					{{ __("Share PDF (WhatsApp, Email, ...)") }}
				</v-btn>

				<div class="share-dialog__grid">
					<v-btn
						variant="tonal"
						color="success"
						class="text-none"
						prepend-icon="mdi-whatsapp"
						:loading="linkLoading"
						:disabled="!shareLink"
						@click="shareWhatsApp"
					>
						WhatsApp
					</v-btn>
					<v-btn
						variant="tonal"
						color="primary"
						class="text-none"
						prepend-icon="mdi-email-outline"
						:loading="linkLoading"
						:disabled="!shareLink"
						@click="shareEmail"
					>
						{{ __("Email") }}
					</v-btn>
					<v-btn
						variant="tonal"
						class="text-none"
						prepend-icon="mdi-link-variant"
						:loading="linkLoading"
						:disabled="!shareLink"
						@click="copyLink"
					>
						{{ copied ? __("Copied") : __("Copy Link") }}
					</v-btn>
					<v-btn
						variant="tonal"
						class="text-none"
						prepend-icon="mdi-download"
						:loading="pdfLoading"
						:disabled="!pdfFile"
						@click="downloadPdf"
					>
						{{ __("Download PDF") }}
					</v-btn>
				</div>

				<p v-if="shareLink" class="text-caption text-medium-emphasis mt-3 mb-0">
					{{ expiresOn
						? __("Anyone with the link can open the PDF until {0}.", [formatDate(expiresOn)])
						: __("Anyone with the link can open the PDF.") }}
				</p>
			</v-card-text>

			<v-card-actions>
				<v-spacer />
				<v-btn variant="text" class="text-none" @click="$emit('update:modelValue', false)">{{ __("Close") }}</v-btn>
			</v-card-actions>
		</v-card>
	</v-dialog>
</template>

<script>
import { ref, watch } from 'vue';
import { fetchDocumentPdfFile, getDocumentShareLink } from '../../../utils/documentShare';
import { formatDisplayDate } from './docStatusUtils';

// WhatsApp, email and the other apps can only carry text + a link from a
// desktop browser, so those buttons send the summary with a public PDF
// link. Where the browser can share files (phones), "Share PDF" hands the
// PDF itself to the system share sheet instead.
export default {
	name: 'ShareDocumentDialog',
	props: {
		modelValue: { type: Boolean, default: false },
		// { doctype, name, printFormat }
		target: { type: Object, required: true },
		// Plain-text summary sent along with the PDF / link.
		text: { type: String, default: '' },
	},
	emits: ['update:modelValue'],
	setup(props) {
		const pdfFile = ref(null);
		const pdfLoading = ref(false);
		const shareLink = ref('');
		const expiresOn = ref(null);
		const linkLoading = ref(false);
		const errorMessage = ref('');
		const copied = ref(false);
		const canNativeShare = ref(false);

		const subject = () => `${props.target.doctype} ${props.target.name}`;
		const messageWithLink = () => [props.text, '', `${__('PDF')}: ${shareLink.value}`].join('\n').trim();

		const prepare = async () => {
			errorMessage.value = '';
			copied.value = false;
			canNativeShare.value = typeof navigator !== 'undefined' && typeof navigator.canShare === 'function';

			// The PDF is fetched up front: navigator.share() must run straight
			// from the click, and generating the PDF there first would outlive
			// the browser's user-gesture window.
			if (!pdfFile.value) {
				pdfLoading.value = true;
				fetchDocumentPdfFile(props.target)
					.then((file) => {
						pdfFile.value = file;
						canNativeShare.value = canNativeShare.value && navigator.canShare({ files: [file] });
					})
					.catch((e) => {
						canNativeShare.value = false;
						errorMessage.value = e?.message || __('Failed to generate PDF');
					})
					.finally(() => {
						pdfLoading.value = false;
					});
			}
			if (!shareLink.value) {
				linkLoading.value = true;
				try {
					const result = await getDocumentShareLink(props.target);
					shareLink.value = result?.url || '';
					expiresOn.value = result?.expires_on || null;
				} catch (e) {
					errorMessage.value = e?.message || __('Failed to create share link');
				} finally {
					linkLoading.value = false;
				}
			}
		};

		watch(
			() => props.modelValue,
			(open) => {
				if (open) prepare();
			},
		);
		watch(
			() => [props.target.doctype, props.target.name, props.target.printFormat],
			() => {
				pdfFile.value = null;
				shareLink.value = '';
				expiresOn.value = null;
			},
		);

		const nativeShare = async () => {
			if (!pdfFile.value) return;
			try {
				await navigator.share({ files: [pdfFile.value], title: subject(), text: props.text });
			} catch (e) {
				if (e?.name !== 'AbortError') errorMessage.value = e?.message || __('Sharing failed');
			}
		};

		const shareWhatsApp = () => {
			window.open(`https://wa.me/?text=${encodeURIComponent(messageWithLink())}`, '_blank', 'noopener');
		};

		const shareEmail = () => {
			const body = messageWithLink().replace(/\*/g, '');
			window.location.href = `mailto:?subject=${encodeURIComponent(subject())}&body=${encodeURIComponent(body)}`;
		};

		const copyLink = async () => {
			try {
				await navigator.clipboard.writeText(shareLink.value);
			} catch {
				const input = document.createElement('textarea');
				input.value = shareLink.value;
				document.body.appendChild(input);
				input.select();
				document.execCommand('copy');
				input.remove();
			}
			copied.value = true;
			setTimeout(() => (copied.value = false), 2000);
		};

		const downloadPdf = () => {
			if (!pdfFile.value) return;
			const url = URL.createObjectURL(pdfFile.value);
			const a = document.createElement('a');
			a.href = url;
			a.download = pdfFile.value.name;
			document.body.appendChild(a);
			a.click();
			a.remove();
			setTimeout(() => URL.revokeObjectURL(url), 10_000);
		};

		return {
			pdfFile,
			pdfLoading,
			shareLink,
			expiresOn,
			linkLoading,
			errorMessage,
			copied,
			canNativeShare,
			nativeShare,
			shareWhatsApp,
			shareEmail,
			copyLink,
			downloadPdf,
			formatDate: formatDisplayDate,
		};
	},
};
</script>

<style scoped>
.share-dialog__grid {
	display: grid;
	grid-template-columns: repeat(2, minmax(0, 1fr));
	gap: 8px;
}
</style>
