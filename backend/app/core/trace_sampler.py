"""Trace sampling for high-volume endpoints."""

import random


class TraceSampler:
    def __init__(self, default_rate: float = 1.0):
        self._rates: dict[str, float] = {}
        self._default = default_rate

    def set_rate(self, path: str, rate: float):
        self._rates[path] = max(0.0, min(1.0, rate))

    def should_sample(self, path: str) -> bool:
        rate = self._rates.get(path, self._default)
        return random.random() < rate


trace_sampler = TraceSampler(default_rate=1.0)
# Health checks: sample 1% only
trace_sampler.set_rate("/health", 0.01)
trace_sampler.set_rate("/health/live", 0.01)
trace_sampler.set_rate("/health/ready", 0.01)
trace_sampler.set_rate("/metrics", 0.01)
