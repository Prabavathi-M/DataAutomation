# Centralized Snowflake MCP Server Guide

This guide describes how to expose one centrally hosted Snowflake MCP server to multiple AI clients while keeping Snowflake credentials private and enforcing application-level roles.

## 1. Target architecture

```text
Team member's AI client
        |
        | HTTPS + OAuth access token
        v
Central MCP server
        |
        | Authenticate, authorize, validate request
        v
Snowflake service user
        |
        | Least-privilege read-only role
        v
Approved Snowflake views and tables
```

The central server is the only component that stores Snowflake credentials. Team members authenticate to the application, not by sharing the Snowflake service-user credentials.

## 2. Local versus centralized MCP

A local `stdio` MCP server works like this:

```text
AI client -> local Python MCP process -> local creds.env -> Snowflake
```

This is suitable for personal development. If every teammate runs the server locally, each machine needs a Snowflake credential, which is difficult to manage securely.

A centralized server works like this:

```text
Many AI clients -> HTTPS -> one central MCP server -> Snowflake
```

For the centralized model, use the MCP SDK's Streamable HTTP transport and protect the endpoint with HTTPS and authentication.

Not every AI client supports remote MCP servers or OAuth. Each client must support remote MCP over HTTP, or an approved adapter must be used.

## 3. Create a Snowflake read-only role

Use `ACCOUNTADMIN` only for security administration. Do not use it for normal MCP queries.

```sql
USE ROLE ACCOUNTADMIN;

CREATE ROLE IF NOT EXISTS MCP_READONLY_ROLE;

GRANT USAGE
ON WAREHOUSE COMPUTE_WH
TO ROLE MCP_READONLY_ROLE;

GRANT USAGE
ON DATABASE MY_LEARNING
TO ROLE MCP_READONLY_ROLE;

GRANT USAGE
ON SCHEMA MY_LEARNING.SAMPLES
TO ROLE MCP_READONLY_ROLE;
```

Prefer granting access to approved secure views instead of granting access to every base table.

Example:

```sql
CREATE OR REPLACE SECURE VIEW MY_LEARNING.SAMPLES.ORDERS_SAFE AS
SELECT
    ORDER_ID,
    ORDER_DATE,
    AMOUNT
FROM MY_LEARNING.SAMPLES.ORDERS;

GRANT SELECT
ON VIEW MY_LEARNING.SAMPLES.ORDERS_SAFE
TO ROLE MCP_READONLY_ROLE;
```

If you intentionally need all current and future tables, use the following broader grants instead:

```sql
GRANT SELECT
ON ALL TABLES IN SCHEMA MY_LEARNING.SAMPLES
TO ROLE MCP_READONLY_ROLE;

GRANT SELECT
ON FUTURE TABLES IN SCHEMA MY_LEARNING.SAMPLES
TO ROLE MCP_READONLY_ROLE;
```

The narrower view-based approach is recommended because it limits the data surface exposed to the MCP server.

## 4. Create a Snowflake service user

Create one dedicated service identity for the central server:

```sql
CREATE USER IF NOT EXISTS MCP_SERVICE_USER
  PASSWORD = '<generated-password>'
  DEFAULT_ROLE = MCP_READONLY_ROLE
  DEFAULT_WAREHOUSE = COMPUTE_WH
  MUST_CHANGE_PASSWORD = FALSE;

GRANT ROLE MCP_READONLY_ROLE
TO USER MCP_SERVICE_USER;
```

The central server should use this account, not your personal account and not `ACCOUNTADMIN`.

For a serious production deployment, prefer Snowflake key-pair authentication or OAuth instead of a long-lived password. Store private keys or passwords in a cloud secret manager such as Azure Key Vault, AWS Secrets Manager, Google Secret Manager, or HashiCorp Vault.

The server's secret configuration conceptually contains:

```env
SNOWFLAKE_USER=MCP_SERVICE_USER
SNOWFLAKE_ROLE=MCP_READONLY_ROLE
SNOWFLAKE_ACCOUNT=<account-identifier>
SNOWFLAKE_DATABASE=MY_LEARNING
SNOWFLAKE_SCHEMA=SAMPLES
SNOWFLAKE_WAREHOUSE=COMPUTE_WH
```

Never commit this file, place it in a public repository, or distribute it to teammates.

## 5. Test the Snowflake service identity

After configuring the service credentials, verify the active identity:

```sql
SELECT
    CURRENT_USER(),
    CURRENT_ROLE(),
    CURRENT_DATABASE(),
    CURRENT_SCHEMA();
```

