"""
Streamlit Frontend for AI-Powered Test Case Generator.
Connects to FastAPI backend - also usable by external agents.
"""

import requests
import streamlit as st

# Backend URL - configurable for agent integration
BACKEND_URL = "http://localhost:8000"

st.set_page_config(
    page_title="AI Test Generator",
    page_icon="🧪",
    layout="wide",
)

st.title("🧪 AI-Powered Test Case Generator")
st.caption("Describe a feature → AI generates tests → Save → Run pytest → Pass/Fail")

# Sidebar: Backend config for agent integration
with st.sidebar:
    st.subheader("⚙️ Configuration")
    backend_url = st.text_input(
        "Backend URL",
        value=BACKEND_URL,
        help="FastAPI backend URL. Change when connecting to agent.",
    )
    st.divider()
    st.markdown("**Agent Integration**")
    st.markdown(
        """
Backend exposes REST API:
- `POST /api/generate-tests`
- `POST /api/save-tests`
- `POST /api/run-tests`
- `GET /api/health`
"""
    )

# Main content
feature_desc = st.text_area(
    "Feature description",
    placeholder="e.g., A function add(a, b) that returns the sum of two numbers. Handle None by returning 0.",
    height=120,
)

col1, col2, col3 = st.columns(3)

with col1:
    generate_btn = st.button("🔄 Generate tests", type="primary", use_container_width=True)

with col2:
    save_btn = st.button("💾 Save to project", use_container_width=True)

with col3:
    run_btn = st.button("▶️ Run pytest", use_container_width=True)

# Initialize session state
if "generated_tests" not in st.session_state:
    st.session_state.generated_tests = None
if "test_file_path" not in st.session_state:
    st.session_state.test_file_path = None

# Generate tests
if generate_btn:
    if not feature_desc.strip():
        st.error("Enter a feature description first.")
    else:
        with st.spinner("Generating tests..."):
            try:
                r = requests.post(
                    f"{backend_url}/api/generate-tests",
                    json={"feature_description": feature_desc},
                    timeout=60,
                )
                r.raise_for_status()
                data = r.json()
                st.session_state.generated_tests = data["test_content"]
                st.session_state.test_file_path = data["file_path"]
                st.success("Tests generated!")
            except requests.exceptions.ConnectionError:
                st.error(
                    f"Could not connect to backend at {backend_url}. Is the FastAPI server running?"
                )
            except requests.exceptions.HTTPError as e:
                st.error(
                    f"Backend error: {e.response.status_code} - {e.response.text[:200]}"
                )
            except Exception as e:
                st.error(f"Error: {e}")

# Display generated tests
if st.session_state.generated_tests:
    st.subheader("Generated tests")
    st.code(st.session_state.generated_tests, language="python")

# Save tests
if save_btn:
    content = st.session_state.generated_tests
    if not content:
        st.error("Generate tests first.")
    else:
        with st.spinner("Saving..."):
            try:
                r = requests.post(
                    f"{backend_url}/api/save-tests",
                    json={"test_content": content},
                    timeout=10,
                )
                r.raise_for_status()
                data = r.json()
                st.session_state.test_file_path = data["file_path"]
                st.success(f"Saved to `{data['file_path']}`")
            except requests.exceptions.ConnectionError:
                st.error(f"Could not connect to backend at {backend_url}.")
            except Exception as e:
                st.error(f"Error: {e}")

# Run pytest
if run_btn:
    with st.spinner("Running pytest..."):
        try:
            payload = {"test_path": "generated_tests"}
            r = requests.post(
                f"{backend_url}/api/run-tests",
                json=payload,
                timeout=120,
            )
            r.raise_for_status()
            data = r.json()
            passed = data["passed"]
            output = data["output"]
            if passed:
                st.success("✅ All tests passed!")
            else:
                st.error("❌ Some tests failed")
            st.subheader("pytest output")
            st.code(output, language="text")
        except requests.exceptions.ConnectionError:
            st.error(f"Could not connect to backend at {backend_url}.")
        except Exception as e:
            st.error(f"Error: {e}")

# Footer
st.divider()
st.caption("Backend: FastAPI | Frontend: Streamlit | Agent-ready REST API")

