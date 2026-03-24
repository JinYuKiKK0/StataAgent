from pydantic import BaseModel


class VariableBinding(BaseModel):
    variable_name: str
    table_name: str
    field_name: str
    confidence: float