Verify that the role is `MCP_READONLY_ROLE` and not `ACCOUNTADMIN`.

Test an approved read:

```sql
SELECT *
FROM MY_LEARNING.SAMPLES.ORDERS_SAFE
LIMIT 10;
```

Test that write access is denied in a controlled test environment. Do not run destructive statements against production data.

## 6. Do not expose arbitrary SQL initially

An unrestricted tool such as this is risky for a shared service:

```text
run_snowflake_query(sql)
```

A caller could submit any SQL permitted by the Snowflake role. Even with read-only access, a caller might read more data than intended or run expensive queries.

Prefer business-specific tools whose SQL is owned by the server:

```text
get_orders
get_order_by_id
get_products
```

Conceptual flow:

```text
get_orders request
    -> authenticate user
    -> require orders:read permission
    -> validate limit and filters
    -> execute predefined query against ORDERS_SAFE
    -> return bounded result
```

If an SQL tool is retained for learning, it should at minimum:

1. Accept only one `SELECT` statement.
2. Reject DDL and DML such as `INSERT`, `UPDATE`, `DELETE`, `DROP`, and `ALTER`.
3. Reject multiple statements and comments.
4. Allow only approved schemas, tables, or views.
5. Require a result limit.
6. Enforce a query timeout.
7. Enforce a maximum returned row count.
8. Record the authenticated user and query identifier.

Keyword filtering alone is not a complete security boundary. Predefined queries and approved views are safer.

## 7. Authenticate application users

Use an identity provider instead of implementing passwords in the MCP server. Suitable providers include:

- Microsoft Entra ID
- Okta
- Auth0
- Keycloak

Each teammate signs in individually. The identity provider issues an OAuth access token, which the AI client sends to the MCP server:

```http
Authorization: Bearer <access-token>
```

The MCP server must validate:

- Token signature
- Token issuer
- Token audience
- Token expiration
- Required scopes
- User identity
- Group or role claims

Never trust a role supplied in the request body. This is unsafe:

```json
{
  "user": "alice@company.com",
  "role": "admin"
}
```

The server must derive the user and role from a validated token or a trusted server-side authorization database.

## 8. Define application roles and permissions

Keep roles and permissions separate:

```text
User -> Application roles -> Permissions -> Allowed tools and data
```

Example permissions:

```text
orders:read
products:read
reports:read
customer_details:read
```

Example role mappings:

```text
orders_reader -> orders:read
products_reader -> products:read
data_admin -> orders:read, products:read, reports:read
```

Example user mappings:

```text
alice@company.com -> orders_reader
bob@company.com -> products_reader
manager@company.com -> data_admin
```

For a larger team, map identity-provider groups to application roles rather than hard-coding individual user names.

## 9. Define a tool authorization policy

Maintain a server-side policy similar to this:

| Tool | Required permission | Data source |
|---|---|---|
| `get_orders` | `orders:read` | `MY_LEARNING.SAMPLES.ORDERS_SAFE` |
| `get_order_by_id` | `orders:read` | `MY_LEARNING.SAMPLES.ORDERS_SAFE` |
| `get_products` | `products:read` | approved products view |

When a tool is called:

```text
1. Identify the authenticated user from the validated token.
2. Resolve the user's application roles.
3. Resolve the permissions for those roles.
4. Find the required permission for the requested tool.
5. Reject the request if the permission is missing.
6. Validate all tool inputs.
7. Execute only the approved query.
```

Authorization must be enforced in server code. Tool descriptions and AI prompts are not security controls.

## 10. Validate tool inputs

For every tool:

- Validate the input type.
- Validate required fields.
- Enforce maximum page size.
- Enforce maximum date range.
- Restrict sort fields to an allowlist.
- Restrict filter fields to approved fields.
- Reject unknown fields when appropriate.
- Set a query timeout.
- Set a maximum response size.

Example policy:

```text
limit: integer from 1 through 1000
sort_by: one of ORDER_DATE, AMOUNT
start_date: valid ISO date
end_date: valid ISO date
```

Never concatenate untrusted values into SQL. Use parameterized queries.

## 11. Add row and column restrictions

A user may have permission to read orders without being allowed to read every column.

Use secure views to expose only approved columns:

```sql
CREATE OR REPLACE SECURE VIEW MY_LEARNING.SAMPLES.ORDERS_SAFE AS
SELECT
    ORDER_ID,
    ORDER_DATE,
    AMOUNT
FROM MY_LEARNING.SAMPLES.ORDERS;
```

Do not grant the MCP role access to the base table if it contains sensitive columns.

For team-specific data, use one or both of these controls:

