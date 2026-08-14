import re


def extract_number(pattern, text, default=0.0):
    """
    Extract first matching numeric value.
    """
    match = re.search(pattern, text, re.IGNORECASE)

    if match:
        try:
            return float(match.group(1))
        except (ValueError, TypeError):
            return default

    return default


def _to_ms(value_str, unit):
    """
    k6 auto-scales duration units based on magnitude: a fast response
    prints e.g. 'avg=245.32ms', but anything over ~1s prints 'avg=1.52s'
    instead (and very fast ones can print 'min=820\u00b5s'). The old regex
    only accepted a literal 'ms' suffix, so any value that crossed 1
    second failed to match and the WHOLE duration line silently fell
    back to 0.0 for every metric. Convert whatever unit k6 used to ms.
    """
    value = float(value_str)
    unit = unit.lower()

    if unit in ("s", "sec", "secs"):
        return value * 1000.0
    if unit in ("\u00b5s", "us", "\u03bcs"):
        return value / 1000.0
    if unit == "m":  # minutes, seen for very slow outliers
        return value * 60_000.0

    return value  # already ms


def parse_k6_output(text):

    metrics = {
        "mean_response_time": 0.0,
        "median_response_time": 0.0,
        "p90_response_time": 0.0,
        "p95_response_time": 0.0,

        "throughput": 0.0,

        "availability": 0.0,
        "error_rate": 0.0,

        "total_requests": 0,
        "successful_requests": 0,
        "failed_requests": 0,

        "latency_consistency": 0.0,

        "min_response_time": 0.0,
        "max_response_time": 0.0,

        "iterations": 0,
        "vus_max": 0,

        "data_received": 0.0,
        "data_sent": 0.0
    }

    # ==========================================================
    # HTTP REQUEST DURATION
    #
    # Each field's unit (ms / s / \u00b5s) is captured independently
    # instead of assumed, since k6 chooses the unit per-value.
    # ==========================================================

    UNIT = r"(ms|s|\u00b5s|us|m)"

    duration_pattern = (
        r"http_req_duration.*?"
        rf"avg=([\d.]+){UNIT}.*?"
        rf"min=([\d.]+){UNIT}.*?"
        rf"med=([\d.]+){UNIT}.*?"
        rf"max=([\d.]+){UNIT}.*?"
        rf"p\(90\)=([\d.]+){UNIT}.*?"
        rf"p\(95\)=([\d.]+){UNIT}"
    )

    duration_match = re.search(
        duration_pattern,
        text,
        re.IGNORECASE | re.DOTALL
    )

    if duration_match:

        g = duration_match.groups()

        metrics["mean_response_time"] = _to_ms(g[0], g[1])
        metrics["min_response_time"] = _to_ms(g[2], g[3])
        metrics["median_response_time"] = _to_ms(g[4], g[5])
        metrics["max_response_time"] = _to_ms(g[6], g[7])
        metrics["p90_response_time"] = _to_ms(g[8], g[9])
        metrics["p95_response_time"] = _to_ms(g[10], g[11])

    # ==========================================================
    # HTTP REQUESTS / THROUGHPUT
    # ==========================================================

    requests_match = re.search(
        r"http_reqs.*?:\s*([\d.]+)\s+([\d.]+)\/s",
        text,
        re.IGNORECASE
    )

    if requests_match:

        metrics["total_requests"] = int(
            float(requests_match.group(1))
        )

        metrics["throughput"] = float(
            requests_match.group(2)
        )

    # ==========================================================
    # HTTP FAILED
    # ==========================================================

    failed_match = re.search(
        r"http_req_failed.*?:\s*([\d.]+)%",
        text,
        re.IGNORECASE
    )

    if failed_match:

        metrics["error_rate"] = float(
            failed_match.group(1)
        )

        metrics["availability"] = (
            100.0 - metrics["error_rate"]
        )

    # ==========================================================
    # CHECKS
    # ==========================================================

    checks_match = re.search(
        r"checks_succeeded.*?:\s*([\d.]+)%\s+([\d]+)\s+out of\s+([\d]+)",
        text,
        re.IGNORECASE
    )

    if checks_match:

        successful_checks = int(
            checks_match.group(2)
        )

        total_checks = int(
            checks_match.group(3)
        )

        failed_checks = (
            total_checks - successful_checks
        )

        metrics["successful_requests"] = successful_checks
        metrics["failed_requests"] = failed_checks

    elif metrics["total_requests"] > 0:

        # Fall back to http_req_failed % when checks_succeeded is
        # absent from the output (e.g. script has no check() calls).
        failed = round(
            metrics["total_requests"] * metrics["error_rate"] / 100
        )

        metrics["failed_requests"] = int(failed)
        metrics["successful_requests"] = (
            metrics["total_requests"] - int(failed)
        )

    # ==========================================================
    # ITERATIONS
    # ==========================================================

    iteration_match = re.search(
        r"iterations.*?:\s*([\d]+)\s+([\d.]+)\/s",
        text,
        re.IGNORECASE
    )

    if iteration_match:

        metrics["iterations"] = int(
            iteration_match.group(1)
        )

    # ==========================================================
    # VUS
    # ==========================================================

    vus_match = re.search(
        r"vus_max.*?:\s*([\d]+)",
        text,
        re.IGNORECASE
    )

    if vus_match:

        metrics["vus_max"] = int(
            vus_match.group(1)
        )

    # ==========================================================
    # NETWORK
    # ==========================================================

    received_match = re.search(
        r"data_received.*?:\s*([\d.]+)\s*(KB|MB|GB)",
        text,
        re.IGNORECASE
    )

    if received_match:

        value = float(received_match.group(1))
        unit = received_match.group(2).upper()

        if unit == "GB":
            value *= 1024

        elif unit == "KB":
            value /= 1024

        metrics["data_received"] = value

    sent_match = re.search(
        r"data_sent.*?:\s*([\d.]+)\s*(KB|MB|GB)",
        text,
        re.IGNORECASE
    )

    if sent_match:

        value = float(sent_match.group(1))
        unit = sent_match.group(2).upper()

        if unit == "GB":
            value *= 1024

        elif unit == "KB":
            value /= 1024

        metrics["data_sent"] = value

    # ==========================================================
    # LATENCY CONSISTENCY
    # ==========================================================

    if metrics["mean_response_time"] > 0:

        metrics["latency_consistency"] = round(
            metrics["p95_response_time"]
            / metrics["mean_response_time"],
            2
        )

    # ==========================================================
    # CONVENIENCE ALIASES
    #
    # dashboard.py historically read short key names ("mean",
    # "requests", ...) while this parser emitted long ones
    # ("mean_response_time", "total_requests", ...). That mismatch
    # was the root cause of response-time metrics showing as 0 on
    # the dashboard. Keeping both names here makes the contract
    # explicit and prevents the bug from silently coming back.
    # ==========================================================

    metrics["requests"] = metrics["total_requests"]
    metrics["mean"] = metrics["mean_response_time"]
    metrics["median"] = metrics["median_response_time"]
    metrics["p90"] = metrics["p90_response_time"]
    metrics["p95"] = metrics["p95_response_time"]

    return metrics