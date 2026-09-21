"""
build_dataset_v3.py
---------------------
build_dataset_v2.py와 특성 계산 방식은 동일하지만, **라벨(label) 정의를
확장**합니다. v2까지는 다음 한 가지 기준만으로 "위험(1)"을 정했습니다:

    label = 1 if danger_count > 0 else 0   # 즉 drug_conflict가 0이 아니면 위험

이 기준은 사실상 drug_conflict 하나로만 결정되는 것이라, v2에서
polypharmacy_load/adverse_history 등 새 특성을 추가해도 순열 중요도를
재보면 drug_conflict 혼자 F1의 86%p를 차지하고 나머지는 거의 기여가
없었습니다(자세한 내용은 이 저장소 README.md의 "v2" 절 참고) — 특성이
아무리 좋아도 라벨이 그 특성을 안 쓰면 모델이 배울 수가 없기 때문입니다.

v3는 임상적으로 근거 있는 3가지 기준을 라벨에 추가합니다(이제 OR 조건):

  1. 기존: 약물 상호작용/기저질환/알레르기 규칙에서 "위험" 알림이 1개
     이상 (danger_count > 0)
  2. 신규: **과다 다약제(hyperpolypharmacy)** -- 매칭된 약물이 10종 이상.
     노인약료·임상약학 문헌에서 통상 5~9종을 "다약제(polypharmacy)",
     10종 이상을 "과다 다약제"로 구분하며, 개별 상호작용이 없어도
     그 자체로 이상반응 위험이 유의하게 증가한다고 알려져 있습니다.
     (이 데이터셋 기준 6.0%가 해당)
  3. 신규: **중증(SEVERE) 약물 알레르기/불내성 이력** -- 특정 약물
     상호작용과 무관하게, 심각한 과거 반응 이력 자체가 독립적인
     안전 신호입니다. (이 데이터셋 기준 0.27%가 해당)
  4. 신규: **경미한 경고가 누적** -- "위험"까지는 아니어도 "주의" 알림이
     3개 이상 겹치면(다중 약물군 중복, 복수 기저질환 상호작용 등)
     누적 위험으로 봅니다 (caution_count >= 3).

**주의**: 이 기준(10종, SEVERE, 3개)은 실제 임상 가이드라인 문헌에 근거를
두되, 이 프로젝트에서 채택한 것입니다 -- 실제 병원에 적용하려면 반드시
임상 전문가 검토를 거쳐야 합니다.

사용법: python3 build_dataset_v3.py --csv-dir <synthea csv 폴더>
"""

import argparse
import csv
import json

from build_dataset_v2 import (
    audit, age_of, load_patient_data,
)

HYPERPOLYPHARMACY_THRESHOLD = 10
CAUTION_ESCALATION_THRESHOLD = 3
SEVERE_ADVERSE_HISTORY = 1.0


def build(csv_dir, today=None):
    from datetime import date
    if today is None:
        today = date(2026, 9, 2)
    patients, meds, conditions, allergies, med_dispenses, med_allergy_severity = load_patient_data(csv_dir)
    rows = []
    for pid, drug_ids in meds.items():
        if len(drug_ids) == 0:
            continue
        p = patients.get(pid)
        if not p:
            continue
        alerts = audit(drug_ids, conditions.get(pid, set()), allergies.get(pid, set()))
        danger_count = alerts.count("위험")
        caution_count = alerts.count("주의")

        drug_conflict = min(1.0, danger_count * 0.5 + caution_count * 0.2)
        comorbidity_load = min(1.0, len(conditions.get(pid, [])) / 5)
        age_risk = min(1.0, age_of(p["BIRTHDATE"], today) / 100)
        allergy_flag = 1.0 if allergies.get(pid) else 0.0
        adverse_history = round(med_allergy_severity.get(pid, 0.0), 3)

        n_drugs = len(drug_ids)
        polypharmacy_load = min(1.0, n_drugs / 10)
        dispenses = med_dispenses.get(pid, [])
        avg_dispenses = sum(dispenses) / len(dispenses) if dispenses else 0.0
        therapy_duration_load = round(min(1.0, avg_dispenses / 24), 3)

        label = 1 if (
            danger_count > 0
            or n_drugs >= HYPERPOLYPHARMACY_THRESHOLD
            or adverse_history >= SEVERE_ADVERSE_HISTORY
            or caution_count >= CAUTION_ESCALATION_THRESHOLD
        ) else 0

        rows.append({
            "patient_id": pid,
            "drug_conflict": round(drug_conflict, 3),
            "comorbidity_load": round(comorbidity_load, 3),
            "age_risk": round(age_risk, 3),
            "allergy_flag": allergy_flag,
            "adverse_history": adverse_history,
            "polypharmacy_load": round(polypharmacy_load, 3),
            "therapy_duration_load": therapy_duration_load,
            "label": label,
            "danger_count": danger_count,
            "caution_count": caution_count,
            "n_drugs": n_drugs,
            "matched_drugs": sorted(drug_ids),
        })
    return rows


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv-dir", required=True)
    parser.add_argument("--out", default="data/risk_training_data_v3.json")
    args = parser.parse_args()

    rows = build(args.csv_dir)
    n_pos = sum(r["label"] for r in rows)
    n_from_danger = sum(1 for r in rows if r["danger_count"] > 0)
    n_from_poly = sum(1 for r in rows if r["danger_count"] == 0 and r["n_drugs"] >= HYPERPOLYPHARMACY_THRESHOLD)
    n_from_severe = sum(1 for r in rows if r["danger_count"] == 0 and r["n_drugs"] < HYPERPOLYPHARMACY_THRESHOLD and r["adverse_history"] >= SEVERE_ADVERSE_HISTORY)
    n_from_caution = sum(1 for r in rows if r["label"] == 1 and r["danger_count"] == 0 and r["n_drugs"] < HYPERPOLYPHARMACY_THRESHOLD and r["adverse_history"] < SEVERE_ADVERSE_HISTORY)
    print(f"총 {len(rows)}명, 고위험 라벨 {n_pos}명 ({n_pos/len(rows)*100:.1f}%)")
    print(f"  - 기존 규칙(danger_count>0) 단독: {n_from_danger}명")
    print(f"  - 신규: 과다다약제(10종+)로 추가된 사람: {n_from_poly}명")
    print(f"  - 신규: 중증 약물알레르기로 추가된 사람: {n_from_severe}명")
    print(f"  - 신규: 주의알림 누적(3개+)로 추가된 사람: {n_from_caution}명")
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
    print(f"저장: {args.out}")
