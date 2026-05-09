"""gpu_monitor.py — Reads GPU metrics from rocm-smi (AMD) or nvidia-smi (NVIDIA).
Falls back to a CPU-mode display when LLM_PROVIDER=gcp_cpu or ollama."""
from __future__ import annotations
import json, subprocess, sys
from dataclasses import dataclass, field
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


@dataclass
class GPUInfo:
    index: int
    name: str
    utilization_pct: float
    memory_used_mb: float
    memory_total_mb: float
    temperature_c: float
    power_w: float
    backend: str   # "rocm" | "nvidia" | "cpu" | "mock"
    raw: dict = field(default_factory=dict)

    @property
    def memory_pct(self) -> float:
        if self.memory_total_mb <= 0:
            return 0.0
        return round(self.memory_used_mb / self.memory_total_mb * 100, 1)


def _try_rocm() -> list[GPUInfo] | None:
    try:
        r = subprocess.run(["rocm-smi", "--json"], capture_output=True, text=True, timeout=5)
        if r.returncode != 0:
            return None
        data = json.loads(r.stdout)
        gpus: list[GPUInfo] = []
        for idx, (key, d) in enumerate(data.items()):
            if not isinstance(d, dict):
                continue
            util     = float(d.get("GPU use (%)", d.get("GPU_USE_PERC", 0)) or 0)
            mem_used = float(d.get("VRAM Total Used Memory (B)", 0)) / 1024 / 1024
            mem_tot  = float(d.get("VRAM Total Memory (B)", 0)) / 1024 / 1024
            temp     = float(d.get("Temperature (Sensor edge) (C)", d.get("temp_edge", 0)) or 0)
            power    = float(d.get("Average Graphics Package Power (W)", 0) or 0)
            name     = d.get("Card Series", d.get("Card model", key))
            gpus.append(GPUInfo(idx, str(name), util, mem_used, mem_tot, temp, power, "rocm", d))
        return gpus or None
    except Exception:
        return None


def _try_nvidia() -> list[GPUInfo] | None:
    try:
        r = subprocess.run(
            ["nvidia-smi", "--query-gpu=index,name,utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5)
        if r.returncode != 0:
            return None
        gpus: list[GPUInfo] = []
        for line in r.stdout.strip().splitlines():
            p = [x.strip() for x in line.split(",")]
            if len(p) < 7:
                continue
            idx, name, util, mu, mt, temp, power = p[:7]
            gpus.append(GPUInfo(int(idx), name,
                float(util) if util != "[N/A]" else 0,
                float(mu)   if mu   != "[N/A]" else 0,
                float(mt)   if mt   != "[N/A]" else 0,
                float(temp) if temp != "[N/A]" else 0,
                float(power) if power not in ("[N/A]","N/A") else 0,
                "nvidia"))
        return gpus or None
    except Exception:
        return None


def _cpu_mode() -> list[GPUInfo]:
    """Return a CPU-mode 'GPU' entry for gcp_cpu / ollama backends."""
    import psutil
    try:
        cpu_pct  = psutil.cpu_percent(interval=0.2)
        mem      = psutil.virtual_memory()
        mem_used = mem.used / 1024 / 1024
        mem_tot  = mem.total / 1024 / 1024
        return [GPUInfo(0, "CPU (no GPU — gcp_cpu/ollama mode)", cpu_pct,
                        mem_used, mem_tot, 0.0, 0.0, "cpu")]
    except Exception:
        return _mock_gpu()


def _mock_gpu() -> list[GPUInfo]:
    import math, time
    t = time.time()
    util = round(abs(math.sin(t / 10)) * 65 + 10, 1)
    mu   = round(abs(math.sin(t / 13 + 1)) * 80_000 + 20_000, 0)
    return [GPUInfo(0, "AMD Instinct MI300X (mock)", util, mu, 192_000.0,
                    round(45 + abs(math.sin(t / 20)) * 20, 1),
                    round(abs(math.sin(t / 8)) * 400 + 200, 1), "mock")]


def get_gpu_info() -> list[GPUInfo]:
    """Auto-detect: ROCm → NVIDIA → CPU (psutil) → mock."""
    # Prefer real GPU detection
    gpus = _try_rocm()
    if gpus:
        return gpus
    gpus = _try_nvidia()
    if gpus:
        return gpus
    # Check if we're running in CPU mode
    try:
        from config.settings import settings
        if settings.LLM_PROVIDER in ("gcp_cpu", "ollama"):
            return _cpu_mode()
    except Exception:
        pass
    return _mock_gpu()
