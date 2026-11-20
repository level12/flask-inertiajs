from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class SchemaModel(BaseModel):
    """Props base with camelCase serialization and strict field validation."""

    model_config = ConfigDict(
        json_schema_serialization_defaults_required=True,
        extra='forbid',
        alias_generator=to_camel,
        serialize_by_alias=True,
        validate_by_name=True,
    )
