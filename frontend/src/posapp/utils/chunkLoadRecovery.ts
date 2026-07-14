import { buildPosAppRecoveryLocation } from "../../loader-utils";

const POSAPP_ROUTE = "/app/posapp";
const CHUNK_RELOAD_KEY = "posa_chunk_reload_once";
const CHUNK_CACHE_RECOVERY_KEY = "posa_chunk_cache_recovery_once";
const CHUNK_RECOVERY_IN_PROGRESS_KEY = "posa_chunk_recovery_in_progress";
const CHUNK_RECOVERY_TERMINAL_KEY = "posa_chunk_recovery_terminal";
const LOADER_RECOVERY_KEY = "posa_loader_chunk_recovery_once";
const CHUNK_RECOVERY_STABLE_DELAY_MS = 3000;
const CHUNK_RELOAD_PARAM = "_posa_chunk_reload";
const CHUNK_CACHE_RECOVERY_PARAM = "_posa_chunk_cache_recovery";
const VERSION_ENDPOINT = "/assets/posawesome/dist/js/version.json";
const FALLBACK_OVERLAY_ID = "posa-boot-fallback-overlay";

function normalizeErrorText(error: unknown): string {
	const message =
		error instanceof Error
			? error.message
			: typeof error === "string"
				? error
				: String(error || "");
	return message.trim().toLowerCase();
}

export function isDynamicImportFailure(error: unknown): boolean {
	const message = normalizeErrorText(error);
	return (
		message.includes("failed to fetch dynamically imported module") ||
		message.includes("loading chunk") ||
		message.includes("chunkloaderror") ||
		message.includes("importing a module script failed") ||
		(message.includes("requested module") &&
			message.includes("does not provide an export named")) ||
		// A deploy landing mid-boot can serve route/layout chunks from a
		// different build than the entry bundle already in memory -- Pinia's
		// module-scope singleton then mismatches across chunks and its (prod-
		// only, since the dev-mode guard is stripped by NODE_ENV=production)
		// internal lookup throws this exact TypeError instead of a normal
		// "chunk load" message. Treat it the same as a stale-chunk failure so
		// it goes through the same reload/cache-clear recovery instead of
		// leaving a blank page.
		(message.includes("cannot read properties of undefined") &&
			message.includes("reading '_s'"))
	);
}

function resetRecoveryState() {
	if (typeof window === "undefined" || !window.sessionStorage) {
		return;
	}
	window.sessionStorage.removeItem(CHUNK_RELOAD_KEY);
	window.sessionStorage.removeItem(CHUNK_CACHE_RECOVERY_KEY);
	window.sessionStorage.removeItem(CHUNK_RECOVERY_IN_PROGRESS_KEY);
	window.sessionStorage.removeItem(CHUNK_RECOVERY_TERMINAL_KEY);
	window.sessionStorage.removeItem(LOADER_RECOVERY_KEY);
}

export function clearChunkRecoveryState() {
	if (typeof window === "undefined" || !window.sessionStorage) {
		return;
	}
	window.sessionStorage.removeItem(CHUNK_RECOVERY_IN_PROGRESS_KEY);
}

export function scheduleChunkRecoveryStateReset() {
	scheduleAfterStableBoot(() => {
		clearChunkRecoveryState();
	});
}

export function scheduleAfterStableBoot(task: () => void | Promise<void>) {
	if (typeof window === "undefined") {
		return;
	}

	window.setTimeout(() => {
		void Promise.resolve(task()).catch((error) => {
			console.warn("Chunk recovery: stable boot task failed", error);
		});
	}, CHUNK_RECOVERY_STABLE_DELAY_MS);
}

export function buildChunkRecoveryLocation(
	locationLike: { pathname?: string; search?: string; hash?: string } | null | undefined,
	param: string,
	token: string | number = Date.now(),
) {
	return buildPosAppRecoveryLocation(locationLike, param, token, POSAPP_ROUTE);
}

function redirectToPosApp(param: string) {
	if (typeof window === "undefined" || !window.location) {
		return false;
	}
	window.location.replace(
		buildChunkRecoveryLocation(window.location, param, Date.now()),
	);
	return true;
}

