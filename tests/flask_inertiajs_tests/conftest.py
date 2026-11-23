from decimal import Decimal

from flask import Flask, flash, request
from flask.json.provider import DefaultJSONProvider
from jinja2 import DictLoader
import pytest

from flask_inertiajs import Inertia, render
from flask_inertiajs.testing import InertiaClient, InertiaResponse
from flask_inertiajs.views import inertia_view


# Tests and other fixtures depend on this being function-scoped. Don't make it session-scoped
# without noting the ramifications.
@pytest.fixture
def app(tmp_path):
    app = Flask(__name__)
    app.config.update(TESTING=True, SECRET_KEY='test-secret')
    app.test_client_class = InertiaClient
    app.response_class = InertiaResponse
    app.json = CustomJSONProvider(app)
    app.jinja_loader = DictLoader(
        {
            'inertia.html': '<title>Default</title>{{ inertia_root() }}',
            'other.html': '<title>Other</title>{{ inertia_root() }}',
        },
    )
    manifest = tmp_path / 'crew.json'
    manifest.write_text('{"picard.ts": {"file": "assets/picard.js"}}')
    app.config['INERTIA_VITE_MANIFEST_PATH'] = manifest
    Inertia(app)

    @app.post('/flash')
    def flash_view():
        for message in request.get_json():
            flash(**message)
        return '', 204

    return app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def render_resp(app, client):
    render_options = {}

    @app.route('/render', methods=['GET', 'POST'])
    @inertia_view
    def render_view():
        return render(**render_options)

    def get_response(
        props=None,
        *,
        component='Enterprise/Bridge',
        inertia=True,
        path='/render',
        method='GET',
        **options,
    ):
        render_options.clear()
        render_options.update(component=component, props=props, **options)
        return client.open(path, method=method, inertia=inertia)

    return get_response


class CustomJSONProvider(DefaultJSONProvider):
    """Serializes `Decimal` values to `{"stardate": "value"}`. Useful for checking that the app's
    JSON config is respected."""

    @staticmethod
    def default(value):
        if isinstance(value, Decimal):
            return {'stardate': str(value)}
        return DefaultJSONProvider.default(value)
