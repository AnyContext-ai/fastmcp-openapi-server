import json
import time
import httpx
from fastmcp import FastMCP
from openapi_client import OpenAPIClient
from .register_openapi_tools import register_openapi_tools
from argparse import ArgumentParser
from typing import Optional, Dict


def load_openapi_spec(openapi_source):
    """Load OpenAPI spec from either a local file or a URL."""
    if openapi_source.startswith("http"):
        try:
            response = httpx.get(openapi_source, timeout=10)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise ValueError(f"Error fetching OpenAPI spec from URL: {e}")
    else:
        try:
            with open(openapi_source, "r", encoding="utf-8") as openapi_spec_file:
                return json.load(openapi_spec_file)
        except FileNotFoundError:
            raise ValueError(f"Error: File not found: {openapi_source}")
        except json.JSONDecodeError:
            raise ValueError(f"Error: Failed to parse JSON from file: {openapi_source}")


class AuthenticatedOpenAPIClient(OpenAPIClient):
    """
    Subclass of OpenAPIClient that adds authentication support, including API keys and OAuth2 Client Credentials.

    Attributes:
        custom_headers (dict): Headers to be included in every request.
        oauth2_client_id (str): OAuth2 Client ID.
        oauth2_client_secret (str): OAuth2 Client Secret.
        oauth2_token_url (str): OAuth2 Token URL.
        access_token (str): The current access token.
        token_expires_at (float): Expiration time of the token in UNIX timestamp.
    """

    def __init__(
        self,
        openapi_spec,
        headers: Optional[Dict[str, str]] = None,
        oauth2_client_id: Optional[str] = None,
        oauth2_client_secret: Optional[str] = None,
        oauth2_token_url: Optional[str] = None,
        oauth2_scopes: Optional[str] = None,
    ):
        super().__init__(openapi_spec)
        self.custom_headers = headers or {}
        self.oauth2_client_id = oauth2_client_id
        self.oauth2_client_secret = oauth2_client_secret
        self.oauth2_token_url = oauth2_token_url
        self.oauth2_scopes = oauth2_scopes
        self.access_token = None
        self.token_expires_at = 0  # Store token expiration time

    def _fetch_oauth2_token(self):
        """
        Fetches an OAuth2 token using the client credentials grant.
        """
        if not self.oauth2_client_id or not self.oauth2_client_secret or not self.oauth2_token_url:
            return

        try:
            response = httpx.post(
                self.oauth2_token_url,
                data={
                    "grant_type": "client_credentials", 
                    "scope": self.oauth2_scopes, 
                    "client_id": self.oauth2_client_id, 
                    "client_secret": self.oauth2_client_secret
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()
            token_data = response.json()
            self.access_token = token_data.get("access_token")
            expires_in = token_data.get("expires_in", 3600)  # Default 1 hour
            self.token_expires_at = time.time() + expires_in - 30  # Refresh 30 sec before expiration

        except httpx.HTTPStatusError as e:
            raise ValueError(f"Error fetching OAuth2 token: {e}")

    def get_headers(self):
        """
        Returns headers, including authentication headers (API keys or OAuth2 Bearer token).

        If OAuth2 Client Credentials is configured, it will fetch a new token when needed.
        """
        headers = self.custom_headers.copy()

        # Handle OAuth2 token
        if self.oauth2_client_id and self.oauth2_client_secret and self.oauth2_token_url:
            if not self.access_token or time.time() >= self.token_expires_at:
                self._fetch_oauth2_token()
            headers["Authorization"] = f"Bearer {self.access_token}"

        return headers


def main():
    parser = ArgumentParser(description="FastMCP Server for OpenAPI-based APIs")
    parser.add_argument("--transport", type=str, default="sse", help="Transport method for FastMCP server (sse or stdio)")
    parser.add_argument("--openapi", type=str, required=True, help="Path to OpenAPI spec (JSON file or URL)")
    parser.add_argument("--port", type=int, default=8000, help="Port to run FastMCP server on (only for SSE transport)")
    parser.add_argument("--headers", type=str, default="{}", help="Custom headers in JSON format (e.g., '{\"Authorization\": \"Bearer XYZ\"}')")

    # OAuth2 Arguments
    parser.add_argument("--oauth2-client-id", type=str, help="OAuth2 Client ID")
    parser.add_argument("--oauth2-client-secret", type=str, help="OAuth2 Client Secret")
    parser.add_argument("--oauth2-token-url", type=str, help="OAuth2 Token URL")
    parser.add_argument("--oauth2-scopes", type=str, help="OAuth2 Scopes")

    args = parser.parse_args()

    # Load OpenAPI Spec (from URL or file)
    openapi_spec = load_openapi_spec(args.openapi)

    # Parse headers from JSON string
    try:
        custom_headers = json.loads(args.headers)
        if not isinstance(custom_headers, dict):
            raise ValueError
    except ValueError:
        raise ValueError("Error: --headers must be a valid JSON object (e.g., '{\"Authorization\": \"Bearer XYZ\"}')")

    # Create an authenticated OpenAPI client
    openapi_client = AuthenticatedOpenAPIClient(
        openapi_spec,
        headers=custom_headers,
        oauth2_client_id=args.oauth2_client_id,
        oauth2_client_secret=args.oauth2_client_secret,
        oauth2_token_url=args.oauth2_token_url,
        oauth2_scopes=args.oauth2_scopes,
    )

    # Create MCP Server
    mcp_server = FastMCP("OpenAPI", port=args.port)

    # Register OpenAPI operations in MCP Server
    register_openapi_tools(openapi_client, mcp_server)
    
    # Run the MCP Server
    mcp_server.run(args.transport)

if __name__ == "__main__":
    main()