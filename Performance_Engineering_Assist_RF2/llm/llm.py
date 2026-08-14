import os
import re

import httpx
import streamlit as st
from langchain_openai import ChatOpenAI

from .prompt import SYSTEM_PROMPT


# =====================================================================
# HACKATHON QUICK-FIX FALLBACK
#
# If secrets.toml / environment variables aren't being picked up and
# you're out of time, fill these in directly as a fallback. They're
# only used when GENAI_API_KEY isn't found anywhere else, so
# secrets.toml still takes priority once you get it working.
#
# ⚠️ Remove/blank these out before pushing this code anywhere public
# (GitHub, a shared drive, etc.) — this key becomes visible to anyone
# with the file otherwise.
# =====================================================================
FALLBACK_API_KEY = "sk-bpXoPH9jL64_6orHh8hP1A"
FALLBACK_BASE_URL = "https://genailab.tcs.in"
FALLBACK_MODEL = "azure/genailab-maas-gpt-4o-mini"
FALLBACK_VERIFY_SSL = "false"


def _get_config_value(key: str, default: str = "") -> str:
    """
    Reads config from st.secrets first (.streamlit/secrets.toml), then
    an environment variable, then the FALLBACK_* constants above.
    """
    try:
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass

    env_value = os.getenv(key)
    if env_value:
        return env_value

    fallback_map = {
        "GENAI_API_KEY": FALLBACK_API_KEY,
        "GENAI_BASE_URL": FALLBACK_BASE_URL,
        "GENAI_MODEL": FALLBACK_MODEL,
        "GENAI_VERIFY_SSL": FALLBACK_VERIFY_SSL,
    }

    return fallback_map.get(key, default)


def _build_llm():
    # --- HARDCODED FOR HACKATHON DEMO (secrets.toml wasn't loading in time) ---
    # TODO: remove these hardcoded values and rotate this key after the demo.
    base_url = _get_config_value("GENAI_BASE_URL", "https://genailab.tcs.in")
    api_key = _get_config_value("GENAI_API_KEY", "sk-bpXoPH9jL64_6orHh8hP1A")
    model = _get_config_value("GENAI_MODEL", "azure/genailab-maas-gpt-4o-mini")
    verify_ssl = False
    # --- END HARDCODED BLOCK ---

    if not api_key:
        raise RuntimeError(
            "No LLM API key configured. Add GENAI_API_KEY (and optionally "
            "GENAI_BASE_URL / GENAI_MODEL) to .streamlit/secrets.toml or as "
            "environment variables before generating a k6 script."
        )

    client = httpx.Client(verify=verify_ssl)

    return ChatOpenAI(
        base_url=base_url,
        model=model,
        api_key=api_key,
        http_client=client,
        temperature=0,
    )


def _strip_code_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:javascript|js)?\s*", "", text)
    text = re.sub(r"```\s*$", "", text)
    return text.strip()


def generate_k6_script(
    journey_json: str,
    target_url: str = "http://localhost:5000",
    max_vus: int = 300,
    ramp_up: str = "30s",
    hold: str = "1m",
    ramp_down: str = "30s",
    p95_threshold_ms: int = 500,
) -> str:

    llm = _build_llm()

    prompt = f"""
{SYSTEM_PROMPT}

Journey JSON:

{journey_json}

Target URL:
{target_url}

Load profile:
- Ramp up to {max_vus} virtual users over {ramp_up}
- Hold {max_vus} virtual users for {hold}
- Ramp down over {ramp_down}
- p(95) threshold: {p95_threshold_ms}ms

IMPORTANT:
- Return ONLY JavaScript.
- Do not use markdown.
- Do not wrap in ```javascript.
"""

    try:
        response = llm.invoke(prompt)
    except Exception as e:
        # The OpenAI SDK often wraps the real httpx/network exception and
        # only exposes a generic "Connection error." message. The actual
        # cause (DNS failure, TLS error, timeout, proxy block...) is
        # usually chained on __cause__ -- surface it so this is debuggable.
        cause_chain = []
        current = e
        seen = set()
        while current is not None and id(current) not in seen:
            seen.add(id(current))
            cause_chain.append(f"{type(current).__name__}: {current}")
            current = current.__cause__ or current.__context__

        detail = " -> caused by -> ".join(cause_chain)

        raise RuntimeError(
            f"Could not reach {base_url}.\n\n"
            f"Full error chain: {detail}\n\n"
            "If this is an internal/corporate endpoint behind a proxy "
            "with a self-signed certificate, set "
            'GENAI_VERIFY_SSL = "false" in .streamlit/secrets.toml. '
            "Also confirm VPN/network access to this host, and that "
            "GENAI_BASE_URL is exactly correct (no trailing path issues)."
        ) from e

    return _strip_code_fences(response.content)
