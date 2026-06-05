import json
from typing import Any, Dict

import httpx


BASE_URL = "http://127.0.0.1:8000"


def pretty_print(title: str, payload: Dict[str, Any]) -> None:
    print(f"\n=== {title} ===")
    print(json.dumps(payload, indent=2))


def main() -> None:
    health = httpx.get(f"{BASE_URL}/health", timeout=20.0)
    pretty_print("Health", health.json())

    analyze = httpx.post(
        f"{BASE_URL}/analyze",
        json={
            "sequence": ">sample_1\nATGGCCATTGTAATGGGCCGCTGAAAGGGTGCCCGATAG",
        },
        timeout=20.0,
    )
    pretty_print("Analyze", analyze.json())

    local_search = httpx.post(
        f"{BASE_URL}/diseases/search",
        json={"query": "BRCA1"},
        timeout=20.0,
    )
    pretty_print("Local Disease Search", local_search.json())

    ncbi_search = httpx.post(
        f"{BASE_URL}/genes/search",
        json={"query": "BRCA1"},
        timeout=20.0,
    )
    pretty_print("NCBI Gene Search", ncbi_search.json())


if __name__ == "__main__":
    main()
