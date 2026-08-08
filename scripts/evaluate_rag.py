from __future__ import annotations

import json
import re
from pathlib import Path

from app.rag import NO_RESULT, RAGService


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").casefold()).strip()


def main():
    dataset = json.loads(
        Path("data/eval_dataset.json").read_text(encoding="utf-8")
    )
    rag = RAGService()
    results = []

    for case in dataset:
        output = rag.ask(case["question"])
        sources = output.get("sources", [])
        answer = output.get("answer", "")
        predicted_negative = not sources or norm(answer) == norm(NO_RESULT)

        if case.get("expect_no_result", False):
            correct = predicted_negative
        else:
            expected = [norm(x) for x in case.get("expected_source_terms", [])]
            source_blob = norm(
                " ".join(
                    f"{s.get('title','')} {s.get('address','')} {s.get('city','')}"
                    for s in sources
                )
            )
            # Pour un cas positif, on mesure d'abord le retrieval :
            # au moins une source doit être retournée, puis les termes annotés
            # sont recherchés dans les sources si le dataset en fournit.
            correct = bool(sources) and all(term in source_blob for term in expected)

        results.append(
            {
                "id": case["id"],
                "question": case["question"],
                "expected_negative": case.get("expect_no_result", False),
                "correct": correct,
                "answer": answer,
                "sources": sources,
            }
        )

    n = len(results)
    negatives = [x for x in results if x["expected_negative"]]
    positives = [x for x in results if not x["expected_negative"]]

    report = {
        "n": n,
        "accuracy": round(sum(x["correct"] for x in results) / max(1, n), 3),
        "negative_accuracy": round(
            sum(x["correct"] for x in negatives) / max(1, len(negatives)), 3
        ),
        "positive_accuracy": round(
            sum(x["correct"] for x in positives) / max(1, len(positives)), 3
        ),
        "results": results,
    }

    Path("reports").mkdir(exist_ok=True)
    Path("reports/evaluation.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({k: v for k, v in report.items() if k != "results"}, indent=2))


if __name__ == "__main__":
    main()
