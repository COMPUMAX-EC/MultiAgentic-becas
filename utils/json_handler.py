from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class JsonHandlerError(ValueError):
    pass


def ensure_parent_dir(file_path: Path) -> None:
    file_path.parent.mkdir(parents=True, exist_ok=True)


def load_json(file_path: str | Path) -> Any:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(path)

    try:
        with path.open("r", encoding="utf-8") as json_file:
            return json.load(json_file)
    except json.JSONDecodeError as exc:
        raise JsonHandlerError(f"Invalid JSON in '{path}': {exc.msg}") from exc


def save_json(file_path: str | Path, payload: Any) -> None:
    path = Path(file_path)
    ensure_parent_dir(path)
    with path.open("w", encoding="utf-8") as json_file:
        json.dump(payload, json_file, indent=2, ensure_ascii=False)


def parse_json_text(raw_text: str) -> Any:
    cleaned_text = raw_text.strip()
    if cleaned_text.startswith("```"):
        cleaned_text = cleaned_text.strip("`").strip()
        if cleaned_text.lower().startswith("json"):
            cleaned_text = cleaned_text[4:].strip()

    try:
        return json.loads(cleaned_text)
    except json.JSONDecodeError:
        start_index = cleaned_text.find("{")
        end_index = cleaned_text.rfind("}")
        if start_index == -1 or end_index == -1 or end_index <= start_index:
            raise JsonHandlerError("LLM response did not contain valid JSON.")

        try:
            return json.loads(cleaned_text[start_index : end_index + 1])
        except json.JSONDecodeError as exc:
            raise JsonHandlerError(f"Invalid JSON from LLM response: {exc.msg}") from exc
