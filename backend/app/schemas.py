from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, Field, field_validator


class Login(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=128)


class OrderInput(BaseModel):
    event_id: str = Field(min_length=1, max_length=120)
    reference: str = Field(min_length=1, max_length=80)
    customer: str = Field(min_length=1, max_length=120)
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    currency: str = Field(pattern=r"^[A-Z]{3}$")

    @field_validator("event_id", "reference", "customer")
    @classmethod
    def clean(cls, value):
        if not value.strip():
            raise ValueError("Must not be blank")
        return value.strip()


class ConnectorInput(BaseModel):
    mode: Literal["available", "outage", "reject"]


class KeyInput(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class MemberInput(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=12, max_length=128)
    role: Literal["admin", "operator", "viewer"]


class MatchInput(BaseModel):
    order_reference: str = Field(min_length=1, max_length=80)
