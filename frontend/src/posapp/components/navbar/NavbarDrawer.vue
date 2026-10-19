<template>
	<v-navigation-drawer
		v-model="drawerOpen"
		:rail="mini && !docked"
		:expand-on-hover="!docked"
		width="240"
		:class="['drawer-custom', { 'drawer-visible': drawerOpen, 'drawer-docked': docked }, rtlClasses]"
		@mouseleave="handleMouseLeave"
		:temporary="!docked"
		:location="isRtl ? 'right' : 'left'"
		:scrim="docked ? false : scrimColor"
	>
		<div class="drawer-shell">
			<div>
				<!-- Pin: keep the menu docked beside the page (wide screens only). -->
				<div v-if="!mini && canDock" class="drawer-toolbar">
					<span class="drawer-toolbar__title">{{ __("Menu") }}</span>
					<v-btn
						size="small"
						variant="text"
						density="comfortable"
						:icon="pinned ? 'mdi-pin' : 'mdi-pin-outline'"
						:title="pinned ? __('Unpin menu') : __('Keep menu open')"
						:aria-pressed="pinned ? 'true' : 'false'"
						:class="['drawer-pin-btn', { 'drawer-pin-btn--active': pinned }]"
						data-test="drawer-pin-toggle"
						@click="togglePinned"
					/>
				</div>
				<v-list density="compact" nav v-model:selected="activeItem" selected-class="active-item">
					<template v-for="(item, index) in items" :key="item.text">
						<!-- Item with sub-menu -->
						<v-list-group v-if="item.children && item.children.length" :value="item.text">
							<template v-slot:activator="{ props: groupProps }">
								<v-list-item
									v-bind="groupProps"
									class="drawer-item"
									active-class="active-item"
								>
									<template v-slot:prepend>
										<v-icon class="drawer-icon">{{ item.icon }}</v-icon>
									</template>
									<v-list-item-title class="drawer-item-title">{{ item.text }}</v-list-item-title>
								</v-list-item>
							</template>
							<v-list-item
								v-for="child in item.children"
								:key="child.text"
								:to="child.to"
								@click="handleItemClick"
								class="drawer-item drawer-item--child"
								active-class="active-item"
							>
								<template v-slot:prepend>
									<v-icon class="drawer-icon" size="18">{{ child.icon }}</v-icon>
								</template>
								<v-list-item-title class="drawer-item-title">{{ child.text }}</v-list-item-title>
							</v-list-item>
						</v-list-group>

						<!-- Plain item -->
						<v-list-item
							v-else
							:value="index"
							:to="item.to"
							@click="handleItemClick"
							class="drawer-item"
							active-class="active-item"
						>
							<template v-slot:prepend>
								<v-icon class="drawer-icon">{{ item.icon }}</v-icon>
							</template>
							<v-list-item-title class="drawer-item-title">{{ item.text }}</v-list-item-title>
						</v-list-item>
					</template>
				</v-list>
				<!-- Sport section, hidden by default -->
				<div v-if="showSport">
					<!-- Sport content goes here -->
				</div>
			</div>

			<div class="drawer-footer" data-test="drawer-footer-settings">
				<div
					class="drawer-user-card"
					:class="{ 'drawer-user-card--mini': mini }"
				>
					<div class="drawer-user-card__identity">
						<div
							class="drawer-user-card__avatar"
							aria-hidden="true"
						>
							{{ userInitials }}
						</div>
						<div v-if="!mini" class="drawer-user-card__meta">
							<span class="drawer-user-card__name">
								{{ currentUserInfo.fullname }}
							</span>
							<span class="drawer-user-card__hint">
								{{ __("Signed in") }}
							</span>
						</div>
					</div>
					<button
						type="button"
						class="drawer-user-card__logout"
						data-test="drawer-logout-action"
						:title="__('Logout')"
						@click="handleLogoutClick"
					>
						<v-icon size="18">mdi-logout</v-icon>
						<span v-if="!mini">{{ __("Logout") }}</span>
					</button>
				</div>
			</div>
		</div>
	</v-navigation-drawer>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRtl } from "../../composables/core/useRtl";

defineOptions({
	name: "NavbarDrawer",
});

const props = defineProps({
	drawer: Boolean,
	company: String,
	companyImg: String,
	items: Array,
	item: Number,
	isDark: Boolean,
});

const emit = defineEmits(["update:drawer", "update:item", "logout"]);

const currentUserInfo = computed(() => {
	const info = frappe?.user_info?.(frappe?.session?.user) || {};
	return {
		fullname: info.fullname || frappe?.session?.user || "",
	};
});

