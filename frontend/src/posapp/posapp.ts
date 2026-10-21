import { createApp } from "vue";
// @ts-ignore
import vuetify from "./plugins/vuetify";
import "@mdi/font/css/materialdesignicons.css";
import "@fontsource/roboto/100.css";
import "@fontsource/roboto/300.css";
import "@fontsource/roboto/400.css";
import "@fontsource/roboto/500.css";
import "@fontsource/roboto/700.css";
import "@fontsource/roboto/900.css";
// @ts-ignore
import Dexie from "dexie/dist/dexie.mjs";
import VueDatePicker from "@vuepic/vue-datepicker";
import "@vuepic/vue-datepicker/dist/main.css";
import "../../../posawesome/public/css/rtl.css";
import "../style.css";
import "./styles/theme.css";
import eventBus from "./bus";
import themePlugin from "./plugins/theme";
import { installNativeTooltipSuppressor } from "./plugins/suppressNativeTooltips";
import { formatDisplayTimeAmPm } from "./components/pos/shared/docStatusUtils";
import { pinia } from "./stores";
import { useToastStore } from "./stores/toastStore";
import { useSocketStore } from "./stores/socketStore";
import { useNotificationLogStore } from "./stores/notificationLogStore";
import { useUpdateStore } from "./stores/updateStore";
import { createPosAppRouter } from "./router";
import {
	installGlobalErrorHandlers,
	isBenignGlobalError,
} from "./utils/errorReporting";
import {
	clearChunkRecoveryState,
	isDynamicImportFailure,
	recoverFromChunkLoadError,
	scheduleAfterStableBoot,
	scheduleChunkRecoveryStateReset,
} from "./utils/chunkLoadRecovery";
import { finalizePendingBundleActivation } from "./utils/bundleVersionActivation";
import { reconcileBuildChangeOnStartup } from "./utils/buildCacheReconciler";
import { ONLINE_ONLY_MODE } from "./config/runtime";
import { installCsrfGuard } from "./utils/csrfGuard";
import { initPromise, isOffline } from "../offline";
import App from "./App.vue";
// @ts-ignore
import {
	attachProfilerHelpers,
	initLongTaskObserver,
	isPerfEnabled,
} from "./utils/perf.js";

declare const __BUILD_VERSION__: string;

attachProfilerHelpers();

// Expose Dexie globally for libraries that expect a global Dexie instance
if (typeof window !== "undefined" && !(window as any).Dexie) {
	(window as any).Dexie = Dexie;
}

if (typeof frappe === "undefined") {
	console.error("Frappe is not defined");
} else {
	frappe.provide("frappe.PosApp");
	// Stale CSRF token -> refresh + retry once, instead of "Invalid Request"
	// on every save until the page is reloaded.
	installCsrfGuard();
}

export async function initPosStorage() {
	if (ONLINE_ONLY_MODE) {
		return;
	}
	await initPromise;
}

export async function runPosBootSync() {
	if (ONLINE_ONLY_MODE) {
		return;
	}
	const buildVersion =
		typeof __BUILD_VERSION__ !== "undefined" ? __BUILD_VERSION__ : null;
	await reconcileBuildChangeOnStartup({
		runtimeBuildVersion: buildVersion,
		isOnline: !isOffline(),
	});
}

async function startOptionalRuntimeServices() {
	const socketStore = useSocketStore();
	socketStore.init();

	const notificationLogStore = useNotificationLogStore();
	notificationLogStore.init();

	// The app works on live data only, so it no longer installs a service
	// worker: one that served cached pages/assets on a slow connection caused
	// "Invalid Request" (stale CSRF token) and half-loaded, unresponsive
	// pages. Remove any worker / caches left from earlier versions.
	void removeLegacyServiceWorker();

	// "New version available" banner: a plain reload picks up the new build.
	useUpdateStore().setReloadAction(() => window.location.reload());
}

