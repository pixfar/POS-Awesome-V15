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
 * 3. Scrub autofill-friendly `name` tokens (customer, phone, search, …).
 * 4. On focus: briefly set `readonly` then clear it — Chrome attaches its
 *    autofill UI at focus time and skips readonly fields. App menus untouched.
 * 5. Re-apply on DOM mutations and on `focusin`.
 *
 * Scope matches `suppressNativeTooltips`: only `.main-section` and Vuetify's
 * teleported `.v-overlay-container`. Desk chrome outside POS is untouched.
 * True `type="password"` fields are left alone (login / password managers).
 */

const POS_SCOPE = ".main-section, .v-overlay-container";

/** Unknown token — more reliable than "off" against Chrome autofill heuristics. */
export const AUTOCOMPLETE_OFF = "posa-off";

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

/** Names Chrome / Firefox / Edge treat as autofill anchors. */
const AUTOFILL_NAME_RE =
	/^(search|q|query|name|customer|customer[_-]?name|supplier|supplier[_-]?name|email|e-?mail|phone|tel|mobile|mobile[_-]?no|address|street|city|state|zip|postal|warehouse|item|barcode|company|employee|username|user|login|posa_item_search|posa_customer_lookup|posa_field)$/i;

const freshFieldName = () =>
	`posa_${Math.random().toString(36).slice(2, 10)}`;

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

const scrubAutofillName = (
	el: HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement,
	{ rotate = false }: { rotate?: boolean } = {},
) => {
	const currentName = (el.getAttribute("name") || ("name" in el ? el.name : "") || "").trim();
	// Chrome's black history dropdown keys off a stable `name`. Keep names
	// non-heuristic at rest; on focus, rotate so prior typed values never match.
	if (rotate || !currentName || AUTOFILL_NAME_RE.test(currentName)) {
		el.setAttribute("name", freshFieldName());
	}
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

	scrubAutofillName(el, { rotate: false });
};

/**
 * Chrome decides autofill at focus. Readonly inputs are skipped. Set readonly
 * for one frame, then unlock so typing / Vuetify menus still work.
 */
const lockThenUnlockForAutofill = (el: HTMLInputElement | HTMLTextAreaElement) => {
	if (el.getAttribute("data-posa-ro-lock") === "1") {
		return;
	}
	const hadReadonly = el.hasAttribute("readonly") || el.readOnly;
	if (hadReadonly) {
		return;
	}
	el.setAttribute("data-posa-ro-lock", "1");
	el.setAttribute("readonly", "readonly");
	const unlock = () => {
		el.removeAttribute("readonly");
		// Allow a fresh lock on the next focus cycle.
		requestAnimationFrame(() => {
			el.removeAttribute("data-posa-ro-lock");
		});
	};
	// Double rAF: Chrome paints autofill UI after the first frame.
	requestAnimationFrame(() => {
		requestAnimationFrame(unlock);
	});
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
		if (!(target instanceof Element)) {
			return;
		}
		hardenControl(target);
		hardenForm(target);
		if (target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement) {
			if (isHardenableControl(target) && inPosScope(target)) {
				// Break Chrome form-history match for this focus session.
				scrubAutofillName(target, { rotate: true });
				lockThenUnlockForAutofill(target);
			}
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
				if (mutation.attributeName === "autocomplete" || mutation.attributeName === "name") {
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
		attributeFilter: ["autocomplete", "name"],
		childList: true,
		subtree: true,
	});

	return () => {
		observer.disconnect();
		document.removeEventListener("focusin", onFocusIn, true);
	};
}
