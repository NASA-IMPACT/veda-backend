# VEDA Auth

Authentication and authorization utilities for veda-backend

## KeycloakPDPClient

A client for interacting with Keycloak's Authorization Services using the UMA (User-Managed Access) protocol to make authorization decisions.

### Overview

The `KeycloakPDPClient` enables applications to:

- Request a RPT (Requesting Party Token) from Keycloak
- Check user permissions for specific resources and scopes
- Extract tenant information from user token claims to help build the list of tenants where users have create/update access (for example, for the writable-tenants API endpoint)

### Installation

The client is part of the `veda_auth` package. You can install it with:

```bash
pip install common/auth/
```

### Basic Usage

```python
from veda_auth.keycloak_client import KeycloakPDPClient

# Initialize the client
pdp_client = KeycloakPDPClient(
    keycloak_url="https://keycloak.example.com",
    realm="my-realm",
    client_id="my-resource-server-client",
    client_secret="my-client-secret",  # Optional for confidential clients to retrieve values from AWS secrets
    timeout=10.0
)

try:
    # Get tenants with create/update access
    tenants = pdp_client.get_tenants_with_create_update_access(
        access_token=user_access_token,
        resource_type="collection"
    )

    # Check specific permission via scope (scopes represent an action you can take on a resource)
    has_permission = pdp_client.check_permission(
        access_token=user_access_token,
        resource_id="collection:tenant-name",
        scope="create"
    )
finally:
    pdp_client.close()
```

### Configuration

#### Required Parameters

- `keycloak_url`: Base URL of your Keycloak instance (e.g., `https://keycloak.example.com`)
- `realm`: Keycloak realm name
- `client_id`: Client ID for the resource server in Keycloak

#### Optional Parameters

- `client_secret`: Client secret (required for confidential clients)
- `timeout`: Request timeout in seconds (default: 5.0)

### Key Methods

#### `get_tenants_with_create_update_access(access_token, resource_type, tenant_list=None)`

Returns a list of tenant names where the user has both `create` and `update` scopes for the specified resource type.

**Parameters:**

- `access_token` (str): User's OAuth2 access token
- `resource_type` (str): Type of resource (`"collection"` or `"item"`)
- `tenant_list` (List[str], optional): Pre-filtered list of tenants to check

**Returns:**

- `List[str]`: Sorted list of tenant names with create/update access

**Example:**

```python
tenants = pdp_client.get_tenants_with_create_update_access(
    access_token=token,
    resource_type="collection"
)
# Returns: ["tenant1", "tenant2", "public"]
```


#### `check_permission(access_token, resource_id, scope)`

Checks if a user has a specific permission for a resource.

**Parameters:**
- `access_token` (str): User's OAuth2 access token
- `resource_id` (str): Resource identifier (e.g., `"collection:tenant-name"`)
- `scope` (str): Permission scope to check (e.g., `"create"`, `"update"`, `"read"`)

