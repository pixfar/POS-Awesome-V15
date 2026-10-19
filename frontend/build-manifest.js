const DIST_BASE_URL = "/assets/posawesome/dist/js/";
const STATIC_ENTRY_NAMES = new Set(["loader"]);

// Entries loaded through a stable file name, but emitted with a content hash
// plus a one-line stable shim that re-exports them (see buildEntryShim).
export const SHIMMED_ENTRY_NAMES = new Set(["posawesome"]);

export function getEntryFileName(chunkInfo) {
	return STATIC_ENTRY_NAMES.has(chunkInfo?.name) ? "[name].js" : "[name]-[hash].js";
}

// Lazy-loaded chunks import shared code from the main entry ("./posawesome.js"
// before). That bare URL is cached by the browser while the loader imports
// "posawesome.js?v=<build>", so after a deploy chunks got a stale second copy
// of the entry and minified exports resolved to the wrong functions (e.g. a
// time formatter returning a status colour). Chunks now import the hashed
// "posawesome-<hash>.js" -- always fresh -- and the stable "posawesome.js"
// the loader, service worker and offline fallbacks request just re-exports
// it, so every path shares one module instance.
export function buildEntryShim(hashedFileName) {
	return `export * from "./${String(hashedFileName).replace(/^.*\//, "")}";\n`;
}

function toPublicAssetUrl(fileName) {
	return `${DIST_BASE_URL}${String(fileName || "").replace(/^\/+/, "")}`;
}

function toVersionedPublicAssetUrl(fileName, version) {
	const url = toPublicAssetUrl(fileName);
	return version ? `${url}?v=${encodeURIComponent(version)}` : url;
}

function getChunkFileName(bundle, chunkName) {
	const match = Object.values(bundle || {}).find(
		(entry) => entry?.type === "chunk" && entry?.name === chunkName,
	);
	return match?.fileName || null;
}

export function buildVersionPayload(version, bundle = {}) {
	const offlineIndexFile = getChunkFileName(bundle, "offline/index");

	return {
		version,
		assets: {
			loader: toVersionedPublicAssetUrl("loader.js", version),
			posawesome: toVersionedPublicAssetUrl("posawesome.js", version),
			css: toVersionedPublicAssetUrl("posawesome.css", version),
			offlineIndex: offlineIndexFile
				? toPublicAssetUrl(offlineIndexFile)
				: toPublicAssetUrl("offline/index.js"),
		},
	};
}
