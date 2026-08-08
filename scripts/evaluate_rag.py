from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

import requests

API_URL = os.getenv(
    "PULS_EVENTS_API_URL",
    "https://puls-events-rag.onrender.com",
).rstrip("/")

DATASET_PATH = Path("data/eval_dataset.json")
REPORT_PATH = Path("reports/evaluation_render.json")
TIMEOUT = int(os.getenv("EVAL_TIMEOUT", "90"))
NO_RESULT = "Je n’ai trouvé aucun événement suffisamment pertinent pour cette demande."


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").casefold()).strip()


def ask_api(question: str) -> dict:
    response = requests.post(
        f"{API_URL}/ask",
        json={"question": question},
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("Réponse API invalide.")
    return payload


def source_blob(sources: list[dict]) -> str:
    parts = []
    for source in sources:
        parts.extend(
            str(source.get(k, ""))
            for k in ("title", "address", "city", "start", "end", "url")
        )
    return norm(" ".join(parts))


def ratio(num: int, den: int) -> float:
    return round(num / den, 3) if den else 0.0


def main() -> None:
    dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    results = []

    print(f"API évaluée : {API_URL}")

    for i, case in enumerate(dataset, start=1):
        print(f"[{i}/{len(dataset)}] {case['id']} : {case['question']}")
        t0 = time.perf_counter()

        try:
            output = ask_api(case["question"])
            sources = output.get("sources") or []
            answer = str(output.get("answer", ""))

            predicted_negative = (
                not sources
                or norm(answer) == norm(NO_RESULT)
                or "aucun événement suffisamment pertinent" in norm(answer)
            )

            expected_negative = bool(case.get("expect_no_result", False))
            expected_terms = [
                norm(x) for x in case.get("expected_source_terms", [])
            ]
            forbidden_terms = [
                norm(x) for x in case.get("forbidden_source_terms", [])
            ]

            blob = source_blob(sources)

            if expected_negative:
                correct = predicted_negative
            else:
                correct = (
                    bool(sources)
                    and all(term in blob for term in expected_terms)
                    and all(term not in blob for term in forbidden_terms)
                )

            relevances = [
                float(source["relevance"])
                for source in sources
                if source.get("relevance") is not None
            ]

            result = {
                "id": case["id"],
                "question": case["question"],
                "expected_negative": expected_negative,
                "correct": correct,
                "latency_seconds": round(time.perf_counter() - t0, 3),
                "answer": answer,
                "sources_count": len(sources),
                "max_relevance": (
                    round(max(relevances), 4) if relevances else None
                ),
                "backend_used": output.get("backend_used"),
                "retrieval": output.get("retrieval"),
                "sources": sources,
                "error": None,
            }

        except Exception as exc:
            result = {
                "id": case.get("id"),
                "question": case.get("question"),
                "expected_negative": bool(
                    case.get("expect_no_result", False)
                ),
                "correct": False,
                "latency_seconds": round(time.perf_counter() - t0, 3),
                "answer": "",
                "sources_count": 0,
                "max_relevance": None,
                "backend_used": None,
                "retrieval": None,
                "sources": [],
                "error": f"{type(exc).__name__}: {exc}",
            }

        results.append(result)

        print(
            f"  -> {'OK' if result['correct'] else 'ECHEC'} "
            f"| sources={result['sources_count']} "
            f"| max={result['max_relevance']} "
            f"| {result['latency_seconds']}s"
        )

        time.sleep(0.4)

    positives = [r for r in results if not r["expected_negative"]]
    negatives = [r for r in results if r["expected_negative"]]

    report = {
        "api_url": API_URL,
        "n": len(results),
        "positive_cases": len(positives),
        "negative_cases": len(negatives),
        "accuracy": ratio(
            sum(r["correct"] for r in results),
            len(results),
        ),
        "positive_accuracy": ratio(
            sum(r["correct"] for r in positives),
            len(positives),
        ),
        "negative_accuracy": ratio(
            sum(r["correct"] for r in negatives),
            len(negatives),
        ),
        "average_latency_seconds": round(
            sum(r["latency_seconds"] for r in results) / len(results),
            3,
        ),
        "backend_values": sorted(
            {r["backend_used"] for r in results if r["backend_used"]}
        ),
        "retrieval_values": sorted(
            {r["retrieval"] for r in results if r["retrieval"]}
        ),
        "results": results,
    }

    REPORT_PATH.parent.mkdir(exist_ok=True)
    REPORT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("\n=== RÉSULTATS GLOBAUX ===")
    print(f"Score global    : {report['accuracy'] * 100:.1f}%")
    print(
        f"Cas positifs    : {report['positive_accuracy'] * 100:.1f}%"
    )
    print(
        f"Cas négatifs    : {report['negative_accuracy'] * 100:.1f}%"
    )
    print(
        f"Latence moyenne : {report['average_latency_seconds']} s"
    )
    print(
        f"Backend         : {', '.join(report['backend_values'])}"
    )
    print(
        f"Retrieval       : {', '.join(report['retrieval_values'])}"
    )
    print(f"Rapport         : {REPORT_PATH}")


if __name__ == "__main__":
    main()
