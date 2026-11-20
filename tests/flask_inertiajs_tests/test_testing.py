from flask import jsonify, request
import pytest
from werkzeug.datastructures import Headers

from flask_inertiajs.asset_version import current_asset_version
from flask_inertiajs.testing import InertiaResponse


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
        response = client.post('/echo', inertia=True, headers=headers, json={'name': 'Picard'})
        assert response.json['headers']['X-Inertia-Version'] == 'stale'
        assert response.json['headers']['X-Custom'] == 'value'
        assert response.json['data'] == {'name': 'Picard'}
        assert Headers(headers) == original


class TestInertiaResponse:
    @pytest.mark.parametrize('root_id', ['app', 'custom-root'])
    def test_html_page(self, root_id):
        response = InertiaResponse(
            '<script src="/app.js"></script><div id="other"></div>'
            f'<script type="application/json" data-page="{root_id}">'
            '{"component":"Users/Show","props":{"name":"Picard"}}</script>'
            f'<div id="{root_id}"></div>',
            mimetype='text/html',
        )
        assert response.inertia_page == {
            'component': 'Users/Show',
            'props': {'name': 'Picard'},
        }
        assert response.inertia_props == {'name': 'Picard'}

    def test_json_page(self):
        response = InertiaResponse(
            '{"component":"Users/Show","props":{"name":"Picard"}}',
            mimetype='application/json',
            headers={'X-Inertia': 'true'},
        )
        assert response.inertia_props == {'name': 'Picard'}

    @pytest.mark.parametrize(
        ('html', 'message'),
        [
            pytest.param('<div id="app"></div>', 'exactly one', id='missing-script'),
            pytest.param(
                '<script data-page="app" type="application/json">{}</script>' * 2,
                'exactly one',
                id='duplicate-scripts',
            ),
            pytest.param(
                '<script data-page="app">{}</script>',
                'application/json',
                id='missing-script-type',
            ),
            pytest.param(
                '<script data-page="" type="application/json">{}</script>',
                'non-empty',
                id='empty-root-id',
            ),
            pytest.param(
                '<script data-page="app" type="application/json">{}</script><div id="other"></div>',
                'matching root div',
                id='mismatched-root-div',
            ),
            pytest.param(
                '<script data-page="app" type="application/json">{}</script>'
                '<div id="app"></div><div id="app"></div>',
                'matching root div',
                id='duplicate-root-divs',
            ),
            pytest.param(
                '<script data-page="app" type="application/json">invalid</script>'
                '<div id="app"></div>',
                'valid JSON',
                id='invalid-json',
            ),
            pytest.param(
                '<script data-page="app" type="application/json">[]</script><div id="app"></div>',
                'page object',
                id='non-object-page',
            ),
        ],
    )
    def test_invalid_html(self, html, message):
        with pytest.raises(AssertionError, match=message):
            _ = InertiaResponse(html, mimetype='text/html').inertia_page

    def test_json_requires_header(self):
        with pytest.raises(AssertionError, match='Inertia JSON response'):
            _ = InertiaResponse('{}', mimetype='application/json').inertia_page

    def test_props_must_be_object(self):
        response = InertiaResponse(
            '{"props":[]}',
            mimetype='application/json',
            headers={'X-Inertia': 'true'},
        )
        with pytest.raises(AssertionError, match='have props'):
            _ = response.inertia_props
