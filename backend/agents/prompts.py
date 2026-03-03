from langchain_core.prompts import PromptTemplate

# 1. Natural Language Requirement Analysis Prompt
# Goal: Infer implementation details from a potentially vague description.
NL_ANALYSIS_PROMPT = PromptTemplate(
    template="""You are a senior software architect. 
A user has provided the following feature description:
---
{feature_description}
---

Your task is to analyze this feature and output a highly detailed implementation specification.
Consider:
1. What the core happy path is.
2. What edge cases and boundary conditions exist.
3. What exceptions or errors should be handled.
4. What external dependencies (like databases or APIs) might be implied.
5. If the description is too vague to determine tests, point out the exact ambiguities.

Generate a structured analysis.
""",
    input_variables=["feature_description"]
)

# 2. Code Analysis Prompt (For pasted code or file uploads)
# Goal: Build a map of what the code does before writing tests.
CODE_ANALYSIS_PROMPT = PromptTemplate(
    template="""You are an expert code reviewer analyzing an implementation in {language}.
Please read the following code carefully:
---
{raw_code}
---

Provide a structured, function-by-function analysis:
For each function or method:
1. What is its primary purpose?
2. What are the inputs and expected outputs?
3. What exceptions can it raise?
4. What external dependencies does it rely on (modules, APIs, classes to mock)?

Output only the analysis, formatted clearly.
""",
    input_variables=["raw_code", "language"]
)

# 3. Test Generation Prompt
# Goal: Using the analysis, generate the final test file.
TEST_GENERATION_PROMPT = PromptTemplate(
    template="""You are an elite QA Engineer writing a test suite using {framework}.
You have the following analysis of the feature/code to be tested:
---
{analysis}
---
{code_context_section}

Options requested by user:
- Include Edge Cases: {include_edge_cases}
- Mock External Dependencies: {mock_external_dependencies}

Write a complete, executable test file in {language}.
- Include all necessary imports (e.g., `import pytest`, `from unittest.mock import patch`).
- Write clear, descriptive test function names.
- Provide a file header docstring explaining what is being tested.
- Do NOT wrap your output in markdown code blocks like ```python. ONLY output the raw code.

Generated Test Code:
""",
    input_variables=["framework", "analysis", "code_context_section", "include_edge_cases", "mock_external_dependencies", "language"]
)

# 4. Clarification Sub-Agent Prompt
# Goal: Formulate up to two targeted questions to ask the user if the feature input was vague.
CLARIFICATION_PROMPT = PromptTemplate(
    template="""You are a technical product manager. 
A user wants to write tests for a feature described as:
"{feature_description}"

We flagged this description as too vague to write proper tests.
Generate exactly TWO concise, targeted clarifying questions that would help you understand the edge cases, dependencies, or missing logic.
Output the questions as a simple numbered list.
""",
    input_variables=["feature_description"]
)
