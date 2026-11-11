"""Run the complete release checks and retain portable, honest test evidence."""
import hashlib
import importlib.metadata
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "docs" / "validation"
MODULES = ["app.py", "diagnosis.py", "ai_layer.py", "request_gate.py", "research_export.py", "review_records.py", "presentation.py"]


def validate():
    DEST.mkdir(parents=True, exist_ok=True)
    commands = [
        ("compile", [sys.executable, "-m", "compileall", "-q", *MODULES]),
        ("unit", [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"]),
        ("analysis", [sys.executable, "tools/evaluate_analysis.py", "--output", "docs/validation/v4-analysis.json"]),
        ("boundary", [sys.executable, "tools/evaluate_boundary_challenge.py", "--output", "docs/validation/v4-boundary.json"]),
        ("whitespace", ["git", "diff", "--check"]),
    ]
    results = []
    for name, command in commands:
        result = subprocess.run(command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                encoding="utf-8", errors="replace")
        output = result.stdout.replace(str(ROOT), "<repo>")
        (DEST / f"v4-{name}.txt").write_text(output, encoding="utf-8")
        results.append({"check": name, "command": ["python" if x == sys.executable else x for x in command],
                        "exit_code": result.returncode, "log": f"v4-{name}.txt"})
        print(f"{name}: exit {result.returncode}", flush=True)
    hashed = MODULES + ["styles.css", "requirements.txt", "data/evidence.json", "data/market_verified.csv"]
    manifest = {"checked_at_utc": datetime.now(timezone.utc).isoformat(), "python": platform.python_version(),
                "platform": platform.system(), "packages": {p: importlib.metadata.version(p) for p in ["streamlit", "pandas", "numpy", "requests"]},
                "checks": results, "model_calls": 0,
                "sha256_lf_normalized": {p: hashlib.sha256((ROOT / p).read_bytes().replace(b"\r\n", b"\n")).hexdigest() for p in hashed},
                "limits": "Unit tests use mocked AI calls. Offline authored fixtures are not live-model accuracy or user validation. Browser QA is recorded separately."}
    (DEST / "v4-checks.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0 if all(r["exit_code"] == 0 for r in results) else 1


if __name__ == "__main__":
    sys.exit(validate())
