from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator

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


class TenantSearchRequest(BaseModel):
    """Tenant-aware search request model."""

    tenant: Optional[str] = Field(None, description="Tenant identifier")
    collections: Optional[List[str]] = Field(None, description="Collection IDs to search")
    bbox: Optional[List[float]] = Field(None, description="Bounding box")
    datetime: Optional[str] = Field(None, description="Datetime range")
    limit: int = Field(10, description="Maximum number of results")
    token: Optional[str] = Field(None, description="Pagination token")
    filter: Optional[Dict[str, Any]] = Field(None, description="CQL2 filter")
    filter_lang: str = Field("cql2-text", description="Filter language")

class TenantValidationError(HTTPException):
    def __init__(
        self,
        resource_type: str,
        resource_id: str,
        tenant: str,
        actual_tenant: Optional[str] = None
    ):
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.tenant = tenant
        self.actual_tenant = actual_tenant

        detail = f"{resource_type} {resource_id} not found for tenant {tenant}"
        if actual_tenant:
            detail += f" (found tenant: {actual_tenant})"

        super().__init__(status_code=404, detail=detail)