The scope is defined by the resource server. To see the definition for veda, check out [veda-keycloak config](https://github.com/NASA-IMPACT/veda-keycloak/blob/main/keycloak-config-cli/config/dev/veda.yaml#L340-L344)

**Returns:**

- `bool`: `True` if permission granted, `False` otherwise

**Example:**

```python
can_create = pdp_client.check_permission(
    access_token=token,
    resource_id="collection:my-tenant",
    scope="create"
)
```

#### `get_rpt(access_token, resources)`

Requests an RPT (Requesting Party Token) from Keycloak containing the user's permissions.

**Parameters:**

- `access_token` (str): User's OAuth2 access token
- `resources` (List[Dict]): List of resources to request permissions for. Each resource should have:
  - `resource_id`: Resource identifier
  - `resource_scopes`: List of scopes to check

**Returns:**

- `Dict`: RPT response containing permissions or an access token JWT

### Resource Identifier Format

Resources in Keycloak should follow this naming convention:

```json
stac:{resource_type}:{tenant_name}
```

These resource definitions must match the resources configured in Keycloak's authorization services.

For the actual resource definitions used in VEDA, see the [veda-keycloak configuration](https://github.com/NASA-IMPACT/veda-keycloak/blob/main/keycloak-config-cli/config/dev/veda.yaml#L334).

Examples:

- `stac:collection:tenant1:*`
- `stac:item:tenant2:*`
- `stac:collection:public:*`

### Token Claims

The `KeycloakPDPClient` extracts tenant names from the user's JWT when building the list of tenants the user can write to (for example, in `get_tenants_with_create_update_access` and the **GET `/auth/tenants/writable`** endpoint). This extraction is used only to **return** a list of writable tenants.

Tenant names are read from these claims:

- `group_membership.tenants` array – an array of group path strings
- `groups` array – an array of group path strings

Each group value is expected to contain the segment `/Tenants/`. The tenant name is taken as the third path component when splitting the string on `/`. For example:

- `"/Tenants/veda"`, the tenant extracted is `"veda"`
- `"/realm/role/Tenants/veda"`, the tenant extracted is  `"veda"`

### Resource Extractor Use Cases

This section summarizes how the resource extractor functions in `veda_auth.resource_extractors` derive the **Keycloak resource ID** for different API calls.

#### STAC API (`extract_stac_resource_id` function)

| Path pattern                           | Methods                           |  Resource          | Tenant source for resource ID                         | Resource ID returned (shape)                     | Notes                                                                                     |
|----------------------------------------------------|-----------------------------------|-------------------------------|-------------------------------------------------------|--------------------------------------------------|-------------------------------------------------------------------------------------------|
| `/collections`                                     | `POST`                            | Create collection             | Request body field `eic:tenant` (or `TENANT_FIELD`), or public | `stac:collection:{tenant}:*` or public | STAC create collection; same body-based extraction as PUT/PATCH.                          |
| `/collections/{collection_id}`                     | `GET`, `DELETE`   | Single collection             | `request.state.tenant` (from URL), or public fallback | `stac:collection:{tenant}:*` or public           | When the URL contains a tenant, the tenant comes from the URL path, otherwise it falls back to `public`.    |
| `/collections/{collection_id}`                     | `PUT`, `PATCH`                    | Single collection (write)     | Request body field `eic:tenant` (or `TENANT_FIELD`), or public | `stac:collection:{tenant}:*` or public | It reads the JSON body to determine tenant, if empty body it returns `None`.                    |
| `/collections/{collection_id}/items/{item_id}`     | All methods                       | Single item                   | `request.state.tenant` (from URL), or public fallback | `stac:item:{tenant}:*` or public                | Item body is **not** read for tenant; only URL-derived tenant (or public) is used.        |
| `/collections/{collection_id}/items`               | `GET`, `POST`                     | Items under a collection      | `request.state.tenant` (from URL), or public fallback | `stac:collection:{tenant}:*` or public           | Collection-scoped resource ID for listing/creating items.                                 |
| `/collections/{collection_id}/bulk_items`          | `POST`                            | Bulk item operations          | `request.state.tenant` (from URL), or public fallback | `stac:collection:{tenant}:*` or public           | Bulk operations are treated as collection-scoped actions.                                 |
| Any path containing `/queryables` or `/search`     | Any                               | Query/search endpoints        | _n/a_                                                 | `None`                                           | Resource ID is not extracted for query/search endpoints.                                  |

\* For methods on `/collections/{collection_id}` other than `PUT`/`PATCH`, the extractor uses the URL-derived tenant (or public) via `_stac_collection_resource_id`.

#### Ingest API (`extract_ingest_resource_id` function)

| Path pattern          | Method | Resource      | Tenant source for resource ID                          | Resource ID returned (shape)            | Notes                                                                                   |
|------------------------------------|--------|---------------------------|--------------------------------------------------------|-----------------------------------------|-----------------------------------------------------------------------------------------|
| `/collections`                     | `POST` | Create collection request | Request body field `eic:tenant` (or `TENANT_FIELD`), or public | `stac:collection:{tenant}:*` or public | Uses the same body-based extraction helper as the STAC collection write case.           |
| `/collections/{collection_id}`     | `DELETE` | Delete collection        | _none_ (no tenant used)                                | `collection:{collection_id}`           | Ingest delete uses an ID-scoped resource (`collection:{id}`) without tenant component. Tenant-aware deletes will be handled in Phase 2. |

### See Also

- [Keycloak Authorization Services Documentation](https://www.keycloak.org/docs/latest/authorization_services/)
- [Keycloak Resource Server Settings](https://www.keycloak.org/docs/latest/authorization_services/#resource_server_settings)
