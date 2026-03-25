#!/usr/bin/env python3
import argparse
import json
import os
import sys
import time
from urllib import request, error


def _print(obj):
    print(json.dumps(obj, ensure_ascii=False))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Smoke check for report_service: prints OK or probes API.")
    parser.add_argument("--mode", choices=["ok", "probe"],
                        default=os.environ.get("SMOKE_MODE", "ok"),
                        help="ok: print success and exit 0; probe: GET /openapi.json and succeed on HTTP 200")
    parser.add_argument("--base-url",
                        default=os.environ.get("BASE_URL", "http://localhost:8085"),
                        help="Base URL for probe mode (default: http://localhost:8085)")
    args = parser.parse_args()

    if args.mode == "ok":
        _print({"status": "ok", "message": "smoke check passed", "ts": int(time.time())})
        return 0

    # probe mode
    url = args.base_url.rstrip("/") + "/openapi.json"
    try:
        with request.urlopen(url, timeout=5) as resp:
            code = resp.getcode()
            ok = 200 <= code < 300
            if ok:
                _print({"status": "ok", "endpoint": url, "code": code})
                return 0
            else:
                _print({"status": "fail", "endpoint": url, "code": code})
                return 2
    except error.URLError as e:
        _print({"status": "fail", "endpoint": url, "error": str(e)})
        return 2


if __name__ == "__main__":
    sys.exit(main())
