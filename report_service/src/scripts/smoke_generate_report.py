from __future__ import annotations

import argparse
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup

SCRIPT_PATH = Path(__file__).resolve()
SRC_ROOT = SCRIPT_PATH.parent.parent
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from app.diagnostic_form_d import build_form_d_diagnostic_request


def main() -> None:
    parser = argparse.ArgumentParser(description="POST smoke-check for /reports/generate using the bundled form_d diagnostic payload.")
    parser.add_argument("--base-url", default="http://localhost:8085", help="API base URL")
    args = parser.parse_args()

    payload = build_form_d_diagnostic_request()
    response = requests.post(
        args.base_url.rstrip("/") + "/reports/generate",
        json=payload,
        timeout=60,
    )

    print(f"HTTP_STATUS={response.status_code}")
    print(response.text[:1000])

    if response.status_code != 200:
        raise SystemExit(1)

    data = response.json()
    missing = [key for key in ("sql", "rows", "html") if key not in data or not data[key]]
    if missing:
        raise RuntimeError(f"В ответе отсутствуют обязательные непустые поля: {missing}")

    template_html = payload["template_html"]
    out_html = data["html"]
    tpl = BeautifulSoup(template_html, "lxml")
    out = BeautifulSoup(out_html, "lxml")
    if len(out.select("td[rowspan], th[rowspan]")) < len(tpl.select("td[rowspan], th[rowspan]")):
        raise RuntimeError("В smoke-ответе потеряны атрибуты rowspan.")
    if len(out.select("td[colspan], th[colspan]")) < len(tpl.select("td[colspan], th[colspan]")):
        raise RuntimeError("В smoke-ответе потеряны атрибуты colspan.")
    for selector in (".line", ".inline-line", ".total-line"):
        if any(not node.get_text(" ", strip=True) for node in out.select(selector)):
            raise RuntimeError(f"В smoke-ответе остались пустые специальные поля формы: {selector}")
    for token in ("{{owner_name}}", "{{report_period}}", "{{road_name}}", "{{accident_count}}", "{{sum(accident_count)}}"):
        if token not in out_html:
            raise RuntimeError(f"В smoke-ответе отсутствует обязательный placeholder: {token}")

    print("CHECKS=OK")


if __name__ == "__main__":
    main()
