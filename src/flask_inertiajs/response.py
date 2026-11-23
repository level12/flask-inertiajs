from dataclasses import asdict, is_dataclass
from typing import Any, NotRequired, TypedDict
from urllib.parse import urlsplit

from flask import (
    Response,
    current_app,
    get_flashed_messages,
    make_response,
    render_template,
    request,
)

from flask_inertiajs.asset_version import current_asset_version


try:
    from pydantic import BaseModel
except ImportError:
    BaseModel = None


class _FlashMessage(TypedDict):
    category: str
    message: str


class _Flash(TypedDict):
    messages: list[_FlashMessage]


class _InertiaPage(TypedDict):
    """The final shape of the Inertia page object."""

    component: str
    props: dict
    url: str
    version: str
    sharedProps: list[str]
    flash: NotRequired[_Flash]


class InertiaPage:
    component: str
    props: dict
    url: str

    def __init__(
        self,
        component: str,
        props: Any = None,
        *,
        errors: dict[str, str] | None = None,
        url: str | None = None,
    ):
        self._check_props_type(component, props)

        self.component = component
        self.props, self.shared_props = self._all_props(props, errors)
        self.url = url if url is not None else self._default_url

    @staticmethod
    def _check_props_type(component: str, props: Any):
        """If `register_component_prop_types` was used, check against it."""
        registry = current_app.extensions['inertia'].component_prop_types
        if registry is not None:
            model = registry[component]
            if not isinstance(props, model):
                raise TypeError(f'{component} requires {model.__name__} props')

    @staticmethod
    def _all_props(page_props: Any, errors: dict[str, str] | None) -> tuple[dict, list[str]]:
        """Given page-specific props and render-specific errors, returns a tuple of serialized
        `props`, `sharedProps`."""

        # Get and serialize shared props
        shared_props_callback = current_app.extensions['inertia'].shared_props_callback
        shared_props = (
            InertiaPage._serialize_props(shared_props_callback()) if shared_props_callback else {}
        )

        # Combine and serialize page props
        props = {
            **shared_props,
            **InertiaPage._serialize_props(page_props),
        }

        # Add errors
        if 'errors' in props:
            raise ValueError('Errors should be passed separately from props')
        props['errors'] = errors or {}

        return props, list(shared_props.keys())

    @staticmethod
    def _serialize_props(props: Any) -> dict:
        """Convert None, a dict, a dataclass, or a Pydantic model instance to a dict."""
        if props is None:
            return {}
        if isinstance(props, dict):
            return props
        if is_dataclass(props):
            return asdict(props)
        if BaseModel is not None and isinstance(props, BaseModel):
            return props.model_dump(mode='json')
        raise TypeError('Props must be a dict, dataclass, or Pydantic model instance')

    @property
    def _default_url(self) -> str:
        """The current url path plus the query string"""
        path = urlsplit(request.url).path
        query = request.query_string.decode()
        return path + (f'?{query}' if query else '')

    @staticmethod
    def _get_flashes() -> _Flash | None:
        if messages := get_flashed_messages(with_categories=True):
            return {'messages': [{'category': c, 'message': m} for c, m in messages]}

    def render(self) -> Response:
        """Render this page as HTML or JSON, depending on the active request headers."""
        page = _InertiaPage(
            component=self.component,
            props=self.props,
            url=self.url,
            version=current_asset_version(),
            sharedProps=self.shared_props,
        )
        if flashes := self._get_flashes():
            page['flash'] = flashes

        if request.headers.get('X-Inertia'):
            response = current_app.json.response(page)
            response.headers['X-Inertia'] = 'true'
        else:
            response = make_response(
                render_template(current_app.config['INERTIA_TEMPLATE'], page=page),
            )
        return response


def render(
    component: str,
    props: Any = None,
    *,
    errors: dict[str, str] | None = None,
    url: str | None = None,
):
    """Render an Inertia page as HTML or JSON, depending on the active request headers."""
    return InertiaPage(component, props, errors=errors, url=url).render()
