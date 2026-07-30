<template>
	<v-navigation-drawer
		v-model="drawerOpen"
		:rail="mini"
		expand-on-hover
		width="200"
		:class="['drawer-custom', { 'drawer-visible': drawerOpen }, rtlClasses]"
		@mouseleave="handleMouseLeave"
		temporary
		:location="isRtl ? 'right' : 'left'"
		:scrim="scrimColor"
	>
		<div class="drawer-shell">
			<div>
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
import { computed, ref, watch } from "vue";
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

const mini = ref(false);
const drawerOpen = ref(props.drawer);
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

watch(drawerOpen, (val) => {
	document.body.style.overflow = val ? "hidden" : "";
	emit("update:drawer", val);
});

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
	if (!drawerOpen.value) return;
	clearTimeout(closeTimeout);
	closeTimeout = setTimeout(() => {
		drawerOpen.value = false;
		mini.value = true;
	}, 250);
}

function handleItemClick() {
	// Close drawer after selection if mobile
	if (window.innerWidth < 1024) {
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
	color: #0097a7;
	font-family: "Roboto", sans-serif;
	overflow: hidden;
	display: -webkit-box;
	-webkit-line-clamp: 2;
	-webkit-box-orient: vertical;
}

/* Styling for icons within the navigation drawer list items */
.drawer-icon {
	font-size: 20px;
	color: var(--pos-primary);
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

.drawer-custom :deep(.drawer-item--child) {
	padding-inline-start: 12px !important;
}

/* Hover effect for all list items in the navigation drawer */
.v-list-item:hover {
	background-color: color-mix(
		in srgb,
		var(--pos-primary) 8%,
		transparent
	) !important;
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

/* Styling for the actively selected list item in the navigation drawer */
.active-item {
	background-color: color-mix(
		in srgb,
		var(--pos-primary) 12%,
		transparent
	) !important;
	border-right: 3px solid var(--pos-primary);
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
	color: var(--pos-primary) !important;
	font-size: 20px;
}

:deep([data-theme="dark"]) .v-list-item:hover,
:deep(.v-theme--dark) .v-list-item:hover {
	background-color: rgba(144, 202, 249, 0.08) !important;
}

:deep([data-theme="dark"]) .active-item,
:deep(.v-theme--dark) .active-item {
	background-color: rgba(144, 202, 249, 0.12) !important;
	border-right: 3px solid #90caf9;
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
		width: 168px !important;
	}
}

@media (min-width: 601px) and (max-width: 1024px) {
	.drawer-custom.drawer-visible {
		width: 190px !important;
	}
}

@media (min-width: 1025px) {
	.drawer-custom.drawer-visible {
		width: 200px !important;
	}
}

@media (max-width: 1024px) {
	.drawer-custom.drawer-visible {
		background-color: var(--pos-navbar-bg) !important;
	}
}
</style>
