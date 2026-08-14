# LoadPilot — Refinement Notes

## 1. The bug that was hiding your response-time metrics

`dashboard/k6_txt_parser.py` returned keys like `mean_response_time`,
`total_requests`, `median_response_time`... but `dashboard/dashboard.py`
was reading `metrics.get("mean")`, `metrics.get("requests")`,
`metrics.get("median")` — **different key names**. Every lookup silently
fell back to its `0` default, so response time, request counts, etc.
always rendered as zero regardless of what k6 actually reported.

Fixed in two places so it can't regress silently:
- `k6_txt_parser.py` now also emits the short aliases (`mean`, `median`,
  `p90`, `p95`, `requests`) alongside the descriptive names.
- `dashboard.py` now reads with a fallback (`metrics.get("mean",
  metrics.get("mean_response_time", 0))`) so it tolerates either key
  set.
- Also hardened the parser: `re.DOTALL` on the duration regex, and a
  fallback for `successful_requests`/`failed_requests` when a script
  has no `check()` calls (so `checks_succeeded` never appears in k6
  output).

## 2. CPU/memory telemetry was 100% `np.random`, unrelated to the test

`dashboard/telemetry.py` previously generated CPU/memory/disk/network
numbers from `np.sin` + `np.random.normal` — pure noise with no
connection to the actual load test. Replaced with two real sources:

- **Live**: `utils/k6_runner.py` runs `k6 run <script>` as a subprocess
  and samples real CPU/memory/disk I/O/network I/O via `psutil` once
  per second while the test executes (Step 4 → "Run k6 from this app").
- **Estimated**: if you only have a results file from a run on another
  machine, the app can't know that machine's real hardware numbers —
  so instead of noise, `estimate_telemetry_from_metrics()` derives a
  ramp-up/plateau/ramp-down curve shaped by the *actual* k6 output
  (VUs, throughput, p95, error rate). Every dashboard section is
  labelled **LIVE MEASUREMENT** or **ESTIMATED** so nobody mistakes one
  for the other — this is important to say out loud to hackathon judges
  rather than let them assume it's a real APM feed.

For a production version, wire `render_dashboard()` up to Prometheus /
Datadog / CloudWatch instead of either of these.

## 3. Hardcoded API key & endpoint

`llm/llm.py` had a live API key and an internal base URL committed in
plaintext. Moved to `st.secrets` / environment variables
(`GENAI_API_KEY`, `GENAI_BASE_URL`, `GENAI_MODEL`) — see
`.streamlit/secrets.toml.example`. **Rotate the key that was in the
original file before your demo**, since it's now been exposed in the
zip/repo history.

## 4. "I keep re-uploading and redoing everything"

The whole pipeline used to live in one linear `if uploaded_file:` block,
so every widget interaction re-ran the script and nothing was cached.
`app.py` now stores each stage's output in `st.session_state`
(parsed logs, sessions, journeys, script, k6 metrics, telemetry) and
uses a sidebar stepper to move between stages — you can jump back to
Step 2 to tweak the journey count without re-uploading the CSV or
re-generating the script.

## 5. UI

- Dark enterprise theme (`utils/theme.py`): consistent card styling,
  a gradient header, and a `LIVE MEASUREMENT` / `ESTIMATED` badge
  system instead of a plain caption.
- 5-step sidebar wizard with a progress stepper (✅/⬜ per stage)
  instead of one long scrolling page.
- Step 3 now exposes target URL, max VUs, ramp timings, and the p95
  threshold as inputs instead of hardcoding `localhost:5000` inside
  the LLM prompt.
- Step 4 has an explicit choice between running k6 live from the app
  vs. uploading an existing results file, each with an accurate
  explanation of what telemetry you'll get.

## Setup

```bash
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml   # fill in your key
streamlit run app.py
```

k6 itself is a separate binary (not a Python package) — install it from
https://k6.io/docs/get-started/installation/ if you want live-run mode
in Step 4; otherwise the upload-results flow still works fully.
