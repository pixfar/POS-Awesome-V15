import { ref, computed, onMounted, onUnmounted, nextTick } from "vue";
import _ from "lodash";
import {
	getCardColumns,
	getCardGap,
	getCardPadding,
} from "../../../utils/itemSelectorLayout.js";

type SelectorLayoutOptions = {
	resizeDebounce?: number;
	loadVisibleItems?: () => void;
};

/**
 * Manages the layout metrics and resize behavior for the ItemsSelector component.
 * Handles calculation of grid columns, card dimensions, and overflow detection.
 */
export function useItemSelectorLayout(options: SelectorLayoutOptions = {}) {
	const {
		resizeDebounce = 100,
		loadVisibleItems,
	} = options;

	// State
	const windowWidth = ref(window.innerWidth);
	const isOverflowing = ref(false);
	const itemsContainerRef = ref<any>(null);
	const scrollThrottle = ref<number | null>(null);

	// Track the actual pixel width of the items panel via ResizeObserver.
	// Falls back to an estimate (55 % of window) when the element isn't bound yet.
	const observedContainerWidth = ref(0);
	let _resizeObserver: ResizeObserver | null = null;

	const setContainerElement = (el: HTMLElement | null) => {
		if (_resizeObserver) {
			_resizeObserver.disconnect();
			_resizeObserver = null;
		}
		if (!el) {
			observedContainerWidth.value = 0;
			return;
		}
		observedContainerWidth.value = el.clientWidth;
		_resizeObserver = new ResizeObserver((entries) => {
			if (entries[0]) {
				observedContainerWidth.value = entries[0].contentRect.width;
			}
		});
		_resizeObserver.observe(el);
	};

	// Use observed width when available, fall back to 55 % window estimate
	// (items panel is roughly that fraction of the full screen in POS layout).
	const cardContainerWidth = computed(() => {
		if (observedContainerWidth.value > 0) return observedContainerWidth.value;
		if (itemsContainerRef.value?.$el) return itemsContainerRef.value.$el.clientWidth;
		return windowWidth.value * 0.55;
	});

	// Computed Metrics — all driven by actual container width
	const cardColumns = computed(() => getCardColumns(cardContainerWidth.value));
	const cardGap = computed(() => getCardGap(windowWidth.value));
	const cardPadding = computed(() => getCardPadding(windowWidth.value));

	// Row heights = image + text content + padding, with a small equal buffer top/bottom.
	const cardRowHeight = computed(() => {
		const cols = cardColumns.value;
		if (cols >= 5) return 158;
		if (cols === 4) return 178;
		if (cols === 3) return 210;
		return 225;
	});

	const cardSlotHeight = computed(() => cardRowHeight.value + cardGap.value);
	const cardSlotWidth = computed(() => cardColumnWidth.value + cardGap.value);

	const cardColumnWidth = computed(() => {
		const columns = Math.max(1, cardColumns.value);
		const containerWidth = cardContainerWidth.value || 0;
		if (!containerWidth) return 180;

		const gapTotal = cardGap.value * (columns - 1);
		const paddingTotal = cardPadding.value * 2;
		const available = Math.max(0, containerWidth - gapTotal - paddingTotal);
		const width = Math.floor(available / columns);
		// Allow cards as narrow as 120 px to support 5-column layout
		return Math.max(120, width);
	});

	// Actions
	const updateWindowWidth = () => {
		windowWidth.value = window.innerWidth;
	};

	const scheduleCardMetricsUpdate = _.debounce(() => {
		updateWindowWidth();
		if (itemsContainerRef.value) {
			// legacy ref path — update observed width if bound
		}
		checkItemContainerOverflow();
	}, resizeDebounce);

	const getItemsContainerElement = (): HTMLElement | null => {
		if (!itemsContainerRef.value) return null;
		return (itemsContainerRef.value.$el ||
			itemsContainerRef.value) as HTMLElement | null;
	};

	const checkItemContainerOverflow = () => {
		const el = getItemsContainerElement();
		if (!el) {
			isOverflowing.value = false;
			return;
		}

		const containerHeight = parseFloat(
			getComputedStyle(el).getPropertyValue("--container-height"),
		);
		if (isNaN(containerHeight)) {
			isOverflowing.value = false;
			return;
		}

		const stickyHeader = el
			.closest(".dynamic-padding")
			?.querySelector(".sticky-header") as HTMLElement | null;
		const headerHeight = stickyHeader ? stickyHeader.offsetHeight : 0;
		const availableHeight = containerHeight - headerHeight;

		if (availableHeight > 0) {
			el.style.maxHeight = `${availableHeight}px`;
			isOverflowing.value = el.scrollHeight > availableHeight;
		}
	};

	const onListScroll = (event: Event) => {
		if (scrollThrottle.value) return;

		scrollThrottle.value = requestAnimationFrame(() => {
			try {
				const el = event.target as HTMLElement | null;
				if (!el) return;
				// Only treat this as "scrolled near the bottom" if the content
				// actually overflows the container — otherwise a page whose
				// items all fit on screen would look "at the bottom" from the
				// very first render and trigger an auto-advance nobody asked for.
				const hasOverflow = el.scrollHeight > el.clientHeight + 1;
				if (hasOverflow && el.scrollTop + el.clientHeight >= el.scrollHeight - 50) {
					if (typeof loadVisibleItems === "function") {
						loadVisibleItems();
					}
				}
			} catch (error: unknown) {
				console.error("Error in list scroll handler:", error);
			} finally {
				scrollThrottle.value = null;
			}
		});
	};

	// Lifecycle
	onMounted(() => {
		window.addEventListener("resize", scheduleCardMetricsUpdate);
		nextTick(() => {
			updateWindowWidth();
			checkItemContainerOverflow();
		});
	});

	onUnmounted(() => {
		window.removeEventListener("resize", scheduleCardMetricsUpdate);
		if (scrollThrottle.value) {
			cancelAnimationFrame(scrollThrottle.value);
		}
		scheduleCardMetricsUpdate.cancel();
		if (_resizeObserver) {
			_resizeObserver.disconnect();
			_resizeObserver = null;
		}
	});

	return {
		// Refs
		windowWidth,
		isOverflowing,
		itemsContainerRef,

		// Methods
		setContainerElement,

		// Computed
		cardColumns,
		cardGap,
		cardPadding,
		cardRowHeight,
		cardSlotHeight,
		cardSlotWidth,
		cardColumnWidth,

		// Methods
		checkItemContainerOverflow,
		scheduleCardMetricsUpdate,
		onListScroll,
	};
}