async function removeLegacyServiceWorker() {
	try {
		if ("serviceWorker" in navigator && navigator.serviceWorker.getRegistrations) {
			const registrations = await navigator.serviceWorker.getRegistrations();
			await Promise.all(registrations.map((registration) => registration.unregister()));
		}
		if (typeof caches !== "undefined") {
			const keys = await caches.keys();
			await Promise.all(
				keys.filter((key) => key.startsWith("posawesome-cache-")).map((key) => caches.delete(key)),
			);
		}
	} catch (error) {
		console.warn("Failed to remove legacy service worker", error);
	}
}

class PosAppController {
	$parent: any;
	page: any;
	app: any;
	router: any;
	routerHistory: any;
	$el: any;
	disposeTooltipSuppressor: (() => void) | null = null;

	constructor(input: any) {
		const parent = input?.parent || input;
		this.$parent = $(document);
		this.page = parent?.page || parent;
		this.app = null;
		this.make_body();
	}

	make_body() {
		this.$el = this.$parent.find(".main-section");
	}

	async initializeApp() {
		// Vuetify instance is now imported from plugins/vuetify.ts
		this.app = createApp(App);
		// Global template helper for the list "Time" columns (creation-based,
		// AM/PM), available in every component template without per-file imports.
		this.app.config.globalProperties.$posTimeAmPm = formatDisplayTimeAmPm;
		const { router, history } = createPosAppRouter();
		this.router = router;
		this.routerHistory = history;
		this.app.component("VueDatePicker", VueDatePicker);
		this.app.use(pinia);
		this.app.use(this.router);
		this.app.use(eventBus);
		this.app.use(vuetify);
		this.app.use(themePlugin, { vuetify });

		this.app.config.errorHandler = (
			err: any,
			_instance: any,
			info: string,
		) => {
			if (isDynamicImportFailure(err)) {
				void recoverFromChunkLoadError(err, "vue-error-handler");
				return;
			}

			if (!isBenignGlobalError(err)) {
				console.error("Global Error:", err, info);
				const toastStore = useToastStore();
				toastStore.show({
					message: `An unexpected error occurred: ${err?.message || err}`,
					color: "error",
					timeout: 5000,
				});
			}
		};

		installGlobalErrorHandlers(this.app);

		this.app.mount(this.$el[0]);
		this.disposeTooltipSuppressor = installNativeTooltipSuppressor(this.$el[0]);
		clearChunkRecoveryState();
		void this.router.isReady().finally(() => {
			scheduleChunkRecoveryStateReset();
			scheduleAfterStableBoot(() => {
				void finalizePendingBundleActivation();
				void startOptionalRuntimeServices();
			});
		});

		if (isPerfEnabled()) {
			initLongTaskObserver("posapp");
		}

		return this;
	}

	unmount() {
		if (this.disposeTooltipSuppressor) {
			this.disposeTooltipSuppressor();
			this.disposeTooltipSuppressor = null;
		}
		if (this.app) {
			// Clean up router to prevent global navigation interference
			if (this.router) {
				// Remove all route guards and listeners
				this.router.beforeEachCbs = [];
				this.router.afterEachCbs = [];
			}

			if (
				this.routerHistory &&
				typeof this.routerHistory.destroy === "function"
			) {
				this.routerHistory.destroy();
			} else if (
				this.router &&
				this.router.options &&
				this.router.options.history &&
				typeof this.router.options.history.destroy === "function"
			) {
				this.router.options.history.destroy();
			}

			this.app.unmount();
			this.app = null;
			this.router = null;
			this.routerHistory = null;
			console.info("POS App unmounted");
		}
	}

	setup_header() {}
}

export async function mountPosApp(pageRef: any) {
	if (pageRef?.$PosApp) {
		return pageRef.$PosApp;
	}

	const instance = new PosAppController(pageRef);
	await instance.initializeApp();
	if (pageRef) {
		pageRef.$PosApp = instance;
	}
	return instance;
}

frappe.PosApp.posapp = class extends PosAppController {
	constructor(pageRef: any) {
		super(pageRef);
		void this.initializeApp();
	}
};
