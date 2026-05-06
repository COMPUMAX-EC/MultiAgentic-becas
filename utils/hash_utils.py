from __future__ import annotations

import hashlib
import json


def stable_hash(value: object) -> str:
    serialized_value = json.dumps(value, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(serialized_value.encode("utf-8")).hexdigest()


def scholarship_hash(name: str, source_url: str) -> str:
    return stable_hash({"scholarship_name": name.strip(), "source_url": source_url.strip()})


def profile_hash(profile: dict) -> str:
    return stable_hash(profile)
