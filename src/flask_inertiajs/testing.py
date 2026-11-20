from flask import Response
from flask.testing import FlaskClient
from werkzeug.datastructures import Headers

from flask_inertiajs.asset_version import current_asset_version


class InertiaClient(FlaskClient):
    """A Flask client accepting `inertia=True` on request methods."""

    def open(self, *args, inertia: bool = False, **kwargs):
        if inertia:
            headers = Headers(kwargs.get('headers'))
            headers['X-Inertia'] = 'true'
            headers.setdefault('X-Inertia-Version', current_asset_version())
            kwargs['headers'] = headers
        return super().open(*args, **kwargs)


class InertiaResponse(Response):
    """Response helpers for asserting against Inertia JSON pages."""

    @property
    def inertia_page(self) -> dict:
        assert self.headers.get('X-Inertia') == 'true', 'Expected an Inertia JSON response'
        page = self.get_json(silent=True)
        assert isinstance(page, dict), 'Expected an Inertia page object with a props object'
        return page

    @property
    def inertia_props(self) -> dict:
        props = self.inertia_page.get('props')
        assert isinstance(props, dict), 'Expected Inertia page to have props'
        return self.inertia_page['props']
