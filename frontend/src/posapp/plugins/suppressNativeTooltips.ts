/**
 * Suppress browser-native `title` tooltips inside the POS app.
 *
 * Vuetify stamps a native HTML `title` attribute onto several field and menu
 * elements (the field label on `.v-field` / the menu-icon, resolved item titles
 * on list rows, selection text, etc.). On hover the browser renders these as a
 * dark native tooltip showing raw field content ("unusual content") on top of
 * the search dropdowns and lists. The POS uses the themed `<v-tooltip>` overlay
 * for every tooltip it actually wants, so no native `title` tooltip is ever
 * intentional here.
 *
 * Coverage: Vuetify teleports its overlays (menus, tooltips, dropdown lists) into
 * a `.v-overlay-container` that it appends to `document.body` — i.e. OUTSIDE the
 * POS mount (`.main-section`). So we observe the whole document but only strip
 * `title` from elements that live inside the POS root (`.main-section`) or inside
 * a Vuetify overlay container (`.v-overlay-container`). Everything else on the
 * page — the surrounding Frappe desk chrome (navbar, sidebar, breadcrumbs) that
 * legitimately uses native `title` tooltips — is left untouched.
 *
 * It does not alter any value, model, filtering or selection behaviour — it only
 * removes a presentational DOM attribute.
 */

const POS_SCOPE = ".main-section, .v-overlay-container";

const inPosScope = (el: Element): boolean =>
	typeof el.closest === "function" && el.closest(POS_SCOPE) != null;

const stripTitle = (el: Element) => {
	if (el.hasAttribute("title") && inPosScope(el)) {
		el.removeAttribute("title");
	}
};

const stripTitlesWithin = (node: Node) => {
	if (!(node instanceof Element)) return;
	stripTitle(node);
	node.querySelectorAll?.("[title]").forEach(stripTitle);
};

/**
 * @param _rootEl unused; kept for call-site compatibility.
 * @returns disposer that disconnects the observer.
 */
export function installNativeTooltipSuppressor(
	_rootEl?: HTMLElement | null,
): () => void {
	if (typeof document === "undefined" || typeof MutationObserver === "undefined") {
		return () => {};
	}

	// Clear anything already present in POS-owned regions.
	try {
		document.querySelectorAll(`${POS_SCOPE}`).forEach(stripTitlesWithin);
	} catch {
		/* no-op */
	}

	const observer = new MutationObserver((mutations) => {
		for (const mutation of mutations) {
			if (mutation.type === "attributes" && mutation.target instanceof Element) {
				stripTitle(mutation.target);
			} else if (mutation.type === "childList") {
				mutation.addedNodes.forEach(stripTitlesWithin);
			}
		}
	});

	observer.observe(document.body, {
		attributes: true,
		attributeFilter: ["title"],
		childList: true,
		subtree: true,
	});

	return () => observer.disconnect();
}
