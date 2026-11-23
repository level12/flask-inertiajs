from flask import Flask
import pytest

from flask_inertiajs import Inertia
from flask_inertiajs.template import inertia_root
from flask_inertiajs.views import inertia_view


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


class TestShare:
    def test_registration(self, app):
        @app.extensions['inertia'].share
        def shared(): ...

        assert app.extensions['inertia'].shared_props_callback is shared

    def test_duplicate_registration(self, app):
        @app.extensions['inertia'].share
        def shared(): ...

        with pytest.raises(ValueError, match='already registered'):

            @app.extensions['inertia'].share
            def other_shared(): ...


class TestBeforeRequest:
    def test_rejects_unmarked_endpoints(self, app, client):
        @app.get('/bridge')
        @inertia_view
        def bridge():
            return 'Picard'

        holodeck_visited = False

        @app.get('/holodeck')
        def holodeck():
            nonlocal holodeck_visited
            holodeck_visited = True
            return 'Data'

        # Inertia -> Inertia
        assert client.get('/bridge', inertia=True).status_code == 200

        # Inertia -> Not Inertia
        assert client.get('/holodeck', inertia=True).status_code == 400
        assert not holodeck_visited

        # Not Inertia -> Not Inertia
        assert client.get('/holodeck').status_code == 200
        assert holodeck_visited

        # The Not Inertia -> Inertia case is handled with the HTML response, tested elsewhere.

        # Flask routing exceptions take priority over the Inertia check.
        assert client.get('/missing', inertia=True).status_code == 404


class TestAfterRequest:
    @pytest.mark.parametrize('inertia', [False, True])
    def test_vary(self, app, client, inertia):
        @app.get('/bridge')
        @inertia_view
        def bridge():
            return '', {'Vary': 'Accept-Language'}

        @app.get('/holodeck')
        def holodeck():
            return '', {'Vary': 'Accept-Language'}

        # X-Inertia is added while existing is preserved.
        response = client.get('/bridge', inertia=inertia)
        assert response.status_code == 200
        assert set(response.vary) == {'Accept-Language', 'X-Inertia'}

        # Not added for non-inertia views.
        assert set(client.get('/holodeck').vary) == {'Accept-Language'}

        # 404s are handled gracefully
        assert 'X-Inertia' not in client.get('/missing', inertia=inertia).vary
