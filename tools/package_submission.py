"""Create a reproducible source handoff from tracked files only."""
import argparse
import hashlib
import json
import subprocess
import zipfile
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def git(*args):
    return subprocess.run(["git",*args],cwd=ROOT,check=True,capture_output=True,text=True).stdout.strip()


def package(ci_url="", version="3.0"):
    if version not in {"3.0", "4.0"}:
        raise ValueError("Unsupported bundle version")
    if git("status","--porcelain","--untracked-files=normal"):
        raise RuntimeError("Commit the intended submission files before packaging")
    revision=git("rev-parse","HEAD")
    output=ROOT/f"output/stock-evidence-lab-v{version.split('.')[0]}.zip"
    output.parent.mkdir(exist_ok=True)
    git("archive","--format=zip","--prefix=stock-evidence-lab/","HEAD","-o",str(output))
    with zipfile.ZipFile(output) as archive:
        files=archive.namelist()
        for name in files:
            parts=Path(name).parts
            if any(p in {".git",".env","secrets.toml",".venv","__pycache__"} for p in parts):
                raise ValueError("Archive contains a private or temporary path")
        required=["app.py","README.md","docs/HANDOFF.md","docs/PRODUCT_REPORT.md",
                  "docs/DEMO.md","docs/images/submission-ui.png","output/pdf/stock-evidence-lab-report.pdf",
                  "output/stock-evidence-example.md","tests/fixtures/analysis_cases.json"]
        if version == "4.0":
            required += ["presentation.py", "styles.css", "docs/UPGRADE_V4.md", "docs/TEST_REPORT_V4.md",
                         "docs/DEMO_V4.md", "docs/DEPLOY_V4.md", "docs/images/v4-en-desktop.jpg",
                         "docs/images/v4-zh-desktop.jpg", "docs/validation/v4-checks.json",
                         "tests/test_international_experience.py"]
        if any("stock-evidence-lab/"+name not in files for name in required):
            raise ValueError("Archive lacks a required deliverable")
        if not archive.read("stock-evidence-lab/output/pdf/stock-evidence-lab-report.pdf").startswith(b"%PDF-"):
            raise ValueError("Report is not a PDF")
        if archive.read("stock-evidence-lab/output/pdf/stock-evidence-lab-report.pdf") != (ROOT/"output/pdf/stock-evidence-lab-report.pdf").read_bytes():
            raise ValueError("Archived PDF bytes differ from the reviewed local file")
        if "stock-evidence-lab/report.pdf" in files:
            raise ValueError("Legacy invalid download must not be shipped")
    manifest={"app_version":version,"git_commit":revision,"created_at":datetime.now(timezone.utc).isoformat(),
              "archive":output.name,"bytes":output.stat().st_size,"sha256":hashlib.sha256(output.read_bytes()).hexdigest(),
              "tracked_entries":len(files),"ci_url":ci_url,"checks":["tracked_files_only","required_deliverables_present","valid_pdf_header","no_secret_or_environment_paths"]}
    (ROOT/"output/submission-manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(manifest,ensure_ascii=False,indent=2))


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--ci-url",default="")
    parser.add_argument("--version", choices=["3.0", "4.0"], default="3.0")
    args=parser.parse_args()
    package(args.ci_url, args.version)
