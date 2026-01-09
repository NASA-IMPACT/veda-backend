# veda.stac_api

## Enabling Multi-tenant STAC Backend

To enable a multi-tenant STAC backend with transaction support and authentication, the following must be set:

1. **Enable Transactions**: Set `VEDA_STAC_ENABLE_TRANSACTIONS=True`
2. **Enable STAC Auth Proxy**: Set `VEDA_STAC_ENABLE_STAC_AUTH_PROXY=True`
3. **Configure OIDC**: Provide `VEDA_STAC_OPENID_CONFIGURATION_URL` and `VEDA_STAC_CLIENT_ID`

### Required Environment Variables

- `VEDA_STAC_ENABLE_TRANSACTIONS=True` - Enables STAC transaction endpoints (POST, PUT, DELETE)
- `VEDA_STAC_ENABLE_STAC_AUTH_PROXY=True` - Enables authentication middleware and custom tenant filtering
- `VEDA_STAC_OPENID_CONFIGURATION_URL` - OIDC discovery endpoint URL
- `VEDA_STAC_CLIENT_ID` - OAuth2 client ID for authentication

#### Additional Notes

- When `enable_transactions` is `True`, `enable_stac_auth_proxy` must also be `True`
- The multitenant feature uses the `eic:tenant` field in collections for tenant filtering. To set a different value, you can change `VEDA_TENANT_FILTER_FIELD`.
- Transaction endpoints require authentication with appropriate scopes:
  - `stac:collection:create`, `stac:collection:update`, `stac:collection:delete`
  - `stac:item:create`, `stac:item:update`, `stac:item:delete`

When multi-tenancy is enabled on a STAC catalog, a collection has the option to be added to a tenant in order to be filtered by that tenant value. This also means that a collection does not need to belong to any tenant. It will still be available and retrievable in the STAC catalog.

### Migrating Existing Data to a Tenant Tagged Catalog

Existing collections in the STAC catalog need the `eic:tenant` field added to be visible in tenant-specific catalogs. Without this field, collections will only be accessible via the base `/api/stac/collections` endpoint and will not be able to be filtered by tenant.

**Migration Process:**

A migration DAG is available in the [veda-data-airflow](https://github.com/NASA-IMPACT/veda-data-airflow) repository to add tenant fields to existing collections. The migration adds the `eic:tenant` field to collection metadata for the specified set of collections

**Field Format:**

The `eic:tenant` field should contain a string identifier for the tenant.
