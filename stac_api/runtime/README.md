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
