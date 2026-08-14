"""
Executes a generated k6 script as a real subprocess (if the k6 binary is
available on the host) and samples ACTUAL system telemetry (CPU, memory,
disk I/O, network I/O) with psutil while the test runs.

This replaces the old `np.random`-based dummy telemetry generator.
If k6 is not installed, or the user only has a results file from a run
on a different machine, we fall back to a clearly-labelled *estimated*
telemetry curve that is derived from the real k6 metrics (throughput,
error rate, latency) rather than pure noise -- see
dashboard/telemetry.py::estimate_telemetry_from_metrics.
"""

import shutil
import subprocess
import threading
import time

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


def k6_binary_available() -> bool:
    return shutil.which("k6") is not None


class SystemTelemetrySampler:
    """Samples real host telemetry once per second on a background thread."""

    def __init__(self, interval_seconds: float = 1.0):
        self.interval = interval_seconds
        self._stop_event = threading.Event()
        self._thread = None
        self.samples = {
            "timestamps": [],
            "cpu": [],
            "memory": [],
            "storage_read": [],
            "storage_write": [],
            "network": [],
        }

    def _sample_loop(self):
        if not PSUTIL_AVAILABLE:
            return

        t = 0
        prev_disk = psutil.disk_io_counters()
        prev_net = psutil.net_io_counters()
        prev_time = time.time()

        while not self._stop_event.is_set():
            time.sleep(self.interval)

            now = time.time()
            elapsed = max(now - prev_time, 1e-6)

            cpu = psutil.cpu_percent(interval=None)
            mem = psutil.virtual_memory().percent

            disk = psutil.disk_io_counters()
            read_mb_s = (disk.read_bytes - prev_disk.read_bytes) / elapsed / (1024 ** 2)
            write_mb_s = (disk.write_bytes - prev_disk.write_bytes) / elapsed / (1024 ** 2)

            net = psutil.net_io_counters()
            net_mbps = (
                (net.bytes_sent - prev_net.bytes_sent + net.bytes_recv - prev_net.bytes_recv)
                * 8 / elapsed / (1024 ** 2)
            )

            self.samples["timestamps"].append(t)
            self.samples["cpu"].append(round(cpu, 2))
            self.samples["memory"].append(round(mem, 2))
            self.samples["storage_read"].append(round(max(read_mb_s, 0), 2))
            self.samples["storage_write"].append(round(max(write_mb_s, 0), 2))
            self.samples["network"].append(round(max(net_mbps, 0), 2))

            prev_disk, prev_net, prev_time = disk, net, now
            t += 1

    def start(self):
        if not PSUTIL_AVAILABLE:
            return
        self._thread = threading.Thread(target=self._sample_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
        return self.samples


def run_k6_script(script_path: str, extra_args=None, timeout_seconds: int = 900):
    """
    Runs `k6 run <script_path>` as a subprocess, sampling real system
    telemetry concurrently. Returns (stdout_text, telemetry_dict, error).
    """
    if not k6_binary_available():
        return None, None, (
            "k6 binary was not found on this machine (PATH lookup failed). "
            "Install k6 (https://k6.io/docs/get-started/installation/) to run "
            "tests directly from the app, or upload a k6 results file instead."
        )

    sampler = SystemTelemetrySampler(interval_seconds=1.0)
    sampler.start()

    cmd = ["k6", "run", script_path] + (extra_args or [])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        stdout_text = result.stdout + "\n" + result.stderr
        error = None
    except subprocess.TimeoutExpired:
        stdout_text = None
        error = f"k6 run timed out after {timeout_seconds} seconds."
    except Exception as e:
        stdout_text = None
        error = f"Failed to execute k6: {e}"
    finally:
        telemetry = sampler.stop()

    return stdout_text, telemetry, error
