from flask import jsonify, request
import pytest
from werkzeug.datastructures import Headers

from flask_inertiajs.asset_version import current_asset_version


class TestInertiaClient:
    @pytest.fixture(autouse=True)
    def echo(self, app):
        @app.route('/echo', methods=['GET', 'POST'])
        def echo():
            return jsonify(headers=dict(request.headers), data=request.get_json(silent=True))

    def test_plain_request(self, client):
        headers = client.get('/echo').json['headers']
        assert 'X-Inertia' not in headers
        assert 'X-Inertia-Version' not in headers

    def test_inertia_request(self, client):
        headers = client.get('/echo', inertia=True).json['headers']
        assert headers['X-Inertia'] == 'true'
        assert headers['X-Inertia-Version'] == current_asset_version()

    @pytest.mark.parametrize('headers_type', [dict, Headers, list])
    def test_headers_preserved(self, client, headers_type):
        headers = headers_type([('x-inertia-version', 'stale'), ('X-Custom', 'value')])
        original = Headers(headers)
        response = client.post('/echo', inertia=True, headers=headers, json={'name': 'Ada'})
        assert response.json['headers']['X-Inertia-Version'] == 'stale'
        assert response.json['headers']['X-Custom'] == 'value'
        assert response.json['data'] == {'name': 'Ada'}
        assert Headers(headers) == original
