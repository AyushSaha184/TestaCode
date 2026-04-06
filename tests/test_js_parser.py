from __future__ import annotations

from backend.input.js_parser import JavaScriptTypeScriptParser
from backend.schemas import Language


def test_named_function():
    code = "function greet(name) { return `Hello ${name}`; }"
    parser = JavaScriptTypeScriptParser()
    result = parser.parse(Language.javascript, code)
    assert len(result) == 1
    assert result[0].name == "greet"
    assert [p.name for p in result[0].params] == ["name"]


def test_async_function():
    code = "async function fetchData(url, options) { return await fetch(url, options); }"
    parser = JavaScriptTypeScriptParser()
    result = parser.parse(Language.javascript, code)
    assert len(result) == 1
    assert result[0].name == "fetchData"
    assert [p.name for p in result[0].params] == ["url", "options"]


def test_arrow_function():
    code = "const add = (a, b) => a + b;"
    parser = JavaScriptTypeScriptParser()
    result = parser.parse(Language.javascript, code)
    assert len(result) == 1
    assert result[0].name == "add"
    assert [p.name for p in result[0].params] == ["a", "b"]


def test_function_expression():
    code = "const multiply = function(x, y) { return x * y; };"
    parser = JavaScriptTypeScriptParser()
    result = parser.parse(Language.javascript, code)
    assert len(result) == 1
    assert result[0].name == "multiply"


def test_class_method():
    code = """
class Calculator {
    add(a, b) { return a + b; }
    async subtract(a, b) { return a - b; }
}
"""
    parser = JavaScriptTypeScriptParser()
    result = parser.parse(Language.javascript, code)
    names = {fn.name for fn in result}
    assert "add" in names
    assert "subtract" in names


def test_typescript_generics():
    code = "export function transform<T>(input: T): T { return input; }"
    parser = JavaScriptTypeScriptParser()
    result = parser.parse(Language.typescript, code)
    assert len(result) == 1
    assert result[0].name == "transform"
    assert [p.name for p in result[0].params] == ["input"]


def test_export_default_function():
    code = "export default function handler(req, res) { res.send('ok'); }"
    parser = JavaScriptTypeScriptParser()
    result = parser.parse(Language.javascript, code)
    assert len(result) == 1
    assert result[0].name == "handler"


def test_dependency_hints_from_imports():
    code = """
import axios from 'axios';
import { readFile } from 'fs';
const lodash = require('lodash');

function processData(data) {
    axios.post('/events', data);
    const parsed = readFile(data.path);
    return lodash.pick(parsed, ['id']);
}
"""
    parser = JavaScriptTypeScriptParser()
    result = parser.parse(Language.javascript, code)
    assert len(result) == 1
    dep_hints = result[0].dependency_hints
    assert "axios" in dep_hints
    assert "lodash" in dep_hints
    # relative imports are excluded
    assert all(not h.startswith(".") for h in dep_hints)


def test_empty_input_returns_empty_list():
    parser = JavaScriptTypeScriptParser()
    result = parser.parse(Language.javascript, "")
    assert result == []


def test_malformed_code_returns_empty_list():
    parser = JavaScriptTypeScriptParser()
    result = parser.parse(Language.javascript, "}{}{}{this is not valid js at all!!!")
    assert isinstance(result, list)


def test_multiple_functions():
    code = """
function a(x) { return x; }
const b = (y) => y * 2;
async function c(z) { return await z; }
"""
    parser = JavaScriptTypeScriptParser()
    result = parser.parse(Language.javascript, code)
    names = [fn.name for fn in result]
    assert "a" in names
    assert "b" in names
    assert "c" in names


def test_skips_keywords():
    """Ensure control-flow keywords are not mistaken for function names."""
    code = """
class Foo {
    if(x) { return x; }
}
"""
    parser = JavaScriptTypeScriptParser()
    result = parser.parse(Language.javascript, code)
    names = [fn.name for fn in result]
    assert "if" not in names


def test_arrow_with_type_annotation():
    code = "const process = async (data: string[]): Promise<void> => { console.log(data); };"
    parser = JavaScriptTypeScriptParser()
    result = parser.parse(Language.typescript, code)
    assert len(result) == 1
    assert result[0].name == "process"
