import os
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from backend.agents.prompts import (
    NL_ANALYSIS_PROMPT,
    CODE_ANALYSIS_PROMPT,
    TEST_GENERATION_PROMPT,
    CLARIFICATION_PROMPT
)

# Shared LLM instance (Using a placeholder for OpenAI model, relies on OPENAI_API_KEY env variable)
def get_llm(temperature=0.2):
    return ChatOpenAI(
        model="gpt-4o-mini",  # Fast, cheap, capable reasoning model 
        temperature=temperature
    )
    
def run_requirement_analysis(feature_desc: str) -> str:
    """Takes vague/natural language intent and outputs a structured requirement analysis"""
    llm = get_llm()
    chain = NL_ANALYSIS_PROMPT | llm
    result = chain.invoke({"feature_description": feature_desc})
    return result.content

def run_code_analysis(raw_code: str, language: str) -> str:
    """Produces function-by-function analysis of code."""
    llm = get_llm()
    chain = CODE_ANALYSIS_PROMPT | llm
    result = chain.invoke({"raw_code": raw_code, "language": language})
    return result.content

def run_test_generation(
    analysis: str, 
    code_context: str, 
    language: str, 
    framework: str, 
    mock: bool, 
    edge: bool
) -> str:
    """The final chain that emits raw generated code."""
    llm = get_llm(temperature=0.1) # low temp for code generation exactly
    chain = TEST_GENERATION_PROMPT | llm
    result = chain.invoke({
        "framework": framework,
        "analysis": analysis,
        "code_context_section": code_context,
        "include_edge_cases": str(edge),
        "mock_external_dependencies": str(mock),
        "language": language
    })
    
    # Strip markdown blocks if the LLM adds them
    raw = result.content.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        if len(lines) >= 2 and lines[-1].strip() == "```":
            return "\n".join(lines[1:-1])
    return raw

def run_clarification_agent(feature_desc: str) -> str:
    """Generates two targeted clarification questions back to the user."""
    llm = get_llm(temperature=0.4) # Slightly creative for questions
    chain = CLARIFICATION_PROMPT | llm
    result = chain.invoke({"feature_description": feature_desc})
    return result.content
