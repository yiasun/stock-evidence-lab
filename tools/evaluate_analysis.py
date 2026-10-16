"""Offline validator regression, not a measurement of model accuracy."""
import argparse
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from ai_layer import _validated_analysis, OUTPUT_REASONS
from diagnosis import cards, load_data


def evaluate():
    evidence=cards(load_data())
    cases=json.loads((ROOT/"tests/fixtures/analysis_cases.json").read_text(encoding="utf-8"))
    results=[]
    for case in cases:
        raw={"interpretations":[{"kind":case.get("kind","推断"),"text":case["text"],"evidence_ids":case["refs"]}],
             "research_questions":[{"question":"还需要核对哪些原始披露？","evidence_ids":["E4"]}]}
        reason=""
        try:
            _validated_analysis(raw,evidence)
            outcome="accept"
        except (ValueError,KeyError,TypeError) as exc:
            outcome="reject"
            reason=OUTPUT_REASONS.get(str(exc),"invalid_json_or_shape")
        results.append({"id":case["id"],"expected":case["expected"],"actual":outcome,"passed":outcome==case["expected"],"reason":reason})
    return {"kind":"offline_validator_regression","model_calls":0,
            "limitation":"固定样本的校验回归，不代表真实模型准确率或完整语义核验。",
            "total":len(results),"passed":sum(r["passed"] for r in results),"cases":results}


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path)
    args=parser.parse_args()
    result=evaluate()
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Offline validator regression: {result['passed']}/{result['total']}; model calls: 0")
    sys.exit(0 if result["passed"]==result["total"] else 1)
