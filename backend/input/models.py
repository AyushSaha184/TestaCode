from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from backend.schemas import Language


class RawGenerationInput(BaseModel):
	model_config = ConfigDict(extra="forbid", strict=True)

	input_mode: str
	code_content: str | None = None
	filename: str | None = None
	language: str | None = None
	user_prompt: str


class NormalizedInput(BaseModel):
	model_config = ConfigDict(extra="forbid", strict=True)

	code_content: str
	filename: str | None
	language: Language
