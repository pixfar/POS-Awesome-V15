/**
 * Frappe's own per-user Notification Log (mentions, assignments, shares,
 * energy points, alerts -- the same feed Desk's bell icon shows), surfaced
 * inside POS Awesome's notification bell alongside its session-only toast
 * history (see toastStore.ts).
 *
 * **`init()`** fetches the current backlog once and subscribes to the
 * `notification` realtime event Frappe emits whenever a new Notification Log
 * entry is inserted for this user (`NotificationLog.after_insert` ->
 * `frappe.publish_realtime("notification", ..., user=self.for_user)`), so a
 * new entry appears live without polling. Safe to call more than once --
 * only the first call does anything.
 *
 * Unlike `toastStore`'s ephemeral, session-only history, these entries are
 * real Frappe documents shared with Desk -- `markAllRead()` marks them read
 * on the server via Frappe's own whitelisted `mark_all_as_read`, it never
 * deletes them, so "Clear All" in the bell only clears the POS's own toast
 * history; read Notification Log entries simply fade to a muted color.
 */
import { defineStore } from "pinia";
import { ref } from "vue";

export interface NotificationLogEntry {
	id: string;
	title: string;
	detail: string;
	color: string;
	icon: string;
	timestamp: number;
	read: boolean;
	link?: string;
}

const TYPE_ICONS: Record<string, string> = {
	Mention: "mdi-at",
	Assignment: "mdi-account-check-outline",
	"Energy Point": "mdi-flash-outline",
	Share: "mdi-share-variant-outline",
	Alert: "mdi-bell-ring-outline",
};

function normalize(row: any): NotificationLogEntry {
	const isRead = !!row.read;
	return {
		id: row.name,
		title: row.subject || row.type || "Notification",
		detail:
			row.document_type && row.document_name
				? `${row.document_type}: ${row.document_name}`
				: "",
		color: isRead ? "muted" : "primary",
		icon: TYPE_ICONS[row.type] || "mdi-bell-outline",
		timestamp: row.creation ? new Date(row.creation).getTime() : Date.now(),
		read: isRead,
		link: row.link || undefined,
	};
}

export const useNotificationLogStore = defineStore("notificationLog", () => {
	const logs = ref<NotificationLogEntry[]>([]);
	const unreadCount = ref(0);
	let initialized = false;

	async function fetchLogs() {
		if (typeof frappe === "undefined" || !frappe.call) return;
		try {
			const r = await frappe.call({
				method: "posawesome.posawesome.api.notification_log.get_recent_notifications",
				args: { limit: 20 },
			});
			const data = r?.message || {};
			logs.value = (data.notifications || []).map(normalize);
			unreadCount.value = Number(data.unread_count || 0);
		} catch (error) {
			console.warn("Failed to fetch notification log", error);
		}
	}

	async function markAllRead() {
		if (!unreadCount.value) return;
		try {
			await frappe.call({
				method: "frappe.desk.doctype.notification_log.notification_log.mark_all_as_read",
			});
			logs.value = logs.value.map((entry) => ({ ...entry, read: true, color: "muted" }));
			unreadCount.value = 0;
		} catch (error) {
			console.warn("Failed to mark notification log as read", error);
		}
	}

	async function markOneRead(name: string) {
		const entry = logs.value.find((row) => row.id === name);
		if (!entry || entry.read) return;
		try {
			await frappe.call({
				method: "frappe.desk.doctype.notification_log.notification_log.mark_as_read",
				args: { docname: name },
			});
			entry.read = true;
			entry.color = "muted";
			unreadCount.value = Math.max(0, unreadCount.value - 1);
		} catch (error) {
			console.warn("Failed to mark notification as read", error);
		}
	}

	function init() {
		if (initialized) return;
		initialized = true;
		fetchLogs();
		if (typeof frappe !== "undefined" && frappe.realtime) {
			frappe.realtime.on("notification", () => {
				fetchLogs();
			});
		}
	}

	return { logs, unreadCount, fetchLogs, markAllRead, markOneRead, init };
});