- Application-level filters based on trusted user context
- Snowflake row access policies

The team or tenant value must come from the authenticated identity, not from a user-provided SQL parameter.

For highly sensitive data, enforce restrictions in Snowflake as well as in the application.

## 12. Central server deployment

Deploy the MCP server behind a secure HTTPS endpoint:

```text
Load balancer or API gateway
        |
        v
Central MCP server instances
        |
        v
Secret manager and Snowflake
```

The deployment should provide:

- HTTPS with certificate validation
- Authentication middleware
- Authorization middleware
- Firewall or private network controls
- Rate limiting
- Request size limits
- Health checks
- Centralized logs
- Monitoring and alerting
- Automated deployment
- Secret rotation

Possible hosting platforms include Azure App Service, Azure Container Apps, Azure Kubernetes Service, AWS ECS, AWS Lambda where compatible, and Google Cloud Run.

The endpoint should expose only the MCP service. Do not expose Snowflake directly to client machines.

## 13. Configure AI clients

Each AI client should receive only the central MCP endpoint, for example:

```text
https://mcp.example.com/mcp
```

The configuration should not contain Snowflake credentials. The client should complete the supported OAuth flow and send access tokens to the server.

A client that supports only local `stdio` MCP cannot directly use a remote server without a compatible adapter or gateway.

## 14. Audit logging

Record application-level and database-level activity.

Application audit events should include:

```text
timestamp
authenticated user ID
application roles
tool name
validated request parameters
authorization result
Snowflake query ID
result row count
query duration
success or failure
```

Do not log:

- Access tokens
- Passwords
- Private keys
- Sensitive query results
- Unnecessary personal data

Snowflake may see only `MCP_SERVICE_USER`, so the application audit log must record which teammate initiated the request. A non-sensitive request ID can also be added as a Snowflake query tag.

## 15. Authorization test plan

Test every permission boundary:

```text
Unauthenticated request -> rejected
Expired token -> rejected
Invalid token -> rejected
Orders reader reads orders -> allowed
Orders reader reads products -> rejected
Products reader reads orders -> rejected
Data admin reads permitted data -> allowed
Unknown tool -> rejected
Excessive limit -> rejected
Arbitrary SQL -> rejected
Restricted column -> rejected
```

Test Snowflake access separately:

```text
MCP_SERVICE_USER can SELECT from approved view
MCP_SERVICE_USER cannot SELECT from restricted table
MCP_SERVICE_USER cannot INSERT
MCP_SERVICE_USER cannot UPDATE
MCP_SERVICE_USER cannot DELETE
MCP_SERVICE_USER cannot DROP
```

## 16. Recommended implementation order

### Stage 1: Snowflake foundation

1. Create `MCP_READONLY_ROLE`.
2. Create `MCP_SERVICE_USER`.
3. Create secure views.
4. Grant access only to approved views.
5. Test the service identity.

### Stage 2: Safer MCP tools

1. Replace unrestricted SQL with `get_orders`.
2. Add input validation.
3. Add row limits.
4. Add query timeouts.
5. Return structured results.

### Stage 3: Central deployment

1. Deploy the MCP server to a hosted environment.
2. Add HTTPS.
3. Move credentials to a secret manager.
4. Verify that multiple clients can reach the endpoint.

### Stage 4: Authentication

1. Register an application with the identity provider.
2. Configure OAuth.
3. Validate JWT issuer, audience, signature, and expiration.
4. Build the authenticated user context.

### Stage 5: Authorization

1. Map identity-provider groups to application roles.
2. Map roles to permissions.
3. Enforce permission checks before every tool.
4. Reject unauthorized tools and data.

### Stage 6: Data protection

1. Add secure views.
2. Add masking policies where required.
3. Add row-level policies for team or tenant isolation.

### Stage 7: Operations

1. Add audit logs.
2. Add rate limiting.
3. Add monitoring and alerting.
4. Rotate secrets.
5. Run authorization tests in CI/CD.

## 17. Production readiness summary

The intended production pattern is:

```text
Many individual users
    -> OAuth-authenticated central MCP server
    -> application RBAC
    -> predefined tools
    -> Snowflake service identity
    -> least-privilege Snowflake role
    -> secure views and row policies
    -> audit logging
```

Do not use this team pattern:

```text
Everyone copies creds.env
Everyone uses ACCOUNTADMIN
Everyone runs an unrestricted local SQL MCP
Users provide their own roles
No authentication
No audit logs
```

Begin with the smallest secure milestone: create the Snowflake service role and one safe `ORDERS_SAFE` view. Then test it before adding central hosting and OAuth.
