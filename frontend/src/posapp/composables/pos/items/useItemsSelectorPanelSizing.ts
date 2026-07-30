import { computed, type CSSProperties, type Ref } from "vue";

type ResponsiveStyleMap = Record<string, string | number | undefined>;

type UseItemsSelectorPanelSizingArgs = {
	isPhone: Ref<boolean>;
	windowWidth: Ref<number>;
	windowHeight: Ref<number>;
	responsiveStyles: Ref<ResponsiveStyleMap>;
};

const PHONE_SELECTOR_HEIGHT =
	"calc(var(--viewport-height) - var(--bottom-safe-space) - 24px)";

export function useItemsSelectorPanelSizing({
	isPhone,
	windowWidth,
	windowHeight,
	responsiveStyles,
}: UseItemsSelectorPanelSizingArgs) {
	const canResizeSelectorPanel = computed(
		() => windowWidth.value >= 1280 && windowHeight.value >= 860,
	);

	const selectorCardStyle = computed<CSSProperties>(() => {
		if (isPhone.value) {
			return {
				height: PHONE_SELECTOR_HEIGHT,
				maxHeight: PHONE_SELECTOR_HEIGHT,
				minHeight: "calc(var(--viewport-height) * 0.46)",
				resize: "none",
				overflow: "auto",
				position: "relative",
				flex: "1 1 auto",
			};
		}

		// Fill remaining shell height above the bottom toolbar.
		// Do not use height:100% here — that ignores the toolbar and causes
		// page-level overflow / double scrolling.
		return {
			height: "auto",
			maxHeight: "none",
			minHeight: 0,
			resize: canResizeSelectorPanel.value ? "vertical" : "none",
			overflow: "hidden",
			position: "relative",
			flex: "1 1 auto",
		};
	});

	return {
		canResizeSelectorPanel,
		selectorCardStyle,
	};
}
