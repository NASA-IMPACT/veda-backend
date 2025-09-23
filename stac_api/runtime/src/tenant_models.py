""" Tenant Models for STAC API """
from typing import Optional

from pydantic import BaseModel, Field, field_validator

class TenantContext(BaseModel):
    """Context information for tenant-aware request processing"""

    tenant_id: str = Field(..., description="Tenant identifier")
    request_id: Optional[str] = Field(None, description="Request correlation ID")

    @field_validator("tenant_id")
    @classmethod
    def validate_tenant_id(cls, v):
        """Validates the tenant ID and also normalizes it to lowercase and trims the whitespace"""
        if not v or not v.strip():
            raise ValueError("Tenant ID cannot be empty")
        if len(v) > 100:
            raise ValueError("Tenant ID too long")
        return v.strip().lower()
