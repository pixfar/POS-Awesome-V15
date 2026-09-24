import {
	getOpeningStorage,
	setOpeningStorage,
	getBootstrapSnapshot,
	setBootstrapSnapshot,
} from "../../offline/index";
import { createBootstrapSnapshotFromRegisterData } from "../../offline/bootstrapSnapshot";
import { ensurePosProfile, refreshRegisterPosProfile } from "../../utils/pos_profile";
import { getValidCachedOpeningForCurrentUser } from "./openingCache";
import { useUIStore } from "../stores/uiStore.js";

declare const frappe: any;
declare const __BUILD_VERSION__: string;

const BUILD_VERSION = typeof __BUILD_VERSION__ !== "undefined" ? __BUILD_VERSION__ : null;

export type RegisterBootstrapResult =
	| { source: "cache" | "store" }
	| { source: "server"; registerData: any }
	| { source: "profile"; profile: any }
	| null;

let pending: Promise<RegisterBootstrapResult> | null = null;

/**
 * Make sure uiStore has the POS Profile (and open shift, if any) before a
 * page needs it.
 *
 * Only the Sales shell (Pos.vue) used to load it from the server. A page
 * opened any other way on a browser with no cached opening shift -- typically
 * a deep link straight after login, /login?redirect-to=/app/posapp/... --
 * started with no POS Profile: the item picker never loaded, and Accounts /
 * warehouse defaults stayed empty. The router awaits this before the first
 * page renders, so every page mounts with the profile already in place.
 *
 * Runs at most once per page load; later calls share the same promise.
 */
export function ensureRegisterData(): Promise<RegisterBootstrapResult> {
	if (!pending) {
		pending = loadRegisterData().catch((e) => {
			console.error("Failed to load POS register data", e);
			return null;
		});
	}
	return pending;
}

async function loadRegisterData(): Promise<RegisterBootstrapResult> {
	const uiStore = useUIStore();
	const user = typeof frappe !== "undefined" ? frappe?.session?.user : null;

	if (uiStore.posProfile?.name) return { source: "store" };

	const cached = getValidCachedOpeningForCurrentUser(getOpeningStorage(), user);
	if (cached) {
		uiStore.setRegisterData(cached);
		return { source: "cache" };
	}

	if (!navigator.onLine || !user || user === "Guest") return null;

	const r = await frappe.call({
		method: "posawesome.posawesome.api.shifts.check_opening_shift",
		args: { user },
	});
	if (r?.message) {
		const registerData = await refreshRegisterPosProfile(r.message);
		uiStore.setRegisterData(registerData);
		try {
			setOpeningStorage(registerData);
			setBootstrapSnapshot(
				createBootstrapSnapshotFromRegisterData(registerData, getBootstrapSnapshot(), {
					buildVersion: BUILD_VERSION,
				}),
			);
		} catch (e) {
			console.error("Failed to cache opening data", e);
		}
		return { source: "server", registerData };
	}

	// No open shift: pages outside the Sales shell still need the profile
	// itself (company, warehouse, price lists). Not cached as an opening --
	// the Sales shell still prompts for opening a shift as before.
	const profile = await ensurePosProfile();
	if (profile?.name && !uiStore.posProfile?.name) {
		uiStore.setPosProfile(profile);
		return { source: "profile", profile };
	}
	return null;
}
