"""
export_csv.py
--------------
data/risk_training_data.csv를 만들 때 실제로 쓴 변환 스크립트입니다
(참고/재현용 -- data/risk_training_data.csv는 이미 이 저장소에 포함되어
있으므로 보통은 다시 실행할 필요가 없습니다).

원본은 YMAS(SynexAgent) 저장소의 backend/real_dataset.json(JSON,
116,262행)입니다. 이 저장소는 그 저장소와 별도이므로, 다시 실행하려면
YMAS 저장소를 옆에 clone해두고 --src로 경로를 지정하세요:

    python3 export_csv.py --src ../YMAS/backend/real_dataset.json

matched_drugs(리스트)는 CSV 셀에 못 넣으므로 ';'로 join한 문자열로 저장합니다.
"""

import argparse
import csv
import json
import os

DST = os.path.join(os.path.dirname(__file__), "data", "risk_training_data.csv")

FIELDS = [
    "patient_id",
    "drug_conflict",
    "comorbidity_load",
    "age_risk",
    "allergy_flag",
    "adverse_history",
    "label",
    "n_drugs",
    "matched_drugs",
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--src", default=os.path.join("..", "YMAS", "backend", "real_dataset.json"))
    args = parser.parse_args()
    rows = json.load(open(args.src, encoding="utf-8"))
    os.makedirs(os.path.dirname(DST), exist_ok=True)
    with open(DST, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow({
                "patient_id": r["patient_id"],
                "drug_conflict": r["drug_conflict"],
                "comorbidity_load": r["comorbidity_load"],
                "age_risk": r["age_risk"],
                "allergy_flag": r["allergy_flag"],
                "adverse_history": r["adverse_history"],
                "label": r["label"],
                "n_drugs": r["n_drugs"],
                "matched_drugs": ";".join(r["matched_drugs"]),
            })
    print(f"{len(rows)}행 -> {DST}")


if __name__ == "__main__":
    main()