function hasRecoveryParam(param: string) {
	if (typeof window === "undefined" || !window.location) {
		return false;
	}

	return new URLSearchParams(window.location.search || "").has(param);
}

async function fetchCurrentChunkFileList(): Promise<string[]> {
	try {
		const response = await fetch(`${VERSION_ENDPOINT}?t=${Date.now()}`, {
			cache: "no-store",
		});
		if (!response.ok) {
			return [];
		}
		const payload = await response.json();
		return Array.isArray(payload?.chunkFiles) ? payload.chunkFiles : [];
	} catch (err) {
		console.warn("Chunk recovery: failed to fetch current chunk list", err);
		return [];
	}
}

async function revalidateChunkFiles(chunkFiles: string[]) {
	// Dynamic import() has no equivalent of fetch's `cache` option, so a chunk
	// the browser already has a long-lived (Cache-Control: max-age) HTTP cache
	// entry for is reused as-is even across a full page reload -- unregistering
	// service workers and clearing the Cache API (above) doesn't touch that
	// separate disk-cache layer. Explicitly re-fetching every currently-built
	// chunk with cache:"reload" forces revalidation against the server and
	// refreshes that HTTP cache entry, so the next import() of the same URL
	// picks up the current file instead of a stale, possibly-deleted one.
	await Promise.allSettled(
		chunkFiles.map((url) => fetch(url, { cache: "reload" }).catch(() => null)),
	);
}

async function clearServiceWorkersAndCaches() {
	if (typeof window === "undefined") {
		return;
	}

	try {
		if (
			typeof navigator !== "undefined" &&
			"serviceWorker" in navigator &&
			typeof navigator.serviceWorker.getRegistrations === "function"
		) {
			const registrations = await navigator.serviceWorker.getRegistrations();
			await Promise.all(
				registrations.map(async (registration) => {
					try {
						registration.active?.postMessage({
							type: "CLIENT_FORCE_UNREGISTER",
						});
					} catch {
						// Service worker messaging is best-effort before unregister.
					}
					try {
						registration.waiting?.postMessage({
							type: "CLIENT_FORCE_UNREGISTER",
						});
					} catch {
						// Service worker messaging is best-effort before unregister.
					}
					try {
						registration.installing?.postMessage({
							type: "CLIENT_FORCE_UNREGISTER",
						});
					} catch {
						// Service worker messaging is best-effort before unregister.
					}
					await registration.unregister();
				}),
			);
		}
	} catch (err) {
		console.warn("Chunk recovery: failed to cleanup service workers", err);
	}

	try {
		if (typeof caches !== "undefined") {
			const cacheKeys = await caches.keys();
			await Promise.all(cacheKeys.map((key) => caches.delete(key)));
		}
	} catch (err) {
		console.warn("Chunk recovery: failed to cleanup Cache API", err);
	}

	try {
		window.localStorage?.removeItem("posawesome_version");
		window.localStorage?.removeItem("posawesome_update_dismissed");
		window.localStorage?.removeItem("posawesome_update_last_check");
		window.sessionStorage?.removeItem("posawesome_update_snooze_until");
	} catch (err) {
		console.warn("Chunk recovery: failed to cleanup update keys", err);
	}

	try {
		const chunkFiles = await fetchCurrentChunkFileList();
		if (chunkFiles.length) {
			await revalidateChunkFiles(chunkFiles);
		}
	} catch (err) {
		console.warn("Chunk recovery: failed to revalidate chunk files", err);
	}
}

