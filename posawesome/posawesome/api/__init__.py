"""POS Awesome API package.

Submodules are imported lazily by Frappe's method resolver using their full
dotted path (e.g. posawesome.posawesome.api.utilities.get_server_usage).
Eager re-exports here are not needed and cause threading deadlocks when
multiple requests race to import heavy submodules like `items` simultaneously.
"""
