import ast
from typing import Dict, Any, List
from backend.core.config import logger
from backend.input.models import ExtractedFunction

def parse_python_code(code_str: str) -> Dict[str, Any]:
    """
    Parses a python code string.
    Returns a dictionary containing 'functions' (list of ExtractedFunction)
    and 'warnings' (list of strings).
    Raises SyntaxError if the code is completely invalid.
    """
    warnings = []
    functions = []
    
    try:
        # Strip potential markdown blocks sometimes passed by LLMs or Users
        if code_str.strip().startswith("```"):
            lines = code_str.strip().split("\n")
            # Remove first line (```python) and last line (```)
            if len(lines) >= 2 and lines[-1].strip() == "```":
                code_str = "\n".join(lines[1:-1])

        tree = ast.parse(code_str)
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Ignore private/dunder methods by default unless it's __init__
                if node.name.startswith("_") and node.name != "__init__":
                    continue
                    
                args = [arg.arg for arg in node.args.args]
                
                # Extract return annotation if it exists as a strict string
                returns = None
                if node.returns:
                    try:
                        returns = ast.unparse(node.returns)
                    except Exception:
                        returns = "Unknown"

                functions.append(
                    ExtractedFunction(
                        name=node.name,
                        args=args,
                        docstring=ast.get_docstring(node),
                        returns=returns
                    )
                )

        if not functions:
            warnings.append("No trackable functions found in the provided Python code.")
            
    except SyntaxError as e:
        logger.error(f"AST Parsing failed with SyntaxError: {e}")
        # Re-raise so the endpoint can trap it and return an explicit HTTP 400
        raise e
    except Exception as e:
        logger.error(f"Unexpected error during AST parsing: {e}")
        warnings.append(f"Could not fully parse the file structure: {str(e)}")
        
    return {
        "functions": functions,
        "warnings": warnings
    }
