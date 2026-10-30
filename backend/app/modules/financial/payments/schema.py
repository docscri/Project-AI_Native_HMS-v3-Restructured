"""Payment and refund bodies."""
from pydantic import BaseModel, Field


class Payment(BaseModel):
    payment_method: str | None = Field(default=None, pattern="^(cash|upi|card)$")
    discount: int = Field(default=0, ge=0)
    discount_reason: str = ""


class Refund(BaseModel):
    amount: int | None = Field(default=None, ge=1)
    reason: str
