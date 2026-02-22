from pydantic import BaseModel, Field
from typing import List, Optional
from backend.schemas import TargetLanguage, InputMode

class ExtractedFunction(BaseModel):
    name: str
    args: List[str]
    docstring: Optional[str] = None
    returns: Optional[str] = None

class UnifiedInput(BaseModel):
    raw_content: str
    mode: InputMode
    language: TargetLanguage
    extracted_functions: List[ExtractedFunction] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
