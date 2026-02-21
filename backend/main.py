"""
FastAPI Backend for AI-Powered Test Case Generator.
Designed for integration with Streamlit frontend and external agents.
"""
import os
import subprocess
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(
    title="AI Test Generator API",
    description="Generate tests from feature descriptions, save to project, run pytest. Agent-friendly.",
    version="0.1.0",
)

# Default paths - configurable via env
PROJECT_ROOT = Path(os.getenv("PROJECT_ROOT", Path(__file__).parent.parent))
TESTS_DIR = PROJECT_ROOT / "generated_tests"
TESTS_DIR.mkdir(parents=True, exist_ok=True)


# --- Request/Response Models ---

class GenerateTestsRequest(BaseModel):
    feature_description: str = Field(..., description="Description of the feature to test")
    test_file_name: Optional[str] = Field(None, description="Output filename (default: test_generated.py)")
    language: str = Field("python", description="Target language/framework (python, pytest)")


class GenerateTestsResponse(BaseModel):
    success: bool
    test_content: str
    file_path: str
    message: str


class SaveTestsRequest(BaseModel):
    test_content: str = Field(..., description="Python test code to save")
    file_path: Optional[str] = Field(None, description="Relative path under generated_tests/")


class SaveTestsResponse(BaseModel):
    success: bool
    file_path: str
    message: str


class RunTestsRequest(BaseModel):
    test_path: Optional[str] = Field(None, description="Path to test file or directory (relative to project)")
    pytest_args: Optional[list[str]] = Field(default_factory=lambda: ["-v"], description="Extra pytest arguments")


class RunTestsResponse(BaseModel):
    success: bool
    passed: bool
    output: str
    exit_code: int
    summary: dict


# --- Services ---

def _call_llm_for_tests(description: str) -> str:
    """Generate test code using LLM. Replace with agent call when integrating."""
    import os
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a test engineer. Generate pytest test cases in Python. Return ONLY valid Python code, no markdown fences or explanations."
                },
                {
                    "role": "user",
                    "content": f"Generate pytest tests for this feature:\n\n{description}"
                }
            ],
            temperature=0.3,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        # Fallback: return a template when no API key or error
        return f'''"""
Auto-generated test template for: {description[:80]}...
Replace with actual test logic or configure OPENAI_API_KEY.
"""
import pytest


def test_feature_placeholder():
    """Placeholder - configure OPENAI_API_KEY for AI generation."""
    assert True
'''


@app.post("/api/generate-tests", response_model=GenerateTestsResponse)
async def generate_tests(req: GenerateTestsRequest):
    """Generate test cases from a feature description. Agent-callable."""
    try:
        content = _call_llm_for_tests(req.feature_description)
        filename = req.test_file_name or "test_generated.py"
        if not filename.endswith(".py"):
            filename += ".py"
        file_path = str(TESTS_DIR / filename)
        return GenerateTestsResponse(
            success=True,
            test_content=content,
            file_path=file_path,
            message="Tests generated successfully",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/save-tests", response_model=SaveTestsResponse)
async def save_tests(req: SaveTestsRequest):
    """Save test content to project. Agent-callable."""
    try:
        rel_path = req.file_path or "test_generated.py"
        if not rel_path.endswith(".py"):
            rel_path += ".py"
        full_path = TESTS_DIR / rel_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(req.test_content, encoding="utf-8")
        return SaveTestsResponse(
            success=True,
            file_path=str(full_path),
            message=f"Saved to {full_path}",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/run-tests", response_model=RunTestsResponse)
async def run_tests(req: RunTestsRequest):
    """Run pytest and return pass/fail. Agent-callable."""
    try:
        target = req.test_path or str(TESTS_DIR)
        if not os.path.isabs(target):
            target = str(PROJECT_ROOT / target)
        if not os.path.exists(target):
            raise HTTPException(status_code=404, detail=f"Path not found: {target}")
        args = ["pytest", target, *(req.pytest_args or ["-v"])]
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
            timeout=120,
        )
        output = result.stdout + result.stderr
        passed = result.returncode == 0
        return RunTestsResponse(
            success=True,
            passed=passed,
            output=output,
            exit_code=result.returncode,
            summary={
                "passed": passed,
                "exit_code": result.returncode,
            },
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="pytest timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/health")
async def health():
    """Health check for agents and load balancers."""
    return {"status": "ok", "service": "ai-test-generator"}


@app.get("/api/config")
async def get_config():
    """Expose config for agent discovery."""
    return {
        "project_root": str(PROJECT_ROOT),
        "tests_dir": str(TESTS_DIR),
        "endpoints": ["/api/generate-tests", "/api/save-tests", "/api/run-tests", "/api/health"],
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
