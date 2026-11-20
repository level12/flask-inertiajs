# flask-inertiajs Initial Spec


## Features

We should only support
[the v3 protocol](https://inertiajs.com/docs/v3/core-concepts/the-protocol), and we should
only partially support that protocol.

Here are the features we should initially support:

- Page responses
- Shared props
- Validation errors
- Flash messages
- Redirects
- Asset versioning

Explicitly out of scope:

- Partial reloads
- CSRF support (we'll assume the CSRF token is passed through props)
- Error bags
- 4xx/5xx handling
- `back()`
- Vite tag helpers
- JSON Schema / TypeScript generation helpers and a CLI


## Principles

- Follow [the official Laravel adapter](https://github.com/inertiajs/inertia-laravel)
  where possible.
- First-class support for Pydantic props.
- Only need to support the latest Flask version.
- Test-driven development


## Decisions + Divergences from Laravel

- Use built-in flask flashes. Use this shape: `{"messages": [{"category", "message"}]}`
- Reject inertia requests to non-inertia endpoints
- Turn redirects to non-inertia pages into 409s
- Support function-based (`@inertia_view`) and class-based views
- Hash the vite manifest and the root template by default
- Pydantic is an extra, not a hard dependency
- Do not redirect for errors. In Flask, the best thing to do is just rerender (200) with
  errors. Allow `url=` overrides so that invalid POSTs to another URL stay on the same one
- Add a `ValidationError` -> `{field: msg}` converter as part of the pydantic extra.
  Generally follow internal prior art. Add a translation hook. One message per field.
- No stacked `share` callbacks. The "blessed" path is one Pydantic model for shared props.
- Allow a component -> props model registry that is validated at render time
- Default manifest path defaults to None, which excludes it from hashing.
- Ship a pydantic helper lib (`validate()`, `FormModel`, `SchemaModel`) in the extra, with
  no Babel or Sentry dependencies. `SchemaModel` serializes camelCase by default; apps can
  override `model_config`.


## Plan


### Prior art

- **inertia-laravel** (v3.7): `Middleware` (version, share, Vary, 302→303, version
  mismatch → 409, fragment redirect → `X-Inertia-Redirect`), `ResponseFactory::location`,
  `Response::toResponse` (page object, JSON vs root view), `Directive` (root element).
- **Internal Flask apps** (private): Pydantic page model, base Inertia view class, version
  hash of root template + manifest, rejecting Inertia requests to non-Inertia endpoints,
  303-vs-409 redirect choice, Flask flashes → `page.flash`, test client helpers, a
  `ValidationError` converter with translations, an `@inertia_view` marker, a strict
  `Props` base, a component → props-model registry checked at render, and a `SharedProps`
  model.


### Public API sketch

```python
from flask_inertiajs import Inertia, InertiaView, inertia_view, location, render
from flask_inertiajs.pydantic import validate

inertia = Inertia(app)  # or inertia.init_app(app)


@inertia.share  # exactly one; registering a second raises
def shared() -> SharedProps | dict:
    return SharedProps(user=..., csrf_token=generate_csrf())


@inertia.version  # optional override of the default hash
def version() -> str | None: ...


# optional registry; like `share` and `version`, applies to every app this instance is
# initialized on
inertia.register_component_prop_types({'Users/Create': UserCreateProps})


@app.route('/users/new', methods=['GET', 'POST'])
@inertia_view
def user_create():
    props = UserCreateProps(...)
    if request.method == 'POST':
        form, errors = validate(UserForm, request.json)
        if errors:
            return render('Users/Create', props, errors=errors, url=url_for('user_create'))
        flash('User created', 'success')
        return redirect(url_for('users'))  # 303, or 409 if `users` isn't Inertia
    return render('Users/Create', props)


class UserEdit(InertiaView):
    component = 'Users/Edit'
    props_model = UserEditProps
```

Config (all `INERTIA_*`): `TEMPLATE` (default `inertia.html`), `VITE_MANIFEST_PATH`
(path; default `None`).


### Behavior

- **Page object**: `component`, `props`, `url`, `version`, plus `sharedProps` (shared
  keys) and `flash` (only when non-empty), matching Laravel.
- **Props**: shared props merged under page props (page wins). `errors` always present,
  `{}` by default, set from `render(errors=...)`. Models dumped with
  `model_dump(mode='json')`, respecting each model's alias configuration; dicts passed
  through `flask.json`.
- **Registry**: without a configured registry, rendering is unchecked. Once a registry is
  configured, `render()` raises `KeyError` for missing components and `TypeError` unless
  the props are an instance of the registered model. An explicitly empty registry rejects
  every component; it is distinct from an unconfigured registry.
- **`url`**: path + query of the request (Laravel rules, trailing slash preserved), unless
  `render(url=...)` overrides it.
- **Flash**: `get_flashed_messages(with_categories=True)` →
  `{"messages": [{"category", "message"}]}`, popped only while rendering a page, so
  redirects and 409s leave them in the session with no reflash logic.
- **Opt-in endpoints**: `@inertia_view` or an `InertiaView` subclass marks an endpoint.
  `X-Inertia` requests to unmarked endpoints get 400; routing errors and Flask's slash
  redirects pass through untouched.
- **Redirects** (Inertia requests only): 302 → 303 for PUT/PATCH/DELETE; a redirect to an
  external URL or an unmarked endpoint becomes 409 + `X-Inertia-Location`; a `Location`
  with a `#fragment` becomes 409 + `X-Inertia-Redirect`. `location(url)` gives 409 for
  Inertia requests and a plain redirect otherwise.
- **Versioning**: default = sha256 of root template source + Vite manifest bytes (manifest
  skipped when absent). GET with mismatched `X-Inertia-Version` → 409 +
  `X-Inertia-Location` + `X-Inertia-Version`.
- **Response headers**: `X-Inertia: true` on JSON pages; `Vary: X-Inertia` on all
  responses from Inertia endpoints.
- **Root template**: Jinja global `inertia_root()` emits
  `<script data-page="app" type="application/json">…</script><div id="app"></div>` with
  `<`, `>`, `&` escaped. Use `inertia_root(id='bridge')` to customize both the script's
  `data-page` and the div's `id`; the default ID is `app`. The app owns the rest of the
  template (Vite tags, etc.).
- **Pydantic extra** (`flask_inertiajs.pydantic`):
    - `validate(model, data, context=None) -> (model | None, errors)`: dotted `loc` keys,
      last message per field wins, messages from a translation table keyed
      by error type.
    - Translation hook: apps replace or extend the table (default English messages, no
      Babel). Untranslated error types fall back to Pydantic's message and call an
      `on_untranslated` hook (default: `logging` warning; apps can plug in Sentry, etc.).
    - `SchemaModel`: props base with camelCase aliases, `serialize_by_alias`,
      `validate_by_name`, `extra='forbid'`.
    - `FormModel`: input base with `str_strip_whitespace`.
    - `InertiaErrors = dict[str, str]`.
    - `errors` is owned by `render()`; a props model that declares an `errors` field
      raises at render time.
    - Core never imports Pydantic directly; it detects models via duck typing
      (`model_dump`) or a guarded import.


### Modules

- `extension.py`: `Inertia` (`init_app`, `share`, `version`,
  `register_component_prop_types`) plus `before_request` (endpoint check, version check)
  and `after_request` (Vary, redirect rewriting).
- `response.py`: `render()`, `location()`, page object assembly, JSON vs HTML.
- `views.py`: `inertia_view` decorator, `InertiaView` (MethodView with `component` and
  `props_model`), `is_inertia_endpoint()`.
- `template.py`: `inertia_root()` and JSON escaping.
- `assets.py`: default asset version (`version.py` is the package version).
- `pydantic.py`: the extra.
- `testing.py`: client with `inertia=True` (sets `X-Inertia` and current version) and
  response helpers `inertia_page` / `inertia_props`.


### Order of work (TDD, one PR-sized step each)

1. **Scaffold**: `flask` dep, `pydantic` extra, test app fixture, `testing.py` helpers.
2. **Page responses**: `render()` HTML + JSON, `inertia_root()`, `url` rules and
   override, `X-Inertia`/`Vary` headers, dict props.
3. **Pydantic props + registry**: model serialization, `register_component_prop_types`
   type check.
4. **Shared props**: single `share` callback, merge precedence, `sharedProps`.
5. **Views**: `@inertia_view`, `InertiaView`, 400 for unmarked endpoints.
6. **Asset versioning**: default hash, override, 409 on mismatch.
7. **Redirects**: 303 rewrite, 409 for non-Inertia targets, fragments, `location()`.
8. **Validation errors**: `render(errors=...)`, `validate()`, translation and untranslated
   hooks, `SchemaModel`/`FormModel`.
9. **Flash**: Flask flashes → `page.flash`.
10. **Docs/readme**: minimal Flask + Vite + Inertia client setup, CSRF-via-props example.
