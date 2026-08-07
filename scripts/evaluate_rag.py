import json, re
from pathlib import Path
from app.rag import RAGService, NO_RESULT

def norm(s): return re.sub(r"\s+"," ",s.lower()).strip()
def main():
    tests=json.loads(Path("data/eval_dataset.json").read_text(encoding="utf-8")); rag=RAGService(); rows=[]
    for t in tests:
        out=rag.ask(t["question"]); ans=out["answer"]; predicted_negative=(ans==NO_RESULT or not out["sources"])
        if t["expect_no_result"]: ok=predicted_negative
        else:
            terms=[norm(x) for x in t.get("required_terms",[])]; ok=(not predicted_negative and all(x in norm(ans) for x in terms))
        rows.append({"id":t["id"],"question":t["question"],"correct":ok,"negative":t["expect_no_result"],"answer":ans})
    accuracy=sum(x["correct"] for x in rows)/len(rows)
    negatives=[x for x in rows if x["negative"]]; negative_accuracy=sum(x["correct"] for x in negatives)/max(1,len(negatives))
    report={"n":len(rows),"accuracy":round(accuracy,3),"negative_accuracy":round(negative_accuracy,3),"results":rows}
    Path("reports").mkdir(exist_ok=True); Path("reports/evaluation.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({k:v for k,v in report.items() if k!="results"},indent=2))
if __name__=="__main__": main()
