"""
backend_info.py — Returns display info for the active LLM backend.
Used by the Monitor page to show GPU vs CPU status.
"""
from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


BACKEND_META = {
    "ollama": {
        "label":    "Local Ollama",
        "icon":     "🖥️",
        "color":    "#6366f1",
        "badge":    "CPU/LOCAL",
        "desc":     "Running locally via Ollama — no GPU",
        "hardware": "cpu",
    },
    "vllm": {
        "label":    "AMD Instinct MI300X",
        "icon":     "⚡",
        "color":    "#ef4444",
        "badge":    "GPU · ROCm",
        "desc":     "AMD MI300X via vLLM — 192 GB VRAM",
        "hardware": "gpu",
    },
    "remote": {
        "label":    "AMD Instinct MI300X",
        "icon":     "⚡",
        "color":    "#ef4444",
        "badge":    "GPU · ROCm",
        "desc":     "AMD MI300X via vLLM — 192 GB VRAM",
        "hardware": "gpu",
    },
    "gcp_cpu": {
        "label":    "GCP VM (CPU)",
        "icon":     "☁️",
        "color":    "#4285f4",
        "badge":    "CPU · GCP",
        "desc":     "Google Cloud VM — CPU-based inference",
        "hardware": "cpu",
    },
}


def get_backend_info() -> dict:
    try:
        from config.settings import settings
        provider = settings.LLM_PROVIDER.strip().lower()
        meta = BACKEND_META.get(provider, {
            "label": provider, "icon": "🤖", "color": "#64748b",
            "badge": provider.upper(), "desc": "", "hardware": "unknown",
        })
        model = (
            settings.OLLAMA_MODEL        if provider == "ollama"  else
            settings.REMOTE_LLM_MODEL    if provider in ("vllm", "remote") else
            settings.GCP_VM_MODEL        if provider == "gcp_cpu" else
            "unknown"
        )
        endpoint = (
            settings.OLLAMA_HOST         if provider == "ollama"  else
            settings.REMOTE_LLM_BASE_URL if provider in ("vllm", "remote") else
            settings.GCP_VM_BASE_URL     if provider == "gcp_cpu" else
            ""
        )
        return {**meta, "provider": provider, "model": model, "endpoint": endpoint}
    except Exception as e:
        return {
            "label": "Unknown", "icon": "❓", "color": "#64748b",
            "badge": "UNKNOWN", "desc": str(e), "hardware": "unknown",
            "provider": "unknown", "model": "unknown", "endpoint": "",
        }
