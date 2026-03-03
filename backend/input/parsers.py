import ast
from typing import Dict, Any, List, Set
from backend.core.config import logger
from backend.input.models import ExtractedFunction


def parse_python_code(code_str: str) -> Dict[str, Any]:
    """
    Parses a Python code string using the ast module.
    Returns a dictionary containing:
      - 'functions': list of ExtractedFunction with full metadata
      - 'warnings': list of warning strings
    Raises SyntaxError if the code cannot be parsed.
    """
    warnings: List[str] = []
    functions: List[ExtractedFunction] = []

    # Strip potential markdown blocks sometimes passed by LLMs or Users
    if code_str.strip().startswith("```"):
        lines = code_str.strip().split("\n")
        if len(lines) >= 2 and lines[-1].strip() == "```":
            code_str = "\n".join(lines[1:-1])

    try:
        tree = ast.parse(code_str)

        # Collect all names defined at module level (for dependency detection)
        defined_names: Set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                defined_names.add(node.name)
            elif isinstance(node, ast.ClassDef):
                defined_names.add(node.name)
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        defined_names.add(target.id)

        # Collect import names
        import_names: Set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    import_names.add(alias.asname or alias.name)
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    import_names.add(alias.asname or alias.name)

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Skip private/dunder methods (except __init__)
                if node.name.startswith("_") and node.name != "__init__":
                    continue

                # Extract argument names
                args = [arg.arg for arg in node.args.args]

                # Extract type annotations
                type_annotations: Dict[str, str] = {}
                for arg in node.args.args:
                    if arg.annotation:
                        try:
                            type_annotations[arg.arg] = ast.unparse(arg.annotation)
                        except Exception:
                            type_annotations[arg.arg] = "Unknown"

                # Extract return annotation
                returns = None
                if node.returns:
                    try:
                        returns = ast.unparse(node.returns)
                    except Exception:
                        returns = "Unknown"

                # Extract decorators
                decorators: List[str] = []
                for dec in node.decorator_list:
                    try:
                        decorators.append(ast.unparse(dec))
                    except Exception:
                        decorators.append("Unknown")

                # Extract external dependencies (names used but not defined locally)
                external_deps: Set[str] = set()
                for child in ast.walk(node):
                    if isinstance(child, ast.Name) and child.id in import_names:
                        if child.id not in defined_names or child.id != node.name:
                            external_deps.add(child.id)
                    elif isinstance(child, ast.Attribute):
                        if isinstance(child.value, ast.Name) and child.value.id in import_names:
                            external_deps.add(child.value.id)

                functions.append(
                    ExtractedFunction(
                        name=node.name,
                        args=args,
                        type_annotations=type_annotations,
                        docstring=ast.get_docstring(node),
                        returns=returns,
                        decorators=decorators,
                        external_deps=sorted(external_deps),
                    )
                )

        if not functions:
            warnings.append("No trackable functions found in the provided Python code.")

        # Summarize external dependency count
        total_deps = sum(len(f.external_deps) for f in functions)
        if total_deps > 0:
            warnings.append(
                f"{total_deps} external import(s) detected across {len(functions)} function(s) — mocking recommended."
            )

    except SyntaxError as e:
        logger.error(f"AST Parsing failed with SyntaxError: {e}")
        raise e
    except Exception as e:
        logger.error(f"Unexpected error during AST parsing: {e}")
        warnings.append(f"Could not fully parse the file structure: {str(e)}")

    return {
        "functions": functions,
        "warnings": warnings,
    }
