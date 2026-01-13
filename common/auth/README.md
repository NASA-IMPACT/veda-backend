# VEDA Auth

Authentication and authorization utilities for veda-backend

## KeycloakPDPClient

A client for interacting with Keycloak's Authorization Services using the UMA (User-Managed Access) protocol to make authorization decisions.

### Overview

The `KeycloakPDPClient` enables applications to:

- Request a RPT (Requesting Party Token) from Keycloak
- Check user permissions for specific resources and scopes
- Extract tenant information from user tokens
- Get lists of tenants where users have create/update access

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
```
stac:{resource_type}:{tenant_name}
```

They are defined by the resource server configuration settings. For more examples, see [veda-keycloak config](https://github.com/NASA-IMPACT/veda-keycloak/blob/main/keycloak-config-cli/config/dev/veda.yaml#L331)

Examples:

- `stac:collection:tenant1`
- `stac:item:tenant2`
- `stac:collection:public`

### Token Claims

The client extracts tenant information from JWT token claims. It looks for tenants in:

- `group_membership.tenants` array
- `groups` array

### See Also

- [Keycloak Authorization Services Documentation](https://www.keycloak.org/docs/latest/authorization_services/)
- [Keycloak Resource Server Settings](https://www.keycloak.org/docs/latest/authorization_services/#resource_server_settings)
