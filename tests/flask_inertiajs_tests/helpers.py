from decimal import Decimal

from flask_inertiajs.pydantic import SchemaModel


class BridgeProps(SchemaModel):
    captain_name: str
    date: Decimal = Decimal('41153.7')


class EngineeringProps(SchemaModel):
    chief_engineer_name: str
