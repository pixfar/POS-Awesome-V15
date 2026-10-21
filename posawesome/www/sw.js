// POS Awesome no longer uses a service worker -- the app works on live data
// only. The old worker served cached pages and assets whenever the server
// was slow, which caused "Invalid Request" (a cached page's stale CSRF token)
// and half-loaded, unresponsive pages.
//
// Browsers that still have it installed re-check this file on their own, so
// it is replaced by this one, which only cleans up: it has no fetch handler
// (every request goes straight to the network), deletes the old caches and
// unregisters itself. Open pages are not reloaded -- they simply stop being
// controlled by it, and the next page load runs without any worker.

self.addEventListener("install", () => {
	self.skipWaiting();
});

self.addEventListener("activate", (event) => {
	event.waitUntil(
		(async () => {
			try {
				const keys = await caches.keys();
				await Promise.all(
					keys.filter((key) => key.startsWith("posawesome-cache-")).map((key) => caches.delete(key)),
				);
			} finally {
				await self.registration.unregister();
			}
		})(),
	);
});
