/**
 * Recovers from a stale CSRF token instead of showing "Invalid Request".
 *
 * frappe.request.call() sends `X-Frappe-CSRF-Token: frappe.csrf_token` with
 * every POST. That token is read once from the /app page, so it goes stale
 * when the page came from a cache, or the session was replaced by a login in
 * another tab -- and from then on *every* save fails with "Invalid Request"
 * until the page is reloaded.
 *
 * This wraps the global $.ajax that frappe.request.call() uses: when a
 * request fails with CSRFTokenError it fetches the session's current token
 * (GET, exempt from the check), and -- only if the session still belongs to
 * the same user -- retries the request once with it. The caller sees just
 * the retried request's result. If the user changed, the page is reloaded
 * rather than acting as someone else.
 */

declare const frappe: any;
declare const $: any;

const TOKEN_METHOD = "/api/method/posawesome.posawesome.api.session.get_csrf_token";

let refreshInFlight: Promise<string | null> | null = null;

const isCsrfFailure = (xhr: any) => {
	if (!xhr || xhr.status !== 400) return false;
	const text = String(xhr.responseText || "");
	return text.includes("CSRFTokenError");
};

const fetchFreshToken = (origAjax: any): Promise<string | null> => {
	if (refreshInFlight) return refreshInFlight;
	refreshInFlight = new Promise<string | null>((resolve) => {
		origAjax({
			url: TOKEN_METHOD,
			type: "GET",
			dataType: "json",
			cache: false,
			headers: { Accept: "application/json" },
		})
			.done((r: any) => {
				const msg = r?.message || {};
				const currentUser = frappe?.session?.user;
				if (!msg.csrf_token || (currentUser && msg.user !== currentUser)) {
					// Logged out, or now logged in as someone else in another
					// tab -- this page's state belongs to the old session.
					window.location.reload();
					resolve(null);
					return;
				}
				frappe.csrf_token = msg.csrf_token;
				resolve(msg.csrf_token);
			})
			.fail(() => resolve(null));
	}).finally(() => {
		refreshInFlight = null;
	});
	return refreshInFlight;
};

export function installCsrfGuard() {
	if (typeof $ === "undefined" || typeof $.ajax !== "function") return;
	if ($.ajax.__posaCsrfGuard) return;

	const origAjax = $.ajax;

	const guarded = function (this: any, url: any, options?: any) {
		const settings = typeof url === "object" ? url : { ...(options || {}), url };
		const headers = settings?.headers;
		const method = String(settings?.type || settings?.method || "GET").toUpperCase();
		// Only Frappe's own unsafe requests carry the header; leave everything else alone.
		if (!headers || !("X-Frappe-CSRF-Token" in headers) || method === "GET") {
			return origAjax.apply(this, arguments as any);
		}

		const deferred = $.Deferred();
		let current = origAjax(settings);
		const promise = deferred.promise({ abort: (reason?: string) => current?.abort?.(reason) });

		current
			.done((...args: any[]) => deferred.resolveWith(this, args))
			.fail((xhr: any, ...rest: any[]) => {
				if (!isCsrfFailure(xhr)) {
					deferred.rejectWith(this, [xhr, ...rest]);
					return;
				}
				fetchFreshToken(origAjax).then((token) => {
					if (!token) {
						deferred.rejectWith(this, [xhr, ...rest]);
						return;
					}
					settings.headers = { ...headers, "X-Frappe-CSRF-Token": token };
					current = origAjax(settings);
					current
						.done((...args: any[]) => deferred.resolveWith(this, args))
						.fail((...args: any[]) => deferred.rejectWith(this, args));
				});
			});

		return promise;
	};
	(guarded as any).__posaCsrfGuard = true;
	$.ajax = guarded;
}
