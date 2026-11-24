from html.parser import HTMLParser

from flask import Response
from flask.testing import FlaskClient
from werkzeug.datastructures import Headers


class InertiaClient(FlaskClient):
    """A Flask client accepting `inertia=True` on request methods."""

    def open(self, *args, inertia: bool = False, **kwargs):
        if inertia:
            headers = Headers(kwargs.get('headers'))
            headers['X-Inertia'] = 'true'
            if 'X-Inertia-Version' not in headers:
                with self.application.test_request_context():
                    headers['X-Inertia-Version'] = self.application.extensions[
                        'inertia'
                    ].active_asset_version
            kwargs['headers'] = headers
        return super().open(*args, **kwargs)


class _InertiaRootParser(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.scripts = []
        self.divs = []
        self.script_data = ''
        self.in_page_script = False
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'script' and 'data-page' in attrs:
            self.scripts.append(attrs)
            self.in_page_script = True
        elif tag == 'div':
            self.divs.append(attrs)

    def handle_endtag(self, tag):
        if tag == 'script':
            self.in_page_script = False

    def handle_data(self, data):
        if self.in_page_script:
            self.script_data += data


class InertiaResponse(Response):
    """Response helpers for asserting against Inertia pages."""

    @property
    def inertia_page_html(self) -> dict:
        root = _InertiaRootParser(self.get_data(as_text=True))
        assert len(root.scripts) == 1, 'Expected exactly one Inertia data-page script'
        script = root.scripts[0]
        assert script.get('type') == 'application/json', 'Expected application/json script'
        root_id = script['data-page']
        assert root_id, 'Expected a non-empty data-page root ID'
        assert sum(div.get('id') == root_id for div in root.divs) == 1, (
            'Expected exactly one matching root div'
        )
        try:
            page = self.json_module.loads(root.script_data)
        except ValueError as exc:
            raise AssertionError('Expected valid JSON in Inertia script') from exc
        assert isinstance(page, dict), 'Expected an Inertia page object'
        return page

    @property
    def inertia_page_json(self) -> dict:
        assert self.headers.get('X-Inertia') == 'true', 'Expected an Inertia JSON response'
        page = self.get_json(silent=True)
        assert isinstance(page, dict), 'Expected an Inertia page object'
        return page

    @property
    def inertia_page(self) -> dict:
        if self.mimetype == 'text/html':
            return self.inertia_page_html
        return self.inertia_page_json

    @property
    def inertia_props(self) -> dict:
        props = self.inertia_page.get('props')
        assert isinstance(props, dict), 'Expected Inertia page to have props'
        return props
