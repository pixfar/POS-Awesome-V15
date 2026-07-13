<template>
	<div class="pa-0 h-100 invoice-shell pos-list-page">
		<v-card flat class="invoice-section-card pos-themed-card pos-list-card">
			<div class="erp-reports-groups">
				<section
					v-for="group in visibleReportGroups"
					:key="group.title"
					class="erp-reports-group"
				>
					<div class="erp-reports-group__header">
						<v-icon size="20" class="mr-2">{{ group.icon }}</v-icon>
						<h4 class="erp-reports-group__title">{{ __(group.title) }}</h4>
					</div>
					<div class="erp-reports-grid">
						<button
							v-for="report in group.reports"
							:key="report.name"
							type="button"
							class="erp-report-card"
							@click="openReport(report)"
						>
							<div class="erp-report-card__icon">
								<v-icon size="22">{{ report.icon }}</v-icon>
							</div>
							<div class="erp-report-card__body">
								<p class="erp-report-card__title">{{ __(report.title) }}</p>
								<p class="erp-report-card__hint">
									{{ report.route ? __('View in POS Awesome') : __('Open in ERPNext') }}
								</p>
							</div>
							<v-icon size="18" class="erp-report-card__arrow">
								{{ report.route ? 'mdi-arrow-right' : 'mdi-open-in-new' }}
							</v-icon>
						</button>
					</div>
				</section>
			</div>
		</v-card>
	</div>
</template>

<script setup>
import { useErpReports } from './useErpReports';

const { __, visibleReportGroups, openReport } = useErpReports();
</script>

<style scoped>
@import './erp-reports-grid.css';
</style>
