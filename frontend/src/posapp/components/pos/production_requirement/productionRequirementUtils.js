// Shared by the Production Requirement list/detail/new screens.

// Set by hand to track where a requirement stands (see the doctype's status field).
export const PRODUCTION_REQUIREMENT_STATUSES = [
	"Pending",
	"In Progress",
	"Completed",
	"On Hold",
	"Cancelled",
];

export const productionRequirementStatusColor = (status) =>
	({
		Pending: "grey",
		"In Progress": "orange",
		Completed: "green",
		"On Hold": "amber-darken-2",
		Cancelled: "red",
	})[status] || "grey";

export const formatQty = (value) => {
	const n = Number(value || 0);
	return Number.isInteger(n) ? String(n) : n.toFixed(2);
};
