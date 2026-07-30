import { computed, ref, watch } from "vue";
import { useResponsive } from "../core/useResponsive";

/**
 * Shared Sales/Purchase compact layout: below 1100px show one pane at a time
 * with a bottom dock (Browse / Cart / primary action).
 */
export function useCompactTransactionPanel(defaultPanel: "invoice" | "selector" = "invoice") {
	const responsive = useResponsive();
	const isCompact = computed(() => responsive.isCompact.value);
	const compactPanel = ref<"invoice" | "selector">(defaultPanel);

	watch(isCompact, (compact) => {
		if (!compact) {
			compactPanel.value = defaultPanel;
		}
	});

	const showInvoicePanel = computed(
		() => !isCompact.value || compactPanel.value === "invoice",
	);
	const showSelectorPanel = computed(
		() => !isCompact.value || compactPanel.value === "selector",
	);

	const invoiceCols = computed(() => (isCompact.value ? 12 : 7));
	const selectorCols = computed(() => (isCompact.value ? 12 : 5));

	const setPanel = (panel: "invoice" | "selector") => {
		compactPanel.value = panel;
	};

	return {
		responsive,
		responsiveStyles: responsive.responsiveStyles,
		isCompact,
		isPhone: responsive.isPhone,
		compactPanel,
		showInvoicePanel,
		showSelectorPanel,
		invoiceCols,
		selectorCols,
		setPanel,
	};
}
