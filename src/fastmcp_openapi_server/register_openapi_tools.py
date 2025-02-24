import inspect
import functools
from fastmcp import FastMCP
from openapi_client import OpenAPIClient
from typing import Any, Literal, Optional
import re

# OpenAPI type → Python type mapping
OPENAPI_TO_PYTHON = {
    "string": str,
    "integer": int,
    "boolean": bool,
    "number": float,
    "array": list,
    "object": dict
}

def sanitize_parameter_name(name: str) -> str:
    # Replace invalid characters with underscores
    sanitized = re.sub(r'\W|^(?=\d)', '_', name)
    return sanitized


def get_python_type(schema: dict) -> Any:
    """Maps OpenAPI types to Python types, handling enums correctly."""
    if "enum" in schema:
        return Literal[tuple(schema["enum"])]  # Convert enum to Literal
    
    openapi_type = schema.get("type", "string")  # Default to string if type is missing
    return OPENAPI_TO_PYTHON.get(openapi_type, str)  # Fallback to str if type is unknown


def get_operation_description(operation: dict, param_descriptions: str) -> str:
    """Retrieves the best description for an OpenAPI operation, including parameters."""
    description = operation.get("description", "").strip()
    summary = operation.get("summary", "").strip()

    if description and summary:
        base_desc = f"{summary} - {description}"
    else:
        base_desc = description or summary or "No description available."

    return f"{base_desc}\n\n**Parameters:**\n{param_descriptions}"


def register_openapi_tools(client: OpenAPIClient, mcp_server: FastMCP):
    """Registers all OpenAPI operations as tools in FastMCP."""
    
    operations = client.get_operations()

    for operation in operations:
        operation_id = operation["details"]["operationId"]
        parameters = operation["details"].get("parameters", [])
        request_body = operation["details"].get("requestBody", {})

        # Separate required and optional parameters
        required_params = []
        optional_params = []
        param_descriptions = []

        # Extract path/query/header parameters with correct types
        for param in parameters:
            param_name = sanitize_parameter_name(param["name"])
            param_schema = param.get("schema", {})
            param_type = get_python_type(param_schema)  # Determine correct type
            required = param.get("required", False)  # Check if required

            # Format parameter description
            param_description = f"- `{param_name}` ({param_type.__name__})"
            if not required:
                param_description += " (Optional)"
            param_descriptions.append(param_description)

            # Define parameter signature
            param_def = inspect.Parameter(
                param_name,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                annotation=param_type
            )

            if required:
                required_params.append(param_def)
            else:
                optional_params.append(param_def.replace(default=None, annotation=Optional[param_type]))

        # Extract body parameters (if requestBody exists)
        if request_body:
            schema = request_body.get("content", {}).get("application/json", {}).get("schema", {})
            required_fields = schema.get("required", [])  # List of required fields

            for prop_name, prop_details in schema.get("properties", {}).items():
                orig_prop_name = prop_name
                prop_name = sanitize_parameter_name(orig_prop_name)
                prop_type = get_python_type(prop_details)

                param_description = f"- `{prop_name}` ({prop_type.__name__})"
                if prop_name not in required_fields:
                    param_description += " (Optional)"
                param_descriptions.append(param_description)

                param_def = inspect.Parameter(
                    prop_name,
                    inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    annotation=prop_type
                )

                if prop_name in required_fields:
                    required_params.append(param_def)
                else:
                    optional_params.append(param_def.replace(default=None, annotation=Optional[prop_type]))

        # Ensure required arguments come first
        param_defs = required_params + optional_params

        # Generate dynamic function signature
        func_signature = inspect.Signature(parameters=param_defs)

        # Get description/summary including parameter details
        formatted_param_descriptions = "\n".join(param_descriptions)
        operation_description = get_operation_description(operation["details"], formatted_param_descriptions)

        # Define the function dynamically using `functools.partial`
        def wrapped_func(operation_id, **kwargs):
            """Wrapped function that invokes OpenAPI operations."""
            response = client.invoke_operation(operation_id, **kwargs)
            try:
                return response.json()
            except: 
                return response.text

        wrapped_func = functools.partial(wrapped_func, operation_id)  # Bind `operation_id`
        functools.update_wrapper(wrapped_func, client.invoke_operation)  # Preserve metadata

        # Assign the dynamically generated signature
        wrapped_func.__signature__ = func_signature

        # Register the function in FastMCP
        mcp_server.add_tool(wrapped_func, operation_id, description=operation_description)
