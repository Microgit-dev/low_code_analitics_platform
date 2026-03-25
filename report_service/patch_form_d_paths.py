from pathlib import Path

# 1) fix repo root in form_d_example_trace.py
script_path = Path("src/scripts/form_d_example_trace.py")
s = script_path.read_text(encoding="utf-8")
s2 = s.replace("parents[2]", "parents[1]")
if s2 == s:
    raise RuntimeError("parents[2] not found in form_d_example_trace.py")
script_path.write_text(s2, encoding="utf-8")

# 2) copy root fixtures into image in Dockerfile
dockerfile = Path("Dockerfile")
d = dockerfile.read_text(encoding="utf-8")
needle = "COPY src /app"
replacement = "COPY src /app\nCOPY form_d.html /app/form_d.html\nCOPY prompt_conversion_dps_new_2026.txt /app/prompt_conversion_dps_new_2026.txt"
if needle not in d:
    raise RuntimeError("COPY src /app not found in Dockerfile")
d2 = d.replace(needle, replacement, 1)
dockerfile.write_text(d2, encoding="utf-8")

print("patched", script_path)
print("patched", dockerfile)
