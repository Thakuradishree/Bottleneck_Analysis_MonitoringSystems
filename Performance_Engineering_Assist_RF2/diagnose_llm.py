"""
Run this directly to test connectivity to the GenAI endpoint, completely
outside Streamlit and LangChain, so we can see the REAL underlying error
instead of the OpenAI SDK's generic "Connection error." message.

Usage:
    python diagnose_llm.py
"""

import httpx

BASE_URL = "https://genailab.tcs.in"
API_KEY = "sk-bpXoPH9jL64_6orHh8hP1A"
MODEL = "azure/genailab-maas-gpt-4o-mini"


def main():
    print(f"Testing connection to: {BASE_URL}")
    print("-" * 60)

    # Step 1: raw TCP/TLS reachability, verify=False (matches original code)
    for verify in (False, True):
        print(f"\n[Step 1] httpx GET {BASE_URL}  (verify={verify})")
        try:
            resp = httpx.get(BASE_URL, timeout=10, verify=verify)
            print(f"  -> reachable. status_code={resp.status_code}")
        except Exception as e:
            print(f"  -> FAILED: {type(e).__name__}: {e}")

    # Step 2: actual chat completions call, matching what the app does
    print(f"\n[Step 2] POST {BASE_URL}/chat/completions  (verify=False)")
    try:
        resp = httpx.post(
            f"{BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": MODEL,
                "messages": [{"role": "user", "content": "Say OK"}],
                "max_tokens": 5,
            },
            timeout=30,
            verify=False,
        )
        print(f"  -> status_code={resp.status_code}")
        print(f"  -> body: {resp.text[:500]}")
    except Exception as e:
        print(f"  -> FAILED: {type(e).__name__}: {e}")

    print("\n" + "-" * 60)
    print("Read the failures above:")
    print("  - 'NameResolutionError' / 'getaddrinfo failed' -> DNS can't")
    print("    resolve genailab.tcs.in -> you need to be on the TCS VPN.")
    print("  - 'ConnectTimeout' -> host resolves but nothing answers ->")
    print("    also usually a VPN/network access issue, or the host is down.")
    print("  - 'SSLCertVerificationError' with verify=True but NOT with")
    print("    verify=False -> confirms it's a self-signed cert issue,")
    print("    set GENAI_VERIFY_SSL=false in secrets.toml.")
    print("  - HTTP status 401/403 -> reachable, but the API key is wrong")
    print("    or expired.")
    print("  - HTTP status 404 -> reachable, but the URL path is wrong")
    print("    for this gateway (may need a different route than")
    print("    /chat/completions, e.g. an Azure-style deployment path).")


if __name__ == "__main__":
    main()
