// Shared by the Molding and Material Issue/Receipt screens, whose API rows
// carry a plain Draft/Submitted/Cancelled status derived from docstatus.

export const formatDisplayDate = (value) => {
	if (!value) return '—';
	const parts = String(value).split('-');
	return parts.length === 3 ? `${parts[2]}-${parts[1]}-${parts[0]}` : value;
};

export const formatDisplayDateTime = (value) => {
	if (!value) return '—';
	const [datePart, timePart] = String(value).split(' ');
	const date = formatDisplayDate(datePart);
	return timePart ? `${date} ${timePart.slice(0, 5)}` : date;
};

export const docStatusColor = (status) =>
	({ Submitted: 'green', Draft: 'grey', Cancelled: 'red' })[status] || 'grey';
