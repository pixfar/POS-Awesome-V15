const CACHE_PREFIX = "posawesome-cache-";
const VERSION_URL = "/assets/posawesome/dist/js/version.json";
const DEFAULT_CACHE_VERSION = "default";
const MAX_CACHE_ITEMS = 1000;

const STATIC_PRECACHE_URLS = [
	"/app/posapp",
	"/assets/posawesome/dist/js/posapp/workers/itemWorker.js",
	"/assets/posawesome/dist/js/libs/dexie.min.js",
	"/manifest.json",
	"/offline.html",
];

// A connection that is "up" but barely moving must never freeze the app: every
// network request made here gives up after these limits and falls back to the
// cache instead of waiting forever.
const NAVIGATION_TIMEOUT_MS = 8000;
const ASSET_TIMEOUT_MS = 6000;
const VERSION_TIMEOUT_MS = 4000;
// Retry a failed version.json lookup at most this often (it used to be
// re-fetched, and awaited, on every single asset request after a failure).
const VERSION_RETRY_MS = 60000;
// Trimming the cache walks every entry -- do it in the background, not per request.
const CACHE_TRIM_INTERVAL_MS = 5 * 60 * 1000;

// Vite build output is content-hashed (e.g. "BomList-D1a4bu-a.js"): a given
// URL never changes content, so serve it from cache without a network round trip.
const HASHED_ASSET_RE = /^\/assets\/posawesome\/dist\/.+-[A-Za-z0-9_-]{8}\.(?:m?js|css)$/;
const NEVER_CACHE_PATHS = ["/assets/posawesome/dist/js/version.json", "/sw.js"];

function fetchWithTimeout(request, timeoutMs, init = {}) {
	const controller = typeof AbortController !== "undefined" ? new AbortController() : null;
	const timer = setTimeout(() => controller && controller.abort(), timeoutMs);
	return fetch(request, controller ? { ...init, signal: controller.signal } : init).finally(() =>
		clearTimeout(timer),
	);
}

function buildVersionedAssetUrl(url, version) {
	return `${url}?v=${encodeURIComponent(version || DEFAULT_CACHE_VERSION)}`;
}

function getPrecacheUrls(version, assets = {}) {
	const offlineIndexUrl =
		typeof assets.offlineIndex === "string" && assets.offlineIndex
			? assets.offlineIndex
			: buildVersionedAssetUrl("/assets/posawesome/dist/js/offline/index.js", version);
	return [
		buildVersionedAssetUrl("/assets/posawesome/dist/js/loader.js", version),
		buildVersionedAssetUrl("/assets/posawesome/dist/js/posawesome.css", version),
		buildVersionedAssetUrl("/assets/posawesome/dist/js/posawesome.js", version),
		offlineIndexUrl,
		...STATIC_PRECACHE_URLS,
	];
}

let cachedCacheName = null;
let cacheNameInFlight = null;
let fallbackCacheName = null;
let lastVersionAttempt = 0;
let lastCacheTrim = 0;

async function findExistingCacheName() {
	const keys = (await caches.keys()).filter((key) => key.startsWith(CACHE_PREFIX));
	return keys.length ? keys[keys.length - 1] : null;
}

function trimCacheIfDue(cacheName) {
	const now = Date.now();
	if (now - lastCacheTrim < CACHE_TRIM_INTERVAL_MS) return Promise.resolve();
	lastCacheTrim = now;
	return caches
		.open(cacheName)
		.then(enforceCacheLimit)
		.catch(() => {});
}
let currentVersion = null;
let currentAssets = {};

async function precacheUrls(cacheName, version, assets = {}) {
	const cache = await caches.open(cacheName);
	await Promise.all(
		getPrecacheUrls(version, assets).map(async (url) => {
			try {
				const resp = await fetch(url);
				if (resp && resp.ok) {
					await cache.put(url, resp.clone());
				}
			} catch (err) {
				console.warn("SW install failed to fetch", url, err);
			}
		}),
	);
	await enforceCacheLimit(cache);
	return cache;
}

async function cleanupObsoleteCaches(activeCacheName) {
	const keys = await caches.keys();
	await Promise.all(keys.filter((key) => key !== activeCacheName).map((key) => caches.delete(key)));
}

