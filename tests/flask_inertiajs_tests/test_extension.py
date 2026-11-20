from flask import Flask
import pytest

from flask_inertiajs import Inertia
from flask_inertiajs.template import inertia_root


class TestInitApp:
    @pytest.fixture
    def app(self):
        # The app fixture from conftest already gets the extension, so use a fresh one here.
        return Flask('enterprise')

    @pytest.fixture(params=['constructor', 'init_app'])
    def init_method(self, request):
        if request.param == 'constructor':
            return Inertia

        def initialize(app):
            inertia = Inertia()
            inertia.init_app(app)
            return inertia

        return initialize

    def test_defaults(self, app, init_method):
        inertia = init_method(app)

        assert app.extensions['inertia'] is inertia
        assert app.config['INERTIA_TEMPLATE'] == 'inertia.html'
        assert app.config['INERTIA_VITE_MANIFEST_PATH'] is None
        assert app.jinja_env.globals['inertia_root'] is inertia_root

    def test_overrides(self, app, init_method):
        app.config.update(
            INERTIA_TEMPLATE='enterprise.html',
            INERTIA_VITE_MANIFEST_PATH='crew/manifest.json',
        )

        inertia = init_method(app)

        assert app.extensions['inertia'] is inertia
        assert app.config['INERTIA_TEMPLATE'] == 'enterprise.html'
        assert app.config['INERTIA_VITE_MANIFEST_PATH'] == 'crew/manifest.json'
