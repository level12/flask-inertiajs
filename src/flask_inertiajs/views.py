from collections.abc import Callable

from flask import Response, current_app
from flask.views import MethodView

from flask_inertiajs.response import render


def inertia_view[F: Callable](view: F) -> F:
    """Mark a function-based view as supporting Inertia requests."""
    view._inertia_view = True
    return view


class InertiaView[PropsT](MethodView):
    """Base class for views that support Inertia requests."""

    component: str
    props_model: type[PropsT]

    def make_props(self, **kwargs) -> PropsT:
        """Build page props; override to load or transform view data."""
        return self.props_model(**kwargs)

    def render(
        self,
        *,
        errors: dict[str, str] | None = None,
        inertia_url: str | None = None,
        **kwargs,
    ) -> Response:
        return render(self.component, self.make_props(**kwargs), errors=errors, url=inertia_url)

    def get(self, **view_args) -> Response:
        return self.render(**view_args)


def is_inertia_endpoint(endpoint: str) -> bool:
    view = current_app.view_functions.get(endpoint)
    if getattr(view, '_inertia_view', False):
        return True
    view_class = getattr(view, 'view_class', None)
    return isinstance(view_class, type) and issubclass(view_class, InertiaView)
