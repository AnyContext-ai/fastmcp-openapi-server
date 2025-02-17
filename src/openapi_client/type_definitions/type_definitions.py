from typing import TypedDict, Dict, Any

class OpenAPIOperation(TypedDict):
    path=str,
    method=str,
    details=dict

class OpenAPISpec(TypedDict):
    openapi: str
    info: Dict[str, Any]
    servers: Dict[str, Any]
    paths: Dict[str, Any]
    components: Dict[str, Any]