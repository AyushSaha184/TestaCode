from __future__ import annotations

import os
import subprocess
import tempfile

from backend.schemas import Language


def validate_generated_code(language: Language, generated_code: str) -> tuple[bool, str | None]:
	if language == Language.python:
		try:
			compile(generated_code, "<generated_tests>", "exec")
			return True, None
		except SyntaxError as exc:
			return False, str(exc)

	if language in (Language.javascript, Language.typescript):
		return _validate_with_node(language, generated_code)

	# Java syntax validation is intentionally deferred in this phase.
	return True, None


def _validate_with_node(language: Language, generated_code: str) -> tuple[bool, str | None]:
	suffix = ".js" if language == Language.javascript else ".ts"
	tmp_path = ""
	try:
		with tempfile.NamedTemporaryFile(mode="w", suffix=suffix, delete=False, encoding="utf-8") as handle:
			handle.write(generated_code)
			tmp_path = handle.name

		result = subprocess.run(
			["node", "--check", tmp_path],
			capture_output=True,
			text=True,
			timeout=8,
			check=False,
		)
		if result.returncode == 0:
			return True, None
		return False, (result.stderr or result.stdout).strip()
	except FileNotFoundError:
		return False, "Node.js runtime not found for JS/TS validation"
	except Exception as exc:
		return False, str(exc)
	finally:
		if tmp_path and os.path.exists(tmp_path):
			os.remove(tmp_path)
