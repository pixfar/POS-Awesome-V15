/**
 * Disable browser autofill / native suggestion dropdowns inside the POS app.
 *
 * Chrome (and others) often ignore `autocomplete="off"` when the field label or
 * nearby text looks like a name, phone, address, warehouse, employee, etc. The
 * POS already has its own search menus (Vuetify autocomplete), so the browser's
 * saved-form overlay is never wanted.
 *
 * Strategy:
 * 1. Force a non-standard `autocomplete` token on every text-like control —
 *    browsers treat unknown tokens as "do not autofill" more reliably than "off".
 * 2. Mark password-manager ignore flags so LastPass / 1Password / Bitwarden
 *    stay out of the way too.
 * 3. Re-apply on DOM mutations and on `focusin` (Chrome decides at focus time).
 *
 * Scope matches `suppressNativeTooltips`: only `.main-section` and Vuetify's
 * teleported `.v-overlay-container`. Desk chrome outside POS is untouched.
 */

const POS_SCOPE = ".main-section, .v-overlay-container";

/** Unknown token — more reliable than "off" against Chrome autofill heuristics. */
const AUTOCOMPLETE_OFF = "posa-off";

const TEXT_INPUT_TYPES = new Set([
	"",
	"text",
	"search",
	"tel",
	"url",
	"email",
	"number",
	"date",
	"datetime-local",
	"month",
	"week",
	"time",
]);

const inPosScope = (el: Element): boolean =>
	typeof el.closest === "function" && el.closest(POS_SCOPE) != null;

const isHardenableControl = (el: Element): el is HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement => {
	if (el instanceof HTMLTextAreaElement || el instanceof HTMLSelectElement) {
		return true;
	}
	if (!(el instanceof HTMLInputElement)) {
		return false;
	}
	const type = (el.getAttribute("type") || el.type || "text").toLowerCase();
	// Leave true password fields alone (none in POS today; keep for safety).
	if (type === "password") {
		return false;
	}
	if (
		type === "hidden" ||
		type === "checkbox" ||
		type === "radio" ||
		type === "file" ||
		type === "button" ||
		type === "submit" ||
		type === "reset" ||
		type === "image" ||
		type === "range" ||
		type === "color"
	) {
		return false;
	}
	return TEXT_INPUT_TYPES.has(type) || !el.hasAttribute("type");
};

const hardenControl = (el: Element) => {
	if (!inPosScope(el) || !isHardenableControl(el)) {
		return;
	}

	if (el.getAttribute("autocomplete") !== AUTOCOMPLETE_OFF) {
		el.setAttribute("autocomplete", AUTOCOMPLETE_OFF);
	}
	if (el.getAttribute("autocorrect") !== "off") {
		el.setAttribute("autocorrect", "off");
	}
	if (el.getAttribute("autocapitalize") !== "off") {
		el.setAttribute("autocapitalize", "off");
	}
	if (el.getAttribute("spellcheck") !== "false") {
		el.setAttribute("spellcheck", "false");
	}
	// Password-manager / autofill-extension ignore flags
	if (el.getAttribute("data-lpignore") !== "true") {
		el.setAttribute("data-lpignore", "true");
	}
	if (!el.hasAttribute("data-1p-ignore")) {
		el.setAttribute("data-1p-ignore", "true");
	}
	if (el.getAttribute("data-bwignore") !== "true") {
		el.setAttribute("data-bwignore", "true");
	}
	if (el.getAttribute("data-form-type") !== "other") {
		el.setAttribute("data-form-type", "other");
	}

	// Chrome matches autofill on common name/id tokens ("search", "customer",
	// …). Give POS search inputs a stable non-matching name when empty or
	// still carrying a browser-friendly name.
	if (el instanceof HTMLInputElement) {
		const currentName = (el.getAttribute("name") || el.name || "").toLowerCase();
		if (
			!currentName ||
			currentName === "search" ||
			currentName === "q" ||
			currentName === "query" ||
			currentName === "customer" ||
			currentName === "email" ||
			currentName === "phone" ||
			currentName === "tel"
		) {
			el.setAttribute("name", "posa_field");
		}
	}
};

const hardenForm = (el: Element) => {
	if (!(el instanceof HTMLFormElement) || !inPosScope(el)) {
		return;
	}
	if (el.getAttribute("autocomplete") !== AUTOCOMPLETE_OFF) {
		el.setAttribute("autocomplete", AUTOCOMPLETE_OFF);
	}
};

const hardenWithin = (node: Node) => {
	if (!(node instanceof Element)) {
		return;
	}
	hardenForm(node);
	hardenControl(node);
	node.querySelectorAll?.("form, input, textarea, select").forEach((child) => {
		hardenForm(child);
		hardenControl(child);
	});
};

/**
 * @param _rootEl unused; kept for call-site compatibility with the tooltip suppressor.
 * @returns disposer that disconnects the observer and focus listener.
 */
export function installBrowserAutocompleteSuppressor(
	_rootEl?: HTMLElement | null,
): () => void {
	if (typeof document === "undefined") {
		return () => {};
	}

	try {
		document.querySelectorAll(POS_SCOPE).forEach(hardenWithin);
	} catch {
		/* no-op */
	}

	const onFocusIn = (event: FocusEvent) => {
		const target = event.target;
		if (target instanceof Element) {
			hardenControl(target);
			hardenForm(target);
		}
	};

	document.addEventListener("focusin", onFocusIn, true);

	if (typeof MutationObserver === "undefined") {
		return () => {
			document.removeEventListener("focusin", onFocusIn, true);
		};
	}

	const observer = new MutationObserver((mutations) => {
		for (const mutation of mutations) {
			if (mutation.type === "attributes" && mutation.target instanceof Element) {
				// Vuetify / Vue may rewrite autocomplete after mount — put ours back.
				if (mutation.attributeName === "autocomplete") {
					hardenControl(mutation.target);
					hardenForm(mutation.target);
				}
			} else if (mutation.type === "childList") {
				mutation.addedNodes.forEach(hardenWithin);
			}
		}
	});

	observer.observe(document.body, {
		attributes: true,
		attributeFilter: ["autocomplete"],
		childList: true,
		subtree: true,
	});

	return () => {
		observer.disconnect();
		document.removeEventListener("focusin", onFocusIn, true);
	};
}
