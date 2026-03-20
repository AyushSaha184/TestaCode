from __future__ import annotations

from backend.input.parsers import ParserService, PythonFunctionParser
from backend.schemas import Language


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


def test_python_parser_cache_key_ignores_formatting() -> None:
    parser_service = ParserService(ttl_seconds=60)

    code_a = "def add(a:int,b:int)->int:\n    return a+b\n"
    code_b = "def add(a: int, b: int) -> int:\n    return a + b\n"

    key_a = parser_service._cache_key("session-1", Language.python, code_a)
    key_b = parser_service._cache_key("session-1", Language.python, code_b)

    assert key_a == key_b


def test_python_parser_cache_key_ignores_comments() -> None:
    parser_service = ParserService(ttl_seconds=60)

    code_a = "def add(a: int, b: int) -> int:\n    # computes sum\n    return a + b\n"
    code_b = "def add(a: int, b: int) -> int:\n    # sum function updated comment\n    return a + b\n"

    key_a = parser_service._cache_key("session-1", Language.python, code_a)
    key_b = parser_service._cache_key("session-1", Language.python, code_b)

    assert key_a == key_b


def test_python_parser_cache_key_changes_with_docstring_change() -> None:
    parser_service = ParserService(ttl_seconds=60)

    code_a = "def add(a: int, b: int) -> int:\n    \"\"\"Add values\"\"\"\n    return a + b\n"
    code_b = "def add(a: int, b: int) -> int:\n    \"\"\"Sum two integers\"\"\"\n    return a + b\n"

    key_a = parser_service._cache_key("session-1", Language.python, code_a)
    key_b = parser_service._cache_key("session-1", Language.python, code_b)

    assert key_a != key_b


def test_python_parser_cache_key_changes_with_signature_change() -> None:
    parser_service = ParserService(ttl_seconds=60)

    code_a = "def add(a: int, b: int) -> int:\n    return a + b\n"
    code_b = "def add(a: int, b: int, c: int = 0) -> int:\n    return a + b + c\n"

    key_a = parser_service._cache_key("session-1", Language.python, code_a)
    key_b = parser_service._cache_key("session-1", Language.python, code_b)

    assert key_a != key_b
