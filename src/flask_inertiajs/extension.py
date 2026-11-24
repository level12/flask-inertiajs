from collections.abc import Callable
from typing import Any

from flask import Flask, Response, abort, g, request

from flask_inertiajs.asset_version import current_asset_version
from flask_inertiajs.template import inertia_root
from flask_inertiajs.views import is_inertia_endpoint, is_inertia_url


REDIRECT_TO_GET_METHODS = frozenset(('PUT', 'PATCH', 'DELETE', 'QUERY'))


class Inertia:
    """Configure Inertia for a Flask application."""

    def __init__(
        self,
        app: Flask | None = None,
        *,
        component_prop_types: dict[str, type] | None = None,
    ):
        self.component_prop_types = (
            component_prop_types.copy() if component_prop_types is not None else None
        )
        self.shared_props_callback: Callable[[], Any] | None = None
        self.asset_version_callback: Callable[[], str] = current_asset_version
        if app is not None:
            self.init_app(app)

    def init_app(self, app: Flask):
        app.config.setdefault('INERTIA_TEMPLATE', 'inertia.html')
        app.config.setdefault('INERTIA_VITE_MANIFEST_PATH', None)
        app.add_template_global(inertia_root)
        app.extensions['inertia'] = self
        app.before_request(self._before_request)
        app.after_request(self._after_request)

    def _before_request(self):
        # Exit early for routing exceptions.
        if request.routing_exception is not None:
            return

        # Request is not to an Inertia endpoint. Fail if Inertia endpoint expected, else continue.
        if not is_inertia_endpoint(request.endpoint):
            if request.headers.get('X-Inertia'):
                abort(400, description='This endpoint does not support Inertia requests.')
            return

        # If there's a new asset version, convert to a full-page load.
        g.inertia_asset_version = self.asset_version_callback()
        if (
            request.headers.get('X-Inertia')
            and request.method == 'GET'
            and request.headers.get('X-Inertia-Version') != g.inertia_asset_version
        ):
            return Response(
                status=409,
                headers={
                    'X-Inertia-Location': request.url,
                    'X-Inertia-Version': g.inertia_asset_version,
                },
            )

    @staticmethod
    def _after_request(response: Response) -> Response:
        # Exit early for routing exceptions and non-Inertia endpoints.
        if request.routing_exception is not None or not is_inertia_endpoint(request.endpoint):
            return response

        # Tell the browser to keep the HTML and JSON responses apart.
        response.vary.add('X-Inertia')

        if request.headers.get('X-Inertia') and response.status_code == 302 and response.location:
            # Redirect points outside the Inertia app, so convert to a full-page load.
            if not is_inertia_url(response.location):
                response.headers['X-Inertia-Location'] = response.location
                response.status_code = 409
            # Tell Inertia to convert these methods to GET on the redirect.
            elif request.method in REDIRECT_TO_GET_METHODS:
                response.status_code = 303
        return response

    def share[F: Callable[[], Any]](self, callback: F) -> F:
        if self.shared_props_callback is not None:
            raise ValueError('A shared props callback is already registered')
        self.shared_props_callback = callback
        return callback

    def asset_version[F: Callable[[], str]](self, callback: F) -> F:
        if self.asset_version_callback is not current_asset_version:
            raise ValueError('An asset version callback is already registered')
        self.asset_version_callback = callback
        return callback
