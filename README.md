# fastmcp-openapi-server

## Installation
1. Clone the repository: `git clone git@github.com:AnyContext-ai/fastmcp-openapi-server.git`
2. Build: `uv build`
3. Install: `uv tool install dist/fastmcp_openapi_server-<version>-py3-none-any.whl`

## Run with Claude Desktop
Add this to your Claude Desktop configuration:
```
{
  "mcpServers": {
    "fastmcp-openapi-server": {
      "command": "fastmcp-openapi-server",
      "args": [
        "--transport",
        "stdio",
        "--openapi"
      ]
    }
  }
}
```

## Command Line Arguments
```
usage: fastmcp-openapi-server [-h] [--transport TRANSPORT] --openapi OPENAPI [--port PORT] [--headers HEADERS] [--oauth2-client-id OAUTH2_CLIENT_ID]
                              [--oauth2-client-secret OAUTH2_CLIENT_SECRET] [--oauth2-token-url OAUTH2_TOKEN_URL] [--oauth2-scopes OAUTH2_SCOPES]

FastMCP Server for OpenAPI-based APIs

options:
  -h, --help            show this help message and exit
  --transport TRANSPORT
                        Transport method for FastMCP server (sse or stdio)
  --openapi OPENAPI     Path to OpenAPI spec (JSON file or URL)
  --port PORT           Port to run FastMCP server on (only for SSE transport)
  --headers HEADERS     Custom headers in JSON format (e.g., '{"Authorization": "Bearer XYZ"}')
  --oauth2-client-id OAUTH2_CLIENT_ID
                        OAuth2 Client ID
  --oauth2-client-secret OAUTH2_CLIENT_SECRET
                        OAuth2 Client Secret
  --oauth2-token-url OAUTH2_TOKEN_URL
                        OAuth2 Token URL
  --oauth2-scopes OAUTH2_SCOPES
                        OAuth2 Scopes
```

### Examples
```
fastmcp-openapi-server --openapi .\sample-openapi-specs\yr.json

fastmcp-openapi-server --openapi .\sample-openapi-specs\weatherapi-openapi.json --headers '{\"key\": \"my-super-secret-api-key\"}'

fastmcp-openapi-server --openapi https://example.com/openapi.json --oauth2-client-id some-client-id --oauth2-client-secret my-super-secret-token --oauth2-token-url https://example.com/token

```