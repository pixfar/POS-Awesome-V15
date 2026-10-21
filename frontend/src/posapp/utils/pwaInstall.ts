import { ref } from "vue";

/**
 * "Install App" support. Chrome fires `beforeinstallprompt` once the page is
 * installable (manifest + service worker); we keep that event so a menu
 * entry can open the install dialog, since the address-bar icon is easy to
 * miss. Not available in Incognito/Guest windows or once already installed.
 */
let deferredPrompt: any = null;
export const canInstallApp = ref(false);

export function initPwaInstall() {
	if (typeof window === "undefined" || (window as any).__posaPwaInstallInit) return;
	(window as any).__posaPwaInstallInit = true;

	if (!document.querySelector('link[rel="manifest"]')) {
		const link = document.createElement("link");
		link.rel = "manifest";
		link.href = "/manifest.json";
		document.head.appendChild(link);
	}

	window.addEventListener("beforeinstallprompt", (event: Event) => {
		event.preventDefault();
		deferredPrompt = event;
		canInstallApp.value = true;
	});
	window.addEventListener("appinstalled", () => {
		deferredPrompt = null;
		canInstallApp.value = false;
	});
}

export async function promptInstallApp() {
	if (!deferredPrompt) return false;
	const promptEvent = deferredPrompt;
	deferredPrompt = null;
	canInstallApp.value = false;
	promptEvent.prompt();
	const choice = await promptEvent.userChoice.catch(() => null);
	return choice?.outcome === "accepted";
}