const userInitials = computed(() => {
	const name = String(currentUserInfo.value.fullname || "").trim();
	if (!name) return "?";
	const parts = name.split(/\s+/).filter(Boolean);
	if (parts.length === 1) {
		return parts[0].slice(0, 2).toUpperCase();
	}
	return (
		(parts[0][0] || "") + (parts[parts.length - 1][0] || "")
	).toUpperCase();
});

const { isRtl, rtlClasses } = useRtl();

// Pinned menu: docked beside the page instead of floating over it, so moving
// to another page is one click. Remembered per browser; only on screens wide
// enough to give up the room, smaller ones keep the overlay menu.
const PIN_STORAGE_KEY = "posawesome_drawer_pinned";
const DOCK_MIN_WIDTH = 1025; // matches the 240px drawer width rule below

function readPinned() {
	try {
		return localStorage.getItem(PIN_STORAGE_KEY) === "1";
	} catch {
		return false;
	}
}

const pinned = ref(readPinned());
const canDock = ref(window.innerWidth >= DOCK_MIN_WIDTH);
const docked = computed(() => pinned.value && canDock.value);

const mini = ref(false);
const drawerOpen = ref(props.drawer || docked.value);
const activeItem = ref(props.item);
const showSport = ref(true);
let closeTimeout = null;

const scrimColor = computed(() => {
	// Use an opaque background in light mode so that
	// underlying content doesn't show through the drawer
	return props.isDark ? true : "rgba(255,255,255,1)";
});

watch(
	() => props.drawer,
	(val) => {
		drawerOpen.value = val;
		if (val) {
			mini.value = false;
		}
	},
);

// Only the floating menu locks page scrolling; a docked one sits beside it.
function syncBodyScroll() {
	document.body.style.overflow = drawerOpen.value && !docked.value ? "hidden" : "";
}

watch(drawerOpen, (val) => {
	syncBodyScroll();
	emit("update:drawer", val);
});

watch(docked, (val) => {
	if (val) {
		drawerOpen.value = true;
		mini.value = false;
	}
	syncBodyScroll();
});

function handleResize() {
	canDock.value = window.innerWidth >= DOCK_MIN_WIDTH;
}

onMounted(() => {
	window.addEventListener("resize", handleResize);
	// Opened docked on load: let the parent's v-model know.
	if (drawerOpen.value !== props.drawer) {
		emit("update:drawer", drawerOpen.value);
	}
	syncBodyScroll();
});

onBeforeUnmount(() => {
	window.removeEventListener("resize", handleResize);
	document.body.style.overflow = "";
});

function togglePinned() {
	pinned.value = !pinned.value;
	try {
		localStorage.setItem(PIN_STORAGE_KEY, pinned.value ? "1" : "0");
	} catch {
		// Storage unavailable (private mode): the pin lasts for this visit.
	}
}

watch(
	() => props.item,
	(val) => {
		activeItem.value = val;
	},
);

watch(activeItem, (val) => {
	emit("update:item", val);
});

function handleMouseLeave() {
	if (!drawerOpen.value || docked.value) return;
	clearTimeout(closeTimeout);
	closeTimeout = setTimeout(() => {
		drawerOpen.value = false;
		mini.value = true;
	}, 250);
}

function handleItemClick() {
	// Close drawer after selection if mobile
	if (!docked.value && window.innerWidth < 1024) {
		closeDrawer();
	}
}

function handleLogoutClick() {
	emit("logout");
	closeDrawer();
}

function closeDrawer() {
	drawerOpen.value = false;
	mini.value = true;
}
</script>

