# AI-Powered Test Case Generator

Feature description → AI generates tests → Save to project → Run pytest → Pass/Fail

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Start the backend

```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```
(From project root)

### 3. Start the frontend

```bash
streamlit run frontend/app.py
```

### 4. (Optional) Set OpenAI API key for AI generation

```bash
set OPENAI_API_KEY=your-key
```

Without it, a placeholder template is generated.

## Agent Integration

The FastAPI backend exposes REST endpoints for agent orchestration:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/generate-tests` | POST | Generate tests from feature description |
| `/api/save-tests` | POST | Save test content to project |
| `/api/run-tests` | POST | Run pytest, return pass/fail |
| `/api/health` | GET | Health check |
| `/api/config` | GET | Project paths and endpoint list |

Example agent flow:

```python
import requests
BASE = "http://localhost:8000"

# 1. Generate
r = requests.post(f"{BASE}/api/generate-tests", json={
    "feature_description": "add(a,b) returns sum"
})
tests = r.json()["test_content"]

# 2. Save
requests.post(f"{BASE}/api/save-tests", json={"test_content": tests})

# 3. Run
r = requests.post(f"{BASE}/api/run-tests", json={"test_path": "generated_tests"})
print(r.json()["passed"])
```
