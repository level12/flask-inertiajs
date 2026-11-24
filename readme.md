# flask-inertiajs

[![nox](https://github.com/level12/flask-inertiajs/actions/workflows/nox.yaml/badge.svg)](https://github.com/level12/flask-inertiajs/actions/workflows/nox.yaml)
[![codecov](https://codecov.io/gh/level12/flask-inertiajs/graph/badge.svg?token=xTfKjUGB3O)](https://codecov.io/gh/level12/flask-inertiajs)

[Inertia](https://inertiajs.com/docs/) v3 adapter for Flask with first-class Pydantic
support.


## Installation

`uv add flask-inertiajs[pydantic]`


## Configuration


### Minimal Config

```python
from pathlib import Path

from flask import Flask
from flask_inertiajs import Inertia

app = Flask(__name__)
app.config.update(
    # Must be set
    INERTIA_VITE_MANIFEST_PATH=(
        Path(app.root_path) / 'static' / 'build' / '.vite' / 'manifest.json'
    ),
)
inertia = Inertia()
inertia.init_app(app)
```


### Maximal Config

```python
from pathlib import Path

from flask import Flask
from flask_inertiajs import Inertia
from flask_inertiajs.asset_version import current_asset_version
from flask_inertiajs.pydantic import PropsModel


class SharedProps(PropsModel):
    csrf_token: str


class MyComponentProps(PropsModel):
    foo: str


app = Flask(__name__)
app.config.update(
    INERTIA_TEMPLATE='inertia.html',
    INERTIA_VITE_MANIFEST_PATH=(
        Path(app.root_path) / 'static' / 'build' / '.vite' / 'manifest.json'
    ),
    SECRET_KEY='not-so-secret',
)

inertia = Inertia(
    # Throw an error if the wrong props are used with a component.
    component_prop_types={
        'MyComponent': MyComponentProps,
    },
)
inertia.init_app(app)


@inertia.share
def shared_props() -> SharedProps:
    return SharedProps(csrf_token='generate CSRF token here')


# You can override or extend the default asset version, which is calculated by hashing INERTIA_VITE_MANIFEST_PATH and INERTIA_TEMPLATE.
@inertia.asset_version
def asset_version() -> str:
    release = (Path(app.root_path) / 'release.txt').read_text().strip()
    return f'{release}-{current_asset_version()}'
```


### Root Template

Create a template at `INERTIA_TEMPLATE` and use `{{ inertia_root() }}`:

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <!-- Load your frontend JS and CSS here. -->
  </head>
  <body>{{ inertia_root() }}</body>
</html>
```


## Usage

```python
from flask import redirect, request, url_for, flash
from pydantic import Field

from flask_inertiajs import InertiaView
from flask_inertiajs.pydantic import FormModel, validate


class MyForm(FormModel):
    captain: str = Field(min_length=1)


class MyView(InertiaView[MyComponentProps]):
    component = 'MyComponent'
    props_model = MyComponentProps

    def make_props(self) -> MyComponentProps:
        return MyComponentProps(foo='bar')

    # `get` is registered for you but overridable.

    def post(self):
        form, errors = validate(MyForm, request.get_json())
        if form is None:  # Validation failed.
            return self.render(errors=errors)

        flash('Yay')
        return redirect(url_for('my_view'))


app.add_url_rule('/bridge', view_func=MyView.as_view('my_view'))
```

See the tests for more examples.


## Features

These elements of
[the Inertia v3 protocol](https://inertiajs.com/docs/v3/core-concepts/the-protocol) are
currently supported:

- Basic responses (headers/component/props/url)
- Shared props
- Validation errors
- Flashes
- Redirects
- Asset versioning

Other elements of the Inertia v3 protocol are not currently supported but may be in the
future.


## Development


### Copier Template

Project structure and tooling mostly derives from
[Coppy](https://github.com/level12/coppy). See its documentation for context and
additional instructions.

This project can be updated from the upstream repo, see
[Updating a Project](https://github.com/level12/coppy?tab=readme-ov-file#template-updates).


### Project Setup

From zero to hero (passing tests that is):

1. Ensure [host dependencies](https://github.com/level12/coppy/wiki/Mise) are installed

2. Start docker service dependencies (if applicable):

   `docker compose up -d`

3. Sync [project](https://docs.astral.sh/uv/concepts/projects/) virtualenv w/ lock file:

   `uv sync`

4. Configure prek:

   `prek install`

5. Run tests:

   `nox`


### Versions

Versions are date based. A `version` task shows and bumps versions:

```shell

  # Show current version
  mise run version show

  # Bump version based on date, tag, and push:
  mise run version bump

  # See other options
  mise run version -- --help
```
