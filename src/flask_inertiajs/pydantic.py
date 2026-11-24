from collections.abc import Callable, Mapping
from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError
from pydantic.alias_generators import to_camel


InertiaErrors = dict[str, str]
Translations = Mapping[str, Callable[[dict[str, Any]], str]]


def validation_errors(
    error: ValidationError,
    *,
    translations: Translations | None = None,
    on_untranslated: Callable[[str], None] | None = None,
) -> InertiaErrors:
    """Flatten Pydantic errors to the shape that Inertia expects."""
    errors: InertiaErrors = {}
    for detail in error.errors():
        message = detail['msg']
        if translations is not None:
            error_type = detail['type']
            if error_type in translations:
                message = translations[error_type](detail.get('ctx', {}))
            elif on_untranslated is not None:
                on_untranslated(error_type)
        errors['.'.join(map(str, detail['loc']))] = message
    return errors


def validate[M: BaseModel](
    model: type[M],
    data: Any,
    context: dict | None = None,
    *,
    translations: Translations | None = None,
    on_untranslated: Callable[[str], None] | None = None,
) -> tuple[M | None, InertiaErrors]:
    """Validate `data` against `model`. Returns model instance (if valid, else None) and errors."""
    try:
        return model.model_validate(data, context=context), {}
    except ValidationError as error:
        return None, validation_errors(
            error,
            translations=translations,
            on_untranslated=on_untranslated,
        )


class FormModel(BaseModel):
    """Form base that strips strings, expects camelCase from the client, and returns errors in
    camelCase."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        alias_generator=to_camel,
    )


class PropsModel(BaseModel):
    """Props base with camelCase serialization and strict field validation."""

    model_config = ConfigDict(
        json_schema_serialization_defaults_required=True,
        extra='forbid',
        strict=True,
        alias_generator=to_camel,
        serialize_by_alias=True,
        validate_by_name=True,
    )
