from pathlib import Path
import re

p = Path("src/scripts/form_d_example_trace.py")
s = p.read_text(encoding="utf-8")

pattern = r'except HtmlPostCheckError:\s*\n(\s*)status = "FAIL_VALIDATION"'
replacement = (
    'except HtmlPostCheckError as e:\n'
    r'\1print("VALIDATION ERROR:", e)' '\n'
    r'\1save_text(OUT_DIR / "result_failed.html", patched)' '\n'
    r'\1status = "FAIL_VALIDATION"'
)

s2 = re.sub(pattern, replacement, s, count=1)
if s2 == s:
    raise RuntimeError("target block not found")

p.write_text(s2, encoding="utf-8")
print("patched", p)
