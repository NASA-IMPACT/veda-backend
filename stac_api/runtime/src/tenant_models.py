from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator
from fastapi import HTTPException

class TenantContext(BaseModel):
    tenant_id: str = Field(..., description="Tenant identifier")
    request_id: Optional[str] = Field(None, description="Request correlation ID")

    @field_validator('tenant_id')
    @classmethod
    def validate_tenant_id(cls, v):
        if not v or not v.strip():
            raise ValueError("Tenant ID cannot be empty")
        if len(v) > 100:
            raise ValueError("Tenant ID too long")
        return v.strip().lower()

