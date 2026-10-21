import { watch, type Ref } from "vue";
import { useToastStore } from "../../stores/toastStore";

/**
 * Create screens show validation errors in an alert at the end of the form.
 * On phones / the installed app (compact layout, < 1100px) that alert sits
 * under the fixed bottom bar, so the cashier never sees why Submit did
 * nothing. Also show each new error as a toast there.
 */
export function useMobileErrorToast(errorMessage: Ref<string | null | undefined>) {
	const toastStore = useToastStore();
	watch(errorMessage, (message) => {
		if (!message || typeof window === "undefined" || window.innerWidth >= 1100) return;
		toastStore.show({ title: String(message), color: "error" });
	});
}
