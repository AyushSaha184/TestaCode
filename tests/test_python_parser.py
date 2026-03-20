from __future__ import annotations

from backend.input.parsers import PythonFunctionParser


def test_python_parser_extracts_metadata_and_dependencies() -> None:
    code = '''
import requests

@decorator
async def fetch_data(client: str, timeout: int = 10) -> dict:
    """Fetches data from remote API."""
    response = requests.get(client)
    return response.json()
'''
    parser = PythonFunctionParser()
    functions = parser.parse(code)

    assert len(functions) == 1
    fn = functions[0]
    assert fn.name == "fetch_data"
    assert [p.name for p in fn.params] == ["client", "timeout"]
    assert fn.return_annotation == "dict"
    assert fn.docstring == "Fetches data from remote API."
    assert "decorator" in fn.decorators
    assert "requests.get" in fn.dependency_hints