function showFallbackUI(error: unknown) {
	if (typeof document === "undefined" || !document.body) {
		return;
	}
	if (document.getElementById(FALLBACK_OVERLAY_ID)) {
		return;
	}

	const overlay = document.createElement("div");
	overlay.id = FALLBACK_OVERLAY_ID;
	overlay.setAttribute(
		"style",
		"position:fixed;inset:0;z-index:2147483647;display:flex;align-items:center;" +
			"justify-content:center;background:#fff;font-family:Arial,Helvetica,sans-serif;" +
			"color:#1f2937;text-align:center;padding:24px;",
	);

	const box = document.createElement("div");
	box.setAttribute("style", "max-width:420px;");

	const title = document.createElement("h2");
	title.textContent = "POS Awesome couldn't load";
	title.setAttribute("style", "margin:0 0 12px;font-size:20px;");

	const message = document.createElement("p");
	message.textContent =
		"A newer version of the app is available but your browser is still using older cached files. Automatic recovery couldn't fix this.";
	message.setAttribute("style", "margin:0 0 20px;color:#4b5563;");

	const button = document.createElement("button");
	button.textContent = "Reload page";
	button.setAttribute(
		"style",
		"padding:10px 20px;font-size:14px;color:#fff;background:#2563eb;border:none;" +
			"border-radius:6px;cursor:pointer;",
	);
	button.onclick = () => {
		resetRecoveryState();
		// A plain reload() would keep the recovery query params already on this
		// URL, immediately re-triggering the terminal branch above instead of
		// giving the (now HTTP-cache-revalidated) chunks a clean attempt.
		const url = new URL(window.location.href);
		url.searchParams.delete(CHUNK_RELOAD_PARAM);
		url.searchParams.delete(CHUNK_CACHE_RECOVERY_PARAM);
		window.location.replace(url.toString());
	};

	box.appendChild(title);
	box.appendChild(message);
	box.appendChild(button);
	overlay.appendChild(box);
	document.body.appendChild(overlay);

	console.error("Chunk recovery: showing terminal fallback UI", error);
}

export async function recoverFromChunkLoadError(
	error: unknown,
	source = "runtime",
): Promise<boolean> {
	if (!isDynamicImportFailure(error)) {
		return false;
	}

	if (typeof window === "undefined" || !window.sessionStorage) {
		return false;
	}

	const urlAlreadyRetried = hasRecoveryParam(CHUNK_RELOAD_PARAM);
	const urlAlreadyRecovered = hasRecoveryParam(CHUNK_CACHE_RECOVERY_PARAM);
	if (
		urlAlreadyRecovered ||
		window.sessionStorage.getItem(CHUNK_RECOVERY_TERMINAL_KEY) === "1"
	) {
		window.sessionStorage.setItem(CHUNK_RECOVERY_TERMINAL_KEY, "1");
		window.sessionStorage.removeItem(CHUNK_RECOVERY_IN_PROGRESS_KEY);
		showFallbackUI(error);
		return false;
	}

	if (
		window.sessionStorage.getItem(CHUNK_RECOVERY_IN_PROGRESS_KEY) === "1"
	) {
		return true;
	}

	window.sessionStorage.setItem(CHUNK_RECOVERY_IN_PROGRESS_KEY, "1");

	const alreadyRetried =
		urlAlreadyRetried ||
		window.sessionStorage.getItem(CHUNK_RELOAD_KEY) === "1";
	if (!alreadyRetried) {
		window.sessionStorage.setItem(CHUNK_RELOAD_KEY, "1");
		console.warn("Chunk recovery: reloading POS app after chunk failure", {
			source,
			error,
		});
		return redirectToPosApp(CHUNK_RELOAD_PARAM);
	}

	const alreadyRecovered =
		urlAlreadyRecovered ||
		window.sessionStorage.getItem(CHUNK_CACHE_RECOVERY_KEY) === "1";
	if (!alreadyRecovered) {
		window.sessionStorage.setItem(CHUNK_CACHE_RECOVERY_KEY, "1");
		console.warn(
			"Chunk recovery: clearing SW/cache after repeated chunk failure",
			{ source, error },
		);
		await clearServiceWorkersAndCaches();
		return redirectToPosApp(CHUNK_CACHE_RECOVERY_PARAM);
	}

	window.sessionStorage.setItem(CHUNK_RECOVERY_TERMINAL_KEY, "1");
	window.sessionStorage.removeItem(CHUNK_RECOVERY_IN_PROGRESS_KEY);
	console.error("Chunk recovery: automatic recovery exhausted", {
		source,
		error,
	});
	showFallbackUI(error);
	return false;
}
