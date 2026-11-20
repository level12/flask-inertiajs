from flask import Flask

from flask_inertiajs.template import inertia_root


class Inertia:
    """Configure Inertia for a Flask application."""

    def __init__(self, app: Flask | None = None) -> None:
        if app is not None:
            self.init_app(app)

    def init_app(self, app: Flask) -> None:
        app.config.setdefault('INERTIA_TEMPLATE', 'inertia.html')
        app.config.setdefault('INERTIA_VITE_MANIFEST_PATH', None)
        app.add_template_global(inertia_root)
        app.extensions['inertia'] = self
