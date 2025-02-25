import pytest
from openapi_client import OpenAPIClient
from openapi_client.type_definitions.type_definitions import OpenAPIOperation

# Sample OpenAPI spec for testing
openapi_spec_simple = {
    "openapi": "3.0.1",
    "info": {
        "title": "Sample API",
        "version": "1.0.0"
    },
    "paths": {
        "/test-endpoint": {
            "get": {
                "summary": "Test endpoint",
                "responses": {  # Adding the 'responses' field
                    "200": {
                        "description": "Successful response"
                    }
                }
            }
        }
    }
}

openapi_spec_3_operations = {
    "openapi": "3.0.1",
    "info": {
        "title": "Sample API",
        "version": "1.0.0"
    },
    "paths": {
        "/test-endpoint": {
            "get": {
                "operationId": "getTestEndpoint",
                "summary": "Test endpoint",
                "responses": {
                    "200": {
                        "description": "Successful response"
                    }
                }
            },
            "post": {
                "operationId": "createTestEndpoint",
                "summary": "Create something",
                "responses": {
                    "201": {
                        "description": "Created"
                    }
                }
            }
        },
        "/another-endpoint": {
            "put": {
                "operationId": "updateAnotherEndpoint",
                "summary": "Update something",
                "responses": {
                    "200": {
                        "description": "Updated"
                    }
                }
            }
        }
    }
}



def test_get_operations():
    client = OpenAPIClient(openapi_spec=openapi_spec_3_operations)
    operations = client.get_operations()

    # Check the number of operations
    assert len(operations) == 3     #There should be 3 operations in the spec

    # Define the expected operations for comparison
    expected_operations = [
        OpenAPIOperation(path="/test-endpoint", method="get", details=openapi_spec_3_operations["paths"]["/test-endpoint"]["get"]),
        OpenAPIOperation(path="/test-endpoint", method="post", details=openapi_spec_3_operations["paths"]["/test-endpoint"]["post"]),
        OpenAPIOperation(path="/another-endpoint", method="put", details=openapi_spec_3_operations["paths"]["/another-endpoint"]["put"])
    ]

    # Check each operation in the returned list
    for op, expected_op in zip(operations, expected_operations):
        assert op["path"] == expected_op["path"], f"Expected path {expected_op['path']}, but got {op['path']}"
        assert op["method"] == expected_op["method"], f"Expected method {expected_op['method']}, but got {op['method']}"
        assert op["details"] == expected_op["details"], "Operation details do not match"

def test_get_operation_by_id():
    client = OpenAPIClient(openapi_spec=openapi_spec_3_operations)

    # Test retrieving an operation that exists
    operation = client.get_operation_by_id("getTestEndpoint")
    assert operation['path'] == "/test-endpoint"
    assert operation['method'] == "get"
    assert operation['details']['operationId'] == "getTestEndpoint"

    # Test retrieving another operation that exists
    operation = client.get_operation_by_id("createTestEndpoint")
    assert operation['path'] == "/test-endpoint"
    assert operation['method'] == "post"
    assert operation['details']['operationId'] == "createTestEndpoint"

    # Test retrieving an operation that does not exist
    with pytest.raises(ValueError, match="Operation nonExistentOperation not found in the spec"):
        client.get_operation_by_id("nonExistentOperation")
