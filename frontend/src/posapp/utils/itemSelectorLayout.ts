/**
 * Utility functions for responsive item card layout.
 */

/**
 * Calculates the number of columns based on the ITEMS PANEL container width
 * (not window width). Thresholds are tuned so each card stays at least 120px wide.
 */
export const getCardColumns = (containerWidth: number): number => {
    if (containerWidth <= 250) return 1;
    if (containerWidth <= 420) return 2;
    if (containerWidth <= 620) return 3;
    if (containerWidth <= 820) return 4;
    return 5;
};

/**
 * Calculates the gap between cards based on container width.
 */
export const getCardGap = (width: number): number => {
    if (width <= 768) {
        return 10;
    }
    if (width <= 1200) {
        return 12;
    }
    return 16;
};

/**
 * Calculates the padding for the card container based on container width.
 */
export const getCardPadding = (width: number): number => {
    if (width <= 768) {
        return 10;
    }
    if (width <= 1200) {
        return 12;
    }
    return 16;
};
