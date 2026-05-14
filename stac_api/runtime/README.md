# veda.stac_api

## Middleware and multitenancy components

Tenant-related behavior comes from **several middleware components**. Each row names one component, what it does, and how it is turned on (some are always on; others depend on environment variables).

| Component | Role | Enabled when |
| --- | --- | --- |
| **`TenantExtractionMiddleware`** | Parses tenant URLs such as `{root_path}/{tenant}/collections`, sets `request.state.tenant`, and rewrites `scope["path"]` so routing matches the usual STAC paths. | **Always** (see `app.py`). Independent of `VEDA_STAC_ENABLE_STAC_AUTH_PROXY`. |
| **`TenantLinksMiddleware`** | For JSON STAC responses, rewrites `links` so clients stay on the tenant-prefixed URL when a tenant is present. | **Always** (see `app.py`). |
| **`stac-auth-proxy` (`configure_app`)** | Wraps the STAC app: OpenAPI + OpenID Connect for clients, registers **`CollectionFilter` / `ItemFilter`** so list/search respect collection tenant metadata (`VEDA_TENANT_FILTER_FIELD`, default `eic:tenant`), and requires OAuth scopes on write routes. | When `VEDA_STAC_OPENID_CONFIGURATION_URL` is set **and** `VEDA_STAC_ENABLE_STAC_AUTH_PROXY=True`. |
| **`PEPMiddleware`** | Keycloak UMA checks on configured write routes. | When `VEDA_STAC_OPENID_CONFIGURATION_URL` is set **and** `VEDA_KEYCLOAK_UMA_RESOURCE_SERVER_CLIENT_SECRET_NAME` is set. |

**How this fits together:**

- **Tenant in the URL** (`/api/stac/{Tenant=veda}/collections`, …) is handled by the **two URL-tenant middleware components** in the table so the core STAC app still sees `/api/stac/collections` while `request.state.tenant` is set. That works even when the auth proxy wrapper is **off**.
- **Tenant in collection metadata** (filtering which collections/items appear for a tenant) is driven by the **filters registered through `stac-auth-proxy`** when the proxy is **on**. Turning the proxy off removes that integration; it does **not** remove URL parsing or link rewriting from the tenant middleware.
- **Transactions** still require `VEDA_STAC_ENABLE_TRANSACTIONS=True` and, per configuration rules, `VEDA_STAC_ENABLE_STAC_AUTH_PROXY=True` when transactions are enabled.

Implementation reference: [`stac_api/runtime/src/app.py`](src/app.py) (conditional `configure_app`, optional PEP, then unconditional `TenantExtractionMiddleware` / `TenantLinksMiddleware`).

## Enabling Multitenant STAC Backend

To enable a multi-tenant STAC backend with transaction support and authentication, the following must be set:

1. **Enable Transactions**: Set `VEDA_STAC_ENABLE_TRANSACTIONS=True`
2. **Enable STAC Auth Proxy**: Set `VEDA_STAC_ENABLE_STAC_AUTH_PROXY=True`
3. **Configure OIDC**: Provide `VEDA_STAC_OPENID_CONFIGURATION_URL` and `VEDA_STAC_CLIENT_ID`

### Required Environment Variables

- `VEDA_STAC_ENABLE_TRANSACTIONS=True` - Enables STAC transaction endpoints (POST, PUT, DELETE)
- `VEDA_STAC_ENABLE_STAC_AUTH_PROXY=True` - Wraps the app with `stac-auth-proxy` (OpenID Connect for clients, and registers `CollectionFilter` / `ItemFilter` so list/search endpoints respect collection tenant metadata and POST/PUT/PATCH/DELETE require OAuth scopes)
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

A [migration DAG](https://github.com/NASA-IMPACT/veda-data-airflow/blob/dev/dags/veda_data_pipeline/veda_tenant_tagging_pipeline.py) is available in the [veda-data-airflow](https://github.com/NASA-IMPACT/veda-data-airflow) repository to add tenant fields to existing collections. The migration adds the `eic:tenant` field to collection metadata for the specified set of collections

**Field Format:**

The `eic:tenant` field should contain a string identifier for the tenant.

## Disabling Multitenancy

Multi-tenancy has several parts. The **two optional layers** below (auth-proxy filter integration and PEP) are toggled independently. Both require `VEDA_STAC_OPENID_CONFIGURATION_URL` to be set, plus each layer’s own second flag.

| Layer | What it does | Enabled when | Disabled when |
| --- | --- | --- | --- |
| **Tenant-scoped filtering** | Wraps the app with `stac-auth-proxy`: OpenID Connect, registers `CollectionFilter` / `ItemFilter` for tenant-aware list/search, OAuth-scoped write endpoints | `VEDA_STAC_OPENID_CONFIGURATION_URL` is set **and** `VEDA_STAC_ENABLE_STAC_AUTH_PROXY=True` | `VEDA_STAC_OPENID_CONFIGURATION_URL` is not set **or** `VEDA_STAC_ENABLE_STAC_AUTH_PROXY=False` |
| **PEP authorization** | Adds Keycloak UMA middleware that checks per-tenant resource permissions on protected routes | `VEDA_STAC_OPENID_CONFIGURATION_URL` is set **and** `VEDA_KEYCLOAK_UMA_RESOURCE_SERVER_CLIENT_SECRET_NAME` is set | `VEDA_STAC_OPENID_CONFIGURATION_URL` is not set **or** `VEDA_KEYCLOAK_UMA_RESOURCE_SERVER_CLIENT_SECRET_NAME` is not set |

> **_NOTE:_**  `TenantExtractionMiddleware` and `TenantLinksMiddleware` (URL tenant prefix and JSON link rewriting) are **always** registered. They do not appear in this table because they are not toggled by these env vars; see [Middleware and multitenancy components](#middleware-and-multitenancy-components). When clients only use normal STAC paths (for example `/api/stac/collections` with no extra path segment), tenant extraction is a no-op.

### Turning off each layer individually

**To disable PEP authorization only** (keep tenant filtering if configured):

- Unset `VEDA_KEYCLOAK_UMA_RESOURCE_SERVER_CLIENT_SECRET_NAME`. This prevents the Keycloak UMA `PEPMiddleware` from being added. Write endpoints will still require a valid OIDC token (enforced by `stac-auth-proxy`), but there will be no per-tenant resource permission checks.

**To disable transaction (write) endpoints:**

- Set `VEDA_STAC_ENABLE_TRANSACTIONS=False` (or leave unset). This is independent of both layers above and removes the POST/PUT/DELETE routes for collections and items.