function postVersionMessage(target) {
	if (!currentVersion) return;
	const message = {
		type: "SW_VERSION_INFO",
		version: currentVersion,
		timestamp: Number(currentVersion),
	};
	if (target && typeof target.postMessage === "function") {
		target.postMessage(message);
	}
}

function extractBuildVersion(payload) {
	const version = payload?.version || payload?.buildVersion;
	return typeof version === "string" && version.trim().length ? version.trim() : DEFAULT_CACHE_VERSION;
}

function extractBuildAssets(payload) {
	return payload?.assets && typeof payload.assets === "object" ? payload.assets : {};
}

// Listen for version check messages
self.addEventListener("message", (event) => {
	const payload = event.data || {};
	if (payload.type === "CHECK_VERSION") {
		if (event.ports && event.ports[0]) {
			postVersionMessage(event.ports[0]);
		} else if (event.source) {
			postVersionMessage(event.source);
		}
		return;
	}
	if (payload.type === "SKIP_WAITING") {
		self.skipWaiting();
		return;
	}
	if (payload.type === "REFRESH_CACHE_VERSION") {
		const target = (event.ports && event.ports[0]) || event.source || null;
		const task = refreshCacheVersion(target);
		if (typeof event.waitUntil === "function") {
			event.waitUntil(task);
		}
		return;
	}
	if (payload.type === "CLIENT_FORCE_UNREGISTER") {
		const task = forceUnregisterServiceWorker();
		if (typeof event.waitUntil === "function") {
			event.waitUntil(task);
		}
	}
});

async function resolveBuildMetadata(forceRefresh = false) {
	if (forceRefresh) {
		currentVersion = null;
		currentAssets = {};
	}
	try {
		const response = await fetchWithTimeout(VERSION_URL, VERSION_TIMEOUT_MS, { cache: "no-store" });
		if (response && response.ok) {
			const payload = await response.json();
			currentVersion = extractBuildVersion(payload);
			currentAssets = extractBuildAssets(payload);
			return {
				version: currentVersion,
				assets: currentAssets,
			};
		}
	} catch (err) {
		console.warn("SW: failed to fetch build version", err);
	}
	return {
		version: DEFAULT_CACHE_VERSION,
		assets: currentAssets || {},
	};
}

async function getCacheName(forceRefresh = false, resolvedMetadata = null) {
	if (forceRefresh) {
		cachedCacheName = null;
		cacheNameInFlight = null;
	}
	if (cachedCacheName) {
		return cachedCacheName;
	}
	if (cacheNameInFlight) {
		return cacheNameInFlight;
	}
	if (!forceRefresh && !resolvedMetadata && fallbackCacheName && Date.now() - lastVersionAttempt < VERSION_RETRY_MS) {
		return fallbackCacheName;
	}
	cacheNameInFlight = (async () => {
		lastVersionAttempt = Date.now();
		try {
			const metadata = resolvedMetadata || (await resolveBuildMetadata(forceRefresh));
			const version = metadata?.version || DEFAULT_CACHE_VERSION;
			if (version !== DEFAULT_CACHE_VERSION) {
				cachedCacheName = `${CACHE_PREFIX}${version}`;
				fallbackCacheName = null;
				return cachedCacheName;
			}
			// Version unknown (offline / server slow): keep using the newest cache
			// we already have rather than an empty "default" one.
			fallbackCacheName = (await findExistingCacheName()) || `${CACHE_PREFIX}${DEFAULT_CACHE_VERSION}`;
			return fallbackCacheName;
		} finally {
			cacheNameInFlight = null;
		}
	})();
	return cacheNameInFlight;
}

async function enforceCacheLimit(cache) {
	const keys = await cache.keys();
	if (keys.length > MAX_CACHE_ITEMS) {
		const excess = keys.length - MAX_CACHE_ITEMS;
		await Promise.all(keys.slice(0, excess).map((key) => cache.delete(key)));
	}
}

async function refreshCacheVersion(target) {
	const metadata = await resolveBuildMetadata(true);
	const activeCacheName = await getCacheName(true, metadata);
	await precacheUrls(activeCacheName, metadata.version, metadata.assets);
	await cleanupObsoleteCaches(activeCacheName);
	postVersionMessage(target);
	const clients = await self.clients.matchAll({
		type: "window",
		includeUncontrolled: true,
	});
	clients.forEach(postVersionMessage);
	return activeCacheName;
}

