from flask.views import MethodView
import pytest

from flask_inertiajs.views import InertiaView, inertia_view, is_inertia_endpoint

from .helpers import BridgeProps


class TestIsInertiaEndpoint:
    def test_supported(self, app):
        @app.get('/engineering')
        @inertia_view
        def engineering(): ...

        class Bridge(InertiaView):
            def get(self): ...

        class BattleBridge(Bridge):
            pass

        @app.get('/holodeck')
        def holodeck(): ...

        class Sickbay(MethodView):
            def get(self): ...

        app.add_url_rule('/bridge', view_func=Bridge.as_view('bridge'))
        app.add_url_rule('/battle-bridge', view_func=BattleBridge.as_view('battle_bridge'))
        app.add_url_rule('/sickbay', view_func=Sickbay.as_view('sickbay'))

        with app.app_context():
            assert is_inertia_endpoint('engineering')
            assert is_inertia_endpoint('bridge')
            assert is_inertia_endpoint('battle_bridge')
            assert not is_inertia_endpoint('missing')
            assert not is_inertia_endpoint('holodeck')
            assert not is_inertia_endpoint('sickbay')


class TestInertiaView:
    @pytest.mark.parametrize('inertia', [False, True])
    def test_render(self, app, client, inertia):
        class Bridge(InertiaView):
            component = 'Enterprise/Bridge'
            props_model = BridgeProps

            def make_props(self, crew_id):
                return super().make_props(captain_name={1: 'Picard'}[crew_id])

            def post(self, crew_id):
                return self.render(
                    crew_id=crew_id,
                    errors={'orders': 'Shields are down'},
                    inertia_url='/bridge/1?orders',
                )

        app.add_url_rule('/bridge/<int:crew_id>', view_func=Bridge.as_view('bridge'))

        response = client.get('/bridge/1', inertia=inertia)

        assert response.status_code == 200
        assert response.mimetype == ('application/json' if inertia else 'text/html')
        assert response.inertia_page['component'] == 'Enterprise/Bridge'
        assert response.inertia_props == {
            'captainName': 'Picard',
            'date': '41153.7',
            'errors': {},
        }

        response = client.post('/bridge/1', inertia=inertia)

        assert response.status_code == 200
        assert response.mimetype == ('application/json' if inertia else 'text/html')
        assert response.inertia_page['url'] == '/bridge/1?orders'
        assert response.inertia_props['captainName'] == 'Picard'
        assert response.inertia_props['errors'] == {'orders': 'Shields are down'}
