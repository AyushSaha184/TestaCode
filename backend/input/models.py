from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from backend.schemas import TargetLanguage, InputMode


class ExtractedFunction(BaseModel):
    """Metadata for a single function extracted during code parsing."""
    name: str
    args: List[str] = Field(default_factory=list)
    type_annotations: Dict[str, str] = Field(default_factory=dict)  # param_name -> type_str
    docstring: Optional[str] = None
    returns: Optional[str] = None
    decorators: List[str] = Field(default_factory=list)
    external_deps: List[str] = Field(default_factory=list)


class ClassifiedIntent(BaseModel):
    """Output of the Prompt Intent Classifier."""
    test_type: str = "unit"  # unit, integration, edge_case, mixed
    target_scope: str = "all"  # all, specific, area
    target_functions: List[str] = Field(default_factory=list)  # when scope=specific
    target_framework: str = "auto"  # pytest, unittest, jest, mocha, auto
    special_requirements: List[str] = Field(default_factory=list)
    confidence: float = 0.5


class UnifiedContext(BaseModel):
    """
    The single structured object passed to the LangChain agent.
    Assembled from the code parser output + prompt intent classifier output.
    The agent layer never touches raw user input directly.
    """
    raw_code: str
    language: TargetLanguage
    input_mode: InputMode
    filename: Optional[str] = None
    extracted_functions: List[ExtractedFunction] = Field(default_factory=list)
    classified_intent: ClassifiedIntent = Field(default_factory=ClassifiedIntent)
    user_prompt: str = ""  # kept for display purposes
    warnings: List[str] = Field(default_factory=list)


# ─── Legacy compatibility alias ──────────────────────────────────────────────
# Some existing code may still reference UnifiedInput
UnifiedInput = UnifiedContext
