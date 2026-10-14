"""Mide OCR exacto y resultado asistido por separado. No disfraza correcciones de aciertos."""
import io
import json
from pathlib import Path
import sys
from time import perf_counter
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app import app
from solver import solve_board

def benchmark(manifest_name="manifest.json", report_name="benchmark.json"):
    app.config["TESTING"]=True
    client=app.test_client()
    headers={"X-Sudoku-Request":"1"}
    fixtures=ROOT/"tests/fixtures"
    manifest=json.loads((fixtures/manifest_name).read_text())
    rows=[]
    for puzzle in manifest:
        for variant,filename in puzzle["images"].items():
            start=perf_counter()
            response=client.post("/api/read",data={"image":(io.BytesIO((fixtures/filename).read_bytes()),filename)},headers=headers)
            data=response.get_json()
            item={"sudoku":puzzle["id"],"variant":variant,"http":response.status_code,
                  "seconds":round(perf_counter()-start,3),"exact":False}
            if response.status_code==200:
                truth=np.array(puzzle["board"])
                # read_image devuelve la orientación elegida; comparar las pistas en esa orientación.
                source_turns=3 if variant=="giro_90" else 0
                turns=(source_turns+data["rotation"]//90)%4
                target=np.rot90(truth,turns)
                actual=np.array(data["board"])
                item.update(exact=bool(np.array_equal(actual,target)),
                            wrong_cells=int((actual!=target).sum()),
                            missing_digits=int(((actual==0)&(target!=0)).sum()),
                            extra_digits=int(((actual!=0)&(target==0)).sum()),
                            uncertain=len(data["uncertain"]),conflicts=len(data["conflicts"]),
                            board=data["board"],rotation=data["rotation"])
                raw_result=solve_board(data["board"])
                item["uncorrected_status"]=raw_result["status"]
                if raw_result["status"]=="solved":
                    item["uncorrected_matches_original"]=bool(np.array_equal(raw_result["solution"],np.rot90(puzzle["solution"],turns)))
                # Simula explícitamente una corrección humana con las pistas verdaderas.
                assisted=client.post("/api/solve",json={"confirmed":True,"board":target.tolist()},headers=headers).get_json()
                item["after_review_correct"]=assisted["status"]=="solved" and bool(np.array_equal(assisted["solution"],np.rot90(puzzle["solution"],turns)))
            else:
                assert response.status_code==422,data
                item["message"]=data["message"]
            rows.append(item)
            print({k:v for k,v in item.items() if k!="board"},flush=True)
    output=ROOT/"docs";output.mkdir(exist_ok=True)
    (output/report_name).write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding="utf-8")
    assert all(r.get("after_review_correct",True) for r in rows)
    assert len(rows)==sum(len(p["images"]) for p in manifest)
    assert all(r.get("uncorrected_matches_original",True) for r in rows)
    print("EXACTOS",sum(r["exact"] for r in rows),"RECHAZADOS",sum(r["http"]!=200 for r in rows))
    return rows

if __name__=="__main__":
    benchmark(*sys.argv[1:])
