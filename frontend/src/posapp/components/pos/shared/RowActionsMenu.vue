<template>
	<v-menu :close-on-content-click="true" location="bottom end">
		<template #activator="{ props: menuProps }">
			<v-btn
				v-bind="menuProps"
				icon
				size="small"
				variant="text"
				class="pos-list-row-actions-btn"
				:loading="loading"
				:aria-label="ariaLabel"
				:title="ariaLabel"
				@click.stop
			>
				<v-icon>mdi-dots-vertical</v-icon>
			</v-btn>
		</template>
		<v-list density="compact" min-width="190">
			<template v-for="action in visibleActions" :key="action.key">
				<v-list-item @click="$emit('action', action.key)">
					<template #prepend>
						<v-icon size="18" :color="action.color">{{ action.icon }}</v-icon>
					</template>
					<v-list-item-title>{{ action.label }}</v-list-item-title>
				</v-list-item>
			</template>
		</v-list>
	</v-menu>
</template>

<script setup>
import { computed } from 'vue';

defineOptions({
	name: 'RowActionsMenu',
});

const props = defineProps({
	actions: { type: Array, default: () => [] },
	loading: { type: Boolean, default: false },
	ariaLabel: { type: String, default: 'Actions' },
});

defineEmits(['action']);

const visibleActions = computed(() => props.actions.filter((action) => action.show !== false));
</script>
