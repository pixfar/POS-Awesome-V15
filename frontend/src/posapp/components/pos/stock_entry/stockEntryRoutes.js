// Material Issue and Material Receipt share one set of Stock Entry screens;
// each purpose lives under its own route prefix.
export const stockEntryBasePath = (purpose) =>
	purpose === 'Material Issue' ? '/material-issues' : '/material-receipts';
