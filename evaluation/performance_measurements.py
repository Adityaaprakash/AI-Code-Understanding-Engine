import contextlib
import os
import platform
import time
from typing import Any

import numpy as np
import psutil


class TimingContext:
    def __init__(self, warmup_count: int = 0):
        self.durations: list[float] = []
        self.warmup_count = warmup_count

    def add(self, duration: float):
        self.durations.append(duration)

    @property
    def sample_count(self) -> int:
        return len(self.durations)

    def mean(self) -> float:
        return float(np.mean(self.durations)) if self.durations else 0.0

    def p50(self) -> float:
        return float(np.percentile(self.durations, 50)) if self.durations else 0.0

    def p95(self) -> float:
        return float(np.percentile(self.durations, 95)) if self.durations else 0.0


@contextlib.contextmanager
def measure_time(timer: TimingContext):
    start = time.perf_counter()
    try:
        yield
    finally:
        end = time.perf_counter()
        timer.add(end - start)


def get_current_rss_bytes() -> int:
    process = psutil.Process(os.getpid())
    return process.memory_info().rss


def collect_environment_metadata() -> dict[str, Any]:
    env = {
        "os": platform.system(),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "cpu": platform.processor(),
        "logical_cpus": psutil.cpu_count(logical=True) or 0,
        "physical_cpus": psutil.cpu_count(logical=False) or 0,
        "ram_bytes": psutil.virtual_memory().total,
        "embedding_provider": "LocalSentenceTransformerProvider",
        "embedding_model": "all-MiniLM-L6-v2",
        "embedding_dimensions": 384,
        "device": "cpu",
    }
    return env
