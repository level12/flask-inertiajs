from flask import current_app
from jinja2 import pass_context
from jinja2.runtime import Context
from jinja2.utils import htmlsafe_json_dumps
from markupsafe import Markup


@pass_context
def inertia_root(context: Context, *, id: str = 'app') -> Markup:
    """Render the page JSON and mount div from the template's `page` context."""
    page_json = htmlsafe_json_dumps(context['page'], dumps=current_app.json.dumps)
    return Markup(
        '<script data-page="{id}" type="application/json">{page}</script><div id="{id}"></div>',
    ).format(id=id, page=page_json)
