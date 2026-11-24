from decimal import Decimal

from pydantic import Field, ValidationInfo, field_validator

from flask_inertiajs.pydantic import FormModel, PropsModel


class BridgeProps(PropsModel):
    captain_name: str
    date: Decimal = Decimal('41153.7')


class EngineeringProps(PropsModel):
    chief_engineer_name: str


class TenForwardForm(FormModel):
    bartender_name: str = Field(min_length=1)
    customer_count: int = 1

    @field_validator('bartender_name')
    @classmethod
    def check_crew_membership(cls, value: str, info: ValidationInfo) -> str:
        if value not in info.context['bartenders']:
            raise ValueError('Not a bartender')
        return value
