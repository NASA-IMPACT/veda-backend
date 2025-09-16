""" Tenant Models for STAC API """
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from fastapi import HTTPException


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


class TenantSearchRequest(BaseModel):
    """Tenant-aware search request model"""

    tenant: Optional[str] = Field(None, description="Tenant identifier")
    collections: Optional[List[str]] = Field(
        None, description="Collection IDs to search"
    )
    bbox: Optional[List[float]] = Field(None, description="Bounding box")
    datetime: Optional[str] = Field(None, description="Datetime range")
    limit: int = Field(10, description="Maximum number of results")
    token: Optional[str] = Field(None, description="Pagination token")
    filter: Optional[Dict[str, Any]] = Field(None, description="CQL2 filter")
    filter_lang: str = Field("cql2-text", description="Filter language")
    conf: Optional[Dict] = None

    def add_tenant_filter(self, tenant: str) -> None:
        """Add tenant filter to the search request"""
        if not tenant:
            return

        # Create tenant filter for properties.tenant
        tenant_filter = {"op": "=", "args": [{"property": "tenant"}, tenant]}

        # If there's already a filter, combine using AND
        if self.filter:
            self.filter = {"op": "and", "args": [self.filter, tenant_filter]}
        else:
            self.filter = tenant_filter


class TenantValidationError(HTTPException):
    """Exception that can be used to raise tenant validation failures"""

    def __init__(
        self,
        resource_type: str,
        resource_id: str,
        tenant: str,
        actual_tenant: Optional[str] = None,
    ):
        """Initiailizes tenant validation error"""
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.tenant = tenant
        self.actual_tenant = actual_tenant

        detail = f"{resource_type} {resource_id} not found for tenant {tenant}"
        if actual_tenant:
            detail += f" (found tenant: {actual_tenant})"

        super().__init__(status_code=404, detail=detail)
