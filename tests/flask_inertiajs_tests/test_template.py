from decimal import Decimal

from flask import render_template_string
from flask.json.provider import DefaultJSONProvider
import pytest


class TestInertiaRoot:
    @pytest.fixture
    def page(self):
        return {'component': 'Enterprise/Bridge', 'props': {'captain': 'Picard'}}

    @pytest.fixture
    def render_root(self, app, page):
        def render(template='{{ inertia_root() }}', **context):
            with app.app_context():
                return render_template_string(template, page=page, **context)

        return render

    def test_default_root(self, app, page, render_root):
        html = render_root()

        assert html.startswith('<script data-page="app" type="application/json">')
        assert html.endswith('</script><div id="app"></div>')
        assert app.response_class(html).inertia_page == page

    def test_custom_root(self, app, page, render_root):
        html = render_root("{{ inertia_root(id='bridge') }}")

        assert html.startswith('<script data-page="bridge" type="application/json">')
        assert html.endswith('</script><div id="bridge"></div>')
        assert app.response_class(html).inertia_page == page

    def test_json_escaping(self, app, page, render_root):
        page['props']['message'] = '</script><script>alert("Q & crew")</script>'
        html = render_root()

        assert html.count('<script') == 1
        assert all(escape in html for escape in (r'\u003c', r'\u003e', r'\u0026'))
        assert app.response_class(html).inertia_page == page

    def test_id_escaping(self, app, page, render_root):
        html = render_root(
            '{{ inertia_root(id=root_id) }}',
            root_id='bridge" onload="Q<&',
        )

        assert 'data-page="bridge&#34; onload=&#34;Q&lt;&amp;"' in html
        assert '<div id="bridge&#34; onload=&#34;Q&lt;&amp;"></div>' in html
        assert app.response_class(html).inertia_page == page

    def test_uses_app_json_provider(self, app, page, render_root):
        class StarfleetJSONProvider(DefaultJSONProvider):
            @staticmethod
            def default(value):
                if isinstance(value, Decimal):
                    return {'stardate': str(value)}
                return DefaultJSONProvider.default(value)

        app.json = StarfleetJSONProvider(app)
        page['props']['date'] = Decimal('41153.7')
        html = render_root()

        assert app.response_class(html).inertia_props['date'] == {'stardate': '41153.7'}
