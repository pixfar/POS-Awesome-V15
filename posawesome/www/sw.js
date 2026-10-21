// Install-only service worker: it exists so POS Awesome can be installed as
// an app (PWA). It deliberately has NO fetch handler -- every request goes
// straight to the network, so pages and data are always live and nothing is
// ever served from a cache. (The previous worker cached pages/assets; a
// cached page's stale CSRF token caused "Invalid Request", and cached
// fallbacks left pages half-loaded on a slow server.)
//
// On activation it deletes the caches that older versions left behind.

self.addEventListener("install", () => {
	self.skipWaiting();
});

self.addEventListener("activate", (event) => {
	event.waitUntil(
		(async () => {
			const keys = await caches.keys();
			await Promise.all(
				keys.filter((key) => key.startsWith("posawesome-cache-")).map((key) => caches.delete(key)),
			);
			await self.clients.claim();
		})(),
	);
});
