"""Authored boundary regression, never an estimate of live model accuracy."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ai_layer import _validated_analysis, OUTPUT_REASONS
from diagnosis import cards, load_data


def evaluate():
    evidence = cards(load_data())
    cases = json.loads((ROOT / "tests/fixtures/boundary_challenge.json").read_text(encoding="utf-8"))
    results = []
    for case in cases:
        raw = {"interpretations": [{"kind": "推断", "text": case["text"], "evidence_ids": case["refs"]}],
               "research_questions": [{"question": "还需核对哪些原始披露？", "evidence_ids": case["refs"]}]}
        reason = ""
        try:
            _validated_analysis(raw, evidence)
            actual = "accept"
        except (ValueError, KeyError, TypeError) as exc:
            actual = "reject"
            reason = OUTPUT_REASONS.get(str(exc), "invalid_json_or_shape")
        results.append({**case, "actual": actual, "passed": actual == case["expected"], "reason": reason})
    negatives = [r for r in results if r["expected"] == "reject"]
    positives = [r for r in results if r["expected"] == "accept"]
    return {"kind": "authored_boundary_regression", "model_calls": 0,
            "ai_layer_sha256": hashlib.sha256((ROOT / "ai_layer.py").read_bytes()).hexdigest(),
            "limitation": "人工构造的开发回归集；不是独立留出集、用户研究或真实模型准确率。",
            "total": len(results), "passed": sum(r["passed"] for r in results),
            "unsafe_accepted": sum(r["actual"] == "accept" for r in negatives), "negative_total": len(negatives),
            "safe_rejected": sum(r["actual"] == "reject" for r in positives), "positive_total": len(positives),
            "cases": results}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = evaluate()
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Boundary regression: {result['passed']}/{result['total']}; unsafe accepted: {result['unsafe_accepted']}/{result['negative_total']}; safe rejected: {result['safe_rejected']}/{result['positive_total']}; model calls: 0")
    sys.exit(0 if result["passed"] == result["total"] else 1)