<style scoped>
/* Custom styling for the navigation drawer */
.drawer-custom {
	background-color: var(--surface-secondary, #ffffff);
	transition: var(--transition-normal, all 0.3s ease);
	z-index: 1005 !important; /* Higher than navbar but lower than dialogs */
}

.drawer-shell {
	height: 100%;
	display: flex;
	flex-direction: column;
	justify-content: space-between;
}

/* Styling for the header section of the expanded navigation drawer */
.drawer-header {
	display: flex;
	align-items: center;
	height: 52px;
	padding: 0 12px;
	background: linear-gradient(135deg, #f8f9fa 0%, #e3f2fd 100%);
	border-bottom: 1px solid rgba(0, 0, 0, 0.1);
}

/* Styling for the header section of the mini navigation drawer */
.drawer-header-mini {
	display: flex;
	justify-content: center;
	align-items: center;
	height: 52px;
	background: linear-gradient(135deg, #f8f9fa 0%, #e3f2fd 100%);
	border-bottom: 1px solid rgba(0, 0, 0, 0.1);
}

/* Styling for the company name text within the drawer header */
.drawer-company {
	margin-left: 10px;
	flex: 1;
	min-width: 0;
	font-weight: 600;
	font-size: 0.8125rem;
	line-height: 1.25;
	color: var(--pos-text-primary);
	font-family: "Roboto", sans-serif;
	overflow: hidden;
	display: -webkit-box;
	-webkit-line-clamp: 2;
	-webkit-box-orient: vertical;
}

/* Styling for icons within the navigation drawer list items: neutral, the
   active page's icon takes the primary colour (see .active-item). */
.drawer-icon {
	font-size: 20px;
	color: var(--pos-menu-icon);
}

/* Styling for the title text of navigation drawer list items */
.drawer-item-title {
	margin-left: 0;
	font-weight: 500;
	font-size: 0.8125rem;
	line-height: 1.25;
	color: var(--pos-text-primary) !important;
	font-family: "Roboto", sans-serif;
	white-space: normal;
	overflow: visible;
	text-overflow: unset;
}

/* Vuetify reserves 32px after icons — tighten to a normal gap */
.drawer-custom :deep(.v-list-item) {
	padding-inline: 8px !important;
	min-height: 36px;
	column-gap: 0;
}

.drawer-custom :deep(.v-list-item__prepend) {
	margin-inline-end: 0 !important;
}

.drawer-custom
	:deep(.v-list-item__prepend > .v-icon ~ .v-list-item__spacer),
.drawer-custom
	:deep(.v-list-item__prepend > .v-badge ~ .v-list-item__spacer),
.drawer-custom
	:deep(.v-list-item__prepend > .v-tooltip ~ .v-list-item__spacer) {
	width: 8px !important;
}

.drawer-custom
	:deep(.v-list-item__append > .v-icon ~ .v-list-item__spacer),
.drawer-custom
	:deep(.v-list-item__append > .v-badge ~ .v-list-item__spacer),
.drawer-custom
	:deep(.v-list-item__append > .v-tooltip ~ .v-list-item__spacer) {
	width: 4px !important;
}

.drawer-custom :deep(.v-list-item-title) {
	overflow: visible;
	text-overflow: unset;
	white-space: normal;
}

/* Sub-menu items sit indented under their group, inside its guide line. */
.drawer-custom :deep(.drawer-item--child) {
	padding-inline-start: 14px !important;
}

/* Menu header with the pin button */
.drawer-toolbar {
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding: 6px 8px 2px 16px;
}

.drawer-toolbar__title {
	font-size: 0.7rem;
	font-weight: 700;
	letter-spacing: 0.08em;
	text-transform: uppercase;
	color: var(--pos-label-text);
}

.drawer-pin-btn {
	color: var(--pos-menu-icon) !important;
}

.drawer-pin-btn--active {
	color: var(--pos-accent-teal) !important;
	background: color-mix(in srgb, var(--pos-primary) 10%, transparent) !important;
}

/* Sub-menu: set apart from the top-level items -- a soft panel behind the
   group's pages, smaller and lighter text. */
.drawer-custom :deep(.v-list-group__items) {
	margin: 2px 0 6px 18px;
	padding: 2px 0;
	border-inline-start: 2px solid var(--pos-panel-border);
	border-radius: 0 8px 8px 0;
	background: var(--pos-panel-bg);
}

.drawer-custom :deep(.drawer-item--child .drawer-item-title) {
	font-size: 0.78rem;
	font-weight: 500;
	color: var(--pos-label-text) !important;
}

.drawer-custom :deep(.drawer-item--child .drawer-icon) {
	color: var(--pos-label-text);
}

.drawer-custom :deep(.drawer-item--child.active-item .drawer-item-title),
.drawer-custom :deep(.drawer-item--child.active-item .drawer-icon) {
	color: var(--pos-accent-teal) !important;
	font-weight: 600;
}

/* Hover effect for all list items in the navigation drawer */
.v-list-item:hover {
	background-color: var(--pos-menu-hover) !important;
}

/* An open group's header reads as the section heading. */
.drawer-custom :deep(.v-list-group--open > .v-list-item .drawer-item-title) {
	font-weight: 600;
}

.drawer-custom :deep(.v-list-group--open > .v-list-item .drawer-icon) {
	color: var(--pos-text-primary);
}

.drawer-footer {
	padding: 10px;
	margin-top: auto;
}

.drawer-user-card {
	display: flex;
	flex-direction: column;
	gap: 8px;
	padding: 10px;
	border: 1px solid var(--pos-border, rgba(0, 0, 0, 0.08));
	border-radius: var(--pos-radius-md, 12px);
	background: color-mix(
		in srgb,
		var(--pos-primary) 5%,
		var(--pos-card-bg, #fff)
	);
}

.drawer-user-card--mini {
	align-items: center;
	padding: 8px;
}

.drawer-user-card__identity {
	display: flex;
	align-items: center;
	gap: 8px;
	min-width: 0;
}

.drawer-user-card__avatar {
	width: 32px;
	height: 32px;
	border-radius: 50%;
	flex-shrink: 0;
	display: inline-flex;
	align-items: center;
	justify-content: center;
	font-size: 11px;
	font-weight: 700;
	letter-spacing: 0.02em;
	color: #fff;
	background: linear-gradient(
		135deg,
		var(--pos-primary) 0%,
		var(--pos-secondary, #00bcd4) 100%
	);
}

.drawer-user-card__meta {
	display: flex;
	flex-direction: column;
	gap: 1px;
	min-width: 0;
}

.drawer-user-card__name {
	font-size: 12.5px;
	font-weight: 600;
	line-height: 1.25;
	color: var(--pos-text-primary);
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
}

.drawer-user-card__hint {
	font-size: 10.5px;
	line-height: 1.2;
	color: var(--pos-text-secondary, #6b7280);
}

.drawer-user-card__logout {
	display: flex;
	align-items: center;
	justify-content: center;
	gap: 6px;
	width: 100%;
	border: 1px solid color-mix(in srgb, #d32f2f 22%, transparent);
	background: color-mix(in srgb, #d32f2f 6%, transparent);
	padding: 7px 10px;
	font-size: 12.5px;
	font-weight: 600;
	color: #c62828;
	border-radius: var(--pos-radius-sm, 8px);
	cursor: pointer;
	transition:
		background-color 0.15s ease,
		border-color 0.15s ease;
}

.drawer-user-card--mini .drawer-user-card__logout {
	width: 36px;
	height: 36px;
	padding: 0;
}

.drawer-user-card__logout:hover {
	background: color-mix(in srgb, #d32f2f 12%, transparent);
	border-color: color-mix(in srgb, #d32f2f 35%, transparent);
}

/* Styling for the actively selected list item in the navigation drawer:
   primary tint with a bar on the leading edge. */
.active-item {
	background-color: color-mix(
		in srgb,
		var(--pos-primary) 10%,
		transparent
	) !important;
	box-shadow: inset 3px 0 0 var(--pos-primary);
}

.active-item :deep(.v-list-item__overlay) {
	opacity: 0 !important;
}

.active-item .drawer-item-title,
.active-item :deep(.drawer-item-title) {
	color: var(--pos-accent-teal) !important;
	font-weight: 600;
}

.active-item .drawer-icon,
.active-item :deep(.drawer-icon) {
	color: var(--pos-accent-teal) !important;
}

.drawer-custom.rtl-layout .active-item {
	box-shadow: inset -3px 0 0 var(--pos-primary);
}

/* Theme-aware drawer styling */
.drawer-custom {
	background-color: var(--pos-navbar-bg) !important;
	color: var(--pos-text-primary) !important;
}

.drawer-header,
.drawer-header-mini {
	background: var(--pos-navbar-bg) !important;
	border-bottom: 1px solid var(--pos-border);
}

:deep([data-theme="dark"]) .drawer-item-title,
:deep(.v-theme--dark) .drawer-item-title {
	color: var(--pos-text-primary) !important;
	font-weight: 500;
	font-size: 0.875rem;
	font-family: "Roboto", sans-serif;
}

:deep([data-theme="dark"]) .drawer-company,
:deep(.v-theme--dark) .drawer-company {
	color: var(--text-primary, #ffffff) !important;
	font-weight: 600;
	font-size: 0.8125rem;
	font-family: "Roboto", sans-serif;
}

:deep([data-theme="dark"]) .drawer-icon,
:deep(.v-theme--dark) .drawer-icon {
	color: var(--pos-menu-icon) !important;
	font-size: 20px;
}

:deep([data-theme="dark"]) .v-list-item:hover,
:deep(.v-theme--dark) .v-list-item:hover {
	background-color: var(--pos-menu-hover) !important;
}

:deep([data-theme="dark"]) .active-item,
:deep(.v-theme--dark) .active-item {
	background-color: color-mix(in srgb, var(--pos-primary) 14%, transparent) !important;
}

:deep([data-theme="dark"]) .v-divider,
:deep(.v-theme--dark) .v-divider {
	border-color: rgba(255, 255, 255, 0.12) !important;
}

/* Hide drawer by default, show only when activated */
.drawer-custom {
	display: none !important;
}
.drawer-custom.drawer-visible {
	display: block !important;
}

/* Responsive adjustments for width and dark theme */
@media (max-width: 900px) and (orientation: landscape) {
	.drawer-custom.drawer-visible {
		width: 190px !important;
	}
}

@media (min-width: 601px) and (max-width: 1024px) {
	.drawer-custom.drawer-visible {
		width: 220px !important;
	}
}

@media (min-width: 1025px) {
	.drawer-custom.drawer-visible {
		width: 240px !important;
	}
}

@media (max-width: 1024px) {
	.drawer-custom.drawer-visible {
		background-color: var(--pos-navbar-bg) !important;
	}
}
</style>
