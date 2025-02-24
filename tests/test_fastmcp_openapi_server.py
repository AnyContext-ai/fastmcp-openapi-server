import pytest
from fastmcp_openapi_server import sanitize_parameter_name


@pytest.mark.parametrize("input_name, expected", [
    ("validName", "validName"),
    ("invalid-name", "invalid_name"),
    ("invalid name", "invalid_name"),
    ("123startwithdigit", "_123startwithdigit"),
    ("special!@#$%^&*()chars", "special__________chars"),
    ("camelCaseName", "camelCaseName"),
    ("snake_case_name", "snake_case_name"),
    ("mixed-CASE Name123", "mixed_CASE_Name123"),
    ("", ""),
    ("123", "_123"),
])
def test_sanitize_parameter_name(input_name, expected):
    assert sanitize_parameter_name(input_name) == expected
