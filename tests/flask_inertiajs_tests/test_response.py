from copy import deepcopy
from dataclasses import dataclass
from decimal import Decimal
from functools import partial

import pytest

from flask_inertiajs.asset_version import current_asset_version

from .helpers import BridgeProps


@pytest.mark.parametrize('inertia', [False, True])
class TestRender:
    @pytest.fixture
    def render_page(self, render_resp, inertia):
        return partial(render_resp, inertia=inertia)

    def test_page(self, render_page, inertia):
        props = {
            'captain': 'Picard',
            'crew': ['Riker', 'Data'],
            'date': Decimal('41153.7'),
        }
        original = deepcopy(props)

        response = render_page(props)

        assert response.status_code == 200
        assert response.inertia_page == {
            'component': 'Enterprise/Bridge',
            'props': {
                'captain': 'Picard',
                'crew': ['Riker', 'Data'],
                # app's JSON config is respected
                'date': {'stardate': '41153.7'},
                'errors': {},
            },
            'url': '/render',
            'version': current_asset_version(),
            'sharedProps': [],
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

    def test_pydantic_props(self, render_page):
        props = BridgeProps(
            captain_name='Picard',
            date=Decimal('41153.7'),
        )
        original = props.model_copy(deep=True)

        response = render_page(props)

        assert response.inertia_props == {
            'captainName': 'Picard',
            # Pydantic controls model serialization; Flask controls dict/dataclass serialization.
            'date': '41153.7',
            'errors': {},
        }
        assert props == original

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

    def test_template_override(self, app, render_page, inertia):
        app.config['INERTIA_TEMPLATE'] = 'other.html'
        response = render_page()
        assert response.inertia_page['component'] == 'Enterprise/Bridge'
        assert response.inertia_props == {'errors': {}}
        if not inertia:
            assert '<title>Other</title>' in response.get_data(as_text=True)
