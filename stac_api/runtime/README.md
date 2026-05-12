# veda.stac_api

## Enabling Multitenant STAC Backend

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

When multitenancy is enabled on a STAC catalog, a collection has the option to be added to a tenant in order to be filtered by that tenant value. This also means that a collection does not need to belong to any tenant. It will still be available and retrievable in the STAC catalog.

### Migrating Existing Data to a Tenant Tagged Catalog

Existing collections in the STAC catalog need the `eic:tenant` field added to be visible in tenant-specific catalogs. Without this field, collections will only be accessible via the base `/api/stac/collections` endpoint and will not be able to be filtered by tenant.

**Migration Process:**

A [migration DAG ](https://github.com/NASA-IMPACT/veda-data-airflow/blob/dev/dags/veda_data_pipeline/veda_tenant_tagging_pipeline.py)is available in the [veda-data-airflow](https://github.com/NASA-IMPACT/veda-data-airflow) repository to add tenant fields to existing collections. The migration adds the `eic:tenant` field to collection metadata for the specified set of collections

**Field Format:**

The `eic:tenant` field should contain a string identifier for the tenant.

## Disabling Multitenancy

Multi-tenancy is composed of two independent layers: **tenant-scoped filtering** and **PEP authorization**. Both require `VEDA_STAC_OPENID_CONFIGURATION_URL` to be set, but each has its own second toggle which can be enabled or disabled independently of each other.

| Layer | What it does | Enabled when |
| --- | --- | --- |
| **Tenant-scoped filtering** | Wraps the app with `stac-auth-proxy`, adding `CollectionFilter` / `ItemFilter` and OIDC-protected write endpoints | `VEDA_STAC_OPENID_CONFIGURATION_URL` is set **and** `VEDA_STAC_ENABLE_STAC_AUTH_PROXY=True` |
| **PEP authorization** | Adds Keycloak UMA middleware that checks per-tenant resource permissions on protected routes | `VEDA_STAC_OPENID_CONFIGURATION_URL` is set **and** `VEDA_KEYCLOAK_UMA_RESOURCE_SERVER_CLIENT_SECRET_NAME` is set |

### Turning off each layer individually

**To disable PEP authorization only** (keep tenant filtering if configured):

- Unset `VEDA_KEYCLOAK_UMA_RESOURCE_SERVER_CLIENT_SECRET_NAME`. This prevents the Keycloak UMA `PEPMiddleware` from being added. Write endpoints will still require a valid OIDC token (enforced by `stac-auth-proxy`), but there will be no per-tenant resource permission checks.

**To disable transaction (write) endpoints:**

- Set `VEDA_STAC_ENABLE_TRANSACTIONS=False` (or leave unset). This is independent of both layers above and removes the POST/PUT/DELETE routes for collections and items.
