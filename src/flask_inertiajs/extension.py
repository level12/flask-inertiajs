from collections.abc import Callable
from typing import Any

from flask import Flask

from flask_inertiajs.template import inertia_root


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

    def register_component_prop_types(self, components_prop_types: dict[str, type]):
        self.component_prop_types = components_prop_types.copy()

    def share[F: Callable[[], Any]](self, callback: F) -> F:
        if self.shared_props_callback is not None:
            raise ValueError('A shared props callback is already registered')
        self.shared_props_callback = callback
        return callback
