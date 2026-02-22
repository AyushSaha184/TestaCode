from backend.core.config import logger
from backend.input.models import UnifiedInput
from backend.schemas import GenerationOptions, InputMode
from backend.agents.chains import (
    run_requirement_analysis, 
    run_code_analysis, 
    run_test_generation, 
    run_clarification_agent
)
from backend.agents.tools import check_syntax, write_test_file

def sanitize_and_fix_code(agent_output: str, language: str, retries_left: int = 2) -> dict:
    """
    Validates AST Syntax. If broken, loops it back up to 2 times for fixing.
    """
    is_valid, error_msg = check_syntax(agent_output, language)
    
    if is_valid:
        return {"success": True, "code": agent_output}
        
    if retries_left <= 0:
        logger.error(f"Auto-correction failed after max retries. Syntax Error: {error_msg}")
        return {"success": False, "code": agent_output, "error": error_msg}
        
    logger.warning(f"Syntax Error caught. Sending to LLM Self-Correction loop. {retries_left} retries left.")
    
    # Simple self-healing prompt wrapper
    from backend.agents.chains import get_llm
    from langchain.prompts import PromptTemplate
    
    fix_prompt = PromptTemplate(
        template="""You are an expert developer. The following code failed syntax validation:
```
{code}
```
Error: {error}
        
Please output ONLY the corrected code without markdown ticks. Maintain all intended testing logic.""",
        input_variables=["code", "error"]
    )
    
    llm = get_llm()
    chain = fix_prompt | llm
    fixed_response = chain.invoke({"code": agent_output, "error": error_msg})
    
    # Recurse
    return sanitize_and_fix_code(fixed_response.content, language, retries_left - 1)


def process_generation_flow(unified_input: UnifiedInput, options: GenerationOptions) -> dict:
    """
    Main Orchestrator tying Phase 2 input to Phase 3 generation loops.
    """
    # 1. Handle Vague inputs (NL Check)
    if unified_input.mode == InputMode.natural_language and any("Vague" in w for w in unified_input.warnings):
        questions = run_clarification_agent(unified_input.raw_content)
        return {
            "status": "clarification_needed", 
            "message": questions,
            "code": ""
        }
        
    # 2. Stage-1 Analysis
    logger.info("Executing Agent Stage 1: Analysis")
    if unified_input.mode == InputMode.natural_language:
        analysis_context = run_requirement_analysis(unified_input.raw_content)
        code_context = ""
    else:
        analysis_context = run_code_analysis(unified_input.raw_content, unified_input.language.value)
        code_context = f"\nOriginal Code Context:\n{unified_input.raw_content}\n"
        
    # 3. Stage-2 Test Generation
    logger.info("Executing Agent Stage 2: Code Generation")
    raw_tests = run_test_generation(
        analysis=analysis_context,
        code_context=code_context,
        language=unified_input.language.value,
        framework=options.framework,
        mock=options.mock_external_dependencies,
        edge=options.include_edge_cases
    )
    
    # 4. Stage-3 Validation & Auto-Correction
    logger.info("Executing Agent Stage 3: Auto-Correction & Syntax Verification")
    validation_result = sanitize_and_fix_code(raw_tests, unified_input.language.value)
    
    if not validation_result["success"]:
        return {
            "status": "failed",
            "message": f"Agent failed to produce valid syntax. Original Error: {validation_result['error']}",
            "code": validation_result["code"]
        }
        
    return {
        "status": "success",
        "message": "Tests successfully generated and passed syntax validation.",
        "code": validation_result["code"]
    }
