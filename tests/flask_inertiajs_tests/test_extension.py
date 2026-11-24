from unittest.mock import Mock

from flask import Flask, redirect
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

        def initialize(app, **kwargs):
            inertia = Inertia(**kwargs)
            inertia.init_app(app)
            return inertia

        return initialize

    def test_defaults(self, app, init_method):
        inertia = init_method(app)

        assert app.extensions['inertia'] is inertia
        assert inertia.component_prop_types is None
        assert app.config['INERTIA_TEMPLATE'] == 'inertia.html'
        assert app.config['INERTIA_VITE_MANIFEST_PATH'] is None
        assert app.jinja_env.globals['inertia_root'] is inertia_root

    @pytest.mark.parametrize('component_prop_types', [{}, {'Enterprise/Bridge': dict}])
    def test_overrides(self, app, init_method, component_prop_types):
        app.config.update(
            INERTIA_TEMPLATE='enterprise.html',
            INERTIA_VITE_MANIFEST_PATH='crew/manifest.json',
        )

        inertia = init_method(app, component_prop_types=component_prop_types)

        assert app.extensions['inertia'] is inertia
        assert inertia.component_prop_types == component_prop_types
        assert inertia.component_prop_types is not component_prop_types
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


class TestAssetVersion:
    def test_registration(self, app, client, render_resp):
        asset_version = Mock(side_effect=['stargazer', 'enterprise-d'])
        assert app.extensions['inertia'].asset_version(asset_version) is asset_version
        asset_version.assert_not_called()

        # Asset version is cached
        assert render_resp(inertia=False).inertia_page['version'] == 'stargazer'
        assert render_resp(inertia=True).inertia_page['version'] == 'stargazer'
        # Unless auto_reload is enabled
        app.jinja_env.auto_reload = True
        assert render_resp(inertia=False).inertia_page['version'] == 'enterprise-d'

    def test_duplicate_registration(self, app):
        @app.extensions['inertia'].asset_version
        def asset_version(): ...

        with pytest.raises(ValueError, match='already registered'):

            @app.extensions['inertia'].asset_version
            def other_asset_version(): ...


class TestBeforeRequest:
    @pytest.mark.parametrize('version', [None, 'stargazer'])
    def test_version_check(self, client, render_resp, version):
        current_version = render_resp().inertia_page['version']
        headers = {'X-Inertia': 'true'}
        if version is not None:
            headers['X-Inertia-Version'] = version

        response = client.get('/render?captain=Picard', headers=headers)

        assert response.status_code == 409
        assert response.headers['X-Inertia-Location'] == 'http://localhost/render?captain=Picard'
        assert response.headers['X-Inertia-Version'] == current_version

        # Non-GET and non-Inertia requests are exempt.
        assert client.post('/render', headers=headers).status_code == 200
        headers.pop('X-Inertia')
        assert client.get('/render', headers=headers).status_code == 200

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
    @pytest.mark.parametrize(
        'method,target,inertia,code,header',
        [
            ('GET', '/bridge', True, 302, 'Location'),
            ('DELETE', '/bridge', True, 303, 'Location'),
            ('POST', '/bridge', False, 302, 'Location'),
            ('POST', '/holodeck', False, 302, 'Location'),
            ('POST', '/holodeck', True, 409, 'X-Inertia-Location'),
            ('POST', 'https://enterprise.example/bridge', True, 409, 'X-Inertia-Location'),
        ],
    )
    def test_redirect(self, app, client, method, target, inertia, code, header):
        @app.route('/bridge', methods=['GET', 'POST', 'DELETE'])
        @inertia_view
        def bridge():
            return redirect(target)

        @app.get('/holodeck')
        def holodeck(): ...

        response = client.open('/bridge', method=method, inertia=inertia)

        assert response.status_code == code
        assert response.headers[header] == target

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

    def test_graceful_404(self, client):
        assert client.get('/missing', inertia=True).status_code == 404
