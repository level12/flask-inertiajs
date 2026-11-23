from copy import deepcopy
from dataclasses import dataclass
from decimal import Decimal
from functools import partial
from unittest.mock import Mock

import pytest

from flask_inertiajs.asset_version import current_asset_version

from .helpers import BridgeProps, EngineeringProps


@pytest.mark.parametrize('inertia', [False, True])
class TestRender:
    @pytest.fixture
    def render_page(self, render_resp, inertia):
        return partial(render_resp, inertia=inertia)

    @pytest.fixture()
    def registry(self, app):
        app.extensions['inertia'].register_component_prop_types({'Enterprise/Bridge': BridgeProps})

    def test_page(self, app, client, render_page, inertia):
        client.post(
            '/flash',
            json=[
                {'message': 'Report to battle stations.'},
                {'message': 'Red alert!', 'category': 'error'},
            ],
        )
        app.extensions['inertia'].share(lambda: {'captain': 'Riker', 'date1': Decimal('45047.2')})
        props = {
            'captain': 'Picard',
            'crew': ['Riker', 'Data'],
            'date2': Decimal('41153.7'),
        }
        original = deepcopy(props)

        response = render_page(props, errors={'shields': 'Shields are down'})
        with app.app_context():
            version = current_asset_version()

        assert response.status_code == 200
        assert response.inertia_page == {
            'component': 'Enterprise/Bridge',
            'props': {
                # Direct props override shared props.
                'captain': 'Picard',
                'crew': ['Riker', 'Data'],
                # app's JSON config is respected
                'date1': {'stardate': '45047.2'},
                'date2': {'stardate': '41153.7'},
                'errors': {'shields': 'Shields are down'},
            },
            'url': '/render',
            'version': version,
            # Overridden keys stay in sharedProps (matches Laravel adapter)
            'sharedProps': ['captain', 'date1'],
            'flash': {
                'messages': [
                    {'category': 'message', 'message': 'Report to battle stations.'},
                    {'category': 'error', 'message': 'Red alert!'},
                ],
            },
        }
        assert 'X-Inertia' in response.vary
        if inertia:
            assert response.mimetype == 'application/json'
            assert response.headers['X-Inertia'] == 'true'
        else:
            assert response.mimetype == 'text/html'
            assert 'X-Inertia' not in response.headers
            assert '<title>Default</title>' in response.get_data(as_text=True)

        # Rendering doesn't mutate the supplied props
        assert props == original

    def test_dataclass_props(self, render_page):
        @dataclass(frozen=True)
        class CrewMember:
            name: str

        @dataclass(frozen=True)
        class BridgeDataclass:
            captain: CrewMember
            crew: list[CrewMember]
            date: Decimal

        props = BridgeDataclass(CrewMember('Picard'), [CrewMember('Data')], Decimal('41153.7'))
        original = deepcopy(props)

        response = render_page(props)

        assert response.inertia_props == {
            'captain': {'name': 'Picard'},
            'crew': [{'name': 'Data'}],
            'date': {'stardate': '41153.7'},
            'errors': {},
        }

        # Rendering doesn't mutate the supplied props
        assert props == original

    def test_pydantic_props(self, app, registry, render_page):
        app.extensions['inertia'].share(lambda: EngineeringProps(chief_engineer_name='La Forge'))

        props = BridgeProps(
            captain_name='Picard',
            date=Decimal('41153.7'),
        )
        original = props.model_copy(deep=True)

        response = render_page(props)

        assert response.inertia_props == {
            'captainName': 'Picard',
            'chiefEngineerName': 'La Forge',
            # Pydantic controls model serialization; Flask controls dict/dataclass serialization.
            'date': '41153.7',
            'errors': {},
        }
        assert props == original
        assert response.inertia_page['sharedProps'] == ['chiefEngineerName']

    def test_fresh_shared_props(self, app, client, render_page, inertia):
        callback = Mock(side_effect=[{'captain': 'Picard'}, {'captain': 'Riker'}])
        app.extensions['inertia'].share(callback)

        first = render_page()
        second = client.get('/render', inertia=inertia)

        assert first.inertia_props == {'captain': 'Picard', 'errors': {}}
        assert second.inertia_props == {'captain': 'Riker', 'errors': {}}
        assert callback.call_count == 2

    def test_flash_consumption(self, client, render_page, inertia):
        client.post('/flash', json=[{'message': 'Romulan ale', 'category': 'warning'}])

        first = render_page()
        second = client.get('/render', inertia=inertia)

        assert first.inertia_page['flash'] == {
            'messages': [{'category': 'warning', 'message': 'Romulan ale'}],
        }
        # The flash was consumed
        assert 'flash' not in second.inertia_page

    @pytest.mark.parametrize(
        'path',
        [
            '/render?crew=Data&crew=Riker',
            '/render?destination=Starbase%203&next=%2Fcrew',
        ],
    )
    def test_url(self, render_page, path):
        assert render_page(path=path).inertia_page['url'] == path

    def test_url_override(self, render_page):
        response = render_page(method='POST', url='/crew/new?ship=Enterprise')
        assert response.inertia_page['url'] == '/crew/new?ship=Enterprise'

    @pytest.mark.parametrize('source', ['page', 'shared'])
    def test_errors_in_props(self, app, render_page, source):
        props = {'errors': {'shields': 'Shields are down'}}
        if source == 'shared':
            app.extensions['inertia'].share(lambda: props)

        with pytest.raises(ValueError, match='Errors should be passed separately'):
            render_page(props if source == 'page' else None)

    def test_template_override(self, app, render_page, inertia):
        app.config['INERTIA_TEMPLATE'] = 'other.html'
        response = render_page()
        assert response.inertia_page['component'] == 'Enterprise/Bridge'
        assert response.inertia_props == {'errors': {}}
        assert response.inertia_page['sharedProps'] == []
        if not inertia:
            assert '<title>Other</title>' in response.get_data(as_text=True)

    @pytest.mark.parametrize(
        'bad_props',
        [None, {'captain_name': 'Picard'}, EngineeringProps(chief_engineer_name='La Forge')],
    )
    def test_wrong_props_type(self, registry, render_page, bad_props):
        with pytest.raises(TypeError, match='Enterprise/Bridge'):
            render_page(bad_props)

    def test_missing_component(self, registry, render_page):
        with pytest.raises(KeyError, match='Enterprise/Engineering'):
            render_page(BridgeProps(captain_name='La Forge'), component='Enterprise/Engineering')