async function forceUnregisterServiceWorker() {
	cachedCacheName = null;
	cacheNameInFlight = null;
	currentVersion = null;
	currentAssets = {};
	const keys = await caches.keys();
	await Promise.all(keys.map((key) => caches.delete(key)));
	await self.registration.unregister();
}

self.addEventListener("install", (event) => {
	self.skipWaiting();
	event.waitUntil(
		(async () => {
			const metadata = await resolveBuildMetadata();
			const cacheName = await getCacheName(false, metadata);
			await precacheUrls(cacheName, metadata.version, metadata.assets);
		})(),
	);
});

self.addEventListener("activate", (event) => {
	event.waitUntil(
		(async () => {
			const metadata = await resolveBuildMetadata();
			const activeCacheName = await getCacheName(false, metadata);
			await precacheUrls(activeCacheName, metadata.version, metadata.assets);
			await cleanupObsoleteCaches(activeCacheName);
			const cache = await caches.open(activeCacheName);
			await enforceCacheLimit(cache);
			await self.clients.claim();
			const clients = await self.clients.matchAll({ type: "window", includeUncontrolled: true });
			clients.forEach(postVersionMessage);
		})(),
	);
});

self.addEventListener("fetch", (event) => {
	if (event.request.method !== "GET") return;

	const url = new URL(event.request.url);
	if (url.protocol !== "http:" && url.protocol !== "https:") return;
	if (url.origin !== self.location.origin) return;
	if (event.request.url.includes("socket.io")) return;
	if (NEVER_CACHE_PATHS.includes(url.pathname)) return;

	const assetDestinations = ["style", "script", "worker", "font", "image"];
	const isAssetRequest = assetDestinations.includes(event.request.destination);
	const isPosawesomeAsset = url.pathname.startsWith("/assets/posawesome/");
	const isNavigation = event.request.mode === "navigate";

	if (!isNavigation && !isAssetRequest && !isPosawesomeAsset) {
		return;
	}

	if (isNavigation) {
		event.respondWith(
			(async () => {
				try {
					return await fetchWithTimeout(event.request, NAVIGATION_TIMEOUT_MS);
				} catch (err) {
					const cached = await caches.match(event.request, { ignoreSearch: true });
					if (cached) {
						return cached;
					}

					const appShell = await caches.match("/app/posapp");
					if (appShell) {
						return appShell;
					}

					const offlinePage = await caches.match("/offline.html");
					if (offlinePage) {
						return offlinePage;
					}

					return Response.error();
				}
			})(),
		);
		return;
	}

	const hasVersionQuery = url.searchParams.has("v");
	// Hashed build chunks and ?v=<build>-versioned files never change for a
	// given URL -- cache first, network only on a miss.
	const isImmutable = HASHED_ASSET_RE.test(url.pathname) || (isPosawesomeAsset && hasVersionQuery);

	const putInCache = (cacheName, copy) =>
		caches
			.open(cacheName)
			.then((cache) => cache.put(event.request, copy))
			.then(() => trimCacheIfDue(cacheName))
			.catch((cacheError) => console.warn("SW cache put failed", cacheError));

	event.respondWith(
		(async () => {
			if (isImmutable) {
				const cached = await caches.match(event.request);
				if (cached) {
					return cached;
				}
			}

			const cacheNamePromise = getCacheName().catch(() => `${CACHE_PREFIX}${DEFAULT_CACHE_VERSION}`);
			try {
				const response = await fetchWithTimeout(event.request, ASSET_TIMEOUT_MS);
				// Resolve the cache name off the response path -- the asset is
				// returned as soon as it arrives, never held for version.json.
				const cacheableTypes = ["basic", "default", "cors"];
				if (response && response.ok && response.status === 200 && cacheableTypes.includes(response.type)) {
					const copy = response.clone();
					event.waitUntil(cacheNamePromise.then((name) => putInCache(name, copy)).catch(() => {}));
				}
				return response;
			} catch (networkError) {
				const cached = await caches.match(event.request);
				if (cached) {
					return cached;
				}

				if (!hasVersionQuery) {
					const fallback = await caches.match(event.request, {
						ignoreSearch: true,
					});
					if (fallback) {
						return fallback;
					}
				}
				return Response.error();
			}
		})(),
	);
});
