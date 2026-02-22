import os
import subprocess
import ast
from typing import Dict, Any, Tuple
from pathlib import Path

# Paths
PROJECT_ROOT = Path(os.getenv("PROJECT_ROOT", Path(__file__).parent.parent.parent))
GENERATED_TESTS_DIR = PROJECT_ROOT / "generated_tests"

def write_test_file(language: str, feature_name: str, code_content: str) -> str:
    """
    Saves the generated string of code securely to the designated test folder.
    Returns the absolute path to the saved file.
    """
    # Sanitize feature name for directory safety
    safe_feature = "".join(c for c in feature_name if c.isalnum() or c in ("_", "-"))
    if not safe_feature:
        safe_feature = "unknown_feature"
        
    ext = "py" if language.lower() == "python" else "js"
    filename = f"test_{safe_feature}.{ext}"
    
    target_dir = GENERATED_TESTS_DIR / language.lower() / safe_feature
    target_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = target_dir / filename
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(code_content)
        
    return str(file_path)

def check_syntax(code_content: str, language: str) -> Tuple[bool, str]:
    """
    Runs AST mapping on python files to catch SyntaxErrors before executing them.
    Returns (True, "Valid") if clean, or (False, ErrorMessage) if flawed.
    """
    if language.lower() != "python":
        return True, "Syntax checking for non-Python currently skipped."
        
    try:
        ast.parse(code_content)
        return True, "Valid"
    except SyntaxError as e:
        error_msg = f"SyntaxError on line {e.lineno}: {e.msg}\nLine content: {e.text}"
        return False, error_msg
    except Exception as e:
        return False, f"Unexpected error parsing AST: {str(e)}"

def run_pytest(test_file_path: str) -> Dict[str, Any]:
    """
    Executes pytest against the specified absolute file path.
    Returns standard console output, pass rate, and full exit codes.
    """
    if not os.path.exists(test_file_path):
        return {"success": False, "passed": False, "output": f"File not found: {test_file_path}", "summary": {}}
        
    try:
        # Run pytest inside the project root for module resolving
        result = subprocess.run(
            ["pytest", test_file_path, "-v"],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
            timeout=30 # Prevent infinite loops in generated tests
        )
        passed = result.returncode == 0
        return {
            "success": True,
            "passed": passed,
            "exit_code": result.returncode,
            "output": result.stdout + result.stderr,
            "summary": {"exit_code": result.returncode}
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "passed": False, "output": "Test execution timed out (30s limits enforced).", "summary": {}}
    except Exception as e:
        return {"success": False, "passed": False, "output": f"Failed to execute pytest: {str(e)}", "summary": {}}
