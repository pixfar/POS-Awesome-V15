import {
	getOpeningStorage,
	setOpeningStorage,
	setPrintTemplate,
	setTermsAndConditions,
	getBootstrapSnapshot,
	setBootstrapSnapshot,
} from "../offline/index";
import { createBootstrapSnapshotFromRegisterData } from "../offline/bootstrapSnapshot";

declare const __BUILD_VERSION__: string;
declare const frappe: any;

const BUILD_VERSION =
	typeof __BUILD_VERSION__ !== "undefined" ? __BUILD_VERSION__ : null;

async function cachePrintTemplateAndTerms(profile: any) {
	if (!profile || typeof frappe === "undefined" || !navigator.onLine) return;

	try {
		setPrintTemplate("");
	} catch (e) {
		console.error("Failed to reset print template", e);
	}

	try {
		const termsName = profile.tc_name || profile.terms_and_conditions;
		if (termsName) {
			const tc = await frappe.call({
				method: "frappe.client.get_value",
				args: {
					doctype: "Terms and Conditions",
					fieldname: "terms",
					filters: { name: termsName },
				},
			});
			if (tc.message && tc.message.terms) {
				setTermsAndConditions(tc.message.terms);
			}
		}
	} catch (e) {
		console.error("Failed to fetch terms and conditions", e);
	}
}

function hasProfileChanged(currentProfile: any, nextProfile: any) {
	if (!nextProfile) return false;
	if (!currentProfile) return true;
	if (currentProfile.name !== nextProfile.name) return true;
	if (currentProfile.modified && nextProfile.modified) {
		return currentProfile.modified !== nextProfile.modified;
	}
	if (currentProfile.warehouse !== nextProfile.warehouse) return true;
	return false;
}

function updateOpeningStorageProfile(profile: any) {
	const cached = getOpeningStorage() as any;
	if (cached?.pos_profile) {
		const updated = { ...cached, pos_profile: profile };
		setOpeningStorage(updated);
		setBootstrapSnapshot(
			createBootstrapSnapshotFromRegisterData(
				updated,
				getBootstrapSnapshot(),
				{ buildVersion: BUILD_VERSION },
			),
		);
	}
}

export async function ensurePosProfile(forceRefresh = false) {
	if (typeof frappe === "undefined") {
		const cached = getOpeningStorage() as any;
		return cached?.pos_profile || null;
	}

	if (navigator.onLine) {
		try {
			const res = await frappe.call({
				method: "posawesome.posawesome.api.utils.get_active_pos_profile",
				args: { user: frappe.session.user },
			});
			if (res.message) {
				const current =
					frappe.boot?.pos_profile ||
					(getOpeningStorage() as any)?.pos_profile;
				if (forceRefresh || hasProfileChanged(current, res.message)) {
					frappe.boot.pos_profile = res.message;
					updateOpeningStorageProfile(res.message);
					await cachePrintTemplateAndTerms(res.message);
				}
				return res.message;
			}
		} catch (e) {
			console.error("Failed to refresh active POS profile", e);
		}
	}

	const bootProfile = frappe?.boot?.pos_profile;
	if (bootProfile) {
		await cachePrintTemplateAndTerms(bootProfile);
		return bootProfile;
	}

	const cached = getOpeningStorage() as any;
	if (cached?.pos_profile) {
		await cachePrintTemplateAndTerms(cached.pos_profile);
		return cached.pos_profile;
	}

	return null;
}

export async function refreshRegisterPosProfile(registerData: any) {
	const profile = await ensurePosProfile(true);
	if (!profile || !registerData) {
		return registerData;
	}
	return { ...registerData, pos_profile: profile };
}
