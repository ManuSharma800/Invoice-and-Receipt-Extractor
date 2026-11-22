
from datetime import date
from typing import Literal, Optional, List

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError
)


# 1. Vendor information
class Vendor(BaseModel):

    model_config = ConfigDict(extra="forbid")

    name: Optional[str] = None
    address: Optional[str] = None
    contact: Optional[str] = None
    tax_id: Optional[str] = None


# 2. Individual purchased item
class InvoiceItem(BaseModel):

    model_config = ConfigDict(extra="forbid")

    description: str
    quantity: Optional[float] = Field(default=None, ge=0)
    unit_price: Optional[float] = Field(default=None, ge=0)
    amount: Optional[float] = Field(default=None, ge=0)


# 3. Main invoice/receipt model
class InvoiceData(BaseModel):

    model_config = ConfigDict(extra="forbid")

    document_type: Literal["invoice", "receipt"]

    document_number: Optional[str] = None

    document_date: Optional[date] = None

    currency: Optional[str] = None

    vendor: Vendor = Field(default_factory=Vendor)

    items: List[InvoiceItem] = Field(default_factory=list)

    subtotal: Optional[float] = Field(default=None, ge=0)

    discount: Optional[float] = Field(default=None, ge=0)

    tax: Optional[float] = Field(default=None, ge=0)

    tax_rate: Optional[float] = Field(default=None, ge=0)

    additional_charges: Optional[float] = Field(
        default=None,
        ge=0
    )

    total: Optional[float] = Field(default=None, ge=0)


# 4. Validate extracted invoice data
def validate_invoice(data: dict) -> InvoiceData:

    return InvoiceData.model_validate(data)


# 5. Convert validated data into JSON-compatible dictionary
def invoice_to_dict(invoice: InvoiceData) -> dict:

    return invoice.model_dump(mode="json")


# 6. Convert validated data into formatted JSON
def invoice_to_json(invoice: InvoiceData) -> str:

    return invoice.model_dump_json(indent=4)


# 7. Identify important missing fields
def get_missing_fields(invoice: InvoiceData) -> list:

    missing = []

    if not invoice.vendor.name:
        missing.append("vendor.name")

    if not invoice.document_date:
        missing.append("document_date")

    if not invoice.total and invoice.total != 0:
        missing.append("total")

    if not invoice.currency:
        missing.append("currency")

    return missing
