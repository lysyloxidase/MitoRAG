"""Pull and smoke-test the configured Ollama reasoning model."""

from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _post_json(host: str, endpoint: str, payload: Dict[str, Any], timeout: int) -> Dict[str, Any]:
    request = urllib.request.Request(
        f"{host.rstrip('/')}{endpoint}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read().decode("utf-8")
    loaded = json.loads(body)
    if not isinstance(loaded, dict):
        raise RuntimeError(f"Ollama returned non-object JSON from {endpoint}")
    return loaded


def pull_model(host: str, model: str, timeout: int) -> None:
    _post_json(host, "/api/pull", {"name": model, "stream": False}, timeout)


def generate_smoke(host: str, model: str, timeout: int) -> str:
    payload = {
        "model": model,
        "prompt": (
            "Answer in one short sentence: what organelle performs oxidative "
            "phosphorylation?"
        ),
        "stream": False,
        "options": {"temperature": 0},
    }
    response = _post_json(host, "/api/generate", payload, timeout)
    text = response.get("response")
    if not isinstance(text, str) or not text.strip():
        raise RuntimeError("Ollama smoke test returned an empty response")
    return text.strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", default=".env", help="Path to dotenv file")
    parser.add_argument("--model", default=None, help="Override MODEL_REASONING")
    parser.add_argument("--skip-pull", action="store_true", help="Only run generation")
    parser.add_argument("--timeout", type=int, default=1800, help="HTTP timeout in seconds")
    args = parser.parse_args()

    _load_dotenv(Path(args.env_file))
    host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    model = args.model or os.environ.get("MODEL_REASONING", "qwen2.5:14b-instruct-q4_K_M")

    try:
        if not args.skip_pull:
            print(f"Pulling {model} from {host}...")
            pull_model(host, model, args.timeout)
        answer = generate_smoke(host, model, args.timeout)
    except urllib.error.URLError as exc:
        raise SystemExit(f"Ollama is not reachable at {host}: {exc}") from exc

    print(f"Ollama smoke test passed with {model}: {answer}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
