import httpx
import re
from typing import List
from openapi_client.type_definitions.type_definitions import OpenAPIOperation, OpenAPISpec
from openapi_spec_validator import validate
from openapi_spec_validator.versions.shortcuts import get_spec_version
from openapi_spec_validator.versions import consts as versions
import jsonref

class OpenAPIClient:
    """
    A dynamic OpenAPI client for invoking HTTP requests based on operationId from the OpenAPI specification.

    This class loads an OpenAPI spec at runtime and dynamically constructs and invokes HTTP requests
    using the provided operationId. The client also allows for the injection of custom headers (e.g., authentication tokens)
    by overriding the `get_headers()` method.

    Attributes:
        openapi_spec (OpenAPISpec): A OpenAPI specification. 

    Methods:
        get_headers():
            Overridable method for injecting custom headers, such as authentication tokens.
        get_operation_by_id(operation_id: str):
            Retrieve the details of an API operation by its operationId.
        invoke_operation(operation_id: str, **kwargs):
            Invoke an API operation dynamically using the provided operationId and parameters.
    """
    
    def __init__(self, openapi_spec: OpenAPISpec):
        """
        Initialize the OpenAPIClient.

        Args:
            openapi_spec (OpenAPISpec): A OpenAPI specification). 
                Either `open_file_path` or `openapi_file_path` must be provided, but not both.
        """
        if openapi_spec:
            self.spec = openapi_spec
        else:
            raise ValueError("Either openapi_file_path or openapi_spec must be provided.")
        
        self.spec = jsonref.replace_refs(openapi_spec)
        
        try:
            spec_version = get_spec_version(self.spec)
            if (spec_version != versions.OPENAPIV30 and spec_version != versions.OPENAPIV31):
                raise ValueError("OpenAPI version must be 3.0 or 3.1")
            
            validate(self.spec)
        except Exception as error:
            raise ValueError(f"OpenAPI specification is not valid: {error}")
        
        # Check if operation_id is missing
        missing_operation_ids = []
        for path, path_item in self.spec['paths'].items():
            for method, operation in path_item.items():
                if 'operationId' not in operation:
                    missing_operation_ids.append(f"{method.upper()} {path}")
        if missing_operation_ids:
            self._add_operation_ids(self.spec)
        
    def get_headers(self):
        """
        Overridable method for users to inject custom headers, such as authentication.

        This method can be overridden by users to return headers like authentication tokens,
        API keys, or any custom headers required for API requests.

        Returns:
            dict: A dictionary of headers to be included in the request. By default, it returns an empty dictionary.
        """
        return {}
    
    def get_body(self):
        """
        Overridable method for users to inject custom body parameters.

        This method can be overridden by users to return body parameters required for API requests.

        Returns:
            dict: A dictionary of body parameters to be included in the request. By default, it returns an empty dictionary.
        """
        return {}
    
    def get_query_params(self):
        """
        Overridable method for users to inject custom query parameters.

        This method can be overridden by users to return query parameters required for API requests.

        Returns:
            dict: A dictionary of query parameters to be included in the request. By default, it returns an empty dictionary.
        """
        return {}
    
    def get_operations(self) -> List[OpenAPIOperation]:
        """
        Retrieve all operations defined in the OpenAPI specification

        Returns:
            list: A list of of OpenAPIOperation dicts.
        """
        operations = []
        for path, path_item in self.spec['paths'].items():
            for method, operation in path_item.items():
                operation = OpenAPIOperation(path=path, method=method, details=operation)
                operations.append(operation)
        return operations
    
    def get_operation_by_id(self, operation_id: str) -> OpenAPIOperation:
        """
        Retrieve the details of an API operation by its operationId.

        Args:
            operation_id (str): The operationId as defined in the OpenAPI specification.

        Returns:
            OpenAPIOperation: Dict object with 'path', 'method' (e.g. 'get', 'post', 'put', etc.) and 'details'.

        Raises:
            ValueError: If the operationId is not found in the OpenAPI specification.
        """
        # Find operation in the spec by operationId
        operations = self.get_operations()
        for operation in operations:
            if isinstance(operation["details"], dict) and operation["details"].get('operationId') == operation_id:
                return operation
        raise ValueError(f"Operation {operation_id} not found in the spec")

    def invoke_operation(self, operation_id: str, **kwargs):
        """
        Invoke the API operation dynamically based on operationId.

        This method uses the OpenAPI specification to determine the correct HTTP method, URL, and parameters 
        (path, query, headers, and body). Users can pass the required parameters as keyword arguments, 
        and they will be assigned to the appropriate part of the request.

        Args:
            operation_id (str): The operationId as defined in the OpenAPI specification.
            **kwargs: Dynamic keyword arguments that represent the parameters for the API call.
                     These can be path, query, header, or body parameters.

        Example:
            response = client.invoke_operation(
                operation_id="getUser",
                userId="123",  # Path parameter
                includeDetails=True  # Query parameter
            )

        Returns:
            httpx.Response: The HTTP response object from the invoked API call.
        """
        # Get the operation details using the operation_id
        operation = self.get_operation_by_id(operation_id)

        # Prepare containers for path, query, header, and body parameters
        path_params = {}
        query_params = self.get_query_params()
        headers = self.get_headers()
        body = self.get_body()

        # Automatically assign the provided kwargs to the correct parameter locations
        for parameter in operation["details"].get('parameters', []):
            param_name = parameter['name']
            param_in = parameter['in']  # Can be 'path', 'query', 'header', etc.

            if param_name in kwargs:
                if param_in == 'path':
                    path_params[param_name] = kwargs[param_name]
                elif param_in == 'query':
                    query_params[param_name] = kwargs[param_name]
                elif param_in == 'header':
                    headers[param_name] = kwargs[param_name]
        
        # Handle request body if present
        if 'requestBody' in operation["details"]:
            schema = operation["details"]['requestBody']['content']['application/json']['schema']
            for prop in schema['properties']:
                if prop in kwargs:
                    body[prop] = kwargs[prop]

        # Dynamically construct the path URL, removing the optional query parameters from the path
        base_url = self.spec['servers'][0]['url']  # Extract the base URL from the spec

        # Extract query params embedded in the path
        path = re.sub(r'\{\?.*?\}', '', operation["path"])  # Remove the `{?query}` part from the path
        url = base_url + path.format(**path_params)

        # Make the HTTP request
        with httpx.Client() as client:
            response = client.request(
                method=operation["method"].upper(),
                url=url,
                params=query_params,  # Add query parameters here
                headers=headers,  # Pass headers
                json=body if body else None  # Pass body if applicable
            )

        return response
    
    def _sanitize_path(self, path: str) -> str:
        path = re.sub(r'\{.*?\}', '', path)  # Remove {path} params
        path = path.strip("/").replace("/", "_")  # Replace / with _
        path = re.sub(r'[^a-zA-Z0-9_]', '', path)  # Remove special characters
        return path
        
    def _generate_operation_id(self, method, path):
        method = method.lower()
        sanitized_path = self._sanitize_path(path)

        # Convert snake_case to camelCase (e.g., "get_user_by_id" → "getUserById")
        components = sanitized_path.split("_")
        readable_path = "".join(word.capitalize() for word in components)

        return f"{method}{readable_path}"  # Example: getUserById

    def _add_operation_ids(self, openapi_spec):
        # Loop through all paths in the spec
        for path, path_item in openapi_spec.get('paths', {}).items():
            for method, operation in path_item.items(): # Loop through all methods (get, post, etc.) for each path
                if 'operationId' not in operation:
                    operation_id = self._generate_operation_id(method, path)
                    operation['operationId'] = operation_id
        return openapi_spec