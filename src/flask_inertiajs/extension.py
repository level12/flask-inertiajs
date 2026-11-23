from collections.abc import Callable
from typing import Any

from flask import Flask, Response, abort, request

from flask_inertiajs.template import inertia_root
from flask_inertiajs.views import is_inertia_endpoint


class Inertia:
    """Configure Inertia for a Flask application."""

    def __init__(self, app: Flask | None = None):
        self.component_prop_types: dict[str, type] | None = None
        self.shared_props_callback: Callable[[], Any] | None = None
        if app is not None:
            self.init_app(app)

    def init_app(self, app: Flask):
        app.config.setdefault('INERTIA_TEMPLATE', 'inertia.html')
        app.config.setdefault('INERTIA_VITE_MANIFEST_PATH', None)
        app.add_template_global(inertia_root)
        app.extensions['inertia'] = self
        app.before_request(self._before_request)
        app.after_request(self._after_request)

    @staticmethod
    def _before_request():
        if not request.headers.get('X-Inertia') or request.routing_exception is not None:
            return
        if not is_inertia_endpoint(request.endpoint):
            abort(400, description='This endpoint does not support Inertia requests.')

    @staticmethod
    def _after_request(response: Response) -> Response:
        if request.endpoint is not None and is_inertia_endpoint(request.endpoint):
            # Tell the browser to keep the HTML and JSON responses apart.
            response.vary.add('X-Inertia')
        return response

    def register_component_prop_types(self, components_prop_types: dict[str, type]):
        self.component_prop_types = components_prop_types.copy()

    def share[F: Callable[[], Any]](self, callback: F) -> F:
        if self.shared_props_callback is not None:
            raise ValueError('A shared props callback is already registered')
        self.shared_props_callback = callback
        return callback
