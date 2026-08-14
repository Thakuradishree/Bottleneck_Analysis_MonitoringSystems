"""
Two telemetry sources:

1. REAL: captured live by utils.k6_runner.SystemTelemetrySampler while k6
   actually runs on this machine (psutil). Used when the user clicks
   "Run k6 Test" inside the app.

2. ESTIMATED: when the user only uploads a k6 results file (test ran
   elsewhere, or on a machine this app has no access to), we cannot
   know real infra numbers. Instead of random noise, we derive a
   plausible curve *from the real k6 metrics themselves* (throughput,
   VUs, latency, error rate) so the shape tracks the actual load
   profile of the test. This is clearly labelled "Estimated" in the UI
   and should be replaced by wiring in a real APM/Prometheus source
   for production use.
"""

import numpy as np


def estimate_telemetry_from_metrics(metrics: dict, duration_seconds: int = 60):
    """
    Build a telemetry curve whose shape is driven by real k6 output
    (vus_max, throughput, p95 latency, error_rate) rather than pure
    randomness. Still an estimate -- always render with source_badge(False).
    """

    n = max(duration_seconds, 10)
    timestamps = list(range(n))

    vus_max = max(metrics.get("vus_max", 0), 1)
    throughput = max(metrics.get("throughput", 0), 0.1)
    p95 = metrics.get("p95_response_time", 0)
    error_rate = metrics.get("error_rate", 0)

    # Ramp-up / plateau / ramp-down load shape (typical k6 stage pattern)
    ramp = np.piecewise(
        np.linspace(0, 1, n),
        [
            np.linspace(0, 1, n) < 0.2,
            (np.linspace(0, 1, n) >= 0.2) & (np.linspace(0, 1, n) < 0.8),
            np.linspace(0, 1, n) >= 0.8,
        ],
        [
            lambda x: x / 0.2,
            lambda x: 1.0,
            lambda x: np.clip(1 - (x - 0.8) / 0.2, 0, 1),
        ],
    )

    noise = np.random.normal(0, 0.03, n)
    load_curve = np.clip(ramp + noise, 0, 1)

    # CPU scales with concurrent VUs and throughput; error rate & high
    # latency push CPU/memory pressure higher (saturation signature).
    saturation_bonus = min(error_rate, 40) * 0.6 + min(p95 / 50, 20)
    cpu = 15 + load_curve * (55 + saturation_bonus)
    cpu = np.clip(cpu, 5, 98)

    memory = 30 + load_curve * (40 + min(error_rate, 30) * 0.4)
    memory = np.clip(memory, 15, 95)

    storage_read = 10 + load_curve * throughput * 0.15
    storage_write = 5 + load_curve * throughput * 0.10

    network = 5 + load_curve * throughput * 0.35

    return {
        "timestamps": timestamps,
        "cpu": cpu.tolist(),
        "memory": memory.tolist(),
        "storage_read": storage_read.tolist(),
        "storage_write": storage_write.tolist(),
        "network": network.tolist(),
        "source": "estimated",
    }


def normalize_real_telemetry(samples: dict):
    """Tag telemetry captured by SystemTelemetrySampler as real/live."""
    samples = dict(samples)
    samples["source"] = "live"
    return samples
