// Shared by the Molding and Material Issue/Receipt screens, whose API rows
// carry a plain Draft/Submitted/Cancelled status derived from docstatus.

export const formatDisplayDate = (value) => {
	if (!value) return '—';
	const parts = String(value).split('-');
	return parts.length === 3 ? `${parts[2]}-${parts[1]}-${parts[0]}` : value;
};

// "DD-MM-YYYY hh:mm AM/PM" (see formatDisplayTimeAmPm below).
export const formatDisplayDateTime = (value) => {
	if (!value) return '—';
	const [datePart, timePart] = String(value).split(' ');
	const date = formatDisplayDate(datePart);
	return timePart ? `${date} ${formatDisplayTimeAmPm(timePart)}` : date;
};

// 24-hour clock "HH:MM" from a datetime ("YYYY-MM-DD HH:MM:SS") or bare time;
// returns '' when absent so callers can render it next to a date.
export const formatClockTime24 = (value) => {
	if (!value) return '';
	const raw = String(value);
	const timePart = raw.includes(' ') ? raw.split(' ')[1] : raw;
	return timePart ? timePart.slice(0, 5) : '';
};

// 12-hour clock with AM/PM, e.g. "08:34 PM". Accepts a full datetime string
// ("YYYY-MM-DD HH:MM:SS") or a bare time ("HH:MM:SS"); returns "—" when absent.
export const formatDisplayTimeAmPm = (value) => {
	if (!value) return '—';
	const raw = String(value);
	const timePart = raw.includes(' ') ? raw.split(' ')[1] : raw;
	if (!timePart) return '—';
	const [hStr, mStr] = timePart.split(':');
	let hours = Number(hStr);
	const minutes = mStr != null ? mStr.slice(0, 2) : '00';
	if (!Number.isFinite(hours)) return '—';
	const suffix = hours >= 12 ? 'PM' : 'AM';
	hours = hours % 12 || 12;
	return `${String(hours).padStart(2, '0')}:${minutes} ${suffix}`;
};

export const docStatusColor = (status) =>
	({ Submitted: 'green', Draft: 'grey', Cancelled: 'red' })[status] || 'grey';